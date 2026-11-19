from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.paths import BASE_DIR


class AppSettings(BaseSettings):
    """Application settings loaded from environment / .env with UTF-8 encoding."""

    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "deepseek/deepseek-chat"

    whisper_model: str = "auto"
    tts_default_rate: str = "+15%"
    music_volume: float = 0.20
    subtitle_highlight_color: str = "#FFE600"
    sdxl_model: str = "stabilityai/sdxl-turbo"

    app_host: str = "127.0.0.1"
    app_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_env_settings() -> AppSettings:
    """Load cached initial settings from .env / environment."""
    return AppSettings()


DEFAULT_DB_SETTINGS: dict[str, str] = {
    "llm_api_key": "",
    "llm_base_url": "https://openrouter.ai/api/v1",
    "llm_model": "deepseek/deepseek-chat",
    "whisper_model": "auto",
    "tts_default_rate": "+15%",
    "music_volume": "0.20",
    "subtitle_highlight_color": "#FFE600",
    "sdxl_model": "stabilityai/sdxl-turbo",
}


def get_initial_db_settings() -> dict[str, str]:
    """Merge default settings with .env values for initial DB seeding."""
    env = get_env_settings()
    return {
        "llm_api_key": env.llm_api_key,
        "llm_base_url": env.llm_base_url,
        "llm_model": env.llm_model,
        "whisper_model": env.whisper_model,
        "tts_default_rate": env.tts_default_rate,
        "music_volume": f"{env.music_volume:.2f}",
        "subtitle_highlight_color": env.subtitle_highlight_color,
        "sdxl_model": env.sdxl_model,
    }


def read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
