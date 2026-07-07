// frontend/src/stores/realtimeStore.ts
import { create } from "zustand";
import type { LEDContent, RealtimeEvent } from "../api/types";

interface AdapterLiveStatus {
  status: string;
  lastHeartbeat: string;
  detail: string | null;
}

interface RealtimeState {
  connected: boolean;
  events: RealtimeEvent[];
  adapterStatuses: Record<string, AdapterLiveStatus>;
  ledContent: LEDContent | null;
  reconnectAttempt: number;
  connect: () => void;
}

let socket: WebSocket | null = null;

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  connected: false,
  events: [],
  adapterStatuses: {},
  ledContent: null,
  reconnectAttempt: 0,
  connect: () => {
    if (socket) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/realtime`);

    socket.onopen = () => set({ connected: true, reconnectAttempt: 0 });
    socket.onclose = () => {
      set({ connected: false, socket: null });
      const attempt = get().reconnectAttempt;
      const delay = Math.min(1000 * Math.pow(2, attempt), 30_000);
      set({ reconnectAttempt: attempt + 1 });
      setTimeout(connect, delay);
    };
    socket.onmessage = (event) => {
      const message: RealtimeEvent = JSON.parse(event.data);
      set((state) => {
        if (message.type === "adapter.heartbeat") {
          const name = String(message.payload.adapter_name);
          return {
            adapterStatuses: {
              ...state.adapterStatuses,
              [name]: {
                status: String(message.payload.status),
                lastHeartbeat: message.timestamp,
                detail: (message.payload.detail as string | null) ?? null,
              },
            },
          };
        }
        if (message.type === "led.content") {
          return { ledContent: message.payload as LEDContent };
        }
        return { events: [message, ...state.events].slice(0, 20) };
      });
    };
  },
}));
