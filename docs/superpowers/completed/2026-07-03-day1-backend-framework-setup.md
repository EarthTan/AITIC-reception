# Day 1 · 后端基本框架搭建 — 完成报告

**日期:** 2026-07-03  
**分支:** master  
**提交数:** 22 commits  
**测试结果:** 44/44 passed ✅

---

## 交付清单

| 任务 | 描述 | 测试 |
|------|------|------|
| Task 1 | Repo 重构至 `backend/`，uv 项目搭建 | — |
| Task 2 | EventBus (`asyncio.Queue` pub/sub) | 5 |
| Task 3 | Settings (pydantic-settings) + Logging | 4 |
| Task 4 | DB engine/session + `session_scope` | 2 |
| Task 5 | 6 个 SQLAlchemy 模型 + 模板种子数据 | 3 |
| Task 6 | 适配器 schemas + 4 个抽象基类 | 7 |
| Task 7 | 4 个 Mock 适配器 (NFC/LED/TTS/AI) | 6 |
| Task 8 | RegistrationService (Excel 解析/校验/导入) | 3 |
| Task 9 | AIWriteupWorker (AI 生成 + 模板降级) | 2 |
| Task 10 | CardService (NFC 写卡) | 1 |
| Task 11 | VerifyService (刷卡校验) | 4 |
| Task 12 | LogService (工作日志持久化) | 1 |
| Task 13 | ExcelWatcher (watchdog 文件夹监控) | 2 |
| Task 14 | `app/main.py` 组装启动入口 | 1 |
| Task 15 | 端到端自测 (登记→AI→写卡→校验→日志) | 1 |
| Task 16 | 每日 SQLite 备份 (APScheduler) | 2 |

---

## 架构概览

```
backend/
├── main.py                    # uv run main.py → uvicorn
├── app/
│   ├── main.py                # build_app(): 组装一切
│   ├── core/                  # EventBus, Settings, DB, Logging, Backup, Seed
│   ├── models/                # Visit, WelcomeTemplate, NFCWriteLog, VerifyLog, WorkLog, AdapterStatus
│   ├── adapters/              # 4 ABCs + 4 Mock 实现 (nfc/led/tts/ai)
│   ├── services/              # Registration, AIWriteup, Card, Verify, Log
│   └── watchers/              # ExcelWatcher
└── tests/                     # 44 个测试，14 个测试文件
```

**事件管线:** `excel.detected` → `visit.imported` → `welcome.requested` → `welcome.generated` → `card.write.completed` → `card.verify.requested` → verify pass/fail  
**旁路日志:** 所有服务均发布 `work_log.append`，由 LogService 统一持久化

---

## 启动方式

```bash
cd backend
uv run main.py          # 启动 FastAPI (:8000)
uv run pytest           # 运行 44 个测试
```

## 后续

Day 2 将添加 FastAPI 路由（手动登记、查询、调试端点），连接前端 API 层。
