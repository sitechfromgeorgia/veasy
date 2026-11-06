/**
 * plates/diorama/lib/kit.mjs
 * 
 * Modular Paper Architecture Kit for the Veasy Paper Stage Diorama Engine.
 * 
 * Design Principles:
 * 1. Paper Aesthetics: Subtle thickness (0.02 - 0.05 units), micro-beveled edges
 *    (0.005 - 0.01) that catch specular-free directional light, and staggered
 *    z-planes mimicking Victorian toy theatres and pop-up books.
 * 2. Tone-Only Shading: Calibrated grey values on a black canvas (#000000)
 *    strictly mapping between canvas (black) and ink (white).
 * 3. Shadowless Depth: Cast shadows are disabled (saving ~533ms per frame to stay
 *    under the 370ms diorama budget). Depth is sculpted entirely through 3-point
 *    directional stage lighting (key, hemisphere fill, rim kicker) and linear fog.
 * 4. Modular Parametric Components: Walls with punched apertures, Roman/Gothic/Horseshoe
 *    arches, plinths, stairs, framed windows with mullions, paper trees (layered discs
 *    and silhouette cuts), rolling hills, colonnades, roofs, and bridge decks.
 * 5. Deterministic: All procedural variations use seeded pseudo-randomness.
 */

import * as THREE from "three";

// ============================================================================
// 1. TONE PALETTE & PAPER DEFAULTS
// ============================================================================

/**
 * Calibrated tone-safe greyscale palette.
 * Black (#000000) is the stage void/canvas; white (#ffffff) is the pack's ink.
 */
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

// ============================================================================
// 2. MATERIAL FACTORY
// ============================================================================

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

// ============================================================================
// 3. CORE GEOMETRY & EXTRUSION HELPERS
// ============================================================================

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

/**
 * Creates a rectangular cardstock slab mesh.
 *
 * @param {number} width Width along X
 * @param {number} height Height along Y
 * @param {Object} [options={}] Material and geometry options
 * @returns {THREE.Mesh}
 */
export function createPaperCard(width, height, options = {}) {
  const shape = new THREE.Shape();
  const halfW = width / 2;
  const halfH = height / 2;
  shape.moveTo(-halfW, -halfH);
  shape.lineTo(halfW, -halfH);
  shape.lineTo(halfW, halfH);
  shape.lineTo(-halfW, halfH);
  shape.closePath();

  const geom = extrudePaper(shape, options);
  const mat = options.material || createPaperMaterial(options.tone || TONES.CARD);
  const mesh = new THREE.Mesh(geom, mat);
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  return mesh;
}

// ============================================================================
// 4. ARCHES: ROMAN, POINTED (GOTHIC), HORSESHOE (MOORISH)
// ============================================================================

/**
 * Appends a Roman (semicircular) arch path to a target path or shape.
 * Starting at (-width/2, springY), rounds up over center (0, springY) with radius width/2,
 * and ends at (width/2, springY).
 *
 * @param {THREE.Path|THREE.Shape} path
 * @param {number} width Total opening span
 * @param {number} springY Elevation where the semicircular arc begins
 * @param {boolean} [reverse=false] If true, curves from right to left
 */
export function appendRomanArch(path, width, springY, reverse = false) {
  const radius = width / 2;
  const centerX = 0;
  const centerY = springY;

  if (!reverse) {
    // Left to right: counter-clockwise from PI to 0
    path.absarc(centerX, centerY, radius, Math.PI, 0, true);
  } else {
    // Right to left: clockwise from 0 to PI
    path.absarc(centerX, centerY, radius, 0, Math.PI, false);
  }
}

/**
 * Appends a Pointed (Gothic / Lancet) arch path.
 * Formed by two intersecting circular arcs meeting at an acute apex.
 *
 * @param {THREE.Path|THREE.Shape} path
 * @param {number} width Total opening span
 * @param {number} springY Elevation where the pointed arc begins
 * @param {number} apexHeight Height of the apex above ground (must be > springY)
 * @param {boolean} [reverse=false]
 */
export function appendPointedArch(path, width, springY, apexHeight, reverse = false) {
  const halfW = width / 2;
  const dH = apexHeight - springY;
  // Analytical center for intersecting arcs on the impost line
  const x0 = (dH * dH) / width - width / 4;
  const radius = x0 + halfW;
  const apexAngle = Math.atan2(dH, x0);

  if (!reverse) {
    // Left arc: centered at (+x0, springY), swinging from (-halfW, springY) up to apex (0, apexHeight)
    // Angle from +x0 to -halfW is Math.PI. Sweeps counter-clockwise to (Math.PI - apexAngle).
    path.absarc(x0, springY, radius, Math.PI, Math.PI - apexAngle, true);
    // Right arc: centered at (-x0, springY), swinging from apex down to (+halfW, springY)
    // Angle from -x0 to apex is apexAngle. Sweeps counter-clockwise to 0.
    path.absarc(-x0, springY, radius, apexAngle, 0, true);
  } else {
    // Right arc up to apex
    path.absarc(-x0, springY, radius, 0, apexAngle, false);
    // Left arc down from apex to left impost
    path.absarc(x0, springY, radius, Math.PI - apexAngle, Math.PI, false);
  }
}

/**
 * Appends a Horseshoe (Moorish) arch path.
 * An arch that extends beyond 180 degrees, pinching inward at the impost line.
 *
 * @param {THREE.Path|THREE.Shape} path
 * @param {number} width Opening span at the impost line
 * @param {number} springY Elevation of the impost line
 * @param {number} [radiusMultiplier=1.18] Factor by which the circle balloon radius exceeds halfW
 * @param {boolean} [reverse=false]
 */
export function appendHorseshoeArch(path, width, springY, radiusMultiplier = 1.18, reverse = false) {
  const halfW = width / 2;
  const radius = halfW * Math.max(1.02, radiusMultiplier);
  const dy = Math.sqrt(radius * radius - halfW * halfW);
  const centerY = springY + dy;
  const theta = Math.acos(halfW / radius); // Angle below horizontal for pinch

  const startAngle = Math.PI + theta; // Inward pinch on left
  const endAngle = -theta;            // Inward pinch on right

  if (!reverse) {
    // Sweeps counter-clockwise up from left pinch, over top, down to right pinch
    path.absarc(0, centerY, radius, startAngle, endAngle, true);
  } else {
    path.absarc(0, centerY, radius, endAngle, startAngle, false);
  }
}

/**
 * Builds an arch cutout path or outer profile shape according to arch type.
 *
 * @param {Object} options
 * @param {"roman"|"pointed"|"horseshoe"|"rect"|"round"} [options.type="roman"] Arch family
 * @param {number} options.width Opening width
 * @param {number} options.height Total opening height
 * @param {number} [options.springHeight] Elevation where curve begins (defaults to height - width/2)
 * @param {number} [options.offsetX=0] Center X offset
 * @param {number} [options.offsetY=0] Base Y offset
 * @returns {THREE.Path} Closed 2D path of the arch aperture
 */
export function createArchPath(options = {}) {
  const type = options.type || "roman";
  const width = options.width;
  const height = options.height;
  const halfW = width / 2;
  const ox = options.offsetX || 0;
  const oy = options.offsetY || 0;

  const path = new THREE.Path();
  path.moveTo(ox - halfW, oy);

  if (type === "rect") {
    path.lineTo(ox - halfW, oy + height);
    path.lineTo(ox + halfW, oy + height);
    path.lineTo(ox + halfW, oy);
    path.closePath();
    return path;
  }

  if (type === "round") {
    // Full circular window aperture
    const radius = Math.min(width, height) / 2;
    path.absarc(ox, oy + radius, radius, 0, Math.PI * 2, false);
    return path;
  }

  const defaultSpring = type === "roman" ? Math.max(0, height - halfW)
                      : type === "pointed" ? Math.max(0, height - halfW * 1.3)
                      : Math.max(0, height - halfW * 1.15);
  const springY = options.springHeight !== undefined ? options.springHeight : defaultSpring;

  // Jamb up to springline
  path.lineTo(ox - halfW, oy + springY);

  // Offset arch generation helper
  const subPath = new THREE.Path();
  if (type === "roman") {
    appendRomanArch(subPath, width, springY, false);
  } else if (type === "pointed") {
    appendPointedArch(subPath, width, springY, height, false);
  } else if (type === "horseshoe") {
    const mult = options.radiusMultiplier || 1.18;
    appendHorseshoeArch(subPath, width, springY, mult, false);
  }

  // Transfer curve points with X and Y offsets
  const points = subPath.getPoints(PAPER_DEFAULTS.curveSegments);
  for (let i = 1; i < points.length; i++) {
    path.lineTo(ox + points[i].x, oy + points[i].y);
  }

  // Drop down right jamb to floor
  path.lineTo(ox + halfW, oy);
  path.closePath();

  return path;
}

// ============================================================================
// 5. WALLS WITH PUNCHED APERTURES
// ============================================================================

/**
 * Creates a modular paper wall with punched window or door apertures.
 * Includes optional recessed dark backing card (giving depth without 3D interiors),
 * top coping strip, and base plinth trim.
 *
 * @param {Object} options
 * @param {number} [options.width=4.0] Total wall width
 * @param {number} [options.height=3.0] Total wall height
 * @param {number} [options.thickness=0.035] Cardstock thickness
 * @param {Array<Object>} [options.apertures=[]] Array of aperture specs:
 *    { x, y, width, height, type: "roman"|"pointed"|"horseshoe"|"rect"|"round" }
 * @param {number} [options.tone=TONES.CARD] Face paper tone
 * @param {boolean} [options.backing=true] Include recessed interior void backing
 * @param {number} [options.backingTone=TONES.VOID] Backing tone
 * @param {boolean} [options.coping=true] Include protruding top wall coping card
 * @param {boolean} [options.baseboard=false] Include bottom plinth trim
 * @returns {THREE.Group}
 */
export function createPunchedWall(options = {}) {
  const width = options.width || 4.0;
  const height = options.height || 3.0;
  const thickness = options.thickness || PAPER_DEFAULTS.thickness;
  const apertures = options.apertures || [];
  const tone = options.tone || TONES.CARD;
  const group = new THREE.Group();

  // 1. Outer Wall Shape
  const wallShape = new THREE.Shape();
  const halfW = width / 2;
  wallShape.moveTo(-halfW, 0);
  wallShape.lineTo(halfW, 0);
  wallShape.lineTo(halfW, height);
  wallShape.lineTo(-halfW, height);
  wallShape.closePath();

  // 2. Punch Apertures (holes in shape)
  for (const ap of apertures) {
    const apHole = createArchPath({
      type: ap.type || "roman",
      width: ap.width || 0.8,
      height: ap.height || 1.4,
      springHeight: ap.springHeight,
      offsetX: ap.x || 0,
      offsetY: ap.y || 0.6
    });
    wallShape.holes.push(apHole);
  }

  // Extrude front paper wall
  const wallGeom = extrudePaper(wallShape, { depth: thickness });
  const wallMat = createPaperMaterial(tone);
  const wallMesh = new THREE.Mesh(wallGeom, wallMat);
  group.add(wallMesh);

  // 3. Recessed Backing Card (simulates interior depth in stage dioramas)
  if (options.backing !== false && apertures.length > 0) {
    const backingTone = options.backingTone || TONES.VOID;
    const backingGeom = extrudePaper(wallShape, {
      depth: thickness * 0.5,
      bevelEnabled: false
    });
    const backingMat = createPaperMaterial(backingTone);
    const backingMesh = new THREE.Mesh(backingGeom, backingMat);
    // Offset backwards in Z
    backingMesh.position.z = -PAPER_DEFAULTS.zStep * 1.5;
    group.add(backingMesh);
  }

  // 4. Coping Strip (projecting cap card along top wall edge catching key light)
  if (options.coping !== false) {
    const copingW = width + 0.1;
    const copingH = 0.06;
    const copingD = thickness + 0.04;
    const copingCard = createPaperCard(copingW, copingH, {
      depth: copingD,
      tone: TONES.CREAM
    });
    copingCard.position.set(0, height + copingH / 2, copingD / 2 - thickness / 2);
    group.add(copingCard);
  }

  // 5. Optional Baseboard Trim
  if (options.baseboard) {
    const baseW = width + 0.05;
    const baseH = 0.12;
    const baseD = thickness + 0.02;
    const baseCard = createPaperCard(baseW, baseH, {
      depth: baseD,
      tone: TONES.CREAM
    });
    baseCard.position.set(0, baseH / 2, baseD / 2 - thickness / 2);
    group.add(baseCard);
  }

  return group;
}

// ============================================================================
// 6. FREESTANDING ARCHWAYS & RECEDING PORTALS
// ============================================================================

/**
 * Creates a standalone architectural archway wall (gateway / portal).
 *
 * @param {Object} options
 * @param {number} [options.width=2.4] Outer width
 * @param {number} [options.height=3.2] Outer height
 * @param {number} [options.archWidth=1.2] Clear opening width
 * @param {number} [options.archHeight=2.2] Clear opening height
 * @param {"roman"|"pointed"|"horseshoe"} [options.archType="roman"] Arch style
 * @param {number} [options.tone=TONES.CARD] Main card tone
 * @param {boolean} [options.keystone=true] Include layered keystone accent
 * @param {boolean} [options.imposts=true] Include impost molding blocks
 * @returns {THREE.Group}
 */
export function createArchway(options = {}) {
  const width = options.width || 2.4;
  const height = options.height || 3.2;
  const archW = options.archWidth || 1.2;
  const archH = options.archHeight || 2.2;
  const archType = options.archType || "roman";
  const tone = options.tone || TONES.CARD;
  const thickness = options.thickness || PAPER_DEFAULTS.thickness;

  const group = new THREE.Group();

  // Wall with arch opening
  const wall = createPunchedWall({
    width,
    height,
    thickness,
    tone,
    backing: false,
    coping: options.coping !== false,
    apertures: [{ x: 0, y: 0, width: archW, height: archH, type: archType }]
  });
  group.add(wall);

  // Impost blocks (layered paper blocks at the springline)
  if (options.imposts !== false) {
    const springY = Math.max(0, archType === "roman" ? archH - archW / 2
                  : archType === "pointed" ? archH - archW * 1.3
                  : archH - archW * 1.15);

    const blockW = 0.14;
    const blockH = 0.08;
    const blockD = thickness + 0.02;

    const leftImpost = createPaperCard(blockW, blockH, { depth: blockD, tone: TONES.WHITE });
    leftImpost.position.set(-archW / 2 - blockW / 2 + 0.02, springY, blockD / 2);
    group.add(leftImpost);

    const rightImpost = createPaperCard(blockW, blockH, { depth: blockD, tone: TONES.WHITE });
    rightImpost.position.set(archW / 2 + blockW / 2 - 0.02, springY, blockD / 2);
    group.add(rightImpost);
  }

  // Keystone on top of arch
  if (options.keystone !== false) {
    const ksW = 0.16;
    const ksH = 0.22;
    const ksD = thickness + 0.03;
    const keystone = createPaperCard(ksW, ksH, { depth: ksD, tone: TONES.WHITE });
    keystone.position.set(0, archH + ksH / 2 - 0.04, ksD / 2);
    group.add(keystone);
  }

  return group;
}

/**
 * Creates a nested receding Romanesque or Gothic portal.
 * Multiple concentric arch card layers step down in opening size and recede in Z.
 *
 * @param {Object} options
 * @param {number} [options.layers=3] Number of concentric receding arch layers
 * @param {number} [options.outerWidth=3.0] Outer width of the largest portal frame
 * @param {number} [options.outerHeight=3.6] Outer height
 * @param {number} [options.archWidth=1.6] Opening width of outermost arch
 * @param {number} [options.archHeight=2.6] Opening height of outermost arch
 * @param {"roman"|"pointed"} [options.archType="pointed"]
 * @param {number} [options.stepZ=0.08] Depth setback between successive card layers
 * @returns {THREE.Group}
 */
export function createRecedingPortal(options = {}) {
  const layers = options.layers || 3;
  const outerW = options.outerWidth || 3.0;
  const outerH = options.outerHeight || 3.6;
  const archW = options.archWidth || 1.6;
  const archH = options.archHeight || 2.6;
  const archType = options.archType || "pointed";
  const stepZ = options.stepZ || PAPER_DEFAULTS.zStep * 1.2;
  const thickness = options.thickness || PAPER_DEFAULTS.thickness;

  const group = new THREE.Group();
  const tones = [TONES.CARD, TONES.CREAM, TONES.MUTED, TONES.SHADOW];

  for (let i = 0; i < layers; i++) {
    const scale = 1 - i * 0.12;
    const layerArchW = archW * scale;
    const layerArchH = archH * scale;
    const layerTone = tones[i % tones.length];

    const wall = createPunchedWall({
      width: outerW - i * 0.18,
      height: outerH - i * 0.1,
      thickness,
      tone: layerTone,
      backing: i === layers - 1, // Dark backing card on final layer
      backingTone: TONES.VOID,
      coping: i === 0,
      apertures: [{ x: 0, y: 0, width: layerArchW, height: layerArchH, type: archType }]
    });

    wall.position.z = -i * stepZ;
    group.add(wall);
  }

  return group;
}

// ============================================================================
// 7. PLINTHS & DISPLAY PODIUMS
// ============================================================================

/**
 * Creates a tiered paper plinth / pedestal stage base.
 * Provides the grounding plinth upon which diorama sets rest.
 *
 * @param {Object} options
 * @param {number} [options.width=6.0] Top tier width
 * @param {number} [options.depth=4.0] Top tier depth
 * @param {number} [options.height=0.4] Total plinth height
 * @param {number} [options.tiers=2] Number of stepped plinth terraces
 * @param {number} [options.setback=0.15] Expansion setback per tier descending
 * @param {number} [options.tone=TONES.CREAM]
 * @returns {THREE.Group}
 */
export function createPlinth(options = {}) {
  const topW = options.width || 6.0;
  const topD = options.depth || 4.0;
  const totalH = options.height || 0.4;
  const tiers = Math.max(1, options.tiers || 2);
  const setback = options.setback || 0.15;
  const tierH = totalH / tiers;
  const group = new THREE.Group();

  const tones = [TONES.CARD, TONES.CREAM, TONES.MUTED, TONES.SHADOW];

  for (let i = 0; i < tiers; i++) {
    // Tier 0 is top, tier (tiers - 1) is base
    const expansion = (tiers - 1 - i) * setback;
    const w = topW + expansion * 2;
    const d = topD + expansion * 2;
    const yCenter = (i + 0.5) * tierH;

    const shape = new THREE.Shape();
    const hw = w / 2;
    const hd = d / 2;
    shape.moveTo(-hw, -hd);
    shape.lineTo(hw, -hd);
    shape.lineTo(hw, hd);
    shape.lineTo(-hw, hd);
    shape.closePath();

    const geom = extrudePaper(shape, {
      depth: tierH,
      bevelEnabled: true,
      bevelThickness: 0.008,
      bevelSize: 0.008
    });

    // Rotate so extrusion runs vertically along Y
    geom.rotateX(-Math.PI / 2);

    const mat = createPaperMaterial(tones[i % tones.length]);
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(0, i * tierH, 0);
    group.add(mesh);
  }

  return group;
}

// ============================================================================
// 8. STEPPED STAIRS
// ============================================================================

/**
 * Creates a papercraft stepped staircase.
 *
 * @param {Object} options
 * @param {number} [options.steps=6] Number of steps
 * @param {number} [options.width=1.6] Staircase span
 * @param {number} [options.stepHeight=0.1] Riser height
 * @param {number} [options.stepDepth=0.22] Tread depth
 * @param {number} [options.tone=TONES.CARD] Step tone
 * @param {boolean} [options.stringers=true] Include lateral side cheek walls
 * @param {"stepped"|"accordion"} [options.style="stepped"]
 * @returns {THREE.Group}
 */
export function createStairs(options = {}) {
  const steps = options.steps || 6;
  const width = options.width || 1.6;
  const stepH = options.stepHeight || 0.1;
  const stepD = options.stepDepth || 0.22;
  const tone = options.tone || TONES.CARD;
  const style = options.style || "stepped";
  const group = new THREE.Group();

  if (style === "accordion") {
    // Folded zig-zag paper sheet
    const shape = new THREE.Shape();
    shape.moveTo(0, 0);
    let curX = 0, curY = 0;
    for (let i = 0; i < steps; i++) {
      curY += stepH;
      shape.lineTo(curX, curY);
      curX += stepD;
      shape.lineTo(curX, curY);
    }
    // Return with card thickness
    const t = PAPER_DEFAULTS.thickness;
    shape.lineTo(curX, curY - t);
    for (let i = steps - 1; i >= 0; i--) {
      curX -= stepD;
      shape.lineTo(curX + t, curY - t);
      curY -= stepH;
      shape.lineTo(curX + t, curY);
    }
    shape.closePath();

    const geom = extrudePaper(shape, { depth: width });
    geom.rotateY(Math.PI / 2);
    geom.translate(-width / 2, 0, 0);

    const mat = createPaperMaterial(tone);
    const mesh = new THREE.Mesh(geom, mat);
    group.add(mesh);
    return group;
  }

  // Classical solid stepped block extruded sideways
  const stairShape = new THREE.Shape();
  stairShape.moveTo(0, 0);
  let curZ = 0, curY = 0;
  for (let i = 0; i < steps; i++) {
    curY += stepH;
    stairShape.lineTo(curZ, curY);
    curZ += stepD;
    stairShape.lineTo(curZ, curY);
  }
  // Drop down and return to origin
  stairShape.lineTo(curZ, 0);
  stairShape.closePath();

  const stairGeom = extrudePaper(stairShape, {
    depth: width,
    bevelEnabled: true,
    bevelThickness: 0.005,
    bevelSize: 0.005
  });
  // Reorient: shape is in Z-Y plane, extrusion along X
  stairGeom.rotateY(-Math.PI / 2);
  stairGeom.translate(width / 2, 0, 0);

  const stairMat = createPaperMaterial(tone);
  const stairMesh = new THREE.Mesh(stairGeom, stairMat);
  group.add(stairMesh);

  // Lateral Cheek Stringers (side balustrade card walls)
  if (options.stringers !== false) {
    const stringerShape = new THREE.Shape();
    const cheekH = 0.22;
    stringerShape.moveTo(-0.04, 0);
    stringerShape.lineTo(-0.04, cheekH);
    stringerShape.lineTo(curZ + 0.04, curY + cheekH);
    stringerShape.lineTo(curZ + 0.04, 0);
    stringerShape.closePath();

    const sGeom = extrudePaper(stringerShape, { depth: PAPER_DEFAULTS.thickness });
    sGeom.rotateY(-Math.PI / 2);
    const sMat = createPaperMaterial(TONES.CREAM);

    const leftCheek = new THREE.Mesh(sGeom, sMat);
    leftCheek.position.set(-width / 2 - PAPER_DEFAULTS.thickness / 2, 0, 0);
    group.add(leftCheek);

    const rightCheek = new THREE.Mesh(sGeom, sMat);
    rightCheek.position.set(width / 2 + PAPER_DEFAULTS.thickness / 2, 0, 0);
    group.add(rightCheek);
  }

  return group;
}

// ============================================================================
// 9. FRAMED WINDOWS WITH MULLIONS
// ============================================================================

/**
 * Creates a framed window module with outer casing trim, internal mullions /
 * muntin bars, projecting sill shelf, and recessed backing card.
 *
 * @param {Object} options
 * @param {number} [options.width=0.9] Opening width
 * @param {number} [options.height=1.5] Opening height
 * @param {"rect"|"roman"|"pointed"|"horseshoe"} [options.archType="rect"]
 * @param {number} [options.rows=3] Number of horizontal pane divisions
 * @param {number} [options.cols=2] Number of vertical pane divisions
 * @param {number} [options.frameWidth=0.06] Outer trim width
 * @param {number} [options.mullionWidth=0.025] Muntin bar width
 * @param {number} [options.sillDepth=0.08] Protruding window sill shelf depth
 * @param {number} [options.frameTone=TONES.WHITE]
 * @param {number} [options.backingTone=TONES.VOID]
 * @returns {THREE.Group}
 */
export function createFramedWindow(options = {}) {
  const width = options.width || 0.9;
  const height = options.height || 1.5;
  const archType = options.archType || "rect";
  const rows = Math.max(1, options.rows || 3);
  const cols = Math.max(1, options.cols || 2);
  const frameW = options.frameWidth || 0.06;
  const mullionW = options.mullionWidth || 0.025;
  const frameTone = options.frameTone || TONES.WHITE;
  const backingTone = options.backingTone || TONES.VOID;
  const thickness = options.thickness || PAPER_DEFAULTS.thickness;

  const group = new THREE.Group();

  // 1. Recessed Backing Card
  const backingCard = createPaperCard(width, height, {
    depth: thickness * 0.5,
    tone: backingTone
  });
  backingCard.position.set(0, height / 2, -PAPER_DEFAULTS.zStep * 0.8);
  group.add(backingCard);

  // 2. Outer Window Frame Molding
  const outerW = width + frameW * 2;
  const outerH = height + frameW * 2;
  const frameShape = new THREE.Shape();
  const halfOuterW = outerW / 2;
  frameShape.moveTo(-halfOuterW, 0);
  frameShape.lineTo(halfOuterW, 0);
  frameShape.lineTo(halfOuterW, outerH);
  frameShape.lineTo(-halfOuterW, outerH);
  frameShape.closePath();

  // Aperture hole in frame
  const holePath = createArchPath({
    type: archType,
    width,
    height,
    offsetX: 0,
    offsetY: frameW
  });
  frameShape.holes.push(holePath);

  const frameGeom = extrudePaper(frameShape, { depth: thickness });
  const frameMat = createPaperMaterial(frameTone);
  const frameMesh = new THREE.Mesh(frameGeom, frameMat);
  group.add(frameMesh);

  // 3. Mullion Grid (vertical & horizontal paper strips)
  const mullionMat = createPaperMaterial(TONES.CREAM);
  const mullionD = thickness * 0.8;

  // Vertical Mullions
  const colStep = width / cols;
  for (let c = 1; c < cols; c++) {
    const x = -width / 2 + c * colStep;
    const vMullion = createPaperCard(mullionW, height - 0.04, { depth: mullionD, tone: TONES.CREAM });
    vMullion.position.set(x, frameW + (height - 0.04) / 2, mullionD / 2);
    group.add(vMullion);
  }

  // Horizontal Transoms / Muntins
  const rowStep = height / rows;
  for (let r = 1; r < rows; r++) {
    const y = frameW + r * rowStep;
    const hMullion = createPaperCard(width - 0.02, mullionW, { depth: mullionD, tone: TONES.CREAM });
    hMullion.position.set(0, y, mullionD / 2);
    group.add(hMullion);
  }

  // 4. Protruding Sill Shelf (catches overhead key light)
  const sillW = outerW + 0.08;
  const sillH = 0.05;
  const sillD = options.sillDepth || 0.08;
  const sillMesh = createPaperCard(sillW, sillH, {
    depth: sillD,
    tone: TONES.WHITE
  });
  sillMesh.position.set(0, sillH / 2, sillD / 2);
  group.add(sillMesh);

  return group;
}

// ============================================================================
// 10. PAPER TREES (LAYERED FOLIAGE DISCS & POP-UP SILHOUETTES)
// ============================================================================

/**
 * Creates a papercraft tree in either:
 * - "disc" mode: Layered horizontal card discs on a central tapered trunk stand
 *   with an X-interlocking slotted base.
 * - "cutout" mode: Staggered multi-layer silhouette cards (cloud, cypress, pine).
 *
 * @param {Object} options
 * @param {"disc"|"cutout"} [options.style="disc"]
 * @param {"cloud"|"cypress"|"pine"} [options.type="cloud"] Silhoutte type for cutout
 * @param {number} [options.height=2.2] Total tree height
 * @param {number} [options.radius=0.7] Maximum foliage radius
 * @param {number} [options.tiers=4] Number of disc tiers
 * @param {boolean} [options.scalloped=true] Whether discs have wavy paper edges
 * @param {number} [options.trunkTone=TONES.DARK]
 * @param {number} [options.foliageTone=TONES.CARD]
 * @returns {THREE.Group}
 */
export function createPaperTree(options = {}) {
  const style = options.style || "disc";
  const height = options.height || 2.2;
  const radius = options.radius || 0.7;
  const foliageTone = options.foliageTone || TONES.CARD;
  const trunkTone = options.trunkTone || TONES.DARK;
  const group = new THREE.Group();

  if (style === "disc") {
    // 1. Central Tapered Trunk Stand with X-Slot Foot
    const trunkH = height * 0.95;
    const trunkRBottom = 0.05;
    const trunkRTop = 0.025;
    const trunkGeom = new THREE.CylinderGeometry(trunkRTop, trunkRBottom, trunkH, 8);
    const trunkMat = createPaperMaterial(trunkTone);
    const trunkMesh = new THREE.Mesh(trunkGeom, trunkMat);
    trunkMesh.position.y = trunkH / 2;
    group.add(trunkMesh);

    // X-Stand Foot (two interlocking paper card slats)
    const footW = radius * 0.6;
    const footH = 0.12;
    const footT = PAPER_DEFAULTS.thickness;
    const foot1 = createPaperCard(footW, footH, { depth: footT, tone: trunkTone });
    foot1.position.y = footH / 2;
    group.add(foot1);

    const foot2 = createPaperCard(footW, footH, { depth: footT, tone: trunkTone });
    foot2.rotateY(Math.PI / 2);
    foot2.position.y = footH / 2;
    group.add(foot2);

    // 2. Layered Foliage Discs stacked vertically
    const tiers = Math.max(2, options.tiers || 4);
    const startY = height * 0.32;
    const endY = height * 0.92;
    const yStep = (endY - startY) / (tiers - 1);

    const tones = [TONES.CARD, TONES.CREAM, TONES.MUTED, TONES.SHADOW];

    for (let i = 0; i < tiers; i++) {
      const t = i / (tiers - 1); // 0 at bottom, 1 at top
      const tierR = radius * (1.0 - t * 0.65);
      const tierY = startY + i * yStep;
      const tierTone = tones[i % tones.length];

      const discShape = new THREE.Shape();
      const segments = options.scalloped !== false ? 12 : 32;

      for (let s = 0; s < segments; s++) {
        const angle = (s / segments) * Math.PI * 2;
        // Subtle deckled wave on foliage disc perimeter
        const wave = options.scalloped !== false ? 1.0 + 0.08 * Math.sin(angle * 6) : 1.0;
        const r = tierR * wave;
        const px = r * Math.cos(angle);
        const py = r * Math.sin(angle);
        if (s === 0) discShape.moveTo(px, py);
        else discShape.lineTo(px, py);
      }
      discShape.closePath();

      // Center punch hole for trunk
      const centerHole = new THREE.Path();
      centerHole.absarc(0, 0, trunkRBottom * 0.8, 0, Math.PI * 2, false);
      discShape.holes.push(centerHole);

      const discGeom = extrudePaper(discShape, {
        depth: PAPER_DEFAULTS.thickness,
        bevelEnabled: true,
        bevelThickness: 0.005,
        bevelSize: 0.005
      });
      // Orient disc horizontally in X-Z plane
      discGeom.rotateX(-Math.PI / 2);

      const discMat = createPaperMaterial(tierTone);
      const discMesh = new THREE.Mesh(discGeom, discMat);
      discMesh.position.y = tierY;
      group.add(discMesh);
    }

    return group;
  }

  // 2. Cutout Silhouette Pop-Up Tree
  const type = options.type || "cloud";
  const layers = Math.max(2, options.layers || 3);
  const zSpacing = options.zSpacing || PAPER_DEFAULTS.zStep * 0.8;

  const tones = [TONES.CARD, TONES.CREAM, TONES.MUTED];

  for (let l = 0; l < layers; l++) {
    const layerScale = 1.0 - l * 0.08;
    const layerTone = tones[l % tones.length];
    const shape = new THREE.Shape();

    if (type === "cloud") {
      // Billowing deciduous oak foliage puffs
      shape.moveTo(0, 0);
      shape.lineTo(0.1, 0.4);
      // Puffs around crown
      const pts = [
        [0.4, 0.6], [0.7, 1.0], [0.65, 1.5], [0.35, 1.9],
        [0.0, 2.1], [-0.35, 1.9], [-0.65, 1.5], [-0.7, 1.0], [-0.4, 0.6]
      ];
      for (const p of pts) {
        shape.lineTo(p[0] * layerScale * radius * 1.4, p[1] * layerScale * (height / 2.1));
      }
      shape.lineTo(-0.1, 0.4);
      shape.lineTo(0, 0);
      shape.closePath();
    } else if (type === "cypress") {
      // Tall Italian cypress flame silhouette
      shape.moveTo(0, 0);
      shape.lineTo(0.08, 0.3);
      shape.lineTo(radius * 0.5 * layerScale, height * 0.5);
      shape.lineTo(radius * 0.3 * layerScale, height * 0.85);
      shape.lineTo(0, height * layerScale);
      shape.lineTo(-radius * 0.3 * layerScale, height * 0.85);
      shape.lineTo(-radius * 0.5 * layerScale, height * 0.5);
      shape.lineTo(-0.08, 0.3);
      shape.lineTo(0, 0);
      shape.closePath();
    } else {
      // Tiered conifer / pine tree
      shape.moveTo(0, 0);
      shape.lineTo(0.08, 0.3);
      const pineTiers = 4;
      for (let pt = 0; pt < pineTiers; pt++) {
        const yBase = 0.3 + pt * (height * 0.6 / pineTiers);
        const yTop = yBase + (height * 0.7 / pineTiers);
        const tierWidth = radius * (1.0 - pt * 0.22) * layerScale;
        shape.lineTo(tierWidth, yBase);
        shape.lineTo(tierWidth * 0.4, yTop);
      }
      shape.lineTo(0, height * layerScale);
      for (let pt = pineTiers - 1; pt >= 0; pt--) {
        const yBase = 0.3 + pt * (height * 0.6 / pineTiers);
        const yTop = yBase + (height * 0.7 / pineTiers);
        const tierWidth = radius * (1.0 - pt * 0.22) * layerScale;
        shape.lineTo(-tierWidth * 0.4, yTop);
        shape.lineTo(-tierWidth, yBase);
      }
      shape.lineTo(-0.08, 0.3);
      shape.lineTo(0, 0);
      shape.closePath();
    }

    const geom = extrudePaper(shape, { depth: PAPER_DEFAULTS.thickness });
    const mat = createPaperMaterial(layerTone);
    const mesh = new THREE.Mesh(geom, mat);
    // Stagger along Z: middle in front, others behind
    mesh.position.z = (l - (layers - 1) / 2) * zSpacing;
    group.add(mesh);
  }

  return group;
}

// ============================================================================
// 11. ROLLING PAPER HILLS (CURVED CONTOUR PLANES)
// ============================================================================

/**
 * Creates layered topographic paper hill silhouette planes.
 * Undulating contour card planes are staggered along the Z axis, receding into
 * distance and depth fog with graduated tone falloff.
 *
 * @param {Object} options
 * @param {number} [options.width=14.0] Total horizon width
 * @param {number} [options.height=2.8] Maximum hill crest height
 * @param {number} [options.minHeight=0.6] Minimum valley height
 * @param {number} [options.layers=4] Number of depth contour planes
 * @param {number} [options.zSpacing=0.8] Depth setback between successive hill cards
 * @param {number} [options.seed=42] Seed for deterministic undulation
 * @returns {THREE.Group}
 */
export function createRollingHills(options = {}) {
  const width = options.width || 14.0;
  const maxHeight = options.height || 2.8;
  const minHeight = options.minHeight || 0.6;
  const layers = Math.max(1, options.layers || 4);
  const zSpacing = options.zSpacing || 0.8;
  const seed = options.seed || 42;

  const group = new THREE.Group();
  const tones = [TONES.CARD, TONES.CREAM, TONES.MUTED, TONES.SHADOW, TONES.DARK];

  // Mulberry32 deterministic generator
  let s = seed >>> 0;
  const rnd = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  const halfW = width / 2;
  const segments = 24;
  const dx = width / segments;

  for (let l = 0; l < layers; l++) {
    const tone = tones[Math.min(l, tones.length - 1)];
    const layerH = minHeight + (maxHeight - minHeight) * (0.4 + 0.6 * (l / (layers || 1)));
    const shape = new THREE.Shape();

    // Start bottom-left
    shape.moveTo(-halfW, 0);

    // Top undulating ridge line
    const phase = rnd() * Math.PI * 2;
    const freq1 = 1.5 + rnd() * 1.5;
    const freq2 = 3.0 + rnd() * 2.0;

    for (let i = 0; i <= segments; i++) {
      const x = -halfW + i * dx;
      const nx = i / segments; // 0 to 1
      const wave = Math.sin(nx * Math.PI * freq1 + phase) * 0.6
                 + Math.sin(nx * Math.PI * freq2 + phase * 1.5) * 0.3;
      // Parabolic drape at edges to keep landscape grounded
      const drape = Math.sin(nx * Math.PI);
      const y = Math.max(0.1, layerH * (0.5 + 0.5 * wave * drape));
      shape.lineTo(x, y);
    }

    // Drop down bottom-right and close
    shape.lineTo(halfW, 0);
    shape.closePath();

    const geom = extrudePaper(shape, {
      depth: PAPER_DEFAULTS.thickness * 1.2,
      bevelEnabled: true,
      bevelThickness: 0.008,
      bevelSize: 0.008
    });

    const mat = createPaperMaterial(tone);
    const mesh = new THREE.Mesh(geom, mat);
    // Recede backwards in Z
    mesh.position.z = -l * zSpacing;
    group.add(mesh);
  }

  return group;
}

// ============================================================================
// 12. COLONNADES & ARCADES
// ============================================================================

/**
 * Creates a classical or modern paper colonnade with rhythmic columns,
 * stylobate base, architrave/entablature beam, and optional arch spans.
 *
 * @param {Object} options
 * @param {number} [options.count=6] Number of columns
 * @param {number} [options.spacing=0.8] Center-to-center column distance
 * @param {number} [options.height=2.4] Height of columns
 * @param {number} [options.columnRadius=0.08] Column shaft radius
 * @param {boolean} [options.arcade=true] Include arch connectors between columns
 * @param {"roman"|"pointed"|"horseshoe"} [options.archType="roman"]
 * @param {number} [options.tone=TONES.CARD]
 * @returns {THREE.Group}
 */
export function createColonnade(options = {}) {
  const count = Math.max(2, options.count || 6);
  const spacing = options.spacing || 0.8;
  const colH = options.height || 2.4;
  const colR = options.columnRadius || 0.08;
  const arcade = options.arcade !== false;
  const archType = options.archType || "roman";
  const tone = options.tone || TONES.CARD;
  const thickness = options.thickness || PAPER_DEFAULTS.thickness;

  const totalLength = (count - 1) * spacing;
  const group = new THREE.Group();

  // 1. Stepped Stylobate Base Plinth
  const baseW = totalLength + colR * 6;
  const baseH = 0.14;
  const baseD = colR * 4;
  const baseMesh = createPaperCard(baseW, baseH, { depth: baseD, tone: TONES.CREAM });
  baseMesh.position.set(0, baseH / 2, 0);
  group.add(baseMesh);

  // 2. Continuous Upper Entablature / Architrave Beam
  const entabW = totalLength + colR * 6;
  const entabH = 0.28;
  const entabD = colR * 3.5;
  const entabMesh = createPaperCard(entabW, entabH, { depth: entabD, tone: TONES.CREAM });
  entabMesh.position.set(0, baseH + colH + entabH / 2, 0);
  group.add(entabMesh);

  // 3. Individual Columns with Bases & Capitals
  const colMat = createPaperMaterial(tone);
  const capMat = createPaperMaterial(TONES.WHITE);

  for (let i = 0; i < count; i++) {
    const x = -totalLength / 2 + i * spacing;

    // Polygonal paper shaft (octagonal cylinder gives folded card feel)
    const shaftGeom = new THREE.CylinderGeometry(colR * 0.85, colR, colH, 8);
    const shaftMesh = new THREE.Mesh(shaftGeom, colMat);
    shaftMesh.position.set(x, baseH + colH / 2, 0);
    group.add(shaftMesh);

    // Capital card block
    const capCard = createPaperCard(colR * 3, 0.08, { depth: colR * 3, tone: TONES.WHITE });
    capCard.position.set(x, baseH + colH - 0.04, 0);
    group.add(capCard);

    // Base card block
    const baseCard = createPaperCard(colR * 3.2, 0.08, { depth: colR * 3.2, tone: TONES.WHITE });
    baseCard.position.set(x, baseH + 0.04, 0);
    group.add(baseCard);
  }

  // 4. Arched Spans between Columns (if arcade mode enabled)
  if (arcade) {
    const archSpan = spacing - colR * 2;
    const archApexH = archSpan * 0.6;
    const archSpringY = baseH + colH - archApexH;

    for (let i = 0; i < count - 1; i++) {
      const x = -totalLength / 2 + (i + 0.5) * spacing;
      const spandrel = createPunchedWall({
        width: spacing,
        height: archApexH + 0.05,
        thickness,
        tone: TONES.CARD,
        coping: false,
        backing: false,
        apertures: [{
          x: 0,
          y: 0,
          width: archSpan,
          height: archApexH,
          type: archType
        }]
      });
      spandrel.position.set(x, archSpringY, 0);
      group.add(spandrel);
    }
  }

  return group;
}

// ============================================================================
// 13. PAPER ROOFS (GABLE, MANSARD, ACCORDION, DOME)
// ============================================================================

/**
 * Creates a folded paper roof structure.
 *
 * @param {Object} options
 * @param {"gable"|"mansard"|"accordion"|"dome"} [options.style="gable"]
 * @param {number} [options.width=3.2] Roof span along X
 * @param {number} [options.depth=2.4] Roof depth along Z
 * @param {number} [options.height=1.2] Ridge apex height
 * @param {number} [options.overhang=0.12] Eaves overhang
 * @param {number} [options.tone=TONES.MUTED] Roof tile/sheet tone
 * @returns {THREE.Group}
 */
export function createPaperRoof(options = {}) {
  const style = options.style || "gable";
  const width = options.width || 3.2;
  const depth = options.depth || 2.4;
  const height = options.height || 1.2;
  const overhang = options.overhang || 0.12;
  const tone = options.tone || TONES.MUTED;
  const thickness = options.thickness || PAPER_DEFAULTS.thickness;

  const group = new THREE.Group();

  if (style === "gable") {
    // Triangular gable end-wall pediments (front and rear)
    const pedShape = new THREE.Shape();
    pedShape.moveTo(-width / 2, 0);
    pedShape.lineTo(width / 2, 0);
    pedShape.lineTo(0, height);
    pedShape.closePath();

    const pedGeom = extrudePaper(pedShape, { depth: thickness });
    const pedMat = createPaperMaterial(TONES.CREAM);

    const frontPed = new THREE.Mesh(pedGeom, pedMat);
    frontPed.position.z = depth / 2;
    group.add(frontPed);

    const rearPed = new THREE.Mesh(pedGeom, pedMat);
    rearPed.position.z = -depth / 2 - thickness;
    group.add(rearPed);

    // Pitched Slope Paper Cards (Left and Right)
    const slopeLen = Math.hypot(width / 2 + overhang, height) + overhang;
    const slopeAngle = Math.atan2(height, width / 2);
    const slopeDepth = depth + overhang * 2;

    const leftSlope = createPaperCard(slopeLen, slopeDepth, { depth: thickness, tone });
    leftSlope.rotateZ(slopeAngle);
    leftSlope.rotateX(Math.PI / 2);
    leftSlope.position.set(-width / 4, height / 2, 0);
    group.add(leftSlope);

    const rightSlope = createPaperCard(slopeLen, slopeDepth, { depth: thickness, tone });
    rightSlope.rotateZ(-slopeAngle);
    rightSlope.rotateX(Math.PI / 2);
    rightSlope.position.set(width / 4, height / 2, 0);
    group.add(rightSlope);

    // Ridge Capping Card (white highlight strip along the crest)
    const ridgeCap = createPaperCard(0.08, slopeDepth, { depth: thickness * 1.5, tone: TONES.WHITE });
    ridgeCap.rotateX(Math.PI / 2);
    ridgeCap.position.set(0, height + 0.02, 0);
    group.add(ridgeCap);

    return group;
  }

  if (style === "accordion") {
    // Modernist folded origami plate roof
    const folds = 8;
    const foldW = width / folds;
    const foldH = height * 0.4;
    const shape = new THREE.Shape();
    shape.moveTo(-width / 2, 0);

    for (let i = 0; i < folds; i++) {
      const x1 = -width / 2 + (i + 0.5) * foldW;
      const x2 = -width / 2 + (i + 1) * foldW;
      shape.lineTo(x1, foldH);
      shape.lineTo(x2, 0);
    }
    shape.lineTo(-width / 2, 0);
    shape.closePath();

    const geom = extrudePaper(shape, { depth });
    geom.translate(0, 0, -depth / 2);
    const mat = createPaperMaterial(tone);
    const mesh = new THREE.Mesh(geom, mat);
    group.add(mesh);
    return group;
  }

  if (style === "dome") {
    // Stepped concentric paper disc cupola
    const tiers = Math.max(3, options.tiers || 6);
    const domeR = Math.min(width, depth) / 2;
    const stepH = height / tiers;
    for (let i = 0; i < tiers; i++) {
      const t = i / tiers;
      const r = domeR * Math.cos(t * (Math.PI / 2));
      const disc = new THREE.CylinderGeometry(r * 0.95, r, stepH, 16);
      const discMat = createPaperMaterial(i % 2 === 0 ? tone : TONES.CREAM);
      const discMesh = new THREE.Mesh(disc, discMat);
      discMesh.position.y = (i + 0.5) * stepH;
      group.add(discMesh);
    }
    return group;
  }

  // Mansard / French Gambrel default fallback
  const mShape = new THREE.Shape();
  mShape.moveTo(-width / 2, 0);
  mShape.lineTo(-width / 3, height * 0.75);
  mShape.lineTo(0, height);
  mShape.lineTo(width / 3, height * 0.75);
  mShape.lineTo(width / 2, 0);
  mShape.closePath();

  const mGeom = extrudePaper(mShape, { depth });
  mGeom.translate(0, 0, -depth / 2);
  const mMat = createPaperMaterial(tone);
  const mMesh = new THREE.Mesh(mGeom, mMat);
  group.add(mMesh);

  return group;
}

// ============================================================================
// 14. BRIDGE DECKS (SEGMENTAL & ROMAN ARCH BRIDGES)
// ============================================================================

/**
 * Creates a modular paper bridge spanning a river or canal.
 * Features arch underpasses, roadbed deck with subtle camber curve,
 * parapet guardrails with punched decorative apertures, and pier cutwaters.
 *
 * @param {Object} options
 * @param {number} [options.length=6.0] Bridge span length along X
 * @param {number} [options.width=1.4] Roadbed deck width along Z
 * @param {number} [options.height=1.4] Deck elevation above water level
 * @param {number} [options.archCount=2] Number of arch spans (1, 2, or 3)
 * @param {"roman"|"segmental"|"pointed"} [options.archType="segmental"]
 * @param {number} [options.pierWidth=0.4] Width of mid-river piers
 * @param {number} [options.parapetHeight=0.28] Parapet balustrade height
 * @param {number} [options.camber=0.12] Crown height curvature of bridge deck
 * @param {number} [options.tone=TONES.CARD]
 * @returns {THREE.Group}
 */
export function createBridgeDeck(options = {}) {
  const length = options.length || 6.0;
  const width = options.width || 1.4;
  const height = options.height || 1.4;
  const archCount = Math.max(1, Math.min(3, options.archCount || 2));
  const archType = options.archType || "segmental";
  const pierW = archCount > 1 ? (options.pierWidth || 0.4) : 0;
  const parapetH = options.parapetHeight || 0.28;
  const camber = options.camber || 0.12;
  const tone = options.tone || TONES.CARD;
  const thickness = options.thickness || PAPER_DEFAULTS.thickness;

  const group = new THREE.Group();

  // Calculate arch span width
  const totalPierW = (archCount - 1) * pierW;
  const totalArchW = length - totalPierW - 0.8; // Setback at abutments
  const spanW = totalArchW / archCount;
  const spanH = height * 0.75;

  // 1. Spandrel Fascia Walls (Front and Rear Card Facings)
  const spandrelShape = new THREE.Shape();
  const halfL = length / 2;
  spandrelShape.moveTo(-halfL, 0);

  // Deck top line with camber curve
  const deckSegments = 20;
  for (let i = 0; i <= deckSegments; i++) {
    const x = -halfL + (i / deckSegments) * length;
    const nx = (x / halfL); // -1 to 1
    const y = height + camber * (1 - nx * nx);
    spandrelShape.lineTo(x, y);
  }
  spandrelShape.lineTo(halfL, 0);

  // Punch arch underpass holes
  const startX = -totalArchW / 2 + spanW / 2;
  for (let a = 0; a < archCount; a++) {
    const archCenterX = -halfL + 0.4 + spanW / 2 + a * (spanW + pierW);
    const hole = createArchPath({
      type: archType === "segmental" ? "roman" : archType,
      width: spanW,
      height: spanH,
      offsetX: archCenterX,
      offsetY: 0
    });
    spandrelShape.holes.push(hole);
  }
  spandrelShape.closePath();

  // Extrude front and rear spandrel walls
  const spandrelGeom = extrudePaper(spandrelShape, { depth: thickness });
  const spandrelMat = createPaperMaterial(tone);

  const frontWall = new THREE.Mesh(spandrelGeom, spandrelMat);
  frontWall.position.z = width / 2;
  group.add(frontWall);

  const rearWall = new THREE.Mesh(spandrelGeom, spandrelMat);
  rearWall.position.z = -width / 2 - thickness;
  group.add(rearWall);

  // 2. Roadbed Deck Slab (curved surface spanning between spandrel walls)
  const deckShape = new THREE.Shape();
  deckShape.moveTo(-halfL, 0);
  for (let i = 0; i <= deckSegments; i++) {
    const x = -halfL + (i / deckSegments) * length;
    const nx = (x / halfL);
    const y = height + camber * (1 - nx * nx);
    deckShape.lineTo(x, y);
  }
  deckShape.lineTo(halfL, height - 0.04);
  for (let i = deckSegments; i >= 0; i--) {
    const x = -halfL + (i / deckSegments) * length;
    const nx = (x / halfL);
    const y = height + camber * (1 - nx * nx) - 0.04;
    deckShape.lineTo(x, y);
  }
  deckShape.closePath();

  const deckGeom = extrudePaper(deckShape, { depth: width });
  deckGeom.translate(0, 0, -width / 2);
  const deckMat = createPaperMaterial(TONES.MUTED);
  const deckMesh = new THREE.Mesh(deckGeom, deckMat);
  group.add(deckMesh);

  // 3. Parapet Balustrades with Decorative Punched Apertures
  const parapetShape = new THREE.Shape();
  parapetShape.moveTo(-halfL, 0);
  for (let i = 0; i <= deckSegments; i++) {
    const x = -halfL + (i / deckSegments) * length;
    const nx = (x / halfL);
    const y = height + camber * (1 - nx * nx) + parapetH;
    parapetShape.lineTo(x, y);
  }
  parapetShape.lineTo(halfL, height);
  for (let i = deckSegments; i >= 0; i--) {
    const x = -halfL + (i / deckSegments) * length;
    const nx = (x / halfL);
    const y = height + camber * (1 - nx * nx);
    parapetShape.lineTo(x, y);
  }
  parapetShape.closePath();

  // Punch ornamental balustrade slots along the parapet
  const slotCount = Math.floor(length * 2.5);
  const slotW = 0.12;
  const slotH = parapetH * 0.45;
  for (let s = 1; s < slotCount; s++) {
    const sx = -halfL + (s / slotCount) * length;
    const snx = sx / halfL;
    const sy = height + camber * (1 - snx * snx) + parapetH * 0.28;
    const slot = new THREE.Path();
    slot.moveTo(sx - slotW / 2, sy);
    slot.lineTo(sx + slotW / 2, sy);
    slot.lineTo(sx + slotW / 2, sy + slotH);
    slot.lineTo(sx - slotW / 2, sy + slotH);
    slot.closePath();
    parapetShape.holes.push(slot);
  }

  const parapetGeom = extrudePaper(parapetShape, { depth: thickness });
  const parapetMat = createPaperMaterial(TONES.WHITE);

  const frontParapet = new THREE.Mesh(parapetGeom, parapetMat);
  frontParapet.position.z = width / 2 + thickness;
  group.add(frontParapet);

  const rearParapet = new THREE.Mesh(parapetGeom, parapetMat);
  rearParapet.position.z = -width / 2 - thickness * 2;
  group.add(rearParapet);

  // 4. Triangular Pier Cutwaters (for multi-arch river bridges)
  if (archCount > 1) {
    const cutwaterW = pierW * 1.5;
    const cutwaterH = spanH * 0.85;
    const cutwaterD = 0.35;

    for (let p = 0; p < archCount - 1; p++) {
      const px = -halfL + 0.4 + spanW + p * (spanW + pierW) + pierW / 2;

      // Triangular wedge shape
      const wedgeShape = new THREE.Shape();
      wedgeShape.moveTo(-cutwaterW / 2, 0);
      wedgeShape.lineTo(cutwaterW / 2, 0);
      wedgeShape.lineTo(0, cutwaterD);
      wedgeShape.closePath();

      const wedgeGeom = extrudePaper(wedgeShape, { depth: cutwaterH });
      wedgeGeom.rotateX(-Math.PI / 2);
      const wedgeMat = createPaperMaterial(TONES.CREAM);

      // Front Cutwater
      const frontWedge = new THREE.Mesh(wedgeGeom, wedgeMat);
      frontWedge.position.set(px, 0, width / 2 + thickness);
      group.add(frontWedge);

      // Rear Cutwater
      const rearWedge = new THREE.Mesh(wedgeGeom, wedgeMat);
      rearWedge.rotateY(Math.PI);
      rearWedge.position.set(px, 0, -width / 2 - thickness);
      group.add(rearWedge);
    }
  }

  return group;
}

// ============================================================================
// 15. STAGE LIGHTING & LINEAR DEPTH FOG RIG
// ============================================================================

/**
 * Sets up the shadowless 3-point stage lighting rig and linear depth fog
 * optimized for paper dioramas. Conforms strictly to the Veasy 370ms budget.
 *
 * @param {THREE.Scene} scene The target Three.js scene
 * @param {Object} [options={}] Lighting parameters
 * @param {number} [options.keyIntensity=2.0] Main directional spotlight intensity
 * @param {THREE.Vector3|Array<number>} [options.keyPosition=[-5, 8, 4]]
 * @param {number} [options.fillIntensity=1.15] Hemisphere ambient fill intensity
 * @param {number} [options.rimIntensity=0.9] Backlight rim kicker intensity
 * @param {THREE.Vector3|Array<number>} [options.rimPosition=[4.5, 3, -6]]
 * @param {number} [options.fogNear=7.0] Fog start distance
 * @param {number} [options.fogFar=24.0] Fog end distance (pure canvas black)
 * @returns {Object} { keyLight, fillLight, rimLight, fog }
 */
export function setupPaperStage(scene, options = {}) {
  // 1. Stage Void Background
  scene.background = new THREE.Color(0x000000);

  // 2. Linear Depth Fog
  const fogNear = options.fogNear !== undefined ? options.fogNear : 7.0;
  const fogFar = options.fogFar !== undefined ? options.fogFar : 24.0;
  const fog = new THREE.Fog(0x000000, fogNear, fogFar);
  scene.fog = fog;

  // 3. Ambient Hemisphere Fill (diffuse ceiling bounce / dark ground)
  const fillIntensity = options.fillIntensity !== undefined ? options.fillIntensity : 1.15;
  const fillLight = new THREE.HemisphereLight(0xe8e8e8, 0x222222, fillIntensity);
  scene.add(fillLight);

  // 4. Key Directional Light (high off-axis, sculpts paper facets & bevels)
  const keyIntensity = options.keyIntensity !== undefined ? options.keyIntensity : 2.0;
  const keyLight = new THREE.DirectionalLight(0xffffff, keyIntensity);
  const keyPos = options.keyPosition || [-5.0, 8.0, 4.0];
  if (Array.isArray(keyPos)) keyLight.position.set(...keyPos);
  else keyLight.position.copy(keyPos);
  keyLight.castShadow = false; // Strictly disabled for budget (saves 533ms)
  scene.add(keyLight);

  // 5. Rim Kicker / Backlight (separates cardstock layers against black void)
  const rimIntensity = options.rimIntensity !== undefined ? options.rimIntensity : 0.9;
  const rimLight = new THREE.DirectionalLight(0xffffff, rimIntensity);
  const rimPos = options.rimPosition || [4.5, 3.0, -6.0];
  if (Array.isArray(rimPos)) rimLight.position.set(...rimPos);
  else rimLight.position.copy(rimPos);
  rimLight.castShadow = false;
  scene.add(rimLight);

  return { keyLight, fillLight, rimLight, fog };
}

/**
 * Creates a circular or rectangular paper stage floor ground plane.
 *
 * @param {Object} options
 * @param {number} [options.radius=5.0] Ground radius
 * @param {number} [options.tone=TONES.DARK] Ground tone
 * @returns {THREE.Mesh}
 */
export function createStageFloor(options = {}) {
  const radius = options.radius || 5.0;
  const tone = options.tone || TONES.DARK;
  const segments = options.segments || 32;

  const shape = new THREE.Shape();
  shape.absarc(0, 0, radius, 0, Math.PI * 2, false);

  const geom = extrudePaper(shape, {
    depth: PAPER_DEFAULTS.thickness * 2,
    bevelEnabled: true,
    bevelThickness: 0.01,
    bevelSize: 0.01
  });
  geom.rotateX(-Math.PI / 2);

  const mat = createPaperMaterial(tone);
  const mesh = new THREE.Mesh(geom, mat);
  mesh.position.y = -PAPER_DEFAULTS.thickness * 2;
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  return mesh;
}
