"""The compose lane: films an agent composes in HTML/CSS/GSAP and HyperFrames renders (docs/plan-v2.md, phase 2).

Veasy has two film engines, both first-class: Remotion (the typed brush kit, NewsShort) and HyperFrames (this). A
video's engine is `"engine": "remotion" | "hyperframes"`: a director's, else the program's, else the format's, else
the pack's, else remotion (engine_for). Whatever the engine, the film gets the same Veasy around it: the story and
its facts, the voice and its word timings, captions.py's pages, the brand pack, the ffmpeg mix (props.mix_audio),
the checks, QA, the queue.

    python -m tt_shorts.engine compose scaffold <story> [--brand] [--project DIR] [--from DIR | --template ID|auto]
    python -m tt_shorts.engine compose check    <story> [--brand] [--project DIR] [--sources FILE]
    python -m tt_shorts.engine compose look     <story> [--brand] [--project DIR] [--video FILE]  # see it, free
    python -m tt_shorts.engine compose render   <story> [--brand] [--project DIR] [--format] [--engine silent]
    python -m tt_shorts.engine compose promote  <project> --as <id>        # an approved film -> templates/<id>/
    python -m tt_shorts.engine compose templates                           # the templates and their slots

A project (default store.compose_dir: $VEASY_HOME/cache/compose/<brand>-<ref>/) holds two kinds of files:

  the agent's   index.html (the root: background and one host per scene), compositions/<scene>.html, beats.json
                (chapters and beats anchored to the narration's words), assets/art/ (its own SVGs), slots.json
                (a template's slots, filled by the agent)
  Veasy's       story.json, facts.json, timing.json, frame.md, assets/brand.css, assets/fonts/, assets/vendor/
                gsap.min.js, assets/icons/, assets/qr.svg, assets/map-*.svg, assets/logo-*.svg, assets/media/
                (the story's asset ledger, phase 1), the locked compositions/chrome.html and captions.html, and
                .veasy/lock.json (the sha256 of every Veasy file; CHROME_VERSION is the locked set's version)

Facts are bound, not typed. Every fact a scene shows (a number, a date, a time, a name, a quote, a source, the
date and time of the story) is a HyperFrames variable declared on index.html's <html> from facts.json, and a scene
binds it with `data-var-text="num-1"` (or reads `window.__hyperframes.getVariables()`). Beats are variables too
(`beat-<id>`: seconds), and a host may be timed by its beats (`data-beat="number" data-until="when"`, shifts in
`data-beat-shift`/`data-until-shift`), so a film keeps its timing under another voice. `compose check` lints the
agent's files (LINT), reads every text from the DOM at the beats' settled frames and through every cut, where two
scenes are live at once and may sit on each other (compose/probe.mjs, cut_problems), and runs the
story's rule tier (news, claims, law, story), ka_check and kaeasy on them, the layout probe's rules, and
`hyperframes check`.

HyperFrames runs only through hyperframes() here: telemetry, update checks, skill installs and auto-installs off
(ENV), the subcommands that upload, call HeyGen or fetch code refused (REFUSED), and so are an allowed subcommand's
flags that send a film out (OFFSITE). Renders are pinned (RENDER).
"""
import collections
import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import time
import zlib

from tt_shorts import brand as packs
from tt_shorts import blocks as blk
from tt_shorts import captions, formats, frame_md, icons, kaeasy, meta, probe, programs, speech, store

ROOT = speech.ROOT
COMPOSE = ROOT / "compose"
TEMPLATES = ROOT / "templates"
HF = COMPOSE / "node_modules" / "hyperframes"
HF_BIN = HF / "bin" / "hyperframes.mjs"
HF_VERSION = "0.9.8"  # compose/package.json pins it
GSAP = HF / "dist" / "vendor" / "npm" / "gsap@3.15.0" / "dist" / "gsap.min.js"
PROBE_JS = COMPOSE / "probe.mjs"
CHROME_VERSION = 3  # the locked set (chrome, captions, end card); 3 fits a long link and CTA, 1 was the phase 0 spike's
FPS = speech.FPS
W, H, SIDE = 1080, 1920, 64
WIPE = 0.34  # seconds the meter bars take to rise (and again to fall) around a chapter cut
BARS = 12
# every hyperframes call: no telemetry (PostHog), no update check, no skill install, no auto-install
ENV = {"HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1",
       "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_NO_AUTO_INSTALL": "1"}
# what an agent may run through Veasy; the rest upload a project, call HeyGen's (paid) services, fetch code from the
# registry or send reports (plan-v2 § Phase 0 result, "Surprises")
ALLOWED = ("render", "lint", "check", "validate", "inspect", "compositions", "timeline", "info", "snapshot", "docs",
           "keyframes", "preview", "play", "measure", "audio", "compare", "diff", "browser", "doctor", "clean", "help")
REFUSED = ("publish", "cloud", "lambda", "tts", "media-use", "feedback", "add", "cloudrun", "auth", "billing",
           "reverse", "open", "catch-up", "skills", "upgrade", "telemetry", "capture", "catalog", "transcribe",
           "models", "remove-background", "init", "beats", "media-treatment", "present")
# an allowed subcommand's flags that send a film out: snapshot --describe to Gemini, audio's providers to HeyGen
OFFSITE = ("--describe", "--provider")
AUDIO_QUALITY = "fast"  # audio's signal measures, all on this machine (its "best" uploads to HeyGen, maybe billed)
# pinned so a film renders to the same frames on the same machine (phase 0: changing the workers changed 831 of
# 1107 frames slightly; software GL is what a GPU-less server has)
RENDER = {"workers": 4, "browser_gpu": False, "quality": "looks", "fps": FPS}
LOCKED = ("compositions/chrome.html", "compositions/captions.html")
SCENE_TOP_Z = 30  # the chrome's host z-index: no scene host may sit on top of it
CODE_KIND = "code"  # facts that are the data's (date, time, sources, link): shown, not claimed by the writer
DONE_FILE = ".veasy/lock.json"
LOOK_DIR = ".veasy/look"  # engine compose look's sheets and reports
NOTES = ("STORYLINES.md", "SPEC.md")  # the film's idea and its shots, written before its scenes (veasy:compose)
REVIEW_NOTE = "REVIEW.md"  # a fresh eye's notes on the sheets, written before the real voice is paid for


class ComposeError(ValueError):
    pass


def esc(s):
    import html
    return html.escape(str(s), quote=True)


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- HyperFrames, locked down


def _offsite(args):
    """The flags in a HyperFrames call that would send the film to an outside service -> [flag]."""
    names = [a.split("=")[0] for a in args]
    out = [n for n in names if n in OFFSITE]
    if args and args[0] == "audio":
        at = names.index("--quality") if "--quality" in names else None
        given = None if at is None else args[at].split("=", 1)[1] if "=" in args[at] else (args[at + 1:] or [None])[0]
        if given != AUDIO_QUALITY:
            out.append(f"--quality {given}")
    return out


def hyperframes(args, cwd=None, timeout=1800):
    """Run the pinned HyperFrames CLI (node compose/node_modules/hyperframes/bin/hyperframes.mjs, never npx: no
    install on the fly) with ENV. Refuses a subcommand outside ALLOWED and a flag in OFFSITE. -> CompletedProcess
    (text)."""
    args = [str(a) for a in args]
    sub = args[0] if args else ""
    if sub in REFUSED or sub not in ALLOWED:
        why = "it uploads, calls HeyGen, fetches code or reports usage" if sub in REFUSED else "not allowed"
        raise ComposeError(f"hyperframes {sub or '(nothing)'} is refused ({why}): use engine compose "
                           f"scaffold|check|look|render; allowed: {', '.join(ALLOWED)}")
    offsite = _offsite(args)
    if offsite:
        raise ComposeError(f"hyperframes {sub} {offsite[0]} is refused: a film stays on this machine")
    if not HF_BIN.exists():
        raise ComposeError(f"HyperFrames {HF_VERSION} is not installed: (cd compose && npm ci)")
    node = shutil.which("node") or "node"
    return subprocess.run([node, str(HF_BIN), *args], cwd=str(cwd or COMPOSE), env={**os.environ, **ENV},
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def engine_for(story, fmt=None, director=None, override=None):
    """-> (engine, why): the film engine of a story. An explicit override (--renderer), else the director's, else the
    program's, else the format's, else the pack's, else remotion."""
    from tt_shorts import directors
    if override:
        return formats.engine_value(override, "--renderer", ComposeError), "override"
    did = director or story.get("director")
    if did:
        d = directors.get(did)
        if d.get("engine"):
            return d["engine"], f"director {did}"
    try:
        p = programs.of(story)
    except programs.ProgramError:
        p = {}
    if p.get("engine"):
        return p["engine"], f"program {p['name']}"
    if fmt and fmt.get("engine"):
        return fmt["engine"], f"format {fmt.get('name')}"
    b = packs.of(story)
    if b.get("engine"):
        return b["engine"], f"brand {b['name']}"
    return formats.DEFAULT_ENGINE, "default"


def review_for(story, fmt=None):
    """The review policy of a composed film -> (policy, n, why): the format's `review`, else the program's, else
    formats.DEFAULT_REVIEW (always)."""
    try:
        p = programs.of(story)
    except programs.ProgramError:
        p = {}
    for where, src in ((f"format {(fmt or {}).get('name')}", fmt or {}), (f"program {p.get('name')}", p)):
        if src.get("review"):
            kind, n = formats.review_policy(src["review"], where, ComposeError)
            return kind, n, where
    return formats.DEFAULT_REVIEW, None, "default"


def project_dir(story, brand=None):
    b = packs.load(brand or story.get("brand"))
    return store.compose_dir(b["name"], story["id"])


# ---------------------------------------------------------------- timing: the voice's words, the beats


def resolve(beats, words):
    """The beat sheet's anchors -> seconds, in order (speech.anchor: each search starts after the previous one)."""
    out, after = [], 0
    for b in beats:
        if not b.get("at"):
            raise ComposeError(f"beat {b.get('id')!r} has no anchor: give it \"at\" (the first narration words it "
                               "lands on)")
        try:
            t, _ = speech.anchor(words, b["at"], after)
        except (ValueError, RuntimeError) as e:
            raise ComposeError(f"beat {b.get('id')!r}: anchor „{b['at']}“ is not in the narration after the "
                               f"previous beat ({e})") from e
        after = next(i for i, w in enumerate(words) if w["start"] == t) + 1  # the next beat may share words
        out.append({**b, "t": round(t, 3)})
    return out


def _anchor(words, phrase, what):
    try:
        return speech.anchor(words, phrase)[0]
    except (ValueError, RuntimeError) as e:
        raise ComposeError(f"{what}: anchor „{phrase}“ is not in the narration ({e})") from e


def timing(story_path, sheet, engine="silent", music="off", tone=None, theme="default", fmt=None):
    """-> (timing dict, the Remotion props of the same story: voice, words, captions, pack; their work dir)."""
    from tt_shorts import props
    # the format's caption design and render keys (formats.render_keys) as Lane A gets them: the captions, the
    # voice and the words are the same for both engines
    work, p = props.build(str(story_path), "cards", engine, tone, music=music, transition="cut", theme=theme,
                          caption_design=(fmt or {}).get("captions"), **(formats.render_keys(fmt) if fmt else {}))
    words = p["words"]
    keys = {speech.norm(k) for k in sheet.get("keywords", [])}
    dur = p["durationInFrames"] / FPS
    chapters = []
    if not sheet.get("chapters"):
        raise ComposeError("beats.json has no chapters (at least one: {\"title\", \"at\"})")
    for i, ch in enumerate(sheet["chapters"]):
        t = 0.0 if i == 0 else round(_anchor(words, ch.get("at") or "", f"chapter {i + 1}") - 0.08, 3)
        chapters.append({"n": i + 1, "of": len(sheet["chapters"]), "title": ch.get("title") or "", "from": t})
    end = round(_anchor(words, (sheet.get("end") or {}).get("at") or "", "end") - 0.08, 3)
    for a, b in zip(chapters, chapters[1:] + [{"from": end}]):
        a["to"] = b["from"]
    beats = resolve(sheet.get("beats") or [], words)
    if not beats:
        raise ComposeError("beats.json has no beats")
    beats[0]["t"] = 0.0  # frame 0 is the hook
    gaps = [round(b["t"] - a["t"], 2) for a, b in zip(beats, beats[1:])] or [0.0]
    where = next((s for s in p["scenes"] if s.get("map")), None)
    return {
        "about": "Written by tt_shorts/compose.py from the story, the voice and beats.json: do not edit.",
        "story": p["id"], "brand": p["brand"]["name"], "theme": p["theme"], "engine": engine, "fps": FPS,
        "frames": p["durationInFrames"], "duration": round(dur, 3), "width": W, "height": H,
        "words": [{"i": i, "text": w["text"], "start": w["start"], "end": w["end"],
                   "keyword": speech.norm(w["text"]) in keys} for i, w in enumerate(words)],
        "chapters": chapters, "end": end, "wipes": [c["from"] for c in chapters[1:]] + [end],
        "beats": beats, "gaps": {"min": min(gaps), "max": max(gaps), "over_3s": [
            beats[i + 1]["id"] for i, g in enumerate(gaps) if g > 3 and beats[i + 1].get("id") != "cta"]},
        "laneA": [{"type": s["type"], "from": round(s["from"] / FPS, 3), "to": round((s["from"] + s["duration"]) / FPS, 3)}
                  for s in p["scenes"]],
        "facts": {"date": p["date"], "category": p["category"], "sources": p["sources"], "sourcesLine": p["sourcesLine"],
                  "url": p["url"], "cta": p["cta"], "previewNote": p["previewNote"]},
        "map": {k: where["map"][k] for k in ("viewBox", "focus", "pins", "level", "credit")} | {
            "occupied": [{k: o[k] for k in ("id", "label", "at", "r", "in_focus")} for o in where["map"].get("occupied") or []]}
               if where else None,
        "sfx": [{"t": b["t"], "name": b["sfx"]} for b in beats if b.get("sfx")],  # beats that name a sound effect
    }, p, work


# ---------------------------------------------------------------- facts: what a scene may show, bound by id


def _put(out, fid, value, kind, where):
    if value in (None, "", []) or fid in out:
        return
    out[fid] = {"value": str(value), "kind": kind, "from": where}


def facts(story, b, p, t=None):
    """The story's facts as {id: {value, kind, from}}: the data's (date, time, weekday, category, link, CTA, sources;
    kind "code"), and the story's own (numbers, dates, times, quotes, names, every on-screen text of its scenes, its
    `facts` map and `characters`). A scene shows them through data-var-text="<id>"; check() reads what it drew."""
    from tt_shorts import claims_check, ka_check, news_check
    out = {}
    d = p["date"]
    for fid, v in (("date", d["date"]), ("time", d["time"]), ("weekday", d["weekday"]), ("category", p["category"]),
                   ("url", p["url"]), ("cta", p["cta"]), ("brand", b["label"]), ("sources-line", p["sourcesLine"])):
        _put(out, fid, v, CODE_KIND, "data")
    if p["sources"]:
        _put(out, "sources-n", len(p["sources"]), CODE_KIND, "data")
    for i, s in enumerate(p["sources"]):
        _put(out, f"source-{i + 1}", s, CODE_KIND, "data")
    if t and t.get("map"):
        _put(out, "map-credit", t["map"]["credit"], CODE_KIND, "the map's licence")
        label = next((o["label"] for o in t["map"].get("occupied") or [] if o.get("label")), "")
        if label:  # the pack's word for the occupied territories: a scene that shows the map writes it in ink beside them
            _put(out, "map-occupied", label, CODE_KIND, "the pack's label of the occupied territories")
    screen = [x for _, x in ka_check.screen_texts(story)]
    texts = screen + [story.get("narration", "")]
    kinds = (("date", news_check._DAY_MONTH), ("time", news_check._TIME), ("quote", re.compile(r"„[^“”]+[“”]")),
             ("num", re.compile(r"(?<![\d:])\d+(?:[.,]\d+)?(?![\d:])")))
    for kind, rx in kinds:
        seen = []
        for text in texts:
            for m in rx.finditer(text):
                if m.group(0) not in seen:
                    seen.append(m.group(0))
        for k, v in enumerate(seen):
            _put(out, f"{kind}-{k + 1}", v, kind, "the story")
    names = []
    for text in texts:
        names += [n for n in claims_check.LATIN_NAME.findall(text) if len(n) > 2 and n[0].isupper()]
    for s in story.get("scenes") or []:
        names += [it.get("name") for it in s.get("items") or [] if isinstance(it, dict) and it.get("name")]
        if s.get("type") == "quote" and s.get("by"):
            names.append(s["by"])
    for k, n in enumerate(dict.fromkeys(names)):
        _put(out, f"name-{k + 1}", n, "name", "the story")
    for k, c in enumerate(story.get("characters") or []):
        _put(out, f"character-{k + 1}", c, "name", "the story's characters")
    for k, v in (story.get("facts") or {}).items():
        _put(out, f"fact-{store.safe(k)}", v, "fact", "the story's facts")
    for i, s in enumerate(story.get("scenes") or []):  # every on-screen text the writer gave a scene (checked)
        for key, v in s.items():
            if key in news_check.NOT_SCREEN or key in ("svg", "type"):
                continue
            base = f"scene-{i}-{store.safe(key)}"
            if isinstance(v, (str, int, float)) and not isinstance(v, bool):
                _put(out, base, v, "words", f"scene {i} ({s.get('type')}) {key}")
            elif isinstance(v, list):
                for j, it in enumerate(v):
                    if isinstance(it, (str, int, float)) and not isinstance(it, bool):
                        _put(out, f"{base}-{j}", it, "words", f"scene {i} {key}[{j}]")
                    elif isinstance(it, dict):
                        for f, x in it.items():
                            if isinstance(x, (str, int, float)) and not isinstance(x, bool):
                                _put(out, f"{base}-{j}-{store.safe(f)}", x, "words", f"scene {i} {key}[{j}].{f}")
            elif isinstance(v, dict):
                for f, x in v.items():
                    if isinstance(x, (str, int, float)) and not isinstance(x, bool):
                        _put(out, f"{base}-{store.safe(f)}", x, "words", f"scene {i} {key}.{f}")
    return out


def slot_values(project, fx):
    """A template's slots (slots.json: {slot: {kind, example, value}}) resolved: "=<fact id>" -> that fact's value,
    else the words given. -> ({slot: value}, [problems])."""
    path = pathlib.Path(project) / "slots.json"
    if not path.exists():
        return {}, []
    slots = json.loads(path.read_text(encoding="utf-8"))
    vals, bad = {}, []
    for sid, spec in slots.items():
        if sid.startswith("_"):
            continue
        v = (spec or {}).get("value")
        if v in (None, ""):
            bad.append(f"slot {sid} ({spec.get('kind')}) is empty: fill slots.json (\"=<fact id>\" or words; "
                       f"example: {spec.get('example')!r})")
            continue
        if isinstance(v, str) and v.startswith("="):
            fid = v[1:]
            if fid not in fx:
                bad.append(f"slot {sid}: no fact {fid!r} (facts.json lists them)")
                continue
            if spec.get("kind") not in (None, "words") and fx[fid]["kind"] not in (spec["kind"], "words", "fact"):
                bad.append(f"slot {sid} wants a {spec['kind']}, {fid} is a {fx[fid]['kind']}")
            vals[sid] = fx[fid]["value"]
        elif spec.get("kind") not in (None, "words"):
            bad.append(f"slot {sid} is a {spec['kind']}: bind it to the story's fact (\"=<fact id>\"), never type it")
        else:
            vals[sid] = str(v)
    return vals, bad


def variables(fx, t, hosts, slots=None):
    """HyperFrames variable declarations: every fact and slot (string), every beat, chapter and host (seconds)."""
    out = [{"id": k, "type": "string", "label": f"{v['kind']}: {v['from']}", "default": v["value"]} for k, v in fx.items()]
    out += [{"id": k, "type": "string", "label": "slot", "default": v} for k, v in (slots or {}).items()]
    out += [{"id": f"beat-{b['id']}", "type": "number", "label": "beat (s)", "default": b["t"]} for b in t["beats"]]
    out += [{"id": f"chapter-{c['n']}", "type": "number", "label": "chapter (s)", "default": c["from"]}
            for c in t["chapters"]]
    out += [{"id": f"host-{h}", "type": "number", "label": "host start (s)", "default": s} for h, s in hosts.items()]
    out += [{"id": "film-end", "type": "number", "label": "the end card (s)", "default": t["end"]},
            {"id": "film-duration", "type": "number", "label": "the film (s)", "default": t["duration"]}]
    return out


# ---------------------------------------------------------------- index.html: bind facts and beats

TAG = re.compile(r"<[a-zA-Z][^<>]*>")


def _attr(tag, name):
    m = re.search(rf"\s{re.escape(name)}\s*=\s*(\"[^\"]*\"|'[^']*')", tag)
    return m.group(1)[1:-1] if m else None


def _set_attr(tag, name, value):
    v = str(value).replace("&", "&amp;").replace("'", "&#39;").replace("<", "&lt;").replace(">", "&gt;")
    new = f" {name}='{v}'"
    rx = re.compile(rf"\s{re.escape(name)}\s*=\s*(\"[^\"]*\"|'[^']*')")
    if rx.search(tag):
        return rx.sub(lambda _: new, tag, count=1)
    return re.sub(r"\s*/?>$", lambda m: new + m.group(0), tag, count=1)


def _beat_time(t, bid):
    if bid == "end":
        return t["end"]
    if bid in ("film-end", "duration"):
        return t["duration"]
    for b in t["beats"]:
        if b["id"] == bid:
            return b["t"]
    raise ComposeError(f"index.html names beat {bid!r}, which beats.json doesn't have")


def bind_index(text, t, fx, slots=None):
    """index.html with Veasy's attributes set: the root's and the chrome's durations, every host timed by its beats
    (data-beat / data-until, with -shift), and the facts, slots, beats and hosts declared as variables on <html>.
    -> (text, {host id: start})."""
    hosts = {}

    def timed(m):
        tag = m.group(0)
        cid = _attr(tag, "data-composition-id")
        if cid in ("main", "chrome", "captions"):
            tag = _set_attr(tag, "data-duration", t["duration"])
        if cid in ("chrome", "captions"):
            tag = _set_attr(tag, "data-start", 0)
        beat = _attr(tag, "data-beat")
        if beat:
            start = max(0.0, round(_beat_time(t, beat) + float(_attr(tag, "data-beat-shift") or 0), 3))
            tag = _set_attr(tag, "data-start", start)
            until = _attr(tag, "data-until")
            if until:
                end = _beat_time(t, until) + float(_attr(tag, "data-until-shift") or 0)
                if end <= start:
                    raise ComposeError(f"host {cid}: data-until {until!r} ends before data-beat {beat!r} starts")
                tag = _set_attr(tag, "data-duration", round(min(end, t["duration"]) - start, 3))
            if cid:
                hosts[cid] = start
        elif cid and cid not in ("main", "chrome", "captions") and _attr(tag, "data-start") is not None:
            try:
                hosts[cid] = float(_attr(tag, "data-start"))
            except ValueError:
                pass
        return tag

    parts = re.split(r"(<!--.*?-->)", text, flags=re.S)  # tags inside comments are left alone
    parts = [p if p.startswith("<!--") else TAG.sub(timed, p) for p in parts]
    decl = json.dumps(variables(fx, t, hosts, slots), ensure_ascii=False, separators=(",", ":"))
    for i, p in enumerate(parts):
        m = None if p.startswith("<!--") else re.search(r"<html\b[^<>]*>", p)
        if m:
            parts[i] = p[:m.start()] + _set_attr(m.group(0), "data-composition-variables", decl) + p[m.end():]
            break
    else:
        raise ComposeError("index.html has no <html> tag")
    text = "".join(parts)
    if VEASY_JS not in text:  # the scenes' scripts read facts and beats from window.VEASY (veasy_js)
        g = re.search(r"<script\s+src\s*=\s*[\"']assets/vendor/gsap\.min\.js[\"']\s*>\s*</script>", text)
        tag = f'<script src="{VEASY_JS}"></script>'
        text = text[:g.end()] + "\n    " + tag + text[g.end():] if g else text.replace("</head>", f"  {tag}\n  </head>", 1)
    if not text.startswith("﻿"):  # UTF-8, whatever the server says: the variables on <html> push <meta charset>
        text = "﻿" + text  # past the 1024 bytes a browser scans for it, and Georgian came out as mojibake
    return text, hosts


VEASY_JS = "assets/vendor/veasy.js"


def veasy_js(fx, t, hosts, slots=None):
    """window.VEASY for the scenes' scripts (a sub-composition's script can't rely on getVariables() at init):
    VEASY.fact(id), VEASY.beat(id), VEASY.host(id), VEASY.at(beat, host) = the beat in the host's own seconds."""
    data = {"facts": {k: v["value"] for k, v in fx.items()}, "slots": dict(slots or {}),
            "beats": {b["id"]: b["t"] for b in t["beats"]}, "hosts": hosts,
            "chapters": [{k: c[k] for k in ("n", "from", "to")} for c in t["chapters"]],
            "end": t["end"], "duration": t["duration"]}
    return ("// Written by tt_shorts/compose.py from facts.json and timing.json (Veasy's file: never edit it).\n"
            f"(function () {{\n  const D = {json.dumps(data, ensure_ascii=False)};\n"
            "  const need = (map, id, what) => { if (!(id in map)) throw new Error(`VEASY: no ${what} ${id}`); return map[id]; };\n"
            "  window.VEASY = Object.freeze({ ...D,\n"
            "    fact: (id) => (id in D.slots ? D.slots[id] : need(D.facts, id, \"fact\")),\n"
            "    beat: (id) => (id === \"end\" ? D.end : need(D.beats, id, \"beat\")),\n"
            "    host: (id) => need(D.hosts, id, \"host\"),\n"
            "    at: (beat, host) => Math.round(((beat === \"end\" ? D.end : need(D.beats, beat, \"beat\")) - "
            "need(D.hosts, host, \"host\")) * 1000) / 1000 });\n})();\n")


# ---------------------------------------------------------------- the locked chrome (CHROME_VERSION)


def font_faces(prefix="assets/fonts"):
    return "\n".join(
        f"@font-face {{ font-family: \"Brand\"; font-weight: {w}; font-style: normal; font-display: block; "
        f"src: url('{prefix}/brand-{w}.woff2') format('woff2'); }}" for w in packs.FONT_WEIGHTS)


def fit_size(text, width, top, floor, font):
    """The largest size from floor to top at which `text` fits `width` on one line, on the pack's real font
    (remotion/src/ui.tsx fitSize): a long link gets smaller, it never runs out of the frame."""
    return max(floor, min(top, int(100 * width / max(1, captions.width(text, 100, font)))))


def footer_size(url, b):
    """The footer's link beside the pack's line, 32 px clear of it (remotion/src/NewsShort.tsx Footer). Under 22 px it
    stops shrinking and the probe holds the film: a footer that small can't be read."""
    fonts, f = b["_fonts"], b["footer"]
    pack = captions.width(f["text"], 28, fonts["400"]) + captions.width(f.get("strong") or "", 28, fonts["700"])
    return fit_size(url, W - 2 * SIDE - pack - 32, 36, 22, fonts["700"])


def tmark(size, b):
    c = b["colors"]
    from_ts = (ROOT / "remotion" / "src" / "brand.ts").read_text(encoding="utf-8")
    path = from_ts.split('T_PATH =\n  "', 1)[1].split('"', 1)[0]
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 512 512"><rect width="512" height="512" rx="112" '
            f'fill="{c["markBg"]}"/><g transform="translate(0,512) scale(0.1,-0.1)"><path d="{path}" fill="{c["markInk"]}"/>'
            f'</g><circle cx="323" cy="295" r="34" fill="{c["accent"]}"/></svg>')


def wordmark(b, size):
    w = b["wordmark"]
    i = w["text"].find(w.get("accent") or "\0")
    t = esc(w["text"]) if i < 0 else (esc(w["text"][:i]) + f'<span class="acc">{esc(w["accent"])}</span>'
                                      + esc(w["text"][i + len(w["accent"]):]))
    return f'<span class="wordmark" style="font-size:{size}px">{t}</span>'


def logo(b, project, place="header"):
    """The pack's logo as Remotion's Logo draws it: tmark = the mark next to (header) or above (end) the wordmark;
    svg = the pack's own files (they carry the name)."""
    if b["logo"]["kind"] == "svg":
        shutil.copy(b["_logo"][place], project / "assets" / f"logo-{place}.svg")
        size = "height:88px" if place == "header" else "height:340px"  # the end logo fits the band above the QR
        return f'<div class="logo-{place}"><img src="assets/logo-{place}.svg" style="{size};display:block" alt=""></div>'
    if place == "header":
        return f'<div class="logo-header">{tmark(88, b)}{wordmark(b, 44)}</div>'
    return f'<div class="logo-end">{tmark(220, b)}{wordmark(b, 84)}</div>'


def end_card(t, b, project):
    """The end card (Lane A's "end" scene): the pack's logo, the story's QR and link, its call to action on the
    pack's button. In at the end mark; the QR and the CTA land on their beats when the beat sheet names them."""
    f = t["facts"]
    at = {x["id"]: x["t"] for x in t["beats"]}
    e = t["end"]
    q, k = at.get("end-link", e + 1.3), at.get("cta", e + 2.9)
    body = f"""
    <div id="chrome-end" class="end" data-probe="scene" data-veasy-code>{logo(b, project, "end")}
      <div id="chrome-qr" class="qr"><img src="assets/qr.svg" alt=""></div>
      <div id="chrome-link" class="link">{esc(f['url'])}</div>
      <div id="chrome-cta" class="cta">{esc(f['cta'])}</div></div>"""
    js = ['tl.set("#chrome-end", { opacity: 0 }, 0);',
          f'tl.set("#chrome-end", {{ opacity: 1 }}, {e:.3f});',
          f'tl.fromTo("#chrome-end .logo-end", {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.6)" }}, {e + 0.08:.3f});',
          f'tl.fromTo("#chrome-qr", {{ opacity: 0, scale: 0.85 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "expo.out" }}, {q:.3f});',
          f'tl.fromTo("#chrome-link", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.35, ease: "expo.out" }}, {q + 0.1:.3f});',
          f'tl.fromTo("#chrome-cta", {{ opacity: 0, scale: 0.8, y: 30 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "back.out(1.7)" }}, {k + 0.06:.3f});']
    return body, js


def chrome(t, b, project, kind="news"):
    """The locked chrome. news: the pack's logo, the date and weekday · time · category, the chapter bar, the meter
    wipes, the ticker, the source line, link and footer, the end card. film (a story, a product film): the logo,
    the chapter bar, the wipes, the link and footer, the end card; no date, source line or ticker (fiction has no
    source and no dateline). Texts that are the data's carry data-veasy-code (check() doesn't claim-check them)."""
    c, f = b["colors"], t["facts"]
    dur, chapters = t["duration"], t["chapters"]
    news = kind == "news"
    seg_w = (W - 2 * SIDE - 8 * (len(chapters) - 1)) / len(chapters)
    segs, labels = [], []
    for i, ch in enumerate(chapters):
        x = SIDE + i * (seg_w + 8)
        segs.append(f'<div class="seg" style="left:{x:.1f}px;width:{seg_w:.1f}px"><div id="chrome-fill-{i}" class="fill"></div></div>')
        labels.append(f'<div id="chrome-ch-{i}" class="chlabel" data-probe="header"><b data-veasy-code>{ch["n"]:02d} / {ch["of"]:02d}</b>'
                      f'<span>{esc(ch["title"])}</span></div>')
    bars = "".join(f'<div class="bar" id="chrome-bar-{w}-{k}" style="left:{SIDE + k * ((W - 2 * SIDE + 8) / BARS):.1f}px;'
                   f'width:{(W - 2 * SIDE + 8) / BARS - 8:.1f}px;background:{c["ink"] if k % 3 else c["muted"]}"></div>'
                   for w in range(len(t["wipes"])) for k in range(BARS))
    row = "  ·  ".join([f["category"], f["date"]["date"], *f["sources"], b["label"]])
    ticker = esc("  ·  ".join([row] * 4))
    footer_strong = f'<b>{esc(b["footer"]["strong"])}</b>' if b["footer"].get("strong") else ""
    note = (f'<div class="note" data-probe="ticker" data-veasy-code>{esc(f["previewNote"])}</div>'
            if f.get("previewNote") else "")
    js = ["const tl = gsap.timeline({ paused: true });"]
    for i, ch in enumerate(chapters):  # the current chapter's segment fills with its time; the dot is its head
        js.append(f'tl.fromTo("#chrome-fill-{i}", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {ch["to"] - ch["from"]:.3f}, ease: "none" }}, {ch["from"]:.3f});')
        if i == 0:  # frame 0 is the thumbnail: the first chapter is already there
            js.append('tl.set("#chrome-ch-0", { opacity: 1 }, 0);')
        else:
            js.append(f'tl.fromTo("#chrome-ch-{i}", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "expo.out", immediateRender: false }}, {ch["from"] + 0.05:.3f});')
        js.append(f'tl.to("#chrome-ch-{i}", {{ opacity: 0, duration: 0.15, ease: "power2.in" }}, {ch["to"] - 0.15:.3f});')
        x0 = SIDE + i * (seg_w + 8)
        js.append(f'tl.fromTo("#chrome-dot", {{ x: {x0 - 10:.1f} }}, {{ x: {x0 + seg_w - 10:.1f}, duration: {ch["to"] - ch["from"]:.3f}, ease: "none", immediateRender: {str(i == 0).lower()} }}, {ch["from"]:.3f});')
    js.append(f'tl.to("#chrome-dot", {{ opacity: 0, duration: 0.2 }}, {t["end"]:.3f});')
    # the meter wipe: the bars rise like an equaliser (each to its own height, then all the way), cover the scene
    # band at the cut for a moment (the scenes swap under them) and fall away upward, left to right
    rng = [0.42, 0.78, 0.55, 0.95, 0.6, 0.86, 0.38, 0.7, 0.92, 0.5, 0.8, 0.64]
    js.append('tl.set(".bar", { scaleY: 0, transformOrigin: "50% 100%" }, 0);')
    for w, at in enumerate(t["wipes"]):
        for k in range(BARS):
            el = f"#chrome-bar-{w}-{k}"
            a = at - WIPE - 0.04 + 0.016 * k
            rise = at - 0.02 - (a + 0.14)
            js.append(f'tl.fromTo("{el}", {{ scaleY: 0, transformOrigin: "50% 100%" }}, {{ scaleY: {rng[k]}, duration: 0.14, ease: "power2.out", immediateRender: false }}, {a:.3f});')
            js.append(f'tl.to("{el}", {{ scaleY: 1.01, duration: {rise:.3f}, ease: "power2.inOut" }}, {a + 0.14:.3f});')
            js.append(f'tl.set("{el}", {{ transformOrigin: "50% 0%" }}, {at + 0.02:.3f});')
            js.append(f'tl.to("{el}", {{ scaleY: 0, duration: 0.3, ease: "power3.in" }}, {at + 0.02 + 0.016 * k:.3f});')
    if news:
        js.append(f'tl.fromTo("#chrome-tickrow", {{ x: 0 }}, {{ x: -{2.2 * FPS * dur:.0f}, duration: {dur:.3f}, ease: "none" }}, 0);')
    end_body, end_js = end_card(t, b, project)
    js += end_js
    fonts = b["_fonts"]
    url_px, link_px = footer_size(f["url"], b), fit_size(f["url"], W - 280, 40, 24, fonts["700"])  # the end link: 140 px each side
    cta_px = fit_size(f["cta"], 704, 40, 24, fonts["600"])  # the button, 32 px inside each end
    js.append('window.__timelines["chrome"] = tl;')
    css = f"""
    {font_faces()}
    #root {{ position: absolute; inset: 0; font-family: "Brand", sans-serif; color: {c['ink']}; }}
    #root .logo-header {{ position: absolute; left: {SIDE}px; top: 80px; height: 88px; display: flex; align-items: center; gap: 24px; }}
    #root .end {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; }}
    #root .logo-end {{ position: absolute; left: 0; right: 0; top: 300px; display: flex; flex-direction: column; align-items: center; gap: 24px; }}
    #root .qr {{ position: absolute; left: 380px; top: 690px; width: 320px; height: 320px; border-radius: 14px; overflow: hidden; }}
    #root .qr img {{ width: 320px; height: 320px; display: block; }}
    #root .link {{ position: absolute; left: 140px; right: 140px; top: 1036px; text-align: center; font-weight: 700; font-size: {link_px}px; line-height: 1.2; white-space: nowrap; }}
    #root .cta {{ position: absolute; left: 156px; width: 768px; top: 1128px; height: 88px; border-radius: 999px; background: {c['accent']}; color: {c['onAccent']};
      display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: {cta_px}px; line-height: 1; white-space: nowrap; }}
    #root .wordmark {{ font-weight: 700; color: {c['ink']}; white-space: nowrap; }}
    #root .acc {{ color: {c['accent']}; }}
    #root .date {{ position: absolute; right: {SIDE}px; top: 80px; text-align: right; }}
    #root .date .d {{ font-weight: 700; font-size: 40px; line-height: 1.2; }}
    #root .date .m {{ font-weight: 400; font-size: 30px; line-height: 1.4; color: {c['muted']}; }}
    #root .seg {{ position: absolute; top: 204px; height: 6px; border-radius: 3px; background: {c['lineStrong']}; overflow: hidden; }}
    #root .fill {{ position: absolute; inset: 0; background: {c['ink']}; transform-origin: 0 50%; }}
    #root .dot {{ position: absolute; left: 0; top: 197px; width: 20px; height: 20px; border-radius: 10px; background: {c['accent']}; }}
    #root .chlabel {{ position: absolute; left: {SIDE}px; top: 222px; display: flex; gap: 16px; align-items: baseline; font-size: 28px; line-height: 1.2; opacity: 0; white-space: nowrap; }}
    #root .chlabel b {{ font-weight: 700; color: {c['ink']}; }}
    #root .chlabel span {{ font-weight: 500; color: {c['muted']}; }}
    #root .bar {{ position: absolute; top: 248px; height: 1132px; border-radius: 14px; }}
    #root .ticker {{ position: absolute; left: 0; right: 0; top: 1580px; height: 180px; overflow: hidden; }}
    #root .tickrow {{ position: absolute; top: 44px; left: 0; white-space: pre; font-weight: 700; font-size: 128px; line-height: 1; color: {c['ticker']}; }}
    #root .note {{ position: absolute; right: {SIDE}px; top: 1580px; font-weight: 600; font-size: 28px; line-height: 1; padding: 11px 20px 13px; border-radius: 999px; border: 2px solid {c['lineStrong']}; white-space: nowrap; }}
    #root .footer {{ position: absolute; left: {SIDE}px; right: {SIDE}px; top: 1768px; border-top: 2px solid {c['line']}; padding-top: 16px; }}
    #root .footer .src {{ font-weight: 400; font-size: 28px; line-height: 1.4; color: {c['muted']}; white-space: nowrap; overflow: hidden; }}
    #root .footer .row {{ display: flex; justify-content: space-between; align-items: baseline; }}
    #root .footer .url {{ font-weight: 700; font-size: {url_px}px; line-height: 1.4; white-space: nowrap; }}
    #root .footer .pack {{ font-size: 28px; line-height: 1.4; color: {c['muted']}; white-space: nowrap; }}
    #root .footer .pack b {{ font-weight: 700; color: {c['ink']}; }}"""
    date = (f"""
    <div class="date" data-probe="header" data-veasy-code><div class="d">{esc(f['date']['date'])}</div>
      <div class="m">{esc(f['date']['weekday'])} · {esc(f['date']['time'])} · {esc(f['category'])}</div></div>""" if news else "")
    tick = (f'\n    <div class="ticker" data-probe="ticker" data-layout-ignore data-veasy-code><div id="chrome-tickrow" '
            f'class="tickrow">{ticker}</div></div>' if news else "")
    src = f'<div class="src">{esc(f["sourcesLine"])}</div>' if news and f.get("sourcesLine") else ""
    body = f"""
    <div data-probe="header" data-veasy-code>{logo(b, project)}</div>{end_body}{date}
    {''.join(segs)}
    <div id="chrome-dot" class="dot"></div>
    {''.join(labels)}
    {bars}{tick}
    {note}
    <div class="footer" data-probe="footer" data-veasy-code>{src}
      <div class="row"><span class="url">{esc(f['url'])}</span><span class="pack">{esc(b['footer']['text'])}{footer_strong}</span></div></div>"""
    return locked("chrome", css, body, js)


def captions_html(cap, t, b):
    """props.captions (captions.py) as HyperFrames DOM + timeline: Captions.tsx's page design, frame for frame."""
    c = b["colors"]
    words = t["words"]
    style = cap.get("keyword")  # design "keyword": each page's key and the pack's style come with the layout
    key = set() if style else {(w["text"], round(w["start"], 3)) for w in words if w["keyword"]}
    style = style or "block"  # the beat sheet's keywords (page and roll) are drawn as an ink block
    size, lh, band, pad = cap["size"], cap["lineHeight"], cap["band"], cap["pad"]
    row = size * lh
    box_h = row * 2 + 28
    pages, js = [], ["const tl = gsap.timeline({ paused: true });"]
    allw = [w for line in cap["lines"] for w in line["words"]]
    n = 0
    for k, p in enumerate(cap["pages"]):
        lines = []
        for li in p["lines"]:
            ws = cap["lines"][li]["words"]
            spans = []
            pk = p.get("key")
            for j, w in enumerate(ws):
                wid = f"cap-w{n}"
                n += 1
                is_key = (w["text"], round(w["from"], 3)) in key or bool(
                    pk and pk["line"] == li and pk["from"] <= j <= pk["to"])  # the layout's line index
                spans.append(f'<span id="{wid}" class="w{" k" if is_key else ""}"{"" if j < len(ws) - 1 else " style=\"margin-right:0\""}>'
                             f'{"<i class=\"kb\"></i>" if is_key else ""}<em>{esc(w["text"])}</em><i class="u"></i></span>')
                nxt = [x["from"] for x in allw if x["from"] > w["from"]]  # the next word anywhere, not only on this line
                until = min([w["to"] + 0.35] + nxt[:1]) if j + 1 == len(ws) else ws[j + 1]["from"]
                js.append(f'tl.set("#{wid}", {{ color: "{c["ink"]}" }}, {max(0, w["from"] - 0.04):.3f});')
                if is_key and style == "block":
                    js.append(f'tl.fromTo("#{wid} .kb", {{ scaleX: 0.6, opacity: 0 }}, {{ scaleX: 1, opacity: 1, duration: 0.12, ease: "power3.out" }}, {max(0, w["from"] - 0.04):.3f});')
                    js.append(f'tl.set("#{wid} em", {{ color: "{c["canvas"]}" }}, {max(0, w["from"] - 0.04):.3f});')
                elif is_key and style == "tint":  # the accent as the keyword's color (a pack that allows it)
                    js.append(f'tl.set("#{wid} em", {{ color: "{c["accent"]}" }}, {max(0, w["from"] - 0.04):.3f});')
                js.append(f'tl.fromTo("#{wid} .u", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.12, ease: "power3.out" }}, {max(0, w["from"] - 0.04):.3f});')
                if not (is_key and style == "underline"):  # an underline keyword keeps its line once said
                    js.append(f'tl.set("#{wid} .u", {{ scaleX: 0 }}, {until:.3f});')
            lines.append(f'<div class="line">{"".join(spans)}</div>')
        pid = f"cap-p{k}"
        pages.append(f'<div id="{pid}" class="page"><div class="inner">{"".join(lines)}</div></div>')
        js.append(f'tl.fromTo("#{pid}", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.14, ease: "power3.out" }}, {p["start"]:.3f});')
        js.append(f'tl.to("#{pid}", {{ opacity: 0, duration: 0.18, ease: "power1.in" }}, {max(p["start"] + 0.2, p["end"] - 0.18):.3f});')
        js.append(f'tl.set("#{pid}", {{ opacity: 0 }}, {p["end"]:.3f});')
    # the box: in after a real silence, out where a page ends without the next one following at once
    runs, cur = [], None
    for p in cap["pages"]:
        if cur and p["start"] - cur[1] <= 0.05:
            cur[1] = p["end"]
        else:
            cur = [p["start"], p["end"]]
            runs.append(cur)
    for a, z in runs:
        js.append(f'tl.fromTo("#cap-box", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2, ease: "none" }}, {a:.3f});')
        js.append(f'tl.to("#cap-box", {{ opacity: 0, duration: 0.18, ease: "none" }}, {max(a + 0.2, z - 0.18):.3f});')
    js.append('window.__timelines["captions"] = tl;')
    css = f"""
    {font_faces()}
    #root {{ position: absolute; inset: 0; font-family: "Brand", sans-serif; }}
    #cap-box {{ position: absolute; left: {W - 940}px; width: {band}px; top: {1552 - box_h:.1f}px; height: {box_h:.1f}px;
      background: rgba({int(c['canvas'][1:3], 16)},{int(c['canvas'][3:5], 16)},{int(c['canvas'][5:7], 16)},0.8);
      border: 2px solid {c['line']}; border-radius: 14px; opacity: 0; }}
    #root .page {{ position: absolute; left: {W - 940}px; width: {band}px; top: {1552 - box_h:.1f}px; height: {box_h:.1f}px;
      display: flex; align-items: center; justify-content: center; padding: 0 {pad}px; opacity: 0; }}
    #root .line {{ font-weight: 700; font-size: {size}px; line-height: {lh}; white-space: nowrap; text-align: center; }}
    #root .w {{ position: relative; display: inline-block; margin-right: 0.27em; color: {c['waiting']}; }}
    #root .w em {{ position: relative; font-style: normal; }}
    #root .w .u {{ position: absolute; left: 0; right: 0; bottom: -4px; height: 5px; border-radius: 3px; background: {c['accent']};
      transform-origin: left; }}
    #root .w .kb {{ position: absolute; left: -0.14em; right: -0.14em; top: 0.1em; bottom: 0.02em; border-radius: 8px;
      background: {c['ink']}; opacity: 0; }}"""
    body = f'<div id="cap-box"></div><div data-probe="captions" data-veasy-code>{"".join(pages)}</div>'
    return locked("captions", css, body, js)


def locked(cid, css, body, js):
    return f"""<!-- LOCKED v{CHROME_VERSION}: written by tt_shorts/compose.py from the pack, the story and its timing. Place its
     host in index.html; never edit, restyle, cover or remove it (frame.md, Locked Chrome; compose check hashes it). -->
<template>
  <style>{css}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="{W}" data-height="{H}">{body}
  </div>
  <script>
    {chr(10).join('    ' + line for line in js).lstrip()}
  </script>
</template>
"""


def icon_svg(name, color, stroke=2):
    parts = []
    for tag, attrs in icons.nodes(name):
        a = " ".join(f'{k}="{esc(v)}"' for k, v in attrs.items())
        parts.append(f"<{tag} {a}/>")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{"".join(parts)}</svg>\n')


MAP_W, MAP_H = 952, 600  # the map's box in a scene, px


def map_box(box, w=MAP_W, h=MAP_H):
    """A viewBox [x, y, w, h] around a map box [x0, y0, x1, y1] with the scene box's aspect ratio."""
    x0, y0, x1, y1 = box
    k = max((x1 - x0) / w, (y1 - y0) / h)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return [round(cx - w * k / 2, 1), round(cy - h * k / 2, 1), round(w * k, 1), round(h * k, 1)]


def map_svg(m, vb, c, tint):
    """Georgia (tt_shorts/geo.py's projection) seen through viewBox vb, drawn as map.tsx draws it: the land in a faint
    ink, the region in a quiet ink tint, rivers, dashed borders, the region outlined; strokes in screen px."""
    u = vb[2] / MAP_W  # map units per screen px
    regions = "".join(f'<path d="{r}" fill="{c["ink"]}" fill-opacity="{0.18 * tint:.2f}"/>' for r in m["regions"])
    outlines = "".join(f'<path d="{r}" fill="none" stroke="{c["ink"]}" stroke-width="{4 * u:.1f}" stroke-linejoin="round" '
                       f'opacity="{tint}"/>' for r in m["regions"])
    # the territories Georgian law calls occupied: the accent at low opacity and a fine hatch, as map.tsx draws them
    occupied = "".join(
        f'<path d="{o["path"]}" fill="{c["accent"]}" fill-opacity="0.16"/><path d="{o["path"]}" fill="url(#hatch)" fill-opacity="0.5"/>'
        f'<path d="{o["path"]}" fill="none" stroke="{c["lineStrong"]}" stroke-width="{2 * u:.1f}" '
        f'stroke-dasharray="{8 * u:.1f} {6 * u:.1f}" stroke-linejoin="round"/>' for o in m.get("occupied") or [])
    hatch = (f'<pattern id="hatch" patternUnits="userSpaceOnUse" width="{9 * u:.1f}" height="{9 * u:.1f}" patternTransform="rotate(45)">'
             f'<line x1="0" y1="0" x2="0" y2="{9 * u:.1f}" stroke="{c["accent"]}" stroke-width="{1.6 * u:.2f}"/></pattern>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(map(str, vb))}" width="{MAP_W}" height="{MAP_H}">'
            f'<defs><clipPath id="land"><path d="{m["land"]}"/></clipPath>{hatch}</defs>'
            f'<path d="{m["land"]}" fill="{c["ink"]}" fill-opacity="0.05"/>{regions}{occupied}'
            f'<path d="{m["rivers"]}" fill="none" stroke="{c["ink"]}" stroke-opacity="0.3" stroke-width="{2.5 * u:.1f}" '
            f'stroke-linejoin="round" stroke-linecap="round" clip-path="url(#land)"/>'
            f'<path d="{m["borders"]}" fill="none" stroke="{c["lineStrong"]}" stroke-width="{2 * u:.1f}" '
            f'stroke-dasharray="{8 * u:.1f} {6 * u:.1f}"/>{outlines}'
            f'<path d="{m["land"]}" fill="none" stroke="{c["ink"]}" stroke-width="{3 * u:.1f}" stroke-linejoin="round"/></svg>\n')


def brand_css(b):
    """The pack's tokens as CSS variables and its font as "Brand": the only place a scene gets a color or a face."""
    c = b["colors"]
    names = {"canvas": "canvas", "panel": "panel", "ink": "ink", "muted": "muted", "accent": "accent", "line": "line",
             "lineStrong": "line-strong", "grid": "grid", "ticker": "ticker", "waiting": "waiting", "markBg": "mark-bg",
             "onAccent": "on-accent", "markInk": "mark-ink"}
    rgb = ",".join(str(int(c["canvas"][i:i + 2], 16)) for i in (1, 3, 5))
    ink = ",".join(str(int(c["ink"][i:i + 2], 16)) for i in (1, 3, 5))
    qr_dark, qr_light = packs.qr_colors(c)
    tokens = "\n".join(f"  --{v}: {c[k]};" for k, v in names.items()) + f"\n  --qr-dark: {qr_dark};\n  --qr-light: {qr_light};"
    return (f"/* {b['label']}, theme {b['theme']}: written by tt_shorts/compose.py from brands/{b['name']}/brand.json */\n"
            f"{font_faces('fonts')}\n:root {{\n{tokens}\n  --canvas-0: rgba({rgb},0);\n  --canvas-90: rgba({rgb},.9);\n"
            f"  --ink-10: rgba({ink},.1);\n  --ink-20: rgba({ink},.2);\n  --ink-40: rgba({ink},.4);\n}}\n")


# ---------------------------------------------------------------- the project: scaffold and build


def _story(story_path, brand=None):
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    if brand:
        packs.load(brand)  # an unknown pack fails here
        story["brand"] = brand
    return story


def starter(story, project):
    """A first film from the story alone (no source, no template): one beat per scene of the story, one chapter,
    index.html with a host per scene timed by its beats, and plain scene files that show the scene's checked words
    through their facts. The agent makes it its own from here."""
    scenes = [s for s in story["scenes"] if s.get("type") != "end"]
    end = next((s for s in story["scenes"] if s.get("type") == "end"), None)
    if not end:
        raise ComposeError("the story has no end scene: its \"at\" is where the end card comes in")
    beats = [{"id": f"s{i}", "at": s["at"], "show": s["type"]} for i, s in enumerate(scenes)]
    sheet = {"about": "The beat sheet (compose.py): chapters and beats anchored to the narration's words. Yours to "
                      "change: add a beat every 1.5-3 s where something new lands.",
             "chapters": [{"title": (scenes[0].get("kicker") or "").split(" · ")[0], "at": scenes[0]["at"]}],
             "end": {"at": end["at"]}, "beats": beats, "keywords": [], "icons": []}
    (project / "beats.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1), encoding="utf-8")
    hosts = []
    for i, s in enumerate(scenes):
        nxt = f"s{i + 1}" if i + 1 < len(scenes) else "end"
        hosts.append(f'      <div id="s{i}" data-composition-id="s{i}" data-composition-src="compositions/s{i}.html" '
                     f'data-beat="s{i}" {_until(nxt)} data-track-index="{1 + i % 2}" '
                     f'data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index: {10 + i}"></div>')
        (project / "compositions" / f"s{i}.html").write_text(starter_scene(i, s), encoding="utf-8")
    (project / "index.html").write_text(INDEX.replace("{hosts}", "\n".join(hosts)), encoding="utf-8")


INDEX = """<!doctype html>
<!-- A composed film (tt_shorts/compose.py). Yours: this file, its background and the scenes it hosts. Veasy's: the
     variables on <html> (the story's facts, the beats), the durations of the root and the chrome, and every host's
     start and length when it names its beats (data-beat / data-until). Colors are var(--token), the face "Brand". -->
<html lang="ka">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/vendor/gsap.min.js"></script>
    <link rel="stylesheet" href="assets/brand.css" />
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: var(--canvas); }
      #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; font-family: "Brand", sans-serif; }
      #bg { position: absolute; inset: 0; background: var(--canvas); }
      #bg-grid { position: absolute; left: 0; top: -72px; width: 1080px; height: 1992px;
        background-image: linear-gradient(var(--grid) 2px, transparent 2px), linear-gradient(90deg, var(--grid) 2px, transparent 2px);
        background-size: 72px 72px; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="30" data-fps="30" data-width="1080" data-height="1920" data-probe-root>
      <div id="bg" data-layout-ignore><div id="bg-grid"></div></div>
{hosts}
      <!-- locked chrome (with the end card) and captions: placed, never edited -->
      <div id="chrome" data-composition-id="chrome" data-composition-src="compositions/chrome.html" data-start="0" data-duration="30" data-track-index="5" data-track-kind="graphics" data-width="1080" data-height="1920" style="z-index: 30"></div>
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="30" data-track-index="6" data-track-kind="captions" data-width="1080" data-height="1920" style="z-index: 40"></div>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.fromTo("#bg-grid", { y: 0 }, { y: 72, duration: VEASY.duration, ease: "none" }, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def starter_scene(i, s):
    """One plain scene: the scene's words, each bound to its fact (s<i>-<field>), stacked and rising in."""
    fields = [k for k, v in s.items() if k not in ("type", "at", "em", "icon", "verb", "style", "svg")]
    rows, n = [], 0
    for k in fields:
        v = s[k]
        vals = v if isinstance(v, list) else [v]
        for j, it in enumerate(vals):
            if isinstance(it, dict):
                ids = [f"scene-{i}-{store.safe(k)}-{j}-{store.safe(f)}" for f, x in it.items() if isinstance(x, (str, int, float))]
            elif isinstance(it, (str, int, float)) and not isinstance(it, bool):
                ids = [f"scene-{i}-{store.safe(k)}" + (f"-{j}" if isinstance(v, list) else "")]
            else:
                continue
            for fid in ids:
                big = "big" if n == 0 else ("mid" if n < 3 else "small")
                rows.append(f'      <div id="s{i}-r{n}" class="row {big}" data-var-text="{fid}">…</div>')
                n += 1
    tweens = "\n".join(f'      tl.fromTo("#s{i}-r{k}", {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.4, '
                       f'ease: "expo.out" }}, {0.1 + 0.25 * k:.2f});' for k in range(n))
    return f"""<!-- scene s{i} ({s['type']}): a plain start, the scene's own words bound to its facts. Make it a picture. -->
<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Brand", sans-serif; color: var(--ink); }}
    #root .stack {{ position: absolute; left: 64px; width: 876px; top: 300px; display: flex; flex-direction: column; gap: 28px; }}
    #root .row {{ font-weight: 700; line-height: 1.15; }}
    #root .big {{ font-size: 88px; }}
    #root .mid {{ font-size: 56px; }}
    #root .small {{ font-size: 44px; font-weight: 500; color: var(--muted); }}
  </style>
  <div id="root" data-composition-id="s{i}" data-width="{W}" data-height="{H}">
    <div class="stack" data-probe="scene">
{chr(10).join(rows)}
    </div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
{tweens}
      window.__timelines["s{i}"] = tl;
    }})();
  </script>
</template>
"""


def _until(nxt):
    """A starter host's end. Scenes cut on the beat: two on screen at once sit on each other (probe cut). The last one
    stays a moment, under the end's wipe."""
    return f'data-until="{nxt}"' + (' data-until-shift="0.3"' if nxt == "end" else "")


def agent_files(project):
    """The agent's files of a project (relative paths): index.html, beats.json, slots.json, the scenes, assets/art/."""
    project = pathlib.Path(project)
    out = [f for f in ("index.html", "beats.json", "slots.json") if (project / f).exists()]
    out += sorted(f"compositions/{p.name}" for p in (project / "compositions").glob("*.html")
                  if f"compositions/{p.name}" not in LOCKED)
    out += sorted(str(p.relative_to(project)).replace("\\", "/") for p in (project / "assets" / "art").rglob("*")
                  if p.is_file()) if (project / "assets" / "art").is_dir() else []
    return out


def _copy_agent(src, project):
    src = pathlib.Path(src)
    if not (src / "index.html").exists():
        raise ComposeError(f"{src} is not a composition (no index.html)")
    for f in agent_files(src):
        (project / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src / f, project / f)


def default_source(story):
    """A composition shipped in the repo for this story (compose/<id>/), or None."""
    d = COMPOSE / store.safe(story["id"])
    return d if (d / "index.html").exists() else None


def blocks():
    """All available composition blocks from compose/blocks/ -> {id: manifest}."""
    return blk.list_all()


def blocks_summary():
    """Summary of all blocks for options and agent prompts -> {id: {label, about, slots, beats, duration}}."""
    return blk.options()


def _plate_block(text, story, scene):
    """The plate block's three placeholders from the story's resolved plate for this scene: its ledger id, where its card
    sits and the dot's track. Without one the clip and the dot are cut out and the card stands on the plain canvas."""
    p = scene.get("plate") or {}
    e = next((x for x in story.get("assets") or [] if x.get("id") == p.get("asset")), None)
    if not e:
        text = re.sub(r"<!--plate-->.*?<!--/plate-->", "", text, flags=re.S)
        text = re.sub(r"<!--note-->.*?<!--/note-->", "", text, flags=re.S)
        return text.replace("{plate_layout}", "mid").replace("{plate_dot}", "[]").replace("{plate_id}", "none")
    from tt_shorts import brand, plates
    dot = (plates.tracks_of(e["hash"]).get("dot") or [])
    if e.get("generated"):  # N13: a plate holding a model's picture carries the pack's label, in the card
        text = text.replace("{plate_note}", brand.of(story)["strings"]["illustrative"])
    else:
        text = re.sub(r"<!--note-->.*?<!--/note-->", "", text, flags=re.S)
    return (text.replace("{plate_id}", e["id"]).replace("{plate_layout}", p.get("layout") or "mid")
            .replace("{plate_dot}", json.dumps(dot, separators=(",", ":"))))


def assemble_blocks(story, project, block_ids, slot_bindings=None):
    """Assemble a multi-block HyperFrames project from reusable blocks (compose/blocks/<id>/).
    block_ids: list of block ids or comma-separated string (e.g. 'kinetic-headline,number-reveal,end-card').
    Creates compositions/s<i>.html for each block, index.html hosting them, and beats.json."""
    project = pathlib.Path(project).resolve()
    story = _story(story) if not isinstance(story, dict) else story
    if isinstance(block_ids, str):
        block_ids = [b.strip() for b in block_ids.split(",") if b.strip()]
    if not block_ids:
        raise ComposeError("no blocks specified; available: " + ", ".join(sorted(blk.list_all())))
    available = blk.list_all()
    for bid in block_ids:
        if bid not in available:
            raise ComposeError(f"unknown block {bid!r}; available: {', '.join(sorted(available))}")

    (project / "compositions").mkdir(parents=True, exist_ok=True)
    scenes = [s for s in story.get("scenes", []) if s.get("type") != "end"]
    end = next((s for s in story.get("scenes", []) if s.get("type") == "end"), None)
    end_at = end["at"] if end else "end"

    hosts, beats, slots_combined = [], [], {}
    for i, bid in enumerate(block_ids):
        cid = f"s{i}"
        manifest, _ = blk.get(bid)
        rendered = blk.render_block(bid, cid, slot_bindings or {})
        if bid == "plate":
            rendered = _plate_block(rendered, story, scenes[i] if i < len(scenes) else {})
        (project / "compositions" / f"{cid}.html").write_text(rendered, encoding="utf-8")
        scene_at = scenes[i]["at"] if i < len(scenes) else end_at
        beats.append({"id": cid, "at": scene_at, "show": bid})
        nxt = f"s{i + 1}" if i + 1 < len(block_ids) else "end"
        hosts.append(f'      <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" '
                     f'data-beat="{cid}" {_until(nxt)} data-track-index="{1 + i % 2}" '
                     f'data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index: {10 + i}"></div>')
        for sname, sinfo in manifest.get("slots", {}).items():
            slots_combined[f"slot-{cid}-{sname}"] = sinfo

    first_title = (scenes[0].get("kicker") or "").split(" · ")[0] if scenes else "Scene"
    sheet = {"about": "The beat sheet (compose.py): assembled from blocks. Anchors tied to story beats.",
             "chapters": [{"title": first_title, "at": scenes[0]["at"] if scenes else 0.0}],
             "end": {"at": end_at},
             "beats": beats, "keywords": [], "icons": []}
    (project / "beats.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1), encoding="utf-8")
    (project / "index.html").write_text(INDEX.replace("{hosts}", "\n".join(hosts)), encoding="utf-8")
    if slots_combined:
        (project / "slots.json").write_text(json.dumps(slots_combined, ensure_ascii=False, indent=1), encoding="utf-8")


def scaffold(story_path, brand=None, project=None, template=None, source=None, blocks=None, engine="silent", force=False,
             music="off", tone=None, theme="default", fmt=None):
    """A HyperFrames project for one story and pack: the agent's files from blocks (compose/blocks/), a template
    (templates/<id>/, or "auto": the least used for the brand), from a source folder, the project's own (kept on a
    re-scaffold), the repo's compose/<id>/, else a plain starter; then everything Veasy owns (build). -> build()'s
    result + "origin"."""
    story = _story(story_path, brand)
    b = packs.of(story)
    project = pathlib.Path(project or project_dir(story, b["name"])).resolve()
    has = (project / "index.html").exists()
    if (template or source or blocks) and has and not force:
        which = f"blocks {blocks}" if blocks else ('template ' + template if template else source)
        raise ComposeError(f"{project} already has the agent's files: pass --force to replace them with {which}")
    if force and project.exists():
        shutil.rmtree(project)
        has = False
    (project / "compositions").mkdir(parents=True, exist_ok=True)
    origin = "kept"
    if blocks:
        assemble_blocks(story, project, blocks)
        b_list = [x.strip() for x in blocks.split(",")] if isinstance(blocks, str) else blocks
        origin = f"blocks: {','.join(b_list)}"
    elif template:
        tid = pick_template(b["name"], story["id"]) if template == "auto" else template
        if not tid:
            raise ComposeError("no templates yet (engine compose promote <project> --as <id>)")
        use_template(tid, project)
        origin = f"template {tid}"
    elif source:
        _copy_agent(source, project)
        origin = f"from {source}"
    elif not has:
        src = default_source(story)
        if src:
            _copy_agent(src, project)
            origin = f"from {src.relative_to(ROOT)}"
        else:
            starter(story, project)
            origin = "starter"
    try:
        built = build(project, story, engine=engine, music=music, tone=tone, theme=theme, fmt=fmt)
    except ComposeError as e:  # a template's beats have no anchors yet: the agent fills them, then scaffolds again
        return {"project": project, "origin": origin, "story": story, "brand": b, "built": False,
                "problems": [f"build: {e}"], "todo": "fill beats.json's anchors (and slots.json for a template), "
                                                     "then run engine compose scaffold again",
                "blocks": blocks_summary(), "templates": sorted(templates().keys())}
    built["origin"] = origin
    built["built"] = True
    built["blocks"] = blocks_summary()
    built["templates"] = sorted(templates().keys())
    return built


def build(project, story, engine="silent", music="off", tone=None, theme="default", fmt=None):
    """Write everything Veasy owns in a project (the agent's files stay) and bind index.html. story: a dict (with its
    pack) or a path. -> {"project", "timing", "props", "work", "facts", "story", "brand", "slots", "problems"}."""
    project = pathlib.Path(project).resolve()
    story = _story(story) if not isinstance(story, dict) else story
    from tt_shorts import props
    b = packs.themed(packs.of(story), props.theme_for(story, theme))  # the pack in the film's theme
    prog = programs.of(story) if "program" in story else programs.get()
    if not (project / "beats.json").exists():
        raise ComposeError(f"{project} has no beats.json (engine compose scaffold writes a first one)")
    sheet = json.loads((project / "beats.json").read_text(encoding="utf-8"))
    for d in ("compositions", "assets/fonts", "assets/icons", "assets/vendor", ".veasy"):
        (project / d).mkdir(parents=True, exist_ok=True)
    story_path = project / "story.json"  # the story with the pack it is built for (props.build reads the pack there)
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    t, p, work = timing(story_path, sheet, engine, music, tone, b["theme"], fmt)
    fx = facts(story, b, p, t)
    slots, problems = slot_values(project, fx)
    code = ["story.json", "facts.json", "timing.json", "frame.md", "assets/brand.css", "assets/vendor/gsap.min.js",
            "assets/qr.svg", *LOCKED]
    (project / "assets" / "brand.css").write_text(brand_css(b), encoding="utf-8")
    for w, f in b["_fonts"].items():
        shutil.copy(f, project / "assets" / "fonts" / f"brand-{w}.woff2")
        code.append(f"assets/fonts/brand-{w}.woff2")
    if not GSAP.exists():
        raise ComposeError(f"HyperFrames {HF_VERSION} is not installed: (cd compose && npm ci)")
    # GSAP from the pinned HyperFrames package, not the CDN: the compiler keeps an https script src as it is, so a
    # CDN reference would be fetched at every render
    shutil.copy(GSAP, project / "assets" / "vendor" / "gsap.min.js")
    for name in sheet.get("icons", []):
        (project / "assets" / "icons" / f"{name}.svg").write_text(icon_svg(name, b["colors"]["ink"]), encoding="utf-8")
        code.append(f"assets/icons/{name}.svg")
    qr = meta.qr_svg(meta.links(story, "shorts", b)[1], *packs.qr_colors(b["colors"]))  # an <img> needs the xmlns
    (project / "assets" / "qr.svg").write_text(qr.replace("<svg ", "<svg xmlns=\"http://www.w3.org/2000/svg\" ", 1),
                                              encoding="utf-8")
    where = next((s for s in p["scenes"] if s.get("map")), None)
    if where:  # the country and the place, the same geometry at two scales (a scene crossfades them as it zooms)
        m = where["map"]
        country, focus = map_box(m["start"]), map_box(m["focus"])
        (project / "assets" / "map-country.svg").write_text(map_svg(m, country, b["colors"], 0), encoding="utf-8")
        (project / "assets" / "map-place.svg").write_text(map_svg(m, focus, b["colors"], 1), encoding="utf-8")
        code += ["assets/map-country.svg", "assets/map-place.svg"]
        t["map"].update({"box": [MAP_W, MAP_H], "country": country, "place": focus,
                         "pinsInCountry": [[round((x - country[0]) / country[2] * MAP_W, 1),
                                            round((y - country[1]) / country[3] * MAP_H, 1)] for x, y in m["pins"]],
                         "pinsInPlace": [[round((x - focus[0]) / focus[2] * MAP_W, 1),
                                          round((y - focus[1]) / focus[3] * MAP_H, 1)] for x, y in m["pins"]],
                         "placeInCountry": [round((focus[0] - country[0]) / country[2] * MAP_W, 1),
                                            round((focus[1] - country[1]) / country[3] * MAP_H, 1),
                                            round(focus[2] / country[2] * MAP_W, 1),
                                            round(focus[3] / country[3] * MAP_H, 1)]})
    code += media(story, b, project)
    code += plate_files(story, b, project)
    (project / "frame.md").write_text(frame_md.render(b), encoding="utf-8")
    (project / "timing.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    (project / "facts.json").write_text(json.dumps({
        "about": "The story's facts (compose.py): bind them in a scene with data-var-text=\"<id>\" or "
                 "window.__hyperframes.getVariables()[\"<id>\"]; never type a number, date, name or quote. kind "
                 "code = the data's (date, time, sources, link): shown as is.",
        "facts": fx, "slots": slots}, ensure_ascii=False, indent=1), encoding="utf-8")
    if b["logo"]["kind"] == "svg":  # chrome() copies them
        code += ["assets/logo-header.svg", "assets/logo-end.svg"]
    (project / "compositions" / "chrome.html").write_text(chrome(t, b, project, prog.get("chrome", "news")),
                                                          encoding="utf-8")
    (project / "compositions" / "captions.html").write_text(captions_html(p["captions"], t, b), encoding="utf-8")
    index = project / "index.html"
    text, hosts = bind_index(index.read_text(encoding="utf-8"), t, fx, slots)
    index.write_text(text, encoding="utf-8")
    (project / VEASY_JS).write_text(veasy_js(fx, t, hosts, slots), encoding="utf-8")
    code.append(VEASY_JS)
    lock = {"about": "The sha256 of every file Veasy wrote here (compose check: an edited one is a problem; engine "
                     "compose scaffold restores them).", "chrome": CHROME_VERSION, "hyperframes": HF_VERSION,
            "brand": b["name"], "theme": b["theme"], "story": story["id"], "engine": engine,
            "files": {f: sha(project / f) for f in sorted(set(code)) if (project / f).exists()}}
    (project / DONE_FILE).write_text(json.dumps(lock, indent=1), encoding="utf-8")
    return {"project": project, "timing": t, "props": p, "work": work, "facts": fx, "story": story, "brand": b,
            "slots": slots, "hosts": hosts, "problems": problems, "program": prog}


def media(story, b, project):
    """The story's pictures (the media layer, tt_shorts/assets.py): the same ledger files Lane A draws, copied into
    assets/media/<id>.<ext> by assets.for_props, and assets/media.json with each one's label and credit, the scene it
    belongs to and the ledger. A scene may use only these (lint net: nothing else). -> the written paths (Veasy's
    files: hashed in the lock)."""
    from tt_shorts import assets
    drawn = assets.for_props(story, b, project / "assets", FPS)
    (project / "assets" / "media.json").write_text(json.dumps({
        "pictures": {k: {**v, "src": f"assets/{v['src']}"} for k, v in drawn.items()},
        "scenes": {i: s["media"]["asset"] for i, s in enumerate(story.get("scenes") or []) if s.get("media")},
        "ledger": story.get("assets") or []}, ensure_ascii=False, indent=1), encoding="utf-8")
    return ["assets/media.json"] + [f"assets/{v['src']}" for v in drawn.values()]


def plate_files(story, b, project):
    """The story's baked plates (plates.py), toned for this theme, as assets/plates/<ledger id>.mp4 and assets/plates.json
    ({scene: ledger id, plates: {id: {src, frames, tracks}}}). A scene plays one with a plain <video muted playsinline
    src>; the `plate` block does it all. Veasy's files: hashed in the lock. A plate gc took is left out (the scene's
    <video> then fails lint: bake it again)."""
    from tt_shorts import plates
    drawn = plates.for_props(story, b, project / "assets", flat=True)
    if not drawn:
        return []
    (project / "assets" / "plates.json").write_text(json.dumps({
        "about": "Baked plates (compose.plate_files): play assets/<src> in a <video muted playsinline>, behind a card on "
                 "var(--canvas-90); tracks are the plate's anchors, page pixels at 30 fps.",
        "scenes": {i: s["plate"]["asset"] for i, s in plates.plate_scenes(story) if s.get("plate")},
        "plates": {k: {**v, "src": f"assets/{v['src']}"} for k, v in drawn.items()}}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return ["assets/plates.json"] + [f"assets/{v['src']}" for v in drawn.values()]


def sfx_cues(t, setting="off"):
    """The sound effects of a composed film (format key sfx, sfx.py's sounds; the mix is props.mix_audio's): a whoosh
    on every meter wipe, and every beat that names one ("sfx": "pop"). [] when the format says off."""
    from tt_shorts import sfx
    if setting not in ("on", "meaning"):
        return []
    out = [] if setting == "meaning" else [{"t": max(0.0, w - sfx.WHOOSH_LEAD), "name": "whoosh"} for w in t["wipes"]]  # a wipe is a cut: meaning gives it no sound
    out += [{"t": b["t"], "name": b["sfx"]} for b in t["beats"] if b.get("sfx") in sfx.NAMES]
    kept = []
    for c in sorted(out, key=lambda c: c["t"]):
        if c["t"] < t["duration"] - 0.05 and (not kept or c["t"] - kept[-1]["t"] >= sfx.MIN_GAP):
            kept.append({"t": round(c["t"], 3), "name": c["name"]})
    return kept


def lock_problems(project):
    """Veasy's files of a project, against .veasy/lock.json: edited, missing, or an older locked set."""
    project = pathlib.Path(project)
    path = project / DONE_FILE
    if not path.exists():
        return [f"lock: {project} was not scaffolded by Veasy (no {DONE_FILE}): run engine compose scaffold"]
    lock = json.loads(path.read_text(encoding="utf-8"))
    out = []
    if lock.get("chrome") != CHROME_VERSION:
        out.append(f"lock: the locked chrome is v{lock.get('chrome')}, Veasy's is v{CHROME_VERSION}: run engine compose "
                   "scaffold to update it")
    for f, h in lock.get("files", {}).items():
        p = project / f
        if not p.exists():
            out.append(f"lock: {f} is missing (Veasy's file): run engine compose scaffold to restore it")
        elif sha(p) != h:
            out.append(f"lock: {f} was edited; it is Veasy's (locked v{CHROME_VERSION}): never edit, restyle or "
                       "replace it; run engine compose scaffold to restore it")
    return out


# ---------------------------------------------------------------- our lint (the agent's files)

TOKEN = re.compile(r"(<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>|<[^<>]+>)", re.S | re.I)
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "path",
        "circle", "rect", "line", "polyline", "polygon", "ellipse", "stop", "use"}
HEX = re.compile(r"(?<![\w#-])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})(?![\w-])")
FUNC_COLOR = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(", re.I)
NAMED = ("white", "black", "red", "green", "blue", "yellow", "orange", "purple", "pink", "gray", "grey", "brown",
         "cyan", "magenta", "gold", "silver", "navy", "teal", "maroon", "lime", "olive", "coral", "salmon")
NAMED_COLOR = re.compile(r"(?:\b(?:color|background(?:-color)?|fill|stroke|border(?:-\w+)?|outline|box-shadow|"
                         r"text-shadow|backgroundColor|borderColor)\s*[:=]\s*[\"']?[^;\"'{}<>]*?\b(" + "|".join(NAMED) +
                         r")\b)", re.I)
FONT = re.compile(r"font-family\s*:\s*([^;}\"]+|\"[^\"]*\"[^;}]*)|fontFamily\s*:\s*[\"']([^\"']+)", re.I)
LINK = re.compile(r"(?:https?:)?//(?!www\.w3\.org/(?:2000/svg|1999/xlink))[\w.-]+\.[a-z]{2,}|(?<![/\w.])www\.(?!w3\.org\b)[\w-]+\.[a-z]{2,}", re.I)
DOMAIN = re.compile(r"\b[\w-]+\.(?:ge|com|org|net|io|ai|app|dev|today|tv|info|co)\b", re.I)
NET = re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts)\s*\(|\bimport\s*\(", re.I)
CANVAS = re.compile(r"<canvas\b|getContext\s*\(|\bfillText\s*\(|\bstrokeText\s*\(|OffscreenCanvas|webgl|\bTHREE\.",
                    re.I)
SRC = re.compile(r"\b(src|href|xlink:href|data-var-src|poster)\s*=\s*[\"']([^\"']*)[\"']", re.I)
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.I)
FACT_TEXT = re.compile(r"\d|[„“”]")
CSS_CONTENT = re.compile(r"(?<![\w-])content\s*:\s*([^;}]+)", re.I)
CSS_EMPTY = re.compile(r"""^(?:""|''|none|normal)$""", re.I)
# numbers the browser writes itself: a counter, a list's markers, a form field's value
GENERATED = re.compile(r"\bcounters?\s*\(|\bcounter-(?:reset|increment|set)\b|@counter-style\b|"
                       r"list-style(?:-type)?\s*:\s*(?!none\b|disc\b|circle\b|square\b|inherit\b|initial\b)[\w-]+", re.I)
GENERATED_TAG = re.compile(r"<(?:ol|input)\b", re.I)
SVG_BLOCK = re.compile(r"<svg\b.*?</svg\s*>", re.S | re.I)
PATH_D = re.compile(r"<path\b[^>]*?\sd\s*=\s*[\"']([^\"']+)[\"']", re.I)
PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
PATH_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}
EASE = re.compile(r"""\bease\s*:\s*["']([^"']+)""")
FROM_BLOCK = re.compile(r"<!--\s*block\s+([\w-]+)")
LINE_GLYPHS = 3  # outlined-text: this many glyph-like shapes on one line...
LINE_KINDS = 2  # ...of at least this many different shapes (a row of equal dots or rounded bars is no word)
LINT_RULES = ("color", "font", "link", "net", "canvas", "probe", "fact", "host", "locked", "art",
              "timeline", "prefix", "template", "css-content", "outlined-text")  # lint()'s names


def _tags(text):
    """Walk an HTML file -> [(kind, token, stack)]: kind tag|text|script|style|comment; stack: the open elements'
    start tags (outermost first) at that point."""
    out, stack = [], []
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            out.append(("text", text[pos:m.start()], list(stack)))
        tok = m.group(0)
        low = tok[:8].lower()
        if tok.startswith("<!--"):
            out.append(("comment", tok, list(stack)))
        elif low.startswith("<script"):
            out.append(("script", tok, list(stack)))
        elif low.startswith("<style"):
            out.append(("style", tok, list(stack)))
        elif tok.startswith("</"):
            name = tok[2:].strip(" >").lower()
            for k in range(len(stack) - 1, -1, -1):
                if re.match(rf"<{re.escape(name)}\b", stack[k], re.I):
                    del stack[k:]
                    break
            out.append(("close", tok, list(stack)))
        elif tok.startswith("<!") or tok.startswith("<?"):
            out.append(("comment", tok, list(stack)))
        else:
            out.append(("tag", tok, list(stack)))
            name = re.match(r"<([a-zA-Z][\w:-]*)", tok)
            if name and not tok.endswith("/>") and name.group(1).lower() not in VOID:
                stack.append(tok)
        pos = m.end()
    if pos < len(text):
        out.append(("text", text[pos:], list(stack)))
    return out


def _local(project, f, ref):
    """A src/href that stays inside the project, or why not (None when fine)."""
    ref = ref.strip()
    if not ref or ref.startswith("#") or ref.startswith("data:"):
        return None
    if re.match(r"^[a-z][\w+.-]*:", ref, re.I) or ref.startswith("//"):
        return f"{ref[:60]} is not a local file (no network at render)"
    p = (project / ref.split("?")[0].split("#")[0]).resolve()
    if not str(p).startswith(str(project.resolve())):
        return f"{ref} leaves the project folder"
    if not p.exists():
        return f"{ref} does not exist in the project"
    return None


def lint(project, b=None):
    """Our rules on the agent's files -> [problem strings]. Every rule is named:
      color   no typed color: no hex, rgb()/hsl()... or color names; only var(--token) from assets/brand.css
      font    no font but "Brand" (assets/brand.css): no other family, no @font-face, no font file of its own
      link    no typed link or domain (the link is the chrome's, from the pack)
      net     nothing from the network: every src/href/url() a file inside the project, scripts only
              assets/vendor/gsap.min.js, no fetch/XHR/WebSocket/import()
      canvas  no <canvas>, 2D/WebGL context or drawn text: text the DOM can't read can't be checked
      probe   every text inside a data-probe region (the layout probe and the checks read regions)
      fact    no typed fact: a digit or a „quote“ in a text node is a fact; bind it (data-var-text)
      host      index.html hosts compositions/chrome.html and captions.html, no scene host at or above their z-index
      locked    Veasy's files unchanged (sha256, .veasy/lock.json), and no agent file in their place
      art       an SVG of the agent's (assets/art/) holds no text and no typed color
      timeline  sub-compositions must register their GSAP timeline on window.__timelines["<id>"]
      prefix    all element IDs in a sub-composition must be prefixed with the composition id or 'root'
      template  sub-compositions must be wrapped in <template> and declare data-composition-id
      css-content    no text the browser generates: CSS content (only an empty ""), counters, a list's numbers, an
                     input; none of it is in the DOM, so no check reads it (the probe's `generated` sees the rest)
      outlined-text  no line of glyphs drawn as SVG paths (a heuristic, outlined_text(): it holds, it never refuses)"""
    project = pathlib.Path(project).resolve()
    out = []
    brand_words = []
    if b:
        brand_words = [b["link"]["display"].split("/")[0].lower(), b["wordmark"]["text"].lower()]

    def bad(rule, f, msg):
        out.append(f"lint {rule}: {f}: {msg}")

    files = agent_files(project)
    for f in files:
        path = project / f
        if not f.endswith((".html", ".svg")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lstrip("﻿")  # bind_index's BOM
        is_index = f == "index.html"
        toks = _tags(text)
        code = "".join(tok for kind, tok, _ in toks if kind != "comment")
        for m in dict.fromkeys(HEX.findall(_no_selectors(code))):
            bad("color", f, f"typed color {m}: use var(--token) (assets/brand.css)")
        for m in dict.fromkeys(x.group(0) for x in FUNC_COLOR.finditer(code)):
            bad("color", f, f"typed color {m}…): use var(--token); a tint is a token too (--ink-10, --canvas-90)")
        for m in dict.fromkeys(x.group(1) for x in NAMED_COLOR.finditer(code)):
            bad("color", f, f"color name {m!r}: use var(--token)")
        for m in FONT.finditer(code):
            fam = (m.group(1) or m.group(2) or "").strip().strip("\"'")
            first = fam.split(",")[0].strip().strip("\"'")
            if first not in ("Brand", "inherit", "var(--font)") and fam:
                bad("font", f, f"font-family {fam[:40]!r}: the face is \"Brand\" (the pack's, assets/brand.css)")
        if re.search(r"@font-face|@import", code, re.I):
            bad("font", f, "@font-face/@import in a scene: the pack's font comes from assets/brand.css")
        for m in dict.fromkeys(x.group(0) for x in LINK.finditer(code)):
            bad("link", f, f"typed link {m[:60]}: links are the chrome's (the pack's), never a scene's")
        for m in dict.fromkeys(x.group(0) for x in NET.finditer(code)):
            bad("net", f, f"{m.strip()}: no network at render")
        for m in dict.fromkeys(x.group(0) for x in CANVAS.finditer(code)):
            bad("canvas", f, f"{m}: text drawn in a canvas or WebGL can't be read from the DOM; draw with DOM/SVG")
        if re.search(r"<iframe\b|<object\b|<embed\b", code, re.I):
            bad("net", f, "<iframe>/<object>/<embed>: not in a film")
        css = [re.sub(r"/\*.*?\*/", "", tok, flags=re.S) for kind, tok, _ in toks if kind == "style"]
        css += [_attr(tok, "style") or "" for kind, tok, _ in toks if kind == "tag"]
        for m in dict.fromkeys(x.group(1).strip() for sheet in css for x in CSS_CONTENT.finditer(sheet)):
            if not CSS_EMPTY.match(re.sub(r"\s*!important$", "", m, flags=re.I)):
                bad("css-content", f, f"content: {m[:40]}: text in CSS is not in the DOM, so no check can read it; "
                                      "put it in the scene and bind it (a shape's content is \"\")")
        for m in dict.fromkeys(x.group(0) for sheet in css for x in GENERATED.finditer(sheet)):
            bad("css-content", f, f"{m}: a number the browser writes is not in the DOM; bind it from facts.json")
        for m in dict.fromkeys(x.lower() for kind, tok, _ in toks if kind == "tag" for x in GENERATED_TAG.findall(tok)):
            bad("css-content", f, f"{m}>: its numbers or value are not DOM text; use a plain element and bind them")
        for block in SVG_BLOCK.findall(code):
            n = outlined_text(block)
            if n:
                bad("outlined-text", f, f"{n} shapes on one line look like letters or digits drawn as paths: words and "
                                        "numbers stay DOM text, bound (an SVG <text> is fine)")
        for kind, tok, stack in toks:
            if kind == "tag" or kind == "script":
                for attr, ref in SRC.findall(tok if kind == "tag" else tok.split(">", 1)[0] + ">"):
                    why = _local(project, f, ref)
                    if why:
                        bad("net", f, f"{attr}: {why}")
                if kind == "script":
                    src = re.match(r"<script\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)", tok, re.I)
                    if src and not (is_index and src.group(1) in ("assets/vendor/gsap.min.js", VEASY_JS)):
                        bad("net", f, f"<script src={src.group(1)!r}>: the only scripts are assets/vendor/gsap.min.js "
                                      f"and {VEASY_JS}, in index.html")
            if kind in ("style", "tag"):
                for ref in CSS_URL.findall(tok):
                    why = _local(project, f, ref)
                    if why:
                        bad("net", f, f"url({ref[:40]}): {why}")
            if kind == "tag" and re.match(r"<link\b", tok, re.I):
                href = _attr(tok, "href") or ""
                if href != "assets/brand.css":
                    bad("font" if "font" in href else "net", f, f"<link href={href!r}>: the only stylesheet is "
                                                                 "assets/brand.css")
            if kind == "text" and tok.strip():
                inside = [s for s in stack]
                if any(re.match(r"<(?:script|style|title)\b", s, re.I) for s in inside):
                    continue
                bound = any(_attr(s, "data-var-text") is not None for s in inside)
                region = any(_attr(s, "data-probe") is not None for s in inside)
                words = " ".join(tok.split())
                if words in ("…", "...") and bound:
                    continue
                if not region and not is_index:
                    bad("probe", f, f"„{words[:40]}“ is outside any data-probe region")
                if is_index and not region:
                    bad("probe", f, f"„{words[:40]}“: text in index.html; put it in a scene, inside a data-probe region")
                if not bound and FACT_TEXT.search(words):
                    bad("fact", f, f"„{words[:40]}“ types a fact (a number, date or quote): bind it from facts.json "
                                   "(data-var-text=\"<id>\")")
                for d in DOMAIN.findall(words):
                    if not bound:
                        bad("link", f, f"„{d}“ is a link typed in a scene: links are the chrome's")
                for w in brand_words:
                    if w and w in words.lower() and not bound:
                        bad("link", f, f"„{w}“: the pack's link and name are the chrome's")
        if f.startswith("assets/art/") and f.endswith(".svg") and re.search(r"<text\b", text, re.I):
            bad("art", f, "text in an image: put words in the scene's DOM, inside a data-probe region")
        is_subcomp = f.startswith("compositions/") and f.endswith(".html") and f not in LOCKED
        if is_subcomp:
            has_template = bool(re.search(r"<template\b", text, re.I) and re.search(r"</template\s*>", text, re.I))
            if not has_template:
                bad("template", f, "sub-composition must be wrapped in <template>...</template>")
            cid_m = re.search(r'data-composition-id\s*=\s*[\"\']([\w-]+)[\"\']', text)
            if not cid_m:
                bad("template", f, "sub-composition root element must declare data-composition-id=\"<id>\"")
            cid = cid_m.group(1) if cid_m else None
            if re.search(r"<script\b", text, re.I):
                tl_m = re.search(r"window\.__timelines\s*\[\s*[\"']([\w-]+)[\"']\s*\]\s*=", text)
                if not tl_m:
                    bad("timeline", f, f"sub-composition script must register its timeline on window.__timelines[\"{cid or 'id'}\"]")
            if cid:
                for mid in re.finditer(r'\bid\s*=\s*[\"\']([^\"\']+)[\"\']', text):
                    el_id = mid.group(1)
                    if el_id != "root" and el_id != cid and not el_id.startswith(f"{cid}-") and not el_id.startswith(f"{cid}_"):
                        bad("prefix", f, f"element id {el_id!r} must be prefixed with '{cid}-' (or equal 'root') to prevent collisions")
        if is_index:
            for need in LOCKED:
                if not re.search(rf"data-composition-src\s*=\s*[\"']{re.escape(need)}[\"']", text):
                    bad("host", f, f"no host for {need}: the locked chrome and captions are always placed")
            for tag in TAG.findall(text):
                src = _attr(tag, "data-composition-src")
                z = re.search(r"z-index\s*:\s*(-?\d+)", _attr(tag, "style") or "")
                if src and src not in LOCKED and z and int(z.group(1)) >= SCENE_TOP_Z:
                    bad("host", f, f"{src} sits at z-index {z.group(1)}: scenes stay under the chrome "
                                   f"(z-index < {SCENE_TOP_Z})")
    for f in LOCKED:
        if f in files:
            bad("locked", f, "is Veasy's")
    out += [f"lint locked: {x[len('lock: '):]}" for x in lock_problems(project)]
    return out


def _subpaths(d):
    """A path's closed subpaths -> [(x0, y0, x1, y1, segments, curves)]. Boxes come from every point a command names,
    control points included: close enough to tell a glyph's size."""
    toks = PATH_TOKEN.findall(d)
    out, xs, ys = [], [], []
    x = y = sx = sy = 0.0
    segs = curves = i = 0
    cmd = None
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                if xs:
                    out.append((min(xs), min(ys), max(xs), max(ys), segs, curves))
                xs, ys, segs, curves = [], [], 0, 0
                x, y = sx, sy
                continue
        if cmd is None or cmd in "Zz":  # numbers with no command before them: not a path we can read
            break
        up, rel = cmd.upper(), cmd.islower()
        n = PATH_ARGS[up]
        vals = [float(v) for v in toks[i:i + n] if not v.isalpha()]
        if len(vals) < n:
            break
        i += n
        if up == "H":
            pts = [(vals[0] + (x if rel else 0), y)]
        elif up == "V":
            pts = [(x, vals[0] + (y if rel else 0))]
        else:
            pair = vals[-2:] if up == "A" else vals
            pts = [(pair[k] + (x if rel else 0), pair[k + 1] + (y if rel else 0)) for k in range(0, len(pair), 2)]
        x, y = pts[-1]
        xs += [p[0] for p in pts]
        ys += [p[1] for p in pts]
        if up == "M":
            sx, sy = x, y
            cmd = "l" if rel else "L"  # a moveto's further pairs are lines
        else:
            segs += 1
            curves += up in "CSQTA"
    return out


def outlined_text(svg):
    """An SVG's largest line of glyph-like shapes (0 when it has none): at least LINE_GLYPHS outer closed shapes of
    about one height on one line, most of them curved, in at least LINE_KINDS different shapes: what a font tool draws.
    A heuristic: a short number can pass under it, so a composed film is still held for a person's eye."""
    shapes = [s for d in PATH_D.findall(svg) for s in _subpaths(d)][:600]
    outer = [s for s in shapes if not any(o is not s and o[0] <= s[0] and o[1] <= s[1] and o[2] >= s[2] and o[3] >= s[3]
                                          for o in shapes)]
    glyphs = [s for s in outer if s[3] > s[1] and s[2] > s[0] and s[2] - s[0] <= 1.6 * (s[3] - s[1])]
    best = 0
    for seed in glyphs:
        h, mid = seed[3] - seed[1], (seed[1] + seed[3]) / 2
        line = [s for s in glyphs if abs((s[1] + s[3]) / 2 - mid) <= h / 2 and h / 2 <= s[3] - s[1] <= 2 * h]
        curved = sum(1 for s in line if s[5])
        if len(line) >= LINE_GLYPHS and len({s[4] for s in line}) >= LINE_KINDS and curved * 2 >= len(line):
            best = max(best, len(line))
    return best


def _no_selectors(code):
    """CSS with its selectors removed (an id like #s3-num is not a color): only declaration bodies, attribute values
    and script text stay."""
    def bodies(m):
        css = m.group(0)
        return " ".join(re.findall(r"\{([^{}]*)\}", css))
    return re.sub(r"<style\b.*?</style>", bodies, code, flags=re.S | re.I)


# ---------------------------------------------------------------- what a film is made of (variety's guard)


def film_kinds(project):
    """A composed film's scenes in film order -> [kind]: the block it started from (its comment, which an edit keeps),
    else own-<crc of its tags>, which two scenes share only with one structure."""
    project = pathlib.Path(project)
    out = []
    for src in re.findall(r"data-composition-src\s*=\s*[\"']([^\"']+)", (project / "index.html").read_text(
            encoding="utf-8", errors="replace")):
        if src in LOCKED or not (project / src).exists():
            continue
        text = (project / src).read_text(encoding="utf-8", errors="replace")
        block = FROM_BLOCK.search(text)
        out.append(block.group(1) if block else
                   f"own-{zlib.crc32(' '.join(re.findall(r'<([a-zA-Z][\w:-]*)', text)).encode()):08x}")
    return out


def film_style(project, music=None):
    """A composed film in variety's words -> (style, scene kinds): style's hook is its opening scene, enter the ease
    its scenes use most, with its template and music loop (variety.assess_composed, variety.record)."""
    project = pathlib.Path(project)
    kinds = film_kinds(project)
    scenes = [p for p in sorted((project / "compositions").glob("*.html")) if f"compositions/{p.name}" not in LOCKED]
    eases = collections.Counter(e for p in scenes for e in EASE.findall(p.read_text(encoding="utf-8", errors="replace"))
                                if e != "none")
    return {"hook": kinds[0] if kinds else None, "enter": eases.most_common(1)[0][0] if eases else None,
            "template": template_of(project), "music": music, "transition": "composed"}, kinds


def missing_notes(project, names):
    """Warnings for a film's notes that aren't in its project yet (the skill's idea and review steps)."""
    project = pathlib.Path(project)
    return [f"film: no {n} in the project: veasy:compose starts from an idea and ends with a review"
            for n in names if not (project / n).exists()]


# ---------------------------------------------------------------- check: the DOM's texts, the probe, HyperFrames


def settled(t):
    """(label, seconds) of each beat once its entrance has landed: 0.7 s in, or just before the next beat."""
    beats, out = t["beats"], []
    for i, b in enumerate(beats):
        nxt = beats[i + 1]["t"] if i + 1 < len(beats) else t["duration"]
        out.append((b["id"], round(min(b["t"] + 0.7, nxt - 0.05), 2)))
    return out


def rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


WORDMARK_ACCENT = {"."}  # the accent's own character in the pack's wordmark (tbilisi.today's dot) is the brand's


def accent_text(report, accent):
    want = rgb(accent)
    return [{"rule": "accent", "region": t.get("region"), "text": t.get("text", ""),
             "detail": f"„{t.get('text', '')[:40]}“ is drawn in the accent {accent} (the accent is never text)"}
            for t in report.get("texts") or [] if t.get("color") == want and t.get("text", "").strip() not in WORDMARK_ACCENT]


# A cut: two scenes live at once. The settled frames can't see it, so the probe reads every other frame of the overlap.
CUT_EVERY = 2  # frames between readings
CUT_READINGS = 15  # at most, on a long overlap
CUT_GRID = 20  # px between the points a cut is read at
CUT_OPACITY = 0.2  # fainter than this, a scene coming or going is a ghost, not a thing on screen
CUT_HIDDEN = 0.75  # a text this far under something solid (a wipe's bars, a panel) is gone, not in a collision
CUT_HOLD = 0.1  # seconds: what a viewer can catch
CUT_TEXT = 0.1  # two texts collide when they share this much of the smaller one
CUT_CELLS = 3  # a text collides with the other scene's drawing at this many grid points
CUT_ART = 0.01  # two scenes draw on this share of the frame: a warning, since a match cut does it on purpose


def host_spans(html):
    """{scene host: (start, end)} of a built index.html."""
    out = {}
    for tag in TAG.findall(re.sub(r"<!--.*?-->", "", html, flags=re.S)):
        cid, start, length = (_attr(tag, k) for k in ("data-composition-id", "data-start", "data-duration"))
        if cid and cid not in ("main", "chrome", "captions") and start is not None and length is not None:
            out[cid] = (float(start), round(float(start) + float(length), 3))  # 19.194000000000003 touches 19.194
    return out


def cuts(spans):
    """[(old, new, from, to)]: a host that starts inside another and outlives it. One that lasts through another (a
    layer over the film) is no cut, and hosts that touch end to end never share a frame."""
    order = sorted(spans.items(), key=lambda kv: kv[1])
    return [(a, b, sb, ea) for i, (a, (sa, ea)) in enumerate(order) for b, (sb, eb) in order[i + 1:] if sa < sb < ea < eb]


def cut_times(start, end):
    """The frames a cut is read at, in seconds."""
    first, last = math.ceil(start * FPS - 1e-6), math.ceil(end * FPS - 1e-6)
    every = max(CUT_EVERY, math.ceil((last - first) / CUT_READINGS))
    return [round(f / FPS, 3) for f in range(first, last, every)]


def _shared(a, b):
    """How much of the smaller of two boxes (x, y, w, h) they share, 0..1."""
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return w * h / max(1.0, min(a[2] * a[3], b[2] * b[3])) if w > 0 and h > 0 else 0.0


def _cells_in(box, cells):
    """How many grid points of `cells` (compose/probe.mjs: row * columns + column) lie inside a box."""
    x, y, w, h = box
    cols, rows = math.ceil(W / CUT_GRID), math.ceil(H / CUT_GRID)
    xs = range(max(0, int(x // CUT_GRID)), min(cols, math.ceil((x + w) / CUT_GRID)))
    ys = range(max(0, int(y // CUT_GRID)), min(rows, math.ceil((y + h) / CUT_GRID)))
    return sum(r * cols + c in cells for r in ys for c in xs)


def cut_hits(report, a, b):
    """One reading of a cut -> (what collides with a text, the share of the frame both scenes draw on)."""
    def shown(scene):
        return [x for x in report.get("texts") or [] if x.get("comp") == scene and x.get("text", "").strip()
                and not x.get("decor") and (x.get("opacity") or 0) >= CUT_OPACITY and (x.get("hidden") or 0) < CUT_HIDDEN]

    cells = {c: set((report.get("cells") or {}).get(c) or ()) for c in (a, b)}
    hits = [f"{probe._quote(x['text'])} on {probe._quote(y['text'])}" for x in shown(a) for y in shown(b)
            if _shared(x["box"], y["box"]) >= CUT_TEXT]
    for scene, other in ((a, b), (b, a)):
        hits += [f"{probe._quote(x['text'])} on {other}'s drawing" for x in shown(scene)
                 if _cells_in(x["box"], cells[other]) >= CUT_CELLS]
    total = math.ceil(W / CUT_GRID) * math.ceil(H / CUT_GRID)
    return hits, len(cells[a] & cells[b]) / total


def cut_problems(a, b, rows):
    """A cut's readings [{"t", "probe"}] -> (problems, warnings). Text in a collision is a problem: nobody can read it.
    Two drawings on one spot are a warning: that is a mistake or a match cut, and only the film knows which."""
    step = rows[1]["t"] - rows[0]["t"] if len(rows) > 1 else CUT_EVERY / FPS
    read = [(x["t"], *cut_hits(x["probe"], a, b)) for x in rows]
    texts, art = [x for x in read if x[1]], [x for x in read if x[2] >= CUT_ART]
    problems, warnings = [], []
    if len(texts) * step >= CUT_HOLD:
        problems.append(f"probe cut: {a} to {b} at {texts[0][0]:.2f}s: {texts[0][1][0]} for {len(texts) * step:.2f} s: "
                        "end the old scene before the new one lands, or cover the overlap with a wipe")
    if len(art) * step >= CUT_HOLD:
        worst = max(art, key=lambda x: x[2])
        warnings.append(f"cut: {a} to {b} at {art[0][0]:.2f}s: both scenes draw on {worst[2]:.0%} of the frame for "
                        f"{len(art) * step:.2f} s: right for a match cut, a collision otherwise")
    return problems, warnings


def run_probe(project, t, b, shots=None):
    """compose/probe.mjs at each beat's settled time and through every cut -> {"reports", "problems", "warnings",
    "blocked", "frames", "texts", "cuts"}."""
    project = pathlib.Path(project).resolve()
    points = settled(t)
    overlaps = [(x, y, cut_times(s, e)) for x, y, s, e in cuts(host_spans((project / "index.html").read_text(encoding="utf-8")))]
    overlaps = [c for c in overlaps if c[2]]
    spec = {"project": str(project), "times": [x for _, x in points], "labels": [x for x, _ in points],
            "shots": str(pathlib.Path(shots).resolve()) if shots else None, "cutGrid": CUT_GRID,
            "cutOpacity": CUT_OPACITY, "cuts": [{"a": x, "b": y, "times": ts} for x, y, ts in overlaps]}
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)
    r = subprocess.run([shutil.which("node") or "node", str(PROBE_JS)], input=json.dumps(spec), capture_output=True,
                       text=True, encoding="utf-8", timeout=900, env={**os.environ, **ENV})
    rows = [json.loads(x) for x in r.stdout.splitlines() if x.startswith("{")]
    fatal = next((x["fatal"] for x in rows if x.get("fatal")), None)
    if fatal or not rows:
        raise ComposeError(f"probe failed: {(fatal or r.stderr or 'no output')[-600:]}")
    reports = [x["probe"] for x in rows if x.get("probe") and "cut" not in x]
    cmaps = probe.cmaps_for(project / "assets")
    strings, _ = probe.problems(reports, cmaps)
    if "text" in ((b.get("design") or {}).get("accent") or {}).get("never", []):  # only a pack that says so
        for rep in reports:
            for it in accent_text(rep, b["colors"]["accent"]):
                strings.append(f"probe accent: {rep['scene']} at {rep['frame'] / FPS:.2f}s: {it['detail']}")
    seen = set()
    for rep in reports:
        for x in rep["texts"]:
            if x.get("region") == "other" and x["text"].strip() and x["text"] not in seen:
                seen.add(x["text"])
                strings.append(f"probe region: {rep['scene']} at {rep['frame'] / FPS:.2f}s: „{x['text'][:40]}“ is "
                               "outside any data-probe region")
    for rep in reports:  # what CSS or a script made the browser write: lint css-content can only read the files
        for g in rep.get("generated") or []:
            if (g["comp"], g["content"]) not in seen:
                seen.add((g["comp"], g["content"]))
                strings.append(f"probe generated: {rep['scene']} at {rep['frame'] / FPS:.2f}s: {g['comp']} generates "
                               f"{g['content'][:40]}, text no check can read: put it in the DOM, bound")
    done = next((x for x in rows if x.get("done")), {})
    blocked = done.get("blocked", [])
    strings += [f"probe net: the page asked for {u[:80]} (refused: no network at render)" for u in blocked]
    warned = []
    for i, (x, y, _) in enumerate(overlaps):
        found, notes = cut_problems(x, y, [r for r in rows if r.get("cut") == i])
        strings += found
        warned += notes
    return {"reports": reports, "problems": strings, "warnings": warned, "blocked": blocked, "frames": len(reports),
            "texts": sum(len(x["texts"]) for x in reports), "fonts": reports[0]["fonts"] if reports else {},
            "cuts": len(overlaps)}


def screen_texts(reports, fx, notes=None):
    """The texts a film shows that its story is answerable for: every text the probe read, without the captions (the
    narration, checked as such), the chrome's data (data-veasy-code), texts bound to the data's facts, and texts
    bound to a story fact that show it (the story's checks judged it). A bound text that shows something else at a
    settled frame (a count still running, a script's change) is noted in `notes` and not judged as a claim."""
    out = []
    for rep in reports:
        for x in rep["texts"]:
            if x.get("region") == "captions" or x.get("code"):
                continue
            s = " ".join(x["text"].split())
            fact = fx.get(x.get("bound") or "")
            if fact:
                if fact["kind"] == CODE_KIND or THOUSANDS.sub("", s) == THOUSANDS.sub("", " ".join(fact["value"].split())):
                    continue
                if notes is not None:
                    notes.append(f"motion: „{s[:30]}“ (bound to {x['bound']} = „{fact['value'][:30]}“) at "
                                 f"{rep['frame'] / FPS:.2f}s ({rep['scene']}): still moving at the beat's settled "
                                 "frame, or changed by a script")
                continue
            if s and s not in out:
                out.append(s)
    return out


THOUSANDS = re.compile(r"(?<=\d)[   ](?=\d{3}(?!\d))")


def text_problems(story, texts, sources=None):
    """The story's rule tier, ka_check (and kaeasy through it) on the texts a film shows (read from its DOM), as if
    they were one scene's on-screen text. 6 400 is read as 6400 (a thousands space)."""
    from tt_shorts import claims_check, ka_check, news_check
    shown = [THOUSANDS.sub("", t) for t in texts]
    pseudo = {**{k: v for k, v in story.items() if k not in ("scenes", "cta")}, "narration": "",
              "scenes": [{"type": "hook", "at": "", "lines": shown}]}
    tier = programs.of(story)["rules"] if "program" in story else "news"
    out = []
    if tier == "news":
        out += news_check.problems(pseudo, sources) if sources else []
    else:
        out += claims_check.problems(pseudo, sources or [], tier, allow=programs._allow_names(story))
    out += ka_check.problems(pseudo, {"title": "", "description": "", "text": " ".join(sources or [])})
    if not sources:
        out = [x for x in out if "is quoted but not in the article" not in x]
    return [f"screen: {x}" for x in dict.fromkeys(out)]


# hyperframes check findings that are Veasy's by design: the sound is mixed after the render (props.mix_audio)
HF_KNOWN = ("film_silent",)


def hf_check(project):
    """`hyperframes check --json` (lint, runtime, layout, contrast, craft, audio) -> (problems, warnings, summary).
    Its errors hold the film; its warnings are shown. Software GL, as at render."""
    r = hyperframes(["check", str(project), "--json", "--no-browser-gpu"], timeout=900)
    try:
        d = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        return [f"hyperframes check: no report ({(r.stderr or r.stdout)[-300:]})"], [], {}
    problems, warnings, summary = [], [], {}
    for part in ("lint", "runtime", "layout", "motion", "contrast", "craft", "audio"):
        sec = d.get(part) or {}
        summary[part] = {k: sec.get(k) for k in ("errorCount", "warningCount")}
        for fnd in sec.get("findings") or []:
            if fnd.get("code") in HF_KNOWN:
                continue
            line =(f"hyperframes {part} {fnd.get('code') or fnd.get('rule') or ''}: "
                    f"{fnd.get('sourceFile') or fnd.get('file') or ''} {fnd.get('message', '')[:160]}"
                    + (f" „{fnd['text'][:30]}“" if fnd.get("text") else "")).strip()
            if fnd.get("severity") == "error":
                problems.append(line)
            elif fnd.get("severity") == "warning":
                warnings.append(line)
    return problems, warnings, summary


def default_sources(story_path):
    side = store.sources_path(story_path)
    return json.loads(side.read_text(encoding="utf-8")) if side.exists() else None


def check(story_path, brand=None, project=None, engine="silent", sources=None, hf=True, shots=None, music="off",
          tone=None, built=None, theme="default", fmt=None):
    """Every check of a composed film -> {"problems", "warnings", ...}: the story's own checks (engine check), Veasy's
    files unchanged, our lint, the probe at every beat's settled frame (layout rules, the pack's accent rule, texts
    outside a region, network asked for) and through every cut, the story's rule tier + ka_check + kaeasy on every text the DOM shows,
    slots filled, and `hyperframes check`. A film too close to the brand's other composed films is a warning (novelty),
    as is one without its notes. The project is rebuilt first (the agent's files stay)."""
    from tt_shorts import engine as eng, variety
    t0 = time.time()
    story = _story(story_path, brand)
    b = packs.of(story)
    project = pathlib.Path(project or project_dir(story, b["name"])).resolve()
    res = {"project": str(project), "story": str(pathlib.Path(story_path).resolve()), "brand": b["name"],
           "film_engine": "hyperframes", "voice": engine, "problems": [], "warnings": []}
    if not (project / "index.html").exists():
        res["problems"].append(f"no composed project at {project}: run engine compose scaffold first")
        return res
    tampered = lock_problems(project)
    if tampered:  # an edited chrome is not rebuilt over: the agent sees what it did, scaffold restores it
        res["problems"] += [f"lint locked: {x[len('lock: '):]}" for x in tampered]
        return res
    if sources is None:
        sources = default_sources(story_path)
    try:
        built = built or build(project, story, engine, music, tone, theme, fmt)
    except ComposeError as e:
        res["problems"].append(f"build: {e}")
        return res
    t, fx = built["timing"], built["facts"]
    res.update(duration=t["duration"], beats=len(t["beats"]), gaps=t["gaps"], chapters=len(t["chapters"]),
               facts=len(fx), slots=len(built["slots"]))
    res["problems"] += [f"story: {x}" for x in eng.check_story(story, sources)] + eng._kaeasy_required()
    res["problems"] += built["problems"]
    res["problems"] += lint(project, b)
    res["novelty"] = variety.assess_composed(b["name"], story["id"], *film_style(project, built["props"].get("music")))
    res["warnings"] += [w for w in [res["novelty"]["warning"]] if w] + missing_notes(project, NOTES)
    res["news_rules"] = bool(sources) or programs.name_of(story) != programs.DEFAULT
    if not sources and programs.of(story)["rules"] in ("news", "claims", "law"):
        res["warnings"].append("no --sources: the numbers, quotes and names on screen were not compared with the "
                               "articles (give <story>.sources.json)")
    if t["gaps"]["over_3s"]:
        res["warnings"].append(f"motion: more than 3 s without a new beat before {', '.join(t['gaps']['over_3s'])}")
    try:
        pr = run_probe(project, t, built["brand"], shots)  # its theme's colors
    except ComposeError as e:
        res["problems"].append(str(e))
        return res
    res["problems"] += pr["problems"]
    res["warnings"] += pr["warnings"]
    notes = []
    shown = screen_texts(pr["reports"], fx, notes)
    res["warnings"] += list(dict.fromkeys(notes))
    res["problems"] += text_problems(story, shown, sources)
    from tt_shorts import ka_check
    res["warnings"] += [f"screen: {w}" for w in ka_check.warnings({"scenes": [{"type": "hook", "lines": shown}]})]
    res["probe"] = {k: pr[k] for k in ("frames", "texts", "blocked", "fonts", "cuts")}
    res["shown"] = shown
    if hf:
        p, w, summary = hf_check(project)
        res["problems"] += p
        res["warnings"] += w
        res["hyperframes"] = summary
    res["problems"] = list(dict.fromkeys(res["problems"]))
    res["seconds"] = round(time.time() - t0, 1)
    return res


# a film that would fetch, hide its text or lose its chrome is never rendered
HARD = ("lint net", "lint canvas", "lint css-content", "lint locked", "lint host", "build:", "no composed project",
        "probe net", "probe generated", "probe failed")


def _mix(work, p, raw, out, t, setting="off"):
    """props.mix_audio on the HyperFrames picture: the voice, the music bed and the film's own sound effects
    (props "sfx": sfx_cues from its wipes and beats, in place of Lane A's scene timeline)."""
    from tt_shorts import props
    p = {**p, "sfx": sfx_cues(t, setting)}
    props.mix_audio(work, p, raw, out)
    return p["sfx"]


def render(story_path, fmt, brand=None, project=None, engine="gemini", out_path=None, sources=None, hf=True,
           template=None):
    """Check, then render a composed film: `hyperframes render` with RENDER's pinned settings, the ffmpeg mix (voice +
    music [+ sound effects]), QA. -> the same result JSON as engine render, plus "check", "project", "film_engine"."""
    from tt_shorts import engine as eng, variety
    story = _story(story_path, brand)
    b = packs.of(story)
    project = pathlib.Path(project or project_dir(story, b["name"])).resolve()
    if not (project / "index.html").exists() or template:
        scaffold(story_path, b["name"], project, template=template, engine=engine, music=fmt["music"], fmt=fmt,
                 force=bool(template))
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    tampered = lock_problems(project)
    built = None if tampered else build(project, story, engine, fmt["music"], tone, fmt.get("theme", "default"), fmt)
    c = check(story_path, b["name"], project, engine, sources, hf, music=fmt["music"], tone=tone, built=built)
    hard = [x for x in c["problems"] if x.startswith(HARD)]
    base = {"film_engine": "hyperframes", "project": str(project), "brand": b["name"], "format": fmt["name"],
            "story": str(pathlib.Path(story_path).resolve()), "check": {k: c.get(k) for k in (
                "problems", "warnings", "probe", "hyperframes", "seconds", "shown")}}
    if hard or built is None:
        return {**base, "problems": hard or c["problems"], "rendered": False}
    t, p, work = built["timing"], built["props"], built["work"]
    target = pathlib.Path(out_path) if out_path else store.render_path(b["name"], story["id"], fmt["name"],
                                                                       "composed", fmt["captions"])
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (pathlib.Path(work) / "composed.mp4").resolve()
    t0 = time.time()
    if os.environ.get("SHORTS_SEGMENTS", "1") != "0":
        from tt_shorts import segments
        ok, err, _ = segments.render_hyperframes(project, p, t, raw, target)
        if not ok:
            return {**base, "rendered": False, "problems": [err]}
    else:
        r = hyperframes(["render", str(project), "--output", str(raw), "--quality", RENDER["quality"], "--workers",
                         RENDER["workers"], "--fps", RENDER["fps"],
                         "--browser-gpu" if RENDER["browser_gpu"] else "--no-browser-gpu", "--strict", "--quiet"],
                        timeout=3600)
        if r.returncode != 0 or not raw.exists():
            return {**base, "rendered": False, "problems": [f"hyperframes render failed ({r.returncode}): "
                                                            f"{(r.stderr or r.stdout)[-600:]}"]}
    render_s = round(time.time() - t0, 1)
    cues = _mix(work, p, raw, target, t, fmt.get("sfx", "off"))
    secs = p["durationInFrames"] / FPS
    kind, n, why = review_for(story, fmt)
    result = {**base, "file": str(target.resolve()), "seconds": round(secs, 1), "look": "composed",
              "style": {"template": template_of(project)}, "transition": "composed", "outro": "card",
              "captions": fmt["captions"], "voice": fmt["voice"], "engine": engine, "music": p["music"],
              "scenes": [x["id"] for x in t["beats"]], "voice_qa": p.get("voiceQa", []),
              "kaeasy": kaeasy.version(),
              "probe": {"problems": [x for x in c["problems"] if x.startswith("probe")], **(c.get("probe") or {})},
              "motion": {"holds": [], "warnings": [w for w in c["warnings"] if w.startswith("motion")]},
              "novelty": c.get("novelty"), "warnings": c["warnings"] + missing_notes(project, (REVIEW_NOTE,)),
              "render_seconds": render_s,
              "render_settings": {**RENDER, "hyperframes": HF_VERSION, "chrome": CHROME_VERSION},
              "review": {"policy": kind, "n": n, "from": why}, "sfx": cues, "rendered": True}
    problems = list(c["problems"])
    if not fmt["min_seconds"] <= secs <= fmt["max_seconds"]:
        problems.append(f"length {secs:.1f}s is outside the format's {fmt['min_seconds']}-{fmt['max_seconds']}s")
    result["problems"] = problems
    side = store.props_path(target)
    side.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    result["props"] = str(side.resolve())
    target.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    q = eng.qa_file(target, fmt)
    result["qa"] = q
    target.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    style, kinds = film_style(project, p["music"])
    variety.record(b["name"], story["id"], variety.COMPOSED, style, kinds, c.get("novelty"))
    shutil.rmtree(work, ignore_errors=True)
    store.log("rendered", file=result["file"], engine="hyperframes", seconds=result["seconds"], problems=problems)
    return result


# ---------------------------------------------------------------- look: the film as a viewer gets it


def _report_of(r, what):
    """A HyperFrames call's JSON -> (report, problem). Its progress lines come before the JSON."""
    try:
        if r.returncode != 0:
            raise ValueError
        return json.loads(r.stdout[r.stdout.index("{"):]), None
    except ValueError:
        return None, f"hyperframes {what}: no report ({(r.stderr or r.stdout)[-300:]})"


def motion_of(timeline):
    """`hyperframes keyframes --json` -> what the agent's motion is made of (the locked chrome and captions aside): its
    tweens, by file, and each ease's share, most used first. One curve everywhere reads as generated."""
    comps = [c for c in timeline.get("compositions") or [] if (c.get("source") or c.get("composition")) not in LOCKED]
    tweens = [x for c in comps for x in c.get("tweens") or []]
    eases = collections.Counter(str(x.get("ease") or "default") for x in tweens)
    return {"tweens": len(tweens), "by_file": {c.get("source") or c.get("composition"): len(c.get("tweens") or [])
                                               for c in comps},
            "eases": {k: round(n / len(tweens), 2) for k, n in eases.most_common(6)}}


def sheets_of(snapshot):
    """`hyperframes snapshot --review --json` -> {"beats", "seams", "phone"}: the sheet of the scenes and beats, the
    strip across each cut, the beat frames at phone width."""
    names = [pathlib.Path(x) for x in snapshot.get("contactSheets") or []]
    one = lambda name: next((str(x) for x in names if x.name == name), None)  # noqa: E731
    return {"beats": one("review-beats.jpg"), "phone": one("review-phone.jpg"),
            "seams": [str(x) for x in names if x.name.startswith("review-seam-")]}


def look(story_path, brand=None, project=None, engine="silent", video=None, tone=None, music="off", theme="default",
         fmt=None):
    """See a composed film before paying for it, as a first-time viewer gets it: the sheets of `hyperframes snapshot
    --review`, the timeline of `keyframes --json` and, with a rendered file (`video`, else this story's render of
    today), the sound of `audio --json`. Free: no voice, no render, nothing leaves the machine. The project is rebuilt
    first, like check; everything is saved in LOOK_DIR. -> {"sheets", "scenes", "timeline", "motion", "audio",
    "problems", "warnings", "next"}. The sheets are for looking at: a person's or a sub-agent's eye, never scored."""
    story = _story(story_path, brand)
    b = packs.of(story)
    project = pathlib.Path(project or project_dir(story, b["name"])).resolve()
    res = {"project": str(project), "story": str(pathlib.Path(story_path).resolve()), "brand": b["name"],
           "film_engine": "hyperframes", "problems": [], "warnings": []}
    if not (project / "index.html").exists():
        res["problems"].append(f"no composed project at {project}: run engine compose scaffold first")
        return res
    tampered = lock_problems(project)
    if tampered:
        res["problems"] += [f"lint locked: {x[len('lock: '):]}" for x in tampered]
        return res
    try:
        built = build(project, story, engine, music, tone, theme, fmt)
    except ComposeError as e:
        res["problems"].append(f"build: {e}")
        return res
    res["duration"] = built["timing"]["duration"]
    shutil.rmtree(built["work"], ignore_errors=True)
    where = project / LOOK_DIR
    where.mkdir(parents=True, exist_ok=True)
    shot, why = _report_of(hyperframes(["snapshot", str(project), "--review", "--json", "--no-browser-gpu", "--output",
                                        str(where)], timeout=900), "snapshot")
    if why:
        res["problems"].append(why)
        return res
    res["sheets"] = sheets_of(shot)
    res["scenes"] = [x for x in (shot.get("review") or {}).get("scenes", []) if x.get("id") not in ("chrome", "captions")]
    timeline, why = _report_of(hyperframes(["keyframes", str(project), "--json"], timeout=300), "keyframes")
    if why:
        res["problems"].append(why)
    else:
        (where / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")
        res["timeline"] = str(where / "timeline.json")
        res["motion"] = motion_of(timeline)
    if video is None and fmt:
        video = store.render_path(b["name"], story["id"], fmt["name"], "composed", fmt["captions"])
    res["audio"] = None
    if video and pathlib.Path(video).exists():
        sound, why = _report_of(hyperframes(["audio", str(pathlib.Path(video).resolve()), "--json", "--quality",
                                             AUDIO_QUALITY], timeout=300), "audio")
        if why:
            res["warnings"].append(why)
        else:
            (where / "audio.json").write_text(json.dumps(sound, ensure_ascii=False, indent=1), encoding="utf-8")
            res["audio"] = str(where / "audio.json")
    else:
        res["warnings"].append("no rendered file, so the sound was not measured: engine compose render --engine silent, "
                               "then look --video <file>")
    res["next"] = (f"open every sheet; a fresh eye gets only SPEC.md and the sheets, and its notes go in {REVIEW_NOTE} "
                   "(veasy:compose); then render")
    return res


# ---------------------------------------------------------------- templates: an approved film, its facts as slots


def template_of(project):
    path = pathlib.Path(project) / "slots.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("_template")
    return None


def templates():
    """{id: manifest} of templates/<id>/manifest.json."""
    out = {}
    for m in sorted(TEMPLATES.glob("*/manifest.json")):
        out[m.parent.name] = json.loads(m.read_text(encoding="utf-8"))
    return out


def pick_template(brand, story_id):
    """The least used template among the brand's last films (variety's rule), or None when there are none."""
    from tt_shorts import variety
    ids = sorted(templates())
    if not ids:
        return None
    used = [r.get("template") for r in variety.history(brand)]
    return variety._least_used(ids, used, story_id, "template")


def promote(project, tid, label=None, about=None, force=False):
    """An approved composed film -> templates/<tid>/: its scenes with every text a slot (a story fact it showed
    becomes a slot of that kind, a word it typed a slot of words), its beat sheet without anchors, its index.html,
    and manifest.json (the slots, the kind of fact each needs, an example, the beats each scene lands on)."""
    project = pathlib.Path(project).resolve()
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,40}", tid or ""):
        raise ComposeError("a template id is lowercase letters, digits and hyphens (e.g. number-card)")
    dest = TEMPLATES / tid
    if dest.exists() and not force:
        raise ComposeError(f"template {tid} exists: pass --force to replace it")
    bad = [x for x in lint(project) if x.startswith(HARD)]
    if bad:
        raise ComposeError("only a film that passes the lint is promoted: " + "; ".join(bad[:5]))
    fx = json.loads((project / "facts.json").read_text(encoding="utf-8"))["facts"]
    story = json.loads((project / "story.json").read_text(encoding="utf-8"))
    sheet = json.loads((project / "beats.json").read_text(encoding="utf-8"))
    code = {k for k, v in fx.items() if v["kind"] == CODE_KIND}
    shutil.rmtree(dest, ignore_errors=True)
    (dest / "compositions").mkdir(parents=True)
    slots = {}
    for f in agent_files(project):
        if f == "slots.json":
            continue
        text = (project / f).read_text(encoding="utf-8") if f.endswith((".html", ".json", ".svg")) else None
        if f.startswith("compositions/") and text is not None:
            text = _slotify(text, pathlib.Path(f).stem, fx, code, slots)
        if f == "index.html":
            text = re.sub(r"\sdata-composition-variables\s*=\s*'[^']*'", "", text)
        if f == "beats.json":
            sheet_t = {**sheet, "story": None, "keywords": [],
                       "chapters": [{"title": "", "at": None, "example": c.get("title")} for c in sheet["chapters"]],
                       "end": {"at": None}, "beats": [{k: v for k, v in b.items() if k != "at"} | {"at": None}
                                                      for b in sheet["beats"]]}
            text = json.dumps(sheet_t, ensure_ascii=False, indent=1)
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        if text is None:
            shutil.copy(project / f, dest / f)
        else:
            (dest / f).write_text(text, encoding="utf-8")
    manifest = {"id": tid, "label": label or tid, "about": about or "", "engine": "hyperframes",
                "chrome": CHROME_VERSION, "from": {"story": story.get("id"), "brand": story.get("brand"),
                                                   "program": story.get("program", programs.DEFAULT)},
                "chapters": len(sheet["chapters"]), "beats": [{"id": b["id"], "show": b.get("show", "")}
                                                              for b in sheet["beats"]],
                "icons": sheet.get("icons", []), "slots": slots,
                "use": "engine compose scaffold <story> --template " + tid + ": fill slots.json (a fact slot: "
                       "\"=<fact id>\" from facts.json; a words slot: the words) and beats.json's anchors"}
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest, manifest


def _slotify(text, scene, fx, code, slots):
    """A scene file with its story facts renamed to slots (data-var-text="num-1" -> "slot-num-1", and in its
    scripts) and every typed text in a data-probe region wrapped as a words slot."""
    def rename(fid):
        if fid in code or fid.startswith(("beat-", "host-", "chapter-", "film-")) or fid not in fx:
            return fid
        sid = f"slot-{scene}-{fid}"
        slots.setdefault(sid, {"kind": fx[fid]["kind"] if fx[fid]["kind"] != "fact" else "words",
                               "example": fx[fid]["value"], "max": max(4, round(len(fx[fid]["value"]) * 1.3))})
        return sid
    text = re.sub(r"data-var-text\s*=\s*\"([^\"]+)\"", lambda m: f'data-var-text="{rename(m.group(1))}"', text)
    text = re.sub(r"(VEASY\.fact\(\s*)\"([a-z0-9-]+)\"", lambda m: f'{m.group(1)}"{rename(m.group(2))}"', text)
    out, k = [], 0
    for kind, tok, stack in _tags(text):
        if kind == "text" and tok.strip() and any(_attr(s, "data-probe") is not None for s in stack) \
                and not any(_attr(s, "data-var-text") is not None for s in stack):
            k += 1
            sid = f"slot-{scene}-w{k}"
            words = " ".join(tok.split())
            slots[sid] = {"kind": "words", "example": words, "max": max(4, round(len(words) * 1.3))}
            lead, trail = tok[:len(tok) - len(tok.lstrip())], tok[len(tok.rstrip()):]
            out.append(f'{lead}<span data-var-text="{sid}">{words}</span>{trail}')
        else:
            out.append(tok)
    return "".join(out)


def use_template(tid, project):
    """Start a project from templates/<tid>/: its files, and slots.json with every slot to fill."""
    src = TEMPLATES / tid
    if not (src / "manifest.json").exists():
        raise ComposeError(f"unknown template {tid!r}; known: {', '.join(templates()) or 'none'}")
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("chrome") != CHROME_VERSION:
        raise ComposeError(f"template {tid} was made for locked chrome v{manifest.get('chrome')}; Veasy's is "
                           f"v{CHROME_VERSION}: promote it again from a film scaffolded now")
    _copy_agent(src, project)
    slots = {"_template": tid, "_about": "Fill every value: a fact slot with \"=<fact id>\" (facts.json: the story's "
                                         "facts of that kind), a words slot with the words (checked like any text)."}
    slots.update({k: {**v, "value": None} for k, v in manifest["slots"].items()})
    (project / "slots.json").write_text(json.dumps(slots, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest
