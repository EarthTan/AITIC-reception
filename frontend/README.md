# AITIC 展厅智能前台 · frontend

Vite + React 19 + TypeScript 6 SPA, served at `http://localhost:5173/` during dev. The Vite dev server proxies `/api/*` and `/ws/*` to the backend on `:8000`, so the SPA sees one origin.

## Run

```bash
pnpm install            # first time, or after package.json change
pnpm dev                # dev server with HMR
```

For the full stack, also run the backend in another terminal — see `../README.md` §"Quick Start".

## Commands

| Command | What it does |
|---|---|
| `pnpm dev` | Vite dev server on :5173 |
| `pnpm exec tsc --noEmit` | Type-check only (fast) |
| `pnpm build` | Production build → `dist/` (also runs `tsc -b`) |
| `pnpm add <pkg>` | Add a runtime dep |
| `pnpm add -D <pkg>` | Add a dev-only dep (type defs, linters) |

## Runtime deps

| Package | Why |
|---|---|
| `react`, `react-dom` | UI |
| `react-router-dom` | Client-side router (BrowserRouter) |
| `@tanstack/react-query` | Server-state cache (every page's data fetch) |
| `zustand` | `realtimeStore` — the single WebSocket connection |
| `axios` | HTTP client to the proxied `/api/*` |

## Project layout

```
src/
├── api/
│   ├── types.ts          # Pydantic schema mirror (one source of truth for TS types)
│   ├── client.ts         # axios instance, baseURL=/api
│   ├── queryKeys.ts      # centralized react-query key factory
│   ├── visits.ts         # GET/PATCH /api/visits*, summary, today
│   ├── imports.ts        # POST /api/import/{preview,commit}
│   ├── templates.ts      # GET/PUT /api/templates*
│   ├── cards.ts          # POST /api/cards/write, GET /write-log
│   ├── logs.ts           # GET /api/{verify-log,work-logs}
│   ├── adapters.ts       # GET /api/adapters/status
│   ├── settings.ts       # GET/PUT /api/settings
│   └── debug.ts          # POST /api/debug/simulate-card-read
├── stores/
│   └── realtimeStore.ts  # zustand: single WebSocket, 20-event ring buffer
├── components/
│   └── NavLayout.tsx     # top nav + <Outlet/>
├── pages/
│   ├── DashboardPage.tsx
│   ├── RegistrationPage.tsx
│   ├── SummaryPage.tsx
│   ├── LiveBoardPage.tsx
│   ├── CardManagementPage.tsx
│   ├── TemplatesPage.tsx
│   ├── WorkLogPage.tsx
│   └── SettingsPage.tsx
├── App.tsx               # QueryClientProvider + RouterProvider + WS connect()
├── router.tsx            # createBrowserRouter (8 routes under NavLayout)
└── main.tsx              # Vite template entry, unchanged
```

## Dev proxy

`vite.config.ts` proxies:

- `/api/*` → `http://localhost:8000`
- `/ws/*` → `ws://localhost:8000` (with `ws: true`)

No CORS configuration needed in dev. In production, deploy both behind a single reverse proxy that strips the prefix and forwards to the backend unchanged — no frontend code change required.

## Dev quirks

See [`../CLAUDE.md`](../CLAUDE.md) §"Known dev quirks" for the full list. The two that bite frontend work:

1. **Dev box npm registry**: shell's `HTTPS_PROXY=http://127.0.0.1:7897` is SOCKS5-on-localhost, can't reach `registry.npmjs.org`. Run `pnpm config set registry https://registry.npmmirror.com/` once per machine. This is per-user config, not in the repo.
2. **No test runner**: verification per task is `tsc --noEmit` + `pnpm build` + a headless `curl` walkthrough of the page. Real browser testing happens on Day 5.

## Type discipline

Every page imports shared types from `src/api/types.ts`. The TS types are a manual mirror of the backend's Pydantic schemas (`backend/app/schemas/`). When you add or change a backend schema, update `types.ts` in the same commit — `pnpm build` will catch most drift via `tsc -b`.

Sensitive fields (`id_number`, `ai_api_key`) are masked server-side. The frontend treats them as opaque display strings and never re-masks.
