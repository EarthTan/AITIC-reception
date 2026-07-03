// frontend/src/stores/realtimeStore.ts
import { create } from "zustand";

export interface RealtimeEvent {
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

interface AdapterLiveStatus {
  status: string;
  lastHeartbeat: string;
  detail: string | null;
}

interface RealtimeState {
  connected: boolean;
  events: RealtimeEvent[];
  adapterStatuses: Record<string, AdapterLiveStatus>;
  connect: () => void;
}

let socket: WebSocket | null = null;

export const useRealtimeStore = create<RealtimeState>((set) => ({
  connected: false,
  events: [],
  adapterStatuses: {},
  connect: () => {
    if (socket) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/realtime`);

    socket.onopen = () => set({ connected: true });
    socket.onclose = () => {
      set({ connected: false });
      socket = null;
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
        return { events: [message, ...state.events].slice(0, 20) };
      });
    };
  },
}));
