# Veasy Tooling & Agent Experience Result Report

**Date:** November 2026  
**Worktree:** `D:\MyStaff\Veasy-tooling`  
**Branch:** `goal/tooling`  
**Base Commit:** `3a6ce8a`  

---

## 1. Executive Summary

This goal transformed Veasy into an autonomous, discoverable, and error-resilient video production instrument for AI agents. By benchmarking leading AI video creation platforms (Opus Clip, Captions, HeyGen, Descript, InVideo, Runway) and agent developer standards (Anthropic Skills, Model Context Protocol, OpenAI/Google Tool Design), we identified key cognitive friction points that cheap or constrained language models face when operating Veasy.

We implemented and verified all six planned milestones without modifying `main` or breaking existing contracts:
1. **Windows Baseline & Cross-Platform Stability:** Eliminated the 3 Windows-specific unittest failures (`charmap` encoding errors in engine subprocesses, venv path resolution for `Scripts/python.exe`, and git text link references in `.claude/skills`).
2. **Comprehensive Research Survey:** Authored `docs/research/tooling.md` surveying 28 industry sources, establishing a commercial license catalog, and architecting an MCP server proposal.
3. **Progressive Capability Discovery & Resilient Errors:** Added `--section` and `summary` support to `veasy_options` (reducing context payload from ~65 KB to ~1 KB), and wrapped engine entry points with structured JSON diagnostic hints.
4. **Pre-Flight Visual Critique & Dry-Run Cost Estimation:** Built `veasy_critique` (`tt_shorts/critique.py`) for automated visual heuristics (safe zones, reading load pacing, stillness detection, variety rules, WCAG contrast) and `veasy_dry_run` (`tt_shorts/dry_run.py`) for $0.00 pre-render financial and resource checks.
5. **Automated Brand Book Ingestion:** Implemented `engine brand new` / `veasy_brand` (`tt_shorts/brand_new.py`), allowing agents to ingest brand specs from URLs, PDFs, or markdown briefs (`brand.md`, `design.md`), self-heal WCAG contrast ratios, and generate dark/light theme contact sheets.
6. **Intent-to-Pipeline Prompt Routing:** Added explicit routing tables to `skills/make-video/SKILL.md` and `skills/programs/SKILL.md` mapping ambiguous agent prompts to exact programs, formats, directors, and engines while staying strictly under the 12,000-byte skill context budget.

All 590 test cases in the test suite pass cleanly, Remotion TypeScript compilation passes without errors (`tsc --noEmit` exit code 0), and all three representative video genres (news, law/explainer, tech blog) were successfully verified end-to-end.

---

## 2. Commit List (What Shipped)

The following commits form the complete, atomic delivery on branch `goal/tooling`:

1. **`6a12258`** — `fix(windows): resolve venv Scripts, force UTF-8 in engine runner, and support link files in skill tests`
   - Updated `_python()` in `__init__.py` to check `Scripts/python.exe` and traverse worktree parent paths.
   - Updated `_engine()` in `__init__.py` to inject `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` into subprocess environments and read with `encoding="utf-8"`, eliminating Windows `charmap` Unicode crashes on Georgian text.
   - Updated `test_claude_code_sees_the_same_skills` in `tests/test_plugin.py` to resolve text file link references created on Windows when `core.symlinks=false`.

2. **`06ef8f5`** — `docs(research): tooling, skills, critique loops, and agent architecture survey`
   - Detailed survey of 28 authoritative references across agent tool design, MCP specifications, commercial video pipelines, and visual self-critique loops.
   - Commercial license verification table confirming all vendored and referenced tools are MIT, Apache-2.0, BSD-3, or CC-BY-4.0.
   - Detailed friction log from end-to-end agent trial runs.
   - Value-effort ranked engineering backlog.
   - Complete architectural proposal for a standalone `veasy-mcp` server.

3. **`eea3015`** — `feat(tooling): add section filtering for options and resilient structured error reporting`
   - Extended `engine.options(brand, section)` and `engine options --section <name>` to support `summary`, `formats`, `looks`, `voices`, `themes`, `directors`, `programs`, `rubrics`, `scenes`, and `categories`.
   - Updated `veasy_options` schema in `__init__.py` and documentation in `skills/formats/SKILL.md`.
   - Intercepted `FileNotFoundError`, `JSONDecodeError`, and `BrandError` in `tt_shorts/engine.py:main` to return structured JSON diagnostics with hints rather than dumping raw Python tracebacks.
   - Added unit tests in `tests/test_engine.py` and `tests/test_plugin.py`.

4. **`1e15e71`** — `feat(tooling): add pre-flight visual critique and dry-run cost estimation tools`
   - Created `tt_shorts/critique.py` (`engine critique` / `veasy_critique`): evaluates safe zone violations, reading load / words-per-second pacing, stillness stretches (>3s), variety violations, hook visual presence, and contrast floors. Generates 0-100 score, PASS/NEEDS_ATTENTION/FAIL grade, and contact sheet path.
   - Created `tt_shorts/dry_run.py` (`engine dry-run` / `veasy_dry_run`): $0.00 zero-compute cost estimator calculating narration word counts, TTS token expenditure, estimated duration, cache readiness, and budget limits.
   - Fixed Windows UTF-8 decoding in `tt_shorts/probe.py:run_jobs` (`encoding="utf-8"`).
   - Registered `veasy_critique` and `veasy_dry_run` across `plugin.yaml`, `__init__.py`, `skills/qa/SKILL.md`, and `skills/make-video/SKILL.md`.
   - Added unit tests in `tests/test_critique.py` and `tests/test_plugin.py`.

5. **`2fe26e4`** — `feat(tooling): automated brand book ingestion and preview generation`
   - Implemented `tt_shorts/brand_new.py` (`engine brand new <name> --from <source>` / `veasy_brand`): ingests URLs, markdown brand specs (`brand.md`, `design.md`), or JSON data; extracts color palettes; self-heals WCAG contrast ratios against `brand.CONTRAST` floors (ink 7:1, muted 4.5:1, button on accent 3:1, waiting captions 3:1); drafts `brands/<name>/brand.json` extending `_ka`; renders contact sheets in both dark and light themes.
   - Registered `veasy_brand` in `plugin.yaml`, `__init__.py`, and `skills/brands/SKILL.md`.
   - Added comprehensive test coverage in `tests/test_brand_new.py`.

6. **`8393e0c`** — `docs(skills): add explicit prompt routing tables for agent discoverability`
   - Added comprehensive intent-to-option routing tables in `skills/make-video/SKILL.md` and `skills/programs/SKILL.md` mapping ambiguous agent prompts ("an animated explainer about X", "a 30 s story for kids", "a data video", "article 17 of Constitution", "SiTech blog post") to program, format, director/look, and engine (`remotion` vs `hyperframes`).
   - Kept all skills strictly under the 12,000-byte context budget limit.

---

## 3. End-to-End Video Verification

To ensure an agent can produce videos strictly through the tool interface without reading engine internals or guessing parameters, three distinct genres were planned, rendered, and verified:

1. **Multi-Outlet News Story:**
   - **Story:** `stories/24835.json` (Source: `tests/fixtures/24835.sources.json`)
   - **Render Command:** `engine render stories/24835.json --format news --look cards --captions page --engine silent`
   - **Output:** `renders/tbilisi-today/2026-10-31/24835-news-cards-page.mp4`
   - **QA Evaluation:** Score 100/100, PASS. Integrated loudness: -17.2 LUFS. Safe zone clean.
2. **Legal / Constitutional Explainer:**
   - **Story:** `stories/law-constitution-17.json` (Source: `tests/fixtures/law-constitution-17.sources.json`)
   - **Render Command:** `engine render stories/law-constitution-17.json --format explainer --look editorial --captions page --engine silent`
   - **Output:** `renders/tbilisi-today/2026-10-31/constitution-17-explainer-editorial-page.mp4`
   - **QA Evaluation:** Score 100/100, PASS. Integrated loudness: -17.3 LUFS. Safe zone clean.
3. **SiTech Technology Blog Post:**
   - **Story:** `stories/sitech-cybercartel.json`
   - **Render Command:** `engine render stories/sitech-cybercartel.json --brand sitech --format news --look editorial --captions page --engine silent`
   - **Output:** `renders/sitech/2026-10-31/claude-and-grok-among-ai-agents-used-to-automate-attacks-on-lati-news-editorial-page.mp4`
   - **QA Evaluation:** Score 100/100, PASS. Integrated loudness: -17.2 LUFS. Safe zone clean.

---

## 4. Files Touched & Potential Overlaps with Other Goals

Four other agents are working concurrently on other goals. Here is the exact breakdown of files modified in `goal/tooling` and how other goals interact with them:

| File | Changes Made | Potential Overlap with Other Goals | Merge Guidance |
|---|---|---|---|
| `__init__.py` | Added tools `veasy_critique`, `veasy_dry_run`, `veasy_brand`; added `section` param to `veasy_options`; fixed `_python()` venv paths & `_engine()` UTF-8. | Other goals may add tool definitions if exposing new scene types or composables. | Purely additive in `TOOLS` dictionary. Merge cleanly by unioning tool dict keys. |
| `plugin.yaml` | Registered `veasy_critique`, `veasy_dry_run`, `veasy_brand`, and updated `veasy_options` parameter schema. | Other goals may register new tool names in `provides_tools`. | Purely additive list. Union lines in `provides_tools`. |
| `tt_shorts/engine.py` | Added subcommands `brand`, `critique`, `dry-run`; added `--section` to `options`; added structured JSON error handling in `main()`. | Goal 1 (scenes) or Goal 3 (motion) may add CLI flags to `options` or `render`. | Subparser definitions are modular; `main()` error wrappers wrap cleanly around subcommands. |
| `tt_shorts/probe.py` | Added `encoding="utf-8"` in `subprocess.run(["node", "probe.mjs"], ...)` (line 246). | Goal 3 or Goal 4 might adjust probe layout bounds. | Single-line bugfix preventing Windows Unicode crashes. Keep `encoding="utf-8"`. |
| `skills/brands/SKILL.md` | Documented `veasy_brand` and `engine brand new`. | Unlikely to be touched by others. | Keep tooling version. |
| `skills/formats/SKILL.md` | Documented `veasy_options` section filtering. | Goal 1 or Goal 3 may document new formats or looks. | Merge additions. |
| `skills/make-video/SKILL.md` | Added prompt routing table and critique/dry-run workflow steps. | All goals may reference their capabilities here. | Additive table rows. |
| `skills/programs/SKILL.md` | Added prompt routing quick-reference. | Unlikely to conflict. | Additive section. |
| `skills/qa/SKILL.md` | Documented `veasy_critique` pre-flight inspection. | Goal 3 might add motion rule QA steps. | Additive section. |
| `tt_shorts/brand_new.py` | **New file** (brand book ingestion engine). | None (new module). | No conflict. |
| `tt_shorts/critique.py` | **New file** (pre-flight visual heuristic checker). | None (new module). | No conflict. |
| `tt_shorts/dry_run.py` | **New file** (pre-render resource estimator). | None (new module). | No conflict. |
| `tests/test_brand_new.py` | **New file** (unit tests for `brand_new.py`). | None (new module). | No conflict. |
| `tests/test_critique.py` | **New file** (unit tests for critique and dry-run). | None (new module). | No conflict. |
| `tests/test_engine.py` | Added tests for `options --section` and structured error handling. | Additive tests. | Union test methods. |
| `tests/test_plugin.py` | Added tests for Windows symlinks, critique, dry-run, and options sectioning. | Other goals might add tests for their own tools. | Union test methods. |

---

## 5. What Was Not Done & Why

1. **Standalone MCP Server Implementation (`veasy-mcp`):**
   - *Why not done:* The brief explicitly instructed: *"Research only, then a proposal for the owner (don't build without the owner's OK): exposing Veasy as an MCP server so any AI client (Antigravity, Claude Code and others) can use it, not only Hermes."*
   - *Status:* Comprehensive architecture, tool mapping, transport design, and security model specified in `docs/research/tooling.md` § 7, ready for owner authorization.
2. **Creating New Scene Types or Animation Presets:**
   - *Why not done:* Reserved for Goal 1 (Scene Types) and Goal 3 (Motion Options). Our charter was strictly tooling, discoverability, error handling, and agent UX.
3. **Creating HyperFrames Block Templates:**
   - *Why not done:* Reserved for Goal 4 (HyperFrames Lane).
4. **Third-Party Stock Imagery / Paid Model Integration:**
   - *Why not done:* Strictly prohibited by ground rules (`ai.py` remains disabled, zero network calls in tests, $0.00 compute gate).

---

## 6. Open Owner Decisions

The following items are strategic product decisions documented during research and implementation that require the repository owner's explicit direction:

1. **MCP Server Authorization (`veasy-mcp`):**
   - *Decision:* Should Veasy expose a native `python -m tt_shorts.mcp` server using `mcp.server.fastmcp` (stdio and SSE transports)?
   - *Context:* This would enable any external agent (Antigravity IDE, Claude Desktop, Cursor, OpenMontage) to plan, critique, dry-run, and render Veasy videos using standard MCP tool calling without requiring Hermes.
   - *Recommendation:* Authorize building `tt_shorts/mcp.py` as an optional add-on package in the next sprint.
2. **Brand Ingestion Tint Keyword Style (`design.keyword = "tint"`):**
   - *Decision:* Should newly ingested brands default to `design.keyword = "underline"` or `"block"` rather than `"tint"` when the brand accent does not meet 4.5:1 contrast against the background?
   - *Context:* Under WCAG rules enforced by `brand.py:325`, if an accent has low contrast with canvas, applying `"tint"` (which colors words with the accent) violates contrast floors.
   - *Recommendation:* Keep `underline` as the safe default for auto-ingested brands whose accents are saturated (e.g. orange, cyan, yellow).
3. **Automated Critique Thresholds for Unattended Publishing:**
   - *Decision:* Should the production queue automatically reject jobs with a critique score below 85, or hold them for human review?
   - *Recommendation:* Hold jobs with scores between 70 and 89 for human review (`error_class: review`), and reject jobs below 70 (`error_class: critique_fail`).

---

## 7. Verification Gates Sign-Off

Before concluding, all quality gates were re-executed and verified green on Windows pwsh in worktree `D:\MyStaff\Veasy-tooling`:
- `D:\MyStaff\Veasy\.venv\Scripts\python.exe -m unittest discover -s tests`: **590 tests passed** (4 skipped, 0 failures, 0 errors).
- `(cd remotion && npx tsc --noEmit)`: **Clean compilation, exit code 0**.
- Git worktree status: Clean, on branch `goal/tooling`, zero uncommitted files, zero changes to `main`.
