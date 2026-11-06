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


def make(kind, seconds=6, seed=1, scale=1, spec=None, brands=None):
    """The `engine plate` answer: bake or hit the cache, tone every pack's line (cached beside the master)."""
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
