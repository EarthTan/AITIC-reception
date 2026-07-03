from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.adapter_status import AdapterHealthStatus


class AdapterStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    adapter_name: str
    status: AdapterHealthStatus
    last_heartbeat: datetime
    detail: str | None
