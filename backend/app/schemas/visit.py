from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.visit import (
    EntrySource,
    IdentityType,
    Visit,
    VisitStatus,
    WelcomeSource,
)


def mask_id_number(id_number: str | None) -> str | None:
    """Return ``id_number`` with the middle replaced by exactly 7 asterisks.

    Keeps the first 3 and last 4 characters when the input is at least 7 chars
    long; otherwise returns the value unchanged. ``None`` passes through.
    """
    if not id_number or len(id_number) < 7:
        return id_number
    return f"{id_number[:3]}{'*' * 7}{id_number[-4:]}"


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_date: date
    session_time: datetime
    name: str
    phone: str | None
    nationality: str | None
    id_number: str | None
    gender: str | None
    organization: str | None
    identity_type: IdentityType
    welcome_text: str | None
    welcome_source: WelcomeSource | None
    entry_source: EntrySource
    import_batch_id: str
    status: VisitStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_visit(cls, visit: Visit) -> "VisitOut":
        out = cls.model_validate(visit)
        out.id_number = mask_id_number(out.id_number)
        return out


class VisitUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    nationality: str | None = None
    gender: str | None = None
    organization: str | None = None
    identity_type: IdentityType | None = None


class ImportPreviewRow(BaseModel):
    row_number: int
    data: dict
    errors: list[str]
    is_valid: bool


class ImportPreviewResponse(BaseModel):
    preview_id: str
    rows: list[ImportPreviewRow]
    valid_count: int
    invalid_count: int


class ImportCommitRequest(BaseModel):
    preview_id: str


class ImportCommitResponse(BaseModel):
    import_batch_id: str
    visit_ids: list[int]


class VisitSummaryRow(BaseModel):
    visit_date: date
    session_time: datetime
    visit_count: int
    visits: list[VisitOut]
