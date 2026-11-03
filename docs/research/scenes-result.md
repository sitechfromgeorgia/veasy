# Veasy Scene Library Expansion — Results Report

## 1. Executive Summary

In this lane (`goal/scenes`), we conducted extensive visual journalism research across 25 leading international newsrooms, data design studios, and vertical video producers (documented in `docs/research/scenes.md`). Based on the ranked backlog, we built, wired, tested, demoed, and visually verified **9 new production scene types (brushes)** for Veasy's Remotion engine:

1. **`ranking`** (order 160): 3–5 ranked items with rank badges, labels, values, and proportional progress bars.
2. **`versus`** (order 170): Head-to-head two-side comparison with metrics, notes, and a centered "VS" badge.
3. **`countdown`** (order 180): Large hero countdown number with unit, target date badge, and explanatory label.
4. **`calendar`** (order 190): Physical desk calendar sheet with header, large day number, weekday, and scheduled event card.
5. **`glossary`** (order 200): Explanatory term card for legal, economic, or technical concepts with context category pill and framed definition.
6. **`checklist`** (order 210): Factual requirements or documentation criteria list with checkmark (done) and pending status indicators.
7. **`impact`** (order 220): "What changes for you" card specifying target group, change description, and effective date badge.
8. **`route`** (order 230): Geographic / transit transit path connecting 2–4 stops with origin-to-destination rail, distance badge, and detail label.
9. **`budget`** (order 240): Segmented proportional progress bar breaking down a total into 2–4 categories with legend table and percentages.

All 9 brushes conform strictly to Veasy brand principles (dark canvas, light ink, single red accent reserved exclusively for active indicators, FiraGO typography, no category colors, no drop shadows, and strict safe zones: text y: 248–1380, rail x: 940 below y: 1100).

---

## 2. Commit List

The following 3 commits were made on branch `goal/scenes` in worktree `D:\MyStaff\Veasy-scenes`:

1. `27ac0f0` — `docs(research): scene library research and ranked backlog`
   - Detailed study of 25 sources (Reuters Graphics, NYT, BBC, Bloomberg, Vox, Axios, The Pudding, FT Visual Vocabulary, Datawrapper, etc.).
   - License compliance table (OFL, MIT, Apache-2.0, BSD; strict rejection of AGPL / commercial restrictions).
   - Ranked backlog of candidate scenes with priority, value, and effort estimates.

2. `6d52f9e` — `feat(scenes): add 9 new scene types (ranking, versus, countdown, calendar, glossary, checklist, impact, route, budget)`
   - Added brush definitions: `brushes/{ranking,versus,countdown,calendar,glossary,checklist,impact,route,budget}.json` (orders 160–240).
   - Registered scene types in `tt_shorts/news_check.py` (`SCENE_TYPES`, `NOT_SCREEN`).
   - Implemented shape validation in `tt_shorts/engine.py` (`shape_problems`).
   - Extended TypeScript contracts in `remotion/src/types.ts` (`Item`, `Scene`).
   - Implemented Remotion scene components in `remotion/src/scenes/extra.tsx`.
   - Exported and registered scenes in `remotion/src/scenes/index.tsx` (`SCENES`).
   - Added comprehensive test coverage in `tests/test_catalog.py` and `tests/test_scenes.py`.
   - Documented scenes in `skills/write-script/SKILL.md` (expanded from 22 to 31 scene types, kept under 12k chars).
   - Created demo stories `stories/veasy-new-01.json` and `stories/veasy-new-02.json`.

3. `a596122` — `feat(directors, programs): additively integrate 9 new scene types into directors and programs`
   - Weighted scene additions in 6 directors: `data.json`, `brief.json`, `chronicle.json`, `type.json`, `map.json`, `witness.json`.
   - Scene additions in 2 non-news programs: `programs/explainer.json`, `programs/law.json`.

---

## 3. Demo Stories & Generated Stills

Two production-grade Georgian demo stories were authored and validated against news check rules N1–N12:
- `stories/veasy-new-01.json`: Covers `ranking`, `versus`, `budget`, and `impact`.
- `stories/veasy-new-02.json`: Covers `countdown`, `calendar`, `glossary`, `checklist`, and `route`.

### Verified Stills Paths

#### Cards Look (Dark Theme):
- **Ranking**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-01-cards-page-silent-231.png`
- **Versus**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-01-cards-page-silent-415.png`
- **Budget**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-01-cards-page-silent-600.png`
- **Impact**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-01-cards-page-silent-797.png`
- **Countdown**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-cards-page-silent-230.png`
- **Calendar**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-cards-page-silent-376.png`
- **Glossary**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-cards-page-silent-564.png`
- **Checklist**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-cards-page-silent-788.png`
- **Route**: `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-cards-page-silent-987.png`

#### Editorial Look:
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-01-editorial-page-silent-*.png`
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-editorial-page-silent-*.png`

#### Kinetic Look:
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-01-kinetic-page-silent-*.png`
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-kinetic-page-silent-*.png`

#### Light Theme Preview:
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-01-cards-page-silent-light-*.png`
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-new-02-cards-page-silent-light-*.png`

### Probe Validation Results
The layout probe (`python -m tt_shorts.engine probe <story> --look all`) ran across all 3 looks (`cards`, `editorial`, `kinetic`):
- `stories/veasy-new-01.json`: **0 problems, 0 overflow issues** across all looks.
- `stories/veasy-new-02.json`: **0 problems, 0 overflow issues** across all looks.

---

## 4. What Was Not Done & Why

1. **Waffle / 100-dot matrix**:
   Veasy already features the `share` brush which renders a 10x10 fill grid. Additional variations (such as dual-category waffle charts) belong in Goal 3 (motion/transitions/variety options) as styling options rather than a duplicate top-level scene type.
2. **Animated Multi-Step Process Flow**:
   Flow diagrams with branching decisions require extensive layout graphs and dynamic connector routing. This is better served by HyperFrames lanes (Goal 4) rather than rigid Remotion scene cards.
3. **Dynamic GPX Map Route Rendering**:
   To comply with the offline/no-paid-API ground rule and keep tests self-contained, `route` was built as a clean topological transit line with connected nodes, distances, and highlighted destinations rather than requiring an external vector tile rendering pipeline.

---

## 5. Open Owner Decisions

1. **Light Theme Production Status**:
   `tbilisi-today` brand config currently has `"theme": {"light": {"allowed": false}}`. While light theme renders cleanly and passes contrast probes, production rendering of light theme Shorts waits for owner approval.
2. **Transit Vehicle Pictograms**:
   The `route` scene currently uses clean typographic pills and dots. Goal 2 (icons lane) may add custom SVG icons for bus, train, and flight routes.
3. **Pacing and Timing Defaults for Explainer Videos**:
   `glossary` and `impact` scenes contain rich textual explanations. For deep explainer programs, consider extending default scene durations from 3.5s to 4.5s for slower voice presets.

---

## 6. Files Touched That Other Goals May Touch

To maintain smooth parallel development with the other 4 goals, all changes in shared files were made strictly additively:

1. `remotion/src/types.ts`:
   - Added optional fields to `Item`: `rank?: number`, `state?: "done" | "pending"`, `note?: string`, `share?: number`.
   - Added optional fields to `Scene`: `target?`, `day?`, `month?`, `weekday?`, `event?`, `term?`, `definition?`, `context?`, `change?`, `stops?`, `detail?`, `when?`.
2. `tt_shorts/news_check.py`:
   - Added 9 scene type names to `SCENE_TYPES`.
   - Added `"rank"`, `"state"`, `"status"` to `NOT_SCREEN`.
3. `tt_shorts/engine.py`:
   - Added shape validation cases for the 9 scenes in `shape_problems()`.
4. `skills/write-script/SKILL.md`:
   - Added rows for the 9 new scenes to the scene catalog table.
5. `directors/*.json`:
   - Added additive scene entries with weights to `data.json`, `brief.json`, `chronicle.json`, `type.json`, `map.json`, and `witness.json`.
6. `programs/*.json`:
   - Added new scenes to allowed lists in `explainer.json` and `law.json`.
