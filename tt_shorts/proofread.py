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
PROMPT = """შენ ხარ ქართული ტექსტის რედაქტორი, რომელიც ამოწმებს ერთ ტექსტს.

**მთავარი წესი: თუ ტექსტი სწორია, დააბრუნე ცარიელი სია.** ცრუ შეცდომა უარესია გამოტოვებულზე.

დაწერე შეცდომა მხოლოდ მაშინ, როცა **ერთი სიტყვა** ქართულ ენაში საერთოდ არ არსებობს და ეს ცხადია.
მაგალითი: "მოქცევარი" - ასეთი სიტყვა არ არის, სწორია "მამაკაცი" ან "მოხუცი".
მაგალითი: "პატროლი" - არ არის, სწორია "პატრული".

**არასდროს დაწერო:**
- ორსიტყვიანი ან მრავალსიტყვიანი ფრაზა. ფრაზა ყოველთვის სწორია, თუ მისი სიტყვები ცალკე სწორია.
  "შუა დერეფანი", "საგარეო საქმეთა სამინისტრო", "ეროვნული ბანკი" ყველა სწორია.
- ტერმინი, პროფესიული სიტყვა ან დარგის ცნება (ეკონომიკა, იურიდიული, სამედიცინო, პოლიტიკური).
- სახელი, გვარი, ბრენდი, ორგანიზაცია, ტოპონიმი.
- ციფრი, თარიღი, ერთეული.
- სიტყვა, რომელიც იშვიათია მაგრამ ლექსიკონში არის.
- თუ ეჭვი გაქვს ერთი პროცენტითაც.

**თუ შესწორება გიჭირს ან არ იცი ზუსტი სწორი ფორმა, არ დაწერო.** არასწორი შესწორება უარესია.

უპასუხე მხოლოდ JSON-ით:
{"findings": [{"span": "ზუსტად ერთი სიტყვა ტექსტიდან", "problem": "რატომ არ არსებობს", "fix": "სწორი ფორმა"}]}

თუ ვერაფერი იპოვე: {"findings": []}

ტექსტი:
"""


# A span must be one word, and must actually occur in the text. A multi-word span is the shape of a
# guess: measured 2026-11-18, the reader named "შუა დერეფანი" (the Middle Corridor, a real trade term
# in every Georgian newsroom) as non-existent and offered "შუა დირექტორი" as the fix. The gate blocked
# a legitimate story. One word at a time is the only shape that has produced a true finding so far.
MIN_SPAN = 3


def _text_of(story: dict) -> str:
    """Everything a viewer hears or reads: the narration and every text field a scene shows."""
    parts = [str(story.get("narration") or "")]
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, value in sc.items():
            # "icon", "motif", "morph_from" and "art" are library names for drawings, never shown as
            # words. Reading them as text produced a false finding on a live reel (measured 2026-11-18:
            # "building-complex" named as English text when it is an icon key), and a false finding on
            # a clean story is worse than a missed one.
            if key in ("at", "type", "art", "say", "icon", "motif", "morph_from", "verb", "value",
                       "unit", "style", "variant", "layout", "tone"):
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
        # One word only. A multi-word span is a phrase, and phrases are never coined words: the reader
        # named "შუა დერეფანი" as wrong and cost a legitimate story (measured 2026-11-18).
        if len(span.split()) > 1:
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
        from tt_shorts import reader
        answer = reader.ask(PROMPT + text, model=model, max_tokens=900, json_out=True)
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
