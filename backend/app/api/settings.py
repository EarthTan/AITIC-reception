# backend/app/api/settings.py
from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.settings_store import load_overrides, save_overrides
from app.schemas.settings import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings_endpoint(request: Request) -> SettingsOut:
    settings = request.app.state.settings
    return SettingsOut(
        excel_watch_dir=settings.excel_watch_dir,
        ai_provider=settings.ai_provider,
        has_ai_api_key=bool(settings.ai_api_key),
        cors_origins=settings.cors_origins,
    )


@router.put("", response_model=SettingsOut)
def update_settings_endpoint(body: SettingsUpdate, request: Request) -> SettingsOut:
    override_path = request.app.state.settings_override_path
    overrides = load_overrides(override_path)
    overrides.update(body.model_dump(exclude_unset=True))
    save_overrides(override_path, overrides)

    settings = request.app.state.settings.model_copy(update=overrides)
    request.app.state.settings = settings

    return SettingsOut(
        excel_watch_dir=settings.excel_watch_dir,
        ai_provider=settings.ai_provider,
        has_ai_api_key=bool(settings.ai_api_key),
        cors_origins=settings.cors_origins,
        message="部分设置（监听目录）需要重启后端服务后才会生效",
    )
