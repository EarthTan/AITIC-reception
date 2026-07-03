# backend/app/adapters/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AdapterHealth(BaseModel):
    status: Literal["online", "offline", "error"]
    detail: str | None = None
    last_heartbeat: datetime


class WriteResult(BaseModel):
    success: bool
    card_uid: str
    error_message: str | None = None


class CardReadEvent(BaseModel):
    card_uid: str
    raw_payload: dict


class VisitInfo(BaseModel):
    visit_id: int
    name: str
    identity_type: str
    visit_date: str
    organization: str | None = None


class LEDContent(BaseModel):
    name: str
    welcome_text: str


class NFCAdapter(ABC):
    @abstractmethod
    async def write_card(self, card_uid: str, payload: dict) -> WriteResult: ...

    @abstractmethod
    def read_stream(self) -> AsyncIterator[CardReadEvent]: ...

    @abstractmethod
    async def health_check(self) -> AdapterHealth: ...


class LEDAdapter(ABC):
    @abstractmethod
    async def display(self, screen_ids: list[str], content: LEDContent) -> None: ...

    @abstractmethod
    async def show_rejected(self, screen_ids: list[str]) -> None: ...

    @abstractmethod
    async def health_check(self) -> AdapterHealth: ...


class TTSAdapter(ABC):
    @abstractmethod
    async def enqueue_speech(self, text: str) -> None: ...

    @abstractmethod
    async def health_check(self) -> AdapterHealth: ...


class AIAdapter(ABC):
    @abstractmethod
    async def generate_welcome(self, visit: VisitInfo) -> str: ...

    @abstractmethod
    async def health_check(self) -> AdapterHealth: ...
