// Summary / 月度汇总总表 — month picker + per-session grouped cards.
//
// Mirrors Summary.dc.html. Backend VisitSummaryRow groups visits by
// (visit_date, session_time).

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchVisitSummary, visitSummaryExportUrl } from "../api/visits";
import { StatusBadge } from "../components/StatusBadge";
import { VISIT_LABELS, VISIT_TONES, COLORS } from "../lib/design";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function SummaryPage() {
  const [month, setMonth] = useState(currentMonth());
  const summaryQuery = useQuery({
    queryKey: queryKeys.visitSummary(month),
    queryFn: () => fetchVisitSummary(month),
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
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
            月度汇总总表
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: 13.5,
              color: "rgba(245,246,248,0.45)",
            }}
          >
            按场次分组查看来访记录
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "#131a2c",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 9,
              padding: "8px 14px",
            }}
          >
            <svg width={14} height={14} viewBox="0 0 16 16" fill="none">
              <rect
                x="2"
                y="3"
                width="12"
                height="11"
                rx="1.3"
                stroke="rgba(245,246,248,0.5)"
                strokeWidth={1.3}
              />
              <line
                x1="2"
                y1="6.5"
                x2="14"
                y2="6.5"
                stroke="rgba(245,246,248,0.5)"
                strokeWidth={1.3}
              />
              <line
                x1="5.5"
                y1="1.5"
                x2="5.5"
                y2="4"
                stroke="rgba(245,246,248,0.5)"
                strokeWidth={1.3}
              />
              <line
                x1="10.5"
                y1="1.5"
                x2="10.5"
                y2="4"
                stroke="rgba(245,246,248,0.5)"
                strokeWidth={1.3}
              />
            </svg>
            <input
              type="month"
              value={month}
              onChange={(event) => setMonth(event.target.value)}
              style={{
                border: "none",
                background: "transparent",
                outline: "none",
                color: "#f5f6f8",
                fontSize: 13,
                fontWeight: 600,
                colorScheme: "dark",
                fontFamily: "inherit",
              }}
            />
          </div>
          <a
            href={visitSummaryExportUrl(month)}
            download
            style={{
              display: "flex",
              alignItems: "center",
              gap: 7,
              padding: "9px 16px",
              borderRadius: 9,
              border: "1px solid rgba(255,106,0,0.4)",
              background: "rgba(255,106,0,0.12)",
              color: "#FF9142",
              fontSize: 13,
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            <svg width={14} height={14} viewBox="0 0 16 16" fill="none">
              <path
                d="M8 2v8m0 0l-3-3m3 3l3-3"
                stroke="#FF9142"
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2.5 12v1.5A1.5 1.5 0 0 0 4 15h8a1.5 1.5 0 0 0 1.5-1.5V12"
                stroke="#FF9142"
                strokeWidth={1.5}
                strokeLinecap="round"
              />
            </svg>
            导出 Excel
          </a>
        </div>
      </div>

      {summaryQuery.data?.map((group) => (
        <div
          key={`${group.visit_date}-${group.session_time}`}
          style={{
            background: "#131a2c",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "16px 22px",
              borderBottom: "1px solid rgba(255,255,255,0.06)",
              background: "rgba(255,255,255,0.02)",
            }}
          >
            <span
              style={{
                width: 6,
                height: 20,
                borderRadius: 3,
                background: COLORS.orangeGradBar,
              }}
            />
            <h3
              style={{
                margin: 0,
                fontSize: 14.5,
                fontWeight: 700,
                color: "#f5f6f8",
              }}
            >
              场次：{group.visit_date} {group.session_time}
            </h3>
            <span
              style={{
                fontSize: 12.5,
                color: "rgba(245,246,248,0.4)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {group.visit_count} 人
            </span>
          </div>
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: "left",
                    padding: "9px 22px",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "rgba(245,246,248,0.4)",
                    letterSpacing: "0.3px",
                  }}
                >
                  姓名
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "9px 14px",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "rgba(245,246,248,0.4)",
                    letterSpacing: "0.3px",
                  }}
                >
                  身份
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "9px 14px",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "rgba(245,246,248,0.4)",
                    letterSpacing: "0.3px",
                  }}
                >
                  单位
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "9px 22px",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "rgba(245,246,248,0.4)",
                    letterSpacing: "0.3px",
                  }}
                >
                  状态
                </th>
              </tr>
            </thead>
            <tbody>
              {group.visits.map((visit) => (
                <tr
                  key={visit.id}
                  style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
                >
                  <td
                    style={{
                      padding: "10px 22px",
                      fontWeight: 600,
                      color: "#f5f6f8",
                    }}
                  >
                    {visit.name}
                  </td>
                  <td
                    style={{
                      padding: "10px 14px",
                      color: "rgba(245,246,248,0.6)",
                    }}
                  >
                    {visit.identity_type}
                  </td>
                  <td
                    style={{
                      padding: "10px 14px",
                      color: "rgba(245,246,248,0.6)",
                    }}
                  >
                    {visit.organization ?? "—"}
                  </td>
                  <td style={{ padding: "10px 22px" }}>
                    <StatusBadge
                      label={VISIT_LABELS[visit.status]}
                      tone={VISIT_TONES[visit.status]}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
