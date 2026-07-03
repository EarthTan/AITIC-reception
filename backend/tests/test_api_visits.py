# backend/tests/test_api_visits.py
from __future__ import annotations

from datetime import date, datetime

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus


def _client_with_visit(tmp_path) -> tuple[TestClient, int]:
    """Build a fresh app, seed one visit, and return a started TestClient + the visit id."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    app = build_app(settings)
    with TestClient(app) as client:
        session_factory = app.state.session_factory
        with session_factory() as session:
            visit = Visit(
                visit_date=date(2026, 7, 6),
                session_time=datetime(2026, 7, 6, 10, 0),
                name="张三",
                id_number="11010119900101",  # 14 chars, exercises the 3+7+4 mask
                identity_type=IdentityType.ENTERPRISE_LEADER,
                entry_source=EntrySource.MANUAL,
                import_batch_id="batch-1",
                status=VisitStatus.PENDING,
            )
            session.add(visit)
            session.commit()
            visit_id = visit.id
    return client, visit_id


def test_list_visits_returns_masked_id_number(tmp_path):
    client, _ = _client_with_visit(tmp_path)
    response = client.get("/api/visits")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id_number"] == "110*******0101"


def test_get_visit_by_id_returns_404_when_missing(tmp_path):
    client, _ = _client_with_visit(tmp_path)
    response = client.get("/api/visits/999999")
    assert response.status_code == 404


def test_patch_visit_updates_editable_fields(tmp_path):
    client, visit_id = _client_with_visit(tmp_path)
    response = client.patch(f"/api/visits/{visit_id}", json={"organization": "新单位"})
    assert response.status_code == 200
    assert response.json()["organization"] == "新单位"


def test_today_visits_filters_by_current_date(tmp_path):
    client, _ = _client_with_visit(tmp_path)
    response = client.get("/api/visits/today")
    assert response.status_code == 200
    # fixture visit is dated 2026-07-06, not "today" relative to the test run,
    # so it should NOT appear
    assert response.json() == []
