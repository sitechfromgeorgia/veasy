---
name: write-script
description: "Use when writing, repairing or reviewing the story JSON (narration + scenes) of a tbilisi.today Short by hand or after the writer model failed a check. Examples: \"fix the script of 24886, check says N2\", \"write a story JSON for this cluster\", \"why does K9 fail\""
---

# Write or repair a story script

The script is `stories/<id>.json`. The full rulebook is `tt_shorts/ka_style.md` (K1-K22 Georgian, N1-N9 news); this
is the working summary. After every edit run
`python -m tt_shorts.engine check stories/<id>.json --sources stories/<id>.sources.json` until `problems` is empty.

## Shape

```json
{"id": 24886, "category": "politics", "date": "2026-11-02T10:00:00Z", "sources": ["..."],
 "narration": "the spoken text", "say": {"Türk": "თურქ"}, "cta": "გამოიწერე არხი",
 "scenes": [{"type": "hook", "at": "first words", "kicker": "მსოფლიო", "lines": ["...", "..."]}, ...]}
```
- `id`, `date`, `sources` come from D1 (the writer and you never invent them).
- `at` is the exact first words of the narration where that scene starts, in order.
- Scene types and fields: `python -m tt_shorts.engine options` → `scenes`. First scene `hook`, last `end`.
  `sources` needs no fields (it shows the outlets from the data). 3-7 scenes.

## Narration

- 25-45 s spoken: about 55-75 words, sentences of 6-14 words, one idea each, active voice, who did what.
- Start with what happened (the hook says it in 6-8 words), then the source ("შსს-ს ცნობით").
- Every number and every quote must be in the member articles (N2, N3). A quote is verbatim, in „…", with the speaker.
- No relative days (დღეს, გუშინ, ხვალ): name the date (N4). No opinion or evaluative words (N1). No „!", no em dash.
- Talk to the viewer as შენ (K1): "გამოიწერე", not "გამოიწერეთ".
- End with „დეტალები იხილე tbilisi.today-ზე." and a short call to action that matches `cta`.
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
- `N2: number X is not in any source article`: remove it or use the article's own figure; don't compute.
- `N3: quote is not verbatim`: copy the exact words or turn it into reported speech without „…".
- `timing: scene anchor not in narration`: `at` must match the narration word for word (punctuation is ignored).
