from __future__ import annotations

from app.models.work_log import LogModule, LogStatus, WorkLog


class LogService:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def handle_work_log_append(self, payload: dict) -> None:
        with self._session_factory() as session:
            session.add(
                WorkLog(
                    module=LogModule(payload["module"]),
                    action=payload["action"],
                    status=LogStatus(payload["status"]),
                    detail=payload.get("detail"),
                )
            )
            session.commit()
