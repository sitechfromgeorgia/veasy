// The brush kit's scenes (brushes/<type>.json, tt_shorts/catalog.py): share (a 10x10 grid), rail (dated events and
// a travelling dot), compare (two squares of true proportion), link (who meets whom) and the stat's number styles
// (count, wheel, flap). Every motion is a function of the frame; colors are the brand pack's live bindings, read
// inside the components; the accent is only the dot. Text that reaches below y=1100 stays left of the rail (low()).
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { CANVAS, FONT, INK, LINE_STRONG, MUTED, PANEL, RAIL_X, RED, SIDE, W } from "../brand";
import { Mark, marked } from "../marker";
import type { Scene } from "../types";
import { Chip, CountUp, Dot, fitSize, Frame, group, In, measure, useTheme } from "../ui";
import { num } from "./more";

const INNER = W - 2 * SIDE; // 952
const low = (inner: number) => Math.min(inner, RAIL_X - (W - inner) / 2);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);
const decimalsOf = (v: number) => (String(v).split(".")[1] ?? "").length;

type P = { s: Scene; inner?: number };

/** The scene's own background (a card is the panel), for fills that sit on it. */
const useGround = () => (useTheme().v === "cards" ? PANEL : CANVAS);

// ---------------------------------------------------------------- stat: count | wheel | flap

/** One odometer digit: a window the digits roll through, settling on its own. Only the digits in view are drawn, so
 *  the settled frame holds one digit in its window (the layout probe sees nothing clipped). */
const WheelDigit: React.FC<{ to: number; t: number; spins: number; size: number }> = ({ to, t, spins, size }) => {
  const pos = (to + 10 * spins) * t;
  const base = Math.floor(pos + 1e-6);
  const frac = pos - base;
  const w = (measure("0", 700) * size) / 100;
  const digit = (k: number, y: number) => (
    <span key={k} style={{ position: "absolute", left: 0, top: y, width: w, textAlign: "center" }}>{k % 10}</span>
  );
  return (
    <span data-probe-clip style={{ position: "relative", display: "inline-block", width: w, height: size, overflow: "hidden",
      verticalAlign: "top" }}>
      {digit(base, -frac * size)}
      {frac > 0.002 && digit(base + 1, (1 - frac) * size)}
    </span>
  );
};

/** One split-flap tile: it flips through the digits from 0 to its own, each flip a top flap falling and a bottom flap
 *  landing. Ink on a quiet tile, a canvas-colored split across the middle. */
const FlapTile: React.FC<{ to: number; t: number; size: number; tile: string }> = ({ to, t, size, tile }) => {
  const steps = to + 10; // a full turn, then on to the digit: the board visibly flips even for 0
  const pos = steps * t;
  const cur = Math.min(steps, Math.floor(pos + 1e-6));
  const p = cur >= steps ? 0 : pos - cur; // the flip in progress, 0..1
  const next = (cur + 1) % 10, now = cur % 10;
  const w = Math.round(size * 0.78), h = Math.round(size * 1.24);
  const face = (d: number, half: "top" | "bottom", extra: React.CSSProperties = {}) => (
    <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
      background: tile, borderRadius: Math.round(size * 0.08), lineHeight: 1,
      clipPath: half === "top" ? "inset(0 0 50% 0)" : "inset(50% 0 0 0)", ...extra }}>{d}</span>
  );
  const flipping = p > 0.002;
  return (
    <span style={{ position: "relative", display: "inline-block", width: w, height: h, verticalAlign: "top" }}>
      {face(flipping ? next : now, "top")}
      {face(flipping && p >= 0.5 ? next : now, "bottom")}
      {flipping && p < 0.5 && face(now, "top", { transform: `perspective(${size * 6}px) rotateX(${-p * 180}deg)` })}
      {flipping && p >= 0.5 && face(next, "bottom", { transform: `perspective(${size * 6}px) rotateX(${(1 - p) * 180}deg)` })}
      <span style={{ position: "absolute", left: 0, right: 0, top: h / 2 - 2, height: 4, background: CANVAS }} />
    </span>
  );
};

/** A stat's number in its style: count (it counts up, grouped: 6 400), wheel (each digit rolls; the lower digits
 *  spin more) or flap (a split-flap board). The prefix and suffix stand still beside it. */
export const StatNumber: React.FC<{ s: Scene; value: number; delay: number; frames: number; size: number }> = (
  { s, value, delay, frames, size }) => {
  const frame = useCurrentFrame();
  const style = s.style ?? "count";
  const tile = useTheme().v === "cards" ? CANVAS : PANEL;
  if (style === "count" || !Number.isInteger(value) || value < 0) {
    return <>{s.prefix}<CountUp to={value} delay={delay} frames={frames} />{s.suffix}</>;
  }
  const chars = group(value).split("");
  const digits = chars.filter((c) => /\d/.test(c)).length;
  let k = -1;
  if (style === "wheel") {
    return (
      <>
        {s.prefix}
        {chars.map((c, i) => {
          if (!/\d/.test(c)) return <span key={i}>{c}</span>;
          k += 1;
          const right = digits - 1 - k; // digits to its right: they spin more and settle last
          const t = interpolate(frame - delay - k * 2, [0, frames + right * 3], [0, 1], { ...clamp, easing: easeOut });
          return <WheelDigit key={i} to={Number(c)} t={t} spins={Math.min(2, right)} size={size} />;
        })}
        {s.suffix}
      </>
    );
  }
  const fs = Math.round(size * 0.8);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: Math.round(fs * 0.1), fontSize: fs }}>
      {s.prefix && <span>{s.prefix}</span>}
      {chars.map((c, i) => {
        if (!/\d/.test(c)) return <span key={i} style={{ width: Math.round(fs * 0.2) }} />;
        k += 1;
        const t = interpolate(frame - delay - k * 3, [0, frames + 6], [0, 1], clamp);
        return <FlapTile key={i} to={Number(c)} t={t} size={fs} tile={tile} />;
      })}
      {s.suffix && <span>{s.suffix}</span>}
    </span>
  );
};

/** The font size a flap board of `text` fits `width` at (tiles are wider than digits). */
export const flapSize = (text: string, width: number, max: number) => {
  const n = text.replace(/\s/g, "").length, gaps = text.length - 1;
  return Math.min(max, Math.floor(width / (n * 0.78 * 0.8 + gaps * 0.1 * 0.8 + 0.2)) - 4);
};

// ---------------------------------------------------------------- share

/** A percent the articles state, as a 10x10 grid: the cells fill in reading order while the number counts up; the
 *  last cell fills only as far as the percent goes, and the dot lands in it. */
export const Share: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const value = Math.max(0, Math.min(100, s.value ?? 0));
  const width = low(inner);
  const tight = inner < INNER - 40;
  const G = tight ? 400 : 480;
  const gap = Math.round(G * 0.022);
  const cell = (G - 9 * gap) / 10;
  const span = Math.min(42, s.duration * 0.45);
  const t = interpolate(frame, [8, 8 + span], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const filled = value * t;
  const dec = decimalsOf(value);
  const numW = width - G - 40;
  const size = fitSize([`${num(value, dec)}%`], numW, tight ? 168 : 200, 72);
  const done = t > 0.98;
  const lastCell = Math.max(0, Math.ceil(value) - 1);
  return (
    <Frame s={s}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 40 }}>
        <svg width={G} height={G} style={{ flex: "none", display: "block" }}>
          {Array.from({ length: 100 }, (_, i) => {
            const x = (i % 10) * (cell + gap), y = Math.floor(i / 10) * (cell + gap);
            const part = Math.max(0, Math.min(1, filled - i));
            return (
              <g key={i}>
                <rect x={x + 1.5} y={y + 1.5} width={cell - 3} height={cell - 3} rx={4} fill="none" stroke={LINE_STRONG} strokeWidth={3} />
                {part > 0 && <rect x={x} y={y} width={cell * part} height={cell} rx={part > 0.9 ? 4 : 2} fill={INK} />}
                {done && i === lastCell && value > 0 && (
                  <circle cx={x + cell / 2} cy={y + cell / 2} r={cell * 0.26} fill={RED} />
                )}
              </g>
            );
          })}
        </svg>
        <In delay={6}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1, color: INK, whiteSpace: "nowrap",
            marginBottom: -Math.round(size * 0.08) }}>
            <Mark s={s} field="value" px={size}>{num(value * t, dec)}%</Mark>
          </div>
        </In>
      </div>
      <In delay={16}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: tight ? 52 : 60, lineHeight: 1.2, color: INK,
          marginTop: tight ? 32 : 48, maxWidth: width }}>
          {marked(s, "label", s.label, { px: tight ? 52 : 60 })}
        </div>
      </In>
    </Frame>
  );
};

// ---------------------------------------------------------------- rail

type Event = { when: string; label: string };

/** 2-4 dated events on a vertical rail. The dot travels from one event to the next; an event lights up (ink) when
 *  the dot reaches it, the rail behind the dot is ink, ahead of it a quiet line. */
export const Rail: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const ground = useGround();
  const items = (s.items ?? []).slice(0, 4).filter((it): it is Event =>
    typeof it !== "string" && typeof it.when === "string" && typeof it.label === "string");
  const n = items.length;
  if (n < 2) return null;
  const width = low(inner);
  const tight = inner < INNER - 40;
  const room = tight ? 620 : 760;
  const rowH = Math.min(room / n, tight ? 210 : 250); // two events sit close, four fill the rail
  const H_ = Math.round(rowH * n);
  const whenSize = tight ? 36 : 40;
  const labelSize = n <= 2 ? (tight ? 56 : 64) : n === 3 ? (tight ? 48 : 56) : (tight ? 42 : 48);
  const ys = items.map((_, i) => i * rowH + whenSize * 0.65);
  const first = 10, step = Math.min(30, Math.max(10, (s.duration * 0.6 - first) / (n - 1)));
  const arrive = items.map((_, i) => first + i * step);
  const pos = interpolate(frame, arrive, items.map((_, i) => i), { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const y = interpolate(pos, items.map((_, i) => i), ys, clamp);
  const reached = (i: number) => frame >= arrive[i] - 1;
  const railW = 56;
  return (
    <Frame s={s}>
      <div style={{ position: "relative", height: H_, width }}>
        <svg width={railW} height={H_} style={{ position: "absolute", left: 0, top: 0 }}>
          <line x1={28} y1={ys[0]} x2={28} y2={ys[n - 1]} stroke={LINE_STRONG} strokeWidth={6} />
          <line x1={28} y1={ys[0]} x2={28} y2={y} stroke={INK} strokeWidth={6} />
          {ys.map((yy, i) => (
            <circle key={i} cx={28} cy={yy} r={16} fill={reached(i) ? INK : ground} stroke={reached(i) ? INK : LINE_STRONG}
              strokeWidth={4} />
          ))}
          <circle cx={28} cy={y} r={22} fill={RED} />
        </svg>
        {items.map((it, i) => (
          <div key={i} style={{ position: "absolute", left: railW + 36, top: i * rowH, width: width - railW - 36 }}>
            <In delay={Math.max(0, Math.round(arrive[i] - 8))}>
              <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: whenSize, lineHeight: 1.3,
                color: reached(i) ? INK : MUTED, whiteSpace: "nowrap" }}>{marked(s, `items.${i}.when`, it.when, { px: whenSize })}</div>
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: labelSize, lineHeight: 1.2, marginTop: 8,
                color: reached(i) ? INK : MUTED }}>{marked(s, `items.${i}.label`, it.label, { px: labelSize })}</div>
            </In>
          </div>
        ))}
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- compare

type Pair2 = { label: string; value: number };

/** Two values of one unit as squares whose areas are the values (sides as square roots), side by side on one base
 *  line; the larger is ink with the dot, the smaller muted. The values count up as the squares grow. */
export const Compare: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const items = (s.items ?? []).slice(0, 2).filter((it): it is Pair2 =>
    typeof it !== "string" && typeof it.value === "number" && it.value > 0);
  if (items.length < 2) return null;
  const width = low(inner);
  const tight = inner < INNER - 40;
  const gap = 48;
  const colW = (width - gap) / 2;
  const S = Math.min(colW, tight ? 360 : 414);
  const max = Math.max(...items.map((it) => it.value));
  const big = items[0].value >= items[1].value ? 0 : 1;
  const dec = Math.max(...items.map((it) => decimalsOf(it.value)));
  const valueSize = fitSize(items.map((it) => num(it.value, dec)), colW - 8, tight ? 72 : 88, 44);
  return (
    <Frame s={s}>
      {s.unit && (
        <In delay={2}>
          <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 36, lineHeight: 1.3, color: MUTED, marginBottom: 24 }}>{s.unit}</div>
        </In>
      )}
      <div style={{ display: "flex", gap, width }}>
        {items.map((it, i) => {
          const t = interpolate(frame - (6 + i * 10), [0, 22], [0, 1], { ...clamp, easing: easeOut });
          const side = S * Math.sqrt(it.value / max);
          const ink = i === big;
          return (
            <div key={i} style={{ width: colW, flex: "none" }}>
              <div style={{ position: "relative", height: S }}>
                <div style={{ position: "absolute", left: 0, bottom: 0, width: side, height: side, borderRadius: 6,
                  background: ink ? INK : MUTED, transform: `scale(${t})`, transformOrigin: "left bottom" }} />
                {ink && t > 0.98 && <span style={{ position: "absolute", left: side - 14, bottom: side - 14 }}><Dot size={28} /></span>}
              </div>
              <div style={{ height: 4, background: LINE_STRONG, marginTop: 0 }} />
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: valueSize, lineHeight: 1.1, color: INK, marginTop: 20,
                whiteSpace: "nowrap", opacity: Math.min(1, t * 2) }}>{num(it.value * t, dec)}</div>
              <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: tight ? 36 : 40, lineHeight: 1.25, color: ink ? INK : MUTED,
                marginTop: 8, opacity: Math.min(1, t * 2) }}>{marked(s, `items.${i}.label`, it.label, { px: 40 })}</div>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- link

type Node = { name: string; role?: string };
const initials = (n: string) => n.split(/[\s-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("");

/** Who meets whom: the first person or body, an edge that draws itself down a spine with the verb on it, then whom
 *  it met (1-2), each a circle with initials (no photos) and the name and role beside it. */
export const Link: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const ground = useGround();
  const nodes = (s.items ?? []).slice(0, 3).filter((it): it is Node => typeof it !== "string" && typeof it.name === "string");
  if (nodes.length < 2) return null;
  const width = low(inner);
  const tight = inner < INNER - 40;
  const D = tight ? 136 : 160;
  const E = tight ? 170 : 200; // the edge with the verb
  const E2 = tight ? 48 : 56; // the spine on to a third
  const tops = nodes.map((_, i) => (i === 0 ? 0 : D + E + (i - 1) * (D + E2)));
  const H_ = tops[tops.length - 1] + D;
  const textW = width - D - 40;
  const nameSize = fitSize(nodes.map((it) => it.name), textW, tight ? 56 : 64, 36);
  const draw = interpolate(frame, [12, 26], [0, 1], { ...clamp, easing: easeOut });
  const more = interpolate(frame, [30, 38], [0, 1], { ...clamp, easing: easeOut });
  const x = D / 2;
  const spineEnd = tops[1] + (nodes.length > 2 ? D + (tops[2] - tops[1] - D) * more : 0);
  return (
    <Frame s={s}>
      <div style={{ position: "relative", height: H_, width }}>
        <svg width={D} height={H_} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
          <line x1={x} y1={D} x2={x} y2={D + E * draw} stroke={INK} strokeWidth={6} strokeLinecap="round" />
          {nodes.length > 2 && more > 0 && <line x1={x} y1={tops[1] + D} x2={x} y2={spineEnd} stroke={INK} strokeWidth={6} />}
        </svg>
        <div style={{ position: "absolute", left: x + 32, top: D + E / 2 - 34, opacity: draw > 0.9 ? 1 : 0,
          transform: `scale(${0.85 + 0.15 * draw})`, transformOrigin: "left center" }}>
          <Chip live size={40}>{marked(s, "edge", s.edge, { px: 40 })}</Chip>
        </div>
        {nodes.map((it, i) => (
          <div key={i} style={{ position: "absolute", left: 0, top: tops[i], width, height: D }}>
            <In delay={i === 0 ? 4 : 24 + (i - 1) * 10}>
              <div style={{ display: "flex", alignItems: "center", gap: 40, height: D }}>
                <div style={{ width: D, height: D, borderRadius: D / 2, flex: "none", display: "flex", alignItems: "center",
                  justifyContent: "center", boxSizing: "border-box", fontFamily: FONT, fontWeight: 700, fontSize: D * 0.38,
                  background: i === 0 ? INK : ground, color: i === 0 ? ground : INK,
                  border: i === 0 ? "none" : `4px solid ${LINE_STRONG}` }}>{initials(it.name)}</div>
                <div style={{ minWidth: 0, width: textW }}>
                  <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: nameSize, lineHeight: 1.2, color: INK, whiteSpace: "nowrap" }}>
                    {marked(s, `items.${i}.name`, it.name, { px: nameSize })}
                  </div>
                  {it.role && <div style={{ fontFamily: FONT, fontWeight: 400, fontSize: tight ? 36 : 40, lineHeight: 1.3, color: MUTED,
                    marginTop: 6 }}>{it.role}</div>}
                </div>
              </div>
            </In>
          </div>
        ))}
      </div>
    </Frame>
  );
};
