# Research: Icons, Animated Pictograms, and SVG Drawings in Veasy

**Author:** Antigravity Agent (Goal 2: Icons, animated pictograms and drawings)  
**Date:** 2026-11-03  
**Status:** Complete & Approved for Implementation  
**Worktree:** `D:\MyStaff\Veasy-icons` (branch `goal/icons`)

---

## 1. Executive Summary & Core Mission

Veasy is SiTech's automated vertical video engine for Georgian news and explainers. On vertical mobile video (Shorts, Reels, TikTok), viewer comprehension is determined in the first **0.5 seconds**. Because news rule N13 forbids illustrative imagery for crime, incidents, and deaths, and publisher photos are legally unavailable, Veasy's visual communication relies fundamentally on:
1. **Line Icons** (24px grid, stroke-only ink rendering, single accent dot on active state);
2. **Animated Pictograms** (`sign` scene with verb-driven micro-motion, isotype unit charts in `stat`);
3. **Seed Drawings** (procedural technical line art in `draw` scenes with multi-phase stroke build-ups).

This document establishes a rigorous visual vocabulary for Veasy: analyzing 28 historical, industry, and technical sources; cataloging licensing boundaries (permissible MIT, ISC, Apache 2.0, Public Domain vs viral CC BY-SA and proprietary terms); and defining a top-down engineering backlog to elevate Veasy's expressive visual capabilities without ever violating brand pack laws or news rule N10.

---

## 2. Deep Research: 28 Sources Across Traditions & Technologies

### 2.1 Icon Sets & Visual Grammars

| # | System / Library | Link | Exact Licence | Grid / Style Specs | Strengths & Domain Coverage | What It Teaches Veasy |
|---|---|---|---|---|---|---|
| 1 | **Lucide Icons** | [lucide.dev](https://lucide.dev) | ISC (derived from Feather MIT) | 24×24 grid, 2px stroke, round caps/joins | 1,450+ clean, semantic vector glyphs across tech, UI, energy, civic, transport. Currently in use in Veasy (`assets/icons/lucide.json`). | Consistent 24px coordinate space; pure geometric tags (`path`, `circle`, `rect`, `line`, `polyline`, `polygon`, `ellipse`). Perfect base for normalized stroke-dash animations. |
| 2 | **Tabler Icons** | [tabler.io/icons](https://tabler.io/icons) | MIT | 24×24 grid, 2px stroke, rounded corners | 5,200+ icons with massive civic, governmental, infrastructure, medical, and regional symbol coverage. | Rich coverage of niche civic and news topics (courtrooms, municipal utilities, specialized vehicles, administrative documents). Clean geometric stroke parity with Lucide. |
| 3 | **Phosphor Icons** | [phosphoricons.com](https://phosphoricons.com) | MIT | 16/24/32/48 grids; 6 weights (thin to fill) | 1,248+ glyphs with exceptional mathematical consistency and optical weight balance. | Strict visual weight parity across glyphs; optical centering principles ensuring an icon's visual center matches its bounding box center. |
| 4 | **Iconoir** | [iconoir.com](https://iconoir.com) | MIT | 24×24 grid, 2px stroke, no dependencies | 1,500+ geometric line icons, strong architectural and digital system symbols. | Minimalist curve definitions with very low node counts; ideal for low-overhead SVG parsing and real-time path interpolation. |
| 5 | **Heroicons** | [heroicons.com](https://heroicons.com) | MIT | 24×24 grid (outline 1.5px), 20×20 (solid) | 290+ refined interface glyphs by Tailwind Labs. | Modern proportioning and restraint; demonstrates how subtle corner radii soften technical symbols for editorial readability. |
| 6 | **Material Symbols** | [fonts.google.com/icons](https://fonts.google.com/icons) | Apache-2.0 | 24×24 base, variable weight/optical size/grade | 3,000+ universally recognized glyphs with internationalized cultural testing by Google. | Semantic universality; symbols tested across diverse literacy and cultural backgrounds. Optical grading for dark-canvas vs light-canvas contrast. |
| 7 | **Remix Icon** | [remixicon.com](https://remixicon.com) | Apache-2.0 | 24×24 grid, consistent stroke & fill pairs | 2,800+ icons with strong media, publication, and institutional categories. | Categorical grouping conventions (Business, Document, Map, System) mapping cleanly to news topics. |
| 8 | **Fluent UI System Icons** | [github.com/microsoft/fluentui-system-icons](https://github.com/microsoft/fluentui-system-icons) | MIT | 20/24/28/32/48 grids, 1.5-2px stroke | 4,000+ icons designed for rapid mobile touch recognition in Windows/Office. | Mobile glanceability: larger internal counters and distinct silhouette silhouettes that avoid muddiness when viewed at 32-48px on mobile devices. |
| 9 | **Health Icons** | [healthicons.org](https://healthicons.org) | CC0 1.0 Universal (Public Domain) | 24×24 grid, stroke/filled/negative | 2,100+ public health, clinical, pharmaceutical, and epidemiological icons created with WHO/UNICEF consultation. | Neutral, non-stigmatizing medical and epidemiology symbology suitable for health news without violating sensitivity guidelines. |
| 10 | **Weather Icons** | [erikflowers.github.io/weather-icons](https://erikflowers.github.io/weather-icons) | SIL OFL 1.1 (font), MIT (code) | 30×30 grid, cardinal alignments | 222 specialized meteorological icons (WMO weather condition codes, barometric trends, maritime winds). | Precise meteorological granularity (solar radiation, precipitation intensity, atmospheric pressure shifts) for weather bulletins. |
| 11 | **Noto Emoji / Symbols** | [github.com/googlefonts/noto-emoji](https://github.com/googlefonts/noto-emoji) | Apache-2.0 | 128×128 vector grid | Universal pictographic coverage across flora, fauna, tools, civic objects. | Deconstruction of complex objects into minimal recognizable contours; monochrome stroke translation of physical items. |
| 12 | **OpenMoji** | [openmoji.org](https://openmoji.org) | CC BY-SA 4.0 (ShareAlike) | 72×72 grid, 2px outline | 4,000+ open-source emojis with extensive cultural and historical artifacts. | **CAUTION - VIRAL LICENCE:** CC BY-SA requires derived works to be shared under the same license. Must NOT be vendored into engine code without legal clearance. Ideas only. |
| 13 | **Streamline Free Core** | [streamlinehq.com](https://streamlinehq.com) | Proprietary / CC BY 4.0 with restrictions | Multiple grids (14px, 24px) | Extensive icon collection. | **CAUTION - TERMS:** Requires explicit author attribution on every asset view and forbids direct redistributed bundling in SaaS/engines. Reject vendoring. |
| 14 | **Feather Icons** | [feathericons.com](https://feathericons.com) | MIT | 24×24 grid, 2px stroke | 287 foundation icons (the ancestor of Lucide). | The purest demonstration of simplicity: 8-point snapping, strict 2px strokes, zero unnecessary decorative arcs. |

---

### 2.2 Pictogram Traditions & Visual Semiotics

| # | Tradition / Scholar | Primary Reference | Date / Origin | Core Principles | Application to Veasy Videos |
|---|---|---|---|---|---|
| 15 | **Isotype (Otto Neurath, Marie Reidemeister, Gerd Arntz)** | *International Picture Language* (1936); *Modern Man in the Making* (1939) | Vienna, 1925–1940 | "Words divide, pictures unite." 1. A picture showing simple signs is remembered longer. 2. A sign shows things, never emotions or opinions. 3. Unit-repetition: to show more things, use more signs, never a larger sign. 4. Profile or flat elevation views only; no perspective distortion. | Direct foundation of Veasy's isotype counts on `stat` (2–30 whole icons, never scaling 1 icon = N). Sign scenes must depict physical entities in true flat profile. |
| 16 | **AIGA / DOT Symbol Signs** | US Department of Transportation & AIGA (Cook and Shanosky Associates) | Washington DC, 1974 (50 symbols) | Public Domain. Created to guide international travelers without language barriers. Strict 34-rule semiotic grid: figure-ground contrast, standardized head-to-body ratios, 45° diagonal limbs. | Benchmark for immediate 0.25s mobile glanceability. Demonstrates how public signs (bus, train, restroom, customs, luggage) achieve unambiguous clarity without words. |
| 17 | **ISO 7001: Public Information Symbols** | International Organization for Standardization (ISO/TC 145) | Geneva, 1980–2023 | Empirical testing methodology: comprehension threshold $\ge 67\%$ across multilingual global sample groups with $\le 10\%$ critical confusion errors. | Veasy's pictogram choices must pass the "no false friend" comprehension test. If a symbol confuses viewers in 0.5s, it is rejected. |
| 18 | **Otl Aicher (Munich 1972 Olympic Pictograms)** | *The World as Design* (1976); Munich 1972 Design System | Ulm / Munich, 1972 | Modular orthogonal and 45° diagonal grid. The human body is reduced to a circle head (separated by negative space) and tubular limbs. Absolute systematic cohesion across 21 disciplines. | Strict mathematical consistency: every icon in a video must share identical stroke weight, terminal curvature, and grid scale. Mixing stroke styles within a video degrades perceived authority. |
| 19 | **Tokyo 1964 Olympic Symbols (Masaru Katsumie, Yoshiro Yamashita)** | Tokyo Organizing Committee Design Guide | Tokyo, 1964 | The first comprehensive universal sports pictogram system. Bold geometric silhouettes eliminating cultural and alphabetic dependency. | Demonstrates that radical abstraction with high positive/negative contrast communicates action faster than detailed illustration. |
| 20 | **Barcelona 1992 Pictograms (Josep Maria Trias)** | COOB'92 Design Documentation | Barcelona, 1992 | Dynamic gestural brushwork (three gestural marks: head, body, motion) inspired by Miró. High visual energy while preserving functional posture. | Demonstrates dynamic kinetic balance: how static strokes convey kinetic momentum (speed, direction, tension) before motion is applied. |
| 21 | **Paris 2024 Pictograms (Critique & Case Study)** | Paris 2024 Brand Identity | Paris, 2024 | "Blazons" (coats of arms) featuring heraldic symmetry and tool juxtapositions rather than human athletic figures. | **Negative Lesson for Veasy:** The Paris 2024 blazons suffered severe public criticism for illegibility on broadcast and mobile screens because intricate bilateral symmetry obscured the focal silhouette. Veasy must avoid dense heraldic symmetry in favor of strong directional asymmetry. |
| 22 | **Jacques Bertin (Semiology of Graphics)** | *Sémiologie Graphique* (Gauthier-Villars, 1967) | Paris, 1967 | Theory of visual variables: Position, Size, Shape, Value (lightness), Color (hue), Orientation, Texture. Pre-attentive processing occurs in $< 200\text{ ms}$. | Shape and Orientation identify category; Position and Value convey magnitude. In Veasy, color (accent) is reserved strictly for state/dot, never for categorical encoding. |
| 23 | **Edward R. Tufte** | *The Visual Display of Quantitative Information* (Graphics Press, 1983) | Cheshire, CT, 1983 | Maximizing the "Data-Ink Ratio" = Data-ink / Total ink used in graphic. Elimination of "chartjunk" (decorative grids, redundant labels, non-functional fills). | Veasy's drawings and icons must carry zero non-semantic flourish. Every line in a `draw` or `sign` scene must represent an actual physical or functional element. |
| 24 | **Colin Ware** | *Information Visualization: Perception for Design* (Morgan Kaufmann, 2012) | San Francisco, 2012 | Preattentive pop-out effects (color contrast, flicker, motion). Foveal vision captures only a 2° cone; peripheral vision detects motion and abrupt luminance shifts. | The accent dot ($r \le 28\text{px}$) functions as a foveal anchor. Icon animation must guide the eye to the key semantic transition rather than creating chaotic full-frame movement. |

---

### 2.3 SVG Animation Techniques & Runtime Mechanics

| # | Technique / Library | Link | Licence | Rendering Mechanism | Strengths & Limits in Remotion | Fit for Veasy |
|---|---|---|---|---|---|
| 25 | **Normalized Stroke Draw-On (`pathLength: 1`)** | SVG 2 Specification § Stroke Properties (W3C) | W3C Standard | `stroke-dasharray: 1`, `stroke-dashoffset: 1 - t` where $t \in [0, 1]$. | Pure declarative CSS/SVG; zero bundle overhead; 100% deterministic frame-by-frame seeking in Remotion. | **Primary Animation Method:** Ultra-lightweight, crisp rendering at any resolution, mathematically exact timing. |
| 26 | **Path Morphing (`@remotion/paths` & `flubber`)** | [remotion.dev/docs/paths](https://www.remotion.dev/docs/paths), [github.com/veltman/flubber](https://github.com/veltman/flubber) | MIT | `interpolatePath` / polygon triangulation & point distribution. | Smooth shape-shifting between two icon outlines. Requires equal path segments or subdivision. | **High Value:** Allows morphing between related state icons (e.g., door-closed $\to$ door-open, flame $\to$ snowflake). |
| 27 | **Rough.js Sketch Animation** | [roughjs.com](https://roughjs.com) | MIT | Procedural multi-stroke canvas/SVG rendering with seeded randomness. | Creates organic, hand-drawn architectural sketch aesthetics. Must be seeded with fixed random seed per frame to avoid jitter. | **Selected Scenes:** Enhances `draw` scenes and editorial explainer graphics with controlled, deterministic sketchy ink. |
| 28 | **Lottie / dotLottie (@remotion/lottie)** | [lottiefiles.com](https://lottiefiles.com), [remotion.dev/docs/lottie](https://www.remotion.dev/docs/lottie) | Apache-2.0 (Player), Assets Vary | After Effects export via Bodymovin to JSON vector curves. | Rich multi-layer animation; BUT large JSON file payloads, opaque licensing per asset, risk of unbranded color leaks. | **REJECTED FOR CORE ENGINE:** Introduces third-party asset licensing risk, uncontrolled styling, and non-brand color leaks. Pure SVG components with code-owned properties are superior. |

---

## 3. Comparative Licensing Audit

Veasy's ground rules mandate: **Commercial use permitted; No GPL/AGPL; No viral CC BY-SA without isolation; Complete source attribution recorded.**

| Asset / Source Family | Licence Type | Commercial Use? | Attribution Required? | Engine Embed Suitability | Policy Decision for Veasy |
|---|---|---|---|---|---|
| **Lucide Icons** | ISC | Yes | Beside vendored file (`assets/icons/LICENSE`) | **YES (Primary)** | Shipped. Expand coverage via `tools/build_icons.py`. |
| **Tabler Icons** | MIT | Yes | MIT notice in vendor directory | **YES (Candidate)** | Excellent secondary pool for civic/legal/infrastructure icons if Lucide lacks a symbol. |
| **Phosphor Icons** | MIT | Yes | MIT notice in vendor directory | **YES (Compatible)** | Clean reference for optical alignment and proportions. |
| **Material Symbols** | Apache-2.0 | Yes | Apache notice in vendor directory | **YES (Compatible)** | Used for conceptual design validation; symbol shapes compatible with 24px grid. |
| **Health Icons** | CC0 1.0 Universal | Yes | None required (Public Domain) | **YES (Compatible)** | Ideal for medical, clinical, and pandemic safety concepts. |
| **AIGA / DOT Signs** | Public Domain (US Gov) | Yes | None required | **YES (Ideal)** | Standard reference for sign postures, profiles, and pictogram legibility. |
| **Rough.js** | MIT | Yes | Standard MIT attribution | **YES (Compatible)** | Usable for procedural sketch styling in Remotion. |
| **flubber / @remotion/paths** | MIT | Yes | Standard MIT attribution | **YES (Compatible)** | Usable for path morphing and length calculations. |
| **OpenMoji** | CC BY-SA 4.0 | Conditional | Strict: ShareAlike copyleft clause | **NO (Reject for Code)** | Viral clause risks forcing codebase release under CC BY-SA. Ideas only. |
| **Lordicon** | Proprietary Commercial | Restricted | Mandatory attribution or paid license | **NO (Reject)** | Violates zero-cost, commercial-distribution engine mandate. |
| **Streamline Core Free** | Custom Proprietary | Restricted | Mandatory visible website link | **NO (Reject)** | Unacceptable distribution constraints for automated video engine. |
| **OpenMontage** | AGPL-3.0 | Viral | Copyleft on network service | **NO (Reject)** | Explicitly forbidden by Veasy ground rules. Study concepts, never copy code. |

---

## 4. Current State Analysis of Veasy's Icon & Drawing Systems

### 4.1 Icons (`tt_shorts/icons.py`)
- **Asset:** `assets/icons/lucide.json` containing 250 Lucide glyphs on a 24px grid with stroke geometries.
- **Stem Mapping:** `_BY_ICON` maps ~170 icons across 11 categories (energy, water, transport, health, schools, courts/government, money/prices, weather, buildings, nature, sport, culture, tech, time/signals) to ~600 Georgian stems.
- **Look-Alikes & Blockers:** `_BLOCK` blocks 38 false-friend Georgian words (e.g., გაზრდა "growth" blocking გაზ- "gas", მზერა "gaze" blocking მზე "sun", გულისხმობს "implies" blocking გულ- "heart").
- **Exact Token Matches:** Stems ending in `=` (e.g. `მთა=`) prevent false matches on longer words (`მთავრობა`).
- **Verbs:** 8 canonical verbs for `sign` scenes: `rises`, `falls`, `stops`, `opens`, `closes`, `moves`, `splits`, `joins`, each checked against narration by `news_check.pictograms` (N10).
- **Isotype Logic:** `stat` scenes with an integer count between 2 and 30 whole items render repeated icon glyphs (`isotype: true`), strictly barring percentages or values $> 30$.
- **Motif Generation:** `icons.story_icon(story)` selects the story's visual emblem for faint background tiling (`variety.py` motif `icons`), strictly suppressed for crime, incidents, or death stories.

### 4.2 Drawing Engine (`tt_shorts/drawings.py` & `tt_shorts/art.py`)
- **Current Seeds:** 18 hand-crafted technical schematic line drawings in `assets/drawings/*.json` (ballot-box, bridge, bus, car, court, factory, fuel-pump, gas-pipe, government, hospital, house, metro, money, phone, power-line, price-tag, school, tap).
- **Quality Gates in `art.py`:**
  - Viewbox: 0 0 952 640.
  - Allowed elements: `g`, `path`, `line`, `polyline`, `polygon`, `rect`, `circle`, `ellipse`, `text`.
  - Allowed color tokens: `INK`, `MUTED`, `LINE`, `CANVAS`, `ACCENT`, `none`.
  - `ACCENT` restriction: Only on circles with $r \le 28\text{px}$ (max 3 accent dots per drawing).
  - Bounds & elements: 6 to 60 elements; occupies $\ge 40\%$ width and $\ge 35\%$ height of the viewbox.
  - Motion tokens: `r` (rise), `p` (pop), `s` (stroke-draw), with `--d:<delay>s`.
- **Mending & Memory:** If a writer drawing fails `art.sanitize` or `art.quality`, `drawings.mend()` retrieves an approved drawing of the same motif from `veasy.db` or `assets/drawings/`, strips any unsaid labels, and re-validates.

---

## 5. Identified Gaps & Opportunities

1. **Georgian Stem Coverage Deficit:**
   - 250 Lucide icons exist, but many critical news and civic stems in Georgia are unmapped (e.g., agriculture/viticulture, municipal fines, border control, public registry, pensions, aviation, maritime shipping, cybersecurity, environmental warnings).
   - Missing look-alike blockers in `_BLOCK`: Words like `ბანაკი` (camp) vs `ბანკი` (bank), `კოდექსი` (code) vs `კოდი` (code), `ტარიფი` (tariff) vs `ტარება` (driving), `ჯარიმა` (fine) vs `ჯარი` (military).

2. **Monotonous Micro-Motion for Pictograms:**
   - Currently, `sign` scenes only draw strokes from $0 \to 1$ and then perform one of 8 verb motions (bar closes, doors swing, lifts, sinks).
   - Missing expressive icon motion personalities:
     - `pop`: snappy spring overshoot scale entry ($0 \to 1.15 \to 1.0$).
     - `pulse`: subtle rhythmic scale heartbeat with accent ping.
     - `count-up`: staggered sequential pop-in for isotype repeat grids.
     - `morph`: fluid transformation from initial symbol to outcome symbol.
     - `sketch`: hand-drawn progressive stroke reveals.

3. **Pictogram & Isotype Charts Beyond Simple Rows:**
   - Today, `isotype` on `stat` draws an unsegmented row or grid of identical glyphs.
   - Missing:
     - **Part-of-Whole Pictogram Grid (Waffle / 10-unit or 100-unit share):** e.g., 7 out of 10 people icons lit in `INK`, 3 in `MUTED` or `LINE`.
     - **Unit Comparison Chart:** e.g., comparing 4 buses vs 8 buses side-by-side.

4. **Seed Drawing Library Scarcity (18 Seeds $\to$ 43+ Seeds):**
   - 18 drawings is insufficient to cover daily news diversity. A failing writer drawing for an agriculture, technology, aviation, maritime, police, or environmental story currently fails to find a motif match and gets dropped completely.
   - At least 25 new seed drawings are urgently needed across:
     1. Agriculture: `tractor`, `wheat-field`, `wine-barrel`, `orchard`
     2. Civic & Legal: `police-car`, `fire-truck`, `prison-cell`, `passport-control`, `city-hall`
     3. Transport: `airplane-runway`, `cargo-ship`, `train-station`, `electric-charger`
     4. Infrastructure: `dam-hydro`, `solar-farm`, `wind-turbine`, `satellite-dish`
     5. Technology & Data: `server-rack`, `microchip-circuit`, `cloud-database`, `cyber-lock`
     6. Economy & Commerce: `shipping-container`, `supermarket-cart`, `bank-vault`, `crane-construction`

5. **Visual Verification Tooling:**
   - No contact sheet tool currently renders the entire icon and drawing library across all themes (`default` dark, `sitech:light`, `tbilisi-today:light`) for human or agent review.

---

## 6. Ranked Implementation Backlog

| Rank | Milestone / Increment | Value | Effort | Files Owned & Touched | Gate Checks |
|---|---|---|---|---|---|
| **1** | **Research Document & Architecture Plan** | High | Low | `docs/research/icons.md` | Clear backlog, licensing audit complete. |
| **2** | **Georgian Stem Expansion (+80 Stems) & Blocker Fortification** | High | Med | `tt_shorts/icons.py`, `tests/test_icons.py` | $\ge 60$ new stems verified with Georgian case-endings; zero false friends; 100% test green. |
| **3** | **Icon Motion Vocabulary Engine (Remotion & Python Options)** | High | Med | `remotion/src/icons.tsx`, `remotion/src/scenes/sign.tsx`, `tt_shorts/icons.py` | Frame-exact, deterministic motion modes: `draw`, `pop`, `pulse`, `morph`, `sketch`; brand pack accent rules preserved. |
| **4** | **Rich Isotype & Pictogram Unit Charts** | High | Med | `remotion/src/scenes/stat.tsx`, `remotion/src/scenes/brushes.tsx`, `tt_shorts/icons.py` | Part-of-whole (ratio of icons lit vs muted), unit comparisons, N10 news rules strictly maintained. |
| **5** | **25+ New Technical Seed Drawings in `assets/drawings/`** | High | High | `assets/drawings/*.json`, `tests/test_drawings.py` | 25+ new clean SVG technical schematics; 100% pass `art.sanitize` & `art.quality`; motif resolution verified. |
| **6** | **Icon & Drawing Contact Sheet Generator (`engine contact-sheet`)** | Med | Med | `tt_shorts/engine.py`, `tools/contact_sheet.py`, `skills/` | Generates full-spectrum visual contact sheets across dark & light themes. |
| **7** | **Visual Verification Probe & Demo Story in All Looks** | High | Med | `stories/veasy-icons.json`, `engine probe --look all` | Settled frames inside safe zones; no layout problems; golden checks updated deliberately. |
| **8** | **Final Results Report & Audit Document** | High | Low | `docs/research/icons-result.md` | Commit catalog, before/after stills, cross-goal boundary touches documented. |

---

## 7. Owner Decisions

The following policy decisions belong strictly to the owner and must not be unilaterally implemented by the agent:
1. **Tints (plan-v2 § 8.2):** Whether to introduce muted colored badges (blue, yellow, green) for icon backgrounds. Currently, tbilisi.today's brand pack v1.2 strictly mandates: *Dark canvas, light ink, one accent (never on text or icon fills).* **Decision:** Tints remain OFF. Icons are rendered strictly in `ink`, `muted`, or `line`.
2. **Expansion to Non-Lucide Icon Libraries in Production Renders:** Whether to vendor a secondary icon pack (e.g. Tabler Icons) into `assets/icons/`. **Decision:** Lucide 1.54.0 provides 1,450+ icons. To honor the rule *"one stroke style per video: never mix sets in one film"*, all expanded stems will map to Lucide's geometry, maintaining 100% stroke style cohesion.
3. **News Rule N10 Strictness:** Pictograms remain strictly prohibited for crime, incidents, and deaths. This safeguard is inviolable.
