# backend/app/services/ai_writeup_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.base import AIAdapter, VisitInfo
from app.core.event_bus import EventBus
from app.models.visit import Visit, VisitStatus, WelcomeSource
from app.models.welcome_template import TemplateIdentityType, WelcomeTemplate


class AIWriteupWorker:
    def __init__(
        self, session_factory, event_bus: EventBus, ai_adapter: AIAdapter
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._ai_adapter = ai_adapter

    async def handle_welcome_requested(self, payload: dict) -> None:
        visit_id = payload["visit_id"]
        with self._session_factory() as session:
            visit = session.get(Visit, visit_id)
            if visit is None:
                return
            visit_info = VisitInfo(
                visit_id=visit.id,
                name=visit.name,
                identity_type=visit.identity_type.value,
                visit_date=visit.visit_date.isoformat(),
                organization=visit.organization,
            )
            try:
                welcome_text = await self._ai_adapter.generate_welcome(visit_info)
                source = WelcomeSource.AI
                log_status = "success"
                log_detail = f"visit_id={visit_id} AI生成成功"
            except Exception as exc:
                welcome_text = self._fallback_text(session, visit)
                source = WelcomeSource.FALLBACK_TEMPLATE
                log_status = "warning"
                log_detail = f"visit_id={visit_id} AI生成失败，已降级为模板: {exc}"

            visit.welcome_text = welcome_text
            visit.welcome_source = source
            visit.status = VisitStatus.WELCOME_READY
            session.commit()

        await self._event_bus.publish(
            "welcome.generated",
            {
                "visit_id": visit_id,
                "welcome_text": welcome_text,
                "source": source.value,
            },
        )
        await self._event_bus.publish(
            "work_log.append",
            {
                "module": "ai_writeup",
                "action": "generate_welcome",
                "status": log_status,
                "detail": log_detail,
            },
        )

    @staticmethod
    def _fallback_text(session: Session, visit: Visit) -> str:
        template = session.execute(
            select(WelcomeTemplate).where(
                WelcomeTemplate.identity_type
                == TemplateIdentityType(visit.identity_type.value)
            )
        ).scalar_one_or_none()
        if template is None:
            template = session.execute(
                select(WelcomeTemplate).where(
                    WelcomeTemplate.identity_type == TemplateIdentityType.DEFAULT
                )
            ).scalar_one_or_none()
        text = template.template_text if template else "{姓名}，欢迎您"
        return text.replace("{姓名}", visit.name)
