import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { useRealtimeStore } from "./stores/realtimeStore";

const queryClient = new QueryClient();

export default function App() {
  const connect = useRealtimeStore((state) => state.connect);

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
