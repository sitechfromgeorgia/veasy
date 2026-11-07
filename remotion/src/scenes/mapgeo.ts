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

const GAPS = [18, 40, 64];
const DIRS = Array.from({ length: 16 }, (_, i) => (i * Math.PI * 2) / 16);

/** The rectangle of a label of w x h sitting outside the circle (centre A, radius rpx) in direction u. */
export const outsideRect = (A: Pt, rpx: number, u: Pt, w: number, h: number, gap = 18): Rect => {
  const reach = rpx * 0.8 + gap + Math.abs(u[0]) * (w / 2) + Math.abs(u[1]) * (h / 2);
  const cx = A[0] + u[0] * reach, cy = A[1] + u[1] * reach;
  return { x: cx - w / 2, y: cy - h / 2, w, h };
};

/** The direction (angle in radians, and the gap from the area) in which a territory's label goes when it does not fit inside. Chosen once per
 *  scene on the camera's first and last view (so it does not wander during the zoom): the least land under the
 *  text, nothing outside the map's box, away from the pins and from the labels placed before it. */
export const labelAngle = (o: {
  views: View[]; boxW: number; boxH: number; at: number[]; r: number; w: number; h: number;
  land: Pt[][]; pins: number[][]; taken: Rect[][];
}): [number, number] => {
  let best: [number, number] = [0, 18], bestScore = Infinity;
  const cands = DIRS.flatMap((th, di) => GAPS.map((g, gi) => [th, g, di * 0.01 + gi * 3] as const));
  cands.forEach(([th, gap, base]) => {
    const u: Pt = [Math.cos(th), Math.sin(th)];
    let score = base;
    o.views.forEach((v, vi) => {
      const A = toScreen(v, o.boxW, o.boxH, o.at);
      if (A[0] < 0 || A[0] > o.boxW || A[1] < 0 || A[1] > o.boxH) return; // not on screen in this view
      const R = outsideRect(A, o.r * v.k, u, o.w, o.h, gap);
      if (R.x < 4 || R.y < 4 || R.x + R.w > o.boxW - 4 || R.y + R.h > o.boxH - 4) score += 1000;
      let onLand = 0;
      for (let i = 0; i <= 6; i++) {
        for (let j = 0; j <= 2; j++) {
          const sx = R.x + (R.w * i) / 6, sy = R.y + (R.h * j) / 2;
          // screen -> map units, to test against the outline
          if (insideAny(o.land, (sx - o.boxW / 2) / v.k + v.cx, (sy - o.boxH / 2) / v.k + v.cy)) onLand++;
        }
      }
      score += onLand * 2;
      for (const p of o.pins) {
        const P = toScreen(v, o.boxW, o.boxH, p);
        if (P[0] > R.x - 30 && P[0] < R.x + R.w + 30 && P[1] > R.y - 70 && P[1] < R.y + R.h + 30) score += 500;
      }
      for (const t of o.taken[vi] ?? []) {
        if (R.x < t.x + t.w + 12 && R.x + R.w + 12 > t.x && R.y < t.y + t.h + 12 && R.y + R.h + 12 > t.y) score += 800;
      }
    });
    if (score < bestScore) { bestScore = score; best = [th, gap]; }
  });
  return best;
};
