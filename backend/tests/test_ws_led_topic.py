"""Tests for the WS realtime topic registry — §三.3 LED 屏内容变化要实时推送给前端模拟屏。"""

from app.api.ws import REALTIME_TOPICS


def test_led_content_in_realtime_topics():
    """§三.3 LED 屏内容变化要实时推送给前端模拟屏。"""
    assert "led.content" in REALTIME_TOPICS
