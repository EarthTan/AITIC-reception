from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, TTSAdapter


class MockTTSAdapter(TTSAdapter):
    def __init__(self) -> None:
        self.spoken: list[str] = []

    async def enqueue_speech(self, text: str) -> None:
        self.spoken.append(text)

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
