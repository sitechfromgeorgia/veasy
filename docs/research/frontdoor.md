# Veasy Front Door Audit: Simplifying Video Generation

**Date:** November 2026  
**Document:** `docs/research/frontdoor.md`  
**Charter:** Make Veasy simple to ask for — one front door where a person or an AI says what they want in a sentence, names at most a brand and a style, answers at most one round of questions, and receives a finished, verified film, while preserving all expert options underneath.

---

## 1. Executive Summary & The Problem

As Veasy evolved from a single news Short renderer to a multi-engine video powerhouse (Remotion kit + HyperFrames composed lane, 31 brush scene types, 18 film styles, 8 directors, 4 programs, rubrics, templates, media layers, and automated self-checking probes), the cognitive overhead for newcomers and AI agents expanded drastically.

Today, an agent or user entering Veasy is confronted with **more than 20 distinct conceptual knobs**, **22 CLI subcommands**, **16 tools**, and **13 skills**. To make a video, one had to know:
- Which program fits the source (`news`, `explainer`, `law`, `blog`, `story`)
- Which format to select (`news`, `explainer`, `story`, etc.)
- Which director to assign (`data`, `map`, `type`, `draw`, `chronicle`, `witness`, `brief`, `single`)
- Which look to apply (`editorial`, `kinetic`, `cards`)
- Which theme (`dark` vs `light`)
- Which film engine to target (`remotion` vs `hyperframes`)
- How to structure the multi-step pipeline (`write` $\to$ `check` $\to$ `plan` $\to$ `critique` $\to$ `render` $\to$ `qa` $\to$ `package`)

Following the design in `docs/lemo-opuscar.md` § 5:
> **A person or an AI only needs three concepts: brand, style, story.**

Everything else — program, format, director, look, theme, engine, scene types, motion parameters, music loop, voice preset, and checks — must be derived automatically by code, with every existing flag remaining available as an override for experts.

---

## 2. Complete Inventory & Separation of Concepts

### 2.1. The Three Newcomer Concepts

| Concept | What It Answers | Newcomer Experience | Default Behavior if Omitted |
|---|---|---|---|
| **Story / Request** | *What is it about?* | A single sentence, headline, URL, or document reference (e.g. "Explain Article 17 of the Georgian Constitution"). | Required. Prompts user if missing. |
| **Brand** | *Who is it for?* | Client brand pack (`tbilisi-today`, `sitech`, or custom pack). Sets palette, typography, logo, and footer. | Inferred from request context or defaults to `tbilisi-today`. |
| **Style** | *How does it look and sound?* | Named film style (e.g. `swiss-motion`, `caption-news`, `terminal-ascii`, `data-storytelling`, `countdown`). | Least-used eligible style chosen by `tt_shorts.variety.pick_style()`. |

### 2.2. The Underlying Expert Concepts (Derived Automatically)

| Concept | What It Controls | How Code Derives It in `engine make` |
|---|---|---|
| **Program** | Fact constraints, source requirements, and rule tiers (`news`, `explainer`, `law`, `blog`, `story`). | Inferred from request: law refs $\to$ `law`; blog/hacker topics $\to$ `blog`; fiction/character $\to$ `story`; explain/analyze $\to$ `explainer`; daily news $\to$ `news`. |
| **Source** | Fact ingestion method (`tbilisi-today`, `text`, `url`, `pdf`, `ordo`, `sitech`, `stories`). | Derived from program and request payload (detects URL, `constitution:<n>`, cluster ID, or file path). |
| **Format** | Production bundle configuration (look, captions, outro, transition, music, length window). | Default format of the derived program (`programs/<id>.json`), modulated by style. |
| **Director** | Editorial pacing and scene weighting (`data`, `map`, `type`, `draw`, `chronicle`, `witness`, `brief`, `single`). | Constrained by chosen style; otherwise assigned by `variety.direct()` based on extracted facts. |
| **Look** | Layout grammar (`editorial`, `kinetic`, `cards`). | Defined by style invariants or family mapping (`meta.variant_for`). |
| **Theme** | Color ground (`dark`, `light`). | Brand's default theme (`dark`), or rotated via variety among allowed themes. |
| **Film Engine** | Execution runtime (`remotion` vs `hyperframes`). | Governed by style (`style.json: "engine"`), program, or template. |
| **Rubric** | Recurring branded show chip and episode counter (`number`, `changes`, `continues`, `agree`, `digest`). | Evaluated against cluster eligibility predicates if requested. |
| **Template** | Pre-composed HyperFrames layouts with slots (`templates/<id>/`). | Selected when style or prompt targets an approved composed template. |
| **Brushes / Scene Types** | 31 atomic layout cards (`hook`, `stat`, `ranking`, `versus`, `countdown`, `calendar`, `glossary`, etc.). | Selected by LLM writer / template slot filler guided by director scene weights. |
| **Captions** | Text subtitle layout (`page`, `roll`, `keyword`). | Derived from format or style specification (`captions.py`). |
| **Voice Preset** | TTS voice tone (`anchor`, `warm`, `clear`, `plain`, `sitech`). | Selected by brand category family (`voice_by_family`) or format default. |
| **Music Loop** | Audio bed (`politics`, `society`, `culture`, etc.). | Assigned by category family and rotated evenly across loop variants. |
| **SFX** | Timeline sound cues (`click`, `pop`, `whoosh`, `thud`, `blip`). | Enabled if format or style specifies `sfx: "on"`; mixed at calibrated loudness. |
| **Variety Parameters** | 8 hook layouts, 10 motifs, 8 entrances, 14 transitions. | Selected via least-used rotation with novelty guard fingerprint re-rolls. |
| **Beats & Chapters** | 1.5–2.5s pacing changes and "01 / 03" progress header. | Activated by default on videos $\ge 40$s (`chapters.py`, `beats.py`). |
| **Outro** | Ending card, overlay chip, or loop (`card`, `overlay`, `loop`). | Set by format. |
| **Media Layer** | Licensed illustrations, screenshots, maps, seed drawings. | Queried via `assets.py` based on writer `show` hints; verified by rule N13. |

---

## 3. Commands, Tools, and Skills Audit

### 3.1. Engine CLI Commands

| Category | Command | Target Audience | Role in the New Front Door |
|---|---|---|---|
| **Front Door** | `engine make` | **Newcomer & AI** | **The primary unified entry point.** Takes sentence, derives parameters, checks, plans, asks $\le 1$ question, and renders. |
| **Discovery** | `engine options` | **Newcomer & Expert** | Refactored: leads with Brands and Styles (with stills); moves expert knobs under `"advanced"`. |
| **Discovery** | `engine gallery` | **Newcomer & Expert** | One static HTML visual catalog of all styles, looks, scenes, and directors with stills and clips. |
| Pipeline | `engine plan` | Expert | Called internally by `engine make` to build free storyboard before rendering. |
| Pipeline | `engine check` | Expert | Called internally by `engine make` to enforce news and language gates. |
| Pipeline | `engine render` | Expert | Direct execution when specific low-level flags are explicitly specified. |
| Pipeline | `engine still` | Expert | Scene still generator for quick verification. |
| Pipeline | `engine qa` | Expert | Post-render quality check run automatically by `engine make`. |
| Pipeline | `engine probe` | Expert | Layout bounding box checker run automatically during plan/render. |
| Pipeline | `engine write` | Expert | Step invoked by `engine make` when translating facts to scene JSON. |
| Tooling | `engine critique` | Expert | Pre-flight visual heuristic check. |
| Tooling | `engine dry-run` | Expert | Zero-compute budget and resource estimator. |
| Management | `engine queue` | Production Operator | Job queue manager for automated batch processing. |
| Management | `engine package` | Social / Marketing | Multi-surface export (SRT, carousel, teaser, texts). |
| Management | `engine brand` | Client Onboarding | Ingests external brand books into `brands/<name>/brand.json`. |
| Management | `engine compose` | Composed Specialist | Low-level HyperFrames block and template assembly. |
| Utility | `engine contact-sheet`| Designer | Icon and drawing review sheet. |
| Utility | `engine selftest` | Developer | Golden stills regression suite. |
| Utility | `engine learn` | Developer | Rule failure frequency analysis. |
| Utility | `engine media` | Pipeline | Asset resolver for image queries. |
| Utility | `engine voices` | Sound Designer | TTS tone audition tool. |
| Utility | `engine gc` | System | Disk retention cleaner. |
| Utility | `engine doctor` | DevOps | System dependency health check. |

### 3.2. Hermes Plugin Tools

| Tool Name | Class | Purpose | Front Door Role |
|---|---|---|---|
| **`veasy_make`** | **Front Door** | High-level video creation from single prompt with $\le 1$ round of questions. | **Primary tool for AI agents.** |
| `veasy_options` | Discovery | Inspects engine choices (supports `section="summary"`). | Used by agents to browse available styles and brands. |
| `veasy_plan` | Inspection | Returns timing, words, variety picks, and storyboard sheet. | Used if agent requests preview before rendering. |
| `veasy_critique` | Inspection | Automated visual heuristics scoring. | Used for pre-flight quality scoring. |
| `veasy_dry_run` | Inspection | $0.00 pre-render financial estimator. | Used for budget verification. |
| `veasy_check` | Verification | Strict rule validation. | Specialized validation step. |
| `veasy_render` | Low-level | Direct render execution. | Expert override. |
| `veasy_still` | Low-level | Single frame render. | Expert inspection. |
| `veasy_qa` | Inspection | Video QA evaluation. | Expert verification. |
| `veasy_probe` | Inspection | Layout boundary evaluation. | Expert verification. |
| `veasy_write` | Generation | Script writing from source. | Expert generation. |
| `veasy_package` | Output | Multi-surface packager. | Downstream marketing. |
| `veasy_queue` | Execution | Batch queue interface. | Production queue. |
| `veasy_rubrics` | Feature | Rubric counters and stamping. | TV show generation. |
| `veasy_compose` | Composed | HyperFrames project runner. | Composed development. |
| `veasy_brand` | Management | Automated brand book ingestion. | New client onboarding. |
| `veasy_doctor` | Utility | Environment diagnostic. | Health check. |

### 3.3. Hermes Plugin Skills

| Skill | Newcomer Role | Action / Routing |
|---|---|---|
| **`veasy:make-video`** | **The Single Front Door Skill** | **Only skill an agent needs to start.** Reads user sentence, asks 1 round of questions if facts are missing, routes to `veasy_make`. |
| `veasy:styles` | Specialized Reference | Consulted only if user wants a deep dive into style invariants or wants to customize one. |
| `veasy:write-script` | Specialized Reference | Consulted if manually authoring brush scenes. |
| `veasy:programs` | Specialized Reference | Consulted when configuring new programs or legal/explainer data sources. |
| `veasy:compose` | Specialized Reference | Consulted when composing custom GSAP / HyperFrames HTML scenes. |
| `veasy:brands` | Specialized Reference | Consulted when onboarding a new client brand book. |
| `veasy:qa` | Specialized Reference | Consulted for troubleshooting audio/video QA failures. |
| `veasy:package` | Specialized Reference | Consulted when generating carousels, teasers, and social captions. |
| `veasy:formats` | Specialized Reference | Consulted when configuring new show formats. |
| `veasy:directors` | Specialized Reference | Consulted when exploring creative directing personas. |
| `veasy:rubrics` | Specialized Reference | Consulted when generating episodic daily series. |
| `veasy:queue` | Specialized Reference | Consulted for multi-worker daemon job scheduling. |
| `veasy:media` | Specialized Reference | Consulted for stock image provider and copyright licensing details. |

---

## 4. The `engine make` Contract

### 4.1. CLI Invocation
```bash
python -m tt_shorts.engine make "<request>" [--brand <brand>] [--style <style>] [--source <source>] [--length short|medium|long] [--yes]
```

### 4.2. Algorithmic Workflow
```
                          [User Prompt: "<request>"]
                                      |
                     Parse Intent, Entity, and Keywords
                                      |
      +-------------------------------+-------------------------------+
      |                               |                               |
Inferred Brand                  Inferred Program                Inferred Source
(sitech vs tbilisi-today)   (news, explainer, law, blog, story) (URL, Ordo, cluster, file)
      |                               |                               |
      +-------------------------------+-------------------------------+
                                      |
                           Select / Resolve Style
                  (Explicit --style OR variety.pick_style)
                                      |
                  Derive Format, Engine, Director, Look, Theme
                                      |
                     Need Input on Missing Source Facts?
                       /                             \
                 YES (missing)                  NO (inferable / --yes)
                     /                                 \
         Ask ONE Round of Questions               Run engine plan
           (facts, custom assets)                  (Free Storyboard)
                     \                                 /
                      +---------------+---------------+
                                      |
                              Render or Queue
                          (gemini/silent, QA check)
                                      |
                            Finished Checked Film
```

### 4.3. One Round of Questions Rule
Code resolves everything it can automatically. Questions are asked **at most once**, and **only** for information that code cannot determine:
1. *Missing Facts / Source*: When the request is an explainer or news topic without a discernible URL, cluster ID, or article body, ask for the text or source link.
2. *Personal Assets*: When the user explicitly requests their own logos, charts, or images, ask for the file paths.
3. *Storyboard Gate*: Whether the user wishes to inspect the storyboard before finalizing the render (skipped if `--yes`).

---

## 5. Summary of Architecture Changes

1. **`tt_shorts/make.py` (New Module):** Houses `make_film()` engine logic, request understanding, intent-to-pipeline mapping, interactive question resolution, planning, and rendering.
2. **`tt_shorts/engine.py` (Updates):**
   - Implements `make` subcommand and `make_cmd()`.
   - Implements `gallery` subcommand and `gallery_cmd()`.
   - Refactors `options()` to lead with `brands` and `styles`, nesting expert parameters under `"advanced"`.
3. **`__init__.py` & `plugin.yaml` (Updates):**
   - Registers tool `veasy_make`.
   - Exposes parameters: `request` (required), `brand`, `style`, `source`, `length`, `preview_storyboard`, `yes`.
4. **`skills/make-video/SKILL.md` (Update):**
   - Streamlined into the single front door skill ($< 12,000$ bytes).
   - Leads with the 3 concepts: Brand, Style, Story.
5. **`tt_shorts/gallery.py` (New Module):**
   - Builds `out/gallery.html` displaying all styles, looks, scenes, and directors with visual stills and media clips.
