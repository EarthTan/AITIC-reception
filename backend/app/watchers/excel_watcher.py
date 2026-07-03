# backend/app/watchers/excel_watcher.py
from __future__ import annotations

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.core.event_bus import EventBus


class _NewExcelHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, event_bus: EventBus) -> None:
        self._loop = loop
        self._event_bus = event_bus

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory or not event.src_path.lower().endswith((".xlsx", ".xls")):
            return
        asyncio.run_coroutine_threadsafe(
            self._event_bus.publish("excel.detected", {"file_path": event.src_path}),
            self._loop,
        )


class ExcelWatcher:
    def __init__(self, watch_dir: str, event_bus: EventBus) -> None:
        self._watch_dir = watch_dir
        self._event_bus = event_bus
        self._observer: Observer | None = None

    def start(self) -> None:
        Path(self._watch_dir).mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()
        handler = _NewExcelHandler(loop, self._event_bus)
        self._observer = Observer()
        self._observer.schedule(handler, self._watch_dir, recursive=False)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
