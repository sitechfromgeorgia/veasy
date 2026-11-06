# Veasy Lit Surfaces — Results Report

## 1. Executive Summary & One-Line Contract

**One-line command:**
```bash
node plates/run.mjs surface --spec plates/surface/specs/loop_01_limestone_rake.json --seconds 6 --seed 1 --out out/plates/loop_01_limestone_rake
```

**What it returns:**
A deterministic, seamless 6-second greyscale plate (`plate.mp4`, `poster.png`, `plate.json`, `anchors.json`) relighting physical material height and Scharr normal maps with a continuous moving light (`rake`, `sweep`, `dawn`) in Oren-Nayar + Blinn-Phong GLSL shading with triangular high-pass (TPDF) anti-banding dither.

---

## 2. "Done When" Scorecard & Evidence

| # | Done When Requirement | Status | Concrete Evidence |
|---|---|---|---|
| **1** | **At least 4 materials are shipped with their ledger, however the quota went, and the count is stated.** | **DONE (9 shipped)** | **9 materials** shipped and verified in `assets/surfaces/` and `assets/surfaces/LEDGER.json` (total **6.70 MB**, well under the 15 MB limit): `limestone`, `worn_plaster`, `handmade_paper`, `raw_wood`, `hammered_metal`, `woven_cloth`, `ornament_rosette`, `ornament_palmette`, `ornament_meander`. Verified by `python tools/build_surfaces.py --check` (`OK: assets/surfaces budget and ledger pass`) and `tests/test_surfaces.py` (6/6 tests pass). |
| **2** | **12 loops are baked behind real facts' layouts, about 83 seconds a bake at most, and every loop closes without a jump.** | **DONE** | All 12 loops baked in **20.3 s – 36.3 s** (95–167 ms/frame, all $\le 83\text{ s}$) and verified in `out/plates/12_loops_report.json`. Every loop closes with trigonometric $C^1$ continuity (`mean_diff` $0.0034\text{--}0.0098$, `p95_diff` $\le 0.0235$, `seam_pass: true` on all 12). Proven behind real facts in `out/plates/composites/loop_01..12_*_fact.png` and in HyperFrames composed film `out/compose_plate_test/` (`engine compose check`: `problems: []`; `engine compose look`: `out/compose_plate_test/.veasy/look/review-beats.jpg`, `review-phone.jpg`). |
| **3** | **Text panels stay readable on every loop (the critic has judged them), and no banding shows on the darkest loop.** | **DONE** | Audited by independent `fresh-eye-critic` subagent (`00b2d624-6f19-4f3a-83f7-880eb563a465`): **12/12 PASS** across all 12 factual composites after applying word-boundary wrapping, centered card padding, and separable X-then-Y periodic cosine tiling, and confirmed **zero 8-bit staircase banding** on the darkest loops (`out/plates/loop_05_handmade_paper_dawn/poster.png` and `out/plates/loop_08_hammered_metal_sweep/poster.png`). |
| **4** | **No generated image holds text, a face, a logo or a real place: a critic has looked at every one.** | **DONE** | Audited by independent `fresh-eye-critic` subagents (`333e6c89-e90a-43b4-b50f-586393fef476` and `34b3be96-f918-4d49-a3ba-d6fdd672064b`). Critic caught footwear at the bottom edge of `ornament_knot` (dropped upon HTTP 429 quota exhaustion) and pseudo-glyphs in initial `ornament_meander` (regenerated and passed 100% purity check). All 9 shipped materials hold zero text, faces, logos, or real places. |

---

## 3. Shipped Materials & Quota Accounting (9 Materials, 6.70 MB)

We generated images in the exact priority order specified. We stopped immediately on the first HTTP 429 quota error (on attempt 12 while regenerating `ornament_knot`), shipping **9 critic-approved materials**:

| # | Material ID | Category | Depth | Roughness | Files (`assets/surfaces/<id>/`) | Critic Verdict |
|---|---|---|---:|---:|---|---|
| 1 | `limestone` | stone | 1.2 | 0.75 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 2 | `worn_plaster` | mineral | 1.1 | 0.85 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 3 | `handmade_paper` | paper | 1.1 | 0.90 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 4 | `raw_wood` | wood | 1.0 | 0.70 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 5 | `hammered_metal` | metal | 1.4 | 0.45 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 6 | `woven_cloth` | textile | 1.1 | 0.80 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 7 | `ornament_rosette` | ornament | 1.5 | 0.65 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 8 | `ornament_palmette` | ornament | 1.5 | 0.65 | `height.png`, `normal.png`, `meta.json` | **PASS** (100% pure) |
| 9 | `ornament_meander` | ornament | 1.4 | 0.70 | `height.png`, `normal.png`, `meta.json` | **PASS** (regenerated & verified) |

All 9 materials record `license: "ai"`, `commercial: true`, and `n13_label_required: true` in `assets/surfaces/LEDGER.json`.

---

## 4. 12 Baked Production Loops & Verification Evidence

Recorded in `out/plates/12_loops_report.json`:

| # | Loop ID | Material | Light | Bake Time | ms/frame | Seam Mean Diff | Seam P95 Diff | Critic Verdict | Fact Composite Still |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 1 | `loop_01_limestone_rake` | `limestone` | `rake` | 33.62 s | 150 | 0.0073 | 0.0196 | **PASS** | `out/plates/composites/loop_01_limestone_rake_fact.png` |
| 2 | `loop_02_limestone_dawn` | `limestone` | `dawn` | 20.33 s | 95 | 0.0062 | 0.0157 | **PASS** | `out/plates/composites/loop_02_limestone_dawn_fact.png` |
| 3 | `loop_03_worn_plaster_sweep` | `worn_plaster` | `sweep` | 28.32 s | 131 | 0.0036 | 0.0118 | **PASS** | `out/plates/composites/loop_03_worn_plaster_sweep_fact.png` |
| 4 | `loop_04_worn_plaster_rake` | `worn_plaster` | `rake` | 29.18 s | 136 | 0.0058 | 0.0157 | **PASS** | `out/plates/composites/loop_04_worn_plaster_rake_fact.png` |
| 5 | `loop_05_handmade_paper_dawn` | `handmade_paper` | `dawn` | 27.93 s | 134 | 0.0042 | 0.0118 | **PASS** | `out/plates/composites/loop_05_handmade_paper_dawn_fact.png` |
| 6 | `loop_06_handmade_paper_sweep` | `handmade_paper` | `sweep` | 28.13 s | 131 | 0.0034 | 0.0118 | **PASS** | `out/plates/composites/loop_06_handmade_paper_sweep_fact.png` |
| 7 | `loop_07_raw_wood_rake` | `raw_wood` | `rake` | 23.99 s | 111 | 0.0073 | 0.0196 | **PASS** | `out/plates/composites/loop_07_raw_wood_rake_fact.png` |
| 8 | `loop_08_hammered_metal_sweep` | `hammered_metal` | `sweep` | 27.12 s | 125 | 0.0052 | 0.0157 | **PASS** | `out/plates/composites/loop_08_hammered_metal_sweep_fact.png` |
| 9 | `loop_09_woven_cloth_rake` | `woven_cloth` | `rake` | 24.18 s | 109 | 0.0086 | 0.0196 | **PASS** | `out/plates/composites/loop_09_woven_cloth_rake_fact.png` |
| 10 | `loop_10_ornament_rosette_rake` | `ornament_rosette` | `rake` | 36.29 s | 167 | 0.0098 | 0.0235 | **PASS** | `out/plates/composites/loop_10_ornament_rosette_rake_fact.png` |
| 11 | `loop_11_ornament_palmette_dawn` | `ornament_palmette` | `dawn` | 26.91 s | 124 | 0.0069 | 0.0157 | **PASS** | `out/plates/composites/loop_11_ornament_palmette_dawn_fact.png` |
| 12 | `loop_12_ornament_meander_sweep` | `ornament_meander` | `sweep` | 35.09 s | 162 | 0.0042 | 0.0157 | **PASS** | `out/plates/composites/loop_12_ornament_meander_sweep_fact.png` |

### Composed Film Proof (`compose/24835` in `out/compose_plate_test`)
- Placed `<video muted playsinline src="assets/plate.mp4" ... data-layout-ignore></video>` behind scene `s3-number.html` (`6 400 აბონენტს დროებით შეუწყდება გაზის მიწოდება`).
- `python -m tt_shorts.engine compose check stories/24835.json --project out/compose_plate_test --no-hf`: `problems: []`, `facts: 46`, `texts: 570`, `blocked: []`.
- `python -m tt_shorts.engine compose look stories/24835.json --project out/compose_plate_test`: `problems: []`, contact sheets generated at `out/compose_plate_test/.veasy/look/review-beats.jpg` and `review-phone.jpg`.

---

## 5. Integration Requirements for Goal 1 (`plates-core`) & `concepts/devices.json`

### What we need from `tt_shorts/engine.py`, `brushes/`, and `remotion/` (owned by Goal 1):
1. **Plate resolution & caching:** Map a scene or film's plate request `{"kind": "surface", "spec": {"material": "limestone", "light": "rake"}}` to the cached bake folder via `plates/run.mjs` hash (`plate.mp4`, `poster.png`, `anchors.json`).
2. **N13 Label Enforcement:** Because `assets/surfaces/LEDGER.json` marks all 9 materials with `"license": "ai"` and `"n13_label_required": true`, any non-news scene using a `surface` plate must include the pack's illustrative label (`საილუსტრაციო`) and must be rejected for `news`, `crime`, `incidents`, or `deaths`.
3. **Palette Mapping:** Map the greyscale plate luma `[0, 1]` between the brand pack's `canvas` and `ink` tokens at `opacity: 0.35–0.50` behind the scene DOM.

### Devices in `concepts/devices.json` that `plates/surface` can draw:
Currently waiting with `"scenes": []` in `concepts/devices.json`:
- **`treated-picture`** (`"use": "the subject's texture behind the type", "rungs": [1], "news": "yes"`): Directly drawn by `plates/surface` using any of the 9 materials behind `stat`, `quote`, `points`, `glossary`, `impact`.
- **`material-film`** (`"use": "one film in one drawn material", "rungs": [1], "news": "cond"`): Drawn by locking one material (`limestone`, `handmade_paper`, `raw_wood`, `worn_plaster`) across a film's scenes while varying `crop`, `rotation`, and `light` (`rake` $\to$ `sweep` $\to$ `dawn`).
- **`document-close-up`** (`"use": "a law or a decision: the line itself, boxed", "rungs": [1], "news": "yes"`): Drawn by `handmade_paper` (`dawn` or `rake`) behind `quote`, `glossary`, or `checklist` scenes in the `law` and `explainer` programs.
- **`period-pastiche`** (`"use": "history in the look of its period", "rungs": [6], "news": "no"`): Drawn by `worn_plaster`, `ornament_rosette`, `ornament_palmette`, and `ornament_meander` under raking light.

---

## 6. Commit List

1. `c64eb7a` — `docs(research): lit surfaces research, sources, and backlog`
   - Studied 24 sources across 6 domains; authored one-line contract, license table, and ranked backlog in `docs/research/lit-surfaces.md`.
2. `feat(plates): add lit surfaces plate kind, 9 materials with normals, and build pipeline`
   - Added `tools/build_surfaces.py` and `tests/test_surfaces.py` (6 unit tests).
   - Built 9 seamless greyscale height + Scharr normal map materials into `assets/surfaces/` (6.70 MB total) with `assets/surfaces/LEDGER.json`.
   - Implemented `plates/surface/index.html`, `plates/surface/README.md`, and 12 production loop specs in `plates/surface/specs/`.
   - Updated `docs/research/lit-surfaces-result.md` with full verification evidence.

---

## 7. What We Didn't Do and Why

- **10th material (`ornament_knot`):** The initial generation of `ornament_knot` failed the Fresh-Eye Critic's purity gate because human footwear/boots were visible at the bottom edge of the stone block. When we invoked the subagent to regenerate a clean orthographic version, the shared image quota returned `HTTP 429: Resource exhausted`. Following the ground rule (*"on the first quota error, stop generating and go on without"*), we immediately halted generation and omitted `ornament_knot`, shipping 9 verified materials (well above the minimum 4 required, including 3 clean ornament panels: `ornament_rosette`, `ornament_palmette`, `ornament_meander`).

---

## 8. Owner Decisions

- **N13 Illustrative Label on Abstract Material Relief:** `assets/surfaces/LEDGER.json` marks all 9 AI-generated material textures with `"n13_label_required": true`. The owner may decide whether pure abstract stone/paper grain underlays at low opacity require the on-screen „საილუსტრაციო“ badge in non-news programs (`explainer`, `law`, `blog`) or if the ledger record suffices.

---

## 9. Touched Shared Files

- **None.** Zero shared files were modified. All work is strictly confined to:
  - `docs/research/lit-surfaces.md`
  - `docs/research/lit-surfaces-result.md`
  - `tools/build_surfaces.py`
  - `tests/test_surfaces.py`
  - `assets/surfaces/`
  - `plates/surface/`

---

## 10. Proposed Paragraph for `CLAUDE.md`

```markdown
- **Lit Surfaces (`plates/surface/`, `tools/build_surfaces.py`, `assets/surfaces/`)**: Physical material relief plates (`limestone`, `worn_plaster`, `handmade_paper`, `raw_wood`, `hammered_metal`, `woven_cloth`, and 3 original ornament panels) relit by deterministic moving light (`rake`, `sweep`, `dawn`). Built only by `python tools/build_surfaces.py` (separable periodic tiling + multi-scale Scharr normals, <= 15 MB in git) with provenance in `assets/surfaces/LEDGER.json` (`licence: "ai"`, N13 label). Tone only, no text, no accent; never used for `news`, crime, incidents or deaths.
```
