"""Tests for OnsiteWelcomeService — drives LED + TTS + beep from verify events.

§三.3 现场欢迎闭环的服务层测试：verify 通过/失败事件被翻译为 LED 显示 +
TTS 朗读/蜂鸣 + work_log 写入。无 VerifyService 依赖（解耦）。
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from app.services.onsite_welcome_service import OnsiteWelcomeService

from app.adapters.led.mock import MockLEDAdapter
from app.adapters.tts.mock import MockTTSAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.visit import (
    EntrySource,
    IdentityType,
    Visit,
    VisitStatus,
    WelcomeSource,
)


@pytest.fixture
def session_factory():
    """In-memory SQLite with one Visit row seeded, plus factory's visit_id attr.

    Mirrors the pattern from `tests/test_verify_service.py` (in-memory engine +
    `Base.metadata.create_all` + `make_session_factory`) per design §3.1.
    """
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = make_session_factory(engine)

    with SessionLocal() as s:
        v = Visit(
            visit_date=date(2026, 7, 7),
            session_time=datetime(2026, 7, 7, 9, 0),
            name="王企业",
            identity_type=IdentityType.ENTERPRISE_LEADER,
            welcome_text="王企业 先生，欢迎您",
            welcome_source=WelcomeSource.AI,
            entry_source=EntrySource.MANUAL,
            import_batch_id="test",
            status=VisitStatus.CARD_WRITTEN,
        )
        s.add(v)
        s.commit()
        s.refresh(v)
        visit_id = v.id

    def factory():
        return SessionLocal()

    factory.visit_id = visit_id
    return factory


@pytest.mark.asyncio
async def test_passed_drives_led_and_tts(session_factory):
    bus = EventBus()
    led = MockLEDAdapter()
    tts = MockTTSAdapter()
    svc = OnsiteWelcomeService(led, tts, bus, session_factory)

    await svc.handle_card_verify_passed(
        {"visit_id": session_factory.visit_id, "card_uid": "TEST-001"}
    )

    assert len(led.displayed) == 1
    assert led.displayed[0].name == "王企业"
    assert led.displayed[0].welcome_text == "王企业 先生，欢迎您"
    assert tts.spoken == ["王企业 先生，欢迎您"]


@pytest.mark.asyncio
async def test_failed_drives_led_rejection_and_beep(session_factory):
    bus = EventBus()
    led = MockLEDAdapter()
    tts = MockTTSAdapter()
    svc = OnsiteWelcomeService(led, tts, bus, session_factory)

    await svc.handle_card_verify_failed(
        {"visit_id": 9999, "card_uid": "BAD-001", "fail_reason": "card_not_found"}
    )

    assert len(led.rejected) == 1
    assert led.rejected[0].is_rejection is True
    assert led.rejected[0].welcome_text == "无权限入场"
    assert tts.beeps == [(1.5,)]
