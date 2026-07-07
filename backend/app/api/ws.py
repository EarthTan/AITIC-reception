# backend/app/api/ws.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.event_bus import EventBus

router = APIRouter()

REALTIME_TOPICS = [
    "card.verify.passed",
    "card.verify.failed",
    "adapter.heartbeat",
    "led.content",
]


@router.websocket("/ws/realtime")
async def realtime(websocket: WebSocket) -> None:
    await websocket.accept()
    event_bus: EventBus = websocket.app.state.event_bus
    # Subscribe per-topic so we can put the topic name in the WS `type` field.
    # EventBus.subscribe(topics) shares ONE queue across all topics, losing
    # the topic name, so we open a queue per topic.
    per_topic_queues = {topic: event_bus.subscribe(topic) for topic in REALTIME_TOPICS}

    async def _forward_topic(topic: str, topic_queue: asyncio.Queue) -> None:
        while True:
            payload = await topic_queue.get()
            await websocket.send_json(
                {
                    "type": topic,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": payload,
                }
            )

    tasks = [
        asyncio.create_task(_forward_topic(topic, topic_queue))
        for topic, topic_queue in per_topic_queues.items()
    ]
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
