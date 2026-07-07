# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

#### 现场欢迎闭环（§三.3 §八 第 6/7 条）
- **`OnsiteWelcomeService`**（`backend/app/services/onsite_welcome_service.py`）— 订阅 `card.verify.passed` / `card.verify.failed`，驱动 LED 显示 + TTS 朗读 + 蜂鸣 + work_log。这是审计发现的 §三.3 "现场欢迎"在 Day 3 实现里完全缺失的修复：之前 LED/TTS adapter 被构造但没有任何事件触发。
- **`RealTTSAdapter`**（`backend/app/adapters/tts/real.py`）— 包装 `pyttsx3` 跨平台离线 TTS：macOS 走 nsss，Windows 走 SAPI5，Linux 走 espeak。`_build_tts_adapter` 构造失败时降级到 Mock。蜂鸣跨平台实现：macOS 生成 880Hz 正弦 wav + `afplay`、Windows `winsound.Beep`、Linux `speaker-test`。蜂鸣默认 1.5 秒（§三.3 "长音"）。
- **`TTSAdapter.play_beep(duration_seconds=1.5)`** 新增抽象方法 — 把蜂鸣通道和语音通道合并到同一 Adapter，符合 §三.3 "复用同一音响输出通道"。
- **`LEDContent` dataclass**（`backend/app/schemas/led.py`）— 统一 LED 显示帧格式，`is_rejection=True` 时所有屏幕显示"无权限入场"。

#### 新 API endpoint
- **`GET /api/work-logs/export?module=&status=&format=xlsx`** — §三.4 工作日志可下载为 Excel。

#### 新事件 / 状态机
- **`led.content` WS topic** — `/ws/realtime` 转发 LED 显示内容给前端，让 `/display`、`/mock-led`、`/live` 实时刷新。
- **`VisitStatus.REJECTED` 现在可达**（`backend/app/services/verify_service.py`）— 校验失败时 visit 状态从 `CARD_WRITTEN` 转为 `REJECTED`。Day 3 状态机枚举值已存在但无任何路径写入。

#### 新前端页面
- **`/display`（DisplayPage.tsx）** — 现场大屏：当日来访名单滚动 + 最新事件。深色背景，5 秒自动刷新 `/api/visits/today`。
- **`/mock-led`（MockLEDPane.tsx）** — 模拟 LED 全屏：黑底 96px 白字姓名+欢迎词，拒绝时红色"无权限入场"。点击可手动全屏。这两个路由放在 `NavLayout` 外（不显示管理后台导航），让全屏 UX 不被破坏。
- **`AdapterOfflineBanner`（NavLayout 顶部）** — 任何 `nfc` / `led` / `tts` / `ai` adapter 心跳非 `online` 时显示红色横条（§六.3 / §八 第 12 条）。

#### 可靠性
- **WS 指数退避重连**（`frontend/src/stores/realtimeStore.ts`）— `1s → 2s → 4s → 8s → 16s → 30s` 上限，`onopen` 时重置 `reconnectAttempt`。之前断线后 `connected` 永远 false，必须手动刷新。
- **PII 脱敏**（`backend/app/api/imports.py::preview_import`）— `POST /api/import/preview` 现在对每行 `data["身份证号"]` 调用 `mask_id_number`（`110********0011`）。Day 3 这一路径**漏了**——之前浏览器拿到原始 18 位身份证号。修复了 §六.2 PII 漏洞。

#### 测试
- 后端测试从 72 → 89（+ 17 新测试）。新增覆盖：TTSAdapter 接口契约、LEDContent mock、TTS RealAdapter monkeypatch、OnsiteWelcomeService 端到端、PII 脱敏、工作日志导出、WS topic 白名单、VisitStatus.REJECTED 转换、手动写卡回归。

### Changed

#### Breaking / Behavior changes
- **写卡改为手动触发**（`backend/app/main.py`、`app/services/card_service.py`、`app/api/cards.py`）— §三.2 spec 要求"值班人员手动触发写卡"，Day 3 实现里写卡被 `welcome.generated` 事件自动触发，导致 `CardManagementPage` 的"待写卡访客"列表始终为空。修复后：
  - `main.py` 不再把 `welcome.generated` 接到 `CardService`
  - `CardService.handle_welcome_generated` 重命名为 `write_card_for_visit`（语义准确）
  - 状态机严格 `PENDING → WELCOME_READY → CARD_WRITTEN → VERIFIED|REJECTED`
  - `CardManagementPage` 现在能正确列出 `welcome_ready` 状态的访客，勾选 + 点"批量写卡"按钮手动写卡

#### Frontend type 重构
- `RealtimeEvent` 从嵌套 `{type, timestamp, payload: {...}}` 改为扁平 `{type, timestamp, ...fields}`，让前端 TS discriminated union 能正确 narrow 各变体。WS 服务端 `_forward_topic` 改为 `{**payload}` 展开。

#### Re-export 清理
- `LEDContent` 从 `backend/app/adapters/base.py`（旧 Pydantic 类）迁移到 `backend/app/schemas/led.py`（dataclass）。`base.py` re-export 以保持向后兼容。

### Fixed
- **`MockLEDAdapter.health_check()` 返回类型修正**（`backend/app/adapters/led/mock.py`）— 之前返回裸字符串 `"online"`，但抽象基类签名是 `-> AdapterHealth`。`_poll_adapter_heartbeats` 调用 `health.status` 会 `AttributeError`，导致 LED 心跳从未写入 `adapter_status` 表。
- **`/ws/realtime` envelope 扁平化**（`backend/app/api/ws.py`）— 服务端现在 `{type, timestamp, adapter_name, status, ...}` 而不是嵌套 `payload`。前端不再读 `undefined`。

### Removed
- 旧的 `LEDContent` Pydantic 类（`app/adapters/base.py`）— 已被 `app/schemas/led.py` 的 dataclass 替代。
- 中间类型 `RealtimeEventPayload` / `CardVerifyPayload` / `AdapterHeartbeatPayload` / `LedContentPayload` — 扁平化后冗余。
- `card.verify.{passed,failed}` 事件 payload 嵌套结构 — 跟随 envelope 扁平化统一。

### Security
- §六.2 PII：`POST /api/import/preview` 现在 mask 身份证号（参见上文 PII 脱敏）。

---

## [0.1.0] - 2026-07-03 — Day 3 完成态

首个可演示状态：导入 → AI 写欢迎词 → 写卡 → 校验的链路跑通，但 §三.3 现场欢迎闭环未实现（LED/TTS 死代码），离线告警、PII preview 脱敏、状态机 REJECTED 等多个审计项缺失。

### Added (Day 1-3)
- 四层架构：数据 → 集成 → 服务 → 表现
- 6 个 SQLAlchemy ORM 模型 + 4 个 mock adapter + 1 个 QwenAIAdapter
- 6 个业务服务（Registration/AIWriteup/Card/Verify/Log/AdapterStatus）
- EventBus pub/sub + 5 个 consumer
- Excel 自动监听 + 手动上传两条入口
- 7 个前端页面 + zustand WS store + TanStack Query
- Day 0–2 决策：4 层架构、自然月归属、6 类身份枚举、单屏同步显示、不做登录、不做防重放、不做 Docker
- 73 个后端测试（72 pass + 1 documented-red）

[Unreleased]: https://github.com/your-org/AITIC-reception/compare/4947658...HEAD
[0.1.0]: https://github.com/your-org/AITIC-reception/releases/tag/0.1.0