import React, { createContext, useContext } from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CANVAS, FONT, INK, LINE_STRONG, MARK_BG, RED, T_PATH } from "./brand";
import { marked } from "./marker";
import type { Motion, Scene, ShortProps, Style, Variant } from "./types";

type Ctx = { v: Variant; props: ShortProps };
export const Theme = createContext<Ctx>(null as unknown as Ctx);
export const useTheme = () => useContext(Theme);

/** The director's motion numbers (tt_shorts/directors.py), or null: today's motion. */
export const useMotion = (): Motion | null => useContext(Theme)?.props?.style?.motion ?? null;

/** The direction slide entrances and directional cuts move in: the director's current, else the given legacy one. */
export const flowOf = (style: Style | undefined, legacy: [number, number]): [number, number] => style?.flow ?? legacy;

/** 0..1 spring that starts `delay` frames into the current Sequence; without explicit numbers, the director's spring. */
export const useIn = (delay = 0, damping?: number, stiffness?: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const m = useMotion();
  return spring({ frame: frame - delay, fps,
    config: { damping: damping ?? m?.damping ?? 20, stiffness: stiffness ?? m?.stiffness ?? 170, mass: 0.8 } });
};

/** This video's style (tt_shorts/variety.py), or the look's own when the props carry none. */
export const useStyle = (): Style => {
  const { v, props } = useTheme();
  return props.style ?? { hook: "stack", motif: v === "kinetic" ? "diagonal" : "grid", enter: v === "kinetic" ? "slide" : "rise" };
};

/** True inside the first scene (outro.tsx SwipeSlot): the swipe is decided at frame 0, so there everything is on
 *  screen and readable from the first frame, and motion only settles by a few px (tt_shorts/swipe.py). */
export const Opening = createContext(false);
export const useOpening = () => useContext(Opening);

/** The opening's entrance: fully visible at frame 0, it only settles the last few px in this video's motion. */
const settle = (enter: Style["enter"], t: number, [fx, fy]: [number, number]): React.CSSProperties => {
  if (enter === "slide") return { transform: `translate(${(1 - t) * -16 * fx}px, ${(1 - t) * -16 * fy}px)` };
  if (enter === "scale") return { transform: `scale(${0.985 + 0.015 * Math.min(1.02, t)})`, transformOrigin: "left center" };
  return { transform: `translateY(${(1 - t) * (enter === "reveal" ? 6 : 10)}px)` }; // rise, reveal (nothing masked)
};

/** How things come on screen: they rise, slide in from the left, come up from behind a mask, or scale up.
 *  Kinetic keeps its harder spring whichever motion the video has. In the opening they only settle (`Opening`). */
export const In: React.FC<{ delay?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ delay = 0, style, children }) => {
  const { v } = useTheme();
  const st = useStyle();
  const { enter } = st;
  const opening = useOpening();
  const m = useMotion(); // a director's spring and stagger replace the look's own (kinetic: 16/220)
  const d = m ? Math.round((delay * m.stagger_frames) / 5) : delay;
  const t = useIn(opening ? Math.round(d / 2) : d, m ? m.damping : v === "kinetic" ? 16 : 20,
    m ? m.stiffness : v === "kinetic" ? 220 : 170);
  const [fx, fy] = flowOf(st, [1, 0]); // a slide moves along the current (today: from the left)
  if (opening) return <div style={{ ...settle(enter, t, [fx, fy]), ...style }}>{children}</div>;
  const css: React.CSSProperties = { opacity: Math.min(1, t * 1.6) };
  if (enter === "slide") css.transform = `translate(${(1 - t) * -140 * fx}px, ${(1 - t) * -140 * fy}px)`;
  if (enter === "rise") css.transform = `translateY(${(1 - t) * 56}px)`;
  if (enter === "scale") {
    css.transform = `scale(${0.9 + 0.1 * Math.min(1.02, t)})`;
    css.transformOrigin = "left center";
  }
  if (enter === "reveal") {
    css.opacity = Math.min(1, t * 3);
    css.clipPath = `inset(${(1 - Math.min(1, t)) * 100}% -4% -20% -4%)`;
    css.transform = `translateY(${(1 - t) * 32}px)`;
  }
  return <div style={{ ...css, ...style }}>{children}</div>;
};

/** Width of `text` at 100px in the brand font (synchronous canvas measure, the same in every frame). */
const canvas = typeof document !== "undefined" ? document.createElement("canvas") : null;
export const measure = (text: string, weight = 700) => {
  const ctx = canvas?.getContext("2d");
  if (!ctx) return text.length * 60;
  ctx.font = `${weight} 100px ${FONT}`;
  return ctx.measureText(text).width;
};

/** The largest size (<= max, a multiple of 4) at which every line fits `width`. */
export const fitSize = (lines: string[], width: number, max: number, min = 40, weight = 700) => {
  const widest = Math.max(...lines.map((l) => measure(l, weight)));
  const size = Math.max(min, Math.min(max, Math.floor((100 * width) / Math.max(1, widest))));
  return size - (size % 4);
};

/** tbilisi.today's mark, exactly as the guide draws it: no frame, no shadow, no recolor. */
export const Mark: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 512 512">
    <rect width={512} height={512} rx={112} fill={MARK_BG} />
    <g transform="translate(0,512) scale(0.1,-0.1)">
      <path d={T_PATH} fill="#FFFFFF" />
    </g>
    <circle cx={323} cy={295} r={34} fill={RED} />
  </svg>
);

/** The pack's name in text: its accent character (the dot of tbilisi.today) in the accent color, as on the site. */
export const Wordmark: React.FC<{ size: number }> = ({ size }) => {
  const { props } = useTheme();
  const w = props.brand.wordmark;
  const i = w.accent ? w.text.indexOf(w.accent) : -1;
  return (
    <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, color: INK, whiteSpace: "nowrap" }}>
      {i < 0 ? w.text : <>{w.text.slice(0, i)}<span style={{ color: RED }}>{w.accent}</span>{w.text.slice(i + (w.accent ?? "").length)}</>}
    </span>
  );
};

/** The brand's logo. tmark: the mark next to the wordmark text. svg: the pack's own files (they carry the name).
 *  `place` header: one row, `size` high; end: the end card's logo, about `size` * 2.4 wide. */
export const Logo: React.FC<{ place: "header" | "end"; size: number }> = ({ place, size }) => {
  const { props } = useTheme();
  if (props.brand.logo === "svg") {
    return place === "header"
      ? <Img src={staticFile("brand/header.svg")} style={{ height: size, display: "block" }} />
      : <Img src={staticFile("brand/end.svg")} style={{ width: size * 2.4, display: "block" }} />;
  }
  if (place === "header") {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <Mark size={size} />
        <Wordmark size={size / 2} />
      </div>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24 }}>
      <Mark size={size} />
      <Wordmark size={size / 2} />
    </div>
  );
};

/** The red dot: "now". It may pulse; it is never text. */
export const Dot: React.FC<{ size?: number; pulse?: boolean }> = ({ size = 20, pulse = false }) => {
  const frame = useCurrentFrame();
  const s = pulse ? 1 + 0.18 * Math.sin(frame / 5) : 1;
  return <span style={{ display: "inline-block", flex: "none", width: size, height: size, borderRadius: size / 2, background: RED,
    transform: `scale(${s})` }} />;
};

/** A pill, as the site's chips: 1px line, fully round; `live` gets the red border and the dot. */
export const Chip: React.FC<{ children: React.ReactNode; live?: boolean; solid?: boolean; size?: number }> = ({ children, live, solid, size = 36 }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 12, fontFamily: FONT, fontWeight: 600, fontSize: size, lineHeight: 1,
    padding: `${size * 0.44}px ${size * 0.78}px ${size * 0.5}px`, borderRadius: 999, whiteSpace: "nowrap",
    border: `2px solid ${live ? RED : LINE_STRONG}`, background: solid ? INK : "transparent", color: solid ? CANVAS : INK }}>
    {live && <Dot size={size * 0.44} pulse />}
    {children}
  </span>
);

/** Scene label: the "now" chip with the red dot (editorial, cards) or an inverted ink block (kinetic). */
export const Kicker: React.FC<{ text?: string; delay?: number }> = ({ text, delay = 0 }) => {
  const { v } = useTheme();
  const shown = useIn(delay);
  const t = useOpening() ? 1 : shown; // the opening's kicker is there at frame 0
  if (!text) return null;
  if (v === "kinetic") {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 16, background: INK, color: CANVAS, fontFamily: FONT, fontWeight: 700,
        fontSize: 40, padding: "12px 24px 16px", clipPath: `inset(0 ${(1 - t) * 100}% 0 0)` }}>
        <Dot size={18} />{text}
      </span>
    );
  }
  return <span style={{ opacity: t }}><Chip live>{text}</Chip></span>;
};

export const Headline: React.FC<{ text?: string; delay?: number; size?: number; s?: Scene }> = ({ text, delay = 4, size = 60, s }) => {
  if (!text) return null;
  return (
    <In delay={delay}>
      <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.2, color: INK, marginTop: 24 }}>{s ? marked(s, "headline", text, { px: size }) : text}</div>
    </In>
  );
};

/** A count-up from 0, grouped as Georgian writes thousands ("6 400"). */
export const CountUp: React.FC<{ to: number; delay?: number; frames?: number }> = ({ to, delay = 0, frames = 32 }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame - delay, [0, frames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: (x) => 1 - Math.pow(1 - x, 3) });
  return <>{group(Math.round(to * t))}</>;
};

export const group = (n: number) => n.toLocaleString("en-US").replace(/,/g, " ");

/** Scene frame: kicker and headline on top, the body fills the rest of the scene band. */
export const Frame: React.FC<{ s: Scene; children: React.ReactNode; head?: boolean }> = ({ s, children, head = true }) => (
  <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column" }}>
    {head && (
      <div>
        <Kicker text={s.kicker} />
        <Headline text={s.headline} s={s} />
      </div>
    )}
    <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>{children}</div>
  </div>
);
