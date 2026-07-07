"""CardService 单元测试。"""

from __future__ import annotations

import asyncio

import pytest

from app.adapters.nfc.mock import MockNFCAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models import Visit
from app.models.nfc_write_log import NFCWriteLog
from app.models.visit import EntrySource, IdentityType, VisitStatus, WelcomeSource
from app.services.card_service import CardService


def _seeded_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as s:
        v = Visit(
            visit_date=__import__("datetime").date(2026, 7, 7),
            session_time=__import__("datetime").datetime(2026, 7, 7, 9, 0),
            name="张三",
            identity_type=IdentityType.ENTERPRISE_LEADER,
            welcome_text="张三先生/女士，欢迎您",
            welcome_source=WelcomeSource.AI,
            entry_source=EntrySource.MANUAL,
            import_batch_id="t",
            status=VisitStatus.WELCOME_READY,
        )
        s.add(v)
        s.commit()
        s.refresh(v)
        vid = v.id
    return SessionLocal, vid


async def test_write_card_for_visit_writes_card_and_updates_status():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    completed_queue = event_bus.subscribe("card.write.completed")
    work_log_queue = event_bus.subscribe("work_log.append")
    nfc_adapter = MockNFCAdapter()
    service = CardService(session_factory, event_bus, nfc_adapter)

    await service.write_card_for_visit({"visit_id": visit_id})

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


async def test_write_card_for_visit_records_failure_when_nfc_write_fails():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    completed_queue = event_bus.subscribe("card.write.completed")
    work_log_queue = event_bus.subscribe("work_log.append")
    nfc_adapter = MockNFCAdapter(fail=True)
    service = CardService(session_factory, event_bus, nfc_adapter)

    await service.write_card_for_visit({"visit_id": visit_id})

    with session_factory() as session:
        visit = session.get(Visit, visit_id)
        assert visit.status == VisitStatus.WELCOME_READY  # unchanged, not CARD_WRITTEN
        write_log = session.query(NFCWriteLog).filter_by(visit_id=visit_id).one()
        assert write_log.write_status.value == "failed"
