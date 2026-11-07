"""Plates: grey clips baked once (plates/run.mjs), toned into a pack's colours, cached by content, used behind scenes.

    engine plate <kind> --seconds n --seed n   bake (or answer from the cache) and tone for every pack and theme
    engine plate list | check                  the library; the kinds and their files

A plate is a function of (the kind's files, spec, seed, seconds, scale): run.mjs says its 16-hex hash (`--hash`), the
master lives in $VEASY_HOME/cache/plates/<hash>/ (store.plate_dir). The master is grey. Toning is one ffmpeg pass
that maps black to the pack's canvas and white to its ink along the straight line between them, so one master serves
every pack and theme and no palette can leak: the clip holds colours of that line only (`line_distance`).

Banding: the grey frame is debanded and dithered in one channel (gradfun) BEFORE the colour is assigned, so the dither
moves a pixel along the line and never off it (dither after the mapping would add a different noise to each channel).

A queue job never bakes (`library` and `pick` only read); a missing plate is a warning, never a lost video. A plate is
refused for `news`, for the crime family and for words about deaths (`refusal`).
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess

from tt_shorts import store

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLATES = ROOT / "plates"
FPS = 30
WIDTH, HEIGHT = 1080, 1920
REFUSED_PROGRAMS = ("news",)
REFUSED_FAMILIES = ("crime",)
# Georgian stems and English words of deaths, crime and incidents: a plate behind such a story would decorate it.
REFUSED_WORDS = ("დაიღუპ", "გარდაიცვალ", "გარდაცვლ", "მოკლეს", "მკვლელობ", "დახვრიტ", "დაჭრ", "ჯარიმ", "დააკავ",
                 "ავარი", "კატასტროფ", "ხანძარ", "აფეთქებ", "თავდასხმ", "კრიმინალ",
                 "killed", "dead", "death", "murder", "shot", "crash", "fire", "explosion", "attack", "arrest")
LICENCE = "own"  # drawn by Veasy's own code (three.js, MIT, is the only library): nothing to credit


class PlateError(ValueError):
    pass


def node():
    return shutil.which("node") or shutil.which("node.exe")


def ffmpeg():
    return os.environ.get("VEASY_FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


# ---------------------------------------------------------------- kinds and refusals


def kinds():
    """The kinds on disk: plates/<kind>/index.html."""
    return sorted(p.parent.name for p in PLATES.glob("*/index.html") if p.parent.name not in ("lib", "node_modules"))


def refusal(program=None, family=None, text=""):
    """Why a plate may not sit behind this story, or None. Three arguments, each enough: the program (news), the
    family (crime) and any words (the narration or headline) about a death or an incident."""
    if program in REFUSED_PROGRAMS:
        return f"program {program!r}: a plate is a made picture and news carries none (N1, N13)"
    if family in REFUSED_FAMILIES:
        return f"family {family!r}: no plates for crime, incidents or deaths (N10, N13)"
    low = (text or "").lower()
    hit = next((w for w in REFUSED_WORDS if w in low), None)
    if hit:
        return f"the text says „{hit}…“: no plates for crime, incidents or deaths (N10, N13)"
    return None


# ---------------------------------------------------------------- the content hash and the bake


def _run_args(kind, seconds, seed, scale, spec):
    if kind not in kinds():
        raise PlateError(f"no plate kind {kind!r}; known: {', '.join(kinds())}")
    a = [node(), str(PLATES / "run.mjs"), kind, "--seconds", str(seconds), "--seed", str(seed), "--scale", str(scale)]
    return a + (["--spec", str(spec)] if spec else [])


def hash_of(kind, seconds=6, seed=1, scale=1, spec=None):
    """The plate's hash, as run.mjs says it (one definition: no second implementation to drift)."""
    if not node():
        raise PlateError("node is not installed: a plate is baked by plates/run.mjs")
    r = subprocess.run(_run_args(kind, seconds, seed, scale, spec) + ["--hash"], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    h = r.stdout.strip()
    if r.returncode or not re.fullmatch(r"[0-9a-f]{16}", h):
        raise PlateError(f"plate hash failed: {(r.stderr or r.stdout).strip()[-300:]}")
    return h


def cached(h):
    """The manifest of a baked plate, or None (never a partial bake: plate.json is written last)."""
    f = store.home() / "cache" / "plates" / h / "plate.json"
    if not f.is_file() or not (f.parent / "plate.mp4").is_file():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def bake(kind, seconds=6, seed=1, scale=1, spec=None):
    """(manifest, from_cache). Bakes only on a miss, into a temporary folder renamed whole on success."""
    h = hash_of(kind, seconds, seed, scale, spec)
    hit = cached(h)
    if hit:
        return hit, True
    final = store.plate_dir(h)
    tmp = final.with_name(h + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    r = subprocess.run(_run_args(kind, seconds, seed, scale, spec) + ["--out", str(tmp)], capture_output=True,
                       text=True, encoding="utf-8", timeout=1800)
    if r.returncode:
        shutil.rmtree(tmp, ignore_errors=True)
        raise PlateError(f"bake of {kind} failed: {r.stderr.strip()[-400:]}")
    for f in tmp.iterdir():
        os.replace(f, final / f.name)
    shutil.rmtree(tmp, ignore_errors=True)
    return json.loads((final / "plate.json").read_text(encoding="utf-8")), False


# ---------------------------------------------------------------- the tone line


def hex_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def line_point(canvas, ink, g):
    """The colour of grey level g (0-255) on the line canvas -> ink, rounded as the filter rounds."""
    return tuple(round(a + (b - a) * g / 255) for a, b in zip(canvas, ink))


def tone_filter(canvas, ink):
    """The ffmpeg -vf that maps a grey clip onto the line: debanded and dithered in grey, then one lookup per channel
    (lutrgb evaluates its expression once per level: 256 points, none off the line)."""
    ch = [f"{k}='clip(round({a}+val*({b}-{a})/255),0,255)'" for k, a, b in zip("rgb", canvas, ink)]
    return ("format=gray,gradfun=strength=1.2:radius=16,format=rgb24," + f"lutrgb={':'.join(ch)}," +
            "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p")


TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def tone_clip(master, out, canvas, ink):
    """Tone the grey master into out (mp4). Same filter, same input: same bytes."""
    r = subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(master), "-vf", tone_filter(canvas, ink),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-g", "15", "-threads", "1",
                        *TAGS, "-an", "-movflags", "+faststart", str(out)], capture_output=True, text=True)
    if r.returncode:
        raise PlateError(f"tone failed: {r.stderr.strip()[-300:]}")
    return out


def decode_frame(clip, index=None, t=None):
    """One frame of a clip as (width, height, RGB bytes), decoded as a viewer's player does (bt709, tv range)."""
    seek = ["-ss", str(t)] if t is not None else []
    r = subprocess.run([ffmpeg(), "-loglevel", "error", *seek, "-i", str(clip), "-frames:v", "1",
                        "-vf", "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24",
                        "-f", "rawvideo", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        raise PlateError(f"could not decode {clip}: {r.stderr.decode(errors='replace')[-200:]}")
    probe = subprocess.run([ffmpeg(), "-i", str(clip)], capture_output=True, text=True).stderr
    m = re.search(r"(\d{3,5})x(\d{3,5})", probe)
    return int(m.group(1)), int(m.group(2)), r.stdout


def line_stats(rgb, canvas, ink):
    """How far a frame's pixels lie from the segment canvas -> ink (Euclidean, 0-255 units): {max, p999, mean,
    colours}. The mapped frame before the codec has max <= sqrt(3)/2 (the rounding of one lookup); a decoded clip adds
    the codec's own noise (x264 and 4:2:0), so its max is a few units and its p999 about one."""
    import numpy as np
    px = np.frombuffer(rgb, dtype=np.uint8).reshape(-1, 3).astype(np.float64)
    c0 = np.array(canvas, dtype=np.float64)
    d = np.array(ink, dtype=np.float64) - c0
    t = np.clip(((px - c0) @ d) / max(float(d @ d), 1.0), 0.0, 1.0)
    dist = np.linalg.norm(px - (c0 + t[:, None] * d), axis=1)
    return {"max": float(dist.max()), "p999": float(np.percentile(dist, 99.9)), "mean": float(dist.mean()),
            "colours": int(len(np.unique(px.astype(np.uint8), axis=0)))}


# ---------------------------------------------------------------- one call: bake, tone for every pack and theme


def palettes(brands=None):
    """{(canvas, ink): [pack/theme, ...]}: the distinct colour lines of the shipped packs (and their light previews)."""
    from tt_shorts import brand as packs
    lines = {}
    for name in brands or packs.names():
        b = packs.load(name)
        for theme in packs.theme_names(b):
            c = packs.themed(b, theme)["colors"]
            lines.setdefault((c["canvas"].upper(), c["ink"].upper()), []).append(f"{name}/{theme}")
    return lines


def clip_name(canvas, ink):
    return f"tone-{canvas.lstrip('#').lower()}-{ink.lstrip('#').lower()}.mp4"


def _fast_key(kind, seconds, seed, scale, spec, brands):
    """What a finished answer is a function of, read from file stats alone (no node, no brand loading): the kind's files,
    run.mjs, the packs' brand.json files, the spec's contents and the numbers. None when something can't be read."""
    try:
        files = [PLATES / "run.mjs", *sorted((PLATES / kind).rglob("*")), *sorted((ROOT / "brands").glob("*/brand.json"))]
        sig = [[str(f.relative_to(ROOT)), f.stat().st_size, f.stat().st_mtime_ns] for f in files if f.is_file()]
        body = pathlib.Path(spec).read_text(encoding="utf-8") if spec else ""
        return hashlib.sha256(json.dumps([kind, seconds, seed, scale, body, sig, brands], sort_keys=True).encode()).hexdigest()
    except OSError:
        return None


def _index_path():
    return store.home() / "cache" / "plates" / "index.json"


def make(kind, seconds=6, seed=1, scale=1, spec=None, brands=None):
    """The `engine plate` answer: bake or hit the cache, tone every pack's line (cached beside the master). A repeat
    call is answered from an index of finished answers keyed by file stats: no node, no brand loading (a few ms)."""
    key = _fast_key(kind, seconds, seed, scale, spec, brands)
    try:
        index = json.loads(_index_path().read_text(encoding="utf-8")) if key else {}
    except (OSError, ValueError):
        index = {}
    hit = index.get(key)
    if hit and cached(hit["hash"]) and all((store.home() / c).is_file() for t in hit["clips"].values() for c in t.values()):
        return {**hit, "cached": True}
    answer = _make(kind, seconds, seed, scale, spec, brands)
    if key:
        index[key] = answer
        try:
            _index_path().write_text(json.dumps(index), encoding="utf-8")
        except OSError:
            pass
    return answer


def _make(kind, seconds, seed, scale, spec, brands):
    manifest, hit = bake(kind, seconds, seed, scale, spec)
    d = store.plate_dir(manifest["hash"])
    clips = {}
    for (canvas, ink), who in palettes(brands).items():
        f = d / clip_name(canvas, ink)
        if not f.is_file():
            tmp = f.with_suffix(".tmp.mp4")
            tone_clip(d / "plate.mp4", tmp, hex_rgb(canvas), hex_rgb(ink))
            os.replace(tmp, f)
        for w in who:
            pack, theme = w.split("/")
            clips.setdefault(pack, {})[theme] = str(f.relative_to(store.home()).as_posix())
    return {**manifest, "cached": hit, "master": f"cache/plates/{manifest['hash']}/plate.mp4",
            "poster": f"cache/plates/{manifest['hash']}/poster.png", "clips": clips,
            "anchors_file": (f"cache/plates/{manifest['hash']}/anchors.json" if manifest.get("anchors") else None)}


def library():
    """Every baked plate: [manifest + path], oldest first. Reads only."""
    out = []
    for f in sorted((store.home() / "cache" / "plates").glob("*/plate.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        out.append({**m, "master": f"cache/plates/{f.parent.name}/plate.mp4", "mtime": f.stat().st_mtime})
    return sorted(out, key=lambda m: m["mtime"])


# ---------------------------------------------------------------- the command (engine plate, or python -m tt_shorts.plates)


def command(a):
    """`plate <kind|list|check>` -> (JSON object, exit code). a: kind, seconds, seed, scale, spec, brand, program, family,
    text (the engine's argparse namespace, or this module's)."""
    if a.kind == "list":
        return {"plates": [{k: m[k] for k in ("kind", "hash", "seed", "seconds", "ms_per_frame", "master")}
                           for m in library()], "kinds": kinds()}, 0
    if a.kind == "check":
        problems = [x for k in kinds() for x in check_kind(k)]
        return {"kinds": kinds(), "problems": problems}, 1 if problems else 0
    why = refusal(program=a.program, family=a.family, text=a.text or "")
    if why:
        return {"kind": a.kind, "refused": why, "problems": [why]}, 1
    problems = check_kind(a.kind)
    if problems:
        return {"kind": a.kind, "problems": problems}, 1
    try:
        return make(a.kind, a.seconds, a.seed, a.scale, a.spec, [a.brand] if a.brand else None), 0
    except PlateError as e:
        return {"kind": a.kind, "problems": [str(e)]}, 1


def main(argv=None):
    """The same command without the engine's imports (a cache answer in well under a second)."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m tt_shorts.plates")
    ap.add_argument("kind")
    ap.add_argument("--seconds", type=float, default=6)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--scale", type=float, default=1)
    ap.add_argument("--spec")
    ap.add_argument("--brand")
    ap.add_argument("--program")
    ap.add_argument("--family")
    ap.add_argument("--text")
    obj, code = command(ap.parse_args(argv))
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1) + chr(10))
    return code



# ---------------------------------------------------------------- what `engine options` and `engine plate check` say

# What a kind's own files may never contain: a clock, unseeded random, text drawn into pixels, a network address.
LINT = (("Math.random", "unseeded random: use plates/lib/seeded.mjs"),
        ("Date.now", "a clock: a frame is a function of t"), ("new Date", "a clock: a frame is a function of t"),
        ("performance.now", "a clock: a frame is a function of t"),
        ("fillText", "text in a plate: words stay in the DOM"), ("strokeText", "text in a plate: words stay in the DOM"),
        ("http://", "a network address: a plate reads local files only"),
        ("https://", "a network address: a plate reads local files only"))


def check_kind(kind):
    """Problems of one kind's folder (the contract in plates/README.md that a program can read): [] when clean."""
    d = PLATES / kind
    if not (d / "index.html").is_file():
        return [f"{kind}: no index.html"]
    out = []
    for f in sorted(d.rglob("*")):
        if f.suffix not in (".html", ".js", ".mjs") or not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for needle, why in LINT:
            if needle in text:
                out.append(f"{kind}/{f.relative_to(d).as_posix()}: {needle}: {why}")
    if "window.setup" not in (d / "index.html").read_text(encoding="utf-8") and not any(
            "window.setup" in f.read_text(encoding="utf-8", errors="replace") for f in d.rglob("*.*")
            if f.suffix in (".js", ".mjs") and f.is_file()):
        out.append(f"{kind}: no window.setup(spec, ctx) / window.step(t)")
    return out


def options():
    """The `plates` section of `engine options`: how to ask, what comes back, what is refused, what is on the shelf."""
    return {"about": "grey clips baked once, toned into the pack's canvas and ink, played behind a scene: one line, "
                     "`engine plate <kind> --seconds n --seed n`; a second call answers from the cache",
            "kinds": kinds(), "command": "python -m tt_shorts.engine plate <kind|list|check> [--seconds 6] [--seed 1]",
            "tool": "veasy_plate", "skill": "veasy:plates", "fps": FPS, "size": [WIDTH, HEIGHT],
            "refused": {"programs": list(REFUSED_PROGRAMS), "families": list(REFUSED_FAMILIES),
                        "words": "deaths, crime and incidents (REFUSED_WORDS)"},
            "queue": "a queue job never bakes: it picks among baked plates (variety) and warns when none is there",
            "baked": len(library())}


# ---------------------------------------------------------------- the story's ledger


def sha_of(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def ledger_entry(manifest):
    """A story's `assets` entry for one plate: kind, hash, seed, licence, the master's sha. Code-owned."""
    h = manifest["hash"]
    master = store.home() / "cache" / "plates" / h / "plate.mp4"
    return {"id": f"plate-{h}", "kind": "plate", "provider": "plates", "url": f"veasy:plates/{manifest['kind']}",
            "licence": LICENCE, "author": "", "title": manifest["kind"], "fetched": store.today(),
            "sha": sha_of(master) if master.is_file() else "", "file": f"cache/plates/{h}/plate.mp4",
            "hash": h, "seed": manifest["seed"]}


def entry_problems(e):
    """A plate's ledger entry (assets.problems calls this for kind "plate"): [] when well formed."""
    out = []
    h = str(e.get("hash"))
    if not re.fullmatch(r"[0-9a-f]{16}", h) or e.get("id") != f"plate-{h}":
        out.append("a plate's id is plate-<its 16-hex hash>")
    if e.get("provider") != "plates" or e.get("licence") != LICENCE:
        out.append(f"a plate is provider plates, licence {LICENCE} (drawn by Veasy's own code)")
    if not str(e.get("url", "")).startswith("veasy:plates/"):
        out.append("url is veasy:plates/<kind>")
    if e.get("file") != f"cache/plates/{h}/plate.mp4":
        out.append(f"file is cache/plates/{h}/plate.mp4")
    if not re.fullmatch(r"[0-9a-f]{64}", str(e.get("sha"))):
        out.append("sha is the master's sha256")
    if not isinstance(e.get("seed"), int):
        out.append("seed is the integer the plate was baked with")
    return out


# ---------------------------------------------------------------- the story: refusals, the pick, the props


def plate_scenes(story):
    return [(i, s) for i, s in enumerate(story.get("scenes") or []) if isinstance(s, dict) and s.get("type") == "plate"]


def story_problems(story):
    """Checks every story with a plate scene passes (engine.structure_problems): the three refusals (news, crime family,
    deaths and incidents in the words) and the shape of the scene's code-owned `plate` field."""
    scenes = plate_scenes(story)
    if not scenes:
        return []
    from tt_shorts import brand, meta, news_check, programs
    out = []
    try:
        pack = brand.of(story)
    except brand.BrandError:
        pack = brand.load()
    program = programs.name_of(story)
    text = f"{story.get('narration', '')} {news_check.screen_text(story)}"
    why = refusal(program=program, family=meta.family(story.get("category", ""), pack), text=text) or \
        news_check.no_pictograms(story)
    if why:
        out.append(f"scene {scenes[0][0]} (plate): refused, {why}")
    ids = {e.get("id") for e in story.get("assets") or [] if isinstance(e, dict) and e.get("kind") == "plate"}
    for i, s in scenes:
        p = s.get("plate")
        if p is None:
            continue
        from tt_shorts import variety
        if not isinstance(p, dict) or set(p) - {"asset", "layout"} or p.get("layout") not in (None, *variety.PLATE_LAYOUTS):
            out.append(f"scene {i} (plate): plate is code's: {{\"asset\": <ledger id>, \"layout\": top|mid|low}}")
        elif p.get("asset") not in ids:
            out.append(f"scene {i} (plate): plate {p.get('asset')} is not in the story's assets ledger")
    return out


CARD_Y = {"top": (272, 700), "mid": (600, 1030), "low": (940, 1360)}  # page y a card of each layout may cover


def free_layouts(tracks):
    """The layouts whose card leaves the plate's accent dot uncovered (a dot under its card is a dot nobody sees); all of
    them for a plate with no `dot` anchor, and all when none is free."""
    ys = [p[1] for p in (tracks or {}).get("dot") or []]
    if not ys:
        return list(CARD_Y)
    lo, hi = min(ys) - 60, max(ys) + 60
    return [k for k, (a, b) in CARD_Y.items() if hi < a or lo > b] or list(CARD_Y)


def resolve(story, b=None):
    """Give every plate scene without one a baked plate from the shelf, and its ledger entry -> (story, report).
    Reads the library only: a queue job never bakes. An empty shelf, or a refused story, is a warning in the report and
    the scene stays on the plain canvas: never a lost film. Picks are recorded (variety.record_plate)."""
    from tt_shorts import brand, variety
    story = json.loads(json.dumps(story))
    report = {"plates": {}, "warnings": []}
    todo = [(i, s) for i, s in plate_scenes(story) if not (s.get("plate") or {}).get("asset")]
    if not todo:
        return story, report
    pack = b or brand.of(story)
    problems = story_problems({**story, "scenes": [{**s, "plate": None} for s in story["scenes"]]})
    if problems:
        report["warnings"] += problems
        return story, report
    shelf = {m["hash"]: m for m in library()}
    ledger = [e for e in story.get("assets") or [] if isinstance(e, dict)]
    have = {e["id"] for e in ledger}
    for i, s in todo:
        h = variety.pick_plate(pack["name"], story.get("id"), sorted(shelf))
        if not h:
            report["warnings"].append(f"scene {i} (plate): no baked plate on the shelf (engine plate example): the scene "
                                      "is drawn on the plain canvas")
            continue
        layout = variety.pick_plate_layout(pack["name"], story.get("id"), i, free_layouts(tracks_of(h)))
        e = ledger_entry(shelf[h])
        if e["id"] not in have:
            ledger.append(e)
            have.add(e["id"])
        s["plate"] = {"asset": e["id"], "layout": layout}
        variety.record_plate(pack["name"], story.get("id"), i, h, layout)
        report["plates"][i] = {"asset": e["id"], "layout": layout}
    if ledger:
        story["assets"] = ledger
    return story, report


def resolve_file(path):
    """resolve() on a story file, in place only when something changed -> the report."""
    path = pathlib.Path(path)
    story = json.loads(path.read_text(encoding="utf-8"))
    new, report = resolve(story)
    if new != story:
        path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def tracks_of(hash16):
    """The anchors a plate wrote ({name: [[x, y] per frame]}, page pixels at 30 fps), or {}."""
    f = store.home() / "cache" / "plates" / hash16 / "anchors.json"
    return json.loads(f.read_text(encoding="utf-8")).get("tracks", {}) if f.is_file() else {}


def for_props(story, b, public, flat=False):
    """Copy each plate scene's toned clip into public/plates/ -> {asset id: {src, frames, tracks}} (props.py). The clip
    is toned for the applied theme's canvas and ink (cached beside the master; toning is seconds, never a bake)."""
    ledger = {e["id"]: e for e in story.get("assets") or [] if isinstance(e, dict) and e.get("kind") == "plate"}
    out = {}
    for _, s in plate_scenes(story):
        aid = (s.get("plate") or {}).get("asset")
        if not aid or aid in out or aid not in ledger:
            continue
        d = store.home() / "cache" / "plates" / ledger[aid]["hash"]
        manifest = cached(ledger[aid]["hash"])
        if not manifest:
            continue  # gc took it: the scene falls back to the plain canvas (a warning in plan, never a lost film)
        canvas, ink = b["colors"]["canvas"].upper(), b["colors"]["ink"].upper()
        clip = d / clip_name(canvas, ink)
        if not clip.is_file():
            tone_clip(d / "plate.mp4", clip, hex_rgb(canvas), hex_rgb(ink))
        dest = pathlib.Path(public) / "plates" / (f"{aid}.mp4" if flat else f"{aid}-{clip.stem}.mp4")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(clip, dest)
        tracks = tracks_of(ledger[aid]["hash"])
        out[aid] = {"src": f"plates/{dest.name}", "frames": manifest["frames"], "tracks": tracks}
    return out

if __name__ == "__main__":
    raise SystemExit(main())
