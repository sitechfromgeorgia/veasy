import React, { useMemo } from "react";
import { AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import {
  CANVAS, CAPTION_BOTTOM, FONT, GRID, H, INK, LINE, LINE_STRONG, MUTED, PANEL, RADIUS, RAIL_X, RED, SCENE_BOTTOM, SCENE_TOP, SIDE,
  TICKER, W,
} from "./brand";
import { SCENES } from "./scenes";
import type { ShortProps, Word } from "./types";
import { Chip, Dot, fitSize, Mark, measure, Theme, useTheme, Wordmark } from "./ui";

const EXIT = 7; // frames a scene takes to leave
const CARD_PAD = 48;

const Background: React.FC = () => {
  const { v } = useTheme();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const cell = 72;
  const pan = interpolate(frame, [0, durationInFrames], [0, cell]);
  return (
    <AbsoluteFill style={{ background: CANVAS }}>
      <svg width={W} height={H + cell} style={{ position: "absolute", top: -cell + pan }}>
        <defs>
          <pattern id="g" width={cell} height={cell} patternUnits="userSpaceOnUse">
            {v === "kinetic"
              ? <path d={`M0 ${cell}L${cell} 0`} fill="none" stroke={GRID} strokeWidth={2} />
              : <path d={`M${cell} 0H0V${cell}`} fill="none" stroke={GRID} strokeWidth={2} />}
          </pattern>
        </defs>
        <rect width={W} height={H + cell} fill="url(#g)" />
      </svg>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 36%, rgba(5,8,15,0) 45%, rgba(5,8,15,.9) 100%)" }} />
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
      <div style={{ position: "absolute", left: SIDE, top: 80, display: "flex", alignItems: "center", gap: 24 }}>
        <Mark size={88} />
        <Wordmark size={44} />
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

/** The cut between scenes: an ink line with the red dot sweeps across (editorial, cards) or an ink panel wipes (kinetic). */
const Cut: React.FC = () => {
  const frame = useCurrentFrame();
  const { v } = useTheme();
  if (frame > 10) return null;
  const x = interpolate(frame, [0, 10], [-W, W], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (v === "kinetic") {
    return <div style={{ position: "absolute", left: x, top: SCENE_TOP, width: W, height: SCENE_BOTTOM - SCENE_TOP, background: INK }} />;
  }
  return (
    <div style={{ position: "absolute", left: x, top: SCENE_TOP - 24, width: W, display: "flex", alignItems: "center" }}>
      <div style={{ flex: 1, height: 4, background: INK }} /><Dot size={20} />
    </div>
  );
};

const SceneSlot: React.FC<{ i: number }> = ({ i }) => {
  const { v, props } = useTheme();
  const s = props.scenes[i];
  const frame = useCurrentFrame();
  const Comp = SCENES[s.type];
  const last = i === props.scenes.length - 1;
  const out = last ? 1 : interpolate(frame, [s.duration - EXIT, s.duration], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (v === "cards" && s.type !== "end") {
    const enter = interpolate(frame, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (t) => 1 - Math.pow(1 - t, 3) });
    return (
      <div style={{ position: "absolute", left: SIDE - 16, right: SIDE - 16, top: SCENE_TOP, bottom: H - SCENE_BOTTOM, background: PANEL,
        border: `2px solid ${LINE}`, borderRadius: RADIUS, opacity: Math.min(enter, out),
        transform: `translateY(${(1 - enter) * 120 + (1 - out) * -40}px) scale(${0.96 + 0.04 * Math.min(enter, out)})` }}>
        <div style={{ position: "absolute", left: CARD_PAD, right: CARD_PAD, top: CARD_PAD, bottom: 120 }}>
          {Comp ? <Comp s={s} inner={W - 2 * (SIDE - 16) - 2 * CARD_PAD} /> : null}
        </div>
        <div style={{ position: "absolute", left: CARD_PAD, right: CARD_PAD, bottom: 40, borderTop: `2px solid ${LINE}`, paddingTop: 20,
          display: "flex", justifyContent: "space-between", fontFamily: FONT, fontSize: 30, color: MUTED }}>
          <span>{props.sources.length} წყარო · {props.date.time}</span>
          <span>{i + 1} / {props.scenes.length - 1}</span>
        </div>
      </div>
    );
  }
  return (
    <div style={{ position: "absolute", left: SIDE, right: SIDE, top: SCENE_TOP, height: SCENE_BOTTOM - SCENE_TOP, opacity: out,
      transform: `translateY(${(1 - out) * -48}px)` }}>
      {Comp ? <Comp s={s} /> : null}
    </div>
  );
};

/** Three-line rolling captions (owner, 2026-11-02): the line just spoken stays above in small type, the
 *  active line is large in the middle, the next line waits below in small type, and the stack rises as the
 *  voice moves on. A line is at most three words and always fits the 800px safe band, so nothing is clipped. */
const CAP_MAX = 66;
const CAP_MIN = 40;
const CAP_SMALL = 32;
const CAP_BAND = 2 * RAIL_X - W - 32;
const CAP_INNER = CAP_BAND - 52; // the box padding, so a line that fits here never wraps inside
const CAP_ROW = 92;

const chunk = (words: Word[]) => {
  const out: Word[][] = [];
  for (const w of words) {
    const cur = out[out.length - 1];
    const cand = cur ? [...cur, w] : [w];
    const wide = (measure(cand.map((x) => x.text).join(" "), 700) * CAP_MAX) / 100 > CAP_INNER;
    const pause = !!cur && !!cur.length && w.start - cur[cur.length - 1].end > 0.25;
    if (!cur || cur.length === 3 || pause || wide) out.push([w]);
    else cur.push(w);
  }
  return out;
};

const Captions: React.FC = () => {
  const { props } = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const chunks = useMemo(() => chunk(props.words), [props.words]);
  const idx = chunks.findIndex((c, k) => t >= c[0].start - 0.05 && t < (chunks[k + 1]?.[0].start ?? 1e9));
  if (idx < 0) return null;
  const c = chunks[idx];
  const prev = chunks[idx - 1];
  const next = chunks[idx + 1];
  // The active line stays pinned; only its own entrance is animated. Moving the whole stack made the
  // block jump down at every chunk boundary (owner: "ტიტრები დახტის, თითქოს გაჭედა").
  const enter = Math.min(1, Math.max(0, (t - (c[0].start - 0.02)) / 0.18));
  const size = fitSize([c.map((w) => w.text).join(" ")], CAP_INNER, CAP_MAX, 38);
  const line = (words: Word[], fs: number, dim: number) => (
    <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: fs, lineHeight: 1.18, color: INK, opacity: dim,
      textAlign: "center", maxWidth: CAP_BAND, margin: "0 auto", overflowWrap: "break-word" }}>
      {words.map((w) => w.text).join(" ")}
    </div>
  );
  return (
    <div style={{ position: "absolute", left: W - RAIL_X, width: CAP_BAND, bottom: H - CAPTION_BOTTOM, height: CAP_ROW * 3,
      overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
      <div>
        {prev ? line(prev, CAP_SMALL, 0.45) : <div style={{ height: CAP_SMALL * 1.18 }} />}
        <div style={{ background: "rgba(5,8,15,.78)", border: `2px solid ${LINE}`, borderRadius: RADIUS, padding: "8px 24px 14px",
          minHeight: CAP_MAX * 1.16 + 26, display: "flex", alignItems: "center", justifyContent: "center",
          opacity: 0.55 + 0.45 * enter, transform: `translateY(${(1 - enter) * 8}px)` }}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.16, color: INK, textAlign: "center",
            whiteSpace: "nowrap" }}>
            {c.map((w, k) => {
              const end = c[k + 1]?.start ?? w.end + 0.4;
              const on = t >= w.start && t < end;
              const said = t >= end;
              const grow = interpolate(t - w.start, [0, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
              return (
                <span key={k} style={{ position: "relative", display: "inline-block", marginRight: k < c.length - 1 ? "0.26em" : 0,
                  color: on || said ? INK : MUTED }}>
                  {w.text}
                  <span style={{ position: "absolute", left: 0, right: 0, bottom: -5, height: 4, borderRadius: 2, background: RED,
                    transform: `scaleX(${on ? grow : 0})`, transformOrigin: "left" }} />
                </span>
              );
            })}
          </div>
        </div>
        {next ? line(next, CAP_SMALL, 0.45) : <div style={{ height: CAP_SMALL * 1.18 }} />}
      </div>
    </div>
  );
};

/** The band the platforms cover with their own UI: no story text there, only motion that fills it. */
const Ticker: React.FC = () => {
  const { v, props } = useTheme();
  const frame = useCurrentFrame();
  const rows = [[props.category, props.date.date, ...props.sources, "tbilisi.today"].join("  ·  ")];
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
  return (
    <div style={{ position: "absolute", left: SIDE, right: SIDE, top: 1768, borderTop: `2px solid ${LINE}`, paddingTop: 16, fontFamily: FONT }}>
      <div style={{ fontWeight: 400, fontSize: 28, lineHeight: 1.4, color: MUTED, whiteSpace: "nowrap", overflow: "hidden" }}>{props.sourcesLine}</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontWeight: 700, fontSize: 36, lineHeight: 1.4, color: INK }}>{props.url}</span>
        {/* tbilisi.today is a SiTech platform (the site's footer says so): the agency's link, quieter than the story's */}
        <span style={{ fontSize: 28, lineHeight: 1.4, color: MUTED }}>
          SiTech-ის პროექტი · <span style={{ fontWeight: 700, color: INK }}>sitech.ge</span>
        </span>
      </div>
    </div>
  );
};

export const NewsShort: React.FC<ShortProps> = (props) => {
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
        <Captions />
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
