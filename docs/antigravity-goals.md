# Veasy: five long goals for Antigravity agents

Written 2026-11-03. Each block below is one self-contained prompt for one agent (`/goal`). Paste the whole block,
from `GOAL` to the end of its fence. The five run side by side: each works in its own git worktree and branch, so
they never write into the same checkout, and nothing reaches `main` until the owner merges it.

| # | Lane | Branch | Owns |
|---|---|---|---|
| 1 | New scene types | `goal/scenes` | `brushes/`, `remotion/src/scenes/`, scene demo stories |
| 2 | Icons, pictograms, drawings | `goal/icons` | `icons.py`, `assets/icons/`, `assets/drawings/`, `remotion/src/icons.tsx` |
| 3 | Motion, typography, transitions | `goal/motion` | `variety.py` options, `ui.tsx`, `motion_rules.py`, directors' motion |
| 4 | Composed films and templates (HyperFrames) | `goal/compose` | `compose/`, `tt_shorts/compose.py`, `templates/` |
| 5 | Veasy as an AI's instrument | `goal/tooling` | `plugin.yaml`, `__init__.py`, `skills/`, agent-facing `engine` commands |
| 6 | Styles, from Lemo-Opuscar ([lemo-opuscar.md](lemo-opuscar.md)) | `goal/styles` | `styles/`, `tt_shorts/styles.py`, the sampler |
| 7 | One front door (after 1-6 are merged) | `goal/frontdoor` | `engine make`, `engine options`, `veasy:make-video`, the gallery |

Merge order afterwards: 5 (it fixes the Windows test baseline), then 2, 3, 1, 4, 6; goal 7 starts after that.

---

## GOAL 1: New scene types

```text
GOAL: Grow Veasy's scene library: research how the best explainer and news-graphics makers turn facts into
vertical motion, then add at least 8 new, fully wired scene types (brushes) that let an AI make many more kinds
of animated videos, each one tested, demoed and checked in every look.

## Ground rules (shared by all five Veasy goals)
- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, docs/plan-v2.md, ROADMAP.md,
  docs/next.md. CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- Four other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch:
  `git worktree add ..\Veasy-scenes -b goal/scenes main`, and stay inside it. Never commit to main, never push,
  never merge, never rewrite history. Before you finish, rebase onto the latest local main and stay green.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set
  PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). In your
  worktree run `npm ci` in remotion/ (and in compose/ if you touch it).
- Baseline: 3 tests in tests/test_plugin.py fail on Windows only (skill symlinks, the charmap error). Note them,
  don't count them against you; goal 5 fixes them.
- Gates for every commit: `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. For any
  visual change also `python -m tt_shorts.engine selftest` and `python -m tt_shorts.engine probe <story> --look all`,
  then open the stills and look at them yourself. `selftest --update` only for a change you meant, committed with it.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); news rules (tt_shorts/ka_style.md § N,
  news_check.py) only ever get stricter, never an opinion scene; the writer fills only text fields, layout, motion,
  date, sources, QR and colours are code; variety grows by adding options, never by replacing them; text on screen
  is Georgian, code, comments and commits are English.
- Money, servers, secrets: no paid API calls (TTS voices, image models, keyed stock APIs): use the fixtures and the
  free preview paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server
  84.46.250.149, cron or timers. Never read, print or copy data/.env.
- Licences: only what allows commercial use; record the source and licence beside every vendored file (like
  assets/icons/LICENSE). No GPL/AGPL code (OpenMontage is AGPL: study it, don't copy it). No AI-generated imagery
  (tt_shorts/media/ai.py stays off). No publisher photos. From other projects take ideas, not code, unless the
  licence is MIT, ISC, Apache-2.0 or BSD and you credit it.
- Way of working: research first, then write docs/research/scenes.md (what you studied, with links; what each
  teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it before building. Then build
  the backlog top-down in small, complete increments: each is code + its test + its skill and `engine options`
  entry + stills checked + one commit with a clear message. Ten finished things beat thirty half-finished ones.
  When something is the owner's call (brand, news rules, licences, money), write it under "Owner decisions" in
  your report and move to the next item. Never guess on those.
- Finish with docs/research/scenes-result.md: what shipped (the commit list), the paths of before/after stills,
  what you didn't do and why, the open owner decisions, and the files you touched that other goals may also touch.

## Your lane: scene types
You own brushes/, remotion/src/scenes/, the scene part of remotion/src/types.ts and new demo stories. Other
goals own icons (goal 2), motion/transitions/variety options (goal 3), HyperFrames (goal 4), and plugin tools and
skill structure (goal 5): touch their files only additively, and list each such touch in your result.

### Research (aim for 25+ real sources, each with a note on what Veasy can take)
- Visual journalism and explainers: Reuters Graphics, NYT, BBC visual journalism, Bloomberg, The Economist's
  short videos, Vox, Kurzgesagt, AJ+, NowThis, Axios ("smart brevity"), The Pudding, the FT Visual Vocabulary
  (map every one of its chart families to a data shape a story can carry), Datawrapper's and Flourish's chart
  types, Isotype (Otto Neurath).
- Vertical news Shorts and Reels from outlets that do it well: how many beats per scene, how numbers are shown,
  how comparisons, places, people, quotes, sequences and deadlines are drawn.
- Remotion's showcase and templates (remotion.dev), Motion Canvas and Revideo examples: scene structure only.
- What Veasy already has: read every brush in brushes/, tt_shorts/catalog.py's docstring, remotion/src/scenes/,
  the directors in directors/, the programs in programs/, the stories in stories/. Don't propose what exists.

### Build (the recipe is CLAUDE.md, "A new scene type": follow it in that order for every scene)
- At least 8 new scene types chosen from your ranked backlog. Candidates to weigh (not a list to copy): ranking,
  part-of-whole (waffle or bar of 100), before/after, countdown or deadline, calendar of dates, route or movement on
  the map, process flow, budget breakdown, two-number versus, glossary card (explain one term), checklist of facts
  (facts, never advice or opinion), a "what changes for you" card. Prefer scenes that open new kinds of video
  (explainers, law, blog, story programs), not only news.
- For each: brushes/<type>.json with `order` in the range 160-299 (other goals don't add brushes), slots with
  Georgian length limits, `em` fields, family gates (crime, incidents and deaths get no imagery and no icons), a
  real Georgian `example`; news_check.SCENE_TYPES, with a rule in engine.shape_problems or news_check for anything
  the slots can't express, and its test; the Remotion component with `marked(...)` for each em field and
  `data-probe` regions; the write-script skill's table; a demo story in stories/; `engine probe --look all` and
  the stills, inside the safe zone in every look and both themes.
- Give the new scenes a home: add them, with weights, to the directors and programs they suit (additively), so the
  writer actually reaches them. tests/test_catalog.py, test_scenes.py and test_engine.py must stay green.
- Done when: 8+ new scenes pass every gate, each has a demo story and stills you have looked at, at least three
  directors and two non-news programs can use them, and the result report is written.
```

---

## GOAL 2: Icons, animated pictograms and drawings

```text
GOAL: Make Veasy's visual vocabulary much richer: research icon systems, pictogram traditions and SVG animation
techniques, then grow Veasy's icons, animated pictograms and seed drawings so an AI can illustrate almost any
story with consistent, licensed, moving SVG, never breaking the brand pack or news rule N10.

## Ground rules (shared by all five Veasy goals)
- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, docs/plan-v2.md, ROADMAP.md,
  docs/next.md. CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- Four other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch:
  `git worktree add ..\Veasy-icons -b goal/icons main`, and stay inside it. Never commit to main, never push,
  never merge, never rewrite history. Before you finish, rebase onto the latest local main and stay green.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set
  PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). In your
  worktree run `npm ci` in remotion/ (and in compose/ if you touch it).
- Baseline: 3 tests in tests/test_plugin.py fail on Windows only (skill symlinks, the charmap error). Note them,
  don't count them against you; goal 5 fixes them.
- Gates for every commit: `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. For any
  visual change also `python -m tt_shorts.engine selftest` and `python -m tt_shorts.engine probe <story> --look all`,
  then open the stills and look at them yourself. `selftest --update` only for a change you meant, committed with it.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); news rules (tt_shorts/ka_style.md § N,
  news_check.py) only ever get stricter, never an opinion scene; the writer fills only text fields, layout, motion,
  date, sources, QR and colours are code; variety grows by adding options, never by replacing them; text on screen
  is Georgian, code, comments and commits are English.
- Money, servers, secrets: no paid API calls (TTS voices, image models, keyed stock APIs): use the fixtures and the
  free preview paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server
  84.46.250.149, cron or timers. Never read, print or copy data/.env.
- Licences: only what allows commercial use; record the source and licence beside every vendored file (like
  assets/icons/LICENSE). No GPL/AGPL code (OpenMontage is AGPL: study it, don't copy it). No AI-generated imagery
  (tt_shorts/media/ai.py stays off). No publisher photos. From other projects take ideas, not code, unless the
  licence is MIT, ISC, Apache-2.0 or BSD and you credit it.
- Way of working: research first, then write docs/research/icons.md (what you studied, with links; what each
  teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it before building. Then build
  the backlog top-down in small, complete increments: each is code + its test + its skill and `engine options`
  entry + stills checked + one commit with a clear message. Ten finished things beat thirty half-finished ones.
  When something is the owner's call (brand, news rules, licences, money), write it under "Owner decisions" in
  your report and move to the next item. Never guess on those.
- Finish with docs/research/icons-result.md: what shipped (the commit list), the paths of before/after stills,
  what you didn't do and why, the open owner decisions, and the files you touched that other goals may also touch.

## Your lane: icons, pictograms, drawings
You own tt_shorts/icons.py, tools/build_icons.py, assets/icons/, assets/drawings/, tt_shorts/drawings.py,
tt_shorts/art.py and remotion/src/icons.tsx. Other goals own scene types (goal 1), general motion and variety
options (goal 3), HyperFrames (goal 4), and plugin tools and skill structure (goal 5): touch their files only
additively, and list each such touch in your result.

### Research (aim for 25+ real sources, each with a note and its exact licence)
- Icon sets: Lucide (in use, ISC), Tabler, Phosphor, Iconoir, Heroicons, Material Symbols, Remix Icon, Fluent UI
  icons, Noto Emoji, OpenMoji (CC BY-SA: share-alike, flag it), Streamline's free sets (check the terms). Judge
  stroke style, grid, coverage for news, civic, transport, money, health, weather, law and tech topics.
- Pictogram traditions: Isotype (Neurath, Arntz), the AIGA/DOT symbol signs (public domain), ISO 7001, Olympic
  pictograms, Otl Aicher: what makes a sign readable in 0.5 s on a phone.
- SVG animation: stroke draw-on (dash offset), path morphing (flubber, MIT), rough.js sketch style (MIT),
  @remotion/paths and @remotion/shapes, Lottie and dotLottie with @remotion/lottie, useAnimations, Lordicon (read
  its licence carefully), SVGator and LottieFiles (licence per file). Decide what fits Remotion's frame-exact model
  and Veasy's "icons drawn in ink, accent only on the dot".
- What Veasy already has: icons.py (_BY_ICON, _BLOCK, find), the sign scene, isotype counts on stat, the icons
  motif, assets/drawings and art.py's sanitize and quality, news rule N10.

### Build
- More coverage: at least 60 new Georgian stems in icons._BY_ICON (and look-alikes in _BLOCK), each with a case in
  tests/test_icons.py; extend tools/build_icons.py (the only way assets/icons is built) if a second set is worth it,
  but one stroke style per video: never mix sets in one film.
- An icon motion vocabulary as code-owned options (draw-on, pop, pulse, count-up isotype, morph from one icon to
  another, sketch), each added beside the existing ones and chosen by variety, never the only option; frame-exact
  and deterministic; the accent only on the dot.
- Isotype and pictogram charts that scenes can use (people counts, part-of-whole, unit charts), with N10: a sign's
  verb is said in its part of the narration; no pictograms for crime, incidents or deaths.
- At least 25 new seed drawings in assets/drawings/ for common topics, each passing art.py (sanitize + quality) and
  tests/test_drawings.py, so a failing writer drawing has a library fallback for more motifs.
- A contact-sheet command or tool output that renders every icon and drawing in every theme, so an agent or the
  owner can review the library at a glance (coordinate the command name in your result for goal 5).
- Done when: the new stems, motions, charts and drawings pass every gate; a demo story uses the new motions in
  every look; the contact sheet exists and you have looked at it; the result report is written. Tints (plan-v2
  § 8.2) are an owner decision: don't add them.
```

---

## GOAL 3: Motion, kinetic typography and transitions

```text
GOAL: Give Veasy a far wider motion language: research motion design, kinetic typography and the animation
toolkits around Remotion, then add many new hook layouts, background motifs, entrances, transitions and motion
personalities as new variety options, plus motion rules that keep everything readable, so 1000 videos never look
alike.

## Ground rules (shared by all five Veasy goals)
- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, docs/plan-v2.md, ROADMAP.md,
  docs/next.md. CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- Four other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch:
  `git worktree add ..\Veasy-motion -b goal/motion main`, and stay inside it. Never commit to main, never push,
  never merge, never rewrite history. Before you finish, rebase onto the latest local main and stay green.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set
  PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). In your
  worktree run `npm ci` in remotion/ (and in compose/ if you touch it).
- Baseline: 3 tests in tests/test_plugin.py fail on Windows only (skill symlinks, the charmap error). Note them,
  don't count them against you; goal 5 fixes them.
- Gates for every commit: `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. For any
  visual change also `python -m tt_shorts.engine selftest` and `python -m tt_shorts.engine probe <story> --look all`,
  then open the stills and look at them yourself. `selftest --update` only for a change you meant, committed with it.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); news rules (tt_shorts/ka_style.md § N,
  news_check.py) only ever get stricter, never an opinion scene; the writer fills only text fields, layout, motion,
  date, sources, QR and colours are code; variety grows by adding options, never by replacing them; text on screen
  is Georgian, code, comments and commits are English.
- Money, servers, secrets: no paid API calls (TTS voices, image models, keyed stock APIs): use the fixtures and the
  free preview paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server
  84.46.250.149, cron or timers. Never read, print or copy data/.env.
- Licences: only what allows commercial use; record the source and licence beside every vendored file (like
  assets/icons/LICENSE). No GPL/AGPL code (OpenMontage is AGPL: study it, don't copy it). No AI-generated imagery
  (tt_shorts/media/ai.py stays off). No publisher photos. From other projects take ideas, not code, unless the
  licence is MIT, ISC, Apache-2.0 or BSD and you credit it.
- Way of working: research first, then write docs/research/motion.md (what you studied, with links; what each
  teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it before building. Then build
  the backlog top-down in small, complete increments: each is code + its test + its skill and `engine options`
  entry + stills checked + one commit with a clear message. Ten finished things beat thirty half-finished ones.
  When something is the owner's call (brand, news rules, licences, money), write it under "Owner decisions" in
  your report and move to the next item. Never guess on those.
- Finish with docs/research/motion-result.md: what shipped (the commit list), the paths of before/after stills,
  what you didn't do and why, the open owner decisions, and the files you touched that other goals may also touch.

## Your lane: motion
You own tt_shorts/variety.py's option pools (OPTIONS, TRANSITIONS), remotion/src/ui.tsx and the motion parts of
NewsShort.tsx and Slide.tsx, tt_shorts/motion_rules.py, the directors' motion personalities, and sound-effect cues
tied to motion (tt_shorts/sfx.py, tools/compose_sfx.py). Other goals own scene types (goal 1), icons and their
motions (goal 2), HyperFrames (goal 4), and plugin tools and skill structure (goal 5): touch their files only
additively, and list each such touch in your result.

### Research (aim for 25+ real sources, each with a note on what Veasy can take)
- Motion principles: the 12 principles of animation, Material motion, IBM Carbon motion, Apple's HIG on motion,
  easing and spring theory (what Remotion's spring() numbers mean), readability on phones (the 0.5 s + 0.3 s a word
  rule Veasy already has), attention in the first 1-2 s of a Short.
- Kinetic typography: title sequences, lyric videos, news-show openers; how Georgian (Mkhedruli, no capitals,
  long words) changes what works.
- Toolkits: Remotion's own packages (@remotion/transitions, paths, shapes, noise, motion-blur, layout-utils,
  animation-utils, lottie) at the pinned version 4.0.539, Motion Canvas and Revideo (MIT), Manim's ideas, Theatre.js,
  GSAP (for what goal 4 can do in HyperFrames), Rive. Licences: Remotion's packages follow Remotion's licence
  (the owner's decision is in ROADMAP: free up to 3 people).
- What Veasy already has: variety.OPTIONS (hook: stack, lead, blocks, underline; motif: grid, diagonal, dots, rules,
  plain, icons; enter: rise, slide, reveal, scale), TRANSITIONS per look (editorial, kinetic, cards), the meter wipe,
  beats inside scenes, the chapter bar, keyword captions, the directors' motion numbers, motion_rules.py.

### Build
- New options inside the existing fields: at least 4 hook layouts, 4 background motifs (texture and motion only,
  in ink: no new colours, no shadows), 4 entrances and 6 transitions, spread over the looks. Each is one more option
  in variety (never a replacement), drawn in Remotion, frame-exact and deterministic, inside the safe zone, and
  covered by tests/test_variety.py's even-use check and the novelty guard. A new variety field changes the
  fingerprint (FIELDS, distance = 1 - similarity / 7): only with a written reason in your research doc and the
  fingerprint tests updated on purpose.
- Kinetic type for Georgian: word-by-word and line-by-line reveals, mask reveals, emphasis on `em` words, all reading
  colours from brand.ts inside components (applyBrand), never at module level.
- New motion personalities for the directors (spring numbers, enter and stagger frames, the "current") so each
  director moves differently; documented in the directors skill.
- Motion rules: new warnings in motion_rules.py (too many moves at once, motion behind text being read, cuts faster
  than the voice) with a case each in tests/test_motion_rules.py; only unreadable text holds a render.
- Sound: optional cues for the new transitions in sfx.py (one constant level, no ducking, no risers), off by default.
- Done when: the new options are all reachable through variety, a demo run of the shipped stories uses every option
  evenly, every look's stills are inside the safe zone and you have looked at them, selftest is green with only the
  goldens you meant to change, and the result report is written.
```

---

## GOAL 4: Composed films and templates (HyperFrames)

```text
GOAL: Take Veasy's composed lane (HyperFrames) to phase 4 of docs/plan-v2.md: research how HTML/GSAP motion and
video-template systems are built, then give agents a library of composable, checked building blocks and a
template pipeline, so an AI can compose rich, original animated films for any program and pack and turn the good
ones into templates.

## Ground rules (shared by all five Veasy goals)
- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, docs/plan-v2.md, ROADMAP.md,
  docs/next.md. CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- Four other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch:
  `git worktree add ..\Veasy-compose -b goal/compose main`, and stay inside it. Never commit to main, never push,
  never merge, never rewrite history. Before you finish, rebase onto the latest local main and stay green.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set
  PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). In your
  worktree run `npm ci` in remotion/ and in compose/.
- Baseline: 3 tests in tests/test_plugin.py fail on Windows only (skill symlinks, the charmap error). Note them,
  don't count them against you; goal 5 fixes them.
- Gates for every commit: `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. For any
  visual change also `python -m tt_shorts.engine selftest` and `python -m tt_shorts.engine probe <story> --look all`,
  then open the stills and look at them yourself. `selftest --update` only for a change you meant, committed with it.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); news rules (tt_shorts/ka_style.md § N,
  news_check.py) only ever get stricter, never an opinion scene; the writer fills only text fields, layout, motion,
  date, sources, QR and colours are code; variety grows by adding options, never by replacing them; text on screen
  is Georgian, code, comments and commits are English.
- Money, servers, secrets: no paid API calls (TTS voices, image models, keyed stock APIs): use the fixtures and the
  free preview paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server
  84.46.250.149, cron or timers. Never read, print or copy data/.env.
- Licences: only what allows commercial use; record the source and licence beside every vendored file (like
  assets/icons/LICENSE). No GPL/AGPL code (OpenMontage is AGPL: study it, don't copy it). No AI-generated imagery
  (tt_shorts/media/ai.py stays off). No publisher photos. From other projects take ideas, not code, unless the
  licence is MIT, ISC, Apache-2.0 or BSD and you credit it.
- Way of working: research first, then write docs/research/compose.md (what you studied, with links; what each
  teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it before building. Then build
  the backlog top-down in small, complete increments: each is code + its test + its skill and `engine options`
  entry + stills checked + one commit with a clear message. Ten finished things beat thirty half-finished ones.
  When something is the owner's call (brand, news rules, licences, money), write it under "Owner decisions" in
  your report and move to the next item. Never guess on those.
- Finish with docs/research/compose-result.md: what shipped (the commit list), the paths of before/after stills,
  what you didn't do and why, the open owner decisions, and the files you touched that other goals may also touch.

## Your lane: the composed lane
You own compose/ (but not its pinned versions), tt_shorts/compose.py, tools/compose_scaffold.py,
tools/compose_probe.py, templates/ and the veasy:compose skill. Other goals own Remotion scene types (goal 1),
icons (goal 2), Remotion motion and variety options (goal 3), and plugin tools and skill structure (goal 5): touch
their files only additively, and list each such touch in your result. HyperFrames runs only through
compose.hyperframes() (telemetry and updates off, REFUSED subcommands), pinned at 0.9.8; the locked chrome and
captions are versioned (CHROME_VERSION) and hashed: a change to them bumps the version.

### Research (aim for 25+ real sources, each with a note on what Veasy can take)
- HyperFrames' own docs and its skills (installed by ops/install.sh --skills: read them where they are installed,
  never copy them into this repo), its examples, and what its lint and render guarantee.
- HTML/CSS/GSAP motion craft: GSAP's docs and showcase (and its current licence terms), CodePen motion collections,
  Awwwards-style kinetic sites, CSS scroll/view timelines as ideas for timeline-driven motion.
- Template systems: Remotion templates, Revideo, Motion Canvas, Editly (MIT), Creatomate's and Shotstack's JSON
  template models (concepts only), After Effects MOGRTs and Essential Graphics (how a template exposes slots),
  Canva and CapCut templates (what users can and can't change).
- AI agents that compose video from HTML or code: what they produce well, where they break (fonts, timing,
  determinism, text overflow), and how they are checked.
- What Veasy already has: engine compose scaffold|check|render|promote|templates, bound facts (data-var-text,
  VEASY.fact), compose.lint and LINT_RULES, the locked chrome v2, the review tier in queue.py, the story tier,
  compose/24835 and compose/bipi-draws, docs/plan-v2.md § 3 and phase 2 + 2b results.

### Build
- A block library (for example compose/blocks/<id>/): reusable, documented scene blocks an agent assembles into a
  film (kinetic headline, number reveal, map pin, comparison, icon grid, quote, process, chapter card, end card...).
  Each block: facts bound never typed, every DOM text through the story's tier, inside the safe zone, the pack's
  theme tokens only, deterministic (renders twice to the same frames), and passing compose check and the probe.
- `compose scaffold` offers blocks (and templates) to the agent, and `engine options` lists them; the veasy:compose
  skill explains how to pick and combine them within its size limit.
- New lint rules for every pitfall you hit (a case each in tests/test_compose.py and an entry in LINT_RULES).
- The template pipeline of phase 4: promote prepares a template from a film with its facts as slots; templates
  rotate through variety like the other options. A composed film stays held for review unless its format or
  program says otherwise: you prepare template candidates, you never mark a film approved (that is the owner's).
- Proof: compose at least four films from the skill alone, in two packs (tbilisi-today and sitech) and three
  programs (news, explainer, story), each passing every check, rendered silent or with the free preview voice.
- Done when: the block library, the lint rules and the template pipeline pass every gate, the four films exist with
  stills you have looked at, the candidates are listed for the owner's review, and the result report is written.
```

---

## GOAL 5: Veasy as an AI's instrument

```text
GOAL: Make Veasy a far stronger instrument in an AI agent's hands: research how the best AI video products and
agent toolkits expose their power, use Veasy end to end only through its tools and skills as a cheaper model
would, then fix every friction, add the missing tools and skills, and make every capability discoverable.

## Ground rules (shared by all five Veasy goals)
- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, docs/plan-v2.md, ROADMAP.md,
  docs/next.md. CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- Four other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch:
  `git worktree add ..\Veasy-tooling -b goal/tooling main`, and stay inside it. Never commit to main, never push,
  never merge, never rewrite history. Before you finish, rebase onto the latest local main and stay green.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set
  PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). In your
  worktree run `npm ci` in remotion/ (and in compose/ if you touch it).
- Baseline: 3 tests in tests/test_plugin.py fail on Windows only (skill symlinks, the charmap error). Fixing them
  is your first task (below).
- Gates for every commit: `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. For any
  visual change also `python -m tt_shorts.engine selftest` and `python -m tt_shorts.engine probe <story> --look all`,
  then open the stills and look at them yourself. `selftest --update` only for a change you meant, committed with it.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); news rules (tt_shorts/ka_style.md § N,
  news_check.py) only ever get stricter, never an opinion scene; the writer fills only text fields, layout, motion,
  date, sources, QR and colours are code; variety grows by adding options, never by replacing them; text on screen
  is Georgian, code, comments and commits are English.
- Money, servers, secrets: no paid API calls (TTS voices, image models, keyed stock APIs): use the fixtures and the
  free preview paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server
  84.46.250.149, cron or timers. Never read, print or copy data/.env.
- Licences: only what allows commercial use; record the source and licence beside every vendored file (like
  assets/icons/LICENSE). No GPL/AGPL code (OpenMontage is AGPL: study it, don't copy it). No AI-generated imagery
  (tt_shorts/media/ai.py stays off). No publisher photos. From other projects take ideas, not code, unless the
  licence is MIT, ISC, Apache-2.0 or BSD and you credit it.
- Way of working: research first, then write docs/research/tooling.md (what you studied, with links; what each
  teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it before building. Then build
  the backlog top-down in small, complete increments: each is code + its test + its skill and `engine options`
  entry + checked output + one commit with a clear message. Ten finished things beat thirty half-finished ones.
  When something is the owner's call (brand, news rules, licences, money), write it under "Owner decisions" in
  your report and move to the next item. Never guess on those.
- Finish with docs/research/tooling-result.md: what shipped (the commit list), what you didn't do and why, the open
  owner decisions, and the files you touched that other goals may also touch.

## Your lane: tools, skills, the agent's experience
You own plugin.yaml, __init__.py (TOOLS), the skills/ structure and .claude/skills, tests/test_plugin.py, and the
agent-facing parts of tt_shorts/engine.py (options, error messages, new commands). A new tool goes in three places
that tests/test_plugin.py checks agree: plugin.yaml, __init__.TOOLS and a skill. Other goals add scene types
(goal 1), icons (goal 2), motion options (goal 3) and HyperFrames blocks (goal 4): your job is that whatever they
add is easy for an agent to find and use; don't build their features.

### First: the Windows baseline
- __init__._engine reads the engine's stdout in the console code page: Georgian fails with 'charmap'. Run the
  engine with PYTHONIOENCODING=utf-8 and read with encoding="utf-8".
- __init__._python looks only for .venv/bin/python; on Windows it is .venv\Scripts\python.exe.
- .claude/skills/* are git symlinks; with core.symlinks=false they check out as text files. Make
  test_claude_code_sees_the_same_skills meaningful on Windows (resolve a link file, or explain the fix in README)
  without breaking Linux.

### Research (aim for 25+ real sources, each with a note on what Veasy can take)
- Writing tools for agents: Anthropic's guidance on tool design and agent skills, the Model Context Protocol spec
  and its best practices, Google's and OpenAI's agent-tool guides, Remotion's and HyperFrames' agent skills.
- AI video products and what they expose: Opus Clip, Captions, HeyGen, InVideo AI, Pictory, Descript, Runway,
  Kapwing, CapCut's AI tools: prompts in, controls offered, how users steer and review.
- Self-critique loops for visual output: render stills, look, check against a list, fix; how agents verify video.
- Veasy itself as an agent sees it: make three videos (a news story, an explainer, a SiTech blog post) only through
  the plugin tools and skills, the way a cheap model would, with fixtures and free preview voices, and log every
  step where you were confused, had to read code, or got an unhelpful error.

### Build (from your friction log and research, ranked)
- Every friction fixed: clearer errors that say what to do next, options that list every choice with a one-line
  meaning, skills that route a request ("an animated explainer about X", "a 30 s story for kids", "a data video")
  to the right program, format, director and engine. Keep each skill under the size test's limit.
- Tools an agent needs to see its own work: a storyboard or contact sheet of a plan's stills, a critique checklist
  the agent runs on its stills before rendering, a dry run that costs nothing and says what a render would cost.
- plan-v2 § 10, "any brand book in": `engine brand new <name> --from <url|pdf|design.md|frame.md>` drafting a pack,
  validating it in brand.py (new keys need tests/test_brand.py cases) and rendering a contact sheet in every theme
  and both engines, with the veasy:brands skill walking an agent through it.
- Research only, then a proposal for the owner (don't build without the owner's OK): exposing Veasy as an MCP
  server so any AI client (Antigravity, Claude Code and others) can use it, not only Hermes.
- Done when: the 3 Windows failures are fixed, the three videos can be made through the tools alone with no step
  needing the code, every new tool is in plugin.yaml, __init__.TOOLS and a skill with tests, the brand-book command
  works on at least one real brand page, and the result report is written.
```

---

## GOAL 6: Styles, from Lemo-Opuscar's lessons

Start it now: it works in new files (`styles/`, `tt_shorts/styles.py`) until goals 4 and 5 are merged, then wires
the styles into the composed lane and the tools. The plan behind it is [lemo-opuscar.md](lemo-opuscar.md).

```text
GOAL: Give Veasy a library of named film styles, learning from lemomo-ai/lemo-opuscar (MIT): styles as data that a
person or an agent names in one word, re-thought for vertical Georgian video and Veasy's brand and news law, with
the directing method, the reading and voice checks and the sound craft that make them work, so Veasy can make far
more kinds of beautiful animated films with no video model.

## Ground rules (shared by all Veasy goals)
- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, docs/plan-v2.md, ROADMAP.md,
  docs/next.md and docs/lemo-opuscar.md. CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- Other agents work on Veasy at the same time (goals 1-5: scenes, icons, motion, compose, tooling). Work only in
  your own worktree and branch: `git worktree add ..\Veasy-styles -b goal/styles main`, and stay inside it. Never
  commit to main, never push, never merge, never rewrite history. Before you finish, rebase onto the latest local
  main and stay green. Until goal/compose and goal/tooling are merged into main, work only in new files; then
  rebase and wire your styles in.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set
  PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). In your
  worktree run `npm ci` in remotion/ and compose/.
- Baseline: 3 tests in tests/test_plugin.py may fail on Windows only (skill symlinks, the charmap error) until goal
  5 is merged. Note them; don't count them against you.
- Gates for every commit: `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. For any
  visual change also `python -m tt_shorts.engine selftest` and `python -m tt_shorts.engine probe <story> --look all`
  (and `engine compose check` for composed films), then open the stills and look at them yourself.
  `selftest --update` only for a change you meant, committed with it.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); news rules (tt_shorts/ka_style.md § N,
  news_check.py) only ever get stricter, never an opinion scene; the writer fills only text fields, layout, motion,
  date, sources, QR and colours are code; variety grows by adding options, never by replacing them; text on screen
  is Georgian, code, comments and commits are English.
- Money, servers, secrets: no paid API calls (TTS voices, image models, keyed stock APIs): use the fixtures and the
  free preview paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server
  84.46.250.149, cron or timers. Never read, print or copy data/.env.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. Lemo-Opuscar's
  code and docs are MIT: you may adapt them with its copyright notice kept beside the file and a line in
  CREDITS/LICENSE; its demo films, stills and three named voice tracks are not ours: never copy them. No GPL/AGPL
  code. No AI-generated imagery (media/ai.py stays off). No publisher photos.
- Way of working: research first, then write docs/research/styles.md and commit it before building. Then build in
  small, complete increments: code + test + skill and `engine options` entry + stills checked + one commit each.
  When something is the owner's call, write it under "Owner decisions" in your report and move on. Never guess on
  brand, news, licence or money questions.
- Finish with docs/research/styles-result.md: what shipped (the commit list), stills paths, what you didn't do and
  why, the open owner decisions, and the files other goals also touch.

## Your lane: styles
You own styles/, tt_shorts/styles.py, tests/test_styles.py, the veasy:styles skill, and the music sampler and
plucked-string tools you add under tools/. Touch other goals' files only additively, and list each touch.

### Research
- Clone https://github.com/lemomo-ai/lemo-opuscar into a scratch folder outside the repo and read, in full:
  README.md, AGENTS.md, DIRECTOR.md, TECHNIQUE.md, MY-STYLES.md, core/README.md, styles/README.md, and at least 15
  styles' STYLE.md (all of the first wave below, plus five more). Read the core tools' code: render/page.mjs,
  video.mjs, still.mjs, readcheck.mjs, sheet.py, tts/asr_check.py, audio/sampler.py, pluck.py, sfx.py,
  INSTRUMENTS.md.
- For each style you consider, write: its essence in one line, what makes it read at a glance, whether it can draw
  in a pack's palette and one font (`palette: pack`) or needs its own (`palette: own`), what vertical 1080x1920 and
  Mkhedruli change, which Veasy engine can draw it, and which programs it suits.
- Spike, and report before building on it: can a HyperFrames composition drive a canvas 2D / WebGL `render(t)`
  page deterministically (render twice, same frames)? If yes, canvas styles run in Lane B. If no, say what it
  would take; a third engine is the owner's decision, not yours.

### Build
- `styles/<slug>/`: style.json (slug, Georgian and English names, category, engine, palette: pack|own,
  fonts: pack|own, programs it suits, families it never takes, the director/look/motion/transition/music/sfx picks
  it narrows variety to, uses) and STYLE.md (the invariants in Lemo-Opuscar's sections, written for vertical
  Georgian video and Veasy's rules; for the composed lane it is the style prompt the agent follows), validated by
  tt_shorts/styles.py with tests.
- Brand law stays: a `palette: own` style is allowed only where the pack lists it in a new `styles` key (validated
  in brand.py with a tests/test_brand.py case) and the program allows it; news never uses one. Variety rotates the
  styles a brand and program allow, least used first, and the novelty guard sees the style.
- First wave, brand-safe: Swiss Motion, Pictogram Motion, Caption News, Data Storytelling, Transit Map, Satellite
  Briefing (Veasy's Georgia map rules, never Lemo-Opuscar's), Engineering Briefing Board, Whiteboard Explainer,
  Blueprint, Isometric Infographic, Countdown. Each: a demo story, rendered in its engine, stills in every pack it
  is allowed in, all checks passing. Then as many of the second wave (docs/lemo-opuscar.md § 3) as quality allows,
  and one Georgian style of our own as a proposal for the owner.
- Checks from Lemo-Opuscar, Veasy's way: a `TEXTS(t)` contract for composed and canvas films so motion_rules'
  reading check (0.5 s + 0.3 s a word) and the safe zone cover them; numbers checked by value in
  speech.voice_qa() for Georgian numerals (a number heard as another number fails the video), with tests.
- Sound: a sampler for real-instrument loops from CC0/CC BY libraries (fetched, never committed, licences in
  CREDITS) and plucked-string modelling for Georgian folk timbres, as new options for tools/compose_music.py.
  One constant level, no ducking, no risers (the owner's rule overrides Lemo-Opuscar's advice).
- "Make a style your own" for a pack: the veasy:styles skill interviews one question at a time (safe to change,
  changes the character, can't change), renders a style frame next to its base and a short demo, and saves it as
  brands/<name>/styles/<slug>/ only when the person says yes.
- Done when: the first wave passes every gate with stills you have looked at, variety rotates styles per brand,
  the TEXTS and numeral checks are tested, the spike is written up, and the result report is written.
```

---

## GOAL 7: One front door (run after goals 1-6 are merged)

```text
GOAL: Make Veasy simple to ask for: one front door where a person or an AI says what they want in a sentence,
names at most a brand and a style, answers one round of questions, and gets a finished, checked film, while every
existing expert option keeps working underneath.

## Ground rules (shared by all Veasy goals)
- Repo: D:\MyStaff\Veasy. Read in full first: CLAUDE.md, README.md, docs/plan-v2.md, ROADMAP.md, docs/next.md,
  docs/lemo-opuscar.md (§ 5 is this goal's design), and every docs/research/*-result.md. CLAUDE.md is law.
- Work only in your own worktree and branch: `git worktree add ..\Veasy-frontdoor -b goal/frontdoor main`. Never
  commit to main, never push, never merge, never rewrite history.
- Windows: use D:\MyStaff\Veasy\.venv\Scripts\python.exe with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8; `npm ci` in
  remotion/ and compose/ in your worktree.
- Gates for every commit: `python -m unittest discover -s tests`, `(cd remotion && npx tsc --noEmit)`, and for any
  visual change `engine selftest` and `engine probe <story> --look all`, stills looked at.
- Hard limits, money, servers, secrets and licences: as in CLAUDE.md and goals 1-6. No paid calls; no server; never
  data/.env. A new tool goes in plugin.yaml, __init__.TOOLS and a skill (tests/test_plugin.py). Keep the engine,
  the skills and `engine options` in step.
- Finish with docs/research/frontdoor-result.md.

## Your lane: the front door
- Audit first: list every concept a person or an agent meets today (brand, program, format, director, look, theme,
  engine, rubric, template, style, captions, music, sfx...) and every command, tool and skill, and write which ones
  a newcomer must know and which only an expert. Commit it as docs/research/frontdoor.md.
- `engine make "<request>" [--brand] [--style] [--source] [--length]` and a matching plugin tool: it reads the
  request, finds or asks for the source, derives program, format, style (variety when not named), director, look,
  theme and engine as code already does, runs `engine plan`, and asks ONE round of questions only for what code
  cannot decide (facts it can't find, the person's own material, whether to see the storyboard first). Then it
  renders or queues. Every existing flag still overrides.
- `engine options` leads with brands and styles (with a still each) and moves the rest under "advanced".
- veasy:make-video becomes the only skill an agent needs to start, routing to the others only when a step needs
  them; every skill stays within the size test's limit.
- A gallery command: one static HTML page of every style, look, scene and director with a still and a short clip
  from the probe, for the owner, clients and agents to choose from.
- Prove it: from a fresh shell, make five films from one sentence each (a news story, an explainer, a law
  article, a SiTech blog post, a short story for children) in two packs, with no flag beyond --brand, using
  fixtures and free preview voices; log every question asked and every step that needed more.
- Done when: the five films pass every check, the newcomer's list of concepts is three (brand, style, story), all
  old commands and tests still pass, and the result report is written.
```
