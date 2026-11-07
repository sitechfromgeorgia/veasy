---
name: scenarios
description: "Use when a Veasy film should follow a plot (a guessing game, a countdown, a day in a life, a deadline, before and after) instead of just a list of facts; when asked which plot fits a story, or to see a storyboard before paying for the writer; when adding a plot. Examples: \"tell this as a guessing game\", \"which scenario fits story 24835\", \"make a film from this URL as a countdown\", \"preview the storyboard first\", \"add a scenario\""
---

# Scenarios (plots)

A **scenario** is the plot of a film: its beats in order, and the job of each beat (promise, setup, false lead,
complication, evidence, turn, payoff, resolution). Same facts, different plot: "how many readers?" as a guessing game
holds the figure to the last scene; as a cold open it says it in the first. Code checks the plot for free, before any
voice or render is paid for. The writer never picks one: `story["scenario"]` is code's, like `rubric` and `date`.

## The one line

```
python -m tt_shorts.engine make "<url or story>" --scenario auto --preview-storyboard
```

You get the plot code chose for the source's facts, its storyboard (a scene per beat, with the job, the allowed scene
types, the word budget, the sound), and the ranked runners-up. **The writer has not been called** (`writer_called:
false`). Run it again without `--preview-storyboard` and the writer gets the beats, the repairs hold the story to them,
and code stamps the scenario. `--length short|standard|long|45` moves the ranking toward plots whose window fits.

## Commands (all free)

Every `engine ...` below is `python -m tt_shorts.engine ...` (or the plugin tool `veasy_scenario`). `stamp` sets a plot on
a story that has none (on a story that already has one it replaces it). `fit`
also compares the story's total words with the plot's window; a miss only lowers the rank, while `check` holds each
beat to its own word budget.

| command | what it does |
|---|---|
| `engine scenario list` | the 24 plots: label, beats, word window, what facts they need |
| `engine scenario fit <story>` | rank the plots that fit this story's facts, each with the reason (`--length`) |
| `engine scenario board <id>` | one plot's storyboard: beat, job, scenes, words, sound, which beats hold the payoff |
| `engine scenario stamp <story> --scenario <id\|auto>` | put the plot on a hand-written story (in place) and check it |
| `engine scenario check <story>` | the beat checks alone (they also run in `check` and `plan`) |
| `engine write --scenario <id\|auto> ...` | write from a source with the plot's beats |

## What the free checks hold the story to

A story with a scenario has **exactly one scene per beat**, in order. Each scene is checked for:

1. **the scene type**: one of the beat's `scene_types` (the beat's brushes);
2. **the word budget**: narration words from the scene's `at` to the next scene's `at` inside the beat's range;
3. **fact gates**: a payoff beat needs a number, a quote beat a quote;
4. **the payoff is not said early**: the payoff scene's figure (`value`, `em`, a pair's `sub`) is not in the narration
   of a scene before it. "18 600" and "18600" are one figure;
5. **the program**: `news` refuses a scenario (no plotted story: a story with no `program` is news); `check` says
   `program 'news' refuses scenarios`;
6. **myth-vs-fact** only when the document itself corrects (a `doc_correction`, or the correction's own words in the
   text). Otherwise it is an opinion scene: refused. Never use it to correct something the document does not.

## A long film: a plot per chapter

`story["scenario"]` may be a list of ids, one per chapter (`engine scenario stamp <story> --scenario a,b`). Chapter 1
keeps its hook, a later chapter has none (the film's hook opened it); a chapter before the last has no end card. The
story's scenes are the chapters' beats in order, and `check`/`plan` hold each chapter to its own plot
(`chapter 2 (before-and-after): ...`). `news`, `digest` and `story` refuse chapters too. The explainer program's own
25-45 s window still applies: a long film needs a longer program or format.

## Choosing by hand

`fit` ranks by what the facts allow (declarative `eligible`/`never`, same grammar as rubrics), then by what each plot
`prefers`, then by whether the story's scenes already carry its beats and its words fit. A short list:

| plot | use it when the document has | the turn |
|---|---|---|
| guess-the-number, three-clues, countdown | one big figure; three facts; a ranking | the figure lands last |
| before-and-after, rise-and-peak, reverse-chronology, cold-open | a then and a now; a series; a date trail | what changed / how it came about |
| false-lead | a plan or forecast and the result | the figure that came out instead |
| rule-and-exception, step-by-step, deadline, what-changes-for-you | a rule, steps, a date, an impact | the exception, the catch, the end |
| head-to-head, two-voices, says-and-shows, profile | two sides, two quotes, a claim and figures | the gap / what they share |
| object-biography, map-tour, day-in-a-life, cause-and-effect, money-trail, what-is-it, chase-through-document | places, hours, a chain, amounts, a term, sections | the end of the trail |
| myth-vs-fact | a correction the document itself makes | the correction |

Every plot says what the document says. The `brief` of a scenario is added to the writer's prompt; no plot lets the
writer judge, advise or invent a figure (the program's rules still run).

## Writing a story by hand for a plot

1. `engine scenario board <id>`: the beats, their words, and the scene types you may use.
2. One sentence or two per beat; the scene's `at` is the first words of its sentence (a number in the `at` is fine).
3. Keep the end card's sentence last (the call to action, 4 words or more: that is the `closing` beat).
4. `engine scenario stamp <story> --scenario <id>` then `engine check <story>` and `engine plan <story>`.
   The demos `stories/scenario-<id>.json` are working examples of each plot.

## Sound

A beat has a `sound` (whoosh, click, tick, pop, thud, blip, or null for none). With `--sfx on` (format key `sfx`) the
cues land on the timeline: the promise opens with a whoosh, the payoff with a thud. They are synthesized by
`tools/compose_sfx.py`, at one constant level: no risers, no ducking.

## Adding a plot

A new file `scenarios/<id>.json` (copy a close one; `scenarios/schema.json` lists the keys): beats with a free `id`, a
`job`, `scene_types` from the program's scene list, a `word_budget` the `explainer` brief can carry (about 45-58 words
in all), `payoff_held: true` on every beat before the reveal; `eligible` as facts (`numbers`, `quotes`, `steps`,
`dates`, ...) never code; `prefers` weights 1-3. Add `stories/scenario-<id>.json` and a case in
`tests/test_scenarios.py` (the demo test covers every scenario by itself: it must pass `check` and its own beats).
