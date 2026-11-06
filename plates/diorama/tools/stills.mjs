#!/usr/bin/env node
// Look before you bake: frames of a set at chosen moments, without an mp4.
//   node plates/diorama/tools/stills.mjs <set.json> --at 0,0.5,1 --scale 0.5 --out out/stills/x
// Run it from the repo root. --at is a fraction of the take. Prints the ms a frame of the last still.
import fs from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const GL = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
  "--enable-webgl", "--force-color-profile=srgb", "--font-render-hinting=none", "--no-sandbox"];
const TYPES = { ".html": "text/html", ".mjs": "text/javascript", ".js": "text/javascript", ".json": "application/json" };

const [specFile, ...rest] = process.argv.slice(2);
const opt = { at: "0,0.5,1", scale: "0.5", out: "out/stills", seconds: "6", seed: "1" };
for (let i = 0; i < rest.length; i += 2) opt[rest[i].replace(/^--/, "")] = rest[i + 1];

function chrome() {
  if (process.env.VEASY_CHROME) return process.env.VEASY_CHROME;
  const base = path.join(os.homedir(), ".cache", "puppeteer", "chrome-headless-shell");
  const name = process.platform === "win32" ? "chrome-headless-shell.exe" : "chrome-headless-shell";
  for (const version of fs.readdirSync(base).sort().reverse()) {
    for (const sub of fs.readdirSync(path.join(base, version))) {
      const exe = path.join(base, version, sub, name);
      if (fs.existsSync(exe)) return exe;
    }
  }
  throw new Error("no chrome-headless-shell");
}

const server = http.createServer((req, res) => {
  const file = path.normalize(path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return res.writeHead(404).end();
  res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const puppeteer = createRequire(path.join(ROOT, "package.json"))("puppeteer-core");
const scale = Number(opt.scale), width = Math.round(1080 * scale), height = Math.round(1920 * scale);
const browser = await puppeteer.launch({ executablePath: chrome(), headless: "shell", args: GL,
  defaultViewport: { width, height, deviceScaleFactor: 1 }, protocolTimeout: 300000 });
try {
  const page = await browser.newPage();
  const failures = [];
  page.on("pageerror", (e) => failures.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") failures.push(m.text()); });
  await page.goto(`http://127.0.0.1:${server.address().port}/diorama/index.html`, { waitUntil: "load" });
  await page.waitForFunction("window.setup && window.step", { timeout: 30000 }).catch(() => {});
  if (failures.length) throw new Error(failures[0]);
  const spec = JSON.parse(fs.readFileSync(specFile, "utf8"));
  const seconds = Number(opt.seconds), ctx = { width, height, fps: 30, seed: Number(opt.seed), seconds };
  await page.evaluate((s, c) => window.setup(s, c), spec, ctx);
  if (failures.length) throw new Error(failures[0]);
  fs.mkdirSync(opt.out, { recursive: true });
  let ms = 0;
  for (const at of opt.at.split(",").map(Number)) {
    const t = Math.min(at * seconds, seconds - 1 / 30);
    ms = await page.evaluate((x) => {
      window.step(x);
      const a = performance.now();
      window.step(x);
      return performance.now() - a;
    }, t);
    const name = `${path.basename(specFile, ".json")}-${String(Math.round(at * 100)).padStart(3, "0")}.png`;
    await page.screenshot({ path: path.join(opt.out, name) });
  }
  console.log(JSON.stringify({ set: spec.id, width, height, ms_step: Math.round(ms) }));
} finally {
  await browser.close();
  server.close();
}
