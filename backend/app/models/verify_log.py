import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class VerifyResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"


class FailReason(str, enum.Enum):
    NAME_MISMATCH = "name_mismatch"
    DATE_MISMATCH = "date_mismatch"
    CARD_NOT_FOUND = "card_not_found"


class VerifyLog(Base):
    __tablename__ = "verify_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    visit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("visits.id"), nullable=True
    )
    verify_result: Mapped[VerifyResult] = mapped_column(
        Enum(VerifyResult), nullable=False
    )
    fail_reason: Mapped[FailReason | None] = mapped_column(
        Enum(FailReason), nullable=True
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
