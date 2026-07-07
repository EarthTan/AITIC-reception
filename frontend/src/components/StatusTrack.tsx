// 4-step visit-status track. The "rejected" branch replaces the "card_written"
// slot (red dot + white cross, connector red up to that point).
// Mirrors StatusTrack.dc.html.

import type { CSSProperties, ReactNode } from "react";

interface Props {
  status: "pending" | "welcome_ready" | "card_written" | "verified" | "rejected";
}

const ORDER = ["pending", "welcome_ready", "card_written", "verified"] as const;

const LABELS: Record<string, string> = {
  pending: "待登记",
  welcome_ready: "待写卡",
  card_written: "已写卡",
  verified: "已入场",
  rejected: "已拒绝",
};

const GREEN = "#2fbf71";
const ORANGE = "#ff6a00";
const RED = "#f0455b";
const GRAY_DOT = "rgba(245,246,248,0.14)";
const GRAY_LINE = "rgba(245,246,248,0.14)";

const TRACK_STYLE: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 0,
  minWidth: 200,
};
const CELL_STYLE: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: 4,
  width: 44,
};

function Indicator({ state }: { state: "done" | "current" | "future" | "rejected" }): ReactNode {
  let bg = GRAY_DOT;
  let border = "1px solid rgba(245,246,248,0.18)";
  let boxShadow: string | undefined;
  let inner: ReactNode = null;
  if (state === "done") {
    bg = GREEN;
    border = "none";
    inner = (
      <svg width={9} height={7} viewBox="0 0 9 7" fill="none">
        <path d="M1 3.5L3.2 5.7L8 1" stroke="white" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  } else if (state === "current") {
    bg = ORANGE;
    border = "none";
    boxShadow = "0 0 0 3px rgba(255,106,0,0.18)";
  } else if (state === "rejected") {
    bg = RED;
    border = "none";
    inner = (
      <svg width={8} height={8} viewBox="0 0 8 8" fill="none">
        <path d="M1 1L7 7M7 1L1 7" stroke="white" strokeWidth={1.6} strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <div
      style={{
        width: 18,
        height: 18,
        borderRadius: "50%",
        background: bg,
        border,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none",
        boxShadow,
      }}
    >
      {inner}
    </div>
  );
}

export function StatusTrack({ status }: Props) {
  const isRejected = status === "rejected";
  const currentIdx = isRejected ? ORDER.indexOf("card_written") : ORDER.indexOf(status);

  return (
    <div style={TRACK_STYLE}>
      {ORDER.map((key, i) => {
        const isLast = i === ORDER.length - 1;
        let state: "done" | "current" | "future" | "rejected";
        if (isRejected) {
          state =
            i < currentIdx ? "done" : i === currentIdx ? "rejected" : "future";
        } else {
          state = i < currentIdx ? "done" : i === currentIdx ? "current" : "future";
        }
        const showLabel = isRejected && i === currentIdx ? "已拒绝" : LABELS[key];
        const labelColor =
          state === "future" ? "rgba(245,246,248,0.32)" : "rgba(245,246,248,0.68)";
        const labelWeight = state === "current" || state === "rejected" ? 600 : 400;
        const connColor =
          i < currentIdx ? GREEN : isRejected && i === currentIdx ? RED : GRAY_LINE;

        return (
          <div style={{ display: "flex", alignItems: "center" }} key={key}>
            <div style={CELL_STYLE}>
              <Indicator state={state} />
              <span
                style={{
                  fontSize: 10,
                  color: labelColor,
                  fontWeight: labelWeight,
                  whiteSpace: "nowrap",
                }}
              >
                {showLabel}
              </span>
            </div>
            {!isLast && (
              <div
                style={{
                  width: 20,
                  height: 2,
                  background: connColor,
                  marginBottom: 16,
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
