from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.welcome_template import TemplateIdentityType


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identity_type: TemplateIdentityType
    template_text: str
    updated_at: datetime


class TemplateUpdate(BaseModel):
    template_text: str
