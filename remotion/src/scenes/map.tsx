// The where scene on a real map of Georgia (tt_shorts/geo.py projects and chooses everything in Python; this only
// draws and moves). Georgia's outline draws itself, the region lines come in, the camera zooms toward the region
// (or into a Tbilisi district), the region fills in a quiet ink tint and the pin with the red dot drops on the town.
// No new colors: ink at low opacity, the line color, the accent only for the pin's dot. Motion is a function of the
// frame; strokes keep their width on screen at any zoom.
// `mode="focus"` (the map-focus scene) is the same paths, projection and camera with one region highlighted in the
// accent, the rest of the country left muted, no pin, and the region's name with an optional number beside it.
import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CANVAS, FONT, INK, LINE_STRONG, MUTED, RAIL_X, RED, SIDE, W } from "../brand";
import { marked } from "../marker";
import type { Scene } from "../types";
import { beat, fitSize, Frame, In, measure, stepped, useTheme } from "../ui";

const INNER = W - 2 * SIDE; // 952
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const smooth = Easing.inOut(Easing.cubic);
// the grid scene's pin: its tip is at (0, 100), the dot at (0, -122)
const PIN = "M0 -250c-74 0-130 56-130 128 0 96 130 222 130 222s130-126 130-222c0-72-56-128-130-128z";
const FADE = "3.5%"; // the map's edges fade out instead of ending in a hard frame

type Box = number[];
const fit = (r: Box, w: number, h: number) => ({
  k: Math.min(w / (r[2] - r[0]), h / (r[3] - r[1])), x: (r[0] + r[2]) / 2, y: (r[1] + r[3]) / 2,
});

/** A long place name in two balanced lines (as the grid scene does). */
const placeLines = (place: string) => {
  const words = place.split(" ").filter(Boolean);
  const half = Math.ceil(words.length / 2);
  return words.length > 2 ? [words.slice(0, half).join(" "), words.slice(half).join(" ")] : [place];
};

/** Georgian numbers: thousands grouped with a space, decimals with a comma ("310 000", "12,5"). */
const decimalsOf = (v: number) => (String(v).split(".")[1] ?? "").length;
const num = (v: number, d: number) => {
  const [i, f] = Math.abs(v).toFixed(d).split(".");
  return (v < 0 ? "-" : "") + i.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + (f ? "," + f : "");
};

export const MapWhere: React.FC<{ s: Scene; inner?: number; mode?: "where" | "focus" }> = (
  { s, inner = INNER, mode = "where" }) => {
  const focus = mode === "focus"; // the map-focus scene: one region in the accent, no pin, a number beside the name
  const m = s.map!;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { v } = useTheme();
  const kinetic = v === "kinetic";
  const tight = inner < INNER - 40; // a card: less height
  const boxW = inner;
  const boxH = tight ? 420 : focus ? 490 : 540;
  // text that may reach below y=1100 stays left of the like/share rail; a card's content starts further right
  const left = SIDE + (INNER - inner) / 2;
  const textW = Math.min(inner, RAIL_X - left);

  // the timeline, squeezed into a short scene: outline, region lines, camera, pins. A focus scene is shorter and
  // lands its highlight early (a map-focus still is often looked at a third of the way in)
  const drawEnd = focus ? 12 : kinetic ? 16 : 24;
  const zoomFrom = focus ? 6 : kinetic ? 12 : 18;
  const zoomTo = Math.max(zoomFrom + 14, Math.min(zoomFrom + (focus ? 22 : kinetic ? 24 : 34), s.duration - 34));
  const draw = interpolate(frame, [0, drawEnd], [0, 1], { ...clamp, easing: smooth });
  const lines = interpolate(frame, [drawEnd - 8, drawEnd + 6], [0, 1], clamp);
  // with a beat track the camera goes in in stages, one a beat (tt_shorts/beats.py), and the pins drop after the last
  const steps = s.beats?.steps ?? [];
  const t = m.level === "country" ? 0 : stepped(s, frame, interpolate(frame, [zoomFrom, zoomTo], [0, 1], { ...clamp, easing: smooth }), 20);
  // a focus scene's highlight lands on its own short clock, not stage by stage: the region is the point of the frame
  const tint = focus ? interpolate(frame, [8, 24], [0, 1], clamp)
    : stepped(s, frame, interpolate(frame, [zoomFrom + 4, zoomTo], [0, 1], clamp), 20);
  const landed = steps.length && m.level !== "country" ? steps[steps.length - 1] + 8 : zoomTo;

  // the camera: the scale moves geometrically, the centre linearly, so the zoom feels even
  const a = fit(m.start, boxW, boxH);
  const b = fit(m.focus, boxW, boxH);
  const k = a.k * Math.pow(b.k / a.k, t);
  const cx = a.x + (b.x - a.x) * t;
  const cy = a.y + (b.y - a.y) * t;
  const px = (n: number) => n / k; // n pixels on screen, in map units
  const screen = (p: number[]) => [boxW / 2 + (p[0] - cx) * k, boxH / 2 + (p[1] - cy) * k];

  const several = m.pins.length > 1;
  const pins = m.pins.map((p, i) => {
    const drop = spring({ frame: frame - (landed - 6 + i * 5), fps, config: { damping: 12, stiffness: 170, mass: 0.8 } });
    const [x, y] = screen(p);
    return { x, y, drop };
  });

  const place = String(s.place ?? "");
  const lns = placeLines(place);
  const pad = kinetic ? 28 : 0;
  const size = fitSize(lns, textW - 2 * pad, focus ? (tight ? 76 : 92) : tight ? 104 : 120, focus ? 44 : 48);
  // the focus number: big, counted once it arrives, with its label beside it (long labels wrap, never widen)
  const value = typeof s.value === "number" ? s.value : null;
  const vtext = value === null ? "" : num(value, decimalsOf(value));
  const vsize = fitSize([vtext], textW * 0.55, tight ? 104 : 128, 56);
  const vw = (measure(vtext, 700) * vsize) / 100;
  const labelW = Math.max(120, textW - vw - 28);
  const clip = `georgia-${s.from}`;
  const mask = `linear-gradient(to right, transparent, #000 ${FADE}, #000 calc(100% - ${FADE}), transparent), ` +
    `linear-gradient(to bottom, transparent, #000 ${FADE}, #000 calc(100% - ${FADE}), transparent)`;

  return (
    <Frame s={s}>
      <div style={{ position: "relative", width: boxW, height: boxH, maskImage: mask, WebkitMaskImage: mask,
        maskComposite: "intersect", WebkitMaskComposite: "source-in" }}>
        <svg width={boxW} height={boxH} viewBox={`0 0 ${boxW} ${boxH}`} style={{ position: "absolute", left: 0, top: 0 }}>
          <defs>
            <clipPath id={clip}><path d={m.land} /></clipPath>
          </defs>
          <g transform={`translate(${boxW / 2} ${boxH / 2}) scale(${k}) translate(${-cx} ${-cy})`}>
            <path d={m.land} fill={INK} fillOpacity={(focus ? 0.07 : 0.05) * draw} stroke="none" />
            {m.regions.map((r, i) => (
              <path key={i} d={r} fill={focus ? RED : INK} fillOpacity={(focus ? 0.34 : 0.18) * tint} stroke="none" />
            ))}
            <path d={m.rivers} fill="none" stroke={INK} strokeOpacity={0.3} strokeWidth={px(2.5)} strokeLinejoin="round"
              strokeLinecap="round" opacity={lines} clipPath={`url(#${clip})`} />
            <path d={m.borders} fill="none" stroke={LINE_STRONG} strokeWidth={px(2)} strokeDasharray={`${px(8)} ${px(6)}`}
              opacity={lines} />
            {m.regions.map((r, i) => (
              <path key={i} d={r} fill="none" stroke={focus ? RED : INK} strokeOpacity={focus ? 0.85 : 1}
                strokeWidth={px(focus ? 5 : 4)} strokeLinejoin="round" opacity={tint} />
            ))}
            <path d={m.land} fill="none" stroke={INK} strokeWidth={px(3)} strokeLinejoin="round" pathLength={1}
              strokeDasharray="1 1" strokeDashoffset={1 - draw} />
          </g>
          {pins.map(({ x, y, drop }, i) => (
            <g key={i} opacity={Math.min(1, drop * 2)}>
              {i === 0 && [0, 1].map((j) => {
                // rings spread from the first pin once it lands (their phase as before beats: the settled frame)
                const r = ((frame - zoomTo - j * 16) % 32) / 32;
                return frame >= zoomTo + j * 16 && frame >= landed + j * 16 ? (
                  <ellipse key={j} cx={x} cy={y} rx={12 + r * 70} ry={(12 + r * 70) * 0.45} fill="none" stroke={INK}
                    strokeWidth={3} opacity={(1 - r) * 0.5} />
                ) : null;
              })}
              {several ? (
                // places close together (two districts): a marker each, so they don't cover one another
                <g transform={`translate(${x} ${y - (1 - drop) * 60}) scale(${0.6 + 0.4 * drop})`}>
                  <circle r={17} fill={INK} />
                  <circle r={8} fill={RED} />
                </g>
              ) : (
                <g transform={`translate(${x} ${y - (1 - drop) * 90}) scale(0.28) translate(0 -100)`}>
                  <path d={PIN} fill={INK} />
                  <circle cx={0} cy={-122} r={46} fill={RED} />
                </g>
              )}
            </g>
          ))}
        </svg>
      </div>
      {/* the boundary data's licence asks for a credit: small, under the map, left of the rail */}
      <div style={{ width: textW, height: 28, textAlign: "right", fontFamily: FONT, fontWeight: 400, fontSize: 22, lineHeight: 1.2,
        color: MUTED, opacity: m.credit ? 0.8 * draw : 0, whiteSpace: "nowrap" }}>{m.credit}</div>
      <In delay={8}>
        <div style={{ marginTop: 8, maxWidth: textW }}>
          <div style={{ display: "inline-block", fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.12,
            color: kinetic ? CANVAS : INK, background: kinetic ? INK : "transparent",
            padding: kinetic ? `0 ${pad}px ${size * 0.1}px` : 0 }}>
            {lns.map((l, i) => <div key={i} style={{ whiteSpace: "nowrap" }}>{l}</div>)}
          </div>
        </div>
      </In>
      {focus && (value !== null || s.label) && (
        <In delay={12} at={beat(s, "label")}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 28, marginTop: 12, maxWidth: textW }}>
            {value !== null && (
              <div style={{ flex: "none", fontFamily: FONT, fontWeight: 700, fontSize: vsize, lineHeight: 1, color: INK,
                whiteSpace: "nowrap" }}>
                {vtext}
              </div>
            )}
            {s.label && (
              <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 40, lineHeight: 1.25, color: MUTED, maxWidth: labelW }}>
                {marked(s, "label", s.label, { px: 40 })}
              </div>
            )}
          </div>
        </In>
      )}
      {s.sub && (
        <In delay={14} at={beat(s, "sub")}>
          <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 40, lineHeight: 1.3, color: MUTED, marginTop: 12,
            maxWidth: textW }}>{marked(s, "sub", s.sub, { px: 44 })}</div>
        </In>
      )}
    </Frame>
  );
};
