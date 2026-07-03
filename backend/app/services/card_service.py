# backend/app/services/card_service.py
from __future__ import annotations

from app.adapters.base import NFCAdapter
from app.core.event_bus import EventBus
from app.models.nfc_write_log import NFCWriteLog, WriteStatus
from app.models.visit import Visit, VisitStatus


class CardService:
    def __init__(
        self, session_factory, event_bus: EventBus, nfc_adapter: NFCAdapter
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._nfc_adapter = nfc_adapter

    async def handle_welcome_generated(self, payload: dict) -> None:
        visit_id = payload["visit_id"]
        with self._session_factory() as session:
            visit = session.get(Visit, visit_id)
            if visit is None:
                return
            card_uid = f"MOCK-{visit_id}"
            card_payload = {
                "visit_id": visit.id,
                "name": visit.name,
                "visit_date": visit.visit_date.isoformat(),
                "identity_type": visit.identity_type.value,
                "welcome_text": visit.welcome_text,
            }
            result = await self._nfc_adapter.write_card(card_uid, card_payload)

            session.add(
                NFCWriteLog(
                    visit_id=visit_id,
                    card_uid=result.card_uid,
                    write_status=WriteStatus.SUCCESS
                    if result.success
                    else WriteStatus.FAILED,
                    error_message=result.error_message,
                )
            )
            if result.success:
                visit.status = VisitStatus.CARD_WRITTEN
            session.commit()

        await self._event_bus.publish(
            "card.write.completed",
            {
                "visit_id": visit_id,
                "card_uid": card_uid,
                "status": "success" if result.success else "failed",
            },
        )
        await self._event_bus.publish(
            "work_log.append",
            {
                "module": "card_write",
                "action": "write_card",
                "status": "success" if result.success else "failure",
                "detail": f"visit_id={visit_id} card_uid={card_uid}",
            },
        )
