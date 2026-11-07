# Thread object: result

Branch `claude/thread-object-ef75d6`. Research: `docs/research/thread-object.md`.

## Done when

The run was stopped by the usage limit. This is the state at that moment.

| Line | State | Evidence |
|---|---|---|
| One line gives a film: object in 3+ scenes, changes state | partly | `engine thread stories/veasy-thread.json` plans 5 scenes, state `grow`. Stills of that film in all three looks were looked at. `engine render` of it was never run |
| catalog, scenes, engine, variety tests; options even; `news` refused | partly | passed on commit before the last changes (208 tests: thread, catalog, scenes, concept, variety, engine, programs). `state` refused by N1, kept out of the news writer's menu, new cuts need a thread, each with a test. Rerun after the last commit: see the commit message |
| flash, motion rules, layout probe in every look | partly | layout probe: 0 problems, 10 films, 3 looks (`tools/thread_pairs.py --check`). flash and motion rules not run |
| One whole film rendered, passes `qa` | no | none rendered |
| Fresh-eye critic judged the ten pairs | no | not run. Draft sheets were made and read by me only |
| Full suite, tsc, selftest after the last fix | no | `tsc` passed earlier; full suite and selftest not run |

## Built

- `tt_shorts/thread.py`: object from `concept`, silhouette traced from any drawing, states drain, fill, break, grow, shrink,
  seats in Python, corner token, `relieve` (a seat with text on it is given up before a render).
- `brushes/state.json`, `remotion/src/thread.tsx`, `remotion/src/scenes/state.tsx`, probe rule `seat`, `engine thread`.
- `object` cut: works, seen in frames around two cuts, and is one more `variety` option for a film with a thread.

## Not working or not done

- **`match` crashes the render tab** (Target closed, frames around a cut, cause not found). The first thing found was that
  `interpolatePath` throws "mismatch" on a path of several parts, fixed for `bars`; the crash came on a film that doesn't
  use `bars`, so it has another cause. `match` is out of `auto` (`variety.THREAD_PICKS`) until it is fixed; asking for it by
  name still crashes.
- HyperFrames blocks (item 5): not started. Missing: the blocks, `flubber` in the pinned script list, a case in `Cuts`.
- Skills not updated: `veasy:direct`, `veasy:formats` (`match`, `object`), `veasy:write-script` (`state`).
- `stat` shows 4 for a value of 3.8 in `stories/explainer-inflation.json`, in the kit too: to check, not touched here.
- Touches to shared files: `tt_shorts/engine.py` (options, `check`, `thread` command, `relieve`), `tt_shorts/programs.py`,
  `tt_shorts/catalog.py` (`NAMED_ONLY`).

## Owner decisions

- Pairs: 7 of the 10 stories are Veasy's own demo stories, and `veasy-map` needed its scenes changed to seat the object.
  The real news stories were left out on purpose. Is that good enough for the blind choice?
