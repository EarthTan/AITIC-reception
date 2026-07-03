# backend/app/core/config.py
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite:///./data/app.db"
    excel_watch_dir: str = "./data/incoming"
    ai_api_key: str = ""
    ai_provider: str = "qwen"
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
