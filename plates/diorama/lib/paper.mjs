// The one primitive of the paper stage: a hand-cut card. A card has a tone on its face and a paler cut edge (the white
// core of the board), which is most of why it reads as paper and not as a game box. Everything is merged into one mesh
// with one material, so a frame is one draw call and the shadow map is rendered once (lib/stage.mjs).
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

let random = () => 0.5;
export const seedPaper = (r) => { random = r; };

export const linear = (tone) => Math.max(0, tone) ** 2.2; // a tone is authored as the grey you want to see

export const rect = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

export function arc(cx, cy, r, from, to, n = 18, ry = r) { // degrees
  const out = [];
  for (let i = 0; i <= n; i++) {
    const a = (from + (to - from) * i / n) * Math.PI / 180;
    out.push([cx + r * Math.cos(a), cy + ry * Math.sin(a)]);
  }
  return out;
}

// An opening with a round head, standing on y0, counter-clockwise from its bottom right.
export const archOutline = (cx, y0, width, spring) => [[cx + width / 2, y0],
  ...arc(cx, y0 + spring, width / 2, 0, 180), [cx - width / 2, y0]];

function handCut(points, wobble) { // a knife wavers on a long edge and misses a curve a little
  const out = [];
  for (let i = 0; i < points.length; i++) {
    const [ax, ay] = points[i], [bx, by] = points[(i + 1) % points.length];
    const length = Math.hypot(bx - ax, by - ay);
    const steps = Math.min(24, Math.floor(length / 0.26));
    out.push([ax + (random() - 0.5) * wobble * 0.4, ay + (random() - 0.5) * wobble * 0.4]);
    for (let s = 1; s < steps; s++) {
      const f = s / steps, push = (random() - 0.5) * wobble;
      out.push([ax + (bx - ax) * f + (by - ay) / length * push, ay + (by - ay) * f - (bx - ax) / length * push]);
    }
  }
  return out;
}

function paint(geometry, tone, edge, glow) { // attribute ink: linear tone, then glow
  const count = geometry.attributes.position.count;
  const ink = new Float32Array(count * 2);
  const groups = geometry.groups.length ? geometry.groups : [{ start: 0, count, materialIndex: 0 }];
  for (const g of groups) {
    const value = linear(g.materialIndex === 1 ? edge : tone);
    for (let i = g.start; i < g.start + g.count; i++) {
      ink[i * 2] = value;
      ink[i * 2 + 1] = glow;
    }
  }
  geometry.setAttribute("ink", new THREE.BufferAttribute(ink, 2));
  geometry.clearGroups();
  return geometry;
}

// Options: holes, z (the back of the card), depth, tone, edge, glow (lit from within: a window, a sky), wobble, bevel.
// The bevel is the cut edge seen from the front: a facet that takes the light on one side and loses it on the other.
export function card(outline, o = {}) {
  const { holes = [], z = 0, depth = 0.04, tone = 0.6, edge = Math.min(1, tone + 0.3), glow = 0, wobble = 0.016 } = o;
  const { bevel = wobble ? 0.014 : 0.005 } = o;
  const toPoints = (pts) => (wobble ? handCut(pts, wobble) : pts).map(([x, y]) => new THREE.Vector2(x, y));
  const shape = new THREE.Shape(toPoints(outline));
  for (const hole of holes) shape.holes.push(new THREE.Path(toPoints(hole)));
  const geometry = new THREE.ExtrudeGeometry(shape, { depth, curveSegments: 1, steps: 1, bevelEnabled: bevel > 0, bevelSegments: 1,
    bevelSize: bevel, bevelThickness: bevel, bevelOffset: -bevel });
  geometry.translate(0, 0, z);
  return new THREE.Mesh(paint(geometry, tone, edge, glow));
}

// A folded block: a card thick enough to stand, its sides shaded like its face.
export function block(x0, y0, x1, y1, z0, z1, o = {}) {
  const { tone = 0.6 } = o;
  return card(rect(x0, y0, x1, y1), { z: z0, depth: z1 - z0, edge: tone + 0.12, wobble: 0, ...o });
}

// A thin strip along a line of points: a rope, a wire, a crack, a chalk line.
export function strip(points, width, o = {}) {
  const left = [], right = [];
  points.forEach(([x, y], i) => {
    const [ax, ay] = points[Math.max(0, i - 1)], [bx, by] = points[Math.min(points.length - 1, i + 1)];
    const l = Math.hypot(bx - ax, by - ay) || 1, nx = -(by - ay) / l * width / 2, ny = (bx - ax) / l * width / 2;
    left.push([x + nx, y + ny]);
    right.unshift([x - nx, y - ny]);
  });
  return card([...right, ...left], { wobble: 0, bevel: 0, ...o });
}

export function group(parts, { at, turn, scale } = {}) {
  const g = new THREE.Group();
  for (const p of parts.flat()) if (p) g.add(p);
  if (at) g.position.set(...at);
  if (turn) g.rotation.y = turn * Math.PI / 180;
  if (scale) g.scale.setScalar(scale);
  return g;
}

function fromMaterial(mesh) { // a mesh of the kit or the extruder: its Lambert tones become the card's attributes
  const geometry = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry.clone();
  const material = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
  const c = material.color, grey = (c.r + c.g + c.b) / 3;
  const ink = new Float32Array(geometry.attributes.position.count * 2);
  for (let i = 0; i < ink.length; i += 2) ink[i] = grey;
  geometry.setAttribute("ink", new THREE.BufferAttribute(ink, 2));
  return geometry;
}

// Bake every mesh under root into one geometry in world space.
export function mergePaper(root) {
  root.updateMatrixWorld(true);
  const all = [];
  root.traverse((o) => {
    if (!o.isMesh) return;
    const g = (o.geometry.attributes.ink ? o.geometry.clone() : fromMaterial(o)).applyMatrix4(o.matrixWorld);
    for (const name of Object.keys(g.attributes)) if (!["position", "normal", "ink"].includes(name)) g.deleteAttribute(name);
    g.index = null;
    all.push(g);
  });
  return mergeGeometries(all, false);
}
