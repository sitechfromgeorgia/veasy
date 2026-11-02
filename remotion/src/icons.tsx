// Icons (tt_shorts/icons.py): Lucide stroke shapes on a 24 px grid, drawn in the brand pack's colors. A shape's stroke
// can draw itself (progress 0..1, a pure function of the frame); the accent never colors an icon.
import React from "react";
import type { IconNode } from "./types";

/** An icon's shapes in its own 24-unit space. `width` is the stroke in those units; `progress(i)` draws shape i
 *  (0: hidden, 1: whole). Round caps would leave a dot on an undrawn shape, so a shape at 0 is hidden. Lucide's
 *  tiny circles (a tag's hole, r <= 1) are dots: they are filled, not stroked into a ring. */
export const glyphShapes = (nodes: IconNode[], stroke: string, width: number, progress?: (i: number) => number, key = "g") =>
  nodes.map(([tag, attrs], i) => {
    const t = progress ? progress(i) : 1;
    const dot = tag === "circle" && Number(attrs.r) <= 1;
    const draw = t < 1 ? { pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - t } : {};
    return React.createElement(tag, {
      key: `${key}${i}`, ...attrs, fill: dot ? stroke : "none", stroke, strokeWidth: width, strokeLinecap: "round",
      strokeLinejoin: "round", opacity: t <= 0 ? 0 : dot ? t : 1, ...(dot ? {} : draw),
    });
  });

/** An icon `size` px wide at (x, y), with a stroke of `px` pixels. */
export const GlyphAt: React.FC<{ nodes: IconNode[]; x: number; y: number; size: number; px: number; color: string;
  progress?: (i: number) => number; clip?: string; id?: string }> = ({ nodes, x, y, size, px, color, progress, clip, id = "g" }) => {
  const k = size / 24;
  return (
    <g transform={`translate(${x} ${y}) scale(${k})`} clipPath={clip ? `url(#${clip})` : undefined}>
      {glyphShapes(nodes, color, px / k, progress, id)}
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

/** A safe id for <clipPath> from React's useId ("«r1»" -> "r1"). */
export const svgId = (raw: string) => `i${raw.replace(/[^a-zA-Z0-9_-]/g, "")}`;
