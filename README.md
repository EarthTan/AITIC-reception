# AITIC 展厅智能前台

> **Status:** Days 1–3 done (51 commits on `master`). Day 4 = hardware swap; Day 5 = styling.
> See `docs/superpowers/completion/` for day-end reports.

Digital pipeline that replaces paper-based exhibition-hall reception: Excel visitor list → AI welcome text generation → NFC card writing → on-site card verification → LED display + TTS speech → work log archiving.

- **Product spec:** [`docs/TARGET.md`](docs/TARGET.md) — what the finished system does
- **Master plan:** [`docs/AITIC展厅_智能前台_完整实现计划_V1.md`](docs/AITIC展厅_智能前台_完整实现计划_V1.md) — 5-day sprint breakdown
- **For AI agents:** [`CLAUDE.md`](CLAUDE.md) — project context, commands, architecture, dev quirks
- **API spec (live):** `http://localhost:8000/docs` after running the backend

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
| `backend/app/services/` | 6 business services (Registration, AIWriteup, Card, Verify, Log, AdapterStatus) — all event-bus driven |
| `backend/app/adapters/` | 4 abstract + 4 mock + 1 real (`QwenAIAdapter`) |
| `backend/app/schemas/` | 7 Pydantic modules (request/response shapes, mirroring the OpenAPI spec) |
| `backend/tests/` | 27 test files, 73 tests (1 documented-acceptable fail — PII guard) |
| `frontend/src/api/` | 10 TS files: types mirror + axios client + 8 endpoint modules |
| `frontend/src/pages/` | 8 route-level pages (Dashboard, Registration, Summary, LiveBoard, CardMgmt, Templates, WorkLog, Settings) |
| `frontend/src/stores/realtimeStore.ts` | zustand store holding the single WebSocket connection |
| `docs/superpowers/completion/` | Day-end reports with commit SHAs and verification results |

## Day-by-day progress

| Day | Scope | Report |
|---|---|---|
| 1 | Backend framework (event bus, 5 services, 4 mock adapters, end-to-end pipeline test) | [`docs/superpowers/completed/2026-07-03-day1-backend-framework-setup.md`](docs/superpowers/completed/2026-07-03-day1-backend-framework-setup.md) |
| 2 | Real Qwen AI adapter, Pydantic schemas, 9 REST routers, WebSocket, settings, openapi.json export | (see `git log` — 16 commits) |
| 3 | Vite + React 19 + TS 6 frontend: 8 pages, API client, WS store, all 17 endpoints wired | [`docs/superpowers/completion/2026-07-05-day3-frontend-functional-buildout.md`](docs/superpowers/completion/2026-07-05-day3-frontend-functional-buildout.md) |
| 4 | Hardware swap (real NFC/LED/TTS adapters + real AI key) | _pending_ |
| 5 | Styling + polish | _pending_ |

## Current state

- ✅ Backend: 17 REST routes + WebSocket, full Pydantic-typed API, OpenAPI snapshot committed at `docs/openapi.json`
- ✅ Frontend: 8 unstyled-but-functional pages, single WebSocket connection, real-time adapter status, two-stage Excel import, work-log filtering, settings round-trip
- ✅ Tests: 72 passing + 1 intentional red (PII guard, by design)
- ⏳ Real hardware: only `QwenAIAdapter` is real; the other 3 adapters still mock — Day 4 work
