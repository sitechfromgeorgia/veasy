"""Variety: so 1000 videos don't look and sound the same (owner, 2026-11-02: "imagine 1000 videos, 90% the same style,
no creativity, nothing new").

Inside one brand and one look, each video gets its own combination of:
    hook        stack | lead | blocks | underline      how the opening lines are set
    motif       grid | diagonal | dots | rules | plain the background's texture; "icons" (the story's main icon
                | icons                                tiled, icons.story_icon) only when the story has one
    enter       rise | slide | reveal | scale          how things come on screen
    transition  the cut between scenes, from the ones that suit the look (when the format says "auto")
    music       one of the family's loops (tools/compose_music.py writes several per family)

Each choice is the least used one among the brand's last RECENT videos (ties broken by the story id), so a run of
videos keeps moving through the options instead of repeating; one story always gets the same picks again (a
re-render in another caption design looks the same). Everything stays inside the brand pack: these change layout
and motion, never the palette.

The history is a table in $VEASY_HOME/veasy.db. recent_sequences() gives the writer the scene orders used lately,
so it can choose a different shape for the next story.
"""
import contextlib
import datetime as dt
import json
import sqlite3
import zlib

from tt_shorts import store

OPTIONS = {
    "hook": ("stack", "lead", "blocks", "underline"),
    "motif": ("grid", "diagonal", "dots", "rules", "plain", "icons"),
    "enter": ("rise", "slide", "reveal", "scale"),
}
NEEDS_ICON = {"motif": ("icons",)}  # options a story without a main icon can't use
# the cuts that suit each look when the format leaves the transition to the engine ("auto")
TRANSITIONS = {
    "editorial": ("line", "wipe", "dot", "slide"),
    "kinetic": ("panel", "push", "wipe", "cut"),
    "cards": ("line", "slide", "dot", "wipe"),
}
RECENT = 20

SCHEMA = """
create table if not exists variety(
  ts text, brand text, story text, look text, hook text, motif text, enter text, transition text, music text,
  scenes text);
create index if not exists variety_brand on variety(brand, ts);
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


def history(brand, n=RECENT):
    with _db() as con:
        return [dict(r) for r in con.execute("select * from variety where brand=? order by ts desc, rowid desc limit ?",
                                             (brand, n))]


def _least_used(options, used, story, key):
    counts = {o: used.count(o) for o in options}
    low = min(counts.values())
    pool = [o for o in options if counts[o] == low]
    return pool[zlib.crc32(f"{story}|{key}".encode()) % len(pool)]


def options_for(key, icon=False):
    """A choice's options for one story: without a main icon, the icon motif is not one of them."""
    return OPTIONS[key] if icon else tuple(o for o in OPTIONS[key] if o not in NEEDS_ICON.get(key, ()))


def pick(brand, story, look, transition="auto", loops=(), icon=False):
    """The style for one video: {hook, motif, enter, transition, music}. A story rendered before in this look gets its
    earlier picks back; otherwise each choice is the least used lately. transition stays as given unless "auto";
    music is None when there are no loops. icon: the story has a main icon (icons.story_icon), so the "icons" motif
    is one of its options."""
    past = history(brand)
    same = next((r for r in past if r["story"] == str(story) and r["look"] == look), None)
    out = {}
    for key in OPTIONS:
        options = options_for(key, icon)
        out[key] = same[key] if same and same[key] in options else _least_used(options, [r[key] for r in past], story, key)
    if transition in (None, "auto"):
        options = TRANSITIONS[look]
        out["transition"] = same["transition"] if same and same["transition"] in options else \
            _least_used(options, [r["transition"] for r in past], story, "transition")
    else:
        out["transition"] = transition
    names = [getattr(p, "name", str(p)) for p in loops]
    if names:
        out["music"] = same["music"] if same and same["music"] in names else \
            _least_used(names, [r["music"] for r in past], story, "music")
    else:
        out["music"] = None
    return out


def record(brand, story, look, style, scenes):
    """Remember what a finished render used (engine.render_story calls this)."""
    with _db() as con:
        con.execute("insert into variety values(?,?,?,?,?,?,?,?,?,?)",
                    (dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), brand, str(story), look,
                     style.get("hook"), style.get("motif"), style.get("enter"), style.get("transition"),
                     style.get("music"), json.dumps(list(scenes))))


def recent_sequences(brand, n=12):
    """The scene orders of the brand's last n videos, most frequent first: ["hook>stat>where>end x4", ...]."""
    seqs = []
    for r in history(brand, n):
        try:
            seqs.append(">".join(json.loads(r["scenes"] or "[]")))
        except ValueError:
            continue
    counted = sorted({s: seqs.count(s) for s in seqs if s}.items(), key=lambda kv: -kv[1])
    return [f"{s} x{c}" if c > 1 else s for s, c in counted]


def report(brand, n=50):
    """How varied the last n videos were: per choice, how often the most used option came up (for the daily report)."""
    past = history(brand, n)
    if not past:
        return {}
    out = {}
    for key in ("hook", "motif", "enter", "transition", "music", "scenes"):
        vals = [r[key] for r in past]
        top = max(set(vals), key=vals.count)
        out[key] = {"distinct": len(set(vals)), "most_used_share": round(vals.count(top) / len(vals), 2)}
    return out
