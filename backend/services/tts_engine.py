from __future__ import annotations

import asyncio
import importlib.util
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.core.hardware import find_binary

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TTSResult:
    audio_path: Path
    raw_duration: float
    final_duration: float
    engine_used: str
    voice_used: str


VOICES: dict[str, list[dict[str, str]]] = {
    "ru": [
        {
            "id": "ru-RU-DmitryNeural",
            "name": "Дмитрий (Мужской, энергичный)",
            "gender": "Male",
            "engine": "edge",
        },
        {
            "id": "ru-RU-SvetlanaNeural",
            "name": "Светлана (Женский, четкий)",
            "gender": "Female",
            "engine": "edge",
        },
    ],
    "en": [
        {
            "id": "en-US-ChristopherNeural",
            "name": "Christopher (Male, storytelling)",
            "gender": "Male",
            "engine": "edge",
        },
        {
            "id": "en-US-AndrewNeural",
            "name": "Andrew (Male, warm)",
            "gender": "Male",
            "engine": "edge",
        },
        {
            "id": "en-US-GuyNeural",
            "name": "Guy (Male, punchy)",
            "gender": "Male",
            "engine": "edge",
        },
        {
            "id": "en-US-AriaNeural",
            "name": "Aria (Female, expressive)",
            "gender": "Female",
            "engine": "edge",
        },
        {
            "id": "en-GB-RyanNeural",
            "name": "Ryan (British Male)",
            "gender": "Male",
            "engine": "edge",
        },
    ],
}

SILERO_SPEAKERS: dict[str, str] = {
    "ru-RU-DmitryNeural": "aidar",
    "ru-RU-SvetlanaNeural": "kseniya",
    "aidar": "aidar",
    "baya": "baya",
    "kseniya": "kseniya",
    "eugene": "eugene",
    "en-US-ChristopherNeural": "en_0",
    "en-US-AriaNeural": "en_1",
}


def get_default_voice(language: str) -> str:
    lang = "ru" if language.lower().startswith("ru") else "en"
    return VOICES[lang][0]["id"]


def probe_audio_duration(audio_path: Path) -> float:
    """Measure media file duration in seconds using ffprobe."""
    ffprobe_path = find_binary("ffprobe")
    if not ffprobe_path:
        raise RuntimeError("ffprobe binary not found on PATH or ~/.local/bin")

    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {audio_path}: {proc.stderr.strip()}")
    try:
        return max(0.0, float(proc.stdout.strip()))
    except ValueError as exc:
        raise RuntimeError(f"Invalid ffprobe duration output: {proc.stdout!r}") from exc


def _parse_rate_multiplier(rate: str) -> float:
    """Convert '+15%' / '-5%' into FFmpeg atempo multiplier (e.g. 1.15)."""
    cleaned = rate.strip().rstrip("%")
    try:
        pct = float(cleaned)
    except ValueError:
        return 1.15
    mult = 1.0 + (pct / 100.0)
    return max(0.75, min(1.5, mult))


async def _synthesize_edge_tts(
    text: str,
    raw_mp3: Path,
    voice: str,
    rate: str,
) -> None:
    import edge_tts

    raw_mp3.parent.mkdir(parents=True, exist_ok=True)
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
            await communicate.save(str(raw_mp3))
            if raw_mp3.exists() and raw_mp3.stat().st_size > 1000:
                return
            raise RuntimeError("edge-tts produced empty audio file")
        except Exception as exc:
            last_exc = exc
            logger.warning("edge-tts attempt %d failed (%s)", attempt + 1, exc)
            await asyncio.sleep(0.8 * (attempt + 1))

    raise RuntimeError(f"edge-tts failed after 3 attempts: {last_exc}")


def _split_text_chunks(text: str, max_chars: int = 800) -> list[str]:
    """Split text into sentence-aware chunks for Silero TTS."""
    import re

    sentences = re.split(r"(?<=[.!?…])\s+", text.strip())
    chunks: list[str] = []
    buf = ""
    for sent in sentences:
        if len(buf) + len(sent) + 1 <= max_chars:
            buf = f"{buf} {sent}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = sent[:max_chars]
    if buf:
        chunks.append(buf)
    return chunks or [text[:max_chars]]


def _synthesize_silero_sync(
    text: str,
    raw_wav: Path,
    language: str,
    voice: str,
    rate: str,
) -> None:
    """Optional local Silero TTS via PyTorch (runs when torch is installed)."""
    import wave

    import numpy as np
    import torch  # type: ignore

    lang = "ru" if language.lower().startswith("ru") else "en"
    model_id = "v4_ru" if lang == "ru" else "v3_en"
    speaker = SILERO_SPEAKERS.get(voice, "aidar" if lang == "ru" else "en_0")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model, _example = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language=lang,
        speaker=model_id,
    )
    model.to(device)
    sample_rate = 48000

    audio_segments: list[Any] = []
    for chunk in _split_text_chunks(text):
        audio = model.apply_tts(
            text=chunk,
            speaker=speaker,
            sample_rate=sample_rate,
        )
        audio_segments.append(audio.cpu().numpy())

    combined = np.concatenate(audio_segments)
    pcm16 = np.clip(combined * 32767.0, -32768, 32767).astype(np.int16)

    raw_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(raw_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())

    # Apply rate adjustment into raw_wav -> mp3 handled in tightening step
    _ = _parse_rate_multiplier(rate)


def _tighten_and_normalize_audio(
    input_audio: Path,
    output_mp3: Path,
    trim_silence: bool = True,
    atempo: float = 1.0,
) -> None:
    """
    Remove dead pauses between sentences via FFmpeg silenceremove and normalize
    voice loudness via loudnorm so narration sounds crisp and punchy.
    """
    ffmpeg_path = find_binary("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg binary not found on PATH or ~/.local/bin")

    filters: list[str] = []
    if abs(atempo - 1.0) > 0.01:
        filters.append(f"atempo={atempo:.3f}")
    if trim_silence:
        filters.append(
            "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB:"
            "stop_periods=-1:stop_duration=0.22:stop_threshold=-42dB:stop_silence=0.12:"
            "detection=peak"
        )
    filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_audio),
        "-af",
        ",".join(filters),
        "-ar",
        "48000",
        "-ac",
        "1",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(output_mp3),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio post-processing failed: {proc.stderr.strip()}")


async def synthesize_speech(
    *,
    text: str,
    output_mp3: Path,
    language: str = "ru",
    voice: str | None = None,
    rate: str = "+15%",
    engine: str = "edge",
    trim_silence: bool = True,
) -> TTSResult:
    """
    Synthesize narration audio to MP3, trimming dead pauses and normalizing loudness.
    Uses edge-tts as primary engine, with optional Silero TTS when PyTorch is present.
    """
    lang = "ru" if language.lower().startswith("ru") else "en"
    resolved_voice = voice or get_default_voice(lang)
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    raw_file = output_mp3.with_name(f"{output_mp3.stem}_raw.mp3")
    engine_used = "edge"
    atempo = 1.0

    if engine.lower() == "silero":
        if importlib.util.find_spec("torch") is not None:
            raw_wav = output_mp3.with_name(f"{output_mp3.stem}_raw.wav")
            try:
                await asyncio.to_thread(
                    _synthesize_silero_sync,
                    text,
                    raw_wav,
                    lang,
                    resolved_voice,
                    rate,
                )
                raw_file = raw_wav
                engine_used = "silero"
                atempo = _parse_rate_multiplier(rate)
            except Exception as exc:
                logger.warning("Silero TTS failed (%s); falling back to edge-tts", exc)
        else:
            logger.info("PyTorch not installed; falling back from Silero to edge-tts")

    if engine_used == "edge":
        # Ensure edge-tts receives a valid voice ID for the language
        valid_ids = {v["id"] for v in VOICES[lang]}
        if resolved_voice not in valid_ids and "-" not in resolved_voice:
            resolved_voice = get_default_voice(lang)
        await _synthesize_edge_tts(text, raw_file, resolved_voice, rate)

    raw_duration = await asyncio.to_thread(probe_audio_duration, raw_file)
    await asyncio.to_thread(
        _tighten_and_normalize_audio,
        raw_file,
        output_mp3,
        trim_silence,
        atempo,
    )
    final_duration = await asyncio.to_thread(probe_audio_duration, output_mp3)

    # Clean intermediate raw file
    try:
        if raw_file.exists() and raw_file != output_mp3:
            raw_file.unlink()
    except OSError:
        pass

    return TTSResult(
        audio_path=output_mp3,
        raw_duration=raw_duration,
        final_duration=final_duration,
        engine_used=engine_used,
        voice_used=resolved_voice,
    )
