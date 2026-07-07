// MockLED / 模拟 LED 屏 — pure black 1920x1080 wall, 96px centred text.
//
// Mirrors MockLED.dc.html. Three modes:
//   empty (waiting), passed (white text), rejected (red text).
// Page-load attempts fullscreen; click anywhere to retry if the auto-prompt
// was denied.

import { useEffect, useRef } from "react";
import { useRealtimeStore } from "../stores/realtimeStore";

export function MockLEDPane() {
  const ledContent = useRealtimeStore((s) => s.ledContent);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }, []);

  const isRejection = ledContent?.is_rejection ?? false;
  const hasContent = !!ledContent;
  const mainText = !hasContent
    ? "等待刷卡…"
    : isRejection
      ? "无权限入场"
      : ledContent
        ? `${ledContent.name}   ${ledContent.welcome_text}`
        : "等待刷卡…";
  const subText =
    isRejection && ledContent?.reason ? `（${ledContent.reason}）` : "";

  return (
    <div
      ref={ref}
      onClick={() => ref.current?.requestFullscreen?.()}
      style={{
        width: "100vw",
        height: "100vh",
        background: "#000",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif',
        gap: 20,
        cursor: "pointer",
        margin: 0,
      }}
    >
      <div
        style={{
          fontSize: 96,
          fontWeight: 700,
          letterSpacing: "1px",
          textAlign: "center",
          padding: "0 80px",
          color: !hasContent
            ? "rgba(255,255,255,0.35)"
            : isRejection
              ? "#ff1744"
              : "#fff",
        }}
      >
        {mainText}
      </div>
      {subText && (
        <div
          style={{
            fontSize: 48,
            fontWeight: 500,
            color: "#ff8a80",
          }}
        >
          {subText}
        </div>
      )}
    </div>
  );
}
