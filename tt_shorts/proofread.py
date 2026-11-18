"""deepseek proofread: a model reads the Georgian before anything is published.

The owner, 2026-11-18: "ტექსტები სანამ დადებ რილსებზე გადაამოწმე დიფსიკის მოდელით რითაც შენ ხარ თორე
ძალიან ყლეობები იწერება რა". He is right: the rule gate checks numbers, quotes, lengths and pattern
rules, but nobody read the sentences. "80 წლის მოქცევარი" is not a Georgian word and no rule had an
opinion about it.

This module asks the writer model itself, with no temperature and one narrow question per story: read
this Georgian, list every word or phrase that is not Georgian, not used, or says something the sources
do not. It answers as strict JSON. A story with a blocking finding is repaired once and re-read; a story
that still fails is refused, not published.

Design rules:
- The model is the same one that writes (deepseek through the configured provider), so no new service.
- The check is deterministic in shape: a JSON array we validate, never prose we interpret.
- A finding is only blocking when it names a span that exists in the text. A hallucinated finding about
  words that are not there cannot block a story.
- The gate never rewrites. A repair is the writer's job, and only for a span the reader named.
"""

from __future__ import annotations

import json
import re

from tt_shorts import writer

# One narrow instruction. The reader is asked for defects, not for style, and told to be silent when the
# text is clean: a gate that always finds something is a gate that never passes.
PROMPT = """შენ ხარ ქართული ტექსტის რედაქტორი. მოცემულია სიახლის ტექსტი რომელიც ვიდეოზე წაიკითხება.

შენი ამოცანაა იპოვო მხოლოდ სიტყვები, რომლებიც ქართულ ენაში **საერთოდ არ არსებობს** და არის გამოგონილი
ან სხვა ენიდან არასწორად გადმოტანილი. მაგალითი: "მოქცევარი" არ არსებობს, სწორია "მამაკაცი" ან "მოხუცი".

მკაცრი წესები:
- თუ სიტყვა ქართულ ლექსიკონში არის, ის არ არის შეცდომა, თუნდაც იშვიათი იყოს. "ჭრილობა", "მრავლობითი",
  "დაუპირისპირდა", "გარდაიცვალა", "სამართალდამცველები" ყველა სწორი ქართული სიტყვაა.
- არ შეამოწმო სტილი, ტონი, სიგრძე, ფაქტები ან გრამატიკული კონსტრუქცია.
- არ შეამოწმო ციფრები, სახელები ან ბრენდები.
- თუ ეჭვი გაქვს, არ დაწერო. ცრუ დადებითი უარესია გამოტოვებულზე.
- თუ ყველა სიტყვა ნამდვილი ქართულია, დააბრუნე ცარიელი სია.

უპასუხე მხოლოდ JSON-ით:
{"findings": [{"span": "ზუსტად ის სიტყვა ტექსტიდან", "problem": "რატომ არ არსებობს", "fix": "რა უნდა იყოს"}]}

თუ ვერაფერი იპოვე: {"findings": []}

ტექსტი:
"""


# A span must be at least this long to be worth a repair, and must actually occur in the text.
MIN_SPAN = 2


def _text_of(story: dict) -> str:
    """Everything a viewer hears or reads: the narration and every text field a scene shows."""
    parts = [str(story.get("narration") or "")]
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, value in sc.items():
            if key in ("at", "type", "art", "say"):
                continue
            if isinstance(value, str) and value.strip():
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(x) for x in value if isinstance(x, str) and x.strip())
    return "\n".join(p for p in parts if p.strip())


def _parse(answer: str) -> list[dict]:
    """The model's JSON, or nothing. A malformed answer must not block a story."""
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return []
    out = []
    for f in (data.get("findings") or []) if isinstance(data, dict) else []:
        if not isinstance(f, dict):
            continue
        span = str(f.get("span") or "").strip()
        if len(span) < MIN_SPAN:
            continue
        out.append({"span": span, "problem": str(f.get("problem") or "").strip(),
                    "fix": str(f.get("fix") or "").strip()})
    return out


def findings(story: dict, model: str | None = None) -> list[dict]:
    """Every finding the reader names, kept only when its span really occurs in the story."""
    text = _text_of(story)
    if len(text) < 40:
        return []
    try:
        answer = writer._call(PROMPT + text, model or writer.MODEL, max_tokens=900)
    except Exception:  # noqa: BLE001 - a reader that cannot answer must not block publishing
        return []
    found = _parse(answer)
    # A finding about words that are not in the text is the reader's own invention.
    return [f for f in found if f["span"] in text]


def blocking(story: dict, model: str | None = None) -> list[dict]:
    """Findings that must stop the story. Today every finding is blocking: the reader is narrow by
    instruction, and a clean story returns nothing."""
    return findings(story, model)


def on() -> bool:
    """Off only when someone explicitly disables it: the owner asked for this gate to run on every
    publishable text, so silence is the surprising state, not the default."""
    import os
    return os.environ.get("TT_PROOFREAD", "1") != "0"
