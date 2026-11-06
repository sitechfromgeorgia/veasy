// Context visuals (brushes/kpi-grid.json, brushes/ticker.json): four numbers counted on a 2x2 grid, and a running
// line of headlines at the bottom of the scene band. Every motion is a pure function of the frame; colors are the
// pack's tokens (brand.ts) and the accent is only ever the dot. Text stays inside the safe zone by construction:
// both blocks are as wide as the column left of the like/share rail (RAIL_X) and end above the caption band.
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { FONT, INK, LINE, LINE_STRONG, MUTED, RAIL_X, SIDE, W } from "../brand";
import { marked } from "../marker";
import type { Scene } from "../types";
import { beat, fitSize, Frame, In, Kicker, measure } from "../ui";

const INNER = W - 2 * SIDE; // 952
// text that reaches the lower part stays left of the like/share rail (a card's content starts further right)
const low = (inner: number) => Math.min(inner, RAIL_X - (W - inner) / 2);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);

type P = { s: Scene; inner?: number };

/** Georgian numbers: thousands grouped with a space, decimals with a comma ("4 200", "12,5"). */
const decimalsOf = (v: number) => (String(v).split(".")[1] ?? "").length;
const num = (v: number, d: number) => {
  const [i, f] = Math.abs(v).toFixed(d).split(".");
  return (v < 0 ? "-" : "") + i.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + (f ? "," + f : "");
};

// ---------------------------------------------------------------- kpi-grid

/** One cell's number, counting up from zero from the frame it arrives. */
const Cell: React.FC<{ to: number; delay: number }> = ({ to, delay }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame - delay, [0, 26], [0, 1], { ...clamp, easing: easeOut });
  return <>{num(to * t, decimalsOf(to))}</>;
};

/** Four numbers in a 2x2 grid (brushes/kpi-grid.json: exactly four items), a thin cross between the cells. */
export const KpiGrid: React.FC<P> = ({ s, inner = INNER }) => {
  const width = low(inner) - 12; // clear of the rail's edge
  const cells = (s.items ?? [])
    .map((it) => (typeof it === "object" && it !== null
      ? { value: typeof it.value === "number" ? it.value : 0, label: it.label ?? "" }
      : { value: 0, label: "" }))
    .filter((c) => c.label.trim() !== "")
    .slice(0, 4);
  if (!cells.length) return null;
  const cellW = (width - 48) / 2;
  return (
    <Frame s={s}>
      <div style={{ width, display: "grid", gridTemplateColumns: "1fr 1fr", borderTop: `2px solid ${LINE_STRONG}`,
        borderBottom: `2px solid ${LINE_STRONG}` }}>
        {cells.map((c, i) => {
          const at = beat(s, `items.${i}`);
          const start = at ?? 6 + i * 7;
          const size = fitSize([num(c.value, decimalsOf(c.value))], cellW - 8, 132, 56);
          return (
            <div key={i} style={{ padding: i % 2 ? "34px 0 30px 40px" : "34px 40px 30px 0",
              borderTop: i >= 2 ? `2px solid ${LINE}` : "none", borderLeft: i % 2 ? `2px solid ${LINE}` : "none" }}>
              <In delay={4 + i * 6} at={at}>
                <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1, color: INK,
                  whiteSpace: "nowrap" }}>
                  <Cell to={c.value} delay={start} />
                </div>
                <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 36, lineHeight: 1.25, color: MUTED,
                  marginTop: 14, maxWidth: cellW - 8 }}>
                  {marked(s, `items.${i}.label`, c.label, { px: 36 })}
                </div>
              </In>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- ticker

/** Three to five short headlines running right to left above the caption band (brushes/ticker.json). The kicker is
 *  drawn here, over the line, so the brush carries no headline. The moving line is the probe's `ticker` region: it
 *  leaves the frame by design, and its box is the column left of the rail, above the captions, by construction. */
export const Ticker: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const width = low(inner) - 8;
  const items = (s.items ?? []).filter((x): x is string => typeof x === "string" && x.trim() !== "").slice(0, 5);
  if (!items.length) return null;
  const size = 44;
  const sep = "   ·   ";
  const line = items.join(sep) + sep;
  const unit = Math.max(80, (measure(line, 700) * size) / 100);
  const reps = Math.max(2, Math.ceil((width * 2) / unit) + 1);
  const speed = 2.6; // px a frame: a headline takes about four seconds to pass
  const x = -((frame * speed) % unit);
  const fade = "linear-gradient(to right, transparent, #000 7%, #000 93%, transparent)";
  return (
    <Frame s={s} head={false}>
      <div style={{ marginTop: "auto", marginBottom: 40, width }}>
        <In delay={2} at={beat(s, "kicker")}><Kicker text={s.kicker} /></In>
        {s.headline && (
          <In delay={6}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 56, lineHeight: 1.2, color: INK, marginTop: 22,
              maxWidth: width }}>
              {marked(s, "headline", s.headline, { px: 56 })}
            </div>
          </In>
        )}
        <div style={{ height: 2, background: LINE_STRONG, marginTop: 18 }} />
        <div data-probe="ticker" style={{ position: "relative", overflow: "hidden", height: 60, marginTop: 20,
          maskImage: fade, WebkitMaskImage: fade }}>
          <div style={{ position: "absolute", left: 0, top: 0, whiteSpace: "pre", fontFamily: FONT, fontWeight: 700,
            fontSize: size, lineHeight: 1.25, color: INK, transform: `translateX(${x}px)` }}>
            {line.repeat(reps)}
          </div>
        </div>
      </div>
    </Frame>
  );
};
