// The materials. Each one decides what a hand would do with this drawing: which marks, in which order, on which
// sheet. Nothing here filters a finished picture: every hatch, gouge and brush stroke is a mark of its own, laid on the
// paper at its own moment. Light pigment on a dark sheet: the engine maps black to the pack's canvas, white to its ink.
import { seeded } from "/lib/seeded.mjs";
import { blur, brush, clamp, Deposit, length, Noise, pieces, plan, shake, smooth, sweep, walk } from "./core.mjs";

export const LINE = 0, TONE = 1, SOFT = 2, BACK = 3; // the four layers of a bake, each with its own moment per pixel

const KEEP = { INK: 1, MUTED: 0.74, LINE: 0.5 };
const lines = (pl) => pl.strokes.filter((s) => s.line !== "none");
const regions = (pl, min) => pl.regions.filter((r) => r.id && r.area >= min).sort((a, b) => a.order - b.order);

class Sheet { // the paper a clip is painted on: tooth (fine), fibre (middle), mottle (wide)
  constructor(W, H, S, noise) {
    Object.assign(this, { W, H, S, noise });
    this.T = new Float32Array(W * H); this.F = new Float32Array(W * H); this.M = new Float32Array(W * H);
    this.ground = new Float32Array(W * H);
    const fine = Math.max(1.15, 1.8 * S);
    for (let y = 0, p = 0; y < H; y++) {
      for (let x = 0; x < W; x++, p++) {
        this.T[p] = clamp((noise.fbm(x / fine, y / fine, 2) - 0.5) * 2.6 + 0.5);
        this.F[p] = clamp((noise.fbm(x / (11 * S), y / (11 * S), 3) - 0.5) * 2.2 + 0.5);
        this.M[p] = clamp((noise.fbm(x / (210 * S), y / (210 * S), 4) - 0.5) * 2.4 + 0.5);
      }
    }
  }
}

class Painter {
  constructor(name, spec, ctx, drawing) {
    const W = ctx.width, H = ctx.height, S = W / 1080;
    Object.assign(this, { name, spec, ctx, W, H, S, seed: ctx.seed });
    this.noise = new Noise(ctx.seed * 7 + 3);
    let salt = 7; // one seed, a different sheet for each drawing
    for (const s of drawing.strokes) for (let i = 0; i < s.pts.length; i += 7) salt = (Math.imul(salt, 31) + Math.round(s.pts[i] * 10)) | 0;
    this.salt = (salt >>> 0) % 997;
    this.rnd = seeded(ctx.seed * 31 + 11 + this.salt);
    this.sheet = new Sheet(W, H, S, this.noise);
    this.pl = plan(drawing, { W, H, S, box: spec.box || [40, 640, 1000], seed: ctx.seed });
    this.marks = [];
    this.passes = [];
    this.dep = new Deposit(W, H);
    this.boil = 1; this.hand = 2; this.handStep = 140; this.boilStep = 60; this.step = 1;
  }
  pass(share) { this.passes.push({ share, marks: [] }); return this.passes.length - 1; }
  mark(pass, layer, pts, style, take, opts = {}) {
    const m = { layer, pts, style, take, key: this.marks.length + 1, len: pts ? length(pts) : 0, ...opts };
    this.marks.push(m); this.passes[pass].marks.push(m);
    return m;
  }
  custom(pass, layer, len, draw, take) { // a mark that deposits by itself (a dot of a screen, a splash)
    return this.mark(pass, layer, null, null, take, { draw, len });
  }
  schedule(start, draw) {
    const total = this.passes.reduce((sum, p) => sum + p.share, 0);
    let at = start;
    for (const p of this.passes) {
      const span = (draw * p.share) / total;
      const weight = p.marks.reduce((sum, m) => sum + (m.weight = Math.pow(m.len, 0.72) + 6), 0) || 1;
      let t = at;
      for (const m of p.marks) {
        const dur = (span * m.weight) / weight;
        m.t0 = t; m.dur = dur * (m.lap || 1); t += dur;
      }
      at += span;
    }
  }
  paint(variant) {
    const { W, H, dep, noise, S } = this;
    const layers = [0, 1, 2, 3].map(() => ({ c: new Float32Array(W * H), a: new Float32Array(W * H).fill(1e6) }));
    for (const m of this.marks) {
      if (m.draw) m.draw(dep, { t0: m.t0, dur: m.dur }, variant);
      else {
        const p = shake(walk(m.pts, this.step), noise, m.key, (m.hand ?? this.hand) * S, this.handStep * S, (m.boil ?? this.boil) * S, this.boilStep * S, variant);
        brush(dep, p, m.style, { t0: m.t0, dur: m.dur }, m.key, noise);
      }
      dep.flush(layers[m.layer], m.take);
    }
    return layers;
  }
}

const MATERIALS = {
  chalk(m) {
    const { sheet, pl, S, W, H, noise, rnd, dep } = m, { T, F, M, ground } = sheet;
    m.hand = 2.2; m.boil = 0.9; m.boilStep = 55;
    // a slate, wiped more than once: the old lessons are still there as long pale smears
    const ghost = { c: new Float32Array(W * H), a: new Float32Array(W * H).fill(1e6) };
    for (let i = 0; i < 22; i++) {
      const y = rnd() * H, x = rnd() * W * 0.6, len = (240 + rnd() * 700) * S, tilt = (rnd() - 0.5) * 0.22, wid = (14 + 46 * rnd()) * S;
      const pts = Float32Array.of(x, y, x + len * 0.5, y + (rnd() - 0.5) * 60 * S, x + len, y + tilt * len);
      brush(dep, shake(walk(pts, 3), noise, i + 300, 8 * S, 120 * S, 0, 60, 0), { w: () => wid, n: 7, dry: 0.7, skip: 0.4, wander: 0.4, body: 0.35, flow: () => 0.5 }, { t0: 0, dur: 1 }, i + 300, noise);
      dep.flush(ghost);
    }
    const smear = blur(ghost.c, W, H, 7 * S);
    for (let y = 0, p = 0; y < H; y++) {
      for (let x = 0; x < W; x++, p++) {
        const swipe = noise.fbm(x / (800 * S), y / (26 * S), 3);
        ground[p] = 0.036 + 0.05 * M[p] + 0.05 * swipe * swipe + 0.026 * T[p] * F[p] + 0.13 * smear[p] * (0.5 + 0.7 * T[p]);
      }
    }
    // chalk stays on the slate's high points: the harder the press, the deeper it reaches
    const dry = (v, p) => {
      const high = T[p] * 0.5 + F[p] * 0.5;
      return smooth(0.56, 0.72, v * 0.9 + high * 0.55) * (0.72 + 0.34 * high);
    };
    const side = m.pass(0.34), stick = m.pass(0.5), dust = m.pass(0.16);
    for (const r of regions(pl, 700 * S * S)) {
      const size = clamp(Math.sqrt(r.area) * 0.3, 14 * S, 40 * S), f = 0.2 + 0.46 * r.tone;
      const clip = (v, p) => (pl.id[p] === r.id ? dry(v * (0.92 + 0.2 * pl.tone[p]), p) : 0);
      for (const seg of sweep(pl, r, W, r.angle * 0.7, size * 0.7, rnd, { min: 8 * S })) {
        const load = f * (0.66 + 0.6 * rnd());
        m.mark(side, TONE, seg, { w: () => size, n: 12, body: 0.42, edge: 0.25, skip: 0.42, wander: 0.3, flow: (u) => load * (1.25 - 0.4 * u) }, clip, { hand: 4, lap: 1.4 });
      }
    }
    const lay = (pts, base, press, key) => {
      m.mark(stick, LINE, pts, {
        w: (u) => base * (0.42 + 1.15 * noise.at(u * 3 + key, key)), n: 3, body: 1, edge: 0.5, wander: 0.3,
        flow: (u) => press * (0.36 + 1.1 * noise.at(u * 6 + key * 2, key + 3)) * smooth(0, 0.03, u) * (1 - 0.3 * smooth(0.9, 1, u)),
      }, dry, { lap: 1.2 });
      m.mark(stick, SOFT, pts, { w: () => base * 2.8, n: 0, body: 0.09 * press }, (v, p) => v * (0.2 + 1.2 * F[p] * T[p]), { hand: 3 });
    };
    for (const s of lines(pl)) {
      const keep = KEEP[s.line] ?? 1, base = Math.max(4.5 * S, s.w * (0.65 + 0.6 * keep));
      for (const pts of pieces(s, 0.8)) {
        lay(pts, base, 0.62 + 0.4 * keep, rnd() * 70);
        if (keep === 1 && rnd() < 0.6) lay(pts, base * 0.8, 0.8, rnd() * 70);
      }
    }
    // what falls off a stick: a few grains under the heavy lines
    for (let i = 0; i < 260; i++) {
      const s = pl.strokes[Math.floor(rnd() * pl.strokes.length)], at = Math.floor(rnd() * (s.pts.length / 2)) * 2;
      const x = s.pts[at] + (rnd() - 0.5) * 34 * S, y = s.pts[at + 1] + rnd() * rnd() * 80 * S, r = (0.5 + rnd() * rnd() * 2) * S, v = 0.25 + 0.5 * rnd();
      m.custom(dust, SOFT, 3, (d, time) => d.dab(x, y, r, v, time.t0));
    }
    return { gain: [1, 1, 1, 1], wet: [0.12, 0.1, 0.1, 0.05], rise: [0.03, 0.05, 0.08, 0.05] };
  },

  pencil_hatch(m) {
    const { sheet, pl, S, W, noise, rnd } = m, { T, F, M, ground } = sheet;
    m.hand = 1.6; m.boil = 0.7; m.boilStep = 50;
    for (let p = 0; p < ground.length; p++) ground[p] = 0.026 + 0.02 * M[p] + 0.03 * T[p] * T[p];
    const lead = (v, p) => smooth(0.38, 0.8, v * 0.86 + T[p] * 0.46) * (0.5 + 0.4 * T[p]);
    const sketch = m.pass(0.14), outline = m.pass(0.34), hatch = m.pass(0.52);
    const run = (pass, layer, pts, width, press, opts = {}) => {
      const key = rnd() * 80;
      return m.mark(pass, layer, pts, {
        w: (u) => width * (0.55 + 1.0 * noise.at(u * 3 + key, key)), n: 1,
        flow: (u) => press * (0.42 + 1.0 * noise.at(u * 4 + key * 1.3, key + 9)) * smooth(0, 0.05, u) * (1 - 0.82 * smooth(0.6, 1, u)),
      }, lead, opts);
    };
    for (const s of lines(pl)) {
      const keep = KEEP[s.line] ?? 1;
      for (const pts of pieces(s, 0.75)) {
        const n = pts.length, L = length(pts), p = walk(pts, 2);
        if (L > 40 * S) { // the searching line, longer than the corner it finds
          const a = Math.min(n - 2, 2), ax = pts[0] - pts[a], ay = pts[1] - pts[a + 1], ad = Math.hypot(ax, ay) || 1, b = (10 + 26 * rnd()) * S;
          run(sketch, SOFT, Float32Array.from([pts[0] + (ax / ad) * b, pts[1] + (ay / ad) * b, ...pts]), 1.4 * S, 0.5);
        }
        // the line itself: overlapping pulls of the wrist, restated where it matters
        for (let again = 0; again < (keep === 1 ? 3 : 2); again++) {
          let from = 0;
          while (from < p.n - 2) {
            const reach = Math.round(((90 + 150 * rnd()) * S) / 2), to = Math.min(p.n - 1, from + reach), part = [];
            const off = again ? (rnd() - 0.5) * 3.6 * S : 0;
            for (let i = from; i <= to; i += 4) part.push(p.x[i] + p.nx[i] * off, p.y[i] + p.ny[i] * off);
            part.push(p.x[to], p.y[to]);
            if (part.length >= 4) run(outline, LINE, Float32Array.from(part), Math.max(1.7 * S, s.w * (0.26 + 0.2 * keep)), (0.5 + 0.34 * keep) * (again ? 0.74 : 1));
            if (to === p.n - 1) break;
            from = to - Math.round((8 + 14 * rnd()) * S);
          }
        }
      }
    }
    // hatching: nested sets, so a darker tone adds strokes and never moves one (tonal art maps)
    for (const r of regions(pl, 300 * S * S)) {
      const sets = [[r.angle, 0.12], [r.angle + 0.92, 0.36], [r.angle - 0.42, 0.6]];
      sets.forEach(([angle, from], set) => {
        const gap = (7 - set * 0.7) * S;
        for (const seg of sweep(pl, r, W, angle, gap, rnd, { margin: 1.5 * S, min: 7 * S })) {
          const x = Math.round((seg[0] + seg[2]) / 2), y = Math.round((seg[1] + seg[3]) / 2), t = pl.tone[x + y * W] || r.tone;
          if (t < from || rnd() > 0.45 + 0.9 * (t - from)) continue;
          const L = Math.hypot(seg[2] - seg[0], seg[3] - seg[1]), parts = Math.max(1, Math.round(L / ((70 + 90 * rnd()) * S)));
          for (let k = 0; k < parts; k++) {
            const a = k / parts, b = Math.min(1, (k + 1) / parts + 0.06), bow = (rnd() - 0.3) * 7 * S, nx = -(seg[3] - seg[1]) / L, ny = (seg[2] - seg[0]) / L;
            const ax = seg[0] + (seg[2] - seg[0]) * a, ay = seg[1] + (seg[3] - seg[1]) * a, bx = seg[0] + (seg[2] - seg[0]) * b, by = seg[1] + (seg[3] - seg[1]) * b;
            run(hatch, set ? SOFT : TONE, Float32Array.of(ax, ay, (ax + bx) / 2 + nx * bow, (ay + by) / 2 + ny * bow, bx, by), 1.7 * S, 0.5 + 0.55 * t, { hand: 0.8, lap: 2 });
          }
        }
      });
    }
    return { gain: [1, 1, 1, 1], wet: [0.1, 0.1, 0.1, 0.1], rise: [0.03, 0.04, 0.04, 0.04] };
  },
};

export const NAMES = Object.keys(MATERIALS);
export const REVEALS = ["stroke", "scrape", "print_through", "flood"];

// Reveals are only a change to when pigment lands. `stroke` is the marks' own order. The others replace that moment.
function scrape(m, draw, start) { // a cover the tool drags off in streaks; the picture was there all along
  const { W, H, S, noise, pl, dep, rnd } = m;
  const box = { c: new Float32Array(W * H), a: new Float32Array(W * H).fill(1e6) };
  const top = pl.oy - 150 * S, high = 640 * pl.scale + 300 * S, runs = 7, wide = (high / runs) * 1.55;
  for (let i = 0; i < runs; i++) {
    const y = top + (i + 0.5) * (high / runs), flip = i % 2, a = flip ? W + 60 * S : -60 * S, b = flip ? -60 * S : W + 60 * S;
    const pts = Float32Array.of(a, y - 16 * S, (a + b) / 2, y + 24 * S * (rnd() - 0.5), b, y + 18 * S);
    const time = { t0: start + (draw * i) / runs, dur: (draw / runs) * 1.1 };
    brush(dep, shake(walk(pts, 2), noise, 500 + i, 6 * S, 200 * S, 0, 60, 0), { w: () => wide, n: 46, dry: 0.5, skip: 0.42, wander: 0.5, flow: () => 1, r: 4.2 * S }, time, 500 + i, noise);
    dep.flush(box);
  }
  return box.a;
}

function rubbed(m, draw, start) { // the print comes through under the baren: in patches, not in order
  const { W, H, S, noise, sheet } = m;
  const at = new Float32Array(W * H);
  for (let y = 0, p = 0; y < H; y++) {
    for (let x = 0; x < W; x++, p++) {
      const patch = clamp((noise.fbm(x / (170 * S), y / (120 * S), 3) - 0.28) * 2.3);
      at[p] = start + draw * (0.38 + 0.6 * patch + 0.03 * sheet.T[p]);
    }
  }
  return at;
}

// Ink poured on: first-passage time over a random floor, so the front runs in fingers and leaves bays (Dijkstra)
function pour(W, H, S, noise, origins) {
  const w = Math.ceil(W / 3), h = Math.ceil(H / 3), n = w * h, time = new Float64Array(n).fill(Infinity), cost = new Float32Array(n);
  for (let y = 0, p = 0; y < h; y++) {
    for (let x = 0; x < w; x++, p++) {
      const c = noise.fbm((x * 3) / (70 * S), (y * 3) / (70 * S), 4);
      cost[p] = 0.5 + 3.4 * c * c + 0.5 * noise.at((x * 3) / (14 * S), (y * 3) / (14 * S));
    }
  }
  const heap = [], swap = (i, j) => { const t = heap[i]; heap[i] = heap[j]; heap[j] = t; };
  const add = (t, p) => {
    heap.push([t, p]);
    for (let i = heap.length - 1; i > 0;) { const u = (i - 1) >> 1; if (heap[u][0] <= heap[i][0]) break; swap(i, u); i = u; }
  };
  const pop = () => {
    const top = heap[0], last = heap.pop();
    if (heap.length) {
      heap[0] = last;
      for (let i = 0; ;) {
        let c = 2 * i + 1;
        if (c >= heap.length) break;
        if (c + 1 < heap.length && heap[c + 1][0] < heap[c][0]) c++;
        if (heap[i][0] <= heap[c][0]) break;
        swap(i, c); i = c;
      }
    }
    return top;
  };
  for (const [x, y] of origins) {
    const p = clamp(Math.round(x / 3), 0, w - 1) + clamp(Math.round(y / 3), 0, h - 1) * w;
    time[p] = 0; add(0, p);
  }
  let latest = 0;
  while (heap.length) {
    const [t, p] = pop();
    if (t > time[p]) continue;
    latest = t;
    const x = p % w, y = (p - x) / w;
    for (const [dx, dy, len] of [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, 1.41], [1, -1, 1.41], [-1, 1, 1.41], [-1, -1, 1.41]]) {
      const nx = x + dx, ny = y + dy;
      if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
      const q = nx + ny * w, next = t + len * (cost[p] + cost[q]) * 0.5;
      if (next < time[q]) { time[q] = next; add(next, q); }
    }
  }
  const out = new Float32Array(W * H);
  for (let y = 0, p = 0; y < H; y++) {
    for (let x = 0; x < W; x++, p++) {
      const fx = Math.min(w - 1.001, x / 3), fy = Math.min(h - 1.001, y / 3), ix = fx | 0, iy = fy | 0, u = fx - ix, v = fy - iy, q = ix + iy * w;
      out[p] = ((time[q] * (1 - u) + time[q + 1] * u) * (1 - v) + (time[q + w] * (1 - u) + time[q + w + 1] * u) * v) / latest;
    }
  }
  return out;
}

function flood(spec, ctx) {
  const W = ctx.width, H = ctx.height, S = W / 1080, noise = new Noise(ctx.seed * 13 + 5);
  const seconds = ctx.seconds, n = W * H, drain = spec.drain !== false;
  const fill = spec.draw ?? seconds * (drain ? 0.42 : 0.8), start = spec.start ?? 0.1, hold = drain ? seconds * 0.1 : 0;
  const origin = (spec.origin || [0.5, 0.42]).map((v, i) => v * (i ? H : W));
  const first = pour(W, H, S, noise, [origin]);
  const second = drain ? pour(W, H, S, new Noise(ctx.seed * 17 + 9), [[W - origin[0], H - origin[1]]]) : null;
  const cov = new Uint8Array(n * 4), arr = new Float32Array(n * 4).fill(1e6), ground = new Float32Array(n * 4);
  for (let y = 0, p = 0; y < H; y++) {
    for (let x = 0; x < W; x++, p++) {
      const fringe = (noise.fbm(x / (9 * S), y / (9 * S), 3) - 0.5) * 0.03;
      cov[p * 4] = 255;
      arr[p * 4] = start + fill * Math.pow(clamp(first[p] + fringe), 1.25); // fast at the pour, slowing as it spreads
      ground[p * 4 + 2] = second ? start + fill + hold + (seconds - start - fill - hold - 0.1) * Math.pow(clamp(second[p] + fringe), 1.25) : 1e6;
    }
  }
  return { ground, variants: [{ cov, arr }], dots: [], marks: 1, gain: [1, 1, 1, 1], wet: [0, 0, 0, 0], rise: [0.05, 1, 1, 1], drain: drain ? 1 : 0, ghost: 0, cover: 0 };
}

export function paint(name, spec, ctx, drawing) {
  if (spec.reveal === "flood") return flood(spec, ctx);
  const m = new Painter(name, spec, ctx, drawing);
  const look = MATERIALS[name](m);
  const draw = spec.draw ?? ctx.seconds * 0.72, start = spec.start ?? 0.15, reveal = spec.reveal || "stroke";
  m.schedule(start, draw);
  const moment = reveal === "scrape" ? scrape(m, draw, start) : reveal === "print_through" ? rubbed(m, draw, start) : null;
  const count = spec.boil === 0 ? 1 : 3, n = m.W * m.H;
  const variants = [];
  const ground = new Float32Array(n * 4), base = m.sheet.ground;
  for (let p = 0; p < n; p++) { ground[p * 4] = base[p]; ground[p * 4 + 2] = 1e6; }
  for (let v = 0; v < count; v++) {
    const layers = m.paint(v);
    const cov = new Uint8Array(n * 4), arr = new Float32Array(n * 4);
    for (let l = 0; l < 4; l++) {
      const { c, a } = layers[l];
      for (let p = 0; p < n; p++) {
        cov[p * 4 + l] = Math.round(clamp(c[p]) * 255);
        arr[p * 4 + l] = moment ? moment[p] : a[p];
      }
    }
    if (v === 0 && moment) {
      if (reveal === "scrape") { // a cover over the drawing, gone where the tool has passed
        for (let p = 0; p < n; p++) {
          ground[p * 4 + 1] = moment[p] < 1e5 ? 0.05 + 0.1 * m.sheet.M[p] * m.sheet.F[p] : 0;
          ground[p * 4 + 2] = moment[p];
        }
      } else { // the same picture, blurred, on its way through the sheet
        const flat = new Float32Array(n);
        for (let p = 0; p < n; p++) {
          let sum = 0;
          for (let l = 0; l < 4; l++) sum += (cov[p * 4 + l] / 255) * (l === 3 ? 0.4 : 1);
          flat[p] = clamp(sum);
        }
        const soft = blur(flat, m.W, m.H, 5 * m.S);
        for (let p = 0; p < n; p++) ground[p * 4 + 3] = soft[p] * 0.55;
      }
    }
    variants.push({ cov, arr });
  }
  return {
    ground, variants, dots: m.pl.dots, marks: m.marks.length, ...look, drain: 0,
    ghost: reveal === "print_through" ? [start, start + draw * 0.5, start + draw] : 0,
    rise: reveal === "stroke" ? look.rise : [0.12, 0.12, 0.12, 0.12],
  };
}
