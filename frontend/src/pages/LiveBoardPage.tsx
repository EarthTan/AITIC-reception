// LiveBoard / 现场实时看板 — latest verify-result hero + simulate form + event log.
//
// Mirrors LiveBoard.dc.html. WS-driven hero card swaps between pass (green
// gradient) and rejection (red gradient) using the led.content envelope from
// realtimeStore.

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { simulateCardRead } from "../api/debug";
import { useRealtimeStore } from "../stores/realtimeStore";
import { StatusBadge } from "../components/StatusBadge";
import {
  formatTimeShort,
  VERIFY_LABELS,
  VERIFY_TONES,
  type Tone,
} from "../lib/design";
import type { RealtimeEvent } from "../api/types";

const FIELDS = [
  { label: "card_uid", defaultValue: "SIM-001", placeholder: "" },
  { label: "visit_id", defaultValue: "", placeholder: "必填" },
  { label: "姓名", defaultValue: "", placeholder: "选填" },
  { label: "来访日期", defaultValue: "", placeholder: "", type: "date" },
];

interface EventView {
  time: string;
  tone: Tone;
  label: string;
  payload: string;
}

function eventView(e: RealtimeEvent): EventView {
  const time = formatTimeShort(e.timestamp);
  switch (e.type) {
    case "card.verify.passed":
      return {
        time,
        tone: VERIFY_TONES.pass,
        label: VERIFY_LABELS.pass,
        payload: `{visit_id:${e.visit_id}, card_uid:"${e.card_uid}"}`,
      };
    case "card.verify.failed":
      return {
        time,
        tone: VERIFY_TONES.fail,
        label: VERIFY_LABELS.fail,
        payload: `{visit_id:${e.visit_id}, card_uid:"${e.card_uid}"}`,
      };
    case "adapter.heartbeat": {
      const tone: Tone =
        e.status === "online"
          ? "success"
          : e.status === "error"
            ? "warning"
            : "info";
      return {
        time,
        tone,
        label: "心跳",
        payload: `{adapter_name:"${e.adapter_name}", status:"${e.status}"}`,
      };
    }
    case "led.content":
      return {
        time,
        tone: "neutral",
        label: "LED内容",
        payload: `{name:"${e.name}", is_rejection:${String(e.is_rejection)}}`,
      };
  }
}

export function LiveBoardPage() {
  const events = useRealtimeStore((state) => state.events);
  const connected = useRealtimeStore((state) => state.connected);
  const ledContent = useRealtimeStore((state) => state.ledContent);
  const [cardUid, setCardUid] = useState("SIM-001");
  const [visitId, setVisitId] = useState("");
  const [name, setName] = useState("");
  const [visitDate, setVisitDate] = useState("");

  const simulateMutation = useMutation({
    mutationFn: () =>
      simulateCardRead(cardUid, {
        visit_id: visitId ? Number(visitId) : undefined,
        name,
        visit_date: visitDate,
      }),
  });

  const display = ledContent ?? null;
  const isRejection = display?.is_rejection ?? false;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1
            style={{
              margin: "0 0 4px",
              fontSize: 24,
              fontWeight: 700,
              color: "#f5f6f8",
            }}
          >
            现场实时看板
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: 13.5,
              color: "rgba(245,246,248,0.45)",
            }}
          >
            来自 /ws/realtime 的现场刷卡结果直播
          </p>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            background: connected
              ? "rgba(47,191,113,0.12)"
              : "rgba(240,69,91,0.12)",
            border: connected
              ? "1px solid rgba(47,191,113,0.28)"
              : "1px solid rgba(240,69,91,0.28)",
            borderRadius: 100,
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: connected ? "#2FBF71" : "#F0455B",
            }}
          />
          <span
            style={{
              fontSize: 12.5,
              color: connected ? "#4fd68d" : "#f97a8b",
              fontWeight: 600,
            }}
          >
            WebSocket {connected ? "已连接" : "未连接"}
          </span>
        </div>
      </div>

      {/* Hero + simulate form */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 380px",
          gap: 22,
          alignItems: "start",
        }}
      >
        <div
          style={{
            background: isRejection
              ? "linear-gradient(160deg,#2e0a10,#1a0709)"
              : "linear-gradient(160deg,#132416,#0f1e13)",
            border: isRejection
              ? "1px solid rgba(240,69,91,0.3)"
              : "1px solid rgba(47,191,113,0.3)",
            borderRadius: 16,
            padding: 48,
            minHeight: 280,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 14,
            justifyContent: "center",
          }}
        >
          {!display && (
            <>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: "rgba(245,246,248,0.06)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width={28} height={28} viewBox="0 0 20 20" fill="none">
                  <circle
                    cx="10"
                    cy="10"
                    r="7"
                    stroke="rgba(245,246,248,0.4)"
                    strokeWidth={1.5}
                  />
                  <line
                    x1="10"
                    y1="6.5"
                    x2="10"
                    y2="10.5"
                    stroke="rgba(245,246,248,0.4)"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                  />
                  <line
                    x1="10"
                    y1="10.5"
                    x2="13"
                    y2="12.5"
                    stroke="rgba(245,246,248,0.4)"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <span
                style={{
                  fontSize: 15,
                  color: "rgba(245,246,248,0.5)",
                  fontWeight: 600,
                }}
              >
                等待首次刷卡…
              </span>
            </>
          )}
          {display && !isRejection && (
            <>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: "rgba(47,191,113,0.16)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width={28} height={28} viewBox="0 0 20 20" fill="none">
                  <path
                    d="M3 10.5L7.5 15L17 4"
                    stroke="#4fd68d"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <span
                style={{
                  fontSize: 15,
                  color: "#4fd68d",
                  fontWeight: 600,
                  letterSpacing: "0.3px",
                }}
              >
                ✓ 欢迎光临
              </span>
              <span style={{ fontSize: 32, fontWeight: 700, color: "#f5f6f8" }}>
                {display.name}
              </span>
              <span
                style={{
                  fontSize: 16,
                  color: "rgba(245,246,248,0.55)",
                  textAlign: "center",
                  maxWidth: 480,
                }}
              >
                {display.welcome_text}
              </span>
            </>
          )}
          {display?.is_rejection && (
            <>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: "rgba(240,69,91,0.16)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width={28} height={28} viewBox="0 0 20 20" fill="none">
                  <path
                    d="M5 5L15 15M15 5L5 15"
                    stroke="#f97a8b"
                    strokeWidth={2}
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <span style={{ fontSize: 15, color: "#f97a8b", fontWeight: 600 }}>
                ✗ 无权限入场
              </span>
              {display.reason && (
                <span style={{ fontSize: 16, color: "rgba(245,246,248,0.55)" }}>
                  原因：{display.reason}
                </span>
              )}
            </>
          )}
        </div>

        {/* Simulate form */}
        <div
          style={{
            background: "#131a2c",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14,
            padding: 22,
            display: "flex",
            flexDirection: "column",
            gap: 14,
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: 14,
              fontWeight: 700,
              color: "#f5f6f8",
            }}
          >
            模拟刷卡（调试用）
          </h2>
          {FIELDS.map((f) => {
            const isVisit = f.label === "visit_id";
            const value =
              f.label === "card_uid"
                ? cardUid
                : f.label === "visit_id"
                  ? visitId
                  : f.label === "姓名"
                    ? name
                    : visitDate;
            const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
              if (f.label === "card_uid") setCardUid(e.target.value);
              else if (f.label === "visit_id") setVisitId(e.target.value);
              else if (f.label === "姓名") setName(e.target.value);
              else setVisitDate(e.target.value);
            };
            return (
              <label
                key={f.label}
                style={{ display: "flex", flexDirection: "column", gap: 5 }}
              >
                <span
                  style={{
                    fontSize: 12,
                    color: "rgba(245,246,248,0.45)",
                    fontWeight: 500,
                  }}
                >
                  {f.label}
                </span>
                <input
                  type={f.type ?? "text"}
                  value={value}
                  onChange={onChange}
                  placeholder={f.placeholder}
                  style={{
                    padding: "9px 12px",
                    borderRadius: 8,
                    border: "1px solid rgba(255,255,255,0.12)",
                    background: "#0d1220",
                    color: "#f5f6f8",
                    fontSize: 13,
                    outline: "none",
                  }}
                />
                {isVisit && (
                  <span
                    style={{ fontSize: 11, color: "rgba(245,246,248,0.32)" }}
                  >
                    从写卡记录或访客列表取 id
                  </span>
                )}
              </label>
            );
          })}
          <button
            onClick={() => simulateMutation.mutate()}
            style={{
              marginTop: 4,
              padding: 10,
              borderRadius: 9,
              border: "none",
              background: "linear-gradient(135deg,#FF6A00,#FF8A2E)",
              color: "#fff",
              fontSize: 13.5,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            模拟刷卡
          </button>
        </div>
      </div>

      {/* Recent events */}
      <div
        style={{
          background: "#131a2c",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 14,
          padding: "20px 24px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <h2
          style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "#f5f6f8" }}
        >
          最近事件
        </h2>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            maxHeight: 280,
            overflow: "auto",
          }}
        >
          {events.length === 0 && (
            <span style={{ fontSize: 13, color: "rgba(245,246,248,0.4)" }}>
              暂无事件
            </span>
          )}
          {events.map((event, idx) => {
            const v = eventView(event);
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "9px 14px",
                  background: "#0d1220",
                  borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <span
                  style={{
                    fontSize: 11.5,
                    color: "rgba(245,246,248,0.35)",
                    fontVariantNumeric: "tabular-nums",
                    width: 70,
                    flex: "none",
                  }}
                >
                  {v.time}
                </span>
                <StatusBadge label={v.label} tone={v.tone} />
                <span
                  style={{
                    fontSize: 12,
                    color: "rgba(245,246,248,0.5)",
                    fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {v.payload}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
