# backend/tests/test_api_settings.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app


def _client(tmp_path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
        ai_api_key="",
    )
    return TestClient(build_app(settings))


def test_get_settings_does_not_leak_the_raw_api_key(tmp_path):
    with _client(tmp_path) as client:
        response = client.get("/api/settings")
        assert response.status_code == 200
        body = response.json()
        assert "ai_api_key" not in body
        assert body["has_ai_api_key"] is False


def test_put_settings_persists_and_is_reflected_on_next_get(tmp_path):
    with _client(tmp_path) as client:
        put_response = client.put("/api/settings", json={"ai_api_key": "sk-test"})
        assert put_response.status_code == 200
        assert put_response.json()["has_ai_api_key"] is True

        get_response = client.get("/api/settings")
        assert get_response.json()["has_ai_api_key"] is True
