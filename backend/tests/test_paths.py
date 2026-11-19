from __future__ import annotations

import asyncio
from pathlib import Path, PureWindowsPath

import pytest

from backend.core import database, hardware, paths


def test_escape_ffmpeg_filter_path_windows_and_special_chars() -> None:
    win_path = PureWindowsPath(r"C:\Projects\shorts-factory\temp\subtitles [ru].ass")
    escaped = paths.escape_ffmpeg_filter_path(win_path)
    assert "\\" in escaped
    assert "C\\:" in escaped
    assert "\\[" in escaped
    assert "\\]" in escaped
    assert "\\ " in escaped
    # Raw Windows backslashes must be converted to forward slashes before escaping
    assert "C\\:/Projects/shorts-factory/temp/subtitles\\ \\[ru\\].ass" == escaped


def test_escape_ffmpeg_filter_path_relative_to_cwd(tmp_path: Path) -> None:
    sub = tmp_path / "temp" / "job1" / "captions.ass"
    sub.parent.mkdir(parents=True, exist_ok=True)
    sub.write_text("", encoding="utf-8")

    escaped = paths.escape_ffmpeg_filter_path(sub, cwd=tmp_path)
    assert escaped == "temp/job1/captions.ass"
    assert ":" not in escaped


def test_safe_asset_path_blocks_traversal(tmp_path: Path) -> None:
    allowed = paths.safe_asset_path(tmp_path, "parkour.mp4")
    assert allowed == (tmp_path / "parkour.mp4").resolve()

    with pytest.raises(ValueError):
        paths.safe_asset_path(tmp_path, "../secret.txt")
    with pytest.raises(ValueError):
        paths.safe_asset_path(tmp_path, "sub/file.mp4")
    with pytest.raises(ValueError):
        paths.safe_asset_path(tmp_path, r"sub\file.mp4")


def test_next_daily_output_paths(tmp_path: Path) -> None:
    mp4_1, txt_1 = paths.next_daily_output_paths(tmp_path, date_str="2026-11-19")
    assert mp4_1.name == "video_01.mp4"
    assert txt_1.name == "video_01.txt"
    mp4_1.write_bytes(b"0")
    txt_1.write_text("meta", encoding="utf-8")

    mp4_2, txt_2 = paths.next_daily_output_paths(tmp_path, date_str="2026-11-19")
    assert mp4_2.name == "video_02.mp4"
    assert txt_2.name == "video_02.txt"


def test_hardware_detection_and_db_init(tmp_path: Path) -> None:
    hardware.detect_hardware.cache_clear()
    info = hardware.detect_hardware()
    assert info.video_encoder in {"h264_nvenc", "libx264"}
    assert info.whisper_device in {"cuda", "cpu"}
    assert info.whisper_compute_type in {"float16", "int8"}

    db_file = tmp_path / "test.db"

    async def _run() -> None:
        await database.init_db(db_file)
        settings = await database.get_all_settings(db_file)
        assert "llm_base_url" in settings
        assert settings["subtitle_highlight_color"] == "#FFE600"
        batch, jobs = await database.create_batch(
            niche="reddit",
            language="ru",
            voice="ru-RU-DmitryNeural",
            tts_engine="edge",
            tts_rate="+15%",
            visual_mode="gameplay",
            subtitle_color="#FFE600",
            custom_topic="",
            total_count=2,
            db_path=db_file,
        )
        assert batch["total_count"] == 2
        assert len(jobs) == 2

    asyncio.run(_run())
