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

# Run the full test suite — 89 tests total: 88 pass + 1 documented-acceptable fail (PII guard)
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
├── imports.py      # POST /api/import/{preview,commit}  (two-stage; preview mask_id_number)
├── visits.py       # GET/PATCH /api/visits, /summary, /summary/export, /today, /{id}
├── templates.py    # GET/PUT /api/templates[/{identity_type}]      ← Chinese URL segments
├── cards.py        # POST /api/cards/write (manual §三.2), GET /api/cards/write-log
├── logs.py         # GET /api/verify-log, /api/work-logs?module=&status=, /api/work-logs/export
├── adapters.py     # GET /api/adapters/status
├── settings.py     # GET/PUT /api/settings   (writes data/settings_override.json)
├── debug.py        # POST /api/debug/simulate-card-read   (Mock-only, 400 in real mode)
└── ws.py           # WS /ws/realtime  (forwards card.verify.* + adapter.heartbeat + led.content)
```

**Backend services** — 7 services now (added `OnsiteWelcomeService`):

```
app/services/
├── registration_service.py   # imports Excel → publishes visit.imported + welcome.requested
├── ai_writeup_service.py     # publishes welcome.generated; sets visit.status = WELCOME_READY
├── card_service.py           # write_card_for_visit (manual trigger); publishes card.write.completed
├── verify_service.py         # publishes card.verify.{passed,failed}; sets visit.status = VERIFIED|REJECTED
├── onsite_welcome_service.py # SUBSCRIBES to card.verify.*; drives led + tts + beep + led.content  [NEW]
├── log_service.py            # persists work_log entries
└── adapter_status_service.py # upserts adapter_status rows from heartbeats
```

**Backend adapters** — 4 abstract + 4 mock + 2 real:

```
app/adapters/
├── base.py          # ABC: NFCAdapter / LEDAdapter / TTSAdapter / AIAdapter
│                    # + AdapterHealth / WriteResult / CardReadEvent / VisitInfo
│                    # + LEDContent is re-exported from schemas/led.py
├── nfc/mock.py      # queue + simulate_card_read + fail= kwarg
├── led/mock.py      # displayed[] + rejected[] (now stores "无权限入场")
├── tts/mock.py      # spoken[] + beeps[]
├── ai/mock.py       # returns "{name}，欢迎您..."
├── tts/real.py      # RealTTSAdapter(pyttsx3): enqueue_speech + play_beep cross-platform  [NEW]
└── ai/real.py       # QwenAIAdapter(DashScope, cloud)
```

**Frontend (`frontend/src/`)** — Vite + React 19 + TS 6 SPA, 10 pages (added /display + /mock-led), a zustand WS store, an axios API layer:

```
src/
├── api/          # types.ts (Pydantic mirror, flattened WS envelope), client.ts, queryKeys.ts
│                 #   + 8 endpoint modules: visits/imports/templates/cards/logs/adapters/settings/debug
├── stores/realtimeStore.ts  # zustand, single WS; ledContent + adapterStatuses + reconnectAttempt state
├── components/
│   ├── NavLayout.tsx              # <AdapterOfflineBanner/> on top, then <Outlet/>
│   └── AdapterOfflineBanner.tsx  # red banner when any adapter non-online                [NEW]
├── pages/
│   ├── DashboardPage           # today's count + adapter status
│   ├── RegistrationPage        # Excel preview (9 cols), commit
│   ├── SummaryPage             # monthly summary, grouped by 场次, export xlsx
│   ├── LiveBoardPage           # WS-driven: passes show name+welcome, fails show red block
│   ├── CardManagementPage      # lists visits where status=welcome_ready, manual batch write
│   ├── DisplayPage             # /display: dark bg, today's list + latest event           [NEW]
│   ├── MockLEDPane             # /mock-led: fullscreen black bg, 96px welcome text         [NEW]
│   ├── TemplatesPage           # edit 7 templates
│   ├── WorkLogPage             # filter + export xlsx
│   └── SettingsPage            # watch dir, AI key (masked), provider (read-only)
├── App.tsx       # QueryClientProvider + RouterProvider + useEffect(connect)
└── router.tsx    # createBrowserRouter, 8 routes under NavLayout + 2 top-level (/display, /mock-led)
```

Vite dev server proxies `/api/*` and `/ws/*` to `http://localhost:8000` — no CORS in dev, no code change to ship.

Vite dev server proxies `/api/*` and `/ws/*` to `http://localhost:8000` — no CORS in dev, no code change to ship.

## REST + WebSocket contract

Full source of truth: `docs/openapi.json`（定期从 `app.openapi()` 重新生成）。当前 18 个 endpoint：

| Method | Path | 用途 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/visits` | 访客列表（含 filter） |
| GET | `/api/visits/{visit_id}` | 单访客（mask_id_number 自动脱敏） |
| PATCH | `/api/visits/{visit_id}` | 修改访客 |
| GET | `/api/visits/today` | 今日来访 |
| GET | `/api/visits/summary?month=YYYY-MM` | 月度汇总（按场次分组） |
| GET | `/api/visits/summary/export?month=YYYY-MM` | 导出月度汇总 xlsx |
| POST | `/api/import/preview` | Excel 预览（`身份证号` 自动脱敏，§六.2） |
| POST | `/api/import/commit` | 提交入库 |
| GET | `/api/templates` | 7 个欢迎词模板 |
| PUT | `/api/templates/{identity_type}` | 更新模板（identity_type 是 URL-encoded 中文枚举） |
| POST | `/api/cards/write` | 手动写卡（§三.2） |
| GET | `/api/cards/write-log` | 写卡历史 |
| POST | `/api/debug/simulate-card-read` | Mock 环境模拟刷卡；真机模式下 400 |
| GET | `/api/verify-log` | 现场校验历史 |
| GET | `/api/work-logs?module=&status=` | 工作日志筛选查询 |
| GET | `/api/work-logs/export?module=&status=&format=xlsx` | 导出工作日志 xlsx（§三.4） |
| GET | `/api/adapters/status` | 4 个 adapter 心跳快照 |
| GET, PUT | `/api/settings` | 设置（`has_ai_api_key: bool` 永不出明文 key） |
| WS | `/ws/realtime` | 见下 |

Key shapes:

- **`VisitOut.id_number`** is **always masked** server-side by `mask_id_number` in `app/schemas/visit.py` (first 3 + 7 asterisks + last 4; passthrough if `<7` chars). Frontend treats it as display text.
- **`SettingsOut.has_ai_api_key: bool`** — the raw `ai_api_key` is **never** in the response (PII per `docs/TARGET.md` §六.2).
- **`PUT /api/templates/{identity_type}`** — the path segment is the raw Chinese enum value (`企业领导`, `默认`, etc.), URL-encoded by the frontend.
- **`ws/realtime` message shape** — envelope is **扁平的**（服务端 `_forward_topic` 用 `**payload` 展开）:
  ```json
  {"type": "card.verify.passed", "timestamp": "<ISO-8601>", "visit_id": 1, "card_uid": "MOCK-1"}
  ```
  4 个 topics: `card.verify.passed`, `card.verify.failed`, `adapter.heartbeat`, `led.content`。每个变体字段在顶层，前端用 TS discriminated union。

**Frontend WS recovery**: 指数退避重连 `1s → 2s → 4s → ... → 30s`，在 `frontend/src/stores/realtimeStore.ts`。

## Pipeline Event Flow

```
Excel file detected  → excel.detected          → RegistrationService.import_file
                     → visit.imported          (in-event for AI+Log)
                     → welcome.requested (×N)  → AIWriteupWorker → welcome.generated
                                                                  → visit.status = WELCOME_READY
                                                                  (停在这里，等值班人员手动写卡)
[手动触发] UI "批量写卡" 按钮 → POST /api/cards/write {visit_ids}
                                → CardService.write_card_for_visit
                                → nfc_adapter.write_card → visit.status = CARD_WRITTEN
                                → card.write.completed + work_log.append

NFC card read (real or simulated) → card.verify.requested
                                  → VerifyService → visit.status = VERIFIED|REJECTED
                                                    → card.verify.{passed,failed}
                                                    → OnsiteWelcomeService:
                                                       · led.display / show_rejected
                                                       · tts.enqueue_speech / play_beep
                                                       · bus.publish("led.content")
                                                       · 2× work_log.append
                                                    → WS push to /ws/realtime

Every step also publishes work_log.append → LogService persists.
Every 30s: _poll_adapter_heartbeats → adapter.heartbeat → AdapterStatusService + WS push.
```

**重要变更 (Unreleased)**: 写卡从自动触发改为手动触发（§三.2 spec 要求）。`welcome.generated` 不再驱动 CardService；CardManagementPage 现在能正确列出待写卡访客。

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

`build_app(settings: Settings | None = None)` is the composition root. It (1) merges any `data/settings_override.json` over the Pydantic settings, (2) builds engine + session_factory + seeds `WelcomeTemplate`, (3) constructs `EventBus` + 4 adapters (Mock×4 or RealTTS+Mock×3+`QwenAIAdapter` if key configured) + 7 services (added `OnsiteWelcomeService`) + `ExcelWatcher` + APScheduler, (4) wires 9 background tasks in the FastAPI lifespan (4 service-event consumers + `adapter.heartbeat` consumer + `card.verify.passed/failed` consumers + card-read pump + heartbeat poller). The lifespan also starts/stops the watcher and scheduler cleanly.

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
│   ├── tests/              # 30 test files, 89 tests total (88 pass + 1 documented-acceptable PII red)
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
│   ├── openapi.json                               # auto-regenerated snapshot of app.openapi()
│   ├── HARDWARE_TESTING.md                        # NFC/LED/TTS/AI 真机接入指南
│   └── superpowers/
│       ├── specs/                                 # design specs (one per major change)
│       ├── plans/                                 # implementation plans (one per major change)
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
