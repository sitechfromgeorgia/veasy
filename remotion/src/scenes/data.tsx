// Data-visualisation scenes added for the visual-data kit: chart (vertical bars from a zero line), sparkline (one
// series over time, the last point on "now") and gauge (a percent as a ring). Every motion is a function of the
// frame; colors are the brand pack's live bindings, read inside the components; the accent is only the dot. Text
// that reaches below y=1100 stays left of the rail (low()).
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT, INK, LINE_STRONG, MUTED, RAIL_X, RED, SIDE, W } from "../brand";
import { Mark, marked } from "../marker";
import type { Scene } from "../types";
import { beat, Dot, fitSize, Frame, In, measure } from "../ui";
import { num } from "./more";

const INNER = W - 2 * SIDE; // 952
const low = (inner: number) => Math.min(inner, RAIL_X - (W - inner) / 2);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);
const decimalsOf = (v: number) => (String(v).split(".")[1] ?? "").length;

type P = { s: Scene; inner?: number };

/** A text wrapped at its spaces as the browser would, for a column `width` wide at `size`. */
const wrap = (text: string, width: number, size: number) => {
  const space = (measure(" ", 600) * size) / 100;
  const lines: string[] = [];
  let line = "";
  for (const w of text.split(/\s+/).filter(Boolean)) {
    const next = line ? line + " " + w : w;
    if (line && (measure(next, 600) * size) / 100 > width) { lines.push(line); line = w; } else line = next;
  }
  if (line) lines.push(line);
  return lines;
};

/** The largest size (<= max, a multiple of 2) at which every label wraps into at most two lines in its column and
 *  no single word has to break: Georgian words are long, and a word split in half reads as a typo. */
const labelSize = (labels: string[], width: number, max: number, min = 24) => {
  for (let size = max - (max % 2); size >= min; size -= 2) {
    const fits = labels.every((l) => wrap(l, width, size).every((line) =>
      line.split(/\s+/).every((w) => (measure(w, 600) * size) / 100 <= width)));
    if (fits && labels.every((l) => wrap(l, width, size).length <= 2)) return size;
  }
  return min;
};

// ---------------------------------------------------------------- chart

type Bar = { label: string; value: number };

/** 2-6 values of one unit as bars growing from a zero line, one after another; the largest is ink with the dot,
 *  the rest muted. Each value counts up over its own bar and `unit` follows it; labels sit under the baseline. */
export const Chart: React.FC<P> = ({ s, inner = INNER }) => {
  const items = (s.items ?? []).filter((it): it is Bar =>
    typeof it !== "string" && typeof it.label === "string" && typeof it.value === "number").slice(0, 6);
  const frame = useCurrentFrame();
  if (!items.length) return null;
  const width = low(inner);
  const tight = inner < INNER - 40;
  const n = items.length;
  const gap = n > 4 ? 20 : 32;
  const colW = (width - gap * (n - 1)) / n;
  const barW = Math.min(colW, tight ? 120 : 144);
  const dec = Math.max(...items.map((it) => decimalsOf(it.value)));
  const top = items.reduce((a, it, i) => (it.value > items[a].value ? i : a), 0);
  const max = Math.max(...items.map((it) => it.value), 1);
  const unit = s.unit ? ` ${s.unit}` : "";
  const widest = items.map((it) => num(it.value, dec)).reduce((a, b) => (measure(b, 700) > measure(a, 700) ? b : a), "");
  // the number and its unit share the column when they can; the unit drops under the number when they can't, and
  // nothing goes under 24 px (probe.py: scene text is at least 24 px and never runs past its box)
  const numW = (size: number) => (measure(widest, 700) * size) / 100;
  const unitW = (size: number) => (s.unit ? (measure(unit, 600) * size * 0.55) / 100 : 0);
  let valueSize = tight ? 46 : 54;
  while (valueSize > 24 && numW(valueSize) + unitW(valueSize) > colW - 16) valueSize -= 2;
  const stacked = Boolean(s.unit) && numW(valueSize) + unitW(valueSize) > colW - 16;
  while (valueSize > 24 && stacked && numW(valueSize) > colW - 16) valueSize -= 2;
  const unitSize = Math.max(24, Math.round(valueSize * 0.6));
  const nameSize = labelSize(items.map((it) => it.label), colW - 12, tight ? 34 : 38);
  const height = tight ? 380 : 470;
  const head = valueSize + 28 + (stacked ? unitSize + 4 : 0); // the room a value needs above the tallest bar
  // one bar after another, ten frames apart (sfx.py's CHART_STEP blips at the same moments)
  const starts = items.map((_, i) => beat(s, `items.${i}`) ?? 6 + i * 10);
  return (
    <Frame s={s}>
      <div style={{ width }}>
        <div style={{ position: "relative", height }}>
          {items.map((it, i) => {
            const t = interpolate(frame - starts[i], [0, 20], [0, 1], { ...clamp, easing: easeOut });
            const h = Math.max(0, (height - head) * (it.value / max) * t);
            const ink = i === top;
            return (
              <div key={i} style={{ position: "absolute", left: i * (colW + gap), bottom: 0, width: colW, height: "100%" }}>
                <div style={{ position: "absolute", left: (colW - barW) / 2, bottom: 0, width: barW, height: h,
                  background: ink ? INK : MUTED, borderRadius: 6 }} />
                <div style={{ position: "absolute", left: -8, width: colW + 16, bottom: h + 12, textAlign: "center",
                  fontFamily: FONT, fontWeight: 700, fontSize: valueSize, lineHeight: 1, color: INK, whiteSpace: "nowrap",
                  opacity: Math.min(1, t * 2.5) }}>
                  {stacked ? (
                    <>
                      <div>{num(it.value * t, dec)}</div>
                      <div style={{ fontSize: unitSize, fontWeight: 600, color: MUTED, lineHeight: 1.2, marginTop: 4 }}>{s.unit}</div>
                    </>
                  ) : (
                    <div>
                      {num(it.value * t, dec)}
                      {s.unit && <span style={{ fontSize: unitSize, fontWeight: 600, color: MUTED, marginLeft: 6 }}>{s.unit}</span>}
                    </div>
                  )}
                </div>
                {ink && t > 0.98 && (
                  <span style={{ position: "absolute", left: (colW + barW) / 2 - 12, bottom: h - 12 }}><Dot size={24} /></span>
                )}
              </div>
            );
          })}
        </div>
        <div style={{ height: 4, background: LINE_STRONG }} />
        <div style={{ display: "flex", gap, marginTop: 20 }}>
          {items.map((it, i) => (
            <div key={i} style={{ width: colW, flex: "none", fontFamily: FONT, fontWeight: 600, fontSize: nameSize,
              lineHeight: 1.25, color: i === top ? INK : MUTED, textAlign: "center", overflowWrap: "anywhere" }}>
              {wrap(it.label, colW - 8, nameSize).map((line, k) => <div key={k}>{line}</div>)}
            </div>
          ))}
        </div>
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- sparkline

/** One series over time (6-24 points the articles state) as a line that draws itself left to right; the last
 *  point is the dot, with its value above it. `delta` is the change an article states, drawn with an arrow. */
export const Sparkline: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const values = (s.values ?? []).filter((v) => typeof v === "number" && Number.isFinite(v)).slice(0, 24);
  const width = low(inner);
  if (values.length < 2) return null;
  const tight = inner < INNER - 40;
  const height = tight ? 330 : 410;
  const padT = 88, padB = 40, padX = 12; // above the line: the last value's room
  const lo = Math.min(...values), hi = Math.max(...values);
  const span = hi - lo || Math.abs(hi) || 1;
  const last = values.length - 1;
  const x = (i: number) => padX + (i * (width - 2 * padX)) / last;
  const y = (v: number) => padT + (1 - (v - lo) / span) * (height - padT - padB);
  const d = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const run = interpolate(frame, [8, 8 + Math.min(60, Math.max(24, s.duration * 0.45))], [0, 1],
    { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const dec = Math.max(...values.map(decimalsOf));
  const delta = s.delta;
  const deltaText = typeof delta === "number" && Number.isFinite(delta)
    ? `${delta > 0 ? "+" : ""}${num(delta, decimalsOf(delta))}` : null;
  const deltaSize = deltaText ? fitSize([deltaText], width - 88, tight ? 84 : 96, 52) : 0;
  const arrow = tight ? 40 : 48;
  return (
    <Frame s={s}>
      {(deltaText || s.label) && (
        <In delay={2}>
          <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: s.label ? 16 : 28 }}>
            {deltaText && (
              <>
                <svg width={arrow} height={arrow} viewBox="0 0 48 48" style={{ flex: "none",
                  transform: delta! < 0 ? "rotate(180deg)" : undefined }}>
                  <path d="M24 40V10 M10 24L24 10L38 24" fill="none" stroke={INK} strokeWidth={6} strokeLinecap="round"
                    strokeLinejoin="round" />
                </svg>
                <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: deltaSize, lineHeight: 1, color: INK,
                  whiteSpace: "nowrap" }}>{deltaText}</span>
              </>
            )}
            {!deltaText && s.label && (
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: fitSize([s.label], width, 56, 36), lineHeight: 1.2,
                color: INK, maxWidth: width }}>{marked(s, "label", s.label, { px: 56 })}</div>
            )}
          </div>
        </In>
      )}
      {deltaText && s.label && (
        <In delay={8}>
          <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 40, lineHeight: 1.25, color: MUTED, marginTop: -8,
            marginBottom: 24, maxWidth: width }}>{marked(s, "label", s.label, { px: 40 })}</div>
        </In>
      )}
      <In delay={4}>
        <svg width={width} height={height} style={{ overflow: "visible", display: "block", flex: "none" }}>
          {lo < 0 && hi > 0 && (
            <line x1={0} x2={width} y1={y(0)} y2={y(0)} stroke={LINE_STRONG} strokeWidth={2} />
          )}
          <path d={d} fill="none" stroke={INK} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round"
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - run} />
          {run > 0.995 && <circle cx={x(last)} cy={y(values[last])} r={20} fill={RED} />}
          {run > 0.9 && (
            <text x={width - padX} y={y(values[last]) - 36} textAnchor="end" fontFamily={FONT} fontWeight={700}
              fontSize={52} fill={INK}>{num(values[last], dec)}</text>
          )}
        </svg>
      </In>
    </Frame>
  );
};

// ---------------------------------------------------------------- gauge

/** A percent of a whole (0-100) as a ring: the track is a quiet line, the arc eases in from the top clockwise and
 *  ends on the dot; the value counts up in the centre with its suffix, the label sits under the ring. */
export const Gauge: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const value = Math.max(0, Math.min(100, s.value ?? 0));
  const width = low(inner);
  const tight = inner < INNER - 40;
  const D = Math.min(width, tight ? 440 : 520);
  const stroke = tight ? 32 : 40;
  const r = (D - stroke) / 2;
  const c = 2 * Math.PI * r;
  const span = Math.min(54, Math.max(26, s.duration * 0.45));
  const t = interpolate(frame, [8, 8 + span], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const dec = decimalsOf(value);
  const suffix = s.suffix ?? "%";
  const size = fitSize([`${num(value, dec)}${suffix}`], D - stroke * 2 - 48, tight ? 128 : 152, 64);
  const cx = D / 2, cy = D / 2;
  const head = -Math.PI / 2 + (2 * Math.PI * Math.min(100, value * t)) / 100;
  return (
    <Frame s={s}>
      <div style={{ position: "relative", width: D, height: D }}>
        <svg width={D} height={D} style={{ display: "block" }}>
          <circle cx={cx} cy={cy} r={r} fill="none" stroke={LINE_STRONG} strokeWidth={stroke} />
          {value > 0 && t > 0.02 && (
            <circle cx={cx} cy={cy} r={r} fill="none" stroke={INK} strokeWidth={stroke} strokeLinecap="round"
              strokeDasharray={c} strokeDashoffset={c * (1 - (value * t) / 100)} transform={`rotate(-90 ${cx} ${cy})`} />
          )}
          {value > 0 && t > 0.5 && (
            <circle cx={cx + r * Math.cos(head)} cy={cy + r * Math.sin(head)} r={stroke * 0.42} fill={RED} />
          )}
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, fontFamily: FONT }}>
            <span style={{ fontWeight: 700, fontSize: size, lineHeight: 1, color: INK, whiteSpace: "nowrap" }}>
              <Mark s={s} field="value" px={size}>{num(value * t, dec)}</Mark>
            </span>
            <span style={{ fontWeight: 600, fontSize: Math.round(size * 0.42), lineHeight: 1, color: MUTED }}>{suffix}</span>
          </div>
        </div>
      </div>
      <In delay={Math.round(8 + span * 0.5)}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: tight ? 48 : 56, lineHeight: 1.2, color: INK,
          textAlign: "center", marginTop: 40, maxWidth: width, marginLeft: "auto", marginRight: "auto" }}>
          {marked(s, "label", s.label, { px: tight ? 48 : 56 })}
        </div>
      </In>
    </Frame>
  );
};
