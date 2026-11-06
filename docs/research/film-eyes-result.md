# Result: The Film's Eyes (film-eyes)

**Goal:** Teach a film to look at itself: free pixel checks and a fresh-eye review loop on both engines, so an agent fixes dull or broken frames before a person ever sees them.  
**Branch:** `goal/film-eyes`  
**Date:** 2026-11-06  
**Status:** In Progress (First commit: Research & Architecture)

---

## 1. Done When Evidence Mapping

| "Done When" Requirement | Status | Evidence / Verification |
|---|---|---|
| **1. 12 seeded-broken stories are in `tests/fixtures/review/`, and at least 10 are caught.** | In Progress | Fixtures in design; sub-agent `Seeded Defect Maker` generating test suite. |
| **2. Approved demos raise no false hold.** | In Progress | Calibration suite in design; baseline verified across `24835.json`, `veasy-demo.json`, `veasy-scenes.json`, `24725.json`. |
| **3. Before and after sheets show a real fix on 3 films, and the facts diff is empty.** | In Progress | Repair loop architecture specified with `facts_diff(before, after) == []` invariant. |
| **4. Skill `veasy:review` and a tool exist, and a sub-agent used them cold.** | In Progress | Skill and Hermes tool schema defined; `Fresh-Eye Critic` sub-agent conducting cold evaluation. |

---

## 2. Commit List

1. `docs(research): film-eyes research, literature review, and initial result tracker`
2. `feat(eyes): free pixel checks, pacing metrics, and safety gates (tt_shorts/eyes.py)`

---

## 3. What Was Not Done & Why

- Visual changes to existing scene components: None needed; the film-eyes lane operates as an auditor and review loop, observing existing frames without modifying core Remotion/HyperFrames rendering primitives.
- Cloud/paid API calls: Banned by ground rules; all review and repair steps execute locally with deterministic algorithms.

---

## 4. Owner Decisions

1. **Warning vs Hold Thresholds**: All newly introduced checks (`same_picture_twice`, `empty_middle`, `no_hero_frame`, `metronome_cuts`, `spoken_redundancy`) trigger *warnings* by default; only safety (`flash`) and reading time (`read`) hold renders today.
2. **Review Rounds Default**: Configured to `--rounds 2`, hard-capped at 3 machine rounds and 2 look rounds.

---

## 5. Shared Files Touched

- `tt_shorts/engine.py` (Additive: `review` subcommand added at end of argument parser)
- `plugin.yaml` (Additive: `veasy_review` tool added to provides_tools)
- `__init__.py` (Additive: `veasy_review` tool and schema added to TOOLS)
- `tests/test_plugin.py` (Additive: `"review"` added to SKILLS tuple)
- `README.md` (Additive: `engine review` documented)
- *(CLAUDE.md is not modified; proposed paragraph included in Section 6 below)*

---

## 6. Proposed Paragraph for CLAUDE.md

```markdown
- **Review and self-repair** (`tt_shorts/eyes.py`, `tt_shorts/review.py`, skill `veasy:review`, tool `veasy_review`):
  `engine review <story> [--rounds 2]` runs free pixel and pacing checks on either engine's frames: duplicate pictures (`golden.dhash`), empty central zones, missing hero frames, metronome cuts, and spoken redundancy. It applies non-destructive repairs (pacing, layout, line wrapping) capped at 3 machine rounds and 2 look rounds, while strictly verifying that facts never change (`facts_diff` stays empty). Flash and unreadable text hold; other checks warn until calibrated.
```
