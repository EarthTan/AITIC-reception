# backend/tests/test_api_templates.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app


def _client(tmp_path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    return TestClient(build_app(settings))


def test_list_templates_returns_seven_seeded_rows(tmp_path):
    with _client(tmp_path) as client:
        response = client.get("/api/templates")
        assert response.status_code == 200
        assert len(response.json()) == 7


def test_put_template_updates_text(tmp_path):
    with _client(tmp_path) as client:
        response = client.put(
            "/api/templates/政府官员",
            json={"template_text": "热烈欢迎{姓名}领导莅临指导"},
        )
        assert response.status_code == 200
        assert response.json()["template_text"] == "热烈欢迎{姓名}领导莅临指导"


def test_put_template_with_unknown_identity_returns_404(tmp_path):
    with _client(tmp_path) as client:
        response = client.put("/api/templates/外星人", json={"template_text": "x"})
        assert response.status_code == 404
