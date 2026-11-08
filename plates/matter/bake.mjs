#!/usr/bin/env node
// plates/matter/bake.mjs: verify the fact, solve once into cache/sim.bin, bake the clip through plates/run.mjs.
//   node plates/matter/bake.mjs --spec s.json --out out/plates/x [--seconds 6] [--seed 1] [--scale 1]
//   node plates/matter/bake.mjs --spec s.json --hash [--seconds 6] [--seed 1] [--scale 1]
// The proof goes into <out>/plate.json under "matter": count x unit = fact, and the sha256 of sim.bin. It prints the
// whole manifest (run.mjs's keys and "matter"). --hash prints the plate's hash without solving or baking: run.mjs's,
// on the spec as this bake resolves it (a fact ref read from its story), so the hash before a bake is the one after.
// `python -m tt_shorts.engine plate matter --spec s.json` calls this file (tt_shorts/plates.py entry()).
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { verifySpec } from "./verifier.mjs";
import { solveToBuffer } from "./solve.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, "..", "run.mjs");

function parse(argv) {
  const o = { seconds: 6, seed: 1, scale: 1, hash: argv.includes("--hash") };
  argv = argv.filter((x) => x !== "--hash");
  for (let i = 0; i < argv.length; i += 2) {
    const k = argv[i].replace(/^--/, "");
    if (argv[i + 1] === undefined) throw new Error(`option ${argv[i]} needs a value`);
    o[k] = ["spec", "out"].includes(k) ? argv[i + 1] : Number(argv[i + 1]);
  }
  if (!o.spec) throw new Error("matter needs --spec: the fact and the unit its blocks prove (plates/matter/README.md)");
  if (!o.out && !o.hash) throw new Error("usage: bake.mjs --spec s.json --out dir [--seconds n] [--seed n] [--scale n]");
  return o;
}

function resolved(o) { // the spec as the bake reads it: verified, its fact refs read from their stories
  const specFile = path.resolve(o.spec);
  return verifySpec(JSON.parse(fs.readFileSync(specFile, "utf8")), { cwd: path.dirname(specFile) });
}

export function hash(o) { // run.mjs's hash of the resolved spec: no solve, no browser
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "matter-hash-"));
  try {
    const runSpec = path.join(dir, "spec.resolved.json");
    fs.writeFileSync(runSpec, JSON.stringify(resolved(o)));
    const r = spawnSync(process.execPath, [RUN, "matter", "--spec", runSpec, "--seconds", o.seconds, "--seed", o.seed,
      "--scale", o.scale, "--hash"].map(String), { encoding: "utf8" });
    if (r.status !== 0) throw new Error(r.stderr || r.stdout);
    return r.stdout.trim();
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

export function bake(o) {
  const spec = resolved(o);
  if (["split", "resort"].includes(spec.form) && spec.groups.length < 2) {
    throw new Error(`form ${spec.form} needs 'groups': at least two shares whose facts add up to the fact`);
  }
  const groups = spec.groups.length ? spec.groups : [{ name: "total", count: spec.count }];
  const solved = solveToBuffer({ ...spec }, { seconds: o.seconds, seed: o.seed });
  const cache = path.join(HERE, "cache");
  fs.rmSync(cache, { recursive: true, force: true }); // only this bake's files stay (run.mjs's hash leaves cache/ out)
  fs.mkdirSync(cache, { recursive: true });
  fs.writeFileSync(path.join(cache, "sim.bin"), solved.buffer);
  fs.writeFileSync(path.join(cache, "meta.json"), JSON.stringify({
    form: spec.form, blockSize: spec.block_size, count: spec.count,
    groups: groups.map((g, i) => ({ id: g.name || `group_${i}`, count: g.count })),
  }));
  const out = path.resolve(o.out);
  fs.mkdirSync(out, { recursive: true });
  const runSpec = path.join(out, "spec.resolved.json");
  fs.writeFileSync(runSpec, JSON.stringify(spec));
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [RUN, "matter", "--spec", runSpec, "--seconds", o.seconds, "--seed", o.seed,
    "--scale", o.scale, "--out", out].map(String), { encoding: "utf8" });
  if (r.status !== 0) throw new Error(r.stderr || r.stdout);
  fs.copyFileSync(path.join(cache, "sim.bin"), path.join(out, "sim.bin"));
  const manifest = JSON.parse(fs.readFileSync(path.join(out, "plate.json"), "utf8"));
  manifest.matter = {
    form: spec.form, fact: spec.fact, unit: spec.unit, count: spec.count,
    proof: `${spec.count} x ${spec.unit} = ${spec.count * spec.unit}`,
    exact: spec.count * spec.unit === spec.fact,
    groups: groups.map((g) => ({ name: g.name, fact: g.fact, count: g.count })),
    sim_sha256: solved.sha256,
    mp4_sha256: createHash("sha256").update(fs.readFileSync(path.join(out, "plate.mp4"))).digest("hex"),
    solve_ms: Math.round(solved.timingMs), bake_wall_ms: Date.now() - t0,
  };
  fs.writeFileSync(path.join(out, "plate.json"), `${JSON.stringify(manifest, null, 1)}\n`);
  return manifest;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const o = parse(process.argv.slice(2));
    console.log(o.hash ? hash(o) : JSON.stringify(bake(o)));
  } catch (e) { console.error(e.message); process.exit(1); }
}
