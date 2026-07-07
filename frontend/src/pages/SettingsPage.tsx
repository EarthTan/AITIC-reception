// Settings / 系统设置 — current-config grid + edit form (760px max width).
//
// Mirrors Settings.dc.html. Empty fields = "don't change" semantics, matching
// the original implementation.

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchSettings, updateSettings } from "../api/settings";
import { StatusBadge } from "../components/StatusBadge";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: queryKeys.settings(),
    queryFn: fetchSettings,
  });
  const [apiKeyDraft, setApiKeyDraft] = useState("");
  const [watchDirDraft, setWatchDirDraft] = useState("");

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings() });
    },
  });

  const settings = settingsQuery.data;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 24,
        maxWidth: 760,
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
          系统设置
        </h1>
        <p
          style={{ margin: 0, fontSize: 13.5, color: "rgba(245,246,248,0.45)" }}
        >
          配置 Excel 监听目录与 AI 服务凭据
        </p>
      </div>

      {settings && (
        <div
          style={{
            background: "#131a2c",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14,
            padding: "24px 26px",
            display: "flex",
            flexDirection: "column",
            gap: 16,
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
            当前配置
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
            }}
          >
            <SettingField label="Excel 监听目录">
              <span
                style={{
                  fontSize: 13,
                  color: "#f5f6f8",
                  fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
                }}
              >
                {settings.excel_watch_dir}
              </span>
            </SettingField>
            <SettingField label="AI 服务商">
              <span style={{ fontSize: 13, color: "#f5f6f8" }}>
                {settings.ai_provider}
              </span>
            </SettingField>
            <SettingField label="AI Key 已配置">
              <StatusBadge
                label={settings.has_ai_api_key ? "是" : "否"}
                tone={settings.has_ai_api_key ? "success" : "neutral"}
              />
            </SettingField>
            <SettingField label="CORS 来源">
              <span
                style={{
                  fontSize: 13,
                  color: "#f5f6f8",
                  fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
                }}
              >
                {settings.cors_origins?.join(", ") || "—"}
              </span>
            </SettingField>
          </div>
        </div>
      )}

      <div
        style={{
          background: "#131a2c",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 14,
          padding: "24px 26px",
          display: "flex",
          flexDirection: "column",
          gap: 18,
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
          修改配置
        </h2>
        <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span
            style={{
              fontSize: 12.5,
              color: "rgba(245,246,248,0.5)",
              fontWeight: 500,
            }}
          >
            新的 Excel 监听目录
          </span>
          <input
            value={watchDirDraft}
            onChange={(e) => setWatchDirDraft(e.target.value)}
            placeholder="留空表示不修改"
            style={inputStyle}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span
            style={{
              fontSize: 12.5,
              color: "rgba(245,246,248,0.5)",
              fontWeight: 500,
            }}
          >
            新的 AI Key
          </span>
          <input
            type="password"
            value={apiKeyDraft}
            onChange={(e) => setApiKeyDraft(e.target.value)}
            placeholder="留空表示不修改"
            style={inputStyle}
          />
        </label>
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={() =>
              updateMutation.mutate({
                excel_watch_dir: watchDirDraft || undefined,
                ai_api_key: apiKeyDraft || undefined,
              })
            }
            style={{
              padding: "10px 24px",
              borderRadius: 9,
              border: "none",
              background: "linear-gradient(135deg,#FF6A00,#FF8A2E)",
              color: "#fff",
              fontSize: 13.5,
              fontWeight: 700,
              cursor: "pointer",
              boxShadow: "0 4px 14px rgba(255,106,0,0.25)",
            }}
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.12)",
  background: "#0d1220",
  color: "#f5f6f8",
  fontSize: 13,
  outline: "none",
};

interface SettingFieldProps {
  label: string;
  children: React.ReactNode;
}
function SettingField({ label, children }: SettingFieldProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11.5, color: "rgba(245,246,248,0.4)" }}>
        {label}
      </span>
      <span style={{ display: "inline-flex" }}>{children}</span>
    </div>
  );
}
