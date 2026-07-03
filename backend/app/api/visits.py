# backend/app/api/visits.py
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.visit import IdentityType, Visit
from app.schemas.visit import VisitOut, VisitSummaryRow, VisitUpdate

router = APIRouter(prefix="/api/visits", tags=["visits"])


@router.get("", response_model=list[VisitOut])
def list_visits(
    db: Session = Depends(get_db),
    visit_date: date | None = Query(default=None),
    identity_type: IdentityType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> list[VisitOut]:
    stmt = select(Visit)
    if visit_date is not None:
        stmt = stmt.where(Visit.visit_date == visit_date)
    if identity_type is not None:
        stmt = stmt.where(Visit.identity_type == identity_type)
    stmt = stmt.order_by(Visit.id).offset((page - 1) * page_size).limit(page_size)
    visits = db.execute(stmt).scalars().all()
    return [VisitOut.from_visit(v) for v in visits]


def _month_bounds(month: str) -> tuple[date, date]:
    year, month_num = (int(part) for part in month.split("-"))
    start = date(year, month_num, 1)
    end = date(year + 1, 1, 1) if month_num == 12 else date(year, month_num + 1, 1)
    return start, end


@router.get("/summary", response_model=list[VisitSummaryRow])
def visit_summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)
) -> list[VisitSummaryRow]:
    start, end = _month_bounds(month)
    stmt = (
        select(Visit)
        .where(Visit.visit_date >= start, Visit.visit_date < end)
        .order_by(Visit.visit_date, Visit.session_time)
    )
    visits = db.execute(stmt).scalars().all()

    groups: dict[tuple[date, datetime], list[Visit]] = {}
    for visit in visits:
        groups.setdefault((visit.visit_date, visit.session_time), []).append(visit)

    return [
        VisitSummaryRow(
            visit_date=key[0],
            session_time=key[1],
            visit_count=len(rows),
            visits=[VisitOut.from_visit(v) for v in rows],
        )
        for key, rows in sorted(groups.items())
    ]


@router.get("/summary/export")
def export_visit_summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)
):
    from io import BytesIO

    import pandas as pd
    from fastapi.responses import StreamingResponse

    groups = visit_summary(month=month, db=db)
    records = [
        {
            "来访日期": group.visit_date.isoformat(),
            "计划场次时间": group.session_time.isoformat(),
            "姓名": visit.name,
            "身份": visit.identity_type.value,
            "单位": visit.organization,
            "欢迎词": visit.welcome_text,
            "状态": visit.status.value,
        }
        for group in groups
        for visit in group.visits
    ]
    frame = pd.DataFrame(records)
    buffer = BytesIO()
    frame.to_excel(buffer, index=False, sheet_name="月度汇总")
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=summary_{month}.xlsx"},
    )


@router.get("/today", response_model=list[VisitOut])
def today_visits(db: Session = Depends(get_db)) -> list[VisitOut]:
    stmt = (
        select(Visit)
        .where(Visit.visit_date == date.today())
        .order_by(Visit.session_time)
    )
    visits = db.execute(stmt).scalars().all()
    return [VisitOut.from_visit(v) for v in visits]


@router.get("/{visit_id}", response_model=VisitOut)
def get_visit(visit_id: int, db: Session = Depends(get_db)) -> VisitOut:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="访客记录不存在")
    return VisitOut.from_visit(visit)


@router.patch("/{visit_id}", response_model=VisitOut)
def update_visit(
    visit_id: int, body: VisitUpdate, db: Session = Depends(get_db)
) -> VisitOut:
    """Update editable person fields. Does NOT re-trigger AI welcome generation."""
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="访客记录不存在")
    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(visit, field_name, value)
    db.commit()
    db.refresh(visit)
    return VisitOut.from_visit(visit)
