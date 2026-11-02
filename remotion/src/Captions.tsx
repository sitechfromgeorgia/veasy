import React from "react";
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { alpha, CANVAS, CAPTION_BOTTOM, FONT, H, INK, LINE, RADIUS, RAIL_X, RED, W, WAITING } from "./brand";
import type { CaptionLayout, CaptionWord } from "./types";

// Captions draw a layout computed once in Python (tt_shorts/captions.py): the same lines and pages in every frame
// and every render tab, one font size per video. Nothing here measures text. Position is a pure function of time:
// "page" never moves the block, "roll" scrolls continuously, so neither can jump (owner, 2026-11-02).

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);
const easeInOut = Easing.inOut(Easing.cubic);

/** One word: dim until spoken, ink once spoken; the word being said gets the red underline (an active state).
 *  Only color and a transform change, so the line never reflows. */
const Word: React.FC<{ w: CaptionWord; next?: CaptionWord; t: number; last: boolean }> = ({ w, next, t, last }) => {
  const said = t >= w.from - 0.04;
  const until = next ? next.from : w.to + 0.35;
  const active = t >= w.from - 0.04 && t < until;
  const grow = interpolate(t - w.from, [0, 0.12], [0, 1], { ...clamp, easing: easeOut });
  return (
    <span style={{ position: "relative", display: "inline-block", marginRight: last ? 0 : "0.27em", color: said ? INK : WAITING }}>
      {w.text}
      <span style={{ position: "absolute", left: 0, right: 0, bottom: -4, height: 5, borderRadius: 3, background: RED,
        transform: `scaleX(${active ? grow : 0})`, transformOrigin: "left" }} />
    </span>
  );
};

const LineView: React.FC<{ words: CaptionWord[]; t: number; size: number; lineHeight: number }> = ({ words, t, size, lineHeight }) => (
  <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight, whiteSpace: "nowrap", textAlign: "center" }}>
    {words.map((w, k) => <Word key={k} w={w} next={words[k + 1]} t={t} last={k === words.length - 1} />)}
  </div>
);

/** A fixed two-line block. The block and its geometry never change; a new page fades in over ~4 frames. */
const PageCaptions: React.FC<{ cap: CaptionLayout; t: number }> = ({ cap, t }) => {
  const { size, lineHeight, band, pad, lines, pages } = cap;
  let i = -1;
  for (let k = 0; k < pages.length; k++) if (pages[k].start <= t) i = k;
  if (i < 0) return null;
  const p = pages[i];
  const prevEnd = i > 0 ? pages[i - 1].end : -1;
  const afterGap = p.start - prevEnd > 0.05; // the box itself fades in only after a real silence
  const enter = interpolate(t - p.start, [0, 0.14], [0, 1], { ...clamp, easing: easeOut });
  const out = interpolate(t, [p.end - 0.18, p.end], [1, 0], clamp);
  const boxIn = afterGap ? interpolate(t - p.start, [0, 0.2], [0, 1], clamp) : 1;
  const rowH = size * lineHeight;
  return (
    <div style={{ position: "absolute", left: W - RAIL_X, width: band, bottom: H - CAPTION_BOTTOM, height: rowH * 2 + 2 * 14,
      background: alpha(CANVAS, 0.8), border: `2px solid ${LINE}`, borderRadius: RADIUS, opacity: Math.min(boxIn, out),
      display: "flex", alignItems: "center", justifyContent: "center", padding: `0 ${pad}px` }}>
      <div style={{ opacity: enter, transform: `translateY(${(1 - enter) * 10}px)` }}>
        {p.lines.map((li) => <LineView key={li} words={lines[li].words} t={t} size={size} lineHeight={lineHeight} />)}
      </div>
    </div>
  );
};

/** A teleprompter: every line in one column, scrolled by a continuous function of time. Each line start adds one
 *  eased step; overlapping steps simply add, so the motion is monotonic and smooth. The middle line is full size,
 *  its neighbours shrink and fade with their distance from it. */
const RollCaptions: React.FC<{ cap: CaptionLayout; t: number }> = ({ cap, t }) => {
  const { size, lineHeight, band, lines, pages } = cap;
  if (!lines.length) return null;
  let pos = 0;
  for (let k = 1; k < lines.length; k++) {
    const T = Math.min(0.26, 0.6 * Math.max(0.12, lines[k].start - lines[k - 1].start));
    pos += interpolate(t - lines[k].start, [0, T], [0, 1], { ...clamp, easing: easeInOut });
  }
  const rowH = size * lineHeight + 10;
  const last = pages[pages.length - 1];
  const fade = Math.min(interpolate(t, [lines[0].start - 0.2, lines[0].start], [0, 1], clamp),
    interpolate(t, [last.end - 0.25, last.end], [1, 0], clamp));
  const viewH = rowH * 3;
  return (
    <div style={{ position: "absolute", left: W - RAIL_X, width: band, bottom: H - CAPTION_BOTTOM, height: viewH + 24,
      background: alpha(CANVAS, 0.62), borderRadius: RADIUS, overflow: "hidden", opacity: fade,
      WebkitMaskImage: "linear-gradient(to bottom, transparent 0, #000 22%, #000 78%, transparent 100%)",
      maskImage: "linear-gradient(to bottom, transparent 0, #000 22%, #000 78%, transparent 100%)" }}>
      {lines.map((l, i) => {
        const d = i - pos;
        if (Math.abs(d) > 2) return null;
        const scale = interpolate(Math.abs(d), [0, 1], [1, 0.62], clamp);
        const opacity = interpolate(Math.abs(d), [0, 1, 1.7], [1, 0.45, 0], clamp);
        return (
          <div key={i} style={{ position: "absolute", left: 0, right: 0, top: (viewH + 24) / 2 - rowH / 2 + d * rowH * 0.78,
            height: rowH, display: "flex", alignItems: "center", justifyContent: "center", opacity,
            transform: `scale(${scale})`, transformOrigin: "center" }}>
            <LineView words={l.words} t={t} size={size} lineHeight={lineHeight} />
          </div>
        );
      })}
    </div>
  );
};

export const Captions: React.FC<{ cap: CaptionLayout | null }> = ({ cap }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!cap || !cap.lines.length) return null;
  const t = frame / fps;
  return cap.design === "roll" ? <RollCaptions cap={cap} t={t} /> : <PageCaptions cap={cap} t={t} />;
};
