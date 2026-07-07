// frontend/src/api/logs.ts
import { apiClient } from "./client";
import type { VerifyLogOut, WorkLogOut } from "./types";

export async function fetchVerifyLog(): Promise<VerifyLogOut[]> {
  const response = await apiClient.get<VerifyLogOut[]>("/verify-log");
  return response.data;
}

export async function fetchWorkLogs(params?: {
  module?: string;
  status?: string;
}): Promise<WorkLogOut[]> {
  const response = await apiClient.get<WorkLogOut[]>("/work-logs", { params });
  return response.data;
}

export function workLogExportUrl(module?: string, status?: string): string {
  const params = new URLSearchParams();
  if (module) params.set("module", module);
  if (status) params.set("status", status);
  const qs = params.toString();
  return `/api/work-logs/export${qs ? `?${qs}` : ""}`;
}
