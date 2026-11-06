/**
 * plates/diorama/test_anchors.mjs
 *
 * Verification suite for the 3D-to-2D Screen Coordinate Projection
 * and Anchor Exporter System (plates/diorama/lib/anchors.mjs).
 */

import * as THREE from "three";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  REFERENCE_WIDTH,
  REFERENCE_HEIGHT,
  DEFAULT_FPS,
  BOUNDS_MIN,
  BOUNDS_MAX,
  NDC_Z_MAX,
  SAFE_ZONE,
  toVector3,
  projectWorldToScreen,
  projectToReferenceScreen,
  AnchorDefinition,
  AnchorSystem,
  createAnchorSystem,
  setupWindowAnchors,
} from "./lib/anchors.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

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

function assertClose(actual, expected, eps = 1e-3, message = "") {
  const diff = Math.abs(actual - expected);
  assert(diff <= eps, `${message} (expected ${expected}, got ${actual}, diff ${diff})`);
}

console.log("=== 1. Testing Core Projection Mathematics ===");

// Setup standard perspective camera (portrait 1080x1920)
const camera = new THREE.PerspectiveCamera(38, REFERENCE_WIDTH / REFERENCE_HEIGHT, 0.1, 100);
camera.position.set(0, 0, 10);
camera.lookAt(0, 0, 0);
camera.updateMatrixWorld(true);

// Center point (0, 0, 0) directly on optical axis
const centerProj = projectWorldToScreen(new THREE.Vector3(0, 0, 0), camera, 1080, 1920);
assertClose(centerProj.u, 0.5, 1e-4, "Center point normalized u is 0.5");
assertClose(centerProj.v, 0.5, 1e-4, "Center point normalized v is 0.5");
assertClose(centerProj.x, 540.0, 0.1, "Center point pixel X is 540.0");
assertClose(centerProj.y, 960.0, 0.1, "Center point pixel Y is 960.0");
assert(centerProj.inFront, "Center point is in front of camera");
assert(centerProj.inBounds, "Center point is within bounds");
assert(centerProj.visible, "Center point is visible");

// Coordinates from array [x, y, z] and object {x, y, z}
const arrProj = projectWorldToScreen([0, 0, 0], camera, 1080, 1920);
assertClose(arrProj.x, 540.0, 0.1, "Array coordinate projects identical X");
assertClose(arrProj.y, 960.0, 0.1, "Array coordinate projects identical Y");

const objProj = projectWorldToScreen({ x: 0, y: 0, z: 0 }, camera, 1080, 1920);
assertClose(objProj.x, 540.0, 0.1, "Object coordinate projects identical X");
assertClose(objProj.y, 960.0, 0.1, "Object coordinate projects identical Y");

console.log("=== 2. Testing Frustum & Occlusion Checks ===");

// Point behind camera (Z = 15 when camera is at Z = 10 looking towards Z = 0)
const behindPoint = new THREE.Vector3(0, 0, 15);
const behindProj = projectWorldToScreen(behindPoint, camera, 1080, 1920);
assert(!behindProj.inFront, "Point behind camera has inFront = false");
assert(!behindProj.visible, "Point behind camera has visible = false");
assert(behindProj.ndc.z >= NDC_Z_MAX, `Point behind camera has ndc.z >= 1.0 (got ${behindProj.ndc.z})`);
assert(behindProj.cameraSpaceZ > 0, `Point behind camera has cameraSpaceZ > 0 (got ${behindProj.cameraSpaceZ})`);

// Point way beyond right edge (offscreen)
const offscreenRight = new THREE.Vector3(20, 0, 0);
const offscreenProj = projectWorldToScreen(offscreenRight, camera, 1080, 1920);
assert(offscreenProj.inFront, "Offscreen point is in front of camera");
assert(!offscreenProj.inBounds, "Offscreen point has inBounds = false");
assert(!offscreenProj.visible, "Offscreen point has visible = false");
assert(offscreenProj.u > BOUNDS_MAX, "Offscreen point normalized u exceeds BOUNDS_MAX (1.1)");

// Point within 10% bleed margin (e.g. u = 1.05)
// Screen edge is at tan(fov_x / 2) * distance
const bleedPoint = new THREE.Vector3(0, 3.6, 0);
const bleedProj = projectWorldToScreen(bleedPoint, camera, 1080, 1920);
assert(bleedProj.inBounds, "Point in 10% bleed margin is inBounds = true");

console.log("=== 3. Testing Scale Invariance (1080x1920 Reference Frame) ===");

const testPoint = new THREE.Vector3(0.5, 1.2, 0.0);

// Scale 1.0: Full 1080x1920
const projScale1 = projectWorldToScreen(testPoint, camera, 1080, 1920);
// Scale 0.5: Half 540x960
const projScaleHalf = projectWorldToScreen(testPoint, camera, 540, 960);
// Scale 2.0: Double 2160x3840
const projScaleDouble = projectWorldToScreen(testPoint, camera, 2160, 3840);

// Verify normalized (u, v) are identical across all scales
assertClose(projScale1.u, projScaleHalf.u, 1e-6, "Normalized u identical across scale 1.0 and 0.5");
assertClose(projScale1.v, projScaleHalf.v, 1e-6, "Normalized v identical across scale 1.0 and 0.5");
assertClose(projScale1.u, projScaleDouble.u, 1e-6, "Normalized u identical across scale 1.0 and 2.0");
assertClose(projScale1.v, projScaleDouble.v, 1e-6, "Normalized v identical across scale 1.0 and 2.0");

// Verify scale normalization (dividing by scale restores canonical 1080x1920 coordinates)
const refXFromHalf = projScaleHalf.x / 0.5;
const refYFromHalf = projScaleHalf.y / 0.5;
assertClose(refXFromHalf, projScale1.x, 0.2, "Half scale divided by 0.5 restores 1080x1920 X");
assertClose(refYFromHalf, projScale1.y, 0.2, "Half scale divided by 0.5 restores 1080x1920 Y");

const refXFromDouble = projScaleDouble.x / 2.0;
const refYFromDouble = projScaleDouble.y / 2.0;
assertClose(refXFromDouble, projScale1.x, 0.2, "Double scale divided by 2.0 restores 1080x1920 X");
assertClose(refYFromDouble, projScale1.y, 0.2, "Double scale divided by 2.0 restores 1080x1920 Y");

console.log("=== 4. Testing Anchor Target Types & Dynamic Hierarchy ===");

const anchorSystem = new AnchorSystem(camera, { width: 1080, height: 1920 });

// Target Type A: Static Vector3
anchorSystem.add("static_point", new THREE.Vector3(0, 1.2, 0));

// Target Type B: Three.js Mesh with local offset
const parentGroup = new THREE.Group();
parentGroup.position.set(1.0, 0.0, -1.0);
const standeeMesh = new THREE.Mesh(
  new THREE.BoxGeometry(0.5, 1.5, 0.1),
  new THREE.MeshBasicMaterial()
);
standeeMesh.position.set(0, 0.75, 0); // center is at 0.75 locally
parentGroup.add(standeeMesh);
parentGroup.updateMatrixWorld(true);

// Add with local head offset
anchorSystem.add("standee_head", standeeMesh, { offset: [0, 0.75, 0] });

// Target Type C: Bounding Box Keypoint ('top', 'center', 'bottom')
const pedestal = new THREE.Mesh(
  new THREE.BoxGeometry(1.0, 2.0, 1.0),
  new THREE.MeshBasicMaterial()
);
pedestal.position.set(-1.5, 1.0, 0.0);
pedestal.updateMatrixWorld(true);
anchorSystem.addKeypoint("pedestal_top", pedestal, "top");
anchorSystem.addKeypoint("pedestal_center", pedestal, "center");

// Target Type D: Dynamic trajectory function (t) => Vector3
anchorSystem.add("moving_orb", (t) => [Math.sin(t), 1.0, 0.0]);

// Evaluate at t = 0
const frame0 = anchorSystem.get(0);
assert(Array.isArray(frame0.static_point), "static_point returned array [x, y]");
assert(Array.isArray(frame0.standee_head), "standee_head returned array [x, y]");
assert(Array.isArray(frame0.pedestal_top), "pedestal_top returned array [x, y]");
assert(Array.isArray(frame0.pedestal_center), "pedestal_center returned array [x, y]");
assert(Array.isArray(frame0.moving_orb), "moving_orb returned array [x, y]");

// Pedestal top must be higher on screen (smaller Y) than pedestal center
assert(
  frame0.pedestal_top[1] < frame0.pedestal_center[1],
  `pedestal_top Y (${frame0.pedestal_top[1]}) < pedestal_center Y (${frame0.pedestal_center[1]})`
);

// Dynamic trajectory test: Orb at t = Math.PI / 2 (sin = 1) must move right (larger X)
const framePi2 = anchorSystem.get(Math.PI / 2);
assert(
  framePi2.moving_orb[0] > frame0.moving_orb[0],
  `moving_orb at t=PI/2 (${framePi2.moving_orb[0]}) > at t=0 (${frame0.moving_orb[0]})`
);

console.log("=== 5. Testing Scene Graph Auto-Scanning ===");

const scene = new THREE.Scene();
const archGroup = new THREE.Group();
archGroup.name = "anchor:arch_apex";
archGroup.position.set(0, 3.2, -2.0);
scene.add(archGroup);

const cardStandee = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.0, 0.1));
cardStandee.position.set(-1, 1, 0);
cardStandee.userData.anchor = "kicker";
scene.add(cardStandee);

const kiosk = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.0, 0.1));
kiosk.position.set(1, 1, 0);
kiosk.userData.anchors = {
  stat_badge: [0, 0.8, 0],
  info_label: [0, 0.2, 0],
};
scene.add(kiosk);

const scannerSystem = new AnchorSystem(camera, { width: 1080, height: 1920 });
const count = scannerSystem.scanScene(scene);
assert(count === 4, `scanScene discovered 4 anchors (got ${count})`);

const scannedAnchors = scannerSystem.get(0);
assert(Array.isArray(scannedAnchors.arch_apex), "scanned arch_apex exists");
assert(Array.isArray(scannedAnchors.kicker), "scanned kicker exists");
assert(Array.isArray(scannedAnchors.stat_badge), "scanned stat_badge exists");
assert(Array.isArray(scannedAnchors.info_label), "scanned info_label exists");

console.log("=== 6. Testing Diorama Set JSON Integration ===");

// Load museum-hall.json set definition
const museumSetPath = path.join(__dirname, "sets", "museum-hall.json");
const museumSet = JSON.parse(fs.readFileSync(museumSetPath, "utf8"));

const setAnchorSystem = new AnchorSystem(camera, { width: 1080, height: 1920 });
setAnchorSystem.loadFromSet(museumSet);

assert(setAnchorSystem.anchors.has("dot"), "Set loaded 'dot' anchor");
assert(setAnchorSystem.anchors.has("headline_label"), "Set loaded 'headline_label' anchor");
assert(setAnchorSystem.anchors.has("stat_callout_left"), "Set loaded 'stat_callout_left' anchor");
assert(setAnchorSystem.anchors.has("stat_callout_right"), "Set loaded 'stat_callout_right' anchor");
assert(setAnchorSystem.anchors.has("vanishing_point"), "Set loaded 'vanishing_point' anchor");

const museumAnchors = setAnchorSystem.get(0);
assert(Array.isArray(museumAnchors.dot), "museum dot anchor projects successfully");
assert(Array.isArray(museumAnchors.headline_label), "museum headline_label anchor projects successfully");
assertClose(museumAnchors.dot[0], 540.0, 1.0, "museum dot anchor is centered horizontally (x ~ 540)");

console.log("=== 7. Testing Export Contract & anchors.json Structure ===");

// Simulate full 6.0 second bake at 30 fps (180 frames)
const fullSystem = new AnchorSystem(camera, {
  width: 1080,
  height: 1920,
  fps: 30,
  seconds: 6.0,
  scale: 1.0,
});
fullSystem.add("dot", [0, 1.2, 0]);
fullSystem.add("kicker", [0, 2.0, 0]);
fullSystem.add("stat", [-1.5, 1.0, 0]);

const totalFrames = 180;
for (let i = 0; i < totalFrames; i++) {
  const t = i / 30;
  fullSystem.recordFrame(t);
}

const exported = fullSystem.exportTracks();
assert(exported.fps === 30, "exported.fps == 30");
assert(exported.width === 1080, "exported.width == 1080");
assert(exported.height === 1920, "exported.height == 1920");
assert(exported.tracks.dot && exported.tracks.dot.length === totalFrames, `tracks.dot length == 180 (got ${exported.tracks.dot.length})`);
assert(exported.tracks.kicker && exported.tracks.kicker.length === totalFrames, `tracks.kicker length == 180 (got ${exported.tracks.kicker.length})`);
assert(exported.tracks.stat && exported.tracks.stat.length === totalFrames, `tracks.stat length == 180 (got ${exported.tracks.stat.length})`);

// Determinism: Same frame evaluation produces bit-identical results
const evalA = fullSystem.get(2.345);
const evalB = fullSystem.get(2.345);
assertClose(evalA.dot[0], evalB.dot[0], 1e-9, "Determinism: dot[0] bit-identical");
assertClose(evalA.dot[1], evalB.dot[1], 1e-9, "Determinism: dot[1] bit-identical");
assertClose(evalA.kicker[0], evalB.kicker[0], 1e-9, "Determinism: kicker[0] bit-identical");
assertClose(evalA.kicker[1], evalB.kicker[1], 1e-9, "Determinism: kicker[1] bit-identical");

console.log("=== 8. Testing Safe Zone Compliance ===");

const detail = fullSystem.getDetailed(0);
assert(detail.dot.inSafeZone, "dot is inside safe zone");
assert(detail.kicker.inSafeZone, "kicker is inside safe zone");

// Add an element deliberately below safe zone (Y > 1380)
fullSystem.add("too_low_stat", [0, -3.0, 0]);
const lowDetail = fullSystem.getDetailed(0);
assert(!lowDetail.too_low_stat.inSafeZone, "too_low_stat correctly marked inSafeZone = false");

console.log(`\n========================================`);
console.log(`Results: ${passed} passed, ${failed} failed.`);
console.log(`========================================`);

if (failed > 0) {
  process.exit(1);
} else {
  console.log("ALL ANCHOR EXPORTER TESTS PASSED SUCCESSFULLY!");
}
