from __future__ import annotations

import logging
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from backend.core.hardware import cleanup_vram, detect_hardware, find_binary
from backend.core.paths import FONTS_DIR, PRIMARY_FONT_FAMILY, PRIMARY_FONT_FILE

logger = logging.getLogger(__name__)

_whisper_lock = threading.Lock()
_whisper_model: Any = None
_whisper_model_key: tuple[str, str, str] | None = None


@dataclass(frozen=True)
class WordTimestamp:
    text: str
    start: float
    end: float


def hex_rgb_to_ass_bgr(hex_color: str) -> str:
    """
    Convert RGB hex color (e.g. '#FFE600') to ASS BGR color format ('&H0000E6FF&').
    ASS stores colors in BBGGRR byte order.
    """
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) != 6 or any(c not in "0123456789abcdefABCDEF" for c in cleaned):
        cleaned = "FFE600"
    rr = cleaned[0:2].upper()
    gg = cleaned[2:4].upper()
    bb = cleaned[4:6].upper()
    return f"&H00{bb}{gg}{rr}&"


def resolve_bundled_font_family() -> str:
    """Read the exact TrueType font family name from assets/fonts/Montserrat-ExtraBold.ttf."""
    font_path = FONTS_DIR / PRIMARY_FONT_FILE
    if font_path.is_file():
        try:
            from PIL import ImageFont

            family, _style = ImageFont.truetype(str(font_path), 48).getname()
            if family:
                return family
        except Exception:
            pass
    return PRIMARY_FONT_FAMILY


def _resolve_whisper_model_name(model_size: str | None) -> str:
    if model_size and model_size != "auto":
        return model_size
    hw = detect_hardware()
    return "small" if hw.cuda_available else "base"


def get_whisper_model(model_size: str | None = None) -> Any:
    """Load and cache faster-whisper model using CUDA float16 when available, else CPU int8."""
    global _whisper_model, _whisper_model_key
    from faster_whisper import WhisperModel

    resolved_size = _resolve_whisper_model_name(model_size)
    hw = detect_hardware()
    device = hw.whisper_device
    compute_type = hw.whisper_compute_type
    target_key = (resolved_size, device, compute_type)

    with _whisper_lock:
        if _whisper_model is not None and _whisper_model_key == target_key:
            return _whisper_model

        if _whisper_model is not None:
            _whisper_model = None
            _whisper_model_key = None
            cleanup_vram()

        logger.info(
            "Loading faster-whisper model=%s device=%s compute_type=%s",
            resolved_size,
            device,
            compute_type,
        )
        try:
            _whisper_model = WhisperModel(
                resolved_size,
                device=device,
                compute_type=compute_type,
            )
            _whisper_model_key = target_key
        except Exception as exc:
            if device == "cuda":
                logger.warning("CUDA Whisper load failed (%s); falling back to CPU int8", exc)
                _whisper_model = WhisperModel(resolved_size, device="cpu", compute_type="int8")
                _whisper_model_key = (resolved_size, "cpu", "int8")
            else:
                raise
        return _whisper_model


def unload_whisper_model() -> None:
    """Unload cached Whisper model and free VRAM before running heavy image generation."""
    global _whisper_model, _whisper_model_key
    with _whisper_lock:
        if _whisper_model is not None:
            logger.info("Unloading faster-whisper model to free memory/VRAM")
            _whisper_model = None
            _whisper_model_key = None
    cleanup_vram()


def _decode_audio_16k_f32(audio_path: Path) -> np.ndarray | str:
    """
    Decode any audio file to 16kHz mono float32 PCM via FFmpeg.
    Passing an ndarray directly to faster-whisper bypasses PyAV version mismatches
    (e.g. av>=19 removing av.open(metadata_errors=...)).
    """
    ffmpeg_path = find_binary("ffmpeg")
    if not ffmpeg_path:
        return str(audio_path)

    cmd = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=60)
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"FFmpeg audio decode failed for {audio_path}: {err}")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def transcribe_words(
    audio_path: Path,
    language: str,
    initial_prompt: str = "",
    model_size: str | None = None,
) -> list[WordTimestamp]:
    """
    Transcribe voiceover audio via faster-whisper and return monotonic word-level timestamps.
    """
    model = get_whisper_model(model_size)
    lang_code = "ru" if language.lower().startswith("ru") else "en"
    prompt_hint = initial_prompt.strip()[:220] if initial_prompt else None
    audio_input = _decode_audio_16k_f32(audio_path)

    segments, _info = model.transcribe(
        audio_input,
        language=lang_code,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 220},
        initial_prompt=prompt_hint,
    )

    words: list[WordTimestamp] = []
    last_end = 0.0
    for segment in segments:
        seg_words = getattr(segment, "words", None) or []
        for w in seg_words:
            raw_text = (w.word or "").strip()
            if not raw_text:
                continue
            start = max(float(w.start), last_end)
            end = max(float(w.end), start + 0.04)
            words.append(WordTimestamp(text=raw_text, start=start, end=end))
            last_end = start

    # Fix any overlapping end > next.start gently so consecutive word highlights never fight
    for i in range(len(words) - 1):
        if words[i].end > words[i + 1].start:
            words[i] = WordTimestamp(
                text=words[i].text,
                start=words[i].start,
                end=max(words[i].start + 0.04, words[i + 1].start),
            )
    return words


def group_words_into_chunks(
    words: list[WordTimestamp],
    max_words: int = 3,
    max_chars: int = 20,
    pause_threshold: float = 0.35,
) -> list[list[WordTimestamp]]:
    """Group word timestamps into punchy 2-3 word Shorts caption phrases."""
    chunks: list[list[WordTimestamp]] = []
    current: list[WordTimestamp] = []

    for word in words:
        if current:
            prev = current[-1]
            gap = word.start - prev.end
            current_chars = sum(len(x.text) + 1 for x in current) + len(word.text)
            prev_ends_sentence = prev.text.endswith((".", "!", "?", "…"))

            if (
                len(current) >= max_words
                or current_chars > max_chars
                or gap > pause_threshold
                or prev_ends_sentence
            ):
                chunks.append(current)
                current = []

        current.append(word)

    if current:
        chunks.append(current)
    return chunks


def _format_ass_time(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    hours, rem = divmod(total_cs, 360_000)
    minutes, rem = divmod(rem, 6_000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _sanitize_ass_text(text: str, uppercase: bool = True) -> str:
    cleaned = text.replace("{", "(").replace("}", ")").replace("\n", " ").strip()
    return cleaned.upper() if uppercase else cleaned


def generate_ass_subtitles(
    words: list[WordTimestamp],
    output_ass: Path,
    highlight_hex: str = "#FFE600",
    font_name: str | None = None,
    font_size: int = 86,
    uppercase: bool = True,
) -> Path:
    """
    Generate an Advanced SubStation Alpha (.ass) subtitle file (1080x1920)
    with centered safe-zone placement and word-by-word highlight animation.
    """
    resolved_font = font_name or resolve_bundled_font_family()
    highlight_bgr = hex_rgb_to_ass_bgr(highlight_hex)
    white_bgr = "&H00FFFFFF&"

    header = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            (
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding"
            ),
            (
                f"Style: Default,{resolved_font},{font_size},{white_bgr},{white_bgr},"
                "&H00000000&,&H80000000&,-1,0,0,0,100,100,1.5,0,1,8,4,5,90,90,120,1"
            ),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )

    chunks = group_words_into_chunks(words)
    events: list[str] = []

    for chunk in chunks:
        if not chunk:
            continue
        for active_idx, active_word in enumerate(chunk):
            start = active_word.start
            if active_idx + 1 < len(chunk):
                next_start = chunk[active_idx + 1].start
                if next_start - active_word.end <= 0.30:
                    end = max(start + 0.04, next_start)
                else:
                    end = max(start + 0.04, active_word.end + 0.08)
            else:
                end = max(start + 0.05, active_word.end + 0.05)

            parts: list[str] = []
            for idx, item in enumerate(chunk):
                token = _sanitize_ass_text(item.text, uppercase=uppercase)
                if not token:
                    continue
                if idx == active_idx:
                    parts.append(
                        f"{{\\c{highlight_bgr}\\fscx112\\fscy112\\t(0,75,\\fscx100\\fscy100)}}"
                        f"{token}"
                        f"{{\\c{white_bgr}\\fscx100\\fscy100}}"
                    )
                else:
                    parts.append(token)

            line_text = " ".join(parts)
            # Position at center-lower safe zone (below top hook card, above Shorts/TikTok bottom bar)
            styled_line = f"{{\\an5\\pos(540,1100)}}{line_text}"
            events.append(
                f"Dialogue: 0,{_format_ass_time(start)},{_format_ass_time(end)},Default,,0,0,0,,{styled_line}"
            )

    output_ass.parent.mkdir(parents=True, exist_ok=True)
    content = header + ("\n" + "\n".join(events) if events else "") + "\n"
    output_ass.write_text(content, encoding="utf-8", newline="\n")
    return output_ass
