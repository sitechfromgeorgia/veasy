# GOAL 6, the scenario library: result

Branch `goal/scenario-library`. Antigravity left a draft (commit `38d2166`); Claude Code resumed, verified it and
finished it. Not rebased onto main (the integrating session does that). Nothing pushed or merged.

## Done when, with evidence

| Done-when line | Status | Evidence |
|---|---|---|
| 24 scenarios validate, each with a Georgian demo story that passes `check` and `plan` | done | `scenarios/*.json` (24); `stories/scenario-<id>.json` (24); `tests/test_scenarios.py::TestData`, `TestDemoStories` (check + the beat checks on all 24). `engine plan` run on all 24: `docs/research/scenario-plan-24.txt` (the two `probe overflow` problems in it, `9 800`, were fixed by changing the demo's figure and re-planned clean; warnings are motion advice only) |
| `engine scenario fit` runs on 10 stories and its picks make sense to the critic | done, with a caveat | `docs/research/scenario-fit-10.txt` (10 stories, top 3 each), `scenario-fit-24-demos.txt` (the 24 demos with their plot removed: 20 rank their own first). A sonnet critic who saw only text judged 7 of 10 first picks right and 3 weak (guess-the-number over countdown / rule-and-exception, chase-through-document over a definition plot); fit was then changed (a rare fact outweighs plain figures) and the weak ones now rank right or second. The demos were written for their plots, so the 20/24 is not independent evidence |
| Three scenarios of one set of facts sit side by side on a storyboard sheet and tell different stories | done | `docs/research/scenario-three-plots.jpg` (guess-the-number, cold-open, false-lead, one library report). The critic: "genuinely different stories, not a reshuffle"; weak spots: the three use slightly different facts of the report, and the false-lead's false lead is a plan, not a belief (by design, N1) |
| `news` is refused, `myth-vs-fact` is gated, each tested | done | `TestEligibility`: `test_news_refuses_every_scenario`, `test_news_story_with_a_scenario_is_a_problem` (also via `check_story`), `test_news_stamp_is_refused`, `test_code_built_and_fiction_programs_take_none` (digest, story too), `test_myth_vs_fact_is_gated`, `test_myth_vs_fact_refused_unless_the_document_corrects`; `TestFrontDoor.test_news_refused_at_the_front_door`; `write_story` refuses before any fetch |
| Skill `veasy:scenarios` and a tool exist, and a sub-agent used them cold | done | `skills/scenarios/SKILL.md` (about 6 KB), link `.claude/skills/scenarios`, tool `veasy_scenario` (plugin.yaml, `__init__.TOOLS`), `tests/test_plugin.py` passes. A haiku agent given only the skill ran fit, stamp, check and board first time; it found the command prefix and the effect of stamp unstated, now fixed in the skill |

## Build list (brief), item by item

1. Scenario as data, `validate`, a case per rule: done (`scenarios/schema.json`, `tt_shorts/scenarios.py`, `TestData`).
2. `story["scenario"]` code-owned, `news` refuses: done (`writer.OWNED`, `check_story`).
3. Free checks at plan: word budgets, fact gates, payoff not said early, scene order and brushes, anchors: done
   (`check_plan_beats`; runs in `check` and so in `plan`).
4. `engine scenario fit`, `make "<url>" --scenario auto --preview-storyboard`: done (the preview fetches the source
   and never calls the writer, tested with a mock that fails if it does). **Chapters with a different plot each: not
   done** (`chapters.py` is code-split by scene count and one `scenario` field per story is the model here).
5. myth-vs-fact only when the document corrects: done; the check is marker words in the text or a `doc_correction`
   field, which is weaker than comparing with the source (owner decision below).
6. Sound cues synthesized, constant level, no risers or ducking: done (`sfx.py` reads the scenario's beats; a beat
   `sound: null` is silent; `props.py` passes the story's scenario to the cues).
7. Measure the cheap writer on stubs and saved outputs: **not measured with a model** (no model calls allowed). What
   the saved outputs show: of 19 existing stories, one has the scene count a plot demands, so an unprompted writer
   will not follow beats; all of the following would have to come from the prompt (`brief_block` states the exact scene
   count, order, brushes and budgets) and the repair loop (`check_plan_beats` is added to `more`, giving specific
   messages), with the writer's default of 2 repairs. The risk the brief names (repairs run out) is real and
   untested. `make --length` is fixed: parsed, used in the ranking, and the plan's seconds are reported against it.

## Commits

`38d2166` wip (as the Antigravity run left it) · `bd12db4` plots, demos, checks, `engine scenario` · `512631d` make:
`--scenario`, `--length` · `696bf12` sfx from beats · `5c8ee9f` skill, tool, digest/story refuse · `1a50c85` three-plots
sheet · `fdc8f2b` fit weighting · `59f3233` research · `1502093` skill notes · plus the final result commit.

## Not done, and why

- Chapters with a different scenario each (needs a design with `chapters.py`).
- Writer compliance measured on real calls (no paid or model calls here).
- Remotion renders of the demos: only `plan` stills (the rule was stills, not full films).
- Research: nine recalled works and one folk-craft row, none fetched; the 30-source target was cut by instruction.

## Owner decisions

1. Should `digest` and `story` (fiction) refuse scenarios as `news` does? Done so for now (code-built, own plot).
2. myth-vs-fact's gate is textual (correction words or `doc_correction`). A stricter gate would compare the correction
   with the source document (`engine check --sources`); say if the news standard should apply.
3. Plots are a fixed scene count each (3-7 beats). Say if a long film should take several plots as chapters.
4. The demos' facts are an invented library report and bus notice, not real news; keep them as demos only.

## Shared files touched (additive)

`tt_shorts/engine.py` (import, `structure_problems`, `write_story(scenario=)`, `scenario_cmd`, parser, options),
`tt_shorts/writer.py` (`OWNED`), `tt_shorts/make.py` (`--scenario`, `--length`, `_scenario_preview`),
`tt_shorts/sfx.py`, `tt_shorts/props.py` (one call), `plugin.yaml`, `__init__.py`, `tests/test_plugin.py`.
Proposed paragraph for CLAUDE.md: "**Scenarios** (`scenarios/<id>.json`, `tt_shorts/scenarios.py`, `veasy:scenarios`):
the plots a film follows, each beat with a job, a word budget, scene types and a sound. `story["scenario"]` is
code-owned like `rubric`; news, digest and story refuse one. The beat checks run in `check` and `plan`; a new scenario
needs a demo `stories/scenario-<id>.json` (the demo test covers it)."

## Tests

Lane: `python -m unittest tests.test_scenarios tests.test_sfx` (36 + sfx) green. Full suite and tsc: see below.
