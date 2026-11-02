"""The job queue: what to make, in what state it is, and what happened. SQLite in $VEASY_HOME/veasy.db.

A job is one video: (brand, source, ref, format, overrides). Its id is a hash of exactly that, so adding the same
request twice returns the same job (idempotent): an agent can't make the same video twice by accident.

    queued ──> writing ──> rendering ──> done            (qa passed, real voice: ready to publish)
                  │            │    └──> held            (rendered, but qa found problems or a preview voice)
                  └────────────┴───────> failed          (content / layout / config: retry by hand after a fix)
    transient errors (network, 429, 5xx, timeouts) go back to queued with a delay: 5, 10, 20 minutes, then failed.
    cancelled: taken out by hand.

One worker at a time per machine (a lock file): cron can run `engine queue run` every few minutes safely; the
renders are serialised, as Remotion advises. A job that already has a story skips writing.

    python -m tt_shorts.engine queue add --source tbilisi-today --ref 24725 [--format news] [--brand tbilisi-today]
    python -m tt_shorts.engine queue add --story path/to/story.json --format news-roll
    python -m tt_shorts.engine queue list [--state queued]
    python -m tt_shorts.engine queue run [--max 5]
    python -m tt_shorts.engine queue show <id> | retry <id> | cancel <id>
"""
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import pathlib
import socket
import sqlite3
import subprocess
import time
import traceback
import urllib.error

from tt_shorts import brand as brand_pack
from tt_shorts import formats, store

STATES = ("queued", "writing", "rendering", "done", "held", "failed", "cancelled")
MAX_TRANSIENT = 3
BACKOFF_MIN = 5

SCHEMA = """
create table if not exists jobs(
  id text primary key, name text, brand text, source text, ref text, format text, overrides text,
  story text, state text, priority int default 0, attempts int default 0, error_class text, error text,
  result text, created text, updated text, not_before real default 0);
create index if not exists jobs_state on jobs(state, priority, created);
"""


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def db():
    con = sqlite3.connect(store.home() / "veasy.db", timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


@contextlib.contextmanager
def _conn():
    """One connection per operation: committed on success, rolled back on error, always closed."""
    con = db()
    try:
        with con:
            yield con
    finally:
        con.close()


def job_id(brand, source, ref, fmt, overrides):
    key = json.dumps({"brand": brand, "source": source, "ref": str(ref), "format": fmt, "overrides": overrides or {}},
                     sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def _row(r):
    if r is None:
        return None
    d = dict(r)
    for k in ("overrides", "result"):
        d[k] = json.loads(d[k]) if d.get(k) else None
    return d


def add(brand=None, source=None, ref=None, fmt="news", overrides=None, story=None, priority=0):
    """-> (job, created). A job needs either a story file or a source + ref. Same request -> same job.
    brand: the pack (default tbilisi-today); a story file's own "brand" is used when none is given, and a different
    one is refused (the story decides how it looks)."""
    if not story and not (source and ref is not None):
        raise ValueError("a job needs --story, or --source and --ref")
    formats.get(fmt, **(overrides or {}))  # refuse a format the engine can't do before it is queued
    label = ref
    if story:
        story = pathlib.Path(story).resolve()  # the worker may run from another folder
        source, ref = "story", str(story)
        data = json.loads(story.read_text(encoding="utf-8"))  # unreadable or not JSON: refused now, not at run time
        label = data.get("id") or story.stem  # name the job after the story's own id
        own = data.get("brand")
        if brand and own and brand != own:
            raise ValueError(f"the story says brand {own!r}, the job {brand!r}: change the story's \"brand\"")
        brand = brand or own
    brand = brand or brand_pack.DEFAULT
    brand_pack.load(brand)  # and a brand pack that doesn't exist
    jid = job_id(brand, source, ref, fmt, overrides)
    with _conn() as con:
        old = con.execute("select * from jobs where id=?", (jid,)).fetchone()
        if old:
            return _row(old), False
        con.execute("insert into jobs(id,name,brand,source,ref,format,overrides,story,state,priority,created,updated) "
                    "values(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (jid, store.job_name(brand, label, fmt), brand, source, str(ref), fmt,
                     json.dumps(overrides or {}), str(story) if story else None, "queued", priority, now(), now()))
        store.log("queued", job=jid, brand=brand, source=source, ref=str(ref), format=fmt)
        return _row(con.execute("select * from jobs where id=?", (jid,)).fetchone()), True


def get(jid):
    with _conn() as con:
        return _row(con.execute("select * from jobs where id=?", (jid,)).fetchone())


def listing(state=None, limit=50):
    with _conn() as con:
        q = "select * from jobs" + (" where state=?" if state else "") + " order by created desc limit ?"
        return [_row(r) for r in con.execute(q, ((state, limit) if state else (limit,)))]


def counts():
    with _conn() as con:
        return {r["state"]: r["n"] for r in con.execute("select state, count(*) n from jobs group by state")}


def _set(jid, **fields):
    fields["updated"] = now()
    for k in ("result", "overrides"):
        if k in fields and not isinstance(fields[k], str):
            fields[k] = json.dumps(fields[k], ensure_ascii=False)
    cols = ", ".join(f"{k}=?" for k in fields)
    with _conn() as con:
        con.execute(f"update jobs set {cols} where id=?", (*fields.values(), jid))


def retry(jid):
    _set(jid, state="queued", not_before=0, error=None, error_class=None)
    return get(jid)


def cancel(jid):
    _set(jid, state="cancelled")
    return get(jid)


def _claim():
    with _conn() as con:
        r = con.execute("select * from jobs where state='queued' and not_before<=? order by priority desc, created "
                        "limit 1", (time.time(),)).fetchone()
        if not r:
            return None
        con.execute("update jobs set state=?, attempts=attempts+1, updated=? where id=? and state='queued'",
                    ("rendering" if r["story"] else "writing", now(), r["id"]))
        return _row(r)


def classify(exc):
    """transient | config | layout | render | content: what the queue does next depends on it."""
    text = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, (TimeoutError, socket.timeout, ConnectionError, urllib.error.URLError)):
        return "transient"
    if isinstance(exc, urllib.error.HTTPError) and (exc.code == 429 or exc.code >= 500):
        return "transient"
    if any(t in text for t in ("HTTP 429", "HTTP 5", "timed out", "Temporary failure", "Connection reset")):
        return "transient"
    if isinstance(exc, (formats.FormatError, KeyError)) or "is not set" in text or "required" in text:
        return "config"
    if "layout QA" in text or "anchor" in text:
        return "layout"
    if isinstance(exc, subprocess.CalledProcessError):  # remotion or ffmpeg failed: see the log, then retry by hand
        return "render"
    return "content"


def process(job, engine="gemini"):
    """Write (if needed), check, render and QA one claimed job; leaves it done, held, failed or re-queued."""
    from tt_shorts import engine as eng
    jid = job["id"]
    try:
        story = job["story"]
        if not story:
            w = eng.write_story(job["source"], job["ref"], job["brand"])
            story = w["story"]
            _set(jid, story=story, state="rendering")
            if w["problems"]:
                _set(jid, state="failed", error_class="content", error="; ".join(w["problems"][:5]), result=w)
                store.log("failed", job=jid, stage="write", problems=w["problems"][:5])
                return get(jid)
        fmt = formats.get(job["format"], **(job["overrides"] or {}))
        side = store.sources_path(story)
        sources = json.loads(side.read_text(encoding="utf-8")) if side.exists() else None
        problems = eng.check_story(json.loads(pathlib.Path(story).read_text(encoding="utf-8")), sources) + eng._kaeasy_required()
        if problems:
            _set(jid, state="failed", error_class="content", error="; ".join(problems[:5]))
            store.log("failed", job=jid, stage="check", problems=problems[:5])
            return get(jid)
        r = eng.render_story(story, fmt, engine)
        q = eng.qa_file(r["file"], fmt) if not r["problems"] else {"problems": r["problems"]}
        if engine != "gemini":  # done means ready to publish: a preview voice never is
            q = {**q, "problems": q["problems"] + [f"preview render (engine {engine}): not for publishing; "
                                                   "retry with the gemini voice"]}
        result = {**r, "qa": q}
        state = "done" if not q["problems"] else "held"
        _set(jid, state=state, result=result, error="; ".join(q["problems"]) or None,
             error_class=None if state == "done" else "qa")
        store.log(state, job=jid, file=r["file"], problems=q["problems"])
    except Exception as e:  # noqa: BLE001 - one job never stops the queue
        kind = classify(e)
        attempts = (get(jid) or {}).get("attempts", 1)
        if kind == "transient" and attempts < MAX_TRANSIENT:
            delay = BACKOFF_MIN * 60 * 2 ** (attempts - 1)
            _set(jid, state="queued", not_before=time.time() + delay, error_class=kind, error=str(e)[:500])
        else:
            _set(jid, state="failed", error_class=kind, error=f"{type(e).__name__}: {e}"[:500])
        store.log("error", job=jid, kind=kind, error=str(e)[:300], trace=traceback.format_exc()[-800:])
    return get(jid)


@contextlib.contextmanager
def _lock():
    path = store.home() / "queue.lock"
    with open(path, "w") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def run(max_jobs=5, engine="gemini"):
    """Process up to max_jobs queued jobs, one at a time; returns what happened. Another worker running -> busy."""
    with _lock() as mine:
        if not mine:
            return {"busy": True, "processed": []}
        processed = []
        for _ in range(max_jobs):
            job = _claim()
            if not job:
                break
            processed.append({k: v for k, v in process(job, engine).items() if k in ("id", "name", "state", "error")})
        return {"busy": False, "processed": processed, "counts": counts()}
