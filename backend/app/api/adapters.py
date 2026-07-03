# backend/app/api/adapters.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.adapter_status import AdapterStatusRow
from app.schemas.adapter import AdapterStatusOut

router = APIRouter(prefix="/api/adapters", tags=["adapters"])


@router.get("/status", response_model=list[AdapterStatusOut])
def adapter_status(db: Session = Depends(get_db)) -> list[AdapterStatusOut]:
    rows = db.execute(select(AdapterStatusRow)).scalars().all()
    return [AdapterStatusOut.model_validate(row) for row in rows]
