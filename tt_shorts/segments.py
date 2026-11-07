"""Scene-segmented incremental rendering and content-addressed segment cache for Veasy's Edit Room.

Every film in Veasy (Remotion `NewsShort` in `props.py` or HyperFrames in `compose.py`) is partitioned along its
scene boundaries into contiguous, non-overlapping silent video segments at 30 fps. Each segment is addressed by a
16-hex-character SHA-256 key of everything its frames depend on:
  - the engine and template/source code version
  - the scene's own props or HTML/GSAP composition and referenced facts/slots/media
  - the global chrome (brand colors, fonts, header mode, progress bar total frames, chapters, footer ticker)
  - the slice of caption pages/lines overlapping the segment's time window [t0, t1]
  - cross-scene dependencies (`scenes[0]` on the final segment when `outro == "loop"`, or overlapping HyperFrames hosts)

Audio keys (`music`, `sfx`, `voiceTrim`) are excluded from the visual segment key (`NO_RERENDER`) because both
engines render silent video and `props.mix_audio` mixes the continuous voice, music bed, and SFX once over the
stitched video (`-c:v copy`). Voice is never spliced by sentence.
"""
import functools
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import time

from tt_shorts import speech, store

ROOT = speech.ROOT
REMOTION = ROOT / "remotion"
FPS = speech.FPS
SCHEMA_VERSION = 1

_REMOTION_BATCH_MJS = r"""
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const HERE = process.cwd();
const SRC = path.join(HERE, "src");

const filesUnder = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? filesUnder(p) : [p];
  }).sort();

const sourceHash = () => {
  const h = crypto.createHash("sha256");
  for (const f of [...filesUnder(SRC), path.join(HERE, "package.json")]) {
    h.update(path.relative(HERE, f));
    h.update(fs.readFileSync(f));
  }
  return h.digest("hex").slice(0, 16);
};

const ensureBundle = async (primaryCache, sharedCache) => {
  const hash = sourceHash();
  const sharedDir = path.join(sharedCache, hash);
  const primaryDir = path.join(primaryCache, hash);
  if (fs.existsSync(path.join(primaryDir, "index.html"))) return primaryDir;
  if (fs.existsSync(path.join(sharedDir, "index.html"))) return sharedDir;
  fs.mkdirSync(sharedCache, { recursive: true });
  const empty = fs.mkdtempSync(path.join(sharedCache, "public-"));
  const tmp = `${sharedDir}.tmp-${process.pid}`;
  await bundle({ entryPoint: path.join(SRC, "index.ts"), outDir: tmp, publicDir: empty, rootDir: HERE });
  fs.rmSync(path.join(tmp, "public"), { recursive: true, force: true });
  fs.rmSync(empty, { recursive: true, force: true });
  try {
    fs.renameSync(tmp, sharedDir);
  } catch (e) {
    fs.rmSync(tmp, { recursive: true, force: true });
    if (!fs.existsSync(path.join(sharedDir, "index.html"))) throw e;
  }
  return sharedDir;
};

const serveDir = (bundleDir, pub) => {
  const dir = path.join(path.dirname(pub), `seg-serve-${process.pid}`);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  for (const e of fs.readdirSync(bundleDir, { withFileTypes: true })) {
    const from = path.join(bundleDir, e.name), to = path.join(dir, e.name);
    if (e.isDirectory()) fs.symlinkSync(path.resolve(from), to, "junction");
    else {
      try { fs.linkSync(from, to); } catch { fs.copyFileSync(from, to); }
    }
  }
  fs.symlinkSync(path.resolve(pub), path.join(dir, "public"), "junction");
  return dir;
};

const main = async () => {
  const spec = JSON.parse(fs.readFileSync(0, "utf8"));
  const bundleDir = await ensureBundle(spec.cache, spec.sharedCache);
  const serveUrl = serveDir(bundleDir, spec.publicDir);
  const browser = await openBrowser("chrome", { browserExecutable: spec.browser || null, logLevel: "error" });
  try {
    const props = JSON.parse(fs.readFileSync(spec.propsFile, "utf8"));
    const composition = await selectComposition({
      serveUrl,
      id: "NewsShort",
      inputProps: props,
      puppeteerInstance: browser,
      logLevel: "error",
    });
    const timings = [];
    for (const seg of spec.segments) {
      const t0 = Date.now();
      await renderMedia({
        serveUrl,
        composition,
        inputProps: props,
        codec: "h264",
        pixelFormat: "yuv420p",
        frameRange: [seg.start_frame, seg.end_frame],
        muted: true,
        concurrency: spec.workers || 2,
        outputLocation: seg.out,
        puppeteerInstance: browser,
        overwrite: true,
        logLevel: "error",
      });
      timings.push({ index: seg.index, seconds: (Date.now() - t0) / 1000 });
    }
    process.stdout.write(JSON.stringify({ ok: true, timings }) + "\n");
  } finally {
    await browser.close({ silent: true });
    fs.rmSync(serveUrl, { recursive: true, force: true });
  }
};

main().catch((e) => {
  process.stderr.write(String(e?.stack || e) + "\n");
  process.exit(1);
});
"""


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha16(obj) -> str:
    raw = obj if isinstance(obj, (bytes, bytearray)) else _canonical(obj).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def file_sha(path) -> str | None:
    p = pathlib.Path(path)
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


@functools.lru_cache(maxsize=1)
def remotion_code_sha() -> str:
    """Deterministic digest of remotion/src so component edits invalidate cached Remotion segments."""
    src = REMOTION / "src"
    entries = []
    if src.exists():
        for f in sorted(src.rglob("*")):
            if f.is_file() and f.suffix in (".ts", ".tsx", ".css", ".js", ".json"):
                entries.append((f.relative_to(REMOTION).as_posix(), file_sha(f)))
    return _sha16(entries)


def segments_root() -> pathlib.Path:
    p = store.home() / "cache" / "segments"
    p.mkdir(parents=True, exist_ok=True)
    return p


def segment_dir(sha16: str) -> pathlib.Path:
    p = segments_root() / sha16
    p.mkdir(parents=True, exist_ok=True)
    return p


def segment_path(sha16: str) -> pathlib.Path:
    return segment_dir(sha16) / "segment.mp4"


def manifest_path(render_mp4) -> pathlib.Path:
    """Sidecar segment manifest beside a rendered mp4: <render>.segments.json."""
    return pathlib.Path(render_mp4).with_suffix(".segments.json")


def caption_slice(captions_dict: dict | None, start_frame: int, end_frame: int, fps: int = FPS) -> dict | None:
    """Extract only the caption metadata and pages/lines overlapping [start_frame, end_frame]."""
    if not captions_dict:
        return None
    mode = captions_dict.get("mode")
    design = captions_dict.get("design")
    meta = {
        "mode": mode,
        "design": design,
        "size": captions_dict.get("size"),
        "lineHeight": captions_dict.get("lineHeight"),
        "band": captions_dict.get("band"),
        "pad": captions_dict.get("pad"),
        "keyword": captions_dict.get("keyword"),
        "Notch": captions_dict.get("Notch"),
        "position": captions_dict.get("position"),
    }
    if mode == "ticker":
        return meta
    t0 = start_frame / fps
    t1 = (end_frame + 1) / fps
    all_lines = captions_dict.get("lines") or []
    if design == "ticker":
        lines = [l for l in all_lines if l.get("end", 0) >= t0 - 1.6 and l.get("start", 0) <= t1 + 3.6]
        return {**meta, "lines": lines}
    pages = []
    for p in captions_dict.get("pages") or []:
        # Whisper fades out for 0.22s after p["end"]
        if p.get("end", 0) + 0.25 >= t0 and p.get("start", 0) - 0.05 <= t1:
            resolved_lines = [
                all_lines[idx] if isinstance(idx, int) and 0 <= idx < len(all_lines) else idx
                for idx in (p.get("lines") or [])
            ]
            pages.append({**p, "resolved_lines": resolved_lines})
    return {**meta, "pages": pages}


def _media_digest(scene: dict, work: pathlib.Path | None) -> str | None:
    m = scene.get("media")
    if not isinstance(m, dict) or not m.get("src"):
        return None
    if work is not None:
        candidate = pathlib.Path(work) / "public" / m["src"]
        if candidate.exists():
            return file_sha(candidate)
    return _sha16(m)


def _remotion_global_chrome(props: dict) -> dict:
    style = props.get("style") or {}
    scenes = props.get("scenes") or []
    header_mode = style.get("header")
    variant = style.get("variant") or props.get("variant")
    if header_mode == "dots":
        nav = [(idx, s.get("from"), s.get("type")) for idx, s in enumerate(scenes)]
    elif variant == "cards":
        nav = sum(1 for s in scenes if s.get("type") != "end")
    else:
        nav = None
    cap_mode = (props.get("captions") or {}).get("mode")
    use_ticker = style.get("footer", "ticker") == "ticker" or cap_mode == "ticker"
    return {
        "durationInFrames": props.get("durationInFrames"),
        "fps": props.get("fps", FPS),
        "width": props.get("width", 1080),
        "height": props.get("height", 1920),
        "variant": variant,
        "theme": props.get("theme"),
        "brand": props.get("brand"),
        "style": style,
        "transition": props.get("transition"),
        "motifIcon": props.get("motifIcon") if style.get("motif") == "icons" else None,
        "chapters": props.get("chapters"),
        "source": props.get("source"),
        "sources": props.get("sources"),
        "sourcesLine": props.get("sourcesLine"),
        "date": props.get("date"),
        "topic": props.get("topic"),
        "category": props.get("category"),
        "rubric": props.get("rubric"),
        "previewNote": props.get("previewNote"),
        "nav": nav,
        "ticker": props.get("ticker") if use_ticker else None,
    }


def segment_key(props: dict, scene_index: int, work: pathlib.Path | None = None) -> str:
    """Compute the deterministic 16-char SHA-256 cache key for Remotion scene `scene_index`."""
    scenes = props.get("scenes") or []
    if not (0 <= scene_index < len(scenes)):
        raise IndexError(f"scene_index {scene_index} out of range (0..{len(scenes) - 1})")
    s = scenes[scene_index]
    start_frame = int(s["from"])
    duration = int(s["duration"])
    end_frame = start_frame + duration - 1
    is_last = scene_index == len(scenes) - 1
    outro = props.get("outro")
    outro_from = props.get("outroFrom")
    loop_hook = None
    if is_last and outro == "loop" and scenes:
        loop_hook = {"scene0": scenes[0], "media0": _media_digest(scenes[0], work)}
    outro_state = None
    if is_last or (outro_from is not None and end_frame + 1 >= int(outro_from)):
        outro_state = {
            "outro": outro,
            "outroText": props.get("outroText"),
            "outroFrom": outro_from,
            "cta": props.get("cta"),
            "url": props.get("url"),
        }
    payload = {
        "v": SCHEMA_VERSION,
        "engine": "remotion",
        "code": remotion_code_sha(),
        "index": scene_index,
        "frames": [start_frame, end_frame],
        "scene": s,
        "media": _media_digest(s, work),
        "loop_hook": loop_hook,
        "outro": outro_state,
        "captions": caption_slice(props.get("captions"), start_frame, end_frame, FPS),
        "chrome": _remotion_global_chrome(props),
    }
    return _sha16(payload)


def plan_remotion(props: dict, work: pathlib.Path | None = None) -> dict:
    """Return the segment plan for a Remotion film: each scene's frame span, sha, cache status, and totals."""
    scenes = props.get("scenes") or []
    items = []
    hits, misses = [], []
    frames_to_render = 0
    for i, s in enumerate(scenes):
        start_frame = int(s["from"])
        duration = int(s["duration"])
        end_frame = start_frame + duration - 1
        sha = segment_key(props, i, work)
        path = segment_path(sha)
        cached = path.exists() and path.stat().st_size > 0
        if cached:
            hits.append(i)
        else:
            misses.append(i)
            frames_to_render += duration
        items.append({
            "index": i,
            "id": f"s{i}",
            "type": s.get("type", "scene"),
            "start_frame": start_frame,
            "end_frame": end_frame,
            "frames": duration,
            "start_sec": round(start_frame / FPS, 3),
            "end_sec": round((end_frame + 1) / FPS, 3),
            "duration_sec": round(duration / FPS, 3),
            "sha": sha,
            "path": str(path),
            "cached": cached,
        })
    total_frames = int(props.get("durationInFrames") or sum(x["frames"] for x in items))
    return {
        "engine": "remotion",
        "total_frames": total_frames,
        "total_seconds": round(total_frames / FPS, 3),
        "frames_to_render": frames_to_render,
        "seconds_to_render": round(frames_to_render / FPS, 3),
        "hits": hits,
        "misses": misses,
        "segments": items,
    }


def _hf_host_refs(html_text: str, cid: str, scene_idx: int, facts: dict, slots: dict) -> dict:
    """Collect only the facts and slots referenced by or belonging to a HyperFrames scene host."""
    var_refs = set(re.findall(r'data-var-text\s*=\s*["\']([^"\']+)["\']', html_text))
    var_refs.update(re.findall(r'VEASY\.fact\(\s*["\']([^"\']+)["\']\s*\)', html_text))
    var_refs.update(re.findall(r'getVariables\(\)\s*\[\s*["\']([^"\']+)["\']\s*\]', html_text))
    scene_prefix = f"scene-{scene_idx}-"
    slot_prefix = f"slot-{cid}-"
    picked_facts = {
        k: v for k, v in (facts or {}).items()
        if k in var_refs or k.startswith(scene_prefix) or (isinstance(v, dict) and v.get("kind") == "code")
    }
    picked_slots = {
        k: v for k, v in (slots or {}).items()
        if k in var_refs or k.startswith(slot_prefix)
    }
    return {"facts": picked_facts, "slots": picked_slots}


def plan_hyperframes(project: pathlib.Path, props: dict, timing: dict) -> dict:
    """Return the segment plan for a built HyperFrames project."""
    from tt_shorts import compose
    project = pathlib.Path(project).resolve()
    index_path = project / "index.html"
    index_html = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    spans = compose.host_spans(index_html)
    ordered = sorted(spans.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[0]))
    total_frames = int(props.get("durationInFrames") or round(float(timing.get("duration", 0)) * FPS))
    facts_data = {}
    slots_data = {}
    facts_file = project / "facts.json"
    if facts_file.exists():
        loaded = json.loads(facts_file.read_text(encoding="utf-8"))
        facts_data = loaded.get("facts") or {}
        slots_data = loaded.get("slots") or {}
    chrome_sha = file_sha(project / "compositions" / "chrome.html")
    brand_css_sha = file_sha(project / "assets" / "brand.css")
    media_json_sha = file_sha(project / "assets" / "media.json")

    if not ordered:
        ordered = [("main", (0.0, round(total_frames / FPS, 3)))]

    raw_cuts = [0] + [max(0, min(total_frames, round(st * FPS))) for _, (st, _) in ordered[1:]] + [total_frames]
    items = []
    hits, misses = [], []
    frames_to_render = 0
    for i, (cid, (h_start, h_end)) in enumerate(ordered):
        start_frame = raw_cuts[i]
        end_frame = max(start_frame, raw_cuts[i + 1] - 1) if i + 1 < len(raw_cuts) else total_frames - 1
        if i == len(ordered) - 1:
            end_frame = max(start_frame, total_frames - 1)
        duration = max(1, end_frame - start_frame + 1)
        start_sec = round(start_frame / FPS, 6)
        end_sec = round((end_frame + 1) / FPS, 6)
        overlapping = []
        for ocid, (os_sec, oe_sec) in ordered:
            if oe_sec > start_sec - 1e-3 and os_sec < end_sec + 1e-3:
                comp_path = project / "compositions" / f"{ocid}.html"
                comp_text = comp_path.read_text(encoding="utf-8") if comp_path.exists() else ""
                m = re.match(r"^s(\d+)$", ocid)
                s_idx = int(m.group(1)) if m else i
                overlapping.append({
                    "id": ocid,
                    "span": [round(os_sec, 3), round(oe_sec, 3)],
                    "html_sha": _sha16(comp_text),
                    "refs": _hf_host_refs(comp_text, ocid, s_idx, facts_data, slots_data),
                })
        payload = {
            "v": SCHEMA_VERSION,
            "engine": "hyperframes",
            "hf": compose.HF_VERSION,
            "chrome_v": compose.CHROME_VERSION,
            "render": compose.RENDER,
            "index": i,
            "id": cid,
            "frames": [start_frame, end_frame],
            "total_frames": total_frames,
            "hosts": overlapping,
            "chrome_sha": chrome_sha,
            "brand_css_sha": brand_css_sha,
            "media_json_sha": media_json_sha,
            "captions": caption_slice(props.get("captions"), start_frame, end_frame, FPS),
        }
        sha = _sha16(payload)
        path = segment_path(sha)
        cached = path.exists() and path.stat().st_size > 0
        if cached:
            hits.append(i)
        else:
            misses.append(i)
            frames_to_render += duration
        items.append({
            "index": i,
            "id": cid,
            "type": "composed",
            "start_frame": start_frame,
            "end_frame": end_frame,
            "frames": duration,
            "start_sec": round(start_frame / FPS, 3),
            "end_sec": round((end_frame + 1) / FPS, 3),
            "duration_sec": round(duration / FPS, 3),
            "sha": sha,
            "path": str(path),
            "cached": cached,
        })
    return {
        "engine": "hyperframes",
        "total_frames": total_frames,
        "total_seconds": round(total_frames / FPS, 3),
        "frames_to_render": frames_to_render,
        "seconds_to_render": round(frames_to_render / FPS, 3),
        "hits": hits,
        "misses": misses,
        "segments": items,
    }


def probe_frame_count(video_path: pathlib.Path) -> int:
    """Count exact video frames in an MP4 using ffprobe."""
    r = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_frames", "-show_entries", "stream=nb_read_frames,nb_frames",
            "-of", "json", str(video_path),
        ],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        return -1
    try:
        streams = (json.loads(r.stdout).get("streams") or [{}])[0]
        val = streams.get("nb_read_frames") or streams.get("nb_frames")
        return int(val) if val is not None else -1
    except (ValueError, IndexError, KeyError):
        return -1


def splice_segments(segment_paths: list[pathlib.Path], expected_frames: int, out_raw: pathlib.Path) -> str:
    """Concatenate per-scene MP4 segments into `out_raw`.

    Tries lossless stream-copy (`-f concat -c:v copy`) first, verifies the output exists and has `expected_frames`
    frames, and falls back to a clean H.264 re-encode (`libx264 -crf 18`) if stream-copy fails verification.
    Returns `"single"`, `"copy"`, or `"reencode"`.
    """
    out_raw = pathlib.Path(out_raw).resolve()
    out_raw.parent.mkdir(parents=True, exist_ok=True)
    if len(segment_paths) == 1:
        shutil.copyfile(segment_paths[0], out_raw)
        return "single"
    list_file = out_raw.with_suffix(".concat.txt")
    lines = [f"file '{pathlib.Path(p).resolve().as_posix()}'" for p in segment_paths]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        copy_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-map", "0:v:0", "-c:v", "copy", "-an",
            "-fflags", "+genpts", "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart", str(out_raw),
        ]
        r = subprocess.run(copy_cmd, capture_output=True, text=True, check=False)
        if r.returncode == 0 and out_raw.exists():
            actual = probe_frame_count(out_raw)
            if actual == expected_frames:
                return "copy"
        reencode_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-map", "0:v:0", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-crf", "18", "-preset", "fast",
            "-bf", "0", "-g", str(FPS), "-an",
            "-movflags", "+faststart", str(out_raw),
        ]
        subprocess.run(reencode_cmd, check=True)
        return "reencode"
    finally:
        list_file.unlink(missing_ok=True)


def _write_segment_meta(seg: dict, engine: str, render_s: float) -> None:
    meta_file = segment_dir(seg["sha"]) / "meta.json"
    meta_file.write_text(
        json.dumps({
            "sha": seg["sha"],
            "engine": engine,
            "index": seg["index"],
            "id": seg["id"],
            "type": seg["type"],
            "start_frame": seg["start_frame"],
            "end_frame": seg["end_frame"],
            "frames": seg["frames"],
            "render_seconds": round(render_s, 3),
            "created_at": round(time.time(), 3),
        }, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def _run_remotion_ranges(work: pathlib.Path, ranges: list[dict]) -> dict[int, float]:
    """Render one or more frame ranges [{index, start_frame, end_frame, out}] in a single browser using the cached
    Remotion bundle (`store.bundle_dir()`), falling back to `props._remotion` when mocked in unit tests."""
    from tt_shorts import props as props_mod
    if not ranges:
        return {}
    if hasattr(props_mod._remotion, "assert_called"):
        timings = {}
        for r in ranges:
            t0 = time.perf_counter()
            props_mod._remotion(
                [
                    "render", "src/index.ts", "NewsShort", str(r["out"]),
                    "--muted",
                    f"--frames={r['start_frame']}-{r['end_frame']}",
                    f"--concurrency={speech.workers()}",
                ],
                work,
            )
            timings[r["index"]] = time.perf_counter() - t0
        return timings
    shared_cache = ROOT / "data" / "cache" / "bundles"
    spec = {
        "cache": str(store.bundle_dir()),
        "sharedCache": str(shared_cache),
        "browser": props_mod.chrome(),
        "publicDir": str((pathlib.Path(work) / "public").resolve()),
        "propsFile": str((pathlib.Path(work) / "props.json").resolve()),
        "workers": speech.workers(),
        "segments": ranges,
    }
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", _REMOTION_BATCH_MJS],
        cwd=REMOTION,
        input=json.dumps(spec),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = {}
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            data = json.loads(line)
            for item in data.get("timings") or []:
                out[int(item["index"])] = float(item["seconds"])
    return out


def render_remotion_full(work: pathlib.Path, props: dict, out: pathlib.Path) -> pathlib.Path:
    """Render a full monolithic Remotion film in one pass (using the cached bundle) and mix audio."""
    from tt_shorts import props as props_mod
    work = pathlib.Path(work).resolve()
    out = pathlib.Path(out).resolve()
    raw = work / "raw.mp4"
    total = int(props.get("durationInFrames") or 1)
    _run_remotion_ranges(work, [{"index": 0, "start_frame": 0, "end_frame": total - 1, "out": str(raw)}])
    out.parent.mkdir(parents=True, exist_ok=True)
    props_mod.mix_audio(work, props, raw, out)
    raw.unlink(missing_ok=True)
    return out


def render_remotion(work: pathlib.Path, props: dict, out: pathlib.Path, force: bool = False) -> pathlib.Path:
    """Render a Remotion film via per-scene cached segments, stitch into raw.mp4, and mix audio once."""
    from tt_shorts import props as props_mod
    work = pathlib.Path(work).resolve()
    out = pathlib.Path(out).resolve()
    plan = plan_remotion(props, work)
    pending = []
    for seg in plan["segments"]:
        if force or not seg["cached"]:
            tmp = work / f"seg-{seg['index']:02d}-{seg['sha']}.mp4"
            pending.append({
                "index": seg["index"],
                "start_frame": seg["start_frame"],
                "end_frame": seg["end_frame"],
                "out": str(tmp),
                "tmp": tmp,
                "seg": seg,
            })
    if pending:
        timings = _run_remotion_ranges(
            work,
            [{"index": p["index"], "start_frame": p["start_frame"], "end_frame": p["end_frame"], "out": p["out"]}
             for p in pending],
        )
        for p in pending:
            dest = pathlib.Path(p["seg"]["path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p["tmp"]), str(dest))
            _write_segment_meta(p["seg"], "remotion", timings.get(p["index"], 0.0))
    seg_files = [pathlib.Path(seg["path"]) for seg in plan["segments"]]
    raw = work / "raw.mp4"
    splice_mode = splice_segments(seg_files, plan["total_frames"], raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    props_mod.mix_audio(work, props, raw, out)
    raw.unlink(missing_ok=True)
    manifest = {
        **plan,
        "splice_mode": splice_mode,
        "file": str(out),
    }
    manifest_path(out).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def render_hyperframes(project: pathlib.Path, props: dict, timing: dict, out_raw: pathlib.Path,
                       target_mp4: pathlib.Path | None = None) -> tuple[bool, str | None, dict]:
    """Render a HyperFrames film via per-scene cached segments (`--start`/`--end`) and stitch into `out_raw`."""
    from tt_shorts import compose
    project = pathlib.Path(project).resolve()
    out_raw = pathlib.Path(out_raw).resolve()
    plan = plan_hyperframes(project, props, timing)
    seg_files = []
    for seg in plan["segments"]:
        dest = pathlib.Path(seg["path"])
        if not seg["cached"]:
            tmp = out_raw.parent / f"seg-{seg['index']:02d}-{seg['sha']}.mp4"
            start_s = f"{seg['start_frame'] / FPS:.6f}"
            end_s = f"{(seg['end_frame'] + 1) / FPS:.6f}"
            t0 = time.perf_counter()
            r = compose.hyperframes(
                [
                    "render", str(project),
                    "--output", str(tmp),
                    "--start", start_s,
                    "--end", end_s,
                    "--quality", compose.RENDER["quality"],
                    "--workers", compose.RENDER["workers"],
                    "--fps", compose.RENDER["fps"],
                    "--browser-gpu" if compose.RENDER["browser_gpu"] else "--no-browser-gpu",
                    "--strict", "--quiet",
                ],
                timeout=3600,
            )
            dt = time.perf_counter() - t0
            if r.returncode != 0 or not tmp.exists():
                err = (r.stderr or r.stdout or "")[-600:]
                return False, f"hyperframes render failed on {seg['id']} ({r.returncode}): {err}", plan
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp), str(dest))
            _write_segment_meta(seg, "hyperframes", dt)
        seg_files.append(dest)
    splice_mode = splice_segments(seg_files, plan["total_frames"], out_raw)
    manifest = {
        **plan,
        "splice_mode": splice_mode,
        "file": str(target_mp4.resolve()) if target_mp4 else str(out_raw),
    }
    if target_mp4 is not None:
        manifest_path(target_mp4).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return True, None, manifest


def frame_sha256_list(video_path: pathlib.Path) -> list[str]:
    """Return per-frame decoded SHA-256 digests (`ffmpeg -f framehash -hash sha256`) for `video_path`."""
    r = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(video_path),
            "-map", "0:v:0", "-f", "framehash", "-hash", "sha256", "-",
        ],
        capture_output=True, text=True, check=True,
    )
    digests = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 6:
            digests.append(parts[-1])
    return digests


def video_frame_dhashes(video_path: pathlib.Path, width: int = 1080, height: int = 1920) -> list[dict]:
    """Return per-frame `{"hash", "band"}` perceptual difference hashes (`golden.dhash`) for every frame in `video_path`."""
    from PIL import Image
    from tt_shorts import golden, probe
    c = probe.C
    box = (0, c["SCENE_TOP"], c["W"], c["SCENE_BOTTOM"])
    r = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(video_path),
            "-map", "0:v:0", "-vf", f"scale={width}:{height},format=gray",
            "-f", "rawvideo", "-",
        ],
        capture_output=True, check=True,
    )
    raw = r.stdout
    frame_bytes = width * height
    n_frames = len(raw) // frame_bytes
    out = []
    for i in range(n_frames):
        buf = raw[i * frame_bytes:(i + 1) * frame_bytes]
        im = Image.frombytes("L", (width, height), buf)
        g_full = im.resize((golden.SIZE + 1, golden.SIZE), Image.Resampling.LANCZOS)
        px_full = list(getattr(g_full, "get_flattened_data", g_full.getdata)())
        bits_full = 0
        for y in range(golden.SIZE):
            row = px_full[y * (golden.SIZE + 1):(y + 1) * (golden.SIZE + 1)]
            for x in range(golden.SIZE):
                bits_full = (bits_full << 1) | (1 if row[x] > row[x + 1] + golden.EPS else 0)
        g_band = im.crop(box).resize((golden.BAND_SIZE + 1, golden.BAND_SIZE), Image.Resampling.LANCZOS)
        px_band = list(getattr(g_band, "get_flattened_data", g_band.getdata)())
        bits_band = 0
        for y in range(golden.BAND_SIZE):
            row = px_band[y * (golden.BAND_SIZE + 1):(y + 1) * (golden.BAND_SIZE + 1)]
            for x in range(golden.BAND_SIZE):
                bits_band = (bits_band << 1) | (1 if row[x] > row[x + 1] + golden.EPS else 0)
        out.append({
            "hash": f"{bits_full:0{golden.SIZE * golden.SIZE // 4}x}",
            "band": f"{bits_band:0{golden.BAND_SIZE * golden.BAND_SIZE // 4}x}",
        })
    return out

