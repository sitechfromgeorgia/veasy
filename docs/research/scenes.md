# Research: Vertical Scene Visual Grammar & Veasy Scene Types

Written: 2026-11-03  
Author: Goal 1 Agent (`goal/scenes`)  
Workspace: `Veasy-scenes`  

This research examines how top-tier visual journalism, vertical news Shorts/Reels, explainer studios, and programmatic video frameworks turn factual data into vertical motion. It establishes the foundations for expanding Veasy's scene library (`brushes/`) with 8+ new, fully wired scene types that enable rich explainer, legal, data, and story productions within Veasy's strict brand, news, and safe zone constraints.

---

## 1. Visual Journalism & Explainer Methodologies (25+ Real Sources)

Each source was analyzed for the storytelling device it uses, how it structures factual beats, and what Veasy's engine can adopt.

### Visual Journalism Outlets & Standards

1. **Financial Times Visual Vocabulary**  
   - *Source*: [ft-interactive.github.io/visual-vocabulary](https://ft-interactive.github.io/visual-vocabulary/)  
   - *Core Concept*: Categorization of charts by analytical intent rather than software widgets: Deviation, Correlation, Ranking, Distribution, Change over Time, Magnitude, Part-to-Whole, Spatial, Flow.  
   - *Veasy Mapping*:
     - *Ranking*: Ordered leaderboard with rank indicators (`ranking`).
     - *Part-to-Whole*: Proportional partition of 100% or total resource (`budget`, `waffle`).
     - *Magnitude*: Head-to-head two-entity confrontation (`versus`), complementing proportional squares (`compare`) and zero-aligned bars (`bars`).
     - *Spatial/Flow*: Origin-to-destination transit path (`route`), building on regional focal points (`where`).
     - *Change over time / Milestone*: Temporal progress and target deadline (`countdown`, `calendar`).

2. **Reuters Graphics**  
   - *Source*: [reuters.com/graphics](https://www.reuters.com/graphics/)  
   - *Core Concept*: Stepwise explanatory card sequences. Complex industrial, geopolitical, or financial transformations are broken into single-focus scrollytelling cards where one metric or milestone is highlighted at a time.
   - *What Veasy Takes*: Single-responsibility scene cards; each scene presents one clear relationship (e.g. A vs B, or Step 1 to N) rather than dense multi-layered graphics.

3. **New York Times Visual Journalism & Graphics**  
   - *Source*: [nytimes.com/section/multimedia](https://www.nytimes.com/section/multimedia)  
   - *Core Concept*: "What changes for you" service journalism cards and paired comparisons. Clear typography cards that distill regulatory, transit, or fiscal shifts into: (1) Who is affected, (2) Exactly what alters, and (3) Effective date.
   - *What Veasy Takes*: An explicit `impact` scene type ("რა იცვლება") giving municipal, fiscal, and regulatory news a standardized service format.

4. **BBC Visual Journalism & BBC Data Unit**  
   - *Source*: [bbc.com/news/explainers](https://www.bbc.com/news/explainers)  
   - *Core Concept*: "At a glance" key-date summaries and condition checklists. High-contrast cards answering: "What are the rules?", "Who qualifies?", "Key dates on the calendar".
   - *What Veasy Takes*: A `checklist` scene type for verifying legal/factual prerequisites, and a `calendar` scene type for scheduled hearings, sessions, and deadlines.

5. **Bloomberg Graphics & QuickTake**  
   - *Source*: [bloomberg.com/graphics](https://www.bloomberg.com/graphics/)  
   - *Core Concept*: Macro budget allocations and segmented financial flows. Clean horizontal proportional bars and grouped metric breakdowns where categories sum to a whole.
   - *What Veasy Takes*: A `budget` scene type that models categorical resource distributions (state budget, energy grid mix, bilateral aid).

6. **The Economist Short Video & Daily Charts**  
   - *Source*: [economist.com/graphic-detail](https://www.economist.com/graphic-detail)  
   - *Core Concept*: High-contrast typographical hierarchy and dual-metric face-offs ("versus"). Two competing entities (countries, currencies, candidates, policy packages) contrasted side-by-side with clear comparative indicators.
   - *What Veasy Takes*: The `versus` scene type for direct head-to-head factual confrontations without subjective editorializing.

7. **Vox Explainers (Vox Video)**  
   - *Source*: [vox.com/videos](https://www.vox.com/videos)  
   - *Core Concept*: Glossary definition cards and highlighted document excerpts. When explaining complex legal or technological topics, a definition card pauses to anchor the core term with pronunciation/category, primary meaning, and real-world application.
   - *What Veasy Takes*: The `glossary` scene type ("განმარტება"), essential for the `law` and `explainer` programs.

8. **Kurzgesagt – In a Nutshell**  
   - *Source*: [youtube.com/@kurzgesagt](https://www.youtube.com/@kurzgesagt)  
   - *Core Concept*: Proportional unit arrays, visual scales, and progressive milestone reveals. Using discrete graphical units and clean geometric rhythm to communicate vast disparities in scale.
   - *What Veasy Takes*: Strict unit consistency in visual comparisons and timed stagger reveals synchronized to spoken phrases.

9. **AJ+ (Al Jazeera Digital)**  
   - *Source*: [ajplus.net](https://www.ajplus.net/)  
   - *Core Concept*: Fast-paced mobile-first vertical fact cards. Large numeric callouts positioned in the upper half of the screen with punchy kicker tags and clear source attributions.
   - *What Veasy Takes*: Safe zone positioning (y: 248–1380) and immediate frame-0 readability so the opening hook never starts with blank canvas.

10. **NowThis News**  
    - *Source*: [nowthisnews.com](https://nowthisnews.com/)  
    - *Core Concept*: Milestone countdown cards and urgency tickers ("Days until the vote", "Hours remaining").
    - *What Veasy Takes*: A `countdown` scene type displaying remaining time (days, hours) to a fixed factual deadline.

11. **Axios ("Smart Brevity")**  
    - *Source*: [axios.com](https://www.axios.com/)  
    - *Core Concept*: Structural card modules: "Why it matters", "By the numbers", "Between the lines", "What's next". Standardized cognitive entry points reduce reader fatigue.
    - *What Veasy Takes*: Clear categorical slots in brush definitions (`slots`) enforcing concise text lengths and preventing paragraph sprawl.

12. **The Pudding (Visual Essays)**  
    - *Source*: [pudding.cool](https://pudding.cool/)  
    - *Core Concept*: Leaderboard rankings and positional shifts. Animated ranks with positional indicators (1st, 2nd, 3rd) and differential values.
    - *What Veasy Takes*: The `ranking` brush featuring ordered badges, item labels, and metric counts.

13. **Datawrapper Chart System**  
    - *Source*: [datawrapper.de](https://www.datawrapper.de/)  
    - *Core Concept*: Accessible, responsive mobile charts: split bars, dot plots, ranked tables, and election donuts. Strict palette discipline where colors encode categories only when necessary and text contrast is never compromised.
    - *What Veasy Takes*: Linear proportional scaling from baseline zero, absence of decorative gradients or drop shadows, adherence to brand token colors.

14. **Flourish Studio**  
    - *Source*: [flourish.studio](https://flourish.studio/)  
    - *Core Concept*: Interactive race charts, multi-category waffles, and parliament grids. Transitioning elements along defined paths to preserve spatial continuity.
    - *What Veasy Takes*: Deterministic frame interpolation where items enter in timed sequence without layout thrashing.

15. **Isotype System (Otto Neurath & Gerd Arntz)**  
    - *Source*: [gerdarntz.org/isotype](https://www.gerdarntz.org/isotype)  
    - *Core Concept*: The International System of Typographic Picture Education. Quantitative information represented through repeated standardized pictograms where "one sign represents a fixed amount", never scaling signs disproportionately.
    - *What Veasy Takes*: Respect for true numerical scale; discrete counters and unit grids (`share`, `stat.isotype`).

### Vertical News Shorts & Mobile Video Leaders

16. **Deutsche Welle (DW) Shorts & Reels**  
    - *Source*: [youtube.com/@dwnews/shorts](https://www.youtube.com/@dwnews/shorts)  
    - *Cadence*: 1.5–2.2 second visual beats. Every sentence boundary triggers a typographic highlight, a number increment, or a graphical change.
    - *What Veasy Takes*: Beat-driven synchronization (`scene.beats`), keeping screen elements alive without violating motion rules.

17. **France 24 English Shorts**  
    - *Source*: [youtube.com/@france24english/shorts](https://www.youtube.com/@france24english/shorts)  
    - *Cadence*: Clear date and location stamps in the top third; lower third reserved for dual-line subtitles.
    - *What Veasy Takes*: Strict enforcement of the safe zone band: scene text confined between y=248 and y=1380, captions between y=1380 and y=1552, right rail (x>940, y>1100) strictly preserved for platform engagement controls.

18. **BBC News Minute / Social Video**  
    - *Source*: [bbc.com/news/video_and_audio](https://www.bbc.com/news/video_and_audio)  
    - *Cadence*: 60-second summary format. Direct statement of facts, zero editorial speculation, verbatim quotes highlighted in quotation glyphs.
    - *What Veasy Takes*: News rules N1–N13 integrity: every number and date grounded in member articles.

19. **The Wall Street Journal Shorts**  
    - *Source*: [youtube.com/@wsj/shorts](https://www.youtube.com/@wsj/shorts)  
    - *Cadence*: Financial comparisons and multi-point breakdowns. Clear category labels, unit indicators, and source citations permanently visible.
    - *What Veasy Takes*: Permanent source credit and timestamp on every frame (`sourcesLine`, `header`).

20. **Washington Post Video Journalism (TikTok/Reels)**  
    - *Source*: [tiktok.com/@washingtonpost](https://www.tiktok.com/@washingtonpost)  
    - *Cadence*: Explanatory graphics using clean document callouts and route maps for infrastructure/investigation stories.
    - *What Veasy Takes*: The `route` scene type for transit corridors, diplomatic paths, and infrastructure links.

21. **Le Monde Shorts (Les Décodeurs)**  
    - *Source*: [lemonde.fr/les-decodeurs](https://www.lemonde.fr/les-decodeurs/)  
    - *Cadence*: Factual verification checklists. "Fact checking in 40 seconds": itemizing claims and verified evidence with clear visual checkmarks.
    - *What Veasy Takes*: The `checklist` scene type for fact verification and statutory requirements.

### Programmatic Video Frameworks & Animation Engines

22. **Remotion Documentation & Showcase**  
    - *Source*: [remotion.dev/docs](https://www.remotion.dev/docs)  
    - *Core Concept*: Deterministic React frame rendering using `useCurrentFrame`, `interpolate`, and spring dynamics. Zero external timing dependencies, pure functional frame mapping.
    - *What Veasy Takes*: Remotion component architecture: stateless rendering of props, using `interpolate` with easing curves, and `@remotion/rough-notation` for phrase emphasis (`marked`).

23. **Motion Canvas (Declarative Animation Architecture)**  
    - *Source*: [motioncanvas.io](https://motioncanvas.io/)  
    - *Core Concept*: Procedural timeline synchronization, compound animation primitives, and layout-aware auto-arranging nodes.
    - *What Veasy Takes*: Coordinated stagger timing where item $i$ enters at `delay + i * stagger`, ending gracefully at settled coordinates.

24. **Revideo (Open Source Video Editing)**  
    - *Source*: [revideo.dev](https://revideo.dev/)  
    - *Core Concept*: Typescript-native video scene graph with strict parametric constraints.
    - *What Veasy Takes*: Strict typed props schemas ensuring LLMs and agents cannot pass arbitrary layout properties.

25. **The Pudding Data Journalism Guidelines on Vertical Storytelling**  
    - *Source*: [pudding.cool/process](https://pudding.cool/process/)  
    - *Core Concept*: Thumb-zone ergonomics, typography scaling based on line length, and avoidance of visual noise on mobile viewports.
    - *What Veasy Takes*: Dynamic `fitSize` font scaling to guarantee text never overflows bounding containers across screen widths.

---

## 2. Inventory of Existing Veasy Brushes

Before proposing new brushes, we audit the existing 22 brushes in `brushes/` to ensure zero overlap:

| Order | Type | Shows |
|---|---|---|
| 10 | `hook` | The opening headline (2–4 lines) |
| 15 | `chapter` | Digest chapter card (`02 / 03`) |
| 20 | `stat` | One big number with optional isotype icons |
| 25 | `share` | Single percentage as 10x10 dot grid |
| 30 | `timeline` | From-to time/date span |
| 35 | `rail` | 2–4 dated milestones along vertical thread |
| 40 | `where` | Georgia map zoom or geographic pin grid |
| 50 | `who` | 1–3 people or entities with role |
| 55 | `link` | Interaction network between 2–3 nodes |
| 60 | `points` | 2–3 short factual bullet points |
| 70 | `quote` | Verbatim quote with attribution |
| 80 | `sources` | Outlets covering the story (data-driven) |
| 90 | `draw` | Animated SVG line drawing |
| 100 | `pair` | Two descriptive cards side by side |
| 110 | `steps` | 2–4 sequential steps joined by arrows |
| 120 | `bars` | 2–5 numeric bars compared from baseline |
| 125 | `compare` | Two values as true-proportion geometric squares |
| 130 | `trend` | 3–8 data points along animated polyline |
| 135 | `agree` | Factual points confirmed across $N$ media outlets |
| 140 | `change` | Single value then vs now (roll-up) |
| 150 | `sign` | Single pictogram performing a verb |
| 1000 | `end` | Closing card with QR code, link, CTA |

### Identified Gaps in Veasy's Current Library
1. **Rankings & Leaderboards**: No dedicated visual for ordered ranks ($1^{\text{st}}, 2^{\text{nd}}, 3^{\text{rd}}$) with rank badges and comparative metric weights.
2. **Head-to-head Clash / Face-off**: `pair` is descriptive text; `compare` is geometric area of squares for one unit; there is no direct head-to-head metric confrontation ("A vs B") with a central confrontation tag.
3. **Deadlines & Countdowns**: `timeline` is only a static text range; there is no dynamic countdown card emphasizing remaining time (days/hours) to a critical deadline.
4. **Calendar Milestone Card**: No card representing an upcoming scheduled session, hearing, or municipal date with explicit day/month/weekday badges.
5. **Glossary & Term Explanation**: Explainer, law, and tech videos lack a formal definition card displaying a core term, category tag, and concise factual definition.
6. **Factual Verification Checklist**: No card displaying 2–4 verified conditions or statutory criteria with structured checkmark indicators.
7. **"What Changes" / Service Impact**: No standardized service journalism card itemizing *Target Group*, *The Change*, and *Effective Date*.
8. **Corridor / Route Movement**: `where` pins a town or region; it cannot draw transit between origin, intermediate waypoint, and destination.
9. **Categorical Budget / Resource Allocation**: `share` is 1 percentage on 100 dots; `bars` are separate non-summing bars; there is no segmented proportion bar illustrating how parts compose a total budget or resource distribution.

---

## 3. Licenses & IP Compliance Table

Veasy strictly requires commercial-use licenses (MIT, ISC, Apache-2.0, BSD, OFL). No GPL or AGPL code is permitted in the engine.

| Asset / Technology | Origin | License | Compliance Status & Notes |
|---|---|---|---|
| FiraGO Font Family | BPG InfoTech / OFL | SIL Open Font License 1.1 | Shipped with Veasy; full commercial rights. |
| Lucide Icons | Lucide Project | ISC License | Shipped in `assets/icons/lucide.json`; LICENSE file preserved. |
| Rough Notation | @remotion/rough-notation | MIT License | Voice-synced marks in `marker.tsx`. |
| Remotion Framework | Remotion Dev GmbH | Remotion License (Free up to 3 people) | Approved by owner (2026-11-02). |
| Handcrafted SVGs | Veasy Project | Proprietary / SiTech | Seed drawings and custom vector geometry. |
| Geostat Region Map | OCHA / Geostat | CC BY-IGO 3.0 | On-screen credit displayed on map scenes. |
| Openverse / Commons | Public Repositories | CC0, PDM, CC-BY, CC-BY-SA | Verified in `assets.py` ledger. |

---

## 4. Ranked Backlog of New Scene Types

We rank 9 candidate scene types by user value, versatility across programs (`news`, `explainer`, `law`, `blog`, `story`), and implementation effort:

| Rank | Scene Type | Order | Value | Effort | Primary Programs | Primary Directors | Rationale |
|---|---|---|---|---|---|---|---|
| 1 | `ranking` | 160 | High | Medium | `news`, `explainer`, `blog` | `data`, `chronicle`, `type` | Ordered top-3 to top-5 list with rank badges, item labels, and metric counts. Universal in economic, civic, and tech news. |
| 2 | `versus` | 170 | High | Medium | `news`, `explainer`, `blog` | `data`, `witness`, `type` | Two-entity head-to-head confrontation with metric values and central "VS" / "წინააღმდეგ" divider. Powerful for debates, market comparisons. |
| 3 | `countdown` | 180 | High | Low | `news`, `explainer`, `law` | `data`, `chronicle`, `brief` | Large remaining count ("12 დღე"), target date, and deadline description. Essential for elections, registrations, and expiring laws. |
| 4 | `calendar` | 190 | High | Low | `news`, `law`, `explainer` | `chronicle`, `brief`, `map` | Calendar sheet displaying month, day, weekday badge, and scheduled hearing or session details. |
| 5 | `glossary` | 200 | Very High | Low | `explainer`, `law`, `blog` | `type`, `brief`, `witness` | Definition card: term title, pronunciation/context chip, concise definition. Opens explainer and legal programs to jargon clarification. |
| 6 | `checklist` | 210 | High | Medium | `law`, `explainer`, `news` | `brief`, `type`, `data` | Fact/criteria verification list: 2–4 factual conditions with state badges. Strictly facts, never advice or subjective opinion. |
| 7 | `impact` | 220 | Very High | Medium | `news`, `explainer`, `law` | `brief`, `data`, `chronicle` | Service news "What changes": target audience, the exact alteration, and effective timeline. Core pillar of public service journalism. |
| 8 | `route` | 230 | High | Medium | `news`, `explainer`, `blog` | `map`, `chronicle`, `brief` | Movement from Origin -> [Via] -> Destination with distance/time indicators. Crucial for transport, trade corridors, and geopolitical itineraries. |
| 9 | `budget` | 240 | High | Medium | `news`, `explainer`, `blog` | `data`, `brief`, `type` | Segmented allocation breakdown: 2–4 categories totaling 100% or absolute sum with proportional segmented bars. |

All 9 brushes fall in the designated `order` range **160–240** (well inside the assigned 160–299 bracket).

---

## 5. Architectural Implementation Plan

Following CLAUDE.md ("A new scene type") and our ground rules:

1. **Brush Definitions (`brushes/<type>.json`)**:
   - Order: 160 to 240.
   - Slots with strict Georgian character limits.
   - `families_deny`: crime, incidents, and deaths excluded where appropriate.
   - Authentic Georgian `example` and `schema`.
   - `em` definitions specifying markable fields and allowed styles.

2. **News Check & Engine Gates (`tt_shorts/news_check.py`, `tt_shorts/engine.py`)**:
   - Add new types to `news_check.SCENE_TYPES`.
   - Add domain-specific validation in `engine.shape_problems`:
     - `ranking`: 3–5 items, ordered rank numbers ($1, 2, 3\dots$), positive values.
     - `versus`: exactly 2 sides, each with title and value/detail, distinct sides.
     - `countdown`: positive integer days/hours, valid target date.
     - `calendar`: valid day (1–31), month name, event text.
     - `glossary`: term, definition text limits, no opinion adjectives.
     - `checklist`: 2–4 factual items, each with text and state.
     - `impact`: target, change, and effective date specified.
     - `route`: 2–4 sequential route stops (origin, destination, optional via).
     - `budget`: 2–4 items, values $>0$, total summing logically.
   - Tests in `tests/test_catalog.py`, `tests/test_scenes.py`, and `tests/test_engine.py`.

3. **Remotion Components (`remotion/src/scenes/`) & Types (`remotion/src/types.ts`)**:
   - Update `types.ts` with new scene fields.
   - Implement components adhering to brand rules (dark canvas, light ink, one red accent never on text, FiraGO font, safe zones, `data-probe` regions, `marked()` for `em` phrases).
   - Register in `SCENES` in `remotion/src/scenes/index.tsx`.

4. **Integration with Directors and Programs**:
   - Add weighted entries to `directors/*.json` (e.g. `data`, `brief`, `chronicle`, `type`, `witness`, `map`).
   - Add to `programs/*.json` (`explainer`, `law`, `blog`, `news`).

5. **Skill Documentation**:
   - Update `skills/write-script/SKILL.md` table and notes.

6. **Demo Stories & Golden Stills**:
   - Provide realistic Georgian demo stories in `stories/`.
   - Execute `engine probe <story> --look all` across all 3 looks (`editorial`, `kinetic`, `cards`) and both themes.
   - Inspect stills to verify optical alignment and safe-zone compliance.

---

## 6. Owner Decisions Log

The following matters are reserved strictly for the project owner and are documented here without unilateral assumption:

1. **Theme Expansion for News**: Whether daytime light theme is approved for production `tbilisi-today` broadcasts (currently `allowed: false` in `brand.json`). All new scenes support both dark and light themes seamlessly.
2. **AI Imagery in Explainer Programs**: Remains disabled in `tt_shorts/media/ai.py` per ROADMAP rules.
3. **World Map Boundaries (C9)**: Global border point-of-view remains an editorial decision; the new `route` scene uses clean topological path geometry without geopolitical dispute risk.
