"""A word-frequency index of human-written Georgian, so a lesson can be checked against reality.

The owner, 2026-11-19: "გადავამოწმოთ რომ ყველაფერი ისწავლოს KAeasy-იმ რაც მოგვცემს საშუალებას რომ
მოდელებით რომლებიც უფრო იაფი და ძალიან ცუდად იცის ქართული ისიც კი სწორად დაწერს".

The point is the inverse of a spell-checker. We are not asking "is this word in a dictionary". We are
asking a question the newsroom itself answers: does anybody write this word? A coined form
("მოქცევარი", "დაიმიტვისა") occurs in zero articles across every outlet. A real word a model misjudged
("დერეფანი", "პრევენციული") occurs in hundreds. That distinction keeps a learned rule from blocking a
correct story, and it needs no model and no dictionary: only the corpus we already have.

Storage: **one file per day**, `days/YYYY-MM-DD.tsv`, plus a merged `words.tsv` for readers.

Per-day files exist because the first version merged into a single file, and a build that ran twice
counted the same articles twice: "მამაკაცი" went from 28 articles to 44 after a re-run over the same
three days. A count that grows when nothing was published is worse than no index, because it makes a rare
word look common. With one file per day, a day is rebuilt from its own rows and replaces its own slice;
running the same day ten times gives the same number as running it once.

Merged view: `words.tsv`, `word<TAB>articles<TAB>outlets`. Counts only, no text.

Usage:
    python -m ops.attest_index build --days 90         # bootstrap, one file per day
    python -m ops.attest_index build --day 2026-11-18  # one day, for the daily loop
    python -m ops.attest_index lookup მოქცევარი დერეფანი
    python -m ops.attest_index stats
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(os.environ.get("TT_ATTEST_PATH") or (ROOT / "data" / "corpus" / "attest"))
DAYS = OUT / "days"
WORDS = OUT / "words.tsv"
META = OUT / "meta.json"

# A Georgian word: one or more letters of the Georgian block. Digits, Latin and punctuation split words.
TOKEN = re.compile(r"[ა-ჰ]+")
MIN_LEN = 2
BATCH = 400
RETRIES = 5  # D1 answers 429 under load; a bounded retry beats a half-built index


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def d1(sql: str, params: list | None = None) -> list[dict]:
    """Read-only D1 query, retrying a rate limit with backoff."""
    acct, tok, db = _env("CLOUDFLARE_ACCOUNT_ID"), _env("CLOUDFLARE_API_TOKEN"), _env("TT_D1_DATABASE_ID")
    body: dict = {"sql": sql}
    if params:
        body["params"] = params
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/d1/database/{db}/query"
    last = ""
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {tok}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
            if not data.get("success"):
                raise RuntimeError(f"D1: {data.get('errors')}")
            return data["result"][0]["results"]
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(min(30, 2 ** attempt))
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(f"D1: gave up after {RETRIES} attempts ({last})")


def _day_path(day: str) -> pathlib.Path:
    return DAYS / f"{day}.tsv"


def _read_day(day: str) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    p = _day_path(day)
    if not p.exists():
        return out
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            try:
                out[parts[0]] = [int(parts[1]), int(parts[2])]
            except ValueError:
                continue
    return out


def _write_day(day: str, index: dict[str, list[int]]) -> None:
    DAYS.mkdir(parents=True, exist_ok=True)
    p = _day_path(day)
    tmp = p.with_suffix(".tsv.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for word in sorted(index, key=lambda w: (-index[w][0], w)):
            fh.write(f"{word}\t{index[word][0]}\t{index[word][1]}\n")
    tmp.replace(p)


def merge() -> dict:
    """Rebuild `words.tsv` from the day files and report what it holds."""
    total: dict[str, list[int]] = {}
    days = sorted(p.stem for p in DAYS.glob("*.tsv")) if DAYS.exists() else []
    for day in days:
        for word, (count, outlets) in _read_day(day).items():
            slot = total.setdefault(word, [0, 0])
            slot[0] += count
            slot[1] += outlets
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = WORDS.with_suffix(".tsv.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for word in sorted(total, key=lambda w: (-total[w][0], w)):
            fh.write(f"{word}\t{total[word][0]}\t{total[word][1]}\n")
    tmp.replace(WORDS)
    meta = {"days": days, "words": len(total), "tokens": sum(v[0] for v in total.values()),
            "built_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone(__import__("datetime").timedelta(hours=4))).isoformat(timespec="seconds")}
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def build(day: str, batch: int = BATCH) -> dict:
    """Rebuild one day's slice from its own articles. Idempotent: the file is replaced, never added to."""
    rows_total = 0
    index: dict[str, list[int]] = {}
    offset = 0
    while True:
        rows = d1(f"""SELECT a.content_text AS body, a.source_slug AS outlet
                      FROM articles a
                      WHERE date(COALESCE(a.published_at, a.fetched_at)) = ?1
                        AND a.content_text IS NOT NULL
                        AND length(a.content_text) > 200
                      LIMIT {batch} OFFSET {offset}""", [day])
        if not rows:
            break
        for row in rows:
            rows_total += 1
            tokens = set(TOKEN.findall(str(row.get("body") or "")))
            for tok in tokens:
                if len(tok) < MIN_LEN:
                    continue
                slot = index.setdefault(tok, [0, 0])
                slot[0] += 1
                slot[1] += 1  # one article counts once, so a repeated word cannot inflate the outlet count
        offset += batch
        if len(rows) < batch:
            break
    _write_day(day, index)
    return {"day": day, "articles": rows_total, "words": len(index)}


def build_range(days: int, batch: int = BATCH) -> dict:
    """One file per day over a window, then a merge. A day already built is rebuilt from its own rows."""
    rows = d1("""SELECT DISTINCT date(COALESCE(published_at, fetched_at)) AS d
                 FROM articles
                 WHERE COALESCE(published_at, fetched_at) >= datetime('now', ?1)
                   AND content_text IS NOT NULL
                 ORDER BY d""", [f"-{int(days)} days"])
    out = []
    for row in rows:
        day = str(row.get("d") or "")
        if not day or day == "None":
            continue
        out.append(build(day, batch=batch))
    return {"days": out, "merged": merge()}


def _load() -> dict[str, list[int]]:
    """word -> [count, outlets]. Missing file is an empty index, not an error."""
    out: dict[str, list[int]] = {}
    if not WORDS.exists():
        return out
    with WORDS.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            try:
                out[parts[0]] = [int(parts[1]), int(parts[2])]
            except ValueError:
                continue
    return out


def lookup(*words: str) -> dict[str, list[int]]:
    """count and outlet count for each word. A word absent from the index is [0, 0]."""
    index = _load()
    return {w: index.get(w.lower(), [0, 0]) for w in words}


def attested(word: str, min_count: int = 3, min_outlets: int = 3) -> bool:
    """Does the newsroom write this word? The threshold is the design's: 3 occurrences in 3 outlets."""
    count, outlets = _load().get(word.lower(), [0, 0])
    return count >= min_count and outlets >= min_outlets


def stats() -> dict:
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    index = _load()
    return {**meta, "loaded_words": len(index),
            "day_files": len(list(DAYS.glob("*.tsv"))) if DAYS.exists() else 0,
            "top": sorted(index.items(), key=lambda kv: -kv[1][0])[:10]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="word-frequency index of human-written Georgian")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--days", type=int, default=None)
    b.add_argument("--day", default=None)
    sub.add_parser("merge")
    sub.add_parser("stats")
    lk = sub.add_parser("lookup")
    lk.add_argument("words", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        if a.day:
            print(json.dumps({**build(a.day), "merged": merge()}, ensure_ascii=False, indent=1))
        elif a.days:
            print(json.dumps(build_range(a.days), ensure_ascii=False, indent=1)[-2000:])
        else:
            print("give --day or --days")
            return 2
    elif a.cmd == "merge":
        print(json.dumps(merge(), ensure_ascii=False, indent=1))
    elif a.cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(lookup(*a.words), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
