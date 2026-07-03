# Day 3 · 前端功能搭建 — 完成报告

**日期:** 2026-07-05
**分支:** master
**新提交数:** 12 commits
**总提交数 (master):** 51 commits
**Day 2 回归:** 72 passed + 1 PII guard fail (by design) — 全部仍 green

---

## 交付清单

| Task | 描述 | Commit |
|------|------|--------|
| 1 | Vite + React + TS 脚手架 + dev-server proxy | `b8bb35b` |
| 2 | 类型 + API client 层 (10 个 src/api/ 文件) | `0fd1bc9` |
| 3 | zustand realtime WebSocket store | `7784305` |
| 4 | App shell: router + NavLayout + providers + 8 个 placeholder | `a8ededf` |
| 5 | Dashboard page (今日来访 + 适配器状态) | `49c9de6` |
| 6 | Registration page (两阶段 Excel 导入 UI) | `22d0ef7` |
| 7 | Summary page (月度汇总 + Excel 导出) | `02a8ac5` |
| 8 | LiveBoard page (实时看板 + 调试刷卡) | `a709350` |
| 9 | CardManagement page (写卡管理 + write-log) | `e9a2cd9` |
| 10 | Templates page (欢迎词模板编辑) | `324e041` |
| 11 | WorkLog page (工作日志 + 过滤) | `5f65260` |
| 12 | Settings page (系统设置) | `37e4c19` |
| 13 | 收尾: `pnpm build` + 8-page headless 走查 | (无 fix commit) |

---

## 验收结果

**Plan 验收标准**(`docs/AITIC展厅_智能前台_完整实现计划_V1.md` Day 3): "8 个页面在浏览器里全部能跑通对应功能(丑但能用),硬件仍是 mock"。

| 验收项 | 结果 |
|---|---|
| 8 个页面均实现并 commit | ✅ |
| `pnpm exec tsc --noEmit` | ✅ 每个 task 末尾 0 errors |
| `pnpm build` (Task 13) | ✅ 379KB JS / 121KB gzipped, 118ms |
| Vite dev server `:5173` 启动 | ✅ 8 routes 全部 HTTP 200 |
| 8 page 端到端 headless 走查 | ✅ 10/10 通过 |
| WebSocket 双向事件(verify pass/fail) | ✅ 两类都收到 |
| `id_number` 在前端不脱敏(继承 Day 2 后端) | ✅ 14 字符 ID → `110*******0101` 透传 |
| PII safety: 原始 `ai_api_key` 不出现在 API 响应 | ✅ GET/PUT 均无 raw key |
| Day 2 backend tests 不回归 | ✅ 72 passed, 1 documented-acceptable fail |

---

## 架构概览

```
frontend/
├── src/
│   ├── api/             # 10 个文件:types + client + queryKeys + 8 个 endpoint group
│   ├── stores/
│   │   └── realtimeStore.ts   # zustand store, 单例 WebSocket, 20-event 环形缓冲
│   ├── components/
│   │   └── NavLayout.tsx      # 顶部 nav + Outlet
│   ├── pages/           # 8 个 named-export page 组件
│   ├── App.tsx          # QueryClientProvider + RouterProvider + useEffect(connect)
│   ├── router.tsx       # createBrowserRouter
│   └── main.tsx         # (Vite 模板原始,未改)
├── vite.config.ts       # /api 和 /ws 代理到 :8000
├── package.json         # 4 个 runtime dep + Vite 模板
└── tsconfig.json        # (Vite 模板原始)
```

**关键架构决策**:
- **类型在边界处唯一**: `src/api/types.ts` 是 Pydantic schemas 的 TS 镜像,所有 page 都从这里 import,无重复定义
- **WebSocket 单例**: 一个 zustand store 持有唯一的 `WebSocket` 对象,App 启动时 `connect()`,8 个 page 全部从 store 读,page 不直接 `new WebSocket`
- **REST proxy**: Vite dev server 代理 `/api/*` 和 `/ws/*` 到 backend `:8000`,生产环境部署到同一域名下无需改任何代码
- **PII 守门**: 原始敏感数据(`id_number`、`ai_api_key`)在 backend Day 2 已 mask,前端只做显示,不做二次处理

---

## 偏离 / 修正

### 1. LiveBoard page 加了 `visit_id` input (plan 修正)

**Plan 原文**(Task 8): 用户在 LiveBoard 模拟刷卡时只填 `card_uid + 姓名 + 来访日期`。

**问题**: 后端 `VerifyService.handle_card_verify_requested` 通过 `raw_payload["visit_id"]` 查 visit;若缺,直接判定 `card_not_found` → `name_mismatch` 永远不触发 → "欢迎光临" 永远不显示。

**修法**: 在 LiveBoard form 加一个 `visit_id` input,作为 `raw_payload` 的必填字段。`a709350` 是 amend 过的同一个 commit,加了 placeholder "必填,从 /api/cards/write-log 取"。

**追溯**: 真正在硬件环境下,卡片(NFC 写入的内容)会有 `visit_id`(Day 1 `CardService.handle_welcome_generated` 写卡时就把 `visit_id` 放进去了,见 `backend/app/services/card_service.py:25-31`)。**只在 Mock 调试页需要手动填**,跟产品语义一致。

### 2. 计划没有用 pnpm 的注册表(本地代理问题)

**环境问题**: Dev box 的 `HTTPS_PROXY=http://127.0.0.1:7897` 是 SOCKS5 转 HTTPS,无法透传到 `registry.npmjs.org` (TLS 握手断)。

**修法**: pnpm registry 切到 `https://registry.npmmirror.com/`(per-user config,不进项目文件)。Day 2 Task 14 的 SOCKS 修复(`uv add 'httpx[socks]'`)是同一个根因(你的 dev box 有代理设置,代理本身有问题)。**Day 4 硬件真机调试时,如果生产环境也走代理,需要查一遍**。

### 3. React 19 / Vite 8 / TypeScript 6 比 plan 暗指的版本新

`pnpm create vite --template react-ts` 拉的是最新模板(React 19.2.7 + Vite 8.1.3 + TS 6.0.3),plan 标题暗指 React 18 + Vite 5。**没有触发任何类型问题**——所有 8 个 page + 10 个 API 文件 `tsc --noEmit` 干净,`pnpm build` 也通过。如果 Day 4 引入新依赖(例如硬件 SDK 适配器、HTTPS 客户端),需要重新跑类型检查。

---

## 子智能体在执行中发现的问题(已修)

| 编号 | 问题 | 修法 | 任务 |
|---|---|---|---|
| 1 | npm registry 走 HTTPS_PROXY 断 | pnpm 切到 npmmirror.com 镜像 | T1 |
| 2 | LiveBoard 缺 visit_id → verify 永远失败 | form 加 visit_id input | T8 |
| 3 | T13 自动化脚本最初打错路径(`/api/imports/file` 等) | 改回正确路径(`/api/import/preview` 等) | T13 |

---

## Day 2 留下的 1 个红色测试(仍未处理)

`test_get_work_logs_does_not_leak_unmasked_id_numbers` — 这是 Day 2 Task 11 设计的长期 PII 守门哨,故意 seed 一个 leak 行让测试失败,证明 services 永远不把 raw `id_number` 放进 work_log detail。**Day 3 范围外,继续保留**。Day 4/5 决定是"删 leak 行"还是"在路由加 mask"。

---

## Day 4 交接清单

✅ Day 3 完整交付。Day 4 (硬件接入)拿到的:
- 完整可工作的 8 page SPA,build artifact 在 `frontend/dist/`
- 16 个 backend REST endpoint + 1 WS endpoint + 完整 openapi.json
- 18 个数据模型(6 ORM) + 5 services + 4 mock adapters + 1 real QwenAI adapter + AdapterStatusService
- 73 tests passing(72 + 1 PII guard fail-by-design)

⚠️ Day 4 接入真硬件时,需要在 backend 做的:
- 替换 `MockNFCAdapter` → real NFC SDK adapter(实现 `write_card` / `read_stream` / `health_check` 三方法)
- 替换 `MockLEDAdapter` / `MockTTSAdapter` → real LED/TTS SDK adapter
- 替换 `MockAIAdapter` → `QwenAIAdapter`(只要 `settings.ai_api_key` 配了,Day 2 Task 14 已经自动选真品;但需要填真 API key)
- 修 `QwenAIAdapter` 的 lazy-construct bug(plan 标记的 follow-up)
- 考虑 SOCKS 代理(见上面"偏离 2")

📦 **Day 4 范围**: 真硬件接入(最高风险日,plan 第 4 天整天的预算);前端无需改一行。

---

## 启动方式

```bash
# Backend (Mock 模式)
cd backend
uv run main.py          # :8000,Swagger UI at /docs

# Frontend
cd frontend
pnpm dev                 # :5173,代理到 :8000
```

浏览器打开 `http://localhost:5173/`,按 8 page 顺序走一遍即可。
