# backend/tests/test_api_logs_export.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app


def test_export_endpoint_exists_and_returns_xlsx():
    app = build_app(Settings())
    with TestClient(app) as client:
        resp = client.get("/api/work-logs/export")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
