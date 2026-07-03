from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, CardReadEvent, NFCAdapter, WriteResult


class MockNFCAdapter(NFCAdapter):
    def __init__(self) -> None:
        self._read_queue: asyncio.Queue[CardReadEvent] = asyncio.Queue()
        self._written_payloads: dict[str, dict] = {}

    async def write_card(self, card_uid: str, payload: dict) -> WriteResult:
        self._written_payloads[card_uid] = payload
        return WriteResult(success=True, card_uid=card_uid)

    def get_written_payload(self, card_uid: str) -> dict:
        return self._written_payloads[card_uid]

    async def simulate_card_read(self, card_uid: str, raw_payload: dict) -> None:
        await self._read_queue.put(
            CardReadEvent(card_uid=card_uid, raw_payload=raw_payload)
        )

    async def read_stream(self) -> AsyncIterator[CardReadEvent]:
        while True:
            event = await self._read_queue.get()
            yield event

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
