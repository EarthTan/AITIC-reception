# backend/tests/test_verify_service.py
import asyncio
from datetime import date, datetime

from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.verify_log import VerifyLog
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus
from app.services.verify_service import VerifyService


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
            status=VisitStatus.CARD_WRITTEN,
        )
        session.add(visit)
        session.commit()
        visit_id = visit.id
    return session_factory, visit_id


async def test_verify_passes_when_name_and_date_match():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    passed_queue = event_bus.subscribe("card.verify.passed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {
            "card_uid": "UID-1",
            "raw_payload": {
                "visit_id": visit_id,
                "name": "张三",
                "visit_date": "2026-07-06",
            },
        }
    )

    payload = await asyncio.wait_for(passed_queue.get(), timeout=1)
    assert payload == {"visit_id": visit_id, "card_uid": "UID-1"}
    with session_factory() as session:
        assert session.get(Visit, visit_id).status == VisitStatus.VERIFIED
        assert (
            session.query(VerifyLog)
            .filter_by(visit_id=visit_id)
            .one()
            .verify_result.value
            == "pass"
        )


async def test_verify_fails_on_name_mismatch():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    failed_queue = event_bus.subscribe("card.verify.failed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {
            "card_uid": "UID-1",
            "raw_payload": {
                "visit_id": visit_id,
                "name": "李四",
                "visit_date": "2026-07-06",
            },
        }
    )

    payload = await asyncio.wait_for(failed_queue.get(), timeout=1)
    assert payload["fail_reason"] == "name_mismatch"


async def test_verify_fails_on_date_mismatch():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    failed_queue = event_bus.subscribe("card.verify.failed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {
            "card_uid": "UID-1",
            "raw_payload": {
                "visit_id": visit_id,
                "name": "张三",
                "visit_date": "2026-07-07",
            },
        }
    )

    payload = await asyncio.wait_for(failed_queue.get(), timeout=1)
    assert payload["fail_reason"] == "date_mismatch"


async def test_verify_fails_when_visit_not_found():
    session_factory, _ = _seeded_session_factory()
    event_bus = EventBus()
    failed_queue = event_bus.subscribe("card.verify.failed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {
            "card_uid": "UID-1",
            "raw_payload": {
                "visit_id": 999999,
                "name": "张三",
                "visit_date": "2026-07-06",
            },
        }
    )

    payload = await asyncio.wait_for(failed_queue.get(), timeout=1)
    assert payload["fail_reason"] == "card_not_found"
