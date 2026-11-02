import React, { useMemo } from "react";
import { AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import {
  alpha, applyBrand, CANVAS, CAPTION_BOTTOM, fill, FONT, GRID, H, INK, LINE, MUTED, PANEL, RADIUS, SCENE_BOTTOM, SCENE_TOP, SIDE,
  TICKER, W,
} from "./brand";
import { Captions } from "./Captions";
import { SCENES } from "./scenes";
import type { ShortProps } from "./types";
import { Chip, Dot, Logo, measure, Theme, useTheme } from "./ui";

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
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 36%, ${alpha(CANVAS, 0)} 45%, ${alpha(CANVAS, 0.9)} 100%)` }} />
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
      <div style={{ position: "absolute", left: SIDE, top: 80, height: 88, display: "flex", alignItems: "center" }}>
        <Logo place="header" size={88} />
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
          <span>{fill(props.brand.strings.card_meta, { n: props.sources.length, time: props.date.time })}</span>
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

/** The band the platforms cover with their own UI: no story text there, only motion that fills it. */
const Ticker: React.FC = () => {
  const { v, props } = useTheme();
  const frame = useCurrentFrame();
  const rows = [[props.category, props.date.date, ...props.sources, props.brand.label].join("  ·  ")];
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
        {/* the pack's line, quieter than the story's link (tbilisi.today: "SiTech-ის პროექტი · sitech.ge") */}
        <span style={{ fontSize: 28, lineHeight: 1.4, color: MUTED, whiteSpace: "nowrap" }}>
          {props.brand.footer.text}
          {props.brand.footer.strong && <span style={{ fontWeight: 700, color: INK }}>{props.brand.footer.strong}</span>}
        </span>
      </div>
    </div>
  );
};

export const NewsShort: React.FC<ShortProps> = (props) => {
  applyBrand(props.brand); // before anything below reads a color
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
        <Captions cap={props.captions} />
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
