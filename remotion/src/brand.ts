// tbilisi.today brand system v1.2 (https://tbilisi.today/brand, web/src/brand-v2.ts, docs/brand/BRAND.md):
// dark canvas, white ink and one red. Red belongs to the dot (it means "now"), an active state and an error mark,
// never to text. One family, FiraGO; hierarchy by size, weight and color only (no caps, letter-spacing, italics).
// Every distance is a multiple of 4; depth is a 1px line and a color step, never a shadow. Card radius 14,
// chips and buttons fully round. The three looks differ in layout and motion, never in palette.

export const CANVAS = "#05080F";
export const PANEL = "#0B0F17";
export const INK = "#F8FAFC";
export const MUTED = "#A7B0BD";
export const RED = "#EF4444";
export const LINE = "rgba(248,250,252,.12)";
export const LINE_STRONG = "rgba(248,250,252,.24)";
export const GRID = "rgba(248,250,252,.045)";
export const TICKER = "rgba(248,250,252,.06)";
export const MARK_BG = "#0B0B0E";

export const FONT = "FiraGO, sans-serif";
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
