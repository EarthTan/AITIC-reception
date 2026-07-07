// Display / 展厅大屏 — fullscreen (1920×1080), 5-col visitor table + latest
// LED content as a giant pass/fail banner.
//
// Mirrors Display.dc.html. Polls /api/visits/today every 5s; led.content
// from realtimeStore drives the banner.

import { useQuery } from "@tanstack/react-query";
import { useRealtimeStore } from "../stores/realtimeStore";
import { fetchVisitsToday } from "../api/visits";
import { VISIT_LABELS, formatChineseDate } from "../lib/design";
import type { VisitStatus } from "../api/types";

const STATUS_COLORS: Record<VisitStatus, string> = {
  pending: "#f7bb4e",
  welcome_ready: "#f7bb4e",
  card_written: "#f7bb4e",
  verified: "#4fd68d",
  rejected: "#f97a8b",
};

export function DisplayPage() {
  const ledContent = useRealtimeStore((s) => s.ledContent);
  const { data: today = [] } = useQuery({
    queryKey: ["visits-today"],
    queryFn: fetchVisitsToday,
    refetchInterval: 5000,
  });

  const showLatest = !!ledContent;
  const isRejection = ledContent?.is_rejection ?? false;
  const latestText = isRejection
    ? `无权限入场${ledContent?.reason ? `（${ledContent.reason}）` : ""}`
    : `最新：${ledContent?.name ?? ""} — ${ledContent?.welcome_text ?? ""}`;

  return (
    <div
      style={{
        width: "100vw",
        minHeight: "100vh",
        background: "radial-gradient(circle at 50% -10%, #10233a, #050b14 60%)",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif',
        display: "flex",
        flexDirection: "column",
        padding: "56px 72px",
        boxSizing: "border-box",
        color: "#f5f6f8",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 36,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "linear-gradient(135deg,#FF6A00,#FF9142)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: 16,
                height: 16,
                background: "#050b14",
                borderRadius: 4,
              }}
            />
          </div>
          <h1
            style={{
              margin: 0,
              fontSize: 38,
              fontWeight: 700,
              letterSpacing: "0.3px",
            }}
          >
            实时来访名单
          </h1>
        </div>
        <span
          style={{
            fontSize: 24,
            color: "rgba(245,246,248,0.5)",
            fontWeight: 500,
          }}
        >
          {formatChineseDate()}
        </span>
      </div>

      {/* Visitor table */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 20,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "140px 140px 1fr 220px 180px",
            padding: "20px 36px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            fontSize: 16,
            fontWeight: 600,
            color: "rgba(245,246,248,0.4)",
            letterSpacing: "0.4px",
          }}
        >
          <span>日期</span>
          <span>场次时间</span>
          <span>姓名</span>
          <span>身份</span>
          <span>状态</span>
        </div>
        <div
          style={{
            flex: 1,
            overflow: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {today.length === 0 && (
            <div
              style={{
                padding: "32px 36px",
                fontSize: 18,
                color: "rgba(245,246,248,0.4)",
              }}
            >
              暂无今日访客
            </div>
          )}
          {today.map((v) => {
            const time = String(v.session_time).slice(11, 16);
            return (
              <div
                key={v.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "140px 140px 1fr 220px 180px",
                  padding: "18px 36px",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  alignItems: "center",
                  fontSize: 22,
                }}
              >
                <span
                  style={{
                    color: "rgba(245,246,248,0.5)",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {v.visit_date.slice(5)}
                </span>
                <span
                  style={{
                    color: "rgba(245,246,248,0.5)",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {time}
                </span>
                <span style={{ fontWeight: 700 }}>{v.name}</span>
                <span style={{ color: "rgba(245,246,248,0.6)" }}>
                  {v.identity_type}
                </span>
                <span
                  style={{
                    fontWeight: 600,
                    color: STATUS_COLORS[v.status],
                  }}
                >
                  {VISIT_LABELS[v.status]}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Latest LED banner */}
      {showLatest && (
        <div
          style={{
            marginTop: 28,
            padding: "30px 40px",
            borderRadius: 18,
            background: isRejection
              ? "linear-gradient(135deg,#5a1420,#2e0a10)"
              : "linear-gradient(135deg,#1a4d2e,#0f2e1c)",
            border: isRejection
              ? "1px solid rgba(240,69,91,0.4)"
              : "1px solid rgba(47,191,113,0.4)",
            fontSize: 42,
            fontWeight: 700,
            textAlign: "center",
            color: isRejection ? "#ff8a94" : "#6fe0a0",
          }}
        >
          {latestText}
        </div>
      )}
    </div>
  );
}
