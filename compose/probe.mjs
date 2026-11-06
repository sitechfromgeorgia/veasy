// The layout probe on a HyperFrames page (tt_shorts/compose.py): the same measurements remotion/src/Probe.tsx takes
// in a Remotion frame, taken from a composed film's DOM at chosen times, so tt_shorts/probe.py's rules judge both
// engines. Each text also says which composition drew it, the fact it is bound to and whether it is the data's, so
// compose.check runs the story's rules on exactly the texts the story is answerable for.
//
//   node compose/probe.mjs < spec.json
//   spec: {"project": "<dir with index.html>", "times": [0.7, 2.2], "labels": ["hook", ...], "browser": "<chrome or null>"}
//
// The page is served from the project folder by a tiny local server with HyperFrames' own runtime and its vendored
// GSAP injected (no CDN): every other request is refused and reported, so a probe run also proves the page needs no
// network. Each time is sought with the runtime's renderSeek (the call `hyperframes render` makes), the brand font's
// faces are awaited, and the page reports every text box. One JSON line per time on stdout:
//   {"t": 0.7, "label": "hook", "probe": {frame, fonts, regions, texts, generated}}   then {"done": true, "blocked": [urls]}
//
// A cut (spec "cuts": [{"a": "s2", "b": "s3", "times": [...]}], "cutGrid": px, "cutOpacity": 0..1) is read the same way,
// frame by frame while both scenes are live, plus what a viewer can see of each: "cells" (the grid points each scene
// shows something at, no further than the first solid thing above it) and a text's "hidden" (how much of it is under
// something solid, a wipe's bars or a panel). One line per reading: {"cut": 0, "t": 10.3, "probe": {...}}.
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(HERE, "node_modules", "hyperframes", "package.json"));
const puppeteer = require("puppeteer-core");
const HF = path.join(HERE, "node_modules", "hyperframes", "dist");
const RUNTIME = path.join(HF, "hyperframe.runtime.iife.js");
const GSAP = path.join(HF, "vendor", "npm", "gsap@3.15.0", "dist", "gsap.min.js");
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml", ".png": "image/png",
  ".jpg": "image/jpeg", ".woff2": "font/woff2", ".json": "application/json", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".mp4": "video/mp4" };

const emit = (o) => process.stdout.write(`${JSON.stringify(o)}\n`);

/** chrome-headless-shell: the spec's, HYPERFRAMES_BROWSER_PATH, or the one HyperFrames/puppeteer cached. */
const chrome = (given) => {
  if (given) return given;
  if (process.env.HYPERFRAMES_BROWSER_PATH) return process.env.HYPERFRAMES_BROWSER_PATH;
  const base = path.join(os.homedir(), ".cache", "puppeteer", "chrome-headless-shell");
  for (const v of fs.existsSync(base) ? fs.readdirSync(base).sort().reverse() : []) {
    for (const exe of ["chrome-headless-shell-win64/chrome-headless-shell.exe", "chrome-headless-shell-linux64/chrome-headless-shell",
      "chrome-headless-shell-mac-x64/chrome-headless-shell", "chrome-headless-shell-mac-arm64/chrome-headless-shell"]) {
      const p = path.join(base, v, exe);
      if (fs.existsSync(p)) return p;
    }
  }
  throw new Error("no chrome-headless-shell: run `npx hyperframes browser ensure` or set HYPERFRAMES_BROWSER_PATH");
};

const serve = (dir) => new Promise((resolve) => {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent((req.url ?? "/").split("?")[0]);
    if (url === "/__veasy/runtime.js") return res.end(fs.readFileSync(RUNTIME));
    if (url === "/__veasy/gsap.js") return res.end(fs.readFileSync(GSAP));
    const file = path.join(dir, url === "/" ? "index.html" : url);
    if (!file.startsWith(dir) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    let body = fs.readFileSync(file);
    if (url === "/" || url === "/index.html") {
      body = String(body).replace(/<script src="https:\/\/cdn\.jsdelivr\.net\/npm\/gsap@[^"]+"><\/script>/, '<script src="/__veasy/gsap.js"></script>')
        .replace("</head>", '<script src="/__veasy/runtime.js"></script></head>');
    }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] ?? "application/octet-stream" });
    res.end(body);
  });
  server.listen(0, "127.0.0.1", () => resolve(server));
});

// ---- in the page: remotion/src/Probe.tsx's collect(), unchanged in what it measures
function collect(t, label, live, grid, faint) {
  const W = 1080;
  const r1 = (n) => Math.round(n * 10) / 10;
  const root = document.querySelector("[data-probe-root]");
  if (!root) return null;
  const R = root.getBoundingClientRect();
  const k = R.width / W || 1;
  const opacityOf = (el) => {
    let o = 1;
    for (let a = el; a && a !== root.parentElement; a = a.parentElement) o *= parseFloat(getComputedStyle(a).opacity || "1");
    return o;
  };
  const box = (r) => [r1((r.left - R.left) / k), r1((r.top - R.top) / k), r1(r.width / k), r1(r.height / k)];
  // the contrast rule's ground (Probe.tsx groundAt): every element painted under a point, composited over the canvas
  const parseColor = (s) => {
    const m = /^rgba?\(([^)]+)\)$/.exec((s ?? "").trim());
    if (!m) return null;
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return p.length >= 3 && p.every((x) => !Number.isNaN(x)) ? [p[0], p[1], p[2], p.length > 3 ? p[3] : 1] : null;
  };
  const hex = getComputedStyle(document.documentElement).getPropertyValue("--canvas").trim() || "#000000";
  const canvas = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) || 0);
  const SHAPES = new Set(["rect", "circle", "ellipse", "path", "polygon"]);
  const layerOf = (e) => {
    const tag = e.tagName.toLowerCase();
    if (["img", "video", "canvas", "image"].includes(tag)) return "image";
    const cs = getComputedStyle(e);
    let c = null;
    if (e instanceof SVGElement) {
      if (!SHAPES.has(tag)) return null;
      c = parseColor(cs.fill);
      if (c) c = [c[0], c[1], c[2], c[3] * parseFloat(cs.fillOpacity || "1")];
    } else {
      c = parseColor(cs.backgroundColor);
      if (!c && cs.backgroundImage.includes("url(")) return "image";
    }
    if (!c || c[3] <= 0) return null;
    return [c[0], c[1], c[2], c[3] * opacityOf(e)];
  };
  const groundAt = (x, y, el) => { // -> [ground] or, over a picture, [over black, over white]
    const layers = [];
    const stack = document.elementsFromPoint(x, y);
    const own = stack.findIndex((e) => e === el || e.contains(el)); // what covers the text is not its ground
    let bases = [canvas.slice()];
    for (const e of own >= 0 ? stack.slice(own) : stack) {
      if (!root.contains(e)) continue;
      const c = layerOf(e);
      if (c === "image") { bases = [[0, 0, 0], [255, 255, 255]]; break; }
      if (!c) continue;
      layers.push(c);
      if (c[3] >= 0.999) break;
    }
    return bases.map((b) => {
      let g = b;
      for (const c of [...layers].reverse()) g = g.map((v, i) => v * (1 - c[3]) + c[i] * c[3]);
      return g.map((v) => Math.round(v));
    });
  };
  // at a cut: how an element paints, wherever the browser's hit test says it is (a stroke is hit on its line, not its box)
  const DRAWN = new Set([...SHAPES, "line", "polyline"]);
  const painted = new Map();
  const paintOf = (e) => {
    if (painted.has(e)) return painted.get(e);
    const tag = e.tagName.toLowerCase();
    const cs = getComputedStyle(e);
    const strength = (paint, opacity) => {
      if (!paint || paint === "none") return 0;
      if (paint.startsWith("url(")) return 0.5; // a gradient: there, but never solid
      return (parseColor(paint)?.[3] ?? 1) * parseFloat(opacity || "1");
    };
    let a = 0;
    if (["img", "video", "canvas", "image"].includes(tag)) a = 1;
    else if (e instanceof SVGElement) a = DRAWN.has(tag) ? strength(cs.fill, cs.fillOpacity) || strength(cs.stroke, cs.strokeOpacity) : 0;
    else a = parseColor(cs.backgroundColor)?.[3] || (cs.backgroundImage !== "none" ? 0.5 : 0);
    let p = null;
    if (a > 0) {
      const q = e.getBoundingClientRect();
      const alpha = a * opacityOf(e);
      p = { scene: e.closest("[data-composition-id]")?.getAttribute("data-composition-id") ?? null, alpha, solid: alpha >= 0.999,
        backdrop: q.width * q.height >= 0.6 * R.width * R.height, decor: !!e.closest("[data-probe-decor]") }; // a scene's ground is no thing in it
    }
    painted.set(e, p);
    return p;
  };
  const hiddenOf = (l, tp, r, b, el) => { // how much of a text is under something solid: what covers it is no collision
    let under = 0;
    for (let i = 0; i < 5; i++) for (let j = 0; j < 3; j++) {
      const stack = document.elementsFromPoint(l + ((r - l) * (i + 0.5)) / 5, tp + ((b - tp) * (j + 0.5)) / 3);
      const own = stack.findIndex((e) => e === el || e.contains(el));
      if (stack.slice(0, Math.max(0, own)).some((e) => root.contains(e) && paintOf(e)?.solid)) under += 1;
    }
    return r1(under / 15);
  };
  const regions = {};
  root.querySelectorAll("[data-probe]").forEach((el) => { (regions[el.dataset.probe] ??= []).push(box(el.getBoundingClientRect())); });
  const texts = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.textContent ?? "";
    const el = n.parentElement;
    if (!el || !text.trim()) continue;
    if (el.closest("template, script, style")) continue;
    const region = el.closest("[data-probe]");
    const name = region?.dataset.probe ?? "other";
    if (name === "ticker") continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") continue;
    const opacity = opacityOf(el);
    if (opacity < 0.05) continue;
    const range = document.createRange();
    range.selectNodeContents(n);
    const svg = el instanceof SVGElement;
    let scale = 1;
    if (svg) { const m = el.getScreenCTM?.(); scale = m ? Math.hypot(m.a, m.b) : 1; }
    else if (el.offsetWidth > 0) scale = el.getBoundingClientRect().width / el.offsetWidth;
    const lineH = svg ? NaN : parseFloat(cs.lineHeight) * scale;
    let l = Infinity, tp = Infinity, r = -Infinity, b = -Infinity;
    let first = null;
    for (const c of Array.from(range.getClientRects())) {
      if (!c.width && !c.height) continue;
      first ??= c;
      const shrink = lineH > 0 ? Math.max(0, (c.height - lineH) / 2) : 0;
      l = Math.min(l, c.left); r = Math.max(r, c.right); tp = Math.min(tp, c.top + shrink); b = Math.max(b, c.bottom - shrink);
    }
    if (!(r > l)) continue;
    const over = { x: 0, y: 0, xIn: "", yIn: "", clipped: false };
    const past = (L, T, Rr, B, what, clipped) => {
      const x = Math.max(L - l, r - Rr) / k, y = Math.max(T - tp, b - B) / k;
      if (x > over.x) { over.x = r1(x); over.xIn = what; over.clipped ||= clipped; }
      if (y > over.y) { over.y = r1(y); over.yIn = what; over.clipped ||= clipped; }
    };
    for (let a = el; a && a !== root; a = a.parentElement) {
      const wide = a.clientWidth > 0 && a.scrollWidth - a.clientWidth > 2;
      const tall = a.clientHeight > 0 && a.scrollHeight - a.clientHeight > 2;
      if (wide || tall) {
        const q = a.getBoundingClientRect();
        const L = q.left + a.clientLeft * k, T = q.top + a.clientTop * k;
        past(wide ? L : -Infinity, tall ? T : -Infinity, wide ? L + a.clientWidth * k : Infinity, tall ? T + a.clientHeight * k : Infinity,
          `${a.tagName.toLowerCase()}${a.dataset?.probe ? `[${a.dataset.probe}]` : ""}`, getComputedStyle(a).overflow !== "visible");
      }
      if (a === region) break;
    }
    const comp = el.closest("[data-composition-id]")?.getAttribute("data-composition-id") ?? null;
    texts.push({ region: name, text, box: [r1((l - R.left) / k), r1((tp - R.top) / k), r1((r - l) / k), r1((b - tp) / k)],
      size: r1((parseFloat(cs.fontSize) * scale) / k), weight: cs.fontWeight, family: cs.fontFamily, color: svg ? cs.fill : cs.color, opacity: r1(opacity), svg,
      overflow: over.x || over.y ? over : null, clipOk: !!el.closest("[data-probe-clip]"), decor: !!el.closest("[data-probe-decor]"),
      ...(() => { const g = first ? groundAt(first.left + first.width / 2, first.top + first.height / 2, el) : [null];
        return { ground: g[0], ground2: g[1] ?? null }; })(),
      // which composition drew it, the fact it is bound to (data-var-text), and whether it is the data's (chrome)
      comp, ...(live?.includes(comp) ? { hidden: hiddenOf(l, tp, r, b, el) } : {}),
      bound: el.closest("[data-var-text]")?.getAttribute("data-var-text") ?? null,
      code: !!el.closest("[data-veasy-code]") });
  }
  // at a cut: the grid points each live scene shows something at, walking down from the top to the first solid thing
  let cells = null;
  if (live) {
    cells = Object.fromEntries(live.map((id) => [id, []]));
    const cols = Math.ceil(W / grid), rows = Math.ceil(R.height / k / grid);
    for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
      const shown = new Set();
      for (const e of document.elementsFromPoint(R.left + (x + 0.5) * grid * k, R.top + (y + 0.5) * grid * k)) {
        if (!root.contains(e)) continue;
        const p = paintOf(e);
        if (!p) continue;
        if (p.scene in cells && p.alpha >= faint && !p.backdrop && !p.decor && !shown.has(p.scene)) {
          shown.add(p.scene);
          cells[p.scene].push(y * cols + x);
        }
        if (p.solid) break;
      }
    }
  }
  // text the walker can't see: what CSS or a script made the browser generate (compose.py: lint css-content, the files)
  const generated = [];
  root.querySelectorAll("*").forEach((el) => {
    if (el.closest("template, script, style")) return;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return;
    const made = ["::before", "::after"].map((p) => getComputedStyle(el, p).content)
      .filter((c) => c && !["none", "normal", '""'].includes(c));
    if (cs.display === "list-item" && !["none", "disc", "circle", "square"].includes(cs.listStyleType)) made.push(cs.listStyleType);
    if (made.length && opacityOf(el) >= 0.05) {
      generated.push({ comp: el.closest("[data-composition-id]")?.getAttribute("data-composition-id") ?? null, content: made[0] });
    }
  });
  const fonts = {};
  document.fonts.forEach((f) => { if (f.family.replace(/["']/g, "") === "Brand") fonts[String(f.weight)] = f.status; });
  return { frame: Math.round(t * 30), scene: label, type: label, fonts, fontsAtRender: fonts, regions, texts, generated, ...(cells ? { cells } : {}) };
}

const main = async () => {
  const spec = JSON.parse(fs.readFileSync(0, "utf8"));
  const dir = path.resolve(spec.project);
  const server = await serve(dir);
  const origin = `http://127.0.0.1:${server.address().port}`;
  const blocked = [];
  const browser = await puppeteer.launch({ executablePath: chrome(spec.browser), headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--font-render-hinting=none", "--hide-scrollbars"] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
    await page.setRequestInterception(true);
    page.on("request", (rq) => {
      if (rq.url().startsWith(origin) || rq.url().startsWith("data:")) rq.continue();
      else { blocked.push(rq.url()); rq.abort(); }
    });
    await page.goto(`${origin}/`, { waitUntil: "load" });
    await page.waitForFunction(() => window.__renderReady === true && !!window.__player, { timeout: 60000 });
    await page.evaluate(() => document.fonts.ready);
    const seek = (at) => page.evaluate(async (s) => {
      await window.__player.renderSeek(s);
      if (window.__hfWaitForSeekCompletion) await window.__hfWaitForSeekCompletion();
      await document.fonts.ready;
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    }, at);
    for (const [i, t] of spec.times.entries()) {
      await seek(t);
      const probe = await page.evaluate(collect, t, spec.labels?.[i] ?? String(t));
      if (spec.shots) await page.screenshot({ path: path.join(spec.shots, `probe-${String(i).padStart(2, "0")}.png`) });
      emit({ t, label: spec.labels?.[i] ?? null, probe });
    }
    for (const [c, cut] of (spec.cuts ?? []).entries()) {
      for (const t of cut.times) {
        await seek(t);
        emit({ cut: c, t, probe: await page.evaluate(collect, t, `${cut.a} to ${cut.b}`, [cut.a, cut.b], spec.cutGrid, spec.cutOpacity) });
      }
    }
  } finally {
    await browser.close();
    server.close();
  }
  emit({ done: true, blocked });
};

main().catch((e) => { emit({ fatal: String(e?.stack ?? e).slice(0, 2000) }); process.exit(1); });
