// A scene's picture (tt_shorts/assets.py): a local file from the story's ledger, drawn behind the scene's content.
// Python resolved everything: the file in public/media/, the pack's label for an illustration and the credit line.
// This component only draws a file; it never fetches anything.
//
//   editorial, kinetic: full-bleed across the frame's width, from under the header rule to the bottom of the scene
//                       band, under a scrim of the pack's canvas color (the text stays readable and the probe passes),
//                       fading into the canvas at both edges, with a slow push-in
//   cards:              the card's image: it fills the card down to its footer line, under a scrim of the card's own
//                       panel color, clipped to the card's radius
//
// The label („საილუსტრაციო", news rule N13) and the credit sit in the scene's own probe region, at the bottom of the
// Frame, left of the like/share rail: small, quiet, like the map's boundary credit. Colors are read inside the
// components (brand.ts live bindings).
import React from "react";
import { Img, interpolate, Loop, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { alpha, CANVAS, FONT, LINE_STRONG, MUTED, PANEL, RADIUS, SCENE_TOP, SIDE, W } from "./brand";
import type { MediaProps, Scene } from "./types";
import { useTheme } from "./ui";

const CARD_PAD = 48; // NewsShort.tsx: the card's inner padding (the Frame sits inside it)
const CARD_FOOT = 120; // NewsShort.tsx: the card's footer band, below the Frame
const TOP = 212; // just under the header's progress rule (y 204-208)
export const CREDIT_ROW = 52; // the label and credit row at the bottom of a Frame with a picture
const SCRIM = 0.72; // the canvas over the picture: ink text on it keeps a contrast of about 7:1

const Picture: React.FC<{ m: MediaProps; s: Scene }> = ({ m, s }) => {
  const frame = useCurrentFrame();
  const push = interpolate(frame, [0, Math.max(1, s.duration)], [1.03, 1.1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const style: React.CSSProperties = { position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover",
    transform: `scale(${push})`, filter: "saturate(0.7)" };
  if (m.kind === "video") {
    const clip = <OffthreadVideo src={staticFile(m.src)} muted style={style} />;
    return m.frames && m.frames < s.duration ? <Loop durationInFrames={m.frames}>{clip}</Loop> : clip;
  }
  return <Img src={staticFile(m.src)} style={style} />;
};

/** The picture behind a scene, positioned out of the Frame's box to the frame's width (or the card's). */
export const SceneMedia: React.FC<{ s: Scene }> = ({ s }) => {
  const { v } = useTheme();
  const m = s.media;
  if (!m) return null;
  const cards = v === "cards";
  const base = cards ? PANEL : CANVAS;
  const box: React.CSSProperties = cards
    ? { left: -CARD_PAD, right: -CARD_PAD, top: -CARD_PAD, bottom: -(CARD_FOOT - 40 - 64), borderRadius: `${RADIUS}px ${RADIUS}px 0 0` }
    : { left: -SIDE, width: W, top: TOP - SCENE_TOP, bottom: 0 };
  const fade = cards
    ? `linear-gradient(to bottom, ${alpha(base, 0)} 70%, ${alpha(base, 1)} 100%)`
    : `linear-gradient(to bottom, ${alpha(base, 1)} 0px, ${alpha(base, 0)} 72px, ${alpha(base, 0)} calc(100% - 200px), ${alpha(base, 1)} 100%)`;
  return (
    <div style={{ position: "absolute", overflow: "hidden", ...box }}>
      <Picture m={m} s={s} />
      <div style={{ position: "absolute", inset: 0, background: alpha(base, SCRIM) }} />
      <div style={{ position: "absolute", inset: 0, background: fade }} />
    </div>
  );
};

/** The label and the credit: one quiet row at the bottom of the Frame (inside the scene's probe region). */
export const MediaCredit: React.FC<{ s: Scene }> = ({ s }) => {
  const m = s.media;
  if (!m || (!m.label && !m.credit)) return null;
  return (
    <div style={{ height: CREDIT_ROW, display: "flex", alignItems: "flex-end", gap: 16, fontFamily: FONT, fontSize: 24,
      lineHeight: 1.2, color: MUTED, whiteSpace: "nowrap" }}>
      {m.label && (
        <span style={{ border: `2px solid ${LINE_STRONG}`, borderRadius: 999, padding: "6px 16px 8px", fontWeight: 600, flex: "none" }}>
          {m.label}
        </span>
      )}
      {m.credit && <span style={{ fontWeight: 400, paddingBottom: 8 }}>{m.credit}</span>}
    </div>
  );
};
