# 真机测试指南（Hardware Bring-Up Guide）

> **状态**：当前所有硬件（NFC 读卡器、LED 屏、TTS 音响、AI 接口）均为 **Mock / 模拟** 状态。本指南面向拿到真机后的开发者/运维人员。
>
> **目标读者**：Day 4 硬件接入工程师、展厅现场调试人员、QA。
>
> **前置阅读**：[TARGET.md §三.3 §六.1 §七](../TARGET.md)、[CLAUDE.md](../CLAUDE.md)、[CHANGELOG.md](../CHANGELOG.md)

---

## 0. 准备清单

### 0.1 设备清单（需采购/已采购）

| 设备 | 推荐型号 | 接口 | 备注 |
|---|---|---|---|
| NFC 读卡器 | ACR122U (PC/SC 兼容) | USB | 任何 PC/SC 兼容读卡器均可；推荐 pyscard 库 |
| LED 屏 + 控制器 | onbon 六代 (BX-6) | 以太网 / RS232 / RS485 | 见 §3 |
| 音响 | 任意 3.5mm / USB / 内置 | 系统音频 | TTS 走系统默认输出 |
| 测试卡 | Mifare Classic 1K (NFC Forum Type 2) | — | 至少 5 张 |

### 0.2 软件依赖

```bash
# Python 端
cd backend
uv add pyscard      # NFC（PC/SC）
uv add python-sdk   # onbon LED（按设备型号对应包）
uv add pyttsx3      # 已装：跨平台 TTS
uv add winsound     # Windows only（标准库自带）

# 系统级（Linux）
sudo apt install -y pcscd libpcsclite-dev espeak-ng libespeak1
sudo systemctl enable pcscd
sudo systemctl start pcscd
```

### 0.3 当前 Mock 行为速查

| Adapter | Mock 类 | Mock 行为 | 切换真机时改什么 |
|---|---|---|---|
| NFC | `MockNFCAdapter`（`backend/app/adapters/nfc/mock.py`） | 写卡 = 存 dict；读卡 = 队列异步出；`fail=True` 注入失败 | 用 `NfcAdapterReal` 替换，构造处加环境判断 |
| LED | `MockLEDAdapter`（`backend/app/adapters/led/mock.py`） | `display()` 追加到 `self.displayed` 列表；`show_rejected()` 追加 `LEDContent(is_rejection=True)` | 调用厂商 SDK `send_text()` 等 |
| TTS | `MockTTSAdapter`（`backend/app/adapters/tts/mock.py`） | `enqueue_speech` 追加到 `spoken` 列表；`play_beep` 追加到 `beeps` | `RealTTSAdapter` 已实现（pyttsx3），开发机可立即启用 |
| AI | `MockAIAdapter`（`backend/app/adapters/ai/mock.py`） | 返回固定字符串 | `QwenAIAdapter` 已实现（DashScope），需 `settings.ai_api_key` |

切换时改 **composition root**（`backend/app/main.py::_build_*_adapter` 函数），业务代码不动。

---

## 1. NFC 读卡器

### 1.1 接线 + 驱动

- ACR122U 插 USB，免驱（macOS / Windows / Linux 都内置 CCID 驱动）
- 验证设备识别：
  ```bash
  # Linux
  lsusb | grep "ACS ACR122U"
  pcsc_scan    # 应能扫到读卡器
  # macOS
  system_profiler SPUSBDataType | grep -i acs
  # Windows
  # 设备管理器 → 智能卡读卡器 → ACS ACR122U
  ```

### 1.2 实现 Real NFC Adapter

**目标**：实现 `backend/app/adapters/nfc/real.py`，提供 `write_card` + `read_stream` (AsyncIterator) + `health_check`。

**推荐库**：`pyscard` (PC/SC API 的 Python 绑定)，跨平台。

**`write_card` 要点**：
- 卡片必须能在 5 秒内被发现（必要时轮询 `card.connection`）
- 按 NDEF 格式写入 5 个字段：`visit_id`, `name`, `visit_date`, `identity_type`, `welcome_text`
- 推荐用 NDEF Type 2 Tag（NFC Forum 标准）
- 写成功立即 `card.disconnect()`
- 失败抛异常，让上层 service 写 `NFCWriteLog(write_status="failed", error_message=...)`

**`read_stream` 要点**：
- 是 `AsyncIterator[CardReadEvent]` —— 用 `asyncio.Queue` 解耦 SDK 回调
- 用 `Observer` 模式注册 SDK 回调，把 `on_card_present` 事件丢进 queue
- `OnsiteWelcomeService` 依赖这个顺序——必须保证 FIFO

**骨架示例**：
```python
# backend/app/adapters/nfc/real.py 草稿
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toHexString
import asyncio

class _SDKEventsToQueue(CardObserver):
    def __init__(self, loop, queue):
        self._loop = loop
        self._queue = queue
    def update(self, observable, event):
        # ... 解析 card.uid + raw_payload（NDEF read），put 到 queue
        ...

class NfcAdapterReal(NFCAdapter):
    def __init__(self):
        self._monitor = CardMonitor()
        self._queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        observer = _SDKEventsToQueue(asyncio.get_running_loop(), self._queue)
        self._monitor.addObserver(observer)

    async def write_card(self, card_uid, payload) -> WriteResult:
        # 用 pyscard 连接 + NDEF write
        ...
```

### 1.3 真机测试清单

- [ ] 读卡器被发现（`pcsc_scan`）
- [ ] `start()` 后 `_monitor` 正在运行
- [ ] 把测试卡放上去 → `read_stream` 出事件（带 card_uid）
- [ ] 手动调用 `write_card("TEST-UID-1", payload)` → 卡片可被 NFC Tools / NXP TagInfo 读到 5 个字段
- [ ] 拿另一台手机（带 NFC）贴近卡片，识别到 NDEF 文本（验证编码对）
- [ ] **失败注入**：拔掉读卡器 USB → 心跳 poller 应该在 30s 内把 `nfc` adapter 标记为 `offline`（验证 §六.3 红色告警）

### 1.4 常见问题

| 症状 | 原因 | 修复 |
|---|---|---|
| `pcsc_scan` 找不到读卡器 | 驱动没装 / USB 接触不良 | 重插；Linux 装 `libccid` |
| 写卡后读不到 | 没按 NDEF 格式 | 用 `ndeflib` 库序列化 |
| 多张卡同时放上去无响应 | ACR122U 默认单卡 | 物理上只能放一张；不要并发 |
| `card.disconnect()` 卡死 | 卡片已被移除 | 加 timeout（5s）+ `ConnectionException` 捕获 |

---

## 2. LED 屏（onbon）

### 2.1 选型

onbon 不是统一 SDK——按控制器型号分：
- **BX-6（六代图文控制器）**：`BX_6SeriesDLL.dll`（Windows）或 `libbx6.so`（Linux）
- **BX-5（五代双基色）**：另一套 SDK
- **YQ / YC 系列**：多媒体播放器，又一套

**第一步**：确认展厅 LED 用的是哪个型号（联系采购 / 行政），再去 onbon 官网 https://www.onbonbx.com/download/SDK 下载对应包。

如果型号不明，发邮件到 `dev@onbonbx.com` 描述设备照片 + 序列号，他们回复很快。

### 2.2 实现 Real LED Adapter

**目标**：实现 `backend/app/adapters/led/real.py`。

**`display(screen_ids, content)` 要点**：
- `content.is_rejection=False`：调 SDK 的 `SendText(screen_id, name, welcome_text)` 或同等接口
- 多屏同步：MVP 阶段**全部 screen 同一批次内容**（§七.3 不做分组），所以可以并发调用 SDK

**`show_rejected(screen_ids, reason)` 要点**：
- 固定显示"无权限入场"（§三.3）
- 可选：附加 `reason`（如 `name_mismatch`）作为副标题或日志条目

**骨架示例**（伪代码，因 SDK 因型号而异）：
```python
class LedAdapterReal(LEDAdapter):
    def __init__(self, host, port, screen_ids):
        from onbon_sdk import Client  # 假设
        self._client = Client(host=host, port=port)
        self._screen_ids = screen_ids

    async def display(self, screen_ids, content):
        for sid in (screen_ids or self._screen_ids):
            await self._client.send_text(
                screen_id=sid,
                text=f"{content.name}  {content.welcome_text}",
                color="white",
                font_size=32,
            )

    async def show_rejected(self, screen_ids, reason=""):
        for sid in (screen_ids or self._screen_ids):
            await self._client.send_text(
                screen_id=sid,
                text="无权限入场",
                color="red",
                font_size=48,
            )
```

### 2.3 真机测试清单

- [ ] SDK `.dll` / `.so` 加载成功（Python `ctypes.CDLL` 不抛 OSError）
- [ ] `client.connect()` 建立 TCP/串口连接
- [ ] 调 `display()` → 物理屏上**立刻**显示测试文本
- [ ] 调 `show_rejected()` → 屏上变红字"无权限入场"
- [ ] 多屏时**所有屏同步显示**同一内容（§七.3）
- [ ] **断网测试**：拔 LED 控制器的网线 → `_poll_adapter_heartbeats` 在 30s 内把 `led` 标 `offline`，NavLayout 顶部红色告警条出现
- [ ] **重启测试**：LED 控制器断电重启 → 心跳恢复后告警自动消失

### 2.4 常见问题

| 症状 | 原因 | 修复 |
|---|---|---|
| SDK load 失败（Windows） | DLL 不在 PATH | 把 `.dll` 放 `backend/` 或加 `os.add_dll_directory()` |
| SDK load 失败（Linux） | `lib*.so.1` 找不到 | `LD_LIBRARY_PATH=/opt/onbon:$LD_LIBRARY_PATH` |
| send_text 无反应 | 协议端口错 / 屏幕离线 | `ping` 控制器 IP；查 SDK 文档的 default port |
| 中文乱码 | SDK 默认 GBK | 显式转 UTF-8 → GBK（`text.encode("gbk")`） |
| 部分屏显示、部分不显示 | 屏 ID 错 | 用厂商配置工具枚举所有 screen_id |

---

## 3. TTS 音响

### 3.1 Real adapter 已实现

`backend/app/adapters/tts/real.py::RealTTSAdapter` 已用 `pyttsx3` 实现。`main.py::_build_tts_adapter` 构造失败时降级 Mock。

### 3.2 真机启用步骤

```bash
cd backend
uv add pyttsx3  # 已装
# 不需要额外系统级依赖（macOS / Windows 自带 TTS 引擎）

# Linux 需要 espeak-ng
sudo apt install -y espeak-ng libespeak1
```

然后在 `Settings` 页面（或 `data/settings_override.json`）**无需任何配置**——只要 `pyttsx3.init()` 成功，RealTTSAdapter 就被自动选用。

### 3.3 中文音色验证

```bash
uv run python -c "
import pyttsx3
eng = pyttsx3.init()
voices = eng.getProperty('voices')
zh = [v for v in voices if any('zh' in str(l).lower() for l in v.languages)]
print(f'Chinese voices available: {len(zh)}')
for v in zh[:3]:
    print(f'  - {v.name!r} ({v.id!r})')
"
```

预期（macOS）：至少 Tingting / Eddy / Flo 等中文音色。
预期（Windows）：Microsoft Huihui / Xiaoxiao 等。
预期（Linux）：可能要 `apt install espeak-ng-voice-zh` 或下载中文 voice data。

如果 0 个中文 voice：
- macOS：System Settings → Accessibility → Spoken Content → System voice → Manage Voices → 下载中文
- Windows：Settings → Time & Language → Language → Chinese → Speech → Add voice
- Linux：`apt search espeak-ng-voice` 找中文包

### 3.4 真机测试清单

- [ ] 启动后端，能听到"测试成功"语音（用 `curl -X POST http://localhost:8000/api/debug/simulate-card-read -d '...'` 触发一次成功刷卡）
- [ ] 拒绝路径听到 1.5 秒 880Hz 蜂鸣（同一音响通道）
- [ ] 调整 `rate` / `voice_id`（构造函数参数）以适配展厅环境（语速、音色）
- [ ] **静音测试**：系统静音后 TTS 是否完全无输出（应该无声）；蜂鸣可能也无声，需要扬声器打开
- [ ] **多访客连刷**：触发 3 次连续成功刷卡，确认 TTS **严格按刷卡顺序**串行朗读（FIFO，由 §三.3 保证）

### 3.5 常见问题

| 症状 | 原因 | 修复 |
|---|---|---|
| `pyttsx3.init()` 抛异常 | 系统 TTS 引擎未装 | Linux 装 espeak-ng |
| 中文念成英文 | 默认 voice 是英文 | 显式 `setProperty('voice', '<zh_voice_id>')` |
| 朗读卡顿 2-3 秒 | pyttsx3 引擎初始化延迟 | `_build_tts_adapter` 已经异步化（`asyncio.to_thread`） |
| 蜂鸣无声 | macOS 默认音量 / 系统静音 | System Settings → Sound 调高 |
| 蜂鸣和语音不串行 | `asyncio.to_thread` 并发跑 | 已用 `await` 保证串行 |

---

## 4. AI 接口（千问 DashScope）

### 4.1 配置

不需要任何代码改动。只需：

1. 在阿里云 DashScope 控制台申请 API Key：https://dashscope.console.aliyun.com/
2. 在 `Settings` 页面填入 key（或直接编辑 `backend/data/settings_override.json`）
3. 重启后端（或仅刷新页面——`_build_ai_adapter` 在 `build_app` 时决定）

```json
// backend/data/settings_override.json
{"ai_api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"}
```

### 4.2 验证

```bash
curl -s http://localhost:8000/api/settings | python3 -m json.tool
# 应该看到 "has_ai_api_key": true

# 上传一条 Excel，触发 AI 生成
curl -X POST http://localhost:8000/api/import/preview -F "file=@fixtures/sample_visitors.xlsx"
# commit 后查 visits，welcome_source 应为 "ai" 而非 "fallback_template"
```

### 4.3 故障排查

| 症状 | 原因 | 修复 |
|---|---|---|
| `has_ai_api_key` 一直是 false | settings_override.json 没生效 | `main.py` 在 `build_app` 时 reload；重启后端 |
| 欢迎词为空（fallback_template） | DashScope API 失败 / key 无效 | `GET /api/work-logs?module=ai_writeup` 看 detail |
| 网络超时 | HTTPS_PROXY 干扰 | macOS 上 `httpx[socks]` 已支持 SOCKS5；HTTP proxy 见 `CLAUDE.md` Known dev quirks #4 |

---

## 5. 离线 / 故障模拟（§六.3）

按用户决策，**不内置随机故障**。但每个 adapter 的 mock 都接受故障注入，便于演示红色告警条：

```bash
# 临时把 MockNFCAdapter 改成 fail=True
# 改 backend/app/main.py 装配处，加一个环境变量开关：
#   NFCAdapter=MockNFCAdapter(fail=os.getenv("NFC_FAIL", "false") == "true")
# 然后：
NFC_FAIL=true uv run main.py

# 30 秒后看 NavLayout 顶部红色告警条
```

或编辑 `backend/app/main.py::_build_nfc_adapter` 加临时开关：

```python
def _build_nfc_adapter():
    import os
    return MockNFCAdapter(fail=os.getenv("NFC_FAIL") == "true")
```

### 验证矩阵

| 场景 | 期望 |
|---|---|
| `NFC_FAIL=true` 启动 30s 后 | NavLayout 顶部红条：`⚠️ 硬件离线：NFC` |
| `LED_FAIL=true` 启动 30s 后 | 红条：`⚠️ 硬件离线：LED` |
| 同时 `NFC_FAIL LED_FAIL TTS_FAIL` | 红条：`⚠️ 硬件离线：NFC / LED / TTS` |
| 移除环境变量重启 | 红条消失，4 个 adapter 全 online |

---

## 6. 完整真机端到端 smoke test

按这个顺序走一遍——模拟 §二.2 mermaid 流水线：

1. **打开管理后台**：浏览器 → http://localhost:5173/
2. **导入访客**：上传 `backend/fixtures/sample_visitors.xlsx` 到 `Registration` 页面，确认提交
3. **AI 生成**：等 2 秒，访客状态自动 `welcome_ready`（Welcome ready, card not yet written）
4. **值班人员写卡**：去 `/cards` 页面，勾选所有访客，点"批量写卡"，听不到声音（mock），但 `write-log` 表有记录
5. **现场大屏 + 模拟 LED**：同时打开 `/display` 和 `/mock-led`
6. **真机刷卡**：拿一张测试卡贴读卡器
   - 预期：物理 LED 屏显示姓名+欢迎词；音响朗读；`/mock-led` 实时更新
7. **拿错卡**：换一张未授权的卡
   - 预期：物理 LED 显示红色"无权限入场"；音响蜂鸣 1.5s；`/mock-led` 显示红色
8. **检查日志**：`/logs` 页面应该有 `module=tts action=speak` 和 `module=tts action=beep` 两条记录
9. **导出日志**：点"导出 Excel"，下载 `work_logs.xlsx`
10. **断电测试**：拔 NFC 读卡器 USB，30 秒后 NavLayout 顶部出现红色告警条

---

## 7. 部署清单

部署到展厅 Windows PC 之前的最后检查：

- [ ] `backend/data/settings_override.json` 含真实 `ai_api_key`
- [ ] `backend/.env`（如果用 .env 而非 settings_override）含 `EXCEL_WATCH_DIR=/path/to/excel_watched_dir`
- [ ] Windows 服务模式启动：`nssm install AITICBackend "C:\path\to\uv.exe" "run main.py"`
- [ ] 前端 build 后用 nginx / IIS 静态托管（CLAUDE.md §五"单机部署，不引入 Docker"）
- [ ] 防火墙允许 8000 / 5173 端口（如果远程访问后台）
- [ ] 计划任务：每天 02:00 触发 SQLite 备份（已自动，验证 `data/backup/` 有 .db 文件）

---

## 8. 相关文档

- [TARGET.md §三.3 §六.1 §七](../TARGET.md) — 现场欢迎模块规格、离线要求、不做清单
- [CLAUDE.md](../CLAUDE.md) — 架构、命令、known dev quirks
- [CHANGELOG.md](../CHANGELOG.md) — 此次实现的变更日志
- [openapi.json](./openapi.json) — 自动生成的 API 文档
- [完整实现计划](./AITIC展厅_智能前台_完整实现计划_V1.md) — 5 天冲刺原始计划
- [设计 spec](./superpowers/specs/2026-07-07-on-site-welcome-and-gaps-design.md) — 本次实现的详细设计