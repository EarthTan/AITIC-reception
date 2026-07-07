from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_services
from app.models.nfc_write_log import NFCWriteLog
from app.models.visit import Visit
from app.schemas.card import CardWriteLogOut, CardWriteRequest, CardWriteResult

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.post("/write", response_model=list[CardWriteResult])
async def write_cards(
    body: CardWriteRequest,
    services: dict = Depends(get_services),
    db: Session = Depends(get_db),
) -> list[CardWriteResult]:
    """手动触发写卡（TARGET §3.2：值班人员点击"批量写卡"按钮触发）。

    不再由 welcome.generated 自动驱动——值班人员必须确认后才写卡。
    """
    card_service = services["card"]
    results: list[CardWriteResult] = []
    for visit_id in body.visit_ids:
        await card_service.write_card_for_visit({"visit_id": visit_id})
        write_log = (
            db.execute(
                select(NFCWriteLog)
                .where(NFCWriteLog.visit_id == visit_id)
                .order_by(NFCWriteLog.id.desc())
            )
            .scalars()
            .first()
        )
        results.append(
            CardWriteResult(
                visit_id=visit_id,
                status=write_log.write_status.value if write_log else "failed",
                error_message=write_log.error_message if write_log else "访客不存在",
            )
        )
    return results


@router.get("/write-log", response_model=list[CardWriteLogOut])
def list_write_log(
    visit_id: int | None = Query(default=None), db: Session = Depends(get_db)
) -> list[CardWriteLogOut]:
    stmt = select(NFCWriteLog).order_by(NFCWriteLog.id.desc())
    if visit_id is not None:
        stmt = stmt.where(NFCWriteLog.visit_id == visit_id)
    logs = db.execute(stmt).scalars().all()
    return [CardWriteLogOut.model_validate(log) for log in logs]
