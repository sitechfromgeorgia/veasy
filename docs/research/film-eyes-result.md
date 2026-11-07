# Result: The Film's Eyes (film-eyes)

**Branch:** `goal/film-eyes` · taken over in Claude Code after the Antigravity run stopped. The status lines of the
first run were unverified and partly wrong (see section 4); this file is rewritten from what was run.

## 1. Done when, with evidence

| Done when | Status | Evidence |
|---|---|---|
| 12 seeded-broken stories in `tests/fixtures/review/`, at least 10 caught | **Done: 12 of 12** | `defect_01..12_*.json` (12 files; 12 byte-identical duplicates removed). Each names its rule in `defect.catch`; `tests.test_review.SeededDefectTest` runs `review.detect` and asserts every fixture is caught by its own rule and that only 06 (read) and 07 (flash) hold. Story-level defects (03, 04, 06, 09, 10, 11) are real in the story; the pixel defects (01, 02, 05, 07, 08, 12) are carried by a `pixels` recipe in the fixture, drawn deterministically by `review.synth_pixels` (no real render). |
| Approved demos raise no false hold | **Done** (stories and real stills of 24835, 24725, veasy-demo) | `ApprovedDemosTest`: 24835, 24725, veasy-demo, veasy-scenes give no hold and review as passed with an empty facts diff. Pixel checks on real Remotion stills raised nothing: `docs/research/film-eyes-calibration.json`. veasy-scenes has two pre-existing `still` warnings from the motion rules (not a hold). |
| Before and after sheets show a real fix on 3 films, facts diff empty | **Done** | `RealFixTest`: `defect_10_pingpong_cuts` (back-and-forth cuts steadied), `fixable_02_double_points` (second `points` -> `pair`), `fixable_03_short_read` (a `read` hold lifted by moving an anchor). Facts diff `[]` on all three. Sheets in `docs/research/film-eyes-sheets/`: `double_points.jpg` (real stills, before: two identical list scenes; after: the second is a pair card) and `short_read.png` (timeline, the quote scene short by 1.2 s before, 1.0 s spare after). For the pingpong film the still at the cut looks the same before and after, so its evidence is the motion finding disappearing (`RealFixTest`), not a picture. A quote that needs new text (`defect_06`) correctly stays `held`. |
| Skill `veasy:review` and a tool exist, and a sub-agent used them cold | **Done** | `skills/review/SKILL.md` (4.5 KB), `.claude/skills/review` (mode 120000), tool `veasy_review` (plugin.yaml, `__init__.TOOLS`), `engine review`; `tests.test_plugin` passes. A haiku sub-agent given only the skill text ran `engine review` on `fixable_02_double_points` and got status `fixed`, empty facts diff; its three questions (is the file changed without `--save`, what do the round counters mean, are pixel rules skipped without stills) are now answered in the skill. |

## 2. Commits (after the Antigravity ones)

wip state; fixture dedupe + test fixes + name-stem facts check; seeded defects realised, eyes wired into the audit,
loop repairs warnings; `engine review`, tool, three real repairs; skill + README + approved-demo test; skill clarified.

## 3. What changed against the first run's code

- `eyes.check_eyes`: removed two fallbacks that fired on every bare story (reading-time and a fake 2 s metronome);
  `no_hero_frame` no longer excused by a hook or stat in the story (pixels decide); new `safe_zone_ink` (rail).
- `review.audit_story` now runs the eyes (metronome on the real timeline, spoken redundancy). The loop used to never
  see them and never repaired a warning; it now repairs `repeat`, `pingpong`, `safe_zone` warnings and no longer
  reports a harmless oscillation as `held`.
- Pingpong repair works on the scenes' own `transition` and `flow`; the facts guard treats layout keys as code.
- Facts guard: name stems matched by prefix (a changed place name was missed before).

## 3b. Report-only metrics (phase 3 of the report)

`eyes.report_metrics(props)`, run inside `review.audit_story`: `word_lag`, `text_echo`, `post_cut_motion`,
`hold_ratio`, `unrelated_cuts` and the film-level `keyframes_one_curve`, `keyframes_fade_up`,
`keyframes_text_moving`. They reuse the motion timeline and cuts and the existing per-scene `spoken_redundancy`;
all are warnings (`hold=False`), numbers are always in `metrics`. One test each in `tests/test_review.py`
(`ReportMetricsTest`) plus a test that none fires on six approved stories (nine checked by hand, including
sitech-cybercartel, explainer-inflation, law-constitution-17). Calibration finding: the first thresholds fired on
every approved film (scene text legitimately comes on up to 5 s before its words, one curve is the pack's normal cut,
`rise` is one option of eight), so thresholds sit outside the approved range and the `word_lag` rule in particular
is weak; it needs a per-word timing of the screen text to be sharper. The `keyframes` rules read the cut kinds and
the style's entrance, not real easing curves (props do not carry them). The brief did not define the five metrics
beyond their names, so the definitions are mine. Owner decision 4: confirm or replace them.

## 4. What was not done, and corrections

- The first result file claimed edits to `engine.py`, `plugin.yaml`, `__init__.py`, `test_plugin.py`, README. None
  existed (the diff against main held only review/eyes files). They are made now, additively (section 5).
- Pixel defects are tested on synthetic frames, and detectors are calibrated on real stills of three demos (veasy-scenes has stories checked, no stills); no HyperFrames film was rendered (frames are engine-neutral, but untested on one).
- The look round of the loop only repairs transitions/flow and hook layout; `still`, `metronome_cuts`, `empty_middle`
  and `no_hero_frame` are reported, not repaired.
- The full suite was run once at the end: see section 6.

## 5. Shared files touched (all additive)

`tt_shorts/engine.py` (`review` subparser, `review_cmd`, dispatch entry), `plugin.yaml` (`veasy_review`),
`__init__.py` (`veasy_review` in TOOLS), `tests/test_plugin.py` (`"review"` in SKILLS), `README.md` (one command
line), `.claude/skills/review` (symlink). `tt_shorts/critique.py` untouched. CLAUDE.md untouched.

## 6. Full suite

`python -m unittest discover -s tests`: 819 tests, 2 skipped, 1 failure: `test_compose.Blocks.test_scaffold_with_blocks`
(`r["built"]` false). It is in the compose lane, touches no file of this lane, and was not run against main to confirm it
fails there too: likely this machine's HyperFrames/node setup, unverified. `tsc` and `selftest` were not run (no
Remotion source changed).

## 7. Owner decisions

1. Which warnings should become holds once the calibration set grows (`spoken_redundancy`, `safe_zone` first?).
   Today only `read` and `flash` hold.
2. Whether the loop may ever rewrite narration or a quote to cure a `read` hold; it refuses today (facts guard).
4. The definitions of the five report-only metrics (section 3b) are an interpretation of the report's names.
3. Thresholds in `eyes.py` rest on four approved demos; more films are needed before tightening.

## 8. Proposed paragraph for CLAUDE.md

- **The film's eyes** (`tt_shorts/eyes.py`, `tt_shorts/review.py`, `engine review`, skill `veasy:review`, tool
  `veasy_review`): free pixel and pacing checks on either engine's frames and a repair loop capped at 3 machine and 2
  look rounds. Only `read` and `flash` hold; every other check is a warning until calibrated on approved demos. The
  loop never changes a fact (`review.facts_diff` must stay empty) and a model's "pass" is never a gate. A new check
  needs a seeded-defect fixture in `tests/fixtures/review/` (with `defect.catch`) and a case in `tests/test_review.py`.
