"""A corpus of every text we publish, so a model can study it once a day instead of re-reading the site.

The owner, 2026-11-18: "თითოეულ გამოქვეყნებულ ამბავს და ასევე რილსში გამოყენებულ ტექსტების რამე საცავი
ხო გაქვს, ჰოდა ეგ ტექსტური მასალები თუ დაგროვდება სწორად ... ეგ საშუალებას მოგვცემს დღეში ერთხელ მერე
მოგცემ gemini cli-ის რომლის საშუალებითაც იმ ტქსტებში გამოავლენს შესცომებს, დახარჯავს ნაკლებ ტოკენს".

The corpus is one JSONL file per day, append-only, one record per published text. It is written when
something is published, not when something is rendered, so it holds exactly the material a reader saw.
Each record carries enough for a reviewer to judge a sentence without opening the site: the text, where
it appeared, and the story it came from.

Two consumers:
- the daily kaeasy pass: a model reads yesterday's records, names defects, and those become entries in
  kaeasy's wrong-forms table, which every agent then uses;
- any later audit: the records are immutable, so a defect found in March can be traced to the exact
  sentence that carried it.

Design rules:
- Append-only. A corrected text is a new record, never an edit of an old one, because the point is to
  remember what was published, not what we wish had been.
- One file per day under `data/corpus/`, so a day can be deleted, replayed or handed to a model alone.
- A record is written once per (kind, ref, surface): re-running a lane must not duplicate the corpus.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = pathlib.Path(os.environ.get("TT_CORPUS_DIR") or (ROOT / "data" / "corpus"))


def _day() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=4))).strftime("%Y-%m-%d")


def _path(day: str | None = None) -> pathlib.Path:
    return CORPUS / f"{day or _day()}.jsonl"


def _key(kind: str, ref: str, surface: str, text: str) -> str:
    return hashlib.sha1(f"{kind}|{ref}|{surface}|{text[:120]}".encode()).hexdigest()[:16]


def seen(kind: str, ref: str, surface: str, text: str, day: str | None = None) -> bool:
    """Has this exact text already been recorded? Cheap, and it keeps a re-run from duplicating a day."""
    path = _path(day)
    if not path.exists():
        return False
    key = _key(kind, ref, surface, text)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                if json.loads(line).get("key") == key:
                    return True
            except ValueError:
                continue
    return False


def record(kind: str, ref: str, surface: str, text: str, day: str | None = None, **extra) -> dict | None:
    """Append one published text. kind: "reel" | "caption" | "article" | "news". surface names the lane.

    `day` files a record under the day it was published; without it the record lands on today. A backfill
    of yesterday's articles must pass its own day, or 803 pieces publish into one file and yesterday's
    review reads an empty corpus (measured 2026-11-19).
    """
    text = (text or "").strip()
    if len(text) < 20:
        return None
    day = day or _day()
    if seen(kind, ref, surface, text, day):
        return None
    rec = {"key": _key(kind, ref, surface, text), "day": day, "kind": kind, "ref": str(ref),
           "surface": surface, "chars": len(text), "text": text, **extra}
    CORPUS.mkdir(parents=True, exist_ok=True)
    with _path(day).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def record_story(story: dict, surface: str = "reel", **extra) -> list[dict]:
    """Record a rendered story: its narration and every line a viewer reads on screen.

    A story is the material a reel publishes, so it is recorded as one record whose text is the
    narration followed by the on-screen lines. Keeping them together matters: a reviewer must see the
    sentence and the card that carried it.
    """
    ref = str(story.get("id") or "")
    out = []
    narration = str(story.get("narration") or "").strip()
    if narration:
        r = record("reel", ref, surface, narration, **extra)
        if r:
            out.append(r)
    lines = []
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, value in sc.items():
            if key in ("at", "type", "art", "say", "icon", "motif", "morph_from", "style", "variant",
                       "layout", "tone", "verb", "value", "unit"):
                continue
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
            elif isinstance(value, list):
                lines.extend(str(x).strip() for x in value if isinstance(x, str) and x.strip())
    if lines:
        r = record("card", ref, surface, "\n".join(lines), **extra)
        if r:
            out.append(r)
    return out


def load(day: str | None = None) -> list[dict]:
    """Every record of one day (today by default)."""
    path = _path(day)
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def days() -> list[str]:
    """Every day that has a corpus file, oldest first."""
    if not CORPUS.exists():
        return []
    return sorted(p.stem for p in CORPUS.glob("*.jsonl"))


def digest(day: str | None = None, limit: int = 400) -> str:
    """A compact, model-readable dump of one day: the material a daily reviewer reads.

    It is deliberately plain: one record per block, no JSON noise, so a model spends its tokens on the
    Georgian rather than on syntax.
    """
    records = load(day)
    blocks = []
    for r in records[:limit]:
        head = f"[{r.get('kind')}/{r.get('surface')} {r.get('ref')}]"
        blocks.append(f"{head}\n{r.get('text', '').strip()}")
    return "\n\n---\n\n".join(blocks)
