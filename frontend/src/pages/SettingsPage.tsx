// frontend/src/pages/SettingsPage.tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchSettings, updateSettings } from "../api/settings";

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
    <div>
      <h1>系统设置</h1>
      {settings && (
        <div>
          <p>Excel监听目录：{settings.excel_watch_dir}</p>
          <p>AI服务商：{settings.ai_provider}</p>
          <p>AI Key已配置：{settings.has_ai_api_key ? "是" : "否"}</p>
          {settings.message && <p>{settings.message}</p>}
        </div>
      )}

      <label>
        新的Excel监听目录：
        <input
          value={watchDirDraft}
          onChange={(e) => setWatchDirDraft(e.target.value)}
        />
      </label>
      <label>
        新的AI Key：
        <input
          type="password"
          value={apiKeyDraft}
          onChange={(e) => setApiKeyDraft(e.target.value)}
        />
      </label>
      <button
        onClick={() =>
          updateMutation.mutate({
            excel_watch_dir: watchDirDraft || undefined,
            ai_api_key: apiKeyDraft || undefined,
          })
        }
      >
        保存
      </button>
    </div>
  );
}
