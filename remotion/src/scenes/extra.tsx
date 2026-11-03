// Extra scene types added for Veasy: ranking, versus, countdown, calendar, glossary, checklist, impact, route, budget.
// Every motion is a pure function of frame; colors are brand tokens; the red accent is only for the dot or active marker.
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { CANVAS, FONT, INK, LINE, LINE_STRONG, MUTED, ON_ACCENT, PANEL, RADIUS, RAIL_X, RED, SIDE, W } from "../brand";
import { marked } from "../marker";
import type { Scene } from "../types";
import { Chip, CountUp, Dot, fitSize, Frame, In, measure, stepped, useIn, useTheme } from "../ui";

const INNER = W - 2 * SIDE; // 952
const low = (inner: number) => Math.min(inner, RAIL_X - (W - inner) / 2);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.out(Easing.cubic);

type P = { s: Scene; inner?: number };

const num = (v: number, decimals = 0) => {
  const [i, d] = Math.abs(v).toFixed(decimals).split(".");
  return (v < 0 ? "-" : "") + i.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + (d ? "," + d : "");
};

// ---------------------------------------------------------------- 1. Ranking
export const Ranking: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const width = low(inner);
  const items = (s.items ?? []).filter((it): it is { label: string; rank?: number; value?: number } =>
    typeof it === "object" && it !== null && typeof it.label === "string"
  );
  if (!items.length) return null;
  const maxVal = Math.max(...items.map((it) => (typeof it.value === "number" ? it.value : 0)), 1);

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", gap: items.length > 3 ? 20 : 28, width, marginTop: 12 }}>
        {items.map((it, i) => {
          const rankNum = it.rank ?? i + 1;
          const t = interpolate(frame - (6 + i * 5), [0, 16], [0, 1], { ...clamp, easing: easeOut });
          const barW = typeof it.value === "number" ? Math.max(12, ((width - 240) * it.value * t) / maxVal) : 0;
          return (
            <In key={i} delay={4 + i * 5}>
              <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                {/* Rank Badge */}
                <div style={{
                  width: 56, height: 56, borderRadius: 12, background: rankNum === 1 ? INK : LINE,
                  color: rankNum === 1 ? CANVAS : INK, display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: FONT, fontWeight: 700, fontSize: 32, flex: "none"
                }}>
                  {rankNum}
                </div>
                {/* Label and Value */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 }}>
                    <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 36, lineHeight: 1.2, color: INK, whiteSpace: "nowrap", overflow: "hidden" }}>
                      {marked(s, `items.${i}.label`, it.label, { px: 36 })}
                    </div>
                    {typeof it.value === "number" && (
                      <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 34, color: INK, whiteSpace: "nowrap" }}>
                        {num(it.value * t)} {s.unit ?? ""}
                      </div>
                    )}
                  </div>
                  {/* Proportional track */}
                  {typeof it.value === "number" && (
                    <div style={{ marginTop: 8, height: 8, width: "100%", background: LINE, borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: barW, background: rankNum === 1 ? INK : MUTED, borderRadius: 4 }} />
                    </div>
                  )}
                </div>
              </div>
            </In>
          );
        })}
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 2. Versus
export const Versus: React.FC<P> = ({ s, inner = INNER }) => {
  const width = low(inner);
  const items = s.items ?? [];
  const sideA = typeof items[0] === "object" ? items[0] : { title: "მხარე ა" };
  const sideB = typeof items[1] === "object" ? items[1] : { title: "მხარე ბ" };
  const between = s.between ?? "VS";

  const cardW = Math.floor((width - 40) / 2);

  return (
    <Frame s={s}>
      <div style={{ display: "flex", alignItems: "stretch", justifyContent: "space-between", width, marginTop: 24, position: "relative" }}>
        {/* Side A */}
        <In delay={4} style={{ width: cardW }}>
          <div style={{
            width: "100%", boxSizing: "border-box", padding: "24px 18px", background: PANEL, border: `2px solid ${LINE}`,
            borderRadius: RADIUS, display: "flex", flexDirection: "column", gap: 10, minHeight: 260
          }}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 28, lineHeight: 1.25, color: INK, wordBreak: "break-word" }}>
              {marked(s, "items.0.title", sideA.title ?? "", { px: 28 })}
            </div>
            {sideA.value !== undefined && (
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 50, lineHeight: 1, color: INK, marginTop: 8 }}>
                {String(sideA.value)}
              </div>
            )}
            {sideA.note && (
              <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 24, lineHeight: 1.3, color: MUTED }}>
                {sideA.note}
              </div>
            )}
          </div>
        </In>

        {/* Between Badge */}
        <In delay={12} style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%, -50%)", zIndex: 2 }}>
          <div style={{
            background: INK, color: CANVAS, borderRadius: 999, padding: "8px 16px",
            fontFamily: FONT, fontWeight: 700, fontSize: 26
          }}>
            {between}
          </div>
        </In>

        {/* Side B */}
        <In delay={8} style={{ width: cardW }}>
          <div style={{
            width: "100%", boxSizing: "border-box", padding: "24px 18px", background: PANEL, border: `2px solid ${LINE}`,
            borderRadius: RADIUS, display: "flex", flexDirection: "column", gap: 10, minHeight: 260
          }}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 28, lineHeight: 1.25, color: INK, wordBreak: "break-word" }}>
              {marked(s, "items.1.title", sideB.title ?? "", { px: 28 })}
            </div>
            {sideB.value !== undefined && (
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 50, lineHeight: 1, color: INK, marginTop: 8 }}>
                {String(sideB.value)}
              </div>
            )}
            {sideB.note && (
              <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 24, lineHeight: 1.3, color: MUTED }}>
                {sideB.note}
              </div>
            )}
          </div>
        </In>
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 3. Countdown
export const Countdown: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const width = low(inner);
  const val = s.value ?? 0;
  const unit = s.unit ?? "დღე";
  const numSize = fitSize([`${val} ${unit}`], width, 180, 80);

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", width, marginTop: 16 }}>
        {/* Hero count */}
        <In delay={4}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 20 }}>
            <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: numSize, lineHeight: 0.95, color: INK }}>
              <CountUp to={val} delay={4} frames={24} />
            </span>
            <span style={{ fontFamily: FONT, fontWeight: 600, fontSize: Math.round(numSize * 0.45), color: MUTED }}>
              {unit}
            </span>
          </div>
        </In>

        {/* Target Milestone Pill */}
        {s.target && (
          <In delay={12}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 28 }}>
              <Chip size={38} solid>{s.target}</Chip>
              <Dot size={20} pulse />
            </div>
          </In>
        )}

        {/* Label description */}
        <In delay={18}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 44, lineHeight: 1.25, color: INK, marginTop: 32, maxWidth: width }}>
            {marked(s, "label", s.label ?? "", { px: 44 })}
          </div>
        </In>
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 4. Calendar
export const Calendar: React.FC<P> = ({ s, inner = INNER }) => {
  const width = low(inner);
  const cardW = Math.min(width, 580);

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", width: cardW, marginTop: 12 }}>
        {/* Calendar Page Container */}
        <In delay={4}>
          <div style={{ borderRadius: RADIUS, border: `3px solid ${LINE}`, overflow: "hidden", background: PANEL }}>
            {/* Header: Month & Weekday */}
            <div style={{ background: INK, color: CANVAS, padding: "16px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: 36 }}>{s.month ?? ""}</span>
              {s.weekday && <span style={{ fontFamily: FONT, fontWeight: 600, fontSize: 28, opacity: 0.85 }}>{s.weekday}</span>}
            </div>
            {/* Big Day Numeral */}
            <div style={{ padding: "36px 24px", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 160, lineHeight: 0.9, color: INK }}>
                {s.day ?? 1}
              </div>
            </div>
          </div>
        </In>

        {/* Event Details below */}
        <In delay={16}>
          <div style={{ marginTop: 32 }}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 44, lineHeight: 1.25, color: INK }}>
              {marked(s, "event", s.event ?? "", { px: 44 })}
            </div>
            {s.sub && (
              <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 32, lineHeight: 1.3, color: MUTED, marginTop: 12 }}>
                {marked(s, "sub", s.sub, { px: 32 })}
              </div>
            )}
          </div>
        </In>
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 5. Glossary
export const Glossary: React.FC<P> = ({ s, inner = INNER }) => {
  const width = low(inner);

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", width, marginTop: 16 }}>
        {/* Context Chip */}
        {s.context && (
          <In delay={2}>
            <div style={{ marginBottom: 20 }}>
              <Chip size={36}>{s.context}</Chip>
            </div>
          </In>
        )}

        {/* Term Title */}
        <In delay={6}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: fitSize([s.term ?? ""], width, 84, 48), lineHeight: 1.15, color: INK }}>
            {marked(s, "term", s.term ?? "", { px: 72 })}
          </div>
          <div style={{ height: 4, width: 140, background: INK, margin: "24px 0 28px" }} />
        </In>

        {/* Definition Panel */}
        <In delay={14}>
          <div style={{
            background: PANEL, border: `2px solid ${LINE}`, borderRadius: RADIUS, padding: "32px 28px",
            fontFamily: FONT, fontWeight: 500, fontSize: 36, lineHeight: 1.45, color: INK
          }}>
            {marked(s, "definition", s.definition ?? "", { px: 36 })}
          </div>
        </In>
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 6. Checklist
export const Checklist: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const width = low(inner);
  const items = (s.items ?? []).filter((it): it is { text: string; state?: "done" | "pending" } =>
    typeof it === "object" && it !== null && typeof it.text === "string"
  );

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", gap: 24, width, marginTop: 12 }}>
        {items.map((it, i) => {
          const isDone = it.state === "done";
          const t = interpolate(frame - (6 + i * 6), [0, 14], [0, 1], { ...clamp, easing: easeOut });
          return (
            <In key={i} delay={4 + i * 6}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 20 }}>
                {/* Checkmark or Pending Icon */}
                <svg width={44} height={44} viewBox="0 0 44 44" style={{ flex: "none", marginTop: 4 }}>
                  <rect x={2} y={2} width={40} height={40} rx={10} fill={isDone ? INK : "none"} stroke={INK} strokeWidth={3} />
                  {isDone && (
                    <path d="M12 22 L19 29 L32 14" fill="none" stroke={CANVAS} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round"
                      pathLength={1} strokeDasharray={1} strokeDashoffset={1 - t} />
                  )}
                  {!isDone && (
                    <circle cx={22} cy={22} r={5} fill={MUTED} />
                  )}
                </svg>
                {/* Item Text */}
                <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 34, lineHeight: 1.35, color: INK, flex: 1 }}>
                  {marked(s, `items.${i}.text`, it.text, { px: 34 })}
                </div>
              </div>
            </In>
          );
        })}
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 7. Impact
export const Impact: React.FC<P> = ({ s, inner = INNER }) => {
  const width = low(inner);

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", width, marginTop: 16 }}>
        {/* Target Audience Pill */}
        {s.target && (
          <In delay={4}>
            <div style={{ marginBottom: 24 }}>
              <Chip size={40} solid>{s.target}</Chip>
            </div>
          </In>
        )}

        {/* Change statement */}
        <In delay={10}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: fitSize([s.change ?? ""], width, 68, 40), lineHeight: 1.25, color: INK }}>
            {marked(s, "change", s.change ?? "", { px: 56 })}
          </div>
        </In>

        {/* Effective timeline banner */}
        {s.when && (
          <In delay={18}>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 36, padding: "16px 24px", background: PANEL, border: `2px solid ${LINE}`, borderRadius: RADIUS, width: "fit-content" }}>
              <Dot size={22} pulse />
              <span style={{ fontFamily: FONT, fontWeight: 600, fontSize: 32, color: INK }}>
                {s.when}
              </span>
            </div>
          </In>
        )}
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 8. Route
export const Route: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const width = low(inner);
  const stops = s.stops ?? [];
  const lineProgress = interpolate(frame, [8, 32], [0, 1], { ...clamp, easing: easeOut });

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", width, marginTop: 16 }}>
        {/* Route stops track */}
        <div style={{ display: "flex", flexDirection: "column", gap: 32, position: "relative", paddingLeft: 48 }}>
          {/* Vertical path line */}
          <div style={{
            position: "absolute", left: 18, top: 20, bottom: 20, width: 6,
            background: LINE, borderRadius: 3, overflow: "hidden"
          }}>
            <div style={{ width: "100%", height: `${lineProgress * 100}%`, background: INK, borderRadius: 3 }} />
          </div>

          {stops.map((stop, i) => {
            const isLast = i === stops.length - 1;
            return (
              <In key={i} delay={4 + i * 8}>
                <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                  {/* Station node dot */}
                  <div style={{
                    position: "absolute", left: -48, top: "50%", transform: "translateY(-50%)",
                    width: isLast ? 24 : 18, height: isLast ? 24 : 18, borderRadius: "50%",
                    background: isLast ? RED : INK, border: `3px solid ${CANVAS}`
                  }} />
                  <div style={{ fontFamily: FONT, fontWeight: isLast ? 700 : 600, fontSize: isLast ? 40 : 36, color: INK }}>
                    {stop}
                  </div>
                </div>
              </In>
            );
          })}
        </div>

        {/* Detail or length tag */}
        {s.detail && (
          <In delay={28}>
            <div style={{ marginTop: 40 }}>
              <Chip size={38}>{s.detail}</Chip>
            </div>
          </In>
        )}

        {s.label && (
          <In delay={32}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 38, lineHeight: 1.25, color: INK, marginTop: 24, maxWidth: width }}>
              {marked(s, "label", s.label, { px: 38 })}
            </div>
          </In>
        )}
      </div>
    </Frame>
  );
};

// ---------------------------------------------------------------- 9. Budget
export const Budget: React.FC<P> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const width = low(inner);
  const items = (s.items ?? []).filter((it): it is { label: string; value: number; share?: number } =>
    typeof it === "object" && it !== null && typeof it.value === "number"
  );
  if (!items.length) return null;

  const total = s.total ?? items.reduce((acc, it) => acc + it.value, 0);
  const progress = interpolate(frame, [8, 30], [0, 1], { ...clamp, easing: easeOut });

  return (
    <Frame s={s}>
      <div style={{ display: "flex", flexDirection: "column", width, marginTop: 12 }}>
        {/* Total Summary */}
        <In delay={4}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 20 }}>
            <span style={{ fontFamily: FONT, fontWeight: 500, fontSize: 32, color: MUTED }}>სულ:</span>
            <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: 56, color: INK }}>
              {num(total)} {s.unit ?? ""}
            </span>
          </div>
        </In>

        {/* Proportional Segmented Bar */}
        <In delay={8}>
          <div style={{
            display: "flex", height: 36, width, borderRadius: 8, overflow: "hidden",
            background: LINE, margin: "12px 0 28px"
          }}>
            {items.map((it, i) => {
              const pct = it.share ?? (total > 0 ? (it.value / total) * 100 : 0);
              const opacities = [1.0, 0.7, 0.45, 0.25];
              return (
                <div key={i} style={{
                  height: "100%", width: `${pct * progress}%`,
                  background: INK, opacity: opacities[i % opacities.length],
                  borderRight: i < items.length - 1 ? `2px solid ${CANVAS}` : "none"
                }} />
              );
            })}
          </div>
        </In>

        {/* Category Items List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          {items.map((it, i) => {
            const pct = it.share ?? (total > 0 ? Math.round((it.value / total) * 100) : 0);
            return (
              <In key={i} delay={12 + i * 5}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 34, color: INK }}>
                    {marked(s, `items.${i}.label`, it.label, { px: 34 })}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                    <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: 32, color: INK }}>
                      {num(it.value)}
                    </span>
                    <span style={{ fontFamily: FONT, fontWeight: 600, fontSize: 26, color: MUTED, background: PANEL, border: `1px solid ${LINE}`, borderRadius: 6, padding: "4px 8px" }}>
                      {pct}%
                    </span>
                  </div>
                </div>
              </In>
            );
          })}
        </div>
      </div>
    </Frame>
  );
};
