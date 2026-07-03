# Day 3 · 前端功能搭建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Prerequisite:** `docs/superpowers/plans/2026-07-04-day2-backend-testing-api.md` must be complete — every page in this plan calls a real endpoint from that plan's `app/api/` layer. Run `cd backend && uv run pytest` and confirm it's green before starting.

**Goal:** Build a fully functional (unstyled) React frontend that exercises every backend capability from Day 1+2 — Excel two-stage import, visit browsing/editing, monthly summary + export, live WebSocket board with debug card-simulation, card write management, template editing, work log viewing, and settings — so Day 5 only has to add CSS, not wire up new functionality.

**Architecture:** Vite + React + TypeScript SPA under `frontend/`. A thin `src/api/` layer wraps every backend REST endpoint with typed functions; `@tanstack/react-query` owns server-state caching/invalidation; a single `zustand` store (`realtimeStore.ts`) owns the one WebSocket connection and exposes live event/adapter-status state to any page. Eight route-level pages, no shared design system yet — plain semantic HTML only (Day 5 owns styling per `docs/AITIC展厅_智能前台_完整实现计划_V1.md` §五 Day 5).

**Tech Stack:** Vite, React 18, TypeScript, `@tanstack/react-query`, `axios`, `react-router-dom`, `zustand`, `pnpm`.

## Global Constraints

- No styling work in this plan — plain HTML elements only, functionality over appearance (`docs/AITIC展厅_智能前台_完整实现计划_V1.md` §五 Day 3: "不做样式设计").
- Frontend dev server runs on Vite's default port 5173, matching the backend's existing `cors_origins` default (`backend/app/core/config.py:18`) — but this plan routes all traffic through Vite's dev-server proxy instead, so CORS never actually triggers in dev.
- All backend calls go through `src/api/*.ts` wrapper functions — pages never call `axios`/`fetch` directly.
- The WebSocket connection is a app-wide singleton (one connection, opened once in `App.tsx`) — pages read from the `zustand` store, they never open their own `WebSocket`.
- No automated frontend test runner is introduced in this plan (none exists yet, and the source plan's own Day 3 acceptance bar is manual browser verification, not unit tests) — verification per task is `tsc --noEmit` for type safety plus a manual browser walkthrough, per this project's `CLAUDE.md` instruction to actually exercise UI changes in a browser before calling them done.
- Never hand-edit `id_number` masking on the frontend — the backend (`VisitOut.from_visit`, Day 2 Task 4) already returns it masked; treat `id_number` as opaque display text.

---

## File Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── router.tsx
│   ├── api/
│   │   ├── client.ts
│   │   ├── queryKeys.ts
│   │   ├── types.ts
│   │   ├── visits.ts
│   │   ├── imports.ts
│   │   ├── templates.ts
│   │   ├── cards.ts
│   │   ├── logs.ts
│   │   ├── adapters.ts
│   │   ├── settings.ts
│   │   └── debug.ts
│   ├── stores/
│   │   └── realtimeStore.ts
│   ├── components/
│   │   └── NavLayout.tsx
│   └── pages/
│       ├── DashboardPage.tsx
│       ├── RegistrationPage.tsx
│       ├── SummaryPage.tsx
│       ├── LiveBoardPage.tsx
│       ├── CardManagementPage.tsx
│       ├── TemplatesPage.tsx
│       ├── WorkLogPage.tsx
│       └── SettingsPage.tsx
```

---

### Task 1: Scaffold the Vite + React + TS project

**Files:**
- Create: `frontend/` (via `pnpm create vite`)
- Modify: `frontend/vite.config.ts`

**Interfaces:**
- Produces: a running dev server on `:5173` proxying `/api/*` and `/ws/*` to the backend on `:8000`. Every later task depends on this proxy config existing verbatim.

- [ ] **Step 1: Scaffold the project**

Run from the repo root:
```bash
pnpm create vite frontend --template react-ts
cd frontend
pnpm install
```
Expected: `frontend/` now contains the standard Vite React-TS template (`src/App.tsx`, `src/main.tsx`, `vite.config.ts`, `package.json`, `tsconfig.json`, etc.).

- [ ] **Step 2: Install runtime dependencies**

Run: `cd frontend && pnpm add @tanstack/react-query axios react-router-dom zustand`
Expected: `package.json` `dependencies` now lists all four packages.

- [ ] **Step 3: Configure the dev-server proxy**

Read the generated `frontend/vite.config.ts` first, then replace its contents with:

```ts
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },
});
```

- [ ] **Step 4: Verify the scaffold builds and runs**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

Run (in a background/separate terminal, backend already running via `cd backend && uv run main.py`): `cd frontend && pnpm dev`
Expected: Vite prints `Local: http://localhost:5173/`. Open it in a browser — the default Vite+React counter page loads with no console errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Vite+React+TS frontend with API proxy"
```

---

### Task 2: Shared types + API client layer

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/queryKeys.ts`
- Create: `frontend/src/api/visits.ts`
- Create: `frontend/src/api/imports.ts`
- Create: `frontend/src/api/templates.ts`
- Create: `frontend/src/api/cards.ts`
- Create: `frontend/src/api/logs.ts`
- Create: `frontend/src/api/adapters.ts`
- Create: `frontend/src/api/settings.ts`
- Create: `frontend/src/api/debug.ts`

**Interfaces:**
- Produces (consumed by every page task, 5-12): all types below, plus one wrapper function per backend endpoint from the Day 2 plan. Every page imports these instead of calling `axios` directly.

- [ ] **Step 1: Shared types matching the Day 2 Pydantic schemas**

```ts
// frontend/src/api/types.ts
export type IdentityType =
  | "企业领导"
  | "企业员工"
  | "学校老师"
  | "大学生"
  | "中小学生"
  | "政府官员";

export type TemplateIdentityType = IdentityType | "默认";

export type WelcomeSource = "ai" | "fallback_template";
export type EntrySource = "auto" | "manual";
export type VisitStatus =
  | "pending"
  | "welcome_ready"
  | "card_written"
  | "verified"
  | "rejected";

export interface VisitOut {
  id: number;
  visit_date: string;
  session_time: string;
  name: string;
  phone: string | null;
  nationality: string | null;
  id_number: string | null;
  gender: string | null;
  organization: string | null;
  identity_type: IdentityType;
  welcome_text: string | null;
  welcome_source: WelcomeSource | null;
  entry_source: EntrySource;
  import_batch_id: string;
  status: VisitStatus;
  created_at: string;
  updated_at: string;
}

export interface VisitUpdate {
  name?: string;
  phone?: string;
  nationality?: string;
  gender?: string;
  organization?: string;
  identity_type?: IdentityType;
}

export interface ImportPreviewRow {
  row_number: number;
  data: Record<string, unknown>;
  errors: string[];
  is_valid: boolean;
}

export interface ImportPreviewResponse {
  preview_id: string;
  rows: ImportPreviewRow[];
  valid_count: number;
  invalid_count: number;
}

export interface ImportCommitResponse {
  import_batch_id: string;
  visit_ids: number[];
}

export interface VisitSummaryRow {
  visit_date: string;
  session_time: string;
  visit_count: number;
  visits: VisitOut[];
}

export interface TemplateOut {
  id: number;
  identity_type: TemplateIdentityType;
  template_text: string;
  updated_at: string;
}

export type WriteStatus = "success" | "failed" | "pending";

export interface CardWriteResult {
  visit_id: number;
  status: string;
  error_message: string | null;
}

export interface CardWriteLogOut {
  id: number;
  visit_id: number;
  card_uid: string | null;
  write_status: WriteStatus;
  error_message: string | null;
  written_at: string;
}

export type VerifyResult = "pass" | "fail";
export type FailReason = "name_mismatch" | "date_mismatch" | "card_not_found";

export interface VerifyLogOut {
  id: number;
  card_uid: string;
  visit_id: number | null;
  verify_result: VerifyResult;
  fail_reason: FailReason | null;
  verified_at: string;
}

export type LogModule =
  | "registration"
  | "ai_writeup"
  | "card_write"
  | "verify"
  | "led"
  | "tts"
  | "system";
export type LogStatus = "success" | "failure" | "warning";

export interface WorkLogOut {
  id: number;
  module: LogModule;
  action: string;
  status: LogStatus;
  detail: string | null;
  created_at: string;
}

export type AdapterHealthStatus = "online" | "offline" | "error";

export interface AdapterStatusOut {
  adapter_name: string;
  status: AdapterHealthStatus;
  last_heartbeat: string;
  detail: string | null;
}

export interface SettingsOut {
  excel_watch_dir: string;
  ai_provider: string;
  has_ai_api_key: boolean;
  cors_origins: string[];
  message?: string | null;
}

export interface SettingsUpdate {
  excel_watch_dir?: string;
  ai_provider?: string;
  ai_api_key?: string;
}
```

- [ ] **Step 2: Axios instance**

```ts
// frontend/src/api/client.ts
import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api",
});
```

- [ ] **Step 3: Centralized query keys**

```ts
// frontend/src/api/queryKeys.ts
export const queryKeys = {
  visits: (params?: Record<string, unknown>) => ["visits", params ?? {}] as const,
  visit: (id: number) => ["visits", id] as const,
  visitSummary: (month: string) => ["visits", "summary", month] as const,
  visitsToday: () => ["visits", "today"] as const,
  templates: () => ["templates"] as const,
  cardWriteLog: (visitId?: number) => ["cards", "write-log", visitId ?? null] as const,
  verifyLog: () => ["verify-log"] as const,
  workLogs: (params?: Record<string, unknown>) => ["work-logs", params ?? {}] as const,
  adapterStatus: () => ["adapters", "status"] as const,
  settings: () => ["settings"] as const,
};
```

- [ ] **Step 4: Visits API**

```ts
// frontend/src/api/visits.ts
import { apiClient } from "./client";
import type { VisitOut, VisitSummaryRow, VisitUpdate } from "./types";

export async function fetchVisits(params?: {
  visit_date?: string;
  identity_type?: string;
}): Promise<VisitOut[]> {
  const response = await apiClient.get<VisitOut[]>("/visits", { params });
  return response.data;
}

export async function fetchVisit(id: number): Promise<VisitOut> {
  const response = await apiClient.get<VisitOut>(`/visits/${id}`);
  return response.data;
}

export async function updateVisit(id: number, patch: VisitUpdate): Promise<VisitOut> {
  const response = await apiClient.patch<VisitOut>(`/visits/${id}`, patch);
  return response.data;
}

export async function fetchVisitSummary(month: string): Promise<VisitSummaryRow[]> {
  const response = await apiClient.get<VisitSummaryRow[]>("/visits/summary", {
    params: { month },
  });
  return response.data;
}

export async function fetchVisitsToday(): Promise<VisitOut[]> {
  const response = await apiClient.get<VisitOut[]>("/visits/today");
  return response.data;
}

export function visitSummaryExportUrl(month: string): string {
  return `/api/visits/summary/export?month=${encodeURIComponent(month)}`;
}
```

- [ ] **Step 5: Imports API**

```ts
// frontend/src/api/imports.ts
import { apiClient } from "./client";
import type { ImportCommitResponse, ImportPreviewResponse } from "./types";

export async function previewImport(file: File): Promise<ImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<ImportPreviewResponse>(
    "/import/preview",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
}

export async function commitImport(previewId: string): Promise<ImportCommitResponse> {
  const response = await apiClient.post<ImportCommitResponse>("/import/commit", {
    preview_id: previewId,
  });
  return response.data;
}
```

- [ ] **Step 6: Templates, cards, logs, adapters, settings, debug APIs**

```ts
// frontend/src/api/templates.ts
import { apiClient } from "./client";
import type { TemplateOut } from "./types";

export async function fetchTemplates(): Promise<TemplateOut[]> {
  const response = await apiClient.get<TemplateOut[]>("/templates");
  return response.data;
}

export async function updateTemplate(
  identityType: string,
  templateText: string
): Promise<TemplateOut> {
  const response = await apiClient.put<TemplateOut>(
    `/templates/${encodeURIComponent(identityType)}`,
    { template_text: templateText }
  );
  return response.data;
}
```

```ts
// frontend/src/api/cards.ts
import { apiClient } from "./client";
import type { CardWriteLogOut, CardWriteResult } from "./types";

export async function writeCards(visitIds: number[]): Promise<CardWriteResult[]> {
  const response = await apiClient.post<CardWriteResult[]>("/cards/write", {
    visit_ids: visitIds,
  });
  return response.data;
}

export async function fetchCardWriteLog(visitId?: number): Promise<CardWriteLogOut[]> {
  const response = await apiClient.get<CardWriteLogOut[]>("/cards/write-log", {
    params: visitId ? { visit_id: visitId } : undefined,
  });
  return response.data;
}
```

```ts
// frontend/src/api/logs.ts
import { apiClient } from "./client";
import type { VerifyLogOut, WorkLogOut } from "./types";

export async function fetchVerifyLog(): Promise<VerifyLogOut[]> {
  const response = await apiClient.get<VerifyLogOut[]>("/verify-log");
  return response.data;
}

export async function fetchWorkLogs(params?: {
  module?: string;
  status?: string;
}): Promise<WorkLogOut[]> {
  const response = await apiClient.get<WorkLogOut[]>("/work-logs", { params });
  return response.data;
}
```

```ts
// frontend/src/api/adapters.ts
import { apiClient } from "./client";
import type { AdapterStatusOut } from "./types";

export async function fetchAdapterStatus(): Promise<AdapterStatusOut[]> {
  const response = await apiClient.get<AdapterStatusOut[]>("/adapters/status");
  return response.data;
}
```

```ts
// frontend/src/api/settings.ts
import { apiClient } from "./client";
import type { SettingsOut, SettingsUpdate } from "./types";

export async function fetchSettings(): Promise<SettingsOut> {
  const response = await apiClient.get<SettingsOut>("/settings");
  return response.data;
}

export async function updateSettings(patch: SettingsUpdate): Promise<SettingsOut> {
  const response = await apiClient.put<SettingsOut>("/settings", patch);
  return response.data;
}
```

```ts
// frontend/src/api/debug.ts
import { apiClient } from "./client";

export async function simulateCardRead(
  cardUid: string,
  rawPayload: Record<string, unknown>
): Promise<void> {
  await apiClient.post("/debug/simulate-card-read", {
    card_uid: cardUid,
    raw_payload: rawPayload,
  });
}
```

- [ ] **Step 7: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors (these files aren't imported anywhere yet, so this only catches syntax/type errors within them).

- [ ] **Step 8: Commit**

```bash
cd frontend
git add src/api
git commit -m "feat: add typed API client layer for all backend endpoints"
```

---

### Task 3: Realtime WebSocket store

**Files:**
- Create: `frontend/src/stores/realtimeStore.ts`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure browser `WebSocket` API).
- Produces: `useRealtimeStore` zustand hook exposing `{ connected: boolean; events: RealtimeEvent[]; adapterStatuses: Record<string, {status, lastHeartbeat, detail}>; connect: () => void }`. `RealtimeEvent = { type: string; timestamp: string; payload: Record<string, unknown> }` matches the WS message shape from Day 2 Task 14 (`docs/AITIC展厅_智能前台_完整实现计划_V1.md` §4.5). `connect()` is idempotent — calling it multiple times reuses the existing socket. Consumed by `App.tsx` (Task 4) and `DashboardPage`/`LiveBoardPage` (Tasks 5, 8).

- [ ] **Step 1: Write the store**

```ts
// frontend/src/stores/realtimeStore.ts
import { create } from "zustand";

export interface RealtimeEvent {
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

interface AdapterLiveStatus {
  status: string;
  lastHeartbeat: string;
  detail: string | null;
}

interface RealtimeState {
  connected: boolean;
  events: RealtimeEvent[];
  adapterStatuses: Record<string, AdapterLiveStatus>;
  connect: () => void;
}

let socket: WebSocket | null = null;

export const useRealtimeStore = create<RealtimeState>((set) => ({
  connected: false,
  events: [],
  adapterStatuses: {},
  connect: () => {
    if (socket) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/realtime`);

    socket.onopen = () => set({ connected: true });
    socket.onclose = () => {
      set({ connected: false });
      socket = null;
    };
    socket.onmessage = (event) => {
      const message: RealtimeEvent = JSON.parse(event.data);
      set((state) => {
        if (message.type === "adapter.heartbeat") {
          const name = String(message.payload.adapter_name);
          return {
            adapterStatuses: {
              ...state.adapterStatuses,
              [name]: {
                status: String(message.payload.status),
                lastHeartbeat: message.timestamp,
                detail: (message.payload.detail as string | null) ?? null,
              },
            },
          };
        }
        return { events: [message, ...state.events].slice(0, 20) };
      });
    };
  },
}));
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/stores
git commit -m "feat: add zustand store owning the single realtime WebSocket connection"
```

---

### Task 4: App shell — router, nav layout, providers, placeholder pages

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/router.tsx`
- Create: `frontend/src/components/NavLayout.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx` (placeholder, filled in Task 5)
- Create: `frontend/src/pages/RegistrationPage.tsx` (placeholder, filled in Task 6)
- Create: `frontend/src/pages/SummaryPage.tsx` (placeholder, filled in Task 7)
- Create: `frontend/src/pages/LiveBoardPage.tsx` (placeholder, filled in Task 8)
- Create: `frontend/src/pages/CardManagementPage.tsx` (placeholder, filled in Task 9)
- Create: `frontend/src/pages/TemplatesPage.tsx` (placeholder, filled in Task 10)
- Create: `frontend/src/pages/WorkLogPage.tsx` (placeholder, filled in Task 11)
- Create: `frontend/src/pages/SettingsPage.tsx` (placeholder, filled in Task 12)
- Delete: `frontend/src/App.css`, `frontend/src/assets/react.svg` (Vite template boilerplate no longer referenced)

**Interfaces:**
- Consumes: `useRealtimeStore` (Task 3).
- Produces: a `router` export used only internally by `App.tsx`; 8 page components each exported as a named export matching the exact name used in `router.tsx` (`DashboardPage`, `RegistrationPage`, `SummaryPage`, `LiveBoardPage`, `CardManagementPage`, `TemplatesPage`, `WorkLogPage`, `SettingsPage`) — Tasks 5-12 fill in each page's body but must keep this exact export name and file path.

- [ ] **Step 1: Minimal placeholder for each of the 8 pages**

Each of the 8 files gets this pattern (substituting the component name and Chinese title):

```tsx
// frontend/src/pages/DashboardPage.tsx
export function DashboardPage() {
  return <h1>仪表盘</h1>;
}
```

Repeat for `RegistrationPage`/"访客登记", `SummaryPage`/"汇总总表", `LiveBoardPage`/"现场实时看板", `CardManagementPage`/"写卡管理", `TemplatesPage`/"欢迎词模板", `WorkLogPage`/"工作日志", `SettingsPage`/"系统设置".

- [ ] **Step 2: Nav layout**

```tsx
// frontend/src/components/NavLayout.tsx
import { Link, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "仪表盘" },
  { to: "/registration", label: "访客登记" },
  { to: "/summary", label: "汇总总表" },
  { to: "/live-board", label: "现场实时看板" },
  { to: "/cards", label: "写卡管理" },
  { to: "/templates", label: "欢迎词模板" },
  { to: "/work-logs", label: "工作日志" },
  { to: "/settings", label: "系统设置" },
];

export function NavLayout() {
  return (
    <div>
      <nav>
        <ul>
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <Link to={item.to}>{item.label}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Router**

```tsx
// frontend/src/router.tsx
import { createBrowserRouter } from "react-router-dom";
import { NavLayout } from "./components/NavLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { RegistrationPage } from "./pages/RegistrationPage";
import { SummaryPage } from "./pages/SummaryPage";
import { LiveBoardPage } from "./pages/LiveBoardPage";
import { CardManagementPage } from "./pages/CardManagementPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { WorkLogPage } from "./pages/WorkLogPage";
import { SettingsPage } from "./pages/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <NavLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "registration", element: <RegistrationPage /> },
      { path: "summary", element: <SummaryPage /> },
      { path: "live-board", element: <LiveBoardPage /> },
      { path: "cards", element: <CardManagementPage /> },
      { path: "templates", element: <TemplatesPage /> },
      { path: "work-logs", element: <WorkLogPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);
```

- [ ] **Step 4: App shell wiring providers + the realtime connection**

Delete the generated `frontend/src/App.css` and the `import "./App.css"` line, then replace `frontend/src/App.tsx` entirely with:

```tsx
// frontend/src/App.tsx
import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { useRealtimeStore } from "./stores/realtimeStore";

const queryClient = new QueryClient();

export default function App() {
  const connect = useRealtimeStore((state) => state.connect);

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
```

- [ ] **Step 5: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Manual browser verification**

With backend running (`cd backend && uv run main.py`) and frontend dev server running (`cd frontend && pnpm dev`), open `http://localhost:5173/`:
- Confirm the nav bar shows all 8 links.
- Click each link and confirm the corresponding placeholder heading renders with no console errors.
- Open browser devtools Network/WS tab, confirm a WebSocket connection to `/ws/realtime` shows status 101 (switching protocols).

- [ ] **Step 7: Commit**

```bash
cd frontend
git add src/App.tsx src/router.tsx src/components src/pages
git rm src/App.css
git commit -m "feat: wire up router, nav layout and realtime connection with placeholder pages"
```

---

### Task 5: Dashboard page (仪表盘)

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

**Interfaces:**
- Consumes: `fetchVisitsToday` (`api/visits.ts`), `fetchAdapterStatus` (`api/adapters.ts`), `queryKeys.visitsToday`/`queryKeys.adapterStatus`, `useRealtimeStore((s) => s.adapterStatuses)`.

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/DashboardPage.tsx
import { useQuery } from "@tanstack/react-query";
import { fetchAdapterStatus } from "../api/adapters";
import { queryKeys } from "../api/queryKeys";
import { fetchVisitsToday } from "../api/visits";
import { useRealtimeStore } from "../stores/realtimeStore";

const ADAPTER_NAMES = ["nfc", "led", "tts", "ai"] as const;

export function DashboardPage() {
  const todayQuery = useQuery({
    queryKey: queryKeys.visitsToday(),
    queryFn: fetchVisitsToday,
  });
  const statusQuery = useQuery({
    queryKey: queryKeys.adapterStatus(),
    queryFn: fetchAdapterStatus,
  });
  const realtimeStatuses = useRealtimeStore((state) => state.adapterStatuses);

  const merged = new Map<string, { status: string; detail?: string | null }>();
  for (const row of statusQuery.data ?? []) {
    merged.set(row.adapter_name, { status: row.status, detail: row.detail });
  }
  for (const [name, live] of Object.entries(realtimeStatuses)) {
    merged.set(name, { status: live.status, detail: live.detail });
  }

  return (
    <div>
      <h1>仪表盘</h1>
      <section>
        <h2>今日来访人数：{todayQuery.data?.length ?? "-"}</h2>
      </section>
      <section>
        <h2>适配器状态</h2>
        <ul>
          {ADAPTER_NAMES.map((name) => {
            const entry = merged.get(name);
            return (
              <li key={name}>
                {name}: {entry ? entry.status : "unknown"}
                {entry?.detail ? ` (${entry.detail})` : ""}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification**

With both servers running, navigate to `http://localhost:5173/`:
- Confirm "今日来访人数" shows a number (0 on a fresh DB) instead of `-`.
- Confirm all 4 adapters show `online` within a few seconds (the Day 2 heartbeat poller ticks every 30s — either wait, or lower `interval_seconds` temporarily while testing).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/DashboardPage.tsx
git commit -m "feat: implement dashboard page with today's count and adapter status"
```

---

### Task 6: Registration page (访客登记) — two-stage import UI

**Files:**
- Modify: `frontend/src/pages/RegistrationPage.tsx`

**Interfaces:**
- Consumes: `previewImport`, `commitImport` (`api/imports.ts`), `ImportPreviewResponse` (`api/types.ts`).

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/RegistrationPage.tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { commitImport, previewImport } from "../api/imports";
import type { ImportPreviewResponse } from "../api/types";

export function RegistrationPage() {
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const queryClient = useQueryClient();

  const previewMutation = useMutation({
    mutationFn: previewImport,
    onSuccess: (data) => setPreview(data),
  });

  const commitMutation = useMutation({
    mutationFn: () => commitImport(preview!.preview_id),
    onSuccess: () => {
      setPreview(null);
      queryClient.invalidateQueries({ queryKey: ["visits"] });
    },
  });

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      previewMutation.mutate(file);
    }
  }

  return (
    <div>
      <h1>访客登记</h1>
      <input type="file" accept=".xlsx,.xls" onChange={handleFileChange} />

      {previewMutation.isPending && <p>解析中...</p>}

      {preview && (
        <div>
          <p>
            有效 {preview.valid_count} 行，无效 {preview.invalid_count} 行
          </p>
          <table>
            <thead>
              <tr>
                <th>行号</th>
                <th>姓名</th>
                <th>身份</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row) => (
                <tr
                  key={row.row_number}
                  style={{ background: row.is_valid ? undefined : "#ffdddd" }}
                >
                  <td>{row.row_number}</td>
                  <td>{String(row.data["姓名"] ?? "")}</td>
                  <td>{String(row.data["身份"] ?? "")}</td>
                  <td>{row.errors.join("; ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            disabled={preview.valid_count === 0 || commitMutation.isPending}
            onClick={() => commitMutation.mutate()}
          >
            确认入库（{preview.valid_count}条）
          </button>
        </div>
      )}

      {commitMutation.isSuccess && (
        <p>
          导入成功，批次号：{commitMutation.data.import_batch_id}，共
          {commitMutation.data.visit_ids.length}条
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification**

Navigate to `/registration`, upload `backend/fixtures/sample_visitors.xlsx` (from the Day 2 plan's Task 3):
- Confirm the preview table shows 7 rows, with the "外星人" identity row highlighted red and listing an error.
- Confirm "有效 6 行，无效 1 行".
- Click "确认入库（6条）" and confirm a success message with 6 `visit_ids` appears.
- Navigate to `/summary` (once Task 7 is done) or hit `GET /api/visits` directly to confirm 6 rows now exist.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/RegistrationPage.tsx
git commit -m "feat: implement registration page with two-stage Excel import"
```

---

### Task 7: Monthly summary page (汇总总表)

**Files:**
- Modify: `frontend/src/pages/SummaryPage.tsx`

**Interfaces:**
- Consumes: `fetchVisitSummary`, `visitSummaryExportUrl` (`api/visits.ts`), `queryKeys.visitSummary`.

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/SummaryPage.tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchVisitSummary, visitSummaryExportUrl } from "../api/visits";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function SummaryPage() {
  const [month, setMonth] = useState(currentMonth());
  const summaryQuery = useQuery({
    queryKey: queryKeys.visitSummary(month),
    queryFn: () => fetchVisitSummary(month),
  });

  return (
    <div>
      <h1>月度汇总总表</h1>
      <input
        type="month"
        value={month}
        onChange={(event) => setMonth(event.target.value)}
      />
      <a href={visitSummaryExportUrl(month)} download>
        导出Excel
      </a>

      {summaryQuery.data?.map((group) => (
        <div key={`${group.visit_date}-${group.session_time}`}>
          <h3>
            场次：{group.visit_date} {group.session_time}（{group.visit_count}人）
          </h3>
          <table>
            <thead>
              <tr>
                <th>姓名</th>
                <th>身份</th>
                <th>单位</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {group.visits.map((visit) => (
                <tr key={visit.id}>
                  <td>{visit.name}</td>
                  <td>{visit.identity_type}</td>
                  <td>{visit.organization}</td>
                  <td>{visit.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification**

Navigate to `/summary`, set the month picker to `2026-07` (matching the fixture's `visit_date`):
- Confirm grouped sections appear per session (场次), each listing the correct visitors.
- Click "导出Excel" and confirm a `.xlsx` file downloads.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/SummaryPage.tsx
git commit -m "feat: implement monthly summary page with export"
```

---

### Task 8: Live board page (现场实时看板) + debug trigger

**Files:**
- Modify: `frontend/src/pages/LiveBoardPage.tsx`

**Interfaces:**
- Consumes: `useRealtimeStore((s) => s.events)`, `useRealtimeStore((s) => s.connected)` (Task 3), `simulateCardRead` (`api/debug.ts`).

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/LiveBoardPage.tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { simulateCardRead } from "../api/debug";
import { useRealtimeStore } from "../stores/realtimeStore";

export function LiveBoardPage() {
  const events = useRealtimeStore((state) => state.events);
  const connected = useRealtimeStore((state) => state.connected);
  const [cardUid, setCardUid] = useState("SIM-001");
  const [name, setName] = useState("");
  const [visitDate, setVisitDate] = useState("");

  const simulateMutation = useMutation({
    mutationFn: () => simulateCardRead(cardUid, { name, visit_date: visitDate }),
  });

  const latest = events[0];

  return (
    <div>
      <h1>现场实时看板</h1>
      <p>WebSocket连接状态：{connected ? "已连接" : "未连接"}</p>

      <section>
        {latest?.type === "card.verify.passed" && (
          <div>
            <h2>欢迎光临！</h2>
            <p>visit_id: {String(latest.payload.visit_id)}</p>
          </div>
        )}
        {latest?.type === "card.verify.failed" && (
          <div>
            <h2 style={{ color: "red" }}>无权限入场</h2>
            <p>原因：{String(latest.payload.fail_reason)}</p>
          </div>
        )}
      </section>

      <section>
        <h3>模拟刷卡（调试用）</h3>
        <label>
          card_uid:
          <input value={cardUid} onChange={(e) => setCardUid(e.target.value)} />
        </label>
        <label>
          姓名:
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          来访日期:
          <input
            type="date"
            value={visitDate}
            onChange={(e) => setVisitDate(e.target.value)}
          />
        </label>
        <button onClick={() => simulateMutation.mutate()}>模拟刷卡</button>
      </section>

      <section>
        <h3>最近事件</h3>
        <ul>
          {events.map((event, index) => (
            <li key={index}>
              {event.timestamp} - {event.type} - {JSON.stringify(event.payload)}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification (this is the plan's key acceptance step — the only way to confirm the realtime pipeline works without hardware)**

Navigate to `/live-board`, confirm "WebSocket连接状态：已连接". Get a real `card_uid` + its written payload from a visit that has already gone through card write (e.g. from Task 6's imported fixture, once its card has been auto-written by the existing event pipeline — check via `GET /api/cards/write-log`):
- Fill in `card_uid`, `姓名` (matching that visit's name), and `来访日期` (matching `visit_date`), click "模拟刷卡".
- Confirm "欢迎光临！" appears with the correct `visit_id` within ~1 second, and the event shows up in "最近事件".
- Repeat with a mismatched name — confirm "无权限入场" (red) appears with `fail_reason: name_mismatch`.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/LiveBoardPage.tsx
git commit -m "feat: implement live board page with realtime verify events and debug trigger"
```

---

### Task 9: Card management page (写卡管理)

**Files:**
- Modify: `frontend/src/pages/CardManagementPage.tsx`

**Interfaces:**
- Consumes: `fetchVisits` (`api/visits.ts`), `writeCards`, `fetchCardWriteLog` (`api/cards.ts`), `queryKeys.visits`/`queryKeys.cardWriteLog`.

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/CardManagementPage.tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCardWriteLog, writeCards } from "../api/cards";
import { queryKeys } from "../api/queryKeys";
import { fetchVisits } from "../api/visits";

export function CardManagementPage() {
  const [selected, setSelected] = useState<number[]>([]);
  const queryClient = useQueryClient();

  const visitsQuery = useQuery({
    queryKey: queryKeys.visits(),
    queryFn: () => fetchVisits(),
  });
  const writeLogQuery = useQuery({
    queryKey: queryKeys.cardWriteLog(),
    queryFn: () => fetchCardWriteLog(),
  });

  const writeMutation = useMutation({
    mutationFn: () => writeCards(selected),
    onSuccess: () => {
      setSelected([]);
      queryClient.invalidateQueries({ queryKey: ["cards", "write-log"] });
      queryClient.invalidateQueries({ queryKey: ["visits"] });
    },
  });

  const writable = (visitsQuery.data ?? []).filter(
    (visit) => visit.status === "welcome_ready"
  );

  function toggle(id: number) {
    setSelected((current) =>
      current.includes(id) ? current.filter((v) => v !== id) : [...current, id]
    );
  }

  return (
    <div>
      <h1>写卡管理</h1>
      <section>
        <h2>待写卡访客</h2>
        <table>
          <thead>
            <tr>
              <th></th>
              <th>姓名</th>
              <th>身份</th>
              <th>欢迎词</th>
            </tr>
          </thead>
          <tbody>
            {writable.map((visit) => (
              <tr key={visit.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.includes(visit.id)}
                    onChange={() => toggle(visit.id)}
                  />
                </td>
                <td>{visit.name}</td>
                <td>{visit.identity_type}</td>
                <td>{visit.welcome_text}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <button disabled={selected.length === 0} onClick={() => writeMutation.mutate()}>
          批量写卡（{selected.length}）
        </button>
      </section>

      <section>
        <h2>写卡记录</h2>
        <table>
          <thead>
            <tr>
              <th>visit_id</th>
              <th>card_uid</th>
              <th>状态</th>
              <th>错误信息</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {(writeLogQuery.data ?? []).map((log) => (
              <tr key={log.id}>
                <td>{log.visit_id}</td>
                <td>{log.card_uid}</td>
                <td>{log.write_status}</td>
                <td>{log.error_message}</td>
                <td>{log.written_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification**

Navigate to `/cards`:
- Confirm "写卡记录" already lists rows auto-written by the event pipeline for previously-imported visits (Day 1's `CardService` writes automatically on `welcome.generated`, so "待写卡访客" will usually be empty unless you catch a visit mid-pipeline — that's expected, not a bug).
- If any visit is caught in `welcome_ready`, check it, click "批量写卡", confirm it disappears from the list and a new row appears in "写卡记录".

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/CardManagementPage.tsx
git commit -m "feat: implement card management page with manual write trigger and write log"
```

---

### Task 10: Templates page (欢迎词模板)

**Files:**
- Modify: `frontend/src/pages/TemplatesPage.tsx`

**Interfaces:**
- Consumes: `fetchTemplates`, `updateTemplate` (`api/templates.ts`), `queryKeys.templates`.

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/TemplatesPage.tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchTemplates, updateTemplate } from "../api/templates";

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const templatesQuery = useQuery({
    queryKey: queryKeys.templates(),
    queryFn: fetchTemplates,
  });
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const updateMutation = useMutation({
    mutationFn: ({ identityType, text }: { identityType: string; text: string }) =>
      updateTemplate(identityType, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.templates() });
    },
  });

  return (
    <div>
      <h1>欢迎词模板</h1>
      <table>
        <thead>
          <tr>
            <th>身份类型</th>
            <th>模板文案</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(templatesQuery.data ?? []).map((template) => {
            const draft = drafts[template.identity_type] ?? template.template_text;
            return (
              <tr key={template.id}>
                <td>{template.identity_type}</td>
                <td>
                  <input
                    value={draft}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [template.identity_type]: event.target.value,
                      }))
                    }
                  />
                </td>
                <td>
                  <button
                    onClick={() =>
                      updateMutation.mutate({
                        identityType: template.identity_type,
                        text: draft,
                      })
                    }
                  >
                    保存
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification**

Navigate to `/templates`:
- Confirm all 7 rows appear (6 identity types + 默认).
- Edit one row's text, click "保存", reload the page and confirm the new text persisted (round-trips through `PUT /api/templates/{identity_type}`).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/TemplatesPage.tsx
git commit -m "feat: implement welcome template editing page"
```

---

### Task 11: Work log page (工作日志)

**Files:**
- Modify: `frontend/src/pages/WorkLogPage.tsx`

**Interfaces:**
- Consumes: `fetchWorkLogs` (`api/logs.ts`), `queryKeys.workLogs`.

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/WorkLogPage.tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchWorkLogs } from "../api/logs";

const MODULES = [
  "registration",
  "ai_writeup",
  "card_write",
  "verify",
  "led",
  "tts",
  "system",
];
const STATUSES = ["success", "failure", "warning"];

export function WorkLogPage() {
  const [moduleFilter, setModuleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const params = {
    module: moduleFilter || undefined,
    status: statusFilter || undefined,
  };
  const logsQuery = useQuery({
    queryKey: queryKeys.workLogs(params),
    queryFn: () => fetchWorkLogs(params),
  });

  return (
    <div>
      <h1>工作日志</h1>
      <select value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)}>
        <option value="">全部模块</option>
        {MODULES.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
        <option value="">全部状态</option>
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>模块</th>
            <th>动作</th>
            <th>状态</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          {(logsQuery.data ?? []).map((log) => (
            <tr key={log.id}>
              <td>{log.created_at}</td>
              <td>{log.module}</td>
              <td>{log.action}</td>
              <td>{log.status}</td>
              <td>{log.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification**

Navigate to `/work-logs`:
- Confirm rows appear for every registration/AI/card-write/verify action performed during earlier manual testing.
- Filter by `module=registration` and confirm only registration rows show; filter by `status=warning` and confirm only warning rows show (e.g. the invalid-row warning from Task 6's import).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/WorkLogPage.tsx
git commit -m "feat: implement work log page with module/status filters"
```

---

### Task 12: Settings page (系统设置)

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`

**Interfaces:**
- Consumes: `fetchSettings`, `updateSettings` (`api/settings.ts`), `queryKeys.settings`.

- [ ] **Step 1: Implement the page**

```tsx
// frontend/src/pages/SettingsPage.tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchSettings, updateSettings } from "../api/settings";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: queryKeys.settings(),
    queryFn: fetchSettings,
  });
  const [apiKeyDraft, setApiKeyDraft] = useState("");
  const [watchDirDraft, setWatchDirDraft] = useState("");

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings() });
    },
  });

  const settings = settingsQuery.data;

  return (
    <div>
      <h1>系统设置</h1>
      {settings && (
        <div>
          <p>Excel监听目录：{settings.excel_watch_dir}</p>
          <p>AI服务商：{settings.ai_provider}</p>
          <p>AI Key已配置：{settings.has_ai_api_key ? "是" : "否"}</p>
          {settings.message && <p>{settings.message}</p>}
        </div>
      )}

      <label>
        新的Excel监听目录：
        <input value={watchDirDraft} onChange={(e) => setWatchDirDraft(e.target.value)} />
      </label>
      <label>
        新的AI Key：
        <input
          type="password"
          value={apiKeyDraft}
          onChange={(e) => setApiKeyDraft(e.target.value)}
        />
      </label>
      <button
        onClick={() =>
          updateMutation.mutate({
            excel_watch_dir: watchDirDraft || undefined,
            ai_api_key: apiKeyDraft || undefined,
          })
        }
      >
        保存
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual browser verification**

Navigate to `/settings`:
- Confirm current values render, `AI Key已配置` shows `否` on a fresh `.env`.
- Enter a fake key, click "保存", confirm `AI Key已配置` flips to `是` and the "重启后生效" message appears.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/SettingsPage.tsx
git commit -m "feat: implement settings page for AI key and watch directory"
```

---

### Task 13: Final integration walkthrough

**Files:** none (verification-only task)

**Interfaces:** exercises the full stack built across Tasks 1-12 plus the Day 2 backend plan end-to-end.

- [ ] **Step 1: Production build check**

Run: `cd frontend && pnpm build`
Expected: build succeeds with no TypeScript errors, output written to `frontend/dist/`.

- [ ] **Step 2: Full manual walkthrough with both servers running**

With `cd backend && uv run main.py` and `cd frontend && pnpm dev` both running, open `http://localhost:5173/` and, in order:
1. `/registration` — upload `backend/fixtures/sample_visitors.xlsx`, confirm preview + commit works (6 imported).
2. `/summary` — confirm the 6 visitors show grouped by session for `2026-07`.
3. `/cards` — confirm write-log shows 6 auto-written cards (from the existing event pipeline).
4. `/live-board` — using one written card's `card_uid` + matching name/date from `/api/cards/write-log`, simulate a card read and confirm "欢迎光临！" appears; simulate a mismatched name and confirm "无权限入场" appears.
5. `/work-logs` — confirm entries exist for every module touched above (`registration`, `ai_writeup`, `card_write`, `verify`).
6. `/templates` — edit and save one template, confirm it persists after reload.
7. `/settings` — confirm settings round-trip.
8. `/` (Dashboard) — confirm today's count and adapter statuses reflect the session's activity.

Expected: no browser console errors at any step; every action's effect is visible either immediately (React Query refetch) or via the realtime WebSocket (verify events, adapter heartbeats) — this is the plan's overall acceptance bar, matching the source doc's Day 3 criterion: "8个页面在浏览器里全部能跑通对应功能（丑但能用），硬件仍是mock".

- [ ] **Step 3: Commit (if Step 1's build check required any fixes)**

```bash
cd frontend
git add -A
git commit -m "fix: address build issues found during final Day 3 integration walkthrough"
```
(Skip this step entirely if Step 1 and Step 2 required no code changes.)

---

## Self-Review Notes

- **Spec coverage:** all 8 pages from `docs/AITIC展厅_智能前台_完整实现计划_V1.md` §五 Day 3 have a task (5-12); the two-stage upload UI is Task 6; the debug-trigger-driven realtime verification is Task 8 (the plan's explicit note that this is "唯一能验证'实时看板真的实时'的方法" without hardware); API client + query keys are Task 2; Zustand realtime store is Task 3.
- **Type consistency:** `VisitOut`, `TemplateOut`, `CardWriteLogOut`, `VerifyLogOut`, `WorkLogOut`, `AdapterStatusOut`, `SettingsOut` are defined once in `api/types.ts` (Task 2) and referenced by name, unchanged, in every subsequent page task — no duplicate/divergent shapes.
- **Deferred to Day 5:** all visual styling (Tailwind, kiosk full-screen mode for the live board, red/green status lights) is explicitly out of scope here per the Global Constraints section — do not add ad hoc CSS mid-plan.
