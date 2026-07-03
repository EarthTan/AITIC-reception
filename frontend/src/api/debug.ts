// frontend/src/api/debug.ts
import { apiClient } from "./client";

export async function simulateCardRead(
  cardUid: string,
  rawPayload: Record<string, unknown>
): Promise<void> {
  await apiClient.post("/debug/simulate-card-read", {
    card_uid: cardUid,
    raw_payload: rawPayload,
  });
}
