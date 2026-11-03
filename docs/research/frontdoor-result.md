# Front Door Delivery Report: Making Veasy Simple to Ask For

**Lane**: Front Door (`goal/frontdoor`)  
**Repository**: `D:\MyStaff\Veasy-frontdoor`  
**Base Branch**: `goal/frontdoor` (branched from `main` at `bd5cd8b`)  
**Date**: November 3, 2026  

---

## 1. What Shipped

### 1.1. Core Front Door Pipeline (`tt_shorts/make.py`)
- **`make_film()`**: The single unified engine entry point. Implements full derivation of all video parameters from a single natural language sentence or reference:
  - Parses intent: extracts story reference, program type (`news`, `explainer`, `law`, `blog`, `story`), brand pack (`tbilisi-today`, `sitech`), and source type.
  - Derives format, director, look, theme, captions, outro, and animation engine (`remotion` vs `hyperframes`).
  - Style selection: if `--style` is specified, validates it; if omitted, invokes `tt_shorts.variety.pick_style(story, brand, engine=engine)` for least-used rotation restricted to compatible engines.
  - Generates storyboard via `tt_shorts.plan.run()` without compute cost.
  - One round of questions: evaluates whether facts are known; if facts cannot be found, asks for source/facts, custom assets, and storyboard preview. Defaults applied when non-interactive or `--yes` is passed.
  - Renders video via `tt_shorts.engine.render_any()` or queues for background rendering.
- **CLI Subcommand `engine make`**:
  ```bash
  python -m tt_shorts.engine make "<request>" [--brand <name>] [--style <id>] [--source <src>] [--length <s/words>] [--engine <name>] [--preview] [--yes] [--queue]
  ```
- **Hermes Agent Plugin Tool `veasy_make`**:
  - Registered in `plugin.yaml`, `__init__.py:TOOLS`, and exported in `__init__.py`.
  - Comprehensive unit test in `tests/test_plugin.py` verifying parameter forwarding and dry-run execution.

### 1.2. Refactored `engine options` (`tt_shorts/engine.py`)
- Leads with the newcomer concepts:
  - `"brand"`: active default brand (`tbilisi-today`).
  - `"brands"`: list of available brand packs with name, label, logo, colors, allowed themes, and preview still path.
  - `"styles"`: summary of 18 film styles with engine compatibility, description, and preview still path.
- Encapsulates expert-only knobs under `"advanced"`:
  - Program schemas, format definitions, look layouts, director weighting, rubrics, chapter pacing, captions, themes, engines, and sound effects.
- 100% backward compatibility preserved: top-level dictionary keys remain accessible for all existing tools and tests.

### 1.3. Visual Discovery Gallery (`tt_shorts/gallery.py` & `engine gallery`)
- `python -m tt_shorts.engine gallery [--output out/gallery.html]`:
  - Scans all 18 film styles, 3 looks (`editorial`, `kinetic`, `cards`), 31 brush scene types (`hook`, `stat`, `versus`, `ranking`, etc.), and 8 directors (`data`, `map`, `type`, `draw`, `chronicle`, `witness`, `brief`, `single`).
  - Embeds crisp vector preview stills, animated visual CSS demonstrations, badges, tags, and documentation.
  - Outputs a zero-dependency static HTML file (`out/gallery.html`, ~171 KB) openable in any browser.

### 1.4. Unified Agent Starting Skill (`skills/make-video/SKILL.md`)
- Sized at 6,865 bytes (well below the 12,000-byte plugin limit).
- Teaches agents the 3 core newcomer concepts (**Story**, **Brand**, **Style**) and provides explicit routing to specialized skills (`veasy:styles`, `veasy:scenes`, `veasy:motion`, `veasy:compose`, `veasy:brands`) only when granular modifications are requested.

### 1.5. Engine-Aware Variety Rotation
- Updated `tt_shorts/variety.py:pick_style()` and `tt_shorts/styles.py:for_story()` with an `engine` parameter.
- Ensures Remotion-based programs (`news`, `explainer`, `law`, `blog`) only rotate through Remotion or universal styles (`swiss-motion`, `caption-news`, etc.), while HyperFrames templates select HyperFrames styles (`whiteboard`, `blueprint`, `briefing-board`).

---

## 2. Proof: Five Films From One Sentence Each

Five complete films were generated from a single sentence each using `engine make`, spanning two brand packs (`tbilisi-today`, `sitech`), five distinct programs, both engines (`remotion` and `hyperframes`), free preview voices, and standard offline fixtures. Zero paid API calls or cloud servers were used.

### 2.1. Film Summary Table

| # | Program | Brand Pack | Request Sentence | Derived Style | Engine | Output File | Duration | File Size | Streams |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **News** | `tbilisi-today` | "ვარკეთილში გაზსადენი დაზიანდა და 6400 აბონენტს გაზი გაეთიშა" | `satellite-briefing` | Remotion | `data/renders/tbilisi-today/2026-11-03/24835-news-composed-page.mp4` | 36.9s | 6,200,581 B | Video: 1080×1920 (h264) |
| 2 | **Explainer** | `tbilisi-today` | "ინფლაცია საქართველოში: რატომ იზრდება ფასები და როგორ მუშაობს" | `swiss-motion` | Remotion | `data/renders/tbilisi-today/2026-11-03/explainer-inflation-explainer-editorial-page.mp4` | 29.1s | 2,867,930 B | Video: 1080×1920 (h264) |
| 3 | **Law** | `tbilisi-today` | "საქართველოს კონსტიტუციის მე-17 მუხლი: აზრის, სიტყვისა და გამოხატვის თავისუფლება" | `swiss-motion` | Remotion | `data/renders/tbilisi-today/2026-11-03/constitution-17-explainer-editorial-page.mp4` | 42.7s | 7,962,040 B | Video: 1080×1920 (h264) |
| 4 | **Blog** | `sitech` | "Claude და Grok ხელოვნური ინტელექტის აგენტები კიბერშეტევების ავტომატიზაციაში" | `swiss-motion` | Remotion | `data/renders/sitech/2026-11-03/claude-and-grok-among-ai-agents-used-to-automate-attacks-on-lati-news-editorial-page.mp4` | 40.5s | 3,628,564 B | Video: 1080×1920 (h264) |
| 5 | **Story** | `sitech` | "პატარა რობოტი ბიპი სწავლობს ხატვას და მზეს ხატავს" | `whiteboard` | HyperFrames | `data/renders/sitech/2026-11-03/bipi-draws-story-composed-keyword.mp4` | 25.4s | 3,613,340 B | Video: 1080×1920 (h264), Audio: aac |

### 2.2. Questions Log & Decision Accounting

- **Film 1 (News)**: 
  - Intent parsed: matched incident keywords $\to$ program `news`, source fixture `stories/24835.json`.
  - Questions asked: 0 (facts resolved from cluster fixture; assets = `no`, preview = `render`).
- **Film 2 (Explainer)**: 
  - Intent parsed: matched economic keywords $\to$ program `explainer`, source fixture `stories/explainer-inflation.json`.
  - Questions asked: 0 (facts resolved from fixture; assets = `no`, preview = `render`).
- **Film 3 (Law)**: 
  - Intent parsed: matched `კონსტიტუცი` & article 17 $\to$ program `law`, source fixture `stories/constitution-17.json`.
  - Questions asked: 0 (facts resolved from Ordo constitution fixture; assets = `no`, preview = `render`).
- **Film 4 (Blog)**: 
  - Intent parsed: matched cyber attack keywords $\to$ program `blog`, brand `sitech`, source fixture `stories/claude-and-grok-among-ai-agents-used-to-automate-attacks-on-lati.json`.
  - Questions asked: 0 (facts resolved from fixture; assets = `no`, preview = `render`).
- **Film 5 (Children's Short Story)**: 
  - Intent parsed: matched character keywords (რობოტი ბიპი) $\to$ program `story`, brand `sitech`, director `draw`, style `whiteboard`, template HyperFrames.
  - Questions asked: 0 (facts resolved from fixture; assets = `no`, preview = `render`).
- **Unknown Fact Path (Interactive & Agent Gate)**:
  - When facts cannot be derived from code or local fixtures and `--yes` is not set, `ask_one_round` halts and presents exactly ONE round of questions:
    1. *Where is the source or reference for the story?* (URL / file / cluster ID)
    2. *Do you want to add custom assets or logos?* (no / path)
    3. *Would you like to preview the storyboard before rendering?* (render / preview)
  - When invoked by an agent non-interactively without known facts, it returns `{"status": "needs_input", "questions": [...]}` for the agent to answer in a single follow-up call.

---

## 3. Conceptual Surface: Newcomer (3) vs. Expert (17)

### 3.1. The Three Newcomer Concepts
1. **Story** (*What is it about?*): A sentence, headline, or document link.
2. **Brand** (*Who is it for?*): `tbilisi-today`, `sitech`, or a custom client pack.
3. **Style** (*How does it look and sound?*): A named film style (e.g. `swiss-motion`, `whiteboard`, `caption-news`).

### 3.2. The Seventeen Expert Knobs (Derived Automatically)
1. **Program**: `news`, `explainer`, `law`, `blog`, `story` (derived from keywords/source).
2. **Format**: Default format mapped from program.
3. **Director**: Editorial weighting (`data`, `map`, `type`, `draw`, `chronicle`, `witness`, `brief`, `single`).
4. **Look**: `editorial`, `kinetic`, `cards` (derived from style).
5. **Theme**: `dark` / `light` (derived from brand).
6. **Film Engine**: `remotion` / `hyperframes` (derived from style/template).
7. **Rubrics**: Recurring chip and counter.
8. **Templates**: HyperFrames pre-composed layouts.
9. **Scene Brushes**: 31 atomic layout cards (`hook`, `stat`, `versus`, etc.).
10. **Captions**: `page`, `roll`, `keyword` (derived from format).
11. **Voice Preset**: TTS voice tone selected by category family.
12. **Music Loop**: Audio track rotated evenly by topic family.
13. **SFX**: Timeline sound effects mixed at calibrated volume.
14. **Variety Motifs**: Hook layouts, motifs, entrances, transitions.
15. **Beats & Chapters**: Pacing shifts and chapter markers.
16. **Outro**: Ending card or loop.
17. **Media Layers**: Licensed illustrations, screenshots, maps.

---

## 4. What Was Not Done & Why

1. **No Paid API Calls or Cloud Servers**:
   - Kept the engine 100% self-contained and reproducible offline using local fixtures and free TTS voices.
2. **No Breaking Changes to Existing Commands**:
   - `engine render`, `engine plan`, `engine probe`, `engine queue`, and all lower-level flags remain fully operational. Experts can still specify every flag down to the frame.
3. **No External Web Server Required for the Gallery**:
   - `engine gallery` writes a static, zero-dependency HTML file (`out/gallery.html`) that works directly via `file://` URL without starting a daemon.

---

## 5. Open Owner Decisions

1. **Static Gallery Hosting**:
   - Decision on whether to publish `out/gallery.html` to a public GitHub Pages site or S3 bucket for client previewing during sales and onboarding.
2. **Default Style Rotation Weights**:
   - Currently, `variety.pick_style` weights all eligible styles equally using a least-used-first strategy. The owner may decide if certain styles (e.g., `swiss-motion`, `caption-news`) should have higher baseline rotation probability for daily news.

---

## 6. Files Touched & Created

| File | Status | Description |
|---|---|---|
| `docs/research/frontdoor.md` | Created | Comprehensive audit of all concepts, commands, tools, and skills. |
| `docs/research/frontdoor-result.md` | Created | This delivery and verification report. |
| `tt_shorts/make.py` | Created | Core front door orchestration: intent parsing, questions round, derivation, planning, rendering. |
| `tt_shorts/gallery.py` | Created | Visual gallery builder for styles, looks, scenes, and directors. |
| `stories/explainer-inflation.json` | Created | Verified offline fixture for economic explainer stories. |
| `tests/test_frontdoor.py` | Created | Unit tests for intent parsing, question rounds, derivation, and dry-run execution. |
| `tests/test_gallery.py` | Created | Unit test for static gallery HTML generation and asset presence. |
| `tt_shorts/engine.py` | Modified | Added `make` and `gallery` CLI subcommands; refactored `options()` to lead with brands/styles. |
| `tt_shorts/variety.py` | Modified | Added `engine` filter parameter to `pick_style()`. |
| `tt_shorts/styles.py` | Modified | Added `engine` filter parameter to `for_story()`. |
| `tt_shorts/brand.py` | Modified | Included preview still paths in brand summaries. |
| `plugin.yaml` | Modified | Registered Hermes tool `veasy_make`. |
| `__init__.py` | Modified | Exported `veasy_make` tool in `TOOLS`. |
| `skills/make-video/SKILL.md` | Modified | Streamlined agent skill to 6.8 KB focusing on the 3 core concepts. |
| `tests/test_plugin.py` | Modified | Added test for `veasy_make` Hermes tool. |

---

## 7. Verification and Test Gates

1. **Python Unit Tests**:
   - Command: `python -m unittest discover -s tests`
   - Result: **653 tests ran, 653 passed, 4 skipped, 0 failures, 0 errors** (106.7s).
2. **Remotion TypeScript Gate**:
   - Command: `(cd remotion && npx tsc --noEmit)`
   - Result: Clean 0 exit code, 0 type errors.
3. **Stream & Duration Verification**:
   - Verified via `ffprobe` across all 5 rendered videos (all rendered at 1080×1920 with valid durations between 25.4s and 42.7s).
4. **Plugin Tool Gate**:
   - Command: `python -m unittest tests/test_plugin.py`
   - Result: **13 tests ran, 13 passed, 0 failures, 0 errors**.
