#!/usr/bin/env node
// Stills of the ink plate without a clip: one browser, many specs. A job list on stdin or in --jobs, one PNG per job.
//   node plates/ink/stills.mjs --jobs jobs.json --scale 0.5
//   jobs.json: [{"out": "a.png", "spec": {"material": "chalk", "drawing": "bus"}, "at": 2.0, "seconds": 4, "seed": 1}]
import fs from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const GL = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
  "--enable-webgl", "--force-color-profile=srgb", "--no-sandbox"];
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json" };

function chrome() {
  if (process.env.VEASY_CHROME) return process.env.VEASY_CHROME;
  const base = path.join(os.homedir(), ".cache", "puppeteer", "chrome-headless-shell");
  const name = process.platform === "win32" ? "chrome-headless-shell.exe" : "chrome-headless-shell";
  for (const version of fs.readdirSync(base).sort().reverse()) {
    for (const sub of fs.readdirSync(path.join(base, version))) if (fs.existsSync(path.join(base, version, sub, name))) return path.join(base, version, sub, name);
  }
  throw new Error("no chrome-headless-shell: set VEASY_CHROME");
}

const argv = process.argv.slice(2), opt = (name, fallback) => (argv.includes(`--${name}`) ? argv[argv.indexOf(`--${name}`) + 1] : fallback);
const jobs = JSON.parse(fs.readFileSync(opt("jobs"), "utf8"));
const scale = Number(opt("scale", 0.5));
const width = Math.round(1080 * scale), height = Math.round(1920 * scale);
const server = http.createServer((req, res) => {
  const file = path.normalize(path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return res.writeHead(404).end();
  res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const puppeteer = createRequire(path.join(ROOT, "package.json"))("puppeteer-core");
const browser = await puppeteer.launch({ executablePath: chrome(), headless: "shell", args: GL, defaultViewport: { width, height, deviceScaleFactor: 1 }, protocolTimeout: 600000 });
let failed = 0;
try {
  const page = await browser.newPage();
  page.on("pageerror", (e) => { console.error("page:", e.message); failed = 1; });
  await page.goto(`http://127.0.0.1:${server.address().port}/ink/index.html`, { waitUntil: "load" });
  await page.waitForFunction("window.setup && window.step", { timeout: 60000 });
  for (const job of jobs) {
    const started = Date.now();
    const c = { width, height, fps: 30, seed: job.seed ?? 1, seconds: job.seconds ?? 4 };
    await page.evaluate((s, x) => window.setup(s, x), { boil: 0, ...job.spec }, c);
    const mid = Date.now();
    await page.evaluate((t) => window.step(t), job.at ?? c.seconds * 0.5);
    fs.mkdirSync(path.dirname(job.out), { recursive: true });
    fs.writeFileSync(job.out, await page.screenshot({ type: "png" }));
    if (!argv.includes("--quiet")) console.log(path.basename(job.out), `setup ${mid - started} ms, still ${Date.now() - mid} ms`);
  }
} finally {
  await browser.close();
  server.close();
}
process.exit(failed);
