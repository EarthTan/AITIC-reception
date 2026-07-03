from app.core.db import Base, make_engine, make_session_factory
from app.models.work_log import LogModule, LogStatus, WorkLog
from app.services.log_service import LogService


async def test_handle_work_log_append_persists_a_row():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    service = LogService(session_factory)

    await service.handle_work_log_append(
        {
            "module": "registration",
            "action": "import_file",
            "status": "success",
            "detail": "批次x导入1条记录",
        }
    )

    with session_factory() as session:
        row = session.query(WorkLog).one()
        assert row.module == LogModule.REGISTRATION
        assert row.action == "import_file"
        assert row.status == LogStatus.SUCCESS
        assert row.detail == "批次x导入1条记录"
