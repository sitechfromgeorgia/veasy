import { getStroke } from "perfect-freehand";
import { getLength, getPointAtLength } from "@remotion/paths";

/** Cache sampled points [x, y, pressure][] per path d string. */
const sampledPointsCache = new Map<string, number[][]>();

/** Cache settled (progress >= 0.999) SVG path strings per `${d}|${strokeWidth}`. */
const settledSvgCache = new Map<string, string>();

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
export const taperedOutline = (d: string, strokeWidth: number, progress = 1): string | null => {
  const p = Math.max(0, Math.min(1, progress));
  if (p <= 0.01) return "";

  const cacheKey = `${d}|${strokeWidth}`;
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

  const slice = p >= 0.999 ? pts : pts.slice(0, Math.max(2, Math.ceil(pts.length * p)));
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
