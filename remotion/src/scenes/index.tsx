import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { CANVAS, fill, FONT, INK, LINE, LINE_STRONG, MUTED, ON_ACCENT, PANEL, RADIUS, RAIL_X, RED, SIDE, W } from "../brand";
import type { Scene } from "../types";
import { Bars, Change, Draw, Pair, Steps, Trend } from "./more";
import { isoSpan, Isotype, railWidth, Sign } from "./sign";
import { Chip, CountUp, Dot, fitSize, Frame, group, In, Kicker, Logo, useIn, useStyle, useTheme } from "../ui";

const INNER = W - 2 * SIDE; // 952
const LOW = RAIL_X - SIDE; // text that reaches the lower part stays left of the like/share rail

type P = { s: Scene; inner?: number };

export const Hook: React.FC<P> = ({ s, inner = INNER }) => {
  const { v, props } = useTheme();
  const { hook } = useStyle();
  const frame = useCurrentFrame();
  const lines = s.lines ?? [];
  const kinetic = v === "kinetic";
  // stack: the lines as they are (kinetic inverts the last) · lead: the first line small and quiet, the rest large ·
  // blocks: every line in an ink block · underline: an ink rule draws under each line after it lands
  const lead = hook === "lead" && lines.length > 1;
  const blocks = hook === "blocks";
  const width = (inner - (kinetic || blocks ? 48 : 8)) * 0.92;
  const size = fitSize(lead ? lines.slice(1) : lines, width, kinetic ? 176 : 160, 44);
  const leadSize = fitSize([lines[0] ?? ""], width, 72, 40);
  const bar = useIn(8 + lines.length * 5, 22, 120);
  return (
    <Frame s={s} head={false}>
      <In><Kicker text={s.kicker ?? props.category} /></In>
      <div style={{ marginTop: 48 }}>
        {lines.map((l, i) => {
          const quiet = lead && i === 0;
          const block = blocks || (kinetic && hook === "stack" && i === lines.length - 1);
          const fs = quiet ? leadSize : size;
          const rule = hook === "underline"
            ? interpolate(frame - (12 + i * 6), [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
          return (
            <In key={i} delay={4 + i * 5}>
              <div style={{ position: "relative", fontFamily: FONT, fontWeight: quiet ? 600 : 700, fontSize: fs, lineHeight: 1.16,
                whiteSpace: "nowrap", color: block ? CANVAS : quiet ? MUTED : INK, background: block ? INK : "transparent",
                display: "inline-block", padding: block ? `0 ${fs * 0.14}px ${fs * 0.1}px` : 0,
                marginTop: block ? 12 : 0, marginBottom: quiet ? 20 : hook === "underline" ? 16 : 0 }}>
                {l}
                {hook === "underline" && (
                  <div style={{ position: "absolute", left: 0, bottom: -6, height: 8, width: `${rule * 100}%`, background: INK }} />
                )}
              </div>
            </In>
          );
        })}
      </div>
      <div style={{ display: "flex", alignItems: "center", marginTop: 40, gap: 0 }}>
        <div style={{ height: 8, width: 400 * bar, background: INK }} />
        <span style={{ transform: `scale(${bar})` }}><Dot size={28} pulse /></span>
      </div>
      <In delay={14 + lines.length * 5}>
        <div style={{ display: "flex", gap: 16, marginTop: 48 }}>
          <Chip solid size={38}>{fill(props.brand.strings.outlets, { n: props.sources.length })}</Chip>
          <Chip size={38}>{props.when}</Chip>
        </div>
      </In>
    </Frame>
  );
};

export const Stat: React.FC<P> = ({ s, inner = INNER }) => {
  const value = s.value ?? 0;
  const text = `${s.prefix ?? ""}${group(value)}${s.suffix ?? ""}`;
  const iso = Boolean(s.isotype && s.glyph); // a count of 2-30 things, drawn as that many icons (tt_shorts/icons.py)
  const size = fitSize([text], inner, iso ? 240 : 360, 120);
  const span = iso ? isoSpan(s.duration) : 32;
  const frame = useCurrentFrame();
  const cells = 20;
  const fill = interpolate(frame, [8, 40], [0, cells], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: (x) => 1 - Math.pow(1 - x, 3) });
  return (
    <Frame s={s}>
      <In delay={4}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1, color: INK, whiteSpace: "nowrap" }}>
          {s.prefix}<CountUp to={value} delay={4} frames={span} />{s.suffix}
        </div>
      </In>
      {iso ? <Isotype s={s} width={railWidth(inner)} height={inner < INNER - 40 ? 300 : 380} delay={4} span={span} /> : (
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 48, width: Math.min(inner, LOW) }}>
        {Array.from({ length: cells }, (_, i) => (
          <div key={i} style={{ flex: 1, height: 40, borderRadius: 4, background: i < fill ? INK : "transparent",
            border: `2px solid ${i < fill ? INK : LINE_STRONG}` }} />
        ))}
        <Dot size={24} pulse />
      </div>)}
      <In delay={14}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 64, lineHeight: 1.2, color: INK, marginTop: iso ? 40 : 48,
          maxWidth: iso ? railWidth(inner) : Math.min(inner, LOW) }}>
          {s.label}
        </div>
      </In>
    </Frame>
  );
};

const split = (x?: string) => {
  const [a, b] = (x ?? "").split(/,\s*/);
  return b ? { day: a, time: b } : { day: "", time: a };
};

export const Timeline: React.FC<P> = ({ s, inner = INNER }) => {
  const a = split(s.start), b = split(s.end);
  const frame = useCurrentFrame();
  const run = interpolate(frame, [12, 44], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: (x) => 1 - Math.pow(1 - x, 3) });
  const tight = inner < INNER - 40; // inside a card there is less height
  const size = fitSize([a.time, b.time], inner - 160, tight ? 176 : 220, 112);
  const H_ = tight ? 440 : 600;
  const block = (d: { day: string; time: string }, muted: boolean, delay: number) => (
    <In delay={delay}>
      <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 44, color: MUTED }}>{d.day}</div>
      <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.04, color: muted ? MUTED : INK }}>{d.time}</div>
    </In>
  );
  return (
    <Frame s={s}>
      <div style={{ display: "flex", gap: 48 }}>
        <svg width={56} height={H_} style={{ flex: "none" }}>
          <line x1={28} y1={44} x2={28} y2={H_ - 44} stroke={LINE_STRONG} strokeWidth={6} />
          <line x1={28} y1={44} x2={28} y2={44 + (H_ - 88) * run} stroke={INK} strokeWidth={6} />
          <circle cx={28} cy={44} r={18} fill={INK} />
          <circle cx={28} cy={H_ - 44} r={18} fill="none" stroke={LINE_STRONG} strokeWidth={4} />
          <circle cx={28} cy={44 + (H_ - 88) * run} r={24} fill={RED} />
        </svg>
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", height: H_ }}>
          {block(a, false, 4)}
          {block(b, run < 0.98, 18)}
        </div>
      </div>
      <In delay={28}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: tight ? 48 : 56, lineHeight: 1.2, color: INK, marginTop: tight ? 24 : 40,
          maxWidth: Math.min(inner, LOW) }}>
          {s.label}
        </div>
      </In>
    </Frame>
  );
};

export const Where: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const pin = useIn(2, 12, 180);
  // A long place name (ველის სასაფლაო, ლილოს ტერიტორია) overflowed the frame at the 72px floor;
  // split it into two balanced lines and let fitSize pick a size that actually fits.
  const words = String(s.place ?? "").split(" ").filter(Boolean);
  const half = Math.ceil(words.length / 2);
  const placeLines = words.length > 2 ? [words.slice(0, half).join(" "), words.slice(half).join(" ")] : [String(s.place ?? "")];
  const size = fitSize(placeLines, inner, 148, 54);
  return (
    <Frame s={s}>
      <div style={{ position: "relative", height: 460 }}>
        <svg width={inner} height={460} viewBox={`0 0 ${inner} 460`} style={{ position: "absolute", left: 0 }}>
          {[-3, -2, -1, 0, 1, 2, 3].map((k) => (
            <line key={`h${k}`} x1={0} y1={300 + k * 64} x2={inner} y2={300 + k * 64} stroke={LINE} strokeWidth={2} />
          ))}
          {[-6, -4, -2, 0, 2, 4, 6].map((k) => (
            <line key={`v${k}`} x1={inner / 2 + k * 64} y1={0} x2={inner / 2 + k * 64} y2={460} stroke={LINE} strokeWidth={2} />
          ))}
          {[0, 1, 2].map((i) => {
            const t = ((frame - i * 18) % 54) / 54;
            return frame >= i * 18 ? (
              <circle key={i} cx={inner / 2} cy={300} r={40 + t * 330} fill="none" stroke={INK} strokeWidth={3} opacity={(1 - t) * 0.5} />
            ) : null;
          })}
          <g transform={`translate(${inner / 2} 300) scale(${pin})`}>
            <path d="M0 -250c-74 0-130 56-130 128 0 96 130 222 130 222s130-126 130-222c0-72-56-128-130-128z" fill={INK} />
            <circle cx={0} cy={-122} r={46} fill={RED} />
          </g>
        </svg>
      </div>
      <In delay={10}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.12, color: INK, textAlign: "center",
          marginTop: 32 }}>{placeLines.map((l, i) => <div key={i}>{l}</div>)}</div>
      </In>
      <In delay={16}>
        <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 44, lineHeight: 1.3, color: MUTED, textAlign: "center", marginTop: 16 }}>
          {s.sub}
        </div>
      </In>
    </Frame>
  );
};

const initials = (n: string) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("");

export const Who: React.FC<P> = ({ s, inner = INNER }) => {
  const items = (s.items ?? []).slice(0, 3) as { name: string; role?: string }[];
  const width = Math.min(inner, LOW);
  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
        {items.map((it, i) => (
          <In key={i} delay={6 + i * 7}>
            <div style={{ display: "flex", alignItems: "center", gap: 40, padding: 40, width, background: PANEL, borderRadius: RADIUS,
              border: `2px solid ${i === 0 ? LINE_STRONG : LINE}` }}>
              <div style={{ position: "relative", width: 168, height: 168, borderRadius: 84, flex: "none", display: "flex",
                alignItems: "center", justifyContent: "center", fontFamily: FONT, fontWeight: 700, fontSize: 64,
                background: i === 0 ? INK : "transparent", color: i === 0 ? CANVAS : INK, border: i === 0 ? "none" : `3px solid ${LINE_STRONG}` }}>
                {initials(it.name)}
                {i === 0 && <span style={{ position: "absolute", right: 4, bottom: 8 }}><Dot size={32} /></span>}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: fitSize([it.name], width - 300, 68, 40), lineHeight: 1.2,
                  color: INK, whiteSpace: "nowrap" }}>{it.name}</div>
                <div style={{ fontFamily: FONT, fontWeight: 400, fontSize: 40, color: MUTED, marginTop: 8 }}>{it.role}</div>
              </div>
            </div>
          </In>
        ))}
      </div>
    </Frame>
  );
};

export const Points: React.FC<P> = ({ s, inner = INNER }) => {
  const items = (s.items ?? []).slice(0, 3) as string[];
  const frame = useCurrentFrame();
  const active = items.reduce((a, _, i) => (frame >= 6 + i * 10 ? i : a), 0);
  return (
    <Frame s={s}>
      {items.map((t, i) => (
        <In key={i} delay={6 + i * 10}>
          <div style={{ display: "flex", alignItems: "center", gap: 40, padding: "32px 0", borderTop: `2px solid ${LINE}`,
            width: Math.min(inner, LOW) }}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 120, lineHeight: 1, width: 120, flex: "none",
              color: i === active ? INK : MUTED }}>{i + 1}</div>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 64, lineHeight: 1.2, color: INK, flex: 1 }}>{t}</div>
            <span style={{ opacity: i === active ? 1 : 0 }}><Dot size={24} pulse /></span>
          </div>
        </In>
      ))}
    </Frame>
  );
};

export const Quote: React.FC<P> = ({ s }) => {
  const text = s.text ?? "";
  const size = text.length > 90 ? 64 : text.length > 60 ? 72 : 84;
  const mark = useIn(0, 12, 180);
  return (
    <Frame s={s}>
      <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 320, lineHeight: 0.5, height: 120, color: LINE_STRONG,
        transform: `scale(${mark})`, transformOrigin: "left bottom" }}>„</div>
      <In delay={6}>
        <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: size, lineHeight: 1.3, color: INK }}>„{text}“</div>
      </In>
      <In delay={16}>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 48, fontFamily: FONT, fontSize: 44 }}>
          <Dot size={22} />
          <span style={{ fontWeight: 700, color: INK }}>{s.by}</span>
          {s.via && <span style={{ fontWeight: 400, color: MUTED }}>· {s.via}</span>}
        </div>
      </In>
    </Frame>
  );
};

export const Sources: React.FC<P> = ({ s, inner = INNER }) => {
  const { props } = useTheme();
  const names = props.sources.slice(0, 8);
  const width = Math.min(inner, LOW);
  return (
    <Frame s={s}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 40 }}>
        <In delay={2}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 320, lineHeight: 0.92, color: INK }}>
            <CountUp to={props.sources.length} delay={2} frames={18} />
          </div>
        </In>
        <In delay={8}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 64, lineHeight: 1.16, color: INK, paddingBottom: 24 }}>
            {props.brand.strings.covered_by[0]}<br /><span style={{ color: MUTED }}>{props.brand.strings.covered_by[1]}</span>
          </div>
        </In>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginTop: 48, width }}>
        {names.map((n, i) => (
          <In key={n} delay={12 + i * 3}><Chip size={40}>{n}</Chip></In>
        ))}
      </div>
    </Frame>
  );
};

export const End: React.FC<P> = () => {
  const { props } = useTheme();
  const qr = useIn(10, 16, 140);
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center" }}>
      <In><Logo place="end" size={176} /></In>
      <div style={{ marginTop: 40, width: 416, height: 416, background: "#FFFFFF", padding: 16, borderRadius: RADIUS,
        transform: `scale(${0.7 + 0.3 * qr})`, opacity: qr }} dangerouslySetInnerHTML={{ __html: props.qrSvg }} />
      <In delay={16}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 44, color: INK, marginTop: 32 }}>{props.url}</div>
      </In>
      <In delay={22}>
        <div style={{ marginTop: 32, background: RED, color: ON_ACCENT, fontFamily: FONT, fontWeight: 700, fontSize: 48,
          padding: "20px 48px 26px", borderRadius: 999, whiteSpace: "nowrap" }}>{props.cta}</div>
      </In>
    </div>
  );
};

export const SCENES: Record<string, React.FC<P>> = {
  hook: Hook, stat: Stat, timeline: Timeline, where: Where, who: Who, points: Points, quote: Quote, sources: Sources, draw: Draw,
  pair: Pair, steps: Steps, bars: Bars, trend: Trend, change: Change, sign: Sign, end: End,
};
