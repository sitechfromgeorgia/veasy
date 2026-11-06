# The Number's Body (Plates: Matter) Result

## Overview

This document records the implementation, verification evidence, rendered artifacts, and quality gates for the `number-matter` goal (Veasy plates for physical quantities).

At the user's level:
```bash
node plates/run.mjs matter --spec spec.json --seconds 6 --seed 1 --out out/plates/budget
```
Returns a verified deterministic 1080×1920 clip (`plate.mp4`, `poster.png`), mathematical proof in `plate.json` that $\text{count} \times \text{unit} = \text{fact}$ exactly, and `anchors.json` tracking 2D centroids for DOM typography and accent dots.

---

## "Done When" Gate Evidence Table

| Requirement / "Done When" | Status | Evidence File / Command | Output Summary / Measurement |
|---|---|---|---|
| **1. `pile`, `split`, and `too-tall` baked and looked at; other forms baked or listed as not done with reason** | In Progress | `out/plates/pile/`, `out/plates/split/`, `out/plates/too-tall/` | Pending first bake |
| **2. Code proves block count equals fact, test shows non-dividing unit refused** | In Progress | `plates/matter/verifier.mjs`, `tests/test_matter.py` | Pending implementation |
| **3. Two bakes of one spec give the same `.bin` and the same mp4** | In Progress | `out/plates/determinism-1/`, `out/plates/determinism-2/` | Pending determinism test |
| **4. `flash.py` passes on every clip, including crash** | In Progress | `tt_shorts/flash.py` run on all baked clips | Area $\le 0.25$ required |
| **5. One 6-second clip sits behind real budget fact in composed film in `out/`, critic judged** | In Progress | `out/compose-matter/`, `REVIEW.md` | Pending composition and critique |

---

## Commit List

| Commit | Summary | Description |
|---|---|---|
| `docs(research)` | Initial research report and result ledger | `docs/research/number-matter.md` and `docs/research/number-matter-result.md` |

---

## Owner Decisions

1. **Plates in News:**
   - Under current `CLAUDE.md § N` and `plates/README.md`, plates are strictly barred from `news`.
   - *Status:* Awaiting owner decision. Plates operate exclusively in `explainer`, `story`, `blog`, and data pieces.
2. **Device Scene Mapping in `concepts/devices.json`:**
   - Devices `pour-or-pile`, `too-tall`, and `data-resort` wait with empty `scenes: []`.
   - *Status:* Goal 1 wires plates to the engine; we will list the proposed device mappings in our result.

---

## Shared Touches

None so far. Only files inside `plates/matter/` and `docs/research/` are authored, preserving the strict lane boundary.
