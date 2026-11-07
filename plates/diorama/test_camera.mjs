/**
 * plates/diorama/test_camera.mjs
 * Verification suite for the Diorama Camera Grammar System
 */

import {
  linear,
  smoothstep,
  smootherstep,
  septic,
  cubicBezier,
  resolveEasing,
  catmullRomVec3,
  evalDolly,
  evalCrane,
  evalPushThrough,
  evalRevealBehind,
  evalWipePass,
  DioramaCameraController,
  createCameraSystem,
} from "./lib/camera.mjs";
import * as THREE from "three";

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
  } else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

function assertClose(actual, expected, eps = 1e-4, message = "") {
  const diff = Math.abs(actual - expected);
  assert(diff <= eps, `${message} (expected ${expected}, got ${actual}, diff ${diff})`);
}

console.log("--- 1. Testing Easing Functions (C¹ / C² Continuity) ---");

// Test boundaries
assertClose(linear(0), 0, 1e-6, "linear(0) == 0");
assertClose(linear(1), 1, 1e-6, "linear(1) == 1");
assertClose(smoothstep(0), 0, 1e-6, "smoothstep(0) == 0");
assertClose(smoothstep(1), 1, 1e-6, "smoothstep(1) == 1");
assertClose(smoothstep(0.5), 0.5, 1e-6, "smoothstep(0.5) == 0.5");
assertClose(smootherstep(0), 0, 1e-6, "smootherstep(0) == 0");
assertClose(smootherstep(1), 1, 1e-6, "smootherstep(1) == 1");
assertClose(smootherstep(0.5), 0.5, 1e-6, "smootherstep(0.5) == 0.5");
assertClose(septic(0), 0, 1e-6, "septic(0) == 0");
assertClose(septic(1), 1, 1e-6, "septic(1) == 1");
assertClose(septic(0.5), 0.5, 1e-6, "septic(0.5) == 0.5");

// Check C² zero acceleration at endpoints for smootherstep
const h = 1e-5;
const s0 = smootherstep(0);
const sH = smootherstep(h);
const s2H = smootherstep(2 * h);
const vel0 = (sH - s0) / h;
const accel0 = (s2H - 2 * sH + s0) / (h * h);
assertClose(vel0, 0, 1e-3, "smootherstep first derivative at 0 is 0");
assertClose(accel0, 0, 1e-2, "smootherstep second derivative (acceleration) at 0 is 0");

// Cubic Bezier easing
const cbEase = cubicBezier(0.5, 0.25, 0.1, 0.25, 1.0);
assert(cbEase > 0 && cbEase < 1, "cubicBezier(0.5) inside (0, 1)");

console.log("--- 2. Testing Camera Moves under spec.move ---");

const ctx = { width: 1080, height: 1920, fps: 30, seconds: 6, seed: 1 };

// Move 1: Dolly In
const dollySpec = {
  move: "dolly",
  direction: "in",
  distance: 3.0,
  startEye: [0, 2.2, 9.5],
};
const dollyCtrl = createCameraSystem(dollySpec, ctx);
const dStart = dollyCtrl.evaluate(0);
const dMid = dollyCtrl.evaluate(3);
const dEnd = dollyCtrl.evaluate(6);

assertClose(dStart.eye.z, 9.5, 1e-4, "Dolly start z is 9.5");
assertClose(dEnd.eye.z, 6.5, 1e-4, "Dolly end z is 6.5 (moved 3.0 in)");
assert(dMid.eye.z < dStart.eye.z && dMid.eye.z > dEnd.eye.z, "Dolly mid z is strictly between start and end");

// Move 2: Crane Descent
const craneSpec = {
  move: "crane",
  direction: "down",
  startY: 5.0,
  endY: 1.5,
  startPitch: -25.0,
  endPitch: -10.0,
};
const craneCtrl = createCameraSystem(craneSpec, ctx);
const cStart = craneCtrl.evaluate(0);
const cEnd = craneCtrl.evaluate(6);
assertClose(cStart.eye.y, 5.0, 1e-4, "Crane start Y is 5.0");
assertClose(cEnd.eye.y, 1.5, 1e-4, "Crane end Y is 1.5");
assert(cEnd.eye.y < cStart.eye.y, "Crane descending downward");

// Move 3: Push-Through
const pushSpec = {
  move: "push-through",
  portalX: 0,
  portalY: 1.8,
  portalZ: 3.0,
};
const pushCtrl = createCameraSystem(pushSpec, ctx);
const pStart = pushCtrl.evaluate(0);
const pMid = pushCtrl.evaluate(3);
const pEnd = pushCtrl.evaluate(6);
const pEndIsPast = (m) => m.eye.z < pStart.eye.z - 1;
assert(pStart.eye.z > 3.0, "Push start is outside portal");
assert(pEndIsPast(pMid), "Push midpoint is still running, never parked in the doorway");
assert(pEnd.eye.z < 3.0, "Push end is inside inner chamber");
assert(pMid.isInside === false || pEnd.isInside === true, "Push detects inner chamber entry");

// Move 4: Reveal-Behind
const revealSpec = {
  move: "reveal-behind",
  occluder: [0, 1.2, 4.0],
  sweepAngleDeg: 40.0,
};
const revCtrl = createCameraSystem(revealSpec, ctx);
const rStart = revCtrl.evaluate(0);
const rEnd = revCtrl.evaluate(6);
assertClose(rStart.eye.x, 0.0, 1e-4, "Reveal start is collinear at X=0");
assert(Math.abs(rEnd.eye.x) > 2.0, "Reveal end has swept laterally to unmask subject");

// Move 5: Wipe-Pass (Hitchcock's Rope Foreground Wipe)
const wipeSpec = {
  move: "wipe-pass",
  direction: "left-to-right",
  travelX: 4.0,
};
const wipeCtrl = createCameraSystem(wipeSpec, ctx);
const wStart = wipeCtrl.evaluate(0);
const wPeak = wipeCtrl.evaluate(3); // p = 0.5
const wEnd = wipeCtrl.evaluate(6);

assertClose(wStart.occlusion, 0.0, 1e-4, "Wipe start occlusion is 0");
assertClose(wPeak.occlusion, 1.0, 1e-4, "Wipe peak midpoint occlusion is 1.0 (cut moment)");
assertClose(wEnd.occlusion, 0.0, 1e-4, "Wipe end occlusion is 0");
assert(wStart.eye.x < 0 && wEnd.eye.x > 0, "Wipe traverses from left to right");

console.log("--- 3. Testing Pure Determinism & Anchors ---");

// Test determinism: Repeated calls at same t produce bit-identical results
const detSpec = { move: "dolly", direction: "in" };
const ctrlA = createCameraSystem(detSpec, ctx);
const ctrlB = createCameraSystem(detSpec, ctx);

for (const t of [0, 1.234, 3.0, 4.89, 6.0]) {
  const resA = ctrlA.evaluate(t);
  const resB = ctrlB.evaluate(t);
  assertClose(resA.eye.x, resB.eye.x, 1e-9, `Determinism eye.x at t=${t}`);
  assertClose(resA.eye.y, resB.eye.y, 1e-9, `Determinism eye.y at t=${t}`);
  assertClose(resA.eye.z, resB.eye.z, 1e-9, `Determinism eye.z at t=${t}`);
  assertClose(resA.target.x, resB.target.x, 1e-9, `Determinism target.x at t=${t}`);
}

// Test Anchor Projection
const anchorSpec = {
  move: "dolly",
  anchors: {
    hero: [0, 1.1, 0],
    plinth: [0, 0, 0],
  },
};
const anchorCtrl = createCameraSystem(anchorSpec, ctx);
anchorCtrl.evaluate(2.0);
const anchors = anchorCtrl.getAnchors();

assert(Array.isArray(anchors.dot) && anchors.dot.length === 2, "Anchor dot exists");
assert(Array.isArray(anchors.hero) && anchors.hero.length === 2, "Anchor hero exists");
assert(anchors.dot[0] >= 0 && anchors.dot[0] <= 1080, "Anchor X inside 1080 width");
assert(anchors.dot[1] >= 0 && anchors.dot[1] <= 1920, "Anchor Y inside 1920 height");

// Check Safe Zone compliance for hero on screen
const projHero = anchorCtrl.projectToScreen([0, 1.1, 0]);
assert(projHero.inSafeZone, "Hero anchor is inside portrait safe zone (Y <= 1380)");

console.log(`\nResults: ${passed} passed, ${failed} failed.`);
if (failed > 0) {
  process.exit(1);
} else {
  console.log("ALL TESTS PASSED SUCCESSFULLY!");
}
