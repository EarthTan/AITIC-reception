# backend/tests/test_adapters_base.py
from datetime import datetime, timezone

import pytest
from app.adapters.base import (
    AdapterHealth,
    AIAdapter,
    CardReadEvent,
    LEDAdapter,
    LEDContent,
    NFCAdapter,
    TTSAdapter,
    VisitInfo,
    WriteResult,
)


def test_adapter_health_model_holds_expected_fields():
    health = AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
    assert health.status == "online"
    assert health.detail is None


def test_write_result_and_card_read_event_models():
    result = WriteResult(success=True, card_uid="ABC123")
    assert result.error_message is None
    event = CardReadEvent(card_uid="ABC123", raw_payload={"name": "张三"})
    assert event.raw_payload["name"] == "张三"


def test_visit_info_and_led_content_models():
    visit_info = VisitInfo(
        visit_id=1, name="张三", identity_type="企业领导", visit_date="2026-07-06"
    )
    assert visit_info.organization is None
    content = LEDContent(name="张三", welcome_text="欢迎您")
    assert content.welcome_text == "欢迎您"


@pytest.mark.parametrize("adapter_cls", [NFCAdapter, LEDAdapter, TTSAdapter, AIAdapter])
def test_abstract_adapters_cannot_be_instantiated_directly(adapter_cls):
    with pytest.raises(TypeError):
        adapter_cls()
