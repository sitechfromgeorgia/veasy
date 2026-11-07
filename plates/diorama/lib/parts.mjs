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
  const { fold = 16, wobble = 0.016, warp = 0 } = o;
  const a = fold * Math.PI / 180;
  const right = card(half, { wobble, warp, spin: 0, ...o }), left = card(mirror(half), { wobble, warp, spin: 0, ...o });
  right.rotation.y = a;
  left.rotation.y = -a;
  return [right, left];
}

// A sheet across the stage, with an arched opening the view passes through.
// A crease where the sheet was once folded: a score line and the pale break beside it.
function crease(random, width, height, tone, clear) { // clear: the height above which the sheet has no opening
  const x = (random() - 0.5) * width * 0.8, lean = (random() - 0.5) * 1.6, y0 = clear + random() * 0.4, y1 = height, line = [];
  for (let i = 0; i <= 6; i++) line.push([x + lean * i / 6 + (random() - 0.5) * 0.02, y0 + (y1 - y0) * i / 6]);
  return [strip(line, 0.018, { tone: tone - 0.14, z: 0.07, depth: 0.004 }), strip(line.map(([a, b]) => [a + 0.018, b]), 0.012, { tone: tone + 0.2, z: 0.07, depth: 0.004 })];
}

function sheet({ at, width = 9, height = 7, tone = 0.4, open = 2.4, spring = 3.2, sill = 0.34, ring = true, cornice = 0, panes = false, windows = 0, gap = 0.5 }, { random }) {
  const clear = sill + spring + open / 2 + 0.4;
  const parts = [...crease(random, width, height, tone, clear), ...crease(random, width, height, tone, clear)], holes = [];
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
  const phase = random() * 6.3, wave = 0.5 + random() * 0.6;
  for (let x = width / 2; x > -width / 2; x -= 0.4) top.push([x, height + 0.05 * Math.sin(x * wave + phase) + (random() - 0.5) * 0.035]);
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

// A jar as a contour cut: nested sheets on spacers, each smaller and paler than the one behind, no two quite centred.
function amphora({ at, height = 1.1, tone = 0.7 }) {
  const k = height / 1.26;
  const curve = new THREE.CatmullRomCurve3(jarProfile.map(([x, y]) => new THREE.Vector3(x * k, y * k, 0)), false, "centripetal");
  const right = curve.getPoints(18).map((p) => [p.x, p.y]);
  const widthAt = (y) => right.reduce((best, p) => (Math.abs(p[1] - y) < Math.abs(best[1] - y) ? p : best))[0];
  const whole = (scale, dx = 0, y0 = 0, y1 = 9) => {
    const part = right.filter(([, y]) => y >= y0 && y <= y1).map(([x, y]) => [x * scale, y]);
    return [...mirror(part), ...part].map(([x, y]) => [x + dx, y]);
  };
  const parts = [];
  for (const side of [1, -1]) { // handles, laminated
    const p = arc(side * 0.22 * k, 1.03 * k, 0.15 * k, side > 0 ? 100 : 80, side > 0 ? -70 : 250, 8);
    parts.push(strip(p, 0.065, { tone: tone - 0.22, z: -0.12, depth: 0.03 }), strip(p, 0.03, { tone: tone - 0.04, z: -0.07, depth: 0.012 }));
  }
  parts.push(card(whole(1), { tone: tone - 0.38, z: -0.05 }));
  parts.push(card(whole(0.9, 0.012), { tone, z: 0.05, wobble: 0.016 }));
  parts.push(card(whole(0.58, -0.05, 0.14 * k, 1.0 * k), { tone: tone + 0.13, z: 0.14, wobble: 0.02, depth: 0.03 }));
  const band = (y, tall, teeth, lift) => { // cut from a dark sheet with the zigzag shears
    const w0 = widthAt(y - tall) * 0.86, w1 = widthAt(y + tall) * 0.86, top = [];
    for (let i = teeth; i >= -teeth; i--) {
      top.push([w1 * i / teeth, y + tall]);
      if (i > -teeth) top.push([w1 * (i - 0.5) / teeth, y + tall + (teeth > 2 ? 0.055 : 0)]);
    }
    return card([[-w0, y - tall], [w0, y - tall], ...top], { tone: 0.18, z: lift, depth: 0.03, wobble: 0.012 });
  };
  parts.push(band(0.66 * k, 0.075 * k, 5, 0.2), band(0.43 * k, 0.03 * k, 2, 0.2), band(0.9 * k, 0.03 * k, 2, 0.2));
  return group(parts, { at });
}

// A bust as a contour cut: shoulders, then neck and head, then the drape and the hair on spacers.
function bust({ at, height = 1, tone = 0.66 }) {
  const k = height, P = (list) => list.map(([x, y]) => [x * k, y * k]);
  const half = [[0.13, 0], [0.17, 0.08], [0.09, 0.11], [0.3, 0.26], [0.37, 0.4], [0.15, 0.5], [0.075, 0.56], [0.08, 0.66], [0.15, 0.72], [0.175, 0.82], [0.14, 0.94], [0.06, 1]];
  const whole = P([...half, ...mirror(half)]);
  return group([
    card(whole.map(([x, y]) => [x * 1.06, y * 1.01]), { tone: tone - 0.38, z: -0.05 }),
    card(whole, { tone, z: 0.05, wobble: 0.014 }),
    card(P([[-0.3, 0.27], [0.06, 0.13], [0.3, 0.27], [0.33, 0.39], [0.1, 0.47], [-0.16, 0.45], [-0.34, 0.39]]), { tone: tone - 0.15, z: 0.12, depth: 0.03 }),
    card(P([[-0.17, 0.83], [-0.1, 0.88], [0.1, 0.87], [0.18, 0.82], [0.14, 0.95], [0.05, 1], [-0.06, 1], [-0.14, 0.95]]), { tone: tone - 0.26, z: 0.12, depth: 0.03 }),
    card(P([[-0.1, 0.72], [-0.03, 0.66], [0.02, 0.84], [-0.09, 0.84]]), { tone: tone + 0.14, z: 0.12, depth: 0.02, wobble: 0.006 }),
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
