// Pictograms (tt_shorts/icons.py, ROADMAP C7 + D3): a sign scene, where one icon draws itself and then its verb plays,
// and the isotype count of a stat. Ink and lines only; the accent is the dot that lands when the motion is done.
import React, { useId } from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { CANVAS, FONT, INK, LINE_STRONG, MUTED, PANEL, RAIL_X, RED, SIDE, W } from "../brand";
import { GlyphAt, svgId } from "../icons";
import { marked } from "../marker";
import type { IconNode, IconMotion, Scene, Verb } from "../types";
import { Frame, In, useTheme } from "../ui";

const INNER = W - 2 * SIDE; // 952
const LOW = RAIL_X - SIDE; // the stage stays left of the like/share rail
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);

type P = { s: Scene; inner?: number };

/** The width that keeps text left of the like/share rail (x=940): inside a card the content starts 32 px further
 *  right (SIDE - 16 + the card's 48 padding = 96, not SIDE = 64), so it is 32 px narrower there. */
export const railWidth = (inner: number) => Math.min(inner, LOW) - (inner < INNER - 40 ? 32 : 0);

/** The red dot ("now"), pulsing like the other scenes' dots. */
const NowDot: React.FC<{ x: number; y: number; r: number; on: boolean }> = ({ x, y, r, on }) => {
  const frame = useCurrentFrame();
  return on ? <circle cx={x} cy={y} r={r * (1 + 0.18 * Math.sin(frame / 5))} fill={RED} /> : null;
};

/** A straight stroke that draws itself from (x1, y1) to (x2, y2), with an arrowhead once it has arrived. */
const Arrow: React.FC<{ x1: number; y1: number; x2: number; y2: number; t: number; px: number; head?: boolean }> = (
  { x1, y1, x2, y2, t, px, head = true }) => {
  const a = Math.atan2(y2 - y1, x2 - x1), h = px * 3.2;
  const wing = (s: number) => `${x2 - h * Math.cos(a + s * 0.7)} ${y2 - h * Math.sin(a + s * 0.7)}`;
  return (
    <g opacity={t > 0 ? 1 : 0}>
      <path d={`M${x1} ${y1}L${x2} ${y2}`} stroke={INK} strokeWidth={px} strokeLinecap="round" fill="none"
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - t} />
      {head && t > 0.92 && <path d={`M${wing(1)}L${x2} ${y2}L${wing(-1)}`} stroke={INK} strokeWidth={px} fill="none"
        strokeLinecap="round" strokeLinejoin="round" />}
    </g>
  );
};

/** One icon, then what happens to it: rises, falls, stops, opens, closes, moves, splits, joins. */
export const Sign: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const { v } = useTheme();
  const id = svgId(useId());
  const ground = v === "cards" ? PANEL : CANVAS;
  const nodes: IconNode[] = s.glyph ?? [];
  const verb: Verb = s.verb ?? "rises";
  const motion: IconMotion = s.motion ?? "draw";
  const morphNodes = s.morphGlyph;
  const width = railWidth(inner);
  const tight = inner < INNER - 40; // inside a card there is less height
  const H_ = tight ? 500 : 580;
  const size = tight ? 320 : 380;
  const px = size * 0.046; // the icon's stroke in pixels
  // timing in frames: the shapes draw one after another, then the verb plays; all inside the first ~65% of the scene
  const step = Math.min(6, 24 / Math.max(1, nodes.length));
  const drawEnd = 6 + (nodes.length - 1) * step + 14;
  const vFrom = drawEnd + 4, vLen = 20;
  const k = Math.min(1, (s.duration * 0.65) / (vFrom + vLen));
  const progress = (i: number) => interpolate(frame, [(6 + i * step) * k, (20 + i * step) * k], [0, 1], { ...clamp, easing: easeOut });
  const t = interpolate(frame, [vFrom * k, (vFrom + vLen) * k], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const built = progress(nodes.length - 1);
  const done = t > 0.98;
  const cx = width / 2, cy = H_ / 2;
  let ix = cx - size / 2, iy = cy - size / 2; // the icon's top-left
  let iconOpacity = 1, iconScale = 1;
  const parts: React.ReactNode[] = [];
  const morphProgress = interpolate(frame, [4 * k, drawEnd * k], [0, 1], { ...clamp, easing: easeOut });
  const glyph = (dx = 0, dy = 0, clip?: string, key = "g") => (
    <GlyphAt key={key} nodes={nodes} x={ix + dx} y={iy + dy} size={size} px={px} color={INK} progress={progress} clip={clip} id={key} motion={motion} morphNodes={morphNodes} morphProgress={morphProgress} />
  );
  let body: React.ReactNode = null;

  if (verb === "rises" || verb === "falls") {
    const up = verb === "rises", lift = tight ? 64 : 72;
    ix -= 64;
    const y0 = up ? lift / 2 : -lift / 2; // where the icon starts, relative to the middle
    const dy = y0 + (up ? -lift : lift) * t;
    const ax = ix + size + 112;
    const from = up ? cy + size / 2 + lift / 2 : cy - size / 2 - lift / 2;
    const to = up ? cy - size / 2 - lift / 2 : cy + size / 2 + lift / 2;
    const rule = up ? cy + lift / 2 + size / 2 + 24 : cy - lift / 2 - size / 2 - 24; // where it stood
    parts.push(<line key="rule" x1={ix} x2={ix + size} y1={rule} y2={rule} stroke={LINE_STRONG} strokeWidth={6} strokeLinecap="round" opacity={built} />);
    parts.push(<Arrow key="arrow" x1={ax} y1={from} x2={ax} y2={to} t={t} px={px * 0.8} />);
    parts.push(<NowDot key="dot" x={ax} y={to + (up ? -44 : 44)} r={20} on={done} />);
    body = glyph(0, dy);
  } else if (verb === "stops") {
    iconOpacity = 1 - 0.55 * t;
    const L = size * 0.62, rise = 0.7;
    const a = { x: cx - L, y: cy - L * rise }, b = { x: cx + L, y: cy + L * rise };
    const half = (p: { x: number; y: number }, key: string) => (
      <g key={key}>
        <path d={`M${p.x} ${p.y}L${cx} ${cy}`} stroke={ground} strokeWidth={px * 3.4} strokeLinecap="round" fill="none"
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - t} opacity={t > 0 ? 1 : 0} />
        <path d={`M${p.x} ${p.y}L${cx} ${cy}`} stroke={INK} strokeWidth={px * 1.7} strokeLinecap="round" fill="none"
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - t} opacity={t > 0 ? 1 : 0} />
      </g>
    );
    body = glyph();
    parts.push(half(a, "a"), half(b, "b"), <NowDot key="dot" x={cx} y={cy} r={22} on={done} />);
  } else if (verb === "opens" || verb === "closes") {
    const opening = verb === "opens";
    const f = opening ? 1 - 0.86 * t : 0.14 + 0.86 * t; // a leaf's width: 1 closed, 0.14 swung open
    const solid = opening ? 0 : 0.88 * t; // closing doors hide what is behind them
    iconOpacity = opening ? 0.55 + 0.45 * t : 1;
    iconScale = opening ? 0.94 + 0.08 * t : 1;
    const pad = 28, top = iy - pad, h = size + 2 * pad;
    const leaf = (hinge: number, side: -1 | 1) => {
      const x = side < 0 ? hinge : cx, w = Math.abs(cx - hinge);
      const hx = side < 0 ? cx - 44 : cx + 44; // the handles leave room for the dot between them
      return (
        <g key={side} transform={`translate(${hinge} 0) scale(${f} 1) translate(${-hinge} 0)`} opacity={built}>
          <rect x={x} y={top} width={w} height={h} rx={14} fill={ground} fillOpacity={solid} stroke={INK} strokeWidth={8}
            vectorEffect="non-scaling-stroke" />
          <line x1={hx} x2={hx} y1={cy - 36} y2={cy + 36} stroke={INK} strokeWidth={8} strokeLinecap="round"
            vectorEffect="non-scaling-stroke" />
        </g>
      );
    };
    body = glyph();
    parts.push(leaf(ix - pad, -1), leaf(ix + size + pad, 1));
    parts.push(<NowDot key="dot" x={cx} y={opening ? top - 44 : cy} r={20} on={done} />);
  } else if (verb === "moves") {
    const shift = Math.max(80, (width - size) / 2 - 56);
    const dx = -shift + 2 * shift * t;
    const left = ix + dx, sway = Math.sin(Math.PI * t);
    [[-0.26, 90], [0, 150], [0.26, 90]].forEach(([fy, len], i) => {
      const y = cy + fy * size;
      parts.push(<line key={`w${i}`} x1={left - 36 - len} x2={left - 36} y1={y} y2={y} stroke={MUTED} strokeWidth={8}
        strokeLinecap="round" opacity={sway} />);
    });
    const ay = cy + size / 2 + 52;
    parts.push(<Arrow key="arrow" x1={cx - shift} y1={ay} x2={cx + shift} y2={ay} t={t} px={px * 0.7} />);
    parts.push(<NowDot key="dot" x={cx + shift + 44} y={ay} r={20} on={done} />);
    body = glyph(dx);
  } else {
    // splits: the halves move apart along a crack; joins: they come together and the crack closes
    const apart = (verb === "splits" ? t : 1 - t) * (tight ? 60 : 72);
    body = (
      <g key="halves">
        <defs>
          <clipPath id={`${id}l`}><rect x={-4} y={-4} width={16} height={32} /></clipPath>
          <clipPath id={`${id}r`}><rect x={12} y={-4} width={16} height={32} /></clipPath>
        </defs>
        {glyph(-apart, 0, `${id}l`, "l")}
        {glyph(apart, 0, `${id}r`, "r")}
      </g>
    );
    const crack = verb === "splits" ? t : (1 - t) * built;
    parts.push(<line key="crack" x1={cx} x2={cx} y1={iy - 24} y2={iy + size + 24} stroke={MUTED} strokeWidth={6}
      strokeDasharray="14 18" strokeLinecap="round" opacity={crack} />);
    parts.push(<NowDot key="dot" x={cx} y={iy - 56} r={20} on={done} />);
  }

  return (
    <Frame s={s}>
      <svg width={width} height={H_} style={{ overflow: "visible", flex: "none", display: "block" }}>
        <g opacity={iconOpacity} transform={`translate(${cx} ${cy}) scale(${iconScale}) translate(${-cx} ${-cy})`}>{body}</g>
        {parts}
      </svg>
      {s.label && (
        <In delay={Math.round(vFrom * k)}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: (tight ? 52 : 60) - (s.label.length > 44 ? 8 : 0),
            lineHeight: 1.2, color: INK, marginTop: tight ? 16 : 24, maxWidth: width }}>{marked(s, "label", s.label, { px: 56 })}</div>
        </In>
      )}
    </Frame>
  );
};

// ---------------------------------------------------------------- isotype

/** Frames the stat's count takes: the icons and the number arrive together, over a little under half the scene. */
export const isoSpan = (duration: number) => Math.max(18, Math.min(60, Math.round(duration * 0.45)));

/** The columns that give the largest icon for n of them in a width x height box. */
const grid = (n: number, width: number, height: number) => {
  let best = { cols: n, rows: 1, cell: 0 };
  for (let cols = 1; cols <= n; cols++) {
    const rows = Math.ceil(n / cols);
    const cell = Math.min(width / cols, height / rows);
    if (cell > best.cell + 0.5) best = { cols, rows, cell };
  }
  return best;
};

/** A stat's value as that many icons (2-30 whole things, tt_shorts/icons.isotype), one by one as the number counts up
 *  (the same easing and frames as its CountUp, so the count and the icons agree on every frame). */
export const Isotype: React.FC<{ s: Scene; width: number; height: number; delay: number; span: number }> = (
  { s, width, height, delay, span }) => {
  const frame = useCurrentFrame();
  const nodes = s.glyph ?? [];
  const n = Math.round(s.value ?? 0);
  const total = s.total ? Math.round(s.total) : n;
  const maxUnits = Math.max(n, total);
  const motion: IconMotion = s.motion ?? "count";
  const { cols, rows, cell } = grid(maxUnits, width, height);
  const size = Math.min(cell * 0.8, 200);
  const px = Math.max(5, size * 0.07);
  const inv = (y: number) => 1 - Math.cbrt(1 - y); // the frame at which CountUp (cubic out) reaches y
  const shown = (i: number) => interpolate(frame, [delay + span * inv((Math.min(i, n - 1) + 0.5) / Math.max(1, n)), delay + span * inv((Math.min(i, n - 1) + 0.5) / Math.max(1, n)) + 8],
    [0, 1], { ...clamp, easing: easeOut });
  const last = shown(Math.max(0, n - 1)) > 0.98;
  return (
    <svg width={cols * cell} height={rows * cell} style={{ display: "block", flex: "none", marginTop: 40, overflow: "visible" }}>
      {Array.from({ length: maxUnits }, (_, i) => {
        const isLit = i < n;
        const p = isLit ? shown(i) : 1;
        const x = (i % cols) * cell + (cell - size) / 2, y = Math.floor(i / cols) * cell + (cell - size) / 2;
        const sc = isLit ? 0.7 + 0.3 * p : 0.85;
        const color = isLit ? INK : LINE_STRONG;
        return (
          <g key={i} opacity={isLit ? (p > 0 ? 1 : 0) : 0.35} transform={`translate(${x + size / 2} ${y + size / 2}) scale(${sc}) translate(${-x - size / 2} ${-y - size / 2})`}>
            <GlyphAt nodes={nodes} x={x} y={y} size={size} px={px} color={color} progress={() => p} motion={isLit ? motion : "draw"} id={`c${i}`} />
          </g>
        );
      })}
      <NowDot x={((Math.max(0, n - 1)) % cols) * cell + (cell + size) / 2} y={Math.floor((Math.max(0, n - 1)) / cols) * cell + (cell + size) / 2}
        r={Math.max(10, size * 0.09)} on={last} />
    </svg>
  );
};

/** Standalone pictogram unit chart for scenes displaying proportional quantities. */
export const UnitChart: React.FC<{
  nodes: IconNode[];
  value: number;
  total?: number;
  width: number;
  height: number;
  motion?: IconMotion;
  label?: string;
}> = ({ nodes, value, total, width, height, motion = "count", label }) => {
  const frame = useCurrentFrame();
  const n = Math.max(1, Math.round(value));
  const maxUnits = total ? Math.max(n, Math.round(total)) : n;
  const { cols, rows, cell } = grid(maxUnits, width, height);
  const size = Math.min(cell * 0.8, 160);
  const px = Math.max(4, size * 0.07);
  const shown = (i: number) => interpolate(frame, [6 + i * 2, 14 + i * 2], [0, 1], { ...clamp, easing: easeOut });

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <svg width={cols * cell} height={rows * cell} style={{ display: "block", overflow: "visible" }}>
        {Array.from({ length: maxUnits }, (_, i) => {
          const isLit = i < n;
          const p = shown(i);
          const x = (i % cols) * cell + (cell - size) / 2;
          const y = Math.floor(i / cols) * cell + (cell - size) / 2;
          const color = isLit ? INK : LINE_STRONG;
          return (
            <g key={i} opacity={isLit ? (p > 0 ? 1 : 0) : 0.35}>
              <GlyphAt nodes={nodes} x={x} y={y} size={size} px={px} color={color} progress={() => (isLit ? p : 1)} motion={isLit ? motion : "draw"} id={`u${i}`} />
            </g>
          );
        })}
      </svg>
      {label && (
        <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 32, color: MUTED, marginTop: 16 }}>
          {label}
        </div>
      )}
    </div>
  );
};
