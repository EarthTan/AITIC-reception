import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class IdentityType(str, enum.Enum):
    ENTERPRISE_LEADER = "企业领导"
    ENTERPRISE_STAFF = "企业员工"
    SCHOOL_TEACHER = "学校老师"
    UNIVERSITY_STUDENT = "大学生"
    SCHOOL_STUDENT = "中小学生"
    GOVERNMENT_OFFICIAL = "政府官员"


class WelcomeSource(str, enum.Enum):
    AI = "ai"
    FALLBACK_TEMPLATE = "fallback_template"


class EntrySource(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class VisitStatus(str, enum.Enum):
    PENDING = "pending"
    WELCOME_READY = "welcome_ready"
    CARD_WRITTEN = "card_written"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identity_type: Mapped[IdentityType] = mapped_column(
        Enum(IdentityType), nullable=False
    )
    welcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    welcome_source: Mapped[WelcomeSource | None] = mapped_column(
        Enum(WelcomeSource), nullable=True
    )
    entry_source: Mapped[EntrySource] = mapped_column(Enum(EntrySource), nullable=False)
    import_batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus), nullable=False, default=VisitStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
