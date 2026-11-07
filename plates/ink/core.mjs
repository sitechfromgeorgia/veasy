// What every material stands on: seeded noise, the sheet's tooth, the drawing's plan (regions, tone, distance fields)
// and a brush that deposits pigment into a layer, with the moment each pixel is touched. All of it runs once, in setup,
// on typed arrays: no browser rasteriser, so the same spec gives the same numbers on any machine.
import { seeded } from "/lib/seeded.mjs";

export const clamp = (v, lo = 0, hi = 1) => (v < lo ? lo : v > hi ? hi : v);
export const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };

export class Noise { // value noise on a 256 lattice of seeded numbers; the lattice is the only randomness
  constructor(seed) {
    const r = seeded(seed);
    this.t = new Float32Array(65536);
    for (let i = 0; i < 65536; i++) this.t[i] = r();
  }
  at(x, y) {
    const fx = Math.floor(x), fy = Math.floor(y), dx = x - fx, dy = y - fy;
    const x0 = fx & 255, x1 = (fx + 1) & 255, y0 = (fy & 255) << 8, y1 = ((fy + 1) & 255) << 8;
    const t = this.t, u = dx * dx * (3 - 2 * dx), v = dy * dy * (3 - 2 * dy);
    const a = t[y0 | x0], b = t[y0 | x1], c = t[y1 | x0], d = t[y1 | x1];
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  fbm(x, y, octaves) {
    let sum = 0, amp = 0.5, total = 0;
    for (let i = 0; i < octaves; i++) {
      sum += amp * this.at(x, y);
      total += amp;
      amp *= 0.5; x = x * 2.03 + 11.7; y = y * 2.03 + 5.3;
    }
    return sum / total;
  }
}

// Felzenszwalb's distance transform: every pixel's distance to the nearest set pixel of `mask`
export function distance(mask, W, H) {
  const INF = 1e12, f = new Float32Array(W * H);
  for (let i = 0; i < f.length; i++) f[i] = mask[i] ? 0 : INF;
  const size = Math.max(W, H) + 1, v = new Int32Array(size), z = new Float64Array(size + 1), d = new Float64Array(size), q = new Float64Array(size);
  const line = (n) => {
    let k = 0; v[0] = 0; z[0] = -INF; z[1] = INF;
    for (let i = 1; i < n; i++) {
      if (q[i] >= INF) continue;
      if (q[v[0]] >= INF) { v[0] = i; continue; }
      let s;
      for (;;) {
        s = ((q[i] + i * i) - (q[v[k]] + v[k] * v[k])) / (2 * i - 2 * v[k]);
        if (s > z[k]) break;
        if (k === 0) { z[0] = -INF; k = -1; break; }
        k--;
      }
      k++; v[k] = i; z[k] = k === 0 ? -INF : s; z[k + 1] = INF;
    }
    k = 0;
    for (let i = 0; i < n; i++) {
      while (z[k + 1] < i) k++;
      d[i] = (i - v[k]) * (i - v[k]) + q[v[k]];
    }
  };
  for (let x = 0; x < W; x++) {
    for (let y = 0; y < H; y++) q[y] = f[x + y * W];
    line(H);
    for (let y = 0; y < H; y++) f[x + y * W] = d[y];
  }
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) q[x] = f[x + y * W];
    line(W);
    for (let x = 0; x < W; x++) f[x + y * W] = Math.sqrt(d[x]);
  }
  return f;
}

// A box blur, three passes: near enough to a gaussian for a halo of dust
export function blur(src, W, H, radius) {
  let a = Float32Array.from(src), b = new Float32Array(W * H);
  const r = Math.max(1, Math.round(radius)), k = 1 / (2 * r + 1);
  for (let pass = 0; pass < 3; pass++) {
    for (let y = 0; y < H; y++) {
      let sum = 0;
      for (let x = -r; x <= r; x++) sum += a[clamp(x, 0, W - 1) + y * W];
      for (let x = 0; x < W; x++) {
        b[x + y * W] = sum * k;
        sum += a[Math.min(x + r + 1, W - 1) + y * W] - a[Math.max(x - r, 0) + y * W];
      }
    }
    for (let x = 0; x < W; x++) {
      let sum = 0;
      for (let y = -r; y <= r; y++) sum += b[x + clamp(y, 0, H - 1) * W];
      for (let y = 0; y < H; y++) {
        a[x + y * W] = sum * k;
        sum += b[x + Math.min(y + r + 1, H - 1) * W] - b[x + Math.max(y - r, 0) * W];
      }
    }
  }
  return a;
}

function fillRings(rings, W, H, paint) { // even-odd scanline over an element's rings
  let top = H, bottom = -1;
  for (const r of rings) for (let i = 1; i < r.length; i += 2) { top = Math.min(top, r[i]); bottom = Math.max(bottom, r[i]); }
  top = Math.max(0, Math.floor(top)); bottom = Math.min(H - 1, Math.ceil(bottom));
  const xs = [];
  for (let y = top; y <= bottom; y++) {
    xs.length = 0;
    const sy = y + 0.5;
    for (const r of rings) {
      for (let i = 0, n = r.length; i < n; i += 2) {
        const j = (i + 2) % n, ay = r[i + 1], by = r[j + 1];
        if ((ay <= sy) !== (by <= sy)) xs.push(r[i] + (sy - ay) / (by - ay) * (r[j] - r[i]));
      }
    }
    xs.sort((a, b) => a - b);
    for (let k = 0; k + 1 < xs.length; k += 2) {
      const from = Math.max(0, Math.ceil(xs[k] - 0.5)), to = Math.min(W - 1, Math.floor(xs[k + 1] - 0.5));
      for (let x = from; x <= to; x++) paint(x + y * W);
    }
  }
}

export function length(pts) {
  let sum = 0;
  for (let i = 2; i < pts.length; i += 2) sum += Math.hypot(pts[i] - pts[i - 2], pts[i + 1] - pts[i - 1]);
  return sum;
}

// A polyline as a walk of even steps, with normals: the shape every brush reads
export function walk(pts, step = 1) {
  const L = length(pts), n = Math.max(2, Math.ceil(L / step) + 1);
  const x = new Float32Array(n), y = new Float32Array(n), nx = new Float32Array(n), ny = new Float32Array(n);
  let seg = 0, done = 0, segLen = Math.hypot(pts[2] - pts[0], pts[3] - pts[1]);
  for (let i = 0; i < n; i++) {
    const want = (L * i) / (n - 1);
    while (seg + 4 < pts.length && done + segLen < want) {
      done += segLen; seg += 2;
      segLen = Math.hypot(pts[seg + 2] - pts[seg], pts[seg + 3] - pts[seg + 1]);
    }
    const f = segLen ? clamp((want - done) / segLen) : 0;
    x[i] = pts[seg] + (pts[seg + 2] - pts[seg]) * f;
    y[i] = pts[seg + 1] + (pts[seg + 3] - pts[seg + 1]) * f;
  }
  for (let i = 0; i < n; i++) {
    const a = Math.max(0, i - 3), b = Math.min(n - 1, i + 3);
    const dx = x[b] - x[a], dy = y[b] - y[a], d = Math.hypot(dx, dy) || 1;
    nx[i] = -dy / d; ny[i] = dx / d;
  }
  return { x, y, nx, ny, n, L };
}

// The hand: a slow bow along the stroke (kept in every drawing of a boil) and a small redraw that is the boil itself
export function shake(p, noise, key, hand, handStep, boil, boilStep, variant) {
  for (let i = 0; i < p.n; i++) {
    const s = (i / (p.n - 1)) * p.L;
    let off = (noise.at(s / handStep + key * 17.3, key * 3.1) - 0.5) * 2 * hand;
    off += (noise.at(s / boilStep + key * 7.9, 40 + variant * 13.7 + key) - 0.5) * 2 * boil;
    p.x[i] += p.nx[i] * off; p.y[i] += p.ny[i] * off;
  }
  return p;
}

// One mark's pigment before it meets the paper. Inside a mark pigment is a union (a brush doesn't add to itself),
// between marks it builds up (flush).
export class Deposit {
  constructor(W, H) {
    this.W = W; this.H = H;
    this.c = new Float32Array(W * H);
    this.a = new Float32Array(W * H).fill(Infinity);
    this.list = new Int32Array(W * H);
    this.n = 0;
  }
  dab(x, y, r, v, a, soft = 1) { // soft: the width of the dab's falling edge, 1 px for a crisp one
    const { W, H, c, a: A, list } = this;
    const x0 = Math.max(0, Math.floor(x - r - 0.5)), x1 = Math.min(W - 1, Math.ceil(x + r + 0.5));
    const y0 = Math.max(0, Math.floor(y - r - 0.5)), y1 = Math.min(H - 1, Math.ceil(y + r + 0.5));
    for (let py = y0; py <= y1; py++) {
      const dy = py + 0.5 - y;
      for (let px = x0; px <= x1; px++) {
        const dx = px + 0.5 - x, edge = r + 0.5 - Math.sqrt(dx * dx + dy * dy);
        if (edge <= 0) continue;
        const p = px + py * W, val = v * (edge < soft ? edge / soft : 1);
        if (A[p] === Infinity) { list[this.n++] = p; A[p] = a; }
        else if (a < A[p]) A[p] = a;
        if (val > c[p]) c[p] = val;
      }
    }
  }
  flush(layer, ground) { // ground(v, p): how this pigment takes on this paper
    const { c, a, list } = this, C = layer.c, A = layer.a;
    for (let i = 0; i < this.n; i++) {
      const p = list[i], v = ground ? ground(c[p], p) : c[p];
      if (v > 0.002) {
        C[p] += v * (1 - C[p]);
        if (a[p] < A[p]) A[p] = a[p];
      }
      c[p] = 0; a[p] = Infinity;
    }
    this.n = 0;
  }
}

// A brush: `n` bristles across the width, each with its own load, wandering a little along the stroke.
// st: {w(u) full width, flow(u), n, r?, dry, skip, wander, body (the mass under the bristles), edge (how soft that mass
// ends)}; time: {t0, dur}.
export function brush(dep, p, st, time, key, noise) {
  const { n = 1, dry = 0, skip = 0, wander = 0, body = 0, edge = 0.8 } = st;
  const flowAt = st.flow || (() => 1);
  const nv = new Float32Array(n), thirst = new Float32Array(n), id = new Float32Array(n);
  for (let b = 0; b < n; b++) {
    const k = noise.at(key * 3.77 + b * 0.73, 91.3);
    nv[b] = n === 1 ? 0 : ((b + 0.5) / n) * 2 - 1 + (k - 0.5) * (2 / n);
    thirst[b] = 0.4 + 1.2 * noise.at(key * 1.31 + b * 1.9, 17.1);
    id[b] = key * 5.3 + b * 2.17;
  }
  for (let i = 0; i < p.n; i++) {
    const u = i / (p.n - 1), s = u * p.L, w = st.w(u) / 2, f = flowAt(u);
    const r = st.r ?? (n === 1 ? Math.max(0.5, w) : Math.max(0.7, (2 * w) / n * 0.8));
    const a = time.t0 + time.dur * u;
    if (body && i % Math.max(1, Math.round(w / 3)) === 0) dep.dab(p.x[i], p.y[i], w, f * body, a, Math.max(1, w * edge));
    for (let b = 0; b < n; b++) {
      const v = nv[b];
      let ink = f;
      if (dry) ink *= clamp(1.25 - dry * u * thirst[b]);
      if (skip) ink *= clamp(0.5 + (noise.at(s * 0.035 + id[b], id[b]) - 0.5) * skip * 4);
      if (ink <= 0.015) continue;
      const off = wander ? (v + (noise.at(s * 0.012, id[b]) - 0.5) * wander) * w : v * w;
      dep.dab(p.x[i] + p.nx[i] * off, p.y[i] + p.ny[i] * off, r, ink, a);
    }
  }
}

// The drawing, in this bake's pixels: strokes, regions (closed shapes as seen, painter's order), a tone plan and the
// distance fields the marks follow. edge: distance to the nearest line or region border. sil: distance outside the
// whole object, 0 inside it.
export function plan(drawing, { W, H, S, box, seed }) {
  const scale = (box[2] * S) / 952, ox = box[0] * S, oy = box[1] * S;
  const strokes = drawing.strokes.map((s, order) => {
    const pts = new Float32Array(s.pts.length);
    for (let i = 0; i < pts.length; i += 2) { pts[i] = s.pts[i] * scale + ox; pts[i + 1] = s.pts[i + 1] * scale + oy; }
    return { ...s, pts, w: s.w * scale, order };
  });
  const id = new Int16Array(W * H), elements = new Map();
  for (const s of [...strokes].sort((a, b) => a.paint - b.paint)) {
    if (!elements.has(s.e)) elements.set(s.e, []);
    elements.get(s.e).push(s);
  }
  const regions = [{ id: 0, tone: 0, fill: "none", order: 0, parent: 0 }];
  for (const rings of elements.values()) {
    const first = rings[0];
    const closed = rings.every((r) => r.closed);
    if (!closed && first.fill === "none") continue;
    const region = { id: regions.length, fill: first.fill, order: Math.min(...rings.map((r) => r.order)), parent: 0 };
    regions.push(region);
    const counts = new Map();
    fillRings(rings.map((r) => r.pts), W, H, (p) => {
      counts.set(id[p], (counts.get(id[p]) || 0) + 1);
      id[p] = region.id;
    });
    let most = 0;
    for (const [k, v] of counts) if (v > most) { most = v; region.parent = k; }
  }
  const line = new Uint8Array(W * H), solid = new Uint8Array(W * H);
  const stamp = (x, y, r) => {
    for (let py = Math.max(0, Math.floor(y - r)); py <= Math.min(H - 1, Math.ceil(y + r)); py++) {
      for (let px = Math.max(0, Math.floor(x - r)); px <= Math.min(W - 1, Math.ceil(x + r)); px++) {
        if ((px - x) ** 2 + (py - y) ** 2 <= r * r) { line[px + py * W] = 1; solid[px + py * W] = 1; }
      }
    }
  };
  for (const s of strokes) {
    if (s.line === "none") continue;
    const p = walk(s.closed ? closeRing(s.pts) : s.pts, 1.5);
    for (let i = 0; i < p.n; i++) stamp(p.x[i], p.y[i], Math.max(1, s.w / 2));
  }
  // what the lines enclose is a shape too, however it was drawn: flood the sheet from its border, the rest is inside
  const outside = new Uint8Array(W * H), stack = new Int32Array(W * H);
  let top = 0;
  const push = (p) => { if (!outside[p] && !line[p] && !id[p]) { outside[p] = 1; stack[top++] = p; } };
  const flood = (start, mark) => {
    push(start);
    while (top) {
      const p = stack[--top], x = p % W;
      mark(p);
      if (x > 0) push(p - 1);
      if (x < W - 1) push(p + 1);
      if (p >= W) push(p - W);
      if (p + W < W * H) push(p + W);
    }
  };
  for (let x = 0; x < W; x++) { flood(x, () => {}); flood(x + (H - 1) * W, () => {}); }
  for (let y = 0; y < H; y++) { flood(y * W, () => {}); flood(W - 1 + y * W, () => {}); }
  const minArea = 400 * S * S;
  for (let p = 0; p < W * H; p++) {
    if (outside[p] || line[p] || id[p]) continue;
    const region = { id: regions.length, fill: "CANVAS", order: 0, parent: 0, open: true }, cells = [];
    flood(p, (q) => cells.push(q));
    if (cells.length < minArea) continue;
    regions.push(region);
    for (const q of cells) id[q] = region.id;
  }
  for (const r of regions) Object.assign(r, { area: 0, sx: 0, sy: 0, x0: W, y0: H, x1: 0, y1: 0 });
  for (let y = 0, p = 0; y < H; y++) {
    for (let x = 0; x < W; x++, p++) {
      const r = regions[id[p]];
      r.area++; r.sx += x; r.sy += y;
      if (x < r.x0) r.x0 = x; if (x > r.x1) r.x1 = x; if (y < r.y0) r.y0 = y; if (y > r.y1) r.y1 = y;
    }
  }
  const rnd = seeded(seed ^ 0x51ed), picks = [0.68, 0.32, 0.84, 0.48, 0.2];
  for (const r of regions) {
    if (!r.id) continue;
    r.cx = r.area ? r.sx / r.area : 0; r.cy = r.area ? r.sy / r.area : 0;
    const parent = regions[r.parent].tone || 0.12;
    const start = Math.floor(rnd() * picks.length);
    let tone = picks[start];
    if (r.fill === "INK") tone = 0.95;
    else if (r.fill === "MUTED") tone = 0.66;
    else if (r.fill === "LINE") tone = 0.4;
    else {
      for (let k = 0; k < picks.length && Math.abs(picks[(start + k) % picks.length] - parent) < 0.22; k++) tone = picks[(start + k + 1) % picks.length];
      if (r.fill === "none" || r.open) tone *= 0.6; // a shape nobody filled may only be the air between two lines
    }
    r.tone = tone;
    r.angle = -0.95 + (rnd() - 0.5) * 0.3; // a right hand's diagonal, a little different per shape
  }

  for (let p = 0; p < W * H; p++) if (id[p]) solid[p] = 1;
  const borders = Uint8Array.from(line);
  for (let y = 1, p = W + 1; y < H - 1; y++, p += 2) {
    for (let x = 1; x < W - 1; x++, p++) {
      if (id[p] !== id[p - 1] || id[p] !== id[p - W]) borders[p] = 1;
    }
  }
  const edge = distance(borders, W, H), sil = distance(solid, W, H);

  // The object's light comes from the upper left: a shape is brighter on that side, and darker along its far border
  const tone = new Float32Array(W * H), LX = -0.55, LY = -0.83;
  for (let y = 0, p = 0; y < H; y++) {
    for (let x = 0; x < W; x++, p++) {
      const r = regions[id[p]];
      if (!r.id) continue;
      const reach = Math.max(30 * S, 0.5 * Math.hypot(r.x1 - r.x0, r.y1 - r.y0));
      const g = ((x - r.cx) * LX + (y - r.cy) * LY) / reach;
      tone[p] = clamp(r.tone * (0.78 + 0.62 * g));
    }
  }
  const dots = (drawing.dots || []).map(([x, y]) => [x * scale + ox, y * scale + oy]);
  return { strokes, regions, id, edge, sil, tone, line, dots, scale, ox, oy };
}

export function closeRing(pts) {
  const out = new Float32Array(pts.length + 2);
  out.set(pts); out[pts.length] = pts[0]; out[pts.length + 1] = pts[1];
  return out;
}

// A stroke as a hand draws it: lifted at every sharp corner, so a box is four strokes and not one trim of a dash
export function pieces(s, corner = 0.9) {
  const ring = s.closed ? closeRing(s.pts) : s.pts;
  const out = [];
  let from = 0;
  for (let i = 2; i + 2 < ring.length; i += 2) {
    const ax = ring[i] - ring[i - 2], ay = ring[i + 1] - ring[i - 1], bx = ring[i + 2] - ring[i], by = ring[i + 3] - ring[i + 1];
    const turn = Math.abs(Math.atan2(ax * by - ay * bx, ax * bx + ay * by));
    if (turn > corner) { out.push(ring.slice(from, i + 2)); from = i; }
  }
  out.push(ring.slice(from));
  return out.filter((p) => length(p) > 3);
}

// Straight lines across a region at `angle`, cut to the region: what a hand fills a shape with
export function sweep(pl, region, W, angle, spacing, rnd, { margin = 0, min = 6 } = {}) {
  const dx = Math.cos(angle), dy = Math.sin(angle), nx = -dy, ny = dx;
  const c = [[region.x0, region.y0], [region.x1, region.y0], [region.x0, region.y1], [region.x1, region.y1]];
  const on = c.map(([x, y]) => x * nx + y * ny), along = c.map(([x, y]) => x * dx + y * dy);
  const lo = Math.min(...on), hi = Math.max(...on), from = Math.min(...along) - 2, to = Math.max(...along) + 2;
  const out = [], H = pl.id.length / W;
  for (let o = lo + spacing * rnd(); o < hi; o += spacing * (0.8 + 0.4 * rnd())) {
    let start = null, last = null;
    for (let t = from; t <= to + 2; t += 1) {
      const x = o * nx + t * dx, y = o * ny + t * dy;
      const px = Math.round(x), py = Math.round(y);
      const p = px + py * W;
      const inside = t <= to && px >= 0 && py >= 0 && px < W && py < H && pl.id[p] === region.id && pl.edge[p] >= margin;
      if (inside) {
        if (start === null) start = [x, y];
        last = [x, y];
      } else if (start !== null) {
        if (Math.hypot(last[0] - start[0], last[1] - start[1]) >= min) out.push(Float32Array.of(...start, ...last));
        start = null;
      }
    }
  }
  return out;
}
