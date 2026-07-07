// Top nav rail. Fixed 240px wide, dark sidebar background, 3 nav groups with
// active-state left rail + orange dot. Bottom row shows hardware-health dot.
//
// Mirrors Sidebar.dc.html. Uses react-router's NavLink so the active-class
// machinery handles "active" automatically (slightly nicer than computing
// it from window.location — survives future nested routes).

import type { CSSProperties } from "react";
import { NavLink } from "react-router-dom";
import { useRealtimeStore } from "../stores/realtimeStore";
import { NAV_GROUPS } from "../lib/design";
import { SIDEBAR_ICONS } from "./icons/SidebarIcon";

const NAV_STYLE: CSSProperties = {
  width: 240,
  minWidth: 240,
  height: "100%",
  background: "#0d1220",
  borderRight: "1px solid rgba(255,255,255,0.08)",
  display: "flex",
  flexDirection: "column",
  padding: "20px 0",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif',
};
const GROUP_HEAD: CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: "rgba(245,246,248,0.32)",
  letterSpacing: "0.6px",
  padding: "8px 12px 6px",
};
const GROUP_HEAD_SPACED: CSSProperties = {
  ...GROUP_HEAD,
  padding: "14px 12px 6px",
};

function navRowStyle(active: boolean): CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "9px 12px",
    margin: "0 0",
    borderRadius: 8,
    fontSize: 13.5,
    fontWeight: active ? 600 : 500,
    color: active ? "#ffffff" : "rgba(245,246,248,0.62)",
    background: active
      ? "linear-gradient(90deg, rgba(255,106,0,0.22), rgba(255,106,0,0.06))"
      : "transparent",
    borderLeft: active ? "2px solid #FF6A00" : "2px solid transparent",
    textDecoration: "none",
    cursor: "pointer",
    transition: "background 0.15s",
  };
}

const ICON_WRAP_BASE: CSSProperties = {
  display: "flex",
  flex: "none",
};
const BRAND_BAR_STYLE: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "stretch",
  marginTop: "auto",
  padding: "14px 24px 0",
  borderTop: "1px solid rgba(255,255,255,0.08)",
};

export function Sidebar() {
  const statuses = useRealtimeStore((s) => s.adapterStatuses);
  const allOnline =
    Object.values(statuses).length > 0 &&
    Object.values(statuses).every((s) => s.status === "online");

  return (
    <nav style={NAV_STYLE}>
      {/* Brand */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "0 24px 20px",
          marginBottom: 12,
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: "linear-gradient(135deg,#FF6A00,#FF9142)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: "none",
          }}
        >
          <div
            style={{
              width: 12,
              height: 12,
              background: "#0d1220",
              borderRadius: 3,
            }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.25 }}>
          <span
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: "#f5f6f8",
              letterSpacing: "0.2px",
            }}
          >
            访客通行系统
          </span>
          <span style={{ fontSize: 11, color: "rgba(245,246,248,0.4)" }}>
            Visitor Access Console
          </span>
        </div>
      </div>

      {/* Nav groups */}
      <div
        style={{
          padding: "0 12px",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        {NAV_GROUPS.map((group, gi) => (
          <div key={group.title}>
            <div style={gi === 0 ? GROUP_HEAD : GROUP_HEAD_SPACED}>{group.title}</div>
            {group.items.map((item) => {
              const IconComponent = SIDEBAR_ICONS[item.iconKey];
              return (
                <NavLink
                  key={item.href}
                  to={item.href}
                  end={item.href === "/"}
                  style={({ isActive }) => navRowStyle(isActive)}
                >
                  {({ isActive }) => (
                    <>
                      <span
                        style={{
                          ...ICON_WRAP_BASE,
                          color: isActive ? "#FF9142" : "rgba(245,246,248,0.4)",
                        }}
                      >
                        <IconComponent />
                      </span>
                      <span>{item.label}</span>
                      {isActive && (
                        <span
                          style={{
                            marginLeft: "auto",
                            width: 5,
                            height: 5,
                            borderRadius: "50%",
                            background: "#FF6A00",
                          }}
                        />
                      )}
                    </>
                  )}
                </NavLink>
              );
            })}
          </div>
        ))}
      </div>

      {/* Bottom: connection health */}
      <div style={BRAND_BAR_STYLE}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: allOnline ? "#2FBF71" : "#F0455B",
            }}
          />
          <span
            style={{
              fontSize: 11.5,
              color: "rgba(245,246,248,0.45)",
            }}
          >
            {allOnline ? "全部硬件在线" : "部分硬件离线"}
          </span>
        </div>
      </div>
    </nav>
  );
}
