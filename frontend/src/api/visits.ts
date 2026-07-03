// frontend/src/api/visits.ts
import { apiClient } from "./client";
import type { VisitOut, VisitSummaryRow, VisitUpdate } from "./types";

export async function fetchVisits(params?: {
  visit_date?: string;
  identity_type?: string;
}): Promise<VisitOut[]> {
  const response = await apiClient.get<VisitOut[]>("/visits", { params });
  return response.data;
}

export async function fetchVisit(id: number): Promise<VisitOut> {
  const response = await apiClient.get<VisitOut>(`/visits/${id}`);
  return response.data;
}

export async function updateVisit(id: number, patch: VisitUpdate): Promise<VisitOut> {
  const response = await apiClient.patch<VisitOut>(`/visits/${id}`, patch);
  return response.data;
}

export async function fetchVisitSummary(month: string): Promise<VisitSummaryRow[]> {
  const response = await apiClient.get<VisitSummaryRow[]>("/visits/summary", {
    params: { month },
  });
  return response.data;
}

export async function fetchVisitsToday(): Promise<VisitOut[]> {
  const response = await apiClient.get<VisitOut[]>("/visits/today");
  return response.data;
}

export function visitSummaryExportUrl(month: string): string {
  return `/api/visits/summary/export?month=${encodeURIComponent(month)}`;
}
