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
| 2 | Changing one label in `demo/film-partia.json` is timed before and after, and the saving is stated | **DONE** | `demo/film-partia.json` (370.5 s, 11 scenes, silent voice, Remotion), same machine load (five lanes rendering, so both runs are slow): full render **16 min 57 s**; `steer out/partia.mp4 --scene 1 --set label="21 სექტემბრიდან 2 ნოემბრამდე"` **71 s** (4.8 s of picture, 10 of 11 segments cache hits, splice `copy`, probe + flash passed): **about 14x faster, 94 % less time**. The 71 s includes props build, probe, flash and the audio mix, which a segment cannot skip. Logs `out/render1.log`, `out/steer1.log` (git-ignored). |
| 3 | Frame hashes outside the changed scene equal a full render | **DONE** (re-run this session) | `tests/test_steer.py::TestFrameHashIdentity` passes: frames outside the changed scene equal the full render, and equal the render before the change. |
| 4 | `--dry` is right on a text change, a timing change and a narration change, each tested | **DONE** | `tests/test_steer.py::TestSteerDry`: text change (scene 1: `4.8 s of picture (scene 1 of 11, frames 297-440), $0`), timing change (`--tighter` on scene 3 dirties s3 and s4, $0), narration change (`new voice, every frame`, full render, voice `new`), and `--dry` renders nothing. |
| 5 | The room page (`<render>.room.html`) opens, and a sub-agent fixed a scene from it alone | **DONE** | Cold haiku sub-agent, given only `film.room.html` of a 3-scene film and the change ("the 6400 scene's label becomes ..."), ran the page's `--dry` command (`3.3 s of picture (scene 1 of 3, frames 83-182), $0`) and then the real one; it succeeded, probe and flash clean, scenes 0 and 2 from cache. I then hashed every frame of the film before and after: **only frames 83-182 changed**, the other 200 are identical. The first cold read (no run) found four confusions, fixed in `af2c617`. |
| 6 | `selftest` is green, and skill `veasy:steer` and a tool (`veasy_steer`) exist | **DONE if the final run below is green** | skill `skills/steer/SKILL.md` (2.8 kB, link `.claude/skills/steer`), tool `veasy_steer` (`plugin.yaml`, `__init__.TOOLS`), `tests/test_plugin.py` passes. Selftest and full-suite result: see Final gates. |

---

## Commit List (Branch `goal/edit-room`)

1. `c4eda21` — `docs(edit-room): add edit-room research and initialize result ledger`
2. `feat(segments): add content-addressed scene segment cache and splice for Remotion and HyperFrames`

---

## Shared Files Touched (Additive Only)

- `tt_shorts/props.py`: 1 additive branch in `render_video(work, props, out, segmented=True)` delegating to `segments.render_remotion`.
- `tt_shorts/compose.py`: 1 additive branch in `render(..., segmented=True)` delegating to `segments.render_hyperframes`.

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

---

## Final gates (run on 2026-11-07, five lanes sharing the machine)

- `python -m unittest discover -s tests`: OK, 2 skipped (4 min 40 s). Run at `af2c617`; the one commit after it only adds a paragraph to `skills/steer/SKILL.md` (size limit still met).
- `(cd remotion && npx tsc --noEmit)`: clean.
- `python -m tt_shorts.engine selftest`: 102 unchanged, no problems.

## Commits since the Antigravity stop

`6d54510` wip (state as left) · `75741f1` engine `steer`/`room`, fixes (nonexistent `formats.resolve`, price constant, `write_room` arguments, steer now saves the story, reports only new problems) · `33892ce` `--dry` tests · `2158360` skill and tool · `af2c617` room command fixes from the cold read · plus a docs commit and this file.

## Also touched (shared files, additive)

`tt_shorts/engine.py` (`steer`, `room` subcommands), `__init__.py` (tool `veasy_steer`, two timeouts), `plugin.yaml` (`veasy_steer`), `tests/test_plugin.py` (`steer` in SKILLS).

## Not done / open

- `props.render_video` now segments every Remotion render by default (`SHORTS_SEGMENTS=0` turns it off). The suite and selftest pass, but the integrating session should know.
- A timing verb on the last scene, or any narration change, costs every frame (progress bar and pan depend on total length).

## Owner decisions (added)

- Segment cache eviction (above).
- Whether `SHORTS_SEGMENTS` should default on for queue jobs.

## HyperFrames parity, measured (`stories/24835.json`, blocks kinetic-headline, number-reveal, end-card; 1107 frames; silent voice; same machine, five lanes loaded, so only the ratios mean anything)

| Run | Time |
|---|---|
| Full monolithic render (`SHORTS_SEGMENTS=0`) | 394 s |
| First segmented render (cold cache, 3 `hyperframes render --start/--end` runs) | 1012 s |
| Segmented render after changing one label in scene 1 (1 miss, 2 hits, splice `copy`, 191 of 1107 frames drawn) | 204 s, **48 % less than a full render**, and includes check, build, mix and QA |

- Frames outside the changed scene are identical to the film before the change (only frames 157-341 differ, inside scene 1's span 151-341).
- **A segmented film is not bit-identical to a monolithic render** (every frame differs: each segment is encoded on its own), so hash parity holds between segmented renders, not against the monolith. Two monolithic renders of the film before and after the edit also differed in frames 342-499 (scene 2), outside the edit: HyperFrames' own monolithic output is not frame-stable there, so the cache's reuse is the more stable of the two.
- The first segmented render is **2.6x slower** than a monolithic one (a browser start per segment). Owner decision below.
- `steer` itself was not run on a composed film end to end: the composed film's text lives in `slots.json`/compositions, which steer's `--set` does not edit. I fixed its `compose.render` call (`fix(steer)` commit) but only the segmented `compose render` path was timed.

## Owner decisions (added 2)

- Render a composed film's first pass monolithically and segment only from the second render on? Today a cold segmented render costs 2.6x.
