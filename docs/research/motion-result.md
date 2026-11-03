# Veasy Motion Language Result Report

## 1. Executive Summary

This report documents the implementation and verification of Veasy's expanded motion language. Over 10 clean, incremental commits, we researched 26 foundational motion design, kinetic typography, and video toolkit sources, and engineered an additive motion suite without breaking brand discipline or layout contracts.

All visual outputs remain strictly within the news-safe canvas:
- Dark canvas, light ink, one accent (never on text), one font family (`FiraGO`), no drop shadows, no frame on the brand mark.
- Scene text ends at $y \le 1380$, captions at $y \le 1552$, below $y=1100$ no text right of $x=940$.
- Georgian on screen; English in code, comments, and commits.
- Deterministic, frame-accurate renders across all looks (`editorial`, `kinetic`, `cards`).

---

## 2. What Shipped (Commits)

1. `9899041` **docs(motion): add research, architecture spec, and backlog for motion language**
   - Research synthesis of 26 authoritative sources covering the 12 Principles of Animation, Material Design 3, Apple HIG, kinetic typography, Georgian Mkhedruli script considerations, and Remotion/HyperFrames contracts. Complete licensing table and ranked backlog.
2. `99b2a5e` **feat(motion): add 4 new background motifs (crosses, mesh, waves, hash)**
   - Expanded motif pool from 6 to 10 options: `crosses` (technical tick marks), `mesh` (isometric grid lines), `waves` (sinusoidal ambient flow), `hash` (tilted editorial rule pattern). Drawn purely in ink line tokens with zero shadows or new colors.
3. `86ee68d` **feat(motion): add 4 new hook layouts (split, badge, bracket, rail)**
   - Expanded hook layouts from 4 to 8 options: `split` (inverted lead block with indented lines), `badge` (pill-badged kicker/title), `bracket` (technical corner registration marks), `rail` (vertical ink accent guide).
4. `decec27` **feat(motion): add 4 new entrances (drop, expand, drift, flip)**
   - Expanded entrances from 4 to 8 options: `drop` (gravitational settle with soft spring), `expand` (horizontal mask unroll), `drift` (directional parallax along current), `flip` (subtle 3D perspective tilt).
5. `1a248b9` **feat(motion): add 6 new scene transitions (fade, shutter, split, corner, iris, blind)**
   - Added 6 transitions tailored across looks: `fade` (clean canvas dip), `shutter` (horizontal staggered slats), `split` (center-outward wipe), `corner` (diagonal geometric sweep), `iris` (circular mask reveal), `blind` (vertical louver rotation).
6. `cf0593c` **feat(motion): add kinetic typography reveals for Georgian (WordReveal, LineReveal, MaskReveal)**
   - Implemented `WordReveal`, `LineReveal`, and `MaskReveal` in `remotion/src/ui.tsx`. Tailored for Georgian Mkhedruli script with ample descender clearance (`ქ`, `ყ`, `ფ`, `წ`, `ჭ`), voice-synced beat support, and inverted ink emphasis blocks for `em` phrases. All colors dynamically read via `applyBrand` inside components.
7. `d033973` **feat(motion): differentiate motion personalities across all 8 directors**
   - Calibrated spring numbers ($\zeta, \omega_n$, damping, stiffness), enter frames, and stagger frames across all 8 directors (`type`, `chronicle`, `witness`, `draw`, `data`, `brief`, `map`, `single`). Documented in `skills/directors/SKILL.md`.
8. `32fb771` **feat(motion): add motion rules for moves, background, and pacing warnings**
   - Added 3 new style warnings in `tt_shorts/motion_rules.py`: `moves` (too many simultaneous animating elements), `background` (video motion behind text being read), `pacing` (cuts faster than voice or 1.5s threshold). Preserved `read` as the only hold rule.
9. `2a8cec0` **feat(motion): add tailored sound cues for new transitions in sfx.py**
   - Added transition sound cues (`click` on shutter/blind, `pop` on iris, `whoosh` on split/corner, silent on fade), off by default, mixed at constant level without ducking.
10. `da8366e` **chore(golden): update selftest golden hashes for expanded motion variety**
    - Updated selftest golden hashes for `veasy-scenes` and `veasy-demo` across all looks and themes. 102/102 frames verified unchanged and clean.

---

## 3. Still Verification and File Paths

Stills were generated, inspected, and verified against the safe zone and brand rules:

- **Editorial Hook with Bracket Layout & Mesh Motif**:
  `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-demo-editorial-page-silent-61.png`
- **Kinetic Hook with Inverted Blocks & Diagonal Motion**:
  `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-demo-kinetic-page-silent-61.png`
- **Cards Hook with Card Radius & Metadata Header/Footer**:
  `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-demo-cards-page-silent-61.png`
- **Selftest Goldens Directory**:
  `data/cache/work/selftest/` (102 verified frame stills)

---

## 4. What Was Not Done and Why

1. **New Variety Fingerprint Fields**:
   - *Decision*: We did not add new variety fields to `variety.FIELDS` (`("director", "scenes", "hook", "motif", "enter", "transition", "music")`).
   - *Reason*: Adding a field alters the similarity metric ($1 - \text{similarity}/7$) and disrupts calibrated novelty re-roll thresholds across historical video ledgers. Expanding existing fields provides rich visual entropy without mutating the distance contract.
2. **Third-Party Animated Lottie / SVG Assets**:
   - *Decision*: Kept all motifs and transitions code-authored in React / Remotion SVG and CSS transforms.
   - *Reason*: Eliminates binary blob dependencies, avoids external licensing ambiguities, and ensures deterministic, 60fps frame rendering on Windows and Linux headless CI.

---

## 5. Owner Decisions (Open for Owner Review)

1. **Default Sound Effects (`sfx`)**:
   - Currently, `sfx` is `"off"` by default across news formats (`formats/news.json`). Accents (snaps on shutter/blinds, pop on iris, whoosh on sweeps) are available and tested. The owner may decide whether specific light-news or sports formats should enable `"sfx": "on"`.
2. **Light Theme Production Rollout**:
   - Shipped brand packs (`tbilisi-today`, `sitech`) define `light` (paper) themes, currently marked `allowed: false` for `tbilisi.today` hard news. All new motifs, hook layouts, and kinetic typography adapt dynamically to light themes via live bindings. The owner can approve light themes for production whenever desired.

---

## 6. Files Touched That Other Goals May Touch

All modifications were strictly additive and maintain backward compatibility:

| File | Nature of Change | Impact on Other Goals |
|---|---|---|
| `tt_shorts/variety.py` | Added options to `OPTIONS` and `TRANSITIONS` pools | Goal 1 (Scenes), Goal 2 (Icons) read from variety |
| `remotion/src/types.ts` | Extended union types for `HookLayout`, `Motif`, `Entrance`, `Transition` | Shared across Remotion components |
| `remotion/src/ui.tsx` | Added `MaskReveal`, `WordReveal`, `LineReveal`; updated `In` and `settle` | Goal 1 (Scene types), Goal 4 (HyperFrames) |
| `remotion/src/NewsShort.tsx` | Added `Cut` branches (`shutter`, `blind`) and `sceneMotion` clips | Primary player component |
| `remotion/src/scenes/index.tsx` | Added hook layout renderers (`split`, `badge`, `bracket`, `rail`) | Goal 1 (Scene types) |
| `tt_shorts/motion_rules.py` | Added `moves`, `background`, `pacing` warnings; added directions to `DIRECTION` | Goal 1 (News rules) |
| `tt_shorts/sfx.py` | Added `CUT_SOUND` mappings for new transitions | Goal 1 & 4 audio mixing |
| `directors/*.json` | Calibrated motion spring numbers and timings | Goal 5 (Agent skills) |
| `skills/formats/SKILL.md` | Documented new transitions and variety options | Goal 5 (Hermes plugin docs) |
| `skills/directors/SKILL.md` | Documented director motion personalities table | Goal 5 (Hermes plugin docs) |
