// The motion brushes (brushes/kinetic.json, brushes/odometer.json): an editorial word-by-word headline and a
// mechanical counter. Both are pure functions of the frame, in the pack's font and ink, and both keep their text
// inside the scene band and left of the like/share rail (low()).
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT, INK, RAIL_X, SIDE, W } from "../brand";
import type { Scene } from "../types";
import { Mark, marked } from "../marker";
import { beat, fitSize, Frame, group, In, Kicker, measure, useMotion, useOpening } from "../ui";

const INNER = W - 2 * SIDE; // 952
const low = (inner: number) => Math.min(inner, RAIL_X - (W - inner) / 2);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);

type P = { s: Scene; inner?: number };

/** A `text` scene's lines: its words split into at most `n` balanced lines (no line is longer than the others by
 *  more than a word). */
const chunk = (text: string, n: number) => {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length <= n) return words;
  const total = words.reduce((a, w) => a + w.length + 1, 0);
  const out: string[] = [];
  let cur: string[] = [], at = 0;
  for (const w of words) {
    const next = at + w.length + 1;
    if (cur.length && out.length < n - 1 && next / total > (out.length + 1) / n) {
      out.push(cur.join(" "));
      cur = [];
    }
    cur.push(w);
    at = next;
  }
  out.push(cur.join(" "));
  return out;
};

/** The size a line of words takes: its own words measured with the gap between them, shrunk only if the line would
 *  still run past the column (a long Georgian word is the whole line). */
const lineSize = (words: string[], size: number, width: number) => {
  const gap = size * 0.26;
  const total = words.reduce((a, w) => a + (measure(w, 700) * size) / 100, 0) + gap * Math.max(0, words.length - 1);
  return total <= width ? size : Math.max(28, Math.floor(((size * width) / total) / 4) * 4);
};

/** A headline revealed word by word from behind its own mask, then still: lines (1-3) or one text split into them.
 *  Words come in five frames apart (four to six with a director's stagger); the opening is readable at frame 0. */
export const Kinetic: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const opening = useOpening();
  const m = useMotion();
  const lines = (s.lines?.length ? s.lines : chunk(s.text ?? "", 3)).slice(0, 3).map((l) => l.trim()).filter(Boolean);
  const width = low(inner);
  const max = lines.length <= 1 ? 176 : lines.length === 2 ? 152 : 128;
  const size = fitSize(lines, width, max, 40);
  const step = m ? Math.max(4, Math.min(6, m.stagger_frames)) : 5;
  let k = 0;
  if (!lines.length) return null;
  return (
    <Frame s={s} head={false}>
      <In><Kicker text={s.kicker} /></In>
      <div style={{ marginTop: 48 }}>
        {lines.map((line, li) => {
          const words = line.split(/\s+/).filter(Boolean);
          const fs = lineSize(words, size, width);
          return (
            <div key={li} style={{ display: "flex", alignItems: "flex-end", columnGap: Math.round(fs * 0.26),
              fontFamily: FONT, fontWeight: 700, fontSize: fs, lineHeight: 1.12, color: INK }}>
              {words.map((w, wi) => {
                const at = 6 + k * step;
                k += 1;
                const t = opening ? 1 : interpolate(frame - at, [0, 14], [0, 1], { ...clamp, easing: easeOut });
                return (
                  <span key={wi} data-probe-clip style={{ display: "inline-block", overflow: "hidden",
                    padding: "0.05em 0 0.18em", margin: "-0.05em 0 -0.18em" }}>
                    <span style={{ display: "inline-block", transform: `translateY(${(1 - t) * 108}%)`,
                      opacity: opening ? 1 : Math.min(1, t * 2.4) }}>{w}</span>
                  </span>
                );
              })}
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

/** One wheel of the counter: a window the digits roll through, drawn only as the two digits in view (the layout
 *  probe sees nothing clipped). A digit starting at zero still makes a full turn, as a mechanical counter does. */
const Wheel: React.FC<{ to: number; t: number; spins: number; size: number }> = ({ to, t, spins, size }) => {
  const pos = (to + 10 * spins) * t;
  const base = Math.floor(pos + 1e-6);
  const frac = pos - base;
  const w = (Math.max(..."0123456789".split("").map((d) => measure(d, 700))) * size) / 100;
  const digit = (n: number, y: number) => (
    <span key={n} style={{ position: "absolute", left: 0, top: y, width: w, textAlign: "center" }}>{(n % 10 + 10) % 10}</span>
  );
  return (
    <span data-probe-clip style={{ position: "relative", display: "inline-block", width: w, height: size,
      overflow: "hidden", verticalAlign: "top" }}>
      {digit(base, -frac * size)}
      {frac > 0.002 && digit(base + 1, (1 - frac) * size)}
    </span>
  );
};

/** A whole number that rolls from zero to its value digit by digit, grouped the Georgian way (6 400), with an
 *  optional prefix, suffix and a label under it. */
export const Odometer: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const value = Math.max(0, Math.round(s.value ?? 0));
  const width = low(inner);
  const digits = group(value);
  const count = (digits.match(/\d/g) ?? []).length;
  const gaps = digits.length - count;
  // the wheels are as wide as the widest digit: size by what is actually drawn, never by the text's own run
  const digit100 = Math.max(..."0123456789".split("").map((d) => measure(d, 700)));
  const est100 = measure(s.prefix ?? "", 700) + measure(s.suffix ?? "", 700) + count * digit100 + gaps * measure(" ", 700);
  const raw = Math.floor((100 * width) / Math.max(1, est100));
  const size = Math.max(80, Math.min(320, raw - (raw % 4)));
  const space = Math.round((measure(" ", 700) * size) / 100);
  const span = Math.min(40, Math.max(18, s.duration - 16)); // settled well before the scene leaves
  let k = -1;
  return (
    <Frame s={s}>
      <In delay={4}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1, color: INK, whiteSpace: "nowrap" }}>
          <Mark s={s} field="value" px={size}>
            <>
              {s.prefix}
              {digits.split("").map((c, i) => {
                if (!/\d/.test(c)) return <span key={i} style={{ display: "inline-block", width: space }} />;
                k += 1;
                const right = count - 1 - k; // digits to its right spin more and settle last
                const t = interpolate(frame - 4 - k * 2, [0, span + right * 3], [0, 1], { ...clamp, easing: easeOut });
                return <Wheel key={i} to={Number(c)} t={t} spins={Math.min(2, right) + (Number(c) === 0 ? 1 : 0)} size={size} />;
              })}
              {s.suffix}
            </>
          </Mark>
        </div>
      </In>
      <In delay={14} at={beat(s, "label")}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 64, lineHeight: 1.2, color: INK, marginTop: 48,
          maxWidth: width }}>
          {marked(s, "label", s.label, { px: 64 })}
        </div>
      </In>
    </Frame>
  );
};
