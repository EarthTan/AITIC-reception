# backend/tests/test_adapters_mock.py
import pytest
from app.adapters.ai.mock import MockAIAdapter
from app.adapters.base import LEDContent, VisitInfo
from app.adapters.led.mock import MockLEDAdapter
from app.adapters.nfc.mock import MockNFCAdapter
from app.adapters.tts.mock import MockTTSAdapter


async def test_mock_nfc_write_then_read_back_round_trip():
    adapter = MockNFCAdapter()
    result = await adapter.write_card("UID-1", {"name": "张三"})
    assert result.success is True
    assert adapter.get_written_payload("UID-1") == {"name": "张三"}

    await adapter.simulate_card_read("UID-1", {"name": "张三"})
    stream = adapter.read_stream()
    event = await stream.__anext__()
    assert event.card_uid == "UID-1"
    assert event.raw_payload == {"name": "张三"}


async def test_mock_nfc_health_check_reports_online():
    adapter = MockNFCAdapter()
    health = await adapter.health_check()
    assert health.status == "online"


async def test_mock_led_records_display_and_rejected_calls():
    adapter = MockLEDAdapter()
    await adapter.display(["screen-1"], LEDContent(name="张三", welcome_text="欢迎您"))
    await adapter.show_rejected(["screen-1"])
    assert len(adapter.displayed) == 1
    assert adapter.displayed[0][0] == ["screen-1"]
    assert adapter.rejected == [["screen-1"]]


async def test_mock_tts_records_spoken_text():
    adapter = MockTTSAdapter()
    await adapter.enqueue_speech("欢迎您")
    assert adapter.spoken == ["欢迎您"]


async def test_mock_ai_generates_welcome_text_by_default():
    adapter = MockAIAdapter()
    visit = VisitInfo(
        visit_id=1, name="张三", identity_type="企业领导", visit_date="2026-07-06"
    )
    text = await adapter.generate_welcome(visit)
    assert "张三" in text
    assert adapter.requests == [visit]


async def test_mock_ai_raises_when_configured_to_fail():
    adapter = MockAIAdapter(raise_error=True)
    visit = VisitInfo(
        visit_id=1, name="张三", identity_type="企业领导", visit_date="2026-07-06"
    )
    with pytest.raises(RuntimeError):
        await adapter.generate_welcome(visit)
