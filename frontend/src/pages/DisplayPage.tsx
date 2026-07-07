import { useQuery } from "@tanstack/react-query";
import { useRealtimeStore } from "../stores/realtimeStore";
import { fetchVisitsToday } from "../api/visits";

export function DisplayPage() {
  const ledContent = useRealtimeStore((s) => s.ledContent);
  const { data: today = [] } = useQuery({
    queryKey: ["visits-today"],
    queryFn: fetchVisitsToday,
    refetchInterval: 5000,
  });

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a1929",
        color: "#e3f2fd",
        padding: 32,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1 style={{ fontSize: 36, marginBottom: 24 }}>
        实时来访名单 · {new Date().toLocaleDateString("zh-CN")}
      </h1>

      <div
        style={{
          background: "#102a43",
          borderRadius: 8,
          padding: 24,
          marginBottom: 24,
          maxHeight: "50vh",
          overflowY: "auto",
        }}
      >
        {today.length === 0 && <p>暂无今日访客</p>}
        {today.map((v) => (
          <div
            key={v.id}
            style={{
              padding: "12px 0",
              borderBottom: "1px solid #1e3a5f",
              display: "flex",
              gap: 24,
              fontSize: 22,
            }}
          >
            <span style={{ width: 80 }}>{v.visit_date}</span>
            <span style={{ width: 80 }}>
              {String(v.session_time).slice(11, 16)}
            </span>
            <span style={{ flex: 1, fontWeight: 600 }}>{v.name}</span>
            <span style={{ width: 140 }}>{v.identity_type}</span>
            <span
              style={{
                width: 100,
                color: v.status === "verified" ? "#81c784" : "#ffb74d",
              }}
            >
              {v.status === "verified" ? "已入场" : v.status}
            </span>
          </div>
        ))}
      </div>

      {ledContent && !ledContent.is_rejection && (
        <div
          style={{
            background: "#1b5e20",
            padding: 32,
            borderRadius: 8,
            fontSize: 42,
            textAlign: "center",
          }}
        >
          最新：{ledContent.name} — {ledContent.welcome_text}
        </div>
      )}

      {ledContent?.is_rejection && (
        <div
          style={{
            background: "#b71c1c",
            padding: 32,
            borderRadius: 8,
            fontSize: 42,
            textAlign: "center",
          }}
        >
          无权限入场{ledContent.reason ? `（${ledContent.reason}）` : ""}
        </div>
      )}
    </div>
  );
}
