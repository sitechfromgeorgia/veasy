// The film's thread (tt_shorts/thread.py): one object in a layer above the scenes. It stands in each scene's seat,
// glides from seat to seat over the cut and changes state. Seats, states and shapes come from Python; every number
// here is a pure function of the frame. No text is ever drawn in this layer.
import { interpolatePath } from "@remotion/paths";
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CANVAS, INK, LINE_STRONG, MUTED, PANEL, RED, SCENE_BOTTOM, SCENE_TOP, W } from "./brand";
import { artNode } from "./scenes/more";
import type { ArtNode, Scene, SceneThread, Thread } from "./types";
import { flowOf, useTheme } from "./ui";

export const CROSS = 7; // frames on each side of a cut the object takes to change seats
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const smooth = (x: number) => x * x * (3 - 2 * x);
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const PAD = 24; // the drawing's strokes reach a little past its silhouette
const GROW_FROM = 0.46; // grow and shrink: the small end, a share of the seat

type Rect = { x: number; y: number; w: number; h: number };
const seatOf = (s?: Scene): SceneThread | undefined => (s?.thread && s.thread.role !== "own" ? s.thread : undefined);
const between = (a: Rect, b: Rect, k: number): Rect => (
  { x: lerp(a.x, b.x, k), y: lerp(a.y, b.y, k), w: lerp(a.w, b.w, k), h: lerp(a.h, b.h, k) });

/** The state's progress in a scene, frame `local` of it: the change takes the scene's middle, the words come first. */
export const threadT = (s: Scene, local: number) => {
  const from = s.thread?.from ?? 0, to = s.thread?.to ?? from;
  return lerp(from, to, smooth(interpolate(local, [s.duration * 0.22, s.duration * 0.82], [0, 1], clamp)));
};

const useColors = (invert = false): Record<string, string> => {
  const ground = useTheme().v === "cards" ? PANEL : CANVAS;
  return invert
    ? { ACCENT: ground, INK: ground, MUTED: ground, LINE: ground, CANVAS: INK, none: "none" }
    : { ACCENT: RED, INK, MUTED, LINE: LINE_STRONG, CANVAS: ground, none: "none" };
};

const Lines: React.FC<{ art: ArtNode[]; drawn: number; invert?: boolean }> = ({ art, drawn, invert = false }) => {
  const colors = useColors(invert);
  const { fps } = useVideoConfig();
  return <>{art.map((n, i) => artNode(n, i, { frame: drawn, fps, k: 0.5, colors }, null))}</>;
};

/** The drawing in its state `t` (0..1), in the drawing's own coordinates. drawn: the frame its strokes draw themselves
 *  on (a large number: it stands). */
const Stateful: React.FC<{ th: Thread; art: ArtNode[]; t: number; drawn: number; id: string }> = ({ th, art, t, drawn, id }) => {
  const [x0, y0, x1, y1] = th.box;
  const cx = (x0 + x1) / 2;
  if (th.state === "drain" || th.state === "fill") {
    const level = interpolatePath(t, th.surface![0], th.surface![1]);
    return (
      <>
        <defs>
          <clipPath id={`${id}s`}><path d={th.outline} /></clipPath>
          <clipPath id={`${id}l`}><path d={level} /></clipPath>
        </defs>
        <Lines art={art} drawn={drawn} />
        <g clipPath={`url(#${id}s)`}>
          <g clipPath={`url(#${id}l)`}>
            <rect x={x0 - PAD} y={y0 - PAD} width={x1 - x0 + 2 * PAD} height={y1 - y0 + 2 * PAD} fill={INK} />
            <Lines art={art} drawn={drawn} invert />
          </g>
        </g>
      </>
    );
  }
  if (th.state === "break") {
    const c = th.crack!;
    const run = smooth(interpolate(t, [0, 0.4], [0, 1], clamp));
    const part = smooth(interpolate(t, [0.35, 1], [0, 1], clamp));
    const crack = interpolatePath(run, c.straight, c.jag);
    const gap = (x1 - x0) * 0.09 * part;
    const tilt = 5 * part;
    const side = (key: string, d: string, dir: number) => (
      <g key={key} transform={`translate(${dir * gap} ${part * 6}) rotate(${dir * tilt} ${cx} ${y1})`}>
        <defs><clipPath id={`${id}${key}`}><path d={d} /></clipPath></defs>
        <g clipPath={`url(#${id}${key})`}>
          <Lines art={art} drawn={drawn} />
          <path d={crack} fill="none" stroke={INK} strokeWidth={6} strokeLinejoin="round" pathLength={1}
            strokeDasharray={1} strokeDashoffset={1 - run} />
        </g>
      </g>
    );
    return <>{side("a", c.left, -1)}{side("b", c.right, 1)}</>;
  }
  if (th.state === "grow" || th.state === "shrink") {
    const k = th.state === "grow" ? lerp(GROW_FROM, 1, t) : lerp(1, GROW_FROM, t);
    return <g transform={`translate(${cx} ${y1}) scale(${k}) translate(${-cx} ${-y1})`}><Lines art={art} drawn={drawn} /></g>;
  }
  return <Lines art={art} drawn={drawn} />;
};

const viewOf = (th: Thread) => {
  const [x0, y0, x1, y1] = th.box;
  return `${x0 - PAD} ${y0 - PAD} ${x1 - x0 + 2 * PAD} ${y1 - y0 + 2 * PAD}`;
};

/** The object as an inline SVG: the draw scene, when its drawing is the object. */
export const ObjectArt: React.FC<{ th: Thread; art: ArtNode[]; t: number; drawn: number; id: string; width: number; height: number }> = (
  { th, art, t, drawn, id, width, height },
) => (
  <svg width={width} height={height} viewBox={viewOf(th)} fill="none" strokeLinecap="round" strokeLinejoin="round"
    style={{ overflow: "visible", flex: "none" }}>
    <Stateful th={th} art={art} t={t} drawn={drawn} id={id} />
  </svg>
);

const At: React.FC<{ th: Thread; r: Rect; opacity?: number; children: React.ReactNode }> = ({ th, r, opacity = 1, children }) => (
  <svg width={r.w} height={r.h} viewBox={viewOf(th)} fill="none" strokeLinecap="round" strokeLinejoin="round"
    style={{ position: "absolute", left: r.x, top: r.y, overflow: "visible", opacity }}>{children}</svg>
);

/** A shape in the object's place: the silhouette on its way to the next scene's opening form (the match cut). */
const Shape: React.FC<{ th: Thread; r: Rect; d: string; opacity?: number }> = ({ th, r, d, opacity = 1 }) => (
  <At th={th} r={r} opacity={opacity}><path d={d} fill={INK} /></At>
);

/** Where the object is during the `object` cut, 0 (off one edge) to 1 (off the other), or null outside it. */
export const sweepOf = (frame: number, s: Scene, last: boolean) => {
  const tail = s.duration - frame;
  if (!last && tail <= CROSS) return 0.5 * (1 - tail / CROSS);
  if (frame < CROSS) return 0.5 + 0.5 * (frame / CROSS);
  return null;
};

const CARRIER_H = 0.66; // of the scene band: the object's size as it carries the cut

/** The object as it carries the cut: it crosses the band, its body hiding the swap. */
const Carrier: React.FC<{ th: Thread; art: ArtNode[]; sweep: number; fx: number; t: number }> = ({ th, art, sweep, fx, t }) => {
  const ground = useColors().CANVAS;
  const [x0, y0, x1, y1] = th.box;
  const band = SCENE_BOTTOM - SCENE_TOP;
  const h = band * CARRIER_H, w = Math.min(h * ((x1 - x0) / (y1 - y0)), W * 1.1);
  const run = W + w;
  const x = fx >= 0 ? -w + run * sweep : W - run * sweep;
  return (
    <At th={th} r={{ x, y: SCENE_TOP + (band - h) / 2, w, h }}>
      <path d={th.outline} fill={ground} stroke={INK} strokeWidth={5} />
      <Stateful th={th} art={art} t={t} drawn={1e6} id="carry" />
    </At>
  );
};

export const ThreadLayer: React.FC = () => {
  const { props } = useTheme();
  const frame = useCurrentFrame();
  const th = props.thread;
  if (!th) return null;
  const scenes = props.scenes;
  const i = scenes.findIndex((s) => frame >= s.from && frame < s.from + s.duration);
  const s = scenes[i];
  const here = seatOf(s);
  if (!s || (!here && props.transition !== "object")) return null;
  const prev = seatOf(scenes[i - 1]), next = seatOf(scenes[i + 1]);
  const local = frame - s.from, tail = s.duration - local;
  const end = i === scenes.length - 1;
  const leaving = !end && tail <= CROSS, arriving = i > 0 && local < CROSS;
  const t = threadT(s, local);
  const first = scenes.findIndex((x) => seatOf(x)) === i;
  const drawn = first ? local + (i === 0 ? 14 : 0) : 1e6; // the opening: it is half drawn at frame 0
  const fill = (children: React.ReactNode) => <AbsoluteFill style={{ pointerEvents: "none" }}>{children}</AbsoluteFill>;
  if (props.transition === "object") {
    const sweep = sweepOf(local, s, end);
    const [fx] = flowOf(props.style, [1, 0]);
    const shown = i === 0 ? 1 : interpolate(local, [CROSS, CROSS + 6], [0, 1], clamp);
    return fill(
      <>
        {here && (
          <At th={th} r={here} opacity={shown * interpolate(tail, [CROSS, CROSS + 4], [0, 1], clamp)}>
            <Stateful th={th} art={th.art} t={t} drawn={drawn} id="seat" />
          </At>
        )}
        {sweep !== null && !(i === 0 && sweep >= 0.5) ? <Carrier th={th} art={th.art} sweep={sweep} fx={fx} t={t} /> : null}
      </>,
    );
  }
  if (!here) return null;
  if (props.transition === "match" && (leaving || (arriving && prev))) {
    const form = (x: SceneThread | undefined) => th.forms[x?.form ?? "circle"];
    if (leaving) {
      const p = smooth(interpolate(tail, [CROSS, 0], [0, 1], clamp));
      const r = next ? between(here, next, p * 0.5) : here;
      return fill(<Shape th={th} r={r} d={interpolatePath(p, th.main, form(next))} opacity={next ? 1 : 1 - p * 0.5} />);
    }
    const p = smooth(interpolate(local, [0, CROSS], [0, 1], clamp));
    return fill(
      <>
        <At th={th} r={here} opacity={p}><Stateful th={th} art={th.art} t={t} drawn={1e6} id="seat" /></At>
        <Shape th={th} r={between(prev!, here, 0.5 + p * 0.5)} d={interpolatePath(p, form(here), th.main)} opacity={1 - p} />
      </>,
    );
  }
  let r: Rect = here, opacity = 1;
  if (leaving) {
    if (next) r = between(here, next, smooth(interpolate(tail, [CROSS, 0], [0, 1], clamp)) * 0.5);
    else {
      opacity = interpolate(tail, [CROSS, 0], [1, 0], clamp);
      r = { ...here, y: here.y + (1 - opacity) * 40 };
    }
  } else if (arriving) {
    if (prev) r = between(prev, here, 0.5 + 0.5 * smooth(interpolate(local, [0, CROSS], [0, 1], clamp)));
    else if (!first) {
      opacity = interpolate(local, [0, CROSS], [0, 1], clamp);
      r = { ...here, y: here.y + (1 - opacity) * 40 };
    }
  }
  return fill(<At th={th} r={r} opacity={opacity}><Stateful th={th} art={th.art} t={t} drawn={drawn} id="seat" /></At>);
};
