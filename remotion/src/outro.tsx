import React from "react";
import { Freeze, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, H, INK, LINE, ON_ACCENT, PANEL, RADIUS, RAIL_X, RED, SCENE_BOTTOM, SCENE_TOP, SIDE, W } from "./brand";
import type { ShortProps } from "./types";
import { fitSize, Opening, useTheme } from "./ui";

// Built for the swipe and the loop (tt_shorts/swipe.py, ROADMAP D7).
// - Scene 0 is the opening: readable at frame 0 (ui.tsx Opening), where a swipe decides.
// - outro "card": the story's end card, as always.
// - outro "overlay": the end scene is dropped; for the last scene's final seconds a compact chip with the QR, the
//   link and the CTA slides into the safe area (left of the rail, above the captions), and the scene makes room.
// - outro "loop": the same, and the last LOOP frames cross-fade into the hook's frame 0, so the replay has no seam.

export const LOOP = 15; // frames: swipe.LOOP_SECONDS at 30 fps
const CHIP_H = 184;
const CHIP_PAD = 16;
const CHIP_BOTTOM = SCENE_BOTTOM - 16; // story text ends at SCENE_BOTTOM; the caption box starts just below it
const CHIP_TOP = CHIP_BOTTOM - CHIP_H;
const ROOM = (CHIP_TOP - 24 - SCENE_TOP) / (SCENE_BOTTOM - SCENE_TOP); // the last scene's scale under the chip

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const hasChip = (p: ShortProps) => (p.outro === "overlay" || p.outro === "loop") && typeof p.outroFrom === "number";

/** 0..1: how far the chip has come in at an absolute frame (0 before outroFrom, and always 0 for the end card). */
const chipIn = (p: ShortProps, frame: number, fps: number) =>
  hasChip(p) ? spring({ frame: frame - (p.outroFrom as number), fps, config: { damping: 20, stiffness: 170, mass: 0.8 } }) : 0;

/** Around every scene slot: scene 0 is the opening (readable at frame 0); the last scene makes room for the chip by
 *  scaling down from its top left corner as the chip comes in. */
export const SwipeSlot: React.FC<{ i: number; children: React.ReactNode }> = ({ i, children }) => {
  const { v, props } = useTheme();
  const frame = useCurrentFrame(); // the scene's own frame (inside its Sequence)
  const { fps } = useVideoConfig();
  const last = i === props.scenes.length - 1;
  const t = last ? Math.min(1, chipIn(props, props.scenes[i].from + frame, fps)) : 0;
  return (
    <Opening.Provider value={i === 0}>
      <div style={{ position: "absolute", inset: 0, transform: t > 0 ? `scale(${1 - (1 - ROOM) * t})` : undefined,
        transformOrigin: `${v === "cards" ? SIDE - 16 : SIDE}px ${SCENE_TOP}px` }}>{children}</div>
    </Opening.Provider>
  );
};

/** overlay and loop: the end card's QR, link and CTA as one compact card that slides in from the left, inside the
 *  safe area (x <= RAIL_X, y <= SCENE_BOTTOM). The accent only on the button. */
export const OutroChip: React.FC = () => {
  const { v, props } = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = chipIn(props, frame, fps);
  if (t <= 0) return null;
  const left = v === "cards" ? SIDE - 16 : SIDE; // in line with the look's scene edge
  // cards: as wide as the card above it once it has made room; the other looks: up to the like/share rail
  const width = v === "cards" ? Math.round((W - 2 * left) * ROOM) : RAIL_X - left;
  const qr = CHIP_H - 2 * CHIP_PAD - 4; // the border is 2px on each side
  const text = width - 2 * CHIP_PAD - 4 - qr - 32;
  const urlSize = fitSize([props.url], text, 40, 24);
  const ctaSize = fitSize([props.cta], text - 64, 36, 24);
  return (
    <div style={{ position: "absolute", left, top: CHIP_TOP, width, height: CHIP_H, boxSizing: "border-box", padding: CHIP_PAD,
      display: "flex", alignItems: "center", gap: 32, background: PANEL, border: `2px solid ${LINE}`, borderRadius: RADIUS,
      transform: `translateX(${(1 - t) * -(left + width + 40)}px)` }}>
      {/* a QR needs its light quiet zone, as on the end card */}
      <div style={{ width: qr, height: qr, flex: "none", boxSizing: "border-box", padding: 8, background: "#FFFFFF", borderRadius: 8,
        lineHeight: 0 }} dangerouslySetInnerHTML={{ __html: props.qrSvg }} />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 16, minWidth: 0 }}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: urlSize, lineHeight: 1.2, color: INK, whiteSpace: "nowrap" }}>
          {props.url}
        </div>
        <div style={{ background: RED, color: ON_ACCENT, fontFamily: FONT, fontWeight: 700, fontSize: ctaSize, lineHeight: 1.2,
          padding: "12px 32px 16px", borderRadius: 999, whiteSpace: "nowrap" }}>{props.cta}</div>
      </div>
    </div>
  );
};

/** loop: the last LOOP frames cross-fade the scene band into the hook's frame 0 (frozen), so the last frame is the
 *  first one. The same background covers the last scene first and the hook comes in over it a little later, so the
 *  two scenes' words barely overlap. The header, captions, ticker and footer stay as they are. */
export const LoopBack: React.FC<{ background: React.ReactNode; hook: React.ReactNode }> = ({ background, hook }) => {
  const { props } = useTheme();
  const frame = useCurrentFrame(); // absolute: this is not inside a Sequence, so the background pans as underneath
  const { durationInFrames } = useVideoConfig();
  const from = durationInFrames - LOOP;
  if (props.outro !== "loop" || frame < from) return null;
  const t = interpolate(frame, [from, durationInFrames - 1], [0, 1], clamp);
  const cover = interpolate(t, [0, 0.6], [0, 1], clamp);
  const shown = interpolate(t, [0.4, 1], [0, 1], clamp);
  return (
    <div style={{ position: "absolute", inset: 0, clipPath: `inset(${SCENE_TOP - 32}px 0 ${H - SCENE_BOTTOM}px 0)` }}>
      <div style={{ position: "absolute", inset: 0, opacity: cover }}>{background}</div>
      <div style={{ position: "absolute", inset: 0, opacity: shown }}><Freeze frame={0}>{hook}</Freeze></div>
    </div>
  );
};

/** loop: a repeating motion's speed, rounded so that it is back where it started one frame after the last (the
 *  ticker). Any other outro keeps the speed. */
export const loopSpeed = (p: ShortProps, speed: number, unit: number, frames: number) =>
  p.outro === "loop" && unit > 0 ? (Math.max(1, Math.round((speed * frames) / unit)) * unit) / frames : speed;

/** The music's level over the video (Studio preview only; the render's mix is ffmpeg's, tt_shorts/props.mix_audio):
 *  a fade in and out, or for a loop one steady level to the last frame. */
export const musicLevel = (p: ShortProps, f: number, frames: number) =>
  p.outro === "loop" ? 1 : interpolate(f, [0, 30, frames - 75, frames], [0, 1, 1, 0], clamp);
