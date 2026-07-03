from __future__ import annotations

from datetime import date, datetime

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus


def _client_with_ready_visit(tmp_path) -> tuple[TestClient, int]:
    """Build a fresh app, seed one welcome-ready visit, return a started TestClient + id."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    app = build_app(settings)
    client = TestClient(app)
    session_factory = app.state.session_factory
    with session_factory() as session:
        visit = Visit(
            visit_date=date(2026, 7, 6),
            session_time=datetime(2026, 7, 6, 10, 0),
            name="张三",
            identity_type=IdentityType.ENTERPRISE_LEADER,
            entry_source=EntrySource.MANUAL,
            import_batch_id="batch-1",
            status=VisitStatus.WELCOME_READY,
            welcome_text="张三先生/女士，欢迎您",
        )
        session.add(visit)
        session.commit()
        visit_id = visit.id
    return client, visit_id


def test_post_cards_write_triggers_write_and_returns_success(tmp_path):
    client, visit_id = _client_with_ready_visit(tmp_path)
    with client:
        response = client.post("/api/cards/write", json={"visit_ids": [visit_id]})

        assert response.status_code == 200
        body = response.json()
        assert body[0]["visit_id"] == visit_id
        assert body[0]["status"] == "success"

        log_response = client.get("/api/cards/write-log", params={"visit_id": visit_id})
        assert log_response.status_code == 200
        assert len(log_response.json()) == 1
