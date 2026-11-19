from __future__ import annotations

import json
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.script_gen import NICHE_INFO, generate_script
from backend.services.visuals import generate_ai_slideshow
from backend.tests.test_stage3_render import ffprobe_inspect


@pytest.mark.asyncio
async def test_offline_script_bank_all_niches_and_languages() -> None:
    for niche in NICHE_INFO:
        for lang in ("ru", "en"):
            seen_titles: list[str] = []
            for _ in range(3):
                script = await generate_script(
                    niche=niche,
                    language=lang,
                    previous_titles=seen_titles,
                )
                assert script.source == "offline"
                assert script.title not in seen_titles
                seen_titles.append(script.title)
                assert len(script.full_narration.split()) >= 75
                assert len(script.tags) >= 6
                assert len(script.image_prompts) == 5
                assert script.description


@pytest.mark.asyncio
async def test_llm_script_parser_with_mocked_client() -> None:
    fake_payload = {
        "subreddit_or_tag": "r/AskReddit",
        "author": "u/mock_user",
        "title": "Тестовый заголовок для шортса",
        "hook": "Никогда не открывай старый подвал в одиночку.",
        "body": "Я спустился туда с фонариком и увидел запертый металлический ящик на столе.",
        "cta_ending": "А вы бы открыли этот ящик? Напишите в комментариях.",
        "description": "Короткое описание для проверки парсера.",
        "tags": ["reddit", "#shorts", "история", "тест", "мистика", "триллер"],
        "image_prompts": [
            "dark wooden basement stairs with flashlight beam, vertical",
            "old rusted metal box on dusty table, moody lighting",
        ],
    }

    fake_message = MagicMock()
    fake_message.content = f"```json\n{json.dumps(fake_payload, ensure_ascii=False)}\n```"
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_resp = MagicMock()
    fake_resp.choices = [fake_choice]

    fake_client = MagicMock()
    fake_client.chat = MagicMock()
    fake_client.chat.completions = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_resp)

    with patch("openai.AsyncOpenAI", return_value=fake_client):
        script = await generate_script(
            niche="reddit",
            language="ru",
            api_key="sk-test-123",
            base_url="https://openrouter.ai/api/v1",
            model="deepseek/deepseek-chat",
        )
        assert script.source == "llm"
        assert script.title == "Тестовый заголовок для шортса"
        assert "shorts" in script.tags
        assert len(script.image_prompts) == 5


def test_ai_slideshow_ken_burns_fallback(tmp_path: Path) -> None:
    prompts = [
        "dark hotel hallway at night",
        "vintage brass key on oak counter",
        "rainy city window reflections",
        "glowing phone screen in dark room",
        "empty elevator corridor",
    ]
    work_dir = tmp_path / "slides"
    out_mp4 = tmp_path / "slideshow.mp4"
    video_path, mode = generate_ai_slideshow(
        image_prompts=prompts,
        duration=8.0,
        output_video=out_mp4,
        work_dir=work_dir,
        niche="scary",
    )
    assert video_path.is_file()
    assert mode == "procedural_art_cpu"

    info = ffprobe_inspect(video_path)
    vs = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    assert vs["width"] == 1080
    assert vs["height"] == 1920
    assert vs["r_frame_rate"] == "60/1"
    dur = float(info["format"]["duration"])
    assert 7.5 <= dur <= 8.5
