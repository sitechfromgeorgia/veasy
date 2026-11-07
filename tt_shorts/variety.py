"""Variety: so 1000 videos don't look and sound the same (owner, 2026-11-02: "imagine 1000 videos, 90% the same style,
no creativity, nothing new").

Inside one brand and one look, each video gets its own combination of:
    hook        stack | lead | blocks | underline      how the opening lines are set
    motif       grid | diagonal | dots | rules | plain the background's texture; "icons" (the story's main icon
                | icons                                tiled, icons.story_icon) only when the story has one
    enter       rise | slide | reveal | scale          how things come on screen
    transition  the cut between scenes, from the ones that suit the look (when the format says "auto")
    music       one of the family's loops (tools/compose_music.py writes several per family)

and, when the format says `theme: auto`, the theme: one of the pack's allowed palettes (brand.json "themes"; a
director may narrow them with its "themes"), least used the same way, a re-render keeping its own (pick_theme). The
theme is not in the novelty guard's fingerprint: a pack with one theme, or a format that names one, would otherwise
make every pair of its videos look one field closer.

Each choice is the least used one among the brand's last RECENT videos (ties broken by the story id), so a run of
videos keeps moving through the options instead of repeating; one story always gets the same picks again (a
re-render in another caption design looks the same). Everything stays inside the brand pack: these change layout
and motion, never the palette.

The novelty guard (ROADMAP D11). Least used per choice still lets two videos match on almost everything: the same
director, the same scene order and three of the five style picks. So a planned video has a fingerprint
    (director, scenes, hook, motif, enter, transition, music)
and similarity(a, b) is a weighted count of the fields two fingerprints share (WEIGHTS: 1 each, so 0-7). Each of
the six single fields counts when equal (two videos without a director, or without music, share that field); the
scene sequence counts as its difflib ratio, 0-1 (identical orders 1; hook>stat>end against hook>stat>where>end
0.86). distance(a, b) = 1 - similarity / 7. A plan is too close when it shares TOO_CLOSE = 5 or more of the 7 with
any of the brand's last RECENT videos (the story's own earlier renders don't count).

Then choose() re-rolls, before any voice is paid for: props.build calls it ahead of speech.voice, so `render`, the
queue, `still` and `probe` all pass through it. The re-rolls are the other combinations of the style picks inside
the director's subsets, cheapest first: a combination costs how far each of its picks is above that choice's least
used option, so the run stays as even as it can. The director and the scenes belong to the story and never change,
nor does a format's fixed transition. The first re-roll that is no longer too close is taken; at most REROLLS are
tried, all deterministic per story and history (ties by crc32 of the story id and the combination), so a probe and
the render after it agree. If none is far enough, the farthest plan is taken (the earliest of equals) with a
warning: the guard never fails a video. A re-render (the story's own row in this look, under this director) gets
its stored picks back without a re-roll.

fingerprint, similarity, distance, nearest and spread are pure; assess() measures any style against the brand's
history without re-rolling (for `engine plan`).

A film an agent composed (compose.py) has none of the kit's picks, so two of them would match on every empty field.
assess_composed() compares such a film only with the brand's other composed films and only on what one has
(COMPOSED_FIELDS: its template, its scene kinds, its opening scene, the ease its scenes use most, its music loop),
too close at COMPOSED_CLOSE. It only warns: the film is the agent's to change, nothing re-rolls it.

The history is a table in $VEASY_HOME/veasy.db: each finished render's picks (the fingerprint's columns), and since
the guard its distance to the nearest recent video and the re-rolls it took (MIGRATIONS adds the columns to an
older database). recent_sequences() gives the writer the scene orders used lately, so it can choose a different
shape for the next story; report() measures how alike the last videos were.
"""
import contextlib
import datetime as dt
import difflib
import itertools
import json
import sqlite3
import zlib

from tt_shorts import store

OPTIONS = {
    "hook": ("stack", "lead", "blocks", "underline", "split", "badge", "bracket", "rail"),
    "motif": ("grid", "diagonal", "dots", "rules", "plain", "icons", "crosses", "mesh", "waves", "hash"),
    "enter": ("rise", "slide", "reveal", "scale", "drop", "expand", "drift", "flip"),
}
NEEDS_ICON = {"motif": ("icons",)}  # options a story without a main icon can't use
# the cuts that suit each look when the format leaves the transition to the engine ("auto")
TRANSITIONS = {
    "editorial": ("line", "wipe", "dot", "slide", "meter", "fade", "shutter", "iris"),
    "kinetic": ("panel", "push", "wipe", "cut", "meter", "split", "corner", "shutter", "blind"),
    "cards": ("line", "slide", "dot", "wipe", "fade", "split", "iris"),
}
RECENT = 20

# the novelty guard: the fingerprint's fields, their weights in similarity(), the threshold and the bound
FIELDS = ("director", "scenes", "hook", "motif", "enter", "transition", "music")
WEIGHTS = {k: 1.0 for k in FIELDS}
TOO_CLOSE = 5.0  # similarity at or above this to one of the last RECENT videos: re-roll ("5 of 7")
REROLLS = 64  # at most this many re-rolls per plan
# a composed film (compose.film_style): the fields it has, and the kit's share of them (5 of 7) as its threshold
COMPOSED = "composed"  # its look in the history
COMPOSED_FIELDS = ("template", "scenes", "hook", "enter", "music")
COMPOSED_CLOSE = 3.5

SCHEMA = """
create table if not exists variety(
  ts text, brand text, story text, look text, hook text, motif text, enter text, transition text, music text,
  scenes text);
create index if not exists variety_brand on variety(brand, ts);
create table if not exists concepts(
  ts text, brand text, story text, family text, object text, device text, rung integer, idea text);
create index if not exists concepts_brand on concepts(brand, ts);
create table if not exists plate_use(ts text, brand text, story text, scene integer, hash text, layout text);
create index if not exists plate_use_brand on plate_use(brand, ts);
"""
MIGRATIONS = {  # columns added since the table was first made; an older veasy.db gets them on first use
    "director": "alter table variety add column director text",  # directors.py, before writing
    "novelty": "alter table variety add column novelty real",  # the guard: distance to the nearest recent video
    "rerolls": "alter table variety add column rerolls integer",  # the guard: the re-rolls it took
    "theme": "alter table variety add column theme text",  # the pack's theme the video was drawn in (themes)
    "template": "alter table variety add column template text",  # a composed film's template (compose.py)
    "style": "alter table variety add column style text",  # named film style (styles.py)
}


@contextlib.contextmanager
def _db():
    con = sqlite3.connect(store.home() / "veasy.db", timeout=30)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        have = {r[1] for r in con.execute("pragma table_info(variety)")}
        for col, sql in MIGRATIONS.items():
            if col not in have:
                con.execute(sql)
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


def _within(options, subset):
    """A director's subset of a choice's options (all of them when it names none that fit)."""
    inside = tuple(o for o in options if o in (subset or ()))
    return inside or tuple(options)


def direct(brand, story, facts, program_scenes="all", forced=None):
    """The director of one story, before it is written (directors.py): forced, else the one this story had, else the
    least used eligible one among the brand's last RECENT videos (ties by the story id). None when none is eligible."""
    from tt_shorts import directors
    if forced:
        return directors.get(forced)["id"]  # an unknown one is refused
    pool = directors.eligible(facts, program_scenes)
    if not pool:
        return None
    past = history(brand)
    same = next((r["director"] for r in past if r["story"] == str(story) and r["director"] in pool), None)
    return same or _least_used(pool, [r["director"] for r in past], story, "director")


PLATE_LAYOUTS = ("top", "mid", "low")  # where the plate scene's card sits: one more option, never a replacement


def _plate_rows(brand, n=RECENT * 3):
    with _db() as con:
        return [dict(r) for r in con.execute("select * from plate_use where brand=? order by ts desc, rowid desc limit ?",
                                             (brand, n))]


def pick_plate(brand, story, hashes):
    """One baked plate of `hashes` for a story: the one it had before if still there, else the least used lately by the
    brand (ties by the story id). Reads only: a queue job never bakes, it picks from the shelf. None: an empty shelf."""
    if not hashes:
        return None
    rows = _plate_rows(brand)
    same = next((r["hash"] for r in rows if r["story"] == str(story) and r["hash"] in hashes), None)
    return same or _least_used(list(hashes), [r["hash"] for r in rows], story, "plate")


def pick_plate_layout(brand, story, scene=0, allowed=None):
    """Where a plate scene's card sits: the one it had before if still allowed, else the least used lately by the brand
    among `allowed` (the layouts that leave the plate's anchor uncovered; default all)."""
    pool = [x for x in PLATE_LAYOUTS if allowed is None or x in allowed] or list(PLATE_LAYOUTS)
    rows = _plate_rows(brand)
    same = next((r["layout"] for r in rows if r["story"] == str(story) and r["scene"] == scene and r["layout"] in pool), None)
    return same or _least_used(pool, [r["layout"] for r in rows], f"{story}|{scene}", "plate-layout")


def record_plate(brand, story, scene, hash16, layout):
    """Remember a plate use (once per story and scene: a re-resolve replaces its row)."""
    with _db() as con:
        con.execute("delete from plate_use where brand=? and story=? and scene=?", (brand, str(story), scene))
        con.execute("insert into plate_use(ts, brand, story, scene, hash, layout) values(?,?,?,?,?,?)",
                    (dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), brand, str(story), scene, hash16,
                     layout))


def pick_theme(brand, story, themes, subset=None):
    """The theme of one video when the format says `theme: auto`: one of `themes` (the pack's allowed ones, in its
    order), inside a director's `subset` when it names any that the pack has; the one this story had before if it
    is still one of them, else the least used among the brand's last RECENT videos (ties by the story id). A pack
    with one allowed theme always gets it. Records nothing (record() does, after a render)."""
    pool = _within(tuple(themes), subset)
    if len(pool) == 1:
        return pool[0]
    past = history(brand)
    same = next((r.get("theme") for r in past if r["story"] == str(story) and r.get("theme") in pool), None)
    return same or _least_used(pool, [r.get("theme") for r in past], story, "theme")


# ---------------------------------------------------------------- the novelty guard (pure)


def _scenes(v):
    if isinstance(v, str):  # a history row keeps them as JSON
        try:
            v = json.loads(v or "[]")
        except ValueError:
            v = []
    return tuple(v) if v is not None else None


def fingerprint(style, scenes=None, director=None):
    """A planned or recorded video as the guard compares it: {director, scenes (a tuple of scene types; None when
    not known), hook, motif, enter, transition, music}, plus "story" when style has one, and "style" (the named
    film style) when specified. style: pick()'s dict, props.style or a history row (whose "scenes" is JSON)."""
    st = style or {}
    out = {"director": director if director is not None else st.get("director"),
           "scenes": _scenes(scenes if scenes is not None else st.get("scenes")),
           **{k: st.get(k) for k in ("hook", "motif", "enter", "transition", "music")}}
    if st.get("story") is not None:
        out["story"] = str(st["story"])
    if st.get("template"):
        out["template"] = st["template"]
    film_style = st.get("style_slug") or (st.get("style") if isinstance(st.get("style"), str) else None)
    if film_style:
        out["style"] = film_style
    return out


def similarity(a, b, fields=FIELDS):
    """How much two fingerprints share, 0-7 (WEIGHTS): each single field when equal, the scene orders as their
    difflib ratio (nothing when either is unknown). When named film styles are present in both, they add +1.0.
    fields: the fields compared (COMPOSED_FIELDS for composed films; "template" counts only when both have one)."""
    out = 0.0
    for k in fields:
        if k == "scenes":
            if a.get(k) is not None and b.get(k) is not None:
                out += WEIGHTS[k] * difflib.SequenceMatcher(None, list(a[k]), list(b[k]), autojunk=False).ratio()
        elif k == "template":
            out += 1.0 if a.get(k) and a.get(k) == b.get(k) else 0.0
        elif a.get(k) == b.get(k):
            out += WEIGHTS[k]
    if a.get("style") is not None and b.get("style") is not None and a["style"] == b["style"]:
        out += WEIGHTS.get("style", 1.0)
    return round(out, 3)


def distance(a, b):
    """1 - similarity / the sum of the weights: 0 for the same video, 1 for nothing shared."""
    return round(1 - similarity(a, b) / sum(WEIGHTS.values()), 3)


def too_close(a, b):
    return similarity(a, b) >= TOO_CLOSE


def nearest(fp, past, fields=FIELDS):
    """(similarity, the nearest fingerprint) of fp against past fingerprints, newest first; the newest wins a tie.
    (0.0, None) when past is empty."""
    best, near = 0.0, None
    for other in past:
        s = similarity(fp, other, fields)
        if near is None or s > best:
            best, near = s, other
    return best, near


def _others(rows, story):
    """History rows as fingerprints, without this story's own renders."""
    return [fingerprint(r) for r in rows if str(r["story"]) != str(story)]


def _report(sim, near, rerolls=0, kept=False, warning=None, total=None, close=TOO_CLOSE):
    return {"similarity": sim, "distance": round(1 - sim / (total or sum(WEIGHTS.values())), 3),
            "nearest": (near or {}).get("story"), "too_close": sim >= close, "rerolls": rerolls, "kept": kept,
            "warning": warning}


def spread(rows, window=RECENT, count=None):
    """How far apart a run of videos is (history rows, newest first): each of the newest `count` (default all)
    videos' distance to the nearest of the `window` videos before it (other stories), averaged, the smallest, and
    how many were too close. None when no video has one before it."""
    fps = [fingerprint(r) for r in rows]
    dists, close = [], 0
    for i, fp in enumerate(fps[:count]):
        before = [x for x in fps[i + 1:i + 1 + window] if x.get("story") != fp.get("story")]
        if not before:
            continue
        sim, _ = nearest(fp, before)
        dists.append(1 - sim / sum(WEIGHTS.values()))
        close += sim >= TOO_CLOSE
    if not dists:
        return None
    return {"mean_distance": round(sum(dists) / len(dists), 3), "min_distance": round(min(dists), 3),
            "too_close": close, "videos": len(dists)}


def assess(brand, story, style, scenes=None):
    """How close a style (and scene order) is to the brand's last RECENT videos, without re-rolling:
    {similarity, distance, nearest (a story id), too_close, rerolls 0, kept False, warning None}."""
    return _report(*nearest(fingerprint(style, scenes), _others(history(brand), story)))


def assess_composed(brand, story, style, scenes):
    """assess() for a film an agent composed: against the brand's other composed films among its last RECENT videos, on
    COMPOSED_FIELDS. style, scenes: compose.film_style()'s. It warns and re-rolls nothing."""
    past = [fingerprint(r) for r in history(brand) if r.get("look") == COMPOSED and str(r["story"]) != str(story)]
    sim, near = nearest(fingerprint(style, scenes), past, COMPOSED_FIELDS)
    warning = None
    if sim >= COMPOSED_CLOSE:
        warning = (f"novelty: this film shares {sim:g} of {len(COMPOSED_FIELDS)} with story {near.get('story')} "
                   f"(too close at {COMPOSED_CLOSE:g}: scene kinds, opening scene, main ease, template, music)")
    return _report(sim, near, warning=warning, total=len(COMPOSED_FIELDS), close=COMPOSED_CLOSE)


# ---------------------------------------------------------------- picking


def _rerolls(first, options, used, story, n=None):
    """The guard's re-rolls of a plan, at most n (REROLLS): every other combination of the options, cheapest first.
    A combination's cost is how far above the least used each of its picks is (sum over the choices of the
    option's count minus the choice's lowest count), so a re-roll keeps the run as even as it can; ties go by crc32
    of the story id and the combination, so they are the same on every call."""
    keys = list(options)
    cost = {k: {o: used[k].count(o) - min(used[k].count(x) for x in options[k]) for o in options[k]} for k in keys}
    combos = [dict(zip(keys, c)) for c in itertools.product(*(options[k] for k in keys))]
    combos = [c for c in combos if any(c[k] != first[k] for k in keys)]
    combos.sort(key=lambda c: (sum(cost[k][c[k]] for k in keys),
                               zlib.crc32(f"{story}|{'|'.join(str(c[k]) for k in keys)}".encode())))
    return [{**first, **c} for c in combos[:REROLLS if n is None else n]]


def choose(brand, story, look, transition="auto", loops=(), icon=False, director=None, scenes=None):
    """-> (style, novelty). style is pick()'s dict. novelty is the guard's report: assess()'s keys, with rerolls (how
    many were tried), kept (a re-render's stored picks) and warning (no re-roll was far enough; the farthest was taken).
    scenes: the scene types the video shows (part of the fingerprint)."""
    past = history(brand)
    did = director["id"] if director else None
    same = next((r for r in past if r["story"] == str(story) and r["look"] == look and r["director"] == did), None)
    sub = {"hook": "hooks", "motif": "motifs", "enter": "enters"}
    options = {}
    for key in OPTIONS:
        options[key] = options_for(key, icon)
        if director:
            options[key] = _within(options[key], director[sub[key]])
    if transition in (None, "auto"):
        options["transition"] = TRANSITIONS[look] if not director else \
            tuple(t for t in TRANSITIONS[look] if t in director["transitions"]) or tuple(director["transitions"])
    names = [getattr(p, "name", str(p)) for p in loops]
    if names:
        options["music"] = tuple(names)
    used = {key: [r[key] for r in past] for key in options}
    out = {key: same[key] if same and same[key] in options[key] else _least_used(options[key], used[key], story, key)
           for key in options}
    out.setdefault("transition", transition)
    out.setdefault("music", None)
    out = {k: out[k] for k in ("hook", "motif", "enter", "transition", "music")}
    others = _others(past, story)
    fp = lambda st: fingerprint(st, scenes, did)  # noqa: E731
    sim, near = nearest(fp(out), others)
    if same:  # a re-render keeps its picks
        return out, _report(sim, near, kept=True)
    best, k = (sim, 0, out, near), 0
    for cand in _rerolls(out, options, used, story) if sim >= TOO_CLOSE else ():
        k += 1
        s, n = nearest(fp(cand), others)
        if s < best[0]:
            best = (s, k, cand, n)
        if s < TOO_CLOSE:
            break
    sim, _, out, near = best
    warning = None
    if sim >= TOO_CLOSE:
        warning = (f"novelty: after {k} re-roll(s) the plan still shares {sim:g} of {sum(WEIGHTS.values()):g} with "
                   f"story {near.get('story')} (too close at {TOO_CLOSE:g}); took the farthest")
    return out, _report(sim, near, k, warning=warning)  # k: the re-rolls tried (the last one is taken unless warned)


def pick(brand, story, look, transition="auto", loops=(), icon=False, director=None, scenes=None):
    """The style for one video: {hook, motif, enter, transition, music}. A story rendered before in this look gets its
    earlier picks back; otherwise each choice is the least used lately, re-rolled by the novelty guard when the plan
    is too close to a recent video (choose()). transition stays as given unless "auto"; music is None when there
    are no loops. icon: the story has a main icon (icons.story_icon), so the "icons" motif is one of its options.
    director: a directors.py director (dict): each choice stays inside its subsets. scenes: the shown scene types."""
    return choose(brand, story, look, transition, loops, icon, director, scenes)[0]


def pick_style(brand_name, story, program="news", family=None, engine=None):
    """The style of one video: rotates eligible styles a brand and program allow, least used first (ties by story id).
    A re-render (this story already having a valid style in history) keeps its own."""
    from tt_shorts import brand as brand_mod, styles
    b = brand_mod.load(brand_name)
    eligible = styles.for_story({"program": program, "family": family, "engine": engine}, brand_pack=b, program=program, engine=engine)
    pool = [s["slug"] for s in eligible]
    if not pool:
        return "swiss-motion"
    if len(pool) == 1:
        return pool[0]
    past = history(brand_name)
    same = next((r.get("style") for r in past if r["story"] == str(story) and r.get("style") in pool), None)
    return same or _least_used(pool, [r.get("style") for r in past], story, "style")


def record(brand, story, look, style, scenes, novelty=None):
    """Remember what a finished render used (engine.render_story and compose.render call this). novelty: choose()'s
    report. A composed film's style carries its template (compose.pick_template: least used first)."""
    nov = novelty or {}
    film_style = style.get("style_slug") or (style.get("style") if isinstance(style.get("style"), str) else None)
    with _db() as con:
        con.execute("insert into variety(ts, brand, story, look, hook, motif, enter, transition, music, scenes, director, "
                    "novelty, rerolls, template, theme, style) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), brand, str(story), look,
                     style.get("hook"), style.get("motif"), style.get("enter"), style.get("transition"),
                     style.get("music"), json.dumps(list(scenes)), style.get("director"), nov.get("distance"),
                     nov.get("rerolls"), style.get("template"), style.get("theme"), film_style))


def record_concept(brand, story, family, concept):
    """A film's idea (concept.py), once per story. Its own table: the fingerprint's thresholds are calibrated."""
    with _db() as con:
        con.execute("delete from concepts where brand=? and story=?", (brand, story))
        con.execute("insert into concepts(ts, brand, story, family, object, device, rung, idea) values(?,?,?,?,?,?,?,?)",
                    (dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), brand, story, family,
                     concept["object"], concept["device"], concept["rung"], concept["idea"]))


def recent_concepts(brand, n=100):
    """The brand's last ideas, newest first."""
    with _db() as con:
        rows = con.execute("select * from concepts where brand=? order by ts desc, rowid desc limit ?", (brand, n))
        return [dict(r) for r in rows.fetchall()]


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
    """How varied the last n videos were: per choice, how often the most used option came up (for the daily report),
    and the guard's view (novelty: spread() of the last n, plus the re-rolls they took)."""
    past = history(brand, n)
    if not past:
        return {}
    out = {}
    for key in ("hook", "motif", "enter", "transition", "music", "scenes", "director", "theme"):
        vals = [r.get(key) for r in past]
        top = max(set(vals), key=vals.count)
        out[key] = {"distinct": len(set(vals)), "most_used_share": round(vals.count(top) / len(vals), 2)}
    names = [r["director"] for r in past]
    out["director"]["share"] = {str(n): round(names.count(n) / len(names), 2) for n in sorted(set(names), key=str)}
    novelty = spread(history(brand, n + RECENT), count=len(past))  # each of the last n against the RECENT before it
    if novelty:
        novelty["rerolls"] = sum(r.get("rerolls") or 0 for r in past)
    out["novelty"] = novelty
    return out
