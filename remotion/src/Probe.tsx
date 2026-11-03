// The layout probe (tt_shorts/probe.py): with props.probe set, every rendered frame reports where its text really
// is, as one console line "VEASY_PROBE {json}" that remotion/probe.mjs collects through onBrowserLog. Python judges
// the boxes against the safe zone; nothing here decides what is wrong, it only measures.
//
// Regions are marked in the composition with data-probe="scene|card|captions|header|footer|ticker" (the ticker
// scrolls out of the frame by design and is skipped). data-probe-clip marks a box whose clipping is by design
// (the roll captions' neighbour lines). data-probe-decor marks a glyph that is ornament, faint by design (the quote
// scene's giant „): it is measured, but not judged for contrast.
//
// For the contrast rule each text also reports its color and its ground (groundAt): what the page paints under it,
// read from the DOM, in whichever theme the pack's colors are.
import React, { useLayoutEffect } from "react";
import { continueRender, delayRender, useCurrentFrame } from "remotion";
import { W } from "./brand";
import { useTheme } from "./ui";

type Box = [number, number, number, number]; // x, y, width, height in frame px

const r1 = (n: number) => Math.round(n * 10) / 10;

const opacityOf = (el: Element, root: Element) => {
  let o = 1;
  for (let a: Element | null = el; a && a !== root.parentElement; a = a.parentElement) {
    o *= parseFloat(getComputedStyle(a).opacity || "1");
  }
  return o;
};

type RGBA = [number, number, number, number];

/** "rgb(1, 2, 3)" / "rgba(1, 2, 3, 0.5)" (what getComputedStyle gives) -> [r, g, b, a], or null (none, a url...). */
const parseColor = (s: string | null | undefined): RGBA | null => {
  const m = /^rgba?\(([^)]+)\)$/.exec((s ?? "").trim());
  if (!m) return null;
  const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
  return p.length >= 3 && p.every((x) => !Number.isNaN(x)) ? [p[0], p[1], p[2], p.length > 3 ? p[3] : 1] : null;
};
const SHAPES = new Set(["rect", "circle", "ellipse", "path", "polygon"]);

/** The color an element paints behind what lies over it: its background (HTML) or its fill (an SVG shape), with
 *  its opacity; "image" for a picture (its colors are unknown: the contrast rule skips the text); null for none. */
const layerOf = (e: Element, root: Element): RGBA | "image" | null => {
  const tag = e.tagName.toLowerCase();
  if (tag === "img" || tag === "video" || tag === "canvas" || tag === "image") return "image";
  const cs = getComputedStyle(e);
  let c: RGBA | null = null;
  if (e instanceof SVGElement) {
    if (!SHAPES.has(tag)) return null;
    c = parseColor(cs.fill);
    if (c) c = [c[0], c[1], c[2], c[3] * parseFloat(cs.fillOpacity || "1")];
  } else {
    c = parseColor(cs.backgroundColor);
    if (!c && cs.backgroundImage.includes("url(")) return "image";
  }
  if (!c || c[3] <= 0) return null;
  return [c[0], c[1], c[2], c[3] * opacityOf(e, root)];
};

/** The text's ground: what is painted under the point (x, y) below the text's own element `el` (every element
 *  there, top to bottom, siblings included: document.elementsFromPoint; whatever covers the text, a wipe passing
 *  over it, is not its ground), composited over the canvas -> [r, g, b], or null under a picture. */
const groundAt = (x: number, y: number, el: Element, root: Element, canvas: RGBA): number[] | null => {
  const layers: RGBA[] = [];
  const stack = document.elementsFromPoint(x, y);
  const own = stack.findIndex((e) => e === el || e.contains(el));
  for (const e of own >= 0 ? stack.slice(own) : stack) {
    if (!root.contains(e)) continue;
    const c = layerOf(e, root);
    if (c === "image") return null;
    if (!c) continue;
    layers.push(c);
    if (c[3] >= 0.999) break;
  }
  let g = [canvas[0], canvas[1], canvas[2]];
  for (const c of layers.reverse()) g = g.map((v, i) => v * (1 - c[3]) + c[i] * c[3]);
  return g.map((v) => Math.round(v));
};

const collect = (frame: number, scenes: { from: number; duration: number; type: string }[], canvasHex: string) => {
  const root = document.querySelector("[data-probe-root]");
  if (!root) return null;
  const canvas = [...[1, 3, 5].map((i) => parseInt(canvasHex.slice(i, i + 2), 16) || 0), 1] as RGBA; // the theme's canvas, under everything
  const R = root.getBoundingClientRect();
  const k = R.width / W || 1;
  const box = (r: DOMRect): Box => [r1((r.left - R.left) / k), r1((r.top - R.top) / k), r1(r.width / k), r1(r.height / k)];
  const regions: Record<string, Box[]> = {};
  root.querySelectorAll("[data-probe]").forEach((el) => {
    const name = (el as HTMLElement).dataset.probe ?? "";
    (regions[name] ??= []).push(box(el.getBoundingClientRect()));
  });
  const texts: Record<string, unknown>[] = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.textContent ?? "";
    const el = n.parentElement;
    if (!el || !text.trim()) continue;
    const region = el.closest("[data-probe]") as HTMLElement | null;
    const name = region?.dataset.probe ?? "other";
    if (name === "ticker") continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") continue;
    const opacity = opacityOf(el, root);
    if (opacity < 0.05) continue;
    const range = document.createRange();
    range.selectNodeContents(n);
    const svg = el instanceof SVGElement;
    let scale = 1;
    if (svg) {
      const m = (el as unknown as SVGGraphicsElement).getScreenCTM?.();
      scale = m ? Math.hypot(m.a, m.b) : 1;
    } else if ((el as HTMLElement).offsetWidth > 0) {
      scale = el.getBoundingClientRect().width / (el as HTMLElement).offsetWidth;
    }
    // The text's extent: its line boxes (a glyph cell is about 1.2em; a line set tighter than that is a choice of
    // the layout, not an overflow), unioned over its lines.
    const lineH = svg ? NaN : parseFloat(cs.lineHeight) * scale;
    let l = Infinity, t = Infinity, r = -Infinity, b = -Infinity;
    let first: DOMRect | null = null;
    for (const c of Array.from(range.getClientRects())) {
      if (!c.width && !c.height) continue;
      first ??= c;
      const shrink = lineH > 0 ? Math.max(0, (c.height - lineH) / 2) : 0;
      l = Math.min(l, c.left); r = Math.max(r, c.right);
      t = Math.min(t, c.top + shrink); b = Math.max(b, c.bottom - shrink);
    }
    if (!(r > l) || !first) continue;
    // the contrast rule's two colors: the text's own (its alpha times its opacity) and its ground, everything painted
    // under the middle of its first line (probe.py judges them)
    const ink = parseColor(svg ? cs.fill : cs.color);
    const color = ink ? [ink[0], ink[1], ink[2], r1(ink[3] * (svg ? parseFloat(cs.fillOpacity || "1") : 1) * opacity * 100) / 100] : null;
    const ground = groundAt(first.left + first.width / 2, first.top + first.height / 2, el, root, canvas);
    // overflow: how far the text reaches past an ancestor whose content is larger than its box (scrollWidth >
    // clientWidth), across and down, up to its region; a drawing's text past its <svg>.
    const over = { x: 0, y: 0, xIn: "", yIn: "", clipped: false };
    const past = (L: number, T: number, R: number, B: number, what: string, clipped: boolean) => {
      const x = Math.max(L - l, r - R) / k, y = Math.max(T - t, b - B) / k;
      if (x > over.x) { over.x = r1(x); over.xIn = what; over.clipped ||= clipped; }
      if (y > over.y) { over.y = r1(y); over.yIn = what; over.clipped ||= clipped; }
    };
    const outer = svg ? (el as unknown as SVGElement).ownerSVGElement : null;
    if (outer) {
      let top: SVGSVGElement = outer;
      while (top.ownerSVGElement) top = top.ownerSVGElement;
      const q = top.getBoundingClientRect();
      past(q.left, q.top, q.right, q.bottom, "svg", getComputedStyle(top).overflow !== "visible");
    }
    for (let a: Element | null = svg ? outer?.parentElement ?? null : el; a && a !== root; a = a.parentElement) {
      const h = a as HTMLElement;
      const wide = h.clientWidth > 0 && h.scrollWidth - h.clientWidth > 2;
      const tall = h.clientHeight > 0 && h.scrollHeight - h.clientHeight > 2;
      if (wide || tall) {
        const q = h.getBoundingClientRect();
        const L = q.left + h.clientLeft * k, T = q.top + h.clientTop * k;
        past(wide ? L : -Infinity, tall ? T : -Infinity, wide ? L + h.clientWidth * k : Infinity,
          tall ? T + h.clientHeight * k : Infinity,
          `${h.tagName.toLowerCase()}${h.dataset.probe ? `[${h.dataset.probe}]` : ""}`,
          getComputedStyle(h).overflow !== "visible");
      }
      if (a === region) break;
    }
    texts.push({
      region: name, text, box: [r1((l - R.left) / k), r1((t - R.top) / k), r1((r - l) / k), r1((b - t) / k)],
      size: r1((parseFloat(cs.fontSize) * scale) / k), weight: cs.fontWeight, family: cs.fontFamily,
      opacity: r1(opacity), svg, overflow: over.x || over.y ? over : null, clipOk: !!el.closest("[data-probe-clip]"),
      decor: !!el.closest("[data-probe-decor]"),
      color, ground,
    });
  }
  const i = scenes.findIndex((s) => frame >= s.from && frame < s.from + s.duration);
  return { frame, scene: i, type: i >= 0 ? scenes[i].type : null, fonts: brandFaces(), regions, texts };
};

/** The brand font's faces in the page: {weight: status}. @remotion/fonts adds a face only once it has loaded. */
const brandFaces = () => {
  const out: Record<string, string> = {};
  document.fonts.forEach((f) => {
    if (f.family.replace(/["']/g, "") === "Brand") out[String(f.weight)] = f.status;
  });
  return out;
};
const WEIGHTS = ["400", "500", "600", "700"]; // tt_shorts/brand.py FONT_WEIGHTS: every pack has the four

/** Remotion mounts the composition in a hidden, unsized container and moves it into the canvas a moment later:
 *  the probe holds the frame (delayRender) until the root has its real size and the fonts are in, then measures. */
const placed = () => {
  const root = document.querySelector("[data-probe-root]");
  const r = root?.getBoundingClientRect();
  return !!r && r.width > 0 && r.top > -1000;
};
const fontsIn = () => {
  const f = brandFaces();
  return WEIGHTS.every((w) => f[w] === "loaded");
};

export const Probe: React.FC = () => {
  const frame = useCurrentFrame();
  const { props } = useTheme();
  useLayoutEffect(() => {
    // the fonts as this frame was laid out: text sized by measure() before a face loaded is sized wrong
    const atRender = brandFaces();
    const handle = delayRender("veasy probe: waiting for the layout");
    let tries = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const tick = () => {
      if ((!placed() || !fontsIn()) && tries++ < 300) {
        timer = setTimeout(tick, 10);
        return;
      }
      const data = collect(frame, props.scenes, props.brand.colors.canvas);
      if (data) console.log(`VEASY_PROBE ${JSON.stringify({ ...data, placed: placed(), fontsAtRender: atRender })}`);
      timer = null;
      continueRender(handle);
    };
    tick();
    return () => {
      if (timer !== null) {
        clearTimeout(timer);
        continueRender(handle);
      }
    };
  }, [frame, props.scenes]);
  return null;
};
