"""Failure memory: what went wrong lately, so the engine and the writer learn from it (ROADMAP D13).

Every failed check is one row in $VEASY_HOME/veasy.db, table failures (ts, brand, stage, rule, message):
    stage   write (the writer's script failed a check; engine.write_story records every failed pass)
            check (a story failed the checks before rendering), render (a render's own problems: length, the
            layout probe), qa (the finished file); queue.process records an exception at the stage it happened in
    rule    the rule's name, from the problem text: K9, N2, kaeasy:<check>, draw, timing, probe:overflow, length...;
            for an exception its class (transient, config, layout, render, content)

    python -m tt_shorts.engine learn [--brand tbilisi-today] [--days 7]    # the rules failing most lately

prompt_block(brand) is the writer's short list of the mistakes the latest scripts made (writer.write, `mistakes`):
only rules a script can fix, most frequent first, each with its latest message.
"""
import contextlib
import datetime as dt
import re
import sqlite3

from tt_shorts import store

SCHEMA = """
create table if not exists failures(ts text, brand text, stage text, rule text, message text);
create index if not exists failures_brand on failures(brand, ts);
"""
STAGES = ("write", "check", "render", "qa")
# The rules a writer can avoid by writing differently; the rest (loudness, a render crash, the network) are not its.
WRITER_RULES = re.compile(r"^(K\d+|N\d+|kaeasy:.+|draw|timing|structure|captions|length|probe:(overflow|band|rail|size|glyph))$")
# What a layout problem means for the one who writes the text
PROBE_HINTS = {
    "probe:overflow": "a text did not fit its box on screen: keep hook lines, names, labels and chart labels short",
    "probe:band": "a scene held more text than fits above the captions: fewer or shorter lines",
    "probe:rail": "a long line ran under the platform buttons on the right: shorter lines",
    "probe:size": "a text had to shrink too far to fit: shorter lines",
    "probe:glyph": "a character the brand font does not have: Georgian letters, digits and „“ only",
}


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


def rule_of(problem):
    """The rule a problem string names: "K9: scene 2 ..." -> K9, "probe overflow: ..." -> probe:overflow."""
    p = str(problem).strip()
    m = re.match(r"([KN]\d+)\b", p)
    if m:
        return m.group(1)
    m = re.match(r"kaeasy (\S+)", p)
    if m:
        return f"kaeasy:{m.group(1)}"
    m = re.match(r"probe (\w+)", p)
    if m:
        return f"probe:{m.group(1)}"
    if re.match(r"(scene \d+ \(\w+\)|story): ", p):
        return "structure"
    m = re.match(r"(length|loudness|size|preview render|no audio track)\b", p)
    if m:
        return m.group(1).replace(" ", "-")
    m = re.match(r"([a-z][a-z-]{1,20}):", p)
    return m.group(1) if m else "other"


def record(brand, stage, problems, rule=None):
    """Remember failed checks: one row per problem. rule: the same rule for all (an exception's class)."""
    rows = [(dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), brand or "", stage,
             rule or rule_of(p), str(p)[:500]) for p in problems or [] if str(p).strip()]
    if not rows:
        return 0
    try:
        with _db() as con:
            con.executemany("insert into failures values(?,?,?,?,?)", rows)
    except sqlite3.Error:  # memory is a help, never a reason for a job to fail
        return 0
    return len(rows)


def top(brand=None, days=7, n=10, stages=None, writer_only=False):
    """The rules failing most in the last `days`: [{rule, count, stages, last, example}], most frequent first."""
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat(timespec="seconds")
    q, args = "select * from failures where ts >= ?", [since]
    if brand:
        q += " and brand = ?"
        args.append(brand)
    if stages:
        q += f" and stage in ({','.join('?' * len(stages))})"
        args += list(stages)
    with _db() as con:
        rows = [dict(r) for r in con.execute(q + " order by ts, rowid", args)]
    out = {}
    for r in rows:
        if writer_only and not WRITER_RULES.match(r["rule"]):
            continue
        o = out.setdefault(r["rule"], {"rule": r["rule"], "count": 0, "stages": [], "last": r["ts"], "example": ""})
        o["count"] += 1
        if r["stage"] not in o["stages"]:
            o["stages"].append(r["stage"])
        o["last"], o["example"] = r["ts"], r["message"]
    return sorted(out.values(), key=lambda o: (-o["count"], o["rule"]))[:n]


def prompt_block(brand, days=14, n=6):
    """The writer's list of the mistakes the latest scripts made ("" when there are none)."""
    rules = top(brand, days, n, writer_only=True)
    if not rules:
        return ""
    lines = []
    for o in rules:
        why = PROBE_HINTS.get(o["rule"]) or re.sub(rf"^{re.escape(o['rule'])}:\s*", "", o["example"])
        why = " ".join(why.split())
        lines.append(f"- {o['rule']} ({o['count']}x): {why[:160]}{'…' if len(why) > 160 else ''}")
    return ("Mistakes the latest scripts made (code rejected them; most frequent first). Avoid them this time:\n"
            + "\n".join(lines))
