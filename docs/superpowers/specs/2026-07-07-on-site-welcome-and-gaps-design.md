# 现场欢迎闭环 + 审计差距修复 · 设计文档

**日期**：2026-07-07
**作者**：brainstorming session output
**状态**：待用户审阅 → 实施计划
**对应审计**：`docs/superpowers/completion/` 内一份全面审计报告（83 项中 17 ❌ 缺失 / 22 ⚠️ 部分）
**目标 spec**：`docs/TARGET.md` §二.2 用户旅程 + §三.3 现场欢迎模块 + §六.3 可靠性 + §八 验收清单

---

## 1. 背景与目标

### 1.1 当前状态

四层架构已经完整跑通（数据 → 集成 → 服务 → 表现），73 个测试 72 ✅ + 1 个文档化红。但
**§三.3 现场欢迎模块的 5 个核心动作在运行系统中是死代码**——适配器被构造、被注入 `app.state`，
但 `card.verify.passed/failed` 事件没有任何 consumer 去驱动 LED/TTS。

加之审计发现的其他 P1/P2 差距，需要一次性集中修复以满足 §八 验收清单。

### 1.2 用户决策汇总（来自 brainstorming session）

| # | 决策 | 出处 |
|---|---|---|
| U1 | 欢迎词回写覆盖原始 Excel — **不做**（仅存 DB） | 用户 #1 |
| U2 | LiveBoard 显示访客姓名 — **必做** | 用户 #2 |
| U3 | TTS 严格本地、跨平台 — **用 `pyttsx3`**（不用 macOS 自带 say，不用 edge-tts） | 用户 #1 |
| U4 | LED "无权限入场" 字样 — **加接口，MockLED 接好** | 用户 #4 |
| U5 | TTS 蜂鸣通道接口 — **必加 `play_beep(duration_seconds)`** | 用户 #5 |
| U6 | 实时大屏（live + 名单）— **必做** | 用户 #6 |
| U7 | 当日来访名单 — **新路由 `/display`**，跟 LED 分开 | 用户 #7 |
| U8 | 离线红色告警 — **只在管理后台 NavLayout**，不随机演示 | 用户 #8 + #3 |
| U9 | 预览表必须全 9 列 | 用户 #9 |
| U10 | 预览表编辑控件 — **不做** | 用户 #10 |
| U11 | WS 指数退避重连 — **必做** | 用户 #11 |
| U12 | 工作日志导出（前端按钮 + 后端端点）— **必做** | 用户 #12 |
| U13 | PII 在 preview 路径不泄漏 — **必修复** | 用户 #13 |
| U14 | VerifyService 失败路径写 `REJECTED` — **必做** | 用户 #14 |
| U15 | 模拟 LED 屏 — **`/mock-led` 单独路由，全屏黑底大字** | 用户 #15 |
| U16 | 蜂鸣器 — **后端直接播**，不依赖浏览器 | 用户决策回复 |

---

## 2. 范围

### 2.1 在范围内（本次实现）

| ID | 改动 | 影响 spec 条目 |
|---|---|---|
| F1 | 新增 `OnsiteWelcomeService` 订阅 `card.verify.passed/failed`，驱动 LED/TTS/beep | §八 第 6、7 条 |
| F2 | `TTSAdapter` 接口加 `play_beep(duration_seconds)` | §三.3 蜂鸣通道 |
| F3 | `MockTTSAdapter` + 新 `RealTTSAdapter(pyttsx3)` 实现 `play_beep` | §六.1 离线 |
| F4 | `MockLEDAdapter.show_rejected` 真正存"无权限入场"字样 | §三.3 拒绝视觉 |
| F5 | `VerifyService` 失败路径写 `Visit.status = REJECTED` | §四 状态机 |
| F6 | `POST /api/import/preview` 的 `data` 走 `mask_id_number` | §六.2 PII |
| F7 | `LiveBoardPage` 渲染 `name` + `welcome_text`（取自 WS payload） | §三.3 LED in-app 等价 |
| F8 | 新路由 `/display`（现场大屏）：滚动当日来访名单 + 最新事件 | §三.3 当日名单 |
| F9 | 新路由 `/mock-led`（模拟 LED 屏）：全屏黑底大字 | 用户决策 U15 |
| F10 | `NavLayout` 顶部 `<AdapterOfflineBanner />`，任何 adapter 非 online 即红色横条 | §六.3 + §八 第 12 条 |
| F11 | `RegistrationPage` 预览表展示 9 列 | §三.1 步骤 2 逐行确认 |
| F12 | `realtimeStore` WS 指数退避重连 | §六.3 |
| F13 | `GET /api/work-logs/export?module=&status=&format=xlsx` + `WorkLogPage` 导出按钮 | §三.4 |
| F14 | `RealTTSAdapter` 异步化（`asyncio.to_thread` 包装 pyttsx3 阻塞 API） | 性能 / FIFO |
| F15 | 路由顺序修正（新增 `/display` 和 `/mock-led` 必须在 `/{visit_id}` 之前——其实不影响，因为这是前端路由，但要确保后端不冲突） | 防御性 |

### 2.2 不在范围（明确不做）

- ❌ 欢迎词回写覆盖原始 Excel（U1）
- ❌ 预览表行内编辑控件（U10）
- ❌ 离线告警的随机演示（U8）
- ❌ 登录/多用户/权限（§七.1）
- ❌ 防重放校验（§七.2）
- ❌ LED 多屏分组（§七.3）
- ❌ Docker / 云部署（§七.4）
- ❌ 移动端 / 小程序（§七.5）
- ❌ 真实硬件 Adapter 实现（Day 4 任务）——本次只确保接口完整、Mock 行为正确

---

## 3. 架构

### 3.1 服务层新增：`OnsiteWelcomeService`

```python
# backend/app/services/onsite_welcome_service.py
class OnsiteWelcomeService:
    """订阅 card.verify.{passed,failed}，驱动 LED + TTS + 蜂鸣。

    与 VerifyService 解耦：Verify 只判断"通过/失败 + 改 DB 状态 + 发事件"，
    本服务只负责"翻译事件 → 硬件副作用"。一个事件多个副作用并行派发。
    """

    def __init__(self, led_adapter, tts_adapter, event_bus):
        self._led = led_adapter
        self._tts = tts_adapter
        self._bus = event_bus

    async def handle_card_verify_passed(self, payload: dict) -> None:
        visit_id = payload["visit_id"]
        content = await self._load_content(visit_id)  # 从 DB 取 name + welcome
        # 三个动作可以并行（互不依赖）
        await asyncio.gather(
            self._led.display(screen_ids=["all"], content=content),
            self._tts.enqueue_speech(content.welcome_text),
            self._bus.publish("led.displayed", {...}),
            self._bus.publish("tts.spoken", {...}),
        )

    async def handle_card_verify_failed(self, payload: dict) -> None:
        # LED 全屏显示"无权限入场" + TTS 蜂鸣 1.5s
        await asyncio.gather(
            self._led.show_rejected(screen_ids=["all"], reason=payload.get("fail_reason", "")),
            self._tts.play_beep(duration_seconds=1.5),
        )
```

**`screen_ids=["all"]`** 是新约定的"所有 LED 同步"标志——`MockLEDAdapter` 收到 `"all"`
就向 `_displayed` / `_rejected` 列表追加一条无 screen_ids 的记录（便于模拟 LED 页渲染）。

### 3.2 TTS Adapter 重设计

```python
# backend/app/adapters/base.py
class TTSAdapter(ABC):
    @abstractmethod
    async def enqueue_speech(self, text: str) -> None: ...

    @abstractmethod
    async def play_beep(self, duration_seconds: float = 1.5) -> None:
        """长音蜂鸣。复用同一音响输出通道，不依赖网络（§3.3）。"""


# backend/app/adapters/tts/real.py  （新增）
class RealTTSAdapter(TTSAdapter):
    """用 pyttsx3 的跨平台离线 TTS。"""

    def __init__(self, voice_id: str | None = None, rate: int = 150) -> None:
        import pyttsx3
        self._engine = pyttsx3.init()
        if voice_id:
            self._engine.setProperty("voice", voice_id)
        self._engine.setProperty("rate", rate)

    async def enqueue_speech(self, text: str) -> None:
        # pyttsx3 是阻塞的，丢到线程池不卡事件循环
        await asyncio.to_thread(self._speak_blocking, text)

    def _speak_blocking(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()

    async def play_beep(self, duration_seconds: float = 1.5) -> None:
        # 直接生成正弦波 wav + afplay (mac) / start / wmp 等（见 §3.2.1）
        await asyncio.to_thread(self._beep_blocking, duration_seconds)

    def _beep_blocking(self, duration_seconds: float) -> None:
        # 跨平台：mac 用 afplay + 系统自带 wav 资源；win 用 winsound.Beep；
        # Linux 用 speaker-test 或 paplay
        if sys.platform == "darwin":
            # 用 say "—" 之类的 hack 太脏；正经做法：生成 880Hz 正弦 wav 再 afplay
            _play_sine_beep_macos(duration_seconds, freq=880)
        elif sys.platform == "win32":
            import winsound
            winsound.Beep(880, int(duration_seconds * 1000))
        else:  # linux
            import subprocess
            subprocess.run(["speaker-test", "-t", "sine", "-f", "880",
                            "-l", "1", "-s", "1"], timeout=duration_seconds + 0.5,
                           capture_output=True)
```

**§3.2.1 macOS 蜂鸣实现**——`afplay` 需要 wav 文件。简单方案：用 Python 内置 `wave` 模块
生成 880Hz 正弦波到 `/tmp/beep_<ts>.wav`，再 `subprocess.run(["afplay", path])`，
播完删除。约 30 行代码，零依赖。

**Windows 路径**：用 `winsound.Beep(freq, duration_ms)`，纯系统调用，最干净。

### 3.3 LED Adapter 改造

```python
# backend/app/adapters/led/mock.py 改造
@dataclass
class LEDContent:
    name: str
    welcome_text: str
    is_rejection: bool = False
    reason: str = ""

class MockLEDAdapter(LEDAdapter):
    def __init__(self):
        self.displayed: list[LEDContent] = []   # 所有屏的内容历史（实际只要 latest）
        self.rejected: list[LEDContent] = []

    async def display(self, screen_ids: list[str], content: LEDContent) -> None:
        self.displayed.append(content)
        # 同步给 WS（已有 adapter.heartbeat 推送，加一个 led.content 推送）
        await self._publish_led_update(content)

    async def show_rejected(self, screen_ids: list[str], reason: str = "") -> None:
        content = LEDContent(name="", welcome_text="无权限入场",
                             is_rejection=True, reason=reason)
        self.rejected.append(content)
        await self._publish_led_update(content)
```

**前端 `/mock-led` 页面**订阅 `led.content`（或加进现有 WS topic）——WS forwarder 加一个订阅。

### 3.4 PII 修复

```python
# backend/app/api/imports.py 改造
def _scrub_pii_in_preview(data: dict) -> dict:
    """preview 阶段把身份证号脱敏，防止值班人员浏览器拿到明文。"""
    raw = data.get("身份证号")
    if isinstance(raw, str) and raw.strip():
        data = {**data, "身份证号": mask_id_number(raw)}
    return data

# 在 preview_import 里
preview_rows.append(
    ImportPreviewRow(
        row_number=row.row_number,
        data=_scrub_pii_in_preview(row.data),  # ← 改动点
        errors=row.errors,
        is_valid=row.is_valid,
    )
)
```

### 3.5 状态机修复

```python
# backend/app/services/verify_service.py
async def handle_card_verify_requested(self, payload):
    ...
    if matched:
        visit.status = VisitStatus.VERIFIED
        await self._bus.publish("card.verify.passed", {...})
    else:
        visit.status = VisitStatus.REJECTED          # ← 新增
        await self._bus.publish("card.verify.failed", {...})
    session.commit()
```

### 3.6 前端新增页面

#### `/display` — 现场大屏（名单滚动）

```
┌────────────────────────────────────────────────────┐
│  实时来访名单  ·  2026-07-07           🟢 NFC 在线  │
├────────────────────────────────────────────────────┤
│  ✓ 09:00  王企业    企业领导    已入场              │
│  ✓ 10:30  赵老师    学校老师    已入场              │
│  ✓ 14:00  周小朋友  中小学生    已入场              │
│  ... (滚动)                                        │
├────────────────────────────────────────────────────┤
│  最新：孙学生 (大学生) 14:35                        │
│  孙学生 同学，欢迎参观                              │
└────────────────────────────────────────────────────┘
```

#### `/mock-led` — 模拟 LED 屏

```
┌────────────────────────────────────────────────────┐
│                                                    │
│                                                    │
│              王企业  先生，欢迎您                   │
│                                                    │
│                                                    │
└────────────────────────────────────────────────────┘
```
全屏黑底，72px+ 字号，居中。拒绝时显示红色"无权限入场"。

### 3.7 NavLayout 加红色告警横条

```tsx
// frontend/src/components/AdapterOfflineBanner.tsx
export function AdapterOfflineBanner() {
    const statuses = useRealtimeStore(s => s.adapterStatuses);
    const offline = Object.entries(statuses).filter(([_, v]) => v !== "online");
    if (offline.length === 0) return null;
    return (
        <div style={{ background: "#d32f2f", color: "white", padding: "8px 16px", ... }}>
            ⚠️ 硬件离线：{offline.map(([n]) => n.toUpperCase()).join(" / ")}
        </div>
    );
}
```

### 3.8 WS 指数退避

```typescript
// frontend/src/stores/realtimeStore.ts
function scheduleReconnect() {
    const attempt = state.reconnectAttempt;
    const delay = Math.min(1000 * Math.pow(2, attempt), 30_000);
    setTimeout(connect, delay);
    set({ reconnectAttempt: attempt + 1 });
}
socket.onclose = () => {
    set({ connected: false, socket: null });
    scheduleReconnect();        // ← 新增
};
socket.onopen = () => {
    set({ reconnectAttempt: 0 }); // ← 重置
};
```

### 3.9 工作日志导出

**后端**：`api/logs.py` 新增
```python
@router.get("/work-logs/export")
async def export_work_logs(
    module: LogModule | None = Query(None),
    status: LogStatus | None = Query(None),
    format: Literal["xlsx"] = "xlsx",
    session_factory = Depends(get_session_factory),
):
    # 同 /summary/export 的实现风格：查 DB → pandas → xlsx → StreamingResponse
```

**前端**：`api/logs.ts` 加 `workLogExportUrl(...)`，`WorkLogPage.tsx` 顶部加导出按钮。

### 3.10 预览表 9 列展示

```tsx
// RegistrationPage.tsx 改造预览表
<thead>
    <tr>
        <th>行号</th>
        <th>姓名</th>
        <th>来访日期</th>
        <th>计划场次时间</th>
        <th>手机号</th>
        <th>国籍</th>
        <th>身份证号</th>
        <th>性别</th>
        <th>单位</th>
        <th>身份</th>
        <th>错误</th>
    </tr>
</thead>
```

身份证号那一列因为 §3.4 修复，已经自动脱敏（`110********0011`）。

---

## 4. 数据模型

**无新增表**。仅复用：
- `visits` — 状态机扩展（`REJECTED` 现在真的被写了）
- `work_log` — 加 LED/TTS 失败/成功的日志条目（由 `OnsiteWelcomeService` 发布）
- `adapter_status` — 已存在，banner 直接消费

**LogModule 枚举已包含 `led` / `tts` / `system`**——之前没人写，现在有来源了。

---

## 5. 测试策略

### 5.1 后端

| 测试文件 | 测试目标 |
|---|---|
| `test_onsite_welcome_service.py` | Mock LED/TTS，断言 passed → display+speech、failed → show_rejected+beep |
| `test_tts_adapter.py` | RealTTSAdapter 单元测试（跳过实际发声，断言调用参数） |
| `test_verify_service.py` 新增 | 失败路径 visit.status == REJECTED |
| `test_api_imports.py` 新增 | preview 路径返回的 data[身份证号] 已被脱敏 |
| `test_work_log_export.py` | GET /api/work-logs/export 返回 .xlsx |

**端到端**：`tests/test_end_to_end.py` 已有，扩展断言 verify passed 之后 LED mock 收到 display 调用。

### 5.2 前端

无新测试（沿用 Day-3 决策）。验证方式：
- `pnpm exec tsc --noEmit` 必须 0 error
- `pnpm build` 必须成功
- 手动走完：导入 Excel → 写卡 → 模拟刷卡 → 看 /display + /mock-led + LiveBoard + NavLayout

### 5.3 验收清单（自检）

跑通后逐项核对 §八：

- [x] §八-3 欢迎词回写 — **改 §八验收文本**为"仅持久化到 DB"（用户决策 U1）
- [x] §八-6 verify pass 三动作 — 修复
- [x] §八-7 verify fail 三动作 — 修复
- [x] §八-12 adapter 离线红色告警 — 修复
- [x] §三.3 当日来访名单 — 修复（新路由 /display）
- [x] §六.2 PII preview 不泄漏 — 修复
- [x] §四 状态机 REJECTED 可达 — 修复
- [x] §六.3 WS 可靠性 — 修复（指数退避）

---

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| pyttsx3 在 macOS 首次调用 3 秒延迟（已实测） | Mock 模式下不调用 RealTTS；测试用 Mock |
| macOS `afplay` 需要 wav 文件 | 临时 wav 写到 `/tmp/`，自带清理 |
| `OnsiteWelcomeService` 跟 `VerifyService` 重复订阅相同事件 | 服务层无相互 import（CLAUDE.md 项目规则），通过 EventBus 自然解耦 |
| TTS 在 Windows Server 无音频设备时崩溃 | `RealTTSAdapter.__init__` try/except，失败时 log warning 但不 raise |
| LED 模拟页 WS 断开后不更新 | WS 指数退避已在范围内 |
| `/display` 路由跟 `/{visit_id}` 冲突 | `/display` 是前端路由不是后端，不冲突；但要避免后端 `/api/visits/display` 跟 `/{visit_id}` 冲突——不暴露这个端点即可 |
| LiveBoardPage 跟 /display 内容重叠 | LiveBoard 是管理工具（含 debug 按钮），/display 是纯展示，不重叠 |

---

## 7. 文件变更清单（实施计划会细化）

### 新增
- `backend/app/services/onsite_welcome_service.py`
- `backend/app/adapters/tts/real.py`
- `backend/app/schemas/led.py` (LEDContent dataclass)
- `frontend/src/pages/DisplayPage.tsx`
- `frontend/src/pages/MockLEDPane.tsx`
- `frontend/src/components/AdapterOfflineBanner.tsx`
- `frontend/src/api/workLogExport.ts` (合并到 logs.ts)
- `tests/test_onsite_welcome_service.py`
- `tests/test_tts_real_adapter.py`

### 修改
- `backend/app/adapters/base.py` (TTSAdapter 加 play_beep)
- `backend/app/adapters/tts/mock.py` (实现 play_beep)
- `backend/app/adapters/led/mock.py` (LEDContent 类型)
- `backend/app/services/verify_service.py` (REJECTED)
- `backend/app/api/imports.py` (PII scrub)
- `backend/app/api/logs.py` (export endpoint)
- `backend/app/main.py` (注册 OnsiteWelcomeService consumer)
- `backend/app/api/ws.py` (新增 led.content topic)
- `frontend/src/router.tsx` (新路由)
- `frontend/src/pages/LiveBoardPage.tsx` (name + welcome)
- `frontend/src/pages/RegistrationPage.tsx` (9 列)
- `frontend/src/pages/WorkLogPage.tsx` (导出按钮)
- `frontend/src/components/NavLayout.tsx` (Banner)
- `frontend/src/stores/realtimeStore.ts` (重连)

---

## 8. 验收（Definition of Done）

实施完成后必须全部 ✅：

1. `uv run pytest -v` 全部通过（新增测试 + 旧的 72 + 1 个文档化红 = 至少 78 测试）
2. `pnpm exec tsc --noEmit` 0 error
3. `pnpm build` 成功
4. 手动跑通：Excel → 写卡 → 模拟刷卡 → 看三个显示面（LiveBoard / Display / MockLED）
5. 模拟失败刷卡 → 听到（或看到播放记录）蜂鸣 + LED 显示"无权限入场"
6. 后端日志里看到 `module=led` / `module=tts` / `module=system` 的条目
7. 拔掉后端进程 5s 再启动 → 前端 WS 自动指数退避重连，无需手动刷新
8. `GET /api/work-logs/export?module=verify&status=success` 返回有效 xlsx
9. 上传 Excel 时，preview 响应里 `data["身份证号"]` 是脱敏的
10. NavLayout 顶部在任何 adapter 离线时显示红色横条

---

**待用户审阅 → 批准后进入 writing-plans skill。**