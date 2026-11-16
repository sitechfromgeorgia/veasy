// A screenshot of one page with the browser Remotion already installed (chrome-headless-shell), driven over the
// DevTools protocol with Node's own WebSocket: no Playwright, no puppeteer, no new dependency (tt_shorts/media/
// screenshot.py calls this and judges the result).
//
//   node shot.mjs --chrome <exe> --url <url> --out <png> [--width 1080] [--height 1920] [--find "text"]
//                 [--color "#EF4444"] [--timeout 30000]
//
// It loads the page at the given viewport, and with --find looks for the smallest element whose text contains the
// phrase (whitespace-insensitive), scrolls it to the middle and draws a box around it in --color. It prints one JSON
// line: {"ok", "url" (where the page ended up after redirects), "title", "found", "box": [x, y, w, h]}.
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1]]);
  return acc;
}, []));
const width = Number(args.width ?? 1080), height = Number(args.height ?? 1920), timeout = Number(args.timeout ?? 30000);
const profile = mkdtempSync(join(tmpdir(), "veasy-shot-"));
const chrome = spawn(args.chrome, ["--headless", "--no-sandbox", "--disable-dev-shm-usage", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
  `--window-size=${width},${height}`, "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
  "--disable-gpu", "--disable-extensions", "--mute-audio", "--lang=ka", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });

const done = (obj, code = 0) => {
  process.stdout.write(JSON.stringify(obj) + "\n");
  try { chrome.kill(); } catch { /* gone */ }
  setTimeout(() => { try { rmSync(profile, { recursive: true, force: true }); } catch { /* busy */ } process.exit(code); }, 300);
};
const timer = setTimeout(() => done({ ok: false, error: `timed out after ${timeout} ms` }, 1), timeout + 15000);

const wsUrl = await new Promise((resolve, reject) => {
  let buf = "";
  chrome.stderr.on("data", (d) => {
    buf += d.toString();
    const m = /DevTools listening on (ws:\/\/\S+)/.exec(buf);
    if (m) resolve(m[1]);
  });
  chrome.on("exit", (c) => reject(new Error(`chrome exited (${c}): ${buf.slice(-400)}`)));
}).catch((e) => { done({ ok: false, error: String(e.message ?? e) }, 1); return null; });
if (!wsUrl) await new Promise(() => {});

const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let seq = 0;
const waiting = new Map();
const listeners = [];
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && waiting.has(msg.id)) {
    const { resolve, reject } = waiting.get(msg.id);
    waiting.delete(msg.id);
    msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
  } else if (msg.method) {
    listeners.forEach((l) => l(msg));
  }
});
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
  const id = ++seq;
  waiting.set(id, { resolve, reject });
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});
const event = (name, sessionId, ms) => new Promise((resolve) => {
  const t = setTimeout(() => resolve(false), ms);
  listeners.push((m) => { if (m.method === name && m.sessionId === sessionId) { clearTimeout(t); resolve(true); } });
});

try {
  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  await send("Page.enable", {}, sessionId);
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false }, sessionId);
  const loaded = event("Page.loadEventFired", sessionId, timeout);
  await send("Page.navigate", { url: args.url }, sessionId);
  await loaded;
  await new Promise((r) => setTimeout(r, 1500)); // late fonts and layout
  const find = args.find ?? "";
  const color = args.color ?? "#EF4444";
  const script = `(() => {
    const norm = (s) => (s || "").replace(/\\s+/g, " ").trim().toLowerCase();
    const want = norm(${JSON.stringify(find)});
    let hit = null;
    if (want) {
      const all = Array.from(document.body.querySelectorAll("*")).filter((el) => norm(el.textContent).includes(want));
      hit = all.find((el) => !Array.from(el.children).some((c) => norm(c.textContent).includes(want))) || null;
    }
    let box = null;
    if (hit) {
      hit.scrollIntoView({ block: "center", inline: "nearest" });
      const r = hit.getBoundingClientRect();
      const pad = 10;
      box = [Math.max(0, r.left - pad), Math.max(0, r.top - pad), Math.min(innerWidth, r.width + 2 * pad), r.height + 2 * pad];
      const o = document.createElement("div");
      o.style.cssText = "position:fixed;pointer-events:none;z-index:2147483647;border:6px solid ${color};border-radius:10px;" +
        "left:" + box[0] + "px;top:" + box[1] + "px;width:" + box[2] + "px;height:" + box[3] + "px;box-sizing:border-box";
      document.documentElement.appendChild(o);
    }
    return { url: location.href, title: document.title, found: Boolean(hit), box };
  })()`;
  const { result } = await send("Runtime.evaluate", { expression: script, returnByValue: true }, sessionId);
  await new Promise((r) => setTimeout(r, 300));
  const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false }, sessionId);
  writeFileSync(args.out, Buffer.from(shot.data, "base64"));
  clearTimeout(timer);
  done({ ok: true, ...result.value });
} catch (e) {
  clearTimeout(timer);
  done({ ok: false, error: String(e.message ?? e) }, 1);
}
