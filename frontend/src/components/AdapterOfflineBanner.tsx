import { useRealtimeStore } from "../stores/realtimeStore";

export function AdapterOfflineBanner() {
  const statuses = useRealtimeStore((s) => s.adapterStatuses);
  const offline = Object.entries(statuses).filter(
    ([_, v]) => v.status !== "online",
  );

  if (offline.length === 0) return null;

  return (
    <div
      role="alert"
      style={{
        background: "#d32f2f",
        color: "#fff",
        padding: "10px 16px",
        fontWeight: 600,
        textAlign: "center",
        fontSize: 14,
      }}
    >
      ⚠️ 硬件离线：{offline.map(([n]) => n.toUpperCase()).join(" / ")}
      {" — "}管理功能仍可使用，但现场刷卡链路可能异常
    </div>
  );
}
