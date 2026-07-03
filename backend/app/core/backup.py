# backend/app/core/backup.py
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def backup_database(db_path: str, backup_dir: str, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    source = Path(db_path)
    destination_dir = Path(backup_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{source.stem}_{now:%Y%m%d_%H%M%S}{source.suffix}"
    shutil.copy2(source, destination)
    return destination


def schedule_daily_backup(scheduler, db_path: str, backup_dir: str) -> None:
    from apscheduler.triggers.cron import CronTrigger

    scheduler.add_job(
        backup_database,
        trigger=CronTrigger(hour=2, minute=0),
        kwargs={"db_path": db_path, "backup_dir": backup_dir},
        id="daily_db_backup",
        replace_existing=True,
    )
