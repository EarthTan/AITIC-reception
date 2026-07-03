# backend/app/api/debug.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.adapters.nfc.mock import MockNFCAdapter
from app.api.deps import get_adapters

router = APIRouter(prefix="/api/debug", tags=["debug"])


class SimulateCardReadRequest(BaseModel):
    card_uid: str
    raw_payload: dict


@router.post("/simulate-card-read")
async def simulate_card_read(
    body: SimulateCardReadRequest, adapters: dict = Depends(get_adapters)
) -> dict:
    nfc_adapter = adapters["nfc"]
    if not isinstance(nfc_adapter, MockNFCAdapter):
        raise HTTPException(
            status_code=400, detail="仅Mock模式下可用，当前已接入真实NFC硬件"
        )
    await nfc_adapter.simulate_card_read(body.card_uid, body.raw_payload)
    return {"status": "queued"}
