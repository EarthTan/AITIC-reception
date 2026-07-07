# backend/app/services/verify_service.py
from __future__ import annotations

from app.core.event_bus import EventBus
from app.models.verify_log import FailReason, VerifyLog, VerifyResult
from app.models.visit import Visit, VisitStatus


class VerifyService:
    def __init__(self, session_factory, event_bus: EventBus) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus

    async def handle_card_verify_requested(self, payload: dict) -> None:
        card_uid = payload["card_uid"]
        raw_payload = payload["raw_payload"]
        visit_id = raw_payload.get("visit_id")

        with self._session_factory() as session:
            visit = session.get(Visit, visit_id) if visit_id is not None else None

            fail_reason: FailReason | None = None
            if visit is None:
                fail_reason = FailReason.CARD_NOT_FOUND
            elif visit.name != raw_payload.get("name"):
                fail_reason = FailReason.NAME_MISMATCH
            elif visit.visit_date.isoformat() != raw_payload.get("visit_date"):
                fail_reason = FailReason.DATE_MISMATCH

            session.add(
                VerifyLog(
                    card_uid=card_uid,
                    visit_id=visit.id if visit else None,
                    verify_result=VerifyResult.FAIL
                    if fail_reason
                    else VerifyResult.PASS,
                    fail_reason=fail_reason,
                )
            )
            if visit and fail_reason is None:
                visit.status = VisitStatus.VERIFIED
            elif visit and fail_reason is not None:
                visit.status = VisitStatus.REJECTED
            session.commit()

        if fail_reason is None:
            await self._event_bus.publish(
                "card.verify.passed", {"visit_id": visit_id, "card_uid": card_uid}
            )
            log_status, log_detail = (
                "success",
                f"card_uid={card_uid} visit_id={visit_id} 校验通过",
            )
        else:
            await self._event_bus.publish(
                "card.verify.failed",
                {
                    "visit_id": visit_id,
                    "card_uid": card_uid,
                    "fail_reason": fail_reason.value,
                },
            )
            log_status = "warning"
            log_detail = f"card_uid={card_uid} 校验失败: {fail_reason.value}"

        await self._event_bus.publish(
            "work_log.append",
            {
                "module": "verify",
                "action": "verify_card",
                "status": log_status,
                "detail": log_detail,
            },
        )
