import pytest
from app.schemas.led import LEDContent

from app.adapters.led.mock import MockLEDAdapter


@pytest.mark.asyncio
async def test_mock_led_display_stores_content():
    mock = MockLEDAdapter()
    content = LEDContent(name="王企业", welcome_text="王企业 先生，欢迎您")
    await mock.display(["all"], content)
    assert mock.displayed == [content]


@pytest.mark.asyncio
async def test_mock_led_show_rejected_stores_rejection():
    mock = MockLEDAdapter()
    await mock.show_rejected(["all"], reason="name_mismatch")
    assert len(mock.rejected) == 1
    rejected = mock.rejected[0]
    assert rejected.is_rejection is True
    assert rejected.welcome_text == "无权限入场"
    assert rejected.reason == "name_mismatch"


@pytest.mark.asyncio
async def test_mock_led_all_screen_id_accepted():
    """screen_ids=['all'] 是新约定的全屏标志，Mock 必须接受。"""
    mock = MockLEDAdapter()
    await mock.display(["all"], LEDContent(name="x", welcome_text="y"))
    assert len(mock.displayed) == 1
