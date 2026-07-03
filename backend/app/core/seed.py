from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate

DEFAULT_TEMPLATES: dict[TemplateIdentityType, str] = {
    TemplateIdentityType.DEFAULT: "{姓名}先生/女士，欢迎您",
    TemplateIdentityType.ENTERPRISE_LEADER: "{姓名}先生/女士，欢迎您",
    TemplateIdentityType.ENTERPRISE_STAFF: "{姓名}先生/女士，欢迎您",
    TemplateIdentityType.GOVERNMENT_OFFICIAL: "欢迎{姓名}同志到场视察",
    TemplateIdentityType.SCHOOL_TEACHER: "欢迎{姓名}专家到场指导",
    TemplateIdentityType.UNIVERSITY_STUDENT: "{姓名}同学，欢迎参观",
    TemplateIdentityType.SCHOOL_STUDENT: "{姓名}同学，你好呀",
}


def seed_default_templates(session: Session) -> None:
    existing = {row.identity_type for row in session.query(WelcomeTemplate).all()}
    for identity_type, template_text in DEFAULT_TEMPLATES.items():
        if identity_type in existing:
            continue
        session.add(
            WelcomeTemplate(identity_type=identity_type, template_text=template_text)
        )
    session.commit()
