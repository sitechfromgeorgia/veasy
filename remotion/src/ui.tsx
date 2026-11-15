import React, { createContext, useContext } from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CANVAS, FONT, INK, LINE_STRONG, MARK_BG, MARK_INK, RED, T_PATH } from "./brand";
import { Mark as NotationMark, marked } from "./marker";
import { MediaCredit, SceneMedia } from "./media";
import { counted, decimalsOf, group } from "./number";
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

/** The frame a beat brings an element in (tt_shorts/beats.py: s.beats.reveal, on the words), or undefined: the
 *  component's own stagger. Pass it as In's `at`. */
export const beat = (s: Scene, key: string): number | undefined => s.beats?.reveal?.[key];

/** A stepped device's progress, 0..1 (tt_shorts/beats.py: s.beats.steps). `base` is the device's own 0..1 motion
 *  and the first of N+1 equal stages; each step eases in the next one. Without steps it is `base` itself, and it
 *  always ends at 1 (the settled frame looks as it did before beats). */
export const stepped = (s: Scene, frame: number, base: number, frames = 12) => {
  const steps = s.beats?.steps ?? [];
  if (!steps.length) return base;
  const more = steps.reduce((a, f) => a + interpolate(frame - f, [0, frames], [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (x) => 1 - Math.pow(1 - x, 3) }), 0);
  return (base + more) / (steps.length + 1);
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
  if (enter === "drop") return { transform: `translateY(${(1 - t) * -8}px)` };
  if (enter === "expand") return { transform: `scale(${0.99 + 0.01 * Math.min(1.01, t)})`, transformOrigin: "center center" };
  if (enter === "drift") return { transform: `translate(${(1 - t) * 8 * fx}px, ${(1 - t) * 6 * fy}px)` };
  if (enter === "flip") return { transform: `translateY(${(1 - t) * 6}px)` };
  return { transform: `translateY(${(1 - t) * (enter === "reveal" ? 6 : 10)}px)` }; // rise, reveal (nothing masked)
};

/** How things come on screen: they rise, slide in, come up from behind a mask, scale up,
 *  drop from above, expand outward from the center, drift directionally, or flip in perspective.
 *  Kinetic keeps its harder spring whichever motion the video has. In the opening they only settle (`Opening`). */
export const In: React.FC<{ delay?: number; at?: number; style?: React.CSSProperties; children: React.ReactNode }> = (
  { delay = 0, at, style, children }) => {
  const { v } = useTheme();
  const st = useStyle();
  const { enter } = st;
  const opening = useOpening();
  const m = useMotion(); // a director's spring and stagger replace the look's own (kinetic: 16/220)
  // `at`: a beat's own frame (tt_shorts/beats.py, on the words), never rescaled by a director's stagger
  const d = at ?? (m ? Math.round((delay * m.stagger_frames) / 5) : delay);
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
  if (enter === "drop") {
    css.transform = `translateY(${(1 - t) * -48}px)`;
  }
  if (enter === "expand") {
    css.opacity = Math.min(1, t * 2.5);
    css.clipPath = `inset(0 ${(1 - Math.min(1, t)) * 50}% 0 ${(1 - Math.min(1, t)) * 50}%)`;
    css.transform = `scale(${0.97 + 0.03 * Math.min(1.01, t)})`;
    css.transformOrigin = "center center";
  }
  if (enter === "drift") {
    css.transform = `translate(${(1 - t) * 32 * fx}px, ${(1 - t) * 24 * fy}px) scale(${0.96 + 0.04 * Math.min(1.01, t)})`;
    css.transformOrigin = "left center";
  }
  if (enter === "flip") {
    css.transform = `perspective(600px) rotateX(${(1 - Math.min(1, t)) * 22}deg) translateY(${(1 - t) * 20}px)`;
    css.transformOrigin = "center top";
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

/** tbilisi.today's mark, exactly as the guide draws it: no frame, no shadow, no recolor (its tile, t and dot are the
 *  theme's markBg, markInk and accent; tbilisi.today's themes keep the guide's own). */
export const Mark: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 512 512">
    <rect width={512} height={512} rx={112} fill={MARK_BG} />
    <g transform="translate(0,512) scale(0.1,-0.1)">
      <path d={T_PATH} fill={MARK_INK} />
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

/** A mask reveal that clips content along an edge and slides it in. */
export const MaskReveal: React.FC<{
  delay?: number;
  direction?: "up" | "down" | "left" | "right";
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ delay = 0, direction = "up", style, children }) => {
  const opening = useOpening();
  const m = useMotion();
  const t = useIn(opening ? 0 : delay, m?.damping ?? 20, m?.stiffness ?? 170);
  if (opening) return <div style={style}>{children}</div>;

  let clip = "inset(0 0 0 0)";
  let tr = "none";
  if (direction === "up") {
    clip = `inset(0 0 ${(1 - t) * 100}% 0)`;
    tr = `translateY(${(1 - t) * 32}px)`;
  } else if (direction === "down") {
    clip = `inset(${(1 - t) * 100}% 0 0 0)`;
    tr = `translateY(${(1 - t) * -32}px)`;
  } else if (direction === "left") {
    clip = `inset(0 ${(1 - t) * 100}% 0 0)`;
    tr = `translateX(${(1 - t) * -32}px)`;
  } else if (direction === "right") {
    clip = `inset(0 0 0 ${(1 - t) * 100}%)`;
    tr = `translateX(${(1 - t) * 32}px)`;
  }

  return (
    <div style={{ clipPath: clip, transform: tr, opacity: Math.min(1, t * 2.5), ...style }}>
      {children}
    </div>
  );
};

/** Computes deterministic reveal frames for each display word in `text` synced to the narrator's spoken words. */
export const spokenWordFrames = (
  text: string,
  s: Scene | undefined,
  words: ShortProps["words"] | undefined,
  fps: number,
  delay: number,
  stagger: number
): number[] => {
  const displayWords = text.split(/\s+/).filter(Boolean);
  if (!displayWords.length) return [];
  const fallback = displayWords.map((_, i) => delay + i * stagger);
  if (!s || !words || !words.length) return fallback;

  const sceneFrom = s.from ?? 0;
  const sceneDur = s.duration ?? 90;
  const sceneEnd = sceneFrom + sceneDur - 14;

  const sceneWords: { word: string; frame: number }[] = [];
  for (const w of words) {
    const absFrame = Math.round(w.start * fps);
    if (absFrame >= sceneFrom && absFrame <= sceneEnd) {
      sceneWords.push({
        word: w.text,
        frame: absFrame - sceneFrom,
      });
    }
  }

  if (!sceneWords.length) return fallback;

  const norm = (str: string) => str.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
  const maxFrame = Math.max(delay, sceneDur - 26);

  const matched: (number | null)[] = new Array(displayWords.length).fill(null);
  let cursor = 0;

  for (let i = 0; i < displayWords.length; i++) {
    const dw = norm(displayWords[i]);
    if (!dw) continue;
    for (let j = cursor; j < sceneWords.length; j++) {
      const sw = norm(sceneWords[j].word);
      if (!sw) continue;
      if (dw === sw || (dw.length >= 4 && sw.length >= 4 && dw.slice(0, 4) === sw.slice(0, 4))) {
        matched[i] = Math.max(delay, Math.min(sceneWords[j].frame, maxFrame));
        cursor = j + 1;
        break;
      }
    }
  }

  // If no words matched at all, return fallback
  const hasMatch = matched.some((m) => m !== null);
  if (!hasMatch) return fallback;

  // Fill unmatched words monotonically by interpolating between surrounding matches
  const result: number[] = new Array(displayWords.length);

  for (let i = 0; i < displayWords.length; i++) {
    if (matched[i] !== null) {
      result[i] = matched[i]!;
      continue;
    }
    // Find previous match
    let prevIdx = -1;
    for (let p = i - 1; p >= 0; p--) {
      if (matched[p] !== null) {
        prevIdx = p;
        break;
      }
    }
    // Find next match
    let nextIdx = -1;
    for (let n = i + 1; n < displayWords.length; n++) {
      if (matched[n] !== null) {
        nextIdx = n;
        break;
      }
    }

    if (prevIdx !== -1 && nextIdx !== -1) {
      const prevF = matched[prevIdx]!;
      const nextF = matched[nextIdx]!;
      const t = (i - prevIdx) / (nextIdx - prevIdx);
      result[i] = Math.round(prevF + t * (nextF - prevF));
    } else if (prevIdx !== -1) {
      const prevF = result[i - 1] ?? matched[prevIdx]!;
      result[i] = Math.min(maxFrame, prevF + stagger);
    } else if (nextIdx !== -1) {
      const nextF = matched[nextIdx]!;
      const t = i / nextIdx;
      result[i] = Math.round(delay + t * (nextF - delay));
    } else {
      result[i] = delay + i * stagger;
    }
  }

  // Ensure monotonicity: frame i >= frame i-1, and clamp to [delay, maxFrame]
  for (let i = 0; i < result.length; i++) {
    let f = result[i];
    if (i > 0 && f < result[i - 1]) {
      f = result[i - 1];
    }
    result[i] = Math.max(delay, Math.min(f, maxFrame));
  }

  return result;
};

/** Kinetic typography for Georgian text: word-by-word reveal with mask reveals and emphasis blocks.
 *  Georgian Mkhedruli script has uniform casing but deep descenders; sufficient clearance ensures no clipping. */
export const WordReveal: React.FC<{
  text: string;
  delay?: number;
  stagger?: number;
  size?: number;
  weight?: number;
  lineHeight?: number;
  color?: string;
  style?: React.CSSProperties;
  s?: Scene;
  field?: string;
  emStyle?: "inverted" | "underline" | "mark";
  inline?: boolean;
}> = ({
  text,
  delay = 4,
  stagger = 3,
  size = 60,
  weight = 700,
  lineHeight = 1.2,
  color,
  style,
  s,
  field,
  emStyle = "inverted",
  inline,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { props } = useTheme();
  const opening = useOpening();
  const m = useMotion();

  // Dynamic brand colors read inside component
  const inkColor = color ?? INK;
  const canvasColor = CANVAS;

  const stag = m ? Math.max(1, Math.round((stagger * m.stagger_frames) / 5)) : stagger;
  const damping = m?.damping ?? 20;
  const stiffness = m?.stiffness ?? 170;

  const lit = field && s?.beats?.lit?.[field];
  const mark = field && s?.mark && s.mark.field === field ? s.mark : null;
  const phrase = mark ? mark.phrase : null;
  const words = text.split(/\s+/).filter(Boolean);

  const spoken = s && props?.words?.length
    ? spokenWordFrames(text, s, props.words, fps, delay, stag)
    : null;

  const renderWord = (w: string, i: number) => {
    const beatFrame = lit && lit[i] !== undefined ? lit[i] : undefined;
    const wordDelay = beatFrame !== undefined ? beatFrame : (spoken ? spoken[i] : delay + i * stag);
    const t = opening
      ? 1
      : spring({
          frame: frame - wordDelay,
          fps,
          config: { damping, stiffness, mass: 0.8 },
        });

    const isEm = phrase && phrase.includes(w);
    const isSettled = opening || Math.min(1, t) >= 0.999;
    const opacity = isSettled ? 1 : Math.min(1, t * 2.5);
    const trY = isSettled ? 0 : (1 - Math.min(1, t)) * (size * 0.4);
    const tr = isSettled ? undefined : `translateY(${trY}px)`;

    const wrapperStyle: React.CSSProperties = {
      display: "inline-block",
      overflow: "hidden",
      padding: "4px 0 8px",
      margin: "-4px 0 -8px",
      ...(inline ? { verticalAlign: "bottom" } : {}),
    };

    if (isEm && emStyle === "inverted") {
      return (
        <span key={i} style={wrapperStyle}>
          <span
            style={{
              display: "inline-block",
              opacity,
              transform: tr,
              background: inkColor,
              color: canvasColor,
              padding: `2px ${Math.round(size * 0.16)}px 4px`,
              borderRadius: 6,
              fontWeight: 800,
            }}
          >
            {w}
          </span>
        </span>
      );
    }

    return (
      <span key={i} style={wrapperStyle}>
        <span style={{ display: "inline-block", opacity, transform: tr }}>
          {w}
        </span>
      </span>
    );
  };

  if (inline) {
    const canMark = Boolean(
      emStyle === "mark" && s && field && mark && text.slice(mark.start, mark.start + mark.phrase.length) === mark.phrase
    );
    const renderInlineSlice = (sliceText: string, wordOffset: number) => {
      const sliceWords = sliceText.split(/\s+/).filter(Boolean);
      return sliceWords.map((w, idx) => (
        <React.Fragment key={wordOffset + idx}>
          {renderWord(w, wordOffset + idx)}
          {idx < sliceWords.length - 1 ? " " : null}
        </React.Fragment>
      ));
    };
    let inlineContent: React.ReactNode;
    if (canMark && mark) {
      const before = text.slice(0, mark.start);
      const after = text.slice(mark.start + mark.phrase.length);
      const beforeWords = before.split(/\s+/).filter(Boolean);
      const phraseWords = mark.phrase.split(/\s+/).filter(Boolean);
      inlineContent = (
        <>
          {beforeWords.length ? <>{renderInlineSlice(before, 0)}{/\s$/.test(before) ? " " : ""}</> : null}
          <NotationMark s={s!} field={field!} px={size}>{renderInlineSlice(mark.phrase, beforeWords.length)}</NotationMark>
          {after.trim() ? <>{/^\s/.test(after) ? " " : ""}{renderInlineSlice(after, beforeWords.length + phraseWords.length)}</> : null}
        </>
      );
    } else {
      inlineContent = renderInlineSlice(text, 0);
    }
    return (
      <div
        style={{
          fontFamily: FONT,
          fontWeight: weight,
          fontSize: size,
          lineHeight,
          color: inkColor,
          ...style,
        }}
      >
        {inlineContent}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "baseline",
        columnGap: Math.round(size * 0.28),
        rowGap: Math.round(size * 0.16),
        fontFamily: FONT,
        fontWeight: weight,
        fontSize: size,
        lineHeight,
        color: inkColor,
        ...style,
      }}
    >
      {words.map((w, i) => renderWord(w, i))}
    </div>
  );
};

/** Kinetic typography for Georgian text: line-by-line reveal with mask reveals. */
export const LineReveal: React.FC<{
  lines: string[];
  delay?: number;
  stagger?: number;
  size?: number;
  weight?: number;
  lineHeight?: number;
  color?: string;
  style?: React.CSSProperties;
  s?: Scene;
  field?: string;
}> = ({
  lines,
  delay = 4,
  stagger = 4,
  size = 60,
  weight = 700,
  lineHeight = 1.25,
  color,
  style,
  s,
  field,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { props } = useTheme();
  const opening = useOpening();
  const m = useMotion();

  const inkColor = color ?? INK;
  const stag = m ? Math.max(1, Math.round((stagger * m.stagger_frames) / 5)) : stagger;
  const damping = m?.damping ?? 20;
  const stiffness = m?.stiffness ?? 170;

  const lineLeadingWords = lines.map((l) => l.trim().split(/\s+/).filter(Boolean)[0] ?? "");
  const firstWordsJoined = lineLeadingWords.join(" ");
  const spoken = s && props?.words?.length
    ? spokenWordFrames(firstWordsJoined, s, props.words, fps, delay, stag)
    : null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: Math.round(size * 0.15),
        fontFamily: FONT,
        fontWeight: weight,
        fontSize: size,
        lineHeight,
        color: inkColor,
        ...style,
      }}
    >
      {lines.map((line, i) => {
        const lineDelay = spoken && spoken[i] !== undefined ? spoken[i] : delay + i * stag;
        const t = opening
          ? 1
          : spring({
              frame: frame - lineDelay,
              fps,
              config: { damping, stiffness, mass: 0.8 },
            });
        const isSettled = opening || Math.min(1, t) >= 0.999;
        const opacity = isSettled ? 1 : Math.min(1, t * 2.2);
        const trY = isSettled ? 0 : (1 - Math.min(1, t)) * (size * 0.5);
        const tr = isSettled ? undefined : `translateY(${trY}px)`;

        return (
          <div key={i} style={{ overflow: "hidden", padding: "4px 0 8px", margin: "-4px 0 -8px" }}>
            <div style={{ opacity, transform: tr }}>
              {s && field ? marked(s, `${field}.${i}`, line, { px: size }) : line}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const Headline: React.FC<{
  text?: string;
  delay?: number;
  size?: number;
  s?: Scene;
  kinetic?: boolean | "word" | "line" | "mask";
}> = ({ text, delay = 4, size = 60, s, kinetic }) => {
  const { v } = useTheme();
  if (!text) return null;
  const mode = kinetic === true
    ? (v === "kinetic" ? "word" : v === "editorial" ? "mask" : undefined)
    : kinetic;

  if (mode === "word") {
    return (
      <div style={{ marginTop: 24 }}>
        <WordReveal text={text} delay={delay} size={size} s={s} field="headline" emStyle="mark" inline />
      </div>
    );
  }
  if (mode === "line") {
    const lines = text.split("\n").length > 1 ? text.split("\n") : [text];
    return (
      <div style={{ marginTop: 24 }}>
        <LineReveal lines={lines} delay={delay} size={size} s={s} field="headline" />
      </div>
    );
  }
  if (mode === "mask") {
    return (
      <MaskReveal delay={delay} direction="up" style={{ marginTop: 24 }}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.2, color: INK }}>
          {s ? marked(s, "headline", text, { px: size }) : text}
        </div>
      </MaskReveal>
    );
  }
  return (
    <In delay={delay}>
      <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.2, color: INK, marginTop: 24 }}>
        {s ? marked(s, "headline", text, { px: size }) : text}
      </div>
    </In>
  );
};

export { group };

/** A count-up from 0, written as Georgian writes numbers ("6 400", "3,8"), ending on the exact fact (number.ts). */
export const CountUp: React.FC<{ to: number; delay?: number; frames?: number }> = ({ to, delay = 0, frames = 32 }) => {
  const frame = useCurrentFrame();
  const m = useMotion();
  const { fps } = useVideoConfig();
  const elapsed = frame - delay;
  const t = !m
    ? interpolate(elapsed, [0, frames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
        easing: (x) => 1 - Math.pow(1 - x, 3) })
    : elapsed >= frames
      ? 1
      : elapsed <= 0
        ? 0
        : Math.max(0, Math.min(1, spring({ frame: elapsed, fps, config: { damping: m.damping, stiffness: m.stiffness, mass: 0.8 } })));
  return <>{group(counted(to, t), decimalsOf(to))}</>;
};


/** Scene frame: kicker and headline on top, the body fills the rest of the scene band. A scene with a picture
 *  (media.tsx, tt_shorts/assets.py) gets it behind everything, and its label and credit in a row at the bottom. */
export const Frame: React.FC<{ s: Scene; children: React.ReactNode; head?: boolean }> = ({ s, children, head = true }) => {
  const { v } = useTheme();
  return (
    <>
      {s.media && <SceneMedia s={s} />}
      {/* a scene that seats the film's object or a drawing keeps the room free (tt_shorts/thread.py, vignettes.py) */}
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", boxSizing: "border-box",
        paddingBottom: (s.thread ?? s.vignette)?.reserve ?? 0 }}>
        {head && (
          <div>
            <Kicker text={s.kicker} />
            <Headline text={s.headline} s={s} kinetic={v === "kinetic" ? "word" : v === "editorial" ? "mask" : undefined} />
          </div>
        )}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>{children}</div>
        {s.media && <MediaCredit s={s} />}
      </div>
    </>
  );
};
