"""Put the site's OWN written Georgian into the corpus the review reads.

The owner, 2026-11-20: "https://tbilisi.today/stories აქ ჩვენი სათაურები და აღწერები წერია, ჰოდა
ეგენი გადაამოწმოს, ვნახოთ რა შეცდომები გვაქვს".

He is right, and this is the opposite of ops/corpus_site.py. That module copies `articles.content_text`,
which is the SOURCE OUTLET's text (verified: corpus ref 2906479 is an interpressnews.ge URL), so
reviewing it teaches the model how other outlets write, not what we get wrong. `story_clusters.headline`
and `story_clusters.summary_ka` are the sentences this project writes: the cluster headline is composed
by the pipeline from the sources, and summary_ka is a model-written Georgian summary.

Scale measured 2026-11-20: 4034 clusters carry a real summary, 466k chars of headline and 649k of
summary. That is 1.1M chars, about 13 agy calls for the WHOLE archive, not per day. A daily slice is
one call.

This is a producer, not a reviewer: it records text that is already public and never writes to kaeasy.
The 05:10 loop keeps deciding what becomes a lesson.

Usage:
    python -m ops.corpus_stories --day 2026-11-20        # one day
    python -m ops.corpus_stories --backfill 180          # the whole archive, once
    python -m ops.corpus_stories --backfill 180 --dry-run
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import corpus  # noqa: E402
from ops.corpus_site import d1  # noqa: E402  one credential story for every D1 reader

KIND = "story"
SURFACE = "site"
BATCH = 100


def rows_for_day(day: str) -> list[dict]:
    """One day's clusters, both fields, with the summary's model so a bad writer can be traced."""
    return d1(
        """SELECT id, headline, summary_ka, summary_model
             FROM story_clusters
            WHERE date(COALESCE(last_updated_at, first_seen_at)) = ?1
              AND headline IS NOT NULL AND length(headline) > 10
            ORDER BY id""",
        [day],
    )


def backfill_rows(days: int) -> list[dict]:
    """The whole recent archive, newest first. Bounded by the caller's --backfill."""
    return d1(
        """SELECT id, headline, summary_ka, summary_model
             FROM story_clusters
            WHERE COALESCE(last_updated_at, first_seen_at) >= datetime('now', ?1)
              AND headline IS NOT NULL AND length(headline) > 10
            ORDER BY id DESC""",
        [f"-{int(days)} days"],
    )


def record(row: dict, day: str, dry_run: bool = False) -> bool:
    """Record one cluster as two surfaces, so a headline defect and a summary defect stay separable.

    The two are written by different steps in the pipeline and fail differently: the headline is often a
    verbatim quote with its own punctuation, the summary is generated. Merging them into one string would
    make "the writer makes this mistake" impossible to tell from "the quoter makes it".
    """
    ref = str(row.get("id") or "")
    if not ref:
        return False
    wrote = False
    for surface, text in (("headline", row.get("headline")), ("summary", row.get("summary_ka"))):
        body = str(text or "").strip()
        if len(body) < 10:
            continue
        if dry_run:
            wrote = True
            continue
        rec = corpus.record(KIND, ref, surface, body, day=day,
                           outlet=str(row.get("summary_model") or ""), title=surface)
        wrote = wrote or bool(rec)
    return wrote


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="record the site's own story text into the review corpus")
    ap.add_argument("--day")
    ap.add_argument("--backfill", type=int, default=0,
                    help="record this many days back in one run (the archive, once)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.backfill:
        rows = backfill_rows(a.backfill)
        written = sum(1 for r in rows if record(r, day=_day_of(r), dry_run=a.dry_run))
        print(json.dumps({"mode": "backfill", "days": a.backfill, "clusters_read": len(rows),
                          "recorded": written, "dry_run": a.dry_run}, ensure_ascii=False))
        return 0

    import datetime as dt
    day = a.day or (dt.date.today() - dt.timedelta(days=1)).isoformat()
    rows = rows_for_day(day)
    written = sum(1 for r in rows if record(r, day=day, dry_run=a.dry_run))
    print(json.dumps({"mode": "day", "day": day, "clusters_read": len(rows),
                      "recorded": written, "dry_run": a.dry_run}, ensure_ascii=False))
    return 0


def _day_of(row: dict) -> str:
    # backfill_csv records everything under the day it belongs to; corpus.record keys on ref+surface too,
    # so an id can never land twice whatever day it is filed under.
    return str(row.get("_day") or "archive")


if __name__ == "__main__":
    raise SystemExit(main())
