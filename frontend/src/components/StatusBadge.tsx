// Pill-style badge with left coloured dot + label. One of 5 tones.
// Mirrors StatusBadge.dc.html — the most-reused component in the design.

import type { CSSProperties } from "react";
import {
  TONE_BG,
  TONE_BORDER,
  TONE_DOT,
  TONE_FG,
  type Tone,
} from "../lib/design";

const BADGE_STYLE: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "3px 10px 3px 8px",
  borderRadius: 100,
  fontSize: 12,
  fontWeight: 600,
  whiteSpace: "nowrap",
};

const DOT_STYLE: CSSProperties = {
  width: 6,
  height: 6,
  borderRadius: "50%",
  flex: "none",
};

interface Props {
  label: string;
  tone?: Tone;
}

export function StatusBadge({ label, tone = "neutral" }: Props) {
  return (
    <span
      style={{
        ...BADGE_STYLE,
        color: TONE_FG[tone],
        background: TONE_BG[tone],
        border: `1px solid ${TONE_BORDER[tone]}`,
      }}
    >
      <span style={{ ...DOT_STYLE, background: TONE_DOT[tone] }} />
      {label}
    </span>
  );
}
