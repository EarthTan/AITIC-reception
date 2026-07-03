from __future__ import annotations

from datetime import datetime, timezone

from app.models.adapter_status import AdapterHealthStatus, AdapterStatusRow


class AdapterStatusService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def handle_adapter_heartbeat(self, payload: dict) -> None:
        adapter_name = payload["adapter_name"]
        status = AdapterHealthStatus(payload["status"])
        detail = payload.get("detail")

        with self._session_factory() as session:
            row = session.get(AdapterStatusRow, adapter_name)
            if row is None:
                row = AdapterStatusRow(
                    adapter_name=adapter_name,
                    status=status,
                    last_heartbeat=datetime.now(timezone.utc),
                    detail=detail,
                )
                session.add(row)
            else:
                row.status = status
                row.detail = detail
                row.last_heartbeat = datetime.now(timezone.utc)
            session.commit()
