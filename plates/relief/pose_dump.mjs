#!/usr/bin/env node
// Camera poses and anchor pixels of every relief spec at a few frames, without rendering (tests/test_relief.py checks
// them against an independent projection of the gazetteer's lat/lon). Needs plates/ `npm ci`. Output: JSON on stdout.
//   node plates/relief/pose_dump.mjs [spec.json ...]   (default: every file in plates/relief/specs)
import fs from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const FRAMES = [0, 45, 90, 135, 179];
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
  ".bin": "application/octet-stream", ".png": "image/png" };

const specs = process.argv.length > 2 ? process.argv.slice(2)
  : fs.readdirSync(path.join(HERE, "specs")).filter((f) => f.endsWith(".json")).map((f) => path.join(HERE, "specs", f));
const server = http.createServer((req, res) => {
  const file = path.join(ROOT, decodeURIComponent(req.url.split("?")[0]).replace(/^\/relief\/data\//, "/relief/data/"));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const origin = `http://127.0.0.1:${server.address().port}`;
const puppeteer = createRequire(path.join(ROOT, "package.json"))("puppeteer-core");
function chrome() { // as plates/run.mjs
  if (process.env.VEASY_CHROME) return process.env.VEASY_CHROME;
  const base = path.join(os.homedir(), ".cache", "puppeteer", "chrome-headless-shell");
  const name = process.platform === "win32" ? "chrome-headless-shell.exe" : "chrome-headless-shell";
  for (const v of fs.existsSync(base) ? fs.readdirSync(base).sort().reverse() : [])
    for (const sub of fs.readdirSync(path.join(base, v))) { const e = path.join(base, v, sub, name); if (fs.existsSync(e)) return e; }
  throw new Error("no chrome-headless-shell: set VEASY_CHROME");
}
const exe = chrome();
const GL = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl", "--no-sandbox"];
const browser = await puppeteer.launch({ executablePath: exe, headless: "shell", args: GL, defaultViewport: { width: 1080, height: 1920 } });
const out = {};
try {
  for (const f of specs) {
    const page = await browser.newPage();
    await page.goto(`${origin}/relief/index.html`, { waitUntil: "load" });
    await page.waitForFunction("window.setup && window.step", { timeout: 60000 });
    await page.evaluate((s, c) => window.setup(s, c), JSON.parse(fs.readFileSync(f, "utf8")),
      { width: 1080, height: 1920, fps: 30, seed: 1, seconds: 6 });
    const rows = [];
    for (const i of FRAMES) rows.push({ frame: i, pose: await page.evaluate((t) => window.pose(t), i / 30), anchors: await page.evaluate((t) => window.anchors(t), i / 30) });
    out[path.basename(f, ".json")] = rows;
    await page.close();
  }
} finally { await browser.close(); server.close(); }
process.stdout.write(JSON.stringify(out));
