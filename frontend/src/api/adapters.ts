// frontend/src/api/adapters.ts
import { apiClient } from "./client";
import type { AdapterStatusOut } from "./types";

export async function fetchAdapterStatus(): Promise<AdapterStatusOut[]> {
  const response = await apiClient.get<AdapterStatusOut[]>("/adapters/status");
  return response.data;
}
