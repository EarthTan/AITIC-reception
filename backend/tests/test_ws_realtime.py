# backend/tests/test_ws_realtime.py
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app


def test_ws_realtime_forwards_card_verify_passed_event(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    app = build_app(settings)
    with TestClient(app) as client:
        with client.websocket_connect("/ws/realtime") as websocket:
            # Publish from the test's thread using asyncio.run since
            # `app.state.event_bus.publish` is async. The WS forwarder is
            # running in the lifespan loop, but `asyncio.Queue` is not
            # bound to a specific event loop — its `_loop` stays None —
            # so cross-loop publish/get works.
            asyncio.run(
                app.state.event_bus.publish(
                    "card.verify.passed", {"visit_id": 1, "card_uid": "ABC"}
                )
            )
            message = websocket.receive_json()

            assert message["type"] == "card.verify.passed"
            assert message["payload"] == {"visit_id": 1, "card_uid": "ABC"}
            assert "timestamp" in message
