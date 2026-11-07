// The state scene (brushes/state.json): the film's object changes state, the two words beside it say from what to what.
// The object itself is drawn by the thread's layer (thread.tsx), in the room Frame keeps free; a film that lost its
// idea keeps the two words and the rail.
import React from "react";
import { useCurrentFrame } from "remotion";
import { FONT, INK, LINE, MUTED, RAIL_X, SIDE, W } from "../brand";
import { threadT } from "../thread";
import type { Scene } from "../types";
import { Dot, fitSize, Frame, In } from "../ui";

const INNER = W - 2 * SIDE;
const RAIL = 40; // the words' indent: the rail the dot moves on

export const State: React.FC<{ s: Scene; inner?: number }> = ({ s, inner = INNER }) => {
  const frame = useCurrentFrame();
  const t = s.thread ? threadT(s, frame) : Math.min(1, frame / Math.max(1, s.duration * 0.8));
  const width = Math.min(inner, RAIL_X - (W - inner) / 2) - RAIL;
  const size = fitSize([s.was ?? "", s.now ?? ""], width, 60, 40);
  const row = size * 1.2 + 16;
  const line = (text: string | undefined, on: boolean) => (
    <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: size, lineHeight: 1.2, whiteSpace: "nowrap", color: on ? INK : MUTED }}>{text}</div>
  );
  return (
    <Frame s={s}>
      <In delay={6}>
        <div style={{ position: "relative", paddingLeft: RAIL, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ position: "absolute", left: 8, top: size * 0.6, width: 4, height: row, background: LINE }} />
          <div style={{ position: "absolute", left: 0, top: size * 0.6 - 10 + t * row }}><Dot size={20} /></div>
          {line(s.was, t < 0.5)}
          {line(s.now, t >= 0.5)}
        </div>
      </In>
    </Frame>
  );
};
