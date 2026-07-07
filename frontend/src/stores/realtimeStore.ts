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
      socket = null;
      set({ connected: false });
      const attempt = get().reconnectAttempt;
      const delay = Math.min(1000 * Math.pow(2, attempt), 30_000);
      set({ reconnectAttempt: attempt + 1 });
      setTimeout(() => get().connect(), delay);
    };
    socket.onmessage = (event) => {
      const message: RealtimeEvent = JSON.parse(event.data);
      if (message.type === "adapter.heartbeat") {
        const hb = message;
        set((state) => ({
          adapterStatuses: {
            ...state.adapterStatuses,
            [hb.adapter_name]: {
              status: String(hb.status),
              lastHeartbeat: hb.timestamp,
              detail: hb.detail ?? null,
            },
          },
        }));
        return;
      }
      if (message.type === "led.content") {
        const lc: LEDContent = {
          name: message.name,
          welcome_text: message.welcome_text,
          is_rejection: message.is_rejection,
          reason: message.reason,
        };
        set({ ledContent: lc });
        return;
      }
      set((state) => ({ events: [message, ...state.events].slice(0, 20) }));
    };
  },
}));
