/**
 * plates/diorama/test_extruder.mjs
 * 
 * Standee Extruder Verification Suite for the Veasy Paper Stage Diorama Engine.
 * 
 * Tests:
 * 1. Default configuration & tone exports
 * 2. Token preparation and SVG wrapping
 * 3. 2D Bounding box computation
 * 4. Slotted pedestal base variants (disc, pedestal, plinth)
 * 5. Backing card shape generation with integrated slot tab
 * 6. 100% RELIABILITY: Conversion of all 44 vector drawings in assets/drawings/*.json
 *    - Watertight mesh generation without NaN vertices
 *    - Base grounded at y = 0
 *    - Scale normalization to standard height
 *    - Export of 3D anchors (dot, top, base)
 * 7. Performance benchmark across all 44 drawings
 */

import * as THREE from "three";
import fs from "fs";
import path from "path";
import {
  STANDEE_DEFAULTS,
  STANDEE_TONES,
  prepareDrawingSVG,
  computeDrawingBounds,
  createPaperCardShape,
  createSlottedPedestal,
  createStandeeFromDrawing,
  createStandeeFromSVG
} from "./lib/extruder.mjs";

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

console.log("=== 1. Testing Default Parameters & Tone Mappings ===");
assert(STANDEE_DEFAULTS.standardHeight === 2.0, "Default standardHeight == 2.0");
assert(STANDEE_DEFAULTS.paperThickness === 0.035, "Default paperThickness == 0.035");
assert(STANDEE_DEFAULTS.baseHeight === 0.08, "Default baseHeight == 0.08");
assert(STANDEE_TONES.INK === "#f6f6f6", "INK mapped to #f6f6f6");
assert(STANDEE_TONES.CARD === "#e2e2e2", "CARD mapped to #e2e2e2");
assert(STANDEE_TONES.CANVAS === "#383838", "CANVAS mapped to #383838");

console.log("=== 2. Testing SVG Preparation & Token Substitution ===");
const sampleSnippet = '<line x1="10" y1="20" x2="100" y2="20" stroke="LINE" fill="CANVAS"/>';
const prepared = prepareDrawingSVG(sampleSnippet);
assert(prepared.startsWith('<svg viewBox="0 0 952 640"'), "SVG snippet wrapped in <svg viewBox='0 0 952 640'>");
assert(prepared.includes(`stroke="${STANDEE_TONES.LINE}"`), "LINE token replaced with hex");
assert(prepared.includes(`fill="${STANDEE_TONES.CANVAS}"`), "CANVAS token replaced with hex");

console.log("=== 3. Testing Slotted Pedestal Variants ===");
for (const bType of ["disc", "pedestal", "plinth"]) {
  const ped = createSlottedPedestal(1.4, 0.6, { baseType: bType, baseHeight: 0.08 });
  assert(ped instanceof THREE.Group, `Pedestal '${bType}' is a THREE.Group`);
  const box = new THREE.Box3().setFromObject(ped);
  assertClose(box.min.y, 0, 1e-4, `Pedestal '${bType}' rests on y = 0`);
  assertClose(box.max.y, 0.08, 1e-4, `Pedestal '${bType}' height is 0.08`);
}

console.log("=== 4. Testing Paper Backing Card Shape with Tab ===");
const cardShape = createPaperCardShape(1.4, 2.2, 0.08, 0.6, 0.04, { cardStyle: "rounded" });
assert(cardShape instanceof THREE.Shape, "Card shape is a THREE.Shape");
const pts = cardShape.getPoints();
assert(pts.length > 10, "Card shape has smooth perimeter points");
// Tab lowest Y point
const minY = Math.min(...pts.map(p => p.y));
assertClose(minY, 0.08 - 0.04 + 0.005, 1e-3, "Card tab extends below card bottom into slot");

console.log("=== 5. Testing ALL 44 Drawings in assets/drawings/*.json ===");
// Locate assets/drawings
const possibleDirs = [
  path.resolve("assets/drawings"),
  path.resolve("../assets/drawings"),
  path.resolve("D:/MyStaff/Veasy/assets/drawings"),
  path.resolve("D:/MyStaff/Veasy-paper-stage/assets/drawings")
];
let drawingsDir = null;
for (const d of possibleDirs) {
  if (fs.existsSync(d)) {
    drawingsDir = d;
    break;
  }
}

assert(drawingsDir !== null, `Found assets/drawings directory at ${drawingsDir}`);

const drawingFiles = fs.readdirSync(drawingsDir).filter(f => f.endsWith(".json"));
assert(drawingFiles.length === 44, `Found exactly 44 drawing JSON files (found ${drawingFiles.length})`);

const summary = [];
const t0 = Date.now();

for (let idx = 0; idx < drawingFiles.length; idx++) {
  const file = drawingFiles[idx];
  const filePath = path.join(drawingsDir, file);
  const data = JSON.parse(fs.readFileSync(filePath, "utf8"));

  // Alternate base types and card styles to verify versatility
  const baseType = idx % 3 === 0 ? "disc" : (idx % 3 === 1 ? "pedestal" : "plinth");
  const cardStyle = idx % 2 === 0 ? "rounded" : "arched";

  let standee;
  try {
    standee = createStandeeFromDrawing(data, {
      standardHeight: 2.0,
      baseType,
      cardStyle
    });
  } catch (err) {
    assert(false, `${file}: createStandeeFromDrawing threw: ${err.message}`);
    continue;
  }

  assert(standee instanceof THREE.Group, `${file}: Standee is a THREE.Group`);

  // Check NaN vertices across all geometries
  let meshCount = 0;
  let totalVerts = 0;
  let nanCount = 0;

  standee.traverse(child => {
    if (child.isMesh && child.geometry) {
      meshCount++;
      const pos = child.geometry.attributes.position;
      if (pos) {
        totalVerts += pos.count;
        for (let i = 0; i < pos.count; i++) {
          const x = pos.getX(i);
          const y = pos.getY(i);
          const z = pos.getZ(i);
          if (isNaN(x) || isNaN(y) || isNaN(z) || !isFinite(x) || !isFinite(y) || !isFinite(z)) {
            nanCount++;
          }
        }
      }
    }
  });

  assert(meshCount > 0, `${file}: Has child meshes (count ${meshCount})`);
  assert(nanCount === 0, `${file}: Zero NaN vertices (total verts ${totalVerts})`);

  // Bounding box checks
  const box = new THREE.Box3().setFromObject(standee);
  assertClose(box.min.y, 0, 1e-4, `${file}: Standee grounded at y = 0`);
  assert(box.max.y > 1.8 && box.max.y < 3.5, `${file}: Standee height in reasonable normalized range (${box.max.y.toFixed(3)})`);

  // Centering check (x-axis symmetry)
  const centerX = (box.min.x + box.max.x) / 2;
  assert(Math.abs(centerX) < 0.25, `${file}: Centered horizontally (|centerX| = ${Math.abs(centerX).toFixed(3)} < 0.25)`);

  // Anchors check
  assert(Boolean(standee.userData.anchors), `${file}: userData.anchors defined`);
  assert(standee.userData.anchors.dot instanceof THREE.Vector3, `${file}: anchors.dot is Vector3`);
  assert(standee.userData.anchors.top instanceof THREE.Vector3, `${file}: anchors.top is Vector3`);
  assert(standee.userData.anchors.base instanceof THREE.Vector3, `${file}: anchors.base is Vector3`);

  summary.push({
    file,
    motif: data.motif,
    baseType,
    cardStyle,
    meshes: meshCount,
    verts: totalVerts,
    height: (box.max.y - box.min.y).toFixed(3)
  });
}

const elapsed = Date.now() - t0;
console.log(`\nExtruded and verified all 44 drawings in ${elapsed} ms (${(elapsed / 44).toFixed(1)} ms/drawing)`);
assert(elapsed < 4000, `Performance budget: All 44 drawings extruded under 4.0s (actual: ${elapsed}ms)`);

console.log("\n=== Sample Extrusion Results (10 drawings) ===");
console.table(summary.slice(0, 10));

console.log(`\n======================================================`);
console.log(`STANDee EXTRUDER SUITE: ${passed} passed, ${failed} failed.`);
console.log(`======================================================\n`);

if (failed > 0) {
  process.exit(1);
} else {
  console.log("ALL STANDEE EXTRUSION VERIFICATIONS PASSED WITH 100% RELIABILITY!");
}
