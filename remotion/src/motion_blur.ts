export const BLUR_MIN = 0.3;
export const BLUR_CAP = 26;
export const VEL_MIN_PX = 2.0;
export const SCALE_VEL_MIN = 0.008;

/**
 * Directional blur standard deviations from frame velocity (dx, dy, dscale).
 * Bypasses tiny velocities below threshold, blends isotropic scale blur, and caps maximum blur.
 */
export function directionalBlur(vx: number, vy: number, vs = 0): { sx: number; sy: number } | null {
  const speed = Math.hypot(vx, vy);
  if (speed < VEL_MIN_PX && Math.abs(vs) < SCALE_VEL_MIN) {
    return null;
  }
  const iso = Math.abs(vs) * 220;
  const sx = Math.min(BLUR_CAP, Math.round((Math.abs(vx) * 0.22 + iso) * 100) / 100);
  const sy = Math.min(BLUR_CAP, Math.round((Math.abs(vy) * 0.22 + iso) * 100) / 100);
  if (sx < BLUR_MIN && sy < BLUR_MIN) {
    return null;
  }
  return { sx, sy };
}
