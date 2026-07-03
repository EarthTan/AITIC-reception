from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.verify_log import FailReason, VerifyResult
from app.models.work_log import LogModule, LogStatus


class VerifyLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_uid: str
    visit_id: int | None
    verify_result: VerifyResult
    fail_reason: FailReason | None
    verified_at: datetime


class WorkLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module: LogModule
    action: str
    status: LogStatus
    detail: str | None
    created_at: datetime
