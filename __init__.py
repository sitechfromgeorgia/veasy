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
TIMEOUTS = {"render": 1500, "write": 900, "still": 600, "queue": 3600, "package": 900, "probe": 600, "plan": 600}

HINT = (
    "[veasy] If this turn involves making, checking or fixing a video (a Short, a reel, a story video), first load "
    "skill_view('veasy:make-video') and use the veasy_* tools; they return JSON. Many videos or a daily batch: "
    "veasy_queue (skill veasy:queue). Never publish a render whose veasy_qa has problems."
)


def _python() -> str:
    env = os.environ.get("VEASY_PYTHON")
    if env:
        return env
    venv = ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def _engine(cmd: str, argv: list[str]) -> str:
    try:
        r = subprocess.run([_python(), "-m", "tt_shorts.engine", cmd, *argv], cwd=ROOT, capture_output=True,
                           text=True, timeout=TIMEOUTS.get(cmd, 300))
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


CHOICES = ("format", "look", "captions", "transition", "outro", "voice", "music", "platform", "engine", "director", "out")
STORY = {"type": "string", "description": "Path to the story JSON (absolute, or relative to the Veasy folder)."}
BRAND = {"type": "string", "description": "A brand pack in brands/ (tbilisi-today, sitech, ...; see veasy_options)."}
PROGRAM = {"type": "string", "description": "What kind of video (skill veasy:programs): news (default), explainer "
           "(any document), law (one article of Georgian law), blog (a SiTech post), or another in veasy_options."}
SOURCE = {"type": "string", "enum": ["tbilisi-today", "text", "url", "pdf", "ordo", "sitech"],
          "description": "Where the facts come from: tbilisi-today (ref = cluster id), text (ref = JSON file), url "
                         "(a web page), pdf (a file or URL), ordo (Georgian law, ref = constitution:17), sitech (a "
                         "sitech.ge post slug). Default: the program's first source."}
CHOICE_PROPS = {
    "format": {"type": "string", "description": "A show format (see veasy_options), default news."},
    "look": {"type": "string", "enum": ["auto", "editorial", "kinetic", "cards"]},
    "captions": {"type": "string", "enum": ["page", "roll"]},
    "transition": {"type": "string", "enum": ["auto", "cut", "line", "panel", "wipe", "slide", "push", "dot"],
                   "description": "The cut between scenes; auto is the look's own."},
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
    "out": {"type": "string", "description": "Output path (optional)."},
}

TOOLS = {
    "veasy_options": ({"type": "object", "properties": {"brand": BRAND}},
                      "Everything Veasy can do: brand packs, looks, caption designs, voices, music, formats, scene "
                      "types and fields, the icons and sign verbs, and one pack's defaults per category. Read it "
                      "before choosing.",
                      lambda a: _engine("options", _flags(a, ("brand",)))),
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
                        "story": STORY, **CHOICE_PROPS,
                        "frames": {"type": "string", "description": "Comma-separated frames; default the middle of every scene."}},
                     "required": ["story"]},
                    "PNG stills of a story (no full render): a quick look at the layout.",
                    lambda a: _engine("still", [a["story"]] + _flags(a, CHOICES + ("frames",)))),
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
                        **{k: CHOICE_PROPS[k] for k in ("format", "captions", "transition", "voice", "platform")},
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
                                                                         "voice", "platform", "engine", "stills")))),
    "veasy_plan": ({"type": "object", "properties": {
                       "story": STORY,
                       **{k: CHOICE_PROPS[k] for k in ("format", "look", "captions", "transition", "outro", "voice",
                                                       "music", "platform", "director")},
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
                                                                       "director", "out")))),
    "veasy_write": ({"type": "object", "properties": {
                        "program": PROGRAM,
                        "source": SOURCE,
                        "ref": {"type": "string", "description": "The story's reference in its source: a cluster id, "
                                "a JSON file, a URL, a PDF, <law>:<article> (constitution:17), a sitech.ge slug."},
                        "cluster": {"type": "integer", "description": "Shorthand: a tbilisi.today cluster id."},
                        "brand": BRAND}},
                    "Write a checked story JSON from a source (free model first; needs the writer key and, for "
                    "tbilisi-today, the D1 keys). Stored as stories/<brand>/<day>/<ref>.json under VEASY_HOME. "
                    "Returns the story path and any remaining problems.",
                    lambda a: _engine("write", _flags(a, ("program", "source", "ref", "cluster", "brand")))),
    "veasy_queue": ({"type": "object", "properties": {
                        "action": {"type": "string", "enum": ["add", "list", "run", "show", "retry", "cancel"]},
                        "id": {"type": "string", "description": "A job id (show, retry, cancel)."},
                        "program": PROGRAM,
                        "source": SOURCE,
                        "ref": {"type": "string", "description": "add: the story's reference in its source."},
                        "story": {"type": "string", "description": "add: an already written story file (skips writing)."},
                        "brand": BRAND, **{k: CHOICE_PROPS[k] for k in ("format", "look", "captions", "transition", "outro",
                                                                        "voice", "music", "platform", "engine",
                                                                        "director")},
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
                            "voice", "music", "platform", "engine", "director", "priority", "state", "max")))),
    "veasy_doctor": ({"type": "object", "properties": {}},
                     "Is this machine ready to render? ffmpeg, Remotion, fonts, music, keys, kaeasy.",
                     lambda a: _engine("doctor", [])),
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
