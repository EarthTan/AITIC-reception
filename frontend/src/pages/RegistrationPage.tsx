// frontend/src/pages/RegistrationPage.tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { commitImport, previewImport } from "../api/imports";
import type { ImportPreviewResponse } from "../api/types";

export function RegistrationPage() {
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const queryClient = useQueryClient();

  const previewMutation = useMutation({
    mutationFn: previewImport,
    onSuccess: (data) => setPreview(data),
  });

  const commitMutation = useMutation({
    mutationFn: () => commitImport(preview!.preview_id),
    onSuccess: () => {
      setPreview(null);
      queryClient.invalidateQueries({ queryKey: ["visits"] });
    },
  });

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      previewMutation.mutate(file);
    }
  }

  return (
    <div>
      <h1>访客登记</h1>
      <input type="file" accept=".xlsx,.xls" onChange={handleFileChange} />

      {previewMutation.isPending && <p>解析中...</p>}

      {preview && (
        <div>
          <p>
            有效 {preview.valid_count} 行，无效 {preview.invalid_count} 行
          </p>
          <table>
            <thead>
              <tr>
                <th>行号</th>
                <th>姓名</th>
                <th>身份</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row) => (
                <tr
                  key={row.row_number}
                  style={{ background: row.is_valid ? undefined : "#ffdddd" }}
                >
                  <td>{row.row_number}</td>
                  <td>{String(row.data["姓名"] ?? "")}</td>
                  <td>{String(row.data["身份"] ?? "")}</td>
                  <td>{row.errors.join("; ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            disabled={preview.valid_count === 0 || commitMutation.isPending}
            onClick={() => commitMutation.mutate()}
          >
            确认入库（{preview.valid_count}条）
          </button>
        </div>
      )}

      {commitMutation.isSuccess && (
        <p>
          导入成功，批次号：{commitMutation.data.import_batch_id}，共
          {commitMutation.data.visit_ids.length}条
        </p>
      )}
    </div>
  );
}
