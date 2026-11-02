// The 4:5 carousel of `engine package` (tt_shorts/package.py): one static slide per frame, 1080x1350.
// A slide is a scene of the video drawn by its own component, frozen at its final frame, in the brand pack and the
// video's look and style. The scene's box is the cards look's content box (888 x 964), so a scene that fits in a
// video card fits a slide; package.py checks every PNG for anything drawn outside it (BOX_* are mirrored there).
import React, { useMemo } from "react";
import { AbsoluteFill, Sequence, useCurrentFrame } from "remotion";
import { applyBrand, FONT, INK, LINE, MUTED, PANEL, RADIUS, SIDE, W } from "./brand";
import { Background } from "./NewsShort";
import { SCENES } from "./scenes";
import type { Scene, ShortProps } from "./types";
import { Dot, Frame, Logo, measure, Theme, useTheme } from "./ui";

export const SLIDE_H = 1350;
export const BOX_W = 888;
export const BOX_H = 964;
export const BOX_LEFT = (W - BOX_W) / 2; // 96, as the cards look's content
export const BAND_TOP = 152; // the slide's scene band, between the header and the footer
export const BAND_BOTTOM = 1204;
export const BOX_TOP = BAND_TOP + (BAND_BOTTOM - BAND_TOP - BOX_H) / 2; // 196
export const FOOTER_TOP = 1228;

// summary: narration sentences, only when a story has too few scenes for five slides (package.py)
// fit: below 1 when the scene did not fit its box at full size: it is laid out in a box 1/fit as tall and scaled
// down to the slide's box, centred (package.py lowers it slide by slide until its pixel check passes)
export type SlideScene = Scene & { freeze?: number; fit?: number };
export type SlideProps = ShortProps & { slides: SlideScene[] };

/** Logo, date and category as in the video; the rule shows the slide's place, the dot at its head. */
const SlideHeader: React.FC<{ i: number; n: number }> = ({ i, n }) => {
  const { props } = useTheme();
  const x = (W - 2 * SIDE) * ((i + 1) / n);
  return (
    <>
      <div style={{ position: "absolute", left: SIDE, top: 40, height: 64, display: "flex", alignItems: "center" }}>
        <Logo place="header" size={64} />
      </div>
      <div style={{ position: "absolute", right: SIDE, top: 36, textAlign: "right", fontFamily: FONT }}>
        <div style={{ fontWeight: 700, fontSize: 32, lineHeight: 1.2, color: INK }}>{props.date.date}</div>
        <div style={{ fontWeight: 400, fontSize: 26, lineHeight: 1.4, color: MUTED }}>
          {props.date.weekday} · {props.date.time} · {props.category}
        </div>
      </div>
      <div style={{ position: "absolute", left: SIDE, right: SIDE, top: 124, height: 4, background: LINE }} />
      <div style={{ position: "absolute", left: SIDE, top: 124, height: 4, width: x, background: INK }} />
      <div style={{ position: "absolute", left: SIDE + x - 10, top: 116 }}><Dot size={20} /></div>
    </>
  );
};

/** The sources and the link are on every slide (the brand's rule), with the slide's number and the pack's line. */
const SlideFooter: React.FC<{ i: number; n: number }> = ({ i, n }) => {
  const { props } = useTheme();
  const right = (measure(props.brand.footer.text, 400) + measure(props.brand.footer.strong ?? "", 700)) * 0.26 + 32;
  const urlSize = Math.max(22, Math.min(32, Math.floor((100 * (W - 2 * SIDE - right)) / Math.max(1, measure(props.url, 700)))));
  return (
    <div style={{ position: "absolute", left: SIDE, right: SIDE, top: FOOTER_TOP, borderTop: `2px solid ${LINE}`, paddingTop: 14,
      fontFamily: FONT }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26, lineHeight: 1.4, color: MUTED }}>
        <span style={{ whiteSpace: "nowrap", overflow: "hidden" }}>{props.sourcesLine}</span>
        <span style={{ flex: "none", marginLeft: 24 }}>{i + 1} / {n}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontWeight: 700, fontSize: urlSize, lineHeight: 1.4, color: INK, whiteSpace: "nowrap" }}>{props.url}</span>
        <span style={{ fontSize: 26, lineHeight: 1.4, color: MUTED, whiteSpace: "nowrap" }}>
          {props.brand.footer.text}
          {props.brand.footer.strong && <span style={{ fontWeight: 700, color: INK }}>{props.brand.footer.strong}</span>}
        </span>
      </div>
    </div>
  );
};

/** A text slide: one or two narration sentences, when the story has too few scenes. */
const Summary: React.FC<{ s: SlideScene }> = ({ s }) => {
  const text = s.text ?? "";
  const size = text.length > 200 ? 52 : text.length > 120 ? 60 : 72;
  return (
    <Frame s={s}>
      <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: size, lineHeight: 1.3, color: INK }}>{text}</div>
    </Frame>
  );
};

const Body: React.FC<{ s: SlideScene; i: number }> = ({ s, i }) => {
  const { v } = useTheme();
  const Comp = s.type === "summary" ? Summary : SCENES[s.type];
  if (!Comp) return null;
  const end = s.type === "end";
  // the scene's final frame: every entrance has landed (the video's exit is SceneSlot's, not the scene's). A
  // Sequence that started `freeze` frames before this slide gives the scene that clock (Freeze would be clamped to
  // this composition's few frames).
  const at = s.freeze ?? Math.max(0, s.duration - 1);
  const content = (
    <Sequence from={i - at} durationInFrames={at + 1} layout="none">
      <Comp s={s} inner={end ? W - 2 * SIDE : BOX_W} />
    </Sequence>
  );
  const k = s.fit ?? 1;
  const scaled = (left: number, top: number, w: number, h: number) => (
    <div style={{ position: "absolute", left: left + (w * (1 - k)) / 2, top, width: w, height: h / k, transform: `scale(${k})`,
      transformOrigin: "left top" }}>{content}</div>
  );
  if (end) { // the end card has its own layout (logo, QR, link, button), as in the video: no card around it
    return scaled(SIDE, BAND_TOP, W - 2 * SIDE, BAND_BOTTOM - BAND_TOP);
  }
  const box = (left: number, top: number) => scaled(left, top, BOX_W, BOX_H);
  if (v !== "cards") return box(BOX_LEFT, BOX_TOP);
  const cardLeft = SIDE - 16;
  return (
    <div style={{ position: "absolute", left: cardLeft, right: cardLeft, top: BAND_TOP, height: BAND_BOTTOM - BAND_TOP, background: PANEL,
      border: `2px solid ${LINE}`, borderRadius: RADIUS }}>
      {box(BOX_LEFT - cardLeft - 2, BOX_TOP - BAND_TOP - 2)}
    </div>
  );
};

export const Slide: React.FC<SlideProps> = (props) => {
  applyBrand(props.brand); // before anything below reads a color
  const theme = useMemo(() => ({ v: props.variant, props }), [props]);
  const frame = useCurrentFrame();
  const n = props.slides.length;
  const i = Math.max(0, Math.min(n - 1, frame));
  return (
    <Theme.Provider value={theme}>
      <AbsoluteFill style={{ overflow: "hidden", fontFamily: FONT }}>
        <Background />
        <SlideHeader i={i} n={n} />
        {n > 0 && <Body s={props.slides[i]} i={i} />}
        <SlideFooter i={i} n={n} />
      </AbsoluteFill>
    </Theme.Provider>
  );
};
