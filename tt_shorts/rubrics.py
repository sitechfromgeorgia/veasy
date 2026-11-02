"""Rubrics: named recurring shows with a shape, a slot and an episode number (ROADMAP D6, B7; docs/next.md 2).

A director (directors.py) changes what kind of film one story becomes; a rubric is a show the audience learns to
recognise: „დღის ციფრი · #12“ every day at the same hour, with the same shape. Rubrics are data,
`rubrics/<id>.json`, validated here:

  id, label     the Georgian name drawn in the hook's chip; "{n}" in it is a count code fills (agree: the outlets
                that state the facts, digest: the stories), never the writer
  about         English, for the agent
  numbering     episode: the chip says „<label> · #<episode>“ (a counter per brand and rubric) |
                part: „<label> · ნაწ. <part>“ (the story's own part, from the stored state of its cluster)
  count         optional: agree | stories, what "{n}" in the label is
  program       the program the rubric's videos are (news, or digest: built by code, tt_shorts/digest.py)
  format        its format (formats/): the length window (number: 20-25 s, digest: 45-60 s)
  slot          "HH:MM", the brand's local time the video is for (ops/daily.py --rubrics orders the jobs by it)
  eligible      [{fact: min | {"max": n} | true/false, "families": [...]}, ...]: any alternative whose every
                condition holds (the same declarative form as a director's; code evaluates it on facts(), there is
                no expression to eval)
  never         conditions that rule the rubric out
  shape         the scene order a video of the rubric has: [{"types": [..] | "any", "min": 1, "max": 1}, ...];
                "any" is any scene but hook, end and chapter
  needs         optional: [[types], ...]: at least one scene of each group (changes: a dated scene)
  brief         English lines added to the writer's prompt (they win over the director where they differ)
  words         optional: Georgian words code uses for the rubric (the digest's intro and outro)

Facts (facts()) are directors.facts plus:
  outlets       the cluster's outlets (its source_count when larger than the names it carries)
  members       the member articles code can read (all members when the source gives them)
  big_numbers   stated quantities of 100 or more (not dates or times) and percents: a number worth a show
  prices        stated money amounts (ლარი, ₾, დოლარი, ევრო, თეთრი)
  rules         rule words: წესი, აკრძალვა, ჯარიმა, სავალდებულო, რეგულაცია, დადგენილება, ნებართვა
  agreed        facts literally in at least AGREE_MIN member articles (agreed())
  had_video     the cluster already had a video that ended done (the stored state, remember())
  new_outlets   outlets it gained since that video; new_facts: numbers and quotes not in that video's articles
  stories       a digest's checked stories

Episodes (decision, documented in the veasy:rubrics skill): the number is reserved when code stamps the story
(engine write --rubric, the queue's write step, or `engine rubrics stamp` for a hand-written story), before the
voice, because the chip that shows it is drawn in the video. A reservation is idempotent per (brand, rubric, story
key): the same story in another look or a re-run of its job gets the same number. The queue marks it done when the
job ends done; a job that ends failed or is cancelled releases it when no later episode exists (the next video
takes the number), else the number stays unused (a gap, never two videos with one number).

"Continues" (ამბავი გრძელდება): every news video that ends done stores what its cluster had (remember(): the
outlets, the stated quantities and the quotes of its articles) in veasy.db; growth() compares a cluster's data now
with the latest stored part, so part N+1 is offered only with 2+ new outlets and a number or quote part N didn't
have.

Agree (ადასტურებს N გამოცემა): agreed() counts, across all member articles, the facts that are literally in at
least N of them: the same number followed by the same word (its first 5 letters: Georgian adds case endings), the
same day and month, the same time, the same gazetteer place, the same verbatim quote. The agree scene shows them
with „მინიმუმ N“ and no outlet names (no side is ever named).
"""
import contextlib
import datetime as dt
import functools
import json
import pathlib
import re
import sqlite3

from tt_shorts import news_check, store

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "rubrics"
KEYS = ("id", "label", "about", "numbering", "count", "program", "format", "slot", "eligible", "never", "shape",
        "needs", "brief", "words")
REQUIRED = ("id", "label", "about", "numbering", "program", "format", "slot", "eligible", "never", "shape", "brief")
NUMBERING = ("episode", "part")
COUNTS = ("agree", "stories")
FACTS = ("numbers", "quantities", "percents", "dates", "times", "places", "regions", "quotes", "speakers", "icons",
         "facts", "outlets", "members", "big_numbers", "prices", "rules", "agreed", "new_outlets", "new_facts",
         "stories")
FLAGS = ("deaths", "had_video")
NOT_ANY = ("hook", "end", "chapter")  # what a shape's "any" slot never takes
AGREE_MIN = 3  # agree: a fact must be in at least this many member articles
AGREE_ITEMS = 3  # at most this many facts on the agree scene
AGREE_TEXT = 40  # characters a fact may have on screen
BIG = 100
PRICE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:ლარ|₾|GEL|დოლარ|\$|ევრო|€|თეთრ)")
RULE_WORDS = re.compile(r"(?<![ა-ჰ])(?:წეს(?:ი|ის|ით|ებ|ზე)|აკრძალ|ჯარიმ|სავალდებულ|რეგულაცი|დადგენილებ|ნებართვ)")


class RubricError(ValueError):
    pass


# ---------------------------------------------------------------- data


def _scene_types():
    from tt_shorts import catalog
    return set(catalog.types())


def _condition(name, where, cond):
    from tt_shorts import brand
    if not isinstance(cond, dict) or not cond:
        raise RubricError(f"rubric {name!r}: {where}: each condition is a non-empty object")
    for k, v in cond.items():
        if k == "families":
            if not isinstance(v, list) or not set(v) <= set(brand.FAMILIES):
                raise RubricError(f"rubric {name!r}: {where}: families must be a list of {', '.join(brand.FAMILIES)}")
        elif k in FLAGS:
            if not isinstance(v, bool):
                raise RubricError(f"rubric {name!r}: {where}: {k} is true or false")
        elif k in FACTS:
            ok = isinstance(v, int) and not isinstance(v, bool) and v >= 0
            ok = ok or (isinstance(v, dict) and set(v) == {"max"} and isinstance(v["max"], int))
            if not ok:
                raise RubricError(f"rubric {name!r}: {where}: {k} is a minimum count or {{\"max\": n}}")
        else:
            raise RubricError(f"rubric {name!r}: {where}: unknown fact {k!r} (facts: {', '.join(FACTS + FLAGS)}, "
                              "families)")


def validate(name, r):
    """Raise RubricError when a rubric names something the engine can't do; returns it resolved."""
    from tt_shorts import formats, programs

    def need(cond, msg):
        if not cond:
            raise RubricError(f"rubric {name!r}: {msg}")
    need(isinstance(r, dict), "not an object")
    missing = [k for k in REQUIRED if k not in r]
    need(not missing, f"missing {missing}")
    need(not set(r) - set(KEYS), f"unknown keys {sorted(set(r) - set(KEYS))}")
    need(r["id"] == name and re.fullmatch(r"[a-z]+", name), "id is its file name (lowercase letters)")
    need(isinstance(r["label"], str) and re.search(r"[ა-ჰ]", r["label"]), "label is Georgian (it is drawn)")
    need(r["numbering"] in NUMBERING, f"numbering is one of {', '.join(NUMBERING)}")
    count = r.get("count")
    need(count is None or count in COUNTS, f"count is one of {', '.join(COUNTS)}")
    need(("{n}" in r["label"]) == bool(count), 'a label with "{n}" names its count, and a count needs "{n}"')
    need(not re.search(r"\d", r["label"].replace("{n}", "")), "the label carries no digit of its own (N2: code "
         'fills "{n}" from the data)')
    try:
        programs.get(r["program"])
    except programs.ProgramError as e:
        need(False, str(e))
    need(r["format"] in formats.load_all(), f"format {r['format']!r} is not a format (see options)")
    need(isinstance(r["slot"], str) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", r["slot"]), "slot is HH:MM")
    need(isinstance(r["eligible"], list) and r["eligible"], "eligible is a list of alternatives")
    for c in r["eligible"]:
        _condition(name, "eligible", c)
    need(isinstance(r["never"], list), "never is a list of conditions")
    for c in r["never"]:
        _condition(name, "never", c)
    known = _scene_types()
    shape = r["shape"]
    need(isinstance(shape, list) and len(shape) >= 2, "shape is a list of slots")
    for i, s in enumerate(shape):
        need(isinstance(s, dict) and set(s) <= {"types", "min", "max"} and "types" in s, f"shape[{i}] is "
             '{"types": [...] | "any", "min", "max"}')
        t = s["types"]
        need(t == "any" or (isinstance(t, list) and t and set(t) <= known),
             f"shape[{i}]: types is \"any\" or scene types of the catalog (brushes/)")
        lo, hi = s.get("min", 1), s.get("max", s.get("min", 1))
        need(isinstance(lo, int) and isinstance(hi, int) and 0 <= lo <= hi <= 6, f"shape[{i}]: 0 <= min <= max <= 6")
    need(shape[0].get("types") == ["hook"] and shape[0].get("min", 1) == 1, "the shape starts with one hook")
    need(shape[-1].get("types") == ["end"], "the shape ends with the end card")
    for g in r.get("needs") or []:
        need(isinstance(g, list) and g and set(g) <= known, "needs is a list of scene type groups")
    need(isinstance(r["brief"], list) and 2 <= len(r["brief"]) <= 10 and all(isinstance(x, str) and x for x in r["brief"]),
         "brief is 2-10 lines for the writer")
    words = r.get("words") or {}
    need(isinstance(words, dict) and all(isinstance(v, (str, dict)) for v in words.values()), "words is {key: text}")
    return {**r, "count": count, "needs": list(r.get("needs") or []), "words": dict(words)}


@functools.lru_cache(maxsize=4)
def _load(path_str):
    out = {}
    for path in sorted(pathlib.Path(path_str).glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RubricError(f"rubric {path.stem!r}: not JSON ({e})") from e
        out[path.stem] = validate(path.stem, raw)
    return out


def load_all():
    return dict(_load(str(DIR)))


def names():
    return sorted(load_all())


def get(name):
    every = load_all()
    if name not in every:
        raise RubricError(f"unknown rubric {name!r}; known: {', '.join(sorted(every))}")
    return every[name]


def by_slot():
    """Every rubric, in the order of its time slot."""
    return sorted(load_all().values(), key=lambda r: (r["slot"], r["id"]))


def types(r):
    """The scene types a rubric's shape names (the writer's menu must have them)."""
    return [t for s in r["shape"] if s["types"] != "any" for t in s["types"]]


# ---------------------------------------------------------------- facts and eligibility


def _quantities(found):
    return [q for q in found.get("quantities") or [] if q.isdigit()]


def members_of(data):
    """[{"outlet", "text"}] of a source's data: its "members" (every member article) when it gives them, else its
    articles, paired with the outlets when there are as many."""
    if data.get("members"):
        return [{"outlet": str(m.get("outlet") or i), "text": str(m.get("text") or "")}
                for i, m in enumerate(data["members"])]
    arts = [a for a in data.get("articles") or [] if isinstance(a, str)]
    outs = list((data.get("cluster") or {}).get("sources") or [])
    return [{"outlet": outs[i] if len(outs) == len(arts) else str(i), "text": a} for i, a in enumerate(arts)]


def facts(data, brand=None, grown=None):
    """What a rubric's eligibility reads, from a source's data ({"cluster", "articles", "members"?, "stories"?}):
    the director facts (directors.facts) plus the rubric facts in the module docstring. grown: growth()'s result
    for this cluster (had_video, new_outlets, new_facts); without it, the cluster had no video."""
    from tt_shorts import brand as packs, directors
    cluster = data.get("cluster") or {}
    arts = [a for a in data.get("articles") or [] if isinstance(a, str)]
    pack = packs.load(brand) if not isinstance(brand, dict) else brand
    f = directors.facts(arts, cluster.get("category", ""), pack, cluster)
    found = f["found"]
    text = " ".join(arts)
    members = members_of(data)
    big = [q for q in _quantities(found) if int(q) >= BIG]
    grown = grown or {}
    out = {**{k: v for k, v in f.items() if k != "found"},
           "outlets": max(len(cluster.get("sources") or []), int(cluster.get("source_count") or 0)),
           "members": len(members), "big_numbers": len(big) + len(found.get("percents") or []),
           "prices": len(PRICE.findall(text)), "rules": len(RULE_WORDS.findall(text)),
           "agreed": len(agreed(members, AGREE_MIN)), "had_video": bool(grown.get("had_video")),
           "new_outlets": len(grown.get("new_outlets") or []),
           "new_facts": len(grown.get("new_numbers") or []) + len(grown.get("new_quotes") or []),
           "stories": len(data.get("stories") or [])}
    out["found"] = {**found, "big_numbers": big, "prices": PRICE.findall(text)}
    return out


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


def holds(r, f):
    """True when the rubric's eligibility holds for these facts and no never-condition rules it out."""
    return not any(_holds(c, f) for c in r["never"]) and any(_holds(c, f) for c in r["eligible"])


def eligible(f, program="news"):
    """The rubrics a cluster's facts allow, in slot order, among those of the program."""
    return [r["id"] for r in by_slot() if r["program"] == program and holds(r, f)]


# ---------------------------------------------------------------- agree: facts literally in N members


def _stem(word):
    return word[:5]


NUM_WORD = re.compile(r"(?<![\d.,])(\d{1,3}(?:[  ]\d{3})+|\d+(?:[.,]\d+)?)\s*(%|[ა-ჰ]{3,})")


def claims(text):
    """{key: the phrase as this text writes it} of the facts one text states: a number with the word after it, a
    day and month, a time, a gazetteer place, a verbatim quote of 4+ words."""
    from tt_shorts import geo
    text = news_check.flat(text or "").replace("&nbsp;", " ")
    out = {}
    for m in NUM_WORD.finditer(text):
        if m.group(2).startswith(news_check.MONTHS):  # „15 სექტემბერს“ is a date, counted below
            continue
        digits = re.sub(r"[  ]", "", m.group(1)).replace(",", ".")
        out.setdefault(("num", digits, _stem(m.group(2))), m.group(0).strip())
    for m in news_check._DAY_MONTH.finditer(text):
        out.setdefault(("date", int(m.group(1)), news_check.MONTHS.index(m.group(2))), m.group(0).strip())
    for m in news_check._TIME.finditer(text):
        out.setdefault(("time", f"{int(m.group(1)):02d}:{m.group(2)}"), m.group(0))
    loc = geo.locate(text) or {}
    for p in loc.get("places", []):
        out.setdefault(("place", p["name"]), p["name"])
    for m in re.finditer(r'"([^"]{8,200})"', text):
        q = m.group(1).strip()
        if len(q.split()) >= 4:
            out.setdefault(("quote", q), f"„{q}“")  # flat() turned „…“ into "…"
    return out


KIND_ORDER = {"num": 0, "date": 1, "time": 1, "place": 2, "quote": 3}


def agreed(members, minimum=AGREE_MIN):
    """The facts literally in at least `minimum` member articles, counted per outlet (two articles of one outlet
    count once): [{"key", "text" (as the first member writes it), "count", "kind"}], most agreed first, numbers
    before dates, places and quotes. members: [{"outlet", "text"}] (members_of) or plain texts."""
    rows = [m if isinstance(m, dict) else {"outlet": str(i), "text": m} for i, m in enumerate(members or [])]
    seen, text = {}, {}
    for m in rows:
        for key, phrase in claims(m.get("text", "")).items():
            seen.setdefault(key, set()).add(m.get("outlet"))
            text.setdefault(key, phrase)
    out = [{"key": k, "text": text[k], "count": len(o), "kind": k[0]} for k, o in seen.items() if len(o) >= minimum]
    out.sort(key=lambda x: (-x["count"], KIND_ORDER[x["kind"]], len(x["text"])))
    return out


def agree_scene(members, minimum=AGREE_MIN, most=AGREE_ITEMS):
    """What an agree scene shows, by code: {"n": N, "total": members, "items": [{"text", "count"}]}: the most agreed
    facts that fit the screen, and N, the smallest of their counts, so „მინიმუმ N“ is true of each. None when
    fewer than 2 facts are in `minimum` members."""
    rows = [m if isinstance(m, dict) else {"outlet": str(i), "text": m} for i, m in enumerate(members or [])]
    facts_ = [x for x in agreed(rows, minimum) if len(x["text"]) <= AGREE_TEXT][:most]
    if len(facts_) < 2:
        return None
    return {"n": min(x["count"] for x in facts_), "total": len({m.get("outlet") for m in rows}),
            "items": [{"text": x["text"], "count": x["count"]} for x in facts_]}


def fill_agree(story, members, minimum=AGREE_MIN):
    """Code fills every agree scene of a story (its items, n and total) from the members; the writer's own items
    are dropped (they are data, like sources). -> the problems (a story whose members agree on too little)."""
    out = []
    for i, s in enumerate(story.get("scenes") or []):
        if s.get("type") != "agree":
            continue
        made = agree_scene(members, minimum)
        if not made:
            out.append(f"scene {i} (agree): fewer than 2 facts are literally in {minimum} member articles")
            continue
        s.update(made)
    return out


# ---------------------------------------------------------------- the episode counter and the stored state

SCHEMA = """
create table if not exists rubric_episodes(brand text, rubric text, key text, episode integer, state text, ts text,
  primary key(brand, rubric, key));
create table if not exists rubric_state(brand text, cluster text, part integer, outlets text, numbers text,
  quotes text, story text, ts text, primary key(brand, cluster, part));
"""


@contextlib.contextmanager
def _db():
    con = sqlite3.connect(store.home() / "veasy.db", timeout=30)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        with con:
            yield con
    finally:
        con.close()


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def reserve(brand, rubric, key):
    """The episode of one story of a rubric for a brand: the one it already has, else the next (the highest so far
    + 1). Idempotent per (brand, rubric, key)."""
    get(rubric)
    with _db() as con:
        old = con.execute("select episode from rubric_episodes where brand=? and rubric=? and key=?",
                          (brand, rubric, str(key))).fetchone()
        if old:
            return old["episode"]
        top = con.execute("select max(episode) m from rubric_episodes where brand=? and rubric=?",
                          (brand, rubric)).fetchone()["m"] or 0
        con.execute("insert into rubric_episodes(brand, rubric, key, episode, state, ts) values(?,?,?,?,?,?)",
                    (brand, rubric, str(key), top + 1, "reserved", _now()))
        return top + 1


def finish(brand, rubric, key):
    """The video of this episode ended done: its number is used."""
    with _db() as con:
        con.execute("update rubric_episodes set state='done', ts=? where brand=? and rubric=? and key=?",
                    (_now(), brand, rubric, str(key)))


def release(brand, rubric, key):
    """The job of this episode failed or was cancelled: the number goes back when no later episode exists (else it
    stays unused: a gap, never a number twice). A done episode is never released."""
    with _db() as con:
        row = con.execute("select episode, state from rubric_episodes where brand=? and rubric=? and key=?",
                          (brand, rubric, str(key))).fetchone()
        if not row or row["state"] == "done":
            return False
        top = con.execute("select max(episode) m from rubric_episodes where brand=? and rubric=?",
                          (brand, rubric)).fetchone()["m"]
        if row["episode"] == top:
            con.execute("delete from rubric_episodes where brand=? and rubric=? and key=?", (brand, rubric, str(key)))
        else:
            con.execute("update rubric_episodes set state='void', ts=? where brand=? and rubric=? and key=?",
                        (_now(), brand, rubric, str(key)))
        return True


def episodes(brand):
    """{rubric: {"last": the highest episode, "done": how many ended done}} for a brand."""
    with _db() as con:
        rows = con.execute("select rubric, max(episode) last, sum(state='done') done from rubric_episodes "
                           "where brand=? group by rubric", (brand,)).fetchall()
    return {r["rubric"]: {"last": r["last"], "done": r["done"] or 0} for r in rows}


def _quotes(texts):
    from tt_shorts import directors
    return [m.group(1).strip() for t in texts for m in directors.QUOTE.finditer(t or "")
            if len(m.group(1).split()) >= 4]


def state_of(story, articles):
    """What a video of a cluster had: its outlets, the stated quantities and the quotes of its articles."""
    from tt_shorts import directors
    found = directors.facts(articles or [], story.get("category", ""))["found"]
    return {"outlets": list(story.get("sources") or []), "numbers": _quantities(found),
            "quotes": [news_check.flat(q) for q in _quotes(articles or [])]}


def remember(brand, story, articles, story_path=""):
    """Store what a done news video of a cluster had (part 1, or its part), for growth() later."""
    st = state_of(story, articles)
    with _db() as con:
        con.execute("insert or replace into rubric_state(brand, cluster, part, outlets, numbers, quotes, story, ts) "
                    "values(?,?,?,?,?,?,?,?)",
                    (brand, str(story["id"]), int(story.get("part") or 1), json.dumps(st["outlets"], ensure_ascii=False),
                     json.dumps(st["numbers"]), json.dumps(st["quotes"], ensure_ascii=False), str(story_path), _now()))
    return st


def last_state(brand, cluster):
    with _db() as con:
        r = con.execute("select * from rubric_state where brand=? and cluster=? order by part desc limit 1",
                        (brand, str(cluster))).fetchone()
    if not r:
        return None
    return {"part": r["part"], "outlets": json.loads(r["outlets"]), "numbers": json.loads(r["numbers"]),
            "quotes": json.loads(r["quotes"]), "story": r["story"], "ts": r["ts"]}


def compare(before, now):
    """Pure: what a cluster gained since a stored state. before: state_of() of the last video (or None), now: the
    same of the cluster today -> {"had_video", "part" (the next part), "new_outlets", "new_numbers", "new_quotes"}."""
    if not before:
        return {"had_video": False, "part": 1, "new_outlets": [], "new_numbers": [], "new_quotes": []}
    had_o, had_n, had_q = set(before["outlets"]), set(before["numbers"]), set(before["quotes"])
    return {"had_video": True, "part": int(before.get("part") or 1) + 1,
            "new_outlets": [o for o in now["outlets"] if o not in had_o],
            "new_numbers": [n for n in now["numbers"] if n not in had_n],
            "new_quotes": [q for q in now["quotes"] if q not in had_q]}


def growth(brand, data):
    """compare() of a cluster's data now against its last stored video."""
    cluster = data.get("cluster") or {}
    now = state_of({"sources": cluster.get("sources") or []}, data.get("articles") or [])
    return compare(last_state(brand, cluster.get("id")), now)


# ---------------------------------------------------------------- the story's code-owned fields

OWNED = ("rubric", "episode", "part")  # never the writer's (writer.write drops them, like date and director)


def n_of(story, r=None):
    """The count in a label with "{n}": the agree scene's n, or the digest's stories."""
    r = r or get(story["rubric"])
    if r["count"] == "agree":
        return next((s.get("n") for s in story.get("scenes") or [] if s.get("type") == "agree"), None)
    if r["count"] == "stories":
        return len((story.get("digest") or {}).get("stories") or [])
    return None


def label_of(r, n=None):
    return r["label"].replace("{n}", str(n)) if r["count"] else r["label"]


def chip(story, b=None):
    """The hook's chip, by code: „დღის ციფრი · #12“, „ამბავი გრძელდება · ნაწ. 2“; None without a rubric."""
    if not story.get("rubric"):
        return None
    try:
        r = get(story["rubric"])
    except RubricError:
        return None
    label = label_of(r, n_of(story, r))
    if r["numbering"] == "part":
        return f"{label} · ნაწ. {story.get('part') or 1}"
    return f"{label} · #{story['episode']}" if story.get("episode") else label


def stamp(story, rubric, brand, key, part=None):
    """Code sets the rubric, its episode (reserved, idempotent per key) and, for a part rubric, the part."""
    r = get(rubric)
    story["rubric"] = r["id"]
    story["episode"] = reserve(brand, r["id"], key)
    if r["numbering"] == "part":
        story["part"] = int(part or story.get("part") or 2)
    else:
        story.pop("part", None)
    return story


def key_of(story):
    """The key an episode is reserved under: the story id (and its part)."""
    return f"{story['id']}" + (f"-part{story['part']}" if story.get("part") else "")


def _match(seq, shape):
    """True when the scene type sequence fits the shape (small: backtracking over the slots)."""
    @functools.lru_cache(maxsize=None)
    def go(i, j):
        if j == len(shape):
            return i == len(seq)
        s = shape[j]
        lo, hi = s.get("min", 1), s.get("max", s.get("min", 1))
        ok = (lambda t: t not in NOT_ANY) if s["types"] == "any" else (lambda t: t in s["types"])  # noqa: E731
        k = 0
        while True:
            if k >= lo and go(i + k, j + 1):
                return True
            if k == hi or i + k >= len(seq) or not ok(seq[i + k]):
                return False
            k += 1
    return go(0, 0)


def shape_text(r):
    parts = []
    for s in r["shape"]:
        t = "any scene" if s["types"] == "any" else "/".join(s["types"])
        lo, hi = s.get("min", 1), s.get("max", s.get("min", 1))
        parts.append(t if (lo, hi) == (1, 1) else f"{lo}-{hi} x {t}")
    return " -> ".join(parts)


def story_problems(story):
    """A story's rubric fields (code-owned) and its shape. A story without a rubric has none of them."""
    if "rubric" not in story:
        return [f"story: {k!r} without a rubric (code sets it with the rubric)" for k in OWNED if k in story]
    try:
        r = get(story["rubric"])
    except RubricError as e:
        return [f"story: {e}; the rubric is set by code, never by the writer"]
    out = []
    ep = story.get("episode")
    if not (isinstance(ep, int) and not isinstance(ep, bool) and ep >= 1):
        out.append("story: a rubric's episode is a number code reserves (engine rubrics stamp), not the writer's")
    if r["numbering"] == "part" and not (isinstance(story.get("part"), int) and story["part"] >= 2):
        out.append(f"story: rubric {r['id']} needs its part (2 or more), set by code from the stored state")
    if programs_name(story) != r["program"]:
        out.append(f"story: rubric {r['id']} is a {r['program']} rubric, the story is {programs_name(story)}")
    seq = [s.get("type") for s in story.get("scenes") or []]
    if not _match(seq, r["shape"]):
        out.append(f"rubric {r['id']}: the scenes {' -> '.join(map(str, seq))} don't fit its shape {shape_text(r)}")
    for g in r["needs"]:
        if not set(g) & set(seq):
            out.append(f"rubric {r['id']}: needs a {' or '.join(g)} scene")
    if r["count"] and not n_of(story, r):
        out.append(f"rubric {r['id']}: its label's count ({r['count']}) is missing")
    return out


def programs_name(story):
    from tt_shorts import programs
    return programs.name_of(story)


def length_problems(story):
    """The narration's estimated length inside the rubric's format window (a news rubric has its own: number is
    20-25 s), so a long script goes back to the writer."""
    from tt_shorts import formats, speech
    if not story.get("rubric"):
        return []
    try:
        r = get(story["rubric"])
    except RubricError:
        return []
    fmt = formats.get(r["format"])
    try:
        secs = speech.scene_frames(story, speech.estimate_words(story.get("narration", "")))[-1] / speech.FPS
    except (ValueError, RuntimeError, IndexError):
        return []
    if fmt["min_seconds"] <= secs <= fmt["max_seconds"]:
        return []
    side = "shorten" if secs > fmt["max_seconds"] else "lengthen"
    return [f"timing: about {secs:.0f}s, rubric {r['id']} wants {fmt['min_seconds']}-{fmt['max_seconds']}s "
            f"({r['format']}): {side} the narration (~0.75 s per word)"]


def gate_problems(story, grown=None):
    """After writing, the rubric's own gates on the facts: continues says at least one thing part 1 didn't have."""
    if story.get("rubric") != "continues" or not grown:
        return []
    said = news_check.flat(story.get("narration", "") + " " + news_check.screen_text(story))
    new = list(grown.get("new_numbers") or []) + [q[:40] for q in grown.get("new_quotes") or []]
    if new and not any(re.search(rf"(?<!\d){re.escape(x)}(?!\d)", said) for x in new):
        return [f"rubric continues: say at least one thing part {grown['part'] - 1} didn't have: {', '.join(new[:5])}"]
    return []


# ---------------------------------------------------------------- the writer's part, options


def brief_block(r, f=None, grown=None):
    """The rubric's lines in the writer's prompt (after the director's; where they differ, the rubric wins)."""
    lines = [f"Rubric (code chose it; follow it): {r['id']} „{label_of(r, (f or {}).get('agreed_n') or 'N')}“. "
             f"Scene shape: {shape_text(r)}."]
    lines += [f"- {x}" for x in r["brief"]]
    if grown and grown.get("had_video"):
        new = grown.get("new_numbers", [])[:6] + [f"„{q[:80]}“" for q in grown.get("new_quotes", [])[:3]]
        lines.append(f"- Part {grown['part'] - 1} already told the story. New since then: "
                     f"{len(grown.get('new_outlets') or [])} more outlets; new facts: {', '.join(new) or '-'}.")
    if f and r["id"] == "agree" and f.get("agreed_n"):
        lines.append(f"- The agree scene's facts and count are filled by code; its part of the narration says "
                     f"„მინიმუმ {f['agreed_n']}“ in words, never which outlets, never their side.")
    return "\n".join(lines) + "\n\n"


def summary(r):
    return {k: r[k] for k in ("label", "about", "numbering", "count", "program", "format", "slot", "eligible",
                              "never", "needs")} | {"shape": shape_text(r)}


def options():
    """What `engine options` shows an agent."""
    return {"about": "named recurring shows (rubrics/<id>.json): a chip in the hook „<label> · #<episode>“, a "
                     "scene shape, a time slot, eligibility on facts code finds. write/queue add --rubric <id>; "
                     "ops/daily.py --rubrics assigns them; engine rubrics facts --source --ref shows which a cluster "
                     "may be",
            "agree_min": AGREE_MIN, "facts": list(FACTS + FLAGS),
            "rubrics": {n: summary(r) for n, r in sorted(load_all().items())}}


# ---------------------------------------------------------------- the day's assignment (ops/daily.py --rubrics)

ASSIGN_ORDER = ("continues", "agree", "number", "changes")  # the rarest first, so it isn't taken by a commoner one


def assign(candidates):
    """Pure: [(story id, facts, allowed rubric ids or None)] -> {story id: rubric}. Each rubric at most once a day,
    each story at most one; the candidates come in the day's order (the best first), so a rubric goes to the first
    story it fits. allowed: a cluster that already had its video may only continue."""
    out, taken = {}, set()
    every = load_all()
    for rid in ASSIGN_ORDER:
        r = every.get(rid)
        if not r or r["program"] != "news":
            continue
        for sid, f, allowed in candidates:
            if sid in out or rid in taken or (allowed is not None and rid not in allowed):
                continue
            if holds(r, f):
                out[sid] = rid
                taken.add(rid)
    return out
