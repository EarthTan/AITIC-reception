# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product Overview

AITIC 展厅智能前台 (AITIC Exhibition Hall Smart Reception) — automates visitor reception in an exhibition hall. Replaces paper-based check-in + handwritten welcome notes + manual sign-holding with a digital pipeline: Excel visitor list → AI welcome text generation → NFC card writing → on-site card verification → LED display + TTS speech → work log archiving.

**Target spec:** `docs/TARGET.md`
**Implementation plan:** `docs/AITIC展厅_智能前台_完整实现计划_V1.md`

## Commands

```bash
cd backend

# Run the FastAPI dev server on :8000 (with auto-reload)
uv run main.py

# Run the full test suite (pytest, async mode)
uv run pytest

# Run a single test file
uv run pytest tests/test_registration_service.py

# Run a single test by name
uv run pytest -k test_import_file

# Run tests with verbose output
uv run pytest -v

# Add a dependency
uv add packagename
```

## Architecture (四层架构)

All backend code lives under `backend/`. The frontend (Web) layer has not been started yet — only the backend exists on Day 1.

### Layer 1: Data & Event Layer (`app/core/`)

- **SQLite** is the single source of truth. Excel is used only for import/export, never for internal read-write contention. Connection via SQLAlchemy (`app/core/db.py`).
- **EventBus** (`app/core/event_bus.py`) is an in-process async pub/sub (asyncio.Queue with string topics). All cross-service communication goes through events — services never call each other directly.
- **Config** (`app/core/config.py`) uses `pydantic-settings` with `.env` file support.
- **Backup** (`app/core/backup.py`) uses APScheduler for daily SQLite backups at 02:00.
- **Logging** (`app/core/logging.py`) configures stdlib logging.

### Layer 2: Integration Adapter Layer (`app/adapters/`)

Four abstract adapters defined in `app/adapters/base.py` — each wrapping one external dependency:

| Adapter | Abstract Methods | Purpose |
|---------|-----------------|---------|
| `NFCAdapter` | `write_card`, `read_stream`, `health_check` | NFC card read/write |
| `LEDAdapter` | `display`, `show_rejected`, `health_check` | LED screen control |
| `TTSAdapter` | `enqueue_speech`, `health_check` | Text-to-speech |
| `AIAdapter` | `generate_welcome`, `health_check` | AI welcome text generation |

Each has a **Mock implementation** under `app/adapters/{nfc,led,tts,ai}/mock.py` — these are used in development and tests. When hardware arrives, only the adapter implementations are swapped; business logic stays unchanged.

### Layer 3: Business Service Layer (`app/services/`)

Six services, each owning a piece of the pipeline:

| Service | Key Method(s) | Event Subscriptions | Events Published |
|---------|--------------|---------------------|-----------------|
| `RegistrationService` | `import_file`, `parse_excel`, `handle_excel_detected` | `excel.detected` | `visit.imported`, `welcome.requested`, `work_log.append` |
| `AIWriteupWorker` | `handle_welcome_requested` | `welcome.requested` | `welcome.generated`, `work_log.append` |
| `CardService` | `handle_welcome_generated` | `welcome.generated` | `card.write.completed`, `work_log.append` |
| `VerifyService` | `handle_card_verify_requested` | `card.verify.requested` | `card.verify.passed` / `card.verify.failed`, `work_log.append` |
| `LogService` | `handle_work_log_append` | `work_log.append` | (none) |
| *(future)* Excel watcher in `app/watchers/excel_watcher.py` uses watchdog to detect new `.xlsx`/`.xls` files and publishes `excel.detected`. |

Services **never import each other**. They communicate exclusively through the EventBus.

### Layer 4: Presentation Layer (not started)

Not yet built — will be a FastAPI Web backend (REST APIs) + a frontend SPA (likely Vue 3, dev server on `:5173` per CORS config).

### Pipeline Event Flow

```
Excel file detected
  → excel.detected
  → RegistrationService.import_file
    → visit.imported
    → welcome.requested (one per visitor)
  → AIWriteupWorker.handle_welcome_requested
    → welcome.generated
  → CardService.handle_welcome_generated
    → card.write.completed
  → NFC card read on-site
    → card.verify.requested
  → VerifyService.handle_card_verify_requested
    → card.verify.passed / card.verify.failed
```

Every step also publishes `work_log.append` → consumed by `LogService`.

## Data Models (`app/models/`)

Six SQLAlchemy ORM models, all inheriting from `app.core.db.Base`:

- **Visit** — core entity with a status machine: `PENDING → WELCOME_READY → CARD_WRITTEN → VERIFIED | REJECTED`
- **WelcomeTemplate** — one row per identity type (7 rows seeded by `app/core/seed.py`)
- **NFCWriteLog** — audit trail for every card write attempt
- **VerifyLog** — audit trail for every on-site card verification
- **WorkLog** — cross-module audit log
- **AdapterStatus** — heartbeat tracking for the 4 adapters

## Wiring (`app/main.py`)

`build_app()` is the composition root: creates engine, session factory, event bus, all adapters (mock), all services, the scheduler, and wires event subscriptions via async background tasks in the FastAPI lifespan. Module-level `__getattr__` gives uvicorn a deferred `app` singleton so tests can import `build_app` directly without triggering a full build.

## Project File Layout (backend only)

```
backend/
├── app/
│   ├── core/           # Config, DB, EventBus, logging, backup, seed
│   ├── models/         # 6 SQLAlchemy ORM models
│   ├── services/       # 5 business services
│   ├── adapters/       # 4 abstract adapters + mock implementations
│   └── watchers/       # Excel file watcher (watchdog)
├── tests/              # pytest suite (~15 test files)
├── data/               # SQLite DB + backups + incoming Excel dir
├── .env.example
├── pyproject.toml
└── main.py             # uvicorn entrypoint
```

## Test Patterns

- Uses in-memory SQLite (`sqlite:///:memory:`) per test — each test creates its own engine/session_factory.
- EventBus is created fresh per test; tests subscribe to topics they need to assert on.
- Mock adapters (`MockAIAdapter`, `MockNFCAdapter`, etc.) are used throughout.
- All async tests use `pytest-asyncio` with `asyncio_mode = "auto"`.
- The e2e test (`test_end_to_end.py`) exercises the full pipeline: import → AI → write → verify → log.
- Backend runs Python 3.13+. Use `uv` (not pip/poetry) for dependency management.
