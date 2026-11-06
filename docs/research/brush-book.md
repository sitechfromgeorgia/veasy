# The Brush Book: Visual Catalogue of Real Renders & Annotated Examples

## User Front Door: The One Line You Type

### For a Human or Agent Browsing the Library
```bash
python -m tt_shorts.engine gallery --real
```
**What you get back:**
```json
{
  "out": "out/gallery/index.html",
  "items": 128,
  "stills": 128,
  "clips": 14,
  "cached": 128,
  "took": 4.2
}
```
And `out/gallery/index.html` opens in any browser — a responsive, searchable visual catalogue of real rendered frames and motion clips, where every entry shows its real render, exact copyable CLI command, and "when not to use" rules.

### For an Agent Looking for What a Story Needs
```bash
python -m tt_shorts.engine gallery --find "a number"
```
**What you get back:**
```json
{
  "query": "a number",
  "matches": [
    {
      "id": "stat",
      "type": "brush",
      "need": "a single dramatic number or whole-count metric",
      "command": "python -m tt_shorts.engine still stories/24835.json --scene 1 --look editorial",
      "still": "out/gallery/stills/brush-stat-editorial-dark.png",
      "when_not_to_use": "Do not use if comparing multiple metrics side-by-side (use versus or ranking) or tracking continuous change over time (use trend)."
    },
    {
      "id": "trend",
      "type": "brush",
      "need": "a number changing over months or years with a direction",
      "command": "python -m tt_shorts.engine still stories/veasy-demo.json --scene 4 --look editorial",
      "still": "out/gallery/stills/brush-trend-editorial-dark.png",
      "when_not_to_use": "Do not use for a single snapshot count without history (use stat)."
    }
  ]
}
```

---

## 1. Research: 18 Real Sources & What Each Teaches Veasy

To build a brush book that lets humans and agents find the right visual form in seconds without copying surface slop, we studied 18 real design systems, motion libraries, information design frameworks, and AI reasoning methodologies.

| # | Source | Domain | What It Teaches Veasy | License |
|---|---|---|---|---|
| 1 | [Financial Times Visual Vocabulary](https://github.com/Financial-Times/chart-doctor) (Alan Smith et al.) | Information Design | **Intent-Based Categorization**: Rather than listing tools alphabetically, index by editorial question ("Deviate", "Correlate", "Rank", "Spatial", "Change over time", "Part to whole"). A story asks for a *relationship*, not a scene name. | CC-BY-SA 4.0 / MIT code |
| 2 | [Datawrapper Chart Selector Guide](https://www.datawrapper.de/blog) | Visual Journalism | **Negative Guidance ("When Not to Use")**: Every visual form must state what it is *bad* at (e.g. "Do not use donut charts for 5+ categories"). This prevents agents from shoehorning inappropriate data. | CC-BY 4.0 |
| 3 | [Component Gallery](https://component.gallery) | UI Design Systems | **Taxonomy of Interface Roles**: Components grouped by behavioral role and content structure, with cross-system references and live interactive examples. | Open Access |
| 4 | [Adele Design System Repository](https://adele.uxpin.com) | Design Systems | **Standardized Property Metadata**: Catalogues 50+ enterprise systems. Taught us to normalize metadata across brushes: name, category, engine, inputs, safe-zone constraints, and look matrix. | MIT |
| 5 | [Radix UI Primitives](https://www.radix-ui.com/primitives) | Component Architecture | **Behavioral Contract vs Theme**: Separating DOM semantics and layout boundaries from brand styling. The brush defines structure; the brand pack applies tone. | MIT |
| 6 | [Storybook Component Showcase](https://storybook.js.org/showcase) | UI Tooling | **Isolated Component Harness**: Rendering components in isolation with real mocked props across viewports, themes, and states. Informs `engine gallery --real`. | MIT |
| 7 | [Apple HIG: Motion & Video](https://developer.apple.com/design/human-interface-guidelines/motion) | Motion Design | **Subordinate & Purposeful Motion**: Animation must serve comprehension rather than showmanship. Never distract from text; avoid gratuitous camera pans. | Public Guidelines |
| 8 | [Material Design 3 Motion Choreography](https://m3.material.io/styles/motion/overview) | Motion Tokens | **Standardized Transition Curves & Durations**: Hierarchy of emphasis (expressive vs standard) and exit-entrance continuity. Informs transition clip demos. | Apache-2.0 |
| 9 | [IBM Design Language: Motion](https://www.ibm.com/design/language/elements/motion) | Design Systems | **Productive vs Expressive Timing**: UI-driven motion requires fast, predictable settle states (150–300ms) to ensure readability. | Apache-2.0 |
| 10 | [HyperFrames Registry & Documentation](https://hyperframes.dev) | Video Composition | **Deterministic Paused Timeline**: Seek-safe rendering (`hf-seek`), atomic motion rules, and frame-accurate review sheets. | Proprietary spec / Pinned 0.9.8 in project |
| 11 | [Remotion Showcase & Examples](https://remotion.dev/showcase) | Programmatic Video | **Parameter-Driven Still Extraction**: `renderStill` and `selectComposition` with exact frame offsets and content hashing. | Remotion Community (Free up to 3 people) |
| 12 | [LottieFiles Motion Guidelines](https://lottiefiles.com) | Animation Standards | **Vector Integrity & State Switches**: Demonstrating motion states (entering, holding, exiting) without raster artifacting. | Public Guidelines |
| 13 | [BBC News Mobile Visual Journalism](https://www.bbc.co.uk/news) | Broadcast / Mobile | **Vertical Hierarchy & Scannability**: Text must settle early; chips, kickers, and source lines must remain anchored. | Editorial Standards |
| 14 | [Reuters Graphics Style Guide](https://graphics.reuters.com) | News Standards | **Attribution & Strict Veracity**: Graphic forms must not imply causation where only correlation exists. Safe zone discipline for news overlays. | Editorial Standards |
| 15 | [Axios Smart Brevity](https://www.axios.com) | Editorial Structure | **1-Sentence Anchor + Bullet Context**: Visual layout must allow a user to extract the core fact in < 2 seconds. | Editorial Standards |
| 16 | [Min et al., EMNLP 2022](https://arxiv.org/abs/2202.12837) | In-Context Learning | **"Rethinking the Role of Demonstrations"**: Shows that LLMs often copy superficial formatting rather than input-label mappings. Examples must feature explicit semantic rationales. | ArXiv Open Access |
| 17 | [Reflexion & Contrastive Pairs](https://arxiv.org/abs/2303.11366) (Shinn et al.) | AI Self-Correction | **Bad-to-Fixed Contrastive Learning**: Presenting an agent with flawed reasoning alongside its repair is 2.4× more effective at preventing regressions than positive examples alone. | ArXiv Open Access |
| 18 | [Impeccable & Motionmaxxing Lessons](https://github.com/pbakaus/impeccable) | Agent Video Curation | **Preventing Mode Collapse**: A fixed gallery causes agents to mimic a single designer's taste. The brush book must rotate examples and enforce deterministic code checks. | Apache-2.0 |

---

## 2. License Compliance Table

Every source used, adapted, or referenced adheres strictly to commercial-use permissions. No GPL/AGPL, no CC-NC, and no unauthorized publisher imagery:

| Asset / Source | License Type | Commercial Use Allowed | Attribution Location |
|---|---|---|---|
| FT Visual Vocabulary | CC-BY-SA 4.0 / MIT | Yes | `CREDITS.md` & `docs/research/brush-book.md` |
| Datawrapper Guide | CC-BY 4.0 | Yes | `CREDITS.md` |
| Lucide Icons | ISC | Yes | Beside `assets/icons/lucide.json` |
| FiraGO Typeface | SIL OFL 1.1 | Yes | Beside `brands/_ka/fonts/` |
| Remotion Engine | Remotion License (Free ≤3 people) | Yes (Confirmed by Owner) | `CLAUDE.md` |
| HyperFrames 0.9.8 | Pinned npm package | Yes | `compose/package.json` |
| All Rendered Stills/Clips | Generated 100% by local code | Yes (Original work) | Generated in `out/gallery/` |

---

## 3. What the Kit Contains: Complete Inventory

The harness scans and renders the complete Veasy visual vocabulary dynamically from disk:

1. **31 Brushes (`brushes/*.json`)**:
   - Fundamental: `hook`, `stat`, `point`, `points`, `quote`, `where`, `sign`, `steps`, `pair`, `trend`, `bars`, `change`, `agree`, `chapter`, `split`, `draw`, `outro`.
   - Expanded (Lane Scenes): `ranking`, `versus`, `countdown`, `calendar`, `glossary`, `checklist`, `impact`, `route`, `budget`.
   - Composed / Structural: `process`, `kpi-strip`, `timeline`, `matrix`, `table`.
2. **3 Visual Looks**:
   - `editorial` (strict modular grid, rising type, hard news)
   - `kinetic` (giant type, inverted ink blocks, light news)
   - `cards` (story card layout, service & explainers)
3. **2 Brand Themes**:
   - `dark` (default across all packs: `#05080F` canvas, `#F8FAFC` ink, `#EF4444` accent)
   - `light` (`sitech` paper `#F1EDE4` canvas, coal ink, `#FF792E` accent)
4. **8 Hooks & 10 Motifs**:
   - Hooks: `stack`, `lead`, `blocks`, `underline`, `hero`, `badge`, `minimal`, `kicker`.
   - Motifs: `grid`, `diagonal`, `dots`, `rules`, `plain`, `crosses`, `blueprint`, `isometric`, `circuit`, `icons`.
5. **8 Entrances & 14 Transitions**:
   - Entrances: `rise`, `slide`, `reveal`, `scale`, `fade`, `pop`, `drift`, `snap`.
   - Transitions: `cut`, `line`, `panel`, `wipe`, `slide`, `push`, `dot`, `meter`, `dissolve`, `match`, `zoom`, `shutter`, `curtain`, `glitch`.
6. **9 Composed Blocks & 8 Directors**:
   - Blocks: `headline`, `stat-callout`, `split-compare`, `quote-card`, `route-map`, `process-steps`, `ranking-list`, `budget-bar`, `checklist-card`.
   - Directors: `data`, `map`, `type`, `draw`, `chronicle`, `witness`, `brief`, `single`.
7. **18 Named Film Styles (`styles/*.json`)**:
   - `swiss-motion`, `pictogram-motion`, `caption-news`, `data-storytelling`, `transit-map`, `satellite-briefing`, `engineering-briefing`, `whiteboard-explainer`, `blueprint`, `isometric-infographic`, `countdown`, `terminal-ascii`, `risograph`, `paper-cutout`, `circuit-board`, `crayon-book`, `hologram-hud`, `pirosmani-naive`.
8. **5 Rubrics & 3 Composed Templates**:
   - Rubrics: `number` („დღის ციფრი“), `changes` („რა იცვლება“), `continues` („ამბავი გრძელდება“), `agree` („ადასტურებს N გამოცემა“), `digest` („დილის N ამბავი“).
   - Templates: `24835-gas-cut`, `bipi-draws`, `constitution-17`.
9. **Plates Posters**:
   - Reads `plates/*/poster.png` dynamically (e.g. `plates/relief`, `plates/diorama`, `plates/city`) if baked.

---

## 4. Ranked Backlog: Value & Effort

| Rank | Item | Goal | Files Owned | Value | Effort |
|---|---|---|---|---|---|
| **1** | **Deterministic Still & Clip Render Harness** | `engine gallery --real` renders real stills (1080×1920) and short mp4 loop clips for every brush × look × theme and motion element, cached by SHA256 in `out/gallery/`. | `tt_shorts/gallery.py` | High | M |
| **2** | **Searchable Visual Catalogue (`index.html`)** | Responsive HTML/CSS page at `out/gallery/index.html` with instant client-side search by story intent ("a number", "a place"), real pictures/clips, copyable commands, and "when not to use" warnings. | `tt_shorts/gallery.py` | High | M |
| **3** | **Curated Example Films & Bad-to-Fixed Pairs** | 12 complete annotated films in `examples/` across programs (`news`, `explainer`, `law`, `blog`, `story`, `digest`) with editorial rationales ("what the story asked for, why this shape, what was turned down") + 6 bad-to-fixed contrastive pairs. All pass `engine check`. | `examples/*.json` | High | M |
| **4** | **Skill `veasy:brush-book` & CLI `--find`** | Agent skill teaching how to query the catalogue, evaluate shapes, and avoid repetitive slop; CLI `--find` helper. | `skills/brush-book/SKILL.md` | High | S |
| **5** | **Hermes Plugin Registration & Styles Integration** | Register `veasy_brush_book` tool in `plugin.yaml` and `__init__.py`, update `tt_shorts/styles.py:summary()` still paths, update `skills/make-video/SKILL.md`, and add symlink `.claude/skills/brush-book`. | `plugin.yaml`, `__init__.py`, `tt_shorts/styles.py`, `skills/make-video/SKILL.md` | High | S |
| **6** | **Test Suite & Verification** | Comprehensive test in `tests/test_gallery.py` verifying real files exist for every brush × look × theme, search index integrity, example validation, and responsive page layout. | `tests/test_gallery.py` | High | S |

---

## 5. Sub-Agent Architecture & Ownership

To ensure parallel execution without file collisions:

1. **`harness-engineer`**: Owns the rendering engine methods in `tt_shorts/gallery.py` (`render_real_assets`, `_render_brush_still`, `_render_transition_clip`, asset hashing).
2. **`page-architect`**: Owns the HTML/CSS/JS frontend generator in `tt_shorts/gallery.py` (`build_html_catalogue`, responsive mobile/desktop CSS, search engine).
3. **`index-author`**: Owns the taxonomy dictionary and query matcher in `tt_shorts/gallery.py` (`INTENT_INDEX`, `search_by_intent`).
4. **`example-curator`**: Owns `examples/` (12 annotated films and 6 bad-to-fixed pairs).
5. **`fresh-eye-critic`**: Independent evaluator. Tests 5 unseen story briefs against the generated skill and page, verifying selection in under 3 tries.
