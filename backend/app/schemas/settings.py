from __future__ import annotations

from pydantic import BaseModel


class SettingsOut(BaseModel):
    excel_watch_dir: str
    ai_provider: str
    has_ai_api_key: bool
    cors_origins: list[str]
    message: str | None = None


class SettingsUpdate(BaseModel):
    excel_watch_dir: str | None = None
    ai_provider: str | None = None
    ai_api_key: str | None = None
