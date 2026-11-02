"""The tbilisi.today Shorts engine: one entry point for people and agents.

Every command prints JSON on stdout (human notes go to stderr), so an agent can call it and read the result.

  python -m tt_shorts.engine options                         # every choice the engine offers (looks, captions, voices,
                                                             # music, formats, scene types and their fields)
  python -m tt_shorts.engine check  stories/24725.json [--sources articles.json]
                                                             # all checks a story must pass before rendering
  python -m tt_shorts.engine render stories/24725.json --format news [--look kinetic] [--captions roll]
                                    [--voice warm] [--music off] [--engine gemini|edge|silent] [--out out/x.mp4]
  python -m tt_shorts.engine still  stories/24725.json --frames 60,300 [same choices as render]
  python -m tt_shorts.engine qa     out/24725.mp4 [--format news]   # length, size, loudness + a contact sheet
  python -m tt_shorts.engine write  --cluster 24725 [--out stories/24725.json]   # D1 cluster -> checked story
  python -m tt_shorts.engine voices [--story stories/24835.json] [--only warm,clear]   # tone samples by ear
  python -m tt_shorts.engine doctor                          # is this machine ready to render?

Exit status: 0 when the command did what it says, 1 when a check or QA found problems, 2 on a usage error.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

from tt_shorts import captions, formats, ka_check, meta, news_check, props, speech, voices

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
    "end": ([], [], "the end card: logo, QR to the story page, the call to action"),
}
STORY_KEYS = ("id", "category", "date", "narration", "scenes")


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    return code


def note(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------- options


def options():
    every = formats.load_all()
    return {
        "looks": {"auto": "by the story's category", **{v: d for v, d in (
            ("editorial", "calm, grid, rising type: hard news"),
            ("kinetic", "giant type, hard cuts, inverted blocks: light news"),
            ("cards", "every scene a site-style story card: service news"))}},
        "look_by_family": meta.VARIANT_BY_FAMILY,
        "captions": {"page": "a fixed two-line block; words light up as spoken (most stable)",
                     "roll": "a three-line teleprompter that scrolls continuously"},
        "voices": {name: {"label": p["label"], "voice": p["voice"], "approved": name in voices.APPROVED}
                   for name, p in voices.PRESETS.items()},
        "voice_by_family": voices.BY_FAMILY,
        "music": ["family", "off", *meta.FAMILIES],
        "engines": {"gemini": "production voice (GEMINI_API_KEY + the alignment venv)",
                    "edge": "free preview stand-in (robotic; timing only)", "silent": "music and captions only"},
        "formats": every,
        "scenes": {t: {"required": r, "optional": o, "shows": d} for t, (r, o, d) in SCENES.items()},
        "categories": {c: {"label": meta.category_label(c), "family": meta.family(c),
                           "look": meta.variant_for(c), "voice": voices.BY_FAMILY[meta.family(c)]}
                       for c in meta.CATEGORY_KA},
    }


# ---------------------------------------------------------------- check


def structure_problems(story):
    p = []
    for k in STORY_KEYS:
        if k not in story:
            p.append(f"story: missing {k!r}")
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
    return p


def check_story(story, sources=None):
    """Every check a story passes before it is rendered: structure, news rules, Georgian rules, timing, captions."""
    p = structure_problems(story)
    if p:
        return p  # the rest needs a well-formed story
    texts = sources or []
    if texts:
        p += news_check.problems(story, texts)
    p += ka_check.problems(story, {"title": "", "description": "", "text": " ".join(texts)})
    words = speech.estimate_words(story["narration"])
    try:
        marks = speech.scene_frames(story, words)
        secs = marks[-1] / FPS
        if not 18 <= secs <= 60:
            p.append(f"timing: about {secs:.0f}s with an estimated voice; aim for 25-45s")
    except (ValueError, RuntimeError) as e:
        p.append(f"timing: {e}")
        return p
    p += [f"captions: {x}" for x in captions.problems(captions.layout(words, "page"), words)]
    return p


# ---------------------------------------------------------------- render / still


def _build(a, fmt):
    look = fmt["look"]
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    return props.build(a.story, look, a.engine, tone, speech.EDGE_VOICES["eka"], fmt["platform"],
                       caption_design=fmt["captions"], music=fmt["music"])


def _format(a):
    return formats.get(a.format, look=a.look, captions=a.captions, voice=a.voice, music=a.music, platform=a.platform)


def render(a):
    fmt = _format(a)
    work, p = _build(a, fmt)
    secs = p["durationInFrames"] / FPS
    target = pathlib.Path(a.out) if a.out else ROOT / "out" / f"{p['id']}-{a.format}-{p['variant']}-{fmt['captions']}.mp4"
    props.render_video(work, p, target)
    result = {"file": str(target.resolve()), "seconds": round(secs, 1), "format": a.format, "look": p["variant"],
              "captions": fmt["captions"], "voice": fmt["voice"], "engine": a.engine, "music": p["music"],
              "scenes": [s["type"] for s in p["scenes"]], "voice_qa": p.get("voiceQa", [])}
    problems = []
    if not fmt["min_seconds"] <= secs <= fmt["max_seconds"]:
        problems.append(f"length {secs:.1f}s is outside the format's {fmt['min_seconds']}-{fmt['max_seconds']}s")
    result["problems"] = problems
    return out(result, 1 if problems else 0)


def still(a):
    fmt = _format(a)
    work, p = _build(a, fmt)
    frames = [int(x) for x in a.frames.split(",")] if a.frames else \
        [s["from"] + s["duration"] // 2 for s in p["scenes"]]  # default: the middle of every scene
    files = props.render_stills(work, frames, pathlib.Path(a.out or ROOT / "out" / "stills"))
    return out({"files": [str(f) for f in files], "frames": frames})


# ---------------------------------------------------------------- qa


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


def qa(a):
    path = pathlib.Path(a.video)
    if not path.exists():
        return out({"problems": [f"no such file: {path}"]}, 1)
    fmt = formats.get(a.format)
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
    return out({"file": str(path.resolve()), "seconds": round(secs, 1), "size": [v.get("width"), v.get("height")],
                "loudness": loud, "sheet": str(sheet.resolve()) if sheet.exists() else None, "problems": problems},
               1 if problems else 0)


# ---------------------------------------------------------------- write / voices / doctor


def write(a):
    sys.path.insert(0, str(ROOT))
    from ops import daily  # D1 access lives with the daily run (CLOUDFLARE_* + TT_D1_DATABASE_ID)
    from tt_shorts import writer
    rows = daily.d1("""SELECT sc.id, sc.headline, sc.source_count, sc.article_count, sc.created_at,
                              COALESCE((SELECT a.category FROM articles a WHERE a.cluster_id = sc.id AND a.category IS NOT NULL
                                        GROUP BY a.category ORDER BY count(*) DESC LIMIT 1), 'general') AS category
                         FROM story_clusters sc WHERE sc.id = ?1""", [a.cluster])
    if not rows:
        return out({"problems": [f"no cluster {a.cluster}"]}, 1)
    data = daily.payload(rows[0])
    if not data["articles"]:
        return out({"problems": ["the cluster has no readable articles"]}, 1)
    story = writer.write(data["cluster"], data["articles"])
    target = pathlib.Path(a.out or ROOT / "stories" / f"{a.cluster}.json")
    target.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    src = target.with_suffix(".sources.json")  # the articles, so `check --sources` can re-run the news rules later
    src.write_text(json.dumps(data["articles"], ensure_ascii=False), encoding="utf-8")
    return out({"story": str(target.resolve()), "sources": str(src.resolve()), "scenes": [s["type"] for s in story["scenes"]],
                "problems": check_story(story, data["articles"])})


def voice_samples(a):
    argv = ["voices"] + (["--story", a.story] if a.story else []) + (["--only", a.only] if a.only else [])
    sys.argv = argv
    voices.main()
    return out({"dir": str((ROOT / "out" / "voices").resolve())})


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
    }
    try:
        n = len(formats.load_all())
        checks["formats"] = n
    except formats.FormatError as e:
        checks["formats"] = f"ERROR: {e}"
    blocking = [k for k in ("ffmpeg", "node", "remotion installed", "fonts") if checks[k] is not True]
    if not checks["music loops"]:
        blocking.append("music loops (run tools/compose_music.py)")
    return out({"checks": checks, "problems": blocking}, 1 if blocking else 0)


# ---------------------------------------------------------------- cli


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tt_shorts.engine", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("options")
    c = sub.add_parser("check")
    c.add_argument("story")
    c.add_argument("--sources", help="JSON list of the member articles' texts (enables the news rules N2/N3)")
    for name in ("render", "still"):
        r = sub.add_parser(name)
        r.add_argument("story")
        r.add_argument("--format", default="news")
        r.add_argument("--look", choices=formats.LOOKS)
        r.add_argument("--captions", choices=formats.CAPTIONS)
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
    w.add_argument("--cluster", type=int, required=True)
    w.add_argument("--out")
    v = sub.add_parser("voices")
    v.add_argument("--story")
    v.add_argument("--only")
    sub.add_parser("doctor")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "options":
            return out(options())
        if a.cmd == "check":
            story = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
            sources = json.loads(pathlib.Path(a.sources).read_text(encoding="utf-8")) if a.sources else None
            problems = check_story(story, sources)
            return out({"story": a.story, "news_rules": bool(sources), "problems": problems}, 1 if problems else 0)
        return {"render": render, "still": still, "qa": qa, "write": write, "voices": voice_samples,
                "doctor": doctor}[a.cmd](a)
    except formats.FormatError as e:
        return out({"problems": [str(e)]}, 2)


if __name__ == "__main__":
    sys.exit(main())
