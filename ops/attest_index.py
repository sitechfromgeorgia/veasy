"""A word-frequency index of human-written Georgian, so a lesson can be checked against reality.

The owner, 2026-11-19: "გადავამოწმოთ რომ ყველაფერი ისწავლოს KAeasy-იმ რაც მოგვცემს საშუალებას რომ
მოდელებით რომლებიც უფროსია ან ძალიან იაფი და ძალიან ცუდად იცის ქართული ისიც კი სწორად დაწერს".

The point is the inverse of a spell-checker. We are not asking "is this word in a dictionary". We are
asking a question the newsroom itself answers: does anybody write this word? A coined form
("მოქცევარი", "დაიმიტვისა") occurs in zero articles across every outlet. A real word a model
misjudged ("დერეფანი", "პრევენციული") occurs in hundreds. That distinction is what keeps a learned rule
from blocking a correct story, and it needs no model and no dictionary: only the corpus we already have.

What is built: `words.tsv`, one row per Georgian token, `word<TAB>count<TAB>outlets`, from
`articles.content_text` over a window of days. Counts only, no text, so the index carries no story.

Why TSV and not a database: kaeasy must stay free of network calls (its own AGENTS.md), and a small
file it can read with one pass is the whole requirement. A month of articles is a few million tokens and
a few tens of thousands of distinct words, which is a few hundred kilobytes.

Usage:
    python -m ops.attest_index build --days 90
    python -m ops.attest_index build --day 2026-11-18   # one day, for the daily loop
    python -m ops.attest_index lookup მოქცევარი დერეფანი
    python -m ops.attest_index stats
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(os.environ.get("TT_ATTEST_PATH") or (ROOT / "data" / "corpus" / "attest"))
WORDS = OUT / "words.tsv"
META = OUT / "meta.json"

# A Georgian word: one or more letters of the Georgian block. Digits, Latin and punctuation split words.
TOKEN = re.compile(r"[ა-ჰ]+")
MIN_LEN = 2  # a single letter is never a word worth indexing


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def d1(sql: str, params: list | None = None) -> list[dict]:
    """Read-only D1 query, the same transport the ingest side uses."""
    acct, tok, db = _env("CLOUDFLARE_ACCOUNT_ID"), _env("CLOUDFLARE_API_TOKEN"), _env("TT_D1_DATABASE_ID")
    body: dict = {"sql": sql}
    if params:
        body["params"] = params
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{acct}/d1/database/{db}/query",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    if not data.get("success"):
        raise RuntimeError(f"D1: {data.get('errors')}")
    return data["result"][0]["results"]


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


def _save(index: dict[str, list[int]], meta: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = WORDS.with_suffix(".tsv.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for word in sorted(index, key=lambda w: (-index[w][0], w)):
            fh.write(f"{word}\t{index[word][0]}\t{index[word][1]}\n")
    tmp.replace(WORDS)  # atomic: a reader never sees a half-written index
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def build(days: int | None = None, day: str | None = None, batch: int = 400) -> dict:
    """Read articles and merge their word counts into the index.

    `day` limits the read to one calendar day (the daily loop); `days` reads a window (the bootstrap).
    Both are additive: an existing index is loaded and updated, so a daily run costs one day's rows.
    """
    if day:
        where, params = "date(COALESCE(a.published_at, a.fetched_at)) = ?1", [day]
        label = day
    else:
        where, params = ("COALESCE(a.published_at, a.fetched_at) >= datetime('now', ?1)",
                         [f"-{int(days or 90)} days"])
        label = f"last {int(days or 90)} days"

    index = _load()
    seen_rows = 0
    offset = 0
    while True:
        rows = d1(f"""SELECT a.content_text AS body, a.source_slug AS outlet
                      FROM articles a
                      WHERE {where}
                        AND a.content_text IS NOT NULL
                        AND length(a.content_text) > 200
                      LIMIT {batch} OFFSET {offset}""", params)
        if not rows:
            break
        for row in rows:
            seen_rows += 1
            outlet = str(row.get("outlet") or "?")
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

    meta = {"label": label, "articles": seen_rows, "words": len(index),
            "tokens": sum(v[0] for v in index.values()),
            "built_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone(__import__("datetime").timedelta(hours=4))).isoformat(timespec="seconds")}
    _save(index, meta)
    return meta


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
            "top": sorted(index.items(), key=lambda kv: -kv[1][0])[:10]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="word-frequency index of human-written Georgian")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--days", type=int, default=None)
    b.add_argument("--day", default=None)
    sub.add_parser("stats")
    lk = sub.add_parser("lookup")
    lk.add_argument("words", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        print(json.dumps(build(a.days, a.day), ensure_ascii=False, indent=1))
    elif a.cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(lookup(*a.words), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
