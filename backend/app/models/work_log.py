import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LogModule(str, enum.Enum):
    REGISTRATION = "registration"
    AI_WRITEUP = "ai_writeup"
    CARD_WRITE = "card_write"
    VERIFY = "verify"
    LED = "led"
    TTS = "tts"
    SYSTEM = "system"


class LogStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"


class WorkLog(Base):
    __tablename__ = "work_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[LogModule] = mapped_column(Enum(LogModule), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[LogStatus] = mapped_column(Enum(LogStatus), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
