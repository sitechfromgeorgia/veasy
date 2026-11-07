// The six materials. Each one decides what a hand would do with this drawing: which marks, in which order, on which
// sheet. Nothing here filters a finished picture: every hatch, gouge and brush stroke is a mark of its own, laid on the
// paper at its own moment. Light pigment on a dark sheet: the engine maps black to the pack's canvas, white to its ink.
import { seeded } from "/lib/seeded.mjs";
import { blur, brush, clamp, Deposit, distance, length, Noise, pieces, plan, shake, smooth, sweep, walk } from "./core.mjs";

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

// A pointed brush: a heavy landing, a thin neck where the hand speeds up, a press, a flick off the paper
const pressure = (noise, key, base) => (u) => {
  const press = 0.2 + 1.5 * noise.at(u * 2.6 + key, key * 0.7) ** 1.5;
  return base * (0.24 + press * smooth(0, 0.04, u + 0.015) * (1 - 0.86 * smooth(0.72, 1, u)));
};

// Marks that follow a field's contours, evenly spaced (Jobard and Lefer's streamlines). Each one is a gouge: pointed at
// both ends, wider where the tone asks for more light.
function gouges(m, pass, layer, o) {
  const { pl, S, W, H, rnd } = m;
  const cell = 2, GW = Math.ceil(W / cell), occ = new Uint8Array(GW * Math.ceil(H / cell));
  const field = o.field, stepLen = 2.5 * S;
  const at = (x, y) => clamp(Math.round(x), 0, W - 1) + clamp(Math.round(y), 0, H - 1) * W;
  const dir = (x, y) => {
    const p = at(x, y), d = field[p];
    if (d < o.near) {
      const gx = field[at(x + 2, y)] - field[at(x - 2, y)], gy = field[at(x, y + 2)] - field[at(x, y - 2)], len = Math.hypot(gx, gy);
      if (len > 0.3) return [-gy / len, gx / len];
    }
    const a = o.angle ? o.angle(p) : 0;
    return [Math.cos(a), Math.sin(a)];
  };
  const seeds = [];
  const gap = 5 * S;
  for (let y = gap / 2; y < H; y += gap) {
    for (let x = gap / 2; x < W; x += gap) {
      const sx = x + (rnd() - 0.5) * gap, sy = y + (rnd() - 0.5) * gap, p = at(sx, sy);
      if (o.keep(p)) seeds.push([sx, sy, rnd()]);
    }
  }
  seeds.sort((a, b) => a[2] - b[2]);
  const blocked = (x, y) => occ[Math.floor(x / cell) + Math.floor(y / cell) * GW];
  const out = [];
  for (const [sx, sy] of seeds) {
    if (blocked(sx, sy)) continue;
    const start = at(sx, sy), region = pl.id[start];
    const tone = o.tone(start);
    if (tone < 0.05) continue;
    const sep = o.sep(tone), limit = o.min + (o.max - o.min) * rnd();
    const line = [[sx, sy]];
    for (const sign of [1, -1]) {
      let [x, y] = [sx, sy], [px, py] = dir(sx, sy);
      px *= sign; py *= sign;
      for (let s = 0; s < limit / 2; s += stepLen) {
        let [dx, dy] = dir(x, y);
        if (dx * px + dy * py < 0) { dx = -dx; dy = -dy; }
        x += dx * stepLen; y += dy * stepLen; px = dx; py = dy;
        if (x < 1 || y < 1 || x >= W - 1 || y >= H - 1) break;
        const p = at(x, y);
        if (!o.keep(p) || pl.id[p] !== region || blocked(x, y)) break;
        if (sign > 0) line.push([x, y]); else line.unshift([x, y]);
      }
    }
    if ((line.length - 1) * stepLen < o.min) continue;
    const reach = Math.ceil((sep * 0.5) / cell);
    for (let i = 0; i < line.length; i += 2) {
      const cx = Math.floor(line[i][0] / cell), cy = Math.floor(line[i][1] / cell);
      for (let dy = -reach; dy <= reach; dy++) {
        for (let dx = -reach; dx <= reach; dx++) {
          if (dx * dx + dy * dy <= reach * reach && cx + dx >= 0 && cx + dx < GW && cy + dy >= 0) occ[cx + dx + (cy + dy) * GW] = 1;
        }
      }
    }
    if (o.broken && rnd() < 1 - o.broken * 1.4 * (tone + 0.35)) continue;
    const pts = Float32Array.from(line.flat());
    const widths = new Float32Array(line.length);
    line.forEach(([x, y], i) => { widths[i] = sep * (0.14 + 0.86 * Math.pow(clamp(o.tone(at(x, y))), 1.1)); });
    out.push({ pts, widths, order: region ? pl.regions[region].order : Math.atan2(sy - H / 2, sx - W / 2), y: sy });
  }
  out.sort((a, b) => a.order - b.order || a.y - b.y);
  for (const g of out) {
    const n = g.widths.length - 1, w = g.widths;
    const lean = rnd(); // a knife enters steep and leaves shallow, at a different point each time
    m.mark(pass, layer, g.pts, {
      w: (u) => w[Math.round(u * n)] * Math.pow(Math.sin(Math.PI * clamp(Math.pow(u, 0.7 + 0.6 * lean))), 0.55), n: 1,
    }, o.take, { lap: o.lap, hand: 0.5 });
  }
}

const MATERIALS = {
  ink_wash(m) {
    const { sheet, pl, S, W, H, noise, rnd } = m, { T, F, M, ground } = sheet;
    m.hand = 2.4; m.boil = 0.8; m.boilStep = 70;
    for (let p = 0; p < W * H; p++) ground[p] = 0.03 + 0.03 * M[p] + 0.022 * F[p] * T[p];
    const grain = (v, p) => v * (0.5 + 0.34 * T[p] + 0.42 * F[p]);
    const air = m.pass(0.16), wash = m.pass(0.34), ink = m.pass(0.5);

    // one pool of thin pigment behind the object, laid by a wide brush: a hard wobbling edge where it dried, the
    // pigment carried out to that edge, soft in the middle (Curtis et al., Deegan's ring)
    const [bx, by, bw] = [pl.ox, pl.oy, 952 * pl.scale], bh = 640 * pl.scale;
    const reach = new Uint8Array(W * H);
    for (let y = 0, p = 0; y < H; y++) {
      for (let x = 0; x < W; x++, p++) {
        const nx = ((x - bx) / bw - 0.5) * 2, ny = ((y - by) / bh - 0.56) * 2;
        const shape = nx * nx * 0.9 + ny * ny * 1.5 + (noise.fbm(x / (150 * S) + m.salt, y / (120 * S) + m.salt * 0.37, 4) - 0.5) * 2.1;
        reach[p] = shape > 0.86 ? 1 : 0;
      }
    }
    const shore = distance(reach, W, H);
    const pool = (v, p) => {
      const d = shore[p];
      if (d <= 0) return 0;
      return v * (0.34 + 0.9 * M[p] * F[p] + 1.9 * Math.exp(-d / (5 * S)) + 0.5 * Math.exp(-d / (46 * S))) * (0.7 + 0.5 * T[p]);
    };
    for (let i = 0; i < 5; i++) {
      const y = by + (0.1 + 0.2 * i) * bh, pts = [];
      for (let k = 0; k <= 6; k++) pts.push((i % 2 ? bx + bw + 60 * S - ((bw + 120 * S) * k) / 6 : bx - 60 * S + ((bw + 120 * S) * k) / 6), y + Math.sin(k * 0.9 + i) * 22 * S);
      m.mark(air, BACK, Float32Array.from(pts), { w: () => bh * 0.34, n: 0, body: 0.17, edge: 0.3, bleed: 0.25 }, pool, { hand: 6, lap: 1.3 });
    }

    // washes: a flat brush filling each shape, the pigment gathering along the wet edge, a backrun where it stayed wet
    for (const r of regions(pl, 500 * S * S)) {
      const size = clamp(Math.sqrt(r.area) * 0.42, 20 * S, 72 * S), flow = 0.1 + 1.15 * r.tone * r.tone;
      const leak = 2.5 * S, big = r.area > 9000 * S * S;
      const bloomX = r.cx + (rnd() - 0.5) * (r.x1 - r.x0) * 0.5, bloomY = r.cy + (rnd() - 0.5) * (r.y1 - r.y0) * 0.5;
      const bloomR = Math.sqrt(r.area) * (0.22 + 0.16 * rnd()), bloomKey = rnd() * 60;
      const take = (v, p) => {
        const near = pl.edge[p], own = pl.id[p] === r.id;
        const inside = own ? 1 : smooth(leak * (0.3 + 1.6 * F[p]), 0, near);
        let out = v * (0.74 + 0.26 * T[p]) * (0.6 + 0.8 * pl.tone[p] / Math.max(0.1, r.tone) * (0.55 + 0.6 * M[p])) * inside;
        out *= 1 + 1.7 * Math.exp(-near / (3.5 * S)) * (own ? 1 : 0.2);
        if (big) {
          const x = p % W, y = (p - x) / W, d = Math.hypot(x - bloomX, y - bloomY);
          const front = d - bloomR * (0.7 + 0.75 * noise.fbm(x / (34 * S) + bloomKey, y / (34 * S), 3));
          out *= front < 0 ? 0.62 : 1;
          out += 0.4 * out * Math.exp(-Math.abs(front) / (2.4 * S));
        }
        return out;
      };
      const angle = r.angle * 0.35;
      for (const seg of sweep(pl, r, W, angle, size * 0.72, rnd, { min: 10 * S })) {
        const f = flow * (0.8 + 0.34 * rnd());
        m.mark(wash, TONE, seg, { w: () => size, n: Math.max(6, Math.round(size / (2.6 * S))), dry: 0.62, skip: 0.14, wander: 0.45, flow: () => f, bleed: 0.34, body: 0.74, edge: 0.3 }, take, { hand: 3, lap: 1.5 });
      }
    }

    // the line: a pointed brush, loaded at the start of a stroke, thin at the neck, running dry at the end
    const fibre = (v, p) => smooth(0.1, 0.34, v - (1 - T[p]) * 0.16 - (1 - F[p]) * 0.1) * (0.8 + 0.2 * v) * (0.9 + 0.14 * T[p]);
    for (const s of lines(pl)) {
      const keep = KEEP[s.line] ?? 1;
      for (const pts of pieces(s, 0.8)) {
        const key = m.marks.length * 1.7, base = s.w * (1 + 1.05 * keep);
        m.mark(ink, LINE, pts, {
          w: pressure(noise, key, base), n: Math.max(6, Math.round(base * 1.3)), dry: 0.92, skip: 0.26, wander: 0.3, bleed: 0.2, body: 0.5, edge: 0.14,
          flow: (u) => keep * (1 - 0.12 * u),
        }, fibre, { lap: 1.2 });
      }
    }
    // a few drops off the loaded brush
    for (let i = 0; i < 26; i++) {
      const x = bx + rnd() * bw, y = by + rnd() * 640 * pl.scale, r = (0.6 + 2.8 * rnd() ** 3) * S, v = 0.25 + 0.5 * rnd();
      m.custom(ink, SOFT, 4, (dep, time) => dep.dab(x, y, r, v, time.t0), grain);
    }
    return { gain: [1, 1, 1, 1], wet: [0.3, 0.35, 0.25, 0.1], rise: [0.05, 0.16, 0.05, 0.3] };
  },

  woodcut(m) {
    const { sheet, pl, S, W, H, noise, rnd } = m, { T, M, ground } = sheet;
    m.hand = 0.9; m.boil = 0.55; m.boilStep = 40;
    // the plank: long grain with slow rings, felt in the bare wood and in every printed mass
    const G = new Float32Array(W * H);
    for (let y = 0, p = 0; y < H; y++) {
      for (let x = 0; x < W; x++, p++) {
        const X = x / S, Y = y / S, warp = 90 * noise.fbm(X / 620, Y / 300, 3);
        const ring = 0.5 + 0.5 * Math.sin((Y + warp) * 0.135 + 7 * noise.fbm(X / 900, Y / 90, 2));
        const hair = noise.fbm(X / 190 + 40, (Y + warp * 0.4) / 3.4, 3);
        G[p] = clamp(0.2 + 0.5 * ring + 0.9 * (hair - 0.42));
        ground[p] = 0.022 + 0.034 * G[p] * G[p] + 0.014 * M[p];
      }
    }
    const take = (v, p) => {
      const pressed = smooth(0.34, 0.52, v + (G[p] - 0.5) * 0.08);
      const miss = smooth(0.74, 0.86, G[p]) * smooth(0.5, 0.62, T[p]); // the block's grain, where ink didn't reach the paper
      return pressed * (0.78 + 0.26 * G[p]) * (1 - 0.72 * miss);
    };
    const cut = m.pass(0.3), inner = m.pass(0.46), halo = m.pass(0.24);

    // the outline, left standing by a knife: straight facets, each one a wedge
    for (const s of lines(pl)) {
      const keep = KEEP[s.line] ?? 1, base = s.w * (1 + 1.8 * keep);
      for (const pts of pieces(s, 0.7)) {
        const facet = [], L = length(pts), every = 26 * S;
        const p = walk(pts, 2);
        for (let d = 0; d < L; d += every * (0.7 + 0.8 * rnd())) {
          const i = Math.min(p.n - 1, Math.round((d / L) * (p.n - 1)));
          facet.push(p.x[i], p.y[i]);
        }
        facet.push(p.x[p.n - 1], p.y[p.n - 1]);
        if (facet.length < 4) continue;
        const key = rnd() * 90;
        m.mark(cut, LINE, Float32Array.from(facet), {
          w: (u) => base * (0.55 + 1.0 * noise.at(u * 5 + key, key)) * (0.72 + 0.28 * smooth(0, 0.05, u) * smooth(1, 0.95, u)), n: 1,
        }, take);
      }
    }
    // inside the shapes: cuts along the form, wider where the tone is lighter, so masses break into wedges
    gouges(m, inner, TONE, {
      keep: (p) => pl.id[p] > 0, tone: (p) => pl.tone[p], sep: (t) => (15 - 6 * t) * S, field: pl.edge, near: 30 * S,
      angle: (p) => pl.regions[pl.id[p]].angle, min: 10 * S, max: 170 * S, take, lap: 1.5,
    });
    // around the object: the block cleared in rings that echo its silhouette, and thinning out
    const R = 240 * S;
    gouges(m, halo, BACK, {
      keep: (p) => !pl.id[p] && !pl.line[p] && pl.sil[p] > 7 * S && pl.sil[p] < R, tone: (p) => 0.5 * Math.exp(-pl.sil[p] / (80 * S)),
      sep: () => 15 * S, field: pl.sil, near: 1e9, min: 16 * S, max: 150 * S, take, broken: 0.55, lap: 1.5,
    });
    return { gain: [1, 1, 1, 1], wet: [0.15, 0.15, 0.15, 0.15], rise: [0.03, 0.05, 0.05, 0.05] };
  },

  blueprint(m) {
    const { sheet, pl, S, W, H, noise, rnd } = m, { T, F, M, ground } = sheet;
    m.hand = 0.3; m.boil = 0.32; m.boilStep = 90;
    // a coated sheet: the brush's streaks in the coating, two folds, the weave of the linen
    const foldX = W * 0.5, foldA = H * 0.34, foldB = H * 0.71;
    for (let y = 0, p = 0; y < H; y++) {
      for (let x = 0; x < W; x++, p++) {
        const coat = noise.fbm(x / (640 * S), y / (15 * S), 3), weave = Math.sin((x / S) * 2.1) * Math.sin((y / S) * 2.1);
        let v = 0.062 + 0.03 * M[p] + 0.05 * coat * coat + 0.008 * weave + 0.012 * T[p];
        const fold = Math.min(Math.abs(x - foldX), Math.abs(y - foldA), Math.abs(y - foldB)) / S + (F[p] - 0.5) * 1.2;
        v += 0.028 * Math.exp((-fold * fold) / 2.2) * (0.5 + F[p]) + 0.012 * Math.exp(-Math.abs(fold) / 22);
        ground[p] = v;
      }
    }
    const grid = m.pass(0.14), build = m.pass(0.22), ink = m.pass(0.46), section = m.pass(0.18);
    const pen = (v, p) => v * (0.8 + 0.2 * T[p]) * (0.9 + 0.1 * F[p]);
    const step = 54 * S;
    for (let i = 1, x = (W % step) / 2; x < W; x += step, i++) {
      const y0 = 40 * S + rnd() * 30 * S, f = i % 5 ? 0.15 : 0.3;
      m.mark(grid, BACK, Float32Array.of(x, y0, x + 1.5 * S * (rnd() - 0.5), H - y0), { w: () => (i % 5 ? 0.9 : 1.2) * S, n: 1, flow: () => f, skip: 0.1 }, pen, { hand: 0.5 });
    }
    for (let i = 1, y = (H % step) / 2; y < H; y += step, i++) {
      const x0 = 30 * S + rnd() * 26 * S, f = i % 5 ? 0.15 : 0.3;
      m.mark(grid, BACK, Float32Array.of(x0, y, W - x0, y + 1.5 * S * (rnd() - 0.5)), { w: () => (i % 5 ? 0.9 : 1.2) * S, n: 1, flow: () => f, skip: 0.1 }, pen, { hand: 0.5 });
    }
    // light construction lines, run past their corners; then the inked line over them
    for (const s of lines(pl)) {
      const keep = KEEP[s.line] ?? 1;
      for (const pts of pieces(s, 0.7)) {
        const L = length(pts), n = pts.length;
        const dx = pts[n - 2] - pts[0], dy = pts[n - 1] - pts[1], d = Math.hypot(dx, dy);
        if (d > 24 * S && d > 0.97 * L) {
          const a = (14 + 34 * rnd()) * S, b = (14 + 34 * rnd()) * S, ux = dx / d, uy = dy / d;
          m.mark(build, SOFT, Float32Array.of(pts[0] - ux * a, pts[1] - uy * a, pts[n - 2] + ux * b, pts[n - 1] + uy * b), { w: () => 1.1 * S, n: 1, flow: () => 0.3 }, pen, { hand: 0.3 });
        }
        const base = Math.max(2.1 * S, s.w * (0.34 + 0.34 * keep));
        m.mark(ink, SOFT, pts, { w: () => base * 5, n: 0, body: 0.09 * keep }, pen);
        m.mark(ink, LINE, pts, { w: (u) => base * (1 + 0.42 * Math.exp(-(u * L) / (3 * S)) + 0.3 * Math.exp(-((1 - u) * L) / (3 * S))), n: 1, flow: () => 0.72 + 0.28 * keep }, pen);
      }
    }
    // section lines in the solid parts: a ruled 45 degrees, even and exact
    for (const r of regions(pl, 1400 * S * S)) {
      if (r.fill === "none" && r.tone < 0.3) continue;
      const gap = (15 - 7 * r.tone) * S, f = 0.32 + 0.28 * r.tone;
      for (const seg of sweep(pl, r, W, -Math.PI / 4, gap, () => 0.5, { margin: 2.5 * S, min: 5 * S })) {
        m.mark(section, TONE, seg, { w: () => 1.3 * S, n: 1, flow: () => f }, pen, { hand: 0.15 });
      }
    }
    // the object's size, ruled below it, with no figure on it: the figure is the film's
    let x0 = W, x1 = 0, y1 = 0;
    for (const s of pl.strokes) {
      for (let i = 0; i < s.pts.length; i += 2) {
        x0 = Math.min(x0, s.pts[i]); x1 = Math.max(x1, s.pts[i]); y1 = Math.max(y1, s.pts[i + 1]);
      }
    }
    const low = y1 + 58 * S, tick = 9 * S, thin = { w: () => 1.2 * S, n: 1, flow: () => 0.62 };
    if (low < H - 80 * S) {
      for (const x of [x0, x1]) m.mark(section, SOFT, Float32Array.of(x, y1 + 10 * S, x, low + 12 * S), thin, pen, { hand: 0.1 });
      m.mark(section, SOFT, Float32Array.of(x0, low, x1, low), thin, pen, { hand: 0.1 });
      for (const x of [x0, x1]) m.mark(section, LINE, Float32Array.of(x - tick, low + tick, x + tick, low - tick), { w: () => 2 * S, n: 1, flow: () => 0.8 }, pen, { hand: 0 });
    }
    return { gain: [1, 1, 1, 1], wet: [0.2, 0.2, 0.2, 0.1], rise: [0.04, 0.04, 0.05, 0.05] };
  },

  halftone(m) {
    const { sheet, pl, S, W, H, noise, rnd } = m, { T, F, M, ground } = sheet;
    m.hand = 1; m.boil = 0.3; m.boilStep = 80;
    for (let p = 0; p < W * H; p++) ground[p] = 0.02 + 0.02 * M[p] + 0.024 * F[p] * T[p];
    // the rollers ran short in places: the plate takes ink in long bands and patches
    const starve = new Float32Array(W * H);
    for (let y = 0, p = 0; y < H; y++) {
      for (let x = 0; x < W; x++, p++) starve[p] = 0.62 + 0.5 * noise.fbm(x / (420 * S) + 9, y / (70 * S), 3) + 0.14 * F[p];
    }
    const printed = (v, p) => {
      const edge = smooth(0.44, 0.56, v + (T[p] - 0.5) * 0.36 + (F[p] - 0.5) * 0.22);
      const salt = smooth(0.56, 0.66, T[p] * 0.5 + F[p] * 0.5) * smooth(0.82, 1.02, 1.5 - starve[p]);
      return edge * clamp(starve[p]) * (1 - 0.85 * salt);
    };
    const key = m.pass(0.3), tint = m.pass(0.28), screen = m.pass(0.42);
    // the key plate: a thin solid line
    for (const s of lines(pl)) {
      const keep = KEEP[s.line] ?? 1, base = s.w * (0.5 + 0.75 * keep);
      for (const pts of pieces(s, 0.8)) {
        const k = rnd() * 50;
        m.mark(key, LINE, pts, { w: (u) => base * (0.7 + 0.6 * noise.at(u * 6 + k, k)), n: 1, flow: () => 0.96 }, printed);
      }
    }
    // the tint plate, cut by hand and off register: its shapes miss the line, and a graded panel stands behind them,
    // knocked out around the object
    const pitch = 15 * S, c = Math.SQRT1_2, shiftX = 13 * S, shiftY = -9 * S, dots = [];
    const px0 = 54 * S, px1 = 1026 * S, py0 = pl.oy - 70 * S, py1 = pl.oy + 640 * pl.scale + 34 * S;
    const inPanel = (x, y) => x > px0 + (y - py0) * 0.02 && x < px1 - (y - py0) * 0.03 && y > py0 + (x - px0) * 0.016 && y < py1 - (x - px0) * 0.01;
    const span = Math.ceil((W + H) / pitch);
    for (let i = -span; i <= span; i++) {
      for (let j = -span; j <= span; j++) {
        const x = (i - j) * pitch * c + W / 2, y = (i + j) * pitch * c + H / 2;
        if (x < 0 || y < 0 || x >= W || y >= H) continue;
        const px = Math.round(x - shiftX), py = Math.round(y - shiftY), p = clamp(px, 0, W - 1) + clamp(py, 0, H - 1) * W;
        const inside = pl.id[p] > 0;
        let q;
        if (inside) q = 0.1 + 1.1 * pl.tone[p] * pl.tone[p];
        else {
          if (!inPanel(x, y) || pl.sil[p] < 26 * S) continue;
          q = 0.05 + 0.3 * smooth(py0, py1, y) ** 1.6;
        }
        const r = pitch * Math.sqrt(Math.pow(clamp(q), 1 / 1.35) / Math.PI) * 1.05;
        dots.push({ x, y, r, order: inside ? pl.regions[pl.id[p]].order : 1e4, back: !inside });
      }
    }
    dots.sort((a, b) => a.order - b.order || a.y - b.y);
    for (const d of dots) {
      const lean = noise.at(d.x / 3 + 5, d.y / 3) * 0.7 * S;
      m.custom(d.back ? tint : screen, d.back ? BACK : TONE, 5 + d.r * 0.2, (dep, time) => {
        dep.dab(d.x, d.y, d.r * 0.5, 1, time.t0, 1.2 * S);
        dep.dab(d.x + lean, d.y - lean, d.r * 0.78, 1, time.t0 + 0.09, 1.4 * S);
        dep.dab(d.x, d.y + lean, d.r, 0.9, time.t0 + 0.2, 1.6 * S);
      }, printed);
    }
    return { gain: [1, 1, 1, 0.8], wet: [0.1, 0.12, 0.12, 0.12], rise: [0.04, 0.05, 0.05, 0.05] };
  },

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
        w: (u) => base * (0.55 + 0.9 * noise.at(u * 3 + key, key)), n: 3, body: 1, edge: 0.5, wander: 0.3,
        flow: (u) => press * (0.56 + 0.8 * noise.at(u * 5 + key * 2, key + 3)) * smooth(0, 0.03, u) * (1 - 0.3 * smooth(0.9, 1, u)),
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
    const lead = (v, p) => smooth(0.3, 0.74, v * 0.92 + (T[p] * 0.8 + F[p] * 0.2) * 0.42) * (0.66 + 0.34 * T[p]);
    const sketch = m.pass(0.14), outline = m.pass(0.34), hatch = m.pass(0.52);
    const run = (pass, layer, pts, width, press, opts = {}) => {
      const key = rnd() * 80;
      return m.mark(pass, layer, pts, {
        w: (u) => width * (0.7 + 0.6 * noise.at(u * 3 + key, key)), n: 1,
        flow: (u) => press * (0.62 + 0.62 * noise.at(u * 3.3 + key * 1.3, key + 9)) * smooth(0, 0.05, u) * (1 - 0.82 * smooth(0.6, 1, u)),
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
            if (part.length >= 4) run(outline, LINE, Float32Array.from(part), Math.max(1.7 * S, s.w * (0.3 + 0.2 * keep)), (0.55 + 0.5 * keep) * (again ? 0.72 : 1));
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
  const w = Math.ceil(W / 3), h = Math.ceil(H / 3), n = w * h, time = new Float32Array(n).fill(Infinity), cost = new Float32Array(n);
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
