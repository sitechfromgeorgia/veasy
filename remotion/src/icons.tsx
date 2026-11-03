// Icons (tt_shorts/icons.py): Lucide stroke shapes on a 24 px grid, drawn in the brand pack's colors.
// Frame-exact, deterministic micro-motion vocabulary: draw, pop, pulse, count, morph, sketch.
// The accent never colors an icon's stroke or fill: accent is only for the dot.
import React from "react";
import type { IconNode, IconMotion } from "./types";

/** Interpolate helper for frame-exact, deterministic easing in local 0..1 space. */
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

/** Snappy overshoot spring simulation (0 -> 1.16 -> 1.0) for "pop" motion. */
export const popScale = (t: number) => {
  const p = clamp01(t);
  if (p <= 0) return 0;
  if (p >= 1) return 1;
  // Cubic overshoot curve
  if (p < 0.65) {
    const u = p / 0.65;
    return 1.18 * (u * u * (3 - 2 * u));
  }
  const u = (p - 0.65) / 0.35;
  return 1.18 - 0.18 * (u * (2 - u));
};

/** Subtle heartbeat pulse (1.0 -> 1.08 -> 1.0) for "pulse" motion. */
export const pulseScale = (t: number, cycles = 2) => {
  const p = clamp01(t);
  if (p <= 0) return 0;
  if (p >= 1) return 1;
  const decay = 1 - 0.7 * p;
  return 1 + 0.09 * Math.sin(p * Math.PI * 2 * cycles) * decay;
};

/** An icon's shapes in its own 24-unit space. `width` is the stroke in those units; `progress(i)` draws shape i
 *  (0: hidden, 1: whole). Supports motion personalities: draw, pop, pulse, count, morph, sketch. */
export const glyphShapes = (
  nodes: IconNode[],
  stroke: string,
  width: number,
  progress?: (i: number) => number,
  key = "g",
  motion: IconMotion = "draw"
) => {
  return nodes.map(([tag, attrs], i) => {
    const t = progress ? progress(i) : 1;
    const dot = tag === "circle" && Number(attrs.r) <= 1;

    // Motion personalities
    if (motion === "pop") {
      const s = popScale(t);
      const op = clamp01(t * 3);
      return (
        <g key={`${key}${i}`} transform={`translate(12 12) scale(${s}) translate(-12 -12)`} opacity={op}>
          {React.createElement(tag, {
            ...attrs,
            fill: dot ? stroke : "none",
            stroke,
            strokeWidth: width,
            strokeLinecap: "round",
            strokeLinejoin: "round",
          })}
        </g>
      );
    }

    if (motion === "pulse") {
      const s = pulseScale(t);
      const op = clamp01(t * 2);
      return (
        <g key={`${key}${i}`} transform={`translate(12 12) scale(${s}) translate(-12 -12)`} opacity={op}>
          {React.createElement(tag, {
            ...attrs,
            fill: dot ? stroke : "none",
            stroke,
            strokeWidth: width,
            strokeLinecap: "round",
            strokeLinejoin: "round",
          })}
        </g>
      );
    }

    if (motion === "sketch") {
      // Architectural hand-drawn technical ink look: primary stroke + subtle sketchy echo
      const draw = t < 1 ? { pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - t } : {};
      const jitter = ((i * 37) % 7) * 0.08 - 0.24;
      return (
        <g key={`${key}${i}`} opacity={t <= 0 ? 0 : 1}>
          {/* Subtle faint hand-drawn undertone */}
          {React.createElement(tag, {
            ...attrs,
            fill: "none",
            stroke,
            strokeWidth: width * 0.75,
            strokeLinecap: "round",
            strokeLinejoin: "round",
            strokeOpacity: 0.35,
            transform: `translate(${jitter} ${-jitter})`,
            ...(dot ? {} : draw),
          })}
          {/* Main solid ink stroke */}
          {React.createElement(tag, {
            ...attrs,
            fill: dot ? stroke : "none",
            stroke,
            strokeWidth: width,
            strokeLinecap: "round",
            strokeLinejoin: "round",
            opacity: dot ? t : 1,
            ...(dot ? {} : draw),
          })}
        </g>
      );
    }

    // Default "draw" & "count": classic pathLength normalized stroke reveal
    const draw = t < 1 ? { pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - t } : {};
    return React.createElement(tag, {
      key: `${key}${i}`,
      ...attrs,
      fill: dot ? stroke : "none",
      stroke,
      strokeWidth: width,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      opacity: t <= 0 ? 0 : dot ? t : 1,
      ...(dot ? {} : draw),
    });
  });
};

/** An icon `size` px wide at (x, y), with a stroke of `px` pixels.
 *  Supports motion: draw, pop, pulse, count, morph, sketch. */
export const GlyphAt: React.FC<{
  nodes: IconNode[];
  x: number;
  y: number;
  size: number;
  px: number;
  color: string;
  progress?: (i: number) => number;
  clip?: string;
  id?: string;
  motion?: IconMotion;
  morphNodes?: IconNode[];
  morphProgress?: number;
}> = ({
  nodes,
  x,
  y,
  size,
  px,
  color,
  progress,
  clip,
  id = "g",
  motion = "draw",
  morphNodes,
  morphProgress = 1,
}) => {
  const k = size / 24;

  if (motion === "morph" && morphNodes && morphNodes.length > 0) {
    const mp = clamp01(morphProgress);
    const scaleA = 1 - 0.15 * mp;
    const scaleB = 0.85 + 0.15 * mp;
    const opacityA = 1 - mp;
    const opacityB = mp;
    return (
      <g transform={`translate(${x} ${y}) scale(${k})`} clipPath={clip ? `url(#${clip})` : undefined}>
        {opacityA > 0.01 && (
          <g transform={`translate(12 12) scale(${scaleA}) translate(-12 -12)`} opacity={opacityA}>
            {glyphShapes(morphNodes, color, px / k, progress, `${id}a`, "draw")}
          </g>
        )}
        {opacityB > 0.01 && (
          <g transform={`translate(12 12) scale(${scaleB}) translate(-12 -12)`} opacity={opacityB}>
            {glyphShapes(nodes, color, px / k, progress, `${id}b`, "draw")}
          </g>
        )}
      </g>
    );
  }

  return (
    <g transform={`translate(${x} ${y}) scale(${k})`} clipPath={clip ? `url(#${clip})` : undefined}>
      {glyphShapes(nodes, color, px / k, progress, id, motion)}
    </g>
  );
};

/** One cell of the background's icon motif: the story's icon twice, offset half a cell, so the tiles interlock. */
export const IconTile: React.FC<{ nodes: IconNode[]; cell: number; color: string }> = ({ nodes, cell, color }) => {
  const size = cell * 0.36;
  return (
    <>
      <GlyphAt nodes={nodes} x={cell * 0.07} y={cell * 0.07} size={size} px={3} color={color} id="a" />
      <GlyphAt nodes={nodes} x={cell * 0.57} y={cell * 0.57} size={size} px={3} color={color} id="b" />
    </>
  );
};

/** Part-of-whole or unit chart: renders `total` units (default 10 or value), lighting `value` units in `color`,
 *  with unlit units in `unlitColor`. Pure function of frame, deterministic and safe-zone verified. */
export const PictogramChart: React.FC<{
  nodes: IconNode[];
  value: number;
  total?: number;
  width: number;
  height: number;
  color: string;
  unlitColor: string;
  progress: (i: number) => number;
  motion?: IconMotion;
}> = ({ nodes, value, total, width, height, color, unlitColor, progress, motion = "count" }) => {
  const count = Math.max(1, Math.round(value));
  const maxUnits = total ? Math.max(count, Math.round(total)) : count;

  // Grid layout computation
  let best = { cols: maxUnits, rows: 1, cell: 0 };
  for (let c = 1; c <= maxUnits; c++) {
    const r = Math.ceil(maxUnits / c);
    const cell = Math.min(width / c, height / r);
    if (cell > best.cell + 0.5) best = { cols: c, rows: r, cell };
  }
  const { cols, rows, cell } = best;
  const size = Math.min(cell * 0.82, 180);
  const px = Math.max(4, size * 0.07);

  return (
    <svg width={cols * cell} height={rows * cell} style={{ display: "block", overflow: "visible" }}>
      {Array.from({ length: maxUnits }, (_, i) => {
        const isLit = i < count;
        const p = progress(i);
        const x = (i % cols) * cell + (cell - size) / 2;
        const y = Math.floor(i / cols) * cell + (cell - size) / 2;
        const unitColor = isLit ? color : unlitColor;
        const itemMotion = isLit ? motion : "draw";

        return (
          <g key={i} opacity={isLit ? (p > 0 ? 1 : 0) : 0.4}>
            <GlyphAt
              nodes={nodes}
              x={x}
              y={y}
              size={size}
              px={px}
              color={unitColor}
              progress={() => (isLit ? p : 1)}
              motion={itemMotion}
              id={`u${i}`}
            />
          </g>
        );
      })}
    </svg>
  );
};

/** A safe id for <clipPath> from React's useId ("«r1»" -> "r1"). */
export const svgId = (raw: string) => `i${raw.replace(/[^a-zA-Z0-9_-]/g, "")}`;
