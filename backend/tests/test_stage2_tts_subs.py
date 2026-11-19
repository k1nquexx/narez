from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.services.subtitles import (
    generate_ass_subtitles,
    hex_rgb_to_ass_bgr,
    transcribe_words,
    unload_whisper_model,
)
from backend.services.tts_engine import probe_audio_duration, synthesize_speech


def test_hex_rgb_to_ass_bgr() -> None:
    assert hex_rgb_to_ass_bgr("#FFE600") == "&H0000E6FF&"
    assert hex_rgb_to_ass_bgr("#39FF50") == "&H0050FF39&"
    assert hex_rgb_to_ass_bgr("invalid") == "&H0000E6FF&"


@pytest.mark.asyncio
async def test_tts_and_subtitles_ru_and_en(tmp_path: Path) -> None:
    try:
        # 1. Russian TTS + silence removal + Whisper word timestamps + ASS
        ru_text = (
            "В нашем отеле строго запрещено открывать дверь номера четыреста четыре после двух часов ночи. "
            "Я поднялся на четвертый этаж с ключом и услышал за дверью собственный голос."
        )
        ru_mp3 = tmp_path / "voice_ru.mp3"
        ru_tts = await synthesize_speech(
            text=ru_text,
            output_mp3=ru_mp3,
            language="ru",
            voice="ru-RU-DmitryNeural",
            rate="+15%",
            engine="edge",
            trim_silence=True,
        )
        assert ru_tts.audio_path.is_file()
        assert ru_tts.final_duration > 3.0
        assert abs(probe_audio_duration(ru_mp3) - ru_tts.final_duration) < 0.2

        ru_words = transcribe_words(
            ru_mp3,
            language="ru",
            initial_prompt=ru_text,
            model_size="base",
        )
        assert len(ru_words) >= 8
        for idx in range(len(ru_words) - 1):
            assert ru_words[idx].start <= ru_words[idx + 1].start

        ru_ass = tmp_path / "subs_ru.ass"
        generate_ass_subtitles(ru_words, ru_ass, highlight_hex="#FFE600")
        ass_text = ru_ass.read_text(encoding="utf-8")
        assert "PlayResX: 1080" in ass_text
        assert "PlayResY: 1920" in ass_text
        assert "Montserrat" in ass_text
        assert "&H0000E6FF&" in ass_text
        assert re.search(r"[А-Яа-яЁё]", ass_text), "Expected Cyrillic subtitle text"
        dialogue_lines = [ln for ln in ass_text.splitlines() if ln.startswith("Dialogue:")]
        assert len(dialogue_lines) == len(ru_words)

        # 2. English TTS + Whisper + ASS
        en_text = "Never answer voices calling your name in thick forest fog after dusk."
        en_mp3 = tmp_path / "voice_en.mp3"
        en_tts = await synthesize_speech(
            text=en_text,
            output_mp3=en_mp3,
            language="en",
            voice="en-US-ChristopherNeural",
            rate="+15%",
            engine="edge",
            trim_silence=True,
        )
        assert en_tts.audio_path.is_file()
        assert en_tts.final_duration > 2.0

        en_words = transcribe_words(
            en_mp3,
            language="en",
            initial_prompt=en_text,
            model_size="base",
        )
        assert len(en_words) >= 6
        en_ass = tmp_path / "subs_en.ass"
        generate_ass_subtitles(en_words, en_ass, highlight_hex="#39FF50")
        en_ass_text = en_ass.read_text(encoding="utf-8")
        assert "&H0050FF39&" in en_ass_text
    finally:
        unload_whisper_model()
