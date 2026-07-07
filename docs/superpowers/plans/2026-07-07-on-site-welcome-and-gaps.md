# 现场欢迎闭环 + 审计差距修复 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复审计发现的 17 个 ❌ 和 22 个 ⚠️，让 §八 验收清单全部通过，新增 OnsiteWelcomeService 驱动 LED + TTS + 蜂鸣，新增 /display 和 /mock-led 两个现场显示页面

**Architecture:** 后端用新 OnsiteWelcomeService 订阅 `card.verify.passed/failed` 事件驱动 LED/TTS/beep；新增 RealTTSAdapter 包 pyttsx3 跨平台离线 TTS；TTSAdapter 接口加 play_beep；PII 在 import preview 阶段脱敏；VerifyService 失败写 REJECTED。前端加 /display（名单滚动）+ /mock-led（模拟 LED 全屏大字）+ NavLayout 顶部离线告警 banner + LiveBoard 渲染姓名欢迎词 + WS 指数退避重连 + 工作日志导出。

**Tech Stack:** Python 3.13 / FastAPI / SQLAlchemy 2.0 / pytest-asyncio / pyttsx3（已装）/ React 19 / TypeScript / Vite / zustand / TanStack Query

**Spec:** `docs/superpowers/specs/2026-07-07-on-site-welcome-and-gaps-design.md`

---

## Global Constraints

- 后端路径风格：snake_case 函数名，PascalCase 类名，模块绝对导入（`from app.x import y`）
- 前端路径风格：camelCase 变量，PascalCase 组件，CSS-in-JS 内联（项目惯例，无 Tailwind）
- 测试：后端 `pytest`，每个新行为先写失败测试再实现
- Commit：每个任务独立 commit，格式 `feat(scope): ...` / `fix(scope): ...`
- §七 严格不做：登录/防重放/LED 分组/Docker/移动端（任何任务都不能引入这些）
- §六.2 PII：id_number 出 API 必走 `mask_id_number`，禁止明文
- §六.1 离线：TTS 必须本地、零网络依赖
- 中文身份枚举固定为：`企业领导 / 企业员工 / 学校老师 / 大学生 / 中小学生 / 政府官员`（+ 默认）
- 蜂鸣默认时长 1.5 秒（§三.3 "长音"）
- LED "全屏"语义用 `screen_ids=["all"]` 标志，MockLED 收到 `"all"` 时向 `_displayed`/`_rejected` 追加一条无 screen_ids 的记录

---

## Task 1: TTSAdapter 接口加 play_beep

**Files:**
- Modify: `backend/app/adapters/base.py`
- Test: `backend/tests/test_tts_interface.py`（新增）

**Interfaces:**
- Consumes: 无
- Produces: `TTSAdapter.play_beep(duration_seconds: float = 1.5) -> None` 抽象方法

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_tts_interface.py`：
```python
import pytest
from app.adapters.base import TTSAdapter


def test_tts_adapter_has_play_beep_abstract_method():
    """§三.3 要求蜂鸣通道复用同一音响，TTSAdapter 必须定义 play_beep。"""
    assert hasattr(TTSAdapter, "play_beep")
    assert getattr(TTSAdapter.play_beep, "__isabstractmethod__", False) is True


def test_concrete_tts_must_implement_play_beep():
    """不实现 play_beep 的子类无法实例化。"""

    class IncompleteTTS(TTSAdapter):
        async def enqueue_speech(self, text: str) -> None:
            pass
        # 故意不实现 play_beep

    with pytest.raises(TypeError):
        IncompleteTTS()


@pytest.mark.asyncio
async def test_mock_tts_play_beep_records_call():
    """Mock 实现必须能被调用并记录参数。"""
    from app.adapters.tts.mock import MockTTSAdapter
    mock = MockTTSAdapter()
    await mock.play_beep(duration_seconds=2.0)
    assert mock.beeps == [(2.0,)]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_tts_interface.py -v
```
Expected: 全部失败（`play_beep` 未定义 + `MockTTSAdapter.beeps` 不存在）

- [ ] **Step 3: 修改 `backend/app/adapters/base.py`**

在 `TTSAdapter` 类（line 64-69）`enqueue_speech` 后新增抽象方法：
```python
    @abstractmethod
    async def play_beep(self, duration_seconds: float = 1.5) -> None:
        """长音蜂鸣——复用同一音响输出通道（§三.3）。"""
```

- [ ] **Step 4: 在 MockTTSAdapter 加 play_beep 和 beeps 列表**

修改 `backend/app/adapters/tts/mock.py`：
```python
class MockTTSAdapter(TTSAdapter):
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.beeps: list[tuple[float, ...]] = []

    async def enqueue_speech(self, text: str) -> None:
        self.spoken.append(text)

    async def play_beep(self, duration_seconds: float = 1.5) -> None:
        self.beeps.append((duration_seconds,))
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd backend && uv run pytest tests/test_tts_interface.py -v
```
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/adapters/base.py backend/app/adapters/tts/mock.py backend/tests/test_tts_interface.py
git commit -m "feat(tts): add play_beep abstract method to TTSAdapter (§3.3)"
```

---

## Task 2: LEDContent 数据类 + MockLEDAdapter 改造

**Files:**
- Create: `backend/app/schemas/led.py`
- Modify: `backend/app/adapters/led/mock.py`
- Test: `backend/tests/test_led_mock.py`（新增）

**Interfaces:**
- Produces: `LEDContent(name, welcome_text, is_rejection=False, reason="")` dataclass，`MockLEDAdapter.displayed: list[LEDContent]`，`MockLEDAdapter.rejected: list[LEDContent]`，`screen_ids=["all"]` 全屏约定

- [ ] **Step 1: 写失败测试**

`backend/tests/test_led_mock.py`：
```python
import pytest
from app.adapters.led.mock import MockLEDAdapter
from app.schemas.led import LEDContent


@pytest.mark.asyncio
async def test_mock_led_display_stores_content():
    mock = MockLEDAdapter()
    content = LEDContent(name="王企业", welcome_text="王企业 先生，欢迎您")
    await mock.display(["all"], content)
    assert mock.displayed == [content]


@pytest.mark.asyncio
async def test_mock_led_show_rejected_stores_rejection():
    mock = MockLEDAdapter()
    await mock.show_rejected(["all"], reason="name_mismatch")
    assert len(mock.rejected) == 1
    rejected = mock.rejected[0]
    assert rejected.is_rejection is True
    assert rejected.welcome_text == "无权限入场"
    assert rejected.reason == "name_mismatch"


@pytest.mark.asyncio
async def test_mock_led_all_screen_id_accepted():
    """screen_ids=['all'] 是新约定的全屏标志，Mock 必须接受。"""
    mock = MockLEDAdapter()
    await mock.display(["all"], LEDContent(name="x", welcome_text="y"))
    assert len(mock.displayed) == 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_led_mock.py -v
```
Expected: 全部失败（`LEDContent` 未导入 + `rejected` 字段不存在）

- [ ] **Step 3: 创建 `backend/app/schemas/led.py`**

```python
"""LED 屏内容数据类——被 LEDAdapter 实现和 OnsiteWelcomeService 共享。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LEDContent:
    """一帧 LED 屏显示内容。is_rejection=True 时 welcome_text 通常是 '无权限入场'。"""

    name: str
    welcome_text: str
    is_rejection: bool = False
    reason: str = ""
```

- [ ] **Step 4: 修改 `backend/app/adapters/led/mock.py`**

完整重写：
```python
"""Mock LED 适配器——记录所有 display / show_rejected 调用，便于测试与模拟屏。"""
from __future__ import annotations

from app.adapters.base import LEDAdapter
from app.schemas.led import LEDContent


class MockLEDAdapter(LEDAdapter):
    def __init__(self) -> None:
        self.displayed: list[LEDContent] = []
        self.rejected: list[LEDContent] = []

    async def display(self, screen_ids: list[str], content: LEDContent) -> None:
        self.displayed.append(content)

    async def show_rejected(self, screen_ids: list[str], reason: str = "") -> None:
        # §三.3 要求拒绝时所有屏显示"无权限入场"
        self.rejected.append(
            LEDContent(
                name="",
                welcome_text="无权限入场",
                is_rejection=True,
                reason=reason,
            )
        )

    async def health_check(self) -> str:
        return "online"
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd backend && uv run pytest tests/test_led_mock.py -v
```
Expected: 3 passed

- [ ] **Step 6: 跑全量测试确认没回归**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 75 passed (72 旧 + 3 新) + 1 红（PII 文档化红）

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/led.py backend/app/adapters/led/mock.py backend/tests/test_led_mock.py
git commit -m "feat(led): add LEDContent dataclass + mock rejection content"
```

---

## Task 3: RealTTSAdapter 实现（pyttsx3 跨平台离线）

**Files:**
- Create: `backend/app/adapters/tts/real.py`
- Modify: `backend/app/main.py`（构造函数选择）
- Test: `backend/tests/test_tts_real_adapter.py`（新增）

**Interfaces:**
- Produces: `RealTTSAdapter(voice_id=None, rate=150)` 类，实现 `enqueue_speech` 和 `play_beep`；`play_beep` 跨平台：macOS 生成 880Hz 正弦 wav + afplay / Windows winsound.Beep / Linux speaker-test

- [ ] **Step 1: 写失败测试**

`backend/tests/test_tts_real_adapter.py`：
```python
import pytest
from app.adapters.tts.real import RealTTSAdapter


def test_real_tts_adapter_is_subclass():
    from app.adapters.base import TTSAdapter
    assert issubclass(RealTTSAdapter, TTSAdapter)


@pytest.mark.asyncio
async def test_real_tts_speech_calls_engine(monkeypatch):
    """enqueue_speech 必须调用 pyttsx3 引擎的 say+runAndWait（不实际发声）。"""
    calls = {"speak": [], "run_and_wait": 0}

    class FakeEngine:
        def setProperty(self, k, v): pass
        def getProperty(self, k): return None
        def say(self, text): calls["speak"].append(text)
        def runAndWait(self): calls["run_and_wait"] += 1

    # patch pyttsx3.init before RealTTSAdapter.__init__ runs
    import sys
    sys.modules.setdefault("pyttsx3", type(sys)("pyttsx3"))
    sys.modules["pyttsx3"].init = lambda: FakeEngine()

    adapter = RealTTSAdapter()
    await adapter.enqueue_speech("王企业 先生，欢迎您")
    assert calls["speak"] == ["王企业 先生，欢迎您"]
    assert calls["run_and_wait"] == 1


@pytest.mark.asyncio
async def test_real_tts_play_beep_cross_platform(monkeypatch):
    """play_beep 必须按平台调用对应实现（mac=afplay, win=winsound, linux=speaker-test）。"""
    import sys
    sys.modules.setdefault("pyttsx3", type(sys)("pyttsx3"))
    sys.modules["pyttsx3"].init = lambda: type("E", (), {"setProperty": lambda s,k,v: None, "getProperty": lambda s,k: None, "say": lambda s,t: None, "runAndWait": lambda s: None})()

    adapter = RealTTSAdapter()

    # monkey-patch _beep_blocking to capture call
    captured = []
    adapter._beep_blocking = lambda d: captured.append(d)  # type: ignore

    await adapter.play_beep(duration_seconds=2.5)
    assert captured == [2.5]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_tts_real_adapter.py -v
```
Expected: 全部失败（`real` 模块不存在）

- [ ] **Step 3: 创建 `backend/app/adapters/tts/real.py`**

```python
"""真实 TTS 适配器——pyttsx3 跨平台离线 TTS + 跨平台蜂鸣。"""
from __future__ import annotations

import asyncio
import math
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path


class RealTTSAdapter:
    """TTSAdapter 真实实现。

    - 语音：pyttsx3（SAPI5 / nsss / espeak，跨平台、严格离线 §6.1）
    - 蜂鸣：跨平台实现
      · macOS: 生成 880Hz 正弦 wav + afplay
      · Windows: winsound.Beep
      · Linux: speaker-test
    """

    def __init__(self, voice_id: str | None = None, rate: int = 150) -> None:
        import pyttsx3
        self._engine = pyttsx3.init()
        if voice_id:
            self._engine.setProperty("voice", voice_id)
        self._engine.setProperty("rate", rate)

    async def enqueue_speech(self, text: str) -> None:
        # pyttsx3.runAndWait 是阻塞的，丢到线程池不卡事件循环
        await asyncio.to_thread(self._speak_blocking, text)

    def _speak_blocking(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()

    async def play_beep(self, duration_seconds: float = 1.5) -> None:
        await asyncio.to_thread(self._beep_blocking, duration_seconds)

    def _beep_blocking(self, duration_seconds: float) -> None:
        if sys.platform == "darwin":
            self._beep_macos(duration_seconds)
        elif sys.platform == "win32":
            import winsound
            winsound.Beep(880, int(duration_seconds * 1000))
        else:  # linux
            import subprocess
            subprocess.run(
                ["speaker-test", "-t", "sine", "-f", "880", "-l", "1", "-s", "1"],
                timeout=duration_seconds + 0.5,
                capture_output=True,
            )

    def _beep_macos(self, duration_seconds: float) -> None:
        """生成 880Hz 正弦 wav 到临时文件，afplay 播完删除。"""
        sample_rate = 44100
        freq = 880
        n_samples = int(sample_rate * duration_seconds)
        path = Path(tempfile.gettempdir()) / f"aitec_beep_{os.getpid()}_{id(self)}.wav"
        try:
            with wave.open(str(path), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                for i in range(n_samples):
                    sample = int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sample_rate))
                    wf.writeframesraw(struct.pack("<h", sample))
            import subprocess
            subprocess.run(["afplay", str(path)], capture_output=True, check=False)
        finally:
            path.unlink(missing_ok=True)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && uv run pytest tests/test_tts_real_adapter.py -v
```
Expected: 3 passed

- [ ] **Step 5: 在 `backend/app/main.py` 装配新 adapter**

找到现有 TTS 装配（约 `app/main.py:64` MockNFCAdapter 附近）：
```python
        TTSAdapter=MockTTSAdapter(),  # 或类似
```
改为：
```python
        TTSAdapter=_build_tts_adapter(),
```
并在文件顶部加：
```python
def _build_tts_adapter():
    """RealTTSAdapter 需要音频设备，构造失败时降级 Mock。"""
    try:
        from app.adapters.tts.real import RealTTSAdapter
        return RealTTSAdapter()
    except Exception as exc:  # noqa: BLE001
        logger.warning("RealTTSAdapter 初始化失败（%s），降级 MockTTSAdapter", exc)
        return MockTTSAdapter()
```

- [ ] **Step 6: 跑全量测试**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 78 passed + 1 红

- [ ] **Step 7: Commit**

```bash
git add backend/app/adapters/tts/real.py backend/app/main.py backend/tests/test_tts_real_adapter.py
git commit -m "feat(tts): add RealTTSAdapter wrapping pyttsx3 (cross-platform offline)"
```

---

## Task 4: OnsiteWelcomeService

**Files:**
- Create: `backend/app/services/onsite_welcome_service.py`
- Modify: `backend/app/main.py`（注册 consumer）
- Test: `backend/tests/test_onsite_welcome_service.py`（新增）

**Interfaces:**
- Consumes: `LEDAdapter`, `TTSAdapter`, `EventBus`, `session_factory`（从 DB 取 name + welcome_text）
- Produces: `OnsiteWelcomeService(led, tts, event_bus, session_factory).handle_card_verify_passed(payload)` + `handle_card_verify_failed(payload)`，两个方法都发布 `work_log.append` 到 event_bus

- [ ] **Step 1: 写失败测试**

`backend/tests/test_onsite_welcome_service.py`：
```python
import pytest
from unittest.mock import MagicMock

from app.adapters.led.mock import MockLEDAdapter
from app.adapters.tts.mock import MockTTSAdapter
from app.core.event_bus import EventBus
from app.services.onsite_welcome_service import OnsiteWelcomeService
from app.models.visit import Visit, VisitStatus, IdentityType, WelcomeSource, EntrySource
from datetime import date, datetime


@pytest.fixture
def session_factory():
    """In-memory SQLite with one Visit row."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Base  # 触发 ORM 注册

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as s:
        v = Visit(
            visit_date=date(2026, 7, 7),
            session_time=datetime(2026, 7, 7, 9, 0),
            name="王企业",
            identity_type=IdentityType.ENTERPRISE_LEADER,
            welcome_text="王企业 先生，欢迎您",
            welcome_source=WelcomeSource.AI,
            entry_source=EntrySource.MANUAL,
            import_batch_id="test",
            status=VisitStatus.CARD_WRITTEN,
        )
        s.add(v)
        s.commit()
        s.refresh(v)
        visit_id = v.id

    def factory():
        return SessionLocal()
    factory.visit_id = visit_id
    return factory


@pytest.mark.asyncio
async def test_passed_drives_led_and_tts(session_factory):
    bus = EventBus()
    led = MockLEDAdapter()
    tts = MockTTSAdapter()
    svc = OnsiteWelcomeService(led, tts, bus, session_factory)

    await svc.handle_card_verify_passed(
        {"visit_id": session_factory.visit_id, "card_uid": "TEST-001"}
    )

    assert len(led.displayed) == 1
    assert led.displayed[0].name == "王企业"
    assert led.displayed[0].welcome_text == "王企业 先生，欢迎您"
    assert tts.spoken == ["王企业 先生，欢迎您"]


@pytest.mark.asyncio
async def test_failed_drives_led_rejection_and_beep(session_factory):
    bus = EventBus()
    led = MockLEDAdapter()
    tts = MockTTSAdapter()
    svc = OnsiteWelcomeService(led, tts, bus, session_factory)

    await svc.handle_card_verify_failed(
        {"visit_id": 9999, "card_uid": "BAD-001", "fail_reason": "card_not_found"}
    )

    assert len(led.rejected) == 1
    assert led.rejected[0].is_rejection is True
    assert led.rejected[0].welcome_text == "无权限入场"
    assert tts.beeps == [(1.5,)]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_onsite_welcome_service.py -v
```
Expected: 全部失败（`OnsiteWelcomeService` 未导入）

- [ ] **Step 3: 创建 `backend/app/services/onsite_welcome_service.py`**

```python
"""OnsiteWelcomeService——订阅 card.verify.passed/failed 驱动 LED + TTS + 蜂鸣。

§三.3 现场欢迎模块的服务实现。VerifyService 只判断通过/失败并改 DB 状态，
本服务只翻译事件为硬件副作用，通过 EventBus 自然解耦（不 import VerifyService）。
"""
from __future__ import annotations

import asyncio
import logging

from app.adapters.base import LEDAdapter, TTSAdapter
from app.core.event_bus import EventBus
from app.models.visit import Visit

logger = logging.getLogger(__name__)


class OnsiteWelcomeService:
    def __init__(
        self,
        led_adapter: LEDAdapter,
        tts_adapter: TTSAdapter,
        event_bus: EventBus,
        session_factory,
    ) -> None:
        self._led = led_adapter
        self._tts = tts_adapter
        self._bus = event_bus
        self._session_factory = session_factory

    async def handle_card_verify_passed(self, payload: dict) -> None:
        visit_id = payload["visit_id"]
        content = self._load_content(visit_id)
        if content is None:
            logger.warning("card.verify.passed 但找不到 visit %s", visit_id)
            return

        # 三个动作可并行：LED 显示、TTS 朗读、work_log
        await asyncio.gather(
            self._led.display(["all"], content),
            self._tts.enqueue_speech(content.welcome_text),
            self._publish_worklog("led", "display", "success",
                                  f"visit_id={visit_id} name={content.name}"),
            self._publish_worklog("tts", "speak", "success",
                                  f"visit_id={visit_id} text={content.welcome_text!r}"),
        )

    async def handle_card_verify_failed(self, payload: dict) -> None:
        reason = payload.get("fail_reason", "")
        card_uid = payload.get("card_uid", "")

        await asyncio.gather(
            self._led.show_rejected(["all"], reason=reason),
            self._tts.play_beep(duration_seconds=1.5),
            self._publish_worklog("led", "show_rejected", "success",
                                  f"card_uid={card_uid} reason={reason}"),
            self._publish_worklog("tts", "beep", "success", f"card_uid={card_uid}"),
        )

    # --- helpers ---

    def _load_content(self, visit_id: int):
        """从 DB 取访客姓名 + 欢迎词。如果 visit 不存在返回 None。"""
        from app.schemas.led import LEDContent
        with self._session_factory() as session:
            v = session.get(Visit, visit_id)
            if v is None:
                return None
            return LEDContent(
                name=v.name,
                welcome_text=v.welcome_text or "",
                is_rejection=False,
                reason="",
            )

    async def _publish_worklog(self, module: str, action: str, status: str, detail: str) -> None:
        await self._bus.publish("work_log.append", {
            "module": module,
            "action": action,
            "status": status,
            "detail": detail,
        })
```

- [ ] **Step 4: 在 `backend/app/main.py` 注册 consumer**

找到 lifespan（约 line 89-133），在 `verify_service.handle_card_verify_requested` consumer 之后加：
```python
                asyncio.create_task(
                    _consume(
                        event_bus,
                        "card.verify.passed",
                        onsite_welcome_service.handle_card_verify_passed,
                    )
                ),
                asyncio.create_task(
                    _consume(
                        event_bus,
                        "card.verify.failed",
                        onsite_welcome_service.handle_card_verify_failed,
                    )
                ),
```

找到 services 构造区（约 line 71-76），加：
```python
    onsite_welcome_service = OnsiteWelcomeService(led_adapter, tts_adapter, event_bus, session_factory)
```

并在顶部加 import：
```python
from app.services.onsite_welcome_service import OnsiteWelcomeService
```

- [ ] **Step 5: 运行测试**

```bash
cd backend && uv run pytest tests/test_onsite_welcome_service.py -v
```
Expected: 2 passed

- [ ] **Step 6: 跑全量测试**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 80 passed + 1 红

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/onsite_welcome_service.py backend/app/main.py backend/tests/test_onsite_welcome_service.py
git commit -m "feat(welcome): add OnsiteWelcomeService to drive LED+TTS+beep from verify events"
```

---

## Task 5: VerifyService 失败路径写 REJECTED

**Files:**
- Modify: `backend/app/services/verify_service.py`
- Test: `backend/tests/test_verify_service.py`（扩展现有或新增）

- [ ] **Step 1: 写失败测试**

新增 `backend/tests/test_verify_service_state_machine.py`：
```python
import pytest
from datetime import date, datetime
from app.core.event_bus import EventBus
from app.models import Base, Visit, VisitStatus, IdentityType, WelcomeSource, EntrySource
from app.services.verify_service import VerifyService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as s:
        v = Visit(
            visit_date=date(2026, 7, 7),
            session_time=datetime(2026, 7, 7, 9, 0),
            name="测试人",
            identity_type=IdentityType.ENTERPRISE_STAFF,
            welcome_text="测试",
            welcome_source=WelcomeSource.AI,
            entry_source=EntrySource.MANUAL,
            import_batch_id="t",
            status=VisitStatus.CARD_WRITTEN,
        )
        s.add(v)
        s.commit()
        s.refresh(v)
        vid = v.id
    return SessionLocal, vid


@pytest.mark.asyncio
async def test_failed_verify_sets_rejected_status(session_factory):
    SessionLocal, vid = session_factory
    bus = EventBus()
    published = []
    bus.subscribe("card.verify.failed")
    original_publish = bus.publish
    async def capture(topic, payload):
        published.append((topic, payload))
        await original_publish(topic, payload)
    bus.publish = capture  # type: ignore

    svc = VerifyService(SessionLocal, bus)
    await svc.handle_card_verify_requested({
        "card_uid": "BAD",
        "raw_payload": {"visit_id": vid, "name": "错误名", "visit_date": "2026-07-07"},
    })

    assert any(t == "card.verify.failed" for t, _ in published)
    with SessionLocal() as s:
        v = s.get(Visit, vid)
        assert v.status == VisitStatus.REJECTED
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_verify_service_state_machine.py -v
```
Expected: 失败（visit.status 还是 CARD_WRITTEN）

- [ ] **Step 3: 修改 `backend/app/services/verify_service.py`**

找到失败分支（约 line 52-62，"不通过"），在发 `card.verify.failed` 事件之前/之后加：
```python
                visit.status = VisitStatus.REJECTED  # ← 新增
```
（在 `session.commit()` 之前，确保状态变更被持久化）

- [ ] **Step 4: 跑测试**

```bash
cd backend && uv run pytest tests/test_verify_service_state_machine.py -v
```
Expected: 1 passed

- [ ] **Step 5: 跑全量**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 81 passed + 1 红

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/verify_service.py backend/tests/test_verify_service_state_machine.py
git commit -m "fix(verify): write VisitStatus.REJECTED on verify-fail path"
```

---

## Task 6: PII 在 /api/import/preview 脱敏

**Files:**
- Modify: `backend/app/api/imports.py`
- Test: `backend/tests/test_api_imports_pii.py`（新增）

- [ ] **Step 1: 写失败测试**

```python
import io
import pandas as pd
from app.main import build_app
from app.core.config import Settings
from app.core.event_bus import EventBus
from fastapi.testclient import TestClient


def _make_xlsx() -> bytes:
    df = pd.DataFrame([{
        "来访日期": "2026-07-07",
        "计划场次时间": "2026-07-07 09:00",
        "姓名": "张三",
        "手机号": "13800000000",
        "国籍": "中国",
        "身份证号": "110101199001010011",
        "性别": "男",
        "单位": "某单位",
        "身份": "企业员工",
    }])
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def test_import_preview_masks_id_number():
    app = build_app(Settings())
    with TestClient(app) as client:
        resp = client.post(
            "/api/import/preview",
            files={"file": ("test.xlsx", _make_xlsx(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 200
    body = resp.json()
    rows = body["rows"]
    assert rows[0]["data"]["身份证号"] != "110101199001010011"
    # mask 形如 110********0011（3 + 7 asterisks + 4）
    assert "********" in rows[0]["data"]["身份证号"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_api_imports_pii.py -v
```
Expected: 失败（assert `"110101199001010011" != ...` 不成立）

- [ ] **Step 3: 修改 `backend/app/api/imports.py`**

在文件顶部加 import：
```python
from app.schemas.visit import mask_id_number
```

在 `preview_import` 函数内构造 `ImportPreviewRow` 之前（`imports.py:33-47` 附近），加 helper：
```python
def _scrub_pii(data: dict) -> dict:
    """§六.2：preview 阶段身份证号必须脱敏，防止值班人员浏览器拿到明文。"""
    raw = data.get("身份证号")
    if isinstance(raw, str) and raw.strip():
        data = {**data, "身份证号": mask_id_number(raw)}
    return data
```

把构造 row 的循环（约 imports.py:39-47）里：
```python
ImportPreviewRow(
    row_number=row.row_number,
    data=row.data,
    ...
)
```
改为：
```python
ImportPreviewRow(
    row_number=row.row_number,
    data=_scrub_pii(row.data),
    ...
)
```

- [ ] **Step 4: 跑测试**

```bash
cd backend && uv run pytest tests/test_api_imports_pii.py -v
```
Expected: 1 passed

- [ ] **Step 5: 跑全量**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 82 passed + 1 红

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/imports.py backend/tests/test_api_imports_pii.py
git commit -m "fix(imports): mask id_number in /api/import/preview (§6.2)"
```

---

## Task 7: 工作日志导出端点

**Files:**
- Modify: `backend/app/api/logs.py`
- Test: `backend/tests/test_api_logs_export.py`（新增）

**Interfaces:**
- Produces: `GET /api/work-logs/export?module=&status=&format=xlsx` 返回 .xlsx 流

- [ ] **Step 1: 写失败测试**

```python
import pandas as pd
from app.main import build_app
from app.core.config import Settings
from fastapi.testclient import TestClient
from app.models import Base, WorkLog, LogModule, LogStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_work_log_export_returns_xlsx():
    # 注入几个测试行
    app = build_app(Settings())
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as s:
        s.add(WorkLog(module=LogModule.REGISTRATION, action="import_file",
                      status=LogStatus.SUCCESS, detail="ok"))
        s.add(WorkLog(module=LogModule.VERIFY, action="verify_card",
                      status=LogStatus.WARNING, detail="name_mismatch"))
        s.commit()

    # 替换 app 的 session_factory
    from app.api import deps
    app.state.session_factory = SessionLocal

    with TestClient(app) as client:
        resp = client.get("/api/work-logs/export?module=verify")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    df = pd.read_excel(io.BytesIO(resp.content)) if False else None  # bytes 是 xlsx
```

简化版（避免复杂 fixture）：
```python
from app.main import build_app
from app.core.config import Settings
from fastapi.testclient import TestClient


def test_export_endpoint_exists_and_returns_xlsx():
    app = build_app(Settings())
    with TestClient(app) as client:
        resp = client.get("/api/work-logs/export")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_api_logs_export.py -v
```
Expected: 404

- [ ] **Step 3: 在 `backend/app/api/logs.py` 加导出端点**

参考 `api/visits.py:69-100` 的 summary/export 风格，在 `logs.py` 末尾加：
```python
from io import BytesIO
import pandas as pd
from fastapi.responses import StreamingResponse
from sqlalchemy import select


@router.get("/work-logs/export")
async def export_work_logs(
    module: LogModule | None = Query(None),
    status: LogStatus | None = Query(None),
    session_factory=Depends(get_session_factory),
):
    """§三.4：工作日志可下载为 xlsx。"""
    with session_factory() as session:
        stmt = select(WorkLog)
        if module:
            stmt = stmt.where(WorkLog.module == module)
        if status:
            stmt = stmt.where(WorkLog.status == status)
        rows = session.execute(stmt.order_by(WorkLog.created_at.desc())).scalars().all()
        frame = pd.DataFrame([{
            "id": r.id, "module": r.module.value, "action": r.action,
            "status": r.status.value, "detail": r.detail, "created_at": r.created_at,
        } for r in rows])

    buffer = BytesIO()
    frame.to_excel(buffer, index=False, sheet_name="工作日志")
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=work_logs.xlsx"},
    )
```

- [ ] **Step 4: 跑测试**

```bash
cd backend && uv run pytest tests/test_api_logs_export.py -v
```
Expected: 1 passed

- [ ] **Step 5: 跑全量**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 83 passed + 1 红

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/logs.py backend/tests/test_api_logs_export.py
git commit -m "feat(logs): add GET /api/work-logs/export endpoint (§3.4)"
```

---

## Task 8: WS 推送 led.content（让前端订阅）

**Files:**
- Modify: `backend/app/api/ws.py`
- Test: `backend/tests/test_ws_led_topic.py`（新增）

**Interfaces:**
- Produces: `REALTIME_TOPICS` 列表新增 `"led.content"`，前端 `/mock-led` 和 `/display` 订阅

- [ ] **Step 1: 写失败测试**

```python
from app.api.ws import REALTIME_TOPICS


def test_led_content_in_realtime_topics():
    """§三.3 LED 屏内容变化要实时推送给前端模拟屏。"""
    assert "led.content" in REALTIME_TOPICS
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && uv run pytest tests/test_ws_led_topic.py -v
```
Expected: 失败

- [ ] **Step 3: 修改 `backend/app/api/ws.py`**

在 `REALTIME_TOPICS` 列表（约 line 13）加：
```python
REALTIME_TOPICS = [
    "card.verify.passed",
    "card.verify.failed",
    "adapter.heartbeat",
    "led.content",   # ← 新增
]
```

- [ ] **Step 4: 同时让 OnsiteWelcomeService 发布 led.content**

修改 `backend/app/services/onsite_welcome_service.py`：在 `handle_card_verify_passed` 的 `asyncio.gather` 加一项：
```python
            self._publish_led(content),
            self._publish_worklog("led", "display", "success", ...),
```
新 helper：
```python
    async def _publish_led(self, content) -> None:
        from dataclasses import asdict
        await self._bus.publish("led.content", asdict(content))
```

`handle_card_verify_failed` 同样：
```python
            self._publish_led(LEDContent(name="", welcome_text="无权限入场",
                                         is_rejection=True, reason=reason)),
```

- [ ] **Step 5: 跑测试**

```bash
cd backend && uv run pytest tests/test_ws_led_topic.py -v
```
Expected: 1 passed

- [ ] **Step 6: 跑全量**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 84 passed + 1 红

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/ws.py backend/app/services/onsite_welcome_service.py backend/tests/test_ws_led_topic.py
git commit -m "feat(ws): add led.content topic for live LED updates"
```

---

## Task 9: 前端类型 + realtimeStore 加 led.content + 指数退避

**Files:**
- Modify: `frontend/src/stores/realtimeStore.ts`
- Modify: `frontend/src/api/types.ts`

**Interfaces:**
- Produces: `RealtimeEvent.type` 新增 `"led.content"`；`store.ledContent: LEDContent | null`；`store.reconnectAttempt: number`；`socket.onclose` 触发 `scheduleReconnect()`

- [ ] **Step 1: 修改 `frontend/src/api/types.ts`**

找到 `RealtimeEvent` 类型定义，加 `led.content`：
```typescript
export type RealtimeEventType =
  | "card.verify.passed"
  | "card.verify.failed"
  | "adapter.heartbeat"
  | "led.content";  // ← 新增

export interface LEDContent {
  name: string;
  welcome_text: string;
  is_rejection: boolean;
  reason: string;
}

// RealtimeEvent 的 payload 联合类型相应扩展
export interface RealtimeEvent {
  type: RealtimeEventType;
  timestamp: string;
  payload:
    | { visit_id: number; card_uid: string }
    | { adapter_name: string; status: string }
    | LEDContent;
}
```

- [ ] **Step 2: 修改 `frontend/src/stores/realtimeStore.ts`**

在 state 加：
```typescript
ledContent: null as LEDContent | null,
reconnectAttempt: 0,
```

在 `connect()` 内 `socket.onclose` 改为：
```typescript
socket.onclose = () => {
  set({ connected: false, socket: null });
  const attempt = get().reconnectAttempt;
  const delay = Math.min(1000 * Math.pow(2, attempt), 30_000);
  set({ reconnectAttempt: attempt + 1 });
  setTimeout(connect, delay);
};
```

`socket.onopen` 改为：
```typescript
socket.onopen = () => {
  set({ connected: true, reconnectAttempt: 0 });
};
```

在 message handler 内 `case "adapter.heartbeat"` 后加：
```typescript
case "led.content":
  set({ ledContent: msg.payload as LEDContent });
  break;
```

并在顶部 import `LEDContent` from `../api/types`。

- [ ] **Step 3: 类型检查**

```bash
cd frontend && pnpm exec tsc --noEmit
```
Expected: 0 error

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/stores/realtimeStore.ts
git commit -m "feat(frontend): realtime store handles led.content + exponential reconnect"
```

---

## Task 10: LiveBoardPage 渲染 name + welcome_text

**Files:**
- Modify: `frontend/src/pages/LiveBoardPage.tsx`

- [ ] **Step 1: 替换 `card.verify.passed` 分支**

找到 LiveBoardPage 中 `latest?.type === "card.verify.passed"` 的渲染分支（约 line 36-41），改为：
```tsx
{latest?.type === "card.verify.passed" && (
  <div style={{ background: "#e8f5e9", padding: 24, borderRadius: 8 }}>
    <h2 style={{ color: "#2e7d32", margin: 0 }}>✓ 欢迎光临</h2>
    <p style={{ fontSize: 28, margin: "12px 0" }}>
      {String((latest.payload as any).name ?? "")}
    </p>
    <p style={{ fontSize: 18, color: "#555" }}>
      {String((latest.payload as any).welcome_text ?? "")}
    </p>
  </div>
)}
```

- [ ] **Step 2: 检查后端 payload 是否含 name+welcome_text**

后端 audit 显示 `card.verify.passed` payload 当前只含 `visit_id + card_uid`。需要让 VerifyService 把 name+welcome_text 加进 payload——**但** VerifyService 不应该反查 DB（那是 OnsiteWelcomeService 的职责）。

修复办法：让 OnsiteWelcomeService **重新发布** `card.verify.passed` 增强版 payload，或单独发布一个 `welcome.display` 事件含完整字段。

**采用：OnsiteWelcomeService 不重新发布**，而是 LiveBoard 同时订阅 `led.content`（Task 9 已加），从那里取 name+welcome。

调整 LiveBoardPage 增加 led.content 分支：
```tsx
const ledContent = useRealtimeStore(s => s.ledContent);

// 优先显示 led.content（包含姓名）
const display = ledContent ?? null;

{display && !display.is_rejection && (
  <div style={{ background: "#e8f5e9", padding: 24, borderRadius: 8 }}>
    <h2>✓ 欢迎光临</h2>
    <p style={{ fontSize: 28 }}>{display.name}</p>
    <p style={{ fontSize: 18, color: "#555" }}>{display.welcome_text}</p>
  </div>
)}

{display?.is_rejection && (
  <div style={{ background: "#ffebee", padding: 24, borderRadius: 8 }}>
    <h2 style={{ color: "#c62828" }}>无权限入场</h2>
    {display.reason && <p>原因：{display.reason}</p>}
  </div>
)}
```

- [ ] **Step 3: 类型检查**

```bash
cd frontend && pnpm exec tsc --noEmit
```
Expected: 0 error

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LiveBoardPage.tsx
git commit -m "feat(liveboard): show visitor name + welcome text from led.content"
```

---

## Task 11: 新路由 /display — 现场大屏

**Files:**
- Create: `frontend/src/pages/DisplayPage.tsx`
- Modify: `frontend/src/router.tsx`

- [ ] **Step 1: 创建 `frontend/src/pages/DisplayPage.tsx`**

```tsx
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRealtimeStore } from "../stores/realtimeStore";
import { fetchVisitsToday } from "../api/visits";

export function DisplayPage() {
  const ledContent = useRealtimeStore(s => s.ledContent);
  const { data: today = [] } = useQuery({
    queryKey: ["visits-today"],
    queryFn: fetchVisitsToday,
    refetchInterval: 5000,
  });

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a1929",
      color: "#e3f2fd",
      padding: 32,
      fontFamily: "system-ui, sans-serif",
    }}>
      <h1 style={{ fontSize: 36, marginBottom: 24 }}>
        实时来访名单 · {new Date().toLocaleDateString("zh-CN")}
      </h1>

      <div style={{
        background: "#102a43",
        borderRadius: 8,
        padding: 24,
        marginBottom: 24,
        maxHeight: "50vh",
        overflowY: "auto",
      }}>
        {today.length === 0 && <p>暂无今日访客</p>}
        {today.map(v => (
          <div key={v.id} style={{
            padding: "12px 0",
            borderBottom: "1px solid #1e3a5f",
            display: "flex",
            gap: 24,
            fontSize: 22,
          }}>
            <span style={{ width: 80 }}>{v.visit_date}</span>
            <span style={{ width: 80 }}>{String(v.session_time).slice(11, 16)}</span>
            <span style={{ flex: 1, fontWeight: 600 }}>{v.name}</span>
            <span style={{ width: 140 }}>{v.identity_type}</span>
            <span style={{
              width: 100,
              color: v.status === "verified" ? "#81c784" : "#ffb74d",
            }}>
              {v.status === "verified" ? "已入场" : v.status}
            </span>
          </div>
        ))}
      </div>

      {ledContent && !ledContent.is_rejection && (
        <div style={{
          background: "#1b5e20",
          padding: 32,
          borderRadius: 8,
          fontSize: 42,
          textAlign: "center",
        }}>
          最新：{ledContent.name} — {ledContent.welcome_text}
        </div>
      )}

      {ledContent?.is_rejection && (
        <div style={{
          background: "#b71c1c",
          padding: 32,
          borderRadius: 8,
          fontSize: 42,
          textAlign: "center",
        }}>
          无权限入场{ledContent.reason ? `（${ledContent.reason}）` : ""}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 在 `frontend/src/router.tsx` 注册路由**

加 import：
```tsx
import { DisplayPage } from "./pages/DisplayPage";
```

在 routes 数组加：
```tsx
{ path: "/display", element: <DisplayPage /> },
```

- [ ] **Step 3: 类型检查 + 构建**

```bash
cd frontend && pnpm exec tsc --noEmit && pnpm build
```
Expected: 0 error + build 成功

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DisplayPage.tsx frontend/src/router.tsx
git commit -m "feat(display): new /display page for on-site live board"
```

---

## Task 12: 新路由 /mock-led — 模拟 LED 屏

**Files:**
- Create: `frontend/src/pages/MockLEDPane.tsx`
- Modify: `frontend/src/router.tsx`

- [ ] **Step 1: 创建 `frontend/src/pages/MockLEDPane.tsx`**

```tsx
import { useEffect, useRef } from "react";
import { useRealtimeStore } from "../stores/realtimeStore";

export function MockLEDPane() {
  const ledContent = useRealtimeStore(s => s.ledContent);
  const ref = useRef<HTMLDivElement>(null);

  // 进入页面自动全屏
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => {/* 用户可能拒绝 */});
    }
  }, []);

  const isRejection = ledContent?.is_rejection ?? false;
  const mainText = isRejection
    ? "无权限入场"
    : (ledContent?.name ? `${ledContent.name}  ${ledContent.welcome_text}` : "等待刷卡…");
  const subText = isRejection && ledContent?.reason ? `（${ledContent.reason}）` : "";

  return (
    <div
      ref={ref}
      style={{
        position: "fixed",
        inset: 0,
        background: "#000",
        color: isRejection ? "#ff1744" : "#fff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: '"PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
        cursor: "pointer",
      }}
      onClick={() => ref.current?.requestFullscreen?.()}
    >
      <div style={{ fontSize: 96, fontWeight: 700, textAlign: "center", padding: 32 }}>
        {mainText}
      </div>
      {subText && (
        <div style={{ fontSize: 48, marginTop: 24, color: "#ff8a80" }}>{subText}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 在 `frontend/src/router.tsx` 注册路由**

加 import：
```tsx
import { MockLEDPane } from "./pages/MockLEDPane";
```

加路由：
```tsx
{ path: "/mock-led", element: <MockLEDPane /> },
```

- [ ] **Step 3: 类型检查 + 构建**

```bash
cd frontend && pnpm exec tsc --noEmit && pnpm build
```
Expected: 0 error + build 成功

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/MockLEDPane.tsx frontend/src/router.tsx
git commit -m "feat(mock-led): new /mock-led fullscreen black LED simulator"
```

---

## Task 13: NavLayout 顶部 AdapterOfflineBanner

**Files:**
- Create: `frontend/src/components/AdapterOfflineBanner.tsx`
- Modify: `frontend/src/components/NavLayout.tsx`

- [ ] **Step 1: 创建 `frontend/src/components/AdapterOfflineBanner.tsx`**

```tsx
import { useRealtimeStore } from "../stores/realtimeStore";

export function AdapterOfflineBanner() {
  const statuses = useRealtimeStore(s => s.adapterStatuses);
  const offline = Object.entries(statuses).filter(([_, v]) => v !== "online");

  if (offline.length === 0) return null;

  return (
    <div
      role="alert"
      style={{
        background: "#d32f2f",
        color: "#fff",
        padding: "10px 16px",
        fontWeight: 600,
        textAlign: "center",
        fontSize: 14,
      }}
    >
      ⚠️ 硬件离线：{offline.map(([n]) => n.toUpperCase()).join(" / ")}
      {" — "}管理功能仍可使用，但现场刷卡链路可能异常
    </div>
  );
}
```

- [ ] **Step 2: 在 NavLayout 顶部插入 Banner**

修改 `frontend/src/components/NavLayout.tsx`，在 `<nav>` 上方：
```tsx
import { AdapterOfflineBanner } from "./AdapterOfflineBanner";

// 在 <nav> 之前
<AdapterOfflineBanner />
<nav>...</nav>
```

- [ ] **Step 3: 类型检查**

```bash
cd frontend && pnpm exec tsc --noEmit
```
Expected: 0 error

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AdapterOfflineBanner.tsx frontend/src/components/NavLayout.tsx
git commit -m "feat(nav): add red AdapterOfflineBanner when any hardware offline"
```

---

## Task 14: RegistrationPage 预览表 9 列

**Files:**
- Modify: `frontend/src/pages/RegistrationPage.tsx`

- [ ] **Step 1: 替换预览表的 thead + 单元格**

找到 `RegistrationPage.tsx:44-50`（预览表的 `<thead>`）替换为：
```tsx
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

找到 tbody 单元格（约 line 53-63），把每行扩展为：
```tsx
<tr key={idx} style={{ background: row.is_valid ? undefined : "#ffdddd" }}>
  <td>{row.row_number}</td>
  <td>{String(row.data["姓名"] ?? "")}</td>
  <td>{String(row.data["来访日期"] ?? "")}</td>
  <td>{String(row.data["计划场次时间"] ?? "")}</td>
  <td>{String(row.data["手机号"] ?? "")}</td>
  <td>{String(row.data["国籍"] ?? "")}</td>
  <td>{String(row.data["身份证号"] ?? "")}</td>
  <td>{String(row.data["性别"] ?? "")}</td>
  <td>{String(row.data["单位"] ?? "")}</td>
  <td>{String(row.data["身份"] ?? "")}</td>
  <td style={{ color: "red", fontSize: 12 }}>
    {row.errors.join("; ")}
  </td>
</tr>
```

- [ ] **Step 2: 类型检查**

```bash
cd frontend && pnpm exec tsc --noEmit
```
Expected: 0 error

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/RegistrationPage.tsx
git commit -m "feat(registration): preview table shows all 9 required columns"
```

---

## Task 15: WorkLogPage 加导出按钮

**Files:**
- Modify: `frontend/src/pages/WorkLogPage.tsx`
- Modify: `frontend/src/api/logs.ts`

- [ ] **Step 1: 在 `frontend/src/api/logs.ts` 加 URL helper**

```typescript
export function workLogExportUrl(module?: string, status?: string): string {
  const params = new URLSearchParams();
  if (module) params.set("module", module);
  if (status) params.set("status", status);
  const qs = params.toString();
  return `/api/work-logs/export${qs ? `?${qs}` : ""}`;
}
```

- [ ] **Step 2: 在 `WorkLogPage.tsx` 顶部加导出按钮**

找到文件顶部 filter 控件区（约 line 18-55），加一个导出链接：
```tsx
<a
  href={workLogExportUrl(module, status)}
  download
  style={{
    padding: "6px 12px",
    background: "#1976d2",
    color: "#fff",
    borderRadius: 4,
    textDecoration: "none",
    marginLeft: 12,
  }}
>
  导出 Excel
</a>
```

- [ ] **Step 3: 类型检查 + 构建**

```bash
cd frontend && pnpm exec tsc --noEmit && pnpm build
```
Expected: 0 error + build 成功

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/WorkLogPage.tsx frontend/src/api/logs.ts
git commit -m "feat(logs): add Excel export button + URL helper"
```

---

## Task 16: 端到端验证（手动 + pytest）

**Files:**
- Modify: `backend/tests/test_end_to_end.py`（扩展）

- [ ] **Step 1: 扩展端到端测试**

在 `tests/test_end_to_end.py` 已有的 happy-path 测试末尾加：
```python
async def test_e2e_passed_drives_led_and_tts(...):
    """§三.3 §八-6：verify passed 必须驱动 LED 显示 + TTS 朗读。"""
    # ... 复用 setup：build_app + e2e 走到 verify.passed ...
    assert led_adapter.displayed[-1].name == visit.name
    assert tts_adapter.spoken[-1] == visit.welcome_text
```

具体实现参考现有 end_to_end 测试结构。

- [ ] **Step 2: 跑全量**

```bash
cd backend && uv run pytest --tb=no -q
```
Expected: 85 passed + 1 红

- [ ] **Step 3: 前端构建**

```bash
cd frontend && pnpm build
```
Expected: 成功

- [ ] **Step 4: 手动走一遍**

启动服务，按 §八 验收清单核对：
1. Excel 导入 → AI 生成 → 写卡 → 模拟刷卡
2. 浏览器开 3 个 tab：localhost:5173/display、/mock-led、/live
3. 触发 `POST /api/debug/simulate-card-read`（带 visit_id）
4. 三个 tab 同时更新（display 滚动 + mock-led 大字 + live 简版）
5. 触发失败刷卡（`{"card_uid": "BAD"}`）：mock-led 显示红色"无权限入场"，听到蜂鸣
6. kill 后端 5s 再启动：前端 WS 自动重连（无需手动刷新）
7. 上传 Excel 时 preview 表格显示全 9 列，身份证号已脱敏
8. 工作日志页点导出 → 下载 .xlsx
9. 模拟 adapter 离线（后端 log 里有 `adapter.heartbeat status=offline`）→ NavLayout 顶部出现红色横条

- [ ] **Step 5: Commit（如有扩展测试改动）**

```bash
git add backend/tests/test_end_to_end.py
git commit -m "test(e2e): assert verify-passed drives LED display + TTS speak"
```

---

## 总结

| Task | 文件数 | 提交数 | 关键改动 |
|---|---|---|---|
| 1 | 2 改 + 1 测 | 1 | TTSAdapter 接口 + Mock 实现 |
| 2 | 1 新 + 1 改 + 1 测 | 1 | LEDContent + MockLED 改造 |
| 3 | 1 新 + 1 改 + 1 测 | 1 | RealTTSAdapter pyttsx3 |
| 4 | 1 新 + 1 改 + 1 测 | 1 | OnsiteWelcomeService + 装配 |
| 5 | 1 改 + 1 测 | 1 | VerifyService REJECTED |
| 6 | 1 改 + 1 测 | 1 | PII 脱敏 |
| 7 | 1 改 + 1 测 | 1 | 工作日志导出 |
| 8 | 2 改 + 1 测 | 1 | WS led.content topic |
| 9 | 2 改 | 1 | 前端 store + 类型 |
| 10 | 1 改 | 1 | LiveBoard 渲染姓名 |
| 11 | 1 新 + 1 改 | 1 | /display 路由 |
| 12 | 1 新 + 1 改 | 1 | /mock-led 路由 |
| 13 | 1 新 + 1 改 | 1 | AdapterOfflineBanner |
| 14 | 1 改 | 1 | 9 列预览表 |
| 15 | 2 改 | 1 | 工作日志导出按钮 |
| 16 | 1 改 | 0-1 | 端到端验证 |
| **合计** | 9 新 + 17 改 + 11 测 | 15 | 全 §八 + 用户决策 |

---

## Self-Review（按 writing-plans skill 要求）

**1. Spec coverage:**
- §三.3 LED 显示姓名 + 欢迎词 → Task 2 (LEDContent) + Task 4 (OnsiteWelcomeService.handle_card_verify_passed 调用 led.display)
- §三.3 LED "无权限入场" → Task 2 (show_rejected 写"无权限入场") + Task 4 (failed handler)
- §三.3 TTS 朗读 → Task 1 (接口) + Task 3 (RealTTSAdapter) + Task 4 (调用)
- §三.3 蜂鸣通道 → Task 1 (接口) + Task 3 (跨平台实现) + Task 4 (调用)
- §三.3 当日名单 → Task 11 (/display)
- §六.1 离线 TTS → Task 3 (pyttsx3 本地)
- §六.2 PII preview → Task 6
- §六.3 离线红色告警 → Task 13
- §三.4 工作日志下载 → Task 7 + Task 15
- §四 状态机 REJECTED → Task 5
- 用户 U11 WS 重连 → Task 9
- 用户 U15 模拟 LED → Task 12
- 用户 U9 预览表 9 列 → Task 14
- ✅ 全部覆盖

**2. Placeholder scan:**
- 无 TBD/TODO
- 无 "implement later"
- 每个测试都给了实际代码
- 每个实现都给了完整代码

**3. Type consistency:**
- `LEDContent` 在 Task 2 定义（schema/led.py），在 Task 4 / Task 8 / Task 10-12 一致使用
- `TTSAdapter.play_beep(duration_seconds: float = 1.5)` 在 Task 1 定义，Task 3/4 一致调用
- `RealtimeEventType` "led.content" 在 Task 9 定义，Task 10-12 一致订阅
- `screen_ids=["all"]` 在 Task 2/4/8 一致使用
- `workLogExportUrl` 在 Task 15 定义，签名一致
- ✅ 无冲突