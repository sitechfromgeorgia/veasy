// The rubrics' scenes (tt_shorts/rubrics.py, brushes/agree.json and chapter.json): agree (what several outlets state
// alike, counted by code: „მინიმუმ N“, never which outlets) and chapter (a digest's card per story: its number of
// the total, its category, its own checked hook lines). Every motion is a function of the frame; colors are the
// brand pack's live bindings, read inside the components; the accent is only the dot. Text that reaches below
// y=1100 stays left of the rail (low()).
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fill, FONT, INK, LINE_STRONG, MUTED, RAIL_X, SIDE, W } from "../brand";
import type { Scene } from "../types";
import { Dot, fitSize, Frame, In, Kicker, useOpening, useTheme } from "../ui";

const INNER = W - 2 * SIDE; // 952
const low = (inner: number) => Math.min(inner, RAIL_X - (W - inner) / 2);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);

type P = { s: Scene; inner?: number };

type Fact = { text: string; count?: number };

/** A tick that draws itself (the stroke grows), ink; it says "stated", not who stated it. */
const Tick: React.FC<{ t: number; size: number }> = ({ t, size }) => {
  const len = 34;
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" style={{ flex: "none", display: "block" }}>
      <rect x={1.5} y={1.5} width={29} height={29} rx={8} fill="none" stroke={LINE_STRONG} strokeWidth={3} />
      <path d="M8 16.5 L14 22.5 L24.5 10" fill="none" stroke={INK} strokeWidth={4} strokeLinecap="round"
        strokeLinejoin="round" strokeDasharray={len} strokeDashoffset={len * (1 - t)} />
    </svg>
  );
};

/** agree: „მინიმუმ N“ large, a row of the counted member articles (N of them ink, the dot on the last), then each
 *  fact with a tick that draws as it comes in. No outlet is named. */
export const Agree: React.FC<P> = ({ s, inner = INNER }) => {
  const { props } = useTheme();
  const frame = useCurrentFrame();
  const tight = inner < INNER - 40;
  const width = low(inner);
  const n = Math.max(0, s.n ?? 0);
  const total = Math.max(n, s.total ?? n);
  const items = (s.items ?? []).filter((it): it is Fact => typeof it !== "string" && typeof it.text === "string").slice(0, 3);
  const big = fill(props.brand.strings.at_least ?? "{n}", { n });
  const size = fitSize([big], width, tight ? 132 : 156, 72);
  const cells = Math.min(12, total);
  const gap = 14;
  const cell = Math.min(64, (width - (cells - 1) * gap) / Math.max(1, cells));
  const lit = interpolate(frame, [10, 10 + Math.min(30, s.duration * 0.3)], [0, n], { ...clamp, easing: easeOut });
  const factSize = items.length > 2 ? (tight ? 46 : 52) : (tight ? 52 : 60);
  return (
    <Frame s={s}>
      <In delay={4}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.05, color: INK, whiteSpace: "nowrap" }}>
          {big}
        </div>
      </In>
      <div style={{ display: "flex", alignItems: "center", gap, marginTop: tight ? 24 : 32 }}>
        {Array.from({ length: cells }, (_, i) => {
          const part = Math.max(0, Math.min(1, lit - i));
          return (
            <div key={i} style={{ position: "relative", width: cell, height: cell, borderRadius: cell / 2,
              border: `3px solid ${part > 0.5 ? INK : LINE_STRONG}`, background: part > 0.5 ? INK : "transparent",
              transform: `scale(${0.8 + 0.2 * part})` }}>
              {i === n - 1 && lit >= n - 0.02 && (
                <span style={{ position: "absolute", left: cell / 2 - 10, top: cell / 2 - 10 }}><Dot size={20} /></span>
              )}
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: tight ? 40 : 56, display: "flex", flexDirection: "column", gap: tight ? 24 : 32, width }}>
        {items.map((it, i) => {
          const at = 20 + i * 10;
          const t = interpolate(frame, [at + 4, at + 16], [0, 1], { ...clamp, easing: easeOut });
          return (
            <In key={i} delay={at}>
              <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
                <Tick t={t} size={factSize} />
                <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: factSize, lineHeight: 1.2, color: INK,
                  maxWidth: width - factSize - 28 }}>{it.text}</div>
              </div>
            </In>
          );
        })}
      </div>
    </Frame>
  );
};

/** chapter: the story's number large with the total beside it, a segment per story (the done ones and this one ink,
 *  the dot on this one), its category as the kicker and its own hook lines. */
export const Chapter: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const opening = useOpening();
  const tight = inner < INNER - 40;
  const width = low(inner);
  const n = Math.max(1, s.n ?? 1), of = Math.max(n, s.of ?? n);
  const lines = s.lines ?? [];
  const numSize = tight ? 220 : 280;
  const size = fitSize(lines, width * 0.94, tight ? 104 : 120, 48);
  const grow = opening ? 1 : interpolate(frame, [6, 26], [0, 1], { ...clamp, easing: easeOut });
  const seg = (width - (of - 1) * 16) / of;
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center" }}>
      <In><Kicker text={s.kicker} /></In>
      <div style={{ display: "flex", alignItems: "baseline", gap: 24, marginTop: tight ? 24 : 40 }}>
        <In delay={2}>
          <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: numSize, lineHeight: 0.9, color: INK }}>{n}</span>
        </In>
        <In delay={6}>
          <span style={{ fontFamily: FONT, fontWeight: 600, fontSize: numSize * 0.36, lineHeight: 1, color: MUTED }}>/ {of}</span>
        </In>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: tight ? 24 : 36, width }}>
        {Array.from({ length: of }, (_, i) => {
          const on = i < n - 1 ? 1 : i === n - 1 ? grow : 0;
          return (
            <div key={i} style={{ position: "relative", width: seg, height: 12, borderRadius: 6, background: LINE_STRONG }}>
              <div style={{ position: "absolute", left: 0, top: 0, height: 12, borderRadius: 6, width: seg * on, background: INK }} />
              {i === n - 1 && (
                <span style={{ position: "absolute", left: seg * on - 14, top: -8, transform: `scale(${0.6 + 0.4 * grow})` }}>
                  <Dot size={28} pulse />
                </span>
              )}
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: tight ? 40 : 64 }}>
        {lines.map((l, i) => (
          <In key={i} delay={10 + i * 5}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.16, color: INK, whiteSpace: "nowrap" }}>
              {l}
            </div>
          </In>
        ))}
      </div>
    </div>
  );
};
