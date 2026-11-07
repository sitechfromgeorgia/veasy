// The five sets as data: parts that exist, moves that exist, generic names, no words, anchors on screen, the camera clear
// of every sheet it passes. Run: node plates/diorama/test_sets.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createCameraSystem } from "./lib/camera.mjs";
import { PARTS as SHAPES } from "./lib/parts.mjs";
import { PROPS } from "./lib/props.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PARTS = { ...SHAPES, ...PROPS };
const MOVES = ["dolly", "crane", "push-through", "reveal-behind", "wipe-pass"];
const SETS = ["museum-hall", "street", "market", "classroom", "river-bridge"];
const WORDS = /\b(tbilisi|georgia|kutaisi|batumi|louvre|rustaveli|mtkvari|sitech)\b/i;

let passed = 0, failed = 0;
function ok(condition, message) {
  if (condition) passed++;
  else { failed++; console.error(`FAIL: ${message}`); }
}

const used = new Set();
for (const id of SETS) {
  const text = fs.readFileSync(path.join(HERE, "sets", `${id}.json`), "utf8"), set = JSON.parse(text);
  ok(set.id === id, `${id}: id is its file name`);
  ok(MOVES.includes(set.move), `${id}: a move of the grammar, got ${set.move}`);
  used.add(set.move);
  ok(!WORDS.test(text), `${id}: a set never names a real place or a client`);
  ok(!/"text"|"label"|"title"/.test(text), `${id}: a plate has no words`);
  for (const p of set.parts) ok(PARTS[p.part], `${id}: no part "${p.part}"`);
  ok(set.parts.filter((p) => !["glow", "sky"].includes(p.part)).length >= 12, `${id}: at least a dozen layers`);

  const ctx = { width: 1080, height: 1920, fps: 30, seconds: 6, seed: 1 };
  const rig = createCameraSystem(set, ctx);
  rig.evaluate(3);
  for (const [name, at] of Object.entries(rig.getAnchors())) {
    ok(at.every(Number.isFinite), `${id}: anchor ${name} is a number`);
    if (name !== "dot") ok(at[0] > -200 && at[0] < 1280 && at[1] > -200 && at[1] < 2120, `${id}: anchor ${name} near the frame at the middle of the take, got ${at}`);
  }
  let last = null, jump = 0;
  for (let i = 0; i < 180; i++) { // no pop in the camera, and no stop in the middle of a move
    rig.evaluate(i / 30);
    const eye = rig.camera.position.clone();
    if (last) jump = Math.max(jump, eye.distanceTo(last));
    last = eye;
  }
  ok(jump < 0.2, `${id}: the camera moves smoothly, largest step ${jump.toFixed(3)}`);
}
ok(used.size === MOVES.length, `all five moves are in use, got ${[...used]}`);

// The push-through really goes through: the eye crosses each sheet inside its opening.
const museum = JSON.parse(fs.readFileSync(path.join(HERE, "sets", "museum-hall.json"), "utf8"));
const rig = createCameraSystem(museum, { width: 1080, height: 1920, fps: 30, seconds: 6, seed: 1 });
for (const sheet of museum.parts.filter((p) => p.part === "sheet")) {
  for (let i = 0; i < 180; i++) {
    rig.evaluate(i / 30);
    const { x, y, z } = rig.camera.position;
    if (Math.abs(z - sheet.at[2]) < 0.06) ok(Math.abs(x) < sheet.open / 2 - 0.1 && y < (sheet.sill ?? 0.34) + (sheet.spring ?? 3.2), `the eye is inside the opening at z=${sheet.at[2]}`);
  }
}

// A wipe really covers the frame, and not on the poster frame.
const river = JSON.parse(fs.readFileSync(path.join(HERE, "sets", "river-bridge.json"), "utf8"));
const wipe = river.parts.find((p) => p.part === "wipe");
const flow = createCameraSystem(river, { width: 1080, height: 1920, fps: 30, seconds: 6, seed: 1 });
let covered = 0, onPoster = false;
for (let i = 0; i < 180; i++) {
  flow.evaluate(i / 30);
  const d = flow.camera.position.z - wipe.at[2], half = d * Math.tan(15 * Math.PI / 180) * 9 / 16;
  const centre = flow.camera.position.x, lens = flow.currentTarget.x, atWipe = centre + (lens - centre) * d / (flow.camera.position.z - flow.currentTarget.z);
  const whole = Math.abs(atWipe - wipe.at[0]) + half < wipe.width / 2;
  if (whole) { covered++; if (i === 90) onPoster = true; }
}
ok(covered > 0 && covered < 30, `the wipe covers the frame for under a second, got ${covered} frames`);
ok(!onPoster, "the middle frame, the poster, is not the wipe");

console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
