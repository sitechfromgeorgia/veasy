# Research: Composed Video Lane, Block Systems, and Template Pipelines

**Document:** `docs/research/compose.md`  
**Author:** Veasy Composed Lane Agent (Goal 4 / Phase 4 of `docs/plan-v2.md`)  
**Scope:** HyperFrames, HTML/CSS/GSAP motion craft, programmatic template systems, AI agent video composition, and quality guardrails for Veasy.

---

## 1. What Was Studied & What Each Teaches Veasy

We studied 28 concrete technical sources across five domains: HyperFrames architecture and runtime skills, HTML/CSS/GSAP motion craft, programmatic video template architectures, AI agent video synthesis pitfalls and verification methods, and Veasy's existing composed lane infrastructure.

### A. HyperFrames Architecture & Runtime Skills

1. **HyperFrames Core Specification (`heygen-com/hyperframes`, Apache-2.0)**  
   *Source:* `C:\Users\Louie\.gemini\config\plugins\openmontage-studio-plugin\skills\hyperframes-core\SKILL.md`  
   *What it teaches Veasy:* HyperFrames treats HTML as video by evaluating `data-*` attributes (`data-start`, `data-duration`, `data-track-index`, `data-composition-id`). Sub-compositions must be wrapped in `<template>`; the runtime only clones the contents of `<template>` and discards outer tags. The host slot's `data-composition-id` must strictly match the inner template's ID and `window.__timelines["<id>"]`. Sized root boxes are mandatory; un-sized flex containers collapse silently.
2. **HyperFrames Animation Adapter Contract (`hyperframes-animation`)**  
   *Source:* `C:\Users\Louie\.gemini\config\plugins\openmontage-studio-plugin\skills\hyperframes-animation\SKILL.md`  
   *What it teaches Veasy:* GSAP 3.15.0 is the native deterministic runtime. HyperFrames enforces a strict animatable property allowlist (`transform` via `x`, `y`, `scale`, `rotation`, and `opacity`, `backgroundColor`, `borderRadius`). Layout properties (`top`, `left`, `width`, `height`, `margin`) are banned because they trigger CPU layout recalculation and parallel frame desynchronization. Crucially, coordinate constants must be computed once at setup, never read dynamically via `getBoundingClientRect()` during animation.
3. **HyperFrames Registry & Component Quality Bar (`hyperframes-registry`)**  
   *Source:* `C:\Users\Louie\.gemini\config\plugins\hyperframes-video-plugin\skills\hyperframes-registry\SKILL.md`  
   *What it teaches Veasy:* Blocks are self-contained compositions; components are inlined snippets. In `references/component-quality-bar.md`, fatal defects (F1: does not implement description, F2: duplicate fingerprint, F3: blank frames, F5: un-seekable accumulator) and fixable defects (X1: missing `__timelines` registration) establish our standard: every block in Veasy must be deterministic, seekable, and independently verifiable.
4. **HyperFrames Determinism Rules (`references/determinism-rules.md`)**  
   *Source:* HyperFrames Core Specification, Section on Determinism  
   *What it teaches Veasy:* Real-time clocks (`Date.now()`, `performance.now()`), unseeded `Math.random()`, and infinite loops (`repeat: -1`) cause non-deterministic renders where frame N cannot be re-rendered identically. Veasy requires bitwise frame determinism on fixed render settings.
5. **HyperFrames CLI & Headless Render Contract (`hyperframes-cli`)**  
   *Source:* `C:\Users\Louie\.gemini\config\plugins\hyperframes-video-plugin\skills\hyperframes-cli\SKILL.md`  
   *What it teaches Veasy:* `hyperframes render` uses a headless Chromium runner. Pinned settings (`--workers 4`, `--no-browser-gpu`, `--quality looks`, `--strict`, `--fps 30`) ensure identical output across Linux server and Windows workstations. Network fetching at render time must be completely blocked.
6. **HyperFrames Specialized Blocks (`canopy-part-title`, `code-slice-hero`, `cuboid-carousel`)**  
   *Source:* HyperFrames Registry Skills in Plugin Catalog  
   *What it teaches Veasy:* Complex motion is achieved by composing 2–4 atomic rules (e.g., kinetic headline reveal + depth wipe + background drift) rather than giant monolithic scripts. Blocks should expose clean variable parameters (`data-var-text`, data attributes) rather than hardcoded DOM elements.

### B. HTML/CSS/GSAP Motion Craft

7. **GSAP Core & Standard "No Charge" License (GreenSock / Webflow 2026)**  
   *Source:* [GSAP Standard License](https://gsap.com/community/standard-license/) & Webflow 2026 Terms  
   *What it teaches Veasy:* Under Webflow stewardship, GSAP's Standard License is free for commercial projects, including all advanced plugins (SplitText, MorphSVG, DrawSVG, ScrollTrigger, InertiaPlugin). Commercial video generation and client rendering are fully permitted without royalties. Restrictions only apply to building competing no-code visual website builders.
8. **GSAP Timeline Sequencing & Position Parameters (`gsap-timeline`)**  
   *Source:* `C:\Users\Louie\.gemini\config\plugins\openmontage-studio-plugin\skills\gsap-timeline\SKILL.md`  
   *What it teaches Veasy:* Using `"<"` (align with previous tween start), `">"` (align with previous tween end), `"<0.2"` (stagger after start), and `"+=0.3"` relative offsets ensures animations stay synchronized even if an earlier tween's duration is adjusted. Chaining with `delay` causes drift and is banned.
9. **GSAP Compositor Performance (`gsap-performance`)**  
   *Source:* `C:\Users\Louie\.gemini\config\plugins\openmontage-studio-plugin\skills\gsap-performance\SKILL.md`  
   *What it teaches Veasy:* Staggering elements (`stagger: 0.08`) is more performant than generating separate tweens. Utilizing `will-change: transform` promotes DOM layers to GPU compositing planes, eliminating paint thrashing.
10. **Kinetic Typography Craft & Stagger Techniques (CodePen Collections)**  
    *Source:* CodePen Kinetic Typography Archives & Codrops Motion Studies  
    *What it teaches Veasy:* Impactful titles require word-by-word or character-by-character reveals using CSS overflow clipping (`overflow: hidden` on a wrapper line, tweening `y: "100%"` to `y: "0%"` with `expo.out` or `back.out(1.4)`). Stepped motion on twos creates tactile, documentary-style authority.
11. **Awwwards Kinetic Web Showcases (Editorial & Brutalist Typography)**  
    *Source:* Awwwards Site of the Day Motion Analysis (2025–2026)  
    *What it teaches Veasy:* High-end editorial looks avoid bouncy consumer easing; they rely on asymmetric typography, clean grid rules, high-contrast monochrome surfaces with a single accent dot, and subtle background grid translations.
12. **CSS View & Scroll Timelines (W3C CSS Scroll-driven Animations Level 1)**  
    *Source:* [W3C Working Draft](https://www.w3.org/TR/scroll-animations-1/)  
    *What it teaches Veasy:* Mapping animation progress to discrete timeline anchors (`@keyframes` progress interpolation) inspires how Veasy maps voiceover words into beat timestamps (`VEASY.at(beat, host)`).
13. **SVG Stroke Drawing Craft (Lucide & Path Animation)**  
    *Source:* W3C SVG 2 & WebKit SVG Stroke Dash Optimization  
    *What it teaches Veasy:* Icon stroke drawing using `stroke-dasharray` and `stroke-dashoffset` set to path length creates procedural line-art reveals without heavy external animation bundles.

### C. Programmatic Video Template Systems

14. **Remotion Parameterized Compositions (`remotion-dev/remotion`)**  
    *Source:* [Remotion Docs](https://www.remotion.dev/docs/) & `remotion-best-practices`  
    *What it teaches Veasy:* Remotion structures templates via Zod schemas (`Composition` schema prop) and `defaultProps`. Veasy's HyperFrames lane mirrors this by declaring variables on `<html>` and generating `facts.json` and `manifest.json`.
15. **Revideo Programmatic Video Architecture (`revideo-dev/revideo`)**  
    *Source:* [Revideo Open Source Engine](https://github.com/redotvideo/revideo) (MIT)  
    *What it teaches Veasy:* Programmatic video engines require strict decoupling between timing data (audio word alignment) and visual scene graphs. Revideo separates audio threads from visual canvases.
16. **Motion Canvas Procedural Generator Model (`motion-canvas`)**  
    *Source:* [Motion Canvas Architecture](https://motioncanvas.net/) (MIT)  
    *What it teaches Veasy:* Uses generator functions `yield* all(...)` for deterministic scene progression. Proves that state changes must be pure functions of time.
17. **Editly Declarative Video Editing Model (`mifi/editly`)**  
    *Source:* [Editly Repository](https://github.com/mifi/editly) (MIT)  
    *What it teaches Veasy:* Demonstrates a clean JSON timeline specification with layers (video, image, canvas text, subtitles) and declarative transitions. Demonstrates how a simple manifest can specify dynamic video assembly.
18. **Creatomate JSON Template & Modification Architecture**  
    *Source:* [Creatomate API Reference](https://creatomate.com/docs/api/rest/renders/post)  
    *What it teaches Veasy:* Creatomate exposes templates where external requests supply `modifications: {"Element-Name.property": "value"}`. Veasy adopts this exact pattern for `slots.json` (`"slot-id": "value"` or `"=fact-id"`).
19. **Shotstack Cloud Media Architecture**  
    *Source:* [Shotstack API Specification](https://shotstack.io/docs/guide/architecting-an-application/timeline/)  
    *What it teaches Veasy:* The `Timeline -> Tracks -> Clips -> Assets` hierarchy models video cleanly. Clips specify `start` and `length`, rendered top-down. Veasy's locked chrome operates as the topmost track (track 5 and 6), ensuring branding and captions can never be obscured by scene clips.
20. **After Effects MOGRTs & Essential Graphics Panel**  
    *Source:* Adobe Motion Graphics Template Architecture & Essential Graphics Specification  
    *What it teaches Veasy:* Designers author master templates and drag specific properties into an "Essential Properties" panel (Source Text, Colors, Sliders, Dropdowns, Media replacement). The template consumer can *only* edit exposed slots; all choreography, easing, and layout math are immutable. Veasy's `promote` workflow follows this exact philosophy.
21. **Canva & CapCut Template Guardrails**  
    *Source:* Canva / CapCut Developer APIs & Template Design Guidelines  
    *What it teaches Veasy:* Consumer video platforms prevent template breakage by locking container bounding boxes, auto-wrapping text, and providing strict character length caps.

### D. AI Agent Video Composition & Quality Gates

22. **Typography & Font Loading Race Conditions in Headless Chromium**  
    *Source:* Chromium Rendering Engine Font Metrics & WebFont Loader Best Practices  
    *What it teaches Veasy:* If a headless browser lays out a frame before local WOFF2 fonts finish decoding, fallback system fonts (e.g., Arial) are measured, producing erroneous word wraps and clipped boxes. Veasy's probe enforces `document.fonts.ready` synchronization and checks every glyph against the WOFF2 `cmap`.
23. **Temporal Drift & Beat Synchronization in LLM Generation**  
    *Source:* Analysis of automated video synthesis failures (AI Slop & YouTube Inauthentic Content 2025 Crackdown)  
    *What it teaches Veasy:* LLMs instructed to "animate for 3 seconds" inevitably suffer cumulative timing drift when audio speeds vary. Veasy solves this by anchoring scenes to narration words via `speech.anchor` and `beats.json`, computing exact seconds in Python before the browser opens.
24. **DOM Layout Probing & Automated Bounding Box Guards**  
    *Source:* Veasy Layout Probe (`compose/probe.mjs`) & Chrome DevTools Protocol DOM APIs  
    *What it teaches Veasy:* Automated layout checking requires reading live computed geometry:
    - Safe zones: scene text between $y=248$ and $y=1380$; captions above $y=1552$.
    - Platform rails: below $y=1100$, no text right of $x=940$.
    - Overflow: `scrollWidth > clientWidth` or `scrollHeight > clientHeight` indicates clipped copy.
    - Type ramp: no body text under $24\text{ px}$ ($40\text{ px}$ in captions).
25. **Color Contrast & Theme Token Strictness**  
    *Source:* WCAG 2.2 APCA / 4.5:1 Contrast Algorithms & DTCG Design Token Standards  
    *What it teaches Veasy:* AI agents often inject hardcoded hex values (`#fff`, `#000`) that break light/dark theme toggles. Veasy bans all literal colors in scene code and verifies WCAG contrast at runtime.

### E. Veasy Existing Composed Lane Infrastructure

26. **Veasy Compose Engine (`tt_shorts/compose.py`)**  
    *Source:* Veasy Codebase (`tt_shorts/compose.py`, `tools/compose_scaffold.py`, `tools/compose_probe.py`)  
    *What it teaches Veasy:* Core pipeline (`scaffold`, `check`, `render`, `promote`, `templates`). Facts are extracted from the story and bound via `data-var-text`. The locked chrome (v2) and captions are versioned, hashed, and protected against edits.
27. **Veasy Layout Probe (`compose/probe.mjs`)**  
    *Source:* Veasy Codebase (`compose/probe.mjs`)  
    *What it teaches Veasy:* Samples DOM at settled frames ($t + 0.7\text{ s}$ or just before next beat), collects text nodes, bounds, colors, and fonts, reporting layout problems as structured JSON.
28. **Veasy Program & Review Tiers (`tt_shorts/programs.py`, `tt_shorts/queue.py`, `docs/plan-v2.md`)**  
    *Source:* Veasy Codebase  
    *What it teaches Veasy:* Composed films are held for human review (`error_class review`) unless program/format allows `review: until:<n>`. Rules check claims against sources for news/law/explainer, or character integrity for story/fiction (rule S1).

---

## 2. Commercial License Table

All software, assets, and libraries used in Veasy's composed lane must be verified for commercial safety. No GPL or AGPL software is permitted inside Veasy.

| Technology / Asset | Stated License | Commercial Use Permitted? | Restrictions / Conditions | Veasy Implementation Rule |
| :--- | :--- | :--- | :--- | :--- |
| **HyperFrames** (`0.9.8`) | Apache-2.0 | **Yes** | Notice preservation, no patent infringement | Pinned in `compose/package.json`. Run only via `compose.hyperframes()` with telemetry and auto-updates disabled. |
| **GSAP** (`3.15.0`) | Standard "No Charge" (Webflow) | **Yes** | Free for commercial projects & client work; no visual no-code builders | Bundled with HyperFrames package. Copied locally to `assets/vendor/gsap.min.js`; no CDN links permitted. |
| **Lucide Icons** | ISC | **Yes** | Copyright notice required | Copied from `assets/icons/lucide.json`; LICENSE file maintained beside it. |
| **FiraGO Fonts** | SIL Open Font License (OFL 1.1) | **Yes** | Cannot be sold alone; reserved font name | Packaged in `brands/_ka/fonts/` as local `.woff2` files; zero external network requests. |
| **Remotion** | Company-size conditional (Free $\le 3$ people) | **Yes** (Current team size) | Free for teams up to 3 people; paid license needed if team expands | Lane A only; HyperFrames lane does not depend on Remotion runtime. |
| **Openverse / Wikimedia Commons** | CC0, Public Domain, CC BY, CC BY-SA | **Yes** | Attribution required for CC BY / CC BY-SA; no trademark/rights violations | Processed through `tt_shorts/assets.py` ledger; attribution rendered in footer. |
| **Editly** | MIT | **Yes** | Attribution in source | Conceptual reference only; no vendored code. |
| **Motion Canvas / Revideo** | MIT | **Yes** | Standard MIT terms | Conceptual reference only; no vendored code. |
| **OpenMontage** | AGPL-3.0 | **NO (Copying banned)** | Copyleft viral clause | **Strictly prohibited from codebase.** Studied for ideas only. Zero code copied. |

---

## 3. Ranked Backlog: Value & Effort

We prioritize top-down implementation in complete, test-driven increments:

| Rank | Backlog Item | Value | Effort | Acceptance Gate |
| :---: | :--- | :---: | :---: | :--- |
| **1** | **Composable Scene Block Library** (`compose/blocks/<id>/`)<br>• `kinetic-headline`<br>• `number-reveal`<br>• `map-pin`<br>• `comparison`<br>• `icon-grid`<br>• `quote`<br>• `process`<br>• `chapter-card`<br>• `end-card` | **Critical** | **M** | 9 reusable blocks in `compose/blocks/`. Each block adheres to safe zone, theme tokens, bound facts, and deterministic GSAP timeline. Passes `compose check` and layout probe. |
| **2** | **Block Integration into `compose scaffold` & `engine options`** | **High** | **S** | `scaffold --blocks ...` assembles chosen blocks into `index.html` and `beats.json`. `engine options` lists all blocks with metadata. `veasy:compose` skill documented. |
| **3** | **Compose Lint Guardrails Expansion** | **High** | **S** | New lint rules for pitfall edge cases: block ID prefix collisions, unbound variable text in blocks, invalid track indices, and malformed tags. Unit test per rule in `tests/test_compose.py`. |
| **4** | **Template Pipeline & Variety Rotation (Phase 4)** | **High** | **M** | `compose promote` converts approved films into `templates/<id>/` with slots. Variety rotation integrates templates into `variety.choose` / `pick_template`. Review held guardrails enforced. |
| **5** | **Proof Films Across Brands & Programs** | **Critical** | **M** | 4 composed films rendered and checked:<br>1. News in `tbilisi-today` (`24835`)<br>2. Explainer in `sitech` (`energy-grid` or `tech-explainer`)<br>3. Story/Fable in `sitech` (`bipi-draws`)<br>4. Explainer/Story in `tbilisi-today` (`tbilisi-heritage`)<br>Stills verified via layout probe. |

---

## 4. Owner Decisions

The following items are policy decisions reserved for the project owner:

1. **Brand Theme Approvals:**  
   `tbilisi-today` currently defaults to its dark brand palette (v1.2). A light theme exists with `"allowed": false` pending owner approval. Composed films for `tbilisi-today` will render in the official dark theme unless explicitly instructed.
2. **Template Auto-Promotion & Review Thresholds:**  
   Currently, all composed films end in `held` status (`error_class review`) in `tt_shorts/queue.py`. The threshold for switching to autonomous publishing (`review: until:<n>`) is set by format/program configuration, defaulting to `always` (human review required).
3. **Third-Party AI Image Models & Media APIs:**  
   Paid external generation tools (HeyGen API, Midjourney, Kling, ElevenLabs paid TTS) remain strictly disabled. All media must flow through Veasy's local assets ledger (`assets.py`) and edge/Gemini free preview paths.
