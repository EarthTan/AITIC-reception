# backend/tests/test_main.py
from app.core.config import Settings
from app.main import build_app
from fastapi.testclient import TestClient


def test_health_endpoint_and_state_are_wired(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    app = build_app(settings)

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        assert set(app.state.adapters) == {"nfc", "led", "tts", "ai"}
        assert set(app.state.services) == {
            "registration",
            "ai_writeup",
            "card",
            "verify",
            "log",
        }
