from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from backend.core.hardware import find_binary
from backend.core.paths import BASE_DIR, FONTS_DIR, escape_ffmpeg_filter_path
from backend.services.renderer import pick_random_music, render_final_video
from backend.services.subtitles import generate_ass_subtitles, transcribe_words, unload_whisper_model
from backend.services.tts_engine import synthesize_speech
from backend.services.visuals import generate_hook_card, prepare_gameplay_background


def ffprobe_inspect(media_path: Path) -> dict:
    ffprobe_path = find_binary("ffprobe")
    assert ffprobe_path, "ffprobe must be installed"
    proc = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0, f"ffprobe failed: {proc.stderr}"
    return json.loads(proc.stdout)


@pytest.mark.asyncio
async def test_hook_card_and_ffmpeg_render(tmp_path: Path) -> None:
    try:
        # 1. Hook card
        hook_png = tmp_path / "hook_card.png"
        generate_hook_card(
            title="Какое правило появилось после одного жуткого случая в отеле?",
            subreddit_or_tag="r/AskReddit",
            author="u/night_auditor_99",
            niche="reddit",
            output_png=hook_png,
        )
        assert hook_png.is_file()
        with Image.open(hook_png) as img:
            assert img.mode == "RGBA"
            assert img.width > 900
            assert img.height > 200

        # 2. Voice + Subtitles (inside BASE_DIR/temp so relative path test works identically to prod)
        work_dir = BASE_DIR / "temp" / f"test_stage3_{tmp_path.name}"
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            text = (
                "В нашем отеле строго запрещено открывать дверь номера четыреста четыре после двух ночи. "
                "В прошлый вторник телефон зазвонил сам по себе."
            )
            voice_mp3 = work_dir / "voice.mp3"
            tts_res = await synthesize_speech(
                text=text,
                output_mp3=voice_mp3,
                language="ru",
                voice="ru-RU-DmitryNeural",
                rate="+15%",
            )
            words = transcribe_words(voice_mp3, language="ru", initial_prompt=text, model_size="base")
            ass_path = work_dir / "captions.ass"
            generate_ass_subtitles(words, ass_path, highlight_hex="#FFE600")

            # Verify libass actually picks bundled Montserrat from assets/fonts
            ffmpeg_path = find_binary("ffmpeg")
            assert ffmpeg_path
            ass_rel = escape_ffmpeg_filter_path(ass_path, cwd=BASE_DIR)
            fonts_rel = escape_ffmpeg_filter_path(FONTS_DIR, cwd=BASE_DIR)
            font_probe = subprocess.run(
                [
                    ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "verbose",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=1080x1920:d=0.5",
                    "-vf",
                    f"subtitles=filename={ass_rel}:fontsdir={fonts_rel}",
                    "-f",
                    "null",
                    "-",
                ],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            assert font_probe.returncode == 0, font_probe.stderr
            assert "Montserrat" in font_probe.stderr, f"Expected Montserrat font in libass log: {font_probe.stderr}"

            # 3. Procedural gradient background + final render with music auto-ducking
            bg_mp4 = work_dir / "bg.mp4"
            prepare_gameplay_background(
                duration=tts_res.final_duration + 0.8,
                output_video=bg_mp4,
                niche="reddit",
                seed=42,
            )

            out_mp4 = work_dir / "final_test.mp4"
            music = pick_random_music(seed=1)
            res = render_final_video(
                bg_video=bg_mp4,
                voice_audio=voice_mp3,
                ass_subtitles=ass_path,
                hook_card_png=hook_png,
                output_mp4=out_mp4,
                music_path=music,
                music_volume=0.20,
            )
            assert res.output_mp4.is_file()
            assert res.file_size_bytes > 100_000

            info = ffprobe_inspect(out_mp4)
            streams = info["streams"]
            v_streams = [s for s in streams if s["codec_type"] == "video"]
            a_streams = [s for s in streams if s["codec_type"] == "audio"]
            assert len(v_streams) == 1
            assert len(a_streams) == 1

            vs = v_streams[0]
            assert vs["width"] == 1080
            assert vs["height"] == 1920
            assert vs["codec_name"] == "h264"
            assert vs["pix_fmt"] == "yuv420p"
            assert vs["r_frame_rate"] == "60/1"

            aus = a_streams[0]
            assert aus["codec_name"] == "aac"
            assert str(aus["sample_rate"]) == "48000"

            dur = float(info["format"]["duration"])
            assert dur >= 4.0
        finally:
            import shutil

            shutil.rmtree(work_dir, ignore_errors=True)
    finally:
        unload_whisper_model()
