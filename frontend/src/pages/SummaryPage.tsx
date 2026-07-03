// frontend/src/pages/SummaryPage.tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchVisitSummary, visitSummaryExportUrl } from "../api/visits";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function SummaryPage() {
  const [month, setMonth] = useState(currentMonth());
  const summaryQuery = useQuery({
    queryKey: queryKeys.visitSummary(month),
    queryFn: () => fetchVisitSummary(month),
  });

  return (
    <div>
      <h1>月度汇总总表</h1>
      <input
        type="month"
        value={month}
        onChange={(event) => setMonth(event.target.value)}
      />
      <a href={visitSummaryExportUrl(month)} download>
        导出Excel
      </a>

      {summaryQuery.data?.map((group) => (
        <div key={`${group.visit_date}-${group.session_time}`}>
          <h3>
            场次：{group.visit_date} {group.session_time}（{group.visit_count}
            人）
          </h3>
          <table>
            <thead>
              <tr>
                <th>姓名</th>
                <th>身份</th>
                <th>单位</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {group.visits.map((visit) => (
                <tr key={visit.id}>
                  <td>{visit.name}</td>
                  <td>{visit.identity_type}</td>
                  <td>{visit.organization}</td>
                  <td>{visit.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
