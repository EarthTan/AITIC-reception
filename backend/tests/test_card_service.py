# backend/tests/test_card_service.py
import asyncio
from datetime import date, datetime

from app.adapters.nfc.mock import MockNFCAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.nfc_write_log import NFCWriteLog
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus
from app.services.card_service import CardService


def _seeded_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
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
    return session_factory, visit_id


async def test_handle_welcome_generated_writes_card_and_updates_status():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    completed_queue = event_bus.subscribe("card.write.completed")
    work_log_queue = event_bus.subscribe("work_log.append")
    nfc_adapter = MockNFCAdapter()
    service = CardService(session_factory, event_bus, nfc_adapter)

    await service.handle_welcome_generated({"visit_id": visit_id})

    with session_factory() as session:
        visit = session.get(Visit, visit_id)
        assert visit.status == VisitStatus.CARD_WRITTEN
        write_log = session.query(NFCWriteLog).filter_by(visit_id=visit_id).one()
        assert write_log.write_status.value == "success"

    completed_payload = await asyncio.wait_for(completed_queue.get(), timeout=1)
    assert completed_payload["visit_id"] == visit_id
    assert completed_payload["status"] == "success"

    written = nfc_adapter.get_written_payload(completed_payload["card_uid"])
    assert written["name"] == "张三"
    assert written["welcome_text"] == "张三先生/女士，欢迎您"

    log_payload = await asyncio.wait_for(work_log_queue.get(), timeout=1)
    assert log_payload["module"] == "card_write"
