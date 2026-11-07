#!/usr/bin/env node
// Bake one plate: a kind's page stepped frame by frame in headless Chrome on software GL, into a grey clip.
// The film never renders this: both engines play the clip as a local file. See README.md.
//
//   node plates/run.mjs <kind> --out out/plates/x [--spec spec.json] [--seconds 6] [--seed 1] [--scale 1]
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const WIDTH = 1080, HEIGHT = 1920, FPS = 30;
const GL = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
  "--enable-webgl", "--force-color-profile=srgb", "--font-render-hinting=none", "--no-sandbox"]; // as HyperFrames' --no-browser-gpu
// a kind's per-bake output, never part of what the plate is a function of: matter's cache/ is solved by its own bake.mjs
// from the spec and the seed, which the hash already covers (tt_shorts/plates.py GENERATED says the same)
const GENERATED = new Set(["cache"]);
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
  ".bin": "application/octet-stream", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml" };

function args(argv) {
  const [kind, ...more] = argv;
  const hashOnly = more.includes("--hash"); // print the content hash and exit: what `engine plate` asks before it bakes
  const rest = more.filter((x) => x !== "--hash");
  const out = { kind, seconds: 6, seed: 1, scale: 1, spec: null, out: hashOnly ? "-" : null, hashOnly };
  for (let i = 0; i < rest.length; i += 2) {
    const key = rest[i].replace(/^--/, "");
    if (!(key in out) || rest[i + 1] === undefined) throw new Error(`unknown or empty option ${rest[i]}`);
    out[key] = key === "spec" || key === "out" ? rest[i + 1] : Number(rest[i + 1]);
  }
  if (!kind || !out.out) throw new Error("usage: run.mjs <kind> --out <dir> [--spec f] [--seconds n] [--seed n] [--scale n]");
  if (!fs.existsSync(path.join(ROOT, kind, "index.html"))) throw new Error(`no plates/${kind}/index.html`);
  return out;
}

function chrome() {
  if (process.env.VEASY_CHROME) return process.env.VEASY_CHROME;
  const base = path.join(os.homedir(), ".cache", "puppeteer", "chrome-headless-shell");
  const name = process.platform === "win32" ? "chrome-headless-shell.exe" : "chrome-headless-shell";
  for (const version of fs.existsSync(base) ? fs.readdirSync(base).sort().reverse() : []) {
    for (const sub of fs.readdirSync(path.join(base, version))) {
      const exe = path.join(base, version, sub, name);
      if (fs.existsSync(exe)) return exe;
    }
  }
  throw new Error("no chrome-headless-shell in ~/.cache/puppeteer: set VEASY_CHROME");
}

function serve() { // plates/ on a local port: a kind may read its own files, nothing else
  const missing = []; // what a page asked for and did not get: named when the page then fails
  const server = http.createServer((req, res) => {
    const name = decodeURIComponent(new URL(req.url, "http://x").pathname);
    const file = path.normalize(path.join(ROOT, name));
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      if (!missing.includes(name)) missing.push(name);
      res.writeHead(404, { "content-type": "application/json" }).end(JSON.stringify({ missing: name }));
      return;
    }
    res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  });
  server.missing = missing;
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}

function encoder(file, scale) {
  const ffmpeg = process.env.VEASY_FFMPEG || "ffmpeg";
  // format=gray first: a plate is tone only, so no colour can reach a film whatever the page drew
  const vf = `${scale === 1 ? "" : `scale=${WIDTH}:${HEIGHT}:flags=lanczos,`}format=gray,format=yuv420p`;
  const child = spawn(ffmpeg, ["-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", String(FPS), "-i", "-",
    "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-g", "15", "-threads", "1", "-movflags", "+faststart", file],
  { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("close", (code) => (code ? reject(new Error(`ffmpeg exited ${code}`)) : resolve()));
  });
  return { child, done };
}

function hashOf(job, spec) { // what the plate is a function of: the kind's own files, the spec, the seed, the size
  const hash = createHash("sha256");
  const walk = (dir) => {
    for (const name of fs.readdirSync(dir).sort()) {
      const file = path.join(dir, name);
      if (fs.statSync(file).isDirectory()) {
        if (!(dir === kindDir && GENERATED.has(name))) walk(file);
      }
      else hash.update(name).update(fs.readFileSync(file));
    }
  };
  const kindDir = path.join(ROOT, job.kind);
  walk(kindDir);
  hash.update(JSON.stringify([spec ?? {}, job.seed, job.seconds, job.scale]));
  return hash.digest("hex").slice(0, 16);
}

async function bake(job) {
  // a kind with its own bake.mjs makes files its page reads (matter solves cache/sim.bin) and calls this runner itself
  if (fs.existsSync(path.join(ROOT, job.kind, "bake.mjs")) && !fs.existsSync(path.join(ROOT, job.kind, "cache"))) {
    throw new Error(`${job.kind} is baked by plates/${job.kind}/bake.mjs, which makes its cache/ first: ` +
      `run that, or python -m tt_shorts.engine plate ${job.kind} --spec <spec.json>`);
  }
  const puppeteer = createRequire(path.join(ROOT, "package.json"))("puppeteer-core");
  const spec = job.spec ? JSON.parse(fs.readFileSync(job.spec, "utf8")) : {};
  const width = Math.round(WIDTH * job.scale), height = Math.round(HEIGHT * job.scale);
  const frames = Math.round(job.seconds * FPS);
  fs.mkdirSync(job.out, { recursive: true });

  const server = await serve();
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await puppeteer.launch({ executablePath: chrome(), headless: "shell", args: GL,
    defaultViewport: { width, height, deviceScaleFactor: 1 }, protocolTimeout: 600000 });
  const offsite = [], errors = [];
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    await page.setRequestInterception(true);
    page.on("request", (r) => {
      const url = r.url();
      if (url.startsWith(origin) || url.startsWith("data:") || url.startsWith("blob:")) return r.continue();
      offsite.push(url);
      return r.abort();
    });
    await page.goto(`${origin}/${job.kind}/index.html`, { waitUntil: "load" });
    await page.waitForFunction("window.setup && window.step", { timeout: 60000 });
    try {
      await page.evaluate((s, c) => window.setup(s, c), spec, { width, height, fps: FPS, seed: job.seed, seconds: job.seconds });
    } catch (e) { // name a missing file rather than what the page said about the empty answer it got
      const lost = server.missing.length ? ` (the page asked for missing files: ${server.missing.join(", ")})` : "";
      throw new Error(`page setup failed: ${e.message}${lost}`);
    }

    const { child, done } = encoder(path.join(job.out, "plate.mp4"), job.scale);
    const tracks = {};
    const started = Date.now();
    let frameHash = null;
    for (let i = 0; i < frames; i++) {
      const t = i / FPS;
      await page.evaluate((x) => window.step(x), t);
      const found = await page.evaluate((x) => (window.anchors ? window.anchors(x) : null), t);
      for (const [name, at] of Object.entries(found || {})) (tracks[name] ||= []).push(at.map((v) => +(v / job.scale).toFixed(1)));
      if (!child.stdin.write(await page.screenshot({ type: "jpeg", quality: 95 }))) {
        await new Promise((resolve) => child.stdin.once("drain", resolve));
      }
      if (i === Math.floor(frames / 2)) {
        const png = await page.screenshot({ type: "png" });
        fs.writeFileSync(path.join(job.out, "poster.png"), png);
        frameHash = createHash("sha256").update(png).digest("hex").slice(0, 16);
      }
    }
    const perFrame = Math.round((Date.now() - started) / frames);
    child.stdin.end();
    await done;
    if (offsite.length) throw new Error(`a plate reads local files only, it asked for ${offsite[0]}`);
    if (errors.length) {
      const lost = server.missing.length ? ` (the page asked for missing files: ${server.missing.join(", ")})` : "";
      throw new Error(`page error: ${errors[0]}${lost}`);
    }

    if (Object.keys(tracks).length) {
      fs.writeFileSync(path.join(job.out, "anchors.json"), JSON.stringify({ fps: FPS, width: WIDTH, height: HEIGHT, tracks }));
    }
    const manifest = { kind: job.kind, hash: hashOf(job, spec), spec, seed: job.seed, seconds: job.seconds, scale: job.scale, fps: FPS,
      frames, frame_hash: frameHash, ms_per_frame: perFrame, anchors: Object.keys(tracks) };
    fs.writeFileSync(path.join(job.out, "plate.json"), `${JSON.stringify(manifest, null, 1)}\n`);
    return manifest;
  } finally {
    try {
      if (browser) {
        const proc = browser.process();
        await Promise.race([
          browser.close(),
          new Promise((r) => setTimeout(r, 1500)),
        ]);
        if (proc && !proc.killed) {
          try { proc.kill("SIGKILL"); } catch {}
        }
      }
    } catch {}
    try {
      if (server) {
        if (server.closeAllConnections) server.closeAllConnections();
        server.close();
      }
    } catch {}
  }
}

const job = args(process.argv.slice(2));
if (job.hashOnly) {
  const spec = job.spec ? JSON.parse(fs.readFileSync(job.spec, "utf8")) : {};
  console.log(hashOf(job, spec));
  process.exit(0);
}
bake(job).then((m) => {
  console.log(JSON.stringify(m));
  process.exit(0);
}, (e) => {
  console.error(e.message);
  process.exit(1);
});
