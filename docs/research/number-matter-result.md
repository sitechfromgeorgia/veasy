# The Number's Body (plates: matter): result

Lane `number-matter`, branch `goal/number-matter`. Antigravity wrote the solver, forms, verifier, camera, anchors and
tests and stopped before anything was baked or run; its earlier status lines and README cost table were unverified and
are replaced here. Claude Code took over on 2026-11-07, ran everything and wrote the missing parts: `plates/matter/index.html`
(the page `run.mjs` loads) and `plates/matter/bake.mjs` (verify, solve into `cache/sim.bin`, bake through `run.mjs`).

At the user's level:

```bash
node plates/matter/bake.mjs --spec spec.json --seconds 6 --seed 1 --out out/plates/budget   # add --scale 0.5 for half size
```

`plate.mp4`, `poster.png`, `anchors.json`, `sim.bin` and `plate.json` (`matter.proof`: `800 x 1 = 800`, the group counts,
the sha256 of the `.bin` and the mp4). Spec example: `out/specs/split.json` (not in git; see the README for keys).

## Done-when, with evidence

All clips are in `out/plates/<form>/` (git-ignored). Baked at half scale (540x960, scaled up by ffmpeg), 6 s, 800 blocks,
the real fact of `stories/veasy-new-01.json` scene 3 (8.0 billion = 3.2 + 2.8 + 2.0, `scale` 100, one block = 10 million).

| Done when | Status | Evidence |
|---|---|---|
| `pile`, `split`, `too-tall` baked and looked at; others baked or listed | Done | All six forms baked. Looked at 4-frame sheets (`out/plates/<form>/sheet.png`) and fixed: too-tall and split cameras were too close to read, pour was invisible (cached instance bounding sphere culled it), versus fogged to black. Known weak spots in the README: split reads as terraces, pour has no container, resort is close and some blocks interpenetrate. |
| Code proves count = fact; non-dividing unit refused | Done | `verifier.mjs`; `plate.json` `matter.proof` and `exact`. `tests/test_matter.py` (14 tests, pass): non-dividing unit, cap 3000, group partition, forbidden categories, scale refusal of fractions, decimal without scale refused. |
| Two bakes of one spec: same `.bin`, same mp4 | Done | `split`: two bakes, sim sha256 `31f32632f2fc9322...`, mp4 sha256 `075e205fadcdc7fe...` identical (`out/plates/determinism-1/`, `-2/`). Pile earlier: three bakes identical. Solver byte-equality is also a unit test. |
| flash.py passes on every clip, including the crash | Done | `flash.measure`, area (limit 0.25): pile 0.021, split 0.0, too-tall 0.0, pour 0.162, resort 0.008, versus 0.0. The first pile failed at 0.33 (blocks bright, in free fall); fixed with the `exposure` key (default 0.4), not by changing the physics. Pour at full light 0.43, fixed with exposure 0.3 and a farther camera. |
| One 6 s clip behind a real budget fact in a composed film in `out/`, critic judged | Done, with caveats | `out/compose-matter/` (scene `s3`, the story's budget scene, 17.0-23.1 s): the `split` plate under the story's own labels and values; red dots follow the plate's anchors. `compose check` problems: `[]`. Frames: `out/compose-matter-sheet.png`. Not rendered to a full mp4 (stills from `compose look` only). Critic (a sonnet sub-agent shown only that sheet) said: not read as money at first sight; the third share was missing in its frame (my chip timing, since moved earlier, not re-judged); no per-share colour; score 2/5; wants labels attached to groups and a total plus a "1 block = X" legend. |

## Not done

- Critic's fixes: a legend ("1 block = 10 million") and a total. The total is not bindable: `compose` exposes no fact id for a story's numeric `total`, and `unit` text is not a fact. Needs `compose.py` to expose it (not mine to touch).
- The film was judged once; after the chip-timing fix it was not shown to a critic again.
- Full-scale (1080x1920) bakes: not measured. The scene uses a half-scale plate scaled up (soft).
- The final full test suite and `tsc` / `selftest`: see "Gates" below.

## Cost (shared machine: five sessions, every time runs high)

Half scale, 6 s, 800 blocks, one bake each. ms/frame, wall: pile 98, 22 s; too-tall 154, 32 s; versus 177, 44 s; pour 203,
54 s; split 230, 48 s; resort 241, 48 s. Solve under 1.5 s. No limit depends on these, so no solo re-measure was made.

## Commits

`c9bcddf` wip state left by the Antigravity run; then page and bake wrapper; scale key and cameras; exposure key;
pile camera; pour/resort/versus, fog, culling, tests (`5c61fd5`); README and this file.

## Owner decisions

1. **Plates and `news`.** `CLAUDE.md` and `plates/README.md` bar plates from news. The proof film uses `veasy-new-01`, which has no `program` (so it is `news` by default). It is a proof in `out/`, never shipped; the owner decides whether a budget explainer program may use matter plates.
2. **Exposure.** A plate is a dim master (0.4 of full) because flash safety demands it; the engine maps it to ink. Decide whether plates may carry this ceiling or the engine should rescale.
3. **Devices** (`concepts/devices.json`, waiting with empty `scenes`): `pour-or-pile` -> `pour`, `pile`; `too-tall` -> `too-tall`; `data-resort` -> `resort`, `split`, `versus`. Wiring needs goal 1's plate scene.

## Needs from other lanes (shared files I did not touch)

- `compose.py` / `probe.mjs`: a way to declare a plate's tone, so text over it is judged on its real tone and not "worst case white". Now worked around with solid bands and chips.
- `compose.py` facts: numeric `total` of budget scenes as a fact id.
- Goal 1: `engine plate` should call `bake.mjs` for kind `matter` (the kind needs `cache/` made before `run.mjs`), or the page should read the `.bin` from the spec.

## Shared touches

None outside `plates/matter/`, `tests/test_matter.py` and `docs/research/number-matter*.md`.

## Gates

Full suite `python -m unittest discover -s tests` on the commit before this note: exit 0 (see the Ran/OK line in `out/full-suite.log`). `tsc` and `selftest` not run: no Remotion or scene code was touched.
