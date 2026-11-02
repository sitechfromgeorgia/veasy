import { loadFont } from "@remotion/fonts";
import React from "react";
import { Composition, continueRender, delayRender, staticFile } from "remotion";
import { DEFAULT_BRAND } from "./brand";
import { NewsShort } from "./NewsShort";
import { Slide, SLIDE_H, type SlideProps } from "./Slide";
import type { ShortProps } from "./types";

// The brand pack's one family, from the render's public dir (props.py copies its four weights there as brand-<w>).
const fonts = delayRender("fonts");
Promise.all(["400", "500", "600", "700"].map((w) =>
  loadFont({ family: "Brand", url: staticFile(`fonts/brand-${w}.woff2`), weight: w })))
  .then(() => continueRender(fonts)).catch((e) => { throw e; });

const sample: ShortProps = {
  brand: DEFAULT_BRAND, variant: "editorial", transition: "line", id: 0, category: "მსოფლიო", date: { date: "1 ნოემბერი 2026", time: "22:38", weekday: "კვირა" },
  when: "1 ნოემბერი 2026", sources: ["პირველი არხი", "ინტერპრესნიუსი"], cta: "გამოიწერე", url: "tbilisi.today/stories/0",
  qrSvg: "", durationInFrames: 90, scenes: [{ type: "hook", from: 0, duration: 90, lines: ["სათაური"] }], words: [], captions: null,
  voice: null, voiceVolume: 1, music: null, musicVolume: 0.3, sourcesLine: "წყარო: პირველი არხი", previewNote: null,
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="NewsShort"
      component={NewsShort as unknown as React.FC<Record<string, unknown>>}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={90}
      defaultProps={sample as unknown as Record<string, unknown>}
      calculateMetadata={({ props }) => ({ durationInFrames: (props as unknown as ShortProps).durationInFrames })}
    />
    {/* engine package's 4:5 carousel: one slide per frame (Slide.tsx) */}
    <Composition
      id="Slide"
      component={Slide as unknown as React.FC<Record<string, unknown>>}
      width={1080}
      height={SLIDE_H}
      fps={30}
      durationInFrames={1}
      defaultProps={{ ...sample, slides: sample.scenes } as unknown as Record<string, unknown>}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, (props as unknown as SlideProps).slides.length) })}
    />
  </>
);
