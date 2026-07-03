// frontend/src/api/queryKeys.ts
export const queryKeys = {
  visits: (params?: Record<string, unknown>) => ["visits", params ?? {}] as const,
  visit: (id: number) => ["visits", id] as const,
  visitSummary: (month: string) => ["visits", "summary", month] as const,
  visitsToday: () => ["visits", "today"] as const,
  templates: () => ["templates"] as const,
  cardWriteLog: (visitId?: number) => ["cards", "write-log", visitId ?? null] as const,
  verifyLog: () => ["verify-log"] as const,
  workLogs: (params?: Record<string, unknown>) => ["work-logs", params ?? {}] as const,
  adapterStatus: () => ["adapters", "status"] as const,
  settings: () => ["settings"] as const,
};
