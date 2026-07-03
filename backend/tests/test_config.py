# backend/tests/test_config.py
import logging

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


def test_settings_defaults():
    settings = Settings()
    assert settings.database_url == "sqlite:///./data/app.db"
    assert settings.excel_watch_dir == "./data/incoming"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_env_var_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./custom.db")
    settings = Settings()
    assert settings.database_url == "sqlite:///./custom.db"


def test_get_settings_returns_cached_instance():
    get_settings.cache_clear()
    assert get_settings() is get_settings()


def test_configure_logging_sets_root_level():
    configure_logging(level=logging.DEBUG)
    assert logging.getLogger().level == logging.DEBUG
