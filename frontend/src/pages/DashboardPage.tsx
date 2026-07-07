// Dashboard / 仪表盘 — today-arrivals hero + adapter status grid.
//
// Mirrors Dashboard.dc.html. Adapter rows are driven by the existing
// fetchAdapterStatus snapshot, overlaid with live websocket heartbeats from
// realtimeStore — same merge logic as before, just visualised.

import type { CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAdapterStatus } from "../api/adapters";
import { queryKeys } from "../api/queryKeys";
import { fetchVisitsToday } from "../api/visits";
import { useRealtimeStore } from "../stores/realtimeStore";
import { StatusBadge } from "../components/StatusBadge";
import {
  ADAPTER_DISPLAY,
  ADAPTER_DOTS,
  ADAPTER_LABELS,
  ADAPTER_TONES,
  formatChineseDate,
  formatTimeShort,
} from "../lib/design";

const PAGE_H1: CSSProperties = {
  margin: "0 0 4px",
  fontSize: 24,
  fontWeight: 700,
  color: "#f5f6f8",
  letterSpacing: "0.2px",
};
const PAGE_SUB: CSSProperties = {
  margin: 0,
  fontSize: 13.5,
  color: "rgba(245,246,248,0.45)",
};
const HERO_CARD: CSSProperties = {
  background: "linear-gradient(160deg,#171216,#1a1310)",
  border: "1px solid rgba(255,106,0,0.22)",
  borderRadius: 14,
  padding: 28,
  display: "flex",
  flexDirection: "column",
  gap: 10,
  justifyContent: "center",
};
const ADAPTER_CARD: CSSProperties = {
  background: "#131a2c",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 14,
  padding: "18px 18px 16px",
  display: "flex",
  flexDirection: "column",
  gap: 12,
};
const NOTE_CARD: CSSProperties = {
  background: "#131a2c",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 14,
  padding: "22px 26px",
};

type Status = "online" | "offline" | "error";
interface Merged {
  status: Status;
  detail: string | null;
  lastHeartbeat: string | null;
}

export function DashboardPage() {
  const todayQuery = useQuery({
    queryKey: queryKeys.visitsToday(),
    queryFn: fetchVisitsToday,
  });
  const statusQuery = useQuery({
    queryKey: queryKeys.adapterStatus(),
    queryFn: fetchAdapterStatus,
  });
  const realtimeStatuses = useRealtimeStore((state) => state.adapterStatuses);

  // Merge REST snapshot with realtime heartbeat — ws-wins for status, newest
  // heartbeat timestamp wins.
  const merged = new Map<string, Merged>();
  for (const row of statusQuery.data ?? []) {
    merged.set(row.adapter_name, {
      status: row.status,
      detail: row.detail,
      lastHeartbeat: row.last_heartbeat,
    });
  }
  for (const [name, live] of Object.entries(realtimeStatuses)) {
    const status: Status =
      live.status === "online" ||
      live.status === "offline" ||
      live.status === "error"
        ? live.status
        : "offline";
    const existing = merged.get(name);
    merged.set(name, {
      status,
      detail: live.detail ?? existing?.detail ?? null,
      lastHeartbeat: live.lastHeartbeat ?? existing?.lastHeartbeat ?? null,
    });
  }

  const todayCount = todayQuery.data?.length ?? 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <div>
        <h1 style={PAGE_H1}>仪表盘</h1>
        <p style={PAGE_SUB}>系统运行概览 · {formatChineseDate()}</p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "340px 1fr",
          gap: 20,
          alignItems: "stretch",
        }}
      >
        {/* Hero */}
        <div style={HERO_CARD}>
          <span
            style={{
              fontSize: 13,
              color: "rgba(245,246,248,0.5)",
              fontWeight: 500,
            }}
          >
            今日来访人数
          </span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span
              style={{
                fontSize: 52,
                fontWeight: 700,
                color: "#FF9142",
                fontVariantNumeric: "tabular-nums",
                lineHeight: 1,
              }}
            >
              {todayCount}
            </span>
            <span style={{ fontSize: 14, color: "rgba(245,246,248,0.4)" }}>
              人
            </span>
          </div>
          <span style={{ fontSize: 12, color: "rgba(245,246,248,0.35)" }}>
            数据来源：/api/visits/today
          </span>
        </div>

        {/* Adapters */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4,1fr)",
            gap: 14,
          }}
        >
          {ADAPTER_DISPLAY.map((adapter) => {
            const entry = merged.get(adapter.key);
            const status: Status = entry?.status ?? "offline";
            const dotColor = ADAPTER_DOTS[status];
            return (
              <div style={ADAPTER_CARD} key={adapter.key}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <span
                    style={{
                      fontSize: 13.5,
                      fontWeight: 600,
                      color: "#f5f6f8",
                    }}
                  >
                    {adapter.name}
                  </span>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: dotColor,
                      boxShadow: `0 0 0 3px ${dotColor}22`,
                    }}
                  />
                </div>
                <div>
                  <StatusBadge
                    label={ADAPTER_LABELS[status]}
                    tone={ADAPTER_TONES[status]}
                  />
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 2,
                    marginTop: "auto",
                  }}
                >
                  <span
                    style={{ fontSize: 11, color: "rgba(245,246,248,0.35)" }}
                  >
                    最近心跳
                  </span>
                  <span
                    style={{
                      fontSize: 12,
                      color: "rgba(245,246,248,0.55)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {entry?.lastHeartbeat
                      ? formatTimeShort(entry.lastHeartbeat)
                      : "—"}
                  </span>
                </div>
                {entry?.detail && (
                  <span
                    style={{
                      fontSize: 11.5,
                      color: "rgba(245,246,248,0.4)",
                      borderTop: "1px solid rgba(255,255,255,0.06)",
                      paddingTop: 8,
                    }}
                  >
                    {entry.detail}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer note */}
      <div style={NOTE_CARD}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 4,
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: 15,
              fontWeight: 600,
              color: "#f5f6f8",
            }}
          >
            适配器状态
          </h2>
          <span style={{ fontSize: 11.5, color: "rgba(245,246,248,0.35)" }}>
            实时心跳 · WebSocket /ws/realtime
          </span>
        </div>
        <p
          style={{
            margin: "6px 0 0",
            fontSize: 12.5,
            color: "rgba(245,246,248,0.4)",
            lineHeight: 1.6,
          }}
        >
          NFC / LED / TTS / AI 四类硬件适配器状态由 REST
          快照与实时心跳共同驱动，任一离线将在页面顶部提示。
        </p>
      </div>
    </div>
  );
}
