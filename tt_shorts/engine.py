"""Veasy's engine: one entry point for people and agents, for every brand pack (brands/, brand.py).

Every command prints JSON on stdout (human notes go to stderr), so an agent can call it and read the result.

  python -m tt_shorts.engine options [--brand sitech]        # every choice the engine offers (brands, looks, captions,
                                                             # voices, music, formats, scene types and their fields)
  python -m tt_shorts.engine check  stories/24725.json [--sources articles.json]
                                                             # all checks a story must pass before rendering
  python -m tt_shorts.engine render stories/24725.json --format news [--look kinetic] [--captions roll]
                                    [--voice warm] [--music off] [--engine gemini|edge|silent] [--out out/x.mp4]
  python -m tt_shorts.engine still  stories/24725.json --frames 60,300 [same choices as render]
  python -m tt_shorts.engine qa     out/24725.mp4 [--format news]   # length, size, loudness + a contact sheet
  python -m tt_shorts.engine write  --source tbilisi-today --ref 24725 [--brand tbilisi-today] [--out x.json]
                                                             # a source's story -> a checked story JSON
  python -m tt_shorts.engine write  --program law --source ordo --ref constitution:17   # a program (programs.py):
                                                             # explainer, law, blog... from url, pdf, ordo, sitech
  python -m tt_shorts.engine queue  add --ref 24725 [--brand sitech] [--format news] | list | run [--max 5]
                                    | show <id> | retry <id> | cancel <id>          # the job queue (queue.py)
  python -m tt_shorts.engine voices [--story stories/24835.json] [--only warm,clear]   # tone samples by ear
  python -m tt_shorts.engine gc     [--dry-run]               # delete scratch, old renders, voices, logs (store.py)
  python -m tt_shorts.engine doctor                          # is this machine ready to render?

Where things are kept and what they are called: store.py ($VEASY_HOME). Brands: brand.py (brands/<name>/).

Exit status: 0 when the command did what it says, 1 when a check or QA found problems, 2 on a usage error.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

from tt_shorts import brand as packs
from tt_shorts import captions, formats, ka_check, kaeasy, meta, news_check, programs, props, speech, store, variety, voices

ROOT = speech.ROOT
FPS = speech.FPS

# The scene vocabulary: type -> (required fields, optional fields, what it shows). remotion/src/scenes draws them.
SCENES = {
    "hook": (["lines"], ["kicker"], "the opening: 2-4 short lines that say what happened"),
    "stat": (["value", "label"], ["kicker", "headline", "prefix", "suffix"], "one number from the articles, counted up"),
    "timeline": (["start", "end"], ["kicker", "headline", "big", "label"], "from-to times or dates stated in the articles"),
    "where": (["place"], ["kicker", "headline", "sub"], "a place, with a pin"),
    "who": (["items"], ["kicker", "headline"], "1-3 people or bodies: items [{name, role}]"),
    "points": (["items"], ["kicker", "headline"], "2-3 short points: items [\"...\"]"),
    "quote": (["text", "by"], ["kicker", "headline", "via"], "a verbatim quote with its speaker"),
    "sources": ([], ["kicker", "headline"], "the outlets that covered it (from the data, never written)"),
    "draw": (["svg"], ["kicker", "headline", "label"],
             "a line drawing of what the story is about, drawn by the writer (art.GUIDE); it builds up stroke by stroke"),
    "pair": (["items"], ["kicker", "headline", "between"],
             "two sides side by side: items [{title, sub}] x2; between: a short word on the divider"),
    "steps": (["items"], ["kicker", "headline"], "2-4 steps in order, joined by drawn arrows: items [\"...\"]"),
    "bars": (["items"], ["kicker", "headline", "unit"],
             "2-5 values from the articles as growing bars: items [{label, value}], one unit"),
    "trend": (["items"], ["kicker", "headline", "unit", "label"],
              "3-8 values over time from the articles, a line that draws itself: items [{label, value}]"),
    "change": (["before", "after"], ["kicker", "headline", "unit", "label"],
               "one value then and now from the articles: before {label, value}, after {label, value}"),
    "end": ([], [], "the end card: logo, QR to the story page, the call to action"),
}
# Shapes the new scenes must have (counts and numbers); the older ones are checked by their required fields.
COUNTS = {"pair": (2, 2), "steps": (2, 4), "bars": (2, 5), "trend": (3, 8), "who": (1, 3), "points": (2, 3)}
STORY_KEYS = ("id", "category", "date", "narration", "scenes")


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    return code


def note(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------- options


def options(brand_name=None):
    every = formats.load_all()
    b = packs.load(brand_name)
    presets = voices.all_presets(b)
    return {
        "brand": b["name"],
        "brands": {n: packs.summary(packs.load(n)) for n in packs.names()},
        "looks": {"auto": "by the story's category", **{v: d for v, d in (
            ("editorial", "calm, grid, rising type: hard news"),
            ("kinetic", "giant type, hard cuts, inverted blocks: light news"),
            ("cards", "every scene a site-style story card: service news"))}},
        "look_by_family": b["look_by_family"],
        "variety": {"about": "each video's own hook layout, background motif, entrance, transition (when auto) and music "
                             "loop: the least used lately for the brand (tt_shorts/variety.py); never the palette",
                    **variety.OPTIONS, "transitions_by_look": variety.TRANSITIONS},
        "transitions": {"auto": "varied per video among the ones that suit the look (variety.TRANSITIONS)",
                        "cut": "a plain cut, the old scene just ends", "line": "an ink line with the dot sweeps across",
                        "panel": "an ink panel wipes through", "wipe": "the new scene is revealed left to right",
                        "slide": "a short slide and fade", "push": "the old scene leaves left, the new one comes from the right",
                        "dot": "an iris opens from the header's progress dot"},
        "captions": {"page": "a fixed two-line block; words light up as spoken (most stable)",
                     "roll": "a three-line teleprompter that scrolls continuously"},
        "voices": {name: {"label": p["label"], "voice": p["voice"], "approved": name in voices.APPROVED,
                          **({"brand": b["name"]} if name in (b.get("voices") or {}) else {})}
                   for name, p in presets.items()},
        "voice_by_family": b["voice_by_family"],
        "music": ["family", "off", *meta.FAMILIES],
        "engines": {"gemini": "production voice (GEMINI_API_KEY + the alignment venv)",
                    "edge": "free preview stand-in (robotic; timing only)", "silent": "music and captions only"},
        "formats": every,
        "programs": {n: programs.summary(p) for n, p in programs.load_all().items()},
        "sources": _sources_about(),
        "scenes": {t: {"required": r, "optional": o, "shows": d} for t, (r, o, d) in SCENES.items()},
        "categories": {c: {"label": meta.category_label(c, b), "family": meta.family(c, b),
                           "look": meta.variant_for(c, b), "voice": b["voice_by_family"][meta.family(c, b)]}
                       for c in b["categories"]},
    }


def _sources_about():
    from tt_shorts import sources
    return dict(sources.ABOUT)


# ---------------------------------------------------------------- check


def structure_problems(story):
    p = []
    for k in STORY_KEYS:
        if k not in story:
            p.append(f"story: missing {k!r}")
    if story.get("brand") and story["brand"] not in packs.names():
        p.append(f"story: unknown brand {story['brand']!r} (known: {', '.join(packs.names())})")
    scenes = story.get("scenes") or []
    if not scenes or scenes[0].get("type") != "hook":
        p.append("story: the first scene must be a hook")
    for i, s in enumerate(scenes):
        t = s.get("type")
        if t not in SCENES:
            p.append(f"scene {i}: unknown type {t!r} (known: {', '.join(SCENES)})")
            continue
        if not s.get("at"):
            p.append(f"scene {i} ({t}): missing 'at' (the first narration words of the scene)")
        for field in SCENES[t][0]:
            if s.get(field) in (None, "", []):
                p.append(f"scene {i} ({t}): missing {field!r}")
        p += [f"scene {i} ({t}): {x}" for x in shape_problems(s)]
    if "program" in story:  # a story without one is news, exactly as before programs
        p += programs.story_problems(story)
    return p


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def shape_problems(s):
    """Counts, item shapes and numbers of one scene; a draw scene's SVG through art.sanitize."""
    t, out = s.get("type"), []
    items = s.get("items")
    if t in COUNTS and isinstance(items, list):
        lo, hi = COUNTS[t]
        if not lo <= len(items) <= hi:
            out.append(f"items: {len(items)}, needs {lo}-{hi}" if lo != hi else f"items: {len(items)}, needs {lo}")
    if t == "pair":
        for k, it in enumerate(items or []):
            if not isinstance(it, dict) or not isinstance(it.get("title"), str) or not it["title"].strip():
                out.append(f"items[{k}]: needs {{title, sub}}")
    if t == "steps":
        if any(not isinstance(it, str) or not it.strip() for it in items or []):
            out.append("items: each step is a short text")
    if t in ("bars", "trend"):
        for k, it in enumerate(items or []):
            if not isinstance(it, dict) or not isinstance(it.get("label"), str) or not _number(it.get("value")):
                out.append(f"items[{k}]: needs {{label, value}} with a number value")
            elif t == "bars" and it["value"] <= 0:
                out.append(f"items[{k}]: a bar's value is above zero (the axis starts at zero)")
    if t == "change":
        for k in ("before", "after"):
            v = s.get(k)
            if v is not None and (not isinstance(v, dict) or not isinstance(v.get("label"), str) or not _number(v.get("value"))):
                out.append(f"{k}: needs {{label, value}} with a number value")
    if t == "draw" and s.get("svg"):
        from tt_shorts import art
        out += art.scene_problems(s["svg"])
    return out


def check_story(story, sources=None):
    """Every check a story passes before it is rendered: structure, news rules, Georgian rules, timing, captions."""
    p = structure_problems(story)
    if p:
        return p  # the rest needs a well-formed story
    story = packs.with_say(story)  # the pack's own names (SiTech) have spoken forms too
    texts = sources or []
    if programs.name_of(story) != programs.DEFAULT:
        p += programs.rule_problems(story, texts)  # the program's tier: claims or law (some rules need no sources)
        p += programs.length_problems(story)  # and its format's length window
    elif texts:
        p += news_check.problems(story, texts)
    ka = ka_check.problems(story, {"title": "", "description": "", "text": " ".join(texts)})
    if not texts:  # without the articles a quote can't be compared: that check needs --sources (the news rules say so)
        ka = [x for x in ka if "is quoted but not in the article" not in x]
    p += ka
    words = speech.estimate_words(story["narration"])
    try:
        marks = speech.scene_frames(story, words)
        secs = marks[-1] / FPS
        if not 18 <= secs <= 60:
            p.append(f"timing: about {secs:.0f}s with an estimated voice; aim for 25-45s")
    except (ValueError, RuntimeError) as e:
        p.append(f"timing: {e}")
        return p
    font = packs.of(story)["_fonts"]["700"]
    p += [f"captions: {x}" for x in captions.problems(captions.layout(words, "page", font=font), words, font)]
    return p


# ---------------------------------------------------------------- render / still


def brand_of(story):
    return packs.of(story)["name"]


def render_story(story_path, fmt, engine="gemini", out_path=None):
    """Render one story in one resolved format -> result dict (with "problems"). Used by `render` and the queue."""
    missing = _kaeasy_required()
    if missing:
        return {"problems": missing}
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    work, p = props.build(str(story_path), fmt["look"], engine, tone, speech.EDGE_VOICES["eka"], fmt["platform"],
                          caption_design=fmt["captions"], music=fmt["music"], transition=fmt["transition"])
    secs = p["durationInFrames"] / FPS
    target = pathlib.Path(out_path) if out_path else store.render_path(
        brand_of(story), story["id"], fmt["name"], p["variant"], fmt["captions"])
    props.render_video(work, p, target)
    variety.record(brand_of(story), story["id"], p["variant"], {**p["style"], "transition": p["transition"],
                                                                "music": p["music"]}, [x["type"] for x in p["scenes"]])
    result = {"file": str(target.resolve()), "seconds": round(secs, 1), "format": fmt["name"], "look": p["variant"],
              "style": p["style"], "transition": p["transition"],
              "captions": fmt["captions"], "voice": fmt["voice"], "engine": engine, "music": p["music"],
              "brand": brand_of(story), "story": str(pathlib.Path(story_path).resolve()),
              "scenes": [s["type"] for s in p["scenes"]], "voice_qa": p.get("voiceQa", []), "kaeasy": kaeasy.version()}
    problems = []
    if not fmt["min_seconds"] <= secs <= fmt["max_seconds"]:
        problems.append(f"length {secs:.1f}s is outside the format's {fmt['min_seconds']}-{fmt['max_seconds']}s")
    result["problems"] = problems
    target.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)  # the scratch; the voice stays cached in cache/voices
    store.log("rendered", file=result["file"], seconds=result["seconds"], problems=problems)
    return result


def _format(a):
    name = a.format or program_format(a.story)
    return formats.get(name, look=a.look, captions=a.captions, transition=a.transition, voice=a.voice, music=a.music,
                       platform=a.platform)


def program_format(story_path):
    """The format a story renders in when none is given: its program's (news: "news")."""
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    return programs.of(story)["format"] if "program" in story else "news"


def _kaeasy_required():
    """On the server SHORTS_REQUIRE_KAEASY=1: no Georgian gate, no video."""
    if os.environ.get("SHORTS_REQUIRE_KAEASY") == "1" and not kaeasy.available():
        return [f"kaeasy is required (SHORTS_REQUIRE_KAEASY=1) but not found in {kaeasy.directory()}"]
    return []


def render(a):
    result = render_story(a.story, _format(a), a.engine, a.out)
    return out(result, 1 if result["problems"] else 0)


def still(a):
    fmt = _format(a)
    story = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    work, p = props.build(a.story, fmt["look"], a.engine, tone, speech.EDGE_VOICES["eka"], fmt["platform"],
                          caption_design=fmt["captions"], music=fmt["music"], transition=fmt["transition"])
    frames = [int(x) for x in a.frames.split(",")] if a.frames else \
        [s["from"] + s["duration"] // 2 for s in p["scenes"]]  # default: the middle of every scene
    target = pathlib.Path(a.out) if a.out else store.home() / "renders" / store.safe(brand_of(story)) / store.today() / "stills"
    files = props.render_stills(work, frames, target)
    return out({"files": [str(f) for f in files], "frames": frames})


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def _loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    vals = {}
    for line in r.stderr.splitlines():
        line = line.strip()
        for key in ("I:", "LRA:", "Peak:"):
            if line.startswith(key):
                try:
                    vals[key[:-1]] = float(line.split()[1])
                except (IndexError, ValueError):
                    pass
    return vals


def qa_file(path, fmt):
    """Size, length window, loudness and a contact sheet -> dict with "problems". Used by `qa` and the queue."""
    path = pathlib.Path(path)
    if not path.exists():
        return {"problems": [f"no such file: {path}"]}
    info = _probe(path)
    secs = float(info["format"]["duration"])
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    loud = _loudness(path) if has_audio else {}
    problems = []
    if (v.get("width"), v.get("height")) != (1080, 1920):
        problems.append(f"size {v.get('width')}x{v.get('height')}, expected 1080x1920")
    if not fmt["min_seconds"] <= secs <= fmt["max_seconds"]:
        problems.append(f"length {secs:.1f}s outside {fmt['min_seconds']}-{fmt['max_seconds']}s")
    if not has_audio:
        problems.append("no audio track")
    elif not -19 <= loud.get("I", -99) <= -13:
        problems.append(f"loudness {loud.get('I')} LUFS, expected -19..-13 (voice -16, music under it)")
    sheet = path.with_suffix(".sheet.jpg")
    n = 8
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf",
                    f"fps={n / max(secs, 1):.4f},scale=270:480,tile={n}x1", "-frames:v", "1", "-q:v", "4", str(sheet)],
                   check=False)
    return {"file": str(path.resolve()), "seconds": round(secs, 1), "size": [v.get("width"), v.get("height")],
            "loudness": loud, "sheet": str(sheet.resolve()) if sheet.exists() else None, "problems": problems}


def qa(a):
    result = qa_file(a.video, formats.get(a.format))
    return out(result, 1 if result["problems"] else 0)


# ---------------------------------------------------------------- write / voices / doctor


def write_story(source, ref, brand=packs.DEFAULT, out_path=None, program=None):
    """A source reference -> a written, checked story file (+ its sources beside it). Used by `write` and the queue.
    program: news (default: the news-cluster writer, as before programs) or another program (programs.py), which
    writes from its brief, under its scenes and rule tier."""
    from tt_shorts import sources as src, writer
    packs.load(brand)  # an unknown pack fails before any model call
    prog = programs.get(program)
    source = source or prog["sources"][0]
    programs.check_source(prog, source)  # and a source the program doesn't take
    data = src.fetch(source, ref)
    if prog["name"] == programs.DEFAULT:
        story = writer.write(data["cluster"], data["articles"], avoid=variety.recent_sequences(brand))
    else:
        story = programs.write(prog, data, brand, avoid=variety.recent_sequences(brand))
    story["brand"] = brand
    story["source"] = {"name": source, "ref": str(ref)}
    programs.stamp(story, prog, data["cluster"])  # program, category, the document's facts and link: data
    name = programs.story_ref(prog, data["cluster"], ref)
    target = pathlib.Path(out_path) if out_path else store.story_path(brand, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    side = store.sources_path(target)  # the articles, so `check --sources` can re-run the news rules later
    side.write_text(json.dumps(data["articles"], ensure_ascii=False), encoding="utf-8")
    problems = check_story(story, data["articles"])
    store.log("written", story=str(target), problems=problems)
    result = {"story": str(target.resolve()), "sources": str(side.resolve()),
              "scenes": [s["type"] for s in story["scenes"]], "problems": problems}
    if prog["name"] != programs.DEFAULT:
        result.update(program=prog["name"], rules=prog["rules"], publish=prog["publish"], format=prog["format"])
    return result


def write(a):
    ref = a.ref if a.ref is not None else a.cluster
    if ref is None:
        return out({"problems": ["give --ref (or --cluster for tbilisi-today)"]}, 2)
    result = write_story(a.source, ref, a.brand, a.out, a.program)
    return out(result, 1 if result["problems"] else 0)


def voice_samples(a):
    argv = ["voices"] + (["--story", a.story] if a.story else []) + (["--only", a.only] if a.only else [])
    sys.argv = argv
    voices.main()
    return out({"dir": str((ROOT / "out" / "voices").resolve())})  # samples to listen to, not part of a job


def queue_cmd(a):
    from tt_shorts import queue
    if a.action == "add":
        overrides = {k: getattr(a, k) for k in ("look", "captions", "transition", "voice", "music", "platform") if getattr(a, k)}
        job, created = queue.add(a.brand, a.source if not a.story else None, a.ref, a.format, overrides, a.story,
                                 a.priority, program=a.program)
        return out({"job": job, "created": created})
    if a.action == "list":
        return out({"counts": queue.counts(), "jobs": queue.listing(a.state, a.limit)})
    if a.action == "run":
        return out(queue.run(a.max, a.engine))
    if not a.id:
        return out({"problems": [f"queue {a.action} needs a job id"]}, 2)
    job = {"show": queue.get, "retry": queue.retry, "cancel": queue.cancel}[a.action](a.id)
    return out({"job": job} if job else {"problems": [f"no job {a.id}"]}, 0 if job else 1)


def gc_cmd(a):
    removed = store.gc(dry_run=a.dry_run)
    return out({"dry_run": a.dry_run, "removed": {k: len(v) for k, v in removed.items()}, "home": str(store.home())})


def _source_tools():
    """What the document sources can use here (none of it blocks a news render)."""
    import importlib.util as iu
    from tt_shorts.sources import ordo
    return {"ordo (law source, ORDO_DIR)": ordo.version() or f"missing in {ordo.directory()} (ORDO_DIR)",
            "url extractor": "trafilatura" if iu.find_spec("trafilatura") else "stdlib fallback (pip install trafilatura)",
            "pdf reader": "pypdf" if iu.find_spec("pypdf") else "pdftotext" if shutil.which("pdftotext") else "missing"}


def doctor(_a):
    have = lambda cmd: shutil.which(cmd) is not None  # noqa: E731
    checks = {
        "ffmpeg": have("ffmpeg"),
        "node": have("node"),
        "remotion installed": (ROOT / "remotion" / "node_modules" / "remotion").is_dir(),
        "chromium for remotion": bool(props.chrome()) or "remotion will download one",
        "fonts": all((ROOT / "assets" / "fonts" / f).exists() for f in (
            "firago-regular.d8b411bacd.woff2", "firago-bold.ed7553cea8.woff2")),
        "music loops": len(list((ROOT / "assets" / "music").glob("*.m4a"))),
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
        "alignment python": os.environ.get("ALIGN_PYTHON") or "unset (uses this python; needs torch + transformers)",
        "writer key (OPENROUTER_API_KEY)": bool(os.environ.get("OPENROUTER_API_KEY")),
        "D1 access (CLOUDFLARE_API_TOKEN)": bool(os.environ.get("CLOUDFLARE_API_TOKEN")),
        "home (VEASY_HOME)": str(store.home()),
        "kaeasy (Georgian gate)": kaeasy.version() or f"missing in {kaeasy.directory()} (KAEASY_DIR)",
    }
    bad_packs = []
    for n in packs.names():
        try:
            packs.load(n)
        except (packs.BrandError, OSError, ValueError) as e:
            bad_packs.append(f"brand {n}: {e}")
    checks["brands"] = packs.names() if not bad_packs else bad_packs
    try:
        n = len(formats.load_all())
        checks["formats"] = n
    except formats.FormatError as e:
        checks["formats"] = f"ERROR: {e}"
    try:
        checks["programs"] = sorted(programs.load_all())
    except programs.ProgramError as e:
        checks["programs"] = f"ERROR: {e}"
        bad_packs.append(str(e))
    checks.update(_source_tools())
    blocking = [k for k in ("ffmpeg", "node", "remotion installed", "fonts") if checks[k] is not True]
    blocking += _kaeasy_required() + bad_packs
    if not checks["music loops"]:
        blocking.append("music loops (run tools/compose_music.py)")
    return out({"checks": checks, "problems": blocking}, 1 if blocking else 0)


# ---------------------------------------------------------------- cli


def queue_states():
    from tt_shorts import queue
    return queue.STATES


def _rules_of(story):
    try:
        return programs.of(story)["rules"]
    except programs.ProgramError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tt_shorts.engine", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("options")
    o.add_argument("--brand", help="the pack whose categories, looks and voices to show (default tbilisi-today)")
    c = sub.add_parser("check")
    c.add_argument("story")
    c.add_argument("--sources", help="JSON list of the member articles' texts (enables the news rules N2/N3)")
    for name in ("render", "still"):
        r = sub.add_parser(name)
        r.add_argument("story")
        r.add_argument("--format", help="a format (default: the story's program's, news for news)")
        r.add_argument("--look", choices=formats.LOOKS)
        r.add_argument("--captions", choices=formats.CAPTIONS)
        r.add_argument("--transition", choices=formats.TRANSITIONS, help="the cut between scenes (auto: the look's own)")
        r.add_argument("--voice", help="family or a preset (see options)")
        r.add_argument("--music", help="family, off or a family name")
        r.add_argument("--platform", help="utm_source of the QR link")
        r.add_argument("--engine", default="gemini", choices=["gemini", "edge", "silent"])
        r.add_argument("--out")
        if name == "still":
            r.add_argument("--frames", help="comma-separated frames (default: the middle of every scene)")
    q = sub.add_parser("qa")
    q.add_argument("video")
    q.add_argument("--format", default="news")
    w = sub.add_parser("write")
    w.add_argument("--program", help="news (default), explainer, law, blog... (see options: programs)")
    w.add_argument("--source", help="tbilisi-today (ref = cluster id), text (ref = JSON file), url, pdf, ordo, sitech "
                                    "(default: the program's first source)")
    w.add_argument("--ref", help="the story's reference in its source")
    w.add_argument("--cluster", help="same as --ref, for tbilisi-today")
    w.add_argument("--brand", default=packs.DEFAULT, help="the brand pack the story will be rendered with")
    w.add_argument("--out")
    v = sub.add_parser("voices")
    v.add_argument("--story")
    v.add_argument("--only")
    sub.add_parser("doctor")
    qp = sub.add_parser("queue")
    qp.add_argument("action", choices=["add", "list", "run", "show", "retry", "cancel"])
    qp.add_argument("id", nargs="?")
    qp.add_argument("--brand", help="a pack in brands/ (default: the story's own, else tbilisi-today)")
    qp.add_argument("--program", help="news (default; a story file's own program), explainer, law, blog...")
    qp.add_argument("--source", help="default: the program's first source (news: tbilisi-today)")
    qp.add_argument("--ref")
    qp.add_argument("--story", help="an already written story file (skips writing)")
    qp.add_argument("--format", help="default: the program's format (news: news)")
    for k in ("look", "captions", "transition", "voice", "music", "platform"):
        qp.add_argument(f"--{k}")
    qp.add_argument("--priority", type=int, default=0)
    qp.add_argument("--state", choices=queue_states())
    qp.add_argument("--limit", type=int, default=50)
    qp.add_argument("--max", type=int, default=5, help="run: jobs to process this time")
    qp.add_argument("--engine", default="gemini", choices=["gemini", "edge", "silent"])
    g = sub.add_parser("gc")
    g.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "options":
            return out(options(a.brand))
        if a.cmd == "check":
            story = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
            sources = json.loads(pathlib.Path(a.sources).read_text(encoding="utf-8")) if a.sources else None
            problems = check_story(story, sources) + _kaeasy_required()
            result = {"story": a.story, "news_rules": bool(sources), "kaeasy": kaeasy.version(),
                      "problems": problems, "warnings": ka_check.warnings(story)}
            if "program" in story:
                result.update(program=programs.name_of(story), rules=_rules_of(story))
            return out(result, 1 if problems else 0)
        return {"render": render, "still": still, "qa": qa, "write": write, "voices": voice_samples,
                "doctor": doctor, "queue": queue_cmd, "gc": gc_cmd}[a.cmd](a)
    except (formats.FormatError, ValueError) as e:
        return out({"problems": [str(e)]}, 2)


if __name__ == "__main__":
    sys.exit(main())
