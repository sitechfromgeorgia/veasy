"""`engine plan`: a free storyboard of one story, before any voice is paid for (ROADMAP B2).

With the silent engine's estimated timings (speech.estimate_words, close to the Gemini pace) it builds the video's
props as a render would, then reports:
    scenes     per scene: its times, the narration words spoken in it, its caption pages, every text on screen with
               the seconds it needs (0.5 s + 0.3 s a word) and gets, and its reading load (motion_rules.py)
    variety    the picks the render would get (hook, motif, entrance, transition, music; inside the story's director's
               subsets), read from the variety history and NOT recorded: planning never uses up an option
    novelty    the novelty guard's view (variety.choose): the video's fingerprint, the closest of the brand's recent
               videos, the similarity (0-7) and distance, how many re-rolls it took, and a warning when none was far
               enough (also in "warnings")
    motion     the motion rules (motion_rules.py): warnings here; only unreadable text would hold the render
    probe      the layout probe of every scene's settled frame (probe.py)
    sheet      a contact sheet of those frames at half size (540x960 each), beside where the render will go:
               renders/<brand>/<day>/<ref>-<format>-<look>-<captions>.plan.jpg (store.plan_sheet_path)

    python -m tt_shorts.engine plan stories/24835.json [--look kinetic] [--director data] [--out sheet.jpg]

picks() is the variety part alone, for anything that needs a video's planned style without building it.
"""
import json
import pathlib
import shutil
import time

from tt_shorts import brand, meta, motion_rules, probe, props, speech, store, swipe, variety

HALF = (540, 960)
COLUMNS = 4
GAP = 12
LABEL = 44  # px under each frame for "scene · type · times"


def picks(story_path, look="auto", transition="auto", music="family", director=None, outro=swipe.DEFAULT_OUTRO):
    """The variety picks a render of this story would get now (after the novelty guard) -> {look, director, hook,
    motif, enter, transition, music, current, novelty}, without recording them (props.choose)."""
    story = brand.with_say(json.loads(pathlib.Path(story_path).read_text(encoding="utf-8")))
    variant = meta.variant_for(story.get("category", ""), brand.of(story)) if look in (None, "auto") else look
    st, chosen, _, _, nov = props.choose(story, variant, transition, music, director, outro=outro)
    did = chosen["id"] if chosen else None
    seq = [s["type"] for s in swipe.shown_scenes(story, outro)]
    return {"look": variant, "director": did, **{k: st[k] for k in st},
            "current": chosen["current"] if chosen else None, "novelty": novelty(nov, st, seq, did)}


def novelty(report, style, scenes, director=None):
    """The guard's report with the fingerprint it judged (variety.fingerprint), for showing."""
    fp = variety.fingerprint(style, scenes, director)
    return {**(report or {}), "fingerprint": {**fp, "scenes": list(fp["scenes"] or [])}}


def _caption_pages(p, row):
    a, b = row["from"] / speech.FPS, row["to"] / speech.FPS
    return sum(1 for pg in p["captions"].get("pages") or [] if a <= pg["start"] < b)


def _spoken(p, row):
    a, b = row["from"] / speech.FPS, row["to"] / speech.FPS
    return sum(1 for w in p["words"] if a <= w["start"] < b)


def scenes(p, rows):
    """The storyboard's rows: the motion timeline with the narration and the captions of each scene."""
    out = []
    for r in rows:
        said = _spoken(p, r)
        out.append({"scene": r["scene"], "type": r["type"], "start": round(r["from"] / speech.FPS, 2),
                    "end": round(r["to"] / speech.FPS, 2), "seconds": r["seconds"], "words": said,
                    "words_per_second": round(said / r["seconds"], 2) if r["seconds"] else None,
                    "caption_pages": _caption_pages(p, r), "load": motion_rules.load(r),
                    "texts": [{k: t[k] for k in ("text", "words", "need", "shown")} for t in r["texts"]]})
    return out


def sheet(files, rows, target):
    """A contact sheet: each still at half size, COLUMNS a row, its scene, type and times under it -> target."""
    from PIL import Image, ImageDraw, ImageFont
    n = len(files)
    cols = max(1, min(COLUMNS, n))
    lines = (n + cols - 1) // cols
    w, h = HALF
    im = Image.new("RGB", (cols * w + (cols + 1) * GAP, lines * (h + LABEL) + (lines + 1) * GAP), (24, 24, 24))
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default(size=28)
    except TypeError:  # an older Pillow
        font = ImageFont.load_default()
    for k, (f, r) in enumerate(zip(files, rows)):
        x, y = GAP + (k % cols) * (w + GAP), GAP + (k // cols) * (h + LABEL + GAP)
        with Image.open(f) as still:
            im.paste(still.convert("RGB").resize(HALF, Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 4, y + h + 8), f"{r['scene']} {r['type']}  {r['from'] / speech.FPS:.1f}-{r['to'] / speech.FPS:.1f}s",
                  fill=(230, 230, 230), font=font)
    target = pathlib.Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    im.save(target, quality=82) if target.suffix.lower() in (".jpg", ".jpeg") else im.save(target)
    return target


def run(story_path, fmt, look=None, director=None, out=None, with_probe=True):
    """The storyboard of one story in one resolved format (formats.get) -> dict with "problems" (what would hold the
    render: unreadable text, layout) and "warnings" (the other motion rules). Costs no voice and records nothing."""
    t0 = time.time()
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    try:
        work, p = props.build(str(story_path), look or fmt["look"], "silent", tone, speech.EDGE_VOICES["eka"],
                              fmt["platform"], caption_design=fmt["captions"], music=fmt["music"],
                              transition=fmt["transition"], outro=fmt["outro"], director=director,
                              sfx=fmt.get("sfx", "off"), theme=fmt.get("theme"))
    except (ValueError, RuntimeError) as e:  # an anchor not in the narration, a scene too short: no storyboard yet
        return {"story": str(pathlib.Path(story_path).resolve()), "problems": [f"timing: {e}"], "warnings": [],
                "took": round(time.time() - t0, 1)}
    motion = motion_rules.check(p)
    rows = motion["timeline"]
    st = p["style"]
    result = {"story": str(pathlib.Path(story_path).resolve()), "format": fmt["name"], "look": p["variant"],
              "theme": p["theme"],
              "director": st.get("director"), "seconds": round(p["durationInFrames"] / speech.FPS, 1),
              "variety": {**{k: st[k] for k in ("hook", "motif", "enter") if k in st}, "transition": p["transition"],
                          "music": p["music"], "current": st.get("current")},
              "novelty": novelty(p.get("novelty"), {**st, "transition": p["transition"], "music": p["music"]},
                                 [s["type"] for s in p["scenes"]], st.get("director")),
              "outro": p["outro"], "captions": {"design": fmt["captions"], "pages": len(p["captions"].get("pages") or [])},
              "scenes": scenes(p, rows), "cuts": motion["cuts"], "sfx": len(p.get("sfx") or []),
              "motion": {"holds": motion["holds"], "warnings": motion["warnings"]}}
    problems = list(motion["holds"])
    if with_probe:
        stills = work / "plan"
        shutil.rmtree(stills, ignore_errors=True)
        frames = probe.settled(p["scenes"])
        job = {"props": str(work / "props.json"), "public": str(work / "public"), "frames": frames,
               "out": str(stills), "name": "scene"}
        done = {}
        try:
            per, done = probe.run_jobs([job])
            judged = probe.judge(per[0], work / "public", frames)
        except probe.ProbeError as e:  # an unchecked layout is a problem, as in a render
            lines = [x for x in str(e).splitlines() if x.strip()] or ["no result"]
            judged = {"problems": [f"probe error: {lines[-1][:300]}"], "texts": 0, "files": []}
        shutil.rmtree(work / "probe-serve", ignore_errors=True)
        problems += judged["problems"]
        result["probe"] = {"problems": judged["problems"], "frames": frames, "texts": judged["texts"],
                           "bundle_built": done.get("built")}
        result["stills"] = judged["files"]
        if len(judged["files"]) == len(rows):
            target = pathlib.Path(out) if out else store.plan_sheet_path(store.render_path(
                brand.of(story)["name"], story["id"], fmt["name"], p["variant"], fmt["captions"]))
            if not out and p["theme"] != brand.of(story)["default_theme"]:  # beside the default theme's sheet
                target = target.with_name(target.name.replace(".plan.", f".{p['theme']}.plan."))
            result["sheet"] = str(sheet(judged["files"], rows, target).resolve())
    result["problems"] = problems
    result["warnings"] = motion["warnings"] + [w for w in [(p.get("novelty") or {}).get("warning")] if w] \
        + brand.theme_problems(brand.of(story, p["theme"]))  # a preview theme: shown here, refused by a render
    result["took"] = round(time.time() - t0, 1)
    return result
