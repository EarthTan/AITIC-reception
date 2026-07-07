// CardManagement / 写卡管理 — pending-visitors table (with batch write)
// + write-log table with search + pagination.
//
// Mirrors CardManagement.dc.html. Search filters client-side on card_uid /
// visit_id; pagination is computed against the filtered list.
//
// Page = 8 rows; previous/next + page indicator. We collapse to a single
// page when the dataset is small (<=8 rows) by hiding the bar.

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCardWriteLog, writeCards } from "../api/cards";
import { queryKeys } from "../api/queryKeys";
import { fetchVisits } from "../api/visits";
import { StatusBadge } from "../components/StatusBadge";
import {
  formatDateShort,
  formatTimeShort,
  WRITE_LABELS,
  WRITE_TONES,
} from "../lib/design";

const PAGE_SIZE = 8;

function pageButtonStyle(): React.CSSProperties {
  return {
    padding: "6px 14px",
    borderRadius: 7,
    border: "1px solid rgba(255,255,255,0.12)",
    background: "transparent",
    color: "rgba(245,246,248,0.55)",
    fontSize: 12.5,
    cursor: "pointer",
  };
}

export function CardManagementPage() {
  const [selected, setSelected] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const queryClient = useQueryClient();

  const visitsQuery = useQuery({
    queryKey: queryKeys.visits(),
    queryFn: () => fetchVisits(),
  });
  const writeLogQuery = useQuery({
    queryKey: queryKeys.cardWriteLog(),
    queryFn: () => fetchCardWriteLog(),
  });

  const writeMutation = useMutation({
    mutationFn: () => writeCards(selected),
    onSuccess: () => {
      setSelected([]);
      queryClient.invalidateQueries({ queryKey: ["cards", "write-log"] });
      queryClient.invalidateQueries({ queryKey: ["visits"] });
    },
  });

  const writable = (visitsQuery.data ?? []).filter(
    (visit) => visit.status === "welcome_ready",
  );

  const filteredLog = useMemo(() => {
    const query = search.toLowerCase();
    const rows = writeLogQuery.data ?? [];
    if (!query) return rows;
    return rows.filter(
      (l) =>
        String(l.visit_id).includes(query) ||
        (l.card_uid?.toLowerCase().includes(query) ?? false),
    );
  }, [search, writeLogQuery.data]);

  const totalPages = Math.max(1, Math.ceil(filteredLog.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageRows = filteredLog.slice(
    safePage * PAGE_SIZE,
    safePage * PAGE_SIZE + PAGE_SIZE,
  );

  function toggle(id: number) {
    setSelected((current) =>
      current.includes(id) ? current.filter((v) => v !== id) : [...current, id],
    );
  }

  const allSelected =
    writable.length > 0 && writable.every((v) => selected.includes(v.id));
  const selectedCount = selected.length;
  const batchActive = selectedCount > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1
          style={{
            margin: "0 0 4px",
            fontSize: 24,
            fontWeight: 700,
            color: "#f5f6f8",
          }}
        >
          写卡管理
        </h1>
        <p
          style={{ margin: 0, fontSize: 13.5, color: "rgba(245,246,248,0.45)" }}
        >
          批量写卡与写卡记录追溯
        </p>
      </div>

      {/* Pending visitors */}
      <div
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
            justifyContent: "space-between",
            padding: "18px 22px",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: 14.5,
              fontWeight: 700,
              color: "#f5f6f8",
            }}
          >
            待写卡访客
          </h2>
          <button
            disabled={!batchActive || writeMutation.isPending}
            onClick={() => writeMutation.mutate()}
            style={{
              padding: "9px 18px",
              borderRadius: 8,
              border: "none",
              background: batchActive
                ? "linear-gradient(135deg,#FF6A00,#FF8A2E)"
                : "rgba(255,255,255,0.06)",
              color: batchActive ? "#fff" : "rgba(245,246,248,0.3)",
              fontSize: 13,
              fontWeight: 700,
              cursor: batchActive ? "pointer" : "not-allowed",
            }}
          >
            批量写卡（{selectedCount}）
          </button>
        </div>
        <table
          style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
        >
          <thead>
            <tr>
              <th
                style={{
                  width: 40,
                  padding: "10px 22px",
                  textAlign: "left",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "rgba(245,246,248,0.4)",
                  letterSpacing: "0.3px",
                }}
              >
                <input
                  type="checkbox"
                  checked={allSelected}
                  disabled={writable.length === 0}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelected(writable.map((v) => v.id));
                    } else {
                      setSelected([]);
                    }
                  }}
                  style={{ width: 15, height: 15, accentColor: "#FF6A00" }}
                />
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "10px 14px",
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
                  padding: "10px 14px",
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
                  padding: "10px 22px",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "rgba(245,246,248,0.4)",
                  letterSpacing: "0.3px",
                }}
              >
                欢迎词
              </th>
            </tr>
          </thead>
          <tbody>
            {writable.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  style={{
                    padding: "24px 22px",
                    textAlign: "center",
                    color: "rgba(245,246,248,0.4)",
                    fontSize: 13,
                  }}
                >
                  暂无待写卡访客
                </td>
              </tr>
            )}
            {writable.map((visit) => (
              <tr
                key={visit.id}
                style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
              >
                <td style={{ padding: "10px 22px" }}>
                  <input
                    type="checkbox"
                    checked={selected.includes(visit.id)}
                    onChange={() => toggle(visit.id)}
                    style={{ width: 15, height: 15, accentColor: "#FF6A00" }}
                  />
                </td>
                <td
                  style={{
                    padding: "10px 14px",
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
                    padding: "10px 22px",
                    color: "rgba(245,246,248,0.45)",
                    maxWidth: 420,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {visit.welcome_text ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Write log */}
      <div
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
            justifyContent: "space-between",
            padding: "18px 22px",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            gap: 16,
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: 14.5,
              fontWeight: 700,
              color: "#f5f6f8",
              whiteSpace: "nowrap",
            }}
          >
            写卡记录
          </h2>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "#0d1220",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              padding: "7px 12px",
              width: 260,
            }}
          >
            <svg width={13} height={13} viewBox="0 0 16 16" fill="none">
              <circle
                cx="7"
                cy="7"
                r="5"
                stroke="rgba(245,246,248,0.4)"
                strokeWidth={1.3}
              />
              <line
                x1="10.8"
                y1="10.8"
                x2="14"
                y2="14"
                stroke="rgba(245,246,248,0.4)"
                strokeWidth={1.3}
                strokeLinecap="round"
              />
            </svg>
            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              placeholder="搜索 card_uid / visit_id"
              style={{
                border: "none",
                background: "transparent",
                outline: "none",
                color: "#f5f6f8",
                fontSize: 12.5,
                width: "100%",
              }}
            />
          </div>
        </div>
        <table
          style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
        >
          <thead>
            <tr>
              <th
                style={{
                  textAlign: "left",
                  padding: "10px 22px",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "rgba(245,246,248,0.4)",
                  letterSpacing: "0.3px",
                }}
              >
                visit_id
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "10px 14px",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "rgba(245,246,248,0.4)",
                  letterSpacing: "0.3px",
                }}
              >
                card_uid
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "10px 14px",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "rgba(245,246,248,0.4)",
                  letterSpacing: "0.3px",
                }}
              >
                状态
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "10px 14px",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "rgba(245,246,248,0.4)",
                  letterSpacing: "0.3px",
                }}
              >
                错误信息
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "10px 22px",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "rgba(245,246,248,0.4)",
                  letterSpacing: "0.3px",
                }}
              >
                时间
              </th>
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
                    color: "rgba(245,246,248,0.6)",
                  }}
                >
                  {log.visit_id}
                </td>
                <td
                  style={{
                    padding: "10px 14px",
                    fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
                    color: "rgba(245,246,248,0.7)",
                  }}
                >
                  {log.card_uid ?? "—"}
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <StatusBadge
                    label={WRITE_LABELS[log.write_status]}
                    tone={WRITE_TONES[log.write_status]}
                  />
                </td>
                <td
                  style={{
                    padding: "10px 14px",
                    color: "#f97a8b",
                    fontSize: 12,
                  }}
                >
                  {log.error_message ?? "—"}
                </td>
                <td
                  style={{
                    padding: "10px 22px",
                    fontVariantNumeric: "tabular-nums",
                    color: "rgba(245,246,248,0.4)",
                    fontSize: 12,
                  }}
                >
                  {formatDateShort(log.written_at)}{" "}
                  {formatTimeShort(log.written_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredLog.length > 0 && (
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
              共 {filteredLog.length} 条
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <button
                style={pageButtonStyle()}
                disabled={safePage === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                上一页
              </button>
              <span style={{ fontSize: 12.5, color: "rgba(245,246,248,0.5)" }}>
                第 {safePage + 1} / {totalPages} 页
              </span>
              <button
                style={pageButtonStyle()}
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
