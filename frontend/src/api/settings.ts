// frontend/src/api/settings.ts
import { apiClient } from "./client";
import type { SettingsOut, SettingsUpdate } from "./types";

export async function fetchSettings(): Promise<SettingsOut> {
  const response = await apiClient.get<SettingsOut>("/settings");
  return response.data;
}

export async function updateSettings(patch: SettingsUpdate): Promise<SettingsOut> {
  const response = await apiClient.put<SettingsOut>("/settings", patch);
  return response.data;
}
