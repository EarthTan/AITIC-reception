import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchWorkLogs, workLogExportUrl } from "../api/logs";

const MODULES = [
  "registration",
  "ai_writeup",
  "card_write",
  "verify",
  "led",
  "tts",
  "system",
];
const STATUSES = ["success", "failure", "warning"];

export function WorkLogPage() {
  const [moduleFilter, setModuleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const params = {
    module: moduleFilter || undefined,
    status: statusFilter || undefined,
  };
  const logsQuery = useQuery({
    queryKey: queryKeys.workLogs(params),
    queryFn: () => fetchWorkLogs(params),
  });

  return (
    <div>
      <h1>工作日志</h1>
      <select
        value={moduleFilter}
        onChange={(e) => setModuleFilter(e.target.value)}
      >
        <option value="">全部模块</option>
        {MODULES.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      <select
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
      >
        <option value="">全部状态</option>
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <a
        href={workLogExportUrl(moduleFilter, statusFilter)}
        download
        style={{
          padding: "6px 12px",
          background: "#1976d2",
          color: "#fff",
          borderRadius: 4,
          textDecoration: "none",
          marginLeft: 12,
        }}
      >
        导出 Excel
      </a>

      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>模块</th>
            <th>动作</th>
            <th>状态</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          {(logsQuery.data ?? []).map((log) => (
            <tr key={log.id}>
              <td>{log.created_at}</td>
              <td>{log.module}</td>
              <td>{log.action}</td>
              <td>{log.status}</td>
              <td>{log.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
