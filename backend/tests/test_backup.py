# backend/tests/test_backup.py
from datetime import datetime

from app.core.backup import backup_database, schedule_daily_backup
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def test_backup_database_copies_file_with_timestamped_name(tmp_path):
    db_path = tmp_path / "app.db"
    db_path.write_bytes(b"fake-sqlite-bytes")
    backup_dir = tmp_path / "backup"

    destination = backup_database(
        str(db_path), str(backup_dir), now=datetime(2026, 7, 6, 2, 0, 0)
    )

    assert destination.name == "app_20260706_020000.db"
    assert destination.read_bytes() == b"fake-sqlite-bytes"


def test_schedule_daily_backup_registers_a_2am_cron_job(tmp_path):
    scheduler = BackgroundScheduler()
    schedule_daily_backup(scheduler, str(tmp_path / "app.db"), str(tmp_path / "backup"))

    job = scheduler.get_job("daily_db_backup")
    assert job is not None
    assert isinstance(job.trigger, CronTrigger)
