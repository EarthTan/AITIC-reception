from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, AIAdapter, VisitInfo


class MockAIAdapter(AIAdapter):
    def __init__(self, raise_error: bool = False) -> None:
        self.raise_error = raise_error
        self.requests: list[VisitInfo] = []

    async def generate_welcome(self, visit: VisitInfo) -> str:
        self.requests.append(visit)
        if self.raise_error:
            raise RuntimeError("mock AI adapter configured to fail")
        return f"{visit.name}，欢迎您（mock-ai）"

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
