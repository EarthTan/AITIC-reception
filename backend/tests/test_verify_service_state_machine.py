# backend/tests/test_verify_service_state_machine.py
import asyncio
from datetime import date, datetime

from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.visit import (
    EntrySource,
    IdentityType,
    Visit,
    VisitStatus,
    WelcomeSource,
)
from app.services.verify_service import VerifyService


def _seeded_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        visit = Visit(
            visit_date=date(2026, 7, 7),
            session_time=datetime(2026, 7, 7, 9, 0),
            name="测试人",
            identity_type=IdentityType.ENTERPRISE_STAFF,
            welcome_text="测试",
            welcome_source=WelcomeSource.AI,
            entry_source=EntrySource.MANUAL,
            import_batch_id="t",
            status=VisitStatus.CARD_WRITTEN,
        )
        session.add(visit)
        session.commit()
        visit_id = visit.id
    return session_factory, visit_id


async def test_failed_verify_sets_rejected_status():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    failed_queue = event_bus.subscribe("card.verify.failed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {
            "card_uid": "BAD",
            "raw_payload": {
                "visit_id": visit_id,
                "name": "错误名",
                "visit_date": "2026-07-07",
            },
        }
    )

    payload = await asyncio.wait_for(failed_queue.get(), timeout=1)
    assert payload["fail_reason"] == "name_mismatch"

    with session_factory() as session:
        assert session.get(Visit, visit_id).status == VisitStatus.REJECTED
