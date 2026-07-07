// Centralised design tokens & helpers shared across pages/components.
// Keeping these in one place means a brand tweak touches a single file.
// Component-local layout values (padding, gap, etc.) stay inline at the call
// site because every layout is bespoke and not worth extracting.

import type {
  AdapterHealthStatus,
  IdentityType,
  LogModule,
  LogStatus,
  TemplateIdentityType,
  VerifyResult,
  VisitStatus,
  WriteStatus,
} from "../api/types";

export const COLORS = {
  brand: "#ff6a00",
  brandSoft: "#ff9142",
  brandGrad: "linear-gradient(135deg,#ff6a00,#ff8a2e)",
  brandBorder: "rgba(255,106,0,0.4)",
  successDot: "#2fbf71",
  warningDot: "#f5a623",
  dangerDot: "#f0455b",
  greenGradSoft: "linear-gradient(160deg,#132416,#0f1e13)",
  orangeGradBar: "linear-gradient(180deg,#ff6a00,#ff9142)",
  todayGradCard: "linear-gradient(160deg,#171216,#1a1310)",
  todayGradPass:
    "linear-gradient(160deg,#132416,#0f1e13)",
  passedBorder: "rgba(47,191,113,0.3)",
} as const;

// Five StatusBadge tones — keep in lock-step with src/components/StatusBadge.tsx
export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

export const TONE_FG: Record<Tone, string> = {
  success: "#4fd68d",
  warning: "#f7bb4e",
  danger: "#f97a8b",
  info: "#6ea3ff",
  neutral: "rgba(245,246,248,0.6)",
};
export const TONE_BG: Record<Tone, string> = {
  success: "rgba(47,191,113,0.14)",
  warning: "rgba(245,166,35,0.14)",
  danger: "rgba(240,69,91,0.14)",
  info: "rgba(76,141,255,0.14)",
  neutral: "rgba(245,246,248,0.08)",
};
export const TONE_BORDER: Record<Tone, string> = {
  success: "rgba(47,191,113,0.3)",
  warning: "rgba(245,166,35,0.3)",
  danger: "rgba(240,69,91,0.3)",
  info: "rgba(76,141,255,0.3)",
  neutral: "rgba(245,246,248,0.16)",
};
export const TONE_DOT: Record<Tone, string> = {
  success: "#2fbf71",
  warning: "#f5a623",
  danger: "#f0455b",
  info: "#4c8dff",
  neutral: "rgba(245,246,248,0.6)",
};

// ---------------- Visit status ----------------
export const VISIT_LABELS: Record<VisitStatus, string> = {
  pending: "待登记",
  welcome_ready: "待写卡",
  card_written: "已写卡",
  verified: "已入场",
  rejected: "已拒绝",
};
export const VISIT_TONES: Record<VisitStatus, Tone> = {
  pending: "neutral",
  welcome_ready: "warning",
  card_written: "info",
  verified: "success",
  rejected: "danger",
};

// ---------------- Adapter health ----------------
export const ADAPTER_LABELS: Record<AdapterHealthStatus, string> = {
  online: "在线",
  offline: "离线",
  error: "异常",
};
export const ADAPTER_TONES: Record<AdapterHealthStatus, Tone> = {
  online: "success",
  offline: "danger",
  error: "warning",
};
export const ADAPTER_DOTS: Record<AdapterHealthStatus, string> = {
  online: COLORS.successDot,
  offline: COLORS.dangerDot,
  error: COLORS.warningDot,
};
// The four adapter names — same order as in the design prototype.
export const ADAPTER_DISPLAY: { key: string; name: string }[] = [
  { key: "nfc", name: "NFC 读卡器" },
  { key: "led", name: "LED 显示屏" },
  { key: "tts", name: "语音播报" },
  { key: "ai", name: "AI 欢迎词" },
];

// ---------------- Card write status ----------------
export const WRITE_LABELS: Record<WriteStatus, string> = {
  success: "成功",
  failed: "失败",
  pending: "待写卡",
};
export const WRITE_TONES: Record<WriteStatus, Tone> = {
  success: "success",
  failed: "danger",
  pending: "warning",
};

// ---------------- Verify result ----------------
export const VERIFY_LABELS: Record<VerifyResult, string> = {
  pass: "验证通过",
  fail: "验证失败",
};
export const VERIFY_TONES: Record<VerifyResult, Tone> = {
  pass: "success",
  fail: "danger",
};

// ---------------- Worklog ----------------
export const LOG_MODULE_LABELS: Record<LogModule | "", string> = {
  "": "全部模块",
  registration: "访客登记",
  ai_writeup: "AI 欢迎词生成",
  card_write: "写卡",
  verify: "现场验证",
  led: "LED 显示",
  tts: "语音播报",
  system: "系统",
};
export const LOG_STATUS_LABELS: Record<LogStatus | "", string> = {
  "": "全部状态",
  success: "成功",
  failure: "失败",
  warning: "警告",
};
export const LOG_STATUS_TONES: Record<LogStatus, Tone> = {
  success: "success",
  failure: "danger",
  warning: "warning",
};

// ---------------- Identity types ----------------
// Order used by both the TemplatesPage list and the file preview.
export const IDENTITY_TYPES: IdentityType[] = [
  "企业领导",
  "企业员工",
  "学校老师",
  "大学生",
  "中小学生",
  "政府官员",
];
export const TEMPLATE_IDENTITY_TYPES: TemplateIdentityType[] = [
  ...IDENTITY_TYPES,
  "默认",
];

// ---------------- Sidebar ----------------
export interface NavItem {
  href: string;
  label: string;
  iconKey: string;
}
export const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "概览",
    items: [{ href: "/", label: "仪表盘", iconKey: "dashboard" }],
  },
  {
    title: "现场作业",
    items: [
      { href: "/registration", label: "访客登记", iconKey: "registration" },
      { href: "/summary", label: "汇总总表", iconKey: "summary" },
      { href: "/live-board", label: "现场实时看板", iconKey: "liveboard" },
      { href: "/cards", label: "写卡管理", iconKey: "cards" },
    ],
  },
  {
    title: "配置",
    items: [
      { href: "/templates", label: "欢迎词模板", iconKey: "templates" },
      { href: "/work-logs", label: "工作日志", iconKey: "worklog" },
      { href: "/settings", label: "系统设置", iconKey: "settings" },
    ],
  },
];

// Format a Date (or ISO string) as HH:MM:SS — used for "last heartbeat".
export function formatTime(d: Date | string): string {
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toTimeString().slice(0, 8);
}

// Format as YYYY-MM-DD (matches the API's visit_date shape).
export function formatDate(d: Date | string): string {
  const date = typeof d === "string" ? new Date(d) : d;
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// Format an ISO timestamp into "MM-DD HH:MM" — used in tables/lists where the
// full iso string is too long for a row cell.
export function formatDateShort(d: Date | string): string {
  const date = typeof d === "string" ? new Date(d) : d;
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${m}-${day}`;
}

export function formatTimeShort(d: Date | string): string {
  const date = typeof d === "string" ? new Date(d) : d;
  return `${String(date.getHours()).padStart(2, "0")}:${String(
    date.getMinutes(),
  ).padStart(2, "0")}`;
}

// Today as a full Chinese date string for display-page heading.
export function formatChineseDate(d: Date = new Date()): string {
  const weekdays = ["日", "一", "二", "三", "四", "五", "六"];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 · 星期${weekdays[d.getDay()]}`;
}
