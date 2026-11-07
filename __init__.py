"""Veasy Hermes plugin: the video engine as agent tools, plus its skills.

The tools run the engine (`python -m tt_shorts.engine ...`) as a subprocess in this folder, with the engine's own
venv when there is one (VEASY_PYTHON, else .venv/bin/python, else this python). So the agent's process needs none of
the render dependencies, a long render can't hang the gateway's interpreter, and every tool returns the engine's
JSON as is. Handlers never raise: they return JSON with "error".
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT / "skills"
TIMEOUTS = {"render": 1500, "write": 900, "still": 600, "queue": 3600, "package": 900, "probe": 600, "plan": 600,
            "compose": 2400, "plate": 1800}

HINT = (
    "[veasy] If this turn involves making, checking or fixing a video (a Short, a reel, a story video), first load "
    "skill_view('veasy:make-video') and use the veasy_* tools; they return JSON. Many videos or a daily batch: "
    "veasy_queue (skill veasy:queue). Never publish a render whose veasy_qa has problems."
)


def _python() -> str:
    env = os.environ.get("VEASY_PYTHON")
    if env:
        return env
    for venv_dir in (ROOT / ".venv", ROOT.parent / "Veasy" / ".venv"):
        for cand in (venv_dir / "Scripts" / "python.exe", venv_dir / "bin" / "python"):
            if cand.exists():
                return str(cand)
    return sys.executable


def _engine(cmd: str, argv: list[str]) -> str:
    try:
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([_python(), "-m", "tt_shorts.engine", cmd, *argv], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", env=env, timeout=TIMEOUTS.get(cmd, 300))
        out = (r.stdout or "").strip()
        try:
            data = json.loads(out) if out else {}
        except json.JSONDecodeError:
            data = {"error": "the engine did not return JSON", "stdout": out[-1500:]}
        if r.returncode not in (0, 1):
            data.setdefault("error", f"engine exited {r.returncode}")
        if r.returncode != 0 and r.stderr:
            data["stderr"] = r.stderr.strip()[-1500:]
        return json.dumps(data, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"veasy {cmd} timed out after {TIMEOUTS.get(cmd, 300)}s"}, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001 - handlers must never raise
        return json.dumps({"error": f"veasy {cmd} failed: {e}"}, ensure_ascii=False)


def _flags(args: dict, names: tuple[str, ...]) -> list[str]:
    out = []
    for n in names:
        v = args.get(n)
        if v not in (None, ""):
            out += [f"--{n}", str(v)]
    return out


CHOICES = ("format", "look", "captions", "transition", "outro", "voice", "music", "platform", "beats", "chapters",
           "engine", "director", "out", "renderer", "style")
RENDERER = {"type": "string", "enum": ["remotion", "hyperframes"],
            "description": "The film engine instead of the story's (director, program, format, pack; default remotion). "
                           "hyperframes renders the story's composed film (veasy_compose)."}
STORY = {"type": "string", "description": "Path to the story JSON (absolute, or relative to the Veasy folder)."}
BRAND = {"type": "string", "description": "A brand pack in brands/ (tbilisi-today, sitech, ...; see veasy_options)."}
PROGRAM = {"type": "string", "description": "What kind of video (skill veasy:programs): news (default), explainer "
           "(any document), law (one article of Georgian law), blog (a SiTech post), or another in veasy_options."}
SOURCE = {"type": "string", "enum": ["tbilisi-today", "text", "url", "pdf", "ordo", "sitech", "stories"],
          "description": "Where the facts come from: tbilisi-today (ref = cluster id), text (ref = JSON file), url "
                         "(a web page), pdf (a file or URL), ordo (Georgian law, ref = constitution:17), sitech (a "
                         "sitech.ge post slug), stories (the digest: 2-3 checked story files a.json,b.json or "
                         "done:<brand>[:<day>]). Default: the program's first source."}
RUBRIC = {"type": "string", "description": "A rubric (skill veasy:rubrics): number („დღის ციფრი“), changes („რა "
          "იცვლება“), continues („ამბავი გრძელდება“), agree („ადასტურებს N გამოცემა“), digest („დილის N ამბავი“). "
          "Code checks it fits the facts, stamps the episode and draws the chip in the hook."}
CHOICE_PROPS = {
    "format": {"type": "string", "description": "A show format (see veasy_options), default news."},
    "look": {"type": "string", "enum": ["auto", "editorial", "kinetic", "cards"]},
    "captions": {"type": "string", "enum": ["page", "roll", "keyword"],
                 "description": "page (two lines that never move), roll (a teleprompter) or keyword (a dark box, the "
                                "spoken word lit, one keyword a page in the pack's style)."},
    "transition": {"type": "string", "enum": ["auto", "cut", "line", "panel", "wipe", "slide", "push", "dot", "meter"],
                   "description": "The cut between scenes; auto is the look's own; meter: equaliser bars."},
    "beats": {"type": "string", "enum": ["on", "off"],
              "description": "on (default): a change inside every scene each 1.5-3 s, on the words."},
    "chapters": {"type": "string", "enum": ["auto", "on", "off"],
                 "description": "The \"01 / 03\" chapter bar in the header: off (default), on, auto (40 s and more)."},
    "outro": {"type": "string", "enum": ["card", "overlay", "loop"],
              "description": "The ending: card (the end card, default), overlay (no end card; a QR/link/CTA chip over "
                             "the last scene) or loop (the chip, then a cross-fade into the hook: a seamless replay)."},
    "voice": {"type": "string", "description": "family or a voice preset (see veasy_options)."},
    "music": {"type": "string", "description": "family, off or a music family."},
    "platform": {"type": "string", "description": "utm_source of the QR link: shorts, youtube, instagram, tiktok."},
    "engine": {"type": "string", "enum": ["gemini", "edge", "silent"],
               "description": "gemini is the real voice; edge and silent are free previews, never to publish."},
    "director": {"type": "string", "description": "A director (skill veasy:directors): data, map, type, draw, "
                 "chronicle, witness, brief, single. Default: the story's own (code assigns it before writing)."},
    "style": {"type": "string", "description": "A named film style (skill veasy:styles; e.g. swiss-motion, pictogram-motion, countdown)."},
    "out": {"type": "string", "description": "Output path (optional)."},
    "renderer": RENDERER,
}

TOOLS = {
    "veasy_make": ({"type": "object", "properties": {
                       "request": {"type": "string", "description": "What you want, ending with what it is about: a story file or name, a cluster id, a URL, or a ref for --source. A sentence alone returns needs_input."},
                       "brand": BRAND,
                       "style": CHOICE_PROPS["style"],
                       "source": SOURCE,
                       "length": {"type": "string", "description": "short (15-30s), standard (30-45s), long (45-60s) or seconds."},
                       "scenario": {"type": "string", "description": "A plot (skill veasy:scenarios) or auto; with preview_storyboard a URL's storyboard comes back before the writer is called."},
                       "yes": {"type": "boolean", "description": "True to accept code decisions and skip question rounds."},
                       "queue": {"type": "boolean", "description": "True to add to queue instead of rendering immediately."},
                       "preview_storyboard": {"type": "boolean", "description": "True to stop after plan and return storyboard stills."},
                       "engine": {"type": "string", "enum": ["gemini", "edge", "silent"], "description": "Voice engine."},
                       "format": CHOICE_PROPS["format"],
                       "look": CHOICE_PROPS["look"],
                       "director": {"type": "string", "description": "Override director."},
                       "theme": {"type": "string", "description": "Override theme."}},
                    "required": ["request"]},
                   "The front door to Veasy: point at a story or a source ref, name at most a brand and a style, and get a "
                   "finished, checked film (a ref is written first). Facts are never guessed from the words: with "
                   "no ref it returns needs_input. Flags like --source, --format or --look override.",
                   lambda a: _engine("make", [a["request"]] + _flags(
                       a, ("brand", "style", "source", "length", "format", "look", "director", "theme", "engine", "scenario")) +
                       (["--yes"] if a.get("yes") else []) +
                       (["--queue"] if a.get("queue") else []) +
                       (["--preview-storyboard"] if a.get("preview_storyboard") else []))),
    "veasy_options": ({"type": "object", "properties": {
                          "brand": BRAND,
                          "section": {"type": "string",
                                      "description": "Optional section to inspect: summary (compact overview), "
                                                     "formats, looks, captions, voices, themes, directors, programs, "
                                                     "rubrics, scenes, icons, variety, media, brands, categories."}}},
                      "Everything Veasy can do: brand packs, looks, caption designs, voices, music, formats, scene "
                      "types and fields, icons and sign verbs, and one pack's defaults per category. Pass "
                      "section='summary' for a compact overview, or name a section to inspect.",
                      lambda a: _engine("options", _flags(a, ("brand", "section")))),
    "veasy_check": ({"type": "object", "properties": {
                        "story": STORY,
                        "sources": {"type": "string", "description": "JSON file with the member articles' texts "
                                    "(stories/<id>.sources.json); enables the news rules."}},
                     "required": ["story"]},
                    "Run every check a story must pass before rendering (structure, news rules, Georgian via kaeasy, "
                    "timing, captions). Free, seconds. problems must be empty.",
                    lambda a: _engine("check", [a["story"]] + _flags(a, ("sources",)))),
    "veasy_render": ({"type": "object", "properties": {"story": STORY, **CHOICE_PROPS}, "required": ["story"]},
                     "Render a story to an mp4 in a format (any single choice can be overridden). The gemini voice "
                     "costs about $0.01; the voice is cached per story. Takes a minute or two.",
                     lambda a: _engine("render", [a["story"]] + _flags(a, CHOICES))),
    "veasy_still": ({"type": "object", "properties": {
                        "story": STORY, **{k: v for k, v in CHOICE_PROPS.items() if k != "renderer"},
                        "frames": {"type": "string", "description": "Comma-separated frames; default the middle of every scene."}},
                     "required": ["story"]},
                    "PNG stills of a story (no full render): a quick look at the layout.",
                    lambda a: _engine("still", [a["story"]] + _flags(a, tuple(c for c in CHOICES if c != "renderer") + ("frames",)))),
    "veasy_qa": ({"type": "object", "properties": {
                     "video": {"type": "string", "description": "Path to the rendered mp4."},
                     "format": {"type": "string", "description": "The format it was rendered in (length window)."}},
                  "required": ["video"]},
                 "Check a rendered video (size, length, loudness, and the layout probe's findings from its render) "
                 "and write a contact sheet of frames. Never publish with problems.",
                 lambda a: _engine("qa", [a["video"]] + _flags(a, ("format",)))),
    "veasy_package": ({"type": "object", "properties": {
                          "render": {"type": "string", "description": "The render's .json manifest (beside its mp4), "
                                     "or the mp4 itself."},
                          "only": {"type": "string", "description": "Comma-separated subset of srt, vtt, cover, "
                                   "carousel, teaser, texts, telegram (default all)."}},
                       "required": ["render"]},
                      "One finished render -> everything a publisher needs, with no new voice and no model call: "
                      "SRT/VTT captions, a cover PNG, a 4:5 carousel (5-7 PNGs), a 6-10 s teaser, texts.json "
                      "(YouTube title + description, Instagram, Facebook, TikTok) and a Telegram post, in "
                      "<render>-package/. Seconds; problems must be empty.",
                      lambda a: _engine("package", [a["render"]] + _flags(a, ("only",)))),
    "veasy_probe": ({"type": "object", "properties": {
                        "story": STORY,
                        "look": {"type": "string", "description": "auto (the story's own look), all, or a "
                                 "comma-separated list of editorial, kinetic, cards. Default auto."},
                        **{k: CHOICE_PROPS[k] for k in ("format", "captions", "transition", "voice", "platform",
                                                        "beats", "chapters", "style")},
                        "engine": {"type": "string", "enum": ["silent", "edge", "gemini"],
                                   "description": "silent (default, free, estimated timing) or a voice already "
                                                  "cached for this story (its real timing)."},
                        "stills": {"type": "string", "description": "A folder to also save each probed frame as a "
                                   "PNG, to look at."}},
                     "required": ["story"]},
                    "The layout probe: renders each scene at its settled frame and checks where every text really "
                    "is: inside the scene band (y<=1380), nothing right of x=940 below y=1100, inside the frame, no "
                    "overflow, the brand font with every glyph, no text shrunk too small. Free, about 5 s a look. "
                    "Every render runs it too; problems must be empty.",
                    lambda a: _engine("probe", [a["story"]] + _flags(a, ("look", "format", "captions", "transition",
                                                                         "voice", "platform", "beats", "chapters",
                                                                         "engine", "stills", "style")))),
    "veasy_plan": ({"type": "object", "properties": {
                       "story": STORY,
                       **{k: CHOICE_PROPS[k] for k in ("format", "look", "captions", "transition", "outro", "voice",
                                                       "music", "platform", "beats", "chapters", "director", "style")},
                       "out": {"type": "string", "description": "Where to write the contact sheet (default: beside "
                               "where the render will go, <render>.plan.jpg)."}},
                    "required": ["story"]},
                   "A free storyboard before paying for a voice (no TTS, no model call, records nothing): each "
                   "scene's times, narration words, caption pages and reading load (every text needs 0.5 s + 0.3 s "
                   "a word), the variety picks the render will get, the motion rules (warnings; unreadable text "
                   "would hold the render), the layout probe and a half-size contact sheet to look at. About 5 s. "
                   "Run it before veasy_render; problems must be empty.",
                   lambda a: _engine("plan", [a["story"]] + _flags(a, ("format", "look", "captions", "transition",
                                                                       "outro", "voice", "music", "platform",
                                                                       "beats", "chapters", "director", "style", "out")))),
    "veasy_critique": ({"type": "object", "properties": {
                           "story": STORY,
                           "format": CHOICE_PROPS["format"],
                           "look": CHOICE_PROPS["look"],
                           "director": CHOICE_PROPS["director"]},
                        "required": ["story"]},
                       "Automated pre-flight visual and pacing critique checklist on plan stills before rendering: "
                       "evaluates safe zones, text reading load, static stretches, novelty, hook pacing, and brand contrast. "
                       "Returns an overall grade (PASS, NEEDS_ATTENTION, FAIL), score (0-100), checklist items, and "
                       "contact sheet path.",
                       lambda a: _engine("critique", [a["story"]] + _flags(a, ("format", "look", "director")))),
    "veasy_dry_run": ({"type": "object", "properties": {
                          "story": STORY,
                          "format": CHOICE_PROPS["format"],
                          "engine": CHOICE_PROPS["engine"],
                          "director": CHOICE_PROPS["director"]},
                       "required": ["story"]},
                      "A free pre-flight cost and timing calculator before rendering (costs $0.00, zero API calls): "
                      "calculates word count, spoken seconds, estimated TTS cost, monthly budget status, and whether "
                      "the voice and bundle are already cached.",
                      lambda a: _engine("dry-run", [a["story"]] + _flags(a, ("format", "engine", "director")))),
    "veasy_write": ({"type": "object", "properties": {
                        "program": PROGRAM,
                        "source": SOURCE,
                        "ref": {"type": "string", "description": "The story's reference in its source: a cluster id, "
                                "a JSON file, a URL, a PDF, <law>:<article> (constitution:17), a sitech.ge slug."},
                        "cluster": {"type": "integer", "description": "Shorthand: a tbilisi.today cluster id."},
                        "brand": BRAND, "rubric": RUBRIC, "style": CHOICE_PROPS["style"]}},
                    "Write a checked story JSON from a source (free model first; needs the writer key and, for "
                    "tbilisi-today, the D1 keys). Stored as stories/<brand>/<day>/<ref>.json under VEASY_HOME. "
                    "Returns the story path and any remaining problems.",
                    lambda a: _engine("write", _flags(a, ("program", "source", "ref", "cluster", "brand", "rubric", "style")))),
    "veasy_concept": ({"type": "object", "properties": {
                          "program": PROGRAM,
                          "source": SOURCE,
                          "ref": {"type": "string", "description": "The story's reference in its source."},
                          "batch": {"type": "string", "description": "A JSON file of [{source, ref}]: a run."},
                          "brand": BRAND,
                          "ideas": {"type": "string", "description": "A JSON file of your own ideas: judged the same "
                                                                     "way, with no model call."}}},
                      "The idea step alone (skill veasy:direct): ideas from named rungs of a ladder, judged and chosen "
                      "by code, before any script. Free of voice and render, nothing recorded. Returns every idea with "
                      "its verdict and the chosen concept.",
                      lambda a: _engine("concept", _flags(a, ("program", "source", "ref", "batch", "brand", "ideas")))),
    "veasy_rubrics": ({"type": "object", "properties": {
                          "action": {"type": "string", "enum": ["list", "facts", "stamp"]},
                          "story": {"type": "string", "description": "stamp: a hand-written story file (stamped in place)."},
                          "rubric": RUBRIC, "brand": BRAND, "source": SOURCE,
                          "ref": {"type": "string", "description": "facts: the cluster or file to judge."},
                          "sources": {"type": "string", "description": "stamp: the member articles (JSON list or "
                                      "{id: [texts]}); an agree story's facts are counted from them."},
                          "part": {"type": "integer", "description": "stamp: a continues story's part (default 2)."}},
                       "required": ["action"]},
                      "The rubrics (named recurring shows with a chip „დღის ციფრი · #12“, a scene shape and a time "
                      "slot): list them with the brand's episode counters; facts: which rubrics a cluster may be "
                      "(the facts code finds, what it gained since its last video, the facts its outlets state "
                      "alike); stamp: give a hand-written story its rubric and episode (code's, never the writer's).",
                      lambda a: _engine("rubrics", [a["action"]] + ([a["story"]] if a.get("story") else []) + _flags(
                          a, ("rubric", "brand", "source", "ref", "sources", "part")))),
    "veasy_scenario": ({"type": "object", "properties": {
                           "action": {"type": "string", "enum": ["list", "fit", "stamp", "board", "check"]},
                           "story": {"type": "string", "description": "fit, stamp, check: a story file; board: a scenario id."},
                           "scenario": {"type": "string", "description": "stamp: the plot's id, or auto for the best fit."},
                           "length": {"type": "string", "description": "fit: short, standard, long or seconds."}},
                        "required": ["action"]},
                       "The scenarios (skill veasy:scenarios): the plots a film can follow, each beat with a job, a word "
                       "budget, scene types and a sound. list them; fit: rank those a story's facts allow, with the "
                       "reason; board: one plot's storyboard before any cost; stamp: set the plot on a hand-written "
                       "story (code's, never the writer's); check: the free beat checks. news refuses every scenario.",
                       lambda a: _engine("scenario", [a["action"]] + ([a["story"]] if a.get("story") else []) +
                                         _flags(a, ("scenario", "length")))),
    "veasy_queue": ({"type": "object", "properties": {
                        "action": {"type": "string", "enum": ["add", "list", "run", "show", "retry", "cancel", "approve",
                                                             "reject"]},
                        "renderer": RENDERER,
                        "id": {"type": "string", "description": "A job id (show, retry, cancel)."},
                        "program": PROGRAM,
                        "source": SOURCE,
                        "ref": {"type": "string", "description": "add: the story's reference in its source."},
                        "story": {"type": "string", "description": "add: an already written story file (skips writing)."},
                        "brand": BRAND, "rubric": RUBRIC,
                        "part": {"type": "integer", "description": "add: a continues job's part (ops/daily.py sets it)."},
                        **{k: CHOICE_PROPS[k] for k in ("format", "look", "captions", "transition", "outro",
                                                        "voice", "music", "platform", "beats", "chapters", "engine",
                                                        "director", "style")},
                        "priority": {"type": "integer", "description": "add: higher runs first (default 0)."},
                        "state": {"type": "string", "enum": ["queued", "writing", "rendering", "done", "held",
                                                             "failed", "cancelled"], "description": "list: filter."},
                        "max": {"type": "integer", "description": "run: jobs to process this time (default 5)."}},
                     "required": ["action"]},
                    "The job queue: add a video (same request twice = the same job), list jobs and counts, run up to "
                    "max queued jobs (write, check, render, qa; one worker at a time), show/retry/cancel one. A done "
                    "job passed QA; held means rendered but QA found problems; failed has error_class and error.",
                    lambda a: _engine("queue", [a["action"]] + ([str(a["id"])] if a.get("id") else []) + _flags(
                        a, ("program", "source", "ref", "story", "brand", "format", "look", "captions", "transition", "outro",
                            "voice", "music", "platform", "beats", "chapters", "engine", "director", "rubric", "part", "renderer",
                            "style", "priority", "state", "max")))),
    "veasy_compose": ({"type": "object", "properties": {
                          "action": {"type": "string", "enum": ["scaffold", "check", "look", "render", "promote",
                                                                "templates", "blocks"]},
                          "story": {"type": "string", "description": "scaffold/check/look/render: the story JSON."},
                          "project": {"type": "string", "description": "The HyperFrames project folder (default: "
                                      "$VEASY_HOME/cache/compose/<brand>-<ref>); promote: the film to promote."},
                          "brand": BRAND,
                          "template": {"type": "string", "description": "scaffold/render: start from templates/<id> "
                                       "(auto: the least used for the brand)."},
                          "blocks": {"type": "string", "description": "scaffold: block ids to assemble, comma-"
                                     "separated (action blocks lists them)."},
                          "video": {"type": "string", "description": "look: a rendered file to measure the sound of."},
                          "from": {"type": "string", "description": "scaffold: copy the agent's files (index.html, "
                                   "compositions/, beats.json) from this folder."},
                          "force": {"type": "boolean", "description": "scaffold: replace the project's own files."},
                          "sources": {"type": "string", "description": "check/render: the member articles (default "
                                      "<story>.sources.json)."},
                          "engine": {"type": "string", "enum": ["gemini", "edge", "silent"],
                                     "description": "The voice (scaffold/check default silent; render default gemini)."},
                          "format": CHOICE_PROPS["format"],
                          "style": CHOICE_PROPS["style"],
                          "as": {"type": "string", "description": "promote: the template id (lowercase, hyphens)."},
                          "label": {"type": "string", "description": "promote: the template's name."}},
                       "required": ["action"]},
                      "Films an agent composes for the HyperFrames engine (skill veasy:compose): scaffold a project "
                      "(the pack's frame.md and tokens, facts.json, timing.json with the voice's words and the beats, "
                      "the locked chrome and captions), check it (our lint, the probe at every beat, the story's rules, "
                      "Georgian and kaeasy on every text the DOM shows, hyperframes check; problems must be empty), "
                      "look at it (free: a sheet of its scenes and beats, a strip across every cut, the frames at "
                      "phone width, its timeline), render it (pinned HyperFrames, the ffmpeg mix, QA), promote an "
                      "approved film to a template.",
                      lambda a: _engine("compose", [a["action"]] + (
                          [a["project"]] if a["action"] == "promote" and a.get("project") else
                          [a["story"]] if a.get("story") else []) + _flags(
                          a, ("brand", "template", "blocks", "sources", "engine", "format", "style", "label",
                              "video")) +
                          (["--project", a["project"]] if a.get("project") and a["action"] != "promote" else []) +
                          (["--from", a["from"]] if a.get("from") else []) + (["--as", a["as"]] if a.get("as") else []) +
                          (["--force"] if a.get("force") else []))),
    "veasy_doctor": ({"type": "object", "properties": {}},
                     "Is this machine ready to render? ffmpeg, Remotion, fonts, music, keys, kaeasy.",
                     lambda a: _engine("doctor", [])),
    "veasy_plate": ({"type": "object", "properties": {
                        "kind": {"type": "string", "description": "A plate kind (veasy_options section plates lists "
                                 "them), or list (the baked library) or check (lint every kind)."},
                        "seconds": {"type": "number", "description": "Length in seconds (default 6)."},
                        "seed": {"type": "integer", "description": "The seed: one seed, one plate (default 1)."},
                        "scale": {"type": "number", "description": "Bake at this fraction of 1080x1920; 0.5 is a preview."},
                        "spec": {"type": "string", "description": "A JSON file for the kind's own setup."},
                        "brand": BRAND,
                        "program": {"type": "string", "description": "The story's program: news is refused."},
                        "family": {"type": "string", "description": "The story's family: crime is refused."},
                        "text": {"type": "string", "description": "The story's words: deaths, crime and incidents are refused."}},
                     "required": ["kind"]},
                    "A baked plate for a scene (skill veasy:plates): a slow grey clip drawn once in headless Chrome, toned "
                    "into every pack's canvas and ink, cached by content. A second call answers from the cache. Returns "
                    "the hash, the clips per pack and theme, the anchors file and what a frame cost. Refused for news, "
                    "crime, incidents and deaths. Baking takes minutes: a queue job never bakes, it picks from the shelf.",
                    lambda a: _engine("plate", [a["kind"]] + _flags(a, ("seconds", "seed", "scale", "spec", "brand", "program",
                                                                         "family", "text")))),
    "veasy_brand": ({"type": "object", "properties": {
                        "action": {"type": "string", "enum": ["new"]},
                        "name": {"type": "string", "description": "The brand identifier (lowercase, hyphens)."},
                        "from": {"type": "string", "description": "Path or URL to brand guidelines, design.md, frame.md or web page."},
                        "no_sheets": {"type": "boolean", "description": "Skip rendering contact sheets (faster)."}},
                     "required": ["action", "name", "from"]},
                    "Brand pack operations (skill veasy:brands): draft a new brand pack from any brand book "
                    "or website URL (engine brand new <name> --from <source>), validate WCAG contrast and schema, "
                    "and render preview contact sheets in dark and light themes.",
                    lambda a: _engine("brand", [a["action"], a["name"], "--from", a["from"]] + (["--no-sheets"] if a.get("no_sheets") else []))),
}


def _handler(fn):
    def run(args: dict, **kwargs) -> str:
        try:
            return fn(args or {})
        except KeyError as e:
            return json.dumps({"error": f"missing argument {e}"}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return run


def _hint(is_first_turn: bool = False, **kwargs):
    if not is_first_turn or os.environ.get("VEASY_HINT", "1") == "0":
        return None
    return {"context": HINT}


def register(ctx):
    for child in sorted(SKILLS_DIR.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)
    for name, (params, description, fn) in TOOLS.items():
        ctx.register_tool(name=name, toolset="veasy", schema={"name": name, "description": description,
                                                               "parameters": params}, handler=_handler(fn))
    ctx.register_hook("pre_llm_call", _hint)
