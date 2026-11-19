"""The daily corpus review: one model pass over everything we published, feeding kaeasy's own tables.

The owner, 2026-11-18: "დღეში ერთხელ მერე მოგცემ gemini cli-ის რომლის საშუალებითაც იმ ტქსტებში
გამოავლენს შესცომებს, დახარჯავს ნაკლებ ტოკენს ეგრე და გააუმჯობესებს KAeasy-ის ექნება საუკეთესო ბაზა".

This runs once a day, after the publishing day closes, and does three things:

1. Reads yesterday's corpus (the exact texts that were published, see `corpus.py`).
2. Asks a model for defects in a strict JSON shape: the wrong span, what is wrong, the correct form.
3. Writes each accepted pair into kaeasy's shared memory, so the strict gate refuses it tomorrow. The
   reviewer's own output never becomes a rule directly: a pair is accepted only when the wrong form does
   not occur in the corrected form, both are Georgian, and the wrong form is still absent from kaeasy's
   lexical allow-lists. A reviewer that invents a rule is worse than no reviewer.

Why the corpus makes this cheap: the same review over the live site would re-read thousands of articles
a day. The corpus holds only what was published, already deduplicated by record key, so a day's material
is a few dozen blocks and one call.

The report is written to `data/corpus/reports/<day>.json` so a human can read what was learned, and so a
bad batch can be inspected after the fact.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

from tt_shorts import corpus, kaeasy, normalize_ka

REPORTS = corpus.CORPUS / "reports"

PROMPT = """შენ ხარ ქართული ტექსტის რედაქტორი, რომელიც ამოწმებს გამოქვეყნებულ ტექსტებს.

წესი პირველი: **თუ ტექსტი სწორია, დააბრუნე ცარიელი სია.** შენი ამოცანა არ არის შეცდომის მოძებნა
ნებისმიერ ფასად, არამედ იმის თქმა, არის თუ არა სიტყვა ნამდვილი ქართული და სწორ ფორმაში.

დაწერე წყვილი მხოლოდ მაშინ, როცა:
1. სიტყვა ქართულ ენაში **საერთოდ არ არსებობს** (გამოგონილი, ან სხვა ენიდან არასწორად გადმოტანილი).
   მაგალითი: "მოქცევარი" არ არსებობს, სწორია "მამაკაცი".
2. სიტყვის ფორმა **ყოველთვის** არასწორია, არა მხოლოდ ამ წინადადებაში.
   მაგალითი: "პატროლი" არ არსებობს, სწორია "პატრული".

**არ დაწერო**, თუ:
- სიტყვა ლექსიკონში არის, თუნდაც იშვიათი იყოს;
- შეცდომა სტილის, ტონის, სიგრძის ან პუნქტუაციისაა;
- ეს არის სახელი, ბრენდი, ციფრი ან ტერმინი;
- wrong და right ერთი და იგივეა (ეს ნიშნავს რომ შეცდომა არ არის).

უპასუხე მხოლოდ JSON-ით:
{"pairs": [{"wrong": "არასწორი ფორმა", "right": "სწორი ფორმა", "why": "მოკლე ახსნა"}]}

თუ ყველაფერი სწორია: {"pairs": []}

ტექსტები:
"""


def _georgian(text: str) -> bool:
    return bool(re.search(r"[ა-ჰ]", text or "")) and not normalize_ka.LATIN.search(text or "")


# The schema the reader must answer in. It is not documentation: `--json-schema` is what makes agy a
# single structured turn instead of an agent loop (see tt_shorts/reader._agy), and it is what the parse
# below can trust. The prompt asks for the same shape, so a backend that ignores the flag still matches.
PAIRS_SCHEMA = {
    "type": "object",
    "properties": {
        "pairs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"wrong": {"type": "string"}, "right": {"type": "string"},
                               "why": {"type": "string"}},
                "required": ["wrong", "right"],
            },
        }
    },
    "required": ["pairs"],
}


def _parse(answer: str) -> list[dict]:
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return []
    out = []
    for p in (data.get("pairs") or []) if isinstance(data, dict) else []:
        if not isinstance(p, dict):
            continue
        wrong = str(p.get("wrong") or "").strip()
        right = str(p.get("right") or "").strip()
        if len(wrong) < 3 or len(right) < 3:
            continue
        out.append({"wrong": wrong, "right": right, "why": str(p.get("why") or "").strip()})
    return out


def _acceptable(pair: dict, day_text: str) -> tuple[bool, str]:
    """A pair is a rule only when it is safe to refuse that form forever."""
    wrong, right = pair["wrong"], pair["right"]
    if wrong == right:
        return False, "same"
    if not _georgian(wrong) or not _georgian(right):
        return False, "not Georgian"
    if wrong in right:
        return False, "the wrong form is inside the right one"
    if wrong not in day_text:
        return False, "the wrong form is not in today's texts"
    return True, ""


def _propose(pairs: list[dict], day_text: str, day: str | None = None) -> tuple[list[dict], list[dict]]:
    """Record the reader's findings as lesson candidates in kaeasy's ledger.

    Until now a pair went straight into the shared memory, which is a prompt aid: it never had a state,
    never waited for attestation and could never be retired. `lessons.propose` is the path that can:
    the candidate is verified against the word index by `lessons.tick`, promoted to a warning, and only
    then considered for the gate. A pair this lane cannot justify is refused at intake and reported.
    """
    from kaeasy import lessons as ka_lessons
    from tt_shorts import reader as ka_reader
    # Stamp the backend that actually answered. The old hardcoded reader="agy" was false whenever agy
    # returned nothing and the writer model produced the pairs (measured 2026-11-19), which makes a
    # lesson's provenance unauditable.
    who = ka_reader.last_backend()
    accepted, rejected = [], []
    for p in pairs:
        ok, why = _acceptable(p, day_text)
        if not ok:
            rejected.append({**p, "rejected": why})
            continue
        try:
            r = ka_lessons.propose(p["wrong"], p["right"], "nonword", why=p.get("why") or "",
                                   quote=p.get("quote") or _quote_for(p["wrong"], day_text),
                                   by="corpus-review", reader=who, corpus_key=day)
        except Exception as e:  # noqa: BLE001
            rejected.append({**p, "rejected": f"propose failed: {e}"})
            continue
        if r.get("refused"):
            rejected.append({**p, "rejected": r["refused"]})
        else:
            accepted.append({**p, "id": r.get("id"), "state": r.get("state")})
    return accepted, rejected


def _quote_for(word: str, text: str) -> str:
    """The sentence carrying the word, which is the evidence a lesson must hold."""
    i = text.find(word)
    if i < 0:
        return ""
    start = max(text.rfind(".", 0, i), text.rfind("\n", 0, i)) + 1
    end = text.find(".", i)
    return text[start:(end + 1 if end > 0 else i + len(word) + 40)].strip()


def review(day: str | None = None, model: str | None = None, dry: bool = False,
           chunk_chars: int = 24000) -> dict:
    """Read one day's corpus, ask for defects, and teach kaeasy the ones worth teaching.

    A day is read in chunks rather than one call. Measured 2026-11-19: once the site's own articles joined
    the corpus, a day's digest was 428k chars and the model refused it
    ("Please reduce the length of the messages"), so the whole day was lost on one oversized request.

    `chunk_chars` is sized from the measured structured-turn cost, not from the model's window: one
    47k-char prompt took 101 s and 51k tokens, and the reader's own timeout is 240 s, so a 90k chunk
    would time out and fall back to the writer for every chunk. 24k keeps the call near a minute.
    """
    records = corpus.load(day)
    if not records:
        return {"day": day, "records": 0, "pairs": 0, "accepted": [], "rejected": [],
                "note": "no corpus for this day"}
    text = corpus.digest(day)
    from tt_shorts import reader
    # agy on the owner's subscription is the daily reader; the writer model is the fallback.
    pairs: list[dict] = []
    chunks, failures = 0, 0
    for i in range(0, len(text), chunk_chars):
        part = text[i:i + chunk_chars]
        if len(part.strip()) < 500:  # a sliver at the end is not worth a call
            continue
        chunks += 1
        try:
            answer = reader.ask(PROMPT + part, model=model, max_tokens=1500, json_out=True,
                                schema=PAIRS_SCHEMA)
        except Exception as e:  # noqa: BLE001 - one bad chunk must not lose the rest of the day
            failures += 1
            print(f"chunk {chunks} failed: {type(e).__name__}: {str(e)[:160]}", file=sys.stderr)
            continue
        pairs.extend(_parse(answer))
    # The same pair can be found twice across chunks (an outlet repeats a story); keep the first.
    seen: set[tuple[str, str]] = set()
    unique = []
    for p in pairs:
        key = (str(p.get("wrong") or "").casefold(), str(p.get("right") or "").casefold())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    pairs = unique
    day_text = "\n".join(r.get("text", "") for r in records)
    # A day whose every chunk failed is not a clean day. Before this guard the run reported
    # {"pairs": 0, "accepted": []} and read as "the Georgian was fine", which is how five failed chunks
    # went unnoticed on 2026-11-19. Silence about a day must be earned by reading it.
    if chunks == 0 or failures >= chunks:
        return {"day": day or records[0].get("day"), "records": len(records), "chars": len(text),
                "chunks": chunks, "chunk_failures": failures, "pairs": 0,
                "accepted": [], "rejected": [],
                "error": f"the reader failed on {failures} of {chunks} chunks: the day was not reviewed"}
    if dry:
        accepted, rejected = [], [{"note": "dry run, nothing written"}]
    else:
        accepted, rejected = _propose(pairs, day_text, day)
    report = {"day": day or records[0].get("day"), "records": len(records), "chars": len(text),
              "chunks": chunks, "chunk_failures": failures, "reader": reader.last_backend(),
              "pairs": len(pairs), "accepted": accepted, "rejected": rejected}
    if not dry:
        REPORTS.mkdir(parents=True, exist_ok=True)
        (REPORTS / f"{report['day']}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                                     encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="review a day of the published corpus and teach kaeasy")
    ap.add_argument("--day", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--dry", action="store_true", help="read and report, write nothing to kaeasy")
    a = ap.parse_args(argv)
    r = review(a.day, a.model, a.dry)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
    # A day that was not read is a failure the caller must see: the cron wrapper prints one line and the
    # platform watchdog treats a non-zero exit as a real stall. Exit 0 here would hide it as "clean".
    return 3 if r.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
