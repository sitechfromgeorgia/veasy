"""Directors: code gives each video a creative direction before the writer runs (owner, 2026-11-02: "we give the AI
brushes, and separate agents each choose a different direction").

Models asked to "be creative" converge (Artificial Hivemind, NeurIPS 2025), so the direction is assigned by code.
A director changes what kind of film a story becomes: which scene types carry it (with weights), how many scenes,
the hook layouts, motifs, entrances and cuts variety.pick() may choose from, the motion personality (spring
numbers, entrance and stagger frames) and the "current", the one direction entrances and cuts move in. A director
never touches the facts, the colors, the fonts, the safe zone or the news rules (it may prefer some of a pack's
themes by name, never its colors): every story goes through the
same checks.

Directors are data, `directors/<id>.json`, validated here:
  id, label (Georgian), about, device, form, brief (6-10 English lines for the writer)
  scenes      {type: weight}; hook and end are always allowed; a type must be in engine.SCENES, or in
              PLANNED (brushes being built) and then it is offered to the writer only once it exists, or a
              device of DEVICES ("marker": the writer marks the words that matter with "em", marks.py)
  count       [lo, hi] scenes, inside the writer's 3-6
  pacing      a line for the writer
  hooks, motifs, enters, transitions    subsets of variety's options
  current     left | right | up        (left: slides come from the right moving left; push goes the same way)
  motion      {damping, stiffness, enter_frames, stagger_frames}   (Remotion spring, mass 0.8; today's: 20, 170, 10, 5)
  eligible    [{fact: min, ...}, ...]  any alternative whose every minimum holds; "families": [...] narrows it
  never       [{...}, ...]             any condition that fully holds rules the director out
  gates       story checks after writing (news integrity): "two_sides" (when the articles quote 2+ speakers,
              the story's quotes show 2 of them)
  holds       scene types the director means to hold on (optional): motion_rules lets them stay still up to
              HOLD_MAX s instead of STILL_MAX (the data director's number: the owner's call, 2026-11-03)
  themes      the pack themes it prefers, by name (optional; "light", "dark"...): with `theme: auto` variety picks
              among the pack's allowed themes that are in this list (all of them when the pack has none of these).
              Names only: the colors stay the pack's
  engine      remotion | hyperframes (optional): the film engine; a director's wins over the program's, the
              format's and the pack's (compose.engine_for)

Facts (facts()) are what code extracts from the articles before writing: numbers (news_check.numbers), quantities
(numbers that are not part of a date or time), percents, dates, times, places (the gazetteer, geo.locate), quotes
(„…“ of 4+ words), speakers (named next to a quote), icons (icons.find), deaths, family, facts (quantities +
dates + places + quotes).
"""
import functools
import json
import pathlib
import re

from tt_shorts import geo, icons, news_check

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "directors"
CURRENTS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1)}
# brushes being built in parallel: a director may name them (optional); the writer sees them once engine.SCENES has them
# (rail, share and compare exist since the brush kit, brushes/)
PLANNED = ()
# devices a director may weigh that are not scene types: "marker" asks the writer for voice-synced marks ("em", marks.py)
DEVICES = ("marker",)
ALWAYS = ("hook", "end")
FACTS = ("numbers", "quantities", "percents", "dates", "times", "places", "regions", "quotes", "speakers", "icons",
         "facts")
FLAGS = ("deaths",)
GATES = ("two_sides",)
KEYS = ("id", "label", "about", "device", "form", "brief", "scenes", "count", "pacing", "hooks", "motifs", "enters",
        "transitions", "current", "motion", "eligible", "never", "gates", "holds", "themes", "engine")
OPTIONAL = ("gates", "holds", "themes", "engine")
MOTION = {"damping": (8, 30), "stiffness": (80, 300), "enter_frames": (6, 16), "stagger_frames": (3, 6)}
DEFAULT_MOTION = {"damping": 20, "stiffness": 170, "enter_frames": 10, "stagger_frames": 5}  # ui.tsx today


class DirectorError(ValueError):
    pass


def _scene_types():
    from tt_shorts import engine
    return set(engine.SCENES)


def _variety():
    from tt_shorts import formats, variety
    return {"hooks": variety.OPTIONS["hook"], "motifs": variety.OPTIONS["motif"], "enters": variety.OPTIONS["enter"],
            "transitions": tuple(t for t in formats.TRANSITIONS if t != "auto")}


def _condition(name, where, cond):
    from tt_shorts import brand
    if not isinstance(cond, dict) or not cond:
        raise DirectorError(f"director {name!r}: {where}: each condition is a non-empty object")
    for k, v in cond.items():
        if k == "families":
            if not isinstance(v, list) or not set(v) <= set(brand.FAMILIES):
                raise DirectorError(f"director {name!r}: {where}: families must be a list of {', '.join(brand.FAMILIES)}")
        elif k in FLAGS:
            if not isinstance(v, bool):
                raise DirectorError(f"director {name!r}: {where}: {k} is true or false")
        elif k in FACTS:
            ok = isinstance(v, int) and not isinstance(v, bool) and v >= 0
            ok = ok or (isinstance(v, dict) and set(v) == {"max"} and isinstance(v["max"], int))
            if not ok:
                raise DirectorError(f"director {name!r}: {where}: {k} is a minimum count or {{\"max\": n}}")
        else:
            raise DirectorError(f"director {name!r}: {where}: unknown fact {k!r} (facts: {', '.join(FACTS + FLAGS)}, "
                                "families)")


def validate(name, d):
    """Raise DirectorError when a director names something the engine can't do."""
    def need(cond, msg):
        if not cond:
            raise DirectorError(f"director {name!r}: {msg}")
    need(isinstance(d, dict), "not an object")
    missing = [k for k in KEYS if k not in d and k not in OPTIONAL]
    need(not missing, f"missing {missing}")
    unknown = sorted(set(d) - set(KEYS))
    need(not unknown, f"unknown keys {unknown}")
    need(d["id"] == name, f"id {d['id']!r} must be its file name")
    need(isinstance(d["label"], str) and re.search(r"[ა-ჰ]", d["label"]), "label is Georgian (it may be shown)")
    need(isinstance(d["brief"], list) and 6 <= len(d["brief"]) <= 10 and all(isinstance(x, str) and x for x in d["brief"]),
         "brief is 6-10 lines for the writer")
    known = _scene_types()
    scenes = d["scenes"]
    need(isinstance(scenes, dict) and scenes, "scenes is {type: weight}")
    for t, w in scenes.items():
        need(t in known or t in PLANNED or t in DEVICES,
             f"scene type {t!r} is neither a scene (engine.SCENES), a device ({', '.join(DEVICES)}) nor planned "
             f"({', '.join(PLANNED) or 'none'})")
        need(isinstance(w, (int, float)) and not isinstance(w, bool) and w > 0, f"scene {t!r}: weight above 0")
    need(len([t for t in scenes if t in known and t not in ALWAYS]) >= 2, "at least 2 scene types that exist today")
    lo, hi = (d["count"] + [0, 0])[:2] if isinstance(d["count"], list) else (0, 0)
    need(isinstance(d["count"], list) and len(d["count"]) == 2 and 3 <= lo <= hi <= 6, "count is [lo, hi] inside 3-6")
    for key, allowed in _variety().items():
        v = d[key]
        need(isinstance(v, list) and v and set(v) <= set(allowed), f"{key} is a non-empty list of {', '.join(allowed)}")
    need(d["current"] in CURRENTS, f"current is one of {', '.join(CURRENTS)}")
    need(isinstance(d["motion"], dict) and set(d["motion"]) == set(MOTION), f"motion has exactly {', '.join(MOTION)}")
    for k, (a, b) in MOTION.items():
        v = d["motion"][k]
        need(isinstance(v, (int, float)) and not isinstance(v, bool) and a <= v <= b, f"motion {k} is {a}-{b}")
    need(isinstance(d["eligible"], list) and d["eligible"], "eligible is a list of alternatives")
    for c in d["eligible"]:
        _condition(name, "eligible", c)
    need(isinstance(d["never"], list), "never is a list of conditions")
    for c in d["never"]:
        _condition(name, "never", c)
    need(set(d.get("gates", [])) <= set(GATES), f"gates are some of {', '.join(GATES)}")
    holds = d.get("holds", [])
    need(isinstance(holds, list) and set(holds) <= set(scenes) - set(DEVICES) - set(ALWAYS),
         "holds is a list of the director's own scene types")
    themes = d.get("themes", [])
    need(isinstance(themes, list) and all(isinstance(t, str) and re.match(r"^[a-z][a-z0-9-]*$", t) for t in themes),
         "themes is a list of theme names (brand.json themes: lowercase, e.g. light)")
    if "engine" in d:
        from tt_shorts import formats
        formats.engine_value(d["engine"], f"director {name!r}", DirectorError)
    return {**d, "gates": list(d.get("gates", [])), "holds": list(holds), "themes": list(themes)}


@functools.lru_cache(maxsize=4)
def _load(path_str):
    out = {}
    for path in sorted(pathlib.Path(path_str).glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise DirectorError(f"director {path.stem!r}: not JSON ({e})") from e
        out[path.stem] = validate(path.stem, raw)
    return out


def load_all():
    return dict(_load(str(DIR)))


def names():
    return sorted(load_all())


def get(name):
    every = load_all()
    if name not in every:
        raise DirectorError(f"unknown director {name!r}; known: {', '.join(sorted(every))}")
    return every[name]


def scene_types(d, program_scenes="all"):
    """The types the writer may use under this director: its own that exist today (a planned brush appears once
    engine.SCENES has it), inside the program's, plus hook and end; ordered by weight."""
    known = _scene_types()
    ok = lambda t: t in known and (program_scenes == "all" or t in program_scenes)  # noqa: E731
    own = sorted((t for t in d["scenes"] if ok(t) and t not in ALWAYS), key=lambda t: -d["scenes"][t])
    from tt_shorts import writer
    if not writer.drawing():
        own = [t for t in own if t != "draw"]
    return ["hook", *own, "end"]


def planned(d):
    """The director's brushes that don't exist yet."""
    return [t for t in d["scenes"] if t not in _scene_types() and t not in DEVICES]


# ---------------------------------------------------------------- facts code extracts before writing

QUOTE = re.compile(r"„([^“”„]{8,400})[“”]")
TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
MONTHS = ("იანვ", "თებერვ", "მარტ", "აპრილ", "მაის", "ივნის", "ივლის", "აგვისტ", "სექტემბ", "ოქტომბ", "ნოემბ", "დეკემბ")
DATE = re.compile(r"(?<!\d)(\d{1,2})\s+(" + "|".join(MONTHS) + r")[ა-ჰ]*")
YEAR = re.compile(r"(?<!\d)(19\d\d|20\d\d)(?!\d)")
PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|პროცენტ)")
SPEECH = ("განაცხად", "თქვა", "აღნიშნ", "დასძინა", "განმარტ", "ამბობს", "აცხადებს", "წერს", "დაწერა", "მიიჩნევს",
          "ჩათვალა", "უთხრა", "ამბობენ", "აცხადებენ")
SAYS = re.compile(r"([ა-ჰ]{3,})(?:-?ის|ს)\s+(?:თქმით|განცხადებით|სიტყვებით|შეფასებით)")


def _speaker(before, after):
    """The speaker named next to a quote: an ergative word (-მა/-მ) beside a speech verb, or "X-ის თქმით"."""
    for words, forward in ((re.findall(r"[ა-ჰ]+", after)[:6], True), (re.findall(r"[ა-ჰ]+", before)[-6:], False)):
        for i, w in enumerate(words):
            if any(w.startswith(v) for v in SPEECH):
                side = words[i + 1:i + 4] if forward else list(reversed(words[max(0, i - 4):i]))
                for x in side:
                    if x.endswith(("მა", "მ")) and len(x) > 3 and x not in ("მან", "ამან", "იმან"):
                        return re.sub(r"(მა|მ)$", "", x)[:6]
    m = SAYS.search(before[-60:])
    return m.group(1)[:6] if m else None


def facts(articles, category="", brand=None, cluster=None):
    """What a director's eligibility reads: counts (and the found values, for the writer's fact list)."""
    from tt_shorts import meta
    text = " ".join(a for a in articles if isinstance(a, str))
    times = sorted({f"{int(h):02d}:{m}" for h, m in TIME.findall(text)})
    dates = sorted({f"{int(d)} {m}" for d, m in DATE.findall(text)} | set(YEAR.findall(text)))
    in_dates = {x for pat in (TIME, DATE, YEAR) for m in pat.finditer(text) for x in re.findall(r"\d+", m.group(0))}
    nums = news_check.numbers(text)
    quantities = sorted(n for n in nums - in_dates if n != "0")
    quotes, speakers = [], []
    for m in QUOTE.finditer(text):
        q = m.group(1).strip()
        if len(q.split()) < 4:  # „თბილისი ენერჯი“: a name in quotes, not a quote
            continue
        who = _speaker(text[max(0, m.start() - 80):m.start()], text[m.end():m.end() + 80])
        quotes.append({"text": q, "by": who})
        if who and who not in speakers:
            speakers.append(who)
    places, regions = [], []
    for a in articles:
        loc = geo.locate(a) if isinstance(a, str) else None
        for p in (loc or {}).get("places", []):
            if p["name"] not in places:
                places.append(p["name"])
        for r in (loc or {}).get("regions", []):
            if r not in regions:
                regions.append(r)
    found = {"numbers": sorted(nums, key=lambda x: (len(x), x)), "quantities": quantities,
             "percents": PERCENT.findall(text), "dates": dates, "times": times, "places": places,
             "regions": regions, "quotes": quotes, "speakers": speakers, "icons": icons.find(text)}
    counts = {k: len(v) for k, v in found.items()}
    counts["facts"] = counts["quantities"] + counts["dates"] + counts["places"] + counts["quotes"]
    family = meta.family(category, brand) if brand is not None else meta.family(category)
    return {**counts, "deaths": bool(news_check.deaths(text)), "family": family, "found": found}


def _holds(cond, f):
    for k, v in cond.items():
        if k == "families":
            if f.get("family") not in v:
                return False
        elif k in FLAGS:
            if bool(f.get(k)) != v:
                return False
        elif isinstance(v, dict):
            if f.get(k, 0) > v["max"]:
                return False
        elif f.get(k, 0) < v:
            return False
    return True


def eligible(f, program_scenes="all"):
    """The directors whose eligibility holds for these facts and that no never-gate rules out, by id."""
    out = []
    for name, d in sorted(load_all().items()):
        if any(_holds(c, f) for c in d["never"]) or not any(_holds(c, f) for c in d["eligible"]):
            continue
        if len(scene_types(d, program_scenes)) < 4:  # hook, end and at least 2 of its own in this program
            continue
        out.append(name)
    return out


# ---------------------------------------------------------------- the writer's part


def brief_block(d, f=None, program_scenes="all"):
    """The direction the writer follows: the director's brief, its scene types and count, and the facts code found."""
    types = scene_types(d, program_scenes)
    lines = [f"Direction for this video (code chose it; follow it): {d['id']} „{d['label']}“: {d['device']} x {d['form']}."]
    lines += [f"- {x}" for x in d["brief"]]
    lines.append(f"- Use only these scene types (most wanted first): {', '.join(types)}; "
                 f"{d['count'][0]}-{d['count'][1]} scenes. Pacing: {d['pacing']}")
    if "marker" in d["scenes"]:
        lines.append('- Mark the words that matter with "em" on 1-3 scenes: the marker draws on them as the voice '
                     "says them.")
    if f:
        found = f.get("found") or {}
        parts = [f"{k}: {', '.join(found[k])}" for k in ("quantities", "dates", "times", "places", "icons", "percents")
                 if found.get(k)]
        parts += [f"quote: „{q['text'][:120]}“" + (f" ({q['by']}...)" if q.get("by") else "")
                  for q in (found.get("quotes") or [])[:4]]
        if parts:
            lines.append("- Facts code found in the articles (build the scenes from these, nothing else): " + "; ".join(parts))
        if "two_sides" in d["gates"] and f.get("speakers", 0) >= 2:
            lines.append("- The articles quote more than one side: show at least two speakers, one quote scene each.")
    return "\n".join(lines) + "\n\n"


def story_problems(story, f=None):
    """A directed story's hard gates (news integrity; they go back to the writer), given the facts."""
    name = story.get("director")
    if not name or not f:
        return []
    try:
        d = get(name)
    except DirectorError:
        return []
    out = []
    if "two_sides" in d["gates"] and f.get("speakers", 0) >= 2:
        by = {str(s.get("by") or "").strip() for s in story.get("scenes") or [] if s.get("type") == "quote"}
        if len(by - {""}) < 2:
            out.append(f"director {name}: the articles quote {f['speakers']} speakers; show at least 2 of them "
                       "(one quote scene each, with by and via)")
    return out


def warnings(story, program_scenes="all"):
    """What a directed story does differently from its director (not a failure: the facts decide)."""
    name = story.get("director")
    if not name:
        return []
    try:
        d = get(name)
    except DirectorError:
        return []
    allowed = set(scene_types(d, program_scenes)) | set(d["scenes"])
    scenes = story.get("scenes") or []
    out = [f"director {name}: scene {i} ({s.get('type')}) is not one of its types" for i, s in enumerate(scenes)
           if s.get("type") not in allowed]
    if not d["count"][0] <= len(scenes) <= d["count"][1]:
        out.append(f"director {name}: {len(scenes)} scenes, it wants {d['count'][0]}-{d['count'][1]}")
    return out


def structure_problems(story):
    """engine.structure_problems: a director in a story must be one of the directors."""
    if "director" not in story:
        return []
    name = story["director"]
    if not isinstance(name, str) or name not in load_all():
        return [f"story: unknown director {name!r} (known: {', '.join(names())}); the director is set by code, "
                "never by the writer"]
    return []


# ---------------------------------------------------------------- the render's part


def flow(current):
    """The unit vector entrances and cuts move along (remotion/src/ui.tsx and NewsShort.tsx read it)."""
    return list(CURRENTS[current])


def style(d):
    """What props.style carries of a director: its id, motion numbers, current and that current's vector."""
    return {"director": d["id"], "motion": dict(d["motion"]), "current": d["current"], "flow": flow(d["current"])}


def options():
    """What `engine options` shows an agent."""
    return {"about": "a creative direction code assigns before writing (variety.direct: the least used eligible one "
                     "for the brand); it picks the scene types, the count, the hook layouts, motifs, entrances, cuts, "
                     "the motion and the current. Never the facts, the palette or the rules. render --director <id> "
                     "or queue add --director overrides it",
            "planned": list(PLANNED), "devices": list(DEVICES), "currents": {k: list(v) for k, v in CURRENTS.items()},
            "directors": {n: {"label": d["label"], "about": d["about"], "form": f"{d['device']} x {d['form']}",
                              "scenes": d["scenes"], "count": d["count"], "current": d["current"],
                              "motion": d["motion"], "hooks": d["hooks"], "motifs": d["motifs"], "enters": d["enters"],
                              "transitions": d["transitions"], "eligible": d["eligible"], "never": d["never"],
                              "gates": d["gates"], "themes": d["themes"], "planned": planned(d)}
                          for n, d in sorted(load_all().items())}}
