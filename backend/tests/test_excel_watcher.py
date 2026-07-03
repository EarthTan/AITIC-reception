# backend/tests/test_excel_watcher.py
import asyncio

import pandas as pd
from app.core.event_bus import EventBus
from app.watchers.excel_watcher import ExcelWatcher


async def test_new_excel_file_triggers_excel_detected_event(tmp_path):
    event_bus = EventBus()
    queue = event_bus.subscribe("excel.detected")
    watcher = ExcelWatcher(str(tmp_path), event_bus)
    watcher.start()
    try:
        target = tmp_path / "visitors.xlsx"
        pd.DataFrame([{"a": 1}]).to_excel(target, index=False)

        payload = await asyncio.wait_for(queue.get(), timeout=5)
        assert payload["file_path"] == str(target)
    finally:
        watcher.stop()


async def test_non_excel_file_does_not_trigger_event(tmp_path):
    event_bus = EventBus()
    queue = event_bus.subscribe("excel.detected")
    watcher = ExcelWatcher(str(tmp_path), event_bus)
    watcher.start()
    try:
        (tmp_path / "notes.txt").write_text("hello")
        try:
            await asyncio.wait_for(queue.get(), timeout=1)
            raised = False
        except asyncio.TimeoutError:
            raised = True
        assert raised
    finally:
        watcher.stop()
