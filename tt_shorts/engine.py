"""Veasy's engine: one entry point for people and agents, for every brand pack (brands/, brand.py).

Every command prints JSON on stdout (human notes go to stderr), so an agent can call it and read the result.

  python -m tt_shorts.engine options [--brand sitech]        # every choice the engine offers (brands, looks, captions,
                                                             # voices, music, formats, scene types and their fields)
  python -m tt_shorts.engine check  stories/24725.json [--sources articles.json]
                                                             # all checks a story must pass before rendering
  python -m tt_shorts.engine render stories/24725.json --format news [--look kinetic] [--captions roll]
                                    [--voice warm] [--music off] [--engine gemini|edge|silent] [--out out/x.mp4]
  python -m tt_shorts.engine still  stories/24725.json --frames 60,300 [same choices as render]
  python -m tt_shorts.engine qa     out/24725.mp4 [--format news]   # length, size, loudness, the layout probe + a sheet
  python -m tt_shorts.engine probe  stories/24725.json [--look all]   # where every text really is, per scene (probe.py)
  python -m tt_shorts.engine plan   stories/24725.json [--look kinetic]   # a free storyboard before paying for a voice:
                                                             # timings, reading load, variety picks, motion rules,
                                                             # the probe and a half-size contact sheet (plan.py)
  python -m tt_shorts.engine selftest [--update]              # golden stills of the fixture stories (golden.py)
  python -m tt_shorts.engine media  stories/24835-media.json [--offline]   # the scenes' show hints -> licensed
                                                             # pictures in the story's assets ledger (assets.py)
  python -m tt_shorts.engine learn  [--brand sitech] [--days 7]   # the rules failing most lately (failures.py)
  python -m tt_shorts.engine package <render>.json [--only srt,vtt,cover,carousel,teaser,texts,telegram]
                                                             # one render -> every surface (package.py), no new voice
  python -m tt_shorts.engine write  --source tbilisi-today --ref 24725 [--brand tbilisi-today] [--out x.json]
                                                             # a source's story -> a checked story JSON
  python -m tt_shorts.engine write  --program law --source ordo --ref constitution:17   # a program (programs.py):
                                                             # explainer, law, blog... from url, pdf, ordo, sitech
  python -m tt_shorts.engine write  --rubric number --ref 24835     # a rubric (rubrics.py): „დღის ციფრი · #12“...
  python -m tt_shorts.engine write  --program digest --source stories --ref a.json,b.json   # the morning digest
  python -m tt_shorts.engine queue  add --ref 24725 [--brand sitech] [--format news] [--rubric number] | list | run
                                    [--max 5] | show <id> | retry <id> | cancel <id>   # the job queue (queue.py)
  python -m tt_shorts.engine rubrics list [--brand] | facts --source --ref | stamp <story> --rubric <id> [--sources]
                                                             # the rubrics: counters, which a cluster may be, a
                                                             # hand-written story's episode (rubrics.py)
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
from tt_shorts import (assets, captions, catalog, chapters, directors, formats, geo, icons, ka_check, kaeasy,
                       meta, motion_rules, news_check, programs, props, rubrics, sfx, speech, store, swipe,
                       variety, voices)

ROOT = speech.ROOT
FPS = speech.FPS

# The scene vocabulary: type -> (required fields, optional fields, what it shows), generated from the brush catalog
# (brushes/<type>.json, catalog.py); remotion/src/scenes draws them. COUNTS: how many items a type holds.
SCENES = catalog.scenes()
COUNTS = catalog.counts()
STORY_KEYS = ("id", "category", "date", "narration", "scenes")


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    return code


def note(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------- options


def options(brand_name=None):
    from tt_shorts import package
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
                    **variety.OPTIONS, "transitions_by_look": variety.TRANSITIONS,
                    "novelty": {"about": "before the voice, a plan sharing too_close or more of the fingerprint's "
                                         "fields with one of the brand's last recent videos is re-rolled (at most "
                                         "rerolls tries; then the farthest, with a warning)",
                                "fingerprint": list(variety.FIELDS), "too_close": variety.TOO_CLOSE,
                                "recent": variety.RECENT, "rerolls": variety.REROLLS}},
        "transitions": {"auto": "varied per video among the ones that suit the look (variety.TRANSITIONS)",
                        "cut": "a plain cut, the old scene just ends", "line": "an ink line with the dot sweeps across",
                        "panel": "an ink panel wipes through", "wipe": "the new scene is revealed left to right",
                        "slide": "a short slide and fade", "push": "the old scene leaves left, the new one comes from the right",
                        "dot": "an iris opens from the header's progress dot",
                        "meter": "equaliser bars in ink rise over the old scene and fall away from the new one"},
        "outros": dict(swipe.ABOUT),
        "themes": {"about": "a pack's palettes (brand.json themes; brands.<pack>.themes lists them): a format's or "
                            "--theme's default (the pack's default theme: nothing changes), auto (variety: the least "
                            "used lately among the pack's allowed themes, inside a director's themes) or a name. "
                            "allowed: false is a preview: plan, probe, still and selftest show it, a render refuses it",
                   "default": b["default_theme"],
                   "pack": {t: {"label": s["label"], "allowed": s["allowed"], "mode": packs.mode(s["colors"])}
                            for t, s in b["themes"].items()},
                   "known": formats.themes_known()},
        "beats": {"on": "a change inside every scene each 1.5-3 s on the words: items and labels come in when said, "
                        "quotes and points light up a phrase a beat, rules, bars, runs and maps step on (beats.py)",
                  "off": "each scene's own stagger (texts in by 40 % of the scene), as before"},
        "chapters": {"off": "the progress rule (default)", "on": "\"01 / 03\" and a segmented bar in the header, "
                     f"chapters of {chapters.MIN_SCENES}+ scenes by code (a digest's chapter cards open its stories)",
                     "auto": f"on for a video of {chapters.AUTO_SECONDS} s or more"},
        "captions": {"page":"a fixed two-line block; words light up as spoken (most stable)",
                     "roll": "a three-line teleprompter that scrolls continuously",
                     "keyword": "a two-line page in a dark box, the spoken word lit, and per page one keyword (a "
                                "number, a name from the story or the scene's em phrase) in the pack's keyword style "
                                f"({packs.keyword_style(b)} here)"},
        "voices": {name: {"label": p["label"], "voice": p["voice"], "approved": name in voices.APPROVED,
                          **({"brand": b["name"]} if name in (b.get("voices") or {}) else {})}
                   for name, p in presets.items()},
        "voice_by_family": b["voice_by_family"],
        "music": ["family", "off", *meta.FAMILIES],
        "engines": {"gemini": "production voice (GEMINI_API_KEY + the alignment venv)",
                    "edge": "free preview stand-in (robotic; timing only)", "silent": "music and captions only"},
        "formats": every,
        "directors": directors.options(),
        "rubrics": rubrics.options(),
        "programs": {n: programs.summary(p) for n, p in programs.load_all().items()},
        "sources": _sources_about(),
        "scenes": catalog.options(),  # every brush's card (brushes/<type>.json): slots, limits, when, an example
        "em": {"about": "a scene whose brush has em fields may carry \"em\": a phrase of its on-screen text that its "
                        "part of the narration says; it is marked on screen as the voice says it (marks.py)",
               "kinds": list(catalog.MARKS), "picked_by": "code: the scene type's kinds, varied per story; never the writer",
               "strokes": "clean for hard and service news, a little rough for light news (by the story's family)"},
        "package": {"about": "engine package <render>.json --only <parts>: one render -> every surface", **package.PARTS},
        "areas": geo.areas(),  # a where scene's optional area (tt_shorts/geo.py)
        "media": {"about": "a scene's \"show\" hint (the writer's: a short English query, or \"screenshot\" for the "
                           "story's own official page) -> a licensed picture behind the scene, resolved by code before "
                           "the voice (engine media; write and plan do it too) into the scene's media and the story's "
                           "assets ledger, both code-owned (assets.py)",
                  "providers": {n: why or "available" for n, why in assets.availability().items()},
                  "order": packs.load(brand_name).get("media", {}).get("providers", []),
                  "licences": {k: v or "a screenshot of an allow-listed page" for k, v in assets.LICENCES.items()},
                  "credited": list(assets.CREDITED), "kinds": list(assets.KINDS),
                  "no_media": list(catalog.NO_MEDIA),
                  "screenshots": "only from the pack's media.official and media.own and a program's screenshots",
                  "rule": "N13: labelled „" + b["strings"]["illustrative"] + "“, never for crime, incidents or deaths, "
                          "never presented as the event; no AI imagery until the owner decides"},
        "sfx": {"about": "format key sfx: sound effects on the timeline's events, mixed by ffmpeg (sfx.py)",
                **sfx.OPTIONS, "sounds": list(sfx.NAMES), "level_db": sfx.LEVEL_DB},
        "self_checks": {"plan": "engine plan <story> [--look]: a free storyboard before the voice is paid for: scene "
                                "times, words and reading load, the variety picks (not recorded), the motion rules, "
                                "the probe and a half-size contact sheet",
                        "probe": "engine probe <story> [--look all]: every text's real box per scene; part of every "
                                 "render (a problem holds the job)",
                        "selftest": "engine selftest [--update]: golden stills of the fixture stories in every look; "
                                    "run before merging a visual change",
                        "learn": "engine learn [--brand]: the rules failing most lately; the writer reads them"},
        "motion_rules": {"about": "checks over a video's timeline (tt_shorts/motion_rules.py): warnings in plan; "
                                  f"only {', '.join(motion_rules.HOLDS)} holds a render", **motion_rules.RULES},
        "icons": icons.options(),
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
    family = _family(story)
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
        p += [f"scene {i} ({t}): {x}" for x in shape_problems(s) + catalog.family_problems(s, family)]
    if "program" in story:  # a story without one is news, exactly as before programs
        p += programs.story_problems(story)
    return p + icons.motif_problems(story) + directors.structure_problems(story) + rubrics.story_problems(story) + \
        assets.problems(story)


def _family(story):
    """The story's family in its pack (an unknown brand is named above; the default pack judges meanwhile)."""
    try:
        pack = packs.of(story)
    except packs.BrandError:
        pack = packs.load()
    return meta.family(story.get("category", ""), pack)


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


COMPARE_RATIO = 40  # compare: above this ratio the small square is a speck; bars show it better


def shape_problems(s):
    """Counts, item shapes and numbers of one scene (the brush's slots: catalog.slot_problems, then each type's
    own); a draw scene's SVG through art.sanitize; a rail's dates in order."""
    t = s.get("type")
    out = catalog.slot_problems(s)
    items = s.get("items")
    if t == "pair":
        for k, it in enumerate(items or []):
            if not isinstance(it, dict) or not isinstance(it.get("title"), str) or not it["title"].strip():
                out.append(f"items[{k}]: needs {{title, sub}}")
    if t == "steps":
        if any(not isinstance(it, str) or not it.strip() for it in items or []):
            out.append("items: each step is a short text")
    if t in ("bars", "trend", "compare"):
        for k, it in enumerate(items or []):
            if not isinstance(it, dict) or not isinstance(it.get("label"), str) or not _number(it.get("value")):
                out.append(f"items[{k}]: needs {{label, value}} with a number value")
            elif t in ("bars", "compare") and it["value"] <= 0:
                out.append(f"items[{k}]: a {'bar' if t == 'bars' else 'square'}'s value is above zero "
                           f"({'the axis starts at zero' if t == 'bars' else 'its area is the value'})")
    if t == "compare" and isinstance(items, list) and len(items) == 2 and \
            all(isinstance(it, dict) and _number(it.get("value")) and it["value"] > 0 for it in items):
        lo, hi = sorted(it["value"] for it in items)
        if hi / lo > COMPARE_RATIO:
            out.append(f"the ratio is {hi / lo:.0f}, more than {COMPARE_RATIO}: the small square would be a speck, "
                       "show the two values as bars")
    if t in ("who", "link"):
        for k, it in enumerate(items or []):
            if not isinstance(it, dict) or not isinstance(it.get("name"), str) or not it["name"].strip():
                out.append(f"items[{k}]: needs {{name, role}}")
    if t == "rail":
        out += rail_problems(items)
    if t == "share" and _number(s.get("value")) and not 0 < s["value"] <= 100:
        out.append(f"value: {s['value']:g} is not a percent of a whole (above 0, at most 100)")
    if t == "change":
        for k in ("before", "after"):
            v = s.get(k)
            if v is not None and (not isinstance(v, dict) or not isinstance(v.get("label"), str) or not _number(v.get("value"))):
                out.append(f"{k}: needs {{label, value}} with a number value")
    if t == "draw" and s.get("svg"):
        from tt_shorts import art
        out += art.scene_problems(s["svg"])
    if t == "where" and s.get("area") is not None:
        out += geo.area_problems(s["area"])
    if t in ("sign", "stat"):
        out += icons.scene_problems(s)
    return out


def rail_problems(items):
    """A rail's events: each with a date code can read (a day and month, a year, a time) and in time order."""
    out, keys = [], []
    for k, it in enumerate(items or []):
        if not isinstance(it, dict) or not isinstance(it.get("when"), str) or not isinstance(it.get("label"), str):
            out.append(f"items[{k}]: needs {{when, label}}")
            continue
        key = news_check.date_key(it["when"])
        if key is None:
            out.append(f"items[{k}]: when „{it['when']}“ is not a date (a day and a month, a year, or a time 22:00)")
        keys.append((k, key))
    dated = [(k, key) for k, key in keys if key]
    for (a, ka), (b, kb) in zip(dated, dated[1:]):
        if news_check.date_before(kb, ka):
            out.append(f"items[{b}]: „{items[b]['when']}“ comes before „{items[a]['when']}“: a rail runs in time order")
    return out


def check_story(story, sources=None):
    """Every check a story passes before it is rendered: structure, news rules, Georgian rules, timing, captions."""
    p = structure_problems(story)
    if p:
        return p  # the rest needs a well-formed story
    story = packs.with_say(story)  # the pack's own names (SiTech) have spoken forms too
    texts = sources or []
    news = programs.name_of(story) == programs.DEFAULT
    if not news:
        p += programs.rule_problems(story, texts)  # the program's tier: claims or law (some rules need no sources)
        p += programs.length_problems(story)  # and its format's length window
    elif texts:
        p += news_check.problems(story, texts)  # N1-N5, with N10 and N11
    if news:
        p += rubrics.length_problems(story)  # a news rubric's own window (number: 20-25 s)
    if texts and story.get("director"):  # the director's own gates (witness: both sides when both are quoted)
        p += directors.story_problems(story, directors.facts(texts, story.get("category", ""), packs.of(story)))
    if not (news and texts):  # N10, N11 and N13 need no articles
        p += news_check.pictograms(story) + news_check.spoken(story) + news_check.imagery(story)
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


def render_story(story_path, fmt, engine="gemini", out_path=None, director=None):
    """Render one story in one resolved format -> result dict (with "problems"). Used by `render` and the queue.
    director: overrides the story's own (directors.py)."""
    missing = _kaeasy_required()
    if missing:
        return {"problems": missing}
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    did = director or story.get("director")
    theme = props.theme_for(story, fmt.get("theme"), directors.get(did) if did else None)
    held = packs.theme_problems(packs.of(story, theme))  # allowed: false (brand.json): not before the owner's yes
    if held:
        return {"problems": held}
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    work, p = props.build(str(story_path), fmt["look"], engine, tone, speech.EDGE_VOICES["eka"], fmt["platform"],
                          caption_design=fmt["captions"], music=fmt["music"], transition=fmt["transition"],
                          outro=fmt["outro"], director=director, theme=theme, **formats.render_keys(fmt))
    checked = _probe_render(work, p)  # the layout probe: seconds, before the minutes of the render
    motion = motion_rules.check(p)  # with the real voice's timings: unreadable text holds the video, like the probe
    secs = p["durationInFrames"] / FPS
    target = pathlib.Path(out_path) if out_path else store.render_path(
        brand_of(story), story["id"], fmt["name"], p["variant"], fmt["captions"])
    props.render_video(work, p, target)
    variety.record(brand_of(story), story["id"], p["variant"], {**p["style"], "transition": p["transition"],
                                                                "music": p["music"], "theme": p.get("theme")},
                   [x["type"] for x in p["scenes"]], p.get("novelty"))
    result = {"file": str(target.resolve()), "seconds": round(secs, 1), "format": fmt["name"], "look": p["variant"],
              "style": p["style"], "transition": p["transition"], "outro": p["outro"], "theme": p.get("theme"),
              "mode": (p.get("brand") or {}).get("mode"), "captions": fmt["captions"], "voice": fmt["voice"], "engine": engine, "music": p["music"],
              "brand": brand_of(story), "story": str(pathlib.Path(story_path).resolve()),
              "scenes": [s["type"] for s in p["scenes"]], "voice_qa": p.get("voiceQa", []), "kaeasy": kaeasy.version(),
              "probe": checked, "motion": {"holds": motion["holds"], "warnings": motion["warnings"]},
              "novelty": p.get("novelty"), "sfx": len(p.get("sfx") or []),
              "media": [s["media"]["what"] for s in p["scenes"] if s.get("media")]}
    # the novelty guard never holds a video: a plan it could not move far enough is a warning
    result["warnings"] = [w for w in [(p.get("novelty") or {}).get("warning")] if w]
    problems = (list(checked["problems"]) if checked else []) + motion["holds"]
    if not fmt["min_seconds"] <= secs <= fmt["max_seconds"]:
        problems.append(f"length {secs:.1f}s is outside the format's {fmt['min_seconds']}-{fmt['max_seconds']}s")
    result["problems"] = problems
    side = store.props_path(target)  # what was drawn (timings, captions, the pack): `engine package` reuses it
    side.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    result["props"] = str(side.resolve())
    target.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)  # the scratch; the voice stays cached in cache/voices
    store.log("rendered", file=result["file"], seconds=result["seconds"], problems=problems,
              warnings=result["warnings"])
    return result


def _probe_render(work, p):
    """The layout probe of a built render (probe.py) -> {"problems", ...}, or None when VEASY_PROBE=0. A probe
    that can't run is itself a problem: an unchecked video is held, not published."""
    from tt_shorts import probe
    if not probe.enabled():
        return None
    try:
        r = probe.check_work(work, p)
    except Exception as e:  # noqa: BLE001 - reported as a problem; the render goes on
        lines = [x for x in str(e).splitlines() if x.strip()] or [type(e).__name__]
        return {"problems": [f"probe error: {lines[-1][:300]}"], "seconds": None}
    return {k: r[k] for k in ("problems", "issues", "frames", "texts", "seconds")}


def probe_cmd(a):
    from tt_shorts import probe
    fmt = formats.get(a.format, captions=a.captions, transition=a.transition, voice=a.voice, platform=a.platform,
                      theme=a.theme, beats=a.beats, chapters=a.chapters)
    result = probe.story(a.story, fmt, a.look, a.engine, a.stills)
    return out(result, 1 if result["problems"] else 0)


def plan_cmd(a):
    from tt_shorts import plan
    media = _resolve_media(a.story)  # the scenes' pictures, before the storyboard (cached; free APIs)
    result = plan.run(a.story, _format(a), director=a.director, out=a.out)  # the format carries --look
    if media:
        result["media"] = media
        result["warnings"] = result.get("warnings", []) + media.get("errors", [])
    return out(result, 1 if result["problems"] else 0)


def _resolve_media(story_path, fetch=True):
    """Resolve a story's show hints into its ledger, in place (assets.resolve_file) -> the report, or None for a
    story with no hints. A provider that fails leaves that scene without a picture: a warning, never a failure."""
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    if not any(isinstance(s, dict) and (s.get("show") or s.get("media")) for s in story.get("scenes") or []):
        return None
    try:
        return assets.resolve_file(story_path, fetch=fetch)
    except Exception as e:  # noqa: BLE001 - no picture is never a failed story
        return {"errors": [f"media: {type(e).__name__}: {e}"]}


def media_cmd(a):
    report = _resolve_media(a.story, fetch=not a.offline) or {"scenes": {}, "errors": [], "assets": 0}
    story = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
    problems = assets.problems(story) + news_check.imagery(story)
    return out({"story": a.story, **report, "problems": problems}, 1 if problems else 0)


def selftest_cmd(a):
    from tt_shorts import golden
    pick = lambda v, every: [x.strip() for x in v.split(",") if x.strip()] if v else list(every)  # noqa: E731
    result = golden.selftest(a.update, pick(a.story, golden.STORIES), pick(a.look, packs.LOOKS),
                             themes=golden.themes_arg(a.theme))
    return out(result, 1 if result["problems"] else 0)


def learn_cmd(a):
    from tt_shorts import failures
    return out({"brand": a.brand, "days": a.days, "top": failures.top(a.brand, a.days, a.limit),
                "writer_block": failures.prompt_block(a.brand, a.days) if a.brand else None})


def _format(a):
    name = a.format or program_format(a.story)
    return formats.get(name, look=a.look, captions=a.captions, transition=a.transition, outro=a.outro, voice=a.voice,
                       music=a.music, platform=a.platform, sfx=getattr(a, "sfx", None),
                       theme=getattr(a, "theme", None), beats=getattr(a, "beats", None),
                       chapters=getattr(a, "chapters", None))


def program_format(story_path):
    """The format a story renders in when none is given: its rubric's, else its program's (news: "news")."""
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    if story.get("rubric"):
        try:
            return rubrics.get(story["rubric"])["format"]
        except rubrics.RubricError:
            pass
    return programs.of(story)["format"] if "program" in story else "news"


def _kaeasy_required():
    """On the server SHORTS_REQUIRE_KAEASY=1: no Georgian gate, no video."""
    if os.environ.get("SHORTS_REQUIRE_KAEASY") == "1" and not kaeasy.available():
        return [f"kaeasy is required (SHORTS_REQUIRE_KAEASY=1) but not found in {kaeasy.directory()}"]
    return []


def render(a):
    result = render_story(a.story, _format(a), a.engine, a.out, a.director)
    return out(result, 1 if result["problems"] else 0)


def still(a):
    fmt = _format(a)
    story = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    work, p = props.build(a.story, fmt["look"], a.engine, tone, speech.EDGE_VOICES["eka"], fmt["platform"],
                          caption_design=fmt["captions"], music=fmt["music"], transition=fmt["transition"],
                          outro=fmt["outro"], director=a.director, theme=fmt["theme"], **formats.render_keys(fmt))
    frames = [int(x) for x in a.frames.split(",")] if a.frames else \
        [s["from"] + s["duration"] // 2 for s in p["scenes"]]  # default: the middle of every scene
    target = pathlib.Path(a.out) if a.out else store.home() / "renders" / store.safe(brand_of(story)) / store.today() / "stills"
    files = props.render_stills(work, frames, target)
    return out({"files": [str(f) for f in files], "frames": frames, "theme": p["theme"],
                "warnings": packs.theme_problems(packs.of(story, p["theme"]))})


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
    """Size, length window, loudness, a readable hook at frame 0 (swipe.opening_problems) and a contact sheet
    -> dict with "problems". Used by `qa` and the queue."""
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
    probed = _sidecar(path).get("probe")  # render_story's layout probe of this video, when it made it
    if probed:
        problems += [x for x in probed.get("problems", []) if x not in problems]
    if not has_audio:
        problems.append("no audio track")
    elif not -19 <= loud.get("I", -99) <= -13:
        problems.append(f"loudness {loud.get('I')} LUFS, expected -19..-13 (voice -16, music under it)")
    light = _sidecar(path).get("mode") == "light"  # a light theme's ink is the dark pixels (render_story's mode)
    ink = swipe.opening_ink(path, light)  # the first frame decides the swipe: the hook must be on screen there
    problems += swipe.opening_problems(path, ink)
    sheet = path.with_suffix(".sheet.jpg")
    n = 8
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf",
                    f"fps={n / max(secs, 1):.4f},scale=270:480,tile={n}x1", "-frames:v", "1", "-q:v", "4", str(sheet)],
                   check=False)
    return {"file": str(path.resolve()), "seconds": round(secs, 1), "size": [v.get("width"), v.get("height")],
            "loudness": loud, "opening_ink": None if ink is None else round(ink, 3),
            "sheet": str(sheet.resolve()) if sheet.exists() else None,
            "probe": {k: probed.get(k) for k in ("problems", "frames", "texts")} if probed else None,
            "problems": problems}


def _sidecar(path):
    """What render_story wrote beside a video (<file>.json), or {}."""
    try:
        return json.loads(pathlib.Path(path).with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def qa(a):
    result = qa_file(a.video, formats.get(a.format))
    return out(result, 1 if result["problems"] else 0)


def package_cmd(a):
    from tt_shorts import package
    result = package.make(a.render, a.only)
    return out(result, 1 if result["problems"] else 0)


# ---------------------------------------------------------------- write / voices / doctor


def write_story(source, ref, brand=packs.DEFAULT, out_path=None, program=None, director=None, rubric=None):
    """A source reference -> a written, checked story file (+ its sources beside it). Used by `write` and the queue.
    program: news (default: the news-cluster writer, as before programs) or another program (programs.py), which
    writes from its brief, under its scenes and rule tier. Every failed writer pass is remembered (failures.py).
    director: force one (directors.py); by default variety.direct picks the least used eligible one from the facts
    code finds in the articles, before the writer runs, and the story keeps it (a code-owned field, like date).
    rubric: a rubric (rubrics.py): its eligibility must hold on the cluster's facts, the writer gets its brief and
    shape, and code stamps the story's rubric and episode (and part) after writing; an agree scene's facts are
    filled by code from all the member articles."""
    from tt_shorts import failures, sources as src, writer
    packs.load(brand)  # an unknown pack fails before any model call
    r = rubrics.get(rubric) if rubric else None
    if r:
        if program and program != r["program"]:
            raise ValueError(f"rubric {r['id']} is a {r['program']} rubric, not {program}")
        program = r["program"]
    prog = programs.get(program)
    source = source or prog["sources"][0]
    programs.check_source(prog, source)  # and a source the program doesn't take
    data = src.fetch(source, ref)
    remember = lambda found: failures.record(brand, "write", found)  # noqa: E731
    category = prog.get("category") or data["cluster"].get("category", "")
    found = directors.facts(data["articles"], category, packs.load(brand), data["cluster"])
    code_writer = prog.get("writer") == "digest"  # built by code from checked stories: no director, no model
    did = None if code_writer else variety.direct(brand, data["cluster"].get("id") or ref, found, prog["scenes"],
                                                  forced=director)
    chosen = directors.get(did) if did else None
    if r and r["count"] == "agree" and not data.get("members") and hasattr(src.get(source), "members"):
        data["members"] = src.get(source).members(ref)  # agree counts across every member, not the writer's three
    grown = rubrics.growth(brand, data) if r and r["numbering"] == "part" else None
    members = rubrics.members_of(data)
    extra, extra_types, more = "", (), (lambda s: [])
    if r:
        rf = rubrics.facts(data, brand, grown)
        if not rubrics.holds(r, rf):
            raise ValueError(f"rubric {r['id']} does not fit this story's facts (eligible: {r['eligible']}, never: "
                             f"{r['never']}); facts: " + ", ".join(f"{k} {v}" for k, v in rf.items()
                                                                     if k not in ("found", "family")))
        made = rubrics.agree_scene(members) if r["count"] == "agree" else None
        extra = rubrics.brief_block(r, {**rf, "agreed_n": (made or {}).get("n")}, grown)
        extra_types = tuple(rubrics.types(r))
        part = (grown or {}).get("part")

        def more(s):  # what the rubric adds to the writer's repair loop
            fill = rubrics.fill_agree(s, members) if r["count"] == "agree" else []
            draft = {**s, "rubric": r["id"], "episode": 1, **({"part": part} if part else {}),
                     **({"program": prog["name"]} if prog["name"] != programs.DEFAULT else {})}
            return fill + [x for x in rubrics.story_problems(draft) if not x.startswith("story:")] + \
                rubrics.length_problems(draft) + rubrics.gate_problems(draft, grown)
    try:  # failure memory: the writer reads the brand's recent mistakes; every failed pass is remembered
        if prog["name"] == programs.DEFAULT:
            story = writer.write(data["cluster"], data["articles"], avoid=variety.recent_sequences(brand),
                                 mistakes=failures.prompt_block(brand), on_problems=remember, director=chosen,
                                 facts=found, extra=extra, extra_types=extra_types,
                                 run_checks=(lambda s, a, c: writer._checks(s, a, c) + more(s) +
                                             directors.story_problems({**s, "director": did}, found)))
        else:
            story = programs.write(prog, data, brand, avoid=variety.recent_sequences(brand), on_problems=remember,
                                   director=chosen, facts=found, rubric=r, extra=extra, more_checks=more)
    except writer.ChecksFailed as e:
        failures.record(brand, "write", e.problems)
        raise
    assets.strip_code_owned(story)  # a picture and its ledger are code's: only the writer's show hints stay
    story["brand"] = brand
    story["source"] = {"name": source, "ref": str(ref)}
    if did:
        story["director"] = did  # code-owned: chosen before writing, kept on every re-render
    programs.stamp(story, prog, data["cluster"])  # program, category, the document's facts and link: data
    name = programs.story_ref(prog, data["cluster"], ref)
    if r:  # the rubric and its episode: code's, reserved before the voice (idempotent per story)
        if r["numbering"] == "part":
            name = f"{name}-part{grown['part']}"
        elif prog["name"] == programs.DEFAULT:
            name = f"{name}-{r['id']}"
        rubrics.stamp(story, r["id"], brand, store.safe(name), part=(grown or {}).get("part"))
    target = pathlib.Path(out_path) if out_path else store.story_path(brand, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    side = store.sources_path(target)  # the articles, so `check --sources` can re-run the news rules later
    texts = [m["text"] for m in members] if r and r["count"] == "agree" else data["articles"]  # agree: every member
    side.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    media = _resolve_media(target)  # the show hints -> licensed pictures, before the voice (assets.py)
    if media and media.get("changed"):
        story = json.loads(target.read_text(encoding="utf-8"))
    problems = check_story(story, texts)
    failures.record(brand, "check", problems)
    store.log("written", story=str(target), problems=problems)
    result = {"story": str(target.resolve()), "sources": str(side.resolve()), "director": did,
              "scenes": [s["type"] for s in story["scenes"]], "problems": problems,
              "warnings": directors.warnings(story, prog["scenes"]) + ((media or {}).get("errors") or [])}
    if prog["name"] != programs.DEFAULT:
        result.update(program=prog["name"], rules=prog["rules"], publish=prog["publish"], format=prog["format"])
    if r:
        result.update(rubric=r["id"], episode=story["episode"], chip=rubrics.chip(story), format=r["format"])
    return result


def write(a):
    ref = a.ref if a.ref is not None else a.cluster
    if ref is None:
        return out({"problems": ["give --ref (or --cluster for tbilisi-today)"]}, 2)
    result = write_story(a.source, ref, a.brand, a.out, a.program, a.director, a.rubric)
    return out(result, 1 if result["problems"] else 0)


def rubrics_cmd(a):
    """engine rubrics list | facts | stamp (rubrics.py)."""
    if a.action == "list":
        return out({**rubrics.options(), "episodes": rubrics.episodes(a.brand or packs.DEFAULT)})
    if a.action == "facts":
        from tt_shorts import sources as src
        if not a.ref:
            return out({"problems": ["rubrics facts needs --ref (and --source)"]}, 2)
        data = src.fetch(a.source or "tbilisi-today", a.ref)
        brand = a.brand or packs.DEFAULT
        grown = rubrics.growth(brand, data)
        f = rubrics.facts(data, brand, grown)
        prog = "digest" if data.get("stories") else "news"
        return out({"facts": {k: v for k, v in f.items() if k != "found"}, "found": f["found"], "growth": grown,
                    "eligible": rubrics.eligible(f, prog),
                    "agree": rubrics.agree_scene(rubrics.members_of(data))})
    if a.action == "stamp":
        if not (a.story and a.rubric):
            return out({"problems": ["rubrics stamp <story> --rubric <id> [--sources articles.json] [--part N]"]}, 2)
        path = pathlib.Path(a.story)
        story = json.loads(path.read_text(encoding="utf-8"))
        r = rubrics.get(a.rubric)
        problems = []
        if r["count"] == "agree":
            if not a.sources:
                return out({"problems": ["an agree story is filled from its member articles: give --sources"]}, 2)
            texts = json.loads(pathlib.Path(a.sources).read_text(encoding="utf-8"))
            if isinstance(texts, dict):
                texts = texts.get(str(story.get("id"))) or []
            problems += rubrics.fill_agree(story, texts)
        brand = brand_of(story)
        rubrics.stamp(story, r["id"], brand, store.safe(path.stem), part=a.part)
        path.write_text(json.dumps(story, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        problems += rubrics.story_problems(story)
        return out({"story": str(path), "rubric": r["id"], "episode": story["episode"], "chip": rubrics.chip(story),
                    "problems": problems}, 1 if problems else 0)
    return out({"problems": [f"unknown rubrics action {a.action}"]}, 2)


def voice_samples(a):
    argv = ["voices"] + (["--story", a.story] if a.story else []) + (["--only", a.only] if a.only else [])
    sys.argv = argv
    voices.main()
    return out({"dir": str((ROOT / "out" / "voices").resolve())})  # samples to listen to, not part of a job


def queue_cmd(a):
    from tt_shorts import queue
    if a.action == "add":
        overrides = {k: getattr(a, k) for k in ("look", "captions", "transition", "outro", "voice", "music", "platform",
                                                 "beats", "chapters", "director", "rubric", "part", "theme") if getattr(a, k)}
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
        "sound effects": "ready" if sfx.files_ready() else "composed on first use (tools/compose_sfx.py)",
        "media providers": {n: why or "available" for n, why in assets.availability().items()},
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
        "alignment python": os.environ.get("ALIGN_PYTHON") or "unset (uses this python; needs torch + transformers)",
        "writer key (OPENROUTER_API_KEY)": bool(os.environ.get("OPENROUTER_API_KEY")),
        "D1 access (CLOUDFLARE_API_TOKEN)": bool(os.environ.get("CLOUDFLARE_API_TOKEN")),
        "home (VEASY_HOME)": str(store.home()),
        "kaeasy (Georgian gate)": kaeasy.version() or f"missing in {kaeasy.directory()} (KAEASY_DIR)",
        "layout probe": "on: every render is probed (VEASY_PROBE=0 turns it off)"
                        if os.environ.get("VEASY_PROBE", "1") != "0" else "OFF (VEASY_PROBE=0): renders are not probed",
        "golden stills": f"{len(list((ROOT / 'tests' / 'golden').glob('*.json')))} in tests/golden; run "
                         "'engine selftest' before merging a visual change",
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


def _beat_args(parser):
    parser.add_argument("--beats", choices=formats.BEATS, help="on: a change inside every scene each 1.5-3 s (beats.py)")
    parser.add_argument("--chapters", choices=formats.CHAPTERS, help="the \"01 / 03\" bar (chapters.py); auto: 40 s+")


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
        r.add_argument("--outro", choices=formats.OUTROS, help="card (end card), overlay (a QR/link/CTA chip) or loop")
        _beat_args(r)
        r.add_argument("--voice", help="family or a preset (see options)")
        r.add_argument("--music", help="family, off or a family name")
        r.add_argument("--sfx", choices=formats.SFX, help="sound effects on the timeline (default: the format's, off)")
        r.add_argument("--platform", help="utm_source of the QR link")
        r.add_argument("--engine", default="gemini", choices=["gemini", "edge", "silent"])
        r.add_argument("--director", help="a director (see options: directors) instead of the story's own")
        r.add_argument("--theme", help="default (the pack's), auto (variety) or a theme's name (see options: brands)")
        r.add_argument("--out")
        if name == "still":
            r.add_argument("--frames", help="comma-separated frames (default: the middle of every scene)")
    q = sub.add_parser("qa")
    q.add_argument("video")
    q.add_argument("--format", default="news")
    pk = sub.add_parser("package")
    pk.add_argument("render", help="the render's .json manifest (or its .mp4)")
    pk.add_argument("--only", help="comma-separated: srt,vtt,cover,carousel,teaser,texts,telegram (default all)")
    w = sub.add_parser("write")
    w.add_argument("--program", help="news (default), explainer, law, blog... (see options: programs)")
    w.add_argument("--source", help="tbilisi-today (ref = cluster id), text (ref = JSON file), url, pdf, ordo, sitech "
                                    "(default: the program's first source)")
    w.add_argument("--ref", help="the story's reference in its source")
    w.add_argument("--cluster", help="same as --ref, for tbilisi-today")
    w.add_argument("--brand", default=packs.DEFAULT, help="the brand pack the story will be rendered with")
    w.add_argument("--director", help="force a director (default: the least used eligible one, variety.direct)")
    w.add_argument("--rubric", help="a rubric (see options: rubrics): number, changes, continues, agree, digest")
    w.add_argument("--out")
    ru = sub.add_parser("rubrics")
    ru.add_argument("action", choices=["list", "facts", "stamp"])
    ru.add_argument("story", nargs="?", help="stamp: the hand-written story file to stamp (in place)")
    ru.add_argument("--rubric")
    ru.add_argument("--brand")
    ru.add_argument("--source", help="facts: the source (default tbilisi-today)")
    ru.add_argument("--ref", help="facts: the cluster or file")
    ru.add_argument("--sources", help="stamp: the member articles (an agree story's facts are counted from them)")
    ru.add_argument("--part", type=int, help="stamp: a part rubric's part (default 2)")
    v = sub.add_parser("voices")
    v.add_argument("--story")
    v.add_argument("--only")
    sub.add_parser("doctor")
    pr = sub.add_parser("probe")
    pr.add_argument("story")
    pr.add_argument("--look", default="auto", help="auto (the story's own), all, or a comma-separated list")
    pr.add_argument("--format", default="news")
    pr.add_argument("--captions", choices=formats.CAPTIONS)
    pr.add_argument("--transition", choices=formats.TRANSITIONS)
    _beat_args(pr)
    pr.add_argument("--voice", help="family or a preset (it only changes the timing)")
    pr.add_argument("--platform")
    pr.add_argument("--engine", default="silent", choices=["gemini", "edge", "silent"],
                    help="silent: free, estimated timing; gemini/edge: a cached voice's real timing")
    pr.add_argument("--stills", help="also save each probed frame as a PNG in this folder")
    pr.add_argument("--theme", help="default (the pack's), auto or a theme's name; a preview theme is allowed here")
    pl = sub.add_parser("plan")
    pl.add_argument("story")
    pl.add_argument("--format", help="a format (default: the story's program's, news for news)")
    pl.add_argument("--look", choices=formats.LOOKS)
    pl.add_argument("--captions", choices=formats.CAPTIONS)
    pl.add_argument("--transition", choices=formats.TRANSITIONS)
    pl.add_argument("--outro", choices=formats.OUTROS)
    _beat_args(pl)
    pl.add_argument("--voice", help="family or a preset (the timing is the silent engine's estimate either way)")
    pl.add_argument("--music", help="family, off or a family name (the loop the render would get)")
    pl.add_argument("--sfx", choices=formats.SFX, help="sound effects (the plan counts the cues)")
    pl.add_argument("--platform")
    pl.add_argument("--director", help="a director (see options: directors) instead of the story's own")
    pl.add_argument("--theme", help="default (the pack's), auto or a theme's name; a preview theme is allowed here")
    pl.add_argument("--out", help="the contact sheet's path (default: beside where the render will go, .plan.jpg)")
    md = sub.add_parser("media")
    md.add_argument("story")
    md.add_argument("--offline", action="store_true", help="no network: keep what the ledger has, drop the rest")
    st = sub.add_parser("selftest")
    st.add_argument("--update", action="store_true", help="rewrite tests/golden/ after a deliberate visual change")
    st.add_argument("--story", help="comma-separated fixtures (default veasy-scenes,veasy-demo)")
    st.add_argument("--look", help="comma-separated looks (default all three)")
    st.add_argument("--theme", help="comma-separated: default (each fixture's pack, its default theme) and/or "
                                    "<pack>:<theme> (golden.THEMED, e.g. sitech:light); default: all of them")
    le = sub.add_parser("learn")
    le.add_argument("--brand", help="one pack (default: every pack)")
    le.add_argument("--days", type=int, default=7)
    le.add_argument("--limit", type=int, default=10)
    qp = sub.add_parser("queue")
    qp.add_argument("action", choices=["add", "list", "run", "show", "retry", "cancel"])
    qp.add_argument("id", nargs="?")
    qp.add_argument("--brand", help="a pack in brands/ (default: the story's own, else tbilisi-today)")
    qp.add_argument("--program", help="news (default; a story file's own program), explainer, law, blog...")
    qp.add_argument("--source", help="default: the program's first source (news: tbilisi-today)")
    qp.add_argument("--ref")
    qp.add_argument("--story", help="an already written story file (skips writing)")
    qp.add_argument("--format", help="default: the program's format (news: news)")
    for k in ("look", "captions", "transition", "outro", "voice", "music", "platform", "beats", "chapters", "director",
              "rubric", "theme"):
        qp.add_argument(f"--{k}")
    qp.add_argument("--part", type=int, help="add: a continues job's part (ops/daily.py sets it from the stored state)")
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
            if isinstance(sources, dict):  # tests/fixtures/sources.json: {story id: [articles]}
                if str(story.get("id")) not in sources:
                    return out({"problems": [f"{a.sources} has no articles for story {story.get('id')}"]}, 2)
                sources = sources[str(story["id"])]
            problems = check_story(story, sources) + _kaeasy_required()
            result = {"story": a.story, "news_rules": bool(sources), "kaeasy": kaeasy.version(),
                      "problems": problems, "warnings": ka_check.warnings(story)}
            if "program" in story:
                result.update(program=programs.name_of(story), rules=_rules_of(story))
            return out(result, 1 if problems else 0)
        return {"render": render, "still": still, "qa": qa, "write": write, "voices": voice_samples,
                "doctor": doctor, "queue": queue_cmd, "gc": gc_cmd, "package": package_cmd, "probe": probe_cmd,
                "plan": plan_cmd, "selftest": selftest_cmd, "media": media_cmd, "learn": learn_cmd,
                "rubrics": rubrics_cmd}[a.cmd](a)
    except (formats.FormatError, directors.DirectorError, ValueError) as e:
        return out({"problems": [str(e)]}, 2)


if __name__ == "__main__":
    sys.exit(main())
