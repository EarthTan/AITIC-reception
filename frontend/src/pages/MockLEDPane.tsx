import { useEffect, useRef } from "react";
import { useRealtimeStore } from "../stores/realtimeStore";

export function MockLEDPane() {
  const ledContent = useRealtimeStore(s => s.ledContent);
  const ref = useRef<HTMLDivElement>(null);

  // 进入页面自动全屏
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => {/* 用户可能拒绝 */});
    }
  }, []);

  const isRejection = ledContent?.is_rejection ?? false;
  const mainText = isRejection
    ? "无权限入场"
    : (ledContent?.name ? `${ledContent.name}  ${ledContent.welcome_text}` : "等待刷卡…");
  const subText = isRejection && ledContent?.reason ? `（${ledContent.reason}）` : "";

  return (
    <div
      ref={ref}
      style={{
        position: "fixed",
        inset: 0,
        background: "#000",
        color: isRejection ? "#ff1744" : "#fff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: '"PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
        cursor: "pointer",
      }}
      onClick={() => ref.current?.requestFullscreen?.()}
    >
      <div style={{ fontSize: 96, fontWeight: 700, textAlign: "center", padding: 32 }}>
        {mainText}
      </div>
      {subText && (
        <div style={{ fontSize: 48, marginTop: 24, color: "#ff8a80" }}>{subText}</div>
      )}
    </div>
  );
}
