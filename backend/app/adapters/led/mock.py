from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, LEDAdapter, LEDContent


class MockLEDAdapter(LEDAdapter):
    def __init__(self) -> None:
        self.displayed: list[tuple[list[str], LEDContent]] = []
        self.rejected: list[list[str]] = []

    async def display(self, screen_ids: list[str], content: LEDContent) -> None:
        self.displayed.append((screen_ids, content))

    async def show_rejected(self, screen_ids: list[str]) -> None:
        self.rejected.append(screen_ids)

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
