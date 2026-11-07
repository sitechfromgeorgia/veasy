# Veasy: ten goals for Antigravity, 2026-11-06

Each block below is one self-contained prompt for one Antigravity conversation. Only one `/goal` can be active in a
conversation, so open ten conversations and paste one whole block into each, from `/goal` to the end of its fence. They
run side by side: each works in its own git worktree and branch, and nothing reaches `main` until the owner merges it.
Earlier run: [antigravity-goals.md](antigravity-goals.md).

The first seven are the core. If the limit is the worry, run 1-7: goals 2-5 and 9 need goal 1 to reach a film.

| # | Lane | Branch | Owns | Images |
|---|---|---|---|---|
| 1 | The plate core | `goal/plates-core` | plates/run.mjs, tt_shorts/plates.py, brushes/plate.json, compose/blocks/plate/, skills/plates/ | 0 |
| 2 | The ink brush | `goal/ink-brush` | plates/ink/ | 2 |
| 3 | The number's body | `goal/number-matter` | plates/matter/ | 0 |
| 4 | The paper stage | `goal/paper-stage` | plates/diorama/ | 2 |
| 5 | Lit surfaces | `goal/lit-surfaces` | plates/surface/, tools/build_surfaces.py, assets/surfaces/ | 30 |
| 6 | The scenario library | `goal/scenario-library` | scenarios/, tt_shorts/scenarios.py, skills/scenarios/, stories/scenario-*.json | 0 |
| 7 | The film's eyes | `goal/film-eyes` | tt_shorts/eyes.py, tt_shorts/review.py, skills/review/, tests/fixtures/review/ | 0 |
| 8 | The brush book | `goal/brush-book` | tt_shorts/gallery.py, examples/, skills/brush-book/ | 0 |
| 9 | Georgia as a world | `goal/georgia-relief` | plates/relief/, tools/build_relief.py, assets/relief/ (git-ignored) | 0 |
| 10 | The edit room | `goal/edit-room` | tt_shorts/steer.py, segments.py, room.py, skills/steer/ | 0 |

Goal 5 is the only one that ships generated images, under the owner's word of 2026-11-06 (see CLAUDE.md, Media). Goal 10
is phase 5's steering from the report: running it is the owner's go.

Merge order afterwards: 1, then 2-5 and 9 (each brings its kind and its list of devices to open), 6, 7, 10, and 8 last,
because the book catalogues whatever has merged by then.

Measured costs are in [plates/README.md](../plates/README.md). The idea step's
centrality (a chosen idea must be the story's own, not a side detail) isn't here: it needs the owner's verdict on 20 ideas.

---

## GOAL 1: The plate core

```text
/goal Make baked plates a first-class brush of Veasy: from one line, an agent gets a beautiful pre-rendered clip behind any scene of either engine, free, cached, in the pack's own tones, with the words still in the DOM and every news rule intact.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/plates-core`; otherwise run
  `git worktree add ..\Veasy-plates-core -b goal/plates-core main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/plates-core-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31010.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships no generated image. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/plates-core.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/plates-core-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the plate core
You own plates/run.mjs, plates/lib/, plates/README.md, tt_shorts/plates.py, brushes/plate.json, the plate
scene in remotion/src/scenes, compose/blocks/plate/, skills/plates/ and tests/test_plates.py. Five other goals each own
one kind in plates/<kind>/ at the same time and bake through run.mjs, so keep its contract stable: add, never break.
Shared touches: tt_shorts/engine.py (command, options), tt_shorts/assets.py (a ledger kind), tt_shorts/variety.py (one
option), news_check.py, plugin.yaml, __init__.py.

### Known, measured on 2026-11-06
- `<video muted playsinline src="assets/plates/x.mp4">` in a composed scene passes every compose lint rule and came
  through a pinned HyperFrames render with 60 of 60 frames exact, and remotion/src/media.tsx already draws local video.
  So don't open the `canvas` lint rule: plates don't need it.
- run.mjs bakes a byte-identical mp4 twice and every frame has neutral chroma. The example costs 265 ms a frame.
- Not measured: what reading a plate costs per frame in HyperFrames. Measure it.
- compose/probe.mjs (`groundAt`) judges text over a plate on black and on white, so text needs a solid panel
  (`--canvas-90`).

### Sub-agents
Engine wiring (command, cache, ledger); players in Remotion and HyperFrames; tone mapper; panel and layout designer;
test author; fresh-eye critic.

### Research (15+ real sources)
Background plates in broadcast packages; tone mapping in ffmpeg (`lut`, `curves`, `geq`); banding in dark gradients on
phones, and dithering; video seeking in headless capture; Remotion's OffthreadVideo; caching keyed by content hash.

### Build
1. `engine plate <kind> [--spec f] --seconds n --seed n`: runs run.mjs, caches by plate.json's hash under store.py's
   paths, answers JSON with the path, the hash and ms_per_frame. `engine plate list` shows the library; `engine options`
   gets a `plates` section.
2. Tone: ffmpeg maps black to the pack's `--canvas` and white to its `--ink`. A test proves a mapped frame holds only
   colours on that line, for both shipped packs and both themes. Solve banding.
3. The `plate` scene by CLAUDE.md's recipe, with panel layouts inside the safe zone, and compose/blocks/plate for composed
   films. `anchors.json` drives a DOM accent dot that follows the plate.
4. Refusal: `news`, crime, incidents and deaths are refused at the command, the brush and the checks, each with a test.
5. Ledger: every plate used enters the story's `assets` ledger with kind, hash, seed and licence. A plate holding
   generated imagery carries the N13 label.
6. A library, not a per-video bake: variety picks among cached plates, least used per brand. A queue job never bakes. At
   50 videos a day a fresh plate each would add 37-135 minutes. A missing plate is a warning, never a lost video.
7. Skill `veasy:plates`, tool `veasy_plate`.

### Done when
- `engine plate example --seconds 4` gives a tone-mapped clip in both packs, and a second call answers from the cache in
  under a second.
- One Remotion film and one composed film show a plate behind real facts: rendered, `qa` and flash pass, `probe` passes,
  and the critic has judged the frames.
- Tests prove the refusals, the tone line, the cache and the ledger.
- The skill states what reading a plate costs in each engine, as measured.
- All gates pass.
```

---

## GOAL 2: The ink brush

```text
/goal Build the literal brush: any of Veasy's drawings painted on screen stroke by stroke in real materials (ink, woodcut, blueprint, halftone, chalk, pencil), so a film looks made by a hand and not by a template.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/ink-brush`; otherwise run
  `git worktree add ..\Veasy-ink-brush -b goal/ink-brush main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/ink-brush-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31020.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships none, but you may generate up to 2 as a private look target that your code then has to match; keep them in out/, not in git. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/ink-brush.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/ink-brush-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the ink brush
You own only plates/ink/ and your docs/research files. Read plates/README.md: it is your contract. Bake with
`node plates/run.mjs ink --spec s.json --seconds 6 --seed 1 --out out/plates/x` (run `npm ci` in plates/ first; `--scale
0.5` bakes at half size). Goal 1 wires plates into both engines at the same time, so don't wait for it, and don't touch
plates/run.mjs, tt_shorts/engine.py, brushes/ or remotion/: what you need from them goes in your result, and so do the
devices of concepts/devices.json your kind can draw (they wait with empty `scenes`). To prove a plate behind real facts
now, copy a composed film into out/ (compose/24835 is a good base), put `<video muted playsinline src="...">` in a
scene, and use `engine compose check` and `engine compose look`. plates/ink/README.md gives the one-line command, a table
of spec keys, a cost table and what the kind refuses. A plate is grey, holds no text and no accent, and never goes to
`news`, crime, incidents or deaths.

### Known
Both engines only trim SVG strokes today. No woodcut, blueprint or halftone code exists: styles/ holds rules in prose.
assets/drawings has 44 drawings, and tt_shorts/art.py sanitizes them. An ink shader costs 276 ms a frame at full size and
113 at half: a 4-second clip bakes in about 33 seconds, or about 14 at half.

### Sub-agents
SDF baker (a drawing into a distance field and a stroke order); material authors; flood-cut author; stroke-order tester;
fresh-eye critic who sees only frames.

### Research (25+ real sources)
Non-photorealistic rendering: painterly rendering with curved brush strokes, tonal art maps for real-time hatching,
computer-generated watercolour, pen-and-ink illustration; line boil in hand-drawn animation; how woodcut, linocut,
risograph, halftone, blueprint and chalk really look and why; signed distance fields for vector art.

### Build
1. A bake step from a drawing to a distance field and a stroke order, reusing art.sanitize's output.
2. Six materials under spec key `material`: woodcut, ink wash, blueprint, halftone, chalk, pencil hatch. Each has paper
   tooth and seeded lines that boil on twos. Add more if they earn it.
3. Reveals: stroke by stroke in the drawing's own order, with bleed into the paper; scrape; print-through.
4. The ink flood: the same shader fills the frame and makes the cut, as a matte clip a film can play. Run it through
   tt_shorts/flash.py.

### Done when
- One sheet shows all 44 drawings in all 6 materials, mid-stroke, and you have looked at it.
- Six 4-second clips are baked, and `plate.json` shows each cost.
- The critic scores each material on "painted, not filtered" and each one gets at least 4 of 5, with reasons kept. A
  material that can't get there is cut, not shipped.
- A second bake of the same spec gives the same mp4.
- plates/ink/README.md is complete, and a sub-agent got a good clip from it on the first try.
```

---

## GOAL 3: The number's body

```text
/goal Give numbers a body: a budget becomes a real pile of blocks that falls, splits and stacks on screen, with code proving that the count on screen equals the fact.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/number-matter`; otherwise run
  `git worktree add ..\Veasy-number-matter -b goal/number-matter main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/number-matter-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31030.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships no generated image. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/number-matter.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/number-matter-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the number's body
You own only plates/matter/ and your docs/research files. Read plates/README.md: it is your contract. Bake with
`node plates/run.mjs matter --spec s.json --seconds 6 --seed 1 --out out/plates/x` (run `npm ci` in plates/ first; `--scale
0.5` bakes at half size). Goal 1 wires plates into both engines at the same time, so don't wait for it, and don't touch
plates/run.mjs, tt_shorts/engine.py, brushes/ or remotion/: what you need from them goes in your result, and so do the
devices of concepts/devices.json your kind can draw (they wait with empty `scenes`). To prove a plate behind real facts
now, copy a composed film into out/ (compose/24835 is a good base), put `<video muted playsinline src="...">` in a
scene, and use `engine compose check` and `engine compose look`. plates/matter/README.md gives the one-line command, a table
of spec keys, a cost table and what the kind refuses. A plate is grey, holds no text and no accent, and never goes to
`news`, crime, incidents or deaths.

### Known
`stat` draws 2-30 marks. Neither engine has occluding physical mass. A pile of 12 000 blocks costs 674 ms a frame, 297
at half size, so the cap is 3 000 blocks and half scale is normal. Devices waiting for this: `pour-or-pile`, `too-tall`,
`data-resort`.

### Sub-agents
Fixed-step solver baked to a `.bin`; count verifier; form authors; camera author; flash and motion reviewer; fresh-eye
critic.

### Research (20+ real sources)
Isotype; 3D data stories from visual desks; why a viewer believes physical quantities; deterministic rigid bodies
(rapier, cannon-es: read their licences, and test determinism yourself); InstancedMesh at this scale; camera moves that
reveal scale.

### Build
1. A solver that runs once at bake time into a `.bin`. The page only reads it, so rendering is deterministic whatever the
   solver does.
2. Forms: `pile` (blocks crash onto a table), `pour`, `split` (one share slides out and stacks itself while the rest
   holds still), `too-tall` (the camera climbs a bar that won't fit), `resort` (the same marks regroup and keep their
   identity), `versus` (two piles).
3. The verifier: block count times unit equals the fact exactly. A unit that doesn't divide the fact exactly is refused
   with a clear message, never rounded. Spec keys take the number by reference to a story's fact, never typed by hand.
4. Anchors for each group, so the film's DOM dot and label can sit on the share.

### Done when
- `pile`, `split` and `too-tall` are baked and looked at; the other forms are baked or listed as not done, with the reason.
- Code proves the block count equals the fact, and a test shows a non-dividing unit refused.
- Two bakes of one spec give the same `.bin` and the same mp4.
- flash.py passes on every clip, including the crash.
- One 6-second clip sits behind a real budget fact in a composed film in out/, and the critic has judged it.
```

---

## GOAL 4: The paper stage

```text
/goal Give every story a set: miniature paper worlds the camera moves through in one take, so a film's steps happen in one place instead of a row of cards.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/paper-stage`; otherwise run
  `git worktree add ..\Veasy-paper-stage -b goal/paper-stage main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/paper-stage-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31040.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships none, but you may generate up to 2 as a private look target that your code then has to match; keep them in out/, not in git. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/paper-stage.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/paper-stage-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the paper stage
You own only plates/diorama/ and your docs/research files. Read plates/README.md: it is your contract. Bake with
`node plates/run.mjs diorama --spec s.json --seconds 6 --seed 1 --out out/plates/x` (run `npm ci` in plates/ first; `--scale
0.5` bakes at half size). Goal 1 wires plates into both engines at the same time, so don't wait for it, and don't touch
plates/run.mjs, tt_shorts/engine.py, brushes/ or remotion/: what you need from them goes in your result, and so do the
devices of concepts/devices.json your kind can draw (they wait with empty `scenes`). To prove a plate behind real facts
now, copy a composed film into out/ (compose/24835 is a good base), put `<video muted playsinline src="...">` in a
scene, and use `engine compose check` and `engine compose look`. plates/diorama/README.md gives the one-line command, a table
of spec keys, a cost table and what the kind refuses. A plate is grey, holds no text and no accent, and never goes to
`news`, crime, incidents or deaths.

### Known
A diorama costs 370 ms a frame. CSS 3D gives no occlusion or perspective light at this scale. Devices waiting for this:
`one-take-world`, `parallax`, `object-wipe`. No cast shadows, no bloom, no PBR: tone and fog give the depth (cast shadows
cost 903 ms a frame). The biggest risk is that it reads as grey game boxes, so prove one still first: build one set,
render one frame, and let the critic judge it before you build more. If it fails, change the approach, not the polish.

### Sub-agents
Part kit author; SVG-to-standee extruder for the 44 drawings; camera grammar author; set designers; anchor exporter;
fresh-eye critic.

### Research (20+ real sources)
Toy theatre, pop-up books, cut-out and silhouette animation, tilt-shift miniature photography, stage lighting; camera
grammar in one-take sequences; ExtrudeGeometry and SVGLoader in three.js; fog and tone as depth cues.

### Build
1. A part kit: walls, arches, plinths, stairs, windows, trees, hills, all in paper-like layers.
2. Any drawing from assets/drawings extruded into a standing paper figure.
3. Camera moves under spec key `move`: dolly, crane, push-through, reveal-behind, and a pass where a foreground layer
   wipes the frame and makes the cut.
4. Sets as data, plates/diorama/sets/*.json: at least museum hall, street, market, classroom, river with a bridge. A set
   is generic: it never claims to be a real place.
5. Anchors exported for the film's DOM dot and label.

### Done when
- The first set's still passed the critic before the others were built, and that verdict is in your research file.
- Five sets are baked, 6 seconds each, about 67 seconds a bake at most.
- A stranger sub-agent shown only stills names each place correctly.
- A second bake gives the same mp4; 44 drawings stand up without a broken one.
- One set sits behind a real story in a composed film in out/, and the critic has judged it.
```

---

## GOAL 5: Lit surfaces

```text
/goal Fill the empty middle of Veasy's frames: a small library of generated materials relit by moving light, so a fact sits on stone, paper or wood that feels real, from a handful of images multiplied by code.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/lit-surfaces`; otherwise run
  `git worktree add ..\Veasy-lit-surfaces -b goal/lit-surfaces main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/lit-surfaces-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31050.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). This is the only goal that ships generated images: at most 30, and it must work on as few as 4, because code multiplies them. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/lit-surfaces.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/lit-surfaces-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: lit surfaces
You own only plates/surface/ and your docs/research files. Read plates/README.md: it is your contract. Bake with
`node plates/run.mjs surface --spec s.json --seconds 6 --seed 1 --out out/plates/x` (run `npm ci` in plates/ first; `--scale
0.5` bakes at half size). Goal 1 wires plates into both engines at the same time, so don't wait for it, and don't touch
plates/run.mjs, tt_shorts/engine.py, brushes/ or remotion/: what you need from them goes in your result, and so do the
devices of concepts/devices.json your kind can draw (they wait with empty `scenes`). To prove a plate behind real facts
now, copy a composed film into out/ (compose/24835 is a good base), put `<video muted playsinline src="...">` in a
scene, and use `engine compose check` and `engine compose look`. plates/surface/README.md gives the one-line command, a table
of spec keys, a cost table and what the kind refuses. A plate is grey, holds no text and no accent, and never goes to
`news`, crime, incidents or deaths.

You also own tools/build_surfaces.py and assets/surfaces/.

### Known
Between y=600 and y=1380 most films are black. Flat textures don't relight: moving light needs normals. The image quota
looks small and output may be 1024x1024 at any aspect ratio, so never depend on a size.

### Sub-agents
Image baker; greyscale and tiling author; normals author; light path author; ledger keeper; fresh-eye critic.

### Research (20+ real sources)
Raking light in museum photography; deriving normals from a height image (Sobel, multi-scale); seamless tiling; relighting
in a shader; which materials read on a phone at low contrast; banding in dark gradients.

### Build
1. Bake images in this order, so the most useful land first: limestone, worn plaster, handmade paper, raw wood, hammered
   metal, woven cloth, then 4 panels of original ornament that copy no real monument.
2. tools/build_surfaces.py is the only way assets/surfaces/ is built: greyscale, seamless tiling, normals, at most 15 MB
   in git in total.
3. assets/surfaces/LEDGER.json records each image: prompt, model, date, licence `ai`, and that it needs the N13 label.
4. The plate kind relights a surface with a moving light: `rake`, `sweep`, `dawn`. A loop must close exactly.
5. Code multiplies each image by crop, rotation, scale and light.

### Done when
- At least 4 materials are shipped with their ledger, however the quota went, and the count is stated.
- 12 loops are baked behind real facts' layouts, about 83 seconds a bake at most, and every loop closes without a jump.
- Text panels stay readable on every loop (the critic has judged them), and no banding shows on the darkest loop.
- No generated image holds text, a face, a logo or a real place: a critic has looked at every one.
```

---

## GOAL 6: The scenario library

```text
/goal Give Veasy 24 real plots, not looks: the same facts told as a guessing game, a countdown or an object's biography, with each beat's job known to code and checked for free before any cost.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/scenario-library`; otherwise run
  `git worktree add ..\Veasy-scenario-library -b goal/scenario-library main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/scenario-library-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31060.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships no generated image. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/scenario-library.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/scenario-library-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the scenario library
You own scenarios/, tt_shorts/scenarios.py, skills/scenarios/, tests/test_scenarios.py and stories/scenario-*.json.
Shared touches: tt_shorts/engine.py (write hook, flag, options), writer.OWNED, tt_shorts/make.py, tt_shorts/sfx.py,
tools/compose_sfx.py, plugin.yaml, __init__.py.

### Known
stories/explainer-inflation.json says 3.8% in its first sentence. demo/film-partia.json is 11 scenes, only `stat` and
`points` between hook and end. Neither engine knows a scene's job. `make --length` is parsed and never used: fix it.
Reuse `rubrics.holds` and `_match` for eligibility.

### Sub-agents
Form researcher; schema author; scenario authors; Georgian examples author; sound-cue designer; fresh-eye critic who
reads only the storyboards.

### Research (30+ real sources)
Narrative forms in explainers, documentaries, radio and short video: cold open, countdown, false lead, reverse
chronology, a day in a life, a chase through a document, rule and exception, before and after, comparison, fable, profile,
one object's biography, guess the number, what changes for you. For each: what it promises, where it turns, why people stay
to the end.

### Build
1. A scenario is data, scenarios/<id>.json: beats, each with a job (promise, false lead, turn, payoff), a word budget, the
   scene types that can carry it, fact gates, a sound cue. Eligibility is declarative, no code strings. `validate` in
   tt_shorts/scenarios.py, a case for each in tests/test_scenarios.py.
2. `story["scenario"]` is code-owned like `rubric`. The writer never picks one. `news` refuses a scenario, with a test.
3. Free checks at `plan`: word budgets (pacing), fact gates, and that the payoff is not said early.
4. `engine scenario fit <story>` ranks the scenarios that fit a story's facts, and says why. `engine make "<url>"
   --scenario auto --preview-storyboard` shows a storyboard before any cost. A long film can take chapters with a
   different scenario each.
5. `myth-vs-fact` only when the document itself makes the correction; otherwise it is an opinion scene, so refuse it.
6. Sound cues stay synthesized at one constant level: no risers, no ducking.
7. Measure the cheap writer on stubs and saved outputs: does it follow beats? The risk is that it ignores them and the
   repairs run out. Say what you found.

### Done when
- 24 scenarios validate, each with a Georgian demo story that passes `check` and `plan`.
- `engine scenario fit` runs on 10 stories and its picks make sense to the critic.
- Three scenarios of one set of facts sit side by side on a storyboard sheet and tell different stories.
- `news` is refused, `myth-vs-fact` is gated, and each is tested.
- Skill `veasy:scenarios` and a tool exist, and a sub-agent used them cold.
```

---

## GOAL 7: The film's eyes

```text
/goal Teach a film to look at itself: free pixel checks and a fresh-eye review loop on both engines, so an agent fixes dull or broken frames before a person ever sees them.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/film-eyes`; otherwise run
  `git worktree add ..\Veasy-film-eyes -b goal/film-eyes main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/film-eyes-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31070.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships no generated image. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/film-eyes.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/film-eyes-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the film's eyes
You own tt_shorts/eyes.py, tt_shorts/review.py, skills/review/, tests/test_eyes.py and tests/fixtures/review/.
Shared touches: tt_shorts/critique.py, tt_shorts/engine.py, plugin.yaml, __init__.py.

### Known
critique.py scores plan numbers and never opens a frame. The fresh-eye review is manual and exists only for composed
films. `golden.dhash`, `probe`, `probe cut`, `compose look` and `flash.py` exist: build on them. Research in the report
ranks critics below planning, so a critic may only hold, and a model's "pass" is never a gate.

### Sub-agents
Pixel metric author; seeded-defect maker; review packet builder; loop author; calibrator on approved demos; fresh-eye
critic.

### Research (20+ real sources)
What editors and motion designers check on a final pass: rhythm, hero frames, negative space, legibility on a phone,
repetition; automated video quality measures; why review loops stall or over-correct; what a vision model can and can't
judge from a contact sheet.

### Build
1. Free pixel checks in eyes.py on either engine's frames: the same picture twice (`golden.dhash`), ink share in the empty
   middle, no hero frame, cuts on a metronome, a scene that only repeats the words spoken.
2. A review packet: sheets and the film's spec only, never the code. Notes in the skill's format `t=4.2s · where ·
   problem -> change`.
3. `engine review <story> --rounds 2`: a loop capped at 3 machine rounds and 2 look rounds, that never changes a fact
   (a facts diff stays empty) and costs nothing but local work.
4. Everything is a warning until calibrated on approved demos; only the flash and unreadable-text rules hold today.

### Done when
- 12 seeded-broken stories are in tests/fixtures/review/, and at least 10 are caught.
- Approved demos raise no false hold.
- Before and after sheets show a real fix on 3 films, and the facts diff is empty.
- Skill `veasy:review` and a tool exist, and a sub-agent used them cold.
```

---

## GOAL 8: The brush book

```text
/goal Show everything the brush can do: a searchable catalogue of real rendered frames and clips with the exact command for each, plus annotated example films agents learn from.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/brush-book`; otherwise run
  `git worktree add ..\Veasy-brush-book -b goal/brush-book main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/brush-book-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31080.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships no generated image. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/brush-book.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/brush-book-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the brush book
You own tt_shorts/gallery.py, examples/, skills/brush-book/ and tests/test_gallery.py. Shared touches:
tt_shorts/styles.py (`summary`), one line in skills/make-video, plugin.yaml, __init__.py.

### Known
gallery.py draws one generic SVG card per item. assets/stills/ doesn't exist, though `styles.summary` and
`veasy:make-video` promise stills. The kit has 31 brushes in 3 looks and 2 themes, 8 hooks, 10 motifs, 8 entrances, 14
transitions, 9 blocks, 8 directors, 18 styles, 5 rubrics, 3 templates. Other goals add scenarios and plate kinds at the same
time, so the harness must read everything from data: what merges later appears by itself. A generated picture would
misreport a brush: every picture here is a real render.

### Sub-agents
Still and clip harness (from each brush's `example`); page builder; search index author; example curator; fresh-eye
reviewer who tries to find a look for a given story.

### Research (15+ real sources)
Design system catalogues, motion libraries, Remotion's and HyperFrames' own galleries: how a person finds the right thing
in seconds. How agents learn from examples, and when they just copy them.

### Build
1. `engine gallery --real` renders real stills and short clips for every item, cached by hash, into out/gallery/.
2. One page, out/gallery/index.html: searchable by what a story needs ("a number", "a place", "a process"), each entry
   with its picture, its command and when not to use it. It reads plates/*/ posters if they exist.
3. examples/: 12 annotated films across programs (what the story asked for, why this shape, what was turned down), and 6
   bad-to-fixed pairs. Agents copy examples, so each teaches the reasoning, and they rotate.
4. Skill `veasy:brush-book`: how an agent picks from it.

### Done when
- A test finds a real file for every brush × look × theme, and for every other listed item.
- The page opens and search works, checked in a browser at phone and desktop width.
- A sub-agent given a story and only this page picks a sensible look in under 3 tries, for 5 stories.
- 12 examples and 6 pairs exist and pass `check`.
```

---

## GOAL 9: Georgia as a world

```text
/goal Make Georgia a world the camera can fly through: contour-line relief of the real terrain, in the pack's tones, from open data baked locally, with every map rule of CLAUDE.md intact.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/georgia-relief`; otherwise run
  `git worktree add ..\Veasy-georgia-relief -b goal/georgia-relief main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/georgia-relief-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31090.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships no generated image. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/georgia-relief.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/georgia-relief-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: georgia as a world
You own only plates/relief/ and your docs/research files. Read plates/README.md: it is your contract. Bake with
`node plates/run.mjs relief --spec s.json --seconds 6 --seed 1 --out out/plates/x` (run `npm ci` in plates/ first; `--scale
0.5` bakes at half size). Goal 1 wires plates into both engines at the same time, so don't wait for it, and don't touch
plates/run.mjs, tt_shorts/engine.py, brushes/ or remotion/: what you need from them goes in your result, and so do the
devices of concepts/devices.json your kind can draw (they wait with empty `scenes`). To prove a plate behind real facts
now, copy a composed film into out/ (compose/24835 is a good base), put `<video muted playsinline src="...">` in a
scene, and use `engine compose check` and `engine compose look`. plates/relief/README.md gives the one-line command, a table
of spec keys, a cost table and what the kind refuses. A plate is grey, holds no text and no accent, and never goes to
`news`, crime, incidents or deaths.

You also own tools/build_relief.py, git-ignored assets/relief/, and may add to assets/maps/README.md. Add
`assets/relief/` to .gitignore: the data is built by the tool, like the music.

### Known
`where` is a flat SVG zoom. HyperFrames' own advice is live satellite tiles, which Veasy refuses: no tiles, no URL at
render time. tt_shorts/geo.py has 149 places, 12 regions and the privacy rule. Relief costs 187 ms a frame. Downloading
open data is allowed in the tool only, never in a test.

### Hard map rules
Outlines come only from assets/maps/georgia.json. Georgia has its 12 regions of Georgian law: Abkhazia and the Tskhinvali
region are part of Georgia, drawn as no separate entity. For the crime family the map stops at the region and marks no
district (`geo.PRIVATE`), and in this run plates don't serve crime at all. A wrong road is a false claim: draw a road only
from a licensed source with a test, else a dot and a place name.

### Sub-agents
DEM baker; camera move author; gazetteer anchor author; licence checker; fresh-eye critic.

### Research (20+ real sources)
Copernicus DEM, SRTM and other open elevation data: exact licence terms and attribution; OpenStreetMap's ODbL and what
share-alike would ask of a film (if unclear, it's an owner decision, and you build without it); hillshade and contour
cartography; terrain meshing in three.js.

### Build
1. tools/build_relief.py is the only way assets/relief/ is built, reproducibly, with its sources in assets/maps/README.md.
2. Moves under spec key `move`: `descend` (the camera falls off a ridge to a place), `ridge` (flies along it), `reveal` (a
   region rises out of the dark).
3. Contour lines and relief in grey, Georgia's outline from georgia.json, nothing outside it drawn as a claim.
4. Anchors from geo.py's gazetteer, so the film's DOM dot lands on the place.

### Done when
- Three flights are baked and looked at in two packs: over Kazbegi to Jvari, over Svaneti, over Kakheti.
- 48 region and district plates are baked, about 27 minutes once, and listed.
- Abkhazia and Tskhinvali region are checked on every map in a test, and a critic checks the anchors land on the place.
- The licence table names every source and what a film must credit.
```

---

## GOAL 10: The edit room

```text
/goal Make a finished film editable: change one scene and only that scene redraws, with a page that shows every scene and says what a change will cost before it runs.

## Ground rules (shared by all ten Veasy goals of 2026-11-06)

The aim, in the owner's words: a brush with which agents paint videos in beautiful frames, a tool that assembles
stories perfectly, equipped with as many different scenarios as possible, and better at the user's level than plain
Remotion or HyperFrames. The owner can't pay for a video generation API, so every film must stay free to render.
Remotion and HyperFrames stay the render engines: you add what neither of them has.

- Repo: D:\MyStaff\Veasy. Veasy is SiTech's video engine (Python + a Remotion project + a HyperFrames lane), and a
  Hermes plugin. Read these in full before anything else: CLAUDE.md, README.md, ROADMAP.md,
  `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`, plates/README.md, and the docs/research/*-result.md files
  (what past goals shipped: never rebuild it). CLAUDE.md is law: where this brief and CLAUDE.md disagree, CLAUDE.md wins.
- You are an orchestrator. Spawn sub-agents from the start and run them in parallel: at least the roles listed in
  your lane, each with a clean brief (its goal, the files it owns, the evidence it must bring back). No two sub-agents
  write the same file. One of them is always a fresh-eye critic who has not seen the code: it gets only rendered
  frames or the skill text, and its notes decide what you fix next. Don't finish while a sub-agent is still running.
- Think at the user's level first. Before you build, write at the top of your research file the one line a person or
  an agent types and what they get back. If it takes more than a line, redesign it. Someone who has read only the
  skill must get a good result on the first try: a sub-agent tests exactly that.
- Nine other agents work on Veasy at the same time on other goals. Work only in your own worktree and branch. If this
  conversation already runs in a worktree, run `git branch -m goal/edit-room`; otherwise run
  `git worktree add ..\Veasy-edit-room -b goal/edit-room main` and stay inside it. Never work in D:\MyStaff\Veasy itself.
  Never commit to main, never push, never merge, never rewrite history.
- Usage limits can end this run at any moment. Put the most valuable thing first in your backlog, commit each finished
  unit at once, and keep docs/research/edit-room-result.md current from your first commit on, so a stop costs one unit at most.
- Windows: `python` is a Microsoft Store stub. Use D:\MyStaff\Veasy\.venv\Scripts\python.exe, and set PYTHONUTF8=1
  and PYTHONIOENCODING=utf-8 (otherwise Georgian output fails with a 'charmap' error). Also set
  KAEASY_DIR=D:\MyStaff\Kaeasy and SHORTS_KAEASY_LEARN=0. In your worktree run `npm ci` only in the folders you use
  (remotion/, compose/, plates/). Files are stored with LF.
- The machine is shared: 8 cores, 32 GB, ten agents. Set SHORTS_RENDER_WORKERS=2. Prefer stills, `engine compose look`
  sheets and half-scale bakes; render a whole film only at a milestone. The full test suite takes 7 minutes on an idle
  machine: per commit run your own test file, the full suite at milestones and before you finish. A local server of
  yours uses port 31100.
- Gates. Main passes all of these today: `python -m unittest discover -s tests` (773 tests, 2 skipped),
  `(cd remotion && npx tsc --noEmit)`, `python -m tt_shorts.engine selftest` (102 unchanged). For any visual change also
  `python -m tt_shorts.engine probe <story> --look all`, then open the stills and look at them yourself. `selftest
  --update` only for a change you meant, committed with it. Before you finish, rebase onto the latest local main and
  stay green.
- Hard limits: no client's name, colour, link or word in engine code (only in brand packs); the brand pack is law
  (dark canvas, light ink, one accent that is never on text, one font family, no shadows, no frame on the mark, no
  category colours, no long dashes, the source and the time always on screen); the safe zone (scene text ends at
  y=1380, captions at y=1552, below y=1100 no text right of x=940); `news` stays exactly as it is, and news rules
  (tt_shorts/ka_style.md § N, news_check.py) only ever get stricter, never an opinion scene; the writer fills only text
  fields, layout, motion, date, sources, QR and colours are code; variety grows by adding options, never by replacing
  them; frames are deterministic (same input, same pixels, no clock, no unseeded random); flash safety and motion
  rules hold (tt_shorts/flash.py, tt_shorts/motion_rules.py); text on screen is Georgian, code, comments and commits
  are English.
- Money, servers, secrets: no paid API calls, no writer or voice calls: use stubs, saved outputs and the free preview
  paths (`engine plan`, `still`, `probe`, edge-tts). No network in tests. Never touch the server 84.46.250.149, cron or
  timers. Never read, print or copy data/.env.
- Images: you can generate images, and the owner allows an image baked once into a local library, never at render
  time (tt_shorts/media/ai.py stays off). Your goal ships no generated image. The image quota is shared and may be small: on the first quota error,
  stop generating and go on without. Never real people, real places or buildings, logos, text, or the style of a named
  artist or studio, and nothing about crime, incidents or deaths.
- Licences: only what allows commercial use; record the source and licence beside every vendored file. No GPL/AGPL
  code. No publisher photos. From other projects take ideas, not code, unless the licence is MIT, ISC, Apache-2.0 or BSD
  and you credit it in CREDITS.md. Shadertoy code is usually non-commercial: study it, never copy it.
- Shared files (tt_shorts/engine.py, plugin.yaml, __init__.py, tests/test_plugin.py, README.md): touch them only
  additively, as small as you can, at the end of a list, and name each touch in your result. Don't edit CLAUDE.md:
  put the paragraph you propose for it in your result. A new skill needs skills/<name>/SKILL.md under 12000 characters,
  a tool in plugin.yaml and __init__.TOOLS, and a link .claude/skills/<name> of mode 120000.
- Way of working: research first, deeply, with sub-agents, from real sources. Write docs/research/edit-room.md (what you
  studied, with links; what each teaches Veasy; a licence table; a ranked backlog with value and effort) and commit it
  before you build. Then build the backlog top-down in small, complete increments: code + its test + its docs + frames
  you looked at + one commit. Ten finished things beat thirty half-finished ones. Stay in your lane. Anything that is the
  owner's call goes under "Owner decisions" in your result, and you move on to the next item. Never guess on those.
- Finish with docs/research/edit-room-result.md: a table that maps every "Done when" line to its evidence (a file, a
  command's output, a still), the commit list, what you didn't do and why, the owner decisions, and every shared file
  you touched. Don't declare the goal complete while a "Done when" line has no evidence.

## Your lane: the edit room
You own tt_shorts/steer.py, tt_shorts/segments.py, tt_shorts/room.py, skills/steer/ and tests/test_steer.py.
Shared touches: one branch in `props.render_video`, one in compose.py's render, tt_shorts/engine.py, plugin.yaml, __init__.py.

### Known
Today one wrong label re-renders everything: `render_video` has no partial path. `dry_run` estimates 1.8x length, so about
9 minutes for a 5-minute film (not measured). Both engines can render a range (Remotion `--frames`, HyperFrames
`--start/--end`), but neither knows which frames a change touches or what it costs. Stream-copy splicing isn't verified
here: test it, and fall back to a clean re-encode of the join. Never splice voice by sentence: tone seams, and later timing
moves anyway.

### Sub-agents
Segment cache author; steer verb author (tighter, breathe, land); room page author; HyperFrames parity author; determinism
tester; fresh-eye critic who uses the page cold.

### Research (15+ real sources)
Incremental rendering in video tools; how non-linear editors track what's dirty; content-addressed caches; frame-accurate
concat in ffmpeg; how a person wants to direct a small change in plain words.

### Build
1. Segments: a film cut by scene into cached parts, keyed by a hash of what each part depends on.
2. `engine steer <story> --scene 3 --set label="..." [--dry]`. `--dry` answers the cost before it runs: "4 s of picture, $0"
   or "new voice, every frame". A narration change moves later frames, so it stays a full render with a new voice, and the
   page says so plainly.
3. Plain verbs: `--tighter`, `--breathe`, `--land`, mapped to timing changes checked by motion_rules.
4. `<render>.room.html`: each scene's still, words, timing and rhythm, with a ready command to copy.
5. Parity on both engines. A change still passes `check`, `probe`, `qa` and flash.

### Done when
- Changing one label in demo/film-partia.json is timed before and after, and the saving is stated.
- Frame hashes outside the changed scene equal a full render.
- `--dry` is right on a text change, a timing change and a narration change, each tested.
- The room page opens, and a sub-agent fixed a scene from it alone.
- `selftest` is green, and skill `veasy:steer` and a tool exist.
```
