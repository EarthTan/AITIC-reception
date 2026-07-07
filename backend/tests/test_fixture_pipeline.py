# backend/tests/test_fixture_pipeline.py
from __future__ import annotations

import asyncio
from pathlib import Path

from app.adapters.ai.mock import MockAIAdapter
from app.adapters.nfc.mock import MockNFCAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.core.seed import seed_default_templates
from app.models.visit import EntrySource, Visit, VisitStatus
from app.services.ai_writeup_service import AIWriteupWorker
from app.services.card_service import CardService
from app.services.registration_service import RegistrationService
from app.services.verify_service import VerifyService

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_visitors.xlsx"


async def test_fixture_covers_all_identity_types_and_rejects_bad_row():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        seed_default_templates(session)

    event_bus = EventBus()
    nfc_adapter = MockNFCAdapter()
    ai_adapter = MockAIAdapter()
    registration_service = RegistrationService(session_factory, event_bus)
    ai_writeup_worker = AIWriteupWorker(session_factory, event_bus, ai_adapter)
    card_service = CardService(session_factory, event_bus, nfc_adapter)
    verify_service = VerifyService(session_factory, event_bus)

    welcome_requested_queue = event_bus.subscribe("welcome.requested")
    welcome_generated_queue = event_bus.subscribe("welcome.generated")
    card_write_queue = event_bus.subscribe("card.write.completed")
    verify_passed_queue = event_bus.subscribe("card.verify.passed")
    verify_failed_queue = event_bus.subscribe("card.verify.failed")

    _, visit_ids = await registration_service.import_file(
        str(FIXTURE_PATH), EntrySource.MANUAL
    )

    # 7 rows in the fixture, 1 has an invalid identity -> only 6 committed
    assert len(visit_ids) == 6

    with session_factory() as session:
        identity_types = {
            session.get(Visit, vid).identity_type.value for vid in visit_ids
        }
        assert identity_types == {
            "企业领导",
            "企业员工",
            "学校老师",
            "大学生",
            "中小学生",
            "政府官员",
        }

    # Drive every visit through AI -> write -> verify (happy path)
    for _ in visit_ids:
        payload = await asyncio.wait_for(welcome_requested_queue.get(), timeout=5)
        await ai_writeup_worker.handle_welcome_requested(payload)

    written_cards: dict[int, str] = {}
    for _ in visit_ids:
        payload = await asyncio.wait_for(welcome_generated_queue.get(), timeout=5)
        await card_service.handle_welcome_generated(payload)
        completed = await asyncio.wait_for(card_write_queue.get(), timeout=5)
        written_cards[completed["visit_id"]] = completed["card_uid"]

    # Correct card+name -> passes verification
    good_visit_id = visit_ids[0]
    good_card_uid = written_cards[good_visit_id]
    good_payload = nfc_adapter.get_written_payload(good_card_uid)
    await verify_service.handle_card_verify_requested(
        {"card_uid": good_card_uid, "raw_payload": good_payload}
    )
    passed = await asyncio.wait_for(verify_passed_queue.get(), timeout=5)
    assert passed["visit_id"] == good_visit_id

    # Tampered name -> fails verification (exercises the reject path from
    # docs/TARGET.md §3.3 without needing a real mismatched fixture row)
    bad_visit_id = visit_ids[1]
    bad_card_uid = written_cards[bad_visit_id]
    tampered_payload = dict(nfc_adapter.get_written_payload(bad_card_uid))
    tampered_payload["name"] = "冒名顶替"
    await verify_service.handle_card_verify_requested(
        {"card_uid": bad_card_uid, "raw_payload": tampered_payload}
    )
    failed = await asyncio.wait_for(verify_failed_queue.get(), timeout=5)
    assert failed["fail_reason"] == "name_mismatch"

    with session_factory() as session:
        assert session.get(Visit, good_visit_id).status == VisitStatus.VERIFIED
        assert session.get(Visit, bad_visit_id).status == VisitStatus.REJECTED
