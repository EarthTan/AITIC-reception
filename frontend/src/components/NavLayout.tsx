// Top-level layout for the 8 admin pages: offline banner (if any) above the
// Sidebar + page content area. Full-screen hardware pages (/display, /mock-led)
// bypass this layout (see router.tsx).

import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { OfflineBanner } from "./OfflineBanner";

export function NavLayout() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        background: "#0a0e1a",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif',
        color: "rgba(245,246,248,0.75)",
      }}
    >
      <OfflineBanner />
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <Sidebar />
        <main
          style={{
            flex: 1,
            padding: "36px 40px 60px",
            display: "flex",
            flexDirection: "column",
            gap: 24,
            minWidth: 0,
            overflowX: "auto",
          }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
