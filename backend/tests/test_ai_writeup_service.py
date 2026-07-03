# backend/tests/test_ai_writeup_service.py
import asyncio
from datetime import date, datetime

from app.adapters.ai.mock import MockAIAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.visit import (
    EntrySource,
    IdentityType,
    Visit,
    VisitStatus,
    WelcomeSource,
)
from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate
from app.services.ai_writeup_service import AIWriteupWorker


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
            status=VisitStatus.PENDING,
        )
        session.add(visit)
        session.add(
            WelcomeTemplate(
                identity_type=TemplateIdentityType.ENTERPRISE_LEADER,
                template_text="{姓名}先生/女士，欢迎您",
            )
        )
        session.add(
            WelcomeTemplate(
                identity_type=TemplateIdentityType.DEFAULT,
                template_text="{姓名}，欢迎您",
            )
        )
        session.commit()
        visit_id = visit.id
    return session_factory, visit_id


async def test_handle_welcome_requested_uses_ai_adapter_on_success():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    generated_queue = event_bus.subscribe("welcome.generated")
    work_log_queue = event_bus.subscribe("work_log.append")
    worker = AIWriteupWorker(session_factory, event_bus, MockAIAdapter())

    await worker.handle_welcome_requested({"visit_id": visit_id})

    with session_factory() as session:
        visit = session.get(Visit, visit_id)
        assert visit.welcome_source == WelcomeSource.AI
        assert visit.status == VisitStatus.WELCOME_READY
        assert "张三" in visit.welcome_text

    generated_payload = await asyncio.wait_for(generated_queue.get(), timeout=1)
    assert generated_payload["visit_id"] == visit_id
    assert generated_payload["source"] == "ai"

    log_payload = await asyncio.wait_for(work_log_queue.get(), timeout=1)
    assert log_payload["status"] == "success"


async def test_handle_welcome_requested_falls_back_to_template_on_ai_failure():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    generated_queue = event_bus.subscribe("welcome.generated")
    work_log_queue = event_bus.subscribe("work_log.append")
    worker = AIWriteupWorker(
        session_factory, event_bus, MockAIAdapter(raise_error=True)
    )

    await worker.handle_welcome_requested({"visit_id": visit_id})

    with session_factory() as session:
        visit = session.get(Visit, visit_id)
        assert visit.welcome_source == WelcomeSource.FALLBACK_TEMPLATE
        assert visit.welcome_text == "张三先生/女士，欢迎您"

    generated_payload = await asyncio.wait_for(generated_queue.get(), timeout=1)
    assert generated_payload["source"] == "fallback_template"

    log_payload = await asyncio.wait_for(work_log_queue.get(), timeout=1)
    assert log_payload["status"] == "warning"
