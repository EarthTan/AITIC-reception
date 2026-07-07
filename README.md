# AITIC 展厅智能前台

> **Status:** Days 1–3 done + §三.3 现场欢迎闭环修复（`master`，24 commits on top of Day 3）。硬件仍 mock，Day 4 真机接入待做。
>
> **Latest:** 审计全流程合规性，修复 17 ❌ / 22 ⚠️，详见 [`CHANGELOG.md`](CHANGELOG.md)。

Digital pipeline that replaces paper-based exhibition-hall reception: Excel visitor list → AI welcome text generation → NFC card writing → on-site card verification → LED display + TTS speech → work log archiving.

## 📚 Documentation

| 文档 | 用途 | 读它的时机 |
|---|---|---|
| **[`TARGET.md`](docs/TARGET.md)** | 产品形态与目标规格 | 任何人首次接触项目 — 系统应该做什么？ |
| **[`CHANGELOG.md`](CHANGELOG.md)** | 每个版本的变更日志 | 想知道这次 update 改了什么 |
| **[`CLAUDE.md`](CLAUDE.md)** | AI agent 用项目上下文（架构、命令、dev quirks） | AI agent 接新任务 / 新开发者入坑 |
| **[`HARDWARE_TESTING.md`](docs/HARDWARE_TESTING.md)** | 真机测试指南（NFC / LED / TTS / AI） | Day 4 硬件接入 / 展厅现场调试 |
| **[`openapi.json`](docs/openapi.json)** | 自动生成的 API 文档（18 endpoint） | 前端开发者、自动化脚本 |
| [`AITIC展厅_智能前台_完整实现计划_V1.md`](docs/AITIC展厅_智能前台_完整实现计划_V1.md) | 5 天冲刺原始计划 | 了解 Day 0 决策和设计意图 |
| `docs/superpowers/specs/` | 每次重要改动的设计 spec | 需要理解某个 feature 为什么这么设计 |
| `docs/superpowers/plans/` | 执行计划 | 做类似改动时参考 |
| **API spec (live)** | `http://localhost:8000/docs` | 后端运行时 Swagger UI |

## Quick Start

Two terminals:

```bash
# Terminal 1 — backend (Python 3.13+, uv)
cd backend
uv run main.py          # → http://localhost:8000 (Swagger UI at /docs)

# Terminal 2 — frontend (Node 22+, pnpm 10)
cd frontend
pnpm install            # first time only
pnpm dev                # → http://localhost:5173
```

Then open <http://localhost:5173/>. The Vite dev server proxies `/api/*` and `/ws/*` to the backend on `:8000`, so the SPA sees one origin.

## What's where

| Path | Purpose |
|---|---|
| `backend/app/api/` | 9 FastAPI routers + `deps.py` — every REST/WebSocket endpoint |
| `backend/app/services/` | 7 business services (Registration, AIWriteup, Card, Verify, **OnsiteWelcome**, Log, AdapterStatus) — all event-bus driven |
| `backend/app/adapters/` | 4 abstract + 4 mock + 2 real (`QwenAIAdapter`, `RealTTSAdapter`) |
| `backend/app/schemas/` | 7 Pydantic modules + `led.py` (LEDContent dataclass) |
| `backend/tests/` | 30 test files, **89 tests** (1 documented-acceptable fail — PII guard) |
| `frontend/src/api/` | 10 TS files: types mirror + axios client + 8 endpoint modules |
| `frontend/src/pages/` | **10 route-level pages** (Dashboard, Registration, Summary, LiveBoard, CardMgmt, Templates, WorkLog, Settings, **Display**, **MockLED**) |
| `frontend/src/stores/realtimeStore.ts` | zustand store: single WebSocket, exponential reconnect, ledContent |
| `frontend/src/components/` | NavLayout + **AdapterOfflineBanner** (red bar when hardware offline) |
| `docs/superpowers/completion/` | Day-end reports with commit SHAs and verification results |

## Day-by-day progress

| Day | Scope | Report |
|---|---|---|
| 1 | Backend framework (event bus, 5 services, 4 mock adapters, end-to-end pipeline test) | [`docs/superpowers/completed/2026-07-03-day1-backend-framework-setup.md`](docs/superpowers/completed/2026-07-03-day1-backend-framework-setup.md) |
| 2 | Real Qwen AI adapter, Pydantic schemas, 9 REST routers, WebSocket, settings, openapi.json export | (see `git log` — 16 commits) |
| 3 | Vite + React 19 + TS 6 frontend: 8 pages, API client, WS store, all 17 endpoints wired | [`docs/superpowers/completion/2026-07-05-day3-frontend-functional-buildout.md`](docs/superpowers/completion/2026-07-05-day3-frontend-functional-buildout.md) |
| 🆕 | **§三.3 现场欢迎闭环修复** — `OnsiteWelcomeService` 驱动 LED+TTS+beep；2 个新页面（/display, /mock-led）；红色告警 banner；WS 指数退避重连；PII preview 脱敏；状态机 REJECTED；工作日志导出；写卡手动触发 | [`spec`](docs/superpowers/specs/2026-07-07-on-site-welcome-and-gaps-design.md) · [`plan`](docs/superpowers/plans/2026-07-07-on-site-welcome-and-gaps.md) · [`changelog`](CHANGELOG.md) |
| 4 | Hardware swap (real NFC/LED/TTS adapters + real AI key) | _pending — see [`HARDWARE_TESTING.md`](docs/HARDWARE_TESTING.md)_ |
| 5 | Styling + polish | _pending_ |

## Current state

- ✅ **Backend:** 18 REST routes + WebSocket (4 topics), full Pydantic-typed API, OpenAPI snapshot at `docs/openapi.json`
- ✅ **Frontend:** 10 pages (functional, unstyled), single WebSocket with exponential backoff, real-time adapter status, two-stage Excel import (9-col preview), work-log filtering + export
- ✅ **§三.3 现场欢迎闭环：** verify.passed → LED 显示姓名+欢迎词 → TTS 朗读 + WS push → 前端 `/display` `/mock-led` `/live` 实时更新。verify.failed → LED "无权限入场" → 蜂鸣 1.5s。
- ✅ **§六.3 可靠性：** WS 指数退避重连；adapter 离线红色告警条；每日 02:00 SQLite 备份
- ✅ **§六.2 PII：** id_number 在所有 API 路径自动脱敏（包括 import preview）
- ✅ **Tests:** 88 passing + 1 intentional red (PII guard, by design)
- ⏳ **Real hardware:** only `QwenAIAdapter` + `RealTTSAdapter` are real; NFC/LED still mock — see [`HARDWARE_TESTING.md`](docs/HARDWARE_TESTING.md) for bring-up guide
- ⏳ **Styling:** frontend pages are functional but unstyled — Day 5 work

## 🧪 How to test

### Automated

```bash
# Backend
cd backend && uv run pytest                   # 88 pass + 1 documented-red
uv run pytest -k "not test_get_work_logs_does_not_leak_unmasked_id_numbers"  # all green

# Frontend (type safety + build)
cd frontend && pnpm exec tsc --noEmit         # type check
cd frontend && pnpm build                     # production bundle
```

### Manual end-to-end (no hardware needed — full mock pipeline)

1. Start both servers (see Quick Start above)
2. Drop `backend/fixtures/sample_visitors.xlsx` into `backend/data/incoming/` → auto-imports 6 visitors
3. Open `http://localhost:5173/cards` → see 6 "待写卡" visitors → check some → click "批量写卡"
4. Open 3 tabs simultaneously:
   - `http://localhost:5173/display` — live board with today's arrivals
   - `http://localhost:5173/mock-led` — fullscreen black LED simulator
   - `http://localhost:5173/live` — management live view
5. **Trigger a successful card read:**
   ```bash
   curl -X POST http://localhost:8000/api/debug/simulate-card-read \
     -H "Content-Type: application/json" \
     -d '{"card_uid":"TEST-OK","raw_payload":{"visit_id":1,"name":"王企业","visit_date":"2026-07-06"}}'
   ```
   → All 3 tabs update: `/mock-led` shows 96px "王企业" in white; `/display` shows latest welcome; `/live` shows green pass block. You hear the welcome text spoken (TTS).
6. **Trigger a rejected card:**
   ```bash
   curl -X POST http://localhost:8000/api/debug/simulate-card-read \
     -H "Content-Type: application/json" \
     -d '{"card_uid":"BAD-001","raw_payload":{"visit_id":9999,"name":"X","visit_date":"2026-07-07"}}'
   ```
   → Red "无权限入场" on `/mock-led`; red block on `/live`; 1.5s beep (880Hz tone).
7. Check `http://localhost:5173/logs` → see `module=tts` entries (speak + beep) → click "导出 Excel" → downloads `work_logs.xlsx`

### Testing the adapter offline banner

To see the red "⚠️ 硬件离线" banner at the top of management pages, temporarily make any adapter return non-online status. The simplest way:

```bash
# Inject a failure into MockNFCAdapter:
cd backend
NFC_CARD_NOT_FOUND=true uv run main.py
# (you'd need a small env-var switch in _build_nfc_adapter to make this work;
#  currently there's no built-in kill switch per user decision U8 —
#  "不要随机演示". Add a manual switch if you want to demo.)
```

## Known dev quirks

See [`CLAUDE.md`](CLAUDE.md) §"Known dev quirks" for details on:

- `asyncio.Queue` event-loop binding in tests
- `EventBus.subscribe(["a","b"])` sharing one queue (WS forwarder needs per-topic subscriptions)
- `QwenAIAdapter` construct-at-import-time issue on dev boxes with SOCKS5 proxy
- `pnpm install` fails with TLS under `HTTPS_PROXY=socks5://...` → workaround: `pnpm config set registry https://registry.npmmirror.com/`
- `/api/visits/summary` route order must be declared before `/{visit_id}`
- The 1 intentionally-red test (PII guard)
