from __future__ import annotations

from app.services.adapter_status_service import AdapterStatusService

from app.core.db import Base, make_engine, make_session_factory
from app.models.adapter_status import AdapterStatusRow


def _session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


async def test_handle_adapter_heartbeat_inserts_a_new_row():
    session_factory = _session_factory()
    service = AdapterStatusService(session_factory)

    await service.handle_adapter_heartbeat(
        {"adapter_name": "nfc", "status": "online", "detail": None}
    )

    with session_factory() as session:
        row = session.get(AdapterStatusRow, "nfc")
        assert row.status.value == "online"


async def test_handle_adapter_heartbeat_updates_an_existing_row():
    session_factory = _session_factory()
    service = AdapterStatusService(session_factory)
    await service.handle_adapter_heartbeat(
        {"adapter_name": "led", "status": "online", "detail": None}
    )

    await service.handle_adapter_heartbeat(
        {"adapter_name": "led", "status": "error", "detail": "timeout"}
    )

    with session_factory() as session:
        rows = session.query(AdapterStatusRow).filter_by(adapter_name="led").all()
        assert len(rows) == 1
        assert rows[0].status.value == "error"
        assert rows[0].detail == "timeout"
