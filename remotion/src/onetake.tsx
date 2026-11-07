import React from "react";
import { Freeze, interpolate, useCurrentFrame } from "remotion";
import { evolvePath, getLength, getPointAtLength } from "@remotion/paths";
import { H, INK, LINE, LINE_STRONG, SCENE_BOTTOM, SCENE_TOP, W } from "./brand";
import { motifCell, motifMark } from "./motif";
import type { Camera } from "./types";
import { Dot, useStyle, useTheme } from "./ui";

// The one-take camera (tt_shorts/onetake.py, ROADMAP D5). The scenes sit on one 2D path; the camera moves only in a
// cut window of `cut` frames that starts at the new scene's first frame, and rests everywhere else (offset 0, zoom
// exactly 1), so text never moves while it is read. Everything here is arithmetic on the frame: no clock, no random.
// The chrome (header, ticker, captions, footer) is not inside it: only the scene band rides the camera.

const CY = (SCENE_TOP + SCENE_BOTTOM) / 2; // the camera's centre on screen: the middle of the scene band
const CLIP_TOP = SCENE_TOP - 32; // the same band the loop's cross-fade clips to (outro.tsx LoopBack)

/** Cubic ease in and out, exactly 0 and 1 at the ends (onetake.py ease). */
export const ease = (u: number) => {
  const t = Math.min(1, Math.max(0, u));
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};

/** The camera at an absolute frame: where it looks (a world point, px) and its zoom. The same arithmetic as
 *  onetake.py position(). `froms` is each scene's first frame. */
export const camera = (cam: Camera, froms: number[], frame: number) => {
  let k = 0;
  for (let i = 1; i < froms.length; i++) if (frame >= froms[i]) k = i;
  if (k === 0) return { x: cam.points[0][0], y: cam.points[0][1], zoom: 1, u: 1, k: 0 };
  const c = cam.cuts[k - 1];
  const u = (frame - froms[k]) / cam.cut;
  if (u >= 1) return { x: c.to[0], y: c.to[1], zoom: 1, u: 1, k };
  const e = ease(u);
  return {
    x: c.from[0] + (c.to[0] - c.from[0]) * e,
    y: c.from[1] + (c.to[1] - c.from[1]) * e,
    // a bell over the window, capped (the hard-news ceiling is 1.15)
    zoom: Math.min(cam.zoomCap, 1 + c.zoom * Math.sin(Math.PI * u)),
    u,
    k,
  };
};

const useCam = (frozen = false) => {
  const { props } = useTheme();
  const frame = useCurrentFrame();
  const cam = props.camera as Camera;
  const froms = props.scenes.map((s) => s.from);
  return { cam, froms, ...camera(cam, froms, frozen ? 0 : frame) };
};

/** Around one scene (inside its Sequence): the scene is drawn at its own point of the path, seen through the camera.
 *  `abs` is the absolute frame (the scene's first plus its own), so a frozen scene (the loop's hook) sits at rest. */
export const OneTakeBand: React.FC<{ i: number; children: React.ReactNode }> = ({ i, children }) => {
  const { props } = useTheme();
  const local = useCurrentFrame();
  const cam = props.camera as Camera;
  const froms = props.scenes.map((s) => s.from);
  const c = camera(cam, froms, froms[i] + local);
  const tx = c.zoom * (cam.points[i][0] - c.x);
  const ty = c.zoom * (cam.points[i][1] - c.y);
  const rest = tx === 0 && ty === 0 && c.zoom === 1;
  return (
    <div style={{ position: "absolute", left: 0, top: CLIP_TOP, width: W, height: SCENE_BOTTOM - CLIP_TOP, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: -CLIP_TOP, width: W, height: H, transformOrigin: `${W / 2}px ${CY}px`,
        transform: rest ? undefined : `translate(${tx}px, ${ty}px) scale(${c.zoom})` }}>
        {children}
      </div>
    </div>
  );
};

const bezier = (c: Camera["cuts"][number]) =>
  `M${c.a[0]} ${c.a[1]}C${c.c1[0]} ${c.c1[1]} ${c.c2[0]} ${c.c2[1]} ${c.b[0]} ${c.b[1]}`;

/** The thread and the dot that runs it, over the cut into scene `i` (inside that scene's Sequence, drawn only while
 *  the camera moves). The thread is a bezier from the old scene's edge to the new scene's edge, in the margins where no text is, in world
 *  space, seen through the camera;
 *  the dot runs it ahead of the camera, has arrived a little before the camera does, then is gone: nothing of it stays
 *  at rest. The accent is only the dot. */
export const Thread: React.FC<{ i: number }> = ({ i }) => {
  const { props } = useTheme();
  const f = useCurrentFrame();
  const cam = props.camera as Camera;
  if (f >= cam.cut) return null;
  const froms = props.scenes.map((s) => s.from);
  const c = camera(cam, froms, froms[i] + f);
  const cut = cam.cuts[i - 1];
  const d = bezier(cut);
  const len = getLength(d);
  const dotAt = ease(Math.min(1, c.u * 1.35)); // the dot leads: it reaches the new scene at about 0.74 of the window
  const p = getPointAtLength(d, dotAt * len) ?? { x: cut.b[0], y: cut.b[1] };
  const shown = interpolate(c.u, [0, 0.12, 0.78, 1], [0, 1, 1, 0]);
  const ev = evolvePath(dotAt, d);
  const to = `translate(${W / 2} ${CY}) scale(${c.zoom}) translate(${-c.x} ${-c.y})`;
  const sx = W / 2 + c.zoom * (p.x - c.x), sy = CY + c.zoom * (p.y - c.y);
  return (
    <div style={{ position: "absolute", left: 0, top: CLIP_TOP, width: W, height: SCENE_BOTTOM - CLIP_TOP, overflow: "hidden",
      pointerEvents: "none", opacity: shown }}>
      <svg width={W} height={H} style={{ position: "absolute", left: 0, top: -CLIP_TOP }}>
        <g transform={to} fill="none" strokeLinecap="round">
          <path d={d} stroke={LINE_STRONG} strokeWidth={4} />
          <path d={d} stroke={INK} strokeWidth={4} strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
        </g>
      </svg>
      <div style={{ position: "absolute", left: sx - 10, top: sy - 10 - CLIP_TOP, transform: `scale(${interpolate(c.u, [0.74, 1], [1, 0.4], { extrapolateLeft: "clamp" })})` }}>
        <Dot size={20} />
      </div>
    </div>
  );
};

/** Parallax layers behind the scenes: this video's own motif tiled three more times, farther layers smaller, fainter
 *  and moving less of the camera's move, nearer ones larger and moving more (all less than the scenes themselves).
 *  `frozen` draws them at the first frame's camera (the loop's cross-fade covers the last scene with them). A plain
 *  motif has no marks to tile, so its layers use dots. Colours are the pack's tokens; flat, no shadows. */
const LAYERS = [{ depth: 0.2, size: 0.8, opacity: 0.4 }, { depth: 0.4, size: 1.35, opacity: 0.55 }, { depth: 0.65, size: 2.1, opacity: 0.75 }];

export const Parallax: React.FC<{ frozen?: boolean }> = ({ frozen = false }) => {
  const { motif } = useStyle();
  const { props } = useTheme();
  const { x, y, zoom } = useCam(frozen);
  const kind = motif === "plain" ? "dots" : motif;
  const tile = kind === "icons" ? props.motifIcon : null;
  const base = motifCell(kind, !!tile);
  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {LAYERS.map((l, k) => {
        const cell = base * l.size;
        const z = 1 + (zoom - 1) * l.depth; // a layer feels a share of the zoom too
        const ox = (W / 2 - x * l.depth) % cell, oy = (CY - y * l.depth) % cell;
        return (
          <svg key={k} width={W} height={H} style={{ position: "absolute", left: 0, top: 0, opacity: l.opacity }}>
            <defs>
              <pattern id={`parallax-${k}${frozen ? "f" : ""}`} width={cell} height={cell} patternUnits="userSpaceOnUse"
                patternTransform={`translate(${ox} ${oy}) scale(${z})`}>
                <g transform={`scale(${l.size})`}>{motifMark(kind, base, tile, LINE)}</g>
              </pattern>
            </defs>
            <rect width={W} height={H} fill={`url(#parallax-${k}${frozen ? "f" : ""})`} />
          </svg>
        );
      })}
    </div>
  );
};

/** For the loop's cross-fade: the layers at the first frame, as a frame-0 background. */
export const FrozenParallax: React.FC = () => <Freeze frame={0}><Parallax frozen /></Freeze>;
