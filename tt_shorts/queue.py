"""The job queue: what to make, in what state it is, and what happened. SQLite in $VEASY_HOME/veasy.db.

A job is one video: (brand, program, source, ref, format, overrides). Its id is a hash of exactly that, so adding the
same request twice returns the same job (idempotent): an agent can't make the same video twice by accident. The
program (programs.py) is in the id only when it isn't news, so a news job keeps the id it had before programs; a
program that says `publish: review` ends `held` (error_class review) even when QA passed: a person watches it first.

    queued ──> writing ──> rendering ──> done            (qa passed, real voice: ready to publish)
                  │            │    └──> held            (rendered, but qa found problems or a preview voice)
                  └────────────┴───────> failed          (content / layout / config: retry by hand after a fix)
    transient errors (network, 429, 5xx, timeouts) go back to queued with a delay: 5, 10, 20 minutes, then failed.
    cancelled: taken out by hand.

One worker at a time per machine (a lock file): cron can run `engine queue run` every few minutes safely; the
renders are serialised, as Remotion advises. A job that already has a story skips writing.

    python -m tt_shorts.engine queue add --source tbilisi-today --ref 24725 [--format news] [--brand tbilisi-today]
    python -m tt_shorts.engine queue add --story path/to/story.json --format news-roll
    python -m tt_shorts.engine queue add --ref 24835 --rubric number      # a rubric (rubrics.py): its program and
                                                                          # format by default
    python -m tt_shorts.engine queue add --rubric digest --ref done:tbilisi-today   # the morning digest

A rubric is an override (in the job id, like a director): the write step stamps the story's rubric and episode; a
story job's file must already carry it (engine rubrics stamp). The episode is the rubric's (rubrics.py): marked done
when the job ends done, released when it fails or is cancelled. Every news job that ends done stores what its
cluster had (rubrics.remember), so a later "continues" part can be compared with it.
    python -m tt_shorts.engine queue list [--state queued]
    python -m tt_shorts.engine queue run [--max 5]
    python -m tt_shorts.engine queue show <id> | retry <id> | cancel <id>
    python -m tt_shorts.engine queue approve <id> | reject <id>      # a held film, after a person watched it

The review tier (composed films): a film the HyperFrames engine made (compose.py; the film engine is the director's,
the program's, the format's or the pack's "engine", or the job's --renderer) that passed QA still ends `held`
(error_class review) unless its format's or program's `review` lets it through: `always` (the default: every
composed film is watched) or `until:<n>` (held until the brand has n approved composed films in a row; a rejection
starts the count again; until:0 never holds). `approve` makes a held job done and counts it; `reject` fails it
(error_class rejected) and resets the brand's count. Counted per brand in the `reviews` table.
"""
import contextlib
import datetime as dt
import hashlib
import json
import os
import pathlib
import socket
import sqlite3
import subprocess
import time
import traceback
import urllib.error

try:
    import fcntl
except ImportError:  # Windows (a developer's machine): the same one-worker lock through msvcrt
    fcntl = None
    import msvcrt

from tt_shorts import brand as brand_pack
from tt_shorts import formats, programs, store

STATES = ("queued", "writing", "rendering", "done", "held", "failed", "cancelled")
MAX_TRANSIENT = 3
BACKOFF_MIN = 5

SCHEMA = """
create table if not exists jobs(
  id text primary key, name text, brand text, source text, ref text, format text, overrides text,
  story text, state text, priority int default 0, attempts int default 0, error_class text, error text,
  result text, created text, updated text, not_before real default 0, program text default 'news');
create index if not exists jobs_state on jobs(state, priority, created);
create table if not exists reviews(ts text, brand text, job text, engine text, verdict text);
create index if not exists reviews_brand on reviews(brand, engine, ts);
"""
# Columns added after the first release: an older veasy.db gets them on open (ALTER TABLE, with their default).
MIGRATIONS = {"program": "alter table jobs add column program text default 'news'"}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def db():
    con = sqlite3.connect(store.home() / "veasy.db", timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    have = {r["name"] for r in con.execute("pragma table_info(jobs)")}
    for col, sql in MIGRATIONS.items():
        if col not in have:
            try:
                con.execute(sql)
                con.commit()
            except sqlite3.OperationalError as e:  # another worker added it a moment ago
                if "duplicate column" not in str(e):
                    raise
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


def job_id(brand, source, ref, fmt, overrides, program=programs.DEFAULT):
    spec = {"brand": brand, "source": source, "ref": str(ref), "format": fmt, "overrides": overrides or {}}
    if program and program != programs.DEFAULT:  # news jobs keep the ids they had before programs
        spec["program"] = program
    key = json.dumps(spec, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def _row(r):
    if r is None:
        return None
    d = dict(r)
    for k in ("overrides", "result"):
        d[k] = json.loads(d[k]) if d.get(k) else None
    return d


def add(brand=None, source=None, ref=None, fmt=None, overrides=None, story=None, priority=0, program=None):
    """-> (job, created). A job needs either a story file or a source + ref. Same request -> same job.
    brand: the pack (default tbilisi-today); a story file's own "brand" is used when none is given, and a different
    one is refused (the story decides how it looks). program: news by default (a story file's own "program");
    the source defaults to the program's first, the format to the program's."""
    data = None
    rub = rubric_of(overrides)  # an unknown rubric is refused before it is queued
    if rub:
        if program and program != rub["program"]:
            raise ValueError(f"rubric {rub['id']} is a {rub['program']} rubric, not {program}")
        program = rub["program"]
    if story:
        story = pathlib.Path(story).resolve()  # the worker may run from another folder
        data = json.loads(story.read_text(encoding="utf-8"))  # unreadable or not JSON: refused now, not at run time
        own = data.get("program")
        if program and own and program != own:
            raise ValueError(f"the story says program {own!r}, the job {program!r}: change the story's \"program\"")
        program = program or own
    prog = programs.get(program)  # an unknown program is refused before it is queued
    program = prog["name"]
    if not story:
        source = source or (prog["sources"][0] if ref is not None else None)
        if not (source and ref is not None):
            raise ValueError("a job needs --story, or --source and --ref")
        programs.check_source(prog, source)
    fmt = fmt or (rubric_of(overrides) or {}).get("format") or prog["format"]
    formats.get(fmt, **_format_overrides(overrides))  # refuse a format the engine can't do before it is queued
    if (overrides or {}).get("director"):
        from tt_shorts import directors
        directors.get(overrides["director"])  # and a director that doesn't exist
    label = ref if program == programs.DEFAULT else f"{program}-{ref}"
    if story:
        source, ref = "story", str(story)
        label = data.get("id") or story.stem  # name the job after the story's own id
        own = data.get("brand")
        if brand and own and brand != own:
            raise ValueError(f"the story says brand {own!r}, the job {brand!r}: change the story's \"brand\"")
        brand = brand or own
    brand = brand or brand_pack.DEFAULT
    brand_pack.load(brand)  # and a brand pack that doesn't exist
    jid = job_id(brand, source, ref, fmt, overrides, program)
    with _conn() as con:
        old = con.execute("select * from jobs where id=?", (jid,)).fetchone()
        if old:
            return _row(old), False
        con.execute("insert into jobs(id,name,brand,source,ref,format,overrides,story,state,priority,created,updated,"
                    "program) values(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (jid, store.job_name(brand, label, fmt), brand, source, str(ref), fmt,
                     json.dumps(overrides or {}), str(story) if story else None, "queued", priority, now(), now(),
                     program))
        store.log("queued", job=jid, brand=brand, program=program, source=source, ref=str(ref), format=fmt)
        return _row(con.execute("select * from jobs where id=?", (jid,)).fetchone()), True


NOT_FORMAT = ("director", "rubric", "part", "renderer")  # overrides that are not format keys (directors.py,
# rubrics.py; renderer: the film engine, compose.engine_for)


def _format_overrides(overrides):
    """A job's overrides without the director, the rubric and its part, which are not format keys."""
    return {k: v for k, v in (overrides or {}).items() if k not in NOT_FORMAT}


def rubric_of(overrides):
    from tt_shorts import rubrics
    name = (overrides or {}).get("rubric")
    return rubrics.get(name) if name else None


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
    j = get(jid)
    if j and j.get("story"):
        _episode(j["story"], j["brand"], "cancelled")
    return j


def _claim():
    """Claim one job. The update is guarded on state='queued' and its rowcount decides the
    race, so two workers can run side by side without ever writing the same story."""
    with _conn() as con:
        for _ in range(6):
            r = con.execute("select * from jobs where state='queued' and not_before<=? order by priority desc, created "
                            "limit 1", (time.time(),)).fetchone()
            if not r:
                return None
            cur = con.execute("update jobs set state=?, attempts=attempts+1, updated=? where id=? and state='queued'",
                              ("rendering" if r["story"] else "writing", now(), r["id"]))
            if cur.rowcount == 1:
                return _row(r)
        return None


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
    from tt_shorts import engine as eng, failures
    jid = job["id"]
    stage = "write" if not job["story"] else "check"  # failure memory: where an exception happened
    try:
        story = job["story"]
        program = job.get("program") or programs.DEFAULT
        rub = (job["overrides"] or {}).get("rubric")
        if not story:
            w = eng.write_story(job["source"], job["ref"], job["brand"], program=program,
                                director=(job["overrides"] or {}).get("director"), rubric=rub)
            story = w["story"]
            _set(jid, story=story, state="rendering")
            if w["problems"]:
                _set(jid, state="failed", error_class="content", error="; ".join(w["problems"][:5]), result=w)
                store.log("failed", job=jid, stage="write", problems=w["problems"][:5])
                _episode(story, job["brand"], "failed")
                return get(jid)
        stage = "check"
        fmt = formats.get(job["format"], **_format_overrides(job["overrides"]))
        side = store.sources_path(story)
        sources = json.loads(side.read_text(encoding="utf-8")) if side.exists() else None
        written = json.loads(pathlib.Path(story).read_text(encoding="utf-8"))
        problems = eng.check_story(written, sources) + eng._kaeasy_required()
        if rub and written.get("rubric") != rub:
            problems.append(f"the job is rubric {rub}, the story {written.get('rubric')!r}: stamp it first "
                            f"(engine rubrics stamp <story> --rubric {rub})")
        if problems:
            failures.record(job["brand"], "check", problems)
            _set(jid, state="failed", error_class="content", error="; ".join(problems[:5]))
            store.log("failed", job=jid, stage="check", problems=problems[:5])
            _episode(story, job["brand"], "failed")
            return get(jid)
        stage = "render"
        director, renderer = (job["overrides"] or {}).get("director"), (job["overrides"] or {}).get("renderer")
        film = eng.film_engine(story, fmt, director, renderer)
        r = eng.render_any(story, fmt, engine, director=director, renderer=renderer)
        failures.record(job["brand"], "render", r["problems"])  # length, the layout probe
        if not r.get("file"):  # a composed film whose checks refused it (network, canvas, the chrome): no video
            _set(jid, state="failed", error_class="layout", error="; ".join(r["problems"][:5]), result=r)
            store.log("failed", job=jid, stage="render", problems=r["problems"][:5])
            _episode(story, job["brand"], "failed")
            return get(jid)
        stage = "qa"
        q = eng.qa_file(r["file"], fmt) if not r["problems"] else {"problems": r["problems"]}
        if not r["problems"]:
            failures.record(job["brand"], "qa", q["problems"])
        if engine != "gemini":  # done means ready to publish: a preview voice never is
            q = {**q, "problems": q["problems"] + [f"preview render (engine {engine}): not for publishing; "
                                                   "retry with the gemini voice"]}
        result = {**r, "qa": q}
        state = "done" if not q["problems"] else "held"
        error_class, error = (None if state == "done" else "qa"), "; ".join(q["problems"]) or None
        if program != programs.DEFAULT:
            result["program"] = program
            if state == "done" and programs.get(program)["publish"] == "review":
                state, error_class = "held", "review"  # QA passed; the program wants a person to watch it first
                error = f"program {program} publishes after a review: watch it, then publish (QA passed)"
        result["film_engine"] = film
        if state == "done" and film == "hyperframes":  # the review tier: composed films are watched first
            why = review_hold(job["brand"], written, fmt)
            if why:
                state, error_class, error = "held", "review", why
        _set(jid, state=state, result=result, error=error, error_class=error_class)
        store.log(state, job=jid, file=r["file"], problems=q["problems"])
        if state == "done":  # its drawing passed and went out: the library keeps it for a story whose drawing fails
            _keep_drawings(story, job["brand"])
        _episode(story, job["brand"], state)
    except Exception as e:  # noqa: BLE001 - one job never stops the queue
        kind = classify(e)
        if not getattr(e, "problems", None):  # a writer's failed checks are already remembered, rule by rule
            failures.record(job["brand"], stage, [f"{type(e).__name__}: {e}"], rule=kind)
        attempts = (get(jid) or {}).get("attempts", 1)
        if kind == "transient" and attempts < MAX_TRANSIENT:
            delay = BACKOFF_MIN * 60 * 2 ** (attempts - 1)
            _set(jid, state="queued", not_before=time.time() + delay, error_class=kind, error=str(e)[:500])
        else:
            _set(jid, state="failed", error_class=kind, error=f"{type(e).__name__}: {e}"[:500])
        store.log("error", job=jid, kind=kind, error=str(e)[:300], trace=traceback.format_exc()[-800:])
        j = get(jid) or {}
        if j.get("state") == "failed" and j.get("story"):
            _episode(j["story"], job["brand"], "failed")
    return get(jid)


def approved_in_a_row(brand, engine="hyperframes"):
    """How many of the brand's composed films were approved since its last rejection."""
    with _conn() as con:
        rows = [r["verdict"] for r in con.execute(
            "select verdict from reviews where brand=? and engine=? order by ts desc, rowid desc", (brand, engine))]
    n = 0
    for v in rows:
        if v != "approved":
            break
        n += 1
    return n


def review_hold(brand, story, fmt):
    """Why a composed film that passed QA is held for a person (compose.review_for: the format's or program's
    `review`, else always), or None when the brand has earned automatic publishing (until:<n>)."""
    from tt_shorts import compose
    kind, n, why = compose.review_for(story, fmt)
    if kind == "always":
        return f"a composed film is watched before it goes out (review always, {why}): approve or reject it (QA passed)"
    have = approved_in_a_row(brand)
    if have < n:
        return (f"a composed film is watched until {n} in a row are approved ({why}); {brand} has {have}: approve or "
                "reject it (QA passed)")
    return None


def approve(jid):
    """A held job, watched and approved by a person: done (ready to publish); a composed film counts toward its
    brand's review tier."""
    j = get(jid)
    if not j or j["state"] != "held":
        raise ValueError(f"job {jid} is not held (state {j and j['state']}): only a held video is approved")
    _set(jid, state="done", error=None, error_class=None)
    if (j.get("result") or {}).get("film_engine") == "hyperframes":
        with _conn() as con:
            con.execute("insert into reviews(ts, brand, job, engine, verdict) values(?,?,?,?,?)",
                        (now(), j["brand"], jid, "hyperframes", "approved"))
    store.log("approved", job=jid)
    if j.get("story"):
        _episode(j["story"], j["brand"], "done")
    return get(jid)


def reject(jid, why="rejected in review"):
    """A held job a person rejected: failed (error_class rejected); a composed film resets its brand's count."""
    j = get(jid)
    if not j or j["state"] != "held":
        raise ValueError(f"job {jid} is not held (state {j and j['state']}): only a held video is rejected")
    _set(jid, state="failed", error_class="rejected", error=why)
    if (j.get("result") or {}).get("film_engine") == "hyperframes":
        with _conn() as con:
            con.execute("insert into reviews(ts, brand, job, engine, verdict) values(?,?,?,?,?)",
                        (now(), j["brand"], jid, "hyperframes", "rejected"))
    store.log("rejected", job=jid)
    if j.get("story"):
        _episode(j["story"], j["brand"], "failed")
    return get(jid)


def _episode(story_path, brand, state):
    """The rubric's episode of a finished job: used when done, released when failed (rubrics.py); a done news video
    stores what its cluster had (for a later continues part). Never fails a job."""
    from tt_shorts import rubrics
    try:
        story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
        name = pathlib.Path(story_path).stem
        if story.get("rubric") and state == "done":
            rubrics.finish(brand, story["rubric"], store.safe(name))
        elif story.get("rubric") and state in ("failed", "cancelled"):
            rubrics.release(brand, story["rubric"], store.safe(name))
        if state == "done" and programs.name_of(story) == programs.DEFAULT:
            side = store.sources_path(story_path)
            arts = json.loads(side.read_text(encoding="utf-8")) if side.exists() else []
            rubrics.remember(brand, story, arts, story_path)
    except (OSError, ValueError, KeyError, sqlite3.Error) as e:
        store.log("error", stage="rubrics", error=str(e)[:300])


def _keep_drawings(story_path, brand):
    """drawings.keep for a done job's story; the library never fails a job."""
    from tt_shorts import drawings
    try:
        saved = drawings.keep(json.loads(pathlib.Path(story_path).read_text(encoding="utf-8")), brand)
        if saved:
            store.log("drawing kept", story=str(story_path), ids=saved)
    except (OSError, ValueError, sqlite3.Error) as e:
        store.log("error", stage="drawings", error=str(e)[:300])


@contextlib.contextmanager
def _lock():
    path = store.home() / "queue.lock"
    with open(path, "w") as fh:
        try:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        except (BlockingIOError, PermissionError, OSError):
            yield False
            return
        try:
            yield True
        finally:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_UN)
            else:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)


def run(max_jobs=5, engine="gemini"):
    """Process up to max_jobs queued jobs, one at a time; returns what happened. Another worker running -> busy."""
    import contextlib
    gate = contextlib.nullcontext(True) if os.environ.get("TT_QUEUE_PARALLEL") == "1" else _lock()
    with gate as mine:
        if not mine:
            return {"busy": True, "processed": []}
        processed = []
        for _ in range(max_jobs):
            job = _claim()
            if not job:
                break
            processed.append({k: v for k, v in process(job, engine).items() if k in ("id", "name", "state", "error")})
        return {"busy": False, "processed": processed, "counts": counts()}
