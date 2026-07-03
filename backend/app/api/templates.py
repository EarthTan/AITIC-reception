# backend/app/api/templates.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate
from app.schemas.template import TemplateOut, TemplateUpdate

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)) -> list[TemplateOut]:
    templates = db.execute(select(WelcomeTemplate)).scalars().all()
    return [TemplateOut.model_validate(t) for t in templates]


@router.put("/{identity_type}", response_model=TemplateOut)
def update_template(
    identity_type: str, body: TemplateUpdate, db: Session = Depends(get_db)
) -> TemplateOut:
    try:
        identity = TemplateIdentityType(identity_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="未知的身份类型") from exc

    template = db.execute(
        select(WelcomeTemplate).where(WelcomeTemplate.identity_type == identity)
    ).scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="模板不存在")

    template.template_text = body.template_text
    db.commit()
    db.refresh(template)
    return TemplateOut.model_validate(template)
