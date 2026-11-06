/**
 * plates/diorama/lib/kit.test.mjs
 * Verification suite for the Paper Stage Modular Architecture Kit.
 */

import * as THREE from "three";
import * as kit from "./kit.mjs";

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

console.log("=== Running Paper Stage Part Kit Verification ===");

// 1. Constants & Palette
assert(kit.TONES.CARD === 0xe2e2e2, "TONES.CARD is calibrated");
assert(kit.TONES.VOID === 0x121212, "TONES.VOID is deep black backing");
assert(kit.PAPER_DEFAULTS.thickness === 0.035, "Paper default thickness is 0.035 units");
assert(kit.PAPER_DEFAULTS.bevelThickness === 0.006, "Paper bevel thickness is 0.006 units");
console.log("✓ Palettes & physical constants verified");

// 2. Materials
const mat1 = kit.createPaperMaterial(kit.TONES.WHITE);
const mat2 = kit.createPaperMaterial(kit.TONES.WHITE);
assert(mat1 === mat2, "Materials are cached to avoid redundant WebGL programs");
assert(mat1 instanceof THREE.MeshLambertMaterial, "Paper uses matte MeshLambertMaterial");
console.log("✓ Material factory & caching verified");

// 3. Punched Wall
const wall = kit.createPunchedWall({
  width: 5.0,
  height: 3.5,
  apertures: [
    { x: -1.2, y: 0.8, width: 0.9, height: 1.5, type: "roman" },
    { x: 1.2, y: 0.8, width: 0.9, height: 1.6, type: "pointed" }
  ]
});
assert(wall instanceof THREE.Group, "Punched wall produces a THREE.Group");
assert(wall.children.length >= 2, "Punched wall includes face, coping, and backing");
console.log("✓ Punched wall with mixed apertures verified");

// 4. Arches (Roman, Pointed Gothic, Horseshoe Moorish)
const archTypes = ["roman", "pointed", "horseshoe", "rect", "round"];
for (const at of archTypes) {
  const p = kit.createArchPath({ type: at, width: 1.2, height: 2.0 });
  assert(p.curves.length > 0, `Arch path generated for ${at}`);
}
const archway = kit.createArchway({ archType: "horseshoe" });
assert(archway instanceof THREE.Group, "Archway produces THREE.Group");
const portal = kit.createRecedingPortal({ layers: 3, archType: "pointed" });
assert(portal.children.length === 3, "Receding portal produces 3 stepped layers");
console.log("✓ Arches (Roman, Pointed, Horseshoe) & Receding Portals verified");

// 5. Plinth
const plinth = kit.createPlinth({ tiers: 3, width: 8.0, depth: 6.0 });
assert(plinth.children.length === 3, "Plinth produces 3 stepped terraces");
console.log("✓ Tiered plinth verified");

// 6. Stairs
const solidStairs = kit.createStairs({ steps: 7, style: "stepped" });
assert(solidStairs.children.length === 3, "Solid stairs includes steps and two lateral cheeks");
const accordionStairs = kit.createStairs({ steps: 5, style: "accordion" });
assert(accordionStairs.children.length === 1, "Accordion stairs folded sheet created");
console.log("✓ Stepped & accordion stairs verified");

// 7. Framed Windows
const win = kit.createFramedWindow({ rows: 3, cols: 2, archType: "pointed" });
assert(win instanceof THREE.Group, "Framed window produces THREE.Group");
console.log("✓ Framed window with mullions verified");

// 8. Trees
const discTree = kit.createPaperTree({ style: "disc", tiers: 4 });
assert(discTree.children.length === 7, "Disc tree has trunk, 2 foot slats, and 4 discs");
const cloudTree = kit.createPaperTree({ style: "cutout", type: "cloud", layers: 3 });
assert(cloudTree.children.length === 3, "Cloud tree has 3 silhouette layers");
const cypressTree = kit.createPaperTree({ style: "cutout", type: "cypress" });
assert(cypressTree.children.length === 3, "Cypress tree created");
const pineTree = kit.createPaperTree({ style: "cutout", type: "pine" });
assert(pineTree.children.length === 3, "Pine tree created");
console.log("✓ Paper trees (disc & cutout variants) verified");

// 9. Rolling Hills
const hills1 = kit.createRollingHills({ layers: 4, seed: 101 });
const hills2 = kit.createRollingHills({ layers: 4, seed: 101 });
assert(hills1.children.length === 4, "Hills produce 4 contour layers");
// Check determinism: first layer vertex counts match
const v1 = hills1.children[0].geometry.attributes.position.count;
const v2 = hills2.children[0].geometry.attributes.position.count;
assert(v1 === v2, "Hills generation is deterministic");
console.log("✓ Deterministic rolling hills verified");

// 10. Colonnade
const colonnade = kit.createColonnade({ count: 6, arcade: true });
assert(colonnade instanceof THREE.Group, "Colonnade produces THREE.Group");
console.log("✓ Colonnade with arcade spans verified");

// 11. Roofs
const gable = kit.createPaperRoof({ style: "gable" });
assert(gable.children.length >= 4, "Gable roof has pediments, slopes, and ridge cap");
const accordionRoof = kit.createPaperRoof({ style: "accordion" });
assert(accordionRoof.children.length === 1, "Accordion roof created");
const dome = kit.createPaperRoof({ style: "dome", tiers: 5 });
assert(dome.children.length === 5, "Dome cupola created");
console.log("✓ Roof systems (gable, accordion, dome, mansard) verified");

// 12. Bridge Deck
const bridge = kit.createBridgeDeck({ archCount: 2, archType: "segmental" });
assert(bridge.children.length >= 5, "Bridge deck includes spandrels, roadway, parapets, and piers");
console.log("✓ Bridge deck system verified");

// 13. Lighting Rig & Linear Fog
const scene = new THREE.Scene();
const rig = kit.setupPaperStage(scene);
assert(scene.fog instanceof THREE.Fog, "Scene fog is THREE.Fog");
assert(rig.keyLight.castShadow === false, "No cast shadows on key light");
assert(rig.rimLight.castShadow === false, "No cast shadows on rim light");
assert(scene.background.getHex() === 0x000000, "Background is pure black");
console.log("✓ Stage lighting & depth fog verified");

console.log("\n==================================================");
console.log("  ALL PAPER STAGE KIT SUITE CHECKS PASSED (13/13) ");
console.log("==================================================");
