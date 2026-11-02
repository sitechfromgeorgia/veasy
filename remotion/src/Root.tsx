import React from "react";
import { Composition } from "remotion";
import { DEFAULT_BRAND } from "./brand";
import { withBrandFonts } from "./fonts";
import { NewsShort } from "./NewsShort";
import type { ShortProps } from "./types";

// The brand pack's fonts load in fonts.tsx; nothing is laid out before they are in (text is sized by measuring it).
const Short = withBrandFonts(NewsShort);

const sample: ShortProps = {
  brand: DEFAULT_BRAND, variant: "editorial", transition: "line", id: 0, category: "მსოფლიო", date: { date: "1 ნოემბერი 2026", time: "22:38", weekday: "კვირა" },
  when: "1 ნოემბერი 2026", sources: ["პირველი არხი", "ინტერპრესნიუსი"], cta: "გამოიწერე", url: "tbilisi.today/stories/0",
  qrSvg: "", durationInFrames: 90, scenes: [{ type: "hook", from: 0, duration: 90, lines: ["სათაური"] }], words: [], captions: null,
  voice: null, voiceVolume: 1, music: null, musicVolume: 0.3, sourcesLine: "წყარო: პირველი არხი", previewNote: null,
};

export const Root: React.FC = () => (
  <Composition
    id="NewsShort"
    component={Short as unknown as React.FC<Record<string, unknown>>}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={90}
    defaultProps={sample as unknown as Record<string, unknown>}
    calculateMetadata={({ props }) => ({ durationInFrames: (props as unknown as ShortProps).durationInFrames })}
  />
);
