#!/usr/bin/env node
// plates/matter/solve.mjs
// CLI & Module Runner: Deterministic Fixed-Step Solver for Veasy Plates (Matter)
// Produces byte-for-byte deterministic .bin buffers (VMTR format).

import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { simulate, FORMS, DEFAULT_BLOCK_SIZE, DEFAULT_FPS } from "./sim.mjs";

export { FORMS, DEFAULT_BLOCK_SIZE, DEFAULT_FPS };

const HEADER_SIZE = 32;
const FLOATS_PER_BLOCK = 7; // x, y, z, qx, qy, qz, qw
const BYTES_PER_BLOCK_FRAME = FLOATS_PER_BLOCK * 4; // 28 bytes

const FORBIDDEN_CATEGORIES = new Set(["news", "crime", "incident", "death", "tragedy"]);

/**
 * Resolves a fact value if it is a number or a { ref, key } story fact reference.
 */
function resolveFactValue(fact) {
  if (typeof fact === "number") return fact;
  if (typeof fact === "string") {
    const num = Number(fact);
    if (!Number.isNaN(num)) return num;
  }
  if (typeof fact === "object" && fact !== null) {
    if (typeof fact.value === "number") return fact.value;
    if (fact.ref) {
      const candidates = [
        fact.ref,
        path.resolve(process.cwd(), fact.ref),
        path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../", fact.ref)
      ];
      let foundPath = null;
      for (const c of candidates) {
        if (fs.existsSync(c)) { foundPath = c; break; }
      }
      if (foundPath) {
        const data = JSON.parse(fs.readFileSync(foundPath, "utf8"));
        if (fact.key) {
          const m = fact.key.match(/scene-(\d+)-value/);
          if (m && data.scenes && data.scenes[Number(m[1])]) {
            return Number(data.scenes[Number(m[1])].value);
          }
          if (data[fact.key] !== undefined) return Number(data[fact.key]);
        }
      }
    }
  }
  return Number(fact);
}

/**
 * Validates spec and extracts fact / unit / group constraints.
 */
export function validateSpec(spec = {}) {
  const normalized = { ...spec };

  if (spec.category && FORBIDDEN_CATEGORIES.has(String(spec.category).toLowerCase())) {
    throw new Error(`ForbiddenCategoryError: plates are strictly prohibited for category '${spec.category}'`);
  }

  if (spec.fact !== undefined && spec.unit !== undefined) {
    const fact = resolveFactValue(spec.fact);
    const unit = Number(spec.unit);

    if (Number.isNaN(fact) || fact <= 0) {
      throw new Error(`InvalidFactError: fact must be a positive number, got ${spec.fact}`);
    }

    if (Number.isNaN(unit) || unit <= 0) {
      throw new Error(`UnitMismatchError: unit must be positive, got ${spec.unit}`);
    }

    const remainder = fact % unit;
    if (remainder !== 0) {
      throw new Error(`UnitMismatchError: unit ${unit} does not divide fact ${fact} exactly (remainder ${remainder})`);
    }

    const count = Math.round(fact / unit);
    if (count > 3000) {
      throw new Error(`BlockCountExceededError: block count ${count} exceeds maximum capacity of 3000 blocks; choose a larger unit`);
    }

    normalized.fact = fact;
    normalized.unit = unit;
    normalized.count = count;

    // Validate groups if provided
    if (Array.isArray(spec.groups) && spec.groups.length > 0) {
      let groupSum = 0;
      for (const g of spec.groups) {
        if (g.fact !== undefined) {
          const gFact = resolveFactValue(g.fact);
          const gRem = gFact % unit;
          if (gRem !== 0) {
            throw new Error(`UnitMismatchError: unit ${unit} does not divide group '${g.name || "unnamed"}' fact ${gFact} exactly (remainder ${gRem})`);
          }
          groupSum += gFact;
        } else if (g.count !== undefined) {
          groupSum += Number(g.count) * unit;
        }
      }
      if (groupSum !== fact) {
        throw new Error(`GroupSumMismatchError: sum of group facts (${groupSum}) does not equal total fact (${fact})`);
      }
    }
  }

  return normalized;
}

/**
 * Solves a matter simulation and serializes it to a VMTR binary buffer.
 *
 * @param {Object|string} specOrPath - Spec object or path to JSON spec file.
 * @param {Object} options - Simulation options (seconds, seed, fps, substeps, out).
 * @returns {Object} { buffer, arrayBuffer, sha256, metadata, timingMs }
 */
export function solveToBuffer(specOrPath = {}, options = {}) {
  const t0 = performance.now();

  let spec = {};
  if (typeof specOrPath === "string") {
    if (fs.existsSync(specOrPath)) {
      spec = JSON.parse(fs.readFileSync(specOrPath, "utf8"));
    } else {
      throw new Error(`Spec file not found: ${specOrPath}`);
    }
  } else if (typeof specOrPath === "object" && specOrPath !== null) {
    spec = { ...specOrPath };
  }

  // Override options into spec if provided
  if (options.form) spec.form = options.form;
  if (options.count) spec.count = Number(options.count);
  if (options.block_size) spec.block_size = Number(options.block_size);
  if (options.seconds) spec.seconds = Number(options.seconds);
  if (options.seed !== undefined) spec.seed = Number(options.seed);

  // Validate spec rules (divisibility, count cap <= 3000, category safety)
  spec = validateSpec(spec);

  const seconds = Number(options.seconds ?? spec.seconds ?? 6);
  const seed = Number(options.seed ?? spec.seed ?? 1);
  const fps = Number(options.fps ?? spec.fps ?? DEFAULT_FPS);

  const simResult = simulate(spec, { seconds, seed, fps, substeps: options.substeps });

  const frames = simResult.frames;
  const count = simResult.count;
  const groupCount = simResult.groupCount;
  const totalFrameBytes = frames * count * BYTES_PER_BLOCK_FRAME;
  const totalBytes = HEADER_SIZE + totalFrameBytes;

  const arrayBuffer = new ArrayBuffer(totalBytes);
  const dataView = new DataView(arrayBuffer);

  // 1. Header (32 bytes)
  // Magic: "VMTR" (0x56, 0x4D, 0x54, 0x52)
  dataView.setUint8(0, 0x56);
  dataView.setUint8(1, 0x4D);
  dataView.setUint8(2, 0x54);
  dataView.setUint8(3, 0x52);

  // Version: 1 (uint16)
  dataView.setUint16(4, 1, true);

  // FPS: uint16
  dataView.setUint16(6, fps, true);

  // Frames: uint32
  dataView.setUint32(8, frames, true);

  // Count: uint32
  dataView.setUint32(12, count, true);

  // Groups: uint32
  dataView.setUint32(16, groupCount, true);

  // Reserved: 12 bytes padding (offsets 20 .. 31)
  for (let b = 20; b < 32; b++) {
    dataView.setUint8(b, 0);
  }

  // 2. Body: frame data
  const floatView = new Float32Array(arrayBuffer, HEADER_SIZE, frames * count * FLOATS_PER_BLOCK);
  floatView.set(simResult.frameBuffer);

  const buffer = Buffer.from(arrayBuffer);
  const sha256 = createHash("sha256").update(buffer).digest("hex");
  const timingMs = performance.now() - t0;

  const metadata = {
    magic: "VMTR",
    version: 1,
    fps,
    frames,
    count,
    groupCount,
    form: simResult.form,
    seconds,
    seed,
    blockSize: simResult.blockSize,
    totalBytes,
    sha256,
    timingMs
  };

  // Optional write to disk
  const outFile = options.out || spec.out;
  if (outFile) {
    fs.mkdirSync(path.dirname(outFile), { recursive: true });
    fs.writeFileSync(outFile, buffer);
  }

  return {
    buffer,
    arrayBuffer,
    sha256,
    metadata,
    timingMs
  };
}

/**
 * Helper to solve and write directly to an output file path.
 */
export function solveToFile(specOrPath, outPath, options = {}) {
  return solveToBuffer(specOrPath, { ...options, out: outPath });
}

/**
 * Parse CLI arguments.
 */
export function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const val = argv[i + 1];
      if (val !== undefined && !val.startsWith("--")) {
        args[key] = val;
        i++;
      } else {
        args[key] = true;
      }
    }
  }
  return args;
}

// CLI Execution entry point
const isDirectCli = process.argv[1] && (
  path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))
);

if (isDirectCli) {
  const cliArgs = parseArgs(process.argv.slice(2));

  if (cliArgs.help || (!cliArgs.spec && !cliArgs.count && !cliArgs.form)) {
    console.log(`
Veasy Plates (Matter): Deterministic Fixed-Step Solver
Usage:
  node plates/matter/solve.mjs [options]

Options:
  --spec <file>       JSON spec file path (e.g. spec.json)
  --out <file>        Output .bin file path (e.g. plates/matter/cache/sim.bin)
  --seconds <n>       Simulation duration in seconds (default: 6)
  --seed <n>          mulberry32 PRNG seed (default: 1)
  --fps <n>           Frame rate (default: 30)
  --form <name>       Form: pile, split, too-tall, pour, resort, versus (default: pile)
  --count <n>         Discrete block count (default: 1000)
  --block_size <n>    Block size in 3D units (default: 0.42)
  --help              Show this help message
`);
    process.exit(0);
  }

  try {
    const res = solveToBuffer(cliArgs.spec || {}, {
      out: cliArgs.out,
      seconds: cliArgs.seconds ? Number(cliArgs.seconds) : undefined,
      seed: cliArgs.seed !== undefined ? Number(cliArgs.seed) : undefined,
      fps: cliArgs.fps ? Number(cliArgs.fps) : undefined,
      form: cliArgs.form,
      count: cliArgs.count ? Number(cliArgs.count) : undefined,
      block_size: cliArgs.block_size ? Number(cliArgs.block_size) : undefined
    });

    const mb = (res.metadata.totalBytes / (1024 * 1024)).toFixed(2);
    console.log(`[solve.mjs] OK: form=${res.metadata.form} count=${res.metadata.count} frames=${res.metadata.frames} (${res.metadata.seconds}s @ ${res.metadata.fps}fps)`);
    console.log(`[solve.mjs] size=${mb} MB sha256=${res.sha256} elapsed=${res.timingMs.toFixed(1)}ms`);
    if (cliArgs.out) {
      console.log(`[solve.mjs] wrote ${cliArgs.out}`);
    }
  } catch (err) {
    console.error(`[solve.mjs] Error: ${err.message}`);
    process.exit(1);
  }
}
