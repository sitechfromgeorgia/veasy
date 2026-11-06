// The part kit: what a set is made of. A part is a function of its JSON (`at`, `turn`, `scale` place it) and returns
// cards. A part names a thing, never a place: there is a tunnel flat, never a particular museum.
import * as THREE from "three";
import { arc, archOutline, block, card, group, rect, strip } from "./paper.mjs";

function checkerFloor({ at, x = [-4, 4], z = [-12, 8], size = 0.9, tones = [0.5, 0.36] }, { random }) {
  const parts = [block(x[0], -0.1, x[1], 0, z[0], z[1], { tone: 0.06 })];
  const rows = Math.round((z[1] - z[0]) / size), cols = Math.round((x[1] - x[0]) / size);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) { // sheets laid by hand: none quite square to the next
      const half = size / 2 - 0.018, tone = tones[(r + c) % 2] + (random() - 0.5) * 0.05;
      const tile = card(rect(-half, -half, half, half), { tone, edge: tone + 0.3, depth: 0.018, bevel: 0.008, wobble: 0.008 });
      tile.rotation.set(Math.PI / 2, 0, (random() - 0.5) * 0.03);
      tile.position.set(x[0] + (c + 0.5) * size + (random() - 0.5) * 0.02, 0.03, z[0] + (r + 0.5) * size + (random() - 0.5) * 0.02);
      parts.push(tile);
    }
  }
  return group(parts, { at });
}

// A column as a toy theatre draws it: a flat cut to its silhouette, fluted with strips of a darker card.
function columnCards({ x = 0, base = 0, height = 3.2, r = 0.2, tone = 0.7, z = 0 }) {
  const top = base + height, shaftBase = base + 0.28, shaftTop = top - 0.34, taper = 0.84;
  const parts = [
    card(rect(x - r * 1.5, base, x + r * 1.5, base + 0.14), { tone, z }),
    card(rect(x - r * 1.28, base + 0.14, x + r * 1.28, base + 0.28), { tone: tone - 0.08, z }),
    card([[x - r, shaftBase], [x + r, shaftBase], [x + r * taper, shaftTop], [x - r * taper, shaftTop]], { tone, z }),
    card([[x - r * taper, shaftTop], [x + r * taper, shaftTop], [x + r * 1.5, top - 0.12], [x - r * 1.5, top - 0.12]],
      { tone: tone - 0.06, z }),
    card(rect(x - r * 1.6, top - 0.12, x + r * 1.6, top), { tone, z }),
  ];
  for (let i = -2; i <= 2; i++) {
    const a = i * 0.34;
    parts.push(card([[x + r * a - 0.012, shaftBase + 0.05], [x + r * a + 0.012, shaftBase + 0.05],
      [x + r * taper * a + 0.01, shaftTop - 0.05], [x + r * taper * a - 0.01, shaftTop - 0.05]],
    { tone: tone - 0.26, z: z + 0.04, depth: 0.012, wobble: 0, bevel: 0 }));
  }
  return parts;
}

// A flat with an arched opening, a tunnel book's page: the camera passes through it.
function archFlat({ at, width = 6, height = 6, open = 1.8, spring = 2.5, tone = 0.5, columns = true, ring = true, coffers = 0 }) {
  const y = spring + open / 2, z = 0.03;
  const outline = [[-width / 2, 0], [-open / 2, 0], ...arc(0, spring, open / 2, 180, 0, 26), [open / 2, 0], [width / 2, 0], [width / 2, height], [-width / 2, height]];
  const parts = [card(outline, { tone, depth: 0.05 })]; // one outline: a hole that touches the edge breaks the triangulation
  if (ring) {
    const outer = open / 2 + 0.2;
    parts.push(card([...arc(0, spring, outer, 0, 180, 26), ...arc(0, spring, open / 2, 180, 0, 26)],
      { tone: tone + 0.16, z: 0.14 }));
    for (let a = 15; a < 180; a += 30) { // voussoir scores
      const c = Math.cos(a * Math.PI / 180), s = Math.sin(a * Math.PI / 180);
      parts.push(strip([[c * open / 2, spring + s * open / 2], [c * outer, spring + s * outer]], 0.012,
        { tone: tone - 0.2, z: 0.185, depth: 0.008 }));
    }
    parts.push(card([[-0.1, y - 0.03], [0.1, y - 0.03], [0.15, y + 0.3], [-0.15, y + 0.3]], { tone: tone + 0.3, z: 0.22 }));
  }
  if (columns) {
    const x = open / 2 + 0.42;
    parts.push(columnCards({ x, height: spring + 0.3, r: 0.17, tone: tone + 0.18, z: 0.16 }));
    parts.push(columnCards({ x: -x, height: spring + 0.3, r: 0.17, tone: tone + 0.18, z: 0.16 }));
  }
  const cornice = y + 0.42;
  parts.push(card(rect(-width / 2, cornice, width / 2, cornice + 0.1), { tone: tone + 0.2, z: 0.2, depth: 0.05 }));
  parts.push(card(rect(-width / 2, cornice - 0.08, width / 2, cornice), { tone: tone - 0.12, z: 0.1, depth: 0.05 }));
  for (let i = -coffers; i <= coffers && coffers; i++) {
    const x = i * 0.62;
    parts.push(card(rect(x - 0.22, cornice + 0.3, x + 0.22, cornice + 0.74), { tone: tone - 0.14, z: 0.09 }));
    parts.push(card(rect(x - 0.13, cornice + 0.39, x + 0.13, cornice + 0.65), { tone: tone + 0.08, z: 0.17 }));
  }
  return group(parts, { at });
}

// A framed picture: a stack of mounts around a little cut-paper view. No figure, no word.
function painting({ at, turn, w = 1, h = 1.3, kind = 0, tone = 0.72 }) {
  const b = 0.11, parts = [
    block(-w / 2 - b, -h / 2 - b, w / 2 + b, h / 2 + b, 0, 0.05, { tone }),
    card(rect(-w / 2 - 0.03, -h / 2 - 0.03, w / 2 + 0.03, h / 2 + 0.03), { tone: tone - 0.3, z: 0.09, depth: 0.012, wobble: 0.006 }),
    card(rect(-w / 2, -h / 2, w / 2, h / 2), { tone: kind === 2 ? 0.2 : 0.42, z: 0.102, depth: 0.01, wobble: 0 }),
  ];
  const z = 0.122;
  if (kind === 0) { // hills under a low sun
    parts.push(card(arc(w * 0.16, h * 0.08, w * 0.17, 0, 360, 22).slice(0, -1), { tone: 0.92, z, wobble: 0.006, depth: 0.02 }));
    parts.push(card([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, -h * 0.1], [w * 0.2, h * 0.02], [-w * 0.1, -h * 0.16], [-w / 2, -h * 0.02]],
      { tone: 0.24, z: z + 0.03, wobble: 0.006, depth: 0.02 }));
    parts.push(card([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, -h * 0.32], [0, -h * 0.2], [-w / 2, -h * 0.34]],
      { tone: 0.1, z: z + 0.06, wobble: 0.006, depth: 0.02 }));
  } else if (kind === 1) { // a still life: a bowl and a jar on a shelf
    parts.push(card(rect(-w / 2, -h / 2, w / 2, -h * 0.2), { tone: 0.2, z, wobble: 0.006, depth: 0.02 }));
    parts.push(card(arc(-w * 0.14, -h * 0.2, w * 0.24, 180, 360, 16), { tone: 0.82, z: z + 0.03, wobble: 0.006, depth: 0.02 }));
    parts.push(card([[w * 0.14, -h * 0.2], [w * 0.38, -h * 0.2], [w * 0.34, h * 0.16], [w * 0.18, h * 0.16]], { tone: 0.62, z: z + 0.03, wobble: 0.006, depth: 0.02 }));
  } else { // an abstract of three leaning forms
    parts.push(card([[-w * 0.4, -h * 0.4], [-w * 0.08, -h * 0.4], [w * 0.2, h * 0.38], [-w * 0.1, h * 0.38]], { tone: 0.82, z, wobble: 0.006, depth: 0.02 }));
    parts.push(card(arc(w * 0.18, -h * 0.14, w * 0.2, 0, 360, 22).slice(0, -1), { tone: 0.5, z: z + 0.03, wobble: 0.006, depth: 0.02 }));
  }
  return group(parts, { at, turn });
}

const jarProfile = [[0.06, 0], [0.16, 0.02], [0.08, 0.1], [0.26, 0.42], [0.31, 0.68], [0.24, 0.92], [0.11, 1.02], [0.09, 1.2], [0.15, 1.26]];

function amphora({ at, height = 1.1, tone = 0.8 }) {
  const k = height / 1.26;
  const curve = new THREE.CatmullRomCurve3(jarProfile.map(([x, y]) => new THREE.Vector3(x * k, y * k, 0)), false, "centripetal");
  const right = curve.getPoints(48).map((p) => [p.x, p.y]);
  const outline = (scale, up = 0) => [...right, ...right.map(([x, y]) => [-x, y]).reverse()].map(([x, y]) => [x * scale, y + up]);
  const parts = [card(outline(1), { tone: tone - 0.34, depth: 0.04 })]; // the back sheet, its shade showing round the body
  for (const side of [1, -1]) { // handles
    const p = arc(side * 0.22 * k, 1.03 * k, 0.15 * k, side > 0 ? 100 : 80, side > 0 ? -70 : 250, 12);
    parts.push(strip(p, 0.05, { tone: tone - 0.1, depth: 0.05, z: 0.04 }));
  }
  parts.push(card(outline(0.9), { tone, z: 0.09 })); // the lit body
  parts.push(card([[0.02, 0.2 * k], [0.14 * k, 0.26 * k], [0.21 * k, 0.56 * k], [0.15 * k, 0.86 * k], [0.03, 0.88 * k], [0.09 * k, 0.56 * k]],
    { tone: tone + 0.14, z: 0.14, depth: 0.02 })); // the side the light takes
  for (const [y, half, tall] of [[0.87, 0.23, 0.03], [0.68, 0.27, 0.075], [0.44, 0.23, 0.03]]) { // cut bands
    parts.push(card(rect(-half * k, (y - tall) * k, half * k, (y + tall) * k), { tone: 0.2, z: 0.19, depth: 0.02, wobble: 0.006 }));
  }
  for (let i = -5; i <= 5; i++) { // the running figure on the middle band
    const x = i * 0.044 * k, y = 0.68 * k;
    parts.push(card([[x - 0.013, y - 0.042 * k], [x + 0.013, y - 0.042 * k], [x, y + 0.042 * k]], { tone: tone, z: 0.22, depth: 0.008, wobble: 0, bevel: 0 }));
  }
  return group(parts, { at });
}

// A classical bust in three stacked cards: head and neck over the shoulders, on a turned foot.
function bust({ at, height = 1, tone = 0.74 }) {
  const k = height;
  const parts = [
    card([[-0.1 * k, 0], [0.1 * k, 0], [0.17 * k, 0.09 * k], [-0.17 * k, 0.09 * k]], { tone: tone - 0.26, depth: 0.06 }),
    card([[-0.11 * k, 0.08 * k], [0.11 * k, 0.08 * k], [0.34 * k, 0.26 * k], [0.37 * k, 0.4 * k], [0.15 * k, 0.5 * k],
      [0.08 * k, 0.6 * k], [-0.08 * k, 0.6 * k], [-0.15 * k, 0.5 * k], [-0.37 * k, 0.4 * k], [-0.34 * k, 0.26 * k]], { tone: tone - 0.14, z: 0.03, depth: 0.05 }),
    card([[-0.32 * k, 0.28 * k], [-0.34 * k, 0.4 * k], [-0.13 * k, 0.48 * k], [0.1 * k, 0.1 * k]], { tone, z: 0.09, depth: 0.03 }), // the drape
    card([[0.1 * k, 0.1 * k], [0.31 * k, 0.27 * k], [0.33 * k, 0.38 * k], [0.04 * k, 0.32 * k]], { tone: tone - 0.06, z: 0.12, depth: 0.03 }),
    card(rect(-0.075 * k, 0.48 * k, 0.075 * k, 0.66 * k), { tone: tone - 0.1, z: 0.09, depth: 0.03 }),
    card(arc(0, 0.78 * k, 0.17 * k, -80, 260, 24, 0.21 * k), { tone, z: 0.13, depth: 0.04 }),
    card(arc(-0.02 * k, 0.87 * k, 0.17 * k, 10, 170, 12, 0.12 * k), { tone: tone - 0.2, z: 0.18, depth: 0.03 }), // hair
    card(rect(-0.01 * k, 0.72 * k, 0.022 * k, 0.82 * k), { tone: tone + 0.1, z: 0.18, depth: 0.012, wobble: 0.003, bevel: 0 }), // nose
  ];
  return group(parts, { at });
}

function pedestal({ at, width = 0.8, height = 1, depth = 0.8, tone = 0.46 }) {
  const w = width / 2, d = depth / 2;
  return group([
    block(-w * 1.25, 0, w * 1.25, 0.1, -d * 1.25, d * 1.25, { tone: tone + 0.1 }),
    block(-w, 0.1, w, height - 0.08, -d, d, { tone }),
    block(-w * 1.18, height - 0.08, w * 1.18, height, -d * 1.18, d * 1.18, { tone: tone + 0.14 }),
    card(rect(-w * 0.78, 0.2, w * 0.78, height - 0.18), { tone: tone + 0.1, z: d - 0.01, depth: 0.03 }),
    card(rect(-w * 0.62, 0.3, w * 0.62, height - 0.28), { tone: tone - 0.08, z: d + 0.03, depth: 0.03 }),
  ], { at });
}

// Posts and a sagging rope: the rule "don't touch".
function rope({ at, turn, posts = 3, span = 1.2, tone = 0.8 }) {
  const parts = [];
  const h = 0.72;
  for (let i = 0; i < posts; i++) {
    const x = i * span;
    parts.push(block(x - 0.018, 0, x + 0.018, h, -0.018, 0.018, { tone }));
    parts.push(card(arc(x, h + 0.03, 0.045, 0, 360, 12).slice(0, -1), { tone: tone + 0.1, z: -0.02, depth: 0.04, wobble: 0 }));
    parts.push(block(x - 0.1, 0, x + 0.1, 0.03, -0.1, 0.1, { tone }));
    if (i < posts - 1) {
      const line = [];
      for (let k = 0; k <= 16; k++) {
        const f = k / 16;
        line.push([x + span * f, h - 0.02 - 0.2 * 4 * f * (1 - f)]);
      }
      parts.push(strip(line, 0.022, { tone: 0.55, depth: 0.02, z: -0.01 }));
    }
  }
  return group(parts, { at, turn });
}

// The side of a room seen in perspective, with its panelling.
function sideWall({ at, turn, length = 16, height = 7, tone = 0.42, dado = 1.1 }) {
  return group([
    card(rect(0, 0, length, height), { tone, wobble: 0 }),
    card(rect(0, 0, length, dado), { tone: tone - 0.12, z: 0.03, wobble: 0 }),
    card(rect(0, dado, length, dado + 0.05), { tone: tone + 0.2, z: 0.06, wobble: 0 }),
    card(rect(0, height - 2, length, height - 1.92), { tone: tone + 0.16, z: 0.03, wobble: 0 }),
  ], { at, turn });
}

// A wall at the end of a view, lit from behind: tall windows, each a sheet of glow behind glazing bars.
function lightWall({ at, width = 8, height = 7, windows = 3, w = 1, spring = 3, gap = 0.5, sill = 0.9, tone = 0.3, glow = 1.1 }) {
  const parts = [], holes = [];
  for (let i = 0; i < windows; i++) {
    const x = (i - (windows - 1) / 2) * (w + gap);
    holes.push(archOutline(x, sill, w, spring));
    for (let k = 1; k <= 3; k++) { // bars
      parts.push(card(rect(x - w / 2, sill + spring * k / 3 - 0.012, x + w / 2, sill + spring * k / 3 + 0.012), { tone: 0.2, z: 0.012, depth: 0.012, wobble: 0 }));
    }
    parts.push(card(rect(x - 0.012, sill, x + 0.012, sill + spring + w / 2), { tone: 0.2, z: 0.012, depth: 0.012, wobble: 0 }));
  }
  parts.push(card(rect(-width / 2, 0, width / 2, height), { holes, tone, depth: 0.04 }));
  parts.push(card(rect(-width / 2, 0, width / 2, height), { tone: 0.9, glow, z: -0.5, wobble: 0 }));
  return group(parts, { at });
}

// A ceiling lantern: slats overhead that catch the top light.
function ceiling({ at, width = 6, z = [-10, 7], height = 6.4, ribs = 7, tone = 0.4 }) {
  const parts = [];
  for (let i = 0; i < ribs; i++) {
    parts.push(block(-width / 2, height - 0.3, width / 2, height, z[0] + (z[1] - z[0]) * i / (ribs - 1) - 0.1, z[0] + (z[1] - z[0]) * i / (ribs - 1) + 0.1, { tone }));
  }
  return group(parts, { at });
}

function bench({ at, turn, width = 1.4, tone = 0.5 }) {
  return group([
    block(-width / 2, 0.34, width / 2, 0.4, -0.2, 0.2, { tone: tone + 0.15 }),
    block(-width / 2 + 0.1, 0, -width / 2 + 0.16, 0.34, -0.17, 0.17, { tone }),
    block(width / 2 - 0.16, 0, width / 2 - 0.1, 0.34, -0.17, 0.17, { tone }),
  ], { at, turn });
}

export const PARTS = {
  "checker-floor": checkerFloor, "arch-flat": archFlat, painting, amphora, bust, pedestal, rope, "side-wall": sideWall,
  "light-wall": lightWall, ceiling, bench,
};
