// Scenes added on 2026-11-02: a drawing (from sitech-shorts), two sides, steps and three charts. Every motion is a
// function of the frame; colors come from the brand pack (brand.ts), the accent only for the dot ("now").
import React from "react";
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CANVAS, FONT, INK, LINE, LINE_STRONG, MUTED, PANEL, RADIUS, RAIL_X, RED, SIDE, W } from "../brand";
import { marked } from "../marker";
import { ObjectArt, threadT } from "../thread";
import type { ArtNode, Scene } from "../types";
import { beat, Chip, Dot, fitSize, Frame, In, measure, useIn, useTheme } from "../ui";

const INNER = W - 2 * SIDE; // 952
// text that reaches the lower part stays left of the like/share rail (a card's content starts further right)
const low = (inner: number) => Math.min(inner, RAIL_X - (W - inner) / 2);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);

type P = { s: Scene; inner?: number };

/** 1450 -> "1 450", 1.5 -> "1,5": Georgian groups thousands with a space and writes decimals with a comma. */
export const num = (v: number, decimals = 0) => {
  const [i, d] = Math.abs(v).toFixed(decimals).split(".");
  return (v < 0 ? "-" : "") + i.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + (d ? "," + d : "");
};
const decimalsOf = (v: number) => (String(v).split(".")[1] ?? "").length;

/** Start frames spread over the first half of the scene, so the last item still has time to be read. */
const stagger = (n: number, duration: number, first = 6, most = 14) => {
  const step = Math.min(most, Math.max(4, (duration * 0.5 - first) / Math.max(1, n)));
  return Array.from({ length: n }, (_, i) => first + i * step);
};

/** The scene's own background, for fills that hide what is behind them. */
const useGround = () => (useTheme().v === "cards" ? PANEL : CANVAS);

// ---------------------------------------------------------------- draw

const CAMEL: Record<string, string> = {
  "stroke-width": "strokeWidth", "stroke-linecap": "strokeLinecap", "stroke-linejoin": "strokeLinejoin",
  "stroke-dasharray": "strokeDasharray", "fill-opacity": "fillOpacity", "stroke-opacity": "strokeOpacity",
  "font-size": "fontSize", "font-weight": "fontWeight", "text-anchor": "textAnchor",
};
const SHAPES = new Set(["path", "line", "polyline", "polygon", "rect", "circle", "ellipse"]);
export type ArtCtx = { frame: number; fps: number; k: number; colors: Record<string, string> };

const maxDelay = (ns: ArtNode[]): number => Math.max(0, ...ns.map((n) => Math.max(n.motion ? n.delay : 0, maxDelay(n.children))));

/** One element of the drawing. r rises, p pops, s draws its stroke; a group that draws passes it to its shapes.
 *  The motion sits on a wrapper <g>, so the element's own transform attribute stays as the writer set it. */
export const artNode = (n: ArtNode, key: number, c: ArtCtx, drawing: number | null): React.ReactNode => {
  const t = n.motion ? interpolate(c.frame - n.delay * c.k * c.fps, [0, 0.5 * c.fps], [0, 1], { ...clamp, easing: easeOut }) : 1;
  const props: Record<string, unknown> = { key };
  for (const [a, v] of Object.entries(n.attrs)) {
    props[CAMEL[a] ?? a] = a === "fill" || a === "stroke" ? (c.colors[v] ?? v) : v;
  }
  const draws = n.motion === "s" ? t : drawing;
  if (draws !== null && SHAPES.has(n.tag)) {
    Object.assign(props, { pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - draws });
  }
  let el: React.ReactNode;
  if (n.tag === "text") {
    el = React.createElement("text", { ...props, fontFamily: FONT, stroke: "none" }, n.text);
  } else {
    el = React.createElement(n.tag, props, ...n.children.map((ch, i) => artNode(ch, i, c, draws)));
  }
  if (n.motion === "r") {
    return <g key={key} style={{ opacity: t, transform: `translateY(${(1 - t) * 24}px)` }}>{el}</g>;
  }
  if (n.motion === "p") {
    return (
      <g key={key} style={{ opacity: Math.min(1, t * 1.4), transform: `scale(${0.6 + 0.4 * t})`, transformBox: "fill-box",
        transformOrigin: "center" }}>{el}</g>
    );
  }
  return el;
};

/** A line drawing of what the story is about (tt_shorts/art.py sanitizes the writer's SVG into s.art). */
export const Draw: React.FC<P> = ({ s, inner = INNER }) => {
  const { props } = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ground = useGround();
  const art = s.art ?? [];
  const last = maxDelay(art);
  const room = (s.duration / fps) * 0.55 - 0.5; // the drawing is complete by about half the scene
  const k = last > 0 ? Math.max(0.2, Math.min(1, room / last)) : 1;
  const colors = { ACCENT: RED, INK, MUTED, LINE: LINE_STRONG, CANVAS: ground, none: "none" };
  const height = Math.round((inner * 640) / 952);
  return (
    <Frame s={s}>
      {props.thread && s.thread ? (
        <ObjectArt th={props.thread} art={props.thread.art} t={threadT(s, frame)} drawn={frame} id="own" width={inner} height={height} />
      ) : (
        <svg width={inner} height={height} viewBox="0 0 952 640" fill="none" strokeLinecap="round" strokeLinejoin="round"
          style={{ overflow: "visible", flex: "none" }}>
          {art.map((n, i) => artNode(n, i, { frame, fps, k, colors }, null))}
        </svg>
      )}
      {s.label && (
        <In delay={Math.round(last * k * fps) + 6}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 52, lineHeight: 1.2, color: INK, marginTop: 24,
            maxWidth: low(inner) }}>{marked(s, "label", s.label, { px: 52 })}</div>
        </In>
      )}
    </Frame>
  );
};

// ---------------------------------------------------------------- pair

/** Two sides: two cards with a drawn divider between them (the optional word on it, else the dot). */
export const Pair: React.FC<P> = ({ s, inner = INNER }) => {
  const items = (s.items ?? []).slice(0, 2).map((it) => (typeof it === "string" ? { title: it } : it));
  const width = low(inner);
  const size = fitSize(items.map((it) => it.title ?? ""), width - 96, 96, 48);
  const line = useIn(10, 22, 120);
  const card = (i: number) => {
    const it = items[i];
    if (!it) return null;
    return (
      <In delay={4 + i * 10} at={beat(s, `items.${i}`)}>
        <div style={{ width, boxSizing: "border-box", padding: "36px 48px 40px", background: PANEL, borderRadius: RADIUS,
          border: `2px solid ${i === 0 ? LINE_STRONG : LINE}` }}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.16, color: INK, whiteSpace: "nowrap" }}>
            {marked(s, `items.${i}.title`, it.title, { px: size })}
          </div>
          {it.sub && <div style={{ fontFamily: FONT, fontWeight: 400, fontSize: 40, lineHeight: 1.3, color: MUTED, marginTop: 12 }}>{marked(s, `items.${i}.sub`, it.sub, { px: 40 })}</div>}
        </div>
      </In>
    );
  };
  return (
    <Frame s={s}>
      {card(0)}
      <div style={{ display: "flex", alignItems: "center", gap: 24, width, margin: "32px 0" }}>
        <div style={{ flex: 1, height: 4, background: INK, transform: `scaleX(${line})`, transformOrigin: "right" }} />
        {s.between ? <span style={{ opacity: line }}><Chip size={36}>{s.between}</Chip></span> : <Dot size={24} pulse />}
        <div style={{ flex: 1, height: 4, background: INK, transform: `scaleX(${line})`, transformOrigin: "left" }} />
      </div>
      {card(1)}
    </Frame>
  );
};

// ---------------------------------------------------------------- steps

/** 2-4 steps in order; each arrow draws itself just before its step rises in; the current step is filled. */
export const Steps: React.FC<P> = ({ s, inner = INNER }) => {
  const items = (s.items ?? []).slice(0, 4).map((it) => (typeof it === "string" ? it : it.title ?? it.label ?? ""));
  const frame = useCurrentFrame();
  const ground = useGround();
  const width = low(inner);
  // each step comes in when it is said (tt_shorts/beats.py), else on the stagger
  const starts = stagger(items.length, s.duration, 6, 16).map((f, i) => beat(s, `items.${i}`) ?? f);
  const active = starts.reduce((a, st, i) => (frame >= st ? i : a), 0);
  const many = items.length > 3;
  const size = many ? 56 : 64;
  const gap = many ? 64 : 88; // the arrow's height
  const circle = many ? 88 : 96;
  return (
    <Frame s={s}>
      {items.map((t, i) => {
        const arrow = interpolate(frame - (starts[i] - 8), [0, 8], [0, 1], clamp);
        return (
          <React.Fragment key={i}>
            {i > 0 && (
              <svg width={circle} height={gap} style={{ display: "block", flex: "none" }}>
                <path d={`M${circle / 2} 6V${gap - 8}`} stroke={LINE_STRONG} strokeWidth={4} fill="none" strokeLinecap="round"
                  pathLength={1} strokeDasharray={1} strokeDashoffset={1 - arrow} />
                <path d={`M${circle / 2 - 12} ${gap - 20}L${circle / 2} ${gap - 6}L${circle / 2 + 12} ${gap - 20}`} stroke={INK} strokeWidth={4} fill="none"
                  strokeLinecap="round" strokeLinejoin="round" opacity={arrow > 0.9 ? 1 : 0} />
              </svg>
            )}
            <In delay={starts[i]} at={beat(s, `items.${i}`)}>
              <div style={{ display: "flex", alignItems: "center", gap: 32, width }}>
                <div style={{ width: circle, height: circle, borderRadius: circle / 2, flex: "none", display: "flex", alignItems: "center",
                  justifyContent: "center", boxSizing: "border-box", fontFamily: FONT, fontWeight: 700, fontSize: circle * 0.46,
                  background: i === active ? INK : ground, color: i === active ? ground : INK,
                  border: i === active ? "none" : `3px solid ${LINE_STRONG}` }}>{i + 1}</div>
                <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.2, flex: 1,
                  color: i <= active ? INK : MUTED }}>{marked(s, `items.${i}`, t, { px: size })}</div>
                <span style={{ opacity: i === active ? 1 : 0, flex: "none" }}><Dot size={22} pulse /></span>
              </div>
            </In>
          </React.Fragment>
        );
      })}
    </Frame>
  );
};

// ---------------------------------------------------------------- charts

const Unit: React.FC<{ text?: string }> = ({ text }) =>
  text ? (
    <In delay={2}>
      <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 36, lineHeight: 1.3, color: MUTED, marginBottom: 16 }}>{text}</div>
    </In>
  ) : null;

/** 2-5 values as bars from zero, growing one after another; the largest is ink with the dot, the rest muted. */
export const Bars: React.FC<P> = ({ s, inner = INNER }) => {
  const items = (s.items ?? []).slice(0, 5).filter((it): it is { label: string; value: number } =>
    typeof it !== "string" && typeof it.value === "number");
  const frame = useCurrentFrame();
  const width = low(inner);
  if (!items.length) return null;
  const max = Math.max(...items.map((it) => it.value));
  const dec = Math.max(...items.map((it) => decimalsOf(it.value)));
  const starts = stagger(items.length, s.duration, 6, 10);
  const valueW = (Math.max(...items.map((it) => measure(num(it.value, dec), 700))) * 56) / 100 + 48;
  const barMax = width - valueW;
  const top = items.reduce((a, it, i) => (it.value > items[a].value ? i : a), 0);
  const tight = items.length > 4;
  return (
    <Frame s={s}>
      <Unit text={s.unit} />
      <div style={{ display: "flex", flexDirection: "column", gap: tight ? 20 : 32, width }}>
        {items.map((it, i) => {
          const t = interpolate(frame - starts[i], [0, 18], [0, 1], { ...clamp, easing: easeOut });
          return (
            <div key={i} style={{ opacity: Math.min(1, t * 3) }}>
              <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: tight ? 34 : 38, lineHeight: 1.3, color: INK,
                whiteSpace: "nowrap", overflow: "hidden" }}>{it.label}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 32, marginTop: 8 }}>
                <div style={{ position: "relative", width: Math.max(8, (barMax * it.value * t) / max), height: tight ? 40 : 48,
                  background: i === top ? INK : MUTED, borderRadius: 4, flex: "none" }}>
                  {i === top && t > 0.98 && <span style={{ position: "absolute", right: -12, top: tight ? 8 : 12 }}><Dot size={24} /></span>}
                </div>
                <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 56, lineHeight: 1, color: INK, whiteSpace: "nowrap" }}>
                  {num(it.value * t, dec)}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

/** 3-8 values over time: the line draws itself left to right, points appear as it passes, the dot sits on "now". */
export const Trend: React.FC<P> = ({ s, inner = INNER }) => {
  const items = (s.items ?? []).slice(0, 8).filter((it): it is { label: string; value: number } =>
    typeof it !== "string" && typeof it.value === "number");
  const frame = useCurrentFrame();
  const ground = useGround();
  const { fps } = useVideoConfig();
  const width = low(inner);
  if (items.length < 2) return null;
  const height = inner < INNER - 40 ? 400 : 480;
  const padT = 96, padB = 72, padX = 28;
  const vals = items.map((it) => it.value);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const last = items.length - 1;
  const x = (i: number) => padX + (i * (width - 2 * padX)) / last;
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo || 1)) * (height - padT - padB);
  const d = items.map((it, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(it.value).toFixed(1)}`).join(" ");
  const span = Math.min(1.4 * fps, s.duration * 0.45);
  const run = interpolate(frame, [8, 8 + span], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const reached = (i: number) => run >= i / last - 1e-6;
  const dec = Math.max(...vals.map(decimalsOf));
  const showAll = items.length <= 5;
  return (
    <Frame s={s}>
      <Unit text={s.unit} />
      <svg width={width} height={height} style={{ overflow: "visible", flex: "none" }}>
        {[0, 0.5, 1].map((f) => {
          const yy = padT + f * (height - padT - padB);
          return <line key={f} x1={0} x2={width} y1={yy} y2={yy} stroke={LINE} strokeWidth={2} />;
        })}
        <path d={d} fill="none" stroke={INK} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round"
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - run} />
        {items.map((it, i) => (i < last && reached(i)
          ? <circle key={i} cx={x(i)} cy={y(it.value)} r={10} fill={ground} stroke={INK} strokeWidth={5} /> : null))}
        {run > 0.98 && <circle cx={x(last)} cy={y(items[last].value)} r={18} fill={RED} />}
        {[0, last].map((i) => (reached(i) ? (
          <text key={`v${i}`} x={x(i)} y={y(items[i].value) - 32} textAnchor={i === 0 ? "start" : "end"} fontFamily={FONT}
            fontWeight={700} fontSize={52} fill={i === last ? INK : MUTED}>{num(items[i].value, dec)}</text>
        ) : null))}
        {items.map((it, i) => ((showAll || i === 0 || i === last) ? (
          <text key={`l${i}`} x={x(i)} y={height - 16} fontFamily={FONT} fontWeight={600} fontSize={32} fill={MUTED}
            textAnchor={i === 0 ? "start" : i === last ? "end" : "middle"}>{it.label}</text>
        ) : null))}
      </svg>
      {s.label && (
        <In delay={Math.round(8 + span)}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 52, lineHeight: 1.2, color: INK, marginTop: 24, maxWidth: width }}>
            {marked(s, "label", s.label, { px: 52 })}
          </div>
        </In>
      )}
    </Frame>
  );
};

/** One value then and now: the old one muted, an arrow draws, the new one rolls up from the old to its value. */
export const Change: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const width = low(inner);
  const b = s.before, a = s.after;
  if (!b || !a) return null;
  const dec = Math.max(decimalsOf(b.value), decimalsOf(a.value));
  const size = fitSize([num(a.value, dec), num(b.value, dec)], width - (s.unit ? measure(s.unit, 600) * 0.52 + 96 : 96), 280, 96);
  const arrow = interpolate(frame, [12, 22], [0, 1], clamp);
  const roll = interpolate(frame, [20, 46], [0, 1], { ...clamp, easing: easeOut });
  const label = (text: string, color: string) => (
    <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 40, lineHeight: 1.3, color }}>{text}</div>
  );
  const unit = (color: string, sz: number) => s.unit
    ? <span style={{ fontFamily: FONT, fontWeight: 600, fontSize: sz, color }}>{s.unit}</span> : null;
  return (
    <Frame s={s}>
      <In delay={4}>
        {label(b.label, MUTED)}
        <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
          <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: Math.round(size * 0.6), lineHeight: 1.05, color: MUTED }}>
            {num(b.value, dec)}
          </span>
          {unit(MUTED, 40)}
        </div>
      </In>
      <svg width={80} height={96} style={{ display: "block", flex: "none", margin: "12px 0" }}>
        <path d="M40 6V82" stroke={INK} strokeWidth={6} fill="none" strokeLinecap="round" pathLength={1} strokeDasharray={1}
          strokeDashoffset={1 - arrow} />
        <path d="M22 64L40 84L58 64" stroke={INK} strokeWidth={6} fill="none" strokeLinecap="round" strokeLinejoin="round"
          opacity={arrow > 0.95 ? 1 : 0} />
      </svg>
      <In delay={14}>
        {label(a.label, INK)}
        <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
          <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.05, color: INK }}>
            {num(b.value + (a.value - b.value) * roll, dec)}
          </span>
          {unit(INK, 52)}
          <span style={{ opacity: roll > 0.98 ? 1 : 0 }}><Dot size={28} pulse /></span>
        </div>
      </In>
      {s.label && (
        <In delay={30}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 48, lineHeight: 1.2, color: INK, marginTop: 32, maxWidth: width }}>
            {marked(s, "label", s.label, { px: 48 })}
          </div>
        </In>
      )}
    </Frame>
  );
};
