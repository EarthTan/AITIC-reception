"""Mock LED 适配器——记录所有 display / show_rejected 调用，便于测试与模拟屏。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterHealth, LEDAdapter
from app.schemas.led import LEDContent


class MockLEDAdapter(LEDAdapter):
    def __init__(self) -> None:
        self.displayed: list[LEDContent] = []
        self.rejected: list[LEDContent] = []

    async def display(self, screen_ids: list[str], content: LEDContent) -> None:
        self.displayed.append(content)

    async def show_rejected(self, screen_ids: list[str], reason: str = "") -> None:
        # §三.3 要求拒绝时所有屏显示"无权限入场"
        self.rejected.append(
            LEDContent(
                name="",
                welcome_text="无权限入场",
                is_rejection=True,
                reason=reason,
            )
        )

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(
            status="online",
            last_heartbeat=datetime.now(timezone.utc),
        )
