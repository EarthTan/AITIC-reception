# backend/app/api/deps.py
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.event_bus import EventBus


def get_db(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


def get_services(request: Request) -> dict:
    return request.app.state.services


def get_adapters(request: Request) -> dict:
    return request.app.state.adapters
