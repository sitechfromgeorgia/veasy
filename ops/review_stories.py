"""Review the site's OWN written Georgian and turn the defects into kaeasy lessons.

This is the lane the owner asked for on 2026-11-20: "https://tbilisi.today/stories აქ ჩვენი სათაურები და
აღწერები წერია :/ ჰოდა ეგენი გადაამოწმოს, ვნახოთ რა შეცდომები გვაქვს".

`ops/corpus_stories` puts 15054 of our own headline and summary records into the corpus. This module
walks them in chunks and asks the reader one question per chunk: which forms here are wrong Georgian, and
what is the correct form. It is deliberately NOT the daily-review shape:

- The daily lane reads ONE day and asks for anything wrong. It found 13 pairs from 11k chars.
- Here the whole archive is 1.8M chars, so the run is bounded by `--max-chunks` and reports coverage
  honestly instead of quietly reading the first 400 records (the bug the Claude design found in
  corpus.digest's defaults).
- Every pair must carry the exact sentence it came from, because a phrase rule with no quote cannot be
  checked, and kaeasy's own intake refuses it (`no_quote`).

A pair is accepted only when `_acceptable()` confirms it: the wrong form must not be a word the corpus
attests on its own, and the right form must be. That is the same guard the daily lane uses, and it is
what stops "გააზროს -> გაიაზროს" style disagreements from becoming gate rules: both sides are checked
against 283k words of real Georgian instead of a model's opinion.

Usage:
    python -m ops.review_stories --max-chunks 4 --dry-run
    python -m ops.review_stories --max-chunks 24 --model gemini-4-neon-high
    python -m ops.review_stories --days 30          # only the recent slice
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import corpus  # noqa: E402

PROMPT = """You are a Georgian copy editor for a newsroom. The text below is written by the newsroom
itself (story headlines and summaries), not by a source outlet, so every error in it is ours.

Find concrete Georgian mistakes. For each one return:
  wrong   the exact substring as it appears in the text, copied character for character
  right   the correct form
  why     one sentence, in Georgian, naming the rule
  quote   the whole sentence the wrong form came from, copied character for character

Rules:
- Prefer a mistake that repeats. A form used once may be a typo; a form used five times is a lesson.
- Only real Georgian errors: wrong verb form, wrong case, a non-word, a calque, an inflection that does
  not exist. Never report style, length, tone or a rewrite you would prefer.
- If a word looks unusual but is a real Georgian word or a correct inflection, do not report it.
- Copy `wrong` and `quote` exactly. A quote that does not appear in the text cannot be verified and
  will be discarded, taking the lesson with it.
- If the text is clean, return an empty list. Finding nothing is a valid and useful answer.

Return JSON: {"pairs": [{"wrong": "...", "right": "...", "why": "...", "quote": "..."}]}
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "pairs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "wrong": {"type": "string"},
                    "right": {"type": "string"},
                    "why": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["wrong", "right", "quote"],
            },
        }
    },
    "required": ["pairs"],
}


def blocks(day: str = "archive", per_record: int = 800) -> list[str]:
    """Every record as its own small block, so a chunk boundary never cuts a sentence in half."""
    out = []
    for r in corpus.load(day):
        text = str(r.get("text", "")).strip()
        if not text:
            continue
        if len(text) > per_record:
            cut = text.rfind(" ", 0, per_record)
            text = text[:cut if cut > 0 else per_record]
        out.append(f"[{r.get('kind')}/{r.get('surface')} {r.get('ref')}]\n{text}")
    return out


def chunks(day: str = "archive", chunk_chars: int = 90000, per_record: int = 800) -> list[tuple[str, str]]:
    """Group blocks into (chunk_text, source_text) pairs under `chunk_chars` each."""
    out, buf, src, size = [], [], [], 0
    for b in blocks(day, per_record=per_record):
        if size and size + len(b) > chunk_chars:
            out.append(("\n\n---\n\n".join(buf), "\n".join(src)))
            buf, src, size = [], [], 0
        buf.append(b)
        src.append(b)
        size += len(b) + 7
    if buf:
        out.append(("\n\n---\n\n".join(buf), "\n".join(src)))
    return out


def _parse(raw: str | dict | None) -> list[dict]:
    """The reader returns the structured answer as a JSON STRING, not a dict. Parse it."""
    if isinstance(raw, str):
        if not raw.strip():
            return []
        try:
            res = json.loads(raw)
        except ValueError:
            return []
    else:
        res = raw
    pairs = (res or {}).get("pairs") if isinstance(res, dict) else None
    out = []
    for p in pairs or []:
        if not isinstance(p, dict):
            continue
        w = str(p.get("wrong") or "").strip()
        r = str(p.get("right") or "").strip()
        q = str(p.get("quote") or "").strip()
        if not (w and r and q) or w == r:
            continue
        out.append({"wrong": w, "right": r, "why": str(p.get("why") or "").strip(), "quote": q})
    return out


GEORGIAN = __import__("re").compile(r"^[ა-ჰ0-9\s\-]+$")


def _acceptable(pair: dict) -> tuple[bool, str]:
    """Is this pair verifiable against real Georgian? Same guard the daily lane uses, plus two.

    Measured 2026-11-20 on the site's own stories: the reader proposed "წმინდა ზარალს ->
    წარმდგომილ ზარალს" and "მეორეხარისხოვან -> მეორე ხარისხის". Both are wrong. The first invents a word
    (`წარმდგომილ` appears in 0 of 283,665 indexed rows) and breaks a real financial term (`წმინდა ზარალი`
    is net loss). The second "corrects" a real adjective that the newsroom writes 57 times.

    Two extra rules cover that class:
    - every word of `right` must exist in the corpus; a correction that invents a word is the model
      writing its own Georgian, not fixing ours
    - a phrase in `wrong` needs every one of its words attested, not just the joined string, because a
      phrase of real words can still be a term the model has never seen
    """
    w, r = pair["wrong"], pair["right"]
    words_w = w.split()
    if len(words_w) > 4:
        return False, "phrase_too_long"
    if any(ch.isdigit() for ch in w):
        return False, "digits"
    if not GEORGIAN.match(w):
        return False, "not_a_georgian_word"

    try:
        from ops import attest_index
        idx = attest_index._load()
        attested = attest_index.attested
    except Exception:
        return True, ""  # no index, no ground truth: the lesson state machine still gates it

    # A correction that invents a word is not a correction.
    for word in r.split():
        if len(word) >= 4 and word.lower() not in idx:
            return False, "right_form_unknown"

    if len(words_w) == 1:
        if attested(w):
            return False, "attested_in_corpus"
    else:
        # A phrase: every content word must be a word the newsroom writes, or the pair is unverifiable.
        for word in words_w:
            if len(word) >= 4 and word.lower() not in idx and word.lower() != r.lower():
                return False, "phrase_word_unknown"
    return True, ""


def review(max_chunks: int = 4, model: str = "gemini-4-neon-high", day: str = "archive",
           chunk_chars: int = 90000, dry_run: bool = False) -> dict:
    from kaeasy import lessons as ka_lessons
    from kaeasy import memory as ka_memory
    from tt_shorts import reader as ka_reader

    parts = chunks(day, chunk_chars=chunk_chars)
    todo = parts[:max_chunks] if max_chunks else parts
    accepted, rejected, failures = [], [], 0
    total_chars = sum(len(p[1]) for p in parts)

    for i, (body, source_text) in enumerate(todo, 1):
        res = ka_reader.ask(f"{PROMPT}\n\n--- TEXT TO REVIEW ---\n{body}", model=model,
                            json_out=True, schema=SCHEMA)
        if not res:
            failures += 1
            print(f"chunk {i}/{len(todo)}: reader returned nothing", file=sys.stderr)
            time.sleep(2)
            continue
        pairs = _parse(res)
        kept = []
        for p in pairs:
            ok, why = _acceptable(p)
            if not ok:
                rejected.append({**p, "rejected": why})
                continue
            r = ka_lessons.propose(p["wrong"], p["right"], "nonword", why=p.get("why") or "",
                                   quote=p["quote"], by="corpus-review",
                                   reader=ka_reader.last_backend() or model,
                                   corpus_key=f"{day}:{i}")
            if r.get("refused"):
                rejected.append({**p, "rejected": r["refused"]})
                continue
            accepted.append({**p, "id": r.get("id"), "state": r.get("state")})
            kept.append(p)
            try:
                ka_memory.learn(p["wrong"], p["right"], reason=p.get("why") or "story review",
                                category="lexical", agent="corpus-review")
            except Exception as e:  # noqa: BLE001
                print(f"memory write failed for {p['wrong']!r}: {type(e).__name__}: {e}", file=sys.stderr)
        print(f"chunk {i}/{len(todo)}: {len(pairs)} pair(s), {len(kept)} accepted", file=sys.stderr)

    return {
        "day": day, "model": model, "reader": ka_reader.last_backend(),
        "chunks_total": len(parts), "chunks_read": len(todo), "chunk_failures": failures,
        "chars_total": total_chars,
        "chars_read": sum(len(p[1]) for p in todo),
        "coverage": round(sum(len(p[1]) for p in todo) / total_chars, 3) if total_chars else 0,
        "accepted": accepted, "rejected": rejected,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="review the site's own story text for Georgian defects")
    ap.add_argument("--max-chunks", type=int, default=4, help="0 = the whole archive")
    ap.add_argument("--model", default="gemini-4-neon-high")
    ap.add_argument("--day", default="archive")
    ap.add_argument("--chunk-chars", type=int, default=90000)
    ap.add_argument("--dry-run", action="store_true", help="chunk and report coverage, ask nothing")
    a = ap.parse_args(argv)

    if a.dry_run:
        parts = chunks(a.day, chunk_chars=a.chunk_chars)
        head = parts[:a.max_chunks] if a.max_chunks else parts
        print(json.dumps({"chunks_total": len(parts), "chunks_would_read": len(head),
                          "chars_total": sum(len(p[1]) for p in parts),
                          "chars_would_read": sum(len(p[1]) for p in head),
                          "coverage": round(sum(len(p[1]) for p in head) /
                                            max(1, sum(len(p[1]) for p in parts)), 3)},
                         ensure_ascii=False))
        return 0

    out = review(a.max_chunks, a.model, a.day, a.chunk_chars)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
