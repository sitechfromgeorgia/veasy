// plates/matter/camera.mjs
// Choreographs camera positions, lookAt targets, and FOV for the 6 matter forms.
// Guarantees: smooth, deterministic, monotonic or eased motion, with zero erratic jumps.
// Optimized for vertical 1080x1920 (9:16) composition.

/**
 * Standard easing functions for deterministic cinematic interpolation.
 */
export function clamp01(x) {
  return x <= 0 ? 0 : x >= 1 ? 1 : x;
}

export function smoothstep(p) {
  const x = clamp01(p);
  return x * x * (3 - 2 * x);
}

export function smootherstep(p) {
  const x = clamp01(p);
  return x * x * x * (x * (x * 6 - 15) + 10);
}

export function easeInOutCubic(p) {
  const x = clamp01(p);
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

export function easeOutCubic(p) {
  const x = clamp01(p);
  return 1 - Math.pow(1 - x, 3);
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function lerp3(a, b, t) {
  return [
    a[0] + (b[0] - a[0]) * t,
    a[1] + (b[1] - a[1]) * t,
    a[2] + (b[2] - a[2]) * t
  ];
}

const DEFAULT_FOV = 38; // degrees, matching plates/example

/**
 * Normalizes scene bounds structure to ensure safe defaults.
 */
function normalizeBounds(bounds) {
  if (!bounds || !bounds.total) {
    return {
      centroid: [0, 1.2, 0],
      size: [4.0, 2.5, 4.0],
      min: [-2.0, 0, -2.0],
      max: [2.0, 2.5, 2.0],
      groups: {}
    };
  }
  const t = bounds.total;
  return {
    centroid: Array.isArray(t.centroid) ? t.centroid : [0, 1.2, 0],
    size: Array.isArray(t.size) ? t.size : [4.0, 2.5, 4.0],
    min: Array.isArray(t.min) ? t.min : [-2.0, 0, -2.0],
    max: Array.isArray(t.max) ? t.max : [2.0, 2.5, 2.0],
    groups: bounds.groups || {}
  };
}

/**
 * 1. FORM: pile
 * Starts at 3/4 high angle, gentle pull-back or subtle push to reveal total mass.
 */
function choreographPile(p, b, options) {
  const u = smoothstep(p);
  const cx = b.centroid[0], cy = b.centroid[1], cz = b.centroid[2];
  const maxHoriz = Math.max(b.size[0], b.size[2], 2.5);
  const height = Math.max(b.size[1], 1.2);

  // Vertical 9:16 frame requires ample distance for horizontal width
  const baseDist = Math.max(5.5, maxHoriz * 2.4 + height * 0.8 + 2.2);

  // 3/4 high angle: azimuth 32 deg, elevation 38 to 44 deg
  const startDist = baseDist * 0.88;
  const endDist = baseDist * 1.14;
  const dist = lerp(startDist, endDist, u);

  const azimuthRad = (32 * Math.PI) / 180;
  const elevRad = (lerp(38, 44, u) * Math.PI) / 180;

  const posX = cx + dist * Math.sin(azimuthRad) * Math.cos(elevRad);
  const posY = cy * 0.5 + dist * Math.sin(elevRad);
  const posZ = cz + dist * Math.cos(azimuthRad) * Math.cos(elevRad);

  const targetX = cx;
  const targetY = lerp(cy * 0.6, cy * 0.85, u);
  const targetZ = cz;

  return {
    position: [posX, posY, posZ],
    target: [targetX, targetY, targetZ],
    fov: options.fov || DEFAULT_FOV
  };
}

/**
 * 2. FORM: split
 * Macro framing focused on the dividing line, tracking the sliding share.
 */
function choreographSplit(p, b, options) {
  // Groups: main (0) and share (1)
  const gMain = b.groups.main || Object.values(b.groups)[0] || { centroid: [-0.8, 0.8, 0], max: [0, 1.5, 0] };
  const gShare = b.groups.share || Object.values(b.groups)[1] || { centroid: [0.8, 0.6, 0.5], max: [1.5, 1.2, 1.0] };

  // Seam is initially between main and share
  const seamX = (gMain.centroid[0] + gShare.centroid[0]) * 0.5;
  const seamY = Math.max(gMain.centroid[1], 0.8);
  const seamZ = (gMain.centroid[2] + gShare.centroid[2]) * 0.5;

  const u = smootherstep(p);

  // Macro start: focused on the dividing seam
  const macroDist = Math.max(8.5, b.size[0] * 1.6 + 4.0, b.size[2] * 1.6 + 4.0);
  const macroPos = [seamX + 0.4, seamY + 1.6 + macroDist * 0.25, macroDist];
  const macroTarget = [seamX, seamY * 0.9, seamZ];

  // Wide end: calibrated for 9:16 vertical framing of both shares
  const wideSpan = Math.max(b.size[0], Math.abs(gShare.centroid[0] - gMain.centroid[0]) + 1.5);
  const wideDist = Math.max(8.5, wideSpan * 3.2 + 2.5);

  const wideCentroidX = (gMain.centroid[0] + gShare.centroid[0]) * 0.5;
  const wideCentroidY = Math.max(gMain.centroid[1], gShare.centroid[1]) * 0.8;
  const wideCentroidZ = (gMain.centroid[2] + gShare.centroid[2]) * 0.5;

  const widePos = [wideCentroidX + 0.6, wideCentroidY + wideDist * 0.35, wideCentroidZ + wideDist * 0.85];
  const wideTarget = [wideCentroidX, wideCentroidY, wideCentroidZ];

  const pos = lerp3(macroPos, widePos, u);
  const target = lerp3(macroTarget, wideTarget, u);

  return {
    position: pos,
    target: target,
    fov: options.fov || DEFAULT_FOV
  };
}

/**
 * 3. FORM: too-tall
 * Starts at the base framing unit 0, smoothly cranes/tilts upward to climb the towering column.
 */
function choreographTooTall(p, b, options) {
  // The column does not fit the frame: start low and far, looking up at it running off the top, then climb it.
  const colHeight = Math.max(b.size[1], 8.0);
  const hold = 0.12; // a beat at the base so the viewer sees what is being climbed
  const u = smootherstep(clamp01((p - hold) / (1 - hold)));
  const width = Math.max(b.size[0], b.size[2], 1.0);
  const camZ = Math.max(9.0, width * 3.2 + 5.0);
  const startCamY = 1.4;
  const endCamY = colHeight - 3.0;
  const camY = lerp(startCamY, endCamY, u);
  const lookAhead = lerp(camZ * 0.55, 1.0, u); // looking up at the start, level at the summit
  const targetY = camY + lookAhead;
  const camX = 1.8 + 0.8 * Math.sin(Math.PI * u);
  return {
    position: [camX, camY, camZ],
    target: [0, targetY, 0],
    fov: options.fov || DEFAULT_FOV
  };
}

/**
 * 4. FORM: pour
 * Eye-level perspective with subtle vertical tracking as heap accumulates.
 */
function choreographPour(p, b, options) {
  const u = easeInOutCubic(p);
  const heapHeight = Math.max(b.size[1], 1.2);

  // Eye-level start: looking at the base landing zone
  const startPos = [0.0, 1.8, 7.5];
  const startTarget = [0.0, 0.6, 0.0];

  // Upward tracking end: camera gently tilts and tracks upward with heap growth
  const endPos = [0.3, 1.8 + heapHeight * 0.45, 7.8];
  const endTarget = [0.0, 0.6 + heapHeight * 0.6, 0.0];

  const pos = lerp3(startPos, endPos, u);
  const target = lerp3(startTarget, endTarget, u);

  return {
    position: pos,
    target: target,
    fov: options.fov || DEFAULT_FOV
  };
}

/**
 * 5. FORM: resort
 * High isometric angle showing the mark migration.
 */
function choreographResort(p, b, options) {
  const u = smoothstep(p);
  const arenaWidth = Math.max(b.size[0], 6.0);
  const baseDist = Math.max(8.5, arenaWidth * 1.35 + 2.5);

  // High isometric perspective: 56 degree elevation, azimuth ~32 deg
  const startElev = (54 * Math.PI) / 180;
  const endElev = (57 * Math.PI) / 180;
  const elev = lerp(startElev, endElev, u);

  const startAzimuth = (34 * Math.PI) / 180;
  const endAzimuth = (29 * Math.PI) / 180;
  const azimuth = lerp(startAzimuth, endAzimuth, u);

  const dist = baseDist;
  const posX = dist * Math.sin(azimuth) * Math.cos(elev);
  const posY = dist * Math.sin(elev);
  const posZ = dist * Math.cos(azimuth) * Math.cos(elev);

  const targetX = 0;
  const targetY = lerp(0.5, 0.7, u);
  const targetZ = 0;

  return {
    position: [posX, posY, posZ],
    target: [targetX, targetY, targetZ],
    fov: options.fov || DEFAULT_FOV
  };
}

/**
 * 6. FORM: versus
 * Centered perspective framing both piles equally.
 */
function choreographVersus(p, b, options) {
  const u = smoothstep(p);
  const totalSpan = Math.max(b.size[0], 4.0);
  const midY = Math.max(b.centroid[1], 0.8);

  // Centered along X = 0 symmetry divider
  // Distance calibrated so both piles fit inside vertical 9:16 frame width
  const baseDist = Math.max(8.5, totalSpan * 2.8 + 2.5);
  const dist = lerp(baseDist * 1.05, baseDist * 0.95, u); // subtle slow push-in

  const elevRad = (38 * Math.PI) / 180;
  const posX = 0.0;
  const posY = midY + dist * Math.sin(elevRad);
  const posZ = dist * Math.cos(elevRad);

  const targetX = 0.0;
  const targetY = lerp(midY * 0.75, midY * 0.95, u);
  const targetZ = 0.0;

  return {
    position: [posX, posY, posZ],
    target: [targetX, targetY, targetZ],
    fov: options.fov || DEFAULT_FOV
  };
}

/**
 * Evaluates camera position and lookAt target for a given form at time t.
 * @param {string} formName One of the 6 matter forms
 * @param {number} t Elapsed time in seconds
 * @param {number} [duration=6] Total plate duration in seconds
 * @param {object} [sceneBounds=null] Scene bounds from getFormGeometry
 * @param {object} [options={}] Additional camera options (e.g. fov)
 * @returns {{ position: [number, number, number], target: [number, number, number], fov: number }}
 */
export function getCameraFrame(formName, t, duration = 6, sceneBounds = null, options = {}) {
  const normForm = (formName || "pile").toLowerCase().trim();
  const safeDuration = duration > 0 ? duration : 6;
  const progress = clamp01(t / safeDuration);
  const bounds = normalizeBounds(sceneBounds);

  switch (normForm) {
    case "pile":
      return choreographPile(progress, bounds, options);
    case "split":
      return choreographSplit(progress, bounds, options);
    case "too-tall":
      return choreographTooTall(progress, bounds, options);
    case "pour":
      return choreographPour(progress, bounds, options);
    case "resort":
      return choreographResort(progress, bounds, options);
    case "versus":
      return choreographVersus(progress, bounds, options);
    default:
      return choreographPile(progress, bounds, options);
  }
}

/**
 * Creates a reusable camera choreography rig.
 * @param {string} formName Form name
 * @param {object} [sceneBounds=null] Bounds from getFormGeometry
 * @param {number} [duration=6] Duration in seconds
 * @param {object} [options={}] Options
 * @returns {object} Rig with evaluate(t) and updateCamera(camera, t)
 */
export function createCameraChoreography(formName, sceneBounds = null, duration = 6, options = {}) {
  const normForm = (formName || "pile").toLowerCase().trim();
  const bounds = normalizeBounds(sceneBounds);

  return {
    form: normForm,
    duration,
    bounds,
    options,

    evaluate(t) {
      return getCameraFrame(normForm, t, duration, bounds, options);
    },

    /**
     * Directly updates a THREE.PerspectiveCamera instance.
     * @param {object} camera THREE.PerspectiveCamera
     * @param {number} t Current elapsed time
     */
    updateCamera(camera, t) {
      const frame = this.evaluate(t);
      if (!camera) return frame;

      camera.position.set(frame.position[0], frame.position[1], frame.position[2]);
      if (typeof camera.lookAt === "function") {
        camera.lookAt(frame.target[0], frame.target[1], frame.target[2]);
      }
      if (typeof camera.updateMatrixWorld === "function") {
        camera.updateMatrixWorld(true);
      }
      return frame;
    }
  };
}
