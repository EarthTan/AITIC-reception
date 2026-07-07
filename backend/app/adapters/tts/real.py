"""真实 TTS 适配器——pyttsx3 跨平台离线 TTS + 跨平台蜂鸣。"""

from __future__ import annotations

import asyncio
import math
import os
import struct
import sys
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.base import AdapterHealth, TTSAdapter


class RealTTSAdapter(TTSAdapter):
    """TTSAdapter 真实实现。

    - 语音：pyttsx3（SAPI5 / nsss / espeak，跨平台、严格离线 §6.1）
    - 蜂鸣：跨平台实现
      · macOS: 生成 880Hz 正弦 wav + afplay
      · Windows: winsound.Beep
      · Linux: speaker-test
    """

    def __init__(self, voice_id: str | None = None, rate: int = 150) -> None:
        import pyttsx3

        self._engine = pyttsx3.init()
        if voice_id:
            self._engine.setProperty("voice", voice_id)
        self._engine.setProperty("rate", rate)

    async def enqueue_speech(self, text: str) -> None:
        # pyttsx3.runAndWait 是阻塞的，丢到线程池不卡事件循环
        await asyncio.to_thread(self._speak_blocking, text)

    def _speak_blocking(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()

    async def play_beep(self, duration_seconds: float = 1.5) -> None:
        await asyncio.to_thread(self._beep_blocking, duration_seconds)

    def _beep_blocking(self, duration_seconds: float) -> None:
        if sys.platform == "darwin":
            self._beep_macos(duration_seconds)
        elif sys.platform == "win32":
            import winsound

            winsound.Beep(880, int(duration_seconds * 1000))
        else:  # linux
            import subprocess

            subprocess.run(
                ["speaker-test", "-t", "sine", "-f", "880", "-l", "1", "-s", "1"],
                timeout=duration_seconds + 0.5,
                capture_output=True,
            )

    def _beep_macos(self, duration_seconds: float) -> None:
        """生成 880Hz 正弦 wav 到临时文件，afplay 播完删除。"""
        sample_rate = 44100
        freq = 880
        n_samples = int(sample_rate * duration_seconds)
        path = Path(tempfile.gettempdir()) / f"aitec_beep_{os.getpid()}_{id(self)}.wav"
        try:
            with wave.open(str(path), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                for i in range(n_samples):
                    sample = int(
                        32767 * 0.5 * math.sin(2 * math.pi * freq * i / sample_rate)
                    )
                    wf.writeframesraw(struct.pack("<h", sample))
            import subprocess

            subprocess.run(["afplay", str(path)], capture_output=True, check=False)
        finally:
            path.unlink(missing_ok=True)

    async def health_check(self) -> AdapterHealth:
        return AdapterHealth(status="online", last_heartbeat=datetime.now(timezone.utc))
