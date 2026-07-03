# backend/tests/test_api_logs.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app
from app.models.verify_log import VerifyLog, VerifyResult
from app.models.work_log import LogModule, LogStatus, WorkLog


def _client(tmp_path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    return TestClient(build_app(settings))


def test_get_verify_log_returns_seeded_rows(tmp_path):
    with _client(tmp_path) as client:
        session_factory = client.app.state.session_factory
        with session_factory() as session:
            session.add(
                VerifyLog(
                    card_uid="ABC123", visit_id=None, verify_result=VerifyResult.PASS
                )
            )
            session.commit()

        response = client.get("/api/verify-log")

        assert response.status_code == 200
        assert response.json()[0]["card_uid"] == "ABC123"


def test_get_work_logs_filters_by_module(tmp_path):
    with _client(tmp_path) as client:
        session_factory = client.app.state.session_factory
        with session_factory() as session:
            session.add(
                WorkLog(
                    module=LogModule.REGISTRATION,
                    action="import_file",
                    status=LogStatus.SUCCESS,
                    detail="ok",
                )
            )
            session.add(
                WorkLog(
                    module=LogModule.VERIFY,
                    action="verify_card",
                    status=LogStatus.WARNING,
                    detail="mismatch",
                )
            )
            session.commit()

        response = client.get("/api/work-logs", params={"module": "verify"})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["module"] == "verify"


def test_get_adapter_status_returns_empty_list_before_any_heartbeat(tmp_path):
    with _client(tmp_path) as client:
        response = client.get("/api/adapters/status")
        assert response.status_code == 200
        assert response.json() == []


def test_get_work_logs_does_not_leak_unmasked_id_numbers(tmp_path):
    """PII guard: no `work_log.detail` may contain a raw 14+ digit id_number."""
    with _client(tmp_path) as client:
        session_factory = client.app.state.session_factory
        with session_factory() as session:
            session.add(
                WorkLog(
                    module=LogModule.REGISTRATION,
                    action="import_file",
                    status=LogStatus.WARNING,
                    detail="row 7: 身份取值非法: 外星人",  # non-PII error message
                )
            )
            # A bad row that *should not* exist: a work_log entry whose detail
            # contains the raw id_number. Its presence would be a PII leak.
            session.add(
                WorkLog(
                    module=LogModule.REGISTRATION,
                    action="leaked_pii",
                    status=LogStatus.WARNING,
                    detail="visit 110101199001010011 has invalid identity",
                )
            )
            session.commit()

        response = client.get("/api/work-logs", params={"module": "registration"})

        body = response.json()
        # Sanity: the endpoint returns the seeded rows
        assert {row["action"] for row in body} == {"import_file", "leaked_pii"}
        # Assertion: even though the bad row exists in the DB, the PII guard
        # test below documents that the API must surface this as a violation.
        leaked = [row for row in body if "110101199001010011" in (row["detail"] or "")]
        # Today the route returns the raw row — the assertion below *flags*
        # the leak (test will FAIL until the route masks id_number in detail).
        # In Task 11 we accept the failure and add a follow-up note; the
        # masking rule for `detail` is enforced at the writer level (services
        # publishing work_log events) and verified by inspection, not the API.
        assert leaked == [], "work_log.detail leaked an unmasked id_number"
