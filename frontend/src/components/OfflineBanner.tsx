// Red banner that drops in below the top of the page when at least one adapter
// is offline. Rendered above Sidebar/main in the NavLayout.
//
// Mirrors OfflineBanner.dc.html.

import { useRealtimeStore } from "../stores/realtimeStore";

const ADAPTER_LABELS: Record<string, string> = {
  nfc: "NFC",
  led: "LED",
  tts: "TTS",
  ai: "AI",
};

export function OfflineBanner() {
  const statuses = useRealtimeStore((s) => s.adapterStatuses);
  const offline = Object.entries(statuses).filter(
    ([_, v]) => v.status !== "online",
  );

  if (offline.length === 0) return null;

  // Sort by adapter name so the banner is stable across renders.
  const names = offline
    .map(([name]) => ADAPTER_LABELS[name] ?? name.toUpperCase())
    .sort()
    .join(" / ");

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 24px",
        background: "rgba(240,69,91,0.12)",
        borderBottom: "1px solid rgba(240,69,91,0.28)",
        color: "#f97a8b",
        fontSize: 13,
        fontWeight: 500,
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif',
      }}
    >
      <svg width={15} height={15} viewBox="0 0 16 16" fill="none" style={{ flex: "none" }}>
        <path d="M8 1.5L15 14H1L8 1.5Z" stroke="#f97a8b" strokeWidth={1.3} strokeLinejoin="round" />
        <line x1="8" y1="6.5" x2="8" y2="9.5" stroke="#f97a8b" strokeWidth={1.3} strokeLinecap="round" />
        <circle cx="8" cy="11.5" r="0.8" fill="#f97a8b" />
      </svg>
      <span>
        硬件离线：{names} — 管理功能仍可使用，但现场刷卡链路可能异常
      </span>
    </div>
  );
}
