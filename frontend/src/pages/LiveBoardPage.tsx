// frontend/src/pages/LiveBoardPage.tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { simulateCardRead } from "../api/debug";
import { useRealtimeStore } from "../stores/realtimeStore";

export function LiveBoardPage() {
  const events = useRealtimeStore((state) => state.events);
  const connected = useRealtimeStore((state) => state.connected);
  const [cardUid, setCardUid] = useState("SIM-001");
  const [visitId, setVisitId] = useState("");
  const [name, setName] = useState("");
  const [visitDate, setVisitDate] = useState("");

  const simulateMutation = useMutation({
    // visit_id is REQUIRED: the backend's VerifyService looks up the visit
    // by raw_payload["visit_id"]; without it, every simulated read would
    // fail with `card_not_found` and the success/name-mismatch branches
    // would never fire. Day 3 plan amendment.
    mutationFn: () =>
      simulateCardRead(cardUid, {
        visit_id: visitId ? Number(visitId) : undefined,
        name,
        visit_date: visitDate,
      }),
  });

  const latest = events[0];

  return (
    <div>
      <h1>现场实时看板</h1>
      <p>WebSocket连接状态：{connected ? "已连接" : "未连接"}</p>

      <section>
        {latest?.type === "card.verify.passed" && (
          <div>
            <h2>欢迎光临！</h2>
            <p>visit_id: {String(latest.payload.visit_id)}</p>
          </div>
        )}
        {latest?.type === "card.verify.failed" && (
          <div>
            <h2 style={{ color: "red" }}>无权限入场</h2>
            <p>原因：{String(latest.payload.fail_reason)}</p>
          </div>
        )}
      </section>

      <section>
        <h3>模拟刷卡（调试用）</h3>
        <label>
          card_uid:
          <input value={cardUid} onChange={(e) => setCardUid(e.target.value)} />
        </label>
        <label>
          visit_id:
          <input
            value={visitId}
            onChange={(e) => setVisitId(e.target.value)}
            placeholder="必填，从 /api/cards/write-log 取"
          />
        </label>
        <label>
          姓名:
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          来访日期:
          <input
            type="date"
            value={visitDate}
            onChange={(e) => setVisitDate(e.target.value)}
          />
        </label>
        <button onClick={() => simulateMutation.mutate()}>模拟刷卡</button>
      </section>

      <section>
        <h3>最近事件</h3>
        <ul>
          {events.map((event, index) => (
            <li key={index}>
              {event.timestamp} - {event.type} - {JSON.stringify(event.payload)}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
