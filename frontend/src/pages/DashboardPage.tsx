// frontend/src/pages/DashboardPage.tsx
import { useQuery } from "@tanstack/react-query";
import { fetchAdapterStatus } from "../api/adapters";
import { queryKeys } from "../api/queryKeys";
import { fetchVisitsToday } from "../api/visits";
import { useRealtimeStore } from "../stores/realtimeStore";

const ADAPTER_NAMES = ["nfc", "led", "tts", "ai"] as const;

export function DashboardPage() {
  const todayQuery = useQuery({
    queryKey: queryKeys.visitsToday(),
    queryFn: fetchVisitsToday,
  });
  const statusQuery = useQuery({
    queryKey: queryKeys.adapterStatus(),
    queryFn: fetchAdapterStatus,
  });
  const realtimeStatuses = useRealtimeStore((state) => state.adapterStatuses);

  const merged = new Map<string, { status: string; detail?: string | null }>();
  for (const row of statusQuery.data ?? []) {
    merged.set(row.adapter_name, { status: row.status, detail: row.detail });
  }
  for (const [name, live] of Object.entries(realtimeStatuses)) {
    merged.set(name, { status: live.status, detail: live.detail });
  }

  return (
    <div>
      <h1>仪表盘</h1>
      <section>
        <h2>今日来访人数：{todayQuery.data?.length ?? "-"}</h2>
      </section>
      <section>
        <h2>适配器状态</h2>
        <ul>
          {ADAPTER_NAMES.map((name) => {
            const entry = merged.get(name);
            return (
              <li key={name}>
                {name}: {entry ? entry.status : "unknown"}
                {entry?.detail ? ` (${entry.detail})` : ""}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
