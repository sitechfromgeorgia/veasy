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


def _apply(pairs: list[dict], day_text: str) -> tuple[list[dict], list[dict]]:
    """Write the acceptable pairs into kaeasy's shared memory."""
    accepted, rejected = [], []
    for p in pairs:
        ok, why = _acceptable(p, day_text)
        if not ok:
            rejected.append({**p, "rejected": why})
            continue
        try:
            saved = kaeasy.learn(p["wrong"], p["right"], reason=p.get("why") or "daily corpus review",
                                 category="grammar", agent="corpus-review")
        except Exception as e:  # noqa: BLE001
            rejected.append({**p, "rejected": f"learn failed: {e}"})
            continue
        accepted.append({**p, "learned": bool(saved)})
    return accepted, rejected


def review(day: str | None = None, model: str | None = None, dry: bool = False) -> dict:
    """Read one day's corpus, ask for defects, and teach kaeasy the ones worth teaching."""
    records = corpus.load(day)
    if not records:
        return {"day": day, "records": 0, "pairs": 0, "accepted": [], "rejected": [],
                "note": "no corpus for this day"}
    text = corpus.digest(day)
    from tt_shorts import reader
    # agy on the owner's subscription is the daily reader; the writer model is the fallback.
    answer = reader.ask(PROMPT + text, model=model, max_tokens=1500, json_out=True)
    pairs = _parse(answer)
    day_text = "\n".join(r.get("text", "") for r in records)
    accepted, rejected = ([], [{"**": "dry"}] if dry else _apply(pairs, day_text))
    report = {"day": day or records[0].get("day"), "records": len(records), "chars": len(text),
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
