# backend/app/main.py
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 - ensures all 6 ORM classes register with Base before create_all
from app.adapters.ai.mock import MockAIAdapter
from app.adapters.led.mock import MockLEDAdapter
from app.adapters.nfc.mock import MockNFCAdapter
from app.adapters.tts.mock import MockTTSAdapter
from app.core.config import Settings, get_settings
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.core.logging import configure_logging
from app.core.seed import seed_default_templates
from app.services.ai_writeup_service import AIWriteupWorker
from app.services.card_service import CardService
from app.services.log_service import LogService
from app.services.registration_service import RegistrationService
from app.services.verify_service import VerifyService
from app.watchers.excel_watcher import ExcelWatcher


def build_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        seed_default_templates(session)

    event_bus = EventBus()
    nfc_adapter = MockNFCAdapter()
    led_adapter = MockLEDAdapter()
    tts_adapter = MockTTSAdapter()
    ai_adapter = MockAIAdapter()

    registration_service = RegistrationService(session_factory, event_bus)
    ai_writeup_worker = AIWriteupWorker(session_factory, event_bus, ai_adapter)
    card_service = CardService(session_factory, event_bus, nfc_adapter)
    verify_service = VerifyService(session_factory, event_bus)
    log_service = LogService(session_factory)
    excel_watcher = ExcelWatcher(settings.excel_watch_dir, event_bus)

    background_tasks: list[asyncio.Task] = []

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        background_tasks.extend(
            [
                asyncio.create_task(
                    _consume(
                        event_bus,
                        "excel.detected",
                        registration_service.handle_excel_detected,
                    )
                ),
                asyncio.create_task(
                    _consume(
                        event_bus,
                        "welcome.requested",
                        ai_writeup_worker.handle_welcome_requested,
                    )
                ),
                asyncio.create_task(
                    _consume(
                        event_bus,
                        "welcome.generated",
                        card_service.handle_welcome_generated,
                    )
                ),
                asyncio.create_task(
                    _consume(
                        event_bus,
                        "card.verify.requested",
                        verify_service.handle_card_verify_requested,
                    )
                ),
                asyncio.create_task(
                    _consume(
                        event_bus, "work_log.append", log_service.handle_work_log_append
                    )
                ),
                asyncio.create_task(_pump_card_reads(nfc_adapter, event_bus)),
            ]
        )
        excel_watcher.start()
        yield
        excel_watcher.stop()
        for task in background_tasks:
            task.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)

    fastapi_app = FastAPI(title="AITIC 展厅智能前台", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.state.event_bus = event_bus
    fastapi_app.state.session_factory = session_factory
    fastapi_app.state.adapters = {
        "nfc": nfc_adapter,
        "led": led_adapter,
        "tts": tts_adapter,
        "ai": ai_adapter,
    }
    fastapi_app.state.services = {
        "registration": registration_service,
        "ai_writeup": ai_writeup_worker,
        "card": card_service,
        "verify": verify_service,
        "log": log_service,
    }

    @fastapi_app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return fastapi_app


async def _consume(event_bus: EventBus, topic: str, handler) -> None:
    queue = event_bus.subscribe(topic)
    while True:
        payload = await queue.get()
        try:
            await handler(payload)
        except Exception:
            logger.exception("Handler for topic %r failed", topic)


async def _pump_card_reads(nfc_adapter: MockNFCAdapter, event_bus: EventBus) -> None:
    async for event in nfc_adapter.read_stream():
        await event_bus.publish(
            "card.verify.requested",
            {"card_uid": event.card_uid, "raw_payload": event.raw_payload},
        )


_APP: FastAPI | None = None


def _get_app() -> FastAPI:
    global _APP
    if _APP is None:
        _APP = build_app()
    return _APP


# Module-level singleton: uvicorn accesses "app.main:app".
# Deferred via __getattr__ so that importing build_app for tests
# does not trigger a full build against the default settings.
def __getattr__(name: str):
    if name == "app":
        return _get_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
