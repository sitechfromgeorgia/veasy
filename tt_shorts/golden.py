"""Golden stills: the check to run before merging a visual change (ROADMAP D13).

`engine selftest` renders the two fixture stories (stories/veasy-scenes.json: every new scene type;
stories/veasy-demo.json: a full news Short) in each look with one fixed style (no variety, no music, no voice),
takes each scene at its settled frame, and compares a perceptual hash of every still with tests/golden/<story>.<look>.json.
A scene whose hash moved more than THRESHOLD bits changed: look at its still and either fix the change or accept
it with `--update`, which rewrites the goldens (commit them with the change). The layout probe runs on the same
frames, so a selftest also fails on a layout problem.

    python -m tt_shorts.engine selftest            # ~30 s with the bundle cached; not part of the unit tests
    python -m tt_shorts.engine selftest --update   # after a deliberate visual change

Two difference hashes (dHash) per still: the whole frame on a 16x16 grid (the header, captions and footer) and the
scene band (y 248-1380) on a 32x32 grid, fine enough to see a 30 px label move. A neighbour pair counts as "left
brighter" only past a small margin, so flat canvas doesn't flip bits on anti-aliasing noise.
"""
import json
import pathlib
import time

from tt_shorts import brand, probe, props, speech, store

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "tests" / "golden"
STORIES = ("veasy-scenes", "veasy-demo")
SIZE = 16  # the frame's grid
BAND_SIZE = 32  # the scene band's grid
EPS = 2  # grey levels: a smaller difference between neighbours is "the same"
# bits that may differ before a scene counts as changed. Measured here: the same render repeated differs by 0; the
# cards' 30 px page count moved 44 px differs by 4-5 in the band (2-3 in the frame); a re-laid scene by 30-300.
# Another machine's Chrome may anti-alias a little differently: if every scene there differs by a bit or two,
# regenerate the goldens on that machine (--update) rather than raising these.
THRESHOLD = {"frame": 6, "band": 3}


def style_for(look):
    """The one style the goldens use: the look's own transition, the first option of every variety choice."""
    return {"hook": "stack", "motif": "grid", "enter": "rise", "transition": props.DEFAULT_TRANSITION[look],
            "music": None}


def dhash(path, size=SIZE, box=None, eps=EPS):
    """Difference hash of an image (or its `box` crop): grey, (size+1) x size, one bit per neighbour pair
    (left brighter by more than eps) -> hex."""
    from PIL import Image
    with Image.open(path) as im:
        g = im.convert("L")
        if box:
            g = g.crop(box)
        g = g.resize((size + 1, size), Image.Resampling.LANCZOS)
        px = list(getattr(g, "get_flattened_data", g.getdata)())
    bits = 0
    for y in range(size):
        row = px[y * (size + 1):(y + 1) * (size + 1)]
        for x in range(size):
            bits = (bits << 1) | (1 if row[x] > row[x + 1] + eps else 0)
    return f"{bits:0{size * size // 4}x}"


def hashes(path):
    """{"hash": the frame's, "band": the scene band's} of one still."""
    c = probe.C
    return {"hash": dhash(path), "band": dhash(path, BAND_SIZE, (0, c["SCENE_TOP"], c["W"], c["SCENE_BOTTOM"]))}


def distance(a, b):
    """Bits that differ between two hashes of the same length."""
    if len(a) != len(b):
        return len(a) * 4
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def golden_path(story, look):
    return DIR / f"{story}.{look}.json"


def compare(old, new, threshold=None):
    """Golden scenes vs this run's: [{scene, type, distance: {frame, band}}] of the scenes that changed (a
    different scene list counts as every scene changed)."""
    threshold = threshold or THRESHOLD
    if [s["type"] for s in old] != [s["type"] for s in new]:
        return [{"scene": s["scene"], "type": s["type"], "distance": None} for s in new]
    out = []
    for o, n in zip(old, new):
        d = {"frame": distance(o["hash"], n["hash"]), "band": distance(o.get("band", ""), n.get("band", ""))}
        if d["frame"] > threshold["frame"] or d["band"] > threshold["band"]:
            out.append({"scene": n["scene"], "type": n["type"], "distance": d})
    return out


def selftest(update=False, stories=STORIES, looks=brand.LOOKS, threshold=None):
    """Render the fixtures' settled frames in each look, probe them and compare their hashes with the goldens."""
    threshold = threshold or THRESHOLD
    t0 = time.time()
    stills = store.work_dir("selftest")
    jobs, meta = [], []
    for name in stories:
        path = ROOT / "stories" / f"{name}.json"
        for look in looks:
            work, p = props.build(str(path), look, "silent", None, speech.EDGE_VOICES["eka"], "shorts",
                                  caption_design="page", music="off", transition=props.DEFAULT_TRANSITION[look],
                                  style=style_for(look))
            frames = probe.settled(p["scenes"])
            jobs.append({"props": str(work / "props.json"), "public": str(work / "public"), "frames": frames,
                         "out": str(stills), "name": f"{name}-{look}"})
            meta.append((name, look, work, p, frames))
    per, done = probe.run_jobs(jobs)
    changed, new, updated, layout, same = [], [], [], [], 0
    for (name, look, work, p, frames), rows in zip(meta, per):
        r = probe.judge(rows, work / "public", frames, prefix=f"{name} {look}: ")
        layout += r["problems"]
        files = {x["frame"]: x["file"] for x in rows if x.get("file")}
        scenes = [{"scene": i, "type": s["type"], "frame": f, **hashes(files[f])}
                  for i, (s, f) in enumerate(zip(p["scenes"], frames)) if f in files]
        if len(scenes) != len(frames):
            continue  # the probe already reported the frames that did not render
        gp = golden_path(name, look)
        if update:
            DIR.mkdir(parents=True, exist_ok=True)
            gp.write_text(json.dumps({"story": name, "look": look, "style": style_for(look), "hash": f"dhash{SIZE}+band{BAND_SIZE}",
                                      "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            updated.append(str(gp.relative_to(ROOT)))
            continue
        if not gp.exists():
            new.append(f"{name}.{look}")
            continue
        diff = compare(json.loads(gp.read_text(encoding="utf-8"))["scenes"], scenes, threshold)
        same += len(scenes) - len(diff)
        changed += [{"story": name, "look": look, **d, "frame": frames[d["scene"]],
                     "still": files[frames[d["scene"]]]} for d in diff]
    problems = [f"golden: {c['story']} {c['look']} scene {c['scene']} ({c['type']}) changed"
                + (f" ({c['distance']['frame']} bits in the frame, {c['distance']['band']} in the scene band)"
                   if c["distance"] else ": the scene list differs")
                for c in changed]
    problems += [f"golden: no golden for {n} (run selftest --update)" for n in new]
    return {"updated": updated, "changed": changed, "unchanged": same, "missing": new, "layout": layout,
            "stills": str(stills), "threshold": threshold, "seconds": round(time.time() - t0, 1),
            "bundle_built": done.get("built"), "problems": problems + layout}
