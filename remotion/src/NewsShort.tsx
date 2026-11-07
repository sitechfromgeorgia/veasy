import React, { useMemo } from "react";
import { AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import {
  alpha, applyBrand, CANVAS, CAPTION_BOTTOM, fill, FONT, GRID, H, INK, LINE, MUTED, PANEL, RADIUS, RAIL_X, SCENE_BOTTOM, SCENE_TOP,
  SIDE, TICKER, W,
} from "./brand";
import { Captions } from "./Captions";
import { useFontsLoaded } from "./fonts";
import { LoopBack, loopSpeed, musicLevel, OutroChip, SwipeSlot } from "./outro";
import { FrozenParallax, OneTakeBand, Parallax, Thread } from "./onetake";
import { motifCell, motifMark } from "./motif";
import { SCENES } from "./scenes";
import type { Scene, ShortProps, Transition } from "./types";
import { Probe } from "./Probe";
import { sweepOf, ThreadLayer } from "./thread";
import { VignetteLayer } from "./vignette";
import { Chip, Dot, flowOf, Logo, measure, Theme, useStyle, useTheme } from "./ui";

const EXIT = 7; // frames a scene takes to leave
const CARD_PAD = 48;

/** The canvas and its texture, drifting slowly: this video's motif (grid, diagonal, dots, rules, plain or the story's
 *  own icon tiled), always in the pack's faint grid color. */
export const Background: React.FC = () => {
  const { motif } = useStyle();
  const { props } = useTheme();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const tile = motif === "icons" ? props.motifIcon : null;
  const cell = motifCell(motif, !!tile);
  const pan = interpolate(frame, [0, durationInFrames], [0, cell]);
  const mark = motifMark(motif, cell, tile);
  return (
    <AbsoluteFill style={{ background: CANVAS }}>
      <svg width={W} height={H + cell} style={{ position: "absolute", top: -cell + pan }}>
        <defs>
          <pattern id="g" width={cell} height={cell} patternUnits="userSpaceOnUse">{mark}</pattern>
        </defs>
        <rect width={W} height={H + cell} fill="url(#g)" />
      </svg>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 36%, ${alpha(CANVAS, 0)} 45%, ${alpha(CANVAS, 0.9)} 100%)` }} />
    </AbsoluteFill>
  );
};

/** Brand, date, weekday, time and category; the rule fills as the video plays, the red dot is "now". */
const Header: React.FC = () => {
  const { props } = useTheme();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const x = (W - 2 * SIDE) * (frame / Math.max(1, durationInFrames - 1));
  return (
    <>
      <div data-probe="header" style={{ position: "absolute", left: SIDE, top: 80, height: 88, display: "flex", alignItems: "center" }}>
        <Logo place="header" size={88} />
      </div>
      <div data-probe="header" style={{ position: "absolute", right: SIDE, top: 80, textAlign: "right", fontFamily: FONT }}>
        <div style={{ fontWeight: 700, fontSize: 40, lineHeight: 1.2, color: INK }}>{props.date.date}</div>
        <div style={{ fontWeight: 400, fontSize: 30, lineHeight: 1.4, color: MUTED }}>
          {props.date.weekday} · {props.date.time} · {props.category}
        </div>
      </div>
      {props.chapters && props.chapters.length > 1 ? <ChapterBar chapters={props.chapters} /> : (
        <>
          <div style={{ position: "absolute", left: SIDE, right: SIDE, top: 204, height: 4, background: LINE }} />
          <div style={{ position: "absolute", left: SIDE, top: 204, height: 4, width: x, background: INK }} />
          <div style={{ position: "absolute", left: SIDE + x - 10, top: 196 }}><Dot size={20} /></div>
        </>
      )}
    </>
  );
};

const two = (n: number) => String(n).padStart(2, "0");

/** The chapters (tt_shorts/chapters.py), where the progress rule was: "01 / 03" and one segment a chapter, as long
 *  as the chapter; past ones full ink, the current one filling, the accent dot at its head ("now"). */
const ChapterBar: React.FC<{ chapters: { from: number; to: number }[] }> = ({ chapters }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const k = chapters.reduce((a, c, i) => (frame >= c.from ? i : a), 0);
  const gap = 12, label = 132;
  const left = SIDE + label, width = W - SIDE - left - gap * (chapters.length - 1);
  const total = Math.max(1, chapters[chapters.length - 1].to - chapters[0].from);
  let x = left, head = left;
  const segs = chapters.map((c, i) => {
    const w = (width * (c.to - c.from)) / total;
    const done = interpolate(frame, [c.from, Math.min(c.to, durationInFrames) - 1], [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    const seg = { x, w, done };
    if (i === k) head = x + w * done;
    x += w + gap;
    return seg;
  });
  // the number changes with a short lift as a chapter begins
  const lift = interpolate(frame - chapters[k].from, [0, 8], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <>
      <div data-probe="header" style={{ position: "absolute", left: SIDE, top: 188, height: 36, display: "flex", alignItems: "center",
        fontFamily: FONT, fontWeight: 700, fontSize: 30, lineHeight: 1, whiteSpace: "nowrap" }}>
        <span style={{ color: INK, display: "inline-block", transform: `translateY(${lift * 8}px)`, opacity: 1 - lift * 0.6 }}>{two(k + 1)}</span>
        <span style={{ color: MUTED }}>{` / ${two(chapters.length)}`}</span>
      </div>
      {segs.map((sg, i) => (
        <React.Fragment key={i}>
          <div style={{ position: "absolute", left: sg.x, top: 204, height: 4, width: sg.w, background: LINE, borderRadius: 2 }} />
          <div style={{ position: "absolute", left: sg.x, top: 204, height: 4, width: sg.w * sg.done, background: INK, borderRadius: 2 }} />
        </React.Fragment>
      ))}
      <div style={{ position: "absolute", left: head - 10, top: 196 }}><Dot size={20} /></div>
    </>
  );
};

/** The cut between scenes, drawn over the new scene: "line" sweeps an ink line with the dot across, "panel" wipes an
 *  ink panel through (kinetic's own), "shutter" sweeps horizontal ink slats, "blind" rotates vertical slats.
 *  The other transitions move the scene itself (sceneMotion). */
const Cut: React.FC = () => {
  const frame = useCurrentFrame();
  const { props } = useTheme();
  const tr = props.transition ?? "line";
  const n = enterFrames(props);
  if (tr === "meter") return frame > n + METER_STAGGER ? null : <Meter t={frame} n={n} fall />;
  if (tr === "shutter") {
    if (frame > n + 6) return null;
    const band = SCENE_BOTTOM - SCENE_TOP;
    const slats = 6;
    const h = band / slats;
    const [fx] = flowOf(props.style, [1, 0]);
    return (
      <div style={{ position: "absolute", left: 0, top: SCENE_TOP, width: W, height: band, overflow: "hidden", pointerEvents: "none" }}>
        {Array.from({ length: slats }).map((_, i) => {
          const delay = (i * 4) / slats;
          const p = interpolate(frame - delay, [0, n], [1, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
            easing: (x) => 1 - Math.pow(1 - x, 3),
          });
          const x = fx < 0 ? (1 - p) * -W : (1 - p) * W;
          return (
            <div key={i} style={{
              position: "absolute", left: x, top: i * h, width: W, height: h + 1,
              background: INK,
            }} />
          );
        })}
      </div>
    );
  }
  if (tr === "blind") {
    if (frame > n + 6) return null;
    const band = SCENE_BOTTOM - SCENE_TOP;
    const count = 8;
    const gap = 8;
    const w = (W - 2 * SIDE - gap * (count - 1)) / count;
    const [fx] = flowOf(props.style, [1, 0]);
    return (
      <div style={{ position: "absolute", left: 0, top: SCENE_TOP, width: W, height: band, overflow: "hidden", pointerEvents: "none" }}>
        {Array.from({ length: count }).map((_, i) => {
          const order = fx < 0 ? count - 1 - i : i;
          const delay = (order * 5) / count;
          const p = interpolate(frame - delay, [0, n], [1, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
            easing: (x) => 1 - Math.pow(1 - x, 3),
          });
          return (
            <div key={i} style={{
              position: "absolute", left: SIDE + i * (w + gap), top: 0, width: w * p, height: band,
              background: INK, transformOrigin: fx < 0 ? "right center" : "left center",
            }} />
          );
        })}
      </div>
    );
  }
  if (frame > n || (tr !== "line" && tr !== "panel")) return null;
  const [fx, fy] = flowOf(props.style, [1, 0]); // the sweep moves along the director's current (today: to the right)
  const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
  const band = SCENE_BOTTOM - SCENE_TOP;
  if (fy !== 0) { // the current is up: the panel and the line rise through the scene band
    const y = interpolate(frame, [0, n], [band, -band], clamp) * -fy;
    if (tr === "panel") {
      return (
        <div style={{ position: "absolute", left: 0, top: SCENE_TOP, width: W, height: band, overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 0, top: y, width: W, height: band, background: INK }} />
        </div>
      );
    }
    return (
      <div style={{ position: "absolute", left: SIDE, right: SIDE, top: interpolate(frame, [0, n], [SCENE_BOTTOM, SCENE_TOP - 24], clamp),
        display: "flex", alignItems: "center" }}>
        <div style={{ flex: 1, height: 4, background: INK }} /><Dot size={20} />
      </div>
    );
  }
  const x = interpolate(frame, [0, n], [-W, W], clamp) * fx;
  if (tr === "panel") {
    return <div style={{ position: "absolute", left: x, top: SCENE_TOP, width: W, height: SCENE_BOTTOM - SCENE_TOP, background: INK }} />;
  }
  return ( // the dot leads the line
    <div style={{ position: "absolute", left: x, top: SCENE_TOP - 24, width: W, display: "flex", alignItems: "center",
      flexDirection: fx < 0 ? "row-reverse" : "row" }}>
      <div style={{ flex: 1, height: 4, background: INK }} /><Dot size={20} />
    </div>
  );
};

const METER_BARS = 14;
const METER_STAGGER = 6; // frames between the first bar's move and the last's
// each bar's peak, a share of the scene band: an equaliser's uneven row (fixed, so every render draws the same)
const METER_PEAKS = [0.72, 0.94, 0.81, 1, 0.66, 0.9, 0.78, 0.97, 0.7, 0.88, 1, 0.75, 0.92, 0.8];

/** The meter wipe (transition "meter"): equaliser bars in ink rise from the bottom of the scene band over the old
 *  scene's last frames, then fall away from the new one, each bar a little after its neighbour. `t` counts frames
 *  into the rise (the old scene's exit) or the fall (the new scene's entrance); `n` is how long each takes. */
const Meter: React.FC<{ t: number; n: number; fall?: boolean; stagger?: number }> = ({ t, n, fall = false, stagger = METER_STAGGER }) => {
  const [fx] = flowOf(useTheme().props.style, [1, 0]); // the bars ripple along the current (today: left to right)
  const band = SCENE_BOTTOM - SCENE_TOP;
  const gap = 12;
  const w = (W - 2 * SIDE - gap * (METER_BARS - 1)) / METER_BARS;
  return (
    <div style={{ position: "absolute", left: 0, top: SCENE_TOP, width: W, height: band, overflow: "hidden", pointerEvents: "none" }}>
      {METER_PEAKS.map((peak, i) => {
        const order = fx < 0 ? METER_BARS - 1 - i : i;
        const delay = (order * stagger) / (METER_BARS - 1);
        const p = interpolate(t - delay, [0, n], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
          easing: (x) => (fall ? x * x : 1 - Math.pow(1 - x, 3)) });
        const h = band * peak * (fall ? 1 - p : p);
        return <div key={i} style={{ position: "absolute", left: SIDE + i * (w + gap), bottom: 0, width: w, height: h,
          background: INK, borderRadius: "6px 6px 0 0" }} />;
      })}
    </div>
  );
};

/** The meter's rise, over the outgoing scene's exit (after its settled frame: the probe and the stills never see
 *  it); its fall is the next scene's Cut. */
const MeterRise: React.FC<{ duration: number }> = ({ duration }) => {
  const frame = useCurrentFrame();
  const from = duration - EXIT;
  return frame < from ? null : <Meter t={frame - from} n={EXIT - 3} stagger={3} />;
};

const ENTER = 10; // frames a scene takes to come in (a director's motion.enter_frames replaces it)
const enterFrames = (p: ShortProps) => p.style?.motion?.enter_frames ?? ENTER;

/** How the scene itself enters and leaves for a transition (frame is the scene's own, left is the slot's x).
 *  wipe: revealed left to right · slide: a short slide and fade · push: the old scene leaves left, the new one
 *  comes from the right · dot: an iris opens from the header's progress dot · cut, line, panel: the scene fades out. */
const sceneMotion = (tr: Transition, frame: number, s: Scene, first: boolean, last: boolean, total: number, left: number,
  p: ShortProps) => {
  const ease = (t: number) => 1 - Math.pow(1 - t, 3);
  const enter = first ? 1 : ease(interpolate(frame, [0, enterFrames(p)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const out = last || tr === "cut" || tr === "one-take" ? 1 // one-take: the camera carries the old scene away, it doesn't fade
    : interpolate(frame, [s.duration - EXIT, s.duration], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const style: React.CSSProperties = {};
  let dx = 0, opacity = out, dy = (1 - out) * -48;
  // a director's current moves every directional cut one way; without one, today's: wipe to the right, slide and
  // push to the left
  const [wx, wy] = flowOf(p.style, [1, 0]);
  const [mx, my] = flowOf(p.style, [-1, 0]);
  if (tr === "wipe" && enter < 1) {
    const k = `${(1 - enter) * 100}%`;
    style.clipPath = wy !== 0 ? `inset(${k} 0 0 0)` : wx < 0 ? `inset(0 0 0 ${k})` : `inset(0 ${k} 0 0)`;
  }
  if (tr === "split" && enter < 1) {
    const k = `${(1 - enter) * 50}%`;
    style.clipPath = `inset(0 ${k} 0 ${k})`;
  }
  if (tr === "corner" && enter < 1) {
    const k = enter * 200;
    style.clipPath = wx < 0
      ? `polygon(100% 0, ${100 - k}% 0, 100% ${k}%)`
      : `polygon(0 0, ${k}% 0, 0 ${k}%)`;
  }
  if (tr === "iris" && enter < 1) {
    const cx = (W - 2 * left) / 2;
    const cy = (SCENE_BOTTOM - SCENE_TOP) / 2;
    style.clipPath = `circle(${enter * 1200}px at ${cx}px ${cy}px)`;
  }
  if (tr === "fade") {
    opacity = Math.min(enter, out);
    dy = 0;
  }
  if (tr === "object") { // the object's body carries the cut (thread.tsx): the old scene goes behind it, the new one comes
    const sweep = sweepOf(frame, s, last);
    const [ox] = flowOf(p.style, [1, 0]);
    if (sweep !== null) {
      const k = Math.abs(sweep - 0.5) * 200; // how much of the band the scene shows on its side of the object
      if (sweep < 0.5) style.clipPath = ox >= 0 ? `inset(0 0 0 ${100 - k}%)` : `inset(0 ${100 - k}% 0 0)`;
      else if (!first) style.clipPath = ox >= 0 ? `inset(0 ${100 - k}% 0 0)` : `inset(0 0 0 ${100 - k}%)`;
    }
    opacity = 1;
    dy = 0;
  }
  const along = (d: number) => -(1 - enter) * d + (1 - out) * d; // comes in from behind, leaves ahead
  if (tr === "slide") { dx = along(160) * mx; dy = along(160) * my; opacity = Math.min(enter, out); }
  if (tr === "push") { dx = along(W) * mx; dy = along(SCENE_BOTTOM - SCENE_TOP) * my; opacity = 1; }
  if (tr === "dot" && enter < 1) {
    const x = SIDE + (W - 2 * SIDE) * ((s.from + frame) / Math.max(1, total - 1)) - left; // the progress dot
    style.clipPath = `circle(${enter * 1600}px at ${x}px ${206 - SCENE_TOP}px)`;
  }
  return { style, dx, dy, opacity, enter, out };
};

/** A scene on the one-take path is seen through the camera (onetake.tsx); every other cut draws it where it is. */
const SceneSlot: React.FC<{ i: number }> = ({ i }) => {
  const { props } = useTheme();
  return props.transition === "one-take" && props.camera ? <OneTakeBand i={i}><SceneBody i={i} /></OneTakeBand> : <SceneBody i={i} />;
};

const SceneBody: React.FC<{ i: number }> = ({ i }) => {
  const { v, props } = useTheme();
  const s = props.scenes[i];
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const Comp = SCENES[s.type];
  const first = i === 0, last = i === props.scenes.length - 1;
  const tr = props.transition ?? "line";
  if (v === "cards" && s.type !== "end") {
    const left = SIDE - 16;
    const m = sceneMotion(tr, frame, s, first, last, durationInFrames, left, props);
    const own = tr === "line" || tr === "cut" || tr === "panel" || tr === "meter" || tr === "fade" || tr === "shutter" || tr === "blind" || tr === "match"; // the card's own entrance: it rises and settles
    const enter = own && !first ? interpolate(frame, [0, enterFrames(props)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: (t) => 1 - Math.pow(1 - t, 3) }) : 1; // the first card is there at frame 0 (outro.tsx: the opening)
    const shown = Math.min(enter, m.opacity);
    return (
      <div data-probe="card" style={{ position: "absolute", left, right: SIDE - 16, top: SCENE_TOP, bottom: H - SCENE_BOTTOM, background: PANEL,
        border: `2px solid ${LINE}`, borderRadius: RADIUS, opacity: shown, ...m.style,
        transform: `translate(${m.dx}px, ${(1 - enter) * 120 + m.dy * (40 / 48)}px) scale(${own ? 0.96 + 0.04 * Math.min(enter, m.out) : 1})` }}>
        <div data-probe="scene" style={{ position: "absolute", left: CARD_PAD, right: CARD_PAD, top: CARD_PAD, bottom: 120 }}>
          {Comp ? <Comp s={s} inner={W - 2 * (SIDE - 16) - 2 * CARD_PAD} /> : null}
        </div>
        {/* the page count ends left of the like/share rail (the layout probe found it under the buttons) */}
        <div style={{ position: "absolute", left: CARD_PAD, right: CARD_PAD, bottom: 40, borderTop: `2px solid ${LINE}`, paddingTop: 20,
          paddingRight: Math.max(0, W - left - CARD_PAD - RAIL_X),
          display: "flex", justifyContent: "space-between", fontFamily: FONT, fontSize: 30, color: MUTED }}>
          <span>{fill(props.brand.strings.card_meta, { n: props.sources.length, time: props.date.time })}</span>
          <span>{i + 1} / {props.scenes.filter((x) => x.type !== "end").length}</span>
        </div>
      </div>
    );
  }
  const m = sceneMotion(tr, frame, s, first, last, durationInFrames, SIDE, props);
  return (
    <div data-probe="scene" style={{ position: "absolute", left: SIDE, right: SIDE, top: SCENE_TOP, height: SCENE_BOTTOM - SCENE_TOP, opacity: m.opacity,
      transform: `translate(${m.dx}px, ${m.dy}px)`, ...m.style }}>
      {Comp ? <Comp s={s} /> : null}
    </div>
  );
};

/** The band the platforms cover with their own UI: no story text there, only motion that fills it. */
const Ticker: React.FC = () => {
  const { v, props } = useTheme();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const rows = [[props.category, props.date.date, ...props.sources, props.brand.label].join("  ·  ")];
  const base = v === "kinetic" ? 4 : 2.2;
  return (
    <div data-probe="ticker" style={{ position: "absolute", left: 0, right: 0, top: CAPTION_BOTTOM + 28, height: 180, overflow: "hidden" }}>
      {props.previewNote && (
        <div style={{ position: "absolute", right: SIDE, top: 0, zIndex: 1 }}><Chip size={26}>{props.previewNote}</Chip></div>
      )}
      {rows.map((r, i) => {
        const unit = (measure(`${r}  ·  `, 700) * 128) / 100;
        const speed = loopSpeed(props, base, unit, durationInFrames); // a loop's ticker ends where it began
        const x = i === 0 ? -((frame * speed) % unit) : -unit + ((frame * speed) % unit);
        return (
          <div key={i} style={{ position: "absolute", top: 44, left: x, whiteSpace: "pre", fontFamily: FONT, fontWeight: 700,
            fontSize: 128, lineHeight: 1, color: TICKER }}>{[r, r, r, r].join("  ·  ")}</div>
        );
      })}
    </div>
  );
};

/** Source and link: always on screen (the brand's rule: the source and the time are always visible). */
const Footer: React.FC = () => {
  const { props } = useTheme();
  // one line always: a long link (a slug) gets smaller, never wraps into the frame's edge
  const right = (measure(props.brand.footer.text, 400) + measure(props.brand.footer.strong ?? "", 700)) * 0.28 + 32;
  const urlSize = Math.max(22, Math.min(36, Math.floor((100 * (W - 2 * SIDE - right)) / Math.max(1, measure(props.url, 700)))));
  return (
    <div data-probe="footer" style={{ position: "absolute", left: SIDE, right: SIDE, top: 1768, borderTop: `2px solid ${LINE}`, paddingTop: 16, fontFamily: FONT }}>
      <div style={{ fontWeight: 400, fontSize: 28, lineHeight: 1.4, color: MUTED, whiteSpace: "nowrap", overflow: "hidden" }}>{props.sourcesLine}</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontWeight: 700, fontSize: urlSize, lineHeight: 1.4, color: INK, whiteSpace: "nowrap" }}>{props.url}</span>
        {/* the pack's line, quieter than the story's link (tbilisi.today: "SiTech-ის პროექტი · sitech.ge") */}
        <span style={{ fontSize: 28, lineHeight: 1.4, color: MUTED, whiteSpace: "nowrap" }}>
          {props.brand.footer.text}
          {props.brand.footer.strong && <span style={{ fontWeight: 700, color: INK }}>{props.brand.footer.strong}</span>}
        </span>
      </div>
    </div>
  );
};

export const NewsShort: React.FC<ShortProps> = (props) => {
  applyBrand(props.brand); // before anything below reads a color
  const theme = useMemo(() => ({ v: props.variant, props }), [props]);
  const { durationInFrames, fps } = useVideoConfig();
  const fonts = useFontsLoaded();
  const oneTake = props.transition === "one-take" && !!props.camera;
  if (!fonts) return null; // nothing is measured with a fallback font (fonts.ts); the render waits for it
  return (
    <Theme.Provider value={theme}>
      <AbsoluteFill data-probe-root style={{ overflow: "hidden", fontFamily: FONT }}>
        <Background />
        {props.transition === "one-take" && props.camera && <Parallax />}
        <Ticker />
        <Header />
        {props.scenes.map((s, i) => (
          // one-take: the old scene stays alive for the camera's window after its own end (no fade), the thread runs over it
          <Sequence key={i} from={s.from} durationInFrames={s.duration + (oneTake && i < props.scenes.length - 1 ? props.camera!.cut : 0)} layout="none">
            <SwipeSlot i={i}><SceneSlot i={i} /></SwipeSlot>
            {i > 0 && <Cut />}
            {oneTake && i > 0 && <Thread i={i} />}
            {props.transition === "meter" && i < props.scenes.length - 1 && <MeterRise duration={s.duration} />}
          </Sequence>
        ))}
        <ThreadLayer />
        <VignetteLayer />
        <OutroChip />
        <LoopBack background={<><Background />{oneTake && <FrozenParallax />}</>} hook={<SwipeSlot i={0}><SceneSlot i={0} /></SwipeSlot>} />
        <Captions cap={props.captions} />
        <Footer />
        {props.probe && <Probe />}
        {/* Studio preview only: the final mix is ffmpeg's (voice levelled alone, music at one constant level) */}
        {props.voice && <Html5Audio src={staticFile(props.voice)} volume={props.voiceVolume}
          trimBefore={props.voiceTrim ? Math.round(props.voiceTrim * fps) : undefined} />}
        {props.music && (
          <Html5Audio src={staticFile(props.music)} loop
            volume={(f) => props.musicVolume * musicLevel(props, f, durationInFrames)} />
        )}
      </AbsoluteFill>
    </Theme.Provider>
  );
};
