import { loadFont } from "@remotion/fonts";
import React from "react";
import { Composition, continueRender, delayRender, staticFile } from "remotion";
import { NewsShort } from "./NewsShort";
import type { ShortProps } from "./types";

// One family, FiraGO (brand v1.2), from the render's public dir (props.py copies video/assets/fonts there).
const fonts = delayRender("fonts");
Promise.all([
  ...[["regular", "400"], ["medium", "500"], ["semibold", "600"], ["bold", "700"]].map(([n, w]) =>
    loadFont({ family: "FiraGO", url: staticFile(`fonts/firago-${n}.woff2`), weight: w })),
]).then(() => continueRender(fonts)).catch((e) => { throw e; });

const sample: ShortProps = {
  variant: "editorial", id: 0, category: "მსოფლიო", date: { date: "1 ნოემბერი 2026", time: "22:38", weekday: "კვირა" },
  when: "1 ნოემბერი 2026", sources: ["პირველი არხი", "ინტერპრესნიუსი"], cta: "გამოიწერე", url: "tbilisi.today/stories/0",
  qrSvg: "", durationInFrames: 90, scenes: [{ type: "hook", from: 0, duration: 90, lines: ["სათაური"] }], words: [],
  voice: null, voiceVolume: 1, music: null, musicVolume: 0.3, sourcesLine: "წყარო: პირველი არხი", previewNote: null,
};

export const Root: React.FC = () => (
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
);
