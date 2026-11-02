// Stills and layout probes in one browser (tt_shorts/probe.py, tt_shorts/golden.py).
//
//   node probe.mjs < spec.json
//   spec: {"cache": "<dir for bundles>", "browser": "<chrome-headless-shell or null>",
//          "jobs": [{"props": "<props.json>", "public": "<public dir>", "frames": [12, 80], "out": "<dir or null>",
//                    "probe": true}]}
//
// The bundle is built once per version of src/ (a hash of its files) and kept in <cache>/<hash>/; each job serves
// it with its own public dir (fonts, logo, voice), so another story or brand costs no rebuild. One browser renders
// every frame of every job. Each result is one JSON line on stdout:
//   {"job": 0, "frame": 12, "file": "<png or null>", "probe": {...the page's VEASY_PROBE report...}}
//   {"job": 0, "error": "..."}                      a job that failed (the others still run)
//   {"done": true, "bundle": "<dir>", "built": false, "seconds": 4.2}
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(HERE, "src");
const TAG = "VEASY_PROBE ";

const emit = (o) => process.stdout.write(`${JSON.stringify(o)}\n`);

const filesUnder = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? filesUnder(p) : [p];
  }).sort();

/** What the bundle is made of: the composition's source and the package versions. */
const sourceHash = () => {
  const h = crypto.createHash("sha256");
  for (const f of [...filesUnder(SRC), path.join(HERE, "package.json")]) {
    h.update(path.relative(HERE, f));
    h.update(fs.readFileSync(f));
  }
  return h.digest("hex").slice(0, 16);
};

const cachedBundle = async (cache) => {
  const dir = path.join(cache, sourceHash());
  if (fs.existsSync(path.join(dir, "index.html"))) return { dir, built: false };
  fs.mkdirSync(cache, { recursive: true });
  const empty = fs.mkdtempSync(path.join(cache, "public-"));
  const tmp = `${dir}.tmp-${process.pid}`;
  await bundle({ entryPoint: path.join(SRC, "index.ts"), outDir: tmp, publicDir: empty, rootDir: HERE });
  fs.rmSync(path.join(tmp, "public"), { recursive: true, force: true });
  fs.rmSync(empty, { recursive: true, force: true });
  try {
    fs.renameSync(tmp, dir);
  } catch (e) {
    fs.rmSync(tmp, { recursive: true, force: true }); // another process built it first
    if (!fs.existsSync(path.join(dir, "index.html"))) throw e;
  }
  return { dir, built: true };
};

/** The bundle as this job sees it: its files linked (or copied), public/ pointing at the job's own public dir.
 *  Remotion's server refuses a file that is a symlink, but follows a symlinked folder. */
const serveDir = (bundleDir, pub) => {
  const dir = path.join(path.dirname(pub), "probe-serve");
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir);
  for (const e of fs.readdirSync(bundleDir, { withFileTypes: true })) {
    const from = path.join(bundleDir, e.name), to = path.join(dir, e.name);
    if (e.isDirectory()) fs.symlinkSync(from, to, "dir");
    else {
      try { fs.linkSync(from, to); } catch { fs.copyFileSync(from, to); }
    }
  }
  fs.symlinkSync(path.resolve(pub), path.join(dir, "public"), "dir");
  return dir;
};

const main = async () => {
  const spec = JSON.parse(fs.readFileSync(0, "utf8"));
  const t0 = Date.now();
  const { dir, built } = await cachedBundle(spec.cache);
  const browser = await openBrowser("chrome", { browserExecutable: spec.browser || null, logLevel: "error" });
  try {
    for (const [j, job] of spec.jobs.entries()) {
      try {
        const props = { ...JSON.parse(fs.readFileSync(job.props, "utf8")), probe: job.probe !== false };
        const serveUrl = serveDir(dir, job.public);
        const composition = await selectComposition({ serveUrl, id: "NewsShort", inputProps: props, puppeteerInstance: browser,
          logLevel: "error" });
        if (job.out) fs.mkdirSync(job.out, { recursive: true });
        for (const frame of job.frames) {
          let probe = null;
          const file = job.out ? path.join(job.out, `${job.name ?? "frame"}-${frame}.png`) : null;
          await renderStill({ serveUrl, composition, inputProps: props, frame, output: file,
            ...(file ? { imageFormat: "png" } : { imageFormat: "jpeg", jpegQuality: 50 }), puppeteerInstance: browser, overwrite: true, logLevel: "error",
            onBrowserLog: (log) => {
              if (!log.text.startsWith(TAG)) return;
              const data = JSON.parse(log.text.slice(TAG.length));
              if (data.frame === frame) probe = data;
            } });
          emit({ job: j, frame, file, probe });
        }
      } catch (e) {
        emit({ job: j, error: String(e?.stack ?? e).slice(0, 2000) });
      }
    }
  } finally {
    await browser.close({ silent: true });
  }
  emit({ done: true, bundle: dir, built, seconds: Math.round((Date.now() - t0) / 100) / 10 });
};

main().catch((e) => {
  emit({ fatal: String(e?.stack ?? e).slice(0, 2000) });
  process.exit(1);
});
