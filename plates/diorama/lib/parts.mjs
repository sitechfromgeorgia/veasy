// The part kit: what a set is made of. A set is a tunnel book: parallel cut sheets a short way apart, seen on a long
// lens, never a modelled room. There is no floor plane: ground rows stand across the stage and hide each other's feet.
// A solid is never modelled: a jar is a silhouette folded down its middle, a column a card creased along its length.
// A part is a function of its JSON (`at`, `turn` place it). It names a thing, never a place.
import * as THREE from "three";
import { createStandeeFromDrawing } from "./extruder.mjs";
import { createPaperMaterial } from "./kit.mjs";
import { arc, card, group, rect, strip } from "./paper.mjs";

const SNIP = 12; // scissors make an arc from short straight cuts, and it shows

const mirror = (points) => points.map(([x, y]) => [-x, y]).reverse();

// A silhouette folded down its middle and stood up: the left half takes the light, the right half loses it. The crease
// is the proof that this is a sheet. `half` is the right half, from its foot on x=0 round to its top on x=0.
function folded(half, o = {}) {
  const { fold = 16, wobble = 0.012, warp = 0 } = o;
  const a = fold * Math.PI / 180;
  const right = card(half, { wobble, warp, spin: 0, ...o }), left = card(mirror(half), { wobble, warp, spin: 0, ...o });
  right.rotation.y = a;
  left.rotation.y = -a;
  return [right, left];
}

// A sheet across the stage, with an arched opening the view passes through.
function sheet({ at, width = 9, height = 7, tone = 0.4, open = 2.4, spring = 3.2, sill = 0.34, ring = true, cornice = 0, panes = false, windows = 0, gap = 0.5 }) {
  const parts = [], holes = [];
  if (windows) {
    for (let i = 0; i < windows; i++) {
      const x = (i - (windows - 1) / 2) * (open + gap);
      if (panes) holes.push(...windowPanes(x, sill, open, spring));
      else holes.push(archHole(x, sill, open, spring));
    }
  } else if (open) {
    holes.push(archHole(0, sill, open, spring));
  }
  parts.push(card(rect(-width / 2, 0, width / 2, height), { holes, tone, depth: 0.05, ...(panes ? { wobble: 0.007, bevel: 0.008 } : {}) }));
  if (ring && open) {
    const inner = open / 2, outer = inner + 0.2, y = sill + spring;
    const band = [...arc(0, y, outer, 0, 180, SNIP), ...arc(0, y, inner, 180, 0, SNIP)];
    parts.push(card(band, { tone: tone + 0.22, z: 0.16 }));
    for (let a = 18; a < 180; a += 36) {
      const c = Math.cos(a * Math.PI / 180), s = Math.sin(a * Math.PI / 180);
      parts.push(strip([[c * inner, y + s * inner], [c * outer, y + s * outer]], 0.016, { tone: tone - 0.1, z: 0.21, depth: 0.01 }));
    }
    parts.push(card([[-0.11, y + inner - 0.04], [0.11, y + inner - 0.04], [0.17, y + outer + 0.1], [-0.17, y + outer + 0.1]], { tone: tone + 0.34, z: 0.3 }));
  }
  if (cornice) {
    parts.push(card(rect(-width / 2, cornice, width / 2, cornice + 0.12), { tone: tone + 0.2, z: 0.2 }));
    parts.push(card(rect(-width / 2, cornice - 0.1, width / 2, cornice), { tone: tone - 0.14, z: 0.1 }));
    for (let x = -4.2; x < 4.3; x += 0.4) parts.push(card(rect(x - 0.1, cornice - 0.26, x + 0.1, cornice - 0.1), { tone: tone + 0.1, z: 0.13, depth: 0.03 }));
  }
  return group(parts, { at });
}

function archHole(x, sill, width, spring) {
  const r = width / 2;
  return [[x - r, sill], [x + r, sill], ...arc(x, sill + spring, r, 0, 180, SNIP).slice(0)];
}

function windowPanes(x, sill, width, spring) { // the bars are what is left of the sheet between the cuts
  const bar = 0.09, holes = [], cols = 2, rows = 3, w = (width - bar * (cols - 1)) / cols, h = (spring - bar * rows) / rows;
  for (let c = 0; c < cols; c++) {
    for (let r = 0; r < rows; r++) {
      const x0 = x - width / 2 + c * (w + bar), y0 = sill + r * (h + bar);
      holes.push(rect(x0, y0, x0 + w, y0 + h));
    }
  }
  const y = sill + spring, r = width / 2;
  holes.push([[x + bar / 2, y], [x + r, y], ...arc(x, y, r, 0, 90, 6).slice(1, -1), [x + bar / 2, y + r - 0.01]]);
  holes.push([[x - r, y], [x - bar / 2, y], [x - bar / 2, y + r - 0.01], ...arc(x, y, r, 90, 180, 6).slice(1, -1)]);
  return holes;
}

// The light behind a wall: one sheet lit from within.
function glow({ at, width = 12, height = 9, power = 1.4, tone = 0.8 }) {
  return group([card(rect(-width / 2, 0, width / 2, height), { tone, glow: power, wobble: 0, bevel: 0, warp: 0 })], { at });
}

// A ground row: a low strip across the stage, its top edge cut by hand.
function groundRow({ at, width = 12, height = 0.3, tone = 0.4 }, { random }) {
  const top = [];
  for (let x = width / 2; x > -width / 2; x -= 0.7) top.push([x, height + (random() - 0.5) * 0.03]);
  return group([card([[-width / 2, 0], [width / 2, 0], ...top], { tone, depth: 0.04 })], { at });
}

// A column on its own card, folded along its length, with the flutes cut from a darker sheet.
function column({ at, height = 3.4, r = 0.24, tone = 0.6 }) {
  const y1 = height;
  const half = [[0, 0], [r * 1.6, 0], [r * 1.6, 0.13], [r * 1.25, 0.15], [r * 1.25, 0.28], [r, 0.3], [r * 0.84, y1 - 0.36], [r * 1.2, y1 - 0.26],
    [r * 1.6, y1 - 0.14], [r * 1.7, y1 - 0.14], [r * 1.7, y1], [0, y1]];
  const parts = [...folded(half, { tone, fold: 22 })];
  for (const side of [1, -1]) {
    for (const f of [0.34, 0.68]) {
      const flute = strip([[side * r * f, 0.36], [side * r * 0.84 * f, y1 - 0.42]], 0.024, { tone: tone - 0.26, z: 0.05, depth: 0.012 });
      flute.rotation.y = side * 22 * Math.PI / 180;
      parts.push(flute);
    }
  }
  return group(parts, { at });
}

// A framed picture: mounts around a little cut-paper view, taped on. No figure, no word.
function painting({ at, w = 1, h = 1.3, kind = 0, tone = 0.72 }) {
  const b = 0.09, z = 0.14, small = { wobble: 0.006, depth: 0.02, warp: 0 };
  const parts = [
    card(rect(-w / 2 - b, -h / 2 - b, w / 2 + b, h / 2 + b), { tone, depth: 0.04 }),
    card(rect(-w / 2, -h / 2, w / 2, h / 2), { tone: kind === 2 ? 0.2 : 0.42, z: 0.1, depth: 0.012, wobble: 0.004, warp: 0 }),
  ];
  if (kind === 0) { // hills under a low sun
    parts.push(card(arc(w * 0.16, h * 0.08, w * 0.17, 0, 360, 10).slice(0, -1), { tone: 0.92, z, ...small }));
    parts.push(card([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, -h * 0.1], [w * 0.2, h * 0.02], [-w * 0.1, -h * 0.16], [-w / 2, -h * 0.02]], { tone: 0.24, z: z + 0.04, ...small }));
    parts.push(card([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, -h * 0.32], [0, -h * 0.2], [-w / 2, -h * 0.34]], { tone: 0.1, z: z + 0.08, ...small }));
  } else if (kind === 1) { // a still life: a bowl and a jar on a shelf
    parts.push(card(rect(-w / 2, -h / 2, w / 2, -h * 0.2), { tone: 0.2, z, ...small }));
    parts.push(card(arc(-w * 0.14, -h * 0.2, w * 0.24, 180, 360, 8), { tone: 0.82, z: z + 0.04, ...small }));
    parts.push(card([[w * 0.14, -h * 0.2], [w * 0.38, -h * 0.2], [w * 0.34, h * 0.16], [w * 0.18, h * 0.16]], { tone: 0.62, z: z + 0.04, ...small }));
  } else { // three leaning forms
    parts.push(card([[-w * 0.4, -h * 0.4], [-w * 0.08, -h * 0.4], [w * 0.2, h * 0.38], [-w * 0.1, h * 0.38]], { tone: 0.82, z, ...small }));
    parts.push(card(arc(w * 0.18, -h * 0.14, w * 0.2, 0, 360, 10).slice(0, -1), { tone: 0.5, z: z + 0.04, ...small }));
  }
  for (const [sx, sy] of [[-1, 1], [1, 1], [1, -1], [-1, -1]]) { // masking tape over the corners
    const piece = card(rect(-0.12, -0.035, 0.12, 0.035), { tone: 0.78, edge: 0.88, edgeGlow: 0.1, z: 0.06, depth: 0.012, bevel: 0.002, wobble: 0.008, warp: 0, spin: 0.3 });
    piece.position.set(sx * (w / 2 + b * 0.4), sy * (h / 2 + b * 0.4), 0);
    piece.rotation.z = sx * sy * -Math.PI / 4;
    parts.push(piece);
  }
  return group(parts, { at });
}

const jarProfile = [[0.1, 0], [0.17, 0.03], [0.09, 0.1], [0.27, 0.42], [0.32, 0.68], [0.25, 0.92], [0.11, 1.02], [0.09, 1.18], [0.16, 1.26]];

// A jar: its silhouette folded in half, bands cut from a dark sheet and glued on each half, the handles behind.
function amphora({ at, height = 1.1, tone = 0.72 }) {
  const k = height / 1.26;
  const curve = new THREE.CatmullRomCurve3(jarProfile.map(([x, y]) => new THREE.Vector3(x * k, y * k, 0)), false, "centripetal");
  const right = curve.getPoints(20).map((p) => [p.x, p.y]);
  const widthAt = (y) => right.reduce((best, p) => (Math.abs(p[1] - y) < Math.abs(best[1] - y) ? p : best))[0];
  const half = [[0, 0], ...right, [0, 1.26 * k]];
  const parts = [];
  for (const side of [1, -1]) { // handles, laminated
    const p = arc(side * 0.22 * k, 1.03 * k, 0.15 * k, side > 0 ? 100 : 80, side > 0 ? -70 : 250, 8);
    parts.push(strip(p, 0.06, { tone: tone - 0.2, z: -0.1, depth: 0.03 }));
  }
  parts.push(...folded(half.map(([x, y]) => [x * 1.05, y]), { tone: tone - 0.36, fold: 16 }).map((c) => { c.position.z = -0.05; return c; }));
  parts.push(...folded(half, { tone, fold: 16 }));
  const band = (y, tall, shade, lift) => {
    const w0 = widthAt(y - tall) * 0.98, w1 = widthAt(y + tall) * 0.98;
    return folded([[0, y - tall], [w0, y - tall], [w1, y + tall], [0, y + tall]], { tone: shade, fold: 16, depth: 0.02, bevel: 0.006, wobble: 0.008, z: lift + 0.06 });
  };
  parts.push(...band(0.68 * k, 0.09 * k, 0.16, 0.05), ...band(0.46 * k, 0.03 * k, 0.16, 0.05), ...band(0.9 * k, 0.03 * k, 0.16, 0.05));
  for (let i = 0; i < 5; i++) { // the running figure on the band
    const x = (i + 0.5) * 0.05 * k;
    parts.push(...folded([[x - 0.014, 0.62 * k], [x + 0.014, 0.62 * k], [x + 0.014, 0.74 * k], [x - 0.014, 0.74 * k]].map(([a, b]) => [Math.max(0.002, a), b]),
      { tone: tone - 0.02, fold: 16, depth: 0.012, bevel: 0, wobble: 0.004, z: 0.16 }));
  }
  return group(parts, { at });
}

// A bust: head, neck and shoulders folded down the nose, the drape a second cut glued across it.
function bust({ at, height = 1, tone = 0.68 }) {
  const k = height, P = (list) => list.map(([x, y]) => [x * k, y * k]);
  const half = P([[0, 0], [0.13, 0], [0.17, 0.08], [0.09, 0.11], [0.3, 0.26], [0.37, 0.4], [0.15, 0.5], [0.075, 0.56], [0.08, 0.66],
    [0.15, 0.72], [0.175, 0.82], [0.14, 0.94], [0.06, 1], [0, 1.01]]);
  return group([
    ...folded(half.map(([x, y]) => [x * 1.05, y * 1.01]), { tone: tone - 0.36, fold: 18 }).map((c) => { c.position.z = -0.05; return c; }),
    ...folded(half, { tone, fold: 18 }),
    ...folded(P([[0, 0.14], [0.26, 0.26], [0.33, 0.39], [0.13, 0.47], [0, 0.4]]), { tone: tone - 0.16, fold: 18, z: 0.11, depth: 0.02 }),
    ...folded(P([[0, 0.9], [0.17, 0.84], [0.15, 0.93], [0.06, 1], [0, 1.01]]), { tone: tone - 0.24, fold: 18, z: 0.11, depth: 0.02 }),
  ], { at });
}

// A pedestal: a stack of cards standing one in front of the next, wider at the foot and the cap.
function pedestal({ at, width = 0.8, height = 1, tone = 0.44 }) {
  const w = width / 2;
  return group([
    card(rect(-w, 0.1, w, height - 0.08), { tone }),
    card(rect(-w * 0.76, 0.22, w * 0.76, height - 0.2), { tone: tone + 0.12, z: 0.08, depth: 0.03 }),
    card(rect(-w * 0.58, 0.32, w * 0.58, height - 0.3), { tone: tone - 0.12, z: 0.13, depth: 0.03 }),
    card(rect(-w * 1.24, 0, w * 1.24, 0.12), { tone: tone + 0.1, z: 0.11 }),
    card(rect(-w * 1.2, height - 0.09, w * 1.2, height), { tone: tone + 0.2, z: 0.11 }),
  ], { at });
}

// Posts and a sagging rope, each cut from card.
function rope({ at, span = 2.4, tone = 0.72 }) {
  const parts = [], h = 0.74, line = [];
  for (const x of [0, span]) {
    parts.push(card(rect(x - 0.03, 0, x + 0.03, h), { tone, depth: 0.03, wobble: 0.006, warp: 0 }));
    parts.push(card(arc(x, h + 0.05, 0.07, 0, 360, 8).slice(0, -1), { tone: tone + 0.1, z: 0.04, depth: 0.03, wobble: 0.006, warp: 0 }));
    parts.push(card(rect(x - 0.14, 0, x + 0.14, 0.05), { tone, z: 0.04, depth: 0.03, wobble: 0.006, warp: 0 }));
  }
  for (let k = 0; k <= 12; k++) {
    const f = k / 12;
    line.push([span * f, h - 0.02 - 0.26 * 4 * f * (1 - f) + (k % 2 ? 0.006 : -0.006)]);
  }
  parts.push(strip(line, 0.04, { tone: 0.5, depth: 0.03, z: -0.05 }));
  return group(parts, { at });
}

// Any drawing of assets/drawings, standing: a dark card cut around it, the lines in pale card on its face.
function standee({ at, turn, drawing, height = 1.2, tone = 0x2e2e2e, base = "disc" }, { drawings }) {
  if (!drawings[drawing]) throw new Error(`no drawing "${drawing}"`);
  const figure = createStandeeFromDrawing(drawings[drawing], { standardHeight: height, cardStyle: "cutout", baseType: base,
    margin: 0.05, baseRadius: 0.3, paperThickness: 0.04, cardMaterial: createPaperMaterial(tone), baseMaterial: createPaperMaterial(0x6e6e6e) });
  return group([figure], { at, turn });
}

export const PARTS = { sheet, glow, "ground-row": groundRow, column, painting, amphora, bust, pedestal, rope, standee };
