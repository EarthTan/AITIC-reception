// Templates / 欢迎词模板 — editable list, one row per identity type.
//
// Mirrors Templates.dc.html. The save button shows "保存" initially; after
// a successful PUT it briefly flips to "已保存" (green) until the next edit.

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchTemplates, updateTemplate } from "../api/templates";
import { TEMPLATE_IDENTITY_TYPES } from "../lib/design";

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const templatesQuery = useQuery({
    queryKey: queryKeys.templates(),
    queryFn: fetchTemplates,
  });
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});

  const updateMutation = useMutation({
    mutationFn: ({
      identityType,
      text,
    }: {
      identityType: string;
      text: string;
    }) => updateTemplate(identityType, text),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.templates() });
      setSaved((s) => ({ ...s, [vars.identityType]: true }));
    },
  });

  // 3-second "已保存" affordance — revert to "保存" so the user can see the
  // button is interactable again.
  useEffect(() => {
    const flagged = Object.entries(saved).filter(([_, v]) => v);
    if (flagged.length === 0) return;
    const timers = flagged.map(([key]) =>
      window.setTimeout(() => setSaved((s) => ({ ...s, [key]: false })), 3000),
    );
    return () => timers.forEach((t) => clearTimeout(t));
  }, [saved]);

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
          欢迎词模板
        </h1>
        <p
          style={{ margin: 0, fontSize: 13.5, color: "rgba(245,246,248,0.45)" }}
        >
          按身份类型配置写卡/播报所用的欢迎文案
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {TEMPLATE_IDENTITY_TYPES.map((identity) => {
          const tpl = templatesQuery.data?.find(
            (t) => t.identity_type === identity,
          );
          const draft = drafts[identity] ?? tpl?.template_text ?? "";
          const isSaved = saved[identity];
          return (
            <div
              key={identity}
              style={{
                background: "#131a2c",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 14,
                padding: "18px 22px",
                display: "grid",
                gridTemplateColumns: "140px 1fr 100px",
                alignItems: "center",
                gap: 18,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: "#FF6A00",
                    flex: "none",
                  }}
                />
                <span
                  style={{
                    fontSize: 13.5,
                    fontWeight: 700,
                    color: "#f5f6f8",
                  }}
                >
                  {identity}
                </span>
              </div>
              <input
                value={draft}
                onChange={(e) => {
                  setDrafts((d) => ({ ...d, [identity]: e.target.value }));
                  setSaved((s) => ({ ...s, [identity]: false }));
                }}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "#0d1220",
                  color: "rgba(245,246,248,0.8)",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              <button
                onClick={() =>
                  updateMutation.mutate({ identityType: identity, text: draft })
                }
                disabled={updateMutation.isPending}
                style={{
                  padding: "9px 0",
                  borderRadius: 8,
                  border: isSaved
                    ? "1px solid rgba(47,191,113,0.35)"
                    : "1px solid rgba(255,106,0,0.4)",
                  background: isSaved
                    ? "rgba(47,191,113,0.12)"
                    : "rgba(255,106,0,0.12)",
                  color: isSaved ? "#4fd68d" : "#FF9142",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  textAlign: "center",
                }}
              >
                {isSaved ? "已保存" : "保存"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
