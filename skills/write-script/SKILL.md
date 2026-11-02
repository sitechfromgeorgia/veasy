---
name: write-script
description: "Use when writing, repairing or reviewing the story JSON (narration + scenes) of a Veasy video (a tbilisi.today or SiTech Short) by hand or after the writer model failed a check. Examples: \"fix the script of 24886, check says N2\", \"write a story JSON for this cluster\", \"why does K9 fail\""
---

# Write or repair a story script

The script is `stories/<brand>/<day>/<ref>.json` under VEASY_HOME (`write` and the queue put it there). The full
rulebook is `tt_shorts/ka_style.md` (K1-K22 Georgian, N1-N9 news); this is the working summary. After every edit run
`python -m tt_shorts.engine check <story.json> --sources <story>.sources.json` until `problems` is empty.

## Shape

```json
{"id": 24886, "brand": "tbilisi-today", "category": "politics", "date": "2026-11-02T10:00:00Z", "sources": ["..."],
 "narration": "the spoken text", "say": {"Türk": "თურქ"}, "cta": "გამოიწერე არხი",
 "scenes": [{"type": "hook", "at": "first words", "kicker": "მსოფლიო", "lines": ["...", "..."]}, ...]}
```
- `id`, `date`, `sources` come from the source's data (the writer and you never invent them). `brand` picks the
  pack (`veasy:brands`); its categories are in `options --brand <name>`.
- `at` is the exact first words of the narration where that scene starts, in order.
- Scene types and fields: `python -m tt_shorts.engine options` → `scenes`. First scene `hook`, last `end`.
  `sources` needs no fields (it shows the outlets from the data). 3-7 scenes.

## Which scene for what (15 types)

| Type | Use it for | Fields |
|---|---|---|
| `hook` | what happened, 2-4 short lines | lines |
| `stat` | one number | value, label |
| `change` | one value then and now (the new one rolls up from the old) | before {label, value}, after {label, value}, unit |
| `bars` | 2-5 values of one kind, compared from zero | items [{label, value}], unit |
| `trend` | 3-8 values over time, a line that draws itself | items [{label, value}], unit, label |
| `timeline` | from-to times or dates the articles state | start, end, label |
| `where` | a place | place, sub |
| `who` | 1-3 people or bodies (initials, no photos) | items [{name, role}] |
| `pair` | two sides: two parties, before and after, two offers | items [{title, sub}] x2, between |
| `steps` | 2-4 steps in order (a procedure, a sequence of events) | items ["..."] |
| `points` | 2-3 separate points | items ["..."] |
| `quote` | a verbatim quote with its speaker | text, by, via |
| `draw` | a drawing of what the story is about: what makes each video look different | svg, label |
| `sources` | the outlets (from the data) | nothing |
| `end` | logo, QR, call to action | nothing |

- Charts (`bars`, `trend`, `change`) only with values the articles state, in one unit; never a computed difference.
  `bars` values are above zero. Numbers can be decimals (1.5 shows as 1,5).
- `draw`: at most one per video. The style guide is `tt_shorts/art.py` GUIDE (line art, tokens INK, MUTED, LINE,
  CANVAS and ACCENT for the one focal part, motion classes r/p/s with `--d` delays, up to 4 Georgian labels).
  `check` sends back anything the whitelist removed. A drawing needs 8 narration words (about 3.5 s).

## Narration

- 25-45 s spoken: about 55-75 words, sentences of 6-14 words, one idea each, active voice, who did what.
- Start with what happened (the hook says it in 6-8 words), then the source ("შსს-ს ცნობით").
- Every number and every quote must be in the member articles (N2, N3). A quote is verbatim, in „…", with the speaker.
- No relative days (დღეს, გუშინ, ხვალ): name the date (N4). No opinion or evaluative words (N1). No „!", no em dash.
- Talk to the viewer as შენ (K1): "გამოიწერე", not "გამოიწერეთ".
- End with where the details are and a short call to action that matches `cta`: tbilisi.today „დეტალები იხილე
  tbilisi.today-ზე. გამოიწერე არხი.", SiTech „... გამოიწერე SiTech." (the pack's `say` reads SiTech as საი-თეჩი).
- Latin names: the screen keeps them, the voice reads `lexicon_ka.json` or the story's `say` map (K20).

## Georgian beyond these rules: kaeasy

The engine's Georgian gate is SiTech's kaeasy plugin.
- `check` returns kaeasy's blocking findings as `problems`: strict rules as `KE:` and mapped rules under their K number.
  It returns the rest as `warnings`; read them, fix what is right to fix.
- When the agent runs on Hermes with kaeasy enabled, load `kaeasy:georgian-writing` (and `kaeasy:georgian-speech`
  for what the voice reads) before writing by hand.
- After a human or a review corrects a phrase, record it with `ka_learn` so every agent avoids it.

## Common check failures

- `K9 … gets only N narration words`: a scene starts too late or too close to the next; move its `at` earlier,
  add words to that part, or merge it into a neighbour.
- `N2: number X is not in any source article`: remove it or use the article's own figure; don't compute. It reads
  chart values and drawing labels too (not a drawing's coordinates).
- `draw: ...`: the drawing used something the whitelist doesn't allow (a tag, a color that isn't a token, a style
  other than `--d:0.5s`); fix that part, the rest of the drawing is kept.
- `N3: quote is not verbatim`: copy the exact words or turn it into reported speech without „…".
- `timing: scene anchor not in narration`: `at` must match the narration word for word (punctuation is ignored).
