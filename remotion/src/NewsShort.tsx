import React, { useMemo } from "react";
import { AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import {
  alpha, applyBrand, CANVAS, CAPTION_BOTTOM, fill, FONT, GRID, H, INK, LINE, MUTED, PANEL, RADIUS, SCENE_BOTTOM, SCENE_TOP, SIDE,
  TICKER, W,
} from "./brand";
import { Captions } from "./Captions";
import { SCENES } from "./scenes";
import type { Scene, ShortProps, Transition } from "./types";
import { Chip, Dot, Logo, measure, Theme, useStyle, useTheme } from "./ui";

const EXIT = 7; // frames a scene takes to leave
const CARD_PAD = 48;

/** The canvas and its texture, drifting slowly: this video's motif (grid, diagonal, dots, rules or plain), always in
 *  the pack's faint grid color. */
export const Background: React.FC = () => {
  const { motif } = useStyle();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const cell = motif === "dots" ? 48 : motif === "rules" ? 96 : 72;
  const pan = interpolate(frame, [0, durationInFrames], [0, cell]);
  const mark = {
    grid: <path d={`M${cell} 0H0V${cell}`} fill="none" stroke={GRID} strokeWidth={2} />,
    diagonal: <path d={`M0 ${cell}L${cell} 0`} fill="none" stroke={GRID} strokeWidth={2} />,
    dots: <circle cx={cell / 2} cy={cell / 2} r={3} fill={GRID} />,
    rules: <path d={`M0 ${cell - 1}H${cell}`} fill="none" stroke={GRID} strokeWidth={2} />,
    plain: null,
  }[motif];
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
      <div style={{ position: "absolute", left: SIDE, top: 80, height: 88, display: "flex", alignItems: "center" }}>
        <Logo place="header" size={88} />
      </div>
      <div style={{ position: "absolute", right: SIDE, top: 80, textAlign: "right", fontFamily: FONT }}>
        <div style={{ fontWeight: 700, fontSize: 40, lineHeight: 1.2, color: INK }}>{props.date.date}</div>
        <div style={{ fontWeight: 400, fontSize: 30, lineHeight: 1.4, color: MUTED }}>
          {props.date.weekday} · {props.date.time} · {props.category}
        </div>
      </div>
      <div style={{ position: "absolute", left: SIDE, right: SIDE, top: 204, height: 4, background: LINE }} />
      <div style={{ position: "absolute", left: SIDE, top: 204, height: 4, width: x, background: INK }} />
      <div style={{ position: "absolute", left: SIDE + x - 10, top: 196 }}><Dot size={20} /></div>
    </>
  );
};

/** The cut between scenes, drawn over the new scene: "line" sweeps an ink line with the dot across, "panel" wipes an
 *  ink panel through (kinetic's own). The other transitions move the scene itself (sceneMotion). */
const Cut: React.FC = () => {
  const frame = useCurrentFrame();
  const { props } = useTheme();
  const tr = props.transition ?? "line";
  if (frame > 10 || (tr !== "line" && tr !== "panel")) return null;
  const x = interpolate(frame, [0, 10], [-W, W], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (tr === "panel") {
    return <div style={{ position: "absolute", left: x, top: SCENE_TOP, width: W, height: SCENE_BOTTOM - SCENE_TOP, background: INK }} />;
  }
  return (
    <div style={{ position: "absolute", left: x, top: SCENE_TOP - 24, width: W, display: "flex", alignItems: "center" }}>
      <div style={{ flex: 1, height: 4, background: INK }} /><Dot size={20} />
    </div>
  );
};

const ENTER = 10; // frames a scene takes to come in

/** How the scene itself enters and leaves for a transition (frame is the scene's own, left is the slot's x).
 *  wipe: revealed left to right · slide: a short slide and fade · push: the old scene leaves left, the new one
 *  comes from the right · dot: an iris opens from the header's progress dot · cut, line, panel: the scene fades out. */
const sceneMotion = (tr: Transition, frame: number, s: Scene, first: boolean, last: boolean, total: number, left: number) => {
  const ease = (t: number) => 1 - Math.pow(1 - t, 3);
  const enter = first ? 1 : ease(interpolate(frame, [0, ENTER], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const out = last || tr === "cut" ? 1
    : interpolate(frame, [s.duration - EXIT, s.duration], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const style: React.CSSProperties = {};
  let dx = 0, opacity = out, dy = (1 - out) * -48;
  if (tr === "wipe" && enter < 1) style.clipPath = `inset(0 ${(1 - enter) * 100}% 0 0)`;
  if (tr === "slide") { dx = (1 - enter) * 160 - (1 - out) * 160; opacity = Math.min(enter, out); dy = 0; }
  if (tr === "push") { dx = (1 - enter) * W - (1 - out) * W; opacity = 1; dy = 0; }
  if (tr === "dot" && enter < 1) {
    const x = SIDE + (W - 2 * SIDE) * ((s.from + frame) / Math.max(1, total - 1)) - left; // the progress dot
    style.clipPath = `circle(${enter * 1600}px at ${x}px ${206 - SCENE_TOP}px)`;
  }
  return { style, dx, dy, opacity, enter, out };
};

const SceneSlot: React.FC<{ i: number }> = ({ i }) => {
  const { v, props } = useTheme();
  const s = props.scenes[i];
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const Comp = SCENES[s.type];
  const first = i === 0, last = i === props.scenes.length - 1;
  const tr = props.transition ?? "line";
  if (v === "cards" && s.type !== "end") {
    const left = SIDE - 16;
    const m = sceneMotion(tr, frame, s, first, last, durationInFrames, left);
    const own = tr === "line" || tr === "cut" || tr === "panel"; // the card's own entrance: it rises and settles
    const enter = own ? interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: (t) => 1 - Math.pow(1 - t, 3) }) : 1;
    const shown = Math.min(enter, m.opacity);
    return (
      <div style={{ position: "absolute", left, right: SIDE - 16, top: SCENE_TOP, bottom: H - SCENE_BOTTOM, background: PANEL,
        border: `2px solid ${LINE}`, borderRadius: RADIUS, opacity: shown, ...m.style,
        transform: `translate(${m.dx}px, ${(1 - enter) * 120 + m.dy * (40 / 48)}px) scale(${own ? 0.96 + 0.04 * Math.min(enter, m.out) : 1})` }}>
        <div style={{ position: "absolute", left: CARD_PAD, right: CARD_PAD, top: CARD_PAD, bottom: 120 }}>
          {Comp ? <Comp s={s} inner={W - 2 * (SIDE - 16) - 2 * CARD_PAD} /> : null}
        </div>
        <div style={{ position: "absolute", left: CARD_PAD, right: CARD_PAD, bottom: 40, borderTop: `2px solid ${LINE}`, paddingTop: 20,
          display: "flex", justifyContent: "space-between", fontFamily: FONT, fontSize: 30, color: MUTED }}>
          <span>{fill(props.brand.strings.card_meta, { n: props.sources.length, time: props.date.time })}</span>
          <span>{i + 1} / {props.scenes.length - 1}</span>
        </div>
      </div>
    );
  }
  const m = sceneMotion(tr, frame, s, first, last, durationInFrames, SIDE);
  return (
    <div style={{ position: "absolute", left: SIDE, right: SIDE, top: SCENE_TOP, height: SCENE_BOTTOM - SCENE_TOP, opacity: m.opacity,
      transform: `translate(${m.dx}px, ${m.dy}px)`, ...m.style }}>
      {Comp ? <Comp s={s} /> : null}
    </div>
  );
};

/** The band the platforms cover with their own UI: no story text there, only motion that fills it. */
const Ticker: React.FC = () => {
  const { v, props } = useTheme();
  const frame = useCurrentFrame();
  const rows = [[props.category, props.date.date, ...props.sources, props.brand.label].join("  ·  ")];
  const speed = v === "kinetic" ? 4 : 2.2;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: CAPTION_BOTTOM + 28, height: 180, overflow: "hidden" }}>
      {props.previewNote && (
        <div style={{ position: "absolute", right: SIDE, top: 0, zIndex: 1 }}><Chip size={26}>{props.previewNote}</Chip></div>
      )}
      {rows.map((r, i) => {
        const unit = (measure(`${r}  ·  `, 700) * 128) / 100;
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
    <div style={{ position: "absolute", left: SIDE, right: SIDE, top: 1768, borderTop: `2px solid ${LINE}`, paddingTop: 16, fontFamily: FONT }}>
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
  const { durationInFrames } = useVideoConfig();
  return (
    <Theme.Provider value={theme}>
      <AbsoluteFill style={{ overflow: "hidden", fontFamily: FONT }}>
        <Background />
        <Ticker />
        <Header />
        {props.scenes.map((s, i) => (
          <Sequence key={i} from={s.from} durationInFrames={s.duration} layout="none">
            <SceneSlot i={i} />
            {i > 0 && <Cut />}
          </Sequence>
        ))}
        <Captions cap={props.captions} />
        <Footer />
        {/* Studio preview only: the final mix is ffmpeg's (voice levelled alone, music at one constant level) */}
        {props.voice && <Html5Audio src={staticFile(props.voice)} volume={props.voiceVolume} />}
        {props.music && (
          <Html5Audio src={staticFile(props.music)} loop
            volume={(f) => props.musicVolume *
              interpolate(f, [0, 30, durationInFrames - 75, durationInFrames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
        )}
      </AbsoluteFill>
    </Theme.Provider>
  );
};
