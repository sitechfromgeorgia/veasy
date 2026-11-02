---
name: write-script
description: "Use when writing, repairing or reviewing the story JSON (narration + scenes) of a Veasy video (a tbilisi.today or SiTech Short) by hand or after the writer model failed a check. Examples: \"fix the script of 24886, check says N2\", \"write a story JSON for this cluster\", \"why does K9 fail\""
---

# Write or repair a story script

The script is `stories/<brand>/<day>/<ref>.json` under VEASY_HOME (`write` and the queue put it there). The full
rulebook is `tt_shorts/ka_style.md` (K1-K22 Georgian, N1-N12 news); this is the working summary. After every edit run
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
- Scene types and fields: `python -m tt_shorts.engine options` → `scenes` (each type's brush, `brushes/<type>.json`:
  when to use it, its slots with their length limits, an example). First scene `hook`, last `end`.
  3-7 scenes.
- On-screen texts have length limits (a kicker 24 characters, a headline 40, a hook line 24; the rest per slot):
  `check` names a text that is too long.

## Which scene for what (22 types)

| Type | Use it for | Fields |
|---|---|---|
| `hook` | what happened, 2-4 short lines | lines |
| `stat` | one number; with `icon`, a count of 2-30 things is drawn as that many icons | value, label, icon, style |
| `share` | a percent an article states with "%": a 10x10 grid fills to it | value (0-100), label |
| `rail` | 2-4 dated events in time order; a dot travels from one to the next | items [{when, label}] |
| `compare` | two values of one unit as squares of true proportion | items [{label, value}] x2, unit |
| `link` | who meets whom: 2-3 people or bodies joined by the verb | items [{name, role}], edge |
| `sign` | one thing and what happens to it: gas stops, prices rise, a bridge opens | icon, verb, label |
| `change` | one value then and now (the new one rolls up from the old) | before {label, value}, after {label, value}, unit |
| `bars` | 2-5 values of one kind, compared from zero | items [{label, value}], unit |
| `trend` | 3-8 values over time, a line that draws itself | items [{label, value}], unit, label |
| `timeline` | from-to times or dates the articles state | start, end, label |
| `where` | a place (in Georgia: the real map) | place, sub, area |
| `who` | 1-3 people or bodies (initials, no photos) | items [{name, role}] |
| `pair` | two sides: two parties, before and after, two offers | items [{title, sub}] x2, between |
| `steps` | 2-4 steps in order (a procedure, a sequence of events) | items ["..."] |
| `points` | 2-3 separate points | items ["..."] |
| `quote` | a verbatim quote with its speaker | text, by, via |
| `draw` | a drawing of what the story is about: what makes each video look different | svg, label |
| `agree`, `chapter` | rubrics only (`veasy:rubrics`) | code |
| `sources` | the outlets (from the data) | nothing |
| `end` | logo, QR, call to action | nothing |

- Charts (`bars`, `trend`, `change`) only with values the articles state, in one unit; never a computed difference.
  `bars` values are above zero. Numbers can be decimals (1.5 shows as 1,5).
- The brush kit:
  - `share`: only a percent an article writes with the % sign (`N2: ... (share) shows 34% but no source article
    states „34%“`); `value` 34 means 34%. Not for a count (use `stat`).
  - `rail`: each `when` is a date the articles give: „2 ნოემბერი“, „2025“, „22:00“ or „3 ნოემბერი, 10:00“, in time
    order (`check` reads them and sends back an event out of order or a date no article has). It needs 8 words.
  - `compare`: both values in one `unit`; if the larger is more than 40 times the smaller, use `bars`.
  - `link`: the first item met the others; `edge` is the verb exactly as that scene's narration says it
    (შეხვდა, მოაწერა ხელი): `N11` sends back an edge the voice doesn't say. Never imply a meeting the articles
    don't state.
  - `stat` `style`: `count` (default), `wheel` (an odometer) or `flap` (a split-flap board). Never `flap` for
    politics or crime: `check` refuses it.
- `"em"`: the marker. On 1-3 scenes, name the 1-4 words that matter most; they are drawn over (underline, box,
  circle, highlight or bracket: code picks, you don't) exactly when the voice says them.
  - Copy them word for word from that scene's on-screen text (a stat's or a share's value counts: `"em": "6400"`;
    the kicker never does) and say them in that scene's part of the narration (case endings may differ).
  - One per scene, not on `end` or `sources`. `N11: scene N marks „…“ but ...` names what is missing.
- `draw`: at most one per video. The style guide is `tt_shorts/art.py` GUIDE (line art, tokens INK, MUTED, LINE,
  CANVAS and ACCENT for the one focal part, motion classes r/p/s with `--d` delays, up to 4 Georgian labels).
  `check` sends back anything the whitelist removed. A drawing needs 8 narration words (about 3.5 s).
  `check` also judges the drawing itself (`art.quality`): big enough (40% of the width, 35% of the height), on
  the canvas, at least 3 moving parts with different delays, ACCENT on at most 6 elements. The automatic writer
  draws by default; a drawing that still fails after the repairs is swapped for a library drawing of the same
  motif (`tt_shorts/drawings.py`: the drawings of videos that ended `done`, and the seeds in `assets/drawings/`;
  only the labels the new story itself says are kept), else dropped, and the video goes out without it
  (`VEASY_WRITER_DRAW=0` turns drawing off).
- `where` in Georgia gets the real map on its own (`tt_shorts/geo.py`).
  - What it shows: Georgia's outline draws itself, the camera zooms to the region, which fills in, and a pin drops
    on the town. A Tbilisi district zooms into the city; two or three places get a marker each.
  - Write `place` as the article names it, in any case: ბათუმიდან, ვაკეში and ქუთაისის are all found. The
    `sub` line helps when a name is shared (ახალდაბა + ბორჯომი).
  - A name it doesn't know, or a foreign place, keeps the grid scene with the pin.
  - `area` is optional: `ge:<region>` (`options` → `areas`), `ge:<place id>` or `ge`, for when the place text
    doesn't name the region (e.g. a village).
  - Crime and incidents: the map stops at the region and never marks a district. This is code, not your choice.
  - Check it without a render: `python -c "from tt_shorts import geo; print(geo.locate('ვაკეში'))"`.
- Icons (`tt_shorts/icons.py`, 250 Lucide line icons; `options` → `icons` lists them):
  - `icon` is an English name (`flame`, `train-front`, `school`) or the Georgian word for the thing (`გაზი`,
    `მეტრო`, `სკოლა`); the stem map reads any case ending.
  - `sign`: the icon draws itself, then `verb` plays. The verbs are rises, falls, stops (a bar closes across it),
    opens, closes (doors), moves, splits and joins. The scene's own part of the narration must say that verb
    (გაიზარდა, შემცირდა, შეწყდება, გაიხსნება, დაიხურება, გადავა, გაიყო, შეუერთდა): N10. It needs 7 narration words
    (3.2 s). Use it for a change to one thing, not for a person or an event.
  - `stat` with `icon`: a whole count of 2-30 from the articles shows as that many icons; the number counts with
    them. Anything else (a percent, 6400, 2.5) keeps the bar.
  - The story's `"motif"` (optional) is its main icon, tiled faintly in the background when variety picks the icon
    motif; without one, the first icon the hook names (or the first sign's) is used.
  - Never for crime, incidents or a story about deaths (N10): no sign, no stat icon, no motif.
- Vary the shape: the writer is shown the scene orders the latest videos used; pick another one when the story's
  facts allow it (a number → stat, bars or change; a place → where; two sides → pair; a process → steps; one thing
  that stops, opens or rises → sign).

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

## A story of another program

A story with `"program"` (explainer, law, blog; `veasy:programs`) follows its brief in `programs/briefs/<name>.md`
instead of the news rules N5-N9, and its scene list. `program`, `source` (the document's title, article, url) and
`link` come from the data, like `id`, `date` and `sources`. Its rule tier adds:
- `C1: the name 'X' is not in the source document`: every Latin name, every person in `who` and a quote's `by` must
  be in the document (the brand's own names and the outlets are fine).
- `L1` show the article number on screen (hook kicker „კონსტიტუცია · მუხლი 17“); `L2` no advice („უნდა მიმართო“,
  „შეგიძლია“, „გირჩევ“: say „ყველას აქვს უფლება“); `L3` name the act in the narration.
- `timing: ... program law wants 25-45s`: about 0.75 s per Georgian word; 45-58 words fit.
- The writer moves the end card to the last sentence and drops it when that sentence has fewer than 4 words: end
  with a call to action of 4+ words.

## Common check failures

- `K9 … gets only N narration words`: a scene starts too late or too close to the next; move its `at` earlier,
  add words to that part, or merge it into a neighbour.
- `N2: number X is not in any source article`: remove it or use the article's own figure; don't compute. It reads
  chart values and drawing labels too (not a drawing's coordinates).
- `draw: ...`: the drawing used something the whitelist doesn't allow (a tag, a color that isn't a token, a style
  other than `--d:0.5s`); fix that part, the rest of the drawing is kept.
- `N3: quote is not verbatim`: copy the exact words or turn it into reported speech without „…".
- `N10: scene N (sign) shows „stops“ but its part of the narration doesn't say it`: say the verb between this
  scene's `at` and the next one's, move `at`, or pick the verb the narration says. `N10: no pictograms in a story
  about ...`: drop the sign scene (use another type), the stat's `icon` and the story's `motif`.
- `icon: 'x' is neither an icon name nor a Georgian word the map knows`: use a name from `options` → `icons`.
- `timing: scene anchor not in narration`: `at` must match the narration word for word (punctuation is ignored).
