// The parts that make a place a place: what a stranger names it by. Each is cut sheets in planes, as lib/parts.mjs says.
// None is a real building, street, river or landmark, and none carries a word or a number.
import { arc, card, group, rect, strip } from "./paper.mjs";

const hem = (x0, x1, y, n, depth) => { // scallops along a hem, right to left
  const out = [];
  for (let i = 0; i < n; i++) {
    const w = (x1 - x0) / n, a = x1 - w * i;
    out.push(...arc(a - w / 2, y, w / 2, 0, -180, 6, depth));
  }
  return out;
};
const disc = (x, y, r, n = 9, ry = r) => arc(x, y, r, 0, 360, n, ry).slice(0, -1);

// A house front: a pitched or flat roofline, windows cut out with a lit sheet behind some of them, a door, a chimney.
function house({ at, width = 2, height = 3, roof = 0.8, floors = 3, cols = 3, tone = 0.4, door = true, shop = false, lit = [] }, { random }) {
  const w = width / 2, parts = [], holes = [], floorH = (height - 0.5) / floors, ww = Math.min(0.34, width / cols * 0.5), wh = floorH * 0.56;
  const outline = roof ? [[-w, 0], [w, 0], [w, height], [0, height + roof], [-w, height]] : [[-w, 0], [w, 0], [w, height], [-w, height]];
  for (let f = shop ? 1 : 0; f < floors; f++) {
    for (let c = 0; c < cols; c++) {
      if (door && !shop && f === 0 && c === Math.floor(cols / 2)) continue;
      const x = -w + width * (c + 0.5) / cols, y = 0.4 + f * floorH;
      holes.push(rect(x - ww / 2, y, x + ww / 2, y + wh));
      const on = lit.includes(f * cols + c) || random() < 0.28;
      parts.push(card(rect(x - ww / 2 - 0.02, y - 0.02, x + ww / 2 + 0.02, y + wh + 0.02), { tone: on ? 0.82 : 0.08, glow: on ? 1 : 0, z: -0.08, depth: 0.01, wobble: 0, bevel: 0, warp: 0 }));
      parts.push(strip([[x, y], [x, y + wh]], 0.028, { tone: tone + 0.1, z: 0.01, depth: 0.01 }));
      parts.push(strip([[x - ww / 2, y + wh * 0.55], [x + ww / 2, y + wh * 0.55]], 0.028, { tone: tone + 0.1, z: 0.01, depth: 0.01 }));
      parts.push(card(rect(x - ww / 2 - 0.05, y - 0.06, x + ww / 2 + 0.05, y - 0.005), { tone: tone + 0.26, z: 0.1, depth: 0.03, wobble: 0.006, warp: 0 })); // sill
      if (random() < 0.5) { // shutters, one pair of cards on spacers
        for (const side of [-1, 1]) parts.push(card(rect(x + side * (ww / 2 + 0.02), y, x + side * (ww / 2 + ww * 0.42), y + wh), { tone: tone - 0.14, z: 0.09, depth: 0.02, wobble: 0.006, warp: 0 }));
      }
    }
  }
  parts.push(card(outline, { holes, tone, depth: 0.05, wobble: 0.01, bevel: 0.012 }));
  if (roof) { // the roof, tiled in scalloped strips
    const rows = 4;
    for (let r = 0; r < rows; r++) {
      const f0 = r / rows, f1 = (r + 1) / rows, y0 = height + roof * f0, y1 = height + roof * f1, half0 = (w + 0.08) * (1 - f0), half1 = (w + 0.08) * (1 - f1);
      parts.push(card([...hem(-half0, half0, y0, Math.max(2, Math.round(half0 * 5)), 0.05), [half1, y1], [-half1, y1]].reverse(), { tone: 0.2 + (r % 2) * 0.07, z: 0.1 + r * 0.03, depth: 0.03, wobble: 0.006 }));
    }
    parts.push(card(rect(w * 0.42, height + roof * 0.3, w * 0.42 + 0.24, height + roof * 1.1), { tone: tone - 0.1, z: -0.1 }));
    parts.push(card(rect(w * 0.42 - 0.04, height + roof * 1.1, w * 0.42 + 0.28, height + roof * 1.1 + 0.06), { tone: tone + 0.1, z: -0.07, depth: 0.03 }));
  } else {
    parts.push(card(rect(-w - 0.06, height - 0.1, w + 0.06, height + 0.03), { tone: tone + 0.2, z: 0.1 }));
  }
  if (shop) { // a shopfront: a dark band for a sign, big panes, an awning
    parts.push(card(rect(-w + 0.08, 0.1, w - 0.08, floorH * 0.78), { tone: 0.8, glow: 0.8, z: 0.06, depth: 0.01, wobble: 0.006, warp: 0 }));
    for (let i = 0; i <= 3; i++) parts.push(strip([[-w + 0.08 + (width - 0.16) * i / 3, 0.1], [-w + 0.08 + (width - 0.16) * i / 3, floorH * 0.78]], 0.05, { tone: tone - 0.1, z: 0.08, depth: 0.02 }));
    parts.push(card(rect(-w, floorH * 0.8, w, floorH * 1.02), { tone: 0.14, z: 0.1 }));
    parts.push(...awning(-w - 0.04, w + 0.04, floorH * 0.8, 0.42, 7, 0.16));
  } else if (door) {
    const x = -w + width * (Math.floor(cols / 2) + 0.5) / cols;
    parts.push(card([[x - 0.17, 0], [x + 0.17, 0], ...arc(x, 0.72, 0.17, 0, 180, 6)], { tone: 0.16, z: 0.06, depth: 0.03, wobble: 0.008, warp: 0 }));
    parts.push(card(disc(x + 0.09, 0.42, 0.018, 6), { tone: 0.8, z: 0.11, depth: 0.01, wobble: 0, bevel: 0, warp: 0 }));
  }
  return group(parts, { at });
}

// An awning of stripes, each stripe its own strip of card ending in a scallop.
function awning(x0, x1, y, drop, stripes, z = 0.2) {
  const out = [], w = (x1 - x0) / stripes;
  for (let i = 0; i < stripes; i++) {
    const a = x0 + i * w, b = a + w, slant = 0.14;
    const outline = [...arc((a + b) / 2, y, w / 2, 180, 360, 6, w * 0.45), [b + (b - (x0 + x1) / 2) * slant * 0.1, y + drop], [a + (a - (x0 + x1) / 2) * slant * 0.1, y + drop]];
    out.push(card(outline, { tone: i % 2 ? 0.74 : 0.2, z: z + (i % 2) * 0.03, depth: 0.03, wobble: 0.008, spin: 0.006, warp: 0 }));
  }
  return out;
}

function lamp({ at, height = 3.2, tone = 0.2 }) {
  return group([
    card([[-0.05, 0], [0.05, 0], [0.03, height], [-0.03, height]], { tone, wobble: 0.006, warp: 0, depth: 0.03 }),
    card(rect(-0.13, 0, 0.13, 0.26), { tone, depth: 0.03, wobble: 0.006, warp: 0 }),
    strip(arc(0.19, height, 0.19, 180, 30, 6), 0.04, { tone, depth: 0.03 }),
    card([[0.27, height - 0.08], [0.47, height - 0.08], [0.42, height + 0.08], [0.32, height + 0.08]], { tone: 0.9, glow: 1.3, z: 0.03, depth: 0.03, wobble: 0.004, warp: 0, edgeGlow: 0.4 }),
    card([[0.24, height + 0.06], [0.5, height + 0.06], [0.37, height + 0.2]], { tone, z: 0.05, depth: 0.03, wobble: 0.004, warp: 0 }),
  ], { at });
}

// A tree of a few overlapping cut leaf-masses, darker behind, paler where the light reaches.
function tree({ at, height = 2.6, r = 0.8, tone = 0.3 }, { random }) {
  const parts = [card([[-0.09, 0], [0.09, 0], [0.05, height * 0.65], [-0.05, height * 0.65]], { tone: 0.16, wobble: 0.01 })];
  const clumps = [[0, 0.62, 1, -0.1], [-0.5, 0.74, 0.72, 0], [0.5, 0.76, 0.7, 0.04], [0, 0.96, 0.66, 0.1]];
  clumps.forEach(([x, y, size, z], i) => {
    const edge = [];
    for (let a = 0; a < 16; a++) { // leafy: a rough ring of bumps
      const ang = a / 16 * Math.PI * 2, rad = r * size * (0.82 + (a % 2) * 0.22 + (random() - 0.5) * 0.1);
      edge.push([x * r + Math.cos(ang) * rad, height * y + Math.sin(ang) * rad * 0.86]);
    }
    parts.push(card(edge, { tone: tone + i * 0.07, z, depth: 0.03, wobble: 0.01 }));
  });
  return group(parts, { at });
}

function trafficLight({ at, height = 2.5 }) {
  return group([
    card(rect(-0.035, 0, 0.035, height), { tone: 0.18, depth: 0.03, wobble: 0.004, warp: 0 }),
    card(rect(-0.13, height - 0.1, 0.13, height + 0.58), { tone: 0.14, z: 0.04, depth: 0.03, wobble: 0.006, warp: 0 }),
    ...[[0.44, 0.34], [0.24, 0.3], [0.04, 0.9]].map(([y, t], i) => card(disc(0, height + y, 0.07), { tone: t, glow: i === 2 ? 1.2 : 0, z: 0.08, depth: 0.01, wobble: 0, bevel: 0, warp: 0 })),
  ], { at });
}

// A strip of road across the stage. Dashes and kerbs stand at fixed x, so depth alone draws them together.
function roadRow({ at, width = 14, height = 0.16, tone = 0.2, kerb = 2.3, dash = true, zebra = false, side = 0.42 }) {
  const parts = [card(rect(-width / 2, 0, width / 2, height), { tone, depth: 0.04, wobble: 0.008 })];
  if (dash) parts.push(card(rect(-0.09, 0.03, 0.09, height - 0.02), { tone: 0.8, z: 0.07, depth: 0.01, wobble: 0.004, warp: 0 }));
  if (zebra) for (let x = -kerb + 0.3; x < kerb; x += 0.6) parts.push(card(rect(x - 0.17, 0.02, x + 0.17, height - 0.01), { tone: 0.84, z: 0.07, depth: 0.01, wobble: 0.006, warp: 0 }));
  for (const s of [-1, 1]) {
    parts.push(card(rect(s > 0 ? kerb : -width / 2, 0, s > 0 ? width / 2 : -kerb, height + 0.1), { tone: side, z: 0.09, depth: 0.04, wobble: 0.008 }));
    parts.push(card(rect(s > 0 ? kerb - 0.03 : -kerb - 0.1, 0, s > 0 ? kerb + 0.1 : -kerb + 0.03, height + 0.1), { tone: 0.66, z: 0.12, depth: 0.03, wobble: 0.004, warp: 0 }));
  }
  return group(parts, { at });
}

// A sky: a sheet lit from within, a disc and a few cut clouds on spacers.
function sky({ at, width = 16, height = 11, tone = 0.46, power = 0.55, sun = [1, 5, 0.5], clouds = [] }) {
  const parts = [card(rect(-width / 2, 0, width / 2, height), { tone, glow: power, wobble: 0, bevel: 0, warp: 0 })];
  if (sun) parts.push(card(disc(sun[0], sun[1], sun[2], 14), { tone: 0.92, glow: 1.4, z: 0.1, wobble: 0.008, warp: 0 }));
  for (const [x, y, s] of clouds) {
    const out = [[x + 0.9 * s, y], ...arc(x + 0.55 * s, y, 0.34 * s, 0, 180, 6).slice(1), ...arc(x, y + 0.1 * s, 0.42 * s, 20, 170, 6), ...arc(x - 0.55 * s, y, 0.3 * s, 10, 180, 5), [x - 0.9 * s, y]];
    parts.push(card(out, { tone: 0.72, glow: 0.3, z: 0.2, depth: 0.03, wobble: 0.01 }));
  }
  return group(parts, { at });
}

// A market stall from the front: posts, a striped scalloped awning, a counter loaded with crates, fruit and a hanging scale.
function stall({ at, width = 2, height = 2.3, tone = 0.32, goods = 0 }, { random }) {
  const w = width / 2, parts = [];
  for (const s of [-1, 1]) parts.push(card(rect(s * w - 0.05, 0, s * w + 0.05, height + 0.1), { tone: 0.2, depth: 0.03, wobble: 0.008 }));
  parts.push(card(rect(-w + 0.02, height * 0.42, w - 0.02, height), { tone: 0.1, z: -0.1, wobble: 0.01 })); // the dark inside of the stall
  parts.push(...awning(-w - 0.16, w + 0.16, height - 0.1, 0.52, Math.round(width * 3.4) | 1, 0.24));
  parts.push(card(rect(-w - 0.16, height + 0.4, w + 0.16, height + 0.56), { tone: 0.3, z: 0.3 }));
  parts.push(card(rect(-w, 0, w, 0.82), { tone, z: 0.3 })); // counter
  parts.push(card(rect(-w - 0.05, 0.78, w + 0.05, 0.88), { tone: tone + 0.3, z: 0.36, depth: 0.03 }));
  for (let i = 0; i < 4; i++) parts.push(strip([[-w + width * (i + 0.5) / 4, 0.04], [-w + width * (i + 0.5) / 4, 0.76]], 0.02, { tone: tone - 0.14, z: 0.35, depth: 0.006 }));
  const crates = Math.max(2, Math.round(width / 0.62));
  for (let i = 0; i < crates; i++) {
    const x = -w + width * (i + 0.5) / crates, cw = width / crates * 0.42;
    for (let f = 0; f < 11; f++) { // fruit heaped above the crate edge
      const row = f < 5 ? 0 : f < 9 ? 1 : 2, fx = x + (f % 5 - 2 + row * 0.5 + (row === 2 ? f - 9 : 0)) * cw * 0.42, fy = 1.12 + row * 0.13;
      parts.push(card(disc(fx, fy, 0.085 - (goods % 3) * 0.012, 8, 0.085), { tone: 0.5 + ((i + goods) % 3) * 0.17 + (random() - 0.5) * 0.08, z: 0.14 + f * 0.012, depth: 0.02, wobble: 0.004, warp: 0, bevel: 0.006 }));
    }
    parts.push(card(rect(x - cw, 0.86, x + cw, 1.14), { tone: 0.42, z: 0.34 }));
    for (const y of [0.92, 1.02]) parts.push(strip([[x - cw, y], [x + cw, y]], 0.03, { tone: 0.62, z: 0.39, depth: 0.012 }));
  }
  // a hanging balance scale
  const sx = w * 0.45, sy = height - 0.42;
  parts.push(strip([[sx, height - 0.1], [sx, sy]], 0.018, { tone: 0.7, z: 0.2, depth: 0.008 }), strip([[sx - 0.26, sy - 0.02], [sx + 0.26, sy + 0.02]], 0.03, { tone: 0.7, z: 0.21, depth: 0.01 }));
  for (const s of [-1, 1]) {
    parts.push(strip([[sx + s * 0.26, sy], [sx + s * 0.17, sy - 0.3]], 0.012, { tone: 0.7, z: 0.2, depth: 0.006 }), strip([[sx + s * 0.26, sy], [sx + s * 0.35, sy - 0.3]], 0.012, { tone: 0.7, z: 0.2, depth: 0.006 }));
    parts.push(card([...arc(sx + s * 0.26, sy - 0.3, 0.11, 180, 360, 6)], { tone: 0.74, z: 0.22, depth: 0.02, wobble: 0.004, warp: 0 }));
  }
  return group(parts, { at });
}

// Pennants on a sagging string across the stage.
function bunting({ at, width = 6, sag = 0.5, count = 14 }) {
  const line = [], parts = [];
  for (let i = 0; i <= 16; i++) {
    const f = i / 16;
    line.push([-width / 2 + width * f, -sag * 4 * f * (1 - f)]);
  }
  parts.push(strip(line, 0.022, { tone: 0.6, depth: 0.01 }));
  for (let i = 0; i < count; i++) {
    const f = (i + 0.5) / count, x = -width / 2 + width * f, y = -sag * 4 * f * (1 - f);
    parts.push(card([[x - 0.11, y], [x, y - 0.3], [x + 0.11, y]], { tone: i % 2 ? 0.76 : 0.3, z: 0.03, depth: 0.012, wobble: 0.006, warp: 0, bevel: 0.006 }));
  }
  return group(parts, { at });
}

// A person seen from behind: a cut silhouette, no face, a coat and a bag.
function figure({ at, height = 1.5, tone = 0.2, bag = true, flip = false }) {
  const h = height, f = flip ? -1 : 1, P = (list) => list.map(([x, y]) => [x * f * h, y * h]);
  const body = [[-0.12, 0], [-0.03, 0], [-0.015, 0.4], [0.015, 0.4], [0.04, 0], [0.13, 0], [0.13, 0.42], [0.17, 0.74], [0.11, 0.8], [0.05, 0.83], [-0.05, 0.83], [-0.11, 0.8], [-0.17, 0.74], [-0.13, 0.42]];
  const parts = [card(P(flip ? body.reverse() : body), { tone, depth: 0.03, wobble: 0.008, warp: 0 }), card(disc(0, 0.91 * h, 0.075 * h, 9, 0.09 * h), { tone, depth: 0.03, wobble: 0.004, warp: 0 })];
  if (bag) {
    parts.push(strip([[0.17 * f * h, 0.72 * h], [0.24 * f * h, 0.42 * h]], 0.02, { tone: tone + 0.1, z: 0.03, depth: 0.01 }));
    parts.push(card([[0.17 * f * h, 0.42 * h], [0.31 * f * h, 0.42 * h], [0.29 * f * h, 0.24 * h], [0.19 * f * h, 0.24 * h]].slice(...(flip ? [0] : [0])), { tone: tone + 0.2, z: 0.03, depth: 0.02, wobble: 0.005, warp: 0 }));
  }
  return group(parts, { at });
}

// A blackboard: a dark sheet in a frame, its chalk lines cut from pale paper. Shapes only, never a letter or a digit.
function blackboard({ at, width = 2.6, height = 1.5 }) {
  const w = width / 2, h = height / 2, parts = [
    card(rect(-w - 0.09, -h - 0.09, w + 0.09, h + 0.09), { tone: 0.58 }),
    card(rect(-w, -h, w, h), { tone: 0.1, z: 0.08 }),
    card(rect(-w - 0.16, -h - 0.17, w + 0.16, -h - 0.09), { tone: 0.66, z: 0.14, depth: 0.05 }),
    card(rect(-w * 0.5, -h - 0.11, -w * 0.5 + 0.2, -h - 0.05), { tone: 0.9, z: 0.19, depth: 0.02, wobble: 0.003, warp: 0 }),
  ];
  const chalk = (points, width2 = 0.022) => parts.push(strip(points, width2, { tone: 0.86, z: 0.2, depth: 0.008 }));
  chalk([[-w * 0.8, -h * 0.5], [-w * 0.3, -h * 0.5], [-w * 0.3, h * 0.45], [-w * 0.8, -h * 0.5]]); // a right triangle
  chalk([[-w * 0.4, -h * 0.5], [-w * 0.4, -h * 0.34], [-w * 0.3, -h * 0.34]], 0.016);
  chalk(arc(w * 0.08, 0, h * 0.5, 0, 360, 14)); // a circle with its radius
  chalk([[w * 0.08, 0], [w * 0.08 + h * 0.5, 0]], 0.016);
  chalk([[w * 0.42, -h * 0.6], [w * 0.42, h * 0.6]]); // a parabola on axes
  chalk([[w * 0.3, -h * 0.34], [w * 0.92, -h * 0.34]]);
  const curve = [];
  for (let i = -6; i <= 6; i++) curve.push([w * 0.62 + i * 0.044 * w, -h * 0.34 + (36 - i * i) * 0.024 * h]);
  chalk(curve);
  return group(parts, { at });
}

function clock({ at, r = 0.3 }) {
  return group([card(disc(0, 0, r, 18), { tone: 0.72 }), card(disc(0, 0, r * 0.84, 16), { tone: 0.86, z: 0.07, depth: 0.012, wobble: 0.004, warp: 0 }),
    ...Array.from({ length: 12 }, (_, i) => {
      const a = i * Math.PI / 6;
      return strip([[Math.cos(a) * r * 0.66, Math.sin(a) * r * 0.66], [Math.cos(a) * r * 0.78, Math.sin(a) * r * 0.78]], 0.012, { tone: 0.2, z: 0.09, depth: 0.004 });
    }),
    strip([[0, 0], [r * 0.3, r * 0.42]], 0.03, { tone: 0.14, z: 0.1, depth: 0.01 }), strip([[0, 0], [-r * 0.2, r * 0.66]], 0.02, { tone: 0.14, z: 0.11, depth: 0.01 })], { at });
}

// A row of classroom seats from behind: chair backs in front of desks, each desk a plank on legs.
function deskRow({ at, count = 3, spacing = 1, tone = 0.42 }) {
  const parts = [];
  for (let i = 0; i < count; i++) {
    const x = (i - (count - 1) / 2) * spacing;
    parts.push(card(rect(x - 0.4, 0.68, x + 0.4, 0.76), { tone: tone + 0.26, depth: 0.05 })); // desk top
    parts.push(card(rect(x - 0.4, 0.42, x + 0.4, 0.68), { tone: tone - 0.14, z: -0.02 })); // its modesty board
    for (const s of [-1, 1]) parts.push(card(rect(x + s * 0.36 - 0.03, 0, x + s * 0.36 + 0.03, 0.68), { tone: tone - 0.1, depth: 0.03, wobble: 0.006, warp: 0 }));
    const back = [[x - 0.2, 0.46], [x + 0.2, 0.46], ...arc(x + 0.08, 0.82, 0.12, 0, 90, 4), ...arc(x - 0.08, 0.82, 0.12, 90, 180, 4)];
    parts.push(card(rect(x - 0.2, 0.42, x + 0.2, 0.47), { tone: tone + 0.2, z: 0.42, depth: 0.03, wobble: 0.006, warp: 0 }));
    parts.push(card(back, { tone, z: 0.5, holes: [rect(x - 0.1, 0.66, x + 0.1, 0.74)], wobble: 0.006, bevel: 0.008 }));
    for (const s of [-1, 1]) parts.push(card(rect(x + s * 0.17 - 0.025, 0, x + s * 0.17 + 0.025, 0.46), { tone: tone - 0.16, z: 0.5, depth: 0.03, wobble: 0.004, warp: 0 }));
  }
  return group(parts, { at });
}

// A teacher's desk with a globe on its stand and a stack of books.
function teacherDesk({ at, width = 1.8 }) {
  const w = width / 2, parts = [
    card(rect(-w, 0, w, 0.74), { tone: 0.34 }), card(rect(-w * 0.8, 0.1, w * 0.8, 0.64), { tone: 0.44, z: 0.08, depth: 0.03 }), card(rect(-w - 0.08, 0.72, w + 0.08, 0.82), { tone: 0.62, z: 0.04 }),
  ];
  const gx = w * 0.55;
  parts.push(card(rect(gx - 0.12, 0.82, gx + 0.12, 0.87), { tone: 0.3, z: -0.02, depth: 0.03, wobble: 0.004, warp: 0 }), strip([[gx, 0.85], [gx, 0.96]], 0.03, { tone: 0.3, z: -0.02, depth: 0.02 }));
  parts.push(card(disc(gx, 1.18, 0.22, 14), { tone: 0.55, z: -0.03 }), strip(arc(gx, 1.18, 0.27, -70, 110, 8), 0.024, { tone: 0.3, z: 0.03, depth: 0.012 }));
  parts.push(card([[gx - 0.14, 1.26], [gx - 0.02, 1.33], [gx + 0.07, 1.24], [gx + 0.02, 1.13], [gx - 0.1, 1.12]], { tone: 0.26, z: 0.04, depth: 0.01, wobble: 0.01, warp: 0, bevel: 0.004 })); // land
  parts.push(card([[gx + 0.06, 1.1], [gx + 0.16, 1.14], [gx + 0.12, 1.02], [gx + 0.05, 1.02]], { tone: 0.26, z: 0.04, depth: 0.01, wobble: 0.008, warp: 0, bevel: 0.004 }));
  [[-w * 0.5, 0.82, 0.3, 0.07, 0.3], [-w * 0.48, 0.89, 0.27, 0.06, 0.7], [-w * 0.51, 0.95, 0.24, 0.07, 0.46]].forEach(([x, y, half, tall, t], i) => {
    parts.push(card(rect(x - half, y, x + half, y + tall), { tone: t, z: 0.03 + i * 0.01, depth: 0.03, wobble: 0.004, warp: 0 }));
  });
  return group(parts, { at });
}

function bookcase({ at, width = 1.2, height = 2.4 }, { random }) {
  const w = width / 2, parts = [card(rect(-w, 0, w, height), { tone: 0.5 }), card(rect(-w + 0.06, 0.06, w - 0.06, height - 0.06), { tone: 0.12, z: 0.06, depth: 0.02, wobble: 0.005, warp: 0 })];
  const shelves = 4;
  for (let s = 0; s < shelves; s++) {
    const y = 0.08 + s * (height - 0.14) / shelves;
    parts.push(card(rect(-w + 0.04, y, w - 0.04, y + 0.05), { tone: 0.6, z: 0.14, depth: 0.03 }));
    let x = -w + 0.1;
    while (x < w - 0.2) {
      const b = 0.05 + random() * 0.05, t = 0.25 + random() * 0.45, tall = 0.26 + random() * 0.16;
      parts.push(card(rect(x, y + 0.05, x + b, y + 0.05 + tall), { tone: t, z: 0.12, depth: 0.02, wobble: 0.003, warp: 0, bevel: 0.004 }));
      x += b + 0.012;
    }
  }
  return group(parts, { at });
}

// Rows of hanging lamps above a room.
function pendant({ at, drop = 1.2 }) {
  return group([strip([[0, 0], [0, -drop]], 0.02, { tone: 0.3, depth: 0.012 }),
    card([[-0.2, -drop - 0.2], [0.2, -drop - 0.2], [0.07, -drop], [-0.07, -drop]], { tone: 0.5, z: 0.02, depth: 0.03, wobble: 0.006, warp: 0 }),
    card(arc(0, -drop - 0.2, 0.09, 180, 360, 6), { tone: 0.9, glow: 1.2, z: 0.01, depth: 0.02, wobble: 0, bevel: 0, warp: 0 })], { at });
}

// Hills: a sheet with a long rolling top edge.
function hill({ at, width = 18, height = 2, tone = 0.3, roll = 0.5, wave = 0.5, phase = 0 }, { random }) {
  const top = [];
  for (let x = width / 2; x >= -width / 2; x -= 0.5) top.push([x, height + roll * Math.sin(x * wave + phase) + roll * 0.4 * Math.sin(x * wave * 2.3 + phase) + (random() - 0.5) * 0.04]);
  return group([card([[-width / 2, 0], [width / 2, 0], ...top], { tone, depth: 0.04 })], { at });
}

// A stone bridge: a sheet with arches cut through, ring stones, courses scored across it, a parapet of balusters.
function bridge({ at, width = 12, height = 2.5, arches = 3, span = 1.9, pier = 0.6, tone = 0.46, water = 0.3 }, { random }) {
  const parts = [], holes = [], total = arches * span + (arches - 1) * pier, spring = height * 0.42;
  const X = (i) => -total / 2 + span / 2 + i * (span + pier);
  for (let i = 0; i < arches; i++) {
    const x = X(i), r = span / 2;
    holes.push([[x - r, water], [x + r, water], ...arc(x, spring, r, 0, 180, 14)]);
  }
  parts.push(card(rect(-width / 2, 0, width / 2, height), { holes, tone, depth: 0.05, wobble: 0.012 }));
  for (let i = 0; i < arches; i++) { // ring stones
    const x = X(i), r = span / 2, stones = 11;
    for (let s = 0; s < stones; s++) {
      const a0 = s / stones * 180 + 1.5, a1 = (s + 1) / stones * 180 - 1.5, out = r + 0.2 + (s % 2) * 0.05;
      parts.push(card([...arc(x, spring, r, a0, a1, 2), ...arc(x, spring, out, a1, a0, 2)], { tone: tone + 0.14 + (random() - 0.5) * 0.1, z: 0.09, depth: 0.03, wobble: 0.006, warp: 0, bevel: 0.008 }));
    }
    if (i < arches - 1) { // a cutwater at the foot of the pier
      const c = x + r + pier / 2;
      parts.push(card([[c - pier / 2 - 0.06, 0], [c + pier / 2 + 0.06, 0], [c, spring * 0.78]], { tone: tone - 0.12, z: 0.1, wobble: 0.01 }));
    }
  }
  for (let c = 0; c < 26; c++) { // loose stones scored into the spandrels
    const x = (random() - 0.5) * width * 0.9, y = height * (0.45 + random() * 0.45);
    parts.push(card(rect(x - 0.14, y, x + 0.14, y + 0.1), { tone: tone + (random() - 0.5) * 0.14, z: 0.06, depth: 0.012, wobble: 0.006, warp: 0, bevel: 0.006 }));
  }
  parts.push(card(rect(-width / 2, height - 0.04, width / 2, height + 0.08), { tone: tone + 0.2, z: 0.1, depth: 0.05 }));
  for (let x = -width / 2 + 0.15; x < width / 2; x += 0.34) { // balusters
    parts.push(card([[x - 0.05, height + 0.08], [x + 0.05, height + 0.08], [x + 0.032, height + 0.26], [x + 0.05, height + 0.4], [x - 0.05, height + 0.4], [x - 0.032, height + 0.26]], { tone: tone + 0.06, z: 0.03, depth: 0.03, wobble: 0.004, warp: 0, bevel: 0.006 }));
  }
  parts.push(card(rect(-width / 2, height + 0.4, width / 2, height + 0.5), { tone: tone + 0.22, z: 0.05 }));
  return group(parts, { at });
}

// Water: a strip with a cut wavelet edge and a few pale glints on spacers.
function waterRow({ at, width = 16, height = 0.28, tone = 0.3, glints = 5 }, { random }) {
  const top = [];
  for (let x = width / 2; x > -width / 2; x -= 0.34) top.push(...arc(x - 0.17, height, 0.17, 0, 180, 4, 0.05));
  const parts = [card([[-width / 2, 0], [width / 2, 0], ...top], { tone, depth: 0.03, wobble: 0.004, bevel: 0.012 })];
  for (let i = 0; i < glints; i++) {
    const x = (random() - 0.5) * width * 0.5, half = 0.14 + random() * 0.3;
    parts.push(card([[x - half, height * 0.5], [x + half, height * 0.5], [x, height * 0.72]], { tone: tone + 0.34, z: 0.05, depth: 0.01, wobble: 0.004, warp: 0, bevel: 0.004 }));
  }
  return group(parts, { at });
}

function bank({ at, side = -1, width = 5, height = 1, slope = 2.4, tone = 0.34 }, { random }) {
  const s = side, top = [];
  for (let i = 0; i <= 8; i++) {
    const f = i / 8;
    top.push([s * (width - slope * (1 - f) * 0) * f, height * (f < 0.3 ? f / 0.3 : 1) + (random() - 0.5) * 0.05]);
  }
  const outline = s > 0 ? [[0, 0], ...top.slice(1).map(([x, y]) => [x, y]), [width, 0]].reverse() : [[0, 0], [-width, 0], ...top.slice(1).reverse()];
  const parts = [card(outline, { tone, depth: 0.05 })];
  for (let i = 0; i < 12; i++) { // reeds
    const x = s * (0.2 + random() * 1.2), y = height * Math.min(1, Math.abs(x) / (width * 0.3)), tall = 0.3 + random() * 0.4;
    parts.push(strip([[x, y * 0.7], [x + (random() - 0.5) * 0.14, y + tall]], 0.024, { tone: tone - 0.12 + random() * 0.1, z: 0.07, depth: 0.012 }));
  }
  return group(parts, { at });
}

// A paper boat, folded as children fold it.
function paperBoat({ at, size = 1 }) {
  const k = size;
  const P = (l) => l.map(([x, y]) => [x * k, y * k]);
  return group([
    card(P([[0, 0.34], [0, 0.72], [0.34, 0.34]]), { tone: 0.72, z: 0, depth: 0.012, wobble: 0.006, warp: 0, bevel: 0.006 }),
    card(P([[0, 0.34], [-0.28, 0.34], [0, 0.66]]), { tone: 0.56, z: 0.02, depth: 0.012, wobble: 0.006, warp: 0, bevel: 0.006 }),
    card(P([[-0.56, 0.36], [0.56, 0.36], [0.36, 0], [-0.36, 0]]), { tone: 0.82, z: 0.05, depth: 0.012, wobble: 0.006, warp: 0, bevel: 0.006 }),
    card(P([[-0.56, 0.36], [0, 0.36], [-0.14, 0]]), { tone: 0.62, z: 0.07, depth: 0.012, wobble: 0.004, warp: 0, bevel: 0.006 }),
  ], { at });
}

// A floor for a room seen from above: long boards that run away from the camera.
function plankFloor({ at, width = 12, z = [-5, 9], planks = 12, tone = 0.3 }, { random }) {
  const parts = [], w = width / planks;
  for (let i = 0; i < planks; i++) {
    const x = -width / 2 + i * w, plank = card(rect(x + 0.006, z[0], x + w - 0.006, z[1]), { tone: tone + (random() - 0.5) * 0.07, depth: 0.012, wobble: 0.008, bevel: 0.006, warp: 0, spin: 0.001 });
    plank.rotation.x = Math.PI / 2;
    parts.push(plank);
  }
  return group(parts, { at });
}

// A plain dark upright close to the lens, for a move that wipes across the frame: a trunk, a column, a door jamb.
function wipe({ at, width = 1, height = 12, tone = 0.1 }) {
  return group([card(rect(-width / 2, -1, width / 2, height), { tone, depth: 0.05, wobble: 0.03 })], { at });
}

export const PROPS = {
  house, lamp, tree, "traffic-light": trafficLight, "road-row": roadRow, sky, stall, bunting, figure, blackboard, clock, "desk-row": deskRow,
  "teacher-desk": teacherDesk, bookcase, pendant, hill, bridge, "water-row": waterRow, bank, "paper-boat": paperBoat, wipe, "plank-floor": plankFloor,
};
