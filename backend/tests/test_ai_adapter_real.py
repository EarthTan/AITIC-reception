from __future__ import annotations

import httpx
import pytest
from app.adapters.ai.real import QwenAIAdapter

from app.adapters.base import VisitInfo


def _visit_info() -> VisitInfo:
    return VisitInfo(
        visit_id=1,
        name="张三",
        identity_type="企业领导",
        visit_date="2026-07-04",
        organization="示例集团",
    )


async def test_generate_welcome_returns_ai_text_on_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "张三先生，热烈欢迎您的到访！"}}]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = QwenAIAdapter(api_key="test-key", client=client)

    result = await adapter.generate_welcome(_visit_info())

    assert result == "张三先生，热烈欢迎您的到访！"


async def test_generate_welcome_raises_when_name_missing_from_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "欢迎光临"}}]}
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = QwenAIAdapter(api_key="test-key", client=client)

    with pytest.raises(ValueError, match="未包含访客姓名"):
        await adapter.generate_welcome(_visit_info())


async def test_generate_welcome_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid key"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = QwenAIAdapter(api_key="bad-key", client=client)

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.generate_welcome(_visit_info())


async def test_health_check_reports_error_status_on_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = QwenAIAdapter(api_key="test-key", client=client)

    health = await adapter.health_check()

    assert health.status == "error"
