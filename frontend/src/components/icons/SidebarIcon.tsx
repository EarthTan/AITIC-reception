// Stroke-only monochrome sidebar icons. The icons intentionally inherit
// currentColor so callers control the hue via the wrapping span's `color`
// style (active vs inactive).

interface IconProps {
  size?: number;
}

const COMMON = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
} as const;

export function DashboardIcon(_: IconProps = {}) {
  return (
    <svg {...COMMON}>
      <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth={1.4} />
      <rect x="9" y="1.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth={1.4} />
      <rect x="1.5" y="9" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth={1.4} />
      <rect x="9" y="9" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth={1.4} />
    </svg>
  );
}

export function RegistrationIcon() {
  return (
    <svg {...COMMON}>
      <rect x="2" y="1.5" width="12" height="13" rx="1.5" stroke="currentColor" strokeWidth={1.4} />
      <line x1="4.5" y1="5" x2="11.5" y2="5" stroke="currentColor" strokeWidth={1.3} />
      <line x1="4.5" y1="8" x2="11.5" y2="8" stroke="currentColor" strokeWidth={1.3} />
      <line x1="4.5" y1="11" x2="8.5" y2="11" stroke="currentColor" strokeWidth={1.3} />
    </svg>
  );
}

export function SummaryIcon() {
  return (
    <svg {...COMMON}>
      <rect x="2" y="9" width="3" height="5" rx="0.8" stroke="currentColor" strokeWidth={1.4} />
      <rect x="6.5" y="5.5" width="3" height="8.5" rx="0.8" stroke="currentColor" strokeWidth={1.4} />
      <rect x="11" y="2" width="3" height="12" rx="0.8" stroke="currentColor" strokeWidth={1.4} />
    </svg>
  );
}

export function LiveBoardIcon() {
  return (
    <svg {...COMMON}>
      <rect x="1.5" y="2.5" width="13" height="8.5" rx="1.3" stroke="currentColor" strokeWidth={1.4} />
      <line x1="5.5" y1="14" x2="10.5" y2="14" stroke="currentColor" strokeWidth={1.3} />
      <line x1="8" y1="11" x2="8" y2="14" stroke="currentColor" strokeWidth={1.3} />
      <circle cx="8" cy="6.7" r="1.5" stroke="currentColor" strokeWidth={1.3} />
    </svg>
  );
}

export function CardsIcon() {
  return (
    <svg {...COMMON}>
      <rect x="1.5" y="3.5" width="13" height="9" rx="1.4" stroke="currentColor" strokeWidth={1.4} />
      <rect x="3.3" y="5.3" width="3.2" height="2.6" rx="0.6" stroke="currentColor" strokeWidth={1.2} />
      <line x1="3.3" y1="10.3" x2="9" y2="10.3" stroke="currentColor" strokeWidth={1.2} />
    </svg>
  );
}

export function TemplatesIcon() {
  return (
    <svg {...COMMON}>
      <path
        d="M2 3.5C2 2.67 2.67 2 3.5 2h9C13.33 2 14 2.67 14 3.5v6c0 .83-.67 1.5-1.5 1.5H6l-3 3v-3H3.5C2.67 11 2 10.33 2 9.5v-6z"
        stroke="currentColor"
        strokeWidth={1.4}
        fill="none"
      />
    </svg>
  );
}

export function WorkLogIcon() {
  return (
    <svg {...COMMON}>
      <circle cx="8" cy="8" r="6.2" stroke="currentColor" strokeWidth={1.4} />
      <line x1="8" y1="8" x2="8" y2="4.5" stroke="currentColor" strokeWidth={1.3} />
      <line x1="8" y1="8" x2="10.6" y2="9.4" stroke="currentColor" strokeWidth={1.3} />
    </svg>
  );
}

export function SettingsIcon() {
  return (
    <svg {...COMMON}>
      <line x1="2" y1="4.5" x2="14" y2="4.5" stroke="currentColor" strokeWidth={1.4} />
      <circle cx="6" cy="4.5" r="1.6" fill="#0d1220" stroke="currentColor" strokeWidth={1.4} />
      <line x1="2" y1="8" x2="14" y2="8" stroke="currentColor" strokeWidth={1.4} />
      <circle cx="10.5" cy="8" r="1.6" fill="#0d1220" stroke="currentColor" strokeWidth={1.4} />
      <line x1="2" y1="11.5" x2="14" y2="11.5" stroke="currentColor" strokeWidth={1.4} />
      <circle cx="5" cy="11.5" r="1.6" fill="#0d1220" stroke="currentColor" strokeWidth={1.4} />
    </svg>
  );
}

import type { ReactNode } from "react";

export const SIDEBAR_ICONS: Record<string, () => ReactNode> = {
  dashboard: DashboardIcon,
  registration: RegistrationIcon,
  summary: SummaryIcon,
  liveboard: LiveBoardIcon,
  cards: CardsIcon,
  templates: TemplatesIcon,
  worklog: WorkLogIcon,
  settings: SettingsIcon,
};
