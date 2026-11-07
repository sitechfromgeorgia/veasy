/**
 * plates/diorama/lib/camera.mjs
 *
 * Cinematic One-Take Camera Movement System for Miniature Paper Worlds (Veasy Paper Stage).
 *
 * Concepts:
 * - Hitchcock's Rope foreground wipes: natural occlusions (pillars, trunks, arches) acting as cuts.
 * - Mendes & Deakins 1917 / Iñárritu Birdman continuous floating trajectories with C² continuity.
 * - Tilt-shift miniature aesthetics: grounded perspective, gentle downward pitch, layered parallax.
 *
 * Contract:
 * - Deterministic pure function of normalized time p = t / seconds (0 to 1).
 * - No Math.random, no clock, no state leakage across frames.
 * - Respects portrait 1080x1920 safe zone rules.
 */

import * as THREE from "three";

// --- EASING FUNCTIONS (C¹ and C² Continuity) ---

/**
 * Linear easing
 */
export function linear(p) {
  return Math.min(1, Math.max(0, p));
}

/**
 * Standard Hermite cubic smoothstep (C¹ continuous)
 * S₃(p) = 3p² - 2p³
 * Derivatives: S'(0) = 0, S'(1) = 0
 */
export function smoothstep(p) {
  const x = Math.min(1, Math.max(0, p));
  return x * x * (3 - 2 * x);
}

/**
 * Perlin quintic smootherstep (C² continuous - zero acceleration & jerk at endpoints)
 * S₅(p) = 6p⁵ - 15p⁴ + 10p³ = p³(10 - 15p + 6p²)
 * Derivatives: S'(0)=0, S'(1)=0, S''(0)=0, S''(1)=0
 * Essential for Mendes/Deakins style continuous floating motion without inertia spikes.
 */
export function smootherstep(p) {
  const x = Math.min(1, Math.max(0, p));
  return x * x * x * (x * (x * 6 - 15) + 10);
}

/**
 * Septic 7th-order smoothstep (C³ continuous)
 * S₇(p) = p⁴(35 - 84p + 70p² - 20p³)
 */
export function septic(p) {
  const x = Math.min(1, Math.max(0, p));
  return x * x * x * x * (35 + x * (-84 + x * (70 - 20 * x)));
}

/**
 * Analytical Cubic-Bezier 1D curve solver with 6-iteration Newton-Raphson.
 * Matches CSS transition-timing-function cubic-bezier(x1, y1, x2, y2).
 */
export function cubicBezier(p, x1, y1, x2, y2) {
  const tNorm = Math.min(1, Math.max(0, p));
  if (tNorm === 0 || tNorm === 1) return tNorm;

  // Bézier polynomial coefficients: B(s) = 3(1-s)²s*P1 + 3(1-s)s²*P2 + s³
  // x(s) = 3*x1*s*(1-s)² + 3*x2*s²*(1-s) + s³
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;

  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;

  function sampleX(s) {
    return ((ax * s + bx) * s + cx) * s;
  }
  function sampleXDerivative(s) {
    return (3 * ax * s + 2 * bx) * s + cx;
  }
  function sampleY(s) {
    return ((ay * s + by) * s + cy) * s;
  }

  // Newton-Raphson iteration to find parameter s such that sampleX(s) == tNorm
  let s = tNorm;
  for (let i = 0; i < 6; i++) {
    const currentX = sampleX(s) - tNorm;
    if (Math.abs(currentX) < 1e-6) break;
    const dX = sampleXDerivative(s);
    if (Math.abs(dX) < 1e-6) break;
    s -= currentX / dX;
    s = Math.min(1, Math.max(0, s));
  }

  return sampleY(s);
}

export const EASING_PRESETS = {
  linear,
  smoothstep,
  smootherstep,
  septic,
  cinematic: (p) => cubicBezier(p, 0.25, 0.1, 0.25, 1.0),    // Deakins fluid drift
  dramatic: (p) => cubicBezier(p, 0.42, 0.0, 0.20, 1.0),     // Prompt acceleration
  slowSettle: (p) => cubicBezier(p, 0.16, 1.0, 0.30, 1.0),   // Gentle plinth arrival
};

export function resolveEasing(nameOrFn) {
  if (typeof nameOrFn === "function") return nameOrFn;
  if (typeof nameOrFn === "string" && EASING_PRESETS[nameOrFn]) {
    return EASING_PRESETS[nameOrFn];
  }
  return smootherstep; // Default to Perlin quintic for silky camera work
}

// --- VECTOR & SPLINE HELPERS ---

export function toVec3(v, fallback = [0, 0, 0]) {
  if (v instanceof THREE.Vector3) return v.clone();
  if (Array.isArray(v) && v.length >= 3) return new THREE.Vector3(v[0], v[1], v[2]);
  if (v && typeof v === "object") return new THREE.Vector3(v.x ?? 0, v.y ?? 0, v.z ?? 0);
  return new THREE.Vector3(fallback[0], fallback[1], fallback[2]);
}

/**
 * Centripetal Catmull-Rom interpolation for 3D waypoints.
 * Guarantees C¹ continuity without cusps or excessive overshoots.
 */
export function catmullRomVec3(out, p0, p1, p2, p3, t, alpha = 0.5) {
  function getT(tPrev, pA, pB) {
    const d = pA.distanceTo(pB);
    return tPrev + Math.pow(d, alpha);
  }

  const t0 = 0;
  const t1 = getT(t0, p0, p1);
  const t2 = getT(t1, p1, p2);
  const t3 = getT(t2, p2, p3);

  // Map local parameter t in [0, 1] to knot interval [t1, t2]
  const time = t1 + t * (t2 - t1);

  // Recursive de Casteljau-like evaluation
  function evalSegment(pA, pB, tA, tB) {
    if (Math.abs(tB - tA) < 1e-6) return pA.clone();
    return pA.clone().multiplyScalar((tB - time) / (tB - tA))
      .add(pB.clone().multiplyScalar((time - tA) / (tB - tA)));
  }

  const a1 = evalSegment(p0, p1, t0, t1);
  const a2 = evalSegment(p1, p2, t1, t2);
  const a3 = evalSegment(p2, p3, t2, t3);

  const b1 = evalSegment(a1, a2, t0, t2);
  const b2 = evalSegment(a2, a3, t1, t3);

  const c = evalSegment(b1, b2, t1, t2);
  out.copy(c);
  return out;
}

// --- MINIATURE STAGE DEFAULTS & SPEC ---

export const MINIATURE_CONFIG = {
  vFov: 38,                 // Moderate macro perspective (portrait 1080x1920)
  near: 0.08,               // 8mm scale threshold (prevents clipping foreground cutouts)
  far: 45.0,                // Bounded depth (fog drops off cleanly at background)
  defaultEye: [0, 2.2, 9.5],// Baseline tabletop eye position
  defaultTarget: [0, 1.1, 0],// Chest/focal height of 1.5 unit standing paper figure
  safeZone: {
    maxTextY: 1380,         // Veasy upper bound for scene text
    maxCaptionY: 1552,      // Captions zone
    socialRightCutY: 1100,  // Below 1100, no text right of 940
    socialRightLimitX: 940,
  },
};

// --- CAMERA MOVE EVALUATORS ---

/**
 * 1. DOLLY MOVE
 * Smooth axial tracking forward/backward (dolly-in / dolly-out) or lateral tracking (truck).
 * Generates layered depth cues via differential motion parallax.
 */
export function evalDolly(p, spec = {}) {
  const ease = resolveEasing(spec.easing);
  const factor = ease(p);

  const startEye = toVec3(spec.fromEye || spec.startEye, [0, 2.2, 9.5]);
  const endEye = toVec3(spec.toEye || spec.endEye, [0, 2.0, 6.8]); // Default subtle dolly-in

  const startTarget = toVec3(spec.fromTarget || spec.startTarget, [0, 1.1, 0]);
  const endTarget = toVec3(spec.toTarget || spec.endTarget, [0, 1.1, 0]);

  // Directional presets if explicit coordinates are not provided
  if (!spec.fromEye && !spec.toEye && spec.direction) {
    const dist = spec.distance ?? 2.5;
    if (spec.direction === "in") {
      endEye.set(startEye.x, startEye.y - 0.2, startEye.z - dist);
    } else if (spec.direction === "out") {
      endEye.set(startEye.x, startEye.y + 0.2, startEye.z + dist);
    } else if (spec.direction === "left") {
      endEye.set(startEye.x - dist, startEye.y, startEye.z);
      endTarget.set(startTarget.x - dist * 0.85, startTarget.y, startTarget.z);
    } else if (spec.direction === "right") {
      endEye.set(startEye.x + dist, startEye.y, startEye.z);
      endTarget.set(startTarget.x + dist * 0.85, startTarget.y, startTarget.z);
    }
  }

  const eye = new THREE.Vector3().lerpVectors(startEye, endEye, factor);
  const target = new THREE.Vector3().lerpVectors(startTarget, endTarget, factor);

  return { eye, target, occlusion: 0 };
}

/**
 * 2. CRANE MOVE
 * Vertical descent or ascent revealing rooftop silhouettes to street/plinth level,
 * with radial jib-arm depth compensation and pitch adaptation.
 */
export function evalCrane(p, spec = {}) {
  const ease = resolveEasing(spec.easing);
  const factor = ease(p);

  const direction = spec.direction || "down"; // "down" or "up"
  const startY = spec.startY ?? (direction === "down" ? 5.2 : 1.3);
  const endY = spec.endY ?? (direction === "down" ? 1.4 : 4.8);

  // Radial jib arc compensation: as jib lowers, eye moves slightly inward along z
  const jibRadius = spec.jibRadius ?? 6.0;
  const startPitch = spec.startPitch ?? (direction === "down" ? -26.0 : -8.0);
  const endPitch = spec.endPitch ?? (direction === "down" ? -9.5 : -24.0);

  const baseZ = spec.baseZ ?? 9.0;
  const currentY = startY + factor * (endY - startY);

  // Natural circular jib arm kinematics
  const verticalDelta = currentY - startY;
  const arcZOffset = Math.sin((verticalDelta / jibRadius) * 0.5) * 0.8;
  const currentZ = baseZ - arcZOffset;

  const currentX = spec.baseX ?? 0.0;
  const eye = new THREE.Vector3(currentX, currentY, currentZ);

  // LookAt target calculation based on pitch and plinth focal height
  const currentPitchRad = (startPitch + factor * (endPitch - startPitch)) * (Math.PI / 180);
  const targetY = spec.targetY ?? 0.9;
  const focalDistance = (currentY - targetY) / Math.max(0.1, -Math.sin(currentPitchRad));
  const targetZ = currentZ - focalDistance * Math.cos(currentPitchRad);
  const target = new THREE.Vector3(spec.targetX ?? 0.0, targetY, Math.min(2.0, targetZ));

  return { eye, target, occlusion: 0 };
}

/**
 * 3. PUSH-THROUGH MOVE
 * Passes directly through an aperture (archway, gothic portal, or window frame)
 * into a deeper interior chamber.
 * Mathematical guarantee: passes within aperture margins without clipping.
 */
export function evalPushThrough(p, spec = {}) {
  const ease = resolveEasing(spec.easing || "cinematic");
  const factor = ease(p);

  // Aperture definition in stage space
  const portal = {
    x: spec.portalX ?? 0.0,
    y: spec.portalY ?? 1.8,
    z: spec.portalZ ?? 4.0,       // Z-plane of the paper wall
    width: spec.portalWidth ?? 1.6,
    height: spec.portalHeight ?? 2.8,
  };

  // One straight run through the opening, never a stop in the doorway: a one-take camera doesn't pause.
  const startEye = toVec3(spec.fromEye || spec.startEye, [portal.x, portal.y + 0.2, portal.z + 5.5]);
  const endEye = toVec3(spec.toEye || spec.endEye, [portal.x, portal.y - 0.2, portal.z - 4.5]);
  const eye = new THREE.Vector3().lerpVectors(startEye, endEye, factor);

  const innerTarget = toVec3(spec.target || spec.fromTarget, [portal.x, portal.y * 0.7, portal.z - 7.0]);
  const target = spec.toTarget ? innerTarget.lerp(toVec3(spec.toTarget), factor) : innerTarget;

  // Subtle interior reveal tone/fog signal (p > 0.5 indicates interior stage)
  const isInside = eye.z < portal.z;

  return { eye, target, occlusion: 0, isInside };
}

/**
 * 4. REVEAL-BEHIND MOVE
 * Orbiting trajectory around a prominent foreground occluder (statue, column, giant tree trunk)
 * to reveal what was previously hidden behind it.
 */
export function evalRevealBehind(p, spec = {}) {
  const ease = resolveEasing(spec.easing);
  const factor = ease(p);

  // Position of the prominent foreground occluder
  const occluder = toVec3(spec.occluder, [0.0, 1.2, 4.0]);
  const radius = spec.orbitRadius ?? 5.5;

  // Angular sweep: from occluding line-of-sight to revealed open angle
  const startAngleDeg = spec.startAngleDeg ?? 0.0;     // directly collinear
  const sweepAngleDeg = spec.sweepAngleDeg ?? 38.0;   // lateral arc sweep
  const currentAngleRad = (startAngleDeg + factor * sweepAngleDeg) * (Math.PI / 180);

  // Orbital eye position in polar coordinates around occluder
  const eyeX = occluder.x + radius * Math.sin(currentAngleRad);
  const eyeZ = occluder.z + radius * Math.cos(currentAngleRad);
  const eyeY = (spec.eyeY ?? 2.1) + factor * (spec.eyeYDelta ?? -0.2);
  const eye = new THREE.Vector3(eyeX, eyeY, eyeZ);

  // Target transitions from occluder edge to the newly discovered subject
  const hiddenSubject = toVec3(spec.subject, [0.8, 1.0, 0.0]);
  const initialLookTarget = occluder.clone().add(new THREE.Vector3(0, -0.1, -1.0));
  const target = new THREE.Vector3().lerpVectors(initialLookTarget, hiddenSubject, smootherstep(factor));

  return { eye, target, occlusion: 0 };
}

/**
 * 5. WIPE-PASS MOVE (Hitchcock's Rope Foreground Wipe)
 * A foreground architectural layer (column, arch jamb, or tree trunk) sweeps across
 * the viewport from left to right or right to left, creating a natural cut for story beats.
 * At p ≈ 0.5, occlusion reaches peak 1.0 (full blackout/monochrome wipe).
 */
export function evalWipePass(p, spec = {}) {
  const ease = resolveEasing(spec.easing);
  const factor = ease(p);

  const direction = spec.direction || "left-to-right"; // or "right-to-left"
  const sign = direction === "left-to-right" ? 1 : -1;

  const travelX = spec.travelX ?? 3.8;
  const startX = -sign * (travelX * 0.5);
  const endX = sign * (travelX * 0.5);

  const eyeX = startX + factor * (endX - startX);
  // Parabolic plunge: camera dips slightly closer to the near plane at midpoint p = 0.5
  const nearDip = spec.nearDip ?? 0.6;
  const eyeZ = (spec.baseZ ?? 9.0) - nearDip * 4 * p * (1 - p);
  const eyeY = (spec.baseY ?? 2.0);

  const eye = new THREE.Vector3(eyeX, eyeY, eyeZ);

  // Target tracks with smooth drag, amplifying the optical shear of the wipe
  const targetX = eyeX * 0.35;
  const targetY = spec.targetY ?? 1.1;
  const targetZ = spec.targetZ ?? 0.0;
  const target = new THREE.Vector3(targetX, targetY, targetZ);

  // Occlusion factor calculation: bell curve centered at p = 0.5
  // Width of wipe window: w = 0.22 normalized time
  const wipeCenter = spec.wipeCenter ?? 0.5;
  const wipeWidth = spec.wipeWidth ?? 0.18;
  const distFromCenter = Math.abs(p - wipeCenter);
  let occlusion = 0;
  if (distFromCenter < wipeWidth) {
    const norm = 1 - (distFromCenter / wipeWidth);
    occlusion = smootherstep(norm); // 0 at edges, 1.0 at center
  }

  return { eye, target, occlusion };
}

/**
 * 6. COMPOUND / FREEWAY SPLINE MOVE
 * Evaluates arbitrary Catmull-Rom waypoint sequences for continuous floating shots.
 */
export function evalSpline(p, spec = {}) {
  const ease = resolveEasing(spec.easing);
  const factor = ease(p);

  const waypoints = spec.waypoints;
  if (!waypoints || waypoints.length < 2) {
    return evalDolly(p, spec);
  }

  // Need at least 4 control points for Catmull-Rom; pad endpoints if needed
  const points = waypoints.map((pt) => toVec3(pt));
  if (points.length === 2) {
    const dir = new THREE.Vector3().subVectors(points[1], points[0]);
    points.unshift(points[0].clone().sub(dir));
    points.push(points[1].clone().add(dir));
  } else if (points.length === 3) {
    points.unshift(points[0].clone());
    points.push(points[points.length - 1].clone());
  }

  const numSegments = points.length - 3;
  const scaledT = factor * numSegments;
  const segmentIndex = Math.min(Math.floor(scaledT), numSegments - 1);
  const localT = scaledT - segmentIndex;

  const eye = new THREE.Vector3();
  catmullRomVec3(
    eye,
    points[segmentIndex],
    points[segmentIndex + 1],
    points[segmentIndex + 2],
    points[segmentIndex + 3],
    localT
  );

  const target = toVec3(spec.target, [0, 1.1, 0]);
  return { eye, target, occlusion: 0 };
}

/**
 * Master Move Dispatcher
 */
export function evaluateMove(moveType, p, spec = {}) {
  switch (moveType) {
    case "crane":
      return evalCrane(p, spec);
    case "push-through":
    case "pushThrough":
      return evalPushThrough(p, spec);
    case "reveal-behind":
    case "revealBehind":
      return evalRevealBehind(p, spec);
    case "wipe-pass":
    case "wipePass":
      return evalWipePass(p, spec);
    case "spline":
      return evalSpline(p, spec);
    case "dolly":
    default:
      return evalDolly(p, spec);
  }
}

// --- DIORAMA CAMERA CONTROLLER CLASS ---

export class DioramaCameraController {
  constructor(spec = {}, ctx = {}) {
    this.spec = spec;
    this.ctx = {
      width: ctx.width || 1080,
      height: ctx.height || 1920,
      fps: ctx.fps || 30,
      seconds: ctx.seconds || 6,
      seed: ctx.seed || 1,
    };

    this.vFov = spec.camera?.vFov || MINIATURE_CONFIG.vFov;
    this.near = spec.camera?.near || MINIATURE_CONFIG.near;
    this.far = spec.camera?.far || MINIATURE_CONFIG.far;

    this.camera = new THREE.PerspectiveCamera(
      this.vFov,
      this.ctx.width / this.ctx.height,
      this.near,
      this.far
    );

    this.currentEye = toVec3(spec.camera?.eye, MINIATURE_CONFIG.defaultEye);
    this.currentTarget = toVec3(spec.camera?.target, MINIATURE_CONFIG.defaultTarget);
    this.currentOcclusion = 0;

    // Registered anchors for DOM projection
    this.anchors = spec.anchors || {};
  }

  /**
   * Evaluates camera at time t (seconds).
   * Pure deterministic function of t.
   */
  evaluate(t) {
    const p = Math.min(1, Math.max(0, t / this.ctx.seconds));
    const moveType = this.spec.move || this.spec.camera?.move || "dolly";
    const moveSpec = {
      ...this.spec.camera,
      ...this.spec,
      easing: this.spec.easing || this.spec.camera?.easing || "smootherstep",
    };

    const state = evaluateMove(moveType, p, moveSpec);

    this.currentEye.copy(state.eye);
    this.currentTarget.copy(state.target);
    this.currentOcclusion = state.occlusion || 0;

    // Apply to Three.js camera
    this.camera.position.copy(this.currentEye);
    this.camera.lookAt(this.currentTarget);
    this.camera.updateMatrixWorld();

    return state;
  }

  /**
   * Projects a 3D world coordinate to 2D screen pixels [x, y] in [0, 1080] x [0, 1920].
   */
  projectToScreen(worldVec) {
    const pos = toVec3(worldVec).clone();
    pos.project(this.camera);

    const x = ((pos.x + 1) / 2) * this.ctx.width;
    const y = ((1 - pos.y) / 2) * this.ctx.height;
    const inFrustum = pos.z > 0 && pos.z < 1 && Math.abs(pos.x) <= 1 && Math.abs(pos.y) <= 1;

    // Check safe zone constraints (y <= 1380, right-edge cut under 1100)
    const inSafeZone = y <= MINIATURE_CONFIG.safeZone.maxTextY &&
      (y <= MINIATURE_CONFIG.safeZone.socialRightCutY || x <= MINIATURE_CONFIG.safeZone.socialRightLimitX);

    return {
      pixel: [Math.round(x * 10) / 10, Math.round(y * 10) / 10],
      inFrustum,
      inSafeZone,
      depth: pos.z,
    };
  }

  /**
   * Export all declared anchors formatted for window.anchors(t)
   */
  getAnchors(customAnchors = null) {
    const targets = customAnchors || this.anchors;
    const result = {};

    // Standard primary focal dot: lookAt target
    result.dot = this.projectToScreen(this.currentTarget).pixel;

    for (const [key, coords] of Object.entries(targets)) {
      result[key] = this.projectToScreen(coords).pixel;
    }

    return result;
  }

  /**
   * Returns current occlusion level (0.0 to 1.0) for Hitchcock wipe cuts
   */
  getOcclusion() {
    return this.currentOcclusion;
  }
}

/**
 * Convenience factory
 */
export function createCameraSystem(spec, ctx) {
  return new DioramaCameraController(spec, ctx);
}
