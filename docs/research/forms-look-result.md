# forms-look: result

Lane `forms-look`, branch `claude/forms-look-579908` (cut from `main`).

**The one line:** `veasy_look({"job": "j_91"})` (or `{"story": "stories/24835.json"}`) returns what exists for it: its
sheets, numbers, warnings, checks, the idea it keeps and the next step. Free and read-only.

## What shipped

1. **`veasy_look`** (`tt_shorts/look.py`, `engine look --job|--story`, tool in `plugin.yaml`, `__init__.TOOLS`, and the
   `veasy:qa` skill). Lists the QA sheet, plan sheet, props and composed `look` sheets that already exist, reads the
   cached props for the motion rules, runs the story checks (free), and names what is missing (`missing`) instead of
   making it. `tools.present` / `tools.absent` point at `veasy_review`, `veasy_steer`, `veasy_brush_book` when this
   build has them (module probe) and never fail when it has not. Tests: `tests/test_look.py`.
2. **Forms** (`skills/direct/references/forms/`, nine short files) linked from `skills/direct/SKILL.md` (6.4 kB, under
   12 kB). Forms are how a film looks and moves; plots stay in `scenario-library`'s scenarios. `tests/test_forms.py`
   checks that every kit-drawable device in `concepts/devices.json` is named in a form.
3. **`figures`** (ROADMAP C6, now closed): `brushes/figures.json`, `Figures` in `remotion/src/scenes/more.tsx`,
   `types.ts`, `engine.shape_problems`, demo story `stories/veasy-figures.json`, goldens in all three looks and the
   SiTech light theme (added to `golden.STORIES`), a row in the `veasy:write-script` table.

## Done when (evidence)

- [x] **`veasy_look` on a real job and on a story with no job, with a test.** `tests/test_look.py`: a job made with
  `queue.add` and a cached render (sheet, props), and `stories/24835.json` with no job; also checks nothing is written,
  missing sibling tools, bad input, and the plugin tool. Passes. Not run against a job from a real render on this
  machine (no voice or render was made: no paid calls).
- [x] **Cold sub-agent picks a sensible form for 3 stories.** A haiku agent, given only the direct skill and its
  linked forms: gas cut in two districts -> `map-led` (clean-map); bus fleet with dated tender, bids, vote ->
  `evidence-board` (space-time-board); a minister's one sentence -> `voice-on-record` (verbatim-quote). Each came with
  the form's own "avoid". Its notes: `clean-map` has no kit mapping spelled out (it is `where`), and
  `through-object` also fits story 2. Both are minor; not changed.
- [x] **`figures` passes** `test_catalog`, `test_scenes`, `test_engine` and the layout probe in every look
  (`probe stories/veasy-figures.json --look all`: no problems in editorial, kinetic, cards; stills looked at).
- [x] **Full suite, `tsc`, `selftest` after the last fix:** 780 tests OK (2 skipped), `tsc --noEmit` exit 0, `selftest` 126 unchanged, no problems (a first selftest run had two transient `Failed to fetch` probe errors; the rerun was clean).

## Owner decisions

- **`figures` is not on `news_check.SCENE_TYPES`.** `news` stays exactly as it is. The brush has no writer line
  (`"schema": null`), so no writer, news or otherwise, is offered it, and tests record it as kit-only
  (`KIT_ONLY` in `tests/test_catalog.py`). Consequence: because `programs.validate` and `claims_check` also use
  `SCENE_TYPES`, no program (explainer, law, blog) can list `figures` either; it is for hand-written and composed
  stories. To open it: add `"figures"` to `SCENE_TYPES`, give the brush a writer line and rule, drop it from the
  `KIT_ONLY` tuples in the tests.
- `veasy_look` calls `queue.get`, which opens (and creates when absent) `veasy.db` under `$VEASY_HOME`: the only
  thing it may create. Say if a pure file read is wanted instead.
- Forms are advice in the story's `concept.form`; code does not judge them (as the report says for `device`).
