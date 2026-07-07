import pytest

from app.adapters.base import TTSAdapter


def test_tts_adapter_has_play_beep_abstract_method():
    """§三.3 要求蜂鸣通道复用同一音响，TTSAdapter 必须定义 play_beep。"""
    assert hasattr(TTSAdapter, "play_beep")
    assert getattr(TTSAdapter.play_beep, "__isabstractmethod__", False) is True


def test_concrete_tts_must_implement_play_beep():
    """不实现 play_beep 的子类无法实例化。"""

    class IncompleteTTS(TTSAdapter):
        async def enqueue_speech(self, text: str) -> None:
            pass

        # 故意不实现 play_beep

    with pytest.raises(TypeError):
        IncompleteTTS()


@pytest.mark.asyncio
async def test_mock_tts_play_beep_records_call():
    """Mock 实现必须能被调用并记录参数。"""
    from app.adapters.tts.mock import MockTTSAdapter

    mock = MockTTSAdapter()
    await mock.play_beep(duration_seconds=2.0)
    assert mock.beeps == [(2.0,)]
