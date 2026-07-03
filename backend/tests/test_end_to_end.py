# backend/tests/test_end_to_end.py
import asyncio

import pandas as pd
from app.adapters.ai.mock import MockAIAdapter
from app.adapters.nfc.mock import MockNFCAdapter
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.core.seed import seed_default_templates
from app.models.visit import EntrySource, Visit, VisitStatus
from app.models.work_log import WorkLog
from app.services.ai_writeup_service import AIWriteupWorker
from app.services.card_service import CardService
from app.services.log_service import LogService
from app.services.registration_service import RegistrationService
from app.services.verify_service import VerifyService


async def test_full_pipeline_runs_end_to_end_without_error(tmp_path):
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        seed_default_templates(session)

    event_bus = EventBus()
    nfc_adapter = MockNFCAdapter()
    ai_adapter = MockAIAdapter()

    registration_service = RegistrationService(session_factory, event_bus)
    ai_writeup_worker = AIWriteupWorker(session_factory, event_bus, ai_adapter)
    card_service = CardService(session_factory, event_bus, nfc_adapter)
    verify_service = VerifyService(session_factory, event_bus)
    log_service = LogService(session_factory)

    welcome_requested_queue = event_bus.subscribe("welcome.requested")
    welcome_generated_queue = event_bus.subscribe("welcome.generated")
    card_write_queue = event_bus.subscribe("card.write.completed")
    verify_passed_queue = event_bus.subscribe("card.verify.passed")
    work_log_queue = event_bus.subscribe("work_log.append")

    # 模拟"值班人员将访客名单Excel放入指定文件夹"这一步产出的文件
    excel_path = tmp_path / "visitors.xlsx"
    pd.DataFrame(
        [
            {
                "来访日期": "2026-07-06",
                "计划场次时间": "2026-07-06 10:00",
                "姓名": "张三",
                "手机号": "13800000000",
                "国籍": "中国",
                "身份证号": "110000000000000000",
                "性别": "男",
                "单位": "AITIC",
                "身份": "企业领导",
            }
        ]
    ).to_excel(excel_path, index=False)

    # 登记
    _, visit_ids = await registration_service.import_file(
        str(excel_path), EntrySource.MANUAL
    )
    assert len(visit_ids) == 1
    visit_id = visit_ids[0]

    # AI（mock）生成欢迎词
    await ai_writeup_worker.handle_welcome_requested(
        await asyncio.wait_for(welcome_requested_queue.get(), timeout=5)
    )
    welcome_generated_payload = await asyncio.wait_for(
        welcome_generated_queue.get(), timeout=5
    )
    assert welcome_generated_payload["visit_id"] == visit_id

    # 写卡（mock）
    await card_service.handle_welcome_generated(welcome_generated_payload)
    card_write_payload = await asyncio.wait_for(card_write_queue.get(), timeout=5)
    assert card_write_payload["status"] == "success"

    # 现场刷卡校验（mock：读回写入卡片的内容）
    card_uid = card_write_payload["card_uid"]
    written_payload = nfc_adapter.get_written_payload(card_uid)
    await nfc_adapter.simulate_card_read(card_uid, written_payload)
    card_read_event = await anext(nfc_adapter.read_stream())
    await verify_service.handle_card_verify_requested(
        {
            "card_uid": card_read_event.card_uid,
            "raw_payload": card_read_event.raw_payload,
        }
    )
    verify_passed_payload = await asyncio.wait_for(verify_passed_queue.get(), timeout=5)
    assert verify_passed_payload["visit_id"] == visit_id

    # 工作日志：消费本次流程中产生的所有 work_log.append 事件
    while not work_log_queue.empty():
        await log_service.handle_work_log_append(
            await asyncio.wait_for(work_log_queue.get(), timeout=5)
        )

    with session_factory() as session:
        visit = session.get(Visit, visit_id)
        assert visit.status == VisitStatus.VERIFIED
        assert session.query(WorkLog).count() >= 3
