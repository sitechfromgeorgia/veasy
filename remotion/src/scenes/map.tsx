// The where scene on a real map of Georgia (tt_shorts/geo.py projects and chooses everything in Python; this only
// draws and moves). Georgia's outline draws itself, the region lines come in, the camera zooms toward the region
// (or into a Tbilisi district), the region fills in a quiet ink tint and the pin with the red dot drops on the town.
// No new colors: ink at different opacities, the line colors and the canvas; the accent is the pin's dot and, by the
// owner's decision (2026-11-07), the tint of the occupied territories (Abkhazia, the Tskhinvali region: a low red
// fill and a fine hatch, labelled in ink with the pack's words). The OpenStreetMap layers (props `layers`) come in
// with the camera's zoom: roads, rivers and lakes for a region, the streets and metro for a Tbilisi district.
// Motion is a function of the frame; strokes keep their width on screen at any zoom.
import React, { useMemo } from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CANVAS, FONT, INK, LINE_STRONG, MUTED, RAIL_X, RED, SIDE, W } from "../brand";
import { marked } from "../marker";
import type { Scene } from "../types";
import { beat, fitSize, Frame, In, measure, stepped, useTheme } from "../ui";
import { labelAngle, lerpView, outsideRect, polygons, toScreen, zoomIn } from "./mapgeo";
import type { Rect, View } from "./mapgeo";

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

export const MapWhere: React.FC<{ s: Scene; inner?: number }> = ({ s, inner = INNER }) => {
  const m = s.map!;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { v } = useTheme();
  const kinetic = v === "kinetic";
  const tight = inner < INNER - 40; // a card: less height
  const boxW = inner;
  const boxH = tight ? 420 : 540;
  // text that may reach below y=1100 stays left of the like/share rail; a card's content starts further right
  const left = SIDE + (INNER - inner) / 2;
  const textW = Math.min(inner, RAIL_X - left);

  // the timeline, squeezed into a short scene: outline, region lines, camera, pins
  const drawEnd = kinetic ? 16 : 24;
  const zoomFrom = kinetic ? 12 : 18;
  const zoomTo = Math.max(zoomFrom + 14, Math.min(zoomFrom + (kinetic ? 24 : 34), s.duration - 34));
  const draw = interpolate(frame, [0, drawEnd], [0, 1], { ...clamp, easing: smooth });
  const lines = interpolate(frame, [drawEnd - 8, drawEnd + 6], [0, 1], clamp);
  // with a beat track the camera goes in in stages, one a beat (tt_shorts/beats.py), and the pins drop after the last
  const steps = s.beats?.steps ?? [];
  const t = m.level === "country" ? 0 : stepped(s, frame, interpolate(frame, [zoomFrom, zoomTo], [0, 1], { ...clamp, easing: smooth }), 20);
  const tint = stepped(s, frame, interpolate(frame, [zoomFrom + 4, zoomTo], [0, 1], clamp), 20);
  const landed = steps.length && m.level !== "country" ? steps[steps.length - 1] + 8 : zoomTo;
  // the occupied territories' tint comes in with the land, its label right after
  const occT = interpolate(frame, [drawEnd - 6, drawEnd + 10], [0, 1], clamp);
  const labelT = interpolate(frame, [drawEnd + 8, drawEnd + 20], [0, 1], clamp);

  // the camera: the scale moves geometrically, the centre linearly, so the zoom feels even
  const a = fit(m.start, boxW, boxH);
  const b = fit(m.focus, boxW, boxH);
  const k = a.k * Math.pow(b.k / a.k, t);
  const cx = a.x + (b.x - a.x) * t;
  const cy = a.y + (b.y - a.y) * t;
  const px = (n: number) => n / k; // n pixels on screen, in map units
  // the layers come in with the zoom (k is px per map unit; the country view is about 0.09)
  const ov = m.layers?.overview;
  const det = m.layers?.detail;
  const city = m.layers?.city;
  const overview = 1 - (det ? zoomIn(k, 0.11, 0.18) : city ? zoomIn(k, 0.35, 0.9) : 0);
  const detailA = det ? zoomIn(k, 0.1, 0.17) : 0;
  const detailB = det ? zoomIn(k, 0.14, 0.28) : 0; // the finer classes: minor rivers, primary roads, rail
  const cityA = city ? zoomIn(k, 0.7, 1.2) : 0;
  const cityB = city ? zoomIn(k, 1.0, 1.7) : 0; // primary and secondary streets
  const coarse = 1 - Math.max(detailA, cityA); // the coarse rivers give way to the fine ones
  const screen = (p: number[]) => [boxW / 2 + (p[0] - cx) * k, boxH / 2 + (p[1] - cy) * k];

  const several = m.pins.length > 1;
  const pins = m.pins.map((p, i) => {
    const drop = spring({ frame: frame - (landed - 6 + i * 5), fps, config: { damping: 12, stiffness: 170, mass: 0.8 } });
    const [x, y] = screen(p);
    return { x, y, drop };
  });

  // the occupied territories' labels: inside the area when it is big enough on screen, else outside beside it with
  // a hairline leader (the side is chosen once, on the camera's first and last view, so it does not wander)
  const land = useMemo(() => polygons(m.land), [m.land]);
  const LS = 26; // the label's size: the layout probe's floor for a scene's text is 24
  const views: View[] = [{ k: a.k, cx: a.x, cy: a.y }, { k: b.k, cx: b.x, cy: b.y }];
  const now = lerpView(views[0], views[1], t);
  const taken: Rect[][] = [[], []];
  const labels = (m.occupied ?? []).filter((o) => o.label).map((o) => {
    const words = o.label.split(" ").filter(Boolean);
    const half = Math.ceil(words.length / 2);
    const lines = words.length > 1 ? [words.slice(0, half).join(" "), words.slice(half).join(" ")] : words;
    const wOf = (size: number) => (Math.max(...lines.map((l) => measure(l, 600))) * size) / 100;
    const hOf = (size: number) => lines.length * size * 1.18;
    const need = (size: number) => Math.hypot(wOf(size) / 2, hOf(size) / 2) + 6;
    const A = toScreen(now, boxW, boxH, o.at);
    const rpx = o.r * now.k;
    const q = (rpx * 0.95) / need(LS);
    const inside = Math.max(0, Math.min(1, (q - 0.92) / 0.14)); // 0: outside beside it, 1: inside, between: both fade
    let size = LS;
    for (let z = 36; z > LS; z -= 2) if (need(z) <= rpx * 0.95) { size = z; break; }
    const [th, gap] = labelAngle({ views: m.level === "country" || o.in_focus ? views : [views[0]], boxW, boxH, at: o.at, r: o.r,
      w: wOf(LS), h: hOf(LS), land, pins: m.pins, taken });
    const u: [number, number] = [Math.cos(th), Math.sin(th)];
    views.forEach((v, i) => taken[i].push(outsideRect(toScreen(v, boxW, boxH, o.at), o.r * v.k, u, wOf(LS), hOf(LS), gap)));
    const R0 = outsideRect(A, rpx, u, wOf(LS), hOf(LS), gap);
    // the camera moves under the label: it stays inside the map's box
    const R = { ...R0, x: Math.max(4, Math.min(R0.x, boxW - 4 - R0.w)), y: Math.max(4, Math.min(R0.y, boxH - 4 - R0.h)) };
    // the area's own on-screen window: a label for a territory the camera has left does not hang in the air
    const seen = Math.max(0, Math.min(1, Math.min(A[0], boxW - A[0], A[1], boxH - A[1]) / 40));
    const vis = (m.level === "country" || o.in_focus ? 1 : 1 - Math.min(1, t * 3)) * seen;
    return { o, lines, A, rpx, inside, size, R, u, vis: vis * labelT };
  });

  const place = String(s.place ?? "");
  const lns = placeLines(place);
  const pad = kinetic ? 28 : 0;
  const size = fitSize(lns, textW - 2 * pad, tight ? 104 : 120, 48);
  const clip = `georgia-${s.from}`;
  const hatch = `occupied-${s.from}`;
  const mask = `linear-gradient(to right, transparent, #000 ${FADE}, #000 calc(100% - ${FADE}), transparent), ` +
    `linear-gradient(to bottom, transparent, #000 ${FADE}, #000 calc(100% - ${FADE}), transparent)`;

  return (
    <Frame s={s}>
      <div style={{ position: "relative", width: boxW, height: boxH }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: boxW, height: boxH, maskImage: mask, WebkitMaskImage: mask,
        maskComposite: "intersect", WebkitMaskComposite: "source-in" }}>
        <svg width={boxW} height={boxH} viewBox={`0 0 ${boxW} ${boxH}`} style={{ position: "absolute", left: 0, top: 0 }}>
          <defs>
            <clipPath id={clip}><path d={m.land} /></clipPath>
            {/* the occupied territories' hatch: fine diagonal lines in the accent (sizes in map units, so px() keeps them
                the same on screen at any zoom) */}
            <pattern id={hatch} patternUnits="userSpaceOnUse" width={px(9)} height={px(9)} patternTransform="rotate(45)">
              <line x1={0} y1={0} x2={0} y2={px(9)} stroke={RED} strokeWidth={px(1.6)} />
            </pattern>
            {/* a window's soft edge: the detail layers end in a fade, not in the edge of their box */}
            {[["det", det?.box], ["city", city?.box]].map(([id, bx]) => {
              const bb = bx as number[] | undefined;
              if (!bb) return null;
              const fx = (bb[2] - bb[0]) * 0.04, fy = (bb[3] - bb[1]) * 0.04;
              return (
                <React.Fragment key={id as string}>
                  <linearGradient id={`${id}-x-${s.from}`} gradientUnits="userSpaceOnUse" x1={bb[0]} y1={0} x2={bb[2]} y2={0}>
                    <stop offset={0} stopColor={INK} stopOpacity={0} /><stop offset={fx / (bb[2] - bb[0])} stopColor={INK} stopOpacity={1} />
                    <stop offset={1 - fx / (bb[2] - bb[0])} stopColor={INK} stopOpacity={1} /><stop offset={1} stopColor={INK} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id={`${id}-y-${s.from}`} gradientUnits="userSpaceOnUse" x1={0} y1={bb[1]} x2={0} y2={bb[3]}>
                    <stop offset={0} stopColor={INK} stopOpacity={0} /><stop offset={fy / (bb[3] - bb[1])} stopColor={INK} stopOpacity={1} />
                    <stop offset={1 - fy / (bb[3] - bb[1])} stopColor={INK} stopOpacity={1} /><stop offset={1} stopColor={INK} stopOpacity={0} />
                  </linearGradient>
                  <mask id={`${id}-mx-${s.from}`} style={{ maskType: "alpha" }} maskUnits="userSpaceOnUse" x={bb[0]} y={bb[1]} width={bb[2] - bb[0]} height={bb[3] - bb[1]}>
                    <rect x={bb[0]} y={bb[1]} width={bb[2] - bb[0]} height={bb[3] - bb[1]} fill={`url(#${id}-x-${s.from})`} />
                  </mask>
                  <mask id={`${id}-my-${s.from}`} style={{ maskType: "alpha" }} maskUnits="userSpaceOnUse" x={bb[0]} y={bb[1]} width={bb[2] - bb[0]} height={bb[3] - bb[1]}>
                    <rect x={bb[0]} y={bb[1]} width={bb[2] - bb[0]} height={bb[3] - bb[1]} fill={`url(#${id}-y-${s.from})`} />
                  </mask>
                </React.Fragment>
              );
            })}
          </defs>
          <g transform={`translate(${boxW / 2} ${boxH / 2}) scale(${k}) translate(${-cx} ${-cy})`}>
            <path d={m.land} fill={INK} fillOpacity={0.05 * draw} stroke="none" />
            {m.regions.map((r, i) => (
              <path key={i} d={r} fill={INK} fillOpacity={0.14 * tint} stroke="none" />
            ))}
            {/* the occupied territories: a low accent tint and a fine hatch, part of Georgia (no thick border) */}
            {(m.occupied ?? []).map((o) => (
              <g key={o.id} opacity={occT}>
                <path d={o.path} fill={RED} fillOpacity={0.16} stroke="none" />
                <path d={o.path} fill={`url(#${hatch})`} fillOpacity={0.5} stroke="none" />
              </g>
            ))}
            <g clipPath={`url(#${clip})`} opacity={lines}>
              {/* the whole country, coarse: lakes and the big roads; it makes way for the fine layers */}
              {ov && overview > 0.01 && (
                <g opacity={overview}>
                  <path d={ov.lakes} fill={INK} fillOpacity={0.1} stroke={INK} strokeOpacity={0.3} strokeWidth={px(1)} strokeLinejoin="round" />
                  <path d={ov.roads} fill="none" stroke={INK} strokeOpacity={0.3} strokeWidth={px(1.3)} strokeLinejoin="round" strokeLinecap="round" />
                </g>
              )}
              <path d={m.rivers} fill="none" stroke={INK} strokeOpacity={0.3 * coarse} strokeWidth={px(2.2)} strokeLinejoin="round"
                strokeLinecap="round" />
              {det && detailA > 0.01 && (
                <g mask={`url(#det-mx-${s.from})`}><g mask={`url(#det-my-${s.from})`}>
                  {det.lakes && <path d={det.lakes} fill={INK} fillOpacity={0.1 * detailA} stroke={INK} strokeOpacity={0.35 * detailA}
                    strokeWidth={px(1)} strokeLinejoin="round" />}
                  {det.rivers?.minor && <path d={det.rivers.minor} fill="none" stroke={INK} strokeOpacity={0.3 * detailB} strokeWidth={px(0.9)}
                    strokeLinejoin="round" strokeLinecap="round" />}
                  {det.rivers?.major && <path d={det.rivers.major} fill="none" stroke={INK} strokeOpacity={0.55 * detailA} strokeWidth={px(1.8)}
                    strokeLinejoin="round" strokeLinecap="round" />}
                  {det.rail && <path d={det.rail} fill="none" stroke={INK} strokeOpacity={0.42 * detailB} strokeWidth={px(1.3)}
                    strokeDasharray={`${px(7)} ${px(5)}`} />}
                  {det.roads?.primary && <path d={det.roads.primary} fill="none" stroke={INK} strokeOpacity={0.34 * detailB} strokeWidth={px(1.1)}
                    strokeLinejoin="round" strokeLinecap="round" />}
                  {det.roads?.trunk && <path d={det.roads.trunk} fill="none" stroke={INK} strokeOpacity={0.55 * detailA} strokeWidth={px(1.6)}
                    strokeLinejoin="round" strokeLinecap="round" />}
                  {det.roads?.motorway && <path d={det.roads.motorway} fill="none" stroke={INK} strokeOpacity={0.75 * detailA} strokeWidth={px(2.4)}
                    strokeLinejoin="round" strokeLinecap="round" />}
                </g></g>
              )}
              {city && cityA > 0.01 && (
                <g mask={`url(#city-mx-${s.from})`}><g mask={`url(#city-my-${s.from})`}>
                  {city.districts.map((d) => (
                    <path key={d.id} d={d.path} fill={INK} fillOpacity={d.named ? 0.16 * cityA : 0} stroke={INK}
                      strokeOpacity={(d.named ? 0.6 : 0.22) * cityA} strokeWidth={px(d.named ? 2.2 : 1.1)} strokeLinejoin="round"
                      strokeDasharray={d.named ? undefined : `${px(7)} ${px(5)}`} />
                  ))}
                  {city.lakes && <path d={city.lakes} fill={INK} fillOpacity={0.1 * cityA} stroke={INK} strokeOpacity={0.3 * cityA}
                    strokeWidth={px(1)} strokeLinejoin="round" />}
                  {city.rail && <path d={city.rail} fill="none" stroke={INK} strokeOpacity={0.3 * cityA} strokeWidth={px(1.3)}
                    strokeDasharray={`${px(7)} ${px(5)}`} />}
                  {city.streams && <path d={city.streams} fill="none" stroke={INK} strokeOpacity={0.2 * cityB} strokeWidth={px(0.9)}
                    strokeLinejoin="round" strokeLinecap="round" />}
                  {city.rivers && <path d={city.rivers} fill="none" stroke={INK} strokeOpacity={0.45 * cityA} strokeWidth={px(3)}
                    strokeLinejoin="round" strokeLinecap="round" />}
                  {city.streets.secondary && <path d={city.streets.secondary} fill="none" stroke={INK} strokeOpacity={0.24 * cityB}
                    strokeWidth={px(0.9)} strokeLinejoin="round" strokeLinecap="round" />}
                  {city.streets.primary && <path d={city.streets.primary} fill="none" stroke={INK} strokeOpacity={0.42 * cityB}
                    strokeWidth={px(1.5)} strokeLinejoin="round" strokeLinecap="round" />}
                  {city.streets.trunk && <path d={city.streets.trunk} fill="none" stroke={INK} strokeOpacity={0.7 * cityA}
                    strokeWidth={px(2.4)} strokeLinejoin="round" strokeLinecap="round" />}
                  {city.metro && <path d={city.metro} fill="none" stroke={INK} strokeOpacity={0.8 * cityA} strokeWidth={px(2.6)}
                    strokeLinejoin="round" strokeLinecap="round" strokeDasharray={`${px(2.6)} ${px(4)}`} />}
                  {(city.stations ?? []).map((p, i) => (
                    <circle key={i} cx={p[0]} cy={p[1]} r={px(4)} fill={CANVAS} stroke={INK} strokeOpacity={0.8 * cityA}
                      strokeWidth={px(1.6)} opacity={cityA} />
                  ))}
                </g></g>
              )}
            </g>
            <path d={m.borders} fill="none" stroke={LINE_STRONG} strokeWidth={px(2)} strokeDasharray={`${px(8)} ${px(6)}`}
              opacity={lines} />
            {(m.occupied ?? []).map((o) => (
              // the same thin line as the other regions' (they are Georgia's: no thick border)
              <path key={o.id} d={o.path} fill="none" stroke={LINE_STRONG} strokeWidth={px(2)} strokeDasharray={`${px(8)} ${px(6)}`}
                strokeLinejoin="round" opacity={occT} />
            ))}
            {m.regions.map((r, i) => (
              <path key={i} d={r} fill="none" stroke={INK} strokeWidth={px(4)} strokeLinejoin="round" opacity={tint} />
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
      {/* the occupied territories' labels, over the (masked) map and clear of it */}
      <svg width={boxW} height={boxH} viewBox={`0 0 ${boxW} ${boxH}`} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}>
        {labels.map(({ o, A, R, vis, inside }) => {
          const o2 = vis * (1 - inside);
          if (o2 < 0.02) return null;
          const ex = Math.max(R.x, Math.min(A[0], R.x + R.w)), ey = Math.max(R.y, Math.min(A[1], R.y + R.h));
          return (
            <g key={o.id} opacity={o2}>
              <line x1={A[0]} y1={A[1]} x2={ex} y2={ey} stroke={INK} strokeOpacity={0.6} strokeWidth={1.5} />
              <circle cx={A[0]} cy={A[1]} r={3.5} fill={INK} />
            </g>
          );
        })}
      </svg>
      {labels.map(({ o, lines: ls, A, R, u, vis, inside, size }) => {
        const out = vis * (1 - inside), inn = vis * inside;
        const align = u[0] > 0.35 ? "left" : u[0] < -0.35 ? "right" : "center";
        const text = (x: number, y: number, w: number, al: "left" | "right" | "center", sz: number, op: number, key: string) => (
          op < 0.02 ? null : (
            <div key={key} style={{ position: "absolute", left: x, top: y, width: w, textAlign: al, opacity: op, fontFamily: FONT,
              fontWeight: 600, fontSize: sz, lineHeight: 1.18, color: INK, whiteSpace: "nowrap",
              // a canvas halo keeps the text clear of the lines under it (not a shadow)
              WebkitTextStroke: `6px ${CANVAS}`, paintOrder: "stroke fill" }}>
              {ls.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          )
        );
        return (
          <React.Fragment key={o.id}>
            {text(R.x, R.y, R.w, align, LS, out, "out")}
            {text(A[0] - 200, A[1] - (ls.length * size * 1.18) / 2, 400, "center", size, inn, "in")}
          </React.Fragment>
        );
      })}
      </div>
      {/* the boundary data's licence asks for a credit: small, under the map, left of the rail */}
      <div style={{ width: textW, height: 28, textAlign: "right", fontFamily: FONT, fontWeight: 400, fontSize: 24, lineHeight: 1.2,
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
      {s.sub && (
        <In delay={14} at={beat(s, "sub")}>
          <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 40, lineHeight: 1.3, color: MUTED, marginTop: 12,
            maxWidth: textW }}>{marked(s, "sub", s.sub, { px: 44 })}</div>
        </In>
      )}
    </Frame>
  );
};
