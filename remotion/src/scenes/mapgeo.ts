// Geometry helpers of the where scene's map (map.tsx): the zoom's fades, a polygon test on the outline and where
// the label of an occupied territory goes. Pure functions of the props and the camera, so every frame is the same
// whichever order it renders in.

export type Pt = [number, number];
export type Rect = { x: number; y: number; w: number; h: number };
export type View = { k: number; cx: number; cy: number };

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

/** 0..1 as the camera's scale k (px per map unit) crosses lo..hi, eased, evenly in the log (the zoom is geometric). */
export const zoomIn = (k: number, lo: number, hi: number) => {
  const x = clamp01((Math.log(k) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)));
  return x * x * (3 - 2 * x);
};

/** The polygons of an SVG path of `M`/`l`/`L`/`h`/`v`/`z` commands (the map files' own dialect), flattened. */
export const polygons = (d: string): Pt[][] => {
  const out: Pt[][] = [];
  let cur: Pt[] = [];
  let x = 0, y = 0, sx = 0, sy = 0;
  const re = /([MmLlHhVvZz])|(-?\d*\.?\d+(?:e[-+]?\d+)?)/g;
  let cmd = "";
  let args: number[] = [];
  const flush = () => {
    const n = { M: 2, m: 2, L: 2, l: 2, H: 1, h: 1, V: 1, v: 1, Z: 0, z: 0 }[cmd as "M"] ?? 0;
    if (!n) return;
    while (args.length >= n) {
      const a = args.splice(0, n);
      if (cmd === "M" || cmd === "m") {
        if (cur.length > 2) out.push(cur);
        x = cmd === "M" ? a[0] : x + a[0];
        y = cmd === "M" ? a[1] : y + a[1];
        sx = x; sy = y;
        cur = [[x, y]];
        cmd = cmd === "M" ? "L" : "l"; // more pairs after a moveto are linetos
      } else if (cmd === "L") { x = a[0]; y = a[1]; cur.push([x, y]); }
      else if (cmd === "l") { x += a[0]; y += a[1]; cur.push([x, y]); }
      else if (cmd === "H") { x = a[0]; cur.push([x, y]); }
      else if (cmd === "h") { x += a[0]; cur.push([x, y]); }
      else if (cmd === "V") { y = a[0]; cur.push([x, y]); }
      else if (cmd === "v") { y += a[0]; cur.push([x, y]); }
    }
  };
  for (let m = re.exec(d); m; m = re.exec(d)) {
    if (m[1]) {
      flush();
      cmd = m[1];
      args = [];
      if (cmd === "z" || cmd === "Z") { x = sx; y = sy; if (cur.length > 2) out.push(cur); cur = []; }
    } else args.push(parseFloat(m[2]));
  }
  flush();
  if (cur.length > 2) out.push(cur);
  return out;
};

/** Even-odd point test over every ring (the outline's islands and holes). */
export const insideAny = (rings: Pt[][], px: number, py: number) => {
  let hit = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) hit = !hit;
    }
  }
  return hit;
};

export const lerpView = (a: View, b: View, t: number): View => ({
  k: a.k * Math.pow(b.k / a.k, t), cx: a.cx + (b.cx - a.cx) * t, cy: a.cy + (b.cy - a.cy) * t,
});

export const toScreen = (v: View, boxW: number, boxH: number, p: number[]): Pt =>
  [boxW / 2 + (p[0] - v.cx) * v.k, boxH / 2 + (p[1] - v.cy) * v.k];

/** A label's words in two lines that keep the wider one narrowest (a long first word stands alone), not a split by
 *  word count. width: a line's width at any one size. */
export const balancedLines = (words: string[], width: (line: string) => number): string[] => {
  if (words.length < 2) return words;
  let best = [words.join(" ")], widest = Infinity;
  for (let i = 1; i < words.length; i++) {
    const lines = [words.slice(0, i).join(" "), words.slice(i).join(" ")];
    const w = Math.max(...lines.map(width));
    if (w < widest) { widest = w; best = lines; }
  }
  return best;
};

/** Where a territory's label sits in one camera view: x, y in map units, angle in degrees, its size in px, and
 *  whether it fits. */
export type Seat = { x: number; y: number; angle: number; size: number; fits: boolean };

const ANGLES = [0, 5, -5, 10, -10, 15, -15]; // straight first; a tilt along the area's shape never past 15°
const PAD = 6; // px around the words that stay on the area too
const GRID = 14; // candidate centres a side over the territory's box

/** Points on a grid over a territory's box that lie inside it (map units): where its label may stand, and, on screen,
 *  how much of it the camera shows and where that part's middle is. */
export const gridInside = (rings: Pt[][], bbox: number[], n = GRID): Pt[] => {
  const step = Math.max(bbox[2] - bbox[0], bbox[3] - bbox[1]) / n;
  const out: Pt[] = [];
  for (let x = bbox[0] + step / 2; x < bbox[2]; x += step) {
    for (let y = bbox[1] + step / 2; y < bbox[3]; y += step) if (insideAny(rings, x, y)) out.push([x, y]);
  }
  return out;
};

/** The owner (2026-11-10): the label is written on the territory, never beside it. Its rectangle (w x h px at each
 *  size, plus PAD) wholly inside the territory and the map's box, clear of the pins: the pole first, straight first,
 *  the biggest size first. Where nothing fits (the Tskhinvali region at the country view holds two words only at
 *  16 px), it is straight at the smallest size where the most of it lands on the part the camera shows: on the
 *  area, running a little past its edges. Pure: the same props and view give the same seat. */
export const seatInside = (o: {
  rings: Pt[][]; view: View; boxW: number; boxH: number; at: number[]; bbox: number[]; sizes: number[];
  dims: (size: number) => [number, number]; pins: number[][];
}): Seat => {
  const v = o.view;
  const near = (p: number[]) => Math.hypot(p[0] - o.at[0], p[1] - o.at[1]);
  const cands: Pt[] = [[o.at[0], o.at[1]], ...gridInside(o.rings, o.bbox)];
  cands.sort((p, q) => near(p) - near(q));
  const onBox = (S: Pt) => S[0] >= 4 && S[1] >= 4 && S[0] <= o.boxW - 4 && S[1] <= o.boxH - 4;
  const pins = o.pins.map((p) => toScreen(v, o.boxW, o.boxH, p));
  for (const size of o.sizes) {
    const [w, h] = o.dims(size);
    const hw = (w / 2 + PAD) / v.k, hh = (h / 2 + PAD) / v.k; // half the rectangle, in map units
    const probe: Pt[] = [[0, 0]];
    for (let i = 0; i <= 8; i++) for (const fy of [-1, 0, 1]) probe.push([(-1 + i / 4) * hw, fy * hh]);
    for (const fy of [-0.5, 0.5]) for (const fx of [-1, 1]) probe.push([fx * hw, fy * hh]);
    for (const angle of ANGLES) {
      const a = (angle * Math.PI) / 180, ca = Math.cos(a), sa = Math.sin(a);
      for (const c of cands) {
        const C = toScreen(v, o.boxW, o.boxH, c);
        // a pin's head stands above its tip: keep the words clear of both
        if (pins.some((P) => Math.abs(P[0] - C[0]) < w / 2 + 30 && P[1] > C[1] - h / 2 - 30 && P[1] < C[1] + h / 2 + 90)) continue;
        const ok = probe.every(([px, py]) => {
          const X = c[0] + px * ca - py * sa, Y = c[1] + px * sa + py * ca;
          return insideAny(o.rings, X, Y) && onBox(toScreen(v, o.boxW, o.boxH, [X, Y]));
        });
        if (ok) return { x: c[0], y: c[1], angle, size, fits: true };
      }
    }
  }
  // nothing fits: straight, the smallest size, where the most of the words land on the territory the camera shows
  // (ties go to the one nearer the pole: the candidates are sorted so)
  const size = o.sizes[o.sizes.length - 1];
  const [w, h] = o.dims(size);
  const hw = w / 2 / v.k, hh = h / 2 / v.k;
  const probe: Pt[] = [];
  for (let i = 0; i <= 8; i++) for (const fy of [-1, -0.5, 0, 0.5, 1]) probe.push([(-1 + i / 4) * hw, fy * hh]);
  let best: Pt = [o.at[0], o.at[1]], most = -1;
  for (const c of cands) {
    if (!onBox(toScreen(v, o.boxW, o.boxH, c))) continue;
    const on = probe.filter(([px, py]) => insideAny(o.rings, c[0] + px, c[1] + py)).length;
    if (on > most) { most = on; best = c; }
  }
  return { x: best[0], y: best[1], angle: 0, size, fits: false };
};
