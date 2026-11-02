import { loadFont } from "@remotion/fonts";
import React, { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

// The brand pack's one family, from the render's public dir (props.py copies its four weights there as brand-<w>).
const fonts = delayRender("fonts");
let loaded = false;
const ready = Promise.all(["400", "500", "600", "700"].map((w) =>
  loadFont({ family: "Brand", url: staticFile(`fonts/brand-${w}.woff2`), weight: w })))
  .then(() => {
    loaded = true;
    continueRender(fonts);
  });
ready.catch((e) => { throw e; });

/** The composition sizes text by measuring it in the brand font (ui.tsx measure, fitSize). Laid out before the font
 *  is in, a frame keeps sizes measured in a fallback font: the layout probe saw it in 3 stills of 24 (a render tab's
 *  first frame). So nothing is laid out until the four weights have loaded, and the frame waits for that layout. */
export const withBrandFonts = <T extends object>(Inner: React.FC<T>): React.FC<T> => {
  const Gated: React.FC<T> = (props) => {
    const [isIn, setIn] = useState(loaded);
    const [handle] = useState(() => (loaded ? null : delayRender("brand fonts before the layout")));
    useEffect(() => {
      if (handle === null) return;
      if (isIn) {
        continueRender(handle);
        return;
      }
      let live = true;
      ready.then(() => live && setIn(true));
      return () => {
        live = false;
      };
    }, [isIn, handle]);
    return isIn ? <Inner {...props} /> : null;
  };
  return Gated;
};
