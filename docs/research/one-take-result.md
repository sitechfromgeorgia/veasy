# one-take: result

Lane `one-take` (ROADMAP D5). Branch `claude/one-take-45e2c4` (cut from `main`; not renamed to `goal/one-take`, the
brief said to stay in the branch started in). Status: IN PROGRESS. This file is kept current from the first commit.

## Done-when evidence

| Line | Status | Evidence |
|---|---|---|
| `tests/test_variety.py` shows the option used evenly; each limit has a test | not yet | |
| layout probe passes in every look; `flash` and motion rules pass | not yet | |
| one whole film rendered with it passes `qa`; frames around each cut looked at | not yet | |
| fresh-eye critic judged a contact sheet; notes in this file | not yet | |
| full suite, `tsc`, `selftest` pass after the last fix | not yet | |

## Commits

(filled as they land)

## Owner decisions

1. Should `news` get one-take? The ROADMAP imagines it with the 1.15 zoom cap; `CLAUDE.md` forbids changing `news`.
   Today the option does not reach it (a story without a `program` is refused an explicit request, and the auto pick
   never offers it).

## Not done / missing

- **HyperFrames (build item 4): not brought over; not cheap.** Composed films are authored HTML, one host per scene
  with the agent's own GSAP timeline (`tt_shorts/compose.py`), so there is no single place that lays scenes out. What
  is missing, in order:
  1. a locked world wrapper (like `chrome.html`/`captions.html`) holding the scene hosts, driven by the path
     `onetake.layout()` already makes (written to `timing.json`), with the chrome and captions outside it;
  2. lint rules in `compose.lint`/`LINT_RULES`, each with a case in `tests/test_compose.py`: the camera moves only in the
     cut windows, zoom at most 1.15, no agent tween on the wrapper;
  3. `probe cut` (`compose.cut_problems`) reads frame pairs where two hosts overlap, assuming they stand still: it needs
     to read them through the camera, with a case in `Cuts`;
  4. a `CHROME_VERSION` bump and new lock hashes (the locked set changes);
  5. a `transition` field in `variety.COMPOSED_FIELDS` / `film_style` (today a composed film has none: "composed");
  6. `@remotion/paths` is not available there: the thread's point-at-length would be GSAP MotionPath or plain bezier
     arithmetic in the wrapper.
  The Python half (`onetake.layout`, `onetake.position`) is engine-free and would be reused unchanged.

## Shared files touched (additively)

(filled as they land)
