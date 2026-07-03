# backend/tests/test_models.py
from datetime import date, datetime

from app.core.db import Base, make_engine, make_session_factory
from app.core.seed import seed_default_templates
from app.models.adapter_status import AdapterHealthStatus, AdapterStatusRow
from app.models.nfc_write_log import NFCWriteLog, WriteStatus
from app.models.verify_log import VerifyLog, VerifyResult
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus
from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate
from app.models.work_log import LogModule, LogStatus, WorkLog


def _fresh_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def test_all_six_tables_accept_one_row_each():
    session_factory = _fresh_session_factory()
    with session_factory() as session:
        visit = Visit(
            visit_date=date(2026, 7, 6),
            session_time=datetime(2026, 7, 6, 10, 0),
            name="张三",
            identity_type=IdentityType.ENTERPRISE_LEADER,
            entry_source=EntrySource.MANUAL,
            import_batch_id="batch-1",
            status=VisitStatus.PENDING,
        )
        session.add(visit)
        session.flush()

        session.add(
            WelcomeTemplate(
                identity_type=TemplateIdentityType.DEFAULT,
                template_text="{姓名}，欢迎您",
            )
        )
        session.add(
            NFCWriteLog(
                visit_id=visit.id, card_uid="UID-1", write_status=WriteStatus.SUCCESS
            )
        )
        session.add(
            VerifyLog(
                card_uid="UID-1", visit_id=visit.id, verify_result=VerifyResult.PASS
            )
        )
        session.add(
            WorkLog(
                module=LogModule.REGISTRATION,
                action="import",
                status=LogStatus.SUCCESS,
                detail="ok",
            )
        )
        session.add(
            AdapterStatusRow(
                adapter_name="nfc",
                status=AdapterHealthStatus.ONLINE,
                last_heartbeat=datetime.utcnow(),
            )
        )
        session.commit()

        assert session.query(Visit).count() == 1
        assert session.query(WelcomeTemplate).count() == 1
        assert session.query(NFCWriteLog).count() == 1
        assert session.query(VerifyLog).count() == 1
        assert session.query(WorkLog).count() == 1
        assert session.query(AdapterStatusRow).count() == 1


def test_seed_default_templates_creates_seven_rows():
    session_factory = _fresh_session_factory()
    with session_factory() as session:
        seed_default_templates(session)
        rows = {
            row.identity_type: row.template_text
            for row in session.query(WelcomeTemplate).all()
        }

    assert len(rows) == 7
    assert rows[TemplateIdentityType.GOVERNMENT_OFFICIAL] == "欢迎{姓名}同志到场视察"
    assert rows[TemplateIdentityType.SCHOOL_STUDENT] == "{姓名}同学，你好呀"


def test_seed_default_templates_is_idempotent():
    session_factory = _fresh_session_factory()
    with session_factory() as session:
        seed_default_templates(session)
        seed_default_templates(session)
        assert session.query(WelcomeTemplate).count() == 7
