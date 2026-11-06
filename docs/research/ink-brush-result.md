# Ink Brush Delivery Result & Verification Log

**Lane**: The Ink Brush (`goal/ink-brush`, `plates/ink/`)  
**Repository**: `D:\MyStaff\Veasy-ink-brush`  
**Base Commit**: `587cd49` (`main`)  
**Date**: November 6, 2026  

---

## 1. Executive Summary & Verification Matrix

| "Done when" Requirement | Status | Evidence / Verification Artifact | Notes |
|---|---|---|---|
| One sheet shows all 44 drawings in all 6 materials, mid-stroke, and you have looked at it | In Progress | `out/plates/ink/contact_sheet.html`, `out/plates/ink/sheet_stills/` | Target: 264 mid-stroke combinations across all 44 sanitized drawings |
| Six 4-second clips are baked, and `plate.json` shows each cost | In Progress | `out/plates/ink/woodcut/plate.json`, `out/plates/ink/ink_wash/plate.json`, `out/plates/ink/blueprint/plate.json`, `out/plates/ink/halftone/plate.json`, `out/plates/ink/chalk/plate.json`, `out/plates/ink/pencil_hatch/plate.json` | Must measure `ms_per_frame` under SwiftShader limits |
| The critic scores each material on "painted, not filtered" and each one gets at least 4 of 5, with reasons kept | In Progress | Critic assessment log in Section 3 of this document | Target $\ge 4.0/5.0$; any material failing is cut, not shipped |
| A second bake of the same spec gives the same mp4 (deterministic) | In Progress | Bit-exact comparison of `frame_hash` and SHA256 file hashes across repeat bakes | Pure function of $(t, \text{spec}, \text{seed})$ |
| `plates/ink/README.md` is complete, and a sub-agent got a good clip from it on the first try | In Progress | `plates/ink/README.md`, sub-agent execution transcript and output manifest | Verifies documentation usability |

---

## 2. Commit Log (Chronological)

1. Pending commit: `docs(research): foundational physical media research and ink brush engine roadmap` (`docs/research/ink-brush.md`, `docs/research/ink-brush-result.md`)

---

## 3. Critic Scores & Evaluation Matrix ("Painted, Not Filtered")

*(Evaluations populated by the Fresh-Eye Critic sub-agent upon rendered stills)*

| Material | Critic Score (1–5) | Verdict | Critic Notes & Observations |
|---|---|---|---|
| `woodcut` | Pending | - | - |
| `ink_wash` | Pending | - | - |
| `blueprint` | Pending | - | - |
| `halftone` | Pending | - | - |
| `chalk` | Pending | - | - |
| `pencil_hatch` | Pending | - | - |

---

## 4. Benchmark Costs (`plate.json`)

| Material | Resolution | Seconds | FPS | Total Frames | ms / frame | Total Bake Time | Frame Hash |
|---|---|---|---|---|---|---|---|
| `woodcut` | 1080×1920 (scale 1.0) | 4.0 | 30 | 120 | TBD | TBD | TBD |
| `ink_wash` | 1080×1920 (scale 1.0) | 4.0 | 30 | 120 | TBD | TBD | TBD |
| `blueprint` | 1080×1920 (scale 1.0) | 4.0 | 30 | 120 | TBD | TBD | TBD |
| `halftone` | 1080×1920 (scale 1.0) | 4.0 | 30 | 120 | TBD | TBD | TBD |
| `chalk` | 1080×1920 (scale 1.0) | 4.0 | 30 | 120 | TBD | TBD | TBD |
| `pencil_hatch` | 1080×1920 (scale 1.0) | 4.0 | 30 | 120 | TBD | TBD | TBD |

---

## 5. What Was Not Done & Why

1. **No Third Film Engine**: Built strictly as a plate within `plates/ink/` and executed via `plates/run.mjs` on headless Chromium/SwiftShader. The engines play the generated MP4 as a local file behind text.
2. **No Color Palette Leakage**: Shaders output tone only (greyscale on black). Remotion/HyperFrames map black to brand canvas and white to brand ink.
3. **No Unlicensed Shaders or Code**: 100% clean-room mathematical shaders derived from peer-reviewed scientific literature and physical optics equations.
4. **No Untracked Assets**: Zero external downloaded texture images or photo scans. All paper tooth, slate grain, and line boil are evaluated procedurally from seeded hash functions.

---

## 6. Devices from `concepts/devices.json` Drawn by This Kind

The Ink Brush plate enables the following devices in `concepts/devices.json`:
- `"material-film"`: `{"use": "one film in one drawn material", "scenes": ["ink_plate"], "rungs": [1], "news": "cond"}` (can render any story drawing in woodcut, ink wash, blueprint, halftone, chalk, or pencil hatch).
- `"drawn-reveal"`: `{"use": "the object draws itself on screen", "scenes": ["ink_plate", "draw", "sign"], "rungs": [1, 5], "news": "yes"}` (draws the object stroke by stroke in physical media with paper bleed).
- `"period-pastiche"`: `{"use": "history in the look of its period", "scenes": ["ink_plate"], "rungs": [6], "news": "no"}` (renders archival woodcut, blueprint, or vintage newsprint halftone).
- `"treated-picture"`: `{"use": "the subject's texture behind the type", "scenes": ["ink_plate"], "rungs": [1], "news": "yes"}` (physical paper tooth and medium texture behind typography).

---

## 7. Shared Files Touched

None. (Strict compliance with lane ownership: only files in `plates/ink/`, `docs/research/`, and lane test fixtures are authored).
Proposal for `CLAUDE.md`:
> - **Plates (ink)** (`plates/ink/`): physical media drawings (woodcut, ink wash, blueprint, halftone, chalk, pencil hatch) baked as tone-only clips, with paper tooth, seeded line boil on twos, stroke-by-stroke reveals, and fluid ink flood transitions.
