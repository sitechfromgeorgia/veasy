import { getStroke } from "perfect-freehand";
import { getLength, getPointAtLength } from "@remotion/paths";

/** Cache sampled points [x, y, pressure][] per path d string. */
const sampledPointsCache = new Map<string, number[][]>();

/** Cache settled (progress >= 0.999) SVG path strings per `${d}|${strokeWidth}` (+ optional boil key). */
const settledSvgCache = new Map<string, string>();

/** Cache boiled SVG path `d` strings per `${d}|${tick}|${seed}|${amp}` (at most 4 ticks per stroke). */
const boilPathCache = new Map<string, string>();

/** Classic 4-cel 15 fps ("on twos") boil step on a 30 fps timeline. */
export const boilFrame = (frame: number): number => Math.floor(Math.max(0, frame) / 2) % 4;

/** Gate line boil to non-news programs (explainer, story, blog) so hard news keeps crisp static geometry. */
export const boilTickFor = (p: { program?: string | null }, frame: number): number | undefined =>
  p.program && p.program !== "news" ? boilFrame(frame) : undefined;

const hash32 = (a: number, b: number, c: number, d: number): number => {
  let h = 2166136261 >>> 0;
  h = Math.imul(h ^ (a | 0), 16777619) >>> 0;
  h = Math.imul(h ^ (b | 0), 16777619) >>> 0;
  h = Math.imul(h ^ (c | 0), 16777619) >>> 0;
  h = Math.imul(h ^ (d | 0), 16777619) >>> 0;
  h ^= h >>> 16;
  return h >>> 0;
};

const round1 = (n: number): number => {
  const r = Math.round(n * 10) / 10;
  return r === 0 ? 0 : r;
};

/**
 * Deterministic spatial vertex perturbation bounded to [-amp, +amp] px.
 * Quantizing `(x, y)` before hashing guarantees touching strokes and closed loops stay sealed.
 */
export const boilPoint = (x: number, y: number, tick: number, seed = 0, amp = 1.0): [number, number] => {
  const qx = Math.round(x * 2);
  const qy = Math.round(y * 2);
  const h1 = hash32(qx, qy, tick, seed);
  const h2 = hash32(qx, qy, tick, seed ^ 0x9e3779b9);
  const dx = ((h1 & 0xffff) / 32767.5 - 1) * amp;
  const dy = ((h2 & 0xffff) / 32767.5 - 1) * amp;
  return [round1(x + dx), round1(y + dy)];
};

/**
 * Perturbs SVG path coordinates deterministically per `(x, y)` while preserving arc radii/flags (`A`/`a`)
 * and orthogonal command validity (`H`/`V`/`Z`). Never emits malformed path grammar.
 */
export const boilPathD = (d: string, tick: number, seed = 0, amp = 1.0): string => {
  const key = `${d}|${tick}|${seed}|${amp}`;
  const cached = boilPathCache.get(key);
  if (cached !== undefined) return cached;
  const tokens = d.match(/[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?/g);
  if (!tokens) return d;

  const isCmd = (s: string) => /^[a-zA-Z]$/.test(s);
  const out: string[] = [];
  let i = 0;
  let cmd = "";
  let cx = 0;
  let cy = 0;
  let sx = 0;
  let sy = 0;
  const readNum = () => parseFloat(tokens[i++]);
  const pushPt = (x: number, y: number) => {
    const [bx, by] = boilPoint(x, y, tick, seed, amp);
    out.push(String(bx), String(by));
  };

  while (i < tokens.length) {
    if (isCmd(tokens[i])) {
      cmd = tokens[i++];
      if (cmd === "Z" || cmd === "z") {
        out.push(cmd);
        cx = sx;
        cy = sy;
        continue;
      }
      out.push(cmd);
    }
    const upper = cmd.toUpperCase();
    const rel = cmd !== upper;
    let firstInM = cmd === "M" || cmd === "m";
    while (i < tokens.length && !isCmd(tokens[i])) {
      if (upper === "M" || upper === "L" || upper === "T") {
        if (i + 1 >= tokens.length) break;
        const x = readNum();
        const y = readNum();
        if (rel) {
          const tx = cx + x;
          const ty = cy + y;
          const [bx, by] = boilPoint(tx, ty, tick, seed, amp);
          const [bcx, bcy] = boilPoint(cx, cy, tick, seed, amp);
          out.push(String(round1(bx - bcx)), String(round1(by - bcy)));
          cx = tx;
          cy = ty;
        } else {
          cx = x;
          cy = y;
          pushPt(x, y);
        }
        if (firstInM) {
          sx = cx;
          sy = cy;
          firstInM = false;
          cmd = rel ? "l" : "L";
        }
      } else if (upper === "H") {
        const x = readNum();
        if (rel) {
          const tx = cx + x;
          const [bx] = boilPoint(tx, cy, tick, seed, amp);
          const [bcx] = boilPoint(cx, cy, tick, seed, amp);
          out.push(String(round1(bx - bcx)));
          cx = tx;
        } else {
          cx = x;
          out.push(String(boilPoint(x, cy, tick, seed, amp)[0]));
        }
      } else if (upper === "V") {
        const y = readNum();
        if (rel) {
          const ty = cy + y;
          const [, by] = boilPoint(cx, ty, tick, seed, amp);
          const [, bcy] = boilPoint(cx, cy, tick, seed, amp);
          out.push(String(round1(by - bcy)));
          cy = ty;
        } else {
          cy = y;
          out.push(String(boilPoint(cx, y, tick, seed, amp)[1]));
        }
      } else if (upper === "C") {
        if (i + 5 >= tokens.length) break;
        const coords = [readNum(), readNum(), readNum(), readNum(), readNum(), readNum()];
        if (rel) {
          const [bcx, bcy] = boilPoint(cx, cy, tick, seed, amp);
          for (let k = 0; k < 6; k += 2) {
            const [bx, by] = boilPoint(cx + coords[k], cy + coords[k + 1], tick, seed, amp);
            out.push(String(round1(bx - bcx)), String(round1(by - bcy)));
          }
          cx += coords[4];
          cy += coords[5];
        } else {
          for (let k = 0; k < 6; k += 2) pushPt(coords[k], coords[k + 1]);
          cx = coords[4];
          cy = coords[5];
        }
      } else if (upper === "S" || upper === "Q") {
        if (i + 3 >= tokens.length) break;
        const coords = [readNum(), readNum(), readNum(), readNum()];
        if (rel) {
          const [bcx, bcy] = boilPoint(cx, cy, tick, seed, amp);
          for (let k = 0; k < 4; k += 2) {
            const [bx, by] = boilPoint(cx + coords[k], cy + coords[k + 1], tick, seed, amp);
            out.push(String(round1(bx - bcx)), String(round1(by - bcy)));
          }
          cx += coords[2];
          cy += coords[3];
        } else {
          for (let k = 0; k < 4; k += 2) pushPt(coords[k], coords[k + 1]);
          cx = coords[2];
          cy = coords[3];
        }
      } else if (upper === "A") {
        if (i + 6 >= tokens.length) break;
        const rx = tokens[i++];
        const ry = tokens[i++];
        const rot = tokens[i++];
        const la = tokens[i++];
        const sw = tokens[i++];
        const x = readNum();
        const y = readNum();
        out.push(rx, ry, rot, la, sw);
        if (rel) {
          const tx = cx + x;
          const ty = cy + y;
          const [bx, by] = boilPoint(tx, ty, tick, seed, amp);
          const [bcx, bcy] = boilPoint(cx, cy, tick, seed, amp);
          out.push(String(round1(bx - bcx)), String(round1(by - bcy)));
          cx = tx;
          cy = ty;
        } else {
          cx = x;
          cy = y;
          pushPt(x, y);
        }
      } else {
        out.push(tokens[i++]);
      }
    }
  }
  const result = out.join(" ");
  boilPathCache.set(key, result);
  return result;
};

/**
 * Standard quadratic midpoint closed SVG contour from perfect-freehand polygon points
 * (M ... Q ... Z), rounding coordinates to 1 decimal place cleanly. If < 3 points, returns "".
 */
export const svgPathFromStroke = (stroke: number[][]): string => {
  if (stroke.length < 3) return "";
  const r = (val: number): number => {
    const n = Math.round(val * 10) / 10;
    return n === 0 ? 0 : n;
  };
  const p0 = stroke[0];
  const acc: (string | number)[] = ["M", r(p0[0]), r(p0[1]), "Q"];
  const len = stroke.length;
  for (let i = 0; i < len; i++) {
    const [x0, y0] = stroke[i];
    const [x1, y1] = stroke[(i + 1) % len];
    acc.push(r(x0), r(y0), r((x0 + x1) / 2), r((y0 + y1) / 2));
  }
  acc.push("Z");
  return acc.join(" ");
};

/**
 * Returns true ONLY when:
 * - attrs.d is a string containing at least one SVG curve command [CQSTAcqsta]
 * - attrs.stroke is truthy and not "none"
 * - fill is absent or "none"
 * - single subpath (at most one M/m command)
 */
export const isCurvedStroke = (attrs: Record<string, string>): boolean => {
  if (typeof attrs.d !== "string") return false;
  if (!/[CQSTAcqsta]/.test(attrs.d)) return false;
  if (!attrs.stroke || attrs.stroke === "none") return false;
  if (attrs.fill && attrs.fill !== "none") return false;
  if ((attrs.d.match(/[Mm]/g) ?? []).length > 1) return false;
  return true;
};

/**
 * Generates a tapered brush-pen stroke outline path for curved strokes.
 * Pure & deterministic!
 */
export const taperedOutline = (
  d: string,
  strokeWidth: number,
  progress = 1,
  boilTick?: number,
  boilSeed = 0,
): string | null => {
  const p = Math.max(0, Math.min(1, progress));
  if (p <= 0.01) return "";

  const cacheKey = `${d}|${strokeWidth}${boilTick !== undefined ? `|b${boilTick}|${boilSeed}` : ""}`;
  if (p >= 0.999) {
    const cached = settledSvgCache.get(cacheKey);
    if (cached !== undefined) return cached;
  }

  const isClosed = /[Zz]\s*$/.test(d.trim());

  let pts = sampledPointsCache.get(d);
  if (!pts) {
    try {
      const len = getLength(d);
      if (!Number.isFinite(len) || len <= 1) return null;

      const steps = Math.min(96, Math.max(20, Math.round(len / 4)));
      const points: number[][] = [];
      for (let k = 0; k <= steps; k++) {
        const pt = getPointAtLength(d, (len * k) / steps);
        if (!pt) continue;
        const t = k / steps;
        const pressure = isClosed
          ? 0.6 + 0.35 * Math.sin(Math.PI * t)
          : 0.45 + 0.55 * Math.sin(Math.PI * t);
        points.push([pt.x, pt.y, pressure]);
      }
      if (points.length < 2) return null;
      pts = points;
      sampledPointsCache.set(d, pts);
    } catch {
      return null;
    }
  }

  const rawSlice = p >= 0.999 ? pts : pts.slice(0, Math.max(2, Math.ceil(pts.length * p)));
  const slice = boilTick !== undefined
    ? rawSlice.map(([x, y, pr]) => {
        const [bx, by] = boilPoint(x, y, boilTick, boilSeed, 1.0);
        return [bx, by, pr];
      })
    : rawSlice;
  if (slice.length < 2) return null;

  try {
    const stroke = getStroke(slice, {
      size: strokeWidth * 1.25,
      thinning: 0.45,
      smoothing: 0.5,
      streamline: 0.45,
      simulatePressure: false,
      last: p >= 0.999,
      start: { taper: !isClosed && strokeWidth * 1.4 },
      end: { taper: (!isClosed || p < 0.999) ? strokeWidth * 1.4 : 0 },
    });

    const path = svgPathFromStroke(stroke);
    if (!path) return null;

    if (p >= 0.999) {
      settledSvgCache.set(cacheKey, path);
    }
    return path;
  } catch {
    return null;
  }
};
