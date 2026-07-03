# backend/app/core/settings_store.py
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings


def load_overrides(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_overrides(path: Path, overrides: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def apply_overrides(settings: Settings, overrides: dict) -> Settings:
    return settings.model_copy(update=overrides)
