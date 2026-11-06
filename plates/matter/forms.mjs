// plates/matter/forms.mjs
// Defines visual parameters, form types, and spatial layouts for the 6 matter forms.
// Forms: pile, split, too-tall, pour, resort, versus.
// Strict determinism: purely a function of spec, count, and seed. No Math.random or clock.

import { seeded } from "../lib/seeded.mjs";

/**
 * Visual & physical constants
 */
export const DEFAULT_BLOCK_SIZE = 0.42; // unit cube dimension in 3D scene units
export const DEFAULT_BLOCK_GAP = 0.03;  // visual gap between blocks to preserve edge contrast
export const DEFAULT_TABLE_Y = 0.0;     // table ground plane height

export const FORMS = Object.freeze(["pile", "split", "too-tall", "pour", "resort", "versus"]);

export const FORM_DESCRIPTIONS = Object.freeze({
  pile: "Blocks crash onto a table in structured waves, settling into a monolithic mound.",
  split: "Monolithic stack divides into constituent budget shares; one share slides forward/sideways and stacks into a tidy cube while the rest holds still.",
  "too-tall": "Dense vertical monolithic column climbing past the top of the screen (communicating extreme ratio).",
  pour: "Continuous stream into a heap.",
  resort: "Blocks regroup from one grouping to another while preserving their individual identity.",
  versus: "Two comparative piles side by side.",
});

// Grayscale tonal luminance tiers for groups (pure tone only, no saturated hues)
export const GROUP_TONES = Object.freeze([
  0xffffff, // 100% white (primary/main)
  0xbbbbbb, // 73% light gray
  0x888888, // 53% medium gray
  0x5c5c5c, // 36% dark gray
  0x3c3c3c  // 24% deep charcoal
]);

/**
 * Returns block dimension specs.
 * @param {object} [spec={}]
 * @returns {{width: number, height: number, depth: number, size: number, gap: number, step: number}}
 */
export function getBlockDimensions(spec = {}) {
  const size = typeof spec.block_size === "number" && spec.block_size > 0 ? spec.block_size : DEFAULT_BLOCK_SIZE;
  const gap = typeof spec.block_gap === "number" && spec.block_gap >= 0 ? spec.block_gap : DEFAULT_BLOCK_GAP;
  return {
    width: size,
    height: size,
    depth: size,
    size,
    gap,
    step: size + gap
  };
}

/**
 * Assigns N blocks to constituent groups based on spec.groups or defaults.
 * @param {number} count Total number of blocks (N)
 * @param {Array<object>} [groupsSpec=[]] Array of group definitions, e.g. [{ name: "health", fact: 600, count: 60 }]
 * @returns {{ assignments: Array<object>, groups: Array<object> }}
 */
export function assignGroups(count, groupsSpec = [], form = "") {
  if (!Number.isInteger(count) || count <= 0) {
    throw new Error(`Invalid block count: ${count}`);
  }

  let groupList = [];
  if (Array.isArray(groupsSpec) && groupsSpec.length > 0) {
    let allocated = 0;
    groupList = groupsSpec.map((g, idx) => {
      const gCount = typeof g.count === "number" ? g.count : (typeof g.blocks === "number" ? g.blocks : Math.round(count * (g.share || 1 / groupsSpec.length)));
      allocated += gCount;
      return {
        id: g.name || `group_${idx}`,
        name: g.name || `Group ${idx + 1}`,
        fact: g.fact ?? null,
        count: gCount,
        index: idx,
        tone: GROUP_TONES[idx % GROUP_TONES.length],
      };
    });

    // Reconcile rounding discrepancies if counts don't sum to total count
    const diff = count - allocated;
    if (diff !== 0 && groupList.length > 0) {
      groupList[groupList.length - 1].count += diff;
    }
  } else if (form === "versus") {
    const half = Math.floor(count * 0.5);
    groupList = [
      { id: "group_a", name: "Side A", fact: null, count: half, index: 0, tone: GROUP_TONES[0] },
      { id: "group_b", name: "Side B", fact: null, count: count - half, index: 1, tone: GROUP_TONES[1] }
    ];
  } else if (form === "split") {
    const shareCount = Math.max(1, Math.floor(count * 0.3));
    groupList = [
      { id: "main", name: "Main Stack", fact: null, count: count - shareCount, index: 0, tone: GROUP_TONES[0] },
      { id: "share", name: "Budget Share", fact: null, count: shareCount, index: 1, tone: GROUP_TONES[1] }
    ];
  } else {
    groupList = [{
      id: "total",
      name: "Total",
      fact: null,
      count,
      index: 0,
      tone: GROUP_TONES[0]
    }];
  }

  // Build per-block assignment array
  const assignments = new Array(count);
  let cursor = 0;
  for (const group of groupList) {
    const end = Math.min(count, cursor + group.count);
    group.startIndex = cursor;
    group.endIndex = end;
    for (let i = cursor; i < end; i++) {
      assignments[i] = {
        blockIndex: i,
        groupId: group.id,
        groupName: group.name,
        groupIndex: group.index,
        tone: group.tone
      };
    }
    cursor = end;
  }

  return { assignments, groups: groupList };
}

/**
 * Computes Axis-Aligned Bounding Box (AABB) and centroid from positions.
 * @param {Array<[number, number, number]>|Float32Array} positions
 * @param {Array<object>} [assignments=null]
 * @returns {{ total: { min: number[], max: number[], size: number[], centroid: number[] }, groups: Record<string, { min: number[], max: number[], size: number[], centroid: number[] }> }}
 */
export function computeGroupBounds(positions, assignments = null) {
  const isFlat = positions instanceof Float32Array;
  const count = isFlat ? positions.length / 3 : positions.length;

  const totalMin = [Infinity, Infinity, Infinity];
  const totalMax = [-Infinity, -Infinity, -Infinity];
  const totalSum = [0, 0, 0];

  const groupData = {};

  for (let i = 0; i < count; i++) {
    const x = isFlat ? positions[i * 3] : positions[i][0];
    const y = isFlat ? positions[i * 3 + 1] : positions[i][1];
    const z = isFlat ? positions[i * 3 + 2] : positions[i][2];

    // Total bounds
    if (x < totalMin[0]) totalMin[0] = x;
    if (y < totalMin[1]) totalMin[1] = y;
    if (z < totalMin[2]) totalMin[2] = z;
    if (x > totalMax[0]) totalMax[0] = x;
    if (y > totalMax[1]) totalMax[1] = y;
    if (z > totalMax[2]) totalMax[2] = z;

    totalSum[0] += x;
    totalSum[1] += y;
    totalSum[2] += z;

    if (assignments && assignments[i]) {
      const gid = assignments[i].groupId;
      if (!groupData[gid]) {
        groupData[gid] = {
          min: [Infinity, Infinity, Infinity],
          max: [-Infinity, -Infinity, -Infinity],
          sum: [0, 0, 0],
          count: 0
        };
      }
      const gd = groupData[gid];
      if (x < gd.min[0]) gd.min[0] = x;
      if (y < gd.min[1]) gd.min[1] = y;
      if (z < gd.min[2]) gd.min[2] = z;
      if (x > gd.max[0]) gd.max[0] = x;
      if (y > gd.max[1]) gd.max[1] = y;
      if (z > gd.max[2]) gd.max[2] = z;
      gd.sum[0] += x;
      gd.sum[1] += y;
      gd.sum[2] += z;
      gd.count++;
    }
  }

  const totalCentroid = count > 0 ? [totalSum[0] / count, totalSum[1] / count, totalSum[2] / count] : [0, 0, 0];
  const totalSize = [
    totalMax[0] - totalMin[0],
    totalMax[1] - totalMin[1],
    totalMax[2] - totalMin[2]
  ];

  const groups = {};
  for (const [gid, gd] of Object.entries(groupData)) {
    groups[gid] = {
      min: gd.min,
      max: gd.max,
      size: [gd.max[0] - gd.min[0], gd.max[1] - gd.min[1], gd.max[2] - gd.min[2]],
      centroid: [gd.sum[0] / gd.count, gd.sum[1] / gd.count, gd.sum[2] / gd.count],
      count: gd.count
    };
  }

  return {
    total: { min: totalMin, max: totalMax, size: totalSize, centroid: totalCentroid, count },
    groups
  };
}

/**
 * Builds a natural pyramid / conical mound resting layout on the table (y >= 0).
 * Perfectly deterministic, fills layers from ground upward, centered at (centerX, 0, centerZ).
 * Guaranteed: every block at layer l > 0 has a supporting block at layer l - 1.
 */
function buildMoundPositions(count, step, blockSize, centerX = 0, centerZ = 0) {
  const positions = new Array(count);
  const halfBlock = blockSize / 2;

  // Approximate search bounds
  const estRadius = Math.max(2, Math.ceil(Math.cbrt((3 * count) / (0.75 * Math.PI))));
  const maxSearchR = estRadius + 6;
  const maxLayers = Math.max(3, Math.ceil(estRadius * 1.5));

  // Collect candidate cells (gx, gz, layer)
  const candidates = [];
  for (let l = 0; l <= maxLayers; l++) {
    for (let gx = -maxSearchR; gx <= maxSearchR; gx++) {
      for (let gz = -maxSearchR; gz <= maxSearchR; gz++) {
        const r2 = gx * gx + gz * gz;
        // Score strictly increases with l and with r2, ensuring layer l-1 is always chosen before layer l
        const score = r2 + l * 4.6;
        candidates.push({ gx, gz, l, score });
      }
    }
  }

  // Sort candidates by score
  candidates.sort((a, b) => a.score - b.score);

  for (let i = 0; i < count; i++) {
    const cell = candidates[i] || {
      gx: (i % 10) - 5,
      gz: Math.floor(i / 10) - 5,
      l: Math.floor(i / 100)
    };
    positions[i] = [
      centerX + cell.gx * step,
      cell.l * step + halfBlock,
      centerZ + cell.gz * step
    ];
  }

  return positions;
}

/**
 * Builds a compact rectangular cuboid layout of blocks.
 */
function buildCuboidPositions(count, step, blockSize, centerX = 0, centerZ = 0, preferredW = null) {
  const positions = new Array(count);
  const halfBlock = blockSize / 2;

  const w = preferredW || Math.max(1, Math.round(Math.cbrt(count)));
  const d = Math.max(1, Math.round(Math.sqrt(count / w)));
  const layerCapacity = w * d;

  for (let i = 0; i < count; i++) {
    const l = Math.floor(i / layerCapacity);
    const inLayer = i % layerCapacity;
    const gx = (inLayer % w) - (w - 1) / 2;
    const gz = Math.floor(inLayer / w) - (d - 1) / 2;

    positions[i] = [
      centerX + gx * step,
      l * step + halfBlock,
      centerZ + gz * step
    ];
  }

  return positions;
}

/**
 * 1. FORM: pile
 * Blocks crash onto a table in structured waves, settling into a mound.
 */
function layoutPile(count, dims, spec, rand) {
  const restPositions = buildMoundPositions(count, dims.step, dims.size);
  const initialPositions = new Array(count);
  const timing = new Array(count);

  for (let i = 0; i < count; i++) {
    const [rx, ry, rz] = restPositions[i];
    // Wave assignment (4-5 cascading drop waves)
    const wave = Math.floor((i / count) * 5);
    const waveDelay = wave * 0.42 + rand() * 0.18;
    const skyY = ry + 10.0 + wave * 2.2 + rand() * 1.2;
    const jitterX = (rand() - 0.5) * 0.35;
    const jitterZ = (rand() - 0.5) * 0.35;

    initialPositions[i] = [rx + jitterX, skyY, rz + jitterZ];
    timing[i] = {
      startTime: waveDelay,
      fallDuration: 0.62,
      impactTime: waveDelay + 0.62,
      bounceDecay: 6.5,
      frequency: 18.0,
      settleTime: waveDelay + 1.25
    };
  }

  return { restPositions, initialPositions, timing };
}

/**
 * 2. FORM: split
 * Monolithic stack divides into constituent budget shares; one share slides forward/sideways
 * and stacks into a tidy cube while the rest holds still.
 */
function layoutSplit(count, dims, spec, rand, groupData) {
  const groups = groupData.groups;
  const assignments = groupData.assignments;

  // Initial configuration: one single monolithic stack containing all N blocks
  const initialPositions = buildCuboidPositions(count, dims.step, dims.size, 0, 0);

  // Target configuration:
  // Share 0 remains at [-gapX, 0, 0]
  // Share 1 (and subsequent shares) slide to [+gapX, 0, +gapZ] as tidy cubes
  const restPositions = new Array(count);
  const timing = new Array(count);

  const mainGroup = groups[0] || { startIndex: 0, endIndex: count };
  const share1Group = groups[1] || null;

  // Dimensions of share 1 cube
  const share1Count = share1Group ? share1Group.count : Math.floor(count * 0.3);
  const share1W = Math.max(1, Math.round(Math.cbrt(share1Count)));
  const share1Positions = buildCuboidPositions(share1Count, dims.step, dims.size, 0, 0, share1W);

  // Separation distance calibrated for 9:16 vertical composition
  // Ensures both shares fit symmetrically inside 1080px width
  const sepX = Math.min(1.6, Math.max(1.1, Math.cbrt(share1Count) * dims.step * 0.6 + 0.5));
  const sepZ = 0.4;

  // Symmetrically balance main group and share around X = 0
  const mainShiftX = -sepX * 0.5;
  const shareShiftX = sepX * 0.5;

  for (let i = 0; i < count; i++) {
    const isShare1 = share1Group ? (assignments[i].groupId === share1Group.id) : (i >= count - share1Count);

    if (!isShare1) {
      // Main share: holds position (with tiny settling shift to center)
      const [ix, iy, iz] = initialPositions[i];
      restPositions[i] = [ix + mainShiftX, iy, iz];
      timing[i] = {
        startTime: 1.0,
        endTime: 2.2,
        isMoving: false
      };
    } else {
      // Split share: slides forward/sideways into a tidy cube
      const subIdx = share1Group ? (i - share1Group.startIndex) : (i - (count - share1Count));
      const [sx, sy, sz] = share1Positions[subIdx] || [0, dims.size / 2, 0];
      restPositions[i] = [sx + shareShiftX, sy, sz + sepZ];
      timing[i] = {
        startTime: 1.2,
        endTime: 4.2,
        isMoving: true,
        liftHeight: 0.25
      };
    }
  }

  return { restPositions, initialPositions, timing };
}

/**
 * 3. FORM: too-tall
 * Dense vertical monolithic column climbing past the top of the screen (communicating extreme ratio).
 */
function layoutTooTall(count, dims, spec, rand) {
  const restPositions = new Array(count);
  const initialPositions = new Array(count);
  const timing = new Array(count);

  // Compact footprint: 2x2 for count <= 1200, 3x3 for count > 1200
  const colW = count > 1200 ? 3 : 2;
  const colD = colW;
  const perLayer = colW * colD;
  const halfBlock = dims.size / 2;

  for (let i = 0; i < count; i++) {
    const layer = Math.floor(i / perLayer);
    const inLayer = i % perLayer;
    const gx = (inLayer % colW) - (colW - 1) / 2;
    const gz = Math.floor(inLayer / colW) - (colD - 1) / 2;

    const x = gx * dims.step;
    const z = gz * dims.step;
    const y = layer * dims.step + halfBlock;

    restPositions[i] = [x, y, z];

    // Assembly delay climbing up the tower
    const assembleTime = (layer / Math.max(1, count / perLayer)) * 2.8 + 0.2;
    initialPositions[i] = [x, y + 8.0, z];
    timing[i] = {
      startTime: assembleTime,
      impactTime: assembleTime + 0.35,
      settleTime: assembleTime + 0.6
    };
  }

  return { restPositions, initialPositions, timing };
}

/**
 * 4. FORM: pour
 * Continuous stream into a heap.
 */
function layoutPour(count, dims, spec, rand) {
  const restPositions = buildMoundPositions(count, dims.step, dims.size, 0, 0);
  const initialPositions = new Array(count);
  const timing = new Array(count);

  const spoutY = 14.0;
  const pourStart = 0.3;
  const pourEnd = 4.2;

  for (let i = 0; i < count; i++) {
    const [rx, ry, rz] = restPositions[i];
    // Stream entrance interval
    const enterTime = pourStart + (i / count) * (pourEnd - pourStart);
    const flightDuration = 0.55;
    const landTime = enterTime + flightDuration;

    // Spout entry with micro-swirl
    const angle = (i * 0.37) % (2 * Math.PI);
    const spoutRadius = 0.22 * rand();
    const sx = Math.cos(angle) * spoutRadius;
    const sz = Math.sin(angle) * spoutRadius;

    initialPositions[i] = [sx, spoutY, sz];
    timing[i] = {
      startTime: enterTime,
      landTime,
      settleTime: landTime + 0.3,
      flightDuration
    };
  }

  return { restPositions, initialPositions, timing };
}

/**
 * 5. FORM: resort
 * Blocks regroup from one grouping to another while preserving their individual identity.
 */
function layoutResort(count, dims, spec, rand, groupData) {
  const initialPositions = new Array(count);
  const restPositions = new Array(count);
  const timing = new Array(count);

  // Grouping A (initial): 3 distinct piles side by side
  const numPilesA = 3;
  const perPileA = Math.ceil(count / numPilesA);
  const sepA = 3.6;

  // Pre-generate layout for each sub-pile
  const pileAPos = [];
  for (let p = 0; p < numPilesA; p++) {
    const pCount = Math.min(perPileA, count - p * perPileA);
    const pCenterX = (p - (numPilesA - 1) / 2) * sepA;
    pileAPos.push(buildCuboidPositions(pCount, dims.step, dims.size, pCenterX, 0));
  }

  // Flatten Initial Positions
  let cursorA = 0;
  for (let p = 0; p < numPilesA; p++) {
    const sub = pileAPos[p];
    for (let j = 0; j < sub.length; j++) {
      initialPositions[cursorA++] = sub[j];
    }
  }

  // Grouping B (target): 2 large organized stacks
  const numPilesB = 2;
  const perPileB = Math.ceil(count / numPilesB);
  const sepB = 4.0;
  const pileBPos = [];
  for (let p = 0; p < numPilesB; p++) {
    const pCount = Math.min(perPileB, count - p * perPileB);
    const pCenterX = (p - (numPilesB - 1) / 2) * sepB;
    pileBPos.push(buildCuboidPositions(pCount, dims.step, dims.size, pCenterX, 0));
  }

  let cursorB = 0;
  for (let p = 0; p < numPilesB; p++) {
    const sub = pileBPos[p];
    for (let j = 0; j < sub.length; j++) {
      restPositions[cursorB++] = sub[j];
    }
  }

  // Flight timing for migration
  for (let i = 0; i < count; i++) {
    const stagger = 1.2 + (i / count) * 1.5;
    const duration = 1.4;
    timing[i] = {
      startTime: stagger,
      landTime: stagger + duration,
      arcHeight: 1.8 + (rand() * 0.8)
    };
  }

  return { restPositions, initialPositions, timing };
}

/**
 * 6. FORM: versus
 * Two comparative piles side by side.
 */
function layoutVersus(count, dims, spec, rand, groupData) {
  const groups = groupData.groups;
  const countA = groups.length >= 2 ? groups[0].count : Math.floor(count * 0.5);
  const countB = count - countA;

  // Piles separated along X axis, calibrated for vertical 9:16 frame
  const estRadiusA = Math.ceil(Math.cbrt(countA)) * dims.step;
  const estRadiusB = Math.ceil(Math.cbrt(countB)) * dims.step;
  const sepX = Math.min(1.6, Math.max(1.1, (estRadiusA + estRadiusB) * 0.35 + 0.5));

  const positionsA = buildMoundPositions(countA, dims.step, dims.size, -sepX, 0);
  const positionsB = buildMoundPositions(countB, dims.step, dims.size, +sepX, 0);

  const restPositions = [...positionsA, ...positionsB];
  const initialPositions = new Array(count);
  const timing = new Array(count);

  for (let i = 0; i < count; i++) {
    const [rx, ry, rz] = restPositions[i];
    const wave = Math.floor((i / count) * 4);
    const waveDelay = wave * 0.38 + rand() * 0.15;
    const skyY = ry + 9.0 + wave * 2.0;

    initialPositions[i] = [rx, skyY, rz];
    timing[i] = {
      startTime: waveDelay,
      impactTime: waveDelay + 0.58,
      settleTime: waveDelay + 1.15
    };
  }

  return { restPositions, initialPositions, timing };
}

/**
 * Evaluates block positions [x, y, z] at time t for any form.
 * Deterministic and zero-jump.
 * @param {object} formGeometry Result of getFormGeometry()
 * @param {number} t Current elapsed time in seconds
 * @returns {Array<[number, number, number]>}
 */
export function evaluateBlockPositions(formGeometry, t) {
  const { form, count, restPositions, initialPositions, timing } = formGeometry;
  const result = new Array(count);

  for (let i = 0; i < count; i++) {
    const rest = restPositions[i];
    const init = initialPositions[i];
    const tm = timing[i];

    if (form === "pile" || form === "versus") {
      if (t < tm.startTime) {
        // Holding at sky drop position
        result[i] = [init[0], init[1], init[2]];
      } else if (t < tm.impactTime) {
        // Falling under gravity acceleration
        const p = (t - tm.startTime) / (tm.impactTime - tm.startTime);
        const y = init[1] + (rest[1] - init[1]) * (p * p);
        result[i] = [rest[0], y, rest[2]];
      } else if (t < tm.settleTime) {
        // Damped bounce
        const dt = t - tm.impactTime;
        const decay = Math.exp(-tm.bounceDecay * dt);
        const bounce = Math.abs(Math.cos(tm.frequency * dt)) * decay * 0.6;
        result[i] = [rest[0], rest[1] + bounce, rest[2]];
      } else {
        // Resting on mound
        result[i] = [rest[0], rest[1], rest[2]];
      }
    } else if (form === "split") {
      if (!tm.isMoving || t <= tm.startTime) {
        result[i] = [init[0], init[1], init[2]];
      } else if (t >= tm.endTime) {
        result[i] = [rest[0], rest[1], rest[2]];
      } else {
        // Sliding forward/sideways with smoothstep and subtle arc lift
        const rawP = (t - tm.startTime) / (tm.endTime - tm.startTime);
        // Smootherstep: 6p^5 - 15p^4 + 10p^3
        const p = rawP * rawP * rawP * (rawP * (rawP * 6 - 15) + 10);
        const lift = (tm.liftHeight || 0.2) * Math.sin(Math.PI * p);
        const x = init[0] + (rest[0] - init[0]) * p;
        const y = init[1] + (rest[1] - init[1]) * p + lift;
        const z = init[2] + (rest[2] - init[2]) * p;
        result[i] = [x, y, z];
      }
    } else if (form === "too-tall") {
      if (t < tm.startTime) {
        result[i] = [init[0], init[1], init[2]];
      } else if (t < tm.impactTime) {
        const p = (t - tm.startTime) / (tm.impactTime - tm.startTime);
        const y = init[1] + (rest[1] - init[1]) * (p * p);
        result[i] = [rest[0], y, rest[2]];
      } else if (t < tm.settleTime) {
        const dt = t - tm.impactTime;
        const bounce = Math.sin(dt * 20) * Math.exp(-dt * 8) * 0.15;
        result[i] = [rest[0], rest[1] + Math.max(0, bounce), rest[2]];
      } else {
        result[i] = [rest[0], rest[1], rest[2]];
      }
    } else if (form === "pour") {
      if (t < tm.startTime) {
        // Has not yet exited spout
        result[i] = [init[0], init[1], init[2]];
      } else if (t < tm.landTime) {
        // Flowing in stream
        const p = (t - tm.startTime) / tm.flightDuration;
        const x = init[0] + (rest[0] - init[0]) * p;
        const y = init[1] + (rest[1] - init[1]) * (p * p); // gravity
        const z = init[2] + (rest[2] - init[2]) * p;
        result[i] = [x, y, z];
      } else {
        result[i] = [rest[0], rest[1], rest[2]];
      }
    } else if (form === "resort") {
      if (t <= tm.startTime) {
        result[i] = [init[0], init[1], init[2]];
      } else if (t >= tm.landTime) {
        result[i] = [rest[0], rest[1], rest[2]];
      } else {
        // 3D Migration arc
        const rawP = (t - tm.startTime) / (tm.landTime - tm.startTime);
        const p = rawP * rawP * (3 - 2 * rawP); // smoothstep
        const arc = (tm.arcHeight || 1.5) * Math.sin(Math.PI * p);
        const x = init[0] + (rest[0] - init[0]) * p;
        const y = init[1] + (rest[1] - init[1]) * p + arc;
        const z = init[2] + (rest[2] - init[2]) * p;
        result[i] = [x, y, z];
      }
    } else {
      result[i] = [rest[0], rest[1], rest[2]];
    }
  }

  return result;
}

/**
 * Main form factory: generates complete layout, bounds, and trajectory metadata for a form.
 * @param {string} formName One of FORMS
 * @param {number} count Total number of blocks (1..3000)
 * @param {object} [spec={}] Spec parameters
 * @param {number} [seed=1] Deterministic seed for mulberry32 PRNG
 * @returns {object} Form geometry, bounds, assignments, and layouts
 */
export function getFormGeometry(formName, count, spec = {}, seed = 1) {
  const normForm = (formName || spec.form || "pile").toLowerCase().trim();
  if (!FORMS.includes(normForm)) {
    throw new Error(`Unknown matter form: "${normForm}". Must be one of: ${FORMS.join(", ")}`);
  }
  if (!Number.isInteger(count) || count <= 0) {
    throw new Error(`Invalid block count: ${count}. Must be a positive integer.`);
  }
  if (count > 3000) {
    throw new Error(`Block count ${count} exceeds maximum capacity of 3000 blocks.`);
  }

  const dims = getBlockDimensions(spec);
  const groupData = assignGroups(count, spec.groups, normForm);
  const rand = seeded(seed);

  let layoutData;
  switch (normForm) {
    case "pile":
      layoutData = layoutPile(count, dims, spec, rand);
      break;
    case "split":
      layoutData = layoutSplit(count, dims, spec, rand, groupData);
      break;
    case "too-tall":
      layoutData = layoutTooTall(count, dims, spec, rand);
      break;
    case "pour":
      layoutData = layoutPour(count, dims, spec, rand);
      break;
    case "resort":
      layoutData = layoutResort(count, dims, spec, rand, groupData);
      break;
    case "versus":
      layoutData = layoutVersus(count, dims, spec, rand, groupData);
      break;
    default:
      layoutData = layoutPile(count, dims, spec, rand);
  }

  const { restPositions, initialPositions, timing } = layoutData;
  const bounds = computeGroupBounds(restPositions, groupData.assignments);

  return {
    form: normForm,
    count,
    dimensions: dims,
    groups: groupData.groups,
    assignments: groupData.assignments,
    restPositions,
    initialPositions,
    timing,
    bounds
  };
}
