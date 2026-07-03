from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.adapters.base import AdapterHealth, AIAdapter, VisitInfo

QWEN_CHAT_ENDPOINT = (
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
)
QWEN_MODELS_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/models"


class QwenAIAdapter(AIAdapter):
    def __init__(
        self,
        api_key: str,
        model: str = "qwen-plus",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=10.0)

    async def generate_welcome(self, visit: VisitInfo) -> str:
        prompt = (
            "请为一位来访者生成一句简短的中文欢迎词。"
            f"姓名：{visit.name}；身份类型：{visit.identity_type}；"
            f"单位：{visit.organization or '未知'}。"
            f"要求：必须原样包含姓名「{visit.name}」，语气需符合其身份类型，"
            "只输出欢迎词本身，不要输出多余说明或引号。"
        )
        response = await self._client.post(
            QWEN_CHAT_ENDPOINT,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
        if visit.name not in text:
            raise ValueError(f"AI生成结果未包含访客姓名: {text!r}")
        return text

    async def health_check(self) -> AdapterHealth:
        try:
            response = await self._client.get(
                QWEN_MODELS_ENDPOINT,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            return AdapterHealth(
                status="online", last_heartbeat=datetime.now(timezone.utc)
            )
        except Exception as exc:
            return AdapterHealth(
                status="error",
                detail=str(exc),
                last_heartbeat=datetime.now(timezone.utc),
            )
