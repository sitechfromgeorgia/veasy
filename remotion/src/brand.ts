// The brand pack's palette and words (brands/<name>/brand.json, tt_shorts/brand.py; props.brand). The defaults are
// tbilisi.today's brand system v1.2 (https://tbilisi.today/brand): dark canvas, white ink and one accent (red).
// The accent belongs to the dot (it means "now"), an active state and the end card's button, never to text. One
// font family per pack; hierarchy by size, weight and color only. Every distance is a multiple of 4; depth is a
// 1px line and a color step, never a shadow. Card radius 14, chips and buttons fully round. The three looks
// differ in layout and motion, never in palette.
//
// The colors are live bindings: NewsShort calls applyBrand(props.brand) before anything draws, and every module
// that imports CANVAS, INK... reads the pack's value from then on. Read them inside components, never at module
// level. props.brand carries one of the pack's themes (brand.json "themes": dark, light...; tt_shorts/brand.py),
// so no component may assume a dark ground: a color is always one of these tokens, never a literal.
import type { BrandProps } from "./types";

export let CANVAS = "#05080F";
export let PANEL = "#0B0F17";
export let INK = "#F8FAFC";
export let MUTED = "#A7B0BD";
export let RED = "#EF4444"; // the accent (tbilisi.today's red, SiTech's orange)
export let ON_ACCENT = "#FFFFFF";
export let LINE = "rgba(248,250,252,.12)";
export let LINE_STRONG = "rgba(248,250,252,.24)";
export let GRID = "rgba(248,250,252,.045)";
export let TICKER = "rgba(248,250,252,.06)";
export let WAITING = "rgba(248,250,252,.42)"; // a caption word not yet spoken: the ink, dimmed
export let MARK_BG = "#0B0B0E";
export let MARK_INK = "#FFFFFF"; // the t of the mark
export let QR_LIGHT = "#FFFFFF"; // the QR's ground (its quiet zone): white on a dark theme, the canvas on a light one

// props.py copies the pack's four weights to public/fonts/brand-<weight>.woff2; Root.tsx loads them as "Brand".
export const FONT = "Brand, sans-serif";

// Studio's sample (Root.tsx); a render always gets the pack from props.py.
export const DEFAULT_BRAND: BrandProps = {
  "name": "tbilisi-today",
  "label": "tbilisi.today",
  "colors": {
    "canvas": "#05080F",
    "panel": "#0B0F17",
    "ink": "#F8FAFC",
    "muted": "#A7B0BD",
    "accent": "#EF4444",
    "line": "rgba(248,250,252,.12)",
    "lineStrong": "rgba(248,250,252,.24)",
    "grid": "rgba(248,250,252,.045)",
    "ticker": "rgba(248,250,252,.06)",
    "waiting": "rgba(248,250,252,.42)",
    "markBg": "#0B0B0E",
    "onAccent": "#FFFFFF",
    "markInk": "#FFFFFF",
    "qrDark": "#05080F",
    "qrLight": "#FFFFFF"
  },
  "wordmark": {
    "text": "tbilisi.today",
    "accent": "."
  },
  "logo": "tmark",
  "footer": {
    "text": "SiTech-ის პროექტი · ",
    "strong": "sitech.ge"
  },
  "strings": {
    "outlets": "{n} წყარო",
    "source_one": "წყარო",
    "source_many": "წყაროები",
    "covered_by": [
      "მედია",
      "აშუქებს"
    ],
    "today": "დღეს",
    "preview_edge": "დროებითი ხმა · პრევიუ",
    "preview_silent": "ხმის გარეშე · პრევიუ",
    "card_meta": "{n} წყარო · {time}",
    "category_default": "ამბები",
    "at_least": "მინიმუმ {n}"
  }
};

export const applyBrand = (b: BrandProps) => {
  const c = b.colors;
  CANVAS = c.canvas; PANEL = c.panel; INK = c.ink; MUTED = c.muted; RED = c.accent; ON_ACCENT = c.onAccent ?? "#FFFFFF";
  LINE = c.line; LINE_STRONG = c.lineStrong; GRID = c.grid; TICKER = c.ticker; WAITING = c.waiting; MARK_BG = c.markBg;
  MARK_INK = c.markInk ?? "#FFFFFF"; QR_LIGHT = c.qrLight ?? "#FFFFFF";
};

/** "#05080F" at alpha .8 -> "rgba(5,8,15,0.8)" (a color step of the canvas, e.g. behind the captions). */
export const alpha = (hex: string, a: number) => {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (!m) return hex;
  return `rgba(${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)},${a})`;
};

/** A pack's string with {n}, {time}... filled in. */
export const fill = (template: string, vars: Record<string, string | number>) =>
  template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));

export const RADIUS = 14;

// Layout bands (px) of the 1080x1920 frame. Platforms draw their caption, channel row and buttons over the lower
// part: story text stays above SCENE_BOTTOM, captions end at CAPTION_BOTTOM, the band below carries motion only.
export const W = 1080;
export const H = 1920;
export const SIDE = 64;
export const SCENE_TOP = 248;
export const SCENE_BOTTOM = 1380;
export const CAPTION_BOTTOM = 1552; // lower third, owner's request (2026-11-01); still above the platforms' caption row
export const RAIL_X = 940;

// The mark: 512 grid, radius 112, the t and the dot (diameter 68). Never framed, recolored or distorted.
export const T_PATH =
  "M1881 3408 c-30 -79 -59 -149 -64 -156 -6 -7 -57 -41 -114 -75 l-103 -62 0 -82 0 -83 94 0 95 0 3 -427 c3 -417 4 -430 26 -492 46 -128 115 -195 237 -234 58 -18 93 -22 205 -21 134 0 210 13 298 49 l32 14 0 140 c0 78 -3 141 -6 141 -3 0 -34 -7 -68 -16 -33 -9 -95 -17 -136 -18 -86 -1 -125 15 -162 66 -23 33 -23 33 -26 416 l-3 382 191 0 190 0 0 145 0 145 -190 0 -190 0 0 155 0 155 -128 0 -127 0 -54 -156z";
