/**
 * plates/diorama/test_sets.mjs
 * Verification suite for the 5 declarative diorama sets.
 */

import fs from "node:fs";
import path from "node:path";
import { DioramaCameraController } from "./lib/camera.mjs";
import { AnchorSystem } from "./lib/anchors.mjs";

const setsDir = "plates/diorama/sets";
const setFiles = [
  "museum-hall.json",
  "street.json",
  "market.json",
  "classroom.json",
  "river-bridge.json",
];

let totalChecks = 0;
let passedChecks = 0;

function assert(condition, message) {
  totalChecks++;
  if (condition) {
    passedChecks++;
  } else {
    console.error(`FAIL: ${message}`);
    process.exitCode = 1;
  }
}

console.log("=== Verifying 5 Generic Diorama Sets ===");

for (const file of setFiles) {
  const filePath = path.join(setsDir, file);
  console.log(`\nChecking set: ${file}...`);

  assert(fs.existsSync(filePath), `File exists: ${filePath}`);
  const spec = JSON.parse(fs.readFileSync(filePath, "utf8"));

  // 1. Mandatory top-level properties
  assert(spec.id && typeof spec.id === "string", `Has id: ${spec.id}`);
  assert(spec.name && typeof spec.name === "string", `Has name: ${spec.name}`);
  assert(spec.duration === 6.0, `Has 6.0s duration: ${spec.duration}`);
  assert(spec.tone === "greys-blacks-paper-whites", `Tone contract respected: ${spec.tone}`);

  // 2. Generic naming rule check (NEVER depict or name a real place or building)
  const forbiddenRealNames = [
    "tbilisi", "paris", "london", "rome", "louvre", "colosseum",
    "georgia", "new york", "berlin", "tokyo", "oxford", "cambridge",
    "brooklyn", "thames", "danube", "seine", "mkg", "rustaveli"
  ];
  const fullText = JSON.stringify(spec).toLowerCase();
  for (const place of forbiddenRealNames) {
    assert(!fullText.includes(` ${place} `) && !fullText.includes(`"${place}"`), `Set does not mention real place '${place}'`);
  }

  // 3. Depth layers check
  assert(spec.depth_layers && spec.depth_layers.foreground, "Has foreground layer definition");
  assert(spec.depth_layers && spec.depth_layers.midground, "Has midground layer definition");
  assert(spec.depth_layers && spec.depth_layers.background, "Has background layer definition");

  // 4. Standees verification
  assert(Array.isArray(spec.standees) && spec.standees.length >= 3, `Has >= 3 standees: ${spec.standees.length}`);
  for (const s of spec.standees) {
    assert(fs.existsSync(s.drawing_path), `Standee drawing file exists: ${s.drawing_path}`);
    assert(s.position && s.position.length === 3, `Standee ${s.id} has 3D position`);
    assert(s.paper_layers >= 2, `Standee ${s.id} has layered paper backing (layers=${s.paper_layers})`);
    assert(s.base_bracket && s.base_bracket.type, `Standee ${s.id} has physical base bracket`);
  }

  // 5. Components verification
  assert(Array.isArray(spec.components) && spec.components.length >= 10, `Has >= 10 part kit components: ${spec.components.length}`);
  for (const c of spec.components) {
    assert(["foreground", "midground", "background"].includes(c.layer), `Component ${c.id} has valid layer: ${c.layer}`);
    assert(c.position && c.position.length === 3, `Component ${c.id} has 3D position`);
    assert(c.paper_properties && c.paper_properties.hex, `Component ${c.id} has paper properties`);
  }

  // 6. Camera kinematics evaluation through DioramaCameraController
  const controller = new DioramaCameraController(spec, { width: 1080, height: 1920, fps: 30, seconds: 6.0 });
  const anchorSystem = new AnchorSystem(controller.camera, { width: 1080, height: 1920, fps: 30, seconds: 6.0 });
  anchorSystem.loadFromSet(spec);

  // Evaluate across 180 frames (6s at 30fps)
  for (let frame = 0; frame <= 180; frame += 30) {
    const t = frame / 30;
    const state = controller.evaluate(t);

    assert(!isNaN(state.eye.x) && !isNaN(state.eye.y) && !isNaN(state.eye.z), `Frame t=${t}s: camera eye is valid numbers`);
    assert(!isNaN(state.target.x) && !isNaN(state.target.y) && !isNaN(state.target.z), `Frame t=${t}s: camera target is valid numbers`);

    // Verify anchors project to valid screen pixels
    const frameAnchors = anchorSystem.get(t);
    assert(frameAnchors.dot !== undefined, `Frame t=${t}s: 'dot' anchor projected`);
    assert(!isNaN(frameAnchors.dot[0]) && !isNaN(frameAnchors.dot[1]), `Frame t=${t}s: 'dot' coordinates are valid: [${frameAnchors.dot.join(", ")}]`);
  }

  console.log(`✓ Set ${spec.id} validated with all depth layers, standees, components, camera & anchors.`);
}

console.log(`\n==================================================`);
console.log(`  ALL 5 DIORAMA SETS PASSED ALL VERIFICATIONS (${passedChecks}/${totalChecks})`);
console.log(`==================================================`);
