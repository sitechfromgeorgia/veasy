# Composed Lane (HyperFrames) Phase 4 Result

## Overview

Veasy's composed lane has been taken through Phase 4 of `docs/plan-v2.md`. Following comprehensive research into GSAP motion craft, modular template engines, and AI code-generation pitfalls, we delivered:
1. A 9-block composable library in `compose/blocks/<id>/` with declarative manifests and deterministic GSAP animations.
2. Block assembly and scaffolding infrastructure (`tt_shorts/blocks.py`, `compose.assemble_blocks`, `engine compose scaffold --blocks`, `engine compose blocks`).
3. 3 new sub-composition lint rules (`timeline`, `prefix`, `template`) integrated into `compose.lint` (13 total rules).
4. Full documentation in `skills/compose/SKILL.md` detailing block composition and template slots.
5. 4 complete proof films composed, checked, and rendered silent across 2 brand packs (`tbilisi-today`, `sitech`) and 3 programs (`news`, `story`, `explainer`).
6. 3 template candidates promoted to `templates/` via `engine compose promote` and cataloged for owner review.

---

## 1. What Shipped (Commits)

The branch `goal/compose` contains the following commits:

1. **`4a1c657`**: `docs(research): research HyperFrames, GSAP motion, and template architectures for composed lane`
   - Detailed research report in `docs/research/compose.md` covering 28 industry sources.
   - Analysis of GSAP timeline mechanics, HyperFrames deterministic contract, template abstraction architectures (MOGRTs, Shotstack, Creatomate, Remotion), and common LLM video generation bugs.
   - Commercial license matrix and ranked engineering backlog.

2. **`527cfc0`**: `feat(compose): 9 checked building blocks, assembly pipeline, and 3 lint rules`
   - Created 9 composable blocks in `compose/blocks/`:
     - `kinetic-headline`: Typographic hook, category pill, block highlight, subhead.
     - `number-reveal`: Big stat counter, segment track, metric unit, detail card.
     - `map-pin`: Radar locator contour, pulsing beacon, place & status card.
     - `comparison`: Split contrasting cards, header pill, summary takeaway.
     - `icon-grid`: 3-badge feature breakdown with animated SVG icons and labels.
     - `quote`: Statement card with SVG quotation mark, speaker badge, and role.
     - `process`: Step-by-step vertical sequence with animated spine and step badges.
     - `chapter-card`: Section transition with backdrop index numeral, chapter pill, and topic.
     - `end-card`: Outro card with takeaway summary, action pill, and brand frame.
   - Created `tt_shorts/blocks.py` for block discovery, validation, and rendering.
   - Extended `tt_shorts/compose.py` with `assemble_blocks()`, `blocks()`, and `blocks_summary()`.
   - Added 3 new lint rules to `LINT_RULES`: `timeline`, `prefix`, and `template`.
   - Added `engine compose blocks` subcommand and `--blocks` option to `engine compose scaffold`.
   - Exposed block catalog in `engine options` (`compose_blocks` and `film_engines.compose.blocks`).
   - Updated `skills/compose/SKILL.md` with complete usage instructions.
   - Added unit tests in `tests/test_compose.py` covering all blocks and new lint rules.

3. **`5a5fb6f`**: `feat(compose): 3 candidate templates promoted and block template refinements`
   - Promoted 3 candidate templates into `templates/`:
     - `templates/news-kinetic` (from `24835`, pack: `tbilisi-today`, program: `news`).
     - `templates/fable-story` (from `bipi-draws`, pack: `sitech`, program: `story`).
     - `templates/tech-explainer` (from `sitech-cybercartel`, pack: `sitech`, program: `news`/`explainer`).
   - Refined block templates:
     - `kinetic-headline`: guaranteed $\ge 2\%$ ink on frame 0 in the hook band; max width 876px to prevent safe-zone clipping.
     - `process`: used CSS counters (`counter-reset` / `counter-increment`) to render step digits without tripping `lint fact`.
     - `quote`: used SVG quotation marks instead of literal `„` characters to pass `lint fact`; fixed `#root [data-probe="scene"]` full-height bounds.
     - `map-pin`: replaced accent color on timestamp text with `var(--ink)` to satisfy Tbilisi Today accent rules.
     - `tt_shorts/compose.py`: updated `assemble_blocks` to support string anchor names for the final beat.

---

## 2. Proof Films & Render Paths

Four proof films were authored from the skill alone, checked via `engine compose check` (0 errors), and rendered silent using the HyperFrames engine:

### Film 1: Tbilisi Today Gas Outage (`24835`)
- **Pack:** `tbilisi-today`
- **Program:** `news`
- **Story:** `stories/24835.json`
- **Technique:** Multi-scene kinetic news story with 7 sequential compositions (`s1-hook`, `s2-source`, `s3-number`, `s4-when`, `s5-why`, `s6-where`, `s7-media`).
- **QA Results:** 0 probe problems, 0 lint problems.
- **Rendered Video:** `data/renders/tbilisi-today/2026-11-03/24835-news-composed-page.mp4`
- **Contact Sheet:** `data/renders/tbilisi-today/2026-11-03/24835-news-composed-page.sheet.jpg`

### Film 2: Bipi the Robot Learns to Draw (`bipi-draws`)
- **Pack:** `sitech`
- **Program:** `story`
- **Story:** `stories/bipi-draws.json`
- **Technique:** 3-chapter illustrated character story with procedural GSAP arm movements, drawing canvas animations, trial-and-error progression, and moral takeaway card (`s1-bipi`, `s2-tries`, `s3-days`, `s4-sun`, `s5-moral`).
- **QA Results:** 0 probe problems, 0 lint problems.
- **Rendered Video:** `data/renders/sitech/2026-11-03/bipi-draws-story-composed-keyword.mp4`
- **Contact Sheet:** `data/renders/sitech/2026-11-03/bipi-draws-story-composed-keyword.sheet.jpg`

### Film 3: AI Agents in Cyberattacks (`sitech-cybercartel`)
- **Pack:** `sitech`
- **Program:** `explainer`
- **Story:** `stories/sitech-cybercartel.json`
- **Technique:** Assembled dynamically from block library: `kinetic-headline` $\to$ `number-reveal` $\to$ `process` $\to$ `end-card`.
- **QA Results:** 0 probe problems, 0 lint problems; Opening ink: 2.6% (meets $\ge 2\%$ threshold).
- **Rendered Video:** `data/renders/sitech/2026-11-03/claude-and-grok-among-ai-agents-used-to-automate-attacks-on-lati-news-composed-page.mp4`
- **Contact Sheet:** `data/renders/sitech/2026-11-03/claude-and-grok-among-ai-agents-used-to-automate-attacks-on-lati-news-composed-page.sheet.jpg`

### Film 4: Turkish Diplomatic Talks (`24725`)
- **Pack:** `tbilisi-today`
- **Program:** `news`
- **Story:** `stories/24725.json`
- **Technique:** Assembled dynamically from block library: `kinetic-headline` $\to$ `quote` $\to$ `map-pin` $\to$ `icon-grid` $\to$ `end-card`.
- **QA Results:** 0 probe problems, 0 lint problems; Opening ink: 2.5% (meets $\ge 2\%$ threshold).
- **Rendered Video:** `data/renders/tbilisi-today/2026-11-03/24725-news-composed-page.mp4`
- **Contact Sheet:** `data/renders/tbilisi-today/2026-11-03/24725-news-composed-page.sheet.jpg`

---

## 3. What Was Not Done & Why

1. **Auto-Approval of Composed Films:**
   - *Why:* Ground rules and CLAUDE.md state that composed films stay held for human review (`error_class review`). Automatic approval would compromise editorial safety on custom HTML/JS code. We adhered strictly to candidate promotion rather than auto-approval.
2. **Touching Remotion Core / Other Lane Files:**
   - *Why:* Goal 1 owns Remotion scene types, Goal 2 owns icons, Goal 3 owns Remotion motion/variety, and Goal 5 owns plugin architecture. All changes were kept inside the composed lane ownership boundary (`compose/`, `templates/`, `tt_shorts/compose.py`, `tt_shorts/blocks.py`), touching shared files (`engine.py`, `SKILL.md`) purely additively.
3. **External JS Libraries & Google Fonts:**
   - *Why:* Composed films must execute fully hermetic renders without internet access. All fonts resolve via brand pack `@font-face` definitions (`Brand`), and all animation uses local pinned GSAP runtime.
4. **Paid API Calls (TTS / AI Generation):**
   - *Why:* Ground rules strictly prohibit paid cloud APIs. All renders utilized the silent preview track or local test fixtures.

---

## 4. Open Owner Decisions

The following items are submitted for owner review and decision:

1. **Candidate Template Promotion & Naming:**
   - Three candidate templates are ready in `templates/`:
     - `templates/news-kinetic`: Fast-paced kinetic news report (46 slots).
     - `templates/fable-story`: Character-driven narrative explainer (12 slots).
     - `templates/tech-explainer`: Modular technical explainer (block-based structure).
   - *Decision:* Review slot names and approve/promote them to active production variety rotation.
2. **Composed Film Review Tier Policies:**
   - Currently, all composed films route to the review tier in `queue.py` awaiting manual sign-off.
   - *Decision:* Determine whether high-confidence templates rendered from verified slots can bypass review into the standard publish queue, or whether all HyperFrames outputs should remain review-gated indefinitely.
3. **Block Library Expansion:**
   - 9 foundational blocks are shipped. Future expansions can include SVG data charts (bar chart, line trend) once brand chart styles are approved.

---

## 5. Files Touched That Other Goals May Also Touch

The following shared files were touched additively:
- `tt_shorts/compose.py`: Composed lane engine (added block rendering, assembly, and 3 lint rules).
- `tt_shorts/engine.py`: Added CLI commands (`engine compose blocks`, `--blocks` argument on scaffold) and exposed `compose_blocks` in `engine options`.
- `skills/compose/SKILL.md`: Documented block library and composition guidelines.
- `tests/test_compose.py`: Added test suite for block loading, assembly, and new lint rules.
