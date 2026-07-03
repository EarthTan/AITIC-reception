# backend/app/api/logs.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.verify_log import VerifyLog
from app.models.work_log import LogModule, LogStatus, WorkLog
from app.schemas.log import VerifyLogOut, WorkLogOut

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/verify-log", response_model=list[VerifyLogOut])
def list_verify_log(db: Session = Depends(get_db)) -> list[VerifyLogOut]:
    logs = db.execute(select(VerifyLog).order_by(VerifyLog.id.desc())).scalars().all()
    return [VerifyLogOut.model_validate(log) for log in logs]


@router.get("/work-logs", response_model=list[WorkLogOut])
def list_work_logs(
    module: LogModule | None = Query(default=None),
    status: LogStatus | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[WorkLogOut]:
    stmt = select(WorkLog).order_by(WorkLog.id.desc())
    if module is not None:
        stmt = stmt.where(WorkLog.module == module)
    if status is not None:
        stmt = stmt.where(WorkLog.status == status)
    logs = db.execute(stmt).scalars().all()
    return [WorkLogOut.model_validate(log) for log in logs]
