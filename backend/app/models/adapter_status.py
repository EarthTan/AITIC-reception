import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AdapterHealthStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class AdapterStatusRow(Base):
    __tablename__ = "adapter_status"

    adapter_name: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[AdapterHealthStatus] = mapped_column(
        Enum(AdapterHealthStatus), nullable=False
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
