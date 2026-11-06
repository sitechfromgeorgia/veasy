# Edit Room — Result & Evidence Ledger

## One-Line User & Agent Interface
```bash
python -m tt_shorts.engine steer demo/film-partia.json --scene 1 --set label="21 სექტემბრიდან 2 ნოემბრამდე" [--dry]
```
Returns a pre-run cost plan (`"4.0 s of picture (scene 1 of 11, frames 116-235), $0.00"` or `"new voice, every frame"`) when `--dry` is passed, or redraws only the dirty scene segment(s), stitches with FFmpeg, mixes continuous audio once via `props.mix_audio`, and writes `<render>.room.html` beside the MP4.

---

## "Done When" Evidence Table

| # | Done When Requirement | Status | Evidence (File / Command Output / Still) |
| :-: | :--- | :---: | :--- |
| 1 | Research committed before build (`docs/research/edit-room.md`: 15+ real sources with links, what each teaches Veasy, licence table, ranked backlog with value & effort) | **DONE** | `docs/research/edit-room.md` (21 real sources across 5 domains, commercial licence table, ranked 4-unit backlog) |
| 2 | Changing one label in `demo/film-partia.json` is timed before and after, and the saving is stated | Pending Unit 2/4 | To be populated in Unit 2/4 |
| 3 | Frame hashes outside the changed scene equal a full render | Pending Unit 1 | To be populated in Unit 1 (`tests/test_steer.py`) |
| 4 | `--dry` is right on a text change, a timing change and a narration change, each tested | Pending Unit 2 | To be populated in Unit 2 (`tests/test_steer.py`) |
| 5 | The room page (`<render>.room.html`) opens, and a sub-agent fixed a scene from it alone | Pending Unit 3/4 | To be populated in Unit 3/4 |
| 6 | `selftest` is green, and skill `veasy:steer` and a tool (`veasy_steer`) exist | Pending Unit 4 | To be populated in Unit 4 |

---

## Commit List (Branch `goal/edit-room`)

1. `docs(edit-room): add edit-room research and initialize result ledger`

---

## Shared Files Touched (Additive Only)

*(None yet — will list exact line additions to `tt_shorts/props.py`, `tt_shorts/compose.py`, `tt_shorts/engine.py`, `plugin.yaml`, and `__init__.py` as each unit lands.)*

---

## Proposed Paragraph for `CLAUDE.md`

> - **The edit room** (`tt_shorts/segments.py`, `tt_shorts/steer.py`, `tt_shorts/room.py`, skill `veasy:steer`, tool `veasy_steer`):
>   - Every render cuts the film by scene into content-addressed silent video segments in `$VEASY_HOME/cache/segments/<sha16>/`, stitched with `ffmpeg -f concat` and mixed once through `props.mix_audio` (voice is never spliced by sentence).
>   - `python -m tt_shorts.engine steer <story> --scene <n> [--set k=v] [--tighter | --breathe | --land] [--dry]` redraws only the scenes a change touches; `--dry` states the cost in seconds of picture and dollars before running (`$0` for text/timing changes, full render + new voice when narration changes).
>   - Every render writes `<render>.room.html` beside the MP4 with each scene's still, words, timing, rhythm check, cost table, and copy-ready `steer` commands.

---

## What We Didn't Do & Why

- Sentence-level voice splicing: intentionally excluded per ground rules ("Never splice voice by sentence: tone seams, and later timing moves anyway") and EBU R 128 `loudnorm` / AAC framing physics.

---

## Owner Decisions

- **Remotion vs. HyperFrames default segment cache eviction policy:** `$VEASY_HOME/cache/segments/` currently persists content-addressed segments indefinitely like `$VEASY_HOME/cache/voices/` and `cache/bundles/` so `steer` and `undo` stay warm across sessions. If disk space on `84.46.250.149` requires a cap, the owner can decide whether `store.py` should prune segments older than N days during queue maintenance.
