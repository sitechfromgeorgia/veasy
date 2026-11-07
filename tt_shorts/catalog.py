"""The brush kit: every scene type the writer may paint with, one JSON file each (brushes/<type>.json).

A brush says what the scene shows, when to use it and when not, what it pairs with, its typed slots (with Georgian
length limits), the families it is never used for, how long it must stay on screen (seconds, narration words), where
a voice-synced mark (`em`) may land and which kinds code picks from, the writer's schema line and rules, and a real
example. Everything the engine used to repeat in seven places is generated from these files:

    engine.SCENES, engine.COUNTS          scenes(), counts()
    speech.MIN_SCENE                      min_scene()
    ka_check.MIN_WORDS, FIELDS            min_words(), text_fields()
    the writer's schema and rules         schema(types=None): only `types` (a director's or a program's menu)
    engine options -> scenes              options()

A brush file (keys in this order; tests/test_catalog.py checks every file):
  type          the file name
  order         its place in the menu (hook 10 ... end 1000); a new type takes a free number between two others
  what          one line: what it shows (engine options "shows")
  use_when, avoid_when    one line each, for the writer and an agent choosing
  pairs_with    scene types that go well before or after it
  slots         {name: spec} in the order the writer sees them, required ones first. spec:
                  {"kind": "text", "max": 24}            a Georgian text of at most 24 characters
                  {"kind": "num", "min": 0, "max": 100}  a number (bounds optional)
                  {"kind": "enum", "values": [...], "deny": {"value": [families]}}
                  {"kind": "list", "count": [2, 4], "of": <spec> | {field: spec}}
                  {"kind": "obj", "of": {field: spec}}
                  {"kind": "icon" | "verb" | "svg" | "area"} checked by icons.py, art.py, geo.py
                "required": true on any spec; a required slot must be filled (engine.structure_problems)
  families_deny the families (brand.FAMILIES) a story of which never uses this type
  min_seconds   on screen at least (speech.scene_frames); min_words: narration words it needs (K9)
  em            {"fields": [...], "kinds": [...]}: the slots a marked phrase may sit in (the component draws the
                mark there: "items" is an item text, "items.name" an item's field) and the mark kinds code picks
                from (marks.py; the writer never picks one); empty: no mark in this scene
  schema        the writer's example line ({"type": ..., "at": "...", ...}); null: the writer gets none
  rules         lines for the writer, shown only when this type is on the menu ("  " starts a continuation)
  example       a real scene, as a story would carry it

Keys every scene may carry beside its slots: type, at (its first narration words), em (marks.py) and show (the
writer's hint for a picture behind the scene: a short English query, "gas pipeline repair", or "screenshot" for the
story's own official page). A hint is all the writer gives: code resolves it (assets.py) into the scene's `media`
and the story's `assets` ledger, both code-owned like date and sources. A type in NO_MEDIA never carries a picture
(the map is the where scene's picture; the end card and a digest's chapter card are the pack's chrome).
This module imports nothing from the engine or the writer (they import it), so it can't make an import cycle.
"""
import functools
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "brushes"
KEYS = ("type", "order", "what", "use_when", "avoid_when", "pairs_with", "slots", "families_deny", "min_seconds",
        "min_words", "em", "schema", "rules", "example")
KINDS = ("text", "num", "enum", "list", "obj", "icon", "verb", "svg", "area")
MARKS = ("underline", "box", "circle", "highlight", "bracket")  # @remotion/rough-notation's, as code picks them
UNIVERSAL = ("type", "at", "em", "show", "art")  # art: vignettes.py
NO_MEDIA = ("where", "end", "chapter", "plate")  # assets.py: these types never carry a picture
NAMED_ONLY = ("state",)  # a program must name these: "all" (news) never means them, its writer never hears of them
MIN_SECONDS_DEFAULT = 2.5
MIN_WORDS_DEFAULT = 6

HEAD = """
Return ONE JSON object and nothing else. Shape:
{
 "category": "politics|world|economy|society|crime|culture|sports|tech|education|region|general",
 "narration": "the spoken text, 70-95 words, sentences of 6-14 words",
 "cta": "short closing call, 4-7 words, no punctuation at the end",
 "say": {"latin-or-brand": "how to say it in Georgian"},
 "motif": "optional: the story's main icon, an icon name or the Georgian word for the thing (გაზი, მეტრო, სკოლა)",
 "scenes": ["""
RULES_HEAD = """Rules that code enforces and will send back to you:
- every number on screen and in the narration must appear in the articles;
- a quote must be verbatim from an article, inside „…“;
- no relative days (დღეს, გუშინ, ხვალ, ზეგ);
- no evaluative words, no „თქვენ“, no em dash or en dash, no „!“, „?“, „…“;
- 3 to 6 scenes; the first is hook; use the scene types that fit the story, do not invent others;
- "at" must be the exact first words of that part of the narration;
- never invent a number, time or date: if the article does not contain it, do not write it;"""
RULE_LIMITS = ("- on-screen texts are short: a kicker at most 24 characters, a headline 40, a hook line 24; each "
               "scene type's limits are code's and a longer text comes back;")
RULE_EM = ('- "em" (optional, at most one per scene, on 1-3 scenes of the video): the 1-4 words that matter most, '
           "copied exactly from that scene's on-screen text (for a stat or a share: its value) and said in that "
           "scene's part of the narration; code marks them on screen as the voice says them;")
RULE_SHOW = ('- "show" (optional, on 2-4 scenes, never the hook of a crime, incident or death story): a picture '
             "behind that scene, as a short English search query of 1-5 plain words for an ordinary thing or place "
             "(\"gas pipeline repair\", \"apartment blocks at night\"); never a person's name, a logo, a brand, text "
             "or the event itself; code finds a licensed photo, labels it illustrative and credits it;")
RULE_ART = ('- "art" (optional, on 1-3 scenes, never for crime, incidents or deaths, never on an end, sources, '
            'where, chapter, draw, sign or plate scene): a line drawing of what that scene\'s part of the narration is '
            'about, an SVG fragment in the draw scene\'s style (below), without labels: code removes every word and '
            'draws it in the room the scene\'s text leaves. Draw the story\'s own things (a cart for food prices, '
            'a valve for gas), a different thing on each scene;')
RULES_TAIL = """- never a sign, a stat icon or a motif for crime, incidents or deaths;
- the last scene must start at least 4 narration words before the end, so it does not flash by."""


class CatalogError(ValueError):
    pass


def _families():
    from tt_shorts import brand  # brand.py imports nothing of the engine
    return brand.FAMILIES


def _spec(where, spec, need):
    need(isinstance(spec, dict) and spec.get("kind") in KINDS, f"{where}: a slot is {{\"kind\": one of {', '.join(KINDS)}}}")
    k = spec["kind"]
    known = {"kind", "required", "max", "min", "values", "deny", "count", "of"}
    need(set(spec) <= known, f"{where}: unknown keys {sorted(set(spec) - known)}")
    if "required" in spec:
        need(spec["required"] is True, f"{where}: required is true or left out")
    if k == "text":
        need(isinstance(spec.get("max"), int) and 2 <= spec["max"] <= 400, f"{where}: a text has a max of 2-400 characters")
    if k == "num":
        for b in ("min", "max"):
            need(b not in spec or isinstance(spec[b], (int, float)), f"{where}: {b} is a number")
    if k == "enum":
        vals = spec.get("values")
        need(isinstance(vals, list) and vals and all(isinstance(v, str) for v in vals), f"{where}: values is a list of names")
        for v, fams in (spec.get("deny") or {}).items():
            need(v in vals and isinstance(fams, list) and set(fams) <= set(_families()),
                 f"{where}: deny maps a value to families ({', '.join(_families())})")
    if k == "list":
        c = spec.get("count")
        need(c is None or (isinstance(c, list) and len(c) == 2 and all(isinstance(x, int) for x in c) and 0 < c[0] <= c[1]),
             f"{where}: count is [lo, hi]")
        of = spec.get("of")
        need(isinstance(of, dict) and of, f"{where}: a list says what it holds (of)")
        if "kind" in of:
            _spec(f"{where}[]", of, need)
        else:
            for n, s in of.items():
                _spec(f"{where}[].{n}", s, need)
    if k == "obj":
        need(isinstance(spec.get("of"), dict) and spec["of"], f"{where}: an obj names its fields (of)")
        for n, s in spec["of"].items():
            _spec(f"{where}.{n}", s, need)


def validate(name, b):
    """Raise CatalogError when a brush names something the engine can't do."""
    def need(cond, msg):
        if not cond:
            raise CatalogError(f"brush {name!r}: {msg}")
    need(isinstance(b, dict), "not an object")
    missing = [k for k in KEYS if k not in b]
    need(not missing, f"missing {missing}")
    need(not set(b) - set(KEYS), f"unknown keys {sorted(set(b) - set(KEYS))}")
    need(b["type"] == name and re.fullmatch(r"[a-z]+", name), "type is its file name (lowercase letters)")
    need(isinstance(b["order"], int) and not isinstance(b["order"], bool) and b["order"] > 0, "order is a positive number")
    for k in ("what", "use_when", "avoid_when"):
        need(isinstance(b[k], str) and b[k].strip(), f"{k} is one line")
    need(isinstance(b["pairs_with"], list) and all(isinstance(t, str) for t in b["pairs_with"]), "pairs_with is a list of types")
    need(isinstance(b["slots"], dict), "slots is {name: spec}")
    for n, spec in b["slots"].items():
        need(n not in UNIVERSAL, f"slot {n!r}: type, at and em belong to every scene")
        _spec(f"slot {n!r}", spec, need)
    order = [bool(s.get("required")) for s in b["slots"].values()]
    need(order == sorted(order, reverse=True), "required slots come first")
    need(isinstance(b["families_deny"], list) and set(b["families_deny"]) <= set(_families()),
         f"families_deny is some of {', '.join(_families())}")
    need(isinstance(b["min_seconds"], (int, float)) and 1.5 <= b["min_seconds"] <= 6, "min_seconds is 1.5-6")
    need(isinstance(b["min_words"], int) and 2 <= b["min_words"] <= 14, "min_words is 2-14")
    em = b["em"]
    need(isinstance(em, dict) and set(em) == {"fields", "kinds"}, "em is {fields, kinds}")
    need(set(em["kinds"]) <= set(MARKS) and (bool(em["kinds"]) == bool(em["fields"])),
         f"em kinds are some of {', '.join(MARKS)}, with fields (both empty: no mark)")
    for f in em["fields"]:
        top = f.split(".")[0]
        need(top in b["slots"], f"em field {f!r} is not a slot")
    line = b["schema"]
    need(line is None or (isinstance(line, dict) and line.get("type") == name and "at" in line and
                          set(line) <= set(b["slots"]) | {"type", "at"}), "schema is the writer's line (its slots) or null")
    need(isinstance(b["rules"], list) and all(isinstance(r, str) and r for r in b["rules"]), "rules is a list of lines")
    ex = b["example"]
    need(isinstance(ex, dict) and ex.get("type") == name and ex.get("at"), "example is a scene of this type with its at")
    need(set(ex) <= set(b["slots"]) | set(UNIVERSAL), f"example: unknown keys {sorted(set(ex) - set(b['slots']) - set(UNIVERSAL))}")
    for n, spec in b["slots"].items():
        need(not spec.get("required") or ex.get(n) not in (None, "", []), f"example: required slot {n!r} is empty")
    bad = slot_problems(ex, {name: b})
    need(not bad, f"example: {'; '.join(bad)}")
    return b


@functools.lru_cache(maxsize=4)
def _load(path_str):
    out = {}
    for path in sorted(pathlib.Path(path_str).glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CatalogError(f"brush {path.stem!r}: not JSON ({e})") from e
        out[path.stem] = validate(path.stem, raw)
    orders = [b["order"] for b in out.values()]
    if len(set(orders)) != len(orders):
        raise CatalogError(f"brushes: two share an order ({sorted(orders)})")
    for t, b in out.items():
        unknown = [p for p in b["pairs_with"] if p not in out]
        if unknown:
            raise CatalogError(f"brush {t!r}: pairs_with names unknown types {unknown}")
    return dict(sorted(out.items(), key=lambda kv: kv[1]["order"]))


def load_all():
    """{type: brush} in menu order."""
    return dict(_load(str(DIR)))


def types():
    return list(load_all())


def get(t):
    every = load_all()
    if t not in every:
        raise CatalogError(f"unknown scene type {t!r}; known: {', '.join(every)}")
    return every[t]


# ---------------------------------------------------------------- the tables the engine reads


def scenes():
    """engine.SCENES: type -> (required slots, optional slots, what it shows)."""
    return {t: ([n for n, s in b["slots"].items() if s.get("required")],
                [n for n, s in b["slots"].items() if not s.get("required")], b["what"]) for t, b in load_all().items()}


def counts():
    """engine.COUNTS: type -> (lo, hi) items."""
    return {t: tuple(b["slots"]["items"]["count"]) for t, b in load_all().items()
            if "items" in b["slots"] and b["slots"]["items"].get("count")}


def min_scene():
    """speech.MIN_SCENE: type -> seconds on screen at least."""
    return {t: b["min_seconds"] for t, b in load_all().items()}


def min_words():
    """ka_check.MIN_WORDS: type -> narration words a scene needs before the next one starts (K9)."""
    return {t: b["min_words"] for t, b in load_all().items()}


def text_fields():
    """(top-level text slots, item and object text fields) of every brush: the on-screen texts ka_check reads."""
    top, inner = [], []
    for b in load_all().values():
        for n, s in b["slots"].items():
            if s["kind"] == "text":
                top.append(n)
            of = s.get("of") or {}
            if s["kind"] in ("list", "obj") and "kind" not in of:
                inner += [f for f, x in of.items() if x["kind"] == "text"]
    return tuple(dict.fromkeys(top)), tuple(dict.fromkeys(inner))


# ---------------------------------------------------------------- checks


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _too_long(path, spec, v):
    if spec["kind"] == "text" and isinstance(v, str) and len(v) > spec["max"]:
        return [f"{path}: {len(v)} characters, at most {spec['max']} (it must fit the screen)"]
    return []


def _check(path, spec, v):
    """One filled slot: counts, lengths, numbers, names. Shapes of items are each type's own (engine.shape_problems)."""
    k = spec["kind"]
    if k == "text":
        return _too_long(path, spec, v)
    if k == "num":
        if not _number(v):
            return [f"{path}: needs a number"]
        if "min" in spec and v < spec["min"] or "max" in spec and v > spec["max"]:
            return [f"{path}: {v:g} is outside {spec.get('min', '-inf')}..{spec.get('max', 'inf')}"]
        return []
    if k == "enum":
        return [] if v in spec["values"] else [f"{path}: {v!r}, use one of {', '.join(spec['values'])}"]
    out = []
    if k == "list" and isinstance(v, list):
        if spec.get("count"):
            lo, hi = spec["count"]
            if not lo <= len(v) <= hi:
                out.append(f"{path}: {len(v)}, needs {lo}-{hi}" if lo != hi else f"{path}: {len(v)}, needs {lo}")
        of = spec["of"]
        for i, it in enumerate(v):
            if "kind" in of:
                out += _too_long(f"{path}[{i}]", of, it)
            elif isinstance(it, dict):
                for f, s in of.items():
                    out += _too_long(f"{path}[{i}].{f}", s, it.get(f))
    if k == "obj" and isinstance(v, dict):
        for f, s in spec["of"].items():
            out += _too_long(f"{path}.{f}", s, v.get(f))
    return out


def slot_problems(scene, brushes=None):
    """Counts, lengths, numbers and names of a scene's filled slots (a missing required one is the structure
    check's). brushes: {type: brush} to check against instead of the catalog (validate's example check)."""
    b = (brushes or load_all()).get(scene.get("type"))
    if not b:
        return []
    out = []
    for n, spec in b["slots"].items():
        v = scene.get(n)
        if v is None or v == "" or v == []:
            continue
        out += _check(n, spec, v)
    return out


def family_problems(scene, family):
    """A type or a slot value this story's family never uses (families_deny, an enum's deny)."""
    b = load_all().get(scene.get("type"))
    if not b:
        return []
    out = []
    if family in b["families_deny"]:
        out.append(f"a {b['type']} scene is not used for the {family} family (brushes/{b['type']}.json)")
    for n, spec in b["slots"].items():
        v = scene.get(n)
        if spec["kind"] == "enum" and family in (spec.get("deny") or {}).get(v, []):
            others = [x for x in spec["values"] if family not in (spec.get("deny") or {}).get(x, [])]
            out.append(f"{n} {v!r} is not used for the {family} family: use {' or '.join(others)}")
    return out


def story_problems(story, family):
    """Every scene's slot and family problems, named by scene (the writer's repair loop; engine.structure_problems
    runs the same per scene)."""
    out = []
    for i, s in enumerate(story.get("scenes") or []):
        if isinstance(s, dict):
            out += [f"scene {i} ({s.get('type')}): {x}" for x in slot_problems(s) + family_problems(s, family)]
    return out


# ---------------------------------------------------------------- the writer's menu


def _line(b):
    return "   " + json.dumps(b["schema"], ensure_ascii=False)


def _rules(b):
    return [r if r.startswith("  ") else f"- {r}" for r in b["rules"]]


def schema(types=None):
    """The writer's JSON shape and rules. types: only these scene types (a director's or a program's menu, in any
    order; shown in the catalog's order); None: every type a program need not name (NAMED_ONLY)."""
    every = load_all()
    menu = [b for t, b in every.items() if (t not in NAMED_ONLY if types is None else t in types)]
    lines = ",\n".join(_line(b) for b in menu if b["schema"] is not None)
    rules = [r for b in menu for r in _rules(b)]
    if any(b["em"]["fields"] for b in menu):
        rules.append(RULE_EM)
    if any(b["type"] not in NO_MEDIA and b["schema"] is not None for b in menu):
        rules.append(RULE_SHOW)
    return "\n".join([HEAD, lines, " ]", "}", RULES_HEAD, *rules, RULE_LIMITS, RULES_TAIL]) + "\n"


def options():
    """engine options -> scenes: every type's menu card."""
    out = {}
    for t, b in load_all().items():
        req = [n for n, s in b["slots"].items() if s.get("required")]
        out[t] = {"required": req, "optional": [n for n in b["slots"] if n not in req], "shows": b["what"],
                  "use_when": b["use_when"], "avoid_when": b["avoid_when"], "pairs_with": b["pairs_with"],
                  "slots": b["slots"], "families_deny": b["families_deny"], "min_seconds": b["min_seconds"],
                  "min_words": b["min_words"], "em": b["em"], "example": b["example"]}
    return out
