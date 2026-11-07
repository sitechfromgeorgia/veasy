# forms-look: result

Lane `forms-look`, branch `claude/forms-look-579908` (cut from `main`). Status is kept current from the first commit.

**The one line:** `veasy_look({"job": "j_91"})` (or `{"story": "stories/24835.json"}`) returns what exists for it: sheets,
numbers, warnings, checks, and the next step. Free, read-only.

## Done when (evidence)

- [ ] `veasy_look` works on a real job and on a story with no job, with a test
- [ ] cold sub-agent picks a sensible form for 3 stories
- [ ] `figures` passes test_catalog, test_scenes, test_engine and the layout probe in every look
- [ ] full suite, `tsc`, `selftest` pass after the last fix

## Owner decisions

- `figures` does **not** join `news_check.SCENE_TYPES`: `news` stays exactly as it is until an owner says otherwise.
