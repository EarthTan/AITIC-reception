"""LED 屏内容数据类——被 LEDAdapter 实现和 OnsiteWelcomeService 共享。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LEDContent:
    """一帧 LED 屏显示内容。is_rejection=True 时 welcome_text 通常是 '无权限入场'。"""

    name: str
    welcome_text: str
    is_rejection: bool = False
    reason: str = ""
