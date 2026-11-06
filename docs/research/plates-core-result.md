# Plates Core Result

## 1. "Done When" Evidence Matrix

| "Done When" Requirement | Status | Evidence (File, Command Output, Still) |
|---|---|---|
| `engine plate example --seconds 4` gives a tone-mapped clip in both packs, and a second call answers from the cache in under a second. | In Progress | Unit 1 done: `plates.make` bakes, tones all 4 pack/theme lines, answers from cache (`tests/test_plates.py` Baked). CLI wiring pending. |
| One Remotion film and one composed film show a plate behind real facts: rendered, `qa` and flash pass, `probe` passes, and the critic has judged the frames. | In Progress | Pending Item 5 & 6 & 9 implementation. |
| Tests prove the refusals, the tone line, the cache and the ledger. | In Progress | Tone line, refusals (library level), cache, ledger entry proven in `tests/test_plates.py` (16 tests pass). Refusals at brush/check and ledger validation pending. |
| The skill states what reading a plate costs in each engine, as measured. | In Progress | Pending Item 8 implementation (`skills/plates/SKILL.md`). |
| All gates pass (`python -m unittest discover -s tests`, `tsc --noEmit`, `engine selftest`). | Ready | Baseline passes (773 tests, 0 errors, tsc clean). |

---

## 2. Commit List

0. `5c8647a` wip: state left by the Antigravity run (unverified, then verified: bakes)
1. `b871090` `docs(research): research 16 sources on broadcast plates, tone mapping, banding and headless video seeking`

3. `caa3c87` feat(plates): the plate core (cache, tone line, refusals, ledger entry)
4. `3b4dce2` feat(plates): engine plate <kind>|list|check, options section
5. (this commit) feat(plates): plate scene (brush, Remotion), refusals in the checks, ledger kind, shelf pick

---

## 3. What Was Not Done & Why

*(Will be updated as backlog items progress)*

---

## 4. Owner Decisions

*(Any items requiring owner confirmation)*

---

## 5. Shared Files Touched

| File | Nature of Touch | Justification |
|---|---|---|
| `docs/research/plates-core.md` | New | Comprehensive research report and backlog |
| `docs/research/plates-core-result.md` | New | Result evidence tracker |

## 6. Measurements (this run, 2026-11-07)

- Tone: the lookup stage puts every pixel within 0.72 of the canvas-to-ink line (limit sqrt(3)/2 = 0.866) and uses at
  most 256 colours, for all four lines (both packs, both themes). A decoded x264 crf 14 clip adds codec noise: mean
  distance 1.0-1.2, p99.9 3-5, max 12-16 (x264 ringing at edges; crf 0 gives max 2.4 but 6x the size). The research's
  claim of "zero off-palette colours" holds for the toned frame, not for the compressed clip: stated plainly.
- Cache hit: `plates.make` second call 1.5 s the first time it was timed including interpreter and brand loading; the test
  holds the call itself under 1 s (node `--hash` about 0.1 s).
- Bake: about 200 ms a frame at half scale on this machine; the browser start costs most of a one-second bake.
- run.mjs: `--hash` added (print the content hash, no bake); the hash used the spec's file path, now its contents.

## 7. Shared files touched (additive), unit 3-5

`tt_shorts/engine.py` (command, options section, `plates.story_problems` in `structure_problems`, plates in
`_resolve_media`), `tt_shorts/assets.py` (ledger kind `plate`, licence `own`, kept through `resolve`, dropped by
`strip_code_owned`), `tt_shorts/variety.py` (table `plate_use`, `pick_plate`, `pick_plate_layout`, `record_plate`),
`tt_shorts/news_check.py` (`MADE_PICTURE_TYPES`; `SCENE_TYPES` unchanged, so N1 refuses a plate in news),
`tt_shorts/claims_check.py` and `tt_shorts/programs.py` (accept `MADE_PICTURE_TYPES` beside `SCENE_TYPES`),
`tt_shorts/catalog.py` (`plate` in `NO_MEDIA`), `tt_shorts/props.py` (`plates.for_props`), `programs/explainer.json`
(`plate` in its scene list), `remotion/src/types.ts`, `remotion/src/scenes/index.tsx`, `stories/veasy-plate.json` (the demo,
program explainer), `tests/test_catalog.py` and `tests/test_scenes.py` (the news allowlist test now names the made-picture
types; the demo list gets `veasy-plate`).
