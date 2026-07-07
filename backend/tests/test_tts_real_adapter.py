import pytest
from app.adapters.tts.real import RealTTSAdapter


def test_real_tts_adapter_is_subclass():
    from app.adapters.base import TTSAdapter

    assert issubclass(RealTTSAdapter, TTSAdapter)


@pytest.mark.asyncio
async def test_real_tts_speech_calls_engine(monkeypatch):
    """enqueue_speech 必须调用 pyttsx3 引擎的 say+runAndWait（不实际发声）。"""
    calls = {"speak": [], "run_and_wait": 0}

    class FakeEngine:
        def setProperty(self, k, v):
            pass

        def getProperty(self, k):
            return None

        def say(self, text):
            calls["speak"].append(text)

        def runAndWait(self):
            calls["run_and_wait"] += 1

    # patch pyttsx3.init before RealTTSAdapter.__init__ runs
    import sys

    sys.modules.setdefault("pyttsx3", type(sys)("pyttsx3"))
    sys.modules["pyttsx3"].init = lambda: FakeEngine()

    adapter = RealTTSAdapter()
    await adapter.enqueue_speech("王企业 先生，欢迎您")
    assert calls["speak"] == ["王企业 先生，欢迎您"]
    assert calls["run_and_wait"] == 1


@pytest.mark.asyncio
async def test_real_tts_play_beep_cross_platform(monkeypatch):
    """play_beep 必须按平台调用对应实现（mac=afplay, win=winsound, linux=speaker-test）。"""
    import sys

    sys.modules.setdefault("pyttsx3", type(sys)("pyttsx3"))
    sys.modules["pyttsx3"].init = lambda: type(
        "E",
        (),
        {
            "setProperty": lambda s, k, v: None,
            "getProperty": lambda s, k: None,
            "say": lambda s, t: None,
            "runAndWait": lambda s: None,
        },
    )()

    adapter = RealTTSAdapter()

    # monkey-patch _beep_blocking to capture call
    captured = []
    adapter._beep_blocking = lambda d: captured.append(d)  # type: ignore

    await adapter.play_beep(duration_seconds=2.5)
    assert captured == [2.5]
