from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, TTSAdapter


class MockTTSAdapter(TTSAdapter):
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.beeps: list[tuple[float, ...]] = []

    async def enqueue_speech(self, text: str) -> None:
        self.spoken.append(text)

    async def play_beep(self, duration_seconds: float = 1.5) -> None:
        self.beeps.append((duration_seconds,))

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
