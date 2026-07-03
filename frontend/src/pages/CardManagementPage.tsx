// frontend/src/pages/CardManagementPage.tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCardWriteLog, writeCards } from "../api/cards";
import { queryKeys } from "../api/queryKeys";
import { fetchVisits } from "../api/visits";

export function CardManagementPage() {
  const [selected, setSelected] = useState<number[]>([]);
  const queryClient = useQueryClient();

  const visitsQuery = useQuery({
    queryKey: queryKeys.visits(),
    queryFn: () => fetchVisits(),
  });
  const writeLogQuery = useQuery({
    queryKey: queryKeys.cardWriteLog(),
    queryFn: () => fetchCardWriteLog(),
  });

  const writeMutation = useMutation({
    mutationFn: () => writeCards(selected),
    onSuccess: () => {
      setSelected([]);
      queryClient.invalidateQueries({ queryKey: ["cards", "write-log"] });
      queryClient.invalidateQueries({ queryKey: ["visits"] });
    },
  });

  const writable = (visitsQuery.data ?? []).filter(
    (visit) => visit.status === "welcome_ready",
  );

  function toggle(id: number) {
    setSelected((current) =>
      current.includes(id) ? current.filter((v) => v !== id) : [...current, id],
    );
  }

  return (
    <div>
      <h1>写卡管理</h1>
      <section>
        <h2>待写卡访客</h2>
        <table>
          <thead>
            <tr>
              <th></th>
              <th>姓名</th>
              <th>身份</th>
              <th>欢迎词</th>
            </tr>
          </thead>
          <tbody>
            {writable.map((visit) => (
              <tr key={visit.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.includes(visit.id)}
                    onChange={() => toggle(visit.id)}
                  />
                </td>
                <td>{visit.name}</td>
                <td>{visit.identity_type}</td>
                <td>{visit.welcome_text}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <button
          disabled={selected.length === 0}
          onClick={() => writeMutation.mutate()}
        >
          批量写卡（{selected.length}）
        </button>
      </section>

      <section>
        <h2>写卡记录</h2>
        <table>
          <thead>
            <tr>
              <th>visit_id</th>
              <th>card_uid</th>
              <th>状态</th>
              <th>错误信息</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {(writeLogQuery.data ?? []).map((log) => (
              <tr key={log.id}>
                <td>{log.visit_id}</td>
                <td>{log.card_uid}</td>
                <td>{log.write_status}</td>
                <td>{log.error_message}</td>
                <td>{log.written_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
