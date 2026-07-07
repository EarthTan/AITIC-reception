"""OnsiteWelcomeService——订阅 card.verify.passed/failed 驱动 LED + TTS + 蜂鸣。

§三.3 现场欢迎模块的服务实现。VerifyService 只判断通过/失败并改 DB 状态，
本服务只翻译事件为硬件副作用，通过 EventBus 自然解耦（不 import VerifyService）。
"""

from __future__ import annotations

import asyncio
import logging

from app.adapters.base import LEDAdapter, TTSAdapter
from app.core.event_bus import EventBus
from app.models.visit import Visit

logger = logging.getLogger(__name__)


class OnsiteWelcomeService:
    def __init__(
        self,
        led_adapter: LEDAdapter,
        tts_adapter: TTSAdapter,
        event_bus: EventBus,
        session_factory,
    ) -> None:
        self._led = led_adapter
        self._tts = tts_adapter
        self._bus = event_bus
        self._session_factory = session_factory

    async def handle_card_verify_passed(self, payload: dict) -> None:
        visit_id = payload["visit_id"]
        content = self._load_content(visit_id)
        if content is None:
            logger.warning("card.verify.passed 但找不到 visit %s", visit_id)
            return

        # 三个动作可并行：LED 显示、TTS 朗读、work_log
        await asyncio.gather(
            self._led.display(["all"], content),
            self._tts.enqueue_speech(content.welcome_text),
            self._publish_worklog(
                "led",
                "display",
                "success",
                f"visit_id={visit_id} name={content.name}",
            ),
            self._publish_worklog(
                "tts",
                "speak",
                "success",
                f"visit_id={visit_id} text={content.welcome_text!r}",
            ),
        )

    async def handle_card_verify_failed(self, payload: dict) -> None:
        reason = payload.get("fail_reason", "")
        card_uid = payload.get("card_uid", "")

        await asyncio.gather(
            self._led.show_rejected(["all"], reason=reason),
            self._tts.play_beep(duration_seconds=1.5),
            self._publish_worklog(
                "led",
                "show_rejected",
                "success",
                f"card_uid={card_uid} reason={reason}",
            ),
            self._publish_worklog("tts", "beep", "success", f"card_uid={card_uid}"),
        )

    # --- helpers ---

    def _load_content(self, visit_id: int):
        """从 DB 取访客姓名 + 欢迎词。如果 visit 不存在返回 None。"""
        from app.schemas.led import LEDContent

        with self._session_factory() as session:
            v = session.get(Visit, visit_id)
            if v is None:
                return None
            return LEDContent(
                name=v.name,
                welcome_text=v.welcome_text or "",
                is_rejection=False,
                reason="",
            )

    async def _publish_worklog(
        self, module: str, action: str, status: str, detail: str
    ) -> None:
        await self._bus.publish(
            "work_log.append",
            {
                "module": module,
                "action": action,
                "status": status,
                "detail": detail,
            },
        )
