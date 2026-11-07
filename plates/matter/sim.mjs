// plates/matter/sim.mjs
// Deterministic Fixed-Step Rigid Body Simulation Engine for Veasy Plates (Matter)
// Uses seeded PRNG (mulberry32) exclusively: zero Math.random, zero Date.now/clock.

import { seeded } from "../lib/seeded.mjs";

export const FORMS = Object.freeze([
  "pile",
  "split",
  "too-tall",
  "pour",
  "resort",
  "versus"
]);

export const DEFAULT_BLOCK_SIZE = 0.42;
export const DEFAULT_FPS = 30;
export const DEFAULT_SUBSTEPS = 2; // 60 Hz internal physics rate at 30 fps
export const DEFAULT_GRAVITY = 9.81;

// 14 symmetric 3D neighbor offsets flattened into constant typed arrays for zero-allocation lookup
const OFF_X = new Int8Array([0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0]);
const OFF_Y = new Int8Array([0, -1, -1, -1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0]);
const OFF_Z = new Int8Array([0, -1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1, 1]);
const NUM_OFFSETS = 14;

/**
 * Normalizes a quaternion in-place.
 */
function normalizeQuat(q, offset) {
  const qx = q[offset];
  const qy = q[offset + 1];
  const qz = q[offset + 2];
  const qw = q[offset + 3];
  const lenSq = qx * qx + qy * qy + qz * qz + qw * qw;
  if (lenSq > 1e-12) {
    const invLen = 1 / Math.sqrt(lenSq);
    q[offset] = qx * invLen;
    q[offset + 1] = qy * invLen;
    q[offset + 2] = qz * invLen;
    q[offset + 3] = qw * invLen;
  } else {
    q[offset] = 0;
    q[offset + 1] = 0;
    q[offset + 2] = 0;
    q[offset + 3] = 1;
  }
}

/**
 * Smooth quintic easing curve (zero 1st and 2nd derivatives at endpoints).
 */
function smoothstep5(t) {
  const x = Math.max(0, Math.min(1, t));
  return x * x * x * (x * (x * 6 - 15) + 10);
}

/**
 * Rigid body simulation state and solver for discrete matter blocks.
 */
export class MatterSimulation {
  constructor(spec = {}, options = {}) {
    this.form = spec.form || "pile";
    if (!FORMS.includes(this.form)) {
      throw new Error(`Unknown form '${this.form}'. Must be one of: ${FORMS.join(", ")}`);
    }

    this.blockSize = Number(spec.block_size) || DEFAULT_BLOCK_SIZE;
    this.halfSize = this.blockSize * 0.5;
    this.fps = Number(options.fps || spec.fps) || DEFAULT_FPS;
    this.seconds = Number(options.seconds || spec.seconds) || 6;
    this.totalFrames = Math.max(1, Math.round(this.seconds * this.fps));
    this.substeps = Number(options.substeps) || DEFAULT_SUBSTEPS;
    this.dt = (1 / this.fps) / this.substeps;
    this.gravity = Number(options.gravity || spec.gravity) || DEFAULT_GRAVITY;
    this.seed = Number(options.seed ?? spec.seed ?? 1);

    this.rng = seeded(this.seed);

    // Resolve block count and groups
    this._resolveCountAndGroups(spec);

    // Physics state arrays (flat typed arrays for maximum cache locality and JIT performance)
    const n = this.count;
    this.px = new Float32Array(n);
    this.py = new Float32Array(n);
    this.pz = new Float32Array(n);

    this.vx = new Float32Array(n);
    this.vy = new Float32Array(n);
    this.vz = new Float32Array(n);

    // Quaternions (qx, qy, qz, qw)
    this.quat = new Float32Array(n * 4);

    // Angular velocities (wx, wy, wz)
    this.wx = new Float32Array(n);
    this.wy = new Float32Array(n);
    this.wz = new Float32Array(n);

    // Block metadata
    this.group = new Uint16Array(n);
    this.active = new Uint8Array(n);
    this.spawnTime = new Float32Array(n);

    // Spatial hash grid for O(N) broadphase collision checks
    this.gridTableSize = 8192;
    this.cellHead = new Int32Array(this.gridTableSize);
    this.nextBlock = new Int32Array(n);
    this.cellSize = this.blockSize * 1.5;

    // Pre-allocated frame buffer: [frames * count * 7] (x, y, z, qx, qy, qz, qw)
    this.outputFloatsPerBlock = 7;
    this.frameBuffer = new Float32Array(this.totalFrames * this.count * this.outputFloatsPerBlock);

    // Initialize initial condition based on form
    this._initFormState();
  }

  _resolveCountAndGroups(spec) {
    if (Array.isArray(spec.groups) && spec.groups.length > 0) {
      this.groups = spec.groups;
      this.groupCount = spec.groups.length;
      let total = 0;
      for (const g of spec.groups) {
        const c = Number(g.count ?? (spec.unit ? Math.round(g.fact / spec.unit) : g.fact));
        total += c;
      }
      this.count = total;
    } else {
      let c = Number(spec.count);
      if (!c && spec.fact && spec.unit) {
        c = Math.round(spec.fact / spec.unit);
      }
      this.count = c || 1000;
      this.groupCount = 1;
      this.groups = [{ name: "default", count: this.count }];
    }

    if (this.count < 1) this.count = 1;
    if (this.count > 3000) {
      throw new Error(`BlockCountExceededError: block count ${this.count} exceeds maximum capacity of 3000 blocks`);
    }
  }

  _initFormState() {
    const n = this.count;
    const rng = this.rng;

    // Assign groups to blocks
    let assigned = 0;
    for (let gIdx = 0; gIdx < this.groups.length; gIdx++) {
      const g = this.groups[gIdx];
      const gCount = Number(g.count ?? (this.specUnit ? Math.round(g.fact / this.specUnit) : Math.floor(n / this.groups.length)));
      const end = Math.min(n, assigned + gCount);
      for (let i = assigned; i < end; i++) {
        this.group[i] = gIdx;
      }
      assigned = end;
    }
    while (assigned < n) {
      this.group[assigned++] = this.groups.length - 1;
    }

    // Default orientations: identity quat (0, 0, 0, 1)
    for (let i = 0; i < n; i++) {
      const qOff = i * 4;
      this.quat[qOff] = 0;
      this.quat[qOff + 1] = 0;
      this.quat[qOff + 2] = 0;
      this.quat[qOff + 3] = 1;
      this.active[i] = 1;
      this.spawnTime[i] = 0;
    }

    switch (this.form) {
      case "pile":
        this._initPile();
        break;
      case "split":
        this._initSplit();
        break;
      case "too-tall":
        this._initTooTall();
        break;
      case "pour":
        this._initPour();
        break;
      case "resort":
        this._initResort();
        break;
      case "versus":
        this._initVersus();
        break;
    }
  }

  _initPile() {
    const n = this.count;
    const s = this.blockSize;
    const rng = this.rng;
    const spreadRadius = Math.max(0.9, 0.22 * Math.sqrt(n) * s);

    for (let i = 0; i < n; i++) {
      const r = spreadRadius * Math.sqrt(rng());
      const theta = rng() * Math.PI * 2;
      this.px[i] = r * Math.cos(theta);
      this.pz[i] = r * Math.sin(theta);
      this.py[i] = 1.2 + (i / n) * Math.max(3.8, 0.007 * n) + (rng() - 0.5) * 0.25;

      this.vx[i] = (rng() - 0.5) * 0.15;
      this.vz[i] = (rng() - 0.5) * 0.15;
      this.vy[i] = -0.4 - rng() * 0.8;

      // Small initial rotational tilt
      const rx = (rng() - 0.5) * 0.2;
      const ry = (rng() - 0.5) * 0.2;
      const rz = (rng() - 0.5) * 0.2;
      const qOff = i * 4;
      this.quat[qOff] = rx;
      this.quat[qOff + 1] = ry;
      this.quat[qOff + 2] = rz;
      this.quat[qOff + 3] = 1.0;
      normalizeQuat(this.quat, qOff);

      this.wx[i] = (rng() - 0.5) * 2.0;
      this.wy[i] = (rng() - 0.5) * 2.0;
      this.wz[i] = (rng() - 0.5) * 2.0;
    }
  }

  _initSplit() {
    // Structured pre-settled pile where Group 1 will smoothly translate out
    const n = this.count;
    const s = this.blockSize;
    const h = this.halfSize;
    const rng = this.rng;

    const baseW = Math.max(3, Math.ceil(Math.pow(n * 1.2, 1 / 3)));
    const baseD = baseW;
    let placed = 0;
    let layer = 0;

    this.splitOrigX = new Float32Array(n);
    this.splitOrigY = new Float32Array(n);
    this.splitOrigZ = new Float32Array(n);
    this.splitTargetX = new Float32Array(n);
    this.splitTargetY = new Float32Array(n);
    this.splitTargetZ = new Float32Array(n);
    this.splitLayer = new Uint16Array(n);

    const splitOffsetZ = Math.max(3.0, 1.8 + 0.16 * Math.sqrt(n) * s);

    while (placed < n) {
      const curW = Math.max(1, baseW - Math.floor(layer * 0.4));
      const curD = Math.max(1, baseD - Math.floor(layer * 0.4));
      for (let ix = 0; ix < curW && placed < n; ix++) {
        for (let iz = 0; iz < curD && placed < n; iz++) {
          const i = placed++;
          const staggerX = (rng() - 0.5) * 0.02 * s;
          const staggerZ = (rng() - 0.5) * 0.02 * s;
          const x = (ix - (curW - 1) * 0.5) * s + staggerX;
          const z = (iz - (curD - 1) * 0.5) * s + staggerZ;
          const y = h + layer * s;

          this.px[i] = x;
          this.py[i] = y;
          this.pz[i] = z;

          this.splitOrigX[i] = x;
          this.splitOrigY[i] = y;
          this.splitOrigZ[i] = z;

          this.splitTargetX[i] = x;
          this.splitTargetY[i] = y;
          this.splitTargetZ[i] = z + splitOffsetZ;
          this.splitLayer[i] = layer;
        }
      }
      layer++;
    }
    this.splitMaxLayer = layer;
  }

  _initTooTall() {
    // High monolithic vertical column with organic stagger
    const n = this.count;
    const s = this.blockSize;
    const h = this.halfSize;
    const rng = this.rng;

    let w = 2, d = 2;
    if (n <= 30) { w = 1; d = 1; }
    else if (n <= 250) { w = 2; d = 2; }
    else if (n <= 900) { w = 3; d = 3; }
    else { w = 4; d = 4; }

    const perLayer = w * d;
    this.tooTallBaseY = new Float32Array(n);
    this.tooTallLayer = new Uint16Array(n);

    for (let i = 0; i < n; i++) {
      const layer = Math.floor(i / perLayer);
      const sub = i % perLayer;
      const ix = sub % w;
      const iz = Math.floor(sub / w);

      const staggerX = (rng() - 0.5) * 0.03 * s;
      const staggerZ = (rng() - 0.5) * 0.03 * s;

      this.px[i] = (ix - (w - 1) * 0.5) * s + staggerX;
      this.pz[i] = (iz - (d - 1) * 0.5) * s + staggerZ;
      this.py[i] = h + layer * s;

      this.tooTallBaseY[i] = this.py[i];
      this.tooTallLayer[i] = layer;

      // Slight organic twist
      const rx = (rng() - 0.5) * 0.02;
      const ry = (rng() - 0.5) * 0.03;
      const rz = (rng() - 0.5) * 0.02;
      const qOff = i * 4;
      this.quat[qOff] = rx;
      this.quat[qOff + 1] = ry;
      this.quat[qOff + 2] = rz;
      this.quat[qOff + 3] = 1.0;
      normalizeQuat(this.quat, qOff);
    }
    this.tooTallMaxLayer = Math.ceil(n / perLayer);
  }

  _initPour() {
    const n = this.count;
    const rng = this.rng;

    // Sequential spawn times between 0.1s and 3.8s
    for (let i = 0; i < n; i++) {
      this.spawnTime[i] = 0.1 + 3.7 * (i / n) + (rng() - 0.5) * (0.5 / n);
      this.active[i] = 0;

      // Park at dispenser nozzle before spawn
      this.px[i] = (rng() - 0.5) * 0.15;
      this.py[i] = 6.2 + (rng() - 0.5) * 0.2;
      this.pz[i] = (rng() - 0.5) * 0.15;
    }
  }

  _initResort() {
    // Initial clusters -> Target sorted clusters along smooth collision-free paths
    const n = this.count;
    const s = this.blockSize;
    const h = this.halfSize;
    const rng = this.rng;
    const kGroups = Math.max(2, this.groupCount);

    this.resortOrigX = new Float32Array(n);
    this.resortOrigY = new Float32Array(n);
    this.resortOrigZ = new Float32Array(n);
    this.resortTargetX = new Float32Array(n);
    this.resortTargetY = new Float32Array(n);
    this.resortTargetZ = new Float32Array(n);
    this.resortLayer = new Uint16Array(n);

    const baseW = Math.max(3, Math.ceil(Math.pow(n * 1.1, 1 / 3)));
    let placed = 0;
    let layer = 0;
    while (placed < n) {
      const curW = Math.max(1, baseW - Math.floor(layer * 0.4));
      for (let ix = 0; ix < curW && placed < n; ix++) {
        for (let iz = 0; iz < curW && placed < n; iz++) {
          const i = placed++;
          const staggerX = (rng() - 0.5) * 0.02 * s;
          const staggerZ = (rng() - 0.5) * 0.02 * s;
          const x = (ix - (curW - 1) * 0.5) * s + staggerX;
          const z = (iz - (curW - 1) * 0.5) * s + staggerZ;
          const y = h + layer * s;

          this.px[i] = x;
          this.py[i] = y;
          this.pz[i] = z;

          this.resortOrigX[i] = x;
          this.resortOrigY[i] = y;
          this.resortOrigZ[i] = z;
          this.resortLayer[i] = layer;
        }
      }
      layer++;
    }
    this.resortMaxLayer = layer;

    // Target positions: K separate piles arranged along X axis
    const groupPlaced = new Uint32Array(kGroups);
    const groupCounts = new Uint32Array(kGroups);
    for (let i = 0; i < n; i++) groupCounts[this.group[i]]++;

    const sepX = Math.max(2.5, 1.4 + 0.18 * Math.sqrt(n) * s);
    for (let i = 0; i < n; i++) {
      const g = this.group[i];
      const gIdx = groupPlaced[g]++;
      const gTotal = groupCounts[g];
      const gBaseW = Math.max(2, Math.ceil(Math.pow(gTotal, 1 / 3)));
      const gLayer = Math.floor(gIdx / (gBaseW * gBaseW));
      const gSub = gIdx % (gBaseW * gBaseW);
      const gix = gSub % gBaseW;
      const giz = Math.floor(gSub / gBaseW);

      const centerX = (g - (kGroups - 1) * 0.5) * sepX;
      this.resortTargetX[i] = centerX + (gix - (gBaseW - 1) * 0.5) * s;
      this.resortTargetZ[i] = (giz - (gBaseW - 1) * 0.5) * s;
      this.resortTargetY[i] = h + gLayer * s;
    }
  }

  _initVersus() {
    // Two distinct heaps side by side
    const n = this.count;
    const s = this.blockSize;
    const rng = this.rng;

    const sepX = Math.max(2.4, 1.3 + 0.18 * Math.sqrt(n) * s);
    const n0 = Math.floor(n * 0.5);

    for (let i = 0; i < n; i++) {
      const isGroup1 = (i >= n0) || (this.group[i] === 1);
      const side = isGroup1 ? 1 : -1;
      const groupCount = isGroup1 ? (n - n0) : n0;
      const idxInGroup = isGroup1 ? (i - n0) : i;

      const r = Math.max(0.6, 0.2 * Math.sqrt(groupCount) * s) * Math.sqrt(rng());
      const theta = rng() * Math.PI * 2;

      this.px[i] = side * sepX + r * Math.cos(theta);
      this.pz[i] = r * Math.sin(theta);
      this.py[i] = 1.2 + (idxInGroup / groupCount) * Math.max(3.2, 0.006 * groupCount) + (rng() - 0.5) * 0.2;

      this.vx[i] = (rng() - 0.5) * 0.15;
      this.vz[i] = (rng() - 0.5) * 0.15;
      this.vy[i] = -0.4 - rng() * 0.8;

      const rx = (rng() - 0.5) * 0.2;
      const ry = (rng() - 0.5) * 0.2;
      const rz = (rng() - 0.5) * 0.2;
      const qOff = i * 4;
      this.quat[qOff] = rx;
      this.quat[qOff + 1] = ry;
      this.quat[qOff + 2] = rz;
      this.quat[qOff + 3] = 1.0;
      normalizeQuat(this.quat, qOff);

      this.wx[i] = (rng() - 0.5) * 2.0;
      this.wy[i] = (rng() - 0.5) * 2.0;
      this.wz[i] = (rng() - 0.5) * 2.0;
    }
  }

  /**
   * Run the complete simulation, filling this.frameBuffer.
   */
  run() {
    const totalFrames = this.totalFrames;
    const substeps = this.substeps;
    let simTime = 0;

    // Record initial frame 0
    this._recordFrame(0);

    for (let f = 1; f < totalFrames; f++) {
      for (let s = 0; s < substeps; s++) {
        this.step(simTime);
        simTime += this.dt;
      }
      this._recordFrame(f);
    }

    return this.frameBuffer;
  }

  /**
   * Advances the simulation by 1 physics sub-step (dt).
   */
  step(simTime) {
    const form = this.form;
    if (form === "split") {
      this._stepSplit(simTime);
      return;
    }
    if (form === "too-tall") {
      this._stepTooTall(simTime);
      return;
    }
    if (form === "resort") {
      this._stepResort(simTime);
      return;
    }

    // Dynamic forms: pile, pour, versus
    if (form === "pour") {
      this._activatePourSpawns(simTime);
    }

    this._stepRigidBodyDynamics(simTime);
  }

  _activatePourSpawns(simTime) {
    const n = this.count;
    const rng = this.rng;
    for (let i = 0; i < n; i++) {
      if (!this.active[i] && simTime >= this.spawnTime[i]) {
        this.active[i] = 1;
        this.px[i] = (rng() - 0.5) * 0.25;
        this.py[i] = 5.6;
        this.pz[i] = (rng() - 0.5) * 0.25;
        this.vy[i] = -3.0 - rng() * 1.2;
        this.vx[i] = (rng() - 0.5) * 0.4;
        this.vz[i] = (rng() - 0.5) * 0.4;
        this.wx[i] = (rng() - 0.5) * 3.0;
        this.wy[i] = (rng() - 0.5) * 3.0;
        this.wz[i] = (rng() - 0.5) * 3.0;
      }
    }
  }

  _stepSplit(simTime) {
    const n = this.count;
    const tStart = 1.2;
    const tEnd = 4.2;
    const duration = tEnd - tStart;
    const maxLayer = Math.max(1, this.splitMaxLayer);

    // Group 0 stays stationary at initial resting position
    // Group 1 translates smoothly along +Z offset axis
    for (let i = 0; i < n; i++) {
      if (this.group[i] === 0) {
        // Stationary share
        this.px[i] = this.splitOrigX[i];
        this.py[i] = this.splitOrigY[i];
        this.pz[i] = this.splitOrigZ[i];
        continue;
      }

      // Active share: staggered translation
      const layerFrac = this.splitLayer[i] / maxLayer;
      const itemStart = tStart + 0.5 * layerFrac;
      const itemDur = duration - 0.5;
      const progress = Math.max(0, Math.min(1, (simTime - itemStart) / itemDur));
      const u = smoothstep5(progress);

      const liftHeight = (0.5 + 0.08 * this.splitLayer[i]) * 4.0 * progress * (1 - progress);

      this.px[i] = this.splitOrigX[i] + u * (this.splitTargetX[i] - this.splitOrigX[i]);
      this.pz[i] = this.splitOrigZ[i] + u * (this.splitTargetZ[i] - this.splitOrigZ[i]);
      this.py[i] = this.splitOrigY[i] + liftHeight;

      // Subtle organic tilt during flight, settling flat
      const qOff = i * 4;
      const tilt = Math.sin(progress * Math.PI) * 0.06;
      this.quat[qOff] = tilt;
      this.quat[qOff + 1] = 0;
      this.quat[qOff + 2] = 0;
      this.quat[qOff + 3] = Math.sqrt(Math.max(0, 1 - tilt * tilt));
    }
  }

  _stepTooTall(simTime) {
    // Monolithic vertical column standing solidly with subtle settling compression wave
    const n = this.count;
    const maxLayer = Math.max(1, this.tooTallMaxLayer);
    const settleDuration = 0.8;

    let compression = 0;
    if (simTime < settleDuration) {
      const p = simTime / settleDuration;
      compression = Math.sin(p * Math.PI) * Math.exp(-3.5 * p) * 0.015;
    }

    for (let i = 0; i < n; i++) {
      const layer = this.tooTallLayer[i];
      const layerRatio = layer / maxLayer;
      this.py[i] = this.tooTallBaseY[i] - compression * layerRatio;
    }
  }

  _stepResort(simTime) {
    const n = this.count;
    const tStart = 1.0;
    const tEnd = 4.2;
    const duration = tEnd - tStart;
    const maxLayer = Math.max(1, this.resortMaxLayer);

    for (let i = 0; i < n; i++) {
      const g = this.group[i];
      const layerFrac = this.resortLayer[i] / maxLayer;
      const itemStart = tStart + 0.4 * g + 0.3 * layerFrac;
      const itemDur = duration - 0.7;
      const progress = Math.max(0, Math.min(1, (simTime - itemStart) / itemDur));
      const u = smoothstep5(progress);

      const arcH = (1.2 + 0.35 * g + 0.06 * layerFrac) * 4.0 * progress * (1 - progress);

      this.px[i] = this.resortOrigX[i] + u * (this.resortTargetX[i] - this.resortOrigX[i]);
      this.pz[i] = this.resortOrigZ[i] + u * (this.resortTargetZ[i] - this.resortOrigZ[i]);
      this.py[i] = this.resortOrigY[i] + u * (this.resortTargetY[i] - this.resortOrigY[i]) + arcH;

      const qOff = i * 4;
      const tilt = Math.sin(progress * Math.PI) * 0.08;
      this.quat[qOff] = tilt;
      this.quat[qOff + 1] = tilt * 0.5;
      this.quat[qOff + 2] = 0;
      this.quat[qOff + 3] = Math.sqrt(Math.max(0, 1 - 1.25 * tilt * tilt));
      normalizeQuat(this.quat, qOff);
    }
  }

  _stepRigidBodyDynamics(simTime) {
    const n = this.count;
    const dt = this.dt;
    const s = this.blockSize;
    const h = this.halfSize;
    const gravity = this.gravity;
    const restitution = 0.18;
    const groundFriction = 0.82;
    const kineticDamping = Math.max(0.92, 1.0 - 0.06 * (simTime / this.seconds));

    // 1. Broadphase: Re-populate spatial hash grid
    const grid = this.cellHead;
    const next = this.nextBlock;
    const mask = this.gridTableSize - 1;
    const cSize = this.cellSize;
    grid.fill(-1);

    for (let i = 0; i < n; i++) {
      if (!this.active[i]) continue;
      const cx = Math.floor(this.px[i] / cSize);
      const cy = Math.floor(this.py[i] / cSize);
      const cz = Math.floor(this.pz[i] / cSize);
      const hash = ((cx * 73856093) ^ (cy * 19349663) ^ (cz * 83492791)) & mask;
      next[i] = grid[hash];
      grid[hash] = i;
    }

    // 2. Narrowphase & Inter-block collision
    const sSq = s * s;

    for (let i = 0; i < n; i++) {
      if (!this.active[i]) continue;
      const pxi = this.px[i];
      const pyi = this.py[i];
      const pzi = this.pz[i];

      const cx = Math.floor(pxi / cSize);
      const cy = Math.floor(pyi / cSize);
      const cz = Math.floor(pzi / cSize);

      for (let o = 0; o < NUM_OFFSETS; o++) {
        const ox = OFF_X[o];
        const oy = OFF_Y[o];
        const oz = OFF_Z[o];
        const nhash = (((cx + ox) * 73856093) ^ ((cy + oy) * 19349663) ^ ((cz + oz) * 83492791)) & mask;
        let j = grid[nhash];

        while (j !== -1) {
          if (o === 0 ? j > i : true) {
            const delx = this.px[j] - pxi;
            const dely = this.py[j] - pyi;
            const delz = this.pz[j] - pzi;
            const distSq = delx * delx + dely * dely + delz * delz;

            if (distSq < sSq && distSq > 1e-10) {
              const dist = Math.sqrt(distSq);
              const overlap = s - dist;
              const nx = delx / dist;
              const ny = dely / dist;
              const nz = delz / dist;

              // Position projection
              const halfSep = overlap * 0.5;
              this.px[i] -= halfSep * nx;
              this.py[i] -= halfSep * ny;
              this.pz[i] -= halfSep * nz;
              this.px[j] += halfSep * nx;
              this.py[j] += halfSep * ny;
              this.pz[j] += halfSep * nz;

              // Velocity impulse
              const dvx = this.vx[j] - this.vx[i];
              const dvy = this.vy[j] - this.vy[i];
              const dvz = this.vz[j] - this.vz[i];
              const vn = dvx * nx + dvy * ny + dvz * nz;

              if (vn < 0) {
                const impulse = -(1 + restitution) * vn * 0.5;
                this.vx[i] -= impulse * nx;
                this.vy[i] -= impulse * ny;
                this.vz[i] -= impulse * nz;
                this.vx[j] += impulse * nx;
                this.vy[j] += impulse * ny;
                this.vz[j] += impulse * nz;

                // Tangential friction damping
                const tx = dvx - vn * nx;
                const ty = dvy - vn * ny;
                const tz = dvz - vn * nz;
                const tLen = Math.hypot(tx, ty, tz);
                if (tLen > 1e-5) {
                  const fShear = Math.min(0.3 * impulse, 0.4 * tLen) / tLen;
                  this.vx[i] += fShear * tx;
                  this.vy[i] += fShear * ty;
                  this.vz[i] += fShear * tz;
                  this.vx[j] -= fShear * tx;
                  this.vy[j] -= fShear * ty;
                  this.vz[j] -= fShear * tz;
                }
              }
            }
          }
          j = next[j];
        }
      }
    }

    // 3. Integration & Ground Collision (y >= 0)
    for (let i = 0; i < n; i++) {
      if (!this.active[i]) continue;

      // Integrate linear velocity
      this.vy[i] -= gravity * dt;
      this.px[i] += this.vx[i] * dt;
      this.py[i] += this.vy[i] * dt;
      this.pz[i] += this.vz[i] * dt;

      // Integrate orientation quaternion with angular velocity
      const wx = this.wx[i];
      const wy = this.wy[i];
      const wz = this.wz[i];
      const wlen = Math.hypot(wx, wy, wz);
      const qOff = i * 4;

      if (wlen > 1e-8) {
        const theta = wlen * dt;
        const sinHalf = Math.sin(theta * 0.5) / wlen;
        const dqw = Math.cos(theta * 0.5);
        const dqx = wx * sinHalf;
        const dqy = wy * sinHalf;
        const dqz = wz * sinHalf;

        const qw = this.quat[qOff + 3];
        const qx = this.quat[qOff];
        const qy = this.quat[qOff + 1];
        const qz = this.quat[qOff + 2];

        this.quat[qOff + 3] = dqw * qw - dqx * qx - dqy * qy - dqz * qz;
        this.quat[qOff] = dqw * qx + dqx * qw + dqy * qz - dqz * qy;
        this.quat[qOff + 1] = dqw * qy - dqx * qz + dqy * qw + dqz * qx;
        this.quat[qOff + 2] = dqw * qz + dqx * qy - dqy * qx + dqz * qw;
        normalizeQuat(this.quat, qOff);
      }

      // Ground plane collision (y >= 0)
      const qx = this.quat[qOff];
      const qy = this.quat[qOff + 1];
      const qz = this.quat[qOff + 2];
      const qw = this.quat[qOff + 3];

      // Matrix elements for face orientation & effective half height
      const R10 = 2 * (qx * qy + qz * qw);
      const R11 = 1 - 2 * (qx * qx + qz * qz);
      const R12 = 2 * (qy * qz - qx * qw);
      const hEff = h * (Math.abs(R10) + Math.abs(R11) + Math.abs(R12));

      if (this.py[i] - hEff < 0) {
        this.py[i] = hEff;
        if (this.vy[i] < 0) {
          this.vy[i] = -restitution * this.vy[i];
          if (Math.abs(this.vy[i]) < 0.08) this.vy[i] = 0;
        }
        this.vx[i] *= groundFriction;
        this.vz[i] *= groundFriction;

        // Ground face-alignment torque to settle flat
        const R00 = 1 - 2 * (qy * qy + qz * qz);
        const R20 = 2 * (qx * qz - qy * qw);
        const R01 = 2 * (qx * qy - qz * qw);
        const R21 = 2 * (qy * qz + qx * qw);
        const R02 = 2 * (qx * qz + qy * qw);
        const R22 = 1 - 2 * (qx * qx + qy * qy);

        let ax = 0, az = 0;
        const a0 = Math.abs(R10), a1 = Math.abs(R11), a2 = Math.abs(R12);
        if (a0 >= a1 && a0 >= a2) {
          const sgn = -Math.sign(R10 || 1);
          ax = sgn * R00; az = sgn * R20;
        } else if (a1 >= a0 && a1 >= a2) {
          const sgn = -Math.sign(R11 || 1);
          ax = sgn * R01; az = sgn * R21;
        } else {
          const sgn = -Math.sign(R12 || 1);
          ax = sgn * R02; az = sgn * R22;
        }
        // Restoring torque = faceNormal x (0, -1, 0) = (-az, 0, ax)
        this.wx[i] += (-az) * 12.0 * dt;
        this.wz[i] += (ax) * 12.0 * dt;
        this.wx[i] *= 0.88;
        this.wy[i] *= 0.88;
        this.wz[i] *= 0.88;
      }

      // Kinetic damping to settle into resting mounds
      this.vx[i] *= kineticDamping;
      this.vy[i] *= kineticDamping;
      this.vz[i] *= kineticDamping;
      this.wx[i] *= kineticDamping;
      this.wy[i] *= kineticDamping;
      this.wz[i] *= kineticDamping;
    }
  }

  _recordFrame(frameIndex) {
    const n = this.count;
    const baseOffset = frameIndex * n * this.outputFloatsPerBlock;
    const buf = this.frameBuffer;

    for (let i = 0; i < n; i++) {
      const bOff = baseOffset + i * 7;
      buf[bOff] = this.px[i];
      buf[bOff + 1] = this.py[i];
      buf[bOff + 2] = this.pz[i];

      const qOff = i * 4;
      buf[bOff + 3] = this.quat[qOff];
      buf[bOff + 4] = this.quat[qOff + 1];
      buf[bOff + 5] = this.quat[qOff + 2];
      buf[bOff + 6] = this.quat[qOff + 3];
    }
  }
}

/**
 * Top-level simulate function.
 * @param {Object} spec - Spec containing form, fact/unit or count, groups, block_size.
 * @param {Object} options - Options including seconds, seed, fps, substeps.
 * @returns {Object} Simulation result with metadata and frame data.
 */
export function simulate(spec = {}, options = {}) {
  const sim = new MatterSimulation(spec, options);
  const frameBuffer = sim.run();
  return {
    frameBuffer,
    frames: sim.totalFrames,
    count: sim.count,
    groupCount: sim.groupCount,
    fps: sim.fps,
    seconds: sim.seconds,
    form: sim.form,
    blockSize: sim.blockSize,
    seed: sim.seed
  };
}
