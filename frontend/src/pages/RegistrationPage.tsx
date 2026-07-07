// Registration / 访客登记 — Excel upload + 11-column preview table.
//
// Mirrors Registration.dc.html. Logic (preview → commit, invalid-row error
// display, file picker) is unchanged from the previous implementation; only
// the markup is restyled.

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { commitImport, previewImport } from "../api/imports";
import type { ImportPreviewResponse } from "../api/types";

const COLUMNS = [
  { key: "row_number", label: "行号", width: 1, mono: true },
  { key: "姓名", label: "姓名", width: 1, bold: true },
  { key: "来访日期", label: "来访日期", width: 1 },
  { key: "计划场次时间", label: "场次时间", width: 1, mono: true },
  { key: "手机号", label: "手机号", width: 1, mono: true, muted: true },
  { key: "国籍", label: "国籍", width: 1 },
  { key: "身份证号", label: "身份证号", width: 1, mono: true, muted: true },
  { key: "性别", label: "性别", width: 1 },
  { key: "单位", label: "单位", width: 1 },
  { key: "身份", label: "身份", width: 1 },
  { key: "__errors", label: "错误", width: 1, danger: true },
] as const;

const HEAD_BASE = {
  textAlign: "left" as const,
  padding: "11px 14px",
  fontSize: 11.5,
  fontWeight: 600,
  color: "rgba(245,246,248,0.45)",
  letterSpacing: "0.3px",
  whiteSpace: "nowrap" as const,
  borderBottom: "1px solid rgba(255,255,255,0.08)",
};

export function RegistrationPage() {
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const previewMutation = useMutation({
    mutationFn: previewImport,
    onSuccess: (data) => setPreview(data),
  });

  const commitMutation = useMutation({
    mutationFn: () => commitImport(preview!.preview_id),
    onSuccess: () => {
      setPreview(null);
      setFileName(null);
      queryClient.invalidateQueries({ queryKey: ["visits"] });
    },
  });

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    previewMutation.mutate(file);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <div>
        <h1
          style={{
            margin: "0 0 4px",
            fontSize: 24,
            fontWeight: 700,
            color: "#f5f6f8",
          }}
        >
          访客登记
        </h1>
        <p
          style={{ margin: 0, fontSize: 13.5, color: "rgba(245,246,248,0.45)" }}
        >
          导入 Excel 访客名单，校验后统一入库
        </p>
      </div>

      {/* Upload zone */}
      <label
        style={{
          background: "#131a2c",
          border: "1px dashed rgba(255,106,0,0.35)",
          borderRadius: 14,
          padding: "26px 28px",
          display: "flex",
          alignItems: "center",
          gap: 20,
          cursor: "pointer",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 10,
            background: "rgba(255,106,0,0.12)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: "none",
          }}
        >
          <svg width={20} height={20} viewBox="0 0 20 20" fill="none">
            <path
              d="M10 3v10M10 3l-4 4M10 3l4 4"
              stroke="#FF9142"
              strokeWidth={1.6}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M3 14v2a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 17 16v-2"
              stroke="#FF9142"
              strokeWidth={1.6}
              strokeLinecap="round"
            />
          </svg>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#f5f6f8" }}>
            选择 Excel 文件（.xlsx / .xls）
          </span>
          <span style={{ fontSize: 12.5, color: "rgba(245,246,248,0.4)" }}>
            {fileName ? `已选择：${fileName}` : "未选择文件"}
          </span>
        </div>
        <span
          style={{
            marginLeft: "auto",
            padding: "9px 18px",
            borderRadius: 8,
            border: "1px solid rgba(255,106,0,0.4)",
            background: "rgba(255,106,0,0.12)",
            color: "#FF9142",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {fileName ? "重新选择" : "选择文件"}
        </span>
        <input
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
      </label>

      {previewMutation.isPending && (
        <p style={{ margin: 0, fontSize: 13, color: "rgba(245,246,248,0.45)" }}>
          解析中...
        </p>
      )}

      {preview && (
        <>
          {/* Stats */}
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 16px",
                background: "rgba(47,191,113,0.12)",
                border: "1px solid rgba(47,191,113,0.28)",
                borderRadius: 10,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#2FBF71",
                }}
              />
              <span style={{ fontSize: 13, color: "#4fd68d", fontWeight: 600 }}>
                有效 {preview.valid_count} 行
              </span>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 16px",
                background: "rgba(240,69,91,0.12)",
                border: "1px solid rgba(240,69,91,0.28)",
                borderRadius: 10,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#F0455B",
                }}
              />
              <span style={{ fontSize: 13, color: "#f97a8b", fontWeight: 600 }}>
                无效 {preview.invalid_count} 行
              </span>
            </div>
            <span
              style={{
                marginLeft: "auto",
                fontSize: 12.5,
                color: "rgba(245,246,248,0.4)",
              }}
            >
              批次预览 · preview_id: {preview.preview_id}
            </span>
          </div>

          {/* Preview table */}
          <div
            style={{
              background: "#131a2c",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 14,
              overflow: "hidden",
            }}
          >
            <div style={{ maxHeight: 420, overflow: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr
                    style={{
                      position: "sticky",
                      top: 0,
                      background: "#171f34",
                      zIndex: 1,
                    }}
                  >
                    {COLUMNS.map((col, i) => (
                      <th
                        key={col.key}
                        style={{
                          ...HEAD_BASE,
                          paddingLeft:
                            i === 0 || i === COLUMNS.length - 1 ? 22 : 14,
                          paddingRight:
                            i === 0 || i === COLUMNS.length - 1 ? 22 : 14,
                        }}
                      >
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row) => {
                    const errText = row.errors.join("; ");
                    return (
                      <tr
                        key={row.row_number}
                        style={{
                          background: row.is_valid
                            ? "transparent"
                            : "rgba(240,69,91,0.08)",
                          borderBottom: "1px solid rgba(255,255,255,0.05)",
                        }}
                      >
                        <td
                          style={{
                            padding: "10px 22px",
                            color: "rgba(245,246,248,0.4)",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          {row.row_number}
                        </td>
                        <td
                          style={{
                            padding: "10px 14px",
                            fontWeight: 600,
                            color: "#f5f6f8",
                          }}
                        >
                          {String(row.data["姓名"] ?? "")}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          {String(row.data["来访日期"] ?? "")}
                        </td>
                        <td
                          style={{
                            padding: "10px 14px",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          {String(row.data["计划场次时间"] ?? "")}
                        </td>
                        <td
                          style={{
                            padding: "10px 14px",
                            fontVariantNumeric: "tabular-nums",
                            color: "rgba(245,246,248,0.55)",
                          }}
                        >
                          {String(row.data["手机号"] ?? "") || "—"}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          {String(row.data["国籍"] ?? "")}
                        </td>
                        <td
                          style={{
                            padding: "10px 14px",
                            fontVariantNumeric: "tabular-nums",
                            color: "rgba(245,246,248,0.55)",
                          }}
                        >
                          {String(row.data["身份证号"] ?? "")}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          {String(row.data["性别"] ?? "")}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          {String(row.data["单位"] ?? "")}
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          {String(row.data["身份"] ?? "")}
                        </td>
                        <td
                          style={{
                            padding: "10px 22px",
                            color: "#f97a8b",
                            fontSize: 12,
                          }}
                        >
                          {errText}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Commit */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              disabled={preview.valid_count === 0 || commitMutation.isPending}
              onClick={() => commitMutation.mutate()}
              style={{
                padding: "11px 26px",
                borderRadius: 9,
                border: "none",
                background:
                  preview.valid_count === 0
                    ? "rgba(255,255,255,0.06)"
                    : "linear-gradient(135deg,#FF6A00,#FF8A2E)",
                color:
                  preview.valid_count === 0 ? "rgba(245,246,248,0.3)" : "#fff",
                fontSize: 14,
                fontWeight: 700,
                cursor: preview.valid_count === 0 ? "not-allowed" : "pointer",
                boxShadow:
                  preview.valid_count === 0
                    ? "none"
                    : "0 4px 14px rgba(255,106,0,0.28)",
              }}
            >
              确认入库（{preview.valid_count}条）
            </button>
          </div>
        </>
      )}

      {commitMutation.isSuccess && commitMutation.data && (
        <p style={{ margin: 0, fontSize: 13, color: "#4fd68d" }}>
          导入成功，批次号：{commitMutation.data.import_batch_id}，共
          {commitMutation.data.visit_ids.length}条
        </p>
      )}
    </div>
  );
}
