// tt_shorts/vignettes.py: a line drawing of what this part of the story is about, in the room the scene's text leaves.
// It draws itself stroke by stroke as the scene comes in, acts out the story when the voice says the scene's key
// phrase (a needle swings, an arrow climbs: art.py's acts), keeps its loops going and goes before the cut.
// Seat, drawing and bounds come from Python; every number here is a pure function of the frame. It holds no words.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CANVAS, INK, LINE_STRONG, MUTED, PANEL, RED } from "./brand";
import { artNode } from "./scenes/more";
import { CROSS } from "./thread";
import { useTheme } from "./ui";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const START = 8; // frames: the scene's entrance first
const DRAW = 1.4; // seconds the strokes take to draw themselves
const DRIFT = 0.03; // the push-in over the scene: from 97% of the seat to all of it

export const VignetteLayer: React.FC = () => {
  const { props, v } = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = props.scenes.find((x) => frame >= x.from && frame < x.from + x.duration);
  const vg = s?.vignette;
  if (!s || !vg) return null;
  const local = frame - s.from, tail = s.duration - local;
  const opacity = interpolate(local, [START - 4, START + 4], [0, 1], clamp) * interpolate(tail, [0, CROSS], [0, 1], clamp);
  const drawing = interpolate(local, [START, START + DRAW * fps], [0, 1], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 2) });
  const colors: Record<string, string> = {
    ACCENT: RED, INK, MUTED, LINE: LINE_STRONG, CANVAS: v === "cards" ? PANEL : CANVAS, none: "none",
  };
  const [x0, y0, x1, y1] = vg.box;
  // the act lands when the voice says the scene's key phrase (its mark), on the drawing's own clock
  const actAt = s.mark ? s.mark.at - START : undefined;
  // a slow push-in from its foot, inside the seat, so even a drawing without an act is never still
  const push = 1 - DRIFT + DRIFT * interpolate(local, [0, s.duration], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={vg.w} height={vg.h} viewBox={`${x0} ${y0} ${x1 - x0} ${y1 - y0}`} fill="none" strokeLinecap="round"
        strokeLinejoin="round" style={{ position: "absolute", left: vg.x, top: vg.y, overflow: "visible", opacity,
          transform: `scale(${push})`, transformOrigin: "50% 100%" }}>
        {vg.art.map((n, i) => artNode(n, i, { frame: local - START, fps, k: 0.5, colors, actAt }, drawing))}
      </svg>
    </AbsoluteFill>
  );
};
