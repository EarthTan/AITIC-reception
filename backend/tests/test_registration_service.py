# backend/tests/test_registration_service.py
import asyncio

import pandas as pd
from app.core.db import Base, make_engine, make_session_factory
from app.core.event_bus import EventBus
from app.models.visit import EntrySource, Visit, VisitStatus
from app.services.registration_service import RegistrationService


def _fresh_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def _write_fixture_excel(path, rows):
    pd.DataFrame(rows).to_excel(path, index=False)


VALID_ROW = {
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


def test_parse_excel_flags_missing_mandatory_field_and_bad_identity(tmp_path):
    path = tmp_path / "visitors.xlsx"
    bad_row = dict(VALID_ROW, 姓名="", 身份="外星人")
    _write_fixture_excel(path, [VALID_ROW, bad_row])

    service = RegistrationService(_fresh_session_factory(), EventBus())
    parsed_rows = service.parse_excel(str(path))

    assert parsed_rows[0].is_valid
    assert not parsed_rows[1].is_valid
    assert "姓名不能为空" in parsed_rows[1].errors
    assert any("身份取值非法" in error for error in parsed_rows[1].errors)


async def test_import_file_commits_valid_rows_and_publishes_events(tmp_path):
    path = tmp_path / "visitors.xlsx"
    bad_row = dict(VALID_ROW, 姓名="")
    _write_fixture_excel(path, [VALID_ROW, bad_row])

    session_factory = _fresh_session_factory()
    event_bus = EventBus()
    imported_queue = event_bus.subscribe("visit.imported")
    requested_queue = event_bus.subscribe("welcome.requested")
    work_log_queue = event_bus.subscribe("work_log.append")

    service = RegistrationService(session_factory, event_bus)
    import_batch_id, visit_ids = await service.import_file(
        str(path), EntrySource.MANUAL
    )

    assert len(visit_ids) == 1
    with session_factory() as session:
        visit = session.get(Visit, visit_ids[0])
        assert visit.name == "张三"
        assert visit.status == VisitStatus.PENDING
        assert visit.import_batch_id == import_batch_id

    imported_payload = await asyncio.wait_for(imported_queue.get(), timeout=1)
    assert imported_payload == {
        "visit_ids": visit_ids,
        "import_batch_id": import_batch_id,
    }

    requested_payload = await asyncio.wait_for(requested_queue.get(), timeout=1)
    assert requested_payload == {"visit_id": visit_ids[0]}

    statuses = set()
    for _ in range(2):
        entry = await asyncio.wait_for(work_log_queue.get(), timeout=1)
        statuses.add(entry["status"])
    assert statuses == {"warning", "success"}


async def test_handle_excel_detected_imports_the_given_file(tmp_path):
    path = tmp_path / "visitors.xlsx"
    _write_fixture_excel(path, [VALID_ROW])

    session_factory = _fresh_session_factory()
    event_bus = EventBus()
    event_bus.subscribe("visit.imported")
    event_bus.subscribe("welcome.requested")
    event_bus.subscribe("work_log.append")

    service = RegistrationService(session_factory, event_bus)
    await service.handle_excel_detected({"file_path": str(path)})

    with session_factory() as session:
        assert (
            session.query(Visit).filter_by(entry_source=EntrySource.AUTO).count() == 1
        )
