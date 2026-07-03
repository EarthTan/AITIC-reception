# backend/app/main.py
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import (
    models,  # noqa: F401 - ensures all 6 ORM classes register with Base before create_all
)
from app.adapters.ai.mock import MockAIAdapter
from app.adapters.ai.real import QwenAIAdapter
from app.adapters.base import AIAdapter
from app.adapters.led.mock import MockLEDAdapter
from app.adapters.nfc.mock import MockNFCAdapter
from app.adapters.tts.mock import MockTTSAdapter
from app.api.adapters import router as adapters_router
from app.api.cards import router as cards_router
from app.api.debug import router as debug_router
from app.api.imports import router as imports_router
from app.api.logs import router as logs_router
from app.api.settings import router as settings_router
from app.api.templates import router as templates_router
from app.api.visits import router as visits_router
from app.api.ws import router as ws_router
from app.core.backup import schedule_daily_backup
from app.core.config import Settings, get_settings
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.core.logging import configure_logging
from app.core.seed import seed_default_templates
from app.core.settings_store import apply_overrides, load_overrides
from app.services.adapter_status_service import AdapterStatusService
from app.services.ai_writeup_service import AIWriteupWorker
from app.services.card_service import CardService
from app.services.log_service import LogService
from app.services.registration_service import RegistrationService
from app.services.verify_service import VerifyService
from app.watchers.excel_watcher import ExcelWatcher

logger = logging.getLogger(__name__)


def build_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings_override_path = Path("data/settings_override.json")
    settings = apply_overrides(settings, load_overrides(settings_override_path))
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
    ai_adapter: AIAdapter = (
        QwenAIAdapter(api_key=settings.ai_api_key)
        if settings.ai_api_key
        else MockAIAdapter()
    )

    registration_service = RegistrationService(session_factory, event_bus)
    ai_writeup_worker = AIWriteupWorker(session_factory, event_bus, ai_adapter)
    card_service = CardService(session_factory, event_bus, nfc_adapter)
    verify_service = VerifyService(session_factory, event_bus)
    log_service = LogService(session_factory)
    adapter_status_service = AdapterStatusService(session_factory)
    excel_watcher = ExcelWatcher(settings.excel_watch_dir, event_bus)

    scheduler = BackgroundScheduler()
    schedule_daily_backup(
        scheduler, settings.database_url.removeprefix("sqlite:///"), "backup"
    )

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
                asyncio.create_task(
                    _consume(
                        event_bus,
                        "adapter.heartbeat",
                        adapter_status_service.handle_adapter_heartbeat,
                    )
                ),
                asyncio.create_task(_pump_card_reads(nfc_adapter, event_bus)),
                asyncio.create_task(
                    _poll_adapter_heartbeats(
                        {
                            "nfc": nfc_adapter,
                            "led": led_adapter,
                            "tts": tts_adapter,
                            "ai": ai_adapter,
                        },
                        event_bus,
                    )
                ),
            ]
        )
        excel_watcher.start()
        scheduler.start()
        yield
        excel_watcher.stop()
        scheduler.shutdown(wait=False)
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
    fastapi_app.state.settings = settings
    fastapi_app.state.settings_override_path = settings_override_path
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
        "adapter_status": adapter_status_service,
    }

    @fastapi_app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    for router in (
        imports_router,
        visits_router,
        templates_router,
        cards_router,
        logs_router,
        adapters_router,
        settings_router,
        debug_router,
        ws_router,
    ):
        fastapi_app.include_router(router)

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


async def _poll_adapter_heartbeats(
    adapters: dict, event_bus: EventBus, interval_seconds: float = 30.0
) -> None:
    """First `adapter.heartbeat` producer in the codebase (Task 14 addition).

    Day 1 has no other producer. Until this loop ticks once, the
    `adapter_status` table is empty and `GET /api/adapters/status` returns `[]`.
    """
    while True:
        for name, adapter in adapters.items():
            health = await adapter.health_check()
            await event_bus.publish(
                "adapter.heartbeat",
                {
                    "adapter_name": name,
                    "status": health.status,
                    "detail": health.detail,
                },
            )
        await asyncio.sleep(interval_seconds)


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
