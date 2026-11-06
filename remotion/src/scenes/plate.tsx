// The plate scene: a baked, tone-only clip (plates/, tt_shorts/plates.py) behind a card with the words.
// The clip is a local file toned into the pack's canvas and ink; it is drawn at page coordinates (the plate's pixel
// (x, y) shows at the page's (x, y)), so the anchors the plate wrote (where its subject is) are the page's own and
// the accent dot, a DOM element, follows them. The words are DOM text on a solid card (a plate under bare text would
// fail the probe's black/white ground test). With no plate resolved (a missing clip is a warning, never a lost
// film) the scene is the same card on the plain canvas. Colors are read inside the component (brand.ts bindings).
import React from "react";
import { interpolate, Loop, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { alpha, CANVAS, FONT, INK, LINE_STRONG, MUTED, PANEL, RADIUS, RAIL_X, SCENE_BOTTOM, SCENE_TOP, SIDE, W, H } from "../brand";
import { marked } from "../marker";
import type { Scene } from "../types";
import { Dot, fitSize, In, Kicker, useTheme } from "../ui";

const INNER = W - 2 * SIDE;
const CARD = 0.92; // the card's opacity: solid enough that any plate pixel under it keeps the text at >= 13:1
const PAD = 40;
const SCRIM = 0.45; // the canvas over the clip: a plate's white is the pack's ink, and a ground that bright overpowers the card
// Where the scene's own box sits on the page, and the box the clip fills (page pixels). The clip is drawn at page
// coordinates, so a plate pixel (x, y) shows at the page's (x, y) in every look; only the clipping box differs:
// editorial and kinetic: the scene band across the frame's width; cards: the card down to its footer line.
const ORIGIN = { flat: [SIDE, SCENE_TOP], cards: [98, 298] } as const; // NewsShort.tsx: SIDE - 16 + border + CARD_PAD
const CLIP = { flat: [0, SCENE_TOP, W, SCENE_BOTTOM], cards: [50, 250, 1030, 1274] } as const; // x0, y0, x1, y1

export const Plate: React.FC<{ s: Scene; inner?: number }> = ({ s, inner = INNER }) => {
  const { v } = useTheme();
  const frame = useCurrentFrame();
  const p = s.plate;
  const base = v === "cards" ? PANEL : CANVAS;
  const layout = p?.layout ?? "mid";
  // below y=1100 no text goes right of x=940 (the like/share rail): the low card ends left of it
  const [ox, oy] = v === "cards" ? ORIGIN.cards : ORIGIN.flat;
  const [x0, y0, x1, y1] = v === "cards" ? CLIP.cards : CLIP.flat;
  const width = layout === "low" ? Math.min(inner, RAIL_X - ox) : inner;
  const text = s.headline ?? "";
  const size = fitSize([text], width - 2 * PAD, 96, 48);
  const place: React.CSSProperties =
    layout === "top" ? { top: 24 } : layout === "low" ? { bottom: 24 } : { top: "50%", transform: "translateY(-50%)" };
  const local = p ? frame % Math.max(1, p.frames) : 0;
  const dot = p?.tracks?.dot?.[Math.min(local, (p.tracks.dot?.length ?? 1) - 1)];
  const dx = dot ? dot[0] - ox : 0, dy = dot ? dot[1] - oy : 0;
  const shown = !!dot && dot[0] >= x0 && dot[0] <= x1 && dot[1] >= y0 && dot[1] <= y1;
  const fade = interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const clip = p && <OffthreadVideo src={staticFile(p.src)} muted style={{ position: "absolute", left: -x0, top: -y0, width: W, height: H }} />;
  return (
    <>
      {p && (
        <div style={{ position: "absolute", left: x0 - ox, top: y0 - oy, width: x1 - x0, height: y1 - y0, overflow: "hidden", opacity: fade,
          borderRadius: v === "cards" ? `${RADIUS}px ${RADIUS}px 0 0` : 0 }}>
          {s.duration > p.frames ? <Loop durationInFrames={p.frames}>{clip}</Loop> : clip}
          <div style={{ position: "absolute", inset: 0, background: alpha(base, SCRIM) }} />
          <div style={{ position: "absolute", inset: 0, background: `linear-gradient(to bottom, ${alpha(base, 0)} calc(100% - 140px), ${alpha(base, 1)} 100%)` }} />
        </div>
      )}
      {shown && (
        <div style={{ position: "absolute", left: dx, top: dy, transform: "translate(-50%, -50%)", opacity: fade }}>
          <Dot size={28} pulse />
        </div>
      )}
      <div style={{ position: "absolute", left: 0, width, ...place }}>
        <In>
          <div style={{ background: alpha(base, CARD), border: `2px solid ${LINE_STRONG}`, borderRadius: RADIUS, padding: PAD }}>
            <Kicker text={s.kicker} />
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.16, color: INK, marginTop: s.kicker ? 28 : 0,
              whiteSpace: "nowrap" }}>
              {marked(s, "headline", text, { px: size })}
            </div>
            {s.label && <div style={{ fontFamily: FONT, fontWeight: 400, fontSize: 32, lineHeight: 1.3, color: MUTED, marginTop: 20 }}>{s.label}</div>}
          </div>
        </In>
      </div>
    </>
  );
};
