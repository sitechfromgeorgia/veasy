# Brush Book Delivery Report: Real Rendered Catalogue & Annotated Examples

**Lane**: Brush Book (`goal/brush-book`)  
**Base Commit**: `587cd49` (`main`)  
**Worktree**: `D:\MyStaff\Veasy-brush-book`  
**Date**: November 6, 2026  

---

## 1. "Done When" Verification & Evidence

| # | "Done When" Requirement | Status | Evidence / Verification |
|---|---|---|---|
| 1 | **A test finds a real file for every brush × look × theme, and for every other listed item.** | In Progress | Will be verified by `tests/test_gallery.py::test_all_real_files_exist` and filesystem inspection of `out/gallery/stills/` and `out/gallery/clips/`. |
| 2 | **The page opens and search works, checked in a browser at phone and desktop width.** | In Progress | Will be verified by `out/gallery/index.html` structure, responsive CSS media queries (phone $\le 480\text{px}$, desktop $\ge 1024\text{px}$), and automated Playwright / node test. |
| 3 | **A sub-agent given a story and only this page picks a sensible look in under 3 tries, for 5 stories.** | In Progress | Will be evaluated by `fresh-eye-critic` subagent across 5 diverse story briefs. |
| 4 | **12 examples and 6 pairs exist and pass `check`.** | In Progress | Will be verified by `python -m tt_shorts.engine check examples/<file>.json` across all 18 files. |

---

## 2. Commit List

1. `docs(research): brush book research, inventory, and ranked backlog` (`docs/research/brush-book.md`, initial `docs/research/brush-book-result.md`).

---

## 3. What Was Not Done & Why

*(Will be updated as development proceeds)*

---

## 4. Owner Decisions

1. **Clip Format and Length in Gallery**:
   - Short loops for transitions/entrances rendered as WebM/MP4 (1.5–2s) at half-scale for fast web loading and zero-bloat caching.
2. **Plates Directory Inclusion**:
   - `out/gallery/index.html` checks dynamically for `plates/*/poster.png`. If baked posters exist from other lanes, they are surfaced in the catalogue automatically without hardcoding.

---

## 5. Shared Files Touched

1. `tt_shorts/styles.py`: Updated `summary()` still path to point to real render stills in `out/gallery/stills/`.
2. `skills/make-video/SKILL.md`: One-line addition referencing the searchable catalogue via `veasy:brush-book`.
3. `plugin.yaml`: Additive registration of `veasy_brush_book`.
4. `__init__.py`: Additive tool definition in `TOOLS` dictionary.
