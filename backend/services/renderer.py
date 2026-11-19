from __future__ import annotations

import logging
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path

from backend.core.hardware import detect_hardware, find_binary
from backend.core.paths import BASE_DIR, FONTS_DIR, MUSIC_DIR, escape_ffmpeg_filter_path
from backend.services.tts_engine import probe_audio_duration

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderResult:
    output_mp4: Path
    duration_sec: float
    file_size_bytes: int
    encoder_used: str
    music_used: str | None


def list_music_tracks() -> list[Path]:
    exts = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
    if not MUSIC_DIR.exists():
        return []
    return sorted(p for p in MUSIC_DIR.iterdir() if p.is_file() and p.suffix.lower() in exts)


def pick_random_music(seed: int | None = None) -> Path | None:
    tracks = list_music_tracks()
    if not tracks:
        return None
    rng = random.Random(seed)
    return rng.choice(tracks)


def render_final_video(
    *,
    bg_video: Path,
    voice_audio: Path,
    ass_subtitles: Path,
    output_mp4: Path,
    hook_card_png: Path | None = None,
    music_path: Path | None = None,
    music_volume: float = 0.20,
    hook_duration: float = 3.6,
    force_encoder: str | None = None,
) -> RenderResult:
    """
    Assemble the final 1080x1920 60fps H.264/AAC vertical video using FFmpeg:
    - Auto-selected encoder (h264_nvenc on RTX GPU or libx264 fallback)
    - Optional timed Reddit/Story hook card overlay with smooth alpha fade
    - Burned-in ASS word-animated subtitles using bundled Cyrillic Montserrat fonts
    - Optional looping background music with sidechaincompress auto-ducking under voice
    """
    ffmpeg_path = find_binary("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg binary not found")

    hw = detect_hardware()
    encoder = force_encoder or hw.video_encoder

    voice_dur = probe_audio_duration(voice_audio)
    target_duration = max(1.5, voice_dur + 0.45)

    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error"]
    # Input 0: Background video (loop if ever slightly shorter than voice)
    cmd.extend(["-stream_loop", "-1", "-i", str(bg_video.resolve())])
    # Input 1: Voiceover audio
    cmd.extend(["-i", str(voice_audio.resolve())])

    next_idx = 2
    hook_idx: int | None = None
    if hook_card_png and hook_card_png.is_file():
        hook_idx = next_idx
        next_idx += 1
        cmd.extend(["-loop", "1", "-t", f"{hook_duration + 0.2:.2f}", "-i", str(hook_card_png.resolve())])

    music_idx: int | None = None
    if music_path and music_path.is_file():
        music_idx = next_idx
        next_idx += 1
        cmd.extend(["-stream_loop", "-1", "-i", str(music_path.resolve())])

    # Build video filtergraph using relative POSIX paths from BASE_DIR to avoid Windows C:\ issues
    ass_escaped = escape_ffmpeg_filter_path(ass_subtitles, cwd=BASE_DIR)
    fonts_escaped = escape_ffmpeg_filter_path(FONTS_DIR, cwd=BASE_DIR)

    v_filters: list[str] = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "fps=60,setsar=1,format=yuv420p[bg]"
    ]

    last_v = "bg"
    if hook_idx is not None:
        fade_out_st = max(0.4, hook_duration - 0.35)
        v_filters.append(
            f"[{hook_idx}:v]format=rgba,"
            f"fade=t=in:st=0:d=0.20:alpha=1,"
            f"fade=t=out:st={fade_out_st:.2f}:d=0.35:alpha=1[hook]"
        )
        v_filters.append(
            f"[{last_v}][hook]overlay=(W-w)/2:270:eof_action=pass:"
            f"enable='between(t,0,{hook_duration:.2f})'[vhook]"
        )
        last_v = "vhook"

    v_filters.append(
        f"[{last_v}]subtitles=filename={ass_escaped}:fontsdir={fonts_escaped},format=yuv420p[vout]"
    )

    # Build audio filtergraph
    a_filters: list[str] = [
        "[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,apad=pad_dur=0.45[vpad]"
    ]
    if music_idx is not None:
        vol = max(0.0, min(1.0, music_volume))
        a_filters.extend(
            [
                "[vpad]asplit=2[vmain][vsc]",
                f"[{music_idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol:.3f}[mus]",
                "[mus][vsc]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=350:makeup=1[ducked]",
                "[vmain][ducked]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]",
            ]
        )
    else:
        a_filters.append("[vpad]acopy[aout]")

    filter_complex = ";".join(v_filters + a_filters)

    cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])

    if encoder == "h264_nvenc":
        cmd.extend(
            [
                "-c:v",
                "h264_nvenc",
                "-preset",
                "p4",
                "-rc",
                "vbr",
                "-cq",
                "21",
                "-b:v",
                "8M",
                "-maxrate",
                "12M",
                "-bufsize",
                "16M",
            ]
        )
    else:
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "21",
            ]
        )

    cmd.extend(
        [
            "-pix_fmt",
            "yuv420p",
            "-r",
            "60",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            "-t",
            f"{target_duration:.3f}",
            str(output_mp4.resolve()),
        ]
    )

    logger.info("Rendering final video (%s) -> %s", encoder, output_mp4.name)
    proc = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"FFmpeg render failed (encoder={encoder}, rc={proc.returncode}): {proc.stderr[-1500:]}"
        )

    final_dur = probe_audio_duration(output_mp4)
    size_bytes = output_mp4.stat().st_size
    return RenderResult(
        output_mp4=output_mp4,
        duration_sec=final_dur,
        file_size_bytes=size_bytes,
        encoder_used=encoder,
        music_used=music_path.name if music_path else None,
    )
