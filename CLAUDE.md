# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product Overview

AITIC 展厅智能前台 (AITIC Exhibition Hall Smart Reception) — automates visitor reception in an exhibition hall. Replaces paper-based check-in + handwritten welcome notes + manual sign-holding with a digital pipeline: Excel visitor list → AI welcome text generation → NFC card writing → on-site card verification → LED display + TTS speech → work log archiving.

**Target spec:** `docs/TARGET.md`
**Master plan:** `docs/AITIC展厅_智能前台_完整实现计划_V1.md` (5-day sprint, Days 1–3 done)
**Day completion reports:** `docs/superpowers/completion/`

## Quick Start (both apps)

```bash
# Backend (one terminal)
cd backend && uv run main.py          # → :8000, Swagger UI at /docs

# Frontend (another terminal)
cd frontend && pnpm install           # only first time
cd frontend && pnpm dev                # → :5173 (proxies /api/* and /ws/* to :8000)
```

Then open **http://localhost:5173/** for the UI, or **http://localhost:8000/docs** for the API spec. Stop either server with `Ctrl-C`.

> **Dev-box proxy note:** if `HTTPS_PROXY` is set in the shell to a local SOCKS5 proxy that doesn't actually forward `registry.npmjs.org`, `pnpm install` will fail with TLS handshake errors. **Workaround:** `pnpm config set registry https://registry.npmmirror.com/` (per-user, doesn't enter the repo). See the "Known dev quirks" section below for the matching `httpx[socks]` backend history.

## Commands

### Backend (Python 3.13+, uv)

```bash
cd backend

# Run the FastAPI dev server on :8000 (with auto-reload via uvicorn)
uv run main.py

# Run the full test suite — 73 tests total: 72 pass + 1 documented-acceptable fail
uv run pytest                                        # quiet
uv run pytest -v                                     # verbose listing
uv run pytest tests/test_registration_service.py     # one file
uv run pytest -k test_import_file                    # one test by name
uv run pytest -k "not test_get_work_logs_does_not_leak_unmasked_id_numbers"  # skip the known-red PII guard

# Re-export the OpenAPI snapshot at docs/openapi.json
uv run python -c "import json; from app.main import build_app; \
  json.dump(build_app().openapi(), open('../docs/openapi.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)"

# Add a dependency (uv manages pyproject.toml + uv.lock; never pip/poetry directly)
uv add packagename
```

### Frontend (Node 22+, pnpm 10)

```bash
cd frontend

# Install deps (first time, or after package.json change)
pnpm install

# Dev server (Vite, :5173, proxies /api/* and /ws/* to :8000)
pnpm dev

# Type-check only (fast, no emit)
pnpm exec tsc --noEmit

# Production build → frontend/dist/
pnpm build

# Add a runtime dep
pnpm add packagename
# Add a dev-only dep (type defs, linters, etc.)
pnpm add -D packagename
```

## Architecture (四层架构)

Backend lives under `backend/`, frontend SPA under `frontend/`. The four-layer architecture spans **both** repos:

### Layer 1: Data & Event Layer — `backend/app/core/`

- **SQLite** is the single source of truth. Excel is only an import/export interface. SQLAlchemy 2.0 ORM in `app/core/db.py`.
- **EventBus** (`app/core/event_bus.py`) — in-process async pub/sub over `asyncio.Queue` with string topic names. **Gotcha:** `subscribe(topics)` creates **one** `asyncio.Queue` shared across all topics in the list — so the WS forwarder in `app/api/ws.py` subscribes **per-topic** to recover the topic name.
- **Config** (`app/core/config.py`) — `pydantic-settings` reading `.env`. `settings_override_path` lives at `backend/data/settings_override.json` (gitignored) and is loaded into `app.state` on every `build_app` call.
- **Backup** (`app/core/backup.py`) — APScheduler fires daily at 02:00.
- **Logging** (`app/core/logging.py`) — stdlib logging.

### Layer 2: Integration Adapter Layer — `backend/app/adapters/`

Four abstract adapters in `app/adapters/base.py`:

| Adapter | Abstract methods | Mock today | Real impl |
|---|---|---|---|
| `NFCAdapter` | `write_card`, `read_stream` (AsyncIterator), `health_check` | `MockNFCAdapter` (has `simulate_card_read` for debug, `fail=True` kwarg for failure-path tests) | (pending — Day 4) |
| `LEDAdapter` | `display`, `show_rejected`, `health_check` | `MockLEDAdapter` | (pending — Day 4) |
| `TTSAdapter` | `enqueue_speech`, `health_check` | `MockTTSAdapter` | (pending — Day 4) |
| `AIAdapter` | `generate_welcome`, `health_check` | `MockAIAdapter` | **`QwenAIAdapter`** (`app/adapters/ai/real.py`, OpenAI-compatible DashScope endpoint, selected automatically when `settings.ai_api_key` is set) |

Adapter health is tracked by `AdapterStatusService` upserting the `adapter_status` table keyed on the 30-second `adapter.heartbeat` poller in `app/main.py`.

### Layer 3: Business Service Layer — `backend/app/services/`

Six services, **none imports another** — all inter-service traffic goes through the EventBus:

| Service | Handler(s) | Subscribes to | Publishes |
|---|---|---|---|
| `RegistrationService` | `parse_excel`, `import_file`, `handle_excel_detected` | `excel.detected` | `visit.imported`, `welcome.requested` (one per visit), `work_log.append` |
| `AIWriteupWorker` | `handle_welcome_requested` | `welcome.requested` | `welcome.generated`, `work_log.append` |
| `CardService` | `handle_welcome_generated` | `welcome.generated` | `card.write.completed`, `work_log.append` |
| `LogService` | `handle_work_log_append` | `work_log.append` | (persists to DB) |
| `VerifyService` | `handle_card_verify_requested` | `card.verify.requested` | `card.verify.passed` / `card.verify.failed`, `work_log.append` |
| `AdapterStatusService` | `handle_adapter_heartbeat` | `adapter.heartbeat` | (upserts `adapter_status` row) |

The `ExcelWatcher` (`app/watchers/excel_watcher.py`) uses `watchdog` to publish `excel.detected` for new `.xlsx`/`.xls` files dropped into the watch directory.

### Layer 4: Presentation Layer (shipped)

**Backend (`backend/app/api/`)** — 9 FastAPI routers, 7 Pydantic schema modules, deps helpers:

```
app/api/
├── deps.py         # get_db / get_event_bus / get_services / get_adapters
├── imports.py      # POST /api/import/{preview,commit}  (two-stage)
├── visits.py       # GET/PATCH /api/visits, /summary, /summary/export, /today, /{id}
├── templates.py    # GET/PUT /api/templates[/{identity_type}]      ← Chinese URL segments
├── cards.py        # POST /api/cards/write, GET /api/cards/write-log
├── logs.py         # GET /api/verify-log, /api/work-logs?module=&status=
├── adapters.py     # GET /api/adapters/status
├── settings.py     # GET/PUT /api/settings   (writes data/settings_override.json)
├── debug.py        # POST /api/debug/simulate-card-read   (Mock-only, 400 in real mode)
└── ws.py           # WS /ws/realtime  (forwards card.verify.* + adapter.heartbeat)
```

**Frontend (`frontend/src/`)** — Vite + React 19 + TS 6 SPA, 8 pages, a zustand WS store, an axios API layer:

```
src/
├── api/          # types.ts (Pydantic mirror), client.ts (axios baseURL=/api),
│                 #   queryKeys.ts + 8 endpoint modules: visits/imports/templates/
│                 #   cards/logs/adapters/settings/debug
├── stores/realtimeStore.ts  # zustand, single WebSocket singleton, 20-event ring buffer
├── components/NavLayout.tsx # top nav + <Outlet/>
├── pages/        # DashboardPage / RegistrationPage / SummaryPage /
│                 #   LiveBoardPage / CardManagementPage /
│                 #   TemplatesPage / WorkLogPage / SettingsPage
├── App.tsx       # QueryClientProvider + RouterProvider + useEffect(connect)
└── router.tsx    # createBrowserRouter, 8 routes under NavLayout
```

Vite dev server proxies `/api/*` and `/ws/*` to `http://localhost:8000` — no CORS in dev, no code change to ship.

## REST + WebSocket contract

Full source of truth: `docs/openapi.json` (snapshot of `app.openapi()` post-Day 2 Task 14). Key shapes:

- **`VisitOut.id_number`** is **always masked** server-side by `mask_id_number` in `app/schemas/visit.py` (first 3 + 7 asterisks + last 4; passthrough if `<7` chars). Frontend treats it as display text.
- **`SettingsOut.has_ai_api_key: bool`** — the raw `ai_api_key` is **never** in the response (PII per `docs/TARGET.md` §六.2).
- **`PUT /api/templates/{identity_type}`** — the path segment is the raw Chinese enum value (`企业领导`, `默认`, etc.), URL-encoded by the frontend.
- **`ws/realtime` message shape** (per `docs/AITIC展厅_智能前台_完整实现计划_V1.md` §4.5):
  ```json
  {"type": "card.verify.passed", "timestamp": "<ISO-8601>", "payload": {"visit_id": 1, "card_uid": "MOCK-1"}}
  ```
  Three topics only: `card.verify.passed`, `card.verify.failed`, `adapter.heartbeat`.

## Pipeline Event Flow

```
Excel file detected  → excel.detected          → RegistrationService.import_file
                     → visit.imported          (in-event for AI+Log)
                     → welcome.requested (×N)  → AIWriteupWorker → welcome.generated
                                                                  → CardService → card.write.completed
NFC card read (real or simulated) → card.verify.requested
                                  → VerifyService → card.verify.{passed,failed}
                                                                    → WS push to /ws/realtime

Every step also publishes work_log.append → LogService persists.
Every 30s: _poll_adapter_heartbeats → adapter.heartbeat → AdapterStatusService + WS push.
```

## Data Models (`backend/app/models/`)

Six SQLAlchemy ORM models, all inheriting from `app.core.db.Base`:

- **Visit** — core entity, status machine: `PENDING → WELCOME_READY → CARD_WRITTEN → VERIFIED | REJECTED`
- **WelcomeTemplate** — 7 rows seeded by `app/core/seed.py` (6 identities + `默认`)
- **NFCWriteLog** — every card write attempt
- **VerifyLog** — every on-site card verification
- **WorkLog** — cross-module audit log
- **AdapterStatusRow** — heartbeat tracking, `adapter_name` is the PK (max 16 chars, fits `nfc/led/tts/ai`)

`id_number` is a sensitive field per `docs/TARGET.md` §六.2 — see the masking rule in §"REST + WebSocket contract" above.

## Wiring — `backend/app/main.py`

`build_app(settings: Settings | None = None)` is the composition root. It (1) merges any `data/settings_override.json` over the Pydantic settings, (2) builds engine + session_factory + seeds `WelcomeTemplate`, (3) constructs `EventBus` + 4 adapters (4 mock or 3 mock + `QwenAIAdapter` if a key is configured) + 6 services + `ExcelWatcher` + APScheduler, (4) wires 8 background tasks in the FastAPI lifespan (5 service-event consumers + `adapter.heartbeat` consumer + card-read pump + heartbeat poller). The lifespan also starts/stops the watcher and scheduler cleanly.

Exposes `app.state.{event_bus, session_factory, settings, settings_override_path, adapters, services}`. Routes read these via `app/api/deps.py`.

**Module-level uvicorn shim:** `__getattr__` lazily builds `app` on first access (uvicorn imports `app.main:app`). Tests import `build_app` directly without triggering the global singleton.

## Project File Layout

```
AITIC-reception/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, DB, EventBus, Logging, Backup, Seed, settings_store
│   │   ├── models/         # 6 SQLAlchemy ORM models
│   │   ├── schemas/        # 7 Pydantic modules (visit/template/card/log/adapter/settings + __init__)
│   │   ├── services/       # 6 business services
│   │   ├── adapters/       # 4 abstract + 4 mock + 1 real (QwenAIAdapter)
│   │   ├── api/            # 10 FastAPI files (deps + 9 routers incl. ws)
│   │   ├── watchers/       # ExcelWatcher (watchdog)
│   │   └── main.py         # build_app composition root + uvicorn shim
│   ├── data/               # SQLite DB + backups + settings_override.json + pending_imports/  (gitignored)
│   ├── fixtures/           # sample_visitors.xlsx + generator script  (committed)
│   ├── tests/              # 27 test files, 73 tests total
│   ├── pyproject.toml
│   └── main.py             # uvicorn entrypoint
├── frontend/
│   ├── src/                # api/ stores/ components/ pages/ + App + router + main
│   ├── vite.config.ts      # /api + /ws proxy to :8000
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   ├── TARGET.md                                  # product spec (source of truth)
│   ├── AITIC展厅_智能前台_完整实现计划_V1.md       # master 5-day plan
│   ├── openapi.json                               # Day 2 snapshot, regenerated by the command in §Commands
│   └── superpowers/
│       ├── plans/                                 # one .md per day (executable plans)
│       ├── completed/                             # day1 only (was the Day 1 completion report)
│       └── completion/                            # day-end reports with commit SHAs + verification results
├── CLAUDE.md                                      # this file
└── README.md
```

## Test Patterns

### Backend

- In-memory SQLite per test (`sqlite:///:memory:`), each test makes its own engine + session_factory. Day-2 intent was "no test pollutes another"; Day 14 added `tests/conftest.py` with an autouse fixture that wipes `data/settings_override.json` between tests to handle a state-leak in `build_app`.
- `EventBus()` is per-test — subscribe with the topic strings from §"Pipeline Event Flow".
- All async tests run via `pytest-asyncio` with `asyncio_mode = "auto"`.
- The end-to-end test `tests/test_end_to_end.py` exercises import → AI → write → verify → log with real services on an in-memory DB.
- `tests/test_fixture_pipeline.py` adds a Day-2 layer: load `fixtures/sample_visitors.xlsx` and run it through 3 event-driven services.
- Mock adapters (`MockAIAdapter`, `MockNFCAdapter`, etc.) — `MockNFCAdapter(fail=True)` is the failure-injection switch.

### Frontend

There is **no frontend test runner** (Day 3 plan §Global Constraints, deliberate). Verification per task is `pnpm exec tsc --noEmit` (type safety) + `pnpm build` (production bundling) + a headless `curl` walkthrough against the dev server. Real browser testing is on Day 5 polish.

## Known dev quirks (worth knowing before you make changes)

1. **`asyncio.Queue` binds to its constructing event loop.** `MockNFCAdapter._read_queue` is built inside `build_app`, which runs in the test client's event loop. Do not try to drain it from a different loop with `asyncio.run(anext(...))` — you'll hit `RuntimeError: <Queue> is bound to a different event loop`. Inspect via `qsize()` (thread-safe, loop-agnostic) or bridge via `anyio.from_thread.run` if you need to publish into the lifespan loop.

2. **`EventBus.subscribe(["a", "b", "c"])` shares ONE queue.** The forwarder at `app/api/ws.py` subscribes per-topic so it can put the topic name in the WS `type` field. If you add a new WS topic, add a per-topic subscription in `ws.py` — don't share.

3. **`MockAIAdapter` already has `simulate_card_read`** (Day 1 method). Day 2 Task 13's debug endpoint calls it; Task 2 added a separate `fail=True` kwarg to `MockNFCAdapter.__init__`. Two independent additions — don't conflate them.

4. **`QwenAIAdapter(api_key=settings.ai_api_key) if settings.ai_api_key else MockAIAdapter()`** is order-of-evaluation fragile. Python evaluates the `QwenAIAdapter(...)` constructor (and its inner `httpx.AsyncClient()`) **before** the ternary picks a branch. On dev boxes with `HTTPS_PROXY=socks5://...`, this crashes at import-time even when `ai_api_key=""`. **Fix used:** `pyproject.toml` declares `httpx[socks]>=0.28.1`. **Cleaner refactor for Day 4:** wrap in an explicit `if settings.ai_api_key:` block.

5. **Dev proxy breaks npm.** `HTTPS_PROXY=http://127.0.0.1:7897` (SOCKS5-on-localhost) drops the TLS handshake to `registry.npmjs.org`. Per-user `pnpm config set registry https://registry.npmmirror.com/` is the working config on this box. **Not in the repo** — it's a per-machine quirk. Same root cause as item 4.

6. **`tests/conftest.py` autouse fixture clears `data/settings_override.json`.** Any test that imports `build_app` (transitively, via `from app.main import build_app`) will load that file. If you write a new test that uses overrides, set the file path yourself or you'll race the autouse cleanup.

7. **`/api/visits/summary` route order matters.** `/summary`, `/summary/export`, `/today` MUST be declared before `/{visit_id}` in `app/api/visits.py` or FastAPI will route `/summary` to `get_visit(visit_id="summary")`. The plan enforces this; preserve it.

8. **The 1 red test (`tests/test_api_logs.py::test_get_work_logs_does_not_leak_unmasked_id_numbers`) is intentional.** It deliberately seeds a leak row in `work_log.detail` to assert that no future service regresses on the PII rule. It will fail as long as that leak row exists in the test. Acceptable per Day 2 + Day 3 reports. Skip with `-k "not test_get_work_logs_does_not_leak_unmasked_id_numbers"` if you need full green.

## Day 4 hand-off (硬件接入 — highest-risk day per the master plan)

- All 4 mock adapters have abstract base interfaces. Replace one at a time; keep the mock for tests.
- `MockNFCAdapter.simulate_card_read` is the in-test cheat used by `/api/debug/simulate-card-read`. Drop it in the real NFC adapter.
- The `MockNFCAdapter(fail=True)` failure-injection kwarg is **only in the mock** — the real adapter should propagate `WriteResult(success=False, ...)` on hardware errors naturally.
- The frontend already covers the full happy + rejection paths via the LiveBoard page (with the `visit_id` field added in `a709350`). No frontend changes expected.
- Check `docs/superpowers/completion/` for the before-state and what shipped per day.
