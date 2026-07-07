# 前端现状清单（供视觉设计 Agent 参考）

**用途**：这不是一份设计文档，而是当前前端实现的**完整现状快照**，供交接给专门做前端视觉设计的 agent 使用。该 agent 会基于此产出新的视觉设计，之后再由本项目把设计结果代码化嵌入本仓库。

**技术栈**：React 19 + TypeScript 6 + Vite，`react-router-dom`（路由），`@tanstack/react-query`（服务端状态/缓存），`zustand`（WebSocket 实时状态），`axios`（HTTP 客户端）。**没有任何 UI 组件库或 CSS 框架**（无 MUI/Antd/Tailwind），页面几乎都是裸 HTML 语义标签（`div/section/table/button/input`），只有少数几个页面用了内联 `style`。这意味着视觉设计可以从零開始，不受现有样式束缚。

---

## 0. 全局结构

### 0.1 路由表（`src/router.tsx`）

| 路径 | 组件 | 是否带导航栏 |
|---|---|---|
| `/` | DashboardPage | 是（`NavLayout` 包裹） |
| `/registration` | RegistrationPage | 是 |
| `/summary` | SummaryPage | 是 |
| `/live-board` | LiveBoardPage | 是 |
| `/cards` | CardManagementPage | 是 |
| `/templates` | TemplatesPage | 是 |
| `/work-logs` | WorkLogPage | 是 |
| `/settings` | SettingsPage | 是 |
| `/display` | DisplayPage | **否**（独立全屏页，不带导航栏/离线横幅） |
| `/mock-led` | MockLEDPane | **否**（独立全屏页，模拟 LED 硬件屏） |

### 0.2 全局组件

**`NavLayout`**（`src/components/NavLayout.tsx`）— 包裹前 8 个路由的外层布局：
- 顶部渲染 `<AdapterOfflineBanner/>`
- 一个 `<nav>`，内含 8 个导航链接（`<ul><li><Link>`），标签：仪表盘 / 访客登记 / 汇总总表 / 现场实时看板 / 写卡管理 / 欢迎词模板 / 工作日志 / 系统设置
- `<main>` 渲染 `<Outlet/>`（当前页面内容）
- 目前没有任何激活态高亮、图标、折叠菜单、面包屑等——纯文字链接横排（或纵排，取决于默认 `<ul>` 布局）

**`AdapterOfflineBanner`**（`src/components/AdapterOfflineBanner.tsx`）— 条件渲染的红色警告横幅：
- 数据源：`realtimeStore.adapterStatuses`（4 个适配器：nfc/led/tts/ai 的实时心跳状态）
- 只要有任一适配器 `status !== "online"` 就显示；全部在线则不渲染（返回 `null`）
- 内容：`⚠️ 硬件离线：{适配器名列表大写，用 " / " 连接} — 管理功能仍可使用，但现场刷卡链路可能异常`
- 纯内联样式：红底白字（`#d32f2f`）、居中、加粗

### 0.3 全局状态（`src/stores/realtimeStore.ts`，zustand）

单一 WebSocket 连接到 `/ws/realtime`，指数退避重连（1s → 2s → 4s → … 上限 30s）。State 字段：
- `connected: boolean`
- `events: RealtimeEvent[]`（最近 20 条原始事件，含 `card.verify.passed/failed`）
- `adapterStatuses: Record<string, {status, lastHeartbeat, detail}>`（来自 `adapter.heartbeat` 消息）
- `ledContent: LEDContent | null`（来自 `led.content` 消息：`{name, welcome_text, is_rejection, reason}`）
- `reconnectAttempt: number`

### 0.4 现有视觉风格现状（`src/index.css`）

- 仅有一套 CSS 变量（浅色/深色两套，跟随系统 `prefers-color-scheme`）：`--text`, `--text-h`, `--bg`, `--border`, `--accent`（紫色 `#aa3bff`）等
- `#root` 被限制为定宽 `1126px` 居中、两侧描边、`text-align: center`（这其实是 Vite 默认脚手架残留的样式，并**不是**为本应用设计的布局，几乎每个页面的内容都没有真正贴合这个居中容器的意图）
- 只定义了 `h1`/`h2`/`code` 的排版，**没有** button/input/table/a 的任何自定义样式——它们全部是浏览器默认样式
- 结论：**当前没有真正意义上的视觉设计**，所有页面呈现的是未加工的语义 HTML。这是本次设计工作要解决的核心问题。

---

## 1. 页面详细清单

### 1.1 DashboardPage（`/`，仪表盘）

**内容**：
- `<h1>仪表盘</h1>`
- 区块一：`<h2>今日来访人数：{count}</h2>`（无数据时显示 `-`）
- 区块二：`<h2>适配器状态</h2>` + 一个 `<ul>`，列出 4 个固定适配器（`nfc/led/tts/ai`）各自的状态文字（`{name}: {status}`，如有 detail 则加 `(detail)`），无数据显示 `unknown`

**交互元素**：无按钮/链接，纯只读展示页。

**API**：
- `GET /api/visits/today` → 今日来访人数（取数组长度）
- `GET /api/adapters/status` → 4 适配器快照
- 另外合并 WebSocket 实时心跳（`realtimeStore.adapterStatuses`）覆盖/补充 REST 快照

---

### 1.2 RegistrationPage（`/registration`，访客登记）

**内容**：
- `<h1>访客登记</h1>`
- 文件选择 `<input type="file" accept=".xlsx,.xls">`
- 解析中提示：`解析中...`
- 预览表格（提交前）：表头 11 列——行号、姓名、来访日期、计划场次时间、手机号、国籍、身份证号、性别、单位、身份、错误
  - 每行如果 `is_valid === false`，整行背景变浅红色（`#ffdddd`）
  - 错误列文字为红色小字
- 顶部统计：`有效 {n} 行，无效 {n} 行`
- 提交成功后提示：`导入成功，批次号：{batch_id}，共{n}条`

**交互元素**：
- 文件 `<input>` → 触发 `previewImport`
- 按钮「确认入库（{n}条）」——`disabled` 条件：`valid_count === 0` 或提交中 → 触发 `commitImport`

**API**：
- `POST /api/import/preview`（multipart/form-data，字段名 `file`）→ `ImportPreviewResponse`
- `POST /api/import/commit`（body: `{preview_id}`）→ `ImportCommitResponse {import_batch_id, visit_ids[]}`

---

### 1.3 SummaryPage（`/summary`，月度汇总总表）

**内容**：
- `<h1>月度汇总总表</h1>`
- 月份选择器 `<input type="month">`（默认当前月）
- 「导出Excel」下载链接
- 按场次（日期+时间）分组渲染：每组一个 `<h3>场次：{date} {time}（{count}人）</h3>` + 一张表格（列：姓名、身份、单位、状态）

**交互元素**：
- 月份选择器 → 切换查询月份
- 「导出Excel」`<a href download>` 链接（非按钮）

**API**：
- `GET /api/visits/summary?month=YYYY-MM` → 分组数据
- 导出链接：`GET /api/visits/summary/export?month=YYYY-MM`（浏览器直接下载，不走 axios）

---

### 1.4 LiveBoardPage（`/live-board`，现场实时看板）

**内容**：
- `<h1>现场实时看板</h1>`
- WebSocket 连接状态文字：`WebSocket连接状态：已连接/未连接`
- **主展示区**（根据 `realtimeStore.ledContent`）：
  - 通过：绿色卡片（`#e8f5e9`背景）—— `✓ 欢迎光临` + 访客姓名（28px）+ 欢迎词文案（18px灰色）
  - 拒绝：红色卡片（`#ffebee`背景）—— `无权限入场` + `原因：{reason}`（如有）
- **调试区**「模拟刷卡（调试用）」：4 个 label+input（card_uid 默认 `SIM-001`、visit_id 必填、姓名、来访日期-date类型）+「模拟刷卡」按钮
- **最近事件区**：`<ul>` 列出最近 20 条原始 WS 事件（`{timestamp} - {type} - {JSON字符串}`）——目前是原始 JSON dump，未做任何格式化展示

**交互元素**：
- 4 个受控输入框（文本/文本/文本/date）
- 「模拟刷卡」按钮 → 触发 `simulateCardRead`

**API**：
- `POST /api/debug/simulate-card-read`（body: `{card_uid, raw_payload: {visit_id?, name, visit_date}}`）
- 主内容驱动源是 WebSocket 推送（`led.content` / `card.verify.passed|failed`），非轮询 REST

---

### 1.5 CardManagementPage（`/cards`，写卡管理）

**内容**：
- `<h1>写卡管理</h1>`
- 区块一「待写卡访客」：表格（复选框列、姓名、身份、欢迎词），数据过滤为 `status === "welcome_ready"` 的访客；「批量写卡（{n}）」按钮
- 区块二「写卡记录」：表格（visit_id、card_uid、状态、错误信息、时间）

**交互元素**：
- 每行一个 `<input type="checkbox">` 勾选/取消勾选
- 「批量写卡（{n}）」按钮，`disabled` 条件：未选中任何行 → 触发批量写卡，成功后清空选中 + 刷新写卡记录和访客列表

**API**：
- `GET /api/visits`（前端本地过滤 `welcome_ready` 状态，接口本身支持 `visit_date`/`identity_type` 参数但此页未用）
- `GET /api/cards/write-log`
- `POST /api/cards/write`（body: `{visit_ids: number[]}`）→ `CardWriteResult[]`

---

### 1.6 TemplatesPage（`/templates`，欢迎词模板）

**内容**：
- `<h1>欢迎词模板</h1>`
- 表格：身份类型、模板文案（可编辑输入框）、保存按钮列
- 共 7 行模板（6 种身份 + "默认"）

**交互元素**：
- 每行一个受控 `<input>`（草稿态存于本地 `drafts` state，未保存前显示草稿值）
- 每行一个「保存」按钮 → 触发该行模板更新

**API**：
- `GET /api/templates` → `TemplateOut[]`
- `PUT /api/templates/{identity_type}`（路径参数是 URL-encode 后的中文枚举值，body: `{template_text}`）

---

### 1.7 WorkLogPage（`/work-logs`，工作日志）

**内容**：
- `<h1>工作日志</h1>`
- 两个筛选下拉：模块（7 个选项：registration/ai_writeup/card_write/verify/led/tts/system，含"全部模块"）、状态（success/failure/warning，含"全部状态"）
- 「导出 Excel」链接（蓝底白字按钮样式，唯一有品牌色内联样式的交互元素）
- 表格：时间、模块、动作、状态、详情

**交互元素**：
- 2 个 `<select>` 筛选器（联动触发查询）
- 「导出 Excel」下载链接

**API**：
- `GET /api/work-logs?module=&status=`
- 导出链接：`GET /api/work-logs/export?module=&status=&format=xlsx`

---

### 1.8 SettingsPage（`/settings`，系统设置）

**内容**：
- `<h1>系统设置</h1>`
- 只读展示当前设置：`Excel监听目录：{dir}`、`AI服务商：{provider}`、`AI Key已配置：是/否`、可选提示消息 `{message}`
- 两个输入：新的 Excel 监听目录（文本）、新的 AI Key（`type="password"`，掩码输入）
- 「保存」按钮

**交互元素**：
- 2 个受控输入框（草稿态，均可留空表示不修改）
- 「保存」按钮 → 触发设置更新（只提交非空字段）

**API**：
- `GET /api/settings` → `SettingsOut {excel_watch_dir, ai_provider, has_ai_api_key, cors_origins, message?}`（**AI Key 明文永不返回**，只有布尔标志）
- `PUT /api/settings`（body 中字段均可选：`{excel_watch_dir?, ai_api_key?}`）

---

### 1.9 DisplayPage（`/display`，独立全屏，展厅大屏）

**用途**：展厅入口处的大屏展示，深色背景（`#0a1929`），非管理员使用，无导航栏。

**内容**：
- 标题：`实时来访名单 · {今天日期，中文格式}`
- 今日访客列表卡片（深蓝背景 `#102a43`，最高 50vh 可滚动）：每行显示 日期 / 场次时间（截取 HH:MM）/ 姓名（加粗）/ 身份 / 状态（`verified` 显示为绿色"已入场"文字，其他状态显示原状态文字+橙色）
  - 空列表时显示 `暂无今日访客`
  - 每 5 秒轮询刷新（`refetchInterval: 5000`）
- 底部「最新」提示条（仅当有 `ledContent` 时出现）：
  - 通过：深绿背景（`#1b5e20`），42px 大字：`最新：{name} — {welcome_text}`
  - 拒绝：深红背景（`#b71c1c`），42px 大字：`无权限入场（{reason}）`

**交互元素**：无——纯展示页，无按钮/链接/输入。

**API**：
- `GET /api/visits/today`（每 5 秒轮询）
- WebSocket `led.content` 驱动底部提示条

---

### 1.10 MockLEDPane（`/mock-led`，独立全屏，模拟硬件 LED 屏）

**用途**：在没有真实 LED 硬件时，用浏览器全屏模拟现场 LED 显示屏（黑底、超大字号），配合 mock 适配器联调用。

**内容**：
- 纯黑背景，居中超大字（96px，加粗）：
  - 无内容时：`等待刷卡…`
  - 有内容且通过：`{name}  {welcome_text}`（白字）
  - 拒绝：`无权限入场`（红色 `#ff1744`），下方 48px 副文案 `（{reason}）`（浅红 `#ff8a80`）
- 进入页面自动尝试全屏（`requestFullscreen`，若浏览器拒绝则静默失败）

**交互元素**：
- 点击整个页面 → 再次尝试请求全屏（无按钮，点击区域是整个 `<div>`）

**API**：无直接 REST 调用，纯由 WebSocket `ledContent` 全局状态驱动。

---

## 2. 全部前端 API 接口一览表

| 方法 | 路径 | 定义文件 | 使用页面 | 说明 |
|---|---|---|---|---|
| GET | `/api/visits` | `api/visits.ts` | CardManagementPage | 支持 `visit_date`/`identity_type` 参数（未在现有页面用到筛选） |
| GET | `/api/visits/{id}` | `api/visits.ts` | （未使用） | 单访客详情，已封装未接入任何页面 |
| PATCH | `/api/visits/{id}` | `api/visits.ts` | （未使用） | 修改访客，已封装未接入任何页面 |
| GET | `/api/visits/today` | `api/visits.ts` | DashboardPage, DisplayPage | 今日来访 |
| GET | `/api/visits/summary?month=` | `api/visits.ts` | SummaryPage | 月度分组汇总 |
| GET | `/api/visits/summary/export?month=` | `api/visits.ts`（URL 构造，非 axios） | SummaryPage | 浏览器直接下载 xlsx |
| POST | `/api/import/preview` | `api/imports.ts` | RegistrationPage | multipart 文件上传 |
| POST | `/api/import/commit` | `api/imports.ts` | RegistrationPage | body `{preview_id}` |
| GET | `/api/templates` | `api/templates.ts` | TemplatesPage | 7 条模板 |
| PUT | `/api/templates/{identity_type}` | `api/templates.ts` | TemplatesPage | 中文路径参数 |
| POST | `/api/cards/write` | `api/cards.ts` | CardManagementPage | body `{visit_ids[]}` |
| GET | `/api/cards/write-log` | `api/cards.ts` | CardManagementPage | 支持可选 `visit_id` 参数 |
| POST | `/api/debug/simulate-card-read` | `api/debug.ts` | LiveBoardPage | 仅 Mock 环境可用 |
| GET | `/api/verify-log` | `api/logs.ts` | （未使用） | 已封装未接入任何页面 |
| GET | `/api/work-logs?module=&status=` | `api/logs.ts` | WorkLogPage | |
| GET | `/api/work-logs/export?...` | `api/logs.ts`（URL 构造） | WorkLogPage | 浏览器直接下载 xlsx |
| GET | `/api/adapters/status` | `api/adapters.ts` | DashboardPage | 4 适配器快照 |
| GET | `/api/settings` | `api/settings.ts` | SettingsPage | |
| PUT | `/api/settings` | `api/settings.ts` | SettingsPage | |
| WS | `/ws/realtime` | `stores/realtimeStore.ts` | LiveBoardPage, DisplayPage, MockLEDPane, DashboardPage(部分), AdapterOfflineBanner(全局) | 4 种消息类型见下 |

**WebSocket 消息类型**（扁平信封，`type` 字段判别）：
1. `card.verify.passed` — `{timestamp, visit_id, card_uid}`
2. `card.verify.failed` — `{timestamp, visit_id, card_uid}`
3. `adapter.heartbeat` — `{timestamp, adapter_name, status, detail}`
4. `led.content` — `{timestamp, name, welcome_text, is_rejection, reason}`

**注意**：`GET /api/visits/{id}`、`PATCH /api/visits/{id}`、`GET /api/verify-log` 这三个接口已在前端封装（`api/visits.ts`, `api/logs.ts`）但**目前没有任何页面调用**——如果视觉重设计中想加"访客详情/编辑"或"现场校验历史"页面，可以直接复用这些封装。

---

## 3. 核心数据类型（决定表格列、状态徽标、筛选项设计）

- **`VisitStatus`**：`pending → welcome_ready → card_written → verified | rejected`（状态机，适合做 5 段式状态徽标/进度条设计）
- **`IdentityType`**（6种）：企业领导 / 企业员工 / 学校老师 / 大学生 / 中小学生 / 政府官员；模板额外有"默认"
- **`AdapterHealthStatus`**：`online | offline | error`（4 个适配器：nfc/led/tts/ai）
- **`WriteStatus`**：`success | failed | pending`
- **`VerifyResult`** + **`FailReason`**：`pass|fail`，失败原因 `name_mismatch|date_mismatch|card_not_found`
- **`LogModule`**（7种）/ **`LogStatus`**（3种，success/failure/warning）

---

## 4. 给设计 Agent 的现状总结（非设计意见，纯客观事实）

- 8 个管理后台页面共享同一套导航（8 项，无分组/无图标），2 个独立全屏"硬件屏幕"页面（现场大屏 + 模拟 LED）不带导航。
- 所有列表页都是原生 `<table>`，无分页、无排序、无搜索框（除 WorkLogPage 有 2 个下拉筛选）。
- 状态类字段（VisitStatus/WriteStatus/AdapterHealthStatus/LogStatus）目前都以纯文字展示，没有颜色/图标/徽标系统。
- 仅有 3 处出现过强调色内联样式：AdapterOfflineBanner（红）、LiveBoardPage 的通过/拒绝卡片（绿/红）、WorkLogPage 导出按钮（蓝）——其余全部是浏览器默认样式。
- DisplayPage 和 MockLEDPane 是唯一两个有完整视觉设计意图的页面（深色大屏风格），可作为"未来风格"的一个参考起点，但也可以整体推翻重做。
- 全局 `index.css` 里的 `#root` 定宽居中容器是 Vite 脚手架残留，不代表任何设计意图，可以整体废弃。
