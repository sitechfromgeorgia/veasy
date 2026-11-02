"""A library of drawings that passed, reused per motif when a new drawing fails (ROADMAP D1).

The writer draws each story's picture (art.py); no person reviews it, so a drawing that still fails art.sanitize or
art.quality after the repairs is dropped and the video goes out without it. Before that, the library is asked for a
drawing of the same motif:
    keep(story, brand)  every drawing of a video that ended `done` (queue.py) and passes sanitize and quality is
                        saved, keyed by its motif: a table `drawings` in $VEASY_HOME/veasy.db (store.py's home, like
                        variety and the queue; no new folder)
    mend(story)         the writer's last step before art.drop_bad: a draw scene whose drawing fails gets a library
                        drawing of the story's motif instead (deterministic per story), with its labels re-checked
    seeds()             assets/drawings/*.json: hand-made line drawings that start the library (tests check that each
                        passes sanitize and quality and names a known icon as its motif)

The motif is an icon name (icons.py: flame for gas, bus, school, scale for a court...): the story's own "motif",
else the icons the draw scene's own words name, else the hook's, else its first sign's or stat's icon. Unlike
icons.story_icon it ignores N10's pictogram ban: a drawing is not a pictogram (a court building for a crime story is
fine; news_check still checks its labels).

Label policy for a reused drawing: a label is kept only when its words are literally in the new story's narration or
its other on-screen texts (after spaces and quote marks are normalised); every other label is removed. A drawing
made for another story must not bring that story's facts (a number, a place, a name) into this one, and a label the
new story itself says can't claim anything new. The fitted drawing must still pass sanitize and quality, and the
writer's full checks (news rules, Georgian) run on the story again after the swap, as after any change.
"""
import contextlib
import datetime as dt
import hashlib
import json
import pathlib
import re
import sqlite3
import xml.etree.ElementTree as ET
import zlib

from tt_shorts import art, icons, ka_check, store

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEEDS = ROOT / "assets" / "drawings"
SCHEMA = """
create table if not exists drawings(
  id text primary key, motif text, svg text, brand text, story text, ts text);
create index if not exists drawings_motif on drawings(motif, ts);
"""
RECENT = 20  # the newest saved drawings per motif that a failing drawing can be swapped for


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


def _id(svg):
    return hashlib.sha256(" ".join(svg.split()).encode("utf-8")).hexdigest()[:16]


def passes(svg):
    """Does a drawing pass art.sanitize and art.quality?"""
    return isinstance(svg, str) and not art.scene_problems(svg)


def seeds():
    """The hand-made drawings in assets/drawings: [{"id", "name", "motif", "svg", "source": "seed"}]."""
    out = []
    for f in sorted(SEEDS.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append({"id": _id(d["svg"]), "name": f.stem, "motif": d["motif"], "svg": d["svg"], "source": "seed",
                    "about": d.get("about", "")})
    return out


def motif_of(story, scene=None):
    """The icon name a story's drawing is filed under, or None (see the module's docstring)."""
    scenes = story.get("scenes") or []
    scene = scene or next((s for s in scenes if s.get("type") == "draw"), {})
    hook = next((s for s in scenes if s.get("type") == "hook"), {})
    candidates = [story.get("motif")] if story.get("motif") else []
    candidates += icons.find(" ".join(str(scene.get(k) or "") for k in ("label", "headline", "kicker")))
    candidates += icons.find(" ".join(str(x) for x in hook.get("lines") or []))
    candidates += [s.get("icon") for s in scenes if s.get("type") in ("sign", "stat") and s.get("icon")]
    return next((n for n in map(icons.resolve, candidates) if n), None)


def keep(story, brand):
    """Save the drawings of a story whose video ended done -> the ids saved (new or already there). A drawing that
    fails the checks, or a story without a motif, saves nothing."""
    saved = []
    for s in story.get("scenes") or []:
        if s.get("type") != "draw" or not passes(s.get("svg")):
            continue
        motif = motif_of(story, s)
        if not motif:
            continue
        did = _id(s["svg"])
        with _db() as con:
            con.execute("insert or ignore into drawings(id, motif, svg, brand, story, ts) values(?,?,?,?,?,?)",
                        (did, motif, s["svg"], brand, str(story.get("id")),
                         dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")))
        saved.append(did)
    return saved


def candidates(motif):
    """Library drawings of one motif: the saved ones (newest first), then the seeds."""
    if not motif:
        return []
    with _db() as con:
        rows = [dict(r, source="done") for r in con.execute(
            "select * from drawings where motif=? order by ts desc, rowid desc limit ?", (motif, RECENT))]
    have = {r["id"] for r in rows}
    return rows + [s for s in seeds() if s["motif"] == motif and s["id"] not in have]


def _norm(text):
    return " ".join(re.sub(r"[„“\"'«»,.:;!?()]", " ", str(text)).lower().split())


def story_text(story):
    """What the new story itself says: its narration and every on-screen text but a drawing's labels."""
    parts = [story.get("narration", "")]
    parts += [t for where, t in ka_check.screen_texts(story) if not where.endswith("svg text")]
    return _norm(" ".join(parts))


def fit(svg, story):
    """A library drawing for a new story -> (svg with only the labels the story says, the labels removed), or
    (None, removed) when what is left fails the checks."""
    said = story_text(story)
    root = ET.fromstring(f"<g>{svg}</g>")
    removed = []

    def strip(el):
        for ch in list(el):
            if ch.tag.split("}")[-1] == "text":
                label = " ".join("".join(ch.itertext()).split())
                if not _norm(label) or f" {_norm(label)} " not in f" {said} ":
                    removed.append(label)
                    el.remove(ch)
            else:
                strip(ch)

    strip(root)
    out = (root.text or "") + "".join(ET.tostring(ch, encoding="unicode") for ch in root)
    return (out, removed) if passes(out) else (None, removed)


def mend(story):
    """(story with each failing drawing swapped for a library one of its motif, [what was swapped]). A drawing with no
    fitting library drawing is left as it was (art.drop_bad drops it next)."""
    scenes, swapped = [], []
    for i, s in enumerate(story.get("scenes") or []):
        if s.get("type") == "draw" and not passes(s.get("svg")):
            motif = motif_of(story, s)
            pool = candidates(motif)
            start = zlib.crc32(f"{story.get('id')}|{motif}".encode()) % len(pool) if pool else 0
            for c in pool[start:] + pool[:start]:  # one story gets the same one again; the next one fits otherwise
                svg, removed = fit(c["svg"], story)
                if svg:
                    s = {**s, "svg": svg}
                    swapped.append({"scene": i, "motif": motif, "drawing": c.get("name") or c["id"],
                                    "source": c["source"], "labels_removed": removed})
                    break
        scenes.append(s)
    return {**story, "scenes": scenes}, swapped
