"""The idea step: a program that asks for it gets one idea per story before its script is written.

Reskinned videos come from the same script shape in new colors, so the difference has to start before the script.
A model is asked for several ideas, each from another rung of a concrete ladder (asking for "something creative"
makes models converge; asking for a named rung with its odds spreads them), code judges them and code chooses:

    rung  question                                     (programs say which they allow: "concept": {"rungs": [...]})
    1     the object: what physical thing is it about?
    2     the mechanism: what does it do, what happens to it?
    3     the place: where can you point?
    4     the number's body: what does the number look like?
    5     the role's moment: what does the role touch, not the name?
    6     the analogy: what else behaves like this?

The filters run in this order; the first that fails names the idea's verdict:

    shape      the fields, a rung the program allows, a device on that rung that the program's scenes can draw
    facts      at least one fact, each copied from the source (the one reason to ask the model again)
    loaded     a metaphor field that asserts what no source says (war, disease, flood, beast)
    generic    the object is the film's own tool (a quote, a list, a map, a sign), not the story's thing
    object     the family's recent films used this object
    seen       too close in words to one of the brand's recent ideas
    swap       the idea doesn't hold its own facts, once what the family's recent ideas said is taken away, so another
               story could use it unchanged. A code stand-in for "would it fit story B?"
    cliche     the first picture of its family: flagged, not rejected, taken only when no clean idea is left

Of what survives, a device that does something beats one that is only the usual scene ("plain": a quote card), then
the least used device wins, then the least used rung, ties by the story id's hash, so a run keeps moving and one
story keeps its choice. No idea left means no concept: the film is written as before, with a warning
(the guard never fails a video). The chosen idea is code-owned like `date`: it goes to the writer, the story keeps it
(`concept`), and the checks ask that the narration says the object and a scene type of the device carries it. A script
that still can't after its repairs keeps its place and loses the idea, with a warning. It is never on screen, so it
can carry no fact. A concept's history is `variety.record_concept` in veasy.db, apart from the
novelty guard's fingerprint: a new field there would shift the calibrated thresholds.

    python -m tt_shorts.engine concept --source url --ref <url> [--program explainer] [--ideas ideas.json]
"""
import difflib
import functools
import json
import pathlib
import re
import zlib

from tt_shorts import news_check

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "concepts"
RUNGS = {1: "the object: what physical thing is this about?",
         2: "the mechanism: what does it do, what happens to it?",
         3: "the place: where can a viewer point?",
         4: "the number's body: what does the key number look like?",
         5: "the role's moment: what does the role touch at the moment it matters? (never a name)",
         6: "the analogy: what else behaves like this?"}
IDEAS = 5  # the model's candidates
MAX_OBJECT_WORDS = 3
MIN_TOKEN = 5  # letters: shorter Georgian words are mostly function words
SEEN = 0.75  # difflib ratio to a recent idea of the brand
RECENT = 100  # the brand's last ideas the filters read
FAMILY_RECENT = 20  # the family's last ideas the swap test takes away
SOURCE_CHARS = 4000  # what the model reads: an idea needs the gist, not every line
VERDICTS = ("ok", "flagged", "rejected")


class ConceptError(ValueError):
    pass


@functools.lru_cache(maxsize=None)
def devices():
    """{id: {use, scenes, rungs, news}}."""
    return json.loads((DIR / "devices.json").read_text(encoding="utf-8"))["devices"]


@functools.lru_cache(maxsize=None)
def cliches():
    return json.loads((DIR / "cliches.json").read_text(encoding="utf-8"))


def validate(value, where="concept"):
    """A program's "concept": {"rungs": [...], "ideas": n}."""
    if not isinstance(value, dict) or set(value) - {"rungs", "ideas"}:
        raise ConceptError(f"{where}: a dict of rungs and ideas")
    rungs = value.get("rungs")
    if not isinstance(rungs, list) or not rungs or any(r not in RUNGS for r in rungs) or len(set(rungs)) != len(rungs):
        raise ConceptError(f"{where}: rungs is a list of different steps out of {sorted(RUNGS)}")
    ideas = value.get("ideas", IDEAS)
    if not isinstance(ideas, int) or not 2 <= ideas <= len(rungs):
        raise ConceptError(f"{where}: ideas is 2 to {len(rungs)}, each from another rung")
    return {"rungs": rungs, "ideas": ideas}


def usable(p, rung=None):
    """{device: the scene types that carry it in this program}: only what the program's scenes can draw today."""
    from tt_shorts import programs
    out = {}
    for did, d in devices().items():
        carried = [t for t in d["scenes"] if programs.allowed(p, t)]
        if carried and (rung is None or rung in d["rungs"]):
            out[did] = carried
    return out


def root(word):
    """A Georgian word without its ending, enough to find it inflected: ვენტილი -> ვენტი, მილი -> მილ."""
    word = word.strip(".,:;!?„“\"'()«»-").lower()
    return word[:-1] if len(word) <= 5 else word[:-2]


def _words(text):
    return re.findall(r"[ა-ჰ]+", text or "")


def said(phrase, text):
    """Is the phrase's head (its last word: Georgian puts it there) in the text, under any ending?"""
    head = _words(phrase)
    if not head:
        return False
    stem = root(head[-1])
    return any(w.startswith(stem) for w in _words(text))


def tokens(text):
    """What a text is made of: its numbers, its Latin names and the roots of its longer words."""
    return set(news_check.numbers(text or "")) | {w[:MIN_TOKEN] for w in _words(text) if len(w) >= MIN_TOKEN} | \
        {w.lower() for w in re.findall(r"[A-Za-z]{2,}", text or "")}


def _stems_hit(text, stems):
    words = _words(text)  # a stem of two letters is a word under its endings (ომი, ომში), never a prefix (ომბუდსმენი)
    return next((s for s in stems if any(w.startswith(s) and (len(s) > 2 or len(w) <= len(s) + 3) for w in words)), None)


def _shape(idea, p, rungs):
    if not isinstance(idea, dict):
        return "not an object"
    for k in ("idea", "object", "verb", "device"):
        if not isinstance(idea.get(k), str) or not idea[k].strip():
            return f"no {k}"
    if idea.get("rung") not in rungs:
        return f"rung {idea.get('rung')!r} is not one of {rungs}"
    if idea["device"] not in usable(p, idea["rung"]):
        return f"device {idea['device']!r} can't be drawn on rung {idea['rung']} here"
    if not _words(idea["object"]) or len(idea["object"].split()) > MAX_OBJECT_WORDS or re.search(r"\d", idea["object"]):
        return f"the object is 1-{MAX_OBJECT_WORDS} words, no digits"
    return None


def _in_source(fact, source, numbers):
    """A fact's numbers, Latin names and Georgian head are all in the source, under any ending."""
    digits = news_check.numbers(fact)
    latin = re.findall(r"[A-Za-z][A-Za-z.&'-]*", fact)
    if digits - numbers or any(w.lower() not in source.lower() for w in latin):
        return False
    return said(fact, source) if _words(fact) else bool(digits or latin)


def _facts(idea, source):
    facts = idea.get("facts")
    if not isinstance(facts, list) or not facts:
        return "it names no fact of the source"
    numbers = news_check.numbers(source)
    return next((f"{f!r} is not in the source" for f in map(str, facts) if not _in_source(f, source, numbers)), None)


def judge(ideas, p, source, family, past=(), story=None):
    """The filters on a list of ideas -> [{idea fields..., "verdict", "why"}], in the model's order. past: the brand's
    recent ideas, newest first ({story, family, object, device, rung, idea}); the story's own don't count."""
    rungs = (p.get("concept") or {}).get("rungs") or list(RUNGS)
    past = [x for x in past if x.get("story") != story]
    kin = [x for x in past if x.get("family") == family]
    used = {root(_words(x["object"])[-1]) for x in kin[:RECENT] if _words(x.get("object"))}
    away = set()
    for x in kin[:FAMILY_RECENT]:
        away |= tokens(x.get("idea"))
    shelf = cliches()
    corny = tuple(shelf.get("all") or ()) + tuple((shelf.get("families") or {}).get(family) or ())
    out, taken = [], set()

    def verdict(idea):
        why = _shape(idea, p, rungs)
        if why:
            return "rejected", "shape", why
        why = _facts(idea, source)
        if why:
            return "rejected", "facts", why
        words = f"{idea['idea']} {idea['object']}"
        hit = _stems_hit(words, tuple(shelf.get("loaded") or ()))
        if hit:
            return "rejected", "loaded", f"„{hit}…“ asserts what no source says"
        if idea["rung"] in taken:
            return "rejected", "shape", f"a second idea from rung {idea['rung']}"
        taken.add(idea["rung"])
        if _stems_hit(_words(idea["object"])[-1], tuple(shelf.get("generic") or ())):
            return "rejected", "generic", f"„{idea['object']}“ is the film's own tool, not this story's thing"
        if root(_words(idea["object"])[-1]) in used:
            return "rejected", "object", f"the family's recent films used „{idea['object']}“"
        close = max(((difflib.SequenceMatcher(None, idea["idea"], x["idea"]).ratio(), x) for x in past if x.get("idea")),
                    key=lambda y: y[0], default=(0, None))
        if close[0] >= SEEN:
            return "rejected", "seen", f"{close[0]:.2f} like the idea of {close[1].get('story')}"
        if not (tokens(idea["idea"]) & tokens(" ".join(map(str, idea["facts"])))) - away:
            return "rejected", "swap", "none of its own facts are in it: another story could use it unchanged"
        hit = _stems_hit(words, corny)
        return ("flagged", "cliche", f"„{hit}…“ is the first picture of its family") if hit else ("ok", None, None)

    for idea in ideas:
        state, rule, why = verdict(idea)
        out.append({**(idea if isinstance(idea, dict) else {"idea": str(idea)}), "verdict": state, "rule": rule, "why": why})
    return out


def choose(judged, story, past=()):
    """The survivor to film: a clean idea before a flagged one, a device that does something before one that is only
    the usual scene, the least used device, the least used rung, ties by the story id's hash. None when nothing
    survived."""
    left = [x for x in judged if x["verdict"] != "rejected"]
    if not left:
        return None
    count = lambda key, value: sum(x.get(key) == value for x in past)  # noqa: E731
    plain = lambda x: bool(devices()[x["device"]].get("plain"))  # noqa: E731
    return min(left, key=lambda x: (x["verdict"] != "ok", plain(x), count("device", x["device"]), count("rung", x["rung"]),
                                    zlib.crc32(f"{story}:{x['object']}".encode())))


def _seed(story, idea):
    return f"{zlib.crc32(f'{story}:{idea['object']}'.encode()):08x}"[:4]


def stamp(chosen, judged, story, kind="assigned"):
    """The story's `concept`: code-owned, what was chosen and, on the record, what was turned down and why."""
    keep = ("idea", "object", "verb", "rung", "device", "facts")
    return {**{k: chosen[k] for k in keep if k in chosen},
            "rejected": [{"idea": x.get("idea", ""), "why": x.get("rule") or x.get("why")} for x in judged if x is not chosen],
            "roll": {"seed": _seed(story, chosen), "kind": kind}}


def prompt(p, cluster, articles, family, past=(), reasons=()):
    """What the model is asked: named rungs and their odds, never "be creative"."""
    c = p["concept"]
    rungs = [r for r in c["rungs"] if usable(p, r)]
    shelf = cliches()
    menu = "\n".join(f"  {did} (rungs {', '.join(map(str, devices()[did]['rungs']))}): {devices()[did]['use']}"
                     for did in usable(p))
    ladder = "\n".join(f"  {r}. {RUNGS[r]}" for r in rungs)
    corny = ", ".join(tuple(shelf.get("all") or ()) + tuple((shelf.get("families") or {}).get(family) or ()))
    lately = ", ".join(dict.fromkeys(x["object"] for x in past if x.get("family") == family and x.get("object")))
    body = "\n\n".join(articles)[:SOURCE_CHARS]
    again = ("\nThe last answer was turned down:\n- " + "\n- ".join(reasons) + "\nFix these. Copy facts from the source.\n"
             if reasons else "")
    return (f"You direct one short film before its script exists. Find the idea of this film.\n\n"
            f"Write exactly {c['ideas']} ideas, each from a different rung. Start from this source's own things, and "
            f"climb only as far as you must:\n{ladder}\n\n"
            f"Each idea picks a device, one that lists its rung:\n{menu}\n\n"
            "JSON only:\n"
            '{"ideas": [{"rung": 2, "device": "state-change", "idea": "one Georgian sentence: what the viewer SEES '
            'happen, built from this source\'s own nouns and numbers", "object": "1-3 Georgian words: a thing that '
            'can be drawn, which the narration will say", "verb": "what happens to it, one English word", "facts": '
            '["a number or a name copied from the source"], "p": 0.2}]}\n\n'
            "p: how likely an average writer is to think of this idea; they sum to 1, and at least two are under 0.15.\n"
            "Rules:\n"
            "- A fact is copied from the source, never made up, summed or rounded.\n"
            "- The object is a thing in this story's world, never the film's own tool: not a quote, list, map, sign, "
            "number, document or screen.\n"
            "- The idea could not be used for another story: it names what only this source has.\n"
            "- No opinion, no blame, nothing the source does not say.\n"
            f"- Not these first pictures: {corny or '-'}.\n"
            f"- No war, disease, flood or beast metaphors: {', '.join(shelf.get('loaded') or ())}.\n"
            f"- Objects used lately, not again: {lately or '-'}.\n{again}\n"
            f"სათაური: {cluster.get('headline', '')}\n--- წყარო ---\n{body}")


def parse(text):
    from tt_shorts import writer
    data = writer._object(text)
    ideas = data.get("ideas") if isinstance(data, dict) else None
    return ideas if isinstance(ideas, list) else []


def direct(p, cluster, articles, brand, family, story, past=(), ideas=None, call=None):
    """The idea step -> {"concept", "ideas", "calls", "warning"}. ideas: an agent's own, judged the same way (no model
    call). Asked again once, and only when facts were the reason: anything else is the idea, not the wording. A
    model that fails is a warning: the film is written without a concept."""
    from tt_shorts import writer
    source = "\n\n".join(articles)
    calls, last = 0, []
    call = call or (lambda text: writer._call(text, writer.MODEL, max_tokens=1400))

    def ask(reasons=()):
        nonlocal calls
        calls += 1
        return parse(call(prompt(p, cluster, articles, family, past, reasons)))

    try:
        last = judge(ideas if ideas is not None else ask(), p, source, family, past, story)
        chosen = choose(last, story, past)
        if chosen is None and ideas is None:
            reasons = [f"„{x.get('idea', '')[:50]}“: {x['why']}" for x in last if x.get("rule") == "facts"]
            if reasons:
                last = judge(ask(reasons), p, source, family, past, story)
                chosen = choose(last, story, past)
    except (RuntimeError, ValueError, OSError) as e:
        return {"concept": None, "ideas": last, "calls": calls, "warning": f"concept: no idea, the model failed: {e}"}
    if chosen is None:
        why = ", ".join(sorted({x.get("rule") or "?" for x in last})) or "no ideas came back"
        return {"concept": None, "ideas": last, "calls": calls, "warning": f"concept: every idea was turned down ({why})"}
    kind = "agent" if ideas is not None else "assigned"
    return {"concept": stamp(chosen, last, story, kind), "ideas": last, "calls": calls, "warning": None}


def brief_block(concept, p):
    """The writer's line: the film's idea, chosen before the script."""
    d = devices()[concept["device"]]
    carried = usable(p).get(concept["device"]) or d["scenes"]
    return ("THE FILM'S IDEA (chosen by code; follow it, never announce it, never put it on screen as a claim):\n"
            f"- What the viewer sees: {concept['idea']}\n"
            f"- The object: {concept['object']}. The narration says this word, and the film comes back to it.\n"
            f"- What happens to it: {concept['verb']}.\n"
            f"- The device: {d['use']}. At least one scene is of type {' or '.join(carried)}, and it shows this.\n"
            f"- Facts it stands on: {', '.join(map(str, concept.get('facts') or []))}.\n"
            "The facts stay the source's: the idea changes how the film shows them, never what it says.\n\n")


def story_problems(story):
    """A concept in a story: only a program that has the step, and the film really carries it."""
    from tt_shorts import programs
    c = story.get("concept")
    if not c:
        return []
    try:
        step = programs.of(story).get("concept")
    except programs.ProgramError:
        return []  # programs.story_problems names it
    if not step:
        return [f"concept: program {programs.name_of(story)!r} has no idea step"]
    out = []
    if not said(c.get("object", ""), story.get("narration", "")):
        out.append(f"concept: the narration never says the film's object, „{c.get('object')}“")
    scenes = usable(programs.of(story)).get(c.get("device")) or []
    if not any(s.get("type") in scenes for s in story.get("scenes") or []):
        out.append(f"concept: no scene carries the device {c.get('device')!r}: use {' or '.join(scenes) or 'another'}")
    return out


def options():
    """engine options: the ladder and what the kit can draw today."""
    return {"about": "a program with \"concept\" gets one idea per story: the model writes several from named rungs, "
                     "code judges and chooses, the story keeps it (concept.py)",
            "rungs": {str(k): v for k, v in RUNGS.items()},
            "devices": {k: v["use"] for k, v in devices().items() if v["scenes"]},
            "later": sorted(k for k, v in devices().items() if not v["scenes"]),
            "filters": ["shape", "facts", "loaded", "generic", "object", "seen", "swap", "cliche"]}


def load_ideas(path):
    """An agent's ideas from a file: a list, or {"ideas": [...]}."""
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    data = data.get("ideas") if isinstance(data, dict) else data
    if not isinstance(data, list):
        raise ConceptError(f"{path}: a list of ideas, or {{\"ideas\": [...]}}")
    return data
