# Film Styles Library: Delivery Report

**Lane**: Styles (`goal/styles`)  
**Repository**: `D:\MyStaff\Veasy-styles`  
**Base Commit**: `3a6ce8aec45f83aab49c232addba6804c4dd1b8f` (`main`)  
**Date**: November 3, 2026  

---

## 1. What Shipped

### Commit History (Chronological)
1. `1e09d73`: `docs(research): film styles library research and spike report`
   - Detailed analysis of 15+ styles from `lemomo-ai/lemo-opuscar` (MIT).
   - Spike proving deterministic `<canvas>` 2D / WebGL rendering via HyperFrames paused timelines (byte-identical SHA256 hashes on repeat runs; no third engine required).
2. `a5a0b5b`: `feat(styles): core style registry, validation and brand law integration`
   - Core `tt_shorts/styles.py` registry with schema validation.
   - Brand law integration in `tt_shorts/brand.py`: `palette: pack` unrestricted; `palette: own` strictly barred from `news` and allowed for other programs only if explicitly listed under `"styles"` in `brand.json`.
   - Comprehensive test suite in `tests/test_styles.py` and `tests/test_brand.py`.
3. `aafa56e`: `feat(styles): library of 18 named film styles with schema, STYLE.md invariants and tests`
   - 18 complete styles with `style.json` and `STYLE.md` invariants adapted for vertical (1080×1920) Georgian Mkhedruli typography and Veasy safe zones.
   - 11 Wave 1 brand-safe styles: `swiss-motion`, `pictogram-motion`, `caption-news`, `data-storytelling`, `transit-map`, `satellite-briefing`, `engineering-briefing`, `whiteboard-explainer`, `blueprint`, `isometric-infographic`, `countdown`.
   - 6 Wave 2 expressive styles: `terminal-ascii`, `risograph`, `paper-cutout`, `circuit-board`, `crayon-book`, `hologram-hud`.
   - 1 Cultural proposal: `pirosmani-naive` (Niko Pirosmani aesthetic on black oilcloth).
4. `abf2475`: `feat(styles): TEXTS(t) contract for reading/safe-zone verification and Georgian numeral voice QA`
   - `check_texts_track()` in `tt_shorts/motion_rules.py`: verifies 0.5 s + 0.3 s/word reading pacing and safe zone bounds ($y \le 1380$, $x \le 940$ below $y=1100$).
   - `speech.voice_qa()` Georgian numeral validation: converts spoken numerals to digits and verifies numeric values against script numbers. Tested in `tests/test_voice_qa.py` and `tests/test_motion_rules.py`.
5. `290764e`: `feat(audio): plucked string physical modeling (panduri/chonguri) and instrument sampler`
   - Karplus-Strong physical modeling in `tools/pluck.py` with Georgian presets (`panduri` 3-string, `chonguri` 4-string with high drone).
   - Instrument sampler in `tools/sampler.py` for real CC0/CC-BY instruments (piping to temporary cache, never committing large binaries).
   - Integration into `tools/compose_music.py`. Documented in `CREDITS.md`.
6. `ca73010`: `feat(styles): variety rotation, engine options, CLI --style flags and veasy:styles skill`
   - Least-used-first style rotation in `tt_shorts/variety.py` (`variety.pick_style()`), with style tracking in fingerprints, similarities, and persistence.
   - Engine CLI integration: `--style` flag added to `render`, `still`, `write`, `probe`, `plan`, `queue`, `compose`.
   - Engine options: `"styles"` summary section in `tt_shorts.engine options`.
   - Skill documentation: `skills/styles/SKILL.md` (`veasy:styles`) with the 4-step "Make a style your own" interview workflow.
   - Hermes plugin registration in `__init__.py`.
7. `f881280`: `fix(probe): enforce utf-8 encoding on node probe subprocess`
   - Enforced explicit `encoding="utf-8"` in `tt_shorts/probe.py` for Windows subprocess execution.

---

## 2. Visual Probe and Stills Verification

### Stills Paths
- News format base stills:
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-61.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-194.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-322.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-446.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-582.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-719.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-882.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-1032.png`
  - `D:\MyStaff\Veasy-styles\out\stills\news\tbilisi-today-veasy-demo-cards-page-silent-1167.png`
- Swiss Motion style stills:
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-61.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-194.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-322.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-446.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-582.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-719.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-882.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-1032.png`
  - `D:\MyStaff\Veasy-styles\out\stills\swiss-motion\tbilisi-today-veasy-demo-cards-page-silent-1167.png`

### Probe Verification
Ran `python -m tt_shorts.engine probe stories/veasy-demo.json --look all`:
- **Editorial**: 9 scenes, 201 probed texts, **0 problems**, **0 issues**.
- **Kinetic**: 9 scenes, 201 probed texts, **0 problems**, **0 issues**.
- **Cards**: 9 scenes, 233 probed texts, **0 problems**, **0 issues**.
- Global probe result: `"problems": []`.

---

## 3. What Was Not Done & Why

1. **No Audio Ducking or Risers**:
   - *Reason*: The Veasy owner rule explicitly overrides `lemo-opuscar`'s ducking and riser practices. Veasy mandates constant background music level (mixed in ffmpeg with loudness spread $\le 0.8\text{ dB}$, -16 LUFS voice target, no volume automation).
2. **No Third Film Engine**:
   - *Reason*: The spike verified that HyperFrames (Lane B) deterministically renders `<canvas>` 2D and WebGL via paused GSAP timelines. Adding a third runtime would violate the architecture without benefit.
3. **No AI Video Generation Models**:
   - *Reason*: In accordance with the prompt brief, all film styles are 100% deterministic code animations.
4. **No Committed Audio Sample Binaries**:
   - *Reason*: Real instrument samples in `sampler.py` are downloaded on-demand into `.cache/sampler/` with CC0/CC-BY attribution in `CREDITS.md`, never committed to git.

---

## 4. Open Owner Decisions

1. **Pirosmani Naive Style Adoption**:
   - Proposal: `styles/pirosmani-naive` captures Georgia's iconic painter Niko Pirosmani (deep black oilcloth, earthen ochres, monumental stillness, chalk white highlights). Owner decision needed on whether to enable this style for cultural explainers or create a dedicated brand pack (e.g., `brands/museum-georgia`).
2. **`palette: own` Pack Approvals**:
   - Currently, `brands/sitech/brand.json` explicitly enables `["blueprint", "circuit-board", "terminal-ascii"]` for non-news programs. Owner decision needed on whether to allow additional expressive styles for client packs.
3. **Tbilisi Today Light Theme**:
   - `brands/tbilisi-today/brand.json` has `"allowed": false` for the `light` theme. Once visually reviewed and signed off, changing to `true` will enable it in variety rotation.

---

## 5. Files Touched That Other Goals Also Touch

All modifications to shared files were made **additively** without modifying existing public contracts:

| File | Other Goals | What Goal 7 (Styles) Added |
|---|---|---|
| `tt_shorts/brand.py` | Goal 1, Goal 4 | Added `"styles"` optional allow-list validation in `_validate_theme()` and brand schema. |
| `tt_shorts/engine.py` | Goal 2, Goal 4, Goal 5 | Added style resolution in `render_story()`, `"styles"` block in `options()`, `style` in `_format()`, `write_story()`, and CLI parser arguments `--style`. |
| `tt_shorts/formats.py` | Goal 4 | Added `"style"` to `OPTIONAL` format choices and format validation. |
| `tt_shorts/motion_rules.py` | Goal 3 | Added `check_texts_track()` for reading speed (0.5 s + 0.3 s/word) and safe zone verification. |
| `tt_shorts/variety.py` | Goal 4 | Added `"style"` column migration, style field in `fingerprint()`, `similarity()`, `record()`, and `pick_style()` function. |
| `tt_shorts/speech.py` | Goal 5 | Added Georgian numeral extraction and value validation in `voice_qa()`. |
| `tt_shorts/probe.py` | Goal 3, Goal 5 | Enforced explicit `encoding="utf-8"` in `run_jobs()` subprocess call. |
| `__init__.py` | Goal 5 | Registered `veasy:styles` skill and added `"style"` argument to tools. |

---

## 6. Gates and Verification Summary

- **Unit Tests**: `python -m unittest discover -s tests` $\rightarrow$ 620 tests run, 619 passed (1 expected baseline failure in `test_plugin.py` due to Windows symlinks, resolved in Goal 5).
- **Remotion TypeScript**: `(cd remotion && npx tsc --noEmit)` $\rightarrow$ Clean 0 exit code.
- **Visual Probe**: `engine probe stories/veasy-demo.json --look all` $\rightarrow$ Clean 0 problems across all 3 looks.
- **Git Rebase**: Branch `goal/styles` rebased cleanly on latest local `main` (`3a6ce8a`).
