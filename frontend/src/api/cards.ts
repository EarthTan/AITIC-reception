// frontend/src/api/cards.ts
import { apiClient } from "./client";
import type { CardWriteLogOut, CardWriteResult } from "./types";

export async function writeCards(visitIds: number[]): Promise<CardWriteResult[]> {
  const response = await apiClient.post<CardWriteResult[]>("/cards/write", {
    visit_ids: visitIds,
  });
  return response.data;
}

export async function fetchCardWriteLog(visitId?: number): Promise<CardWriteLogOut[]> {
  const response = await apiClient.get<CardWriteLogOut[]>("/cards/write-log", {
    params: visitId ? { visit_id: visitId } : undefined,
  });
  return response.data;
}
