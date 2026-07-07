// WorkLog / 工作日志 — module/status filter chips + paginated table.
//
// Mirrors WorkLog.dc.html. Module & status filters drive React Query cache;
// export endpoint mirrors them.

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchWorkLogs, workLogExportUrl } from "../api/logs";
import { StatusBadge } from "../components/StatusBadge";
import {
  formatDateShort,
  formatTimeShort,
  LOG_MODULE_LABELS,
  LOG_STATUS_LABELS,
  LOG_STATUS_TONES,
} from "../lib/design";
import type { LogModule, LogStatus } from "../api/types";

const MODULE_OPTIONS: (LogModule | "")[] = [
  "",
  "registration",
  "ai_writeup",
  "card_write",
  "verify",
  "led",
  "tts",
  "system",
];
const STATUS_OPTIONS: (LogStatus | "")[] = [
  "",
  "success",
  "failure",
  "warning",
];
const PAGE_SIZE = 8;

export function WorkLogPage() {
  const [moduleFilter, setModuleFilter] = useState<LogModule | "">("");
  const [statusFilter, setStatusFilter] = useState<LogStatus | "">("");
  const [page, setPage] = useState(0);

  const params = {
    module: moduleFilter || undefined,
    status: statusFilter || undefined,
  };
  const logsQuery = useQuery({
    queryKey: queryKeys.workLogs(params),
    queryFn: () => fetchWorkLogs(params),
  });

  const allRows = logsQuery.data ?? [];
  const totalPages = Math.max(1, Math.ceil(allRows.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageRows = allRows.slice(
    safePage * PAGE_SIZE,
    safePage * PAGE_SIZE + PAGE_SIZE,
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
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
            工作日志
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: 13.5,
              color: "rgba(245,246,248,0.45)",
            }}
          >
            系统各模块运行事件追溯
          </p>
        </div>
        <a
          href={workLogExportUrl(moduleFilter, statusFilter)}
          download
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            padding: "9px 16px",
            borderRadius: 9,
            border: "none",
            background: "linear-gradient(135deg,#FF6A00,#FF8A2E)",
            color: "#fff",
            fontSize: 13,
            fontWeight: 700,
            textDecoration: "none",
            boxShadow: "0 4px 14px rgba(255,106,0,0.25)",
          }}
        >
          <svg width={14} height={14} viewBox="0 0 16 16" fill="none">
            <path
              d="M8 2v8m0 0l-3-3m3 3l3-3"
              stroke="#fff"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M2.5 12v1.5A1.5 1.5 0 0 0 4 15h8a1.5 1.5 0 0 0 1.5-1.5V12"
              stroke="#fff"
              strokeWidth={1.5}
              strokeLinecap="round"
            />
          </svg>
          导出 Excel
        </a>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <select
          value={moduleFilter}
          onChange={(e) => {
            setModuleFilter(e.target.value as LogModule | "");
            setPage(0);
          }}
          style={selectStyle}
        >
          {MODULE_OPTIONS.map((m) => (
            <option key={m || "all"} value={m}>
              {LOG_MODULE_LABELS[m]}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as LogStatus | "");
            setPage(0);
          }}
          style={selectStyle}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s || "all"} value={s}>
              {LOG_STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 12.5,
            color: "rgba(245,246,248,0.4)",
          }}
        >
          共 {allRows.length} 条记录
        </span>
      </div>

      <div
        style={{
          background: "#131a2c",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 14,
          overflow: "hidden",
        }}
      >
        <table
          style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
        >
          <thead>
            <tr>
              <th style={thStyle("22")}>时间</th>
              <th style={thStyle("14")}>模块</th>
              <th style={thStyle("14")}>动作</th>
              <th style={thStyle("14")}>状态</th>
              <th style={thStyle("22")}>详情</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((log) => (
              <tr
                key={log.id}
                style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
              >
                <td
                  style={{
                    padding: "10px 22px",
                    fontVariantNumeric: "tabular-nums",
                    color: "rgba(245,246,248,0.45)",
                    fontSize: 12,
                  }}
                >
                  {formatDateShort(log.created_at)}{" "}
                  {formatTimeShort(log.created_at)}
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <span
                    style={{
                      fontSize: 11.5,
                      padding: "3px 9px",
                      borderRadius: 6,
                      background: "rgba(245,246,248,0.06)",
                      color: "rgba(245,246,248,0.6)",
                      fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
                    }}
                  >
                    {log.module}
                  </span>
                </td>
                <td
                  style={{
                    padding: "10px 14px",
                    color: "#f5f6f8",
                    fontWeight: 500,
                  }}
                >
                  {log.action}
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <StatusBadge
                    label={LOG_STATUS_LABELS[log.status]}
                    tone={LOG_STATUS_TONES[log.status]}
                  />
                </td>
                <td
                  style={{
                    padding: "10px 22px",
                    color: "rgba(245,246,248,0.4)",
                    fontSize: 12.5,
                    maxWidth: 340,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {log.detail ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {allRows.length > 0 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "14px 22px",
              borderTop: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span style={{ fontSize: 12, color: "rgba(245,246,248,0.35)" }}>
              每页 {PAGE_SIZE} 条
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <button
                style={{
                  padding: "6px 14px",
                  borderRadius: 7,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "transparent",
                  color: "rgba(245,246,248,0.55)",
                  fontSize: 12.5,
                  cursor: safePage === 0 ? "not-allowed" : "pointer",
                  opacity: safePage === 0 ? 0.5 : 1,
                }}
                disabled={safePage === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                上一页
              </button>
              <span style={{ fontSize: 12.5, color: "rgba(245,246,248,0.5)" }}>
                第 {safePage + 1} / {totalPages} 页
              </span>
              <button
                style={{
                  padding: "6px 14px",
                  borderRadius: 7,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "transparent",
                  color: "rgba(245,246,248,0.55)",
                  fontSize: 12.5,
                  cursor:
                    safePage >= totalPages - 1 ? "not-allowed" : "pointer",
                  opacity: safePage >= totalPages - 1 ? 0.5 : 1,
                }}
                disabled={safePage >= totalPages - 1}
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  padding: "9px 14px",
  borderRadius: 9,
  border: "1px solid rgba(255,255,255,0.12)",
  background: "#131a2c",
  color: "#f5f6f8",
  fontSize: 13,
  outline: "none",
  colorScheme: "dark",
};

function thStyle(side: "14" | "22"): React.CSSProperties {
  return {
    textAlign: "left",
    padding: `11px ${side}px`,
    fontSize: 11,
    fontWeight: 600,
    color: "rgba(245,246,248,0.4)",
    letterSpacing: "0.3px",
  };
}
