# backend/app/core/event_bus.py
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Iterable


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, topics: str | Iterable[str]) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        for topic in self._normalize_topics(topics):
            self._queues[topic].append(queue)
        return queue

    async def publish(self, topic: str, payload: dict) -> None:
        for queue in self._queues.get(topic, []):
            await queue.put(payload)

    @staticmethod
    def _normalize_topics(topics: str | Iterable[str]) -> list[str]:
        if isinstance(topics, str):
            return [topics]
        return list(topics)
