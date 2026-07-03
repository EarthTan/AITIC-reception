from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.nfc_write_log import WriteStatus


class CardWriteRequest(BaseModel):
    visit_ids: list[int]


class CardWriteResult(BaseModel):
    visit_id: int
    status: str
    error_message: str | None = None


class CardWriteLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    card_uid: str | None
    write_status: WriteStatus
    error_message: str | None
    written_at: datetime
