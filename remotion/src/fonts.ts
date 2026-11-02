import { loadFont } from "@remotion/fonts";
import { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

// The brand pack's one family, from the render's public dir (props.py copies its four weights there as brand-<w>).
// Nothing may be measured (ui.tsx measure, fitSize) before these are in: a canvas that first measured with the
// fallback font kept those widths for several frames, so a render tab's first frames set the hook ~5% too large
// and it jumped a moment later (visible once the opening is on screen at frame 0, tt_shorts/swipe.py).
let loaded = false;
export const fontsLoaded = Promise.all(["400", "500", "600", "700"].map((w) =>
  loadFont({ family: "Brand", url: staticFile(`fonts/brand-${w}.woff2`), weight: w }))).then(() => { loaded = true; });

/** False until the brand fonts are loaded; the frame waits until the composition has drawn with them. */
export const useFontsLoaded = () => {
  const [ready, setReady] = useState(loaded);
  const [handle] = useState(() => (loaded ? null : delayRender("brand fonts, then the first measure")));
  useEffect(() => {
    let live = true;
    fontsLoaded.then(() => { if (live) setReady(true); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    if (ready && handle !== null) continueRender(handle);
  }, [ready, handle]);
  return ready;
};
