"""Put the site's own published articles into the corpus the Georgian review reads.

The daily loop at 05:10 reviews `data/corpus/<day>.jsonl` and teaches kaeasy from what it finds. Measured
2026-11-19: that file held only reels and captions, because the only producers were ops/telegram_top.py and
ops/facebook_top.py. `corpus.record` documents `kind="article"` and nothing ever wrote it, so 34 video
records a day were reviewed against the 931 article bodies that were actually published on the same day.
The site is 27x more Georgian per day than the video lane, and it was invisible to the language loop.

This is a producer, not a reviewer: it copies text that is already public, records it once per id+surface,
and never writes to kaeasy itself. The 05:10 loop keeps deciding what becomes a lesson.

Usage:
    python -m ops.corpus_site --day 2026-11-18          # one day
    python -m ops.corpus_site --days 7 --dry-run        # what would be recorded
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import urllib.error
import urllib.request
import json
import os
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import corpus  # noqa: E402

# The same D1 REST endpoint ops/attest_index.py uses, so one credential story covers both.
API = "https://api.cloudflare.com/client/v4/accounts/{account}/d1/database/{db}/query"
BATCH = 100
MIN_CHARS = 400  # the readiness floor the rest of the pipeline already uses for a real body
MAX_CHARS = 4000  # a day's review is one model call: a very long piece must not crowd out the rest
UA = "Mozilla/5.0 (compatible; tbilisi.today corpus/1.0)"


def _env() -> dict:
    path = pathlib.Path(os.environ.get("TT_ENV", "/root/.hermes/profiles/tbilisi/.env"))
    out = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def d1(sql: str, params: list | None = None, retries: int = 5) -> list[dict]:
    env = _env()
    account = env.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    db = env.get("TT_D1_DATABASE_ID") or os.environ.get("TT_D1_DATABASE_ID")
    token = env.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (account and db and token):
        raise RuntimeError("D1 credentials missing (CLOUDFLARE_ACCOUNT_ID / TT_D1_DATABASE_ID / CLOUDFLARE_API_TOKEN)")
    body = json.dumps({"sql": sql, "params": params or []}).encode()
    req = urllib.request.Request(API.format(account=account, db=db), data=body, method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                          "User-Agent": UA})
    # The D1 REST endpoint throttles a burst of statements (measured 2026-11-19: HTTP 429 after the third
    # page of one day). A page-at-a-time walk is exactly that burst, so back off and retry rather than
    # losing the day; a real error still raises after the last attempt.
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"D1 unavailable after {retries} attempts: {last}")
    if not payload.get("success"):
        raise RuntimeError(f"D1 FAIL {str(payload)[:300]}")
    result = payload.get("result") or []
    return (result[0] or {}).get("results") or []


def day_rows(day: str, limit: int = 2000) -> list[dict]:
    """One day's published article bodies, bounded. Reader-visible rows only, the same filter the site uses."""
    out, offset = [], 0
    while offset < limit:
        rows = d1(
            """SELECT a.id AS id, a.title AS title, a.content_text AS body, a.source_slug AS outlet
                 FROM articles a
                WHERE date(COALESCE(a.published_at, a.fetched_at)) = ?1
                  AND a.content_text IS NOT NULL
                  AND length(a.content_text) >= ?2
                  AND COALESCE(a.content_status, '') NOT IN ('backfill_hidden', 'blocked')
                ORDER BY a.id
                LIMIT ?3 OFFSET ?4""",
            [day, MIN_CHARS, BATCH, offset],
        )
        if not rows:
            break
        out.extend(rows)
        offset += BATCH
        if len(rows) < BATCH:
            break
    return out


def record_day(day: str, dry_run: bool = False) -> dict:
    rows = day_rows(day)
    written, skipped = 0, 0
    for row in rows:
        ref = str(row.get("id") or "")
        body = str(row.get("body") or "").strip()
        if not ref or len(body) < MIN_CHARS:
            skipped += 1
            continue
        if dry_run:
            written += 1
            continue
        rec = corpus.record("article", ref, "site", body[:MAX_CHARS], day=day,
                            outlet=str(row.get("outlet") or ""), title=str(row.get("title") or ""))
        if rec:
            written += 1
        else:
            skipped += 1
    return {"day": day, "articles_read": len(rows), "recorded": written, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="record the site's published articles into the review corpus")
    ap.add_argument("--day")
    ap.add_argument("--days", type=int, default=0, help="walk this many days back from --day or today")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    days: list[str] = []
    if a.day:
        days = [a.day]
    if a.days:
        import datetime as dt
        base = dt.date.fromisoformat(a.day) if a.day else dt.date.today()
        days = [(base - dt.timedelta(days=i)).isoformat() for i in range(a.days)]
    if not days:
        import datetime as dt
        days = [dt.date.today().isoformat()]
    total = {"recorded": 0, "articles_read": 0, "skipped": 0}
    for day in days:
        try:
            r = record_day(day, dry_run=a.dry_run)
        except Exception as e:  # noqa: BLE001 - one bad day must not stop the rest
            print(f"{day}: FAILED {type(e).__name__}: {str(e)[:200]}")
            continue
        print(f"{day}: read={r['articles_read']} recorded={r['recorded']} skipped={r['skipped']}"
              + (" (dry run)" if a.dry_run else ""))
        for k in total:
            total[k] += r.get(k, 0)
    print(f"total: read={total['articles_read']} recorded={total['recorded']} skipped={total['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
