"""Where Veasy keeps things, and what they are called. One home, the same layout on every machine.

    $VEASY_HOME/                     default: <veasy>/data  (SHORTS_DATA is still read, for old installs)
      .env                           secrets (chmod 600), never in git
      veasy.db                       the job queue and the cost ledger (SQLite)
      stories/<brand>/<day>/<ref>.json            a story script; <ref>.sources.json beside it (the articles)
      renders/<brand>/<day>/<ref>-<format>-<look>-<captions>.mp4   + .sheet.jpg (QA) + .json (what was rendered)
                                     + .props.json (what Remotion drew: timings, captions, the pack)
      renders/<brand>/<day>/<ref>-<format>-<look>-<captions>-package/   `engine package`: one render's publishing
                                     kit (captions.srt/.vtt, cover.png, carousel-NN.png, teaser.mp4, texts.json,
                                     telegram.md); kept and deleted with its render
      cache/voices/<sha16>/          one voice + its word timings per (engine, voice, style, spoken text)
      cache/work/<job>/              render scratch, deleted after a good render
      logs/<day>.jsonl               one JSON line per event (queued, rendered, failed, gc...)

Names:
  brand   a brand pack folder name: lowercase, digits and hyphens (tbilisi-today, sitech)
  ref     the story's id in its source (a cluster id, a post slug), made safe the same way
  day     YYYY-MM-DD of when the job was created (the server's local date)
  job     <brand>-<ref>-<format>, e.g. tbilisi-today-24725-news

Retention (`engine gc`): work scratch 2 days, renders 30 days, voices 90 days (re-renders within that window are
free), logs 90 days. Stories are kept: they are small and they are the record of what was published.
"""
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEEP_DAYS = {"work": 2, "renders": 30, "voices": 90, "logs": 90}


def home():
    p = pathlib.Path(os.environ.get("VEASY_HOME") or os.environ.get("SHORTS_DATA") or ROOT / "data")
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe(name):
    """A name fit for a path: lowercase ASCII letters, digits and hyphens (Georgian or spaces become hyphens)."""
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return s or "x"


def today():
    return dt.date.today().isoformat()


def job_name(brand, ref, fmt):
    return f"{safe(brand)}-{safe(ref)}-{safe(fmt)}"


def story_path(brand, ref, day=None):
    p = home() / "stories" / safe(brand) / (day or today()) / f"{safe(ref)}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def sources_path(story):
    return pathlib.Path(story).with_suffix(".sources.json")


def render_path(brand, ref, fmt, look, captions, day=None):
    p = home() / "renders" / safe(brand) / (day or today()) / f"{safe(ref)}-{safe(fmt)}-{safe(look)}-{safe(captions)}.mp4"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def props_path(render):
    """The Remotion props of a render, beside its mp4: <render>.props.json."""
    return pathlib.Path(render).with_suffix(".props.json")


def package_dir(render):
    """The publishing kit of a render (its .mp4 or .json): <render>-package/ beside it."""
    r = pathlib.Path(render)
    stem = next((r.name[:-len(s)] for s in (".props.json", ".json", ".mp4") if r.name.endswith(s)), r.stem)
    return r.with_name(f"{stem}-package")


def voice_dir(key):
    """The cache folder of one voice track: the key names engine, voice, style and the exact spoken text."""
    p = home() / "cache" / "voices" / hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    p.mkdir(parents=True, exist_ok=True)
    return p


def work_dir(name):
    p = home() / "cache" / "work" / safe(name)
    p.mkdir(parents=True, exist_ok=True)
    return p


def log(event, **fields):
    """Append one event to today's log: {"ts", "event", ...}."""
    d = home() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    row = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "event": event, **fields}
    with (d / f"{today()}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _older_than(path, days, now):
    try:
        return now - path.stat().st_mtime > days * 86400
    except OSError:
        return False


def gc(dry_run=False, now=None):
    """Delete what has outlived KEEP_DAYS. Returns {kind: [removed paths]}."""
    now = now or time.time()
    h = home()
    targets = {
        "work": [p for p in (h / "cache" / "work").glob("*") if p.is_dir()],
        "voices": [p for p in (h / "cache" / "voices").glob("*") if p.is_dir()],
        "renders": [p for p in (h / "renders").glob("*/*/*") if p.is_file() or p.name.endswith("-package")],
        "logs": [p for p in (h / "logs").glob("*.jsonl")],
    }
    removed = {}
    for kind, paths in targets.items():
        old = [p for p in paths if _older_than(p, KEEP_DAYS[kind], now)]
        removed[kind] = [str(p) for p in old]
        if not dry_run:
            for p in old:
                shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    if not dry_run:
        for empty in sorted((h / "renders").glob("*/*"), reverse=True):  # day folders left empty
            if empty.is_dir() and not any(empty.iterdir()):
                empty.rmdir()
        log("gc", removed={k: len(v) for k, v in removed.items()})
    return removed
