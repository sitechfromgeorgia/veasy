// The tones and the matte material of a standee (lib/extruder.mjs). A part of a set is lib/parts.mjs.
import * as THREE from "three";

export const TONES = Object.freeze({
  WHITE:  0xf6f6f6, // 96% - Highlight edge strips, crisp card edges, white trim
  CARD:   0xe2e2e2, // 88% - Main cardstock body, primary wall face
  CREAM:  0xd0d0d0, // 81% - Secondary card surfaces, architraves, balustrades
  MUTED:  0xa2a2a2, // 63% - Roof planes, bridge roadbed, recessed panels
  SHADOW: 0x6e6e6e, // 43% - Under-arch soffits, plinth flanks, sill undersides
  DARK:   0x383838, // 22% - Tree trunks, interior reveal cards, dark trim
  VOID:   0x121212  //  7% - Window aperture void backings, deep recesses
});

/**
 * Default paper physical and geometric properties.
 */
export const PAPER_DEFAULTS = Object.freeze({
  thickness: 0.035,        // Standard cardstock sheet thickness (0.02 - 0.05)
  bevelThickness: 0.006,   // Subtle micro-bevel for catching edge light
  bevelSize: 0.005,        // Micro-bevel chamfer width
  bevelSegments: 1,        // Single segment = crisp cut paper edge
  curveSegments: 24,       // Smooth curves for arcs and hills
  zStep: 0.06              // Layer depth offset for staggered pop-up planes
});

const materialCache = new Map();

/**
 * Creates or retrieves a cached matte paper material with tone-only color.
 * Uses MeshLambertMaterial for pure diffuse reflection without shiny plastic highlights.
 *
 * @param {number|string} tone Hex color code from TONES or custom grey
 * @param {Object} [options={}] Additional material options
 * @returns {THREE.MeshLambertMaterial}
 */
export function createPaperMaterial(tone = TONES.CARD, options = {}) {
  const colorHex = typeof tone === "number" ? tone : parseInt(tone, 16);
  const flatShading = options.flatShading !== false; // Default true for faceted card look
  const side = options.side || THREE.FrontSide;
  const transparent = Boolean(options.transparent);
  const opacity = options.opacity !== undefined ? options.opacity : 1.0;

  const cacheKey = `${colorHex}_${flatShading}_${side}_${transparent}_${opacity}`;
  if (materialCache.has(cacheKey)) {
    return materialCache.get(cacheKey);
  }

  const mat = new THREE.MeshLambertMaterial({
    color: colorHex,
    flatShading,
    side,
    transparent,
    opacity
  });

  materialCache.set(cacheKey, mat);
  return mat;
}

/**
 * Clears the material cache (useful between scene reloads).
 */
export function clearMaterialCache() {
  materialCache.clear();
}

/**
 * Extrudes a 2D THREE.Shape into a 3D cut-cardstock slab with paper micro-bevels.
 *
 * @param {THREE.Shape} shape The 2D cross-section shape
 * @param {Object} [options={}] Extrusion overrides
 * @returns {THREE.ExtrudeGeometry}
 */
export function extrudePaper(shape, options = {}) {
  const depth = options.depth || PAPER_DEFAULTS.thickness;
  const bevelEnabled = options.bevelEnabled !== false;
  const bevelThickness = bevelEnabled ? (options.bevelThickness || PAPER_DEFAULTS.bevelThickness) : 0;
  const bevelSize = bevelEnabled ? (options.bevelSize || PAPER_DEFAULTS.bevelSize) : 0;
  const bevelSegments = options.bevelSegments || PAPER_DEFAULTS.bevelSegments;
  const curveSegments = options.curveSegments || PAPER_DEFAULTS.curveSegments;

  return new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled,
    bevelThickness,
    bevelSize,
    bevelSegments,
    curveSegments
  });
}
