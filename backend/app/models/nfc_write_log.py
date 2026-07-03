import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WriteStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class NFCWriteLog(Base):
    __tablename__ = "nfc_write_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("visits.id"), nullable=False
    )
    card_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    write_status: Mapped[WriteStatus] = mapped_column(Enum(WriteStatus), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    written_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
