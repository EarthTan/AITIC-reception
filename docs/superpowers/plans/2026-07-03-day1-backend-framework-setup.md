# Day 1 · 后端基本框架搭建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend skeleton for AITIC展厅智能前台 — 6 SQLite tables, an asyncio event bus, 4 Mock hardware adapters, and 5 business services wired end-to-end in a single FastAPI process, so that dropping a visitor Excel into the watched folder flows through 登记→AI(mock)→写卡(mock)→校验(mock)→日志 without touching real hardware.

**Architecture:** Four layers per `docs/AITIC展厅_智能前台_完整实现计划_V1.md` §五: 表现层(FastAPI, no routes yet — Day 2) / 业务服务层(5 services) / 集成适配层(4 Adapter ABCs + Mock impls) / 数据事件层(SQLite via SQLAlchemy + an in-process `asyncio.Queue` pub/sub event bus). Services never call adapters' concrete SDKs directly — only the `NFCAdapter`/`LEDAdapter`/`TTSAdapter`/`AIAdapter` ABCs — so Day 4 swaps Mock→Real without touching service code. Modules talk only through the event bus (never direct method calls across services), so one module failing doesn't take down the process.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 (declarative, sqlite), pydantic-settings, pandas+openpyxl (Excel), watchdog (folder watch), APScheduler (DB backup), uv (package manager), pytest + pytest-asyncio (TDD).

## Global Constraints

- Single machine, local-only: one Windows PC, local Python process, no Docker/Postgres/Redis. (TARGET.md §五)
- SQLite is the sole authoritative data store; Excel is only an import/export interface, never read back into the app. (TARGET.md §五)
- All hardware/AI access goes through the 4 Adapter ABCs (`NFCAdapter`/`LEDAdapter`/`TTSAdapter`/`AIAdapter`); business/service code must never import a concrete SDK. Develop and test entirely against Mock adapters — Real adapters land Day 4. (TARGET.md §五, 完整实现计划 §4.3)
- Decouple modules via the event bus; one module's failure must not take down the rest of the process. (TARGET.md §五)
- No login/multi-user/permissions, no anti-replay/dedup on card verification, no LED multi-screen grouping — explicitly out of scope for the whole V1, not just Day 1. (TARGET.md §七)
- AI-generated welcome text must never be left empty — on AI failure, fall back to the rule-based template, no exceptions. (TARGET.md §3.1)
- `visits` is keyed by (来访日期, 姓名) for on-site verification — both fields must be recoverable from whatever the NFC card carries. (TARGET.md §3.3)
- Sensitive fields (身份证号) are stored as given by Excel; masking is a **display-time** concern for the Day 2/3 API+frontend layer, not the Day 1 data layer — do not print `id_number` into `work_log.detail` in any service written today. (TARGET.md §六.2)
- Package/dependency management is `uv` (`uv add <pkg>`, `uv run <cmd>`) per the existing repo convention in `README.md` — do not introduce pip/poetry/conda.
- Every service and adapter method that does I/O is `async def`; the event bus and all service handlers use `asyncio`, not threads (except `watchdog`'s Observer, which is thread-based by design — bridge it back to the event loop with `asyncio.run_coroutine_threadsafe`).

---

## File Structure

```text
AITIC-reception/
├── docs/                              # unchanged — spec + this plan
├── README.md                          # updated to point at backend/README.md
├── .gitignore                         # extended: __pycache__, *.db, backend/data/, backend/backup/, ._*
└── backend/
    ├── pyproject.toml                 # moved from repo root, uv-managed, +pytest ini config
    ├── .python-version                # moved from repo root
    ├── main.py                        # `uv run main.py` launcher → runs uvicorn against app.main:app
    ├── .env.example
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                    # build_app(): assembles DB+event bus+services+adapters+watcher
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── config.py              # Settings (pydantic-settings) + get_settings()
    │   │   ├── event_bus.py           # EventBus: asyncio.Queue pub/sub, multi-subscriber
    │   │   ├── db.py                  # Base, make_engine, make_session_factory, session_scope
    │   │   ├── logging.py             # configure_logging()
    │   │   └── seed.py                # seed_default_templates()
    │   ├── models/
    │   │   ├── __init__.py            # re-exports all 6 ORM classes so create_all sees them
    │   │   ├── visit.py               # Visit + IdentityType/WelcomeSource/EntrySource/VisitStatus
    │   │   ├── welcome_template.py    # WelcomeTemplate + TemplateIdentityType
    │   │   ├── nfc_write_log.py       # NFCWriteLog + WriteStatus
    │   │   ├── verify_log.py          # VerifyLog + VerifyResult/FailReason
    │   │   ├── work_log.py            # WorkLog + LogModule/LogStatus
    │   │   └── adapter_status.py      # AdapterStatusRow + AdapterHealthStatus
    │   ├── adapters/
    │   │   ├── __init__.py
    │   │   ├── base.py                # AdapterHealth/WriteResult/CardReadEvent/VisitInfo/LEDContent + 4 ABCs
    │   │   ├── nfc/{__init__.py, mock.py}
    │   │   ├── led/{__init__.py, mock.py}
    │   │   ├── tts/{__init__.py, mock.py}
    │   │   └── ai/{__init__.py, mock.py}
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── registration_service.py  # Excel parse/validate/import + excel.detected handler
    │   │   ├── ai_writeup_service.py    # AIWriteupWorker
    │   │   ├── card_service.py          # CardService
    │   │   ├── verify_service.py        # VerifyService
    │   │   └── log_service.py           # LogService
    │   └── watchers/
    │       ├── __init__.py
    │       └── excel_watcher.py       # watchdog Observer → publishes excel.detected
    └── tests/
        ├── test_event_bus.py
        ├── test_config.py
        ├── test_db.py
        ├── test_models.py
        ├── test_adapters_base.py
        ├── test_adapters_mock.py
        ├── test_registration_service.py
        ├── test_ai_writeup_service.py
        ├── test_card_service.py
        ├── test_verify_service.py
        ├── test_log_service.py
        ├── test_excel_watcher.py
        ├── test_end_to_end.py
        └── test_backup.py
```

`frontend/` is **not** created today — it's Day 3's job (完整实现计划 §五). `app/api/` (FastAPI routes) is also not created today — routes land Day 2; Day 1 only needs the services/adapters/event-bus callable directly from tests and from `app/main.py`'s wiring.

---

### Task 1: Repo restructure into `backend/`, dependencies, package skeleton

**Files:**
- Move: `pyproject.toml` → `backend/pyproject.toml`
- Move: `main.py` → `backend/main.py`
- Move: `.python-version` → `backend/.python-version`
- Modify: `README.md`
- Modify: `.gitignore`
- Delete: `._.DS_Store`, `docs/._TARGET.md`, `docs/._AITIC展厅_智能前台_完整实现计划_V1.md`
- Create: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/models/__init__.py` (placeholder), `backend/app/adapters/__init__.py`, `backend/app/adapters/nfc/__init__.py`, `backend/app/adapters/led/__init__.py`, `backend/app/adapters/tts/__init__.py`, `backend/app/adapters/ai/__init__.py`, `backend/app/services/__init__.py`, `backend/app/watchers/__init__.py`, `backend/tests/` (dir only)
- Create: `backend/.env.example`

**Interfaces:**
- Produces: a `backend/` directory that is a working `uv` project (`uv run python -c "import fastapi"` succeeds), with an importable `app` package and an empty-but-collectible `tests/` directory (`uv run pytest` exits 0 with "no tests ran").

This task has no unit under test yet — it's pure scaffolding. Its own "test" is the verification command in Step 4.

- [ ] **Step 1: Move the existing Python project into `backend/`**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
mkdir -p backend
mv pyproject.toml backend/pyproject.toml
mv main.py backend/main.py
mv .python-version backend/.python-version
rm ._.DS_Store "docs/._TARGET.md" "docs/._AITIC展厅_智能前台_完整实现计划_V1.md"
```

- [ ] **Step 2: Update `backend/pyproject.toml`** (rename project, add pytest config)

```toml
[project]
name = "aitic-reception-backend"
version = "0.1.0"
description = "AITIC 展厅智能前台 · 后端服务"
readme = "../README.md"
requires-python = ">=3.13"
dependencies = []

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: Replace `backend/main.py`** with the uv-run launcher (the real FastAPI app assembly lives in `app/main.py`, built in Task 14)

```python
import uvicorn


def main() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Install dependencies and verify the environment**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception/backend
uv add fastapi "uvicorn[standard]" sqlalchemy pydantic-settings watchdog pandas openpyxl python-multipart websockets httpx apscheduler
uv add --dev pytest pytest-asyncio
```

Run: `uv run python -c "import fastapi, sqlalchemy, pydantic_settings, watchdog, pandas, openpyxl, websockets, httpx, apscheduler; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Create the package skeleton**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception/backend
mkdir -p app/core app/models app/adapters/nfc app/adapters/led app/adapters/tts app/adapters/ai app/services app/watchers tests
: > app/__init__.py
: > app/core/__init__.py
: > app/models/__init__.py
: > app/adapters/__init__.py
: > app/adapters/nfc/__init__.py
: > app/adapters/led/__init__.py
: > app/adapters/tts/__init__.py
: > app/adapters/ai/__init__.py
: > app/services/__init__.py
: > app/watchers/__init__.py
```

Run: `uv run pytest`
Expected: `no tests ran` (exit code 0 or 5, not a collection error)

- [ ] **Step 6: `backend/.env.example`**

```
DATABASE_URL=sqlite:///./data/app.db
EXCEL_WATCH_DIR=./data/incoming
AI_API_KEY=
AI_PROVIDER=qwen
CORS_ORIGINS=["http://localhost:5173"]
```

- [ ] **Step 7: Update root `README.md`**

```markdown
# AITIC 展厅智能前台

See `docs/TARGET.md` for product spec and `docs/AITIC展厅_智能前台_完整实现计划_V1.md` for the implementation plan.

Backend: `cd backend && uv run main.py` (see `backend/README.md`... — none yet, Day 1 covers backend only).
```

Also create `backend/README.md`:

```markdown
# AITIC 展厅智能前台 · backend

Uses uv for the Python environment.

    uv add packagename
    uv run main.py       # starts the FastAPI app on :8000
    uv run pytest        # run the test suite
```

- [ ] **Step 8: Extend `.gitignore`** (append to existing root `.gitignore`)

```
__pycache__/
*.pyc
*.db
backend/data/
backend/backup/
._*
```

- [ ] **Step 9: Commit** (first commit of the repo)

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add README.md .gitignore docs backend
git commit -m "chore: restructure into backend/, set up uv project skeleton"
```

---

### Task 2: Event bus (`core/event_bus.py`)

**Files:**
- Create: `backend/app/core/event_bus.py`
- Test: `backend/tests/test_event_bus.py`

**Interfaces:**
- Produces: `class EventBus` with `subscribe(topics: str | Iterable[str]) -> asyncio.Queue` and `async def publish(topic: str, payload: dict) -> None`. Every later service takes an `EventBus` instance in its constructor and calls exactly these two methods.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_event_bus.py
import asyncio

from app.core.event_bus import EventBus


async def test_subscriber_receives_published_payload():
    bus = EventBus()
    queue = bus.subscribe("visit.imported")

    await bus.publish("visit.imported", {"visit_ids": [1]})

    payload = await asyncio.wait_for(queue.get(), timeout=1)
    assert payload == {"visit_ids": [1]}


async def test_multiple_subscribers_each_receive_the_event():
    bus = EventBus()
    queue_a = bus.subscribe("welcome.generated")
    queue_b = bus.subscribe("welcome.generated")

    await bus.publish("welcome.generated", {"visit_id": 5})

    assert await asyncio.wait_for(queue_a.get(), timeout=1) == {"visit_id": 5}
    assert await asyncio.wait_for(queue_b.get(), timeout=1) == {"visit_id": 5}


async def test_events_delivered_in_publish_order():
    bus = EventBus()
    queue = bus.subscribe("card.verify.requested")

    await bus.publish("card.verify.requested", {"card_uid": "A"})
    await bus.publish("card.verify.requested", {"card_uid": "B"})
    await bus.publish("card.verify.requested", {"card_uid": "C"})

    received = [await queue.get() for _ in range(3)]
    assert [item["card_uid"] for item in received] == ["A", "B", "C"]


async def test_subscribe_to_multiple_topics_merges_into_one_queue():
    bus = EventBus()
    queue = bus.subscribe(["a.topic", "b.topic"])

    await bus.publish("a.topic", {"from": "a"})
    await bus.publish("b.topic", {"from": "b"})

    first = await asyncio.wait_for(queue.get(), timeout=1)
    second = await asyncio.wait_for(queue.get(), timeout=1)
    assert {first["from"], second["from"]} == {"a", "b"}


async def test_publish_with_no_subscribers_does_not_raise():
    bus = EventBus()
    await bus.publish("nobody.listens", {})
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_event_bus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.event_bus'`

- [ ] **Step 3: Implement**

```python
# backend/app/core/event_bus.py
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Iterable


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, topics: str | Iterable[str]) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        for topic in self._normalize_topics(topics):
            self._queues[topic].append(queue)
        return queue

    async def publish(self, topic: str, payload: dict) -> None:
        for queue in self._queues.get(topic, []):
            await queue.put(payload)

    @staticmethod
    def _normalize_topics(topics: str | Iterable[str]) -> list[str]:
        if isinstance(topics, str):
            return [topics]
        return list(topics)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_event_bus.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/core/event_bus.py backend/tests/test_event_bus.py
git commit -m "feat: add asyncio.Queue-backed pub/sub event bus"
```

---

### Task 3: Settings & logging (`core/config.py`, `core/logging.py`)

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/logging.py`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `class Settings(BaseSettings)` with fields `database_url: str`, `excel_watch_dir: str`, `ai_api_key: str`, `ai_provider: str`, `cors_origins: list[str]`; `get_settings() -> Settings` (lru_cache'd). `configure_logging(level: int = logging.INFO) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_config.py
import logging

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


def test_settings_defaults():
    settings = Settings()
    assert settings.database_url == "sqlite:///./data/app.db"
    assert settings.excel_watch_dir == "./data/incoming"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_env_var_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./custom.db")
    settings = Settings()
    assert settings.database_url == "sqlite:///./custom.db"


def test_get_settings_returns_cached_instance():
    get_settings.cache_clear()
    assert get_settings() is get_settings()


def test_configure_logging_sets_root_level():
    configure_logging(level=logging.DEBUG)
    assert logging.getLogger().level == logging.DEBUG
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.config'`

- [ ] **Step 3: Implement**

```python
# backend/app/core/config.py
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/app.db"
    excel_watch_dir: str = "./data/incoming"
    ai_api_key: str = ""
    ai_provider: str = "qwen"
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# backend/app/core/logging.py
from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/core/config.py backend/app/core/logging.py backend/tests/test_config.py
git commit -m "feat: add pydantic-settings config and logging setup"
```

---

### Task 4: Database engine/session (`core/db.py`)

**Files:**
- Create: `backend/app/core/db.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `class Base(DeclarativeBase)` (all 6 models inherit from this), `make_engine(database_url: str) -> Engine`, `make_session_factory(engine: Engine) -> sessionmaker[Session]`, `session_scope(session_factory) -> ContextManager[Session]` (commits on success, rolls back on exception).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_db.py
import pytest
from sqlalchemy import Column, Integer, String

from app.core.db import Base, make_engine, make_session_factory, session_scope


class ScratchRow(Base):
    __tablename__ = "scratch_row"
    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)


def _fresh_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def test_session_scope_commits_on_success():
    session_factory = _fresh_session_factory()
    with session_scope(session_factory) as session:
        session.add(ScratchRow(name="ok"))
    with session_scope(session_factory) as session:
        assert session.query(ScratchRow).count() == 1


def test_session_scope_rolls_back_on_error():
    session_factory = _fresh_session_factory()
    with pytest.raises(ValueError):
        with session_scope(session_factory) as session:
            session.add(ScratchRow(name="a"))
            raise ValueError("boom")
    with session_scope(session_factory) as session:
        assert session.query(ScratchRow).count() == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.db'`

- [ ] **Step 3: Implement**

```python
# backend/app/core/db.py
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope(session_factory: sessionmaker) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/core/db.py backend/tests/test_db.py
git commit -m "feat: add SQLAlchemy engine/session factory with session_scope helper"
```

---

### Task 5: Six SQLAlchemy models + default template seeding

**Files:**
- Create: `backend/app/models/visit.py`
- Create: `backend/app/models/welcome_template.py`
- Create: `backend/app/models/nfc_write_log.py`
- Create: `backend/app/models/verify_log.py`
- Create: `backend/app/models/work_log.py`
- Create: `backend/app/models/adapter_status.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/core/seed.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `Base` from `app.core.db` (Task 4).
- Produces: ORM classes `Visit`, `WelcomeTemplate`, `NFCWriteLog`, `VerifyLog`, `WorkLog`, `AdapterStatusRow`, and enums `IdentityType`, `WelcomeSource`, `EntrySource`, `VisitStatus`, `TemplateIdentityType`, `WriteStatus`, `VerifyResult`, `FailReason`, `LogModule`, `LogStatus`, `AdapterHealthStatus` — every later service imports these by these exact names. `seed_default_templates(session: Session) -> None` — idempotent, called once at startup (Task 14).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_models.py
from datetime import date, datetime

from app.core.db import Base, make_engine, make_session_factory
from app.core.seed import seed_default_templates
from app.models.adapter_status import AdapterHealthStatus, AdapterStatusRow
from app.models.nfc_write_log import NFCWriteLog, WriteStatus
from app.models.verify_log import VerifyLog, VerifyResult
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus
from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate
from app.models.work_log import LogModule, LogStatus, WorkLog


def _fresh_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def test_all_six_tables_accept_one_row_each():
    session_factory = _fresh_session_factory()
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
        session.flush()

        session.add(WelcomeTemplate(identity_type=TemplateIdentityType.DEFAULT, template_text="{姓名}，欢迎您"))
        session.add(
            NFCWriteLog(visit_id=visit.id, card_uid="UID-1", write_status=WriteStatus.SUCCESS)
        )
        session.add(
            VerifyLog(card_uid="UID-1", visit_id=visit.id, verify_result=VerifyResult.PASS)
        )
        session.add(
            WorkLog(module=LogModule.REGISTRATION, action="import", status=LogStatus.SUCCESS, detail="ok")
        )
        session.add(
            AdapterStatusRow(
                adapter_name="nfc",
                status=AdapterHealthStatus.ONLINE,
                last_heartbeat=datetime.utcnow(),
            )
        )
        session.commit()

        assert session.query(Visit).count() == 1
        assert session.query(WelcomeTemplate).count() == 1
        assert session.query(NFCWriteLog).count() == 1
        assert session.query(VerifyLog).count() == 1
        assert session.query(WorkLog).count() == 1
        assert session.query(AdapterStatusRow).count() == 1


def test_seed_default_templates_creates_seven_rows():
    session_factory = _fresh_session_factory()
    with session_factory() as session:
        seed_default_templates(session)
        rows = {row.identity_type: row.template_text for row in session.query(WelcomeTemplate).all()}

    assert len(rows) == 7
    assert rows[TemplateIdentityType.GOVERNMENT_OFFICIAL] == "欢迎{姓名}同志到场视察"
    assert rows[TemplateIdentityType.SCHOOL_STUDENT] == "{姓名}同学，你好呀"


def test_seed_default_templates_is_idempotent():
    session_factory = _fresh_session_factory()
    with session_factory() as session:
        seed_default_templates(session)
        seed_default_templates(session)
        assert session.query(WelcomeTemplate).count() == 7
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.visit'`

- [ ] **Step 3: Implement**

```python
# backend/app/models/visit.py
import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# NOTE: sqlalchemy.Enum persists the Python enum MEMBER NAME (e.g. "ENTERPRISE_LEADER"),
# not its .value ("企业领导"). Round-trips through the ORM are unaffected; only matters
# if someone inspects the raw .db file with a SQL client.


class IdentityType(str, enum.Enum):
    ENTERPRISE_LEADER = "企业领导"
    ENTERPRISE_STAFF = "企业员工"
    SCHOOL_TEACHER = "学校老师"
    UNIVERSITY_STUDENT = "大学生"
    SCHOOL_STUDENT = "中小学生"
    GOVERNMENT_OFFICIAL = "政府官员"


class WelcomeSource(str, enum.Enum):
    AI = "ai"
    FALLBACK_TEMPLATE = "fallback_template"


class EntrySource(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class VisitStatus(str, enum.Enum):
    PENDING = "pending"
    WELCOME_READY = "welcome_ready"
    CARD_WRITTEN = "card_written"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identity_type: Mapped[IdentityType] = mapped_column(Enum(IdentityType), nullable=False)
    welcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    welcome_source: Mapped[WelcomeSource | None] = mapped_column(Enum(WelcomeSource), nullable=True)
    entry_source: Mapped[EntrySource] = mapped_column(Enum(EntrySource), nullable=False)
    import_batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[VisitStatus] = mapped_column(Enum(VisitStatus), nullable=False, default=VisitStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

```python
# backend/app/models/welcome_template.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TemplateIdentityType(str, enum.Enum):
    DEFAULT = "默认"
    ENTERPRISE_LEADER = "企业领导"
    ENTERPRISE_STAFF = "企业员工"
    SCHOOL_TEACHER = "学校老师"
    UNIVERSITY_STUDENT = "大学生"
    SCHOOL_STUDENT = "中小学生"
    GOVERNMENT_OFFICIAL = "政府官员"


class WelcomeTemplate(Base):
    __tablename__ = "welcome_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identity_type: Mapped[TemplateIdentityType] = mapped_column(
        Enum(TemplateIdentityType), nullable=False, unique=True
    )
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

```python
# backend/app/models/nfc_write_log.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WriteStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class NFCWriteLog(Base):
    __tablename__ = "nfc_write_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id"), nullable=False)
    card_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    write_status: Mapped[WriteStatus] = mapped_column(Enum(WriteStatus), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    written_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/verify_log.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class VerifyResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"


class FailReason(str, enum.Enum):
    NAME_MISMATCH = "name_mismatch"
    DATE_MISMATCH = "date_mismatch"
    CARD_NOT_FOUND = "card_not_found"


class VerifyLog(Base):
    __tablename__ = "verify_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    visit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("visits.id"), nullable=True)
    verify_result: Mapped[VerifyResult] = mapped_column(Enum(VerifyResult), nullable=False)
    fail_reason: Mapped[FailReason | None] = mapped_column(Enum(FailReason), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/work_log.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LogModule(str, enum.Enum):
    REGISTRATION = "registration"
    AI_WRITEUP = "ai_writeup"
    CARD_WRITE = "card_write"
    VERIFY = "verify"
    LED = "led"
    TTS = "tts"
    SYSTEM = "system"


class LogStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"


class WorkLog(Base):
    __tablename__ = "work_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[LogModule] = mapped_column(Enum(LogModule), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[LogStatus] = mapped_column(Enum(LogStatus), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/adapter_status.py
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AdapterHealthStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class AdapterStatusRow(Base):
    __tablename__ = "adapter_status"

    adapter_name: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[AdapterHealthStatus] = mapped_column(Enum(AdapterHealthStatus), nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
```

```python
# backend/app/models/__init__.py
from app.models.adapter_status import AdapterStatusRow
from app.models.nfc_write_log import NFCWriteLog
from app.models.verify_log import VerifyLog
from app.models.visit import Visit
from app.models.welcome_template import WelcomeTemplate
from app.models.work_log import WorkLog

__all__ = [
    "AdapterStatusRow",
    "NFCWriteLog",
    "VerifyLog",
    "Visit",
    "WelcomeTemplate",
    "WorkLog",
]
```

```python
# backend/app/core/seed.py
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate

DEFAULT_TEMPLATES: dict[TemplateIdentityType, str] = {
    TemplateIdentityType.DEFAULT: "{姓名}先生/女士，欢迎您",
    TemplateIdentityType.ENTERPRISE_LEADER: "{姓名}先生/女士，欢迎您",
    TemplateIdentityType.ENTERPRISE_STAFF: "{姓名}先生/女士，欢迎您",
    TemplateIdentityType.GOVERNMENT_OFFICIAL: "欢迎{姓名}同志到场视察",
    TemplateIdentityType.SCHOOL_TEACHER: "欢迎{姓名}专家到场指导",
    TemplateIdentityType.UNIVERSITY_STUDENT: "{姓名}同学，欢迎参观",
    TemplateIdentityType.SCHOOL_STUDENT: "{姓名}同学，你好呀",
}


def seed_default_templates(session: Session) -> None:
    existing = {row.identity_type for row in session.query(WelcomeTemplate).all()}
    for identity_type, template_text in DEFAULT_TEMPLATES.items():
        if identity_type in existing:
            continue
        session.add(WelcomeTemplate(identity_type=identity_type, template_text=template_text))
    session.commit()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_models.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/models backend/app/core/seed.py backend/tests/test_models.py
git commit -m "feat: add SQLAlchemy models for all 6 tables and default template seeding"
```

---

### Task 6: Adapter schemas & abstract base classes (`adapters/base.py`)

**Files:**
- Create: `backend/app/adapters/base.py`
- Test: `backend/tests/test_adapters_base.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure pydantic + ABC).
- Produces: pydantic models `AdapterHealth`, `WriteResult`, `CardReadEvent`, `VisitInfo`, `LEDContent`; abstract classes `NFCAdapter` (`write_card`, `read_stream`, `health_check`), `LEDAdapter` (`display`, `show_rejected`, `health_check`), `TTSAdapter` (`enqueue_speech`, `health_check`), `AIAdapter` (`generate_welcome`). All 4 Mock adapters (Task 7) and all services (Tasks 8-11) import these exact names from `app.adapters.base`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_adapters_base.py
from datetime import datetime, timezone

import pytest

from app.adapters.base import (
    AdapterHealth,
    AIAdapter,
    CardReadEvent,
    LEDAdapter,
    LEDContent,
    NFCAdapter,
    TTSAdapter,
    VisitInfo,
    WriteResult,
)


def test_adapter_health_model_holds_expected_fields():
    health = AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
    assert health.status == "online"
    assert health.detail is None


def test_write_result_and_card_read_event_models():
    result = WriteResult(success=True, card_uid="ABC123")
    assert result.error_message is None
    event = CardReadEvent(card_uid="ABC123", raw_payload={"name": "张三"})
    assert event.raw_payload["name"] == "张三"


def test_visit_info_and_led_content_models():
    visit_info = VisitInfo(visit_id=1, name="张三", identity_type="企业领导", visit_date="2026-07-06")
    assert visit_info.organization is None
    content = LEDContent(name="张三", welcome_text="欢迎您")
    assert content.welcome_text == "欢迎您"


@pytest.mark.parametrize("adapter_cls", [NFCAdapter, LEDAdapter, TTSAdapter, AIAdapter])
def test_abstract_adapters_cannot_be_instantiated_directly(adapter_cls):
    with pytest.raises(TypeError):
        adapter_cls()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_adapters_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.adapters.base'`

- [ ] **Step 3: Implement**

```python
# backend/app/adapters/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AdapterHealth(BaseModel):
    status: Literal["online", "offline", "error"]
    detail: str | None = None
    last_heartbeat: datetime


class WriteResult(BaseModel):
    success: bool
    card_uid: str
    error_message: str | None = None


class CardReadEvent(BaseModel):
    card_uid: str
    raw_payload: dict


class VisitInfo(BaseModel):
    visit_id: int
    name: str
    identity_type: str
    visit_date: str
    organization: str | None = None


class LEDContent(BaseModel):
    name: str
    welcome_text: str


class NFCAdapter(ABC):
    @abstractmethod
    async def write_card(self, card_uid: str, payload: dict) -> WriteResult: ...

    @abstractmethod
    def read_stream(self) -> AsyncIterator[CardReadEvent]:
        """持续产出刷卡事件；多读写器的轮询/去重在实现内部处理，
        对上层就是一个源源不断的事件流"""

    @abstractmethod
    async def health_check(self) -> AdapterHealth: ...


class LEDAdapter(ABC):
    @abstractmethod
    async def display(self, screen_ids: list[str], content: LEDContent) -> None: ...

    @abstractmethod
    async def show_rejected(self, screen_ids: list[str]) -> None: ...

    @abstractmethod
    async def health_check(self) -> AdapterHealth: ...


class TTSAdapter(ABC):
    @abstractmethod
    async def enqueue_speech(self, text: str) -> None:
        """加入播报队列，内部保证FIFO顺序播放"""

    @abstractmethod
    async def health_check(self) -> AdapterHealth: ...


class AIAdapter(ABC):
    @abstractmethod
    async def generate_welcome(self, visit: VisitInfo) -> str:
        """失败时抛异常，由AIWriteupWorker捕获后走规则模板兜底"""
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_adapters_base.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/adapters/base.py backend/tests/test_adapters_base.py
git commit -m "feat: add adapter schemas and abstract base classes for NFC/LED/TTS/AI"
```

---

### Task 7: Mock adapters (NFC/LED/TTS/AI)

**Files:**
- Create: `backend/app/adapters/nfc/mock.py`
- Create: `backend/app/adapters/led/mock.py`
- Create: `backend/app/adapters/tts/mock.py`
- Create: `backend/app/adapters/ai/mock.py`
- Test: `backend/tests/test_adapters_mock.py`

**Interfaces:**
- Consumes: `AdapterHealth`, `WriteResult`, `CardReadEvent`, `VisitInfo`, `LEDContent`, `NFCAdapter`, `LEDAdapter`, `TTSAdapter`, `AIAdapter` from `app.adapters.base` (Task 6).
- Produces: `MockNFCAdapter` (extra methods `get_written_payload(card_uid) -> dict`, `async simulate_card_read(card_uid, raw_payload) -> None` — used by the debug endpoint in Day 2 and by Task 15's end-to-end test), `MockLEDAdapter` (`.displayed: list`, `.rejected: list`), `MockTTSAdapter` (`.spoken: list[str]`), `MockAIAdapter(raise_error: bool = False)` (`.requests: list[VisitInfo]`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_adapters_mock.py
import pytest

from app.adapters.ai.mock import MockAIAdapter
from app.adapters.base import LEDContent, VisitInfo
from app.adapters.led.mock import MockLEDAdapter
from app.adapters.nfc.mock import MockNFCAdapter
from app.adapters.tts.mock import MockTTSAdapter


async def test_mock_nfc_write_then_read_back_round_trip():
    adapter = MockNFCAdapter()
    result = await adapter.write_card("UID-1", {"name": "张三"})
    assert result.success is True
    assert adapter.get_written_payload("UID-1") == {"name": "张三"}

    await adapter.simulate_card_read("UID-1", {"name": "张三"})
    stream = adapter.read_stream()
    event = await stream.__anext__()
    assert event.card_uid == "UID-1"
    assert event.raw_payload == {"name": "张三"}


async def test_mock_nfc_health_check_reports_online():
    adapter = MockNFCAdapter()
    health = await adapter.health_check()
    assert health.status == "online"


async def test_mock_led_records_display_and_rejected_calls():
    adapter = MockLEDAdapter()
    await adapter.display(["screen-1"], LEDContent(name="张三", welcome_text="欢迎您"))
    await adapter.show_rejected(["screen-1"])
    assert len(adapter.displayed) == 1
    assert adapter.displayed[0][0] == ["screen-1"]
    assert adapter.rejected == [["screen-1"]]


async def test_mock_tts_records_spoken_text():
    adapter = MockTTSAdapter()
    await adapter.enqueue_speech("欢迎您")
    assert adapter.spoken == ["欢迎您"]


async def test_mock_ai_generates_welcome_text_by_default():
    adapter = MockAIAdapter()
    visit = VisitInfo(visit_id=1, name="张三", identity_type="企业领导", visit_date="2026-07-06")
    text = await adapter.generate_welcome(visit)
    assert "张三" in text
    assert adapter.requests == [visit]


async def test_mock_ai_raises_when_configured_to_fail():
    adapter = MockAIAdapter(raise_error=True)
    visit = VisitInfo(visit_id=1, name="张三", identity_type="企业领导", visit_date="2026-07-06")
    with pytest.raises(RuntimeError):
        await adapter.generate_welcome(visit)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_adapters_mock.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.adapters.nfc.mock'`

- [ ] **Step 3: Implement**

```python
# backend/app/adapters/nfc/mock.py
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, CardReadEvent, NFCAdapter, WriteResult


class MockNFCAdapter(NFCAdapter):
    def __init__(self) -> None:
        self._read_queue: asyncio.Queue[CardReadEvent] = asyncio.Queue()
        self._written_payloads: dict[str, dict] = {}

    async def write_card(self, card_uid: str, payload: dict) -> WriteResult:
        self._written_payloads[card_uid] = payload
        return WriteResult(success=True, card_uid=card_uid)

    def get_written_payload(self, card_uid: str) -> dict:
        return self._written_payloads[card_uid]

    async def simulate_card_read(self, card_uid: str, raw_payload: dict) -> None:
        await self._read_queue.put(CardReadEvent(card_uid=card_uid, raw_payload=raw_payload))

    async def read_stream(self) -> AsyncIterator[CardReadEvent]:
        while True:
            event = await self._read_queue.get()
            yield event

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
```

```python
# backend/app/adapters/led/mock.py
from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, LEDAdapter, LEDContent


class MockLEDAdapter(LEDAdapter):
    def __init__(self) -> None:
        self.displayed: list[tuple[list[str], LEDContent]] = []
        self.rejected: list[list[str]] = []

    async def display(self, screen_ids: list[str], content: LEDContent) -> None:
        self.displayed.append((screen_ids, content))

    async def show_rejected(self, screen_ids: list[str]) -> None:
        self.rejected.append(screen_ids)

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
```

```python
# backend/app/adapters/tts/mock.py
from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, TTSAdapter


class MockTTSAdapter(TTSAdapter):
    def __init__(self) -> None:
        self.spoken: list[str] = []

    async def enqueue_speech(self, text: str) -> None:
        self.spoken.append(text)

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
```

```python
# backend/app/adapters/ai/mock.py
from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, AIAdapter, VisitInfo


class MockAIAdapter(AIAdapter):
    def __init__(self, raise_error: bool = False) -> None:
        self.raise_error = raise_error
        self.requests: list[VisitInfo] = []

    async def generate_welcome(self, visit: VisitInfo) -> str:
        self.requests.append(visit)
        if self.raise_error:
            raise RuntimeError("mock AI adapter configured to fail")
        return f"{visit.name}，欢迎您（mock-ai）"

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_adapters_mock.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/adapters/nfc/mock.py backend/app/adapters/led/mock.py backend/app/adapters/tts/mock.py backend/app/adapters/ai/mock.py backend/tests/test_adapters_mock.py
git commit -m "feat: add mock NFC/LED/TTS/AI adapters"
```

---

### Task 8: RegistrationService (Excel parse/validate/import)

**Files:**
- Create: `backend/app/services/registration_service.py`
- Test: `backend/tests/test_registration_service.py`

**Interfaces:**
- Consumes: `EventBus` (Task 2), `Visit`/`EntrySource`/`IdentityType`/`VisitStatus` (Task 5).
- Produces: `class RegistrationService(session_factory, event_bus)` with `parse_excel(file_path: str) -> list[ParsedRow]`, `async def import_file(file_path: str, entry_source: EntrySource) -> tuple[str, list[int]]` (returns `(import_batch_id, visit_ids)`), `async def handle_excel_detected(payload: dict) -> None`. Publishes `visit.imported {visit_ids, import_batch_id}`, `welcome.requested {visit_id}` (once per imported visit), and `work_log.append {module, action, status, detail}`. Task 9's `AIWriteupWorker` consumes `welcome.requested`; Task 13's watcher payload (`{"file_path": ...}`) is what `handle_excel_detected` expects.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_registration_service.py
import asyncio

import pandas as pd

from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.visit import EntrySource, Visit, VisitStatus
from app.services.registration_service import RegistrationService


def _fresh_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def _write_fixture_excel(path, rows):
    pd.DataFrame(rows).to_excel(path, index=False)


VALID_ROW = {
    "来访日期": "2026-07-06",
    "计划场次时间": "2026-07-06 10:00",
    "姓名": "张三",
    "手机号": "13800000000",
    "国籍": "中国",
    "身份证号": "110000000000000000",
    "性别": "男",
    "单位": "AITIC",
    "身份": "企业领导",
}


def test_parse_excel_flags_missing_mandatory_field_and_bad_identity(tmp_path):
    path = tmp_path / "visitors.xlsx"
    bad_row = dict(VALID_ROW, 姓名="", 身份="外星人")
    _write_fixture_excel(path, [VALID_ROW, bad_row])

    service = RegistrationService(_fresh_session_factory(), EventBus())
    parsed_rows = service.parse_excel(str(path))

    assert parsed_rows[0].is_valid
    assert not parsed_rows[1].is_valid
    assert "姓名不能为空" in parsed_rows[1].errors
    assert any("身份取值非法" in error for error in parsed_rows[1].errors)


async def test_import_file_commits_valid_rows_and_publishes_events(tmp_path):
    path = tmp_path / "visitors.xlsx"
    bad_row = dict(VALID_ROW, 姓名="")
    _write_fixture_excel(path, [VALID_ROW, bad_row])

    session_factory = _fresh_session_factory()
    event_bus = EventBus()
    imported_queue = event_bus.subscribe("visit.imported")
    requested_queue = event_bus.subscribe("welcome.requested")
    work_log_queue = event_bus.subscribe("work_log.append")

    service = RegistrationService(session_factory, event_bus)
    import_batch_id, visit_ids = await service.import_file(str(path), EntrySource.MANUAL)

    assert len(visit_ids) == 1
    with session_factory() as session:
        visit = session.get(Visit, visit_ids[0])
        assert visit.name == "张三"
        assert visit.status == VisitStatus.PENDING
        assert visit.import_batch_id == import_batch_id

    imported_payload = await asyncio.wait_for(imported_queue.get(), timeout=1)
    assert imported_payload == {"visit_ids": visit_ids, "import_batch_id": import_batch_id}

    requested_payload = await asyncio.wait_for(requested_queue.get(), timeout=1)
    assert requested_payload == {"visit_id": visit_ids[0]}

    statuses = set()
    for _ in range(2):
        entry = await asyncio.wait_for(work_log_queue.get(), timeout=1)
        statuses.add(entry["status"])
    assert statuses == {"warning", "success"}


async def test_handle_excel_detected_imports_the_given_file(tmp_path):
    path = tmp_path / "visitors.xlsx"
    _write_fixture_excel(path, [VALID_ROW])

    session_factory = _fresh_session_factory()
    event_bus = EventBus()
    event_bus.subscribe("visit.imported")
    event_bus.subscribe("welcome.requested")
    event_bus.subscribe("work_log.append")

    service = RegistrationService(session_factory, event_bus)
    await service.handle_excel_detected({"file_path": str(path)})

    with session_factory() as session:
        assert session.query(Visit).filter_by(entry_source=EntrySource.AUTO).count() == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_registration_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.registration_service'`

- [ ] **Step 3: Implement**

```python
# backend/app/services/registration_service.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from app.core.event_bus import EventBus
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus

REQUIRED_COLUMNS = [
    "来访日期",
    "计划场次时间",
    "姓名",
    "手机号",
    "国籍",
    "身份证号",
    "性别",
    "单位",
    "身份",
]
# PLAN DEFAULT: TARGET.md §3.1 lists the fixed header set but doesn't spell out which
# columns are individually mandatory. Minimum viable set for the pipeline to function:
# date+name (needed for on-site verification) and identity (needed for template choice).
MANDATORY_FIELDS = ["来访日期", "计划场次时间", "姓名", "身份"]
VALID_IDENTITIES = {member.value for member in IdentityType}


@dataclass
class ParsedRow:
    row_number: int
    data: dict
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class RegistrationService:
    def __init__(self, session_factory, event_bus: EventBus) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus

    def parse_excel(self, file_path: str) -> list[ParsedRow]:
        frame = pd.read_excel(file_path, dtype=str)
        missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
        if missing:
            raise ValueError(f"表头缺少必填列: {missing}")

        parsed_rows: list[ParsedRow] = []
        for offset, row in enumerate(frame.to_dict(orient="records")):
            row_number = offset + 2  # +2: 1-indexed rows, plus header row
            errors: list[str] = []
            for field_name in MANDATORY_FIELDS:
                value = row.get(field_name)
                if value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == "":
                    errors.append(f"{field_name}不能为空")
            identity = row.get("身份")
            if identity and identity not in VALID_IDENTITIES:
                errors.append(f"身份取值非法: {identity}")
            parsed_rows.append(ParsedRow(row_number=row_number, data=row, errors=errors))
        return parsed_rows

    async def import_file(self, file_path: str, entry_source: EntrySource) -> tuple[str, list[int]]:
        parsed_rows = self.parse_excel(file_path)
        valid_rows = [row for row in parsed_rows if row.is_valid]
        invalid_rows = [row for row in parsed_rows if not row.is_valid]

        import_batch_id = str(uuid.uuid4())
        visit_ids: list[int] = []
        with self._session_factory() as session:
            for row in valid_rows:
                visit = Visit(
                    visit_date=_parse_date(row.data["来访日期"]),
                    session_time=_parse_datetime(row.data["计划场次时间"]),
                    name=row.data["姓名"],
                    phone=row.data.get("手机号"),
                    nationality=row.data.get("国籍"),
                    id_number=row.data.get("身份证号"),
                    gender=row.data.get("性别"),
                    organization=row.data.get("单位"),
                    identity_type=IdentityType(row.data["身份"]),
                    entry_source=entry_source,
                    import_batch_id=import_batch_id,
                    status=VisitStatus.PENDING,
                )
                session.add(visit)
                session.flush()
                visit_ids.append(visit.id)
            session.commit()

        if invalid_rows:
            detail = "; ".join(f"第{row.row_number}行: {','.join(row.errors)}" for row in invalid_rows)
            await self._event_bus.publish(
                "work_log.append",
                {
                    "module": "registration",
                    "action": "import_file",
                    "status": "warning",
                    "detail": f"{len(invalid_rows)} 行校验失败: {detail}",
                },
            )

        if visit_ids:
            await self._event_bus.publish(
                "visit.imported", {"visit_ids": visit_ids, "import_batch_id": import_batch_id}
            )
            for visit_id in visit_ids:
                await self._event_bus.publish("welcome.requested", {"visit_id": visit_id})
            await self._event_bus.publish(
                "work_log.append",
                {
                    "module": "registration",
                    "action": "import_file",
                    "status": "success",
                    "detail": f"批次{import_batch_id}导入{len(visit_ids)}条记录",
                },
            )

        return import_batch_id, visit_ids

    async def handle_excel_detected(self, payload: dict) -> None:
        # PLAN DEFAULT: TARGET.md §3.1 keeps auto-detected files behind the same
        # preview→confirm gate as manual uploads once the UI exists (Day 2/3). Day 1
        # has no UI, so the watcher path auto-commits valid rows directly to prove the
        # full mock pipeline end-to-end, matching 完整实现计划's literal Day-1
        # acceptance test ("扔一个假Excel...完整走完全流程").
        await self.import_file(payload["file_path"], EntrySource.AUTO)


def _parse_date(value: str) -> date:
    return pd.to_datetime(value).date()


def _parse_datetime(value: str) -> datetime:
    return pd.to_datetime(value).to_pydatetime()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_registration_service.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/services/registration_service.py backend/tests/test_registration_service.py
git commit -m "feat: add RegistrationService with shared Excel parser and two-stage-capable import"
```

---

### Task 9: AIWriteupWorker

**Files:**
- Create: `backend/app/services/ai_writeup_service.py`
- Test: `backend/tests/test_ai_writeup_service.py`

**Interfaces:**
- Consumes: `EventBus` (Task 2), `Visit`/`VisitStatus`/`WelcomeSource` and `WelcomeTemplate`/`TemplateIdentityType` (Task 5), `AIAdapter`/`VisitInfo` (Task 6), `MockAIAdapter` (Task 7, used in tests).
- Produces: `class AIWriteupWorker(session_factory, event_bus, ai_adapter)` with `async def handle_welcome_requested(payload: dict) -> None` — subscribes to `welcome.requested {visit_id}` (produced by Task 8), publishes `welcome.generated {visit_id, welcome_text, source}` and `work_log.append`. Task 10's `CardService` consumes `welcome.generated`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_ai_writeup_service.py
import asyncio
from datetime import date, datetime

from app.adapters.ai.mock import MockAIAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus, WelcomeSource
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
            WelcomeTemplate(identity_type=TemplateIdentityType.ENTERPRISE_LEADER, template_text="{姓名}先生/女士，欢迎您")
        )
        session.add(WelcomeTemplate(identity_type=TemplateIdentityType.DEFAULT, template_text="{姓名}，欢迎您"))
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
    worker = AIWriteupWorker(session_factory, event_bus, MockAIAdapter(raise_error=True))

    await worker.handle_welcome_requested({"visit_id": visit_id})

    with session_factory() as session:
        visit = session.get(Visit, visit_id)
        assert visit.welcome_source == WelcomeSource.FALLBACK_TEMPLATE
        assert visit.welcome_text == "张三先生/女士，欢迎您"

    generated_payload = await asyncio.wait_for(generated_queue.get(), timeout=1)
    assert generated_payload["source"] == "fallback_template"

    log_payload = await asyncio.wait_for(work_log_queue.get(), timeout=1)
    assert log_payload["status"] == "warning"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_ai_writeup_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai_writeup_service'`

- [ ] **Step 3: Implement**

```python
# backend/app/services/ai_writeup_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.base import AIAdapter, VisitInfo
from app.core.event_bus import EventBus
from app.models.visit import Visit, VisitStatus, WelcomeSource
from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate


class AIWriteupWorker:
    def __init__(self, session_factory, event_bus: EventBus, ai_adapter: AIAdapter) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._ai_adapter = ai_adapter

    async def handle_welcome_requested(self, payload: dict) -> None:
        visit_id = payload["visit_id"]
        with self._session_factory() as session:
            visit = session.get(Visit, visit_id)
            if visit is None:
                return
            visit_info = VisitInfo(
                visit_id=visit.id,
                name=visit.name,
                identity_type=visit.identity_type.value,
                visit_date=visit.visit_date.isoformat(),
                organization=visit.organization,
            )
            try:
                welcome_text = await self._ai_adapter.generate_welcome(visit_info)
                source = WelcomeSource.AI
                log_status = "success"
                log_detail = f"visit_id={visit_id} AI生成成功"
            except Exception as exc:  # noqa: BLE001 - 降级路径需要捕获任意adapter异常
                welcome_text = self._fallback_text(session, visit)
                source = WelcomeSource.FALLBACK_TEMPLATE
                log_status = "warning"
                log_detail = f"visit_id={visit_id} AI生成失败({exc})，已降级为模板"

            visit.welcome_text = welcome_text
            visit.welcome_source = source
            visit.status = VisitStatus.WELCOME_READY
            session.commit()

        await self._event_bus.publish(
            "welcome.generated",
            {"visit_id": visit_id, "welcome_text": welcome_text, "source": source.value},
        )
        await self._event_bus.publish(
            "work_log.append",
            {"module": "ai_writeup", "action": "generate_welcome", "status": log_status, "detail": log_detail},
        )

    @staticmethod
    def _fallback_text(session: Session, visit: Visit) -> str:
        template = session.execute(
            select(WelcomeTemplate).where(
                WelcomeTemplate.identity_type == TemplateIdentityType(visit.identity_type.value)
            )
        ).scalar_one_or_none()
        if template is None:
            template = session.execute(
                select(WelcomeTemplate).where(WelcomeTemplate.identity_type == TemplateIdentityType.DEFAULT)
            ).scalar_one_or_none()
        text = template.template_text if template else "{姓名}，欢迎您"
        return text.replace("{姓名}", visit.name)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_ai_writeup_service.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/services/ai_writeup_service.py backend/tests/test_ai_writeup_service.py
git commit -m "feat: add AIWriteupWorker with template fallback on AI failure"
```

---

### Task 10: CardService

**Files:**
- Create: `backend/app/services/card_service.py`
- Test: `backend/tests/test_card_service.py`

**Interfaces:**
- Consumes: `EventBus` (Task 2), `Visit`/`VisitStatus` and `NFCWriteLog`/`WriteStatus` (Task 5), `NFCAdapter` (Task 6), `MockNFCAdapter` (Task 7, used in tests).
- Produces: `class CardService(session_factory, event_bus, nfc_adapter)` with `async def handle_welcome_generated(payload: dict) -> None` — subscribes to `welcome.generated` (Task 9), publishes `card.write.completed {visit_id, card_uid, status}` and `work_log.append`. Task 11's `VerifyService`/Task 15's e2e test read the card back via `nfc_adapter.get_written_payload(card_uid)`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_card_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.card_service'`

- [ ] **Step 3: Implement**

```python
# backend/app/services/card_service.py
from __future__ import annotations

from app.adapters.base import NFCAdapter
from app.core.event_bus import EventBus
from app.models.nfc_write_log import NFCWriteLog, WriteStatus
from app.models.visit import Visit, VisitStatus


class CardService:
    def __init__(self, session_factory, event_bus: EventBus, nfc_adapter: NFCAdapter) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._nfc_adapter = nfc_adapter

    async def handle_welcome_generated(self, payload: dict) -> None:
        visit_id = payload["visit_id"]
        with self._session_factory() as session:
            visit = session.get(Visit, visit_id)
            if visit is None:
                return
            # PLAN DEFAULT: real card UIDs only become known once a physical card is
            # presented to the writer (Day 4). For Day 1's mock-driven auto-pipeline,
            # derive a deterministic UID so write/verify can round-trip in tests.
            card_uid = f"MOCK-{visit_id}"
            card_payload = {
                "visit_id": visit.id,
                "name": visit.name,
                "visit_date": visit.visit_date.isoformat(),
                "identity_type": visit.identity_type.value,
                "welcome_text": visit.welcome_text,
            }
            result = await self._nfc_adapter.write_card(card_uid, card_payload)

            session.add(
                NFCWriteLog(
                    visit_id=visit_id,
                    card_uid=result.card_uid,
                    write_status=WriteStatus.SUCCESS if result.success else WriteStatus.FAILED,
                    error_message=result.error_message,
                )
            )
            if result.success:
                visit.status = VisitStatus.CARD_WRITTEN
            session.commit()

        await self._event_bus.publish(
            "card.write.completed",
            {"visit_id": visit_id, "card_uid": card_uid, "status": "success" if result.success else "failed"},
        )
        await self._event_bus.publish(
            "work_log.append",
            {
                "module": "card_write",
                "action": "write_card",
                "status": "success" if result.success else "failure",
                "detail": f"visit_id={visit_id} card_uid={card_uid}",
            },
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_card_service.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/services/card_service.py backend/tests/test_card_service.py
git commit -m "feat: add CardService writing visit+welcome text to NFC card"
```

---

### Task 11: VerifyService

**Files:**
- Create: `backend/app/services/verify_service.py`
- Test: `backend/tests/test_verify_service.py`

**Interfaces:**
- Consumes: `EventBus` (Task 2), `Visit`/`VisitStatus` and `VerifyLog`/`VerifyResult`/`FailReason` (Task 5).
- Produces: `class VerifyService(session_factory, event_bus)` with `async def handle_card_verify_requested(payload: dict) -> None` — expects `{"card_uid": str, "raw_payload": {"visit_id", "name", "visit_date", ...}}` (this exact shape is what Task 13's card-read pump and Task 15's e2e test construct from `MockNFCAdapter.read_stream()`/`CardReadEvent`). Publishes `card.verify.passed {visit_id, card_uid}` or `card.verify.failed {visit_id, card_uid, fail_reason}`, plus `work_log.append`.

- [ ] **Step 1: Write the failing tests**

```python
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
        {"card_uid": "UID-1", "raw_payload": {"visit_id": visit_id, "name": "张三", "visit_date": "2026-07-06"}}
    )

    payload = await asyncio.wait_for(passed_queue.get(), timeout=1)
    assert payload == {"visit_id": visit_id, "card_uid": "UID-1"}
    with session_factory() as session:
        assert session.get(Visit, visit_id).status == VisitStatus.VERIFIED
        assert session.query(VerifyLog).filter_by(visit_id=visit_id).one().verify_result.value == "pass"


async def test_verify_fails_on_name_mismatch():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    failed_queue = event_bus.subscribe("card.verify.failed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {"card_uid": "UID-1", "raw_payload": {"visit_id": visit_id, "name": "李四", "visit_date": "2026-07-06"}}
    )

    payload = await asyncio.wait_for(failed_queue.get(), timeout=1)
    assert payload["fail_reason"] == "name_mismatch"


async def test_verify_fails_on_date_mismatch():
    session_factory, visit_id = _seeded_session_factory()
    event_bus = EventBus()
    failed_queue = event_bus.subscribe("card.verify.failed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {"card_uid": "UID-1", "raw_payload": {"visit_id": visit_id, "name": "张三", "visit_date": "2026-07-07"}}
    )

    payload = await asyncio.wait_for(failed_queue.get(), timeout=1)
    assert payload["fail_reason"] == "date_mismatch"


async def test_verify_fails_when_visit_not_found():
    session_factory, _ = _seeded_session_factory()
    event_bus = EventBus()
    failed_queue = event_bus.subscribe("card.verify.failed")
    service = VerifyService(session_factory, event_bus)

    await service.handle_card_verify_requested(
        {"card_uid": "UID-1", "raw_payload": {"visit_id": 999999, "name": "张三", "visit_date": "2026-07-06"}}
    )

    payload = await asyncio.wait_for(failed_queue.get(), timeout=1)
    assert payload["fail_reason"] == "card_not_found"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_verify_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.verify_service'`

- [ ] **Step 3: Implement**

```python
# backend/app/services/verify_service.py
from __future__ import annotations

from app.core.event_bus import EventBus
from app.models.verify_log import FailReason, VerifyLog, VerifyResult
from app.models.visit import Visit, VisitStatus


class VerifyService:
    def __init__(self, session_factory, event_bus: EventBus) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus

    async def handle_card_verify_requested(self, payload: dict) -> None:
        card_uid = payload["card_uid"]
        raw_payload = payload["raw_payload"]
        visit_id = raw_payload.get("visit_id")

        with self._session_factory() as session:
            visit = session.get(Visit, visit_id) if visit_id is not None else None

            fail_reason: FailReason | None = None
            if visit is None:
                fail_reason = FailReason.CARD_NOT_FOUND
            elif visit.name != raw_payload.get("name"):
                fail_reason = FailReason.NAME_MISMATCH
            elif visit.visit_date.isoformat() != raw_payload.get("visit_date"):
                fail_reason = FailReason.DATE_MISMATCH

            session.add(
                VerifyLog(
                    card_uid=card_uid,
                    visit_id=visit.id if visit else None,
                    verify_result=VerifyResult.FAIL if fail_reason else VerifyResult.PASS,
                    fail_reason=fail_reason,
                )
            )
            if visit and fail_reason is None:
                visit.status = VisitStatus.VERIFIED
            session.commit()

        if fail_reason is None:
            await self._event_bus.publish("card.verify.passed", {"visit_id": visit_id, "card_uid": card_uid})
            log_status, log_detail = "success", f"card_uid={card_uid} visit_id={visit_id} 校验通过"
        else:
            await self._event_bus.publish(
                "card.verify.failed",
                {"visit_id": visit_id, "card_uid": card_uid, "fail_reason": fail_reason.value},
            )
            log_status = "warning"
            log_detail = f"card_uid={card_uid} 校验失败: {fail_reason.value}"

        await self._event_bus.publish(
            "work_log.append",
            {"module": "verify", "action": "verify_card", "status": log_status, "detail": log_detail},
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_verify_service.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/services/verify_service.py backend/tests/test_verify_service.py
git commit -m "feat: add VerifyService comparing card date+name against authoritative visit data"
```

---

### Task 12: LogService

**Files:**
- Create: `backend/app/services/log_service.py`
- Test: `backend/tests/test_log_service.py`

**Interfaces:**
- Consumes: `WorkLog`/`LogModule`/`LogStatus` (Task 5).
- Produces: `class LogService(session_factory)` with `async def handle_work_log_append(payload: dict) -> None` — subscribes to `work_log.append` (published by Tasks 8/9/10/11), persists one `WorkLog` row per call.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_log_service.py
from app.core.db import Base, make_engine, make_session_factory
from app.models.work_log import LogModule, LogStatus, WorkLog
from app.services.log_service import LogService


async def test_handle_work_log_append_persists_a_row():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    service = LogService(session_factory)

    await service.handle_work_log_append(
        {"module": "registration", "action": "import_file", "status": "success", "detail": "批次x导入1条记录"}
    )

    with session_factory() as session:
        row = session.query(WorkLog).one()
        assert row.module == LogModule.REGISTRATION
        assert row.action == "import_file"
        assert row.status == LogStatus.SUCCESS
        assert row.detail == "批次x导入1条记录"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_log_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.log_service'`

- [ ] **Step 3: Implement**

```python
# backend/app/services/log_service.py
from __future__ import annotations

from app.models.work_log import LogModule, LogStatus, WorkLog


class LogService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def handle_work_log_append(self, payload: dict) -> None:
        with self._session_factory() as session:
            session.add(
                WorkLog(
                    module=LogModule(payload["module"]),
                    action=payload["action"],
                    status=LogStatus(payload["status"]),
                    detail=payload.get("detail"),
                )
            )
            session.commit()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_log_service.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/services/log_service.py backend/tests/test_log_service.py
git commit -m "feat: add LogService persisting work_log.append events to work_log table"
```

---

### Task 13: ExcelWatcher

**Files:**
- Create: `backend/app/watchers/excel_watcher.py`
- Test: `backend/tests/test_excel_watcher.py`

**Interfaces:**
- Consumes: `EventBus` (Task 2).
- Produces: `class ExcelWatcher(watch_dir: str, event_bus: EventBus)` with `start() -> None` / `stop() -> None`. Publishes `excel.detected {"file_path": str}` for any new `.xlsx`/`.xls` file — this is exactly the payload shape Task 8's `RegistrationService.handle_excel_detected` expects.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_excel_watcher.py
import asyncio

import pandas as pd

from app.core.event_bus import EventBus
from app.watchers.excel_watcher import ExcelWatcher


async def test_new_excel_file_triggers_excel_detected_event(tmp_path):
    event_bus = EventBus()
    queue = event_bus.subscribe("excel.detected")
    watcher = ExcelWatcher(str(tmp_path), event_bus)
    watcher.start()
    try:
        target = tmp_path / "visitors.xlsx"
        pd.DataFrame([{"a": 1}]).to_excel(target, index=False)

        payload = await asyncio.wait_for(queue.get(), timeout=5)
        assert payload["file_path"] == str(target)
    finally:
        watcher.stop()


async def test_non_excel_file_does_not_trigger_event(tmp_path):
    event_bus = EventBus()
    queue = event_bus.subscribe("excel.detected")
    watcher = ExcelWatcher(str(tmp_path), event_bus)
    watcher.start()
    try:
        (tmp_path / "notes.txt").write_text("hello")
        try:
            await asyncio.wait_for(queue.get(), timeout=1)
            raised = False
        except asyncio.TimeoutError:
            raised = True
        assert raised
    finally:
        watcher.stop()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_excel_watcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.watchers.excel_watcher'`

- [ ] **Step 3: Implement**

```python
# backend/app/watchers/excel_watcher.py
from __future__ import annotations

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.core.event_bus import EventBus


class _NewExcelHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, event_bus: EventBus) -> None:
        self._loop = loop
        self._event_bus = event_bus

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory or not event.src_path.lower().endswith((".xlsx", ".xls")):
            return
        asyncio.run_coroutine_threadsafe(
            self._event_bus.publish("excel.detected", {"file_path": event.src_path}),
            self._loop,
        )


class ExcelWatcher:
    def __init__(self, watch_dir: str, event_bus: EventBus) -> None:
        self._watch_dir = watch_dir
        self._event_bus = event_bus
        self._observer: Observer | None = None

    def start(self) -> None:
        Path(self._watch_dir).mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()
        handler = _NewExcelHandler(loop, self._event_bus)
        self._observer = Observer()
        self._observer.schedule(handler, self._watch_dir, recursive=False)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_excel_watcher.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/watchers/excel_watcher.py backend/tests/test_excel_watcher.py
git commit -m "feat: add watchdog-based ExcelWatcher publishing excel.detected"
```

---

### Task 14: `main.py` wiring — the single startup entry point

**Files:**
- Create: `backend/app/main.py`
- Modify: `backend/main.py` (no change needed — already correct from Task 1, verify only)

**Interfaces:**
- Consumes: everything from Tasks 2-13 by their exact names above.
- Produces: `build_app(settings: Settings | None = None) -> FastAPI` and module-level `app = build_app()`. `app.state.event_bus`, `app.state.session_factory`, `app.state.adapters` (`dict[str, ...]`), `app.state.services` (`dict[str, ...]`) — Day 2's API routes will read these off `request.app.state`. `GET /health` returns `{"status": "ok"}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_main.py
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app


def test_health_endpoint_and_state_are_wired(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    app = build_app(settings)

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        assert set(app.state.adapters) == {"nfc", "led", "tts", "ai"}
        assert set(app.state.services) == {"registration", "ai_writeup", "card", "verify", "log"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Implement**

```python
# backend/app/main.py
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

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
                asyncio.create_task(_consume(event_bus, "excel.detected", registration_service.handle_excel_detected)),
                asyncio.create_task(_consume(event_bus, "welcome.requested", ai_writeup_worker.handle_welcome_requested)),
                asyncio.create_task(_consume(event_bus, "welcome.generated", card_service.handle_welcome_generated)),
                asyncio.create_task(_consume(event_bus, "card.verify.requested", verify_service.handle_card_verify_requested)),
                asyncio.create_task(_consume(event_bus, "work_log.append", log_service.handle_work_log_append)),
                asyncio.create_task(_pump_card_reads(nfc_adapter, event_bus)),
            ]
        )
        excel_watcher.start()
        yield
        excel_watcher.stop()
        for task in background_tasks:
            task.cancel()

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
    fastapi_app.state.adapters = {"nfc": nfc_adapter, "led": led_adapter, "tts": tts_adapter, "ai": ai_adapter}
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
        await handler(payload)


async def _pump_card_reads(nfc_adapter: MockNFCAdapter, event_bus: EventBus) -> None:
    async for event in nfc_adapter.read_stream():
        await event_bus.publish(
            "card.verify.requested", {"card_uid": event.card_uid, "raw_payload": event.raw_payload}
        )


app = build_app()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv add httpx --dev 2>/dev/null; uv run pytest tests/test_main.py -v`
Expected: 1 passed (`httpx` is already a runtime dependency from Task 1, needed by `TestClient`)

- [ ] **Step 5: Run the entire suite so far**

Run: `cd backend && uv run pytest -v`
Expected: all tests from Tasks 2-14 pass

- [ ] **Step 6: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/main.py backend/tests/test_main.py
git commit -m "feat: wire DB, event bus, mock adapters, services and watcher into app.main.build_app"
```

---

### Task 15: End-to-end self-test (today's acceptance criterion)

**Files:**
- Create: `backend/tests/test_end_to_end.py`

**Interfaces:**
- Consumes: `RegistrationService`, `AIWriteupWorker`, `CardService`, `VerifyService`, `LogService` (Tasks 8-12), `MockNFCAdapter`, `MockAIAdapter` (Task 7), `EventBus` (Task 2), `Base`/`make_engine`/`make_session_factory` (Task 4), `seed_default_templates` (Task 5).
- Produces: nothing consumed by later tasks — this is the terminal verification task for Day 1, standing in for 完整实现计划's literal acceptance line: *"往watchdog监听目录扔一个准备好的假Excel，控制台/work_log表里能看到完整走完 登记→AI(mock)→写卡(mock)→校验(mock)→日志 全流程，不报错。"*

- [ ] **Step 1: Write the end-to-end test**

```python
# backend/tests/test_end_to_end.py
import pandas as pd

from app.adapters.ai.mock import MockAIAdapter
from app.adapters.nfc.mock import MockNFCAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.core.seed import seed_default_templates
from app.models.visit import EntrySource, Visit, VisitStatus
from app.models.work_log import WorkLog
from app.services.ai_writeup_service import AIWriteupWorker
from app.services.card_service import CardService
from app.services.log_service import LogService
from app.services.registration_service import RegistrationService
from app.services.verify_service import VerifyService


async def test_full_pipeline_runs_end_to_end_without_error(tmp_path):
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
    log_service = LogService(session_factory)

    welcome_requested_queue = event_bus.subscribe("welcome.requested")
    welcome_generated_queue = event_bus.subscribe("welcome.generated")
    card_write_queue = event_bus.subscribe("card.write.completed")
    verify_passed_queue = event_bus.subscribe("card.verify.passed")
    work_log_queue = event_bus.subscribe("work_log.append")

    # 模拟"值班人员将访客名单Excel放入指定文件夹"这一步产出的文件
    excel_path = tmp_path / "visitors.xlsx"
    pd.DataFrame(
        [
            {
                "来访日期": "2026-07-06",
                "计划场次时间": "2026-07-06 10:00",
                "姓名": "张三",
                "手机号": "13800000000",
                "国籍": "中国",
                "身份证号": "110000000000000000",
                "性别": "男",
                "单位": "AITIC",
                "身份": "企业领导",
            }
        ]
    ).to_excel(excel_path, index=False)

    # 登记
    _, visit_ids = await registration_service.import_file(str(excel_path), EntrySource.MANUAL)
    assert len(visit_ids) == 1
    visit_id = visit_ids[0]

    # AI（mock）生成欢迎词
    await ai_writeup_worker.handle_welcome_requested(await welcome_requested_queue.get())
    welcome_generated_payload = await welcome_generated_queue.get()
    assert welcome_generated_payload["visit_id"] == visit_id

    # 写卡（mock）
    await card_service.handle_welcome_generated(welcome_generated_payload)
    card_write_payload = await card_write_queue.get()
    assert card_write_payload["status"] == "success"

    # 现场刷卡校验（mock：读回写入卡片的内容）
    card_uid = card_write_payload["card_uid"]
    written_payload = nfc_adapter.get_written_payload(card_uid)
    await nfc_adapter.simulate_card_read(card_uid, written_payload)
    card_read_event = await nfc_adapter.read_stream().__anext__()
    await verify_service.handle_card_verify_requested(
        {"card_uid": card_read_event.card_uid, "raw_payload": card_read_event.raw_payload}
    )
    verify_passed_payload = await verify_passed_queue.get()
    assert verify_passed_payload["visit_id"] == visit_id

    # 工作日志：消费本次流程中产生的所有 work_log.append 事件
    while not work_log_queue.empty():
        await log_service.handle_work_log_append(await work_log_queue.get())

    with session_factory() as session:
        visit = session.get(Visit, visit_id)
        assert visit.status == VisitStatus.VERIFIED
        assert session.query(WorkLog).count() >= 3
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_end_to_end.py -v`
Expected: FAIL initially only if any earlier task's file is missing — since Tasks 2-12 are already implemented at this point, this should actually collect and run. If it fails on a real assertion, that's a genuine bug in an earlier task; fix the earlier task's file, not this test.

- [ ] **Step 3: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_end_to_end.py -v`
Expected: 1 passed

- [ ] **Step 4: Run the whole suite as today's final self-check**

Run: `cd backend && uv run pytest -v`
Expected: all tests across every task pass, zero failures/errors

- [ ] **Step 5: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/tests/test_end_to_end.py
git commit -m "test: add end-to-end pipeline test covering 登记→AI→写卡→校验→日志"
```

---

### Task 16 (🟡 P1 — optional, do only if time remains today): Daily SQLite backup via APScheduler

**Files:**
- Create: `backend/app/core/backup.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_backup.py`

**Interfaces:**
- Consumes: nothing from earlier tasks except being wired into `build_app` (Task 14).
- Produces: `backup_database(db_path: str, backup_dir: str, now: datetime | None = None) -> Path`, `schedule_daily_backup(scheduler, db_path: str, backup_dir: str) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_backup.py
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.backup import backup_database, schedule_daily_backup


def test_backup_database_copies_file_with_timestamped_name(tmp_path):
    db_path = tmp_path / "app.db"
    db_path.write_bytes(b"fake-sqlite-bytes")
    backup_dir = tmp_path / "backup"

    destination = backup_database(str(db_path), str(backup_dir), now=datetime(2026, 7, 6, 2, 0, 0))

    assert destination.name == "app_20260706_020000.db"
    assert destination.read_bytes() == b"fake-sqlite-bytes"


def test_schedule_daily_backup_registers_a_2am_cron_job(tmp_path):
    scheduler = BackgroundScheduler()
    schedule_daily_backup(scheduler, str(tmp_path / "app.db"), str(tmp_path / "backup"))

    job = scheduler.get_job("daily_db_backup")
    assert job is not None
    assert isinstance(job.trigger, CronTrigger)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/test_backup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.backup'`

- [ ] **Step 3: Implement**

```python
# backend/app/core/backup.py
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def backup_database(db_path: str, backup_dir: str, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    source = Path(db_path)
    destination_dir = Path(backup_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{source.stem}_{now:%Y%m%d_%H%M%S}{source.suffix}"
    shutil.copy2(source, destination)
    return destination


def schedule_daily_backup(scheduler, db_path: str, backup_dir: str) -> None:
    from apscheduler.triggers.cron import CronTrigger

    scheduler.add_job(
        backup_database,
        trigger=CronTrigger(hour=2, minute=0),
        kwargs={"db_path": db_path, "backup_dir": backup_dir},
        id="daily_db_backup",
        replace_existing=True,
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && uv run pytest tests/test_backup.py -v`
Expected: 2 passed

- [ ] **Step 5: Wire the scheduler into `app/main.py`**

In `backend/app/main.py`, add the import and start/shutdown the scheduler in `lifespan`:

```python
# add near the other imports
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.backup import schedule_daily_backup
```

Inside `build_app`, before `background_tasks: list[asyncio.Task] = []`:

```python
    scheduler = BackgroundScheduler()
    schedule_daily_backup(scheduler, settings.database_url.removeprefix("sqlite:///"), "backup")
```

Inside `lifespan`, right after `excel_watcher.start()`:

```python
        scheduler.start()
```

And right after `excel_watcher.stop()`:

```python
        scheduler.shutdown(wait=False)
```

- [ ] **Step 6: Run the full suite to confirm nothing broke**

Run: `cd backend && uv run pytest -v`
Expected: all tests still pass

- [ ] **Step 7: Commit**

```bash
cd /home/asyncb/Documents/Github/AITIC-reception
git add backend/app/core/backup.py backend/app/main.py backend/tests/test_backup.py
git commit -m "feat: add daily SQLite backup via APScheduler"
```

---

## Non-coding action item for today (not covered by this plan)

完整实现计划 §二.8 flags this as the single highest-risk open question, and it can't be resolved by writing code: **confirm today** (a) the exact NFC reader model and whether it's PC/SC-compatible, and (b) when the Windows test machine will be available — both block Day 4, and the plan warns that nobody will be reachable over the weekend to answer this. This is a question for the supplier/admin contact, not an engineering task — flag it to whoever owns that relationship before end of day.
