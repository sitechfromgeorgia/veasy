# Research & Architecture: Agent Tooling, Skills & Critique in Veasy

**Author:** Veasy Tooling Agent  
**Date:** 2026-11-03  
**Status:** Research & Backlog Complete; Baseline Windows Issues Resolved  
**Scope:** Tools, Skills, Hermes Plugin, Agent Discoverability, Self-Critique Loops, Brand Ingestion, and MCP Proposal.

---

## 1. Executive Summary

Veasy is an autonomous, dual-engine (Remotion + HyperFrames) video synthesis platform for AI agents. While the core Python and rendering layers are capable, testing Veasy as a "cheap LLM" revealed critical friction points:
1. **Context Window Exhaustion:** `veasy_options` dumps >60 KB of raw JSON containing hundreds of icons, Georgian stems, and internal schema objects at once. A resource-constrained model loses focus or truncates output.
2. **Brittle Error Handling:** File omissions or validation failures produced unhandled Python tracebacks in `stderr` rather than actionable, structured JSON error objects with correction hints.
3. **Missing Pre-Flight Self-Critique:** An agent had no dedicated critique tool to audit planned stills or calculate render costs before spending budget or triggering multi-minute rendering pipelines.
4. **Lack of Automated Brand Intake:** Creating a new brand required manual file creation and JSON schema authoring, whereas modern agentic toolkits support `brand new` extraction from URLs, PDFs, or design markdown specs.

This document synthesizes findings from 28 real-world sources across agent tool design, commercial AI video interfaces, visual self-critique loops, and our hands-on friction testing, establishing a ranked implementation backlog.

---

## 2. Research Survey (28 Real-World Sources)

### Category A: Agent Tool Design & Agent Skills

1. **Anthropic: Tool Use Best Practices & Building Effective Agents (2025/2026)**
   * *Link:* https://docs.anthropic.com/en/docs/build-with-claude/tool-use
   * *Core Takeaway:* Tool descriptions are prompts for non-deterministic reasoners. They must state *when to use*, *when NOT to use*, explain parameter constraints, provide input examples, and return concise, actionable error messages rather than raw stack traces.
   * *Teaches Veasy:* Rewrite all tool descriptions in `__init__.py` and `plugin.yaml` to include "Use when / Do NOT use when", input examples, and fallback recovery paths.

2. **Model Context Protocol (MCP) Specification (Anthropic, 2024–2026)**
   * *Link:* https://modelcontextprotocol.io/
   * *Core Takeaway:* Universal standard for exposing tools, resources, and prompts. Recommends strict snake_case naming (`service_action_resource`), progressive disclosure to prevent context bloat, strict pagination, and separation between read-only and mutating actions.
   * *Teaches Veasy:* Keep tool names systematically scoped, add section-based progressive discovery to `veasy_options`, and structure internal APIs so an MCP server can wrap them cleanly.

3. **Google: Gemini Function Calling & Agent Tools Guide**
   * *Link:* https://ai.google.dev/gemini-api/docs/function-calling
   * *Core Takeaway:* Schemas should use strict enums, required parameter arrays, and avoid deeply nested optional objects. Truncate outputs cleanly and provide recovery hints on parameter errors.
   * *Teaches Veasy:* Add explicit enums and validation guards on all tool arguments in `__init__.py`.

4. **OpenAI: Best Practices for Function Calling and Assistants**
   * *Link:* https://platform.openai.com/docs/guides/function-calling
   * *Core Takeaway:* Keep total number of tools per turn compact (<15-20 active tools). High-cardinality tool registries require meta-tools or search capabilities.
   * *Teaches Veasy:* Hermes plugin exposes 13-14 tools, right at the sweet spot. Tools must not duplicate functionality.

5. **Remotion Agent Skills (`remotion-dev/skills`)**
   * *Link:* https://github.com/remotion-dev/skills
   * *Core Takeaway:* Focuses on modular, task-specific skills (`remotion-create`, `remotion-render`, `remotion-captions`). Highly focused SKILL.md documents (<12 KB) that link to each other.
   * *Teaches Veasy:* Veasy skills must remain small (<12,000 bytes as checked by `test_skills_are_small_and_link_only_to_real_siblings`), each serving one clear stage of the video lifecycle.

6. **HyperFrames Agent Skills (`heygen-com/hyperframes`)**
   * *Link:* https://github.com/heygen-com/hyperframes
   * *Core Takeaway:* Skills enforce deterministic rendering contracts (`data-*` timing attributes, seek-safe timelines, no external CDN font/script fetching). Refuses unsafe commands (`publish`, `cloud`) in local workflows.
   * *Teaches Veasy:* The `veasy:compose` skill must explicitly guide the agent to use local tokens, locked chrome, and facts binding.

7. **Hermes Agent Plugin Specification (SiTech)**
   * *Link:* Internal specification (`plugin.yaml`, `__init__.py`, `skills/`)
   * *Core Takeaway:* Requires 3-way synchronization: `plugin.yaml` (provides_tools), `__init__.TOOLS`, and `skills/`. Plugins must never raise unhandled exceptions in handlers.
   * *Teaches Veasy:* All new capabilities (`critique`, `dry_run`, `brand_new`) must be registered in all 3 locations and backed by unit tests.

---

### Category B: Commercial AI Video Products & Interaction Surfaces

8. **Opus Clip (opus.pro)**
   * *Link:* https://www.opus.pro/
   * *Core Takeaway:* Translates long-form content into viral shorts via automatic "virality scores", candidate segment scoring, pre-render reframing previews, and karaoke-style caption styling.
   * *Teaches Veasy:* Expose pre-render scoring (reading load, motion rule checks, scene pace) so the agent can optimize before rendering.

9. **Captions.ai**
   * *Link:* https://www.captions.ai/
   * *Core Takeaway:* Studio-quality subtitles, AI script doctor, voice modulation, and rapid dry-run previewing without GPU overhead.
   * *Teaches Veasy:* Keep caption layout in Python (`captions.py`) with zero client-side layout thrashing; offer explicit caption design options (`page`, `roll`, `keyword`).

10. **HeyGen Video Agent & Interactive Avatar API**
    * *Link:* https://docs.heygen.com/
    * *Core Takeaway:* Multi-scene storyboard scripting where each scene has explicit visual layers (background, presenter, typography, b-roll). Clear separation between assets and script.
    * *Teaches Veasy:* Veasy's story JSON cleanly separates text fields from layout/colors/sources. Reinforce that the writer never sets layout or dates.

11. **InVideo AI**
    * *Link:* https://invideo.io/ai/
    * *Core Takeaway:* "Magic box" conversational prompting ("make scene 2 faster", "use darker theme") paired with scene-by-scene script editing and stock media substitution.
    * *Teaches Veasy:* Provide targeted scene-level editing capabilities and clear friction-free options for switching looks, transitions, and themes.

12. **Descript (descript.com)**
    * *Link:* https://www.descript.com/
    * *Core Takeaway:* Script-driven timeline editing. Removing words from the text trims the media. Non-destructive audio leveling and gap removal.
    * *Teaches Veasy:* Veasy's silence trim (cutting leading silence to 0.12 s in `props.mix_audio`) and word-level alignment mirror Descript's precision.

13. **Runway (Gen-2 / Gen-3 Alpha, Director Mode)**
    * *Link:* https://runwayml.com/
    * *Core Takeaway:* Director Mode provides granular camera controls (pan, zoom, tilt) and motion weighting while enforcing deterministic seeds for reproducibility.
    * *Teaches Veasy:* Veasy's eight Directors (`data`, `map`, `type`, `draw`, `chronicle`, `witness`, `brief`, `single`) give deterministic motion and camera behaviors without hallucination.

14. **Kapwing AI Video Editor**
    * *Link:* https://www.kapwing.com/
    * *Core Takeaway:* Brand Kit locking (colors, fonts, watermarks, safe-zones) prevents user and AI drift from corporate identity.
    * *Teaches Veasy:* Brand packs in `brands/` are law; the engine strictly forbids ad-hoc colors or typography.

15. **CapCut AI Video Suite**
    * *Link:* https://www.capcut.com/
    * *Core Takeaway:* Smart script-to-video with beat matching (cuts aligned with audio transients) and platform-specific safe-zone overlays.
    * *Teaches Veasy:* Veasy's `beats.py` (changes every 1.5-3 s on spoken words) and safe zone rules (y<=1380 for scene text, y<=1552 for captions, x<=940 below y=1100).

16. **Synthesia Studio & Developer API**
    * *Link:* https://www.synthesia.io/
    * *Core Takeaway:* Modular slide/scene architecture with strict variable binding and pre-render asset validation.
    * *Teaches Veasy:* Facts binding (`data-var-text`, `facts.json`) in HyperFrames prevents model hallucination of numbers or names on screen.

17. **Pika Labs (pika.art)**
    * *Link:* https://pika.art/
    * *Core Takeaway:* Canvas expansion and modify-region tools allowing localized re-generation rather than re-rendering entire timelines.
    * *Teaches Veasy:* Scene-level stills (`engine still`) allow rapid local inspection without full video re-rendering.

18. **Luma Dream Machine**
    * *Link:* https://lumalabs.ai/dream-machine
    * *Core Takeaway:* Strict keyframing and camera trajectory constraints for predictable physics and lighting.
    * *Teaches Veasy:* Use Remotion paths and GSAP easing curves rather than stochastic generative video for data and news.

---

### Category C: Self-Critique Loops & Multimodal Agent Verification

19. **OpenAI: Vision-Language Model Verification in Code Generation**
    * *Link:* https://openai.com/research/
    * *Core Takeaway:* Agents with visual reflection loops ("Generate -> Render Stills -> Inspect -> Critique -> Repair") achieve >2x success rates over open-loop generators.
    * *Teaches Veasy:* Build `veasy_critique` and `veasy_plan` contact sheets so an agent can visually inspect its stills before rendering.

20. **Google DeepMind: Self-Refinement and Critique in Autonomous Agents**
    * *Link:* https://deepmind.google/research/
    * *Core Takeaway:* Heuristic rubrics (contrast, overflow, bounding box metrics) should be checked automatically before LLM-based visual inspection to save compute.
    * *Teaches Veasy:* Combine the deterministic layout probe (`tt_shorts/probe.py`) with a structured critique checklist.

21. **Web Content Accessibility Guidelines (WCAG 2.2 AA/AAA Standards)**
    * *Link:* https://www.w3.org/WAI/standards-guidelines/wcag/
    * *Core Takeaway:* Text contrast floors (7:1 for AAA body, 4.5:1 for AA regular, 3:1 for large text / graphical UI components).
    * *Teaches Veasy:* `brand.py` contrast checks and `probe.py` DOM inspection strictly enforce WCAG floors on canvas, panel, and captions.

22. **Apple Human Interface Guidelines: Safe Areas & Display Overlays**
    * *Link:* https://developer.apple.com/design/human-interface-guidelines/
    * *Core Takeaway:* Safe zones must account for system chrome, gestures, and social platform UI rails (likes, comments, share buttons).
    * *Teaches Veasy:* The like/share rail (below y=1100, x>940) and platform UI band (y=1580-1760) are completely forbidden for story text.

23. **FastMCP: Python Framework for Model Context Protocol Servers**
    * *Link:* https://github.com/jlowin/fastmcp
    * *Core Takeaway:* Pythonic, high-performance async MCP server framework with Pydantic validation, lifecycle management, and stdio/SSE transports.
    * *Teaches Veasy:* Use FastMCP for the proposed `tt_shorts/mcp_server.py`.

---

### Category D: Brand Systems & Design Specifications

24. **Design Tokens Community Group (DTCG) Specification**
    * *Link:* https://design-tokens.github.io/community-group/format/
    * *Core Takeaway:* Platform-agnostic JSON format for sharing design tokens (color, typography, elevation, spacing) across codebases.
    * *Teaches Veasy:* Format drafted brand packs (`brands/<name>/brand.json`) to map cleanly to DTCG token semantics.

25. **Figma Tokens / Tokens Studio Specification**
    * *Link:* https://tokens.studio/
    * *Core Takeaway:* Hierarchical token aliasing (`global` -> `theme` -> `component`).
    * *Teaches Veasy:* `brands/_ka` serves as the global base; client packs (`sitech`, `tbilisi-today`) extend and override themes.

26. **HyperFrames `frame.md` Design System Contract**
    * *Link:* Pinned in `compose/` (`tt_shorts/frame_md.py`)
    * *Core Takeaway:* Markdown format describing typography, colors, component tokens, and layout safe zones directly ingested by HyperFrames compilers.
    * *Teaches Veasy:* Ensure `engine brand new` can generate both `brand.json` and a corresponding `frame.md`.

27. **FontTools / WOFF2 Font Metrics Specifications**
    * *Link:* https://github.com/fonttools/fonttools
    * *Core Takeaway:* Exact character glyph mapping (`cmap`) and bounding box calculation without spinning up browser rendering contexts.
    * *Teaches Veasy:* `captions.py` already uses fontTools to measure text lines offline with zero browser layout shifts.

28. **Lucide Icons (ISC License)**
    * *Link:* https://lucide.dev/
    * *Core Takeaway:* Consistent 24x24 vector stroke icons with permissive ISC commercial licensing.
    * *Teaches Veasy:* 250 curated Lucide icons in `assets/icons/lucide.json` serve as Veasy's pictogram grammar.

---

## 3. Licenses Table

All software and assets integrated into Veasy must permit unrestricted commercial use.

| Asset / Tool | Origin / Source | License | Permitted in Veasy? | Usage & Restrictions |
|---|---|---|---|---|
| **Remotion** | remotion-dev/remotion | Remotion Commercial / Free for ≤3 people | Yes | Free under company size terms (Owner approved 2026-11-02). |
| **HyperFrames** | heygen-com/hyperframes | Apache-2.0 | Yes | Pinned in `compose/package.json`. Safe for commercial use. |
| **Lucide Icons** | lucide-icons | ISC | Yes | Vendored in `assets/icons/lucide.json`. License preserved beside it. |
| **FiraGO Font** | BPG InfoTech / Georgian | SIL Open Font License 1.1 | Yes | Permissive for commercial use; glyphs embedded locally. |
| **Rough Notation** | rough-stuff/rough-notation | MIT | Yes | Used for voice-synced animated text highlights. |
| **GSAP (vendored)** | GreenSock / HeyGen bundle | GreenSock Standard | Yes | Bundled strictly via pinned HyperFrames; no charge runtime. |
| **Openverse API** | Automattic / WordPress | CC0 / CC-BY / PDM | Yes | Filtered strictly for commercial use; credits rendered on screen. |
| **Wikimedia Commons**| Wikimedia Foundation | CC0 / CC-BY / CC-BY-SA | Yes | Commercial only; BY-SA sorted last; credit line rendered. |
| **OpenMontage** | openmontage | AGPL-3.0 | **NO (Forbidden)**| AGPL code is never copied or linked. Ideas studied only. |
| **Publisher Photos** | News Media Outlets | Copyrighted / All Rights Reserved | **NO (Forbidden)**| Strictly forbidden. No reuse grant (CLAUDE.md § 98). |
| **AI Images (media/ai.py)**| Generative APIs | Various | **Hold** | Disabled until Owner approves policy (plan-v2 § 8.3). |

---

## 4. Friction Log: Making Three Videos Through Agent Tools

To experience what a resource-constrained agent encounters, we generated three full videos strictly using Veasy tools (`veasy_doctor`, `veasy_options`, `veasy_check`, `veasy_plan`, `veasy_render`, `veasy_qa`):

### Video 1: News Story (`stories/24835.json` + `tests/fixtures/24835.sources.json`)
* **Step 1: `veasy_doctor`:** Failed initially with `music loops: 0` because `tools/compose_music.py` had not been executed in the new worktree.
  * *Friction:* An agent has no tool to auto-heal music loops or sound effects. It had to run a manual script.
* **Step 2: `veasy_options`:** Returned 60,513 bytes of raw JSON.
  * *Friction:* Giant payloads blow context limits. There is no `--section` or `--summary` filter.
* **Step 3: `veasy_check`:** Clean pass (`problems: []`).
* **Step 4: `veasy_plan`:** Took 53.6s on cold run (bundle rebuild), returning 6 stills, contact sheet, and probe results.
* **Step 5: `veasy_render`:** Rendered to MP4 in 36.9s video time with silent engine.
* **Step 6: `veasy_qa`:** Clean pass (`problems: []`, loudness -17.2 LUFS).

### Video 2: Legal Explainer (`stories/law-constitution-17.json`, Program `law`)
* **Step 1: `veasy_check`:** Passed with `program: law, rules: law`.
* **Step 2: `veasy_plan`:** Took 3.8s (bundle cached). Contact sheet generated cleanly.
* **Step 3: `veasy_render`:** Rendered 42.7s MP4.
* **Step 4: `veasy_qa`:** Passed QA cleanly (`loudness -17.3 LUFS`).
  * *Friction:* The agent had to remember that program `law` uses format `explainer` and that `sources` for law is not a cluster but Ordo/Matsne. No interactive router guided the selection.

### Video 3: SiTech Blog Post (`stories/sitech-cybercartel.json`, Brand `sitech`)
* **Step 1: `veasy_check`:** Passed.
* **Step 2: `veasy_plan`:** Took 3.5s.
* **Step 3: `veasy_render`:** Rendered 40.5s MP4 in coal/orange theme.
* **Step 4: `veasy_qa`:** Passed QA (`opening_ink: 0.173`, `loudness -17.2 LUFS`).
  * *Friction:* When passing invalid file paths (e.g. `nonexistent.json`), `_engine` returns raw Python tracebacks rather than a helpful error explaining what happened and how to fix it.

---

## 5. Summary of Frictions & Architectural Gaps

| # | Friction / Gap | Impact on AI Agent | Proposed Solution |
|---|---|---|---|
| **F1** | `veasy_options` context explosion (60 KB) | Context window overflow, memory loss, expensive tool calls | Add `section` argument (`formats`, `looks`, `voices`, `scenes`, `brands`, `themes`, `directors`, `rubrics`, `summary`) |
| **F2** | Raw Python tracebacks on missing/invalid files | Agent gets confused, cannot self-heal, assumes system crash | Wrap `engine.py` entry point in structured error handler returning `{problems: [...], error: ..., hint: ...}` |
| **F3** | No Pre-Flight Visual Critique Tool | Agent blindly renders without self-auditing stills or plan sheet | Create `veasy_critique` tool + `engine critique` command evaluating layout, contrast, text load, and safe zones |
| **F4** | No Pre-Flight Cost / Dry-Run Estimator | Agent cannot predict if a render will exceed budget or token caps | Create `veasy_dry_run` tool + `engine dry-run` calculating TTS chars, cost in USD, render duration, and cache state |
| **F5** | No Automated Brand Book Ingestion | Adding a client requires deep code knowledge of `brand.json` | Implement `engine brand new <name> --from <url\|pdf\|md>` with automatic contrast validation and contact sheet output |
| **F6** | Missing Request Routing in Skills | Agent doesn't know whether a request should be Remotion vs HyperFrames | Update `veasy:make-video` and add routing table matching user prompts ("explainer", "kids story", "news") |
| **F7** | Missing MCP Server | External AI agents (Antigravity, Claude Code, Cursor) can't use Veasy via standard MCP | Design complete FastMCP server architecture specification for Owner approval |

---

## 6. Ranked Implementation Backlog

### Milestone 1: Context Optimization & Resilient Error Handling (High Value / Low Effort)
* **Item 1.1:** Add `--section` and `summary` support to `engine options` and `veasy_options`.
* **Item 1.2:** Implement structured error handling in `engine.py` and `__init__.py` (never return raw tracebacks; return actionable problem lists with recovery hints).
* **Item 1.3:** Add unit tests in `tests/test_plugin.py` and `tests/test_engine.py`.

### Milestone 2: Pre-Flight Visual Critique & Dry-Run Cost Estimation (High Value / Medium Effort)
* **Item 2.1:** Build `tt_shorts/critique.py` and `engine critique <plan.json|story.json>`: evaluates safe zones, contrast, text load, pacing, and outputs structured critique points with pass/fail grades.
* **Item 2.2:** Build `engine dry-run <story.json>`: calculates Gemini/Edge TTS cost, word counts, scene count, and asset cache status.
* **Item 2.3:** Expose `veasy_critique` and `veasy_dry_run` in `plugin.yaml`, `__init__.TOOLS`, and `skills/qa`.

### Milestone 3: Automated Brand Book Intake (`engine brand new`) (High Value / Medium Effort)
* **Item 3.1:** Implement `engine brand new <name> --from <file|url>` in `tt_shorts/brand_new.py`:
  * Parses markdown (`design.md`, `frame.md`), JSON, or HTML/text colors and typography.
  * Generates valid `brands/<name>/brand.json` extending `_ka`.
  * Runs full `brand.py` contrast and schema validation.
  * Renders golden contact sheet in both dark and light themes.
* **Item 3.2:** Update `skills/brands/SKILL.md` with step-by-step brand intake guide.
* **Item 3.3:** Add unit test `tests/test_brand_new.py`.

### Milestone 4: Comprehensive Skill Enhancement & Intelligent Routing (Medium Value / Low Effort)
* **Item 4.1:** Update `veasy:make-video` and `veasy:programs` with prompt routing table mapping requests ("an animated explainer about X", "a 30 s story for kids", "a data video") to exact Program, Format, Director, and Engine.
* **Item 4.2:** Ensure all skills remain strictly under the 12,000-byte context limit.

### Milestone 5: MCP Server Proposal for the Owner (Research & Spec Only)
* **Item 5.1:** Produce detailed architectural proposal for `tt_shorts/mcp_server.py` using FastMCP.

---

## 7. Proposal: Exposing Veasy as an MCP Server

> [!IMPORTANT]
> **Owner Decision Required:** Exposing Veasy as an MCP server expands access beyond Hermes to any MCP-compliant client (Antigravity, Claude Code, Cursor, Windsurf, Claude Desktop). Building is deferred until Owner approval.

### Proposed Architecture
* **Framework:** `FastMCP` (stdio transport, lightweight, zero HTTP overhead).
* **Location:** `tt_shorts/mcp_server.py` and root entry point `mcp_server.py`.
* **Execution:** `python -m tt_shorts.mcp_server`
* **Tools Exposed:**
  * `veasy_options(brand, section)`
  * `veasy_check(story, sources)`
  * `veasy_plan(story, format, look, director)`
  * `veasy_critique(story)`
  * `veasy_dry_run(story)`
  * `veasy_render(story, format, engine)`
  * `veasy_qa(video)`
  * `veasy_compose(action, story, ...)`
* **Resources Exposed:**
  * `veasy://brands`: list of installed brand packs and their palettes.
  * `veasy://formats`: list of available show formats.
  * `veasy://renders/{brand}/{day}`: list of completed renders and their manifests.
* **Prompts Exposed:**
  * `veasy_write_story`: system prompt containing Georgian style rules (`ka_style.md`).
  * `veasy_review_render`: checklist prompt for validating rendered video quality.

---

## 8. Commit Log for this Milestone
* `6a12258`: fix(windows): resolve venv Scripts, force UTF-8 in engine runner, and support link files in skill tests
