# one-take: result

Lane `one-take` (ROADMAP D5). Branch `claude/one-take-45e2c4` (cut from `main`; not renamed to `goal/one-take`: the
brief said to stay in the branch it started in). Nothing pushed or merged.

One line for the user: `"transition": "one-take"` in a format, or nothing (variety picks it for a film of a program).
`python -m tt_shorts.engine plan|still|render <story> --transition one-take`.

## What was built

- `tt_shorts/onetake.py` (pure): `layout(types, seed)` lays the scenes on a grid of cells (8 compass steps, no turn of
  more than 90 degrees, a box of 3 cells, no cell twice, a one-step look-ahead, the arriving scene's shape bias: lists
  come down the page, charts across it, a seeded jitter for the rest) and `position(cam, froms, frame)` is the camera
  as a pure function of the frame. `attach()` writes `props["camera"]`.
- `remotion/src/onetake.tsx`: `OneTakeBand` (only the scene band, clipped to the band, rides the camera), `Thread`
  (a bezier between the two scenes' margins and the dot running it, `@remotion/paths` 4.0.539, pinned to the other
  Remotion packages), `Parallax` (three layers of the film's own motif behind everything, depth 0.2/0.4/0.65).
  `remotion/src/motif.tsx` is the motif tile moved out of `Background` unchanged (selftest proves no pixel moved).
- `variety.transitions_for(look, program)` / `PROGRAM_ONLY = ("one-take",)`: one more option in every look's pool for a
  story with a `program` other than `news`; `props.choose` refuses it by name for news; `formats.TRANSITIONS`,
  `props.TRANSITIONS`, `types.ts`, `engine options` (`transitions.one-take`, `variety.program_only_transitions`),
  `skills/formats/SKILL.md`, `motion_rules` (direction of the camera's move, no fade-out lost to a cut), `sfx` (whoosh).
- Window: 12 frames from each new scene's first frame; the old scene stays alive 12 frames past its end. A scene's
  settled frame for the layout probe is its first + 12, exactly at rest, so `probe.py` needed no change.

## Done-when evidence

| Line | Status | Evidence |
|---|---|---|
| `tests/test_variety.py` shows the option used evenly; each limit has a test | done | `test_variety`: `test_one_take_is_one_more_cut_for_a_film_of_a_program` (every look: 2 of each of its cuts incl. one-take), `test_news_never_meets_one_take_in_a_run`. `tests/test_onetake.py` (29 tests): zoom <= 1.15 (every frame, 200 seeds, the picture clamps too); moves only in the cut window (no drift at rest, exact rest on a scene with zoom 1.0); probe's settled frame at rest; chrome/captions/footer outside the band (source check of `NewsShort.tsx`); band clipped to the safe zone; pure of the frame (no clock/random); accent only the dot (no `RED`, no shadow); the thread starts and ends in a scene's margin; news refused and its pools unchanged; no ping-pong in the motion rules |
| layout probe passes in every look; `flash` and motion rules pass | done | `engine probe stories/explainer-inflation.json --look all --transition one-take --engine silent`: editorial, kinetic, cards, `problems: []`. Render report: `motion: {holds: [], warnings: []}`; qa `flash`: `checked: true, area 0.002, limit 0.25` |
| one whole film rendered with it passes `qa`; frames around each cut looked at | done | `stories/explainer-inflation.json`, cards look, edge-tts preview voice, 26.6 s, `--transition one-take`, rendered with the final code. Render report: probe `problems: []`, `motion: holds [], warnings []`. `engine qa`: `problems: []`, -16.6 LUFS, flash `checked: true, area 0.002, limit 0.25`. Frames at -3/+2/+5/+8/+11 around all four cuts (starts at frames 133, 332, 491, 634): `docs/research/one-take-sheet.jpg` |
| fresh-eye critic judged a contact sheet; notes here | done | "Critic" below (two sonnet passes, given only the sheet) |
| full suite, `tsc`, `selftest` pass after the last fix | done | after the last code commit: `python -m unittest discover -s tests`: 804 tests, 2 skipped, all pass (`test_compose.Blocks.test_scaffold_with_blocks` first failed only because `compose/node_modules` was not installed here; after `npm ci` in `compose/` it passes); `(cd remotion && npx tsc --noEmit)` clean; `engine selftest`: 102 unchanged, `layout: []`, `problems: []` (no `--update`, no golden touched) |

## Critic (sonnet, given only the contact sheet)

Round 1 (thread anchored at scene centres): the thread was a huge arbitrary curve that cut through text in cuts 2 and
3; cut 1 reads as a wipe; the hatch gives no depth. Action: the thread now runs between the two scenes' margins
(inside the text margin), a gentle bend, so it never crosses what is read (test added).
Round 2 (after the fix): text collisions gone, header/caption/footer stable. Remaining notes, with what was done:
1. cuts read as pans, clipped mid-word on a card, "a slide-show push" (cut 1, 3, 4). **Not changed**: a pan clips
   what leaves the view; a still can't show continuity. The window is 12 frames because the probe settles a scene 12
   frames in; a longer, softer glide needs `probe.settled` to learn the window (owner/integrator decision, below).
2. the thread is a faint short hairline; the parallax is invisible in a still. **Changed**: stroke 6 px, dot 26 px,
   layers' opacity 0.6/0.8/1.0 and the nearest layer in the stronger line colour.
3. the end card is nearly empty at +8 and its QR faint at +11. **Not camera**: that is the end scene's own entrance
   (it also happens with a plain cut).
4. direction changes between cuts (sideways, down, diagonal). By design: the route follows the scenes' shapes and the
   seed.

## Owner decisions

1. Should `news` get one-take? The ROADMAP imagines it with the 1.15 cap; `CLAUDE.md` forbids changing `news`. Today
   it does not reach it (auto never offers it; naming it for a story without a `program`, or with `news`, is refused).
2. A longer glide (about 20 frames) reads more continuous than 12. It needs the layout probe's settled frame to be
   `first + max(12, window)`; `probe.settled` is shared. Left alone.
3. Parallax uses dots for the `plain` motif (so a plain film still has depth). If "plain means nothing" should win,
   skip the layers for it.

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
- No golden still for a one-take scene was added: the goldens are rest frames, identical to a plain cut by design, so a
  golden would prove nothing the probe doesn't. `selftest` goldens are unchanged.
- The `loop` outro with one-take was written (the loop's cross-fade carries a frozen parallax so the last frame is
  the first) but not rendered; only the `card` outro film was.
- The TS `camera()` and the Python `position()` are kept equal by a source-level test (same easing and window
  strings) and by the render, not by running both on the same frames.
- Not benchmarked: three full-canvas SVG pattern layers per frame (the 26 s film rendered in about 3 min with other
  agents running).

## Shared files touched (additively)

`tt_shorts/variety.py` (PROGRAM_ONLY, `transitions_for`, `one_take_ok`, a `program` argument), `tt_shorts/props.py` (one
transition, the camera, the refusal), `tt_shorts/formats.py` and `tt_shorts/engine.py` (the option in lists and
`options`), `tt_shorts/motion_rules.py`, `tt_shorts/sfx.py`, `remotion/src/NewsShort.tsx` (the band, the thread, the
layers, the longer sequence for one-take; `Background`'s tile moved to `motif.tsx` unchanged), `remotion/src/types.ts`,
`remotion/package.json` + lock (`@remotion/paths` 4.0.539), `skills/formats/SKILL.md`, `tests/test_variety.py`.
Not touched: `plugin.yaml`, `__init__.py`, `README.md`, `CLAUDE.md`, `probe.py`.

Paragraph proposed for CLAUDE.md: "**One-take camera** (`tt_shorts/onetake.py`, `remotion/src/onetake.tsx`, transition
`one-take`): the scenes sit on a path laid out in code and seeded per video; the camera moves only in a 12-frame window
from each new scene's first frame (zoom <= 1.15, exactly at rest otherwise); chrome and captions never ride it; the
dot runs the thread. Offered only to a film of a program, never to `news`. A change to the window needs
`probe.settled` to follow it; a change to the route needs a case in `tests/test_onetake.py`."

## Commits

(see `git log`; the last is named in the final message)
