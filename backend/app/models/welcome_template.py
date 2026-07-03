import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TemplateIdentityType(str, enum.Enum):
    DEFAULT = "默认"
    ENTERPRISE_LEADER = "企业领导"
    ENTERPRISE_STAFF = "企业员工"
    SCHOOL_TEACHER = "学校老师"
    UNIVERSITY_STUDENT = "大学生"
    SCHOOL_STUDENT = "中小学生"
    GOVERNMENT_OFFICIAL = "政府官员"


class WelcomeTemplate(Base):
    __tablename__ = "welcome_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identity_type: Mapped[TemplateIdentityType] = mapped_column(
        Enum(TemplateIdentityType), nullable=False, unique=True
    )
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
