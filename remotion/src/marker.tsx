// The marker (ROADMAP C2): a scene's "em" phrase is drawn over as the voice says it, with @remotion/rough-notation
// (MIT). Python decides everything (tt_shorts/marks.py, props scene.mark): the field, where the phrase starts in it,
// the frame, the kind and the strokes. Here the phrase is only wrapped and its stroke drawn by the frame.
// The wrapper is there in every frame (before the voice reaches the phrase too), so the layout never jumps; a scene
// without a mark renders exactly as before. Ink only (the accent is the dot's); on an inverted ink block the mark is
// the canvas color.
import React from "react";
import { Box, Bracket, Circle, Highlight, Underline } from "@remotion/rough-notation";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { alpha, CANVAS, INK, LINE_STRONG } from "./brand";
import type { Scene } from "./types";

type Opts = { px?: number; inverted?: boolean };

const markOf = (s: Scene, field: string) => (s.mark && s.mark.field === field ? s.mark : null);

/** Wraps `children` in the scene's mark when `field` is the marked one; otherwise returns them as they are. */
export const Mark: React.FC<{ s: Scene; field: string; children: React.ReactNode } & Opts> = (
  { s, field, px = 64, inverted = false, children }) => {
  const frame = useCurrentFrame();
  const m = markOf(s, field);
  if (!m) return <>{children}</>;
  const progress = interpolate(frame, [m.at, m.at + m.frames], [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad) });
  const ink = inverted ? CANVAS : INK;
  const stroke = Math.min(10, Math.max(4, Math.round(px * 0.075)));
  const pad = Math.min(24, Math.round(px * 0.16));
  const rough = { seed: m.seed, roughness: m.roughness, bowing: m.bowing, maxRandomnessOffset: m.roughness > 0 ? 2 : 0,
    disableMultiStroke: true };
  const iterations = m.roughness > 0 ? 2 : 1;
  switch (m.kind) {
    case "box":
      return <Box progress={progress} {...rough} color={ink} strokeWidth={stroke} iterations={iterations}
        padding={{ left: pad, right: pad, top: Math.round(pad / 2), bottom: Math.round(pad / 2) }}>{children}</Box>;
    case "circle":
      return <Circle progress={progress} {...rough} color={ink} strokeWidth={stroke} iterations={iterations} box="inside"
        padding={{ left: pad * 2, right: pad * 2, top: pad, bottom: pad }}>{children}</Circle>;
    case "highlight": // a quiet ink tint behind the words (the brand's strong line color), so the ink stays readable
      return <Highlight progress={progress} {...rough} color={inverted ? alpha(CANVAS, 0.22) : LINE_STRONG} iterations={1}
        padding={{ left: Math.round(pad / 2), right: Math.round(pad / 2), top: -Math.round(px * 0.14), bottom: -Math.round(px * 0.1) }}>
        {children}</Highlight>;
    case "bracket":
      return <Bracket progress={progress} {...rough} color={ink} strokeWidth={stroke} bracketLeft bracketRight
        padding={{ left: pad, right: pad, top: Math.round(pad / 3), bottom: Math.round(pad / 3) }}>{children}</Bracket>;
    default:
      return <Underline progress={progress} {...rough} color={ink} strokeWidth={stroke} iterations={iterations}
        padding={{ top: Math.round(px * 0.02) }}>{children}</Underline>;
  }
};

/** A text with the scene's marked phrase wrapped in its mark, when `field` is the marked field and the text still
 *  holds the phrase where Python found it; otherwise the text as it is. */
export const marked = (s: Scene, field: string, text: string | undefined, opts: Opts = {}): React.ReactNode => {
  const m = markOf(s, field);
  if (!m || text == null) return text;
  const end = m.start + m.phrase.length;
  if (text.slice(m.start, end) !== m.phrase) return text;
  return (
    <>
      {text.slice(0, m.start)}
      <Mark s={s} field={field} {...opts}>{m.phrase}</Mark>
      {text.slice(end)}
    </>
  );
};
