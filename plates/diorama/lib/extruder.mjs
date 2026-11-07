/**
 * plates/diorama/lib/extruder.mjs
 * 
 * Vector Drawing to Freestanding Miniature Paper Standee Extruder.
 * Part of the Veasy Paper Stage Diorama Engine (plates/diorama/).
 * 
 * Historical & Physical Inspiration:
 * - Victorian Toy Theatres (Benjamin Pollock, George Speaight, Webb's, 1850s-1900s):
 *   Printed cardstock characters cut with a protective margin, folded or slotted at the base,
 *   standing in wooden or tin stage sliders.
 * - Tabletop Cardboard Miniatures (Pathfinder Pawns, Steve Jackson Cardboard Heroes):
 *   Die-cut character silhouettes with bottom insertion tabs mounted into slotted disc pedestals.
 * 
 * Technical Architecture:
 * 1. Tone-Only Token Mapping: Brand tokens (LINE, INK, MUTED, ACCENT, CANVAS) are mapped
 *    to calibrated paper stage grey values (TONES from kit.mjs) on pure black canvas (#000000).
 * 2. Robust SVG Parsing: Wraps SVG snippet and parses with SVGLoader. Includes a built-in
 *    pure-JS mini-DOM parser for Node.js test environments and uses native DOMParser in browsers.
 * 3. 100% Watertight Geometry:
 *    - Open paths & lines are thickened into planar ribbon quads via SVGLoader.pointsToStroke
 *      with deduplicated vertices to eliminate zero-length direction errors and NaNs.
 *    - Closed filled shapes are triangulated with ShapeGeometry with area verification.
 * 4. Extruded Paper Backing Card:
 *    - Connects all disconnected/floating drawing parts (wheels, windows, antennas, sun rays)
 *      into a single monolithic physical cardboard body with paper thickness (0.035) and cut bevels.
 *    - Features an integrated bottom mounting tab that extends down into the pedestal base slot.
 * 5. Slotted Foot Pedestal:
 *    - Extruded paper foot/base (disc CylinderGeometry or rectangular BoxGeometry) with a physical
 *      vertical mounting slot channel where the card tab seats.
 *    - Ground anchor: Pedestal bottom rests flush on diorama floor at y = 0.
 * 6. Normalization & Anchors:
 *    - Normalizes drawing height to standard height (default 2.0 units), centered horizontally at x = 0.
 *    - Tracks ACCENT token (focal dot) and exports 3D position in standee.userData.anchors.dot.
 */

import * as THREE from "three";
import { SVGLoader } from "three/addons/loaders/SVGLoader.js";
import { TONES, PAPER_DEFAULTS, createPaperMaterial, extrudePaper } from "./kit.mjs";

// ============================================================================
// 1. DOMPARSER SHIM FOR NODE.JS ENVIRONMENTS
// ============================================================================

/**
 * Lightweight XML/SVG element parser used only in non-browser (Node.js) test runners
 * where globalThis.DOMParser is not natively defined. In browser/puppeteer environments,
 * the native high-performance DOMParser is used directly.
 */
function parseXMLMini(xmlStr) {
  const tagRegex = /<([a-zA-Z0-9\-:]+)([^>]*?)(\/?>)|<\/([a-zA-Z0-9\-:]+)>|([^<]+)/gs;
  function createNode(name, attrsStr) {
    const attrs = {};
    const attrRegex = /([a-zA-Z0-9\-:]+)="([^"]*)"/g;
    let m;
    while ((m = attrRegex.exec(attrsStr)) !== null) attrs[m[1]] = m[2];
    return {
      nodeType: 1,
      nodeName: name,
      attributes: attrs,
      childNodes: [],
      hasAttribute(k) { return attrs[k] !== undefined; },
      getAttribute(k) { return attrs[k] !== undefined ? attrs[k] : null; },
      getAttributeNS(ns, k) { return attrs[k] !== undefined ? attrs[k] : null; },
      viewportElement: null,
      sheet: null,
      style: new Proxy({}, { get: () => "" })
    };
  }

  const root = { nodeType: 9, childNodes: [], documentElement: null };
  const stack = [root];
  let match;

  while ((match = tagRegex.exec(xmlStr)) !== null) {
    const [full, openTag, attrsStr, selfClose, closeTag, text] = match;
    if (openTag) {
      const node = createNode(openTag, attrsStr);
      stack[stack.length - 1].childNodes.push(node);
      if (!root.documentElement && openTag === "svg") root.documentElement = node;
      if (!selfClose || !selfClose.endsWith("/>")) stack.push(node);
    } else if (closeTag && stack.length > 1 && stack[stack.length - 1].nodeName === closeTag) {
      stack.pop();
    }
  }

  return root;
}

if (typeof globalThis.DOMParser === "undefined") {
  globalThis.DOMParser = class {
    parseFromString(str) {
      return parseXMLMini(str);
    }
  };
}

// ============================================================================
// 2. CONFIGURATION DEFAULTS & TONE MAPPINGS
// ============================================================================

export const STANDEE_DEFAULTS = Object.freeze({
  standardHeight: 2.0,       // Standard visual height of the figure in world units
  paperThickness: 0.035,     // 300gsm cardstock thickness (0.02 - 0.05)
  bevelThickness: 0.005,     // Cut paper micro-bevel
  bevelSize: 0.004,          // Edge chamfer size
  bevelSegments: 1,          // Crisp cut facet
  margin: 0.12,              // Card border padding around vector artwork
  cornerRadius: 0.06,        // Rounded corner radius on paper card
  cardStyle: "rounded",      // "rounded" | "arched" | "rectangular"
  baseType: "disc",          // "disc" | "pedestal" | "plinth"
  baseHeight: 0.08,          // Pedestal elevation above floor
  baseRadius: 0.55,          // Disc base default radius
  slotDepth: 0.04,           // Depth of mounting slot channel
  slotClearance: 0.012,      // Extra slot width clearance over paper thickness
  tabHeight: 0.055           // Tab extension below card bottom into slot
});

/**
 * Greyscale hex values mapping brand tokens to diorama paper tones.
 */
export const STANDEE_TONES = Object.freeze({
  CANVAS: "#383838", // Dark backing fill (TONES.DARK)
  LINE:   "#6e6e6e", // Faint structural linework (TONES.SHADOW)
  MUTED:  "#a2a2a2", // Secondary detail strokes (TONES.MUTED)
  INK:    "#f6f6f6", // Primary contour lines and hero marks (TONES.WHITE)
  ACCENT: "#ffffff", // Hero accent highlight / dot
  CARD:   "#e2e2e2", // Cut cardstock body (TONES.CARD)
  BASE:   "#d0d0d0"  // Pedestal base tone (TONES.CREAM)
});

// ============================================================================
// 3. SVG TOKEN PRE-PROCESSING & BOUNDS COMPUTATION
// ============================================================================

/**
 * Wraps and token-substitutes an SVG snippet into standard XML parseable by SVGLoader.
 *
 * @param {string} svgFragment Raw SVG fragment from drawing JSON
 * @param {Object} [toneMap=STANDEE_TONES] Color token replacements
 * @returns {string} Fully formed <svg> document string
 */
export function prepareDrawingSVG(svgFragment, toneMap = STANDEE_TONES) {
  let svg = `<svg viewBox="0 0 952 640" xmlns="http://www.w3.org/2000/svg">${svgFragment}</svg>`;
  svg = svg
    .replace(/stroke="LINE"/g, `stroke="${toneMap.LINE}"`)
    .replace(/stroke="INK"/g, `stroke="${toneMap.INK}"`)
    .replace(/stroke="MUTED"/g, `stroke="${toneMap.MUTED}"`)
    .replace(/stroke="ACCENT"/g, `stroke="${toneMap.ACCENT}"`)
    .replace(/fill="CANVAS"/g, `fill="${toneMap.CANVAS}"`)
    .replace(/fill="INK"/g, `fill="${toneMap.INK}"`)
    .replace(/fill="MUTED"/g, `fill="${toneMap.MUTED}"`)
    .replace(/fill="ACCENT"/g, `fill="${toneMap.ACCENT}"`);
  return svg;
}

/**
 * Computes exact 2D bounding box across all parsed ShapePath subpaths.
 *
 * @param {Array<THREE.ShapePath>} paths Array of parsed paths from SVGLoader
 * @returns {{minX: number, minY: number, maxX: number, maxY: number, width: number, height: number}}
 */
export function computeDrawingBounds(paths) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const p of paths) {
    for (const sub of p.subPaths) {
      const pts = sub.getPoints();
      for (const pt of pts) {
        if (pt.x < minX) minX = pt.x;
        if (pt.x > maxX) maxX = pt.x;
        if (pt.y < minY) minY = pt.y;
        if (pt.y > maxY) maxY = pt.y;
      }
    }
  }

  // Fallback to standard drawing canvas viewBox (952 x 640) if empty
  if (!isFinite(minX) || !isFinite(maxX) || minX >= maxX || minY >= maxY) {
    minX = 40;
    maxX = 912;
    minY = 100;
    maxY = 560;
  }

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY
  };
}

// ============================================================================
// 4. CUT-OUT PAPER BACKING CARD WITH INTEGRATED MOUNTING TAB
// ============================================================================

/**
 * Creates the 2D THREE.Shape for the cut cardstock standee backing.
 * Features an integrated rectangular tab at the bottom that inserts into the pedestal slot,
 * ensuring the card is a single watertight extruded mesh without separate fragile joints.
 *
 * @param {number} cardWidth Width of the card body
 * @param {number} cardHeight Height of the card body
 * @param {number} baseHeight Elevation of the pedestal top surface
 * @param {number} tabWidth Width of the bottom mounting tab
 * @param {number} slotDepth Depth of the pedestal slot
 * @param {Object} [options={}]
 * @returns {THREE.Shape}
 */
export function createPaperCardShape(cardWidth, cardHeight, baseHeight, tabWidth, slotDepth, options = {}) {
  const shape = new THREE.Shape();
  const halfW = cardWidth / 2;
  const cornerR = Math.min(options.cornerRadius || STANDEE_DEFAULTS.cornerRadius, cardWidth * 0.15);
  const cardStyle = options.cardStyle || STANDEE_DEFAULTS.cardStyle;

  const yCardBottom = baseHeight;
  const yCardTop = baseHeight + cardHeight;
  const tabHalfW = tabWidth / 2;
  const yTabBottom = baseHeight - slotDepth + 0.005; // Sits 5mm above slot bottom to avoid clipping

  // 1. Mounting Tab Bottom
  shape.moveTo(-tabHalfW, yTabBottom);
  shape.lineTo(tabHalfW, yTabBottom);
  shape.lineTo(tabHalfW, yCardBottom);

  // 2. Card Bottom-Right
  shape.lineTo(halfW - cornerR, yCardBottom);
  shape.absarc(halfW - cornerR, yCardBottom + cornerR, cornerR, -Math.PI / 2, 0, false);

  // 3. Card Top
  if (cardStyle === "arched") {
    // Victorian Proscenium Arch Top: smoothly crowns the upper card without dipping
    const archH = Math.min(halfW * 0.5, cardHeight * 0.25);
    const springY = yCardTop - archH;
    shape.lineTo(halfW, springY);
    shape.quadraticCurveTo(halfW, yCardTop, 0, yCardTop);
    shape.quadraticCurveTo(-halfW, yCardTop, -halfW, springY);
    shape.lineTo(-halfW, yCardBottom + cornerR);
  } else {
    // Classic Rounded Corner Card
    shape.lineTo(halfW, yCardTop - cornerR);
    shape.absarc(halfW - cornerR, yCardTop - cornerR, cornerR, 0, Math.PI / 2, false);
    shape.lineTo(-halfW + cornerR, yCardTop);
    shape.absarc(-halfW + cornerR, yCardTop - cornerR, cornerR, Math.PI / 2, Math.PI, false);
    shape.lineTo(-halfW, yCardBottom + cornerR);
  }

  // 4. Card Bottom-Left back to Tab
  shape.absarc(-halfW + cornerR, yCardBottom + cornerR, cornerR, Math.PI, Math.PI * 1.5, false);
  shape.lineTo(-tabHalfW, yCardBottom);
  shape.closePath();

  return shape;
}

// ============================================================================
// 5. SLOTTED PEDESTAL BASE (DISC, PEDESTAL BOX, TIERED PLINTH)
// ============================================================================

/**
 * A card cut around the drawing, as a toy theatre's actor is: the convex hull of its points grown by a margin, with
 * the mounting tab. A hull is always one simple outline, so no drawing can break it.
 *
 * @param {Array<[number, number]>} points Drawing points in card space
 * @param {number} margin Paper left around the drawing
 * @param {[number, number]} tab Half width of the tab and the y of its foot
 * @returns {THREE.Shape}
 */
export function createCutoutShape(points, margin, [tabHalf, tabFoot]) {
  const grown = [[-tabHalf, tabFoot], [tabHalf, tabFoot]];
  for (const [x, y] of points) {
    for (let i = 0; i < 12; i++) {
      const a = i * Math.PI / 6;
      grown.push([x + margin * Math.cos(a), y + margin * Math.sin(a)]);
    }
  }
  grown.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const half = (list) => {
    const hull = [];
    for (const p of list) {
      while (hull.length >= 2 && cross(hull[hull.length - 2], hull[hull.length - 1], p) <= 0) hull.pop();
      hull.push(p);
    }
    return hull.slice(0, -1);
  };
  const hull = [...half(grown), ...half([...grown].reverse())];
  return new THREE.Shape(hull.map(([x, y]) => new THREE.Vector2(x, y)));
}

/**
 * Builds the freestanding paper foot/pedestal with a physical vertical mounting slot.
 *
 * @param {number} cardWidth Width of the standee card
 * @param {number} tabWidth Width of the insertion tab
 * @param {Object} [options={}] Base configuration options
 * @returns {THREE.Group} Pedestal group grounded at y = 0
 */
export function createSlottedPedestal(cardWidth, tabWidth, options = {}) {
  const baseType = options.baseType || STANDEE_DEFAULTS.baseType;
  const baseHeight = options.baseHeight || STANDEE_DEFAULTS.baseHeight;
  const paperThickness = options.paperThickness || STANDEE_DEFAULTS.paperThickness;
  const slotDepth = options.slotDepth || STANDEE_DEFAULTS.slotDepth;
  const slotW = paperThickness + (options.slotClearance || STANDEE_DEFAULTS.slotClearance);
  const slotL = tabWidth + 0.04;
  const baseMat = options.material || createPaperMaterial(TONES.CREAM);

  const group = new THREE.Group();
  group.name = `base_${baseType}`;

  if (baseType === "disc") {
    // --- CIRCULAR SLOTTED DISC ---
    const radius = Math.max(cardWidth * 0.42, options.baseRadius || STANDEE_DEFAULTS.baseRadius);
    const bottomH = Math.max(baseHeight - slotDepth, 0.02);

    // Solid base disc slab resting on y=0
    const bottomGeom = new THREE.CylinderGeometry(radius, radius, bottomH, 32);
    bottomGeom.translate(0, bottomH / 2, 0);
    const bottomMesh = new THREE.Mesh(bottomGeom, baseMat);
    bottomMesh.castShadow = false;
    bottomMesh.receiveShadow = false;
    group.add(bottomMesh);

    // Slotted top collar extruded from a circle with a centered rectangular slot hole
    const capShape = new THREE.Shape();
    capShape.absarc(0, 0, radius, 0, Math.PI * 2, false);

    const slotHole = new THREE.Path();
    slotHole.moveTo(-slotL / 2, -slotW / 2);
    slotHole.lineTo(slotL / 2, -slotW / 2);
    slotHole.lineTo(slotL / 2, slotW / 2);
    slotHole.lineTo(-slotL / 2, slotW / 2);
    slotHole.closePath();
    capShape.holes.push(slotHole);

    const capGeom = new THREE.ExtrudeGeometry(capShape, {
      depth: slotDepth,
      bevelEnabled: false,
      curveSegments: 24
    });
    // Rotate from XY plane to XZ floor plane
    capGeom.rotateX(Math.PI / 2);
    capGeom.translate(0, baseHeight, 0);
    const capMesh = new THREE.Mesh(capGeom, baseMat);
    capMesh.castShadow = false;
    capMesh.receiveShadow = false;
    group.add(capMesh);

  } else if (baseType === "plinth") {
    // --- TIERED EXHIBITION PLINTH ---
    const lowerW = cardWidth * 0.95;
    const lowerD = 0.50;
    const lowerH = baseHeight * 0.45;

    const lowerGeom = new THREE.BoxGeometry(lowerW, lowerH, lowerD);
    lowerGeom.translate(0, lowerH / 2, 0);
    group.add(new THREE.Mesh(lowerGeom, createPaperMaterial(TONES.MUTED)));

    const upperW = cardWidth * 0.80;
    const upperD = 0.36;
    const upperH = baseHeight - lowerH;
    const uSlotDepth = slotDepth;

    // Upper base solid slab
    const uSolidH = upperH - uSlotDepth;
    const uSolidGeom = new THREE.BoxGeometry(upperW, uSolidH, upperD);
    uSolidGeom.translate(0, lowerH + uSolidH / 2, 0);
    group.add(new THREE.Mesh(uSolidGeom, baseMat));

    // Upper slotted cheeks
    const flankW = (upperW - slotL) / 2;
    if (flankW > 0.01) {
      const leftGeom = new THREE.BoxGeometry(flankW, uSlotDepth, upperD);
      leftGeom.translate(-upperW / 2 + flankW / 2, baseHeight - uSlotDepth / 2, 0);
      group.add(new THREE.Mesh(leftGeom, baseMat));

      const rightGeom = new THREE.BoxGeometry(flankW, uSlotDepth, upperD);
      rightGeom.translate(upperW / 2 - flankW / 2, baseHeight - uSlotDepth / 2, 0);
      group.add(new THREE.Mesh(rightGeom, baseMat));
    }
    const cheekD = (upperD - slotW) / 2;
    if (cheekD > 0.01) {
      const frontGeom = new THREE.BoxGeometry(slotL, uSlotDepth, cheekD);
      frontGeom.translate(0, baseHeight - uSlotDepth / 2, -upperD / 2 + cheekD / 2);
      group.add(new THREE.Mesh(frontGeom, baseMat));

      const backGeom = new THREE.BoxGeometry(slotL, uSlotDepth, cheekD);
      backGeom.translate(0, baseHeight - uSlotDepth / 2, upperD / 2 - cheekD / 2);
      group.add(new THREE.Mesh(backGeom, baseMat));
    }

  } else {
    // --- RECTANGULAR BOX PEDESTAL ---
    const pedW = Math.max(cardWidth * 0.85, slotL + 0.08);
    const pedD = Math.max(cardWidth * 0.35, 0.40);
    const bottomH = Math.max(baseHeight - slotDepth, 0.02);

    // Bottom solid plate
    const bottomGeom = new THREE.BoxGeometry(pedW, bottomH, pedD);
    bottomGeom.translate(0, bottomH / 2, 0);
    group.add(new THREE.Mesh(bottomGeom, baseMat));

    // Flanks and cheeks enclosing slot
    const flankW = (pedW - slotL) / 2;
    if (flankW > 0.01) {
      const leftGeom = new THREE.BoxGeometry(flankW, slotDepth, pedD);
      leftGeom.translate(-pedW / 2 + flankW / 2, baseHeight - slotDepth / 2, 0);
      group.add(new THREE.Mesh(leftGeom, baseMat));

      const rightGeom = new THREE.BoxGeometry(flankW, slotDepth, pedD);
      rightGeom.translate(pedW / 2 - flankW / 2, baseHeight - slotDepth / 2, 0);
      group.add(new THREE.Mesh(rightGeom, baseMat));
    }
    const cheekD = (pedD - slotW) / 2;
    if (cheekD > 0.01) {
      const frontGeom = new THREE.BoxGeometry(slotL, slotDepth, cheekD);
      frontGeom.translate(0, baseHeight - slotDepth / 2, -pedD / 2 + cheekD / 2);
      group.add(new THREE.Mesh(frontGeom, baseMat));

      const backGeom = new THREE.BoxGeometry(slotL, slotDepth, cheekD);
      backGeom.translate(0, baseHeight - slotDepth / 2, pedD / 2 - cheekD / 2);
      group.add(new THREE.Mesh(backGeom, baseMat));
    }
  }

  return group;
}

// ============================================================================
// 6. DRAWING ARTWORK VECTOR GEOMETRY EXTRUSION
// ============================================================================

/**
 * Converts parsed SVG paths into watertight 3D meshes positioned on the card face.
 * Handles both closed filled shapes (ShapeGeometry) and open stroked paths (pointsToStroke).
 *
 * @param {Array<THREE.ShapePath>} paths Parsed ShapePath array
 * @param {Object} bounds 2D bounding box
 * @param {number} scale Normalization scale factor
 * @param {number} baseHeight Pedestal top elevation
 * @param {number} margin Padding above pedestal
 * @param {number} zFront Z-plane coordinate for front face
 * @param {Object} materials Material dictionary
 * @returns {{group: THREE.Group, dotAnchor: THREE.Vector3|null}}
 */
export function buildStandeeArtworkGeometry(paths, bounds, scale, baseHeight, margin, zFront, materials) {
  const artGroup = new THREE.Group();
  artGroup.name = "standee_artwork";

  const cxSvg = (bounds.minX + bounds.maxX) / 2;
  const maxYSvg = bounds.maxY;
  let dotAnchor = null;

  for (const p of paths) {
    const style = p.userData.style || {};
    const node = p.userData.node;

    // Detect role and material from SVG style and node attributes
    const rawStroke = node ? node.getAttribute("stroke") : null;
    const rawFill = node ? node.getAttribute("fill") : null;

    const isAccent = rawStroke === "ACCENT" || rawFill === "ACCENT" ||
                     style.stroke === "#ffffff" || style.fill === "#ffffff";
    const isDark = rawFill === "CANVAS" || style.fill === "#383838";
    const isMuted = rawStroke === "MUTED" || rawFill === "MUTED" ||
                    style.stroke === "#a2a2a2" || style.fill === "#a2a2a2";
    const isLine = rawStroke === "LINE" || style.stroke === "#6e6e6e";

    let mat = materials.ink;
    if (isDark) mat = materials.canvas;
    else if (isLine) mat = materials.line;
    else if (isMuted) mat = materials.muted;
    else if (isAccent) mat = materials.accent;

    // 1. Closed Filled Shapes
    if (rawFill && rawFill !== "none") { // SVG fills black by default, but these drawings mean line unless they say fill
      const shapes = SVGLoader.createShapes(p);
      for (const sh of shapes) {
        const pts = sh.getPoints();
        // Skip degenerate lines auto-closed into 0-area polygons
        if (pts.length < 3) continue;

        let area = 0;
        for (let i = 0; i < pts.length; i++) {
          const j = (i + 1) % pts.length;
          area += pts[i].x * pts[j].y - pts[j].x * pts[i].y;
        }
        if (Math.abs(area) < 1e-4) continue;

        const geom = new THREE.ShapeGeometry(sh);
        const pos = geom.attributes.position;
        let hasNaN = false;

        for (let i = 0; i < pos.count; i++) {
          const xSvg = pos.getX(i);
          const ySvg = pos.getY(i);
          const x3d = (xSvg - cxSvg) * scale;
          const y3d = baseHeight + margin + (maxYSvg - ySvg) * scale;
          const z3d = zFront + (isDark ? 0.001 : 0.003);

          if (isNaN(x3d) || isNaN(y3d)) {
            hasNaN = true;
            break;
          }
          pos.setXY(i, x3d, y3d);
          pos.setZ(i, z3d);
        }

        if (!hasNaN) {
          geom.computeVertexNormals();
          const mesh = new THREE.Mesh(geom, mat);
          mesh.userData.flat = true;
          mesh.castShadow = false;
          mesh.receiveShadow = false;
          artGroup.add(mesh);
        }
      }
    }

    // 2. Open & Closed Stroked Paths (Ribbon Quads)
    if (style.stroke && style.stroke !== "none") {
      for (const sub of p.subPaths) {
        const pts = sub.getPoints();
        if (pts.length < 2) continue;

        // Deduplicate coincident points to avoid 0-length tangent division NaNs
        const cleanPts = [pts[0]];
        for (let i = 1; i < pts.length; i++) {
          const prev = cleanPts[cleanPts.length - 1];
          const cur = pts[i];
          const dist = Math.hypot(cur.x - prev.x, cur.y - prev.y);
          if (dist > 1e-4) cleanPts.push(cur);
        }
        if (cleanPts.length < 2) continue;

        const sGeom = SVGLoader.pointsToStroke(cleanPts, style);
        if (sGeom) {
          const pos = sGeom.attributes.position;
          let hasNaN = false;

          for (let i = 0; i < pos.count; i++) {
            const xSvg = pos.getX(i);
            const ySvg = pos.getY(i);
            const x3d = (xSvg - cxSvg) * scale;
            const y3d = baseHeight + margin + (maxYSvg - ySvg) * scale;
            const z3d = zFront + (isAccent ? 0.006 : 0.004);

            if (isNaN(x3d) || isNaN(y3d)) {
              hasNaN = true;
              break;
            }
            pos.setXY(i, x3d, y3d);
            pos.setZ(i, z3d);
          }

          if (!hasNaN) {
            sGeom.computeVertexNormals();
            const strokeMesh = new THREE.Mesh(sGeom, mat);
            strokeMesh.userData.flat = true;
            strokeMesh.castShadow = false;
            strokeMesh.receiveShadow = false;
            artGroup.add(strokeMesh);
          }
        }
      }
    }

    // 3. Focal Accent Dot Anchor Extraction
    if (isAccent && !dotAnchor && node && node.nodeName === "circle") {
      const cx = parseFloat(node.getAttribute("cx") || "0");
      const cy = parseFloat(node.getAttribute("cy") || "0");
      if (isFinite(cx) && isFinite(cy) && (cx !== 0 || cy !== 0)) {
        dotAnchor = new THREE.Vector3(
          (cx - cxSvg) * scale,
          baseHeight + margin + (maxYSvg - cy) * scale,
          zFront + 0.015
        );
      }
    }
  }

  return { artGroup, dotAnchor };
}

// ============================================================================
// 7. PUBLIC API: CREATE STANDEE FROM DRAWING OR SVG
// ============================================================================

/**
 * Creates a freestanding miniature paper figure (standee) from a Veasy vector drawing JSON.
 *
 * @param {Object} drawingData Drawing JSON object { motif, about, svg }
 * @param {Object} [options={}] Standee geometry, scale and pedestal options
 * @returns {THREE.Group} Standee group ready to be placed at (x, 0, z) on stage
 */
export function createStandeeFromDrawing(drawingData, options = {}) {
  if (!drawingData || !drawingData.svg) {
    throw new Error("createStandeeFromDrawing: drawingData must contain valid svg string");
  }

  const standardHeight = options.standardHeight || STANDEE_DEFAULTS.standardHeight;
  const paperThickness = options.paperThickness || STANDEE_DEFAULTS.paperThickness;
  const bevelThickness = options.bevelThickness || STANDEE_DEFAULTS.bevelThickness;
  const bevelSize = options.bevelSize || STANDEE_DEFAULTS.bevelSize;
  const bevelSegments = options.bevelSegments || STANDEE_DEFAULTS.bevelSegments;
  const baseHeight = options.baseHeight || STANDEE_DEFAULTS.baseHeight;
  const baseType = options.baseType || STANDEE_DEFAULTS.baseType;
  const margin = options.margin !== undefined ? options.margin : STANDEE_DEFAULTS.margin;
  const slotDepth = options.slotDepth || STANDEE_DEFAULTS.slotDepth;

  const group = new THREE.Group();
  group.name = `standee_${drawingData.motif || "actor"}`;

  // 1. Prepare materials
  const materials = {
    card: options.cardMaterial || createPaperMaterial(TONES.CARD),
    base: options.baseMaterial || createPaperMaterial(TONES.CREAM),
    ink: createPaperMaterial(TONES.WHITE),
    muted: createPaperMaterial(TONES.MUTED),
    line: createPaperMaterial(TONES.SHADOW),
    canvas: createPaperMaterial(TONES.DARK),
    accent: createPaperMaterial(TONES.WHITE)
  };

  // 2. Parse SVG and compute bounds
  const preparedSvg = prepareDrawingSVG(drawingData.svg);
  const loader = new SVGLoader();
  const parsed = loader.parse(preparedSvg);
  const bounds = computeDrawingBounds(parsed.paths);

  // 3. Normalization Scale & Dimensions
  const scale = standardHeight / Math.max(bounds.height, 1);
  const artWidth = bounds.width * scale;
  const artHeight = standardHeight;
  const cardWidth = artWidth + margin * 2;
  const cardHeight = artHeight + margin * 2;
  const tabWidth = Math.max(cardWidth * 0.45, 0.4);

  // 4. Slotted Foot Pedestal (resting on stage floor at y=0)
  const pedestal = createSlottedPedestal(cardWidth, tabWidth, {
    baseType,
    baseHeight,
    paperThickness,
    slotDepth,
    baseRadius: options.baseRadius,
    material: materials.base
  });
  group.add(pedestal);

  // 5. Extruded Paper Backing Card with Integrated Mounting Tab
  const cxSvg = (bounds.minX + bounds.maxX) / 2;
  const cardShape = options.cardStyle === "cutout"
    ? createCutoutShape(
      parsed.paths.flatMap((p) => p.subPaths.flatMap((sub) => sub.getPoints().map((pt) => [
        (pt.x - cxSvg) * scale, baseHeight + margin + (bounds.maxY - pt.y) * scale
      ]))),
      margin,
      [tabWidth / 2, baseHeight - slotDepth + 0.005]
    )
    : createPaperCardShape(cardWidth, cardHeight, baseHeight, tabWidth, slotDepth, {
      cornerRadius: options.cornerRadius,
      cardStyle: options.cardStyle
    });

  const cardGeom = new THREE.ExtrudeGeometry(cardShape, {
    depth: paperThickness,
    bevelEnabled: true,
    bevelThickness,
    bevelSize,
    bevelSegments,
    curveSegments: 16
  });
  // Center card thickness around Z=0
  cardGeom.translate(0, 0, -paperThickness / 2);
  const cardMesh = new THREE.Mesh(cardGeom, materials.card);
  cardMesh.name = "paper_backing_card";
  cardMesh.castShadow = false;
  cardMesh.receiveShadow = false;
  group.add(cardMesh);

  // 6. Vector Artwork Meshes (Front Face)
  const zFront = paperThickness / 2 + 0.002;
  const { artGroup, dotAnchor } = buildStandeeArtworkGeometry(
    parsed.paths,
    bounds,
    scale,
    baseHeight,
    margin,
    zFront,
    materials
  );
  group.add(artGroup);

  // 7. Metadata, Anchors and Dimensions
  const fallbackDot = new THREE.Vector3(0, baseHeight + standardHeight * 0.75, zFront + 0.015);
  group.userData = {
    motif: drawingData.motif || "standee",
    about: drawingData.about || "",
    standardHeight,
    scale,
    bounds,
    dimensions: {
      cardWidth,
      cardHeight,
      totalHeight: baseHeight + cardHeight,
      thickness: paperThickness
    },
    base: {
      type: baseType,
      height: baseHeight,
      slotDepth
    },
    anchors: {
      dot: dotAnchor || fallbackDot,
      top: new THREE.Vector3(0, baseHeight + cardHeight, 0),
      base: new THREE.Vector3(0, 0, 0)
    }
  };

  return group;
}

/**
 * Convenience wrapper converting raw SVG string directly to a standee.
 *
 * @param {string} svgString Raw SVG content
 * @param {Object} [options={}] Standee options
 * @returns {THREE.Group}
 */
export function createStandeeFromSVG(svgString, options = {}) {
  return createStandeeFromDrawing({ motif: "svg-custom", about: "Custom SVG standee", svg: svgString }, options);
}
