# Veasy: rules for agents

**Veasy** is SiTech's video engine; kaeasy is its sibling for Georgian. It is also a Hermes plugin
(`plugin.yaml`, `__init__.py`, `skills/`). A new tool goes in three places, and `tests/test_plugin.py` checks they
agree: `plugin.yaml`, `__init__.TOOLS` and a skill.

Read [README.md](README.md) first. Veasy is Python plus a Remotion project.

Veasy belongs to no single project: a client is a **brand pack** (`brands/<name>/brand.json`, `tt_shorts/brand.py`).
- No client's name, color, link or word goes into engine code (`tt_shorts/`, `remotion/src/`); it goes in a pack.
  `brands/_ka` is the Georgian base; a pack extends it. A new pack key needs validation in `brand.py` and a case in
  `tests/test_brand.py`.
- Shipped packs: `tbilisi-today` (the default) and `sitech`.
- Storage and names are `tt_shorts/store.py` (`$VEASY_HOME`); work for many videos goes through the queue
  (`tt_shorts/queue.py`). Don't invent other folders or naming schemes.

Its first client is tbilisi.today ([sitechfromgeorgia/tbilisi.today](https://github.com/sitechfromgeorgia/tbilisi.today)):
- Veasy only reads that project's D1, never writes to it.
- That repo's rules apply to anything Veasy does there.

- **Where it runs:** the tbilisi.today agent server, 84.46.250.149. Setup is `ops/install.sh`.
  - Secrets live only in `data/.env` (chmod 600, git-ignored).
  - Timers, cron and anything installed on the server need the owner's OK.
- **Entry point:** `python -m tt_shorts.engine` (options, check, plan, render, still, qa, probe, write, concept, queue, gc,
  voices, doctor, compose, plate, scenario, review, steer, room, look, gallery, thread, vignettes; JSON out). `plan` is the free storyboard to run before paying for a voice.
  The skills in `skills/` say how an agent uses it. Keep the engine, the skills and `options` in step: a new
  choice in code must appear in `engine.options()`, `formats.py` validation and the `veasy:formats` skill.
- **A new scene type** is a brush (`brushes/<type>.json`, validated by `tt_shorts/catalog.py`; its docstring lists
  the keys). The brush alone gives `engine.SCENES`/`COUNTS`, `speech.MIN_SCENE`, `ka_check.MIN_WORDS`/`FIELDS`, the
  writer's line and rules and `engine options`. By hand, in this order:
  1. `brushes/<type>.json` (copy a close one; a free `order`; slots with Georgian length limits; `em` fields the
     component will mark, or empty; a real `example`);
  2. `news_check.SCENE_TYPES` (the news rules' own allowlist, N1) and, for a rule the slots can't express,
     `engine.shape_problems` (shape, order) or `news_check` (against the articles or the narration) with a test;
  3. `remotion/src/scenes` (`SCENES`) and `types.ts`; mark text with `marked(s, "<field>", text)` (`marker.tsx`) for
     each em field;
  4. the `veasy:write-script` skill's table, a demo story, `engine probe <story> --look all` and the stills.
  `tests/test_catalog.py`, `test_scenes.py` and `test_engine.py` check the catalog, the news list and Remotion agree.
- **Variety is a rule** (owner, 2026-11-02: "1000 videos in one style is no good"). `tt_shorts/variety.py` gives
  each video its own hook layout, background motif, entrance, transition and music loop (the least used lately per
  brand, remembered in `veasy.db`), and the writer sees the scene orders used lately. A new layout or motion goes in
  as one more option there (and in `remotion/src`), never as a replacement of the others; `tests/test_variety.py`
  checks a run uses every option evenly. The novelty guard (`variety.choose`) re-rolls a plan too close to one of
  the brand's last 20 before the voice is made; it warns, never fails a video. The writer draws (`art.py`:
  sanitize + quality; a failing drawing is swapped for a library one of its motif, `drawings.py`, else dropped,
  not the video); `VEASY_WRITER_DRAW=0` turns it off. A new seed drawing in `assets/drawings/` must pass both (`tests/test_drawings.py`).
- **Rubrics** (`rubrics/<id>.json`, `tt_shorts/rubrics.py`, `veasy:rubrics`): named shows with a chip in the hook,
  a shape, a slot and an episode. `rubric`, `episode` and `part` are code-owned like `date`; eligibility is
  declarative data (no code strings); a new rubric needs a case in `tests/test_rubrics.py`. The digest (program
  `digest`) is built by code from checked stories, never by a model, and states its real story count.
- **Two film engines** (`"engine": "remotion" | "hyperframes"`: director, else program, else format, else pack,
  else remotion; `compose.engine_for`). The HyperFrames lane is `tt_shorts/compose.py` (`engine compose
  scaffold|check|look|render|promote`, skill `veasy:compose`, tool `veasy_compose`):
  - HyperFrames runs only through `compose.hyperframes()` (telemetry and updates off, `REFUSED` subcommands and
    `OFFSITE` flags), pinned in `compose/package.json`; renders pinned in `compose.RENDER`.
  - A composed film meets the novelty guard through `variety.assess_composed` (`COMPOSED_FIELDS`): a warning, never a
    hold. `variety.FIELDS` stays the kit's.
  - The locked chrome and captions are versioned (`CHROME_VERSION`) and hashed; a change to them bumps the version.
  - A new lint rule goes in `compose.lint` and `LINT_RULES` with a case in `tests/test_compose.py`.
  - `probe cut` (`compose.cut_problems`) reads every frame pair where two scene hosts overlap: text colliding is a
    problem, drawings colliding a warning (a match cut does it on purpose). A change needs a case in `Cuts` there.
  - Facts are bound (`data-var-text`, `VEASY.fact`), never typed; every DOM text goes through the story's tier.
  - A composed film is held for review unless its format or program says `review: until:<n>` (queue.py).
  - The engines' own skills are installed by `ops/install.sh --skills`, never copied into this repo.
- **The film's eyes** (`tt_shorts/eyes.py`, `tt_shorts/review.py`, `engine review`, skill `veasy:review`, tool `veasy_review`):
  free pixel and pacing checks on either engine's frames, and a repair loop capped at 3 machine and 2 look rounds. Only `read`
  and `flash` hold; every other check is a warning until calibrated on approved demos. The loop never changes a fact
  (`review.facts_diff` stays empty), and a model's "pass" is never a gate. A new check needs a seeded-defect fixture in
  `tests/fixtures/review/` and a case in `tests/test_review.py`.
- **The edit room** (`tt_shorts/segments.py`, `steer.py`, `room.py`, skill `veasy:steer`, tool `veasy_steer`): `engine steer
  <story> --scene <n> [--set k=v] [--tighter | --breathe | --land] [--dry]` redraws only the scenes a change touches, from
  content-addressed segments in `$VEASY_HOME/cache/segments`, and mixes the voice once (never spliced by sentence). `--dry`
  states the cost first. Every render writes `<render>.room.html`.
- **Scenarios** (`scenarios/<id>.json`, `tt_shorts/scenarios.py`, `engine scenario`, skill `veasy:scenarios`): a plot as data:
  beats with a job, a word budget, the scene types that can carry it, fact gates and a sound cue. `story["scenario"]` is
  code-owned; the writer never picks one. `news` refuses it, and `myth-vs-fact` runs only when the document itself makes the
  correction. A new scenario needs a case in `tests/test_scenarios.py` and a demo story that passes `check` and `plan`.
- **The brush book** (`tt_shorts/gallery.py`, `examples/`, `engine gallery`, skill `veasy:brush-book`): a searchable page of
  real renders, read from data, so what merges later appears by itself. `out/gallery/` isn't in git.
- **The film's thread** (`tt_shorts/thread.py`, brush `state`, `engine thread`): one object from the chosen idea runs through a film's
  scenes, changes state, and can carry a cut (`match`, `object`). Only for a story with a `concept`; never in `news`. Code seats
  it and gives a seat up before it collides with text.
- **Vignettes** (`tt_shorts/vignettes.py`, `engine vignettes`, skill `veasy:draw`): 1-3 line drawings of what the film
  is about, centred in the room a scene's text leaves (the thread's seats), drawn stroke by stroke (owner, 2026-11-07:
  "the visual follows the topic"). A scene's own `art` first, else the library's drawing of a thing its part of the
  narration names. No words in them, so no facts; none for crime, incidents or deaths, none in a film with a thread.
  `points` are never numbered, and more than one list in a short film is a `motion lists` warning. A change needs a
  case in `tests/test_vignettes.py`.
  - The writer never draws `art`: the illustrator (`tt_shorts/illustrator.py`, `engine vignettes --draw`) does, in a
    call of its own after the script, with its own guide and examples (`VEASY_ILLUSTRATOR_MODEL`, so a cheap model;
    `VEASY_ILLUSTRATOR=0` gives `art` back to the writer). Code checks every drawing, one repair, never fails a video.
  - Drawings move (owner, 2026-11-07: "moving, not static"): one part acts out the words (`art.py` classes `t` turn,
    `m` move, `g` grow) when the voice says the scene's `em`, a part may loop (`--spin`, `--swing`, `--bob`,
    `--pulse`), and every vignette pushes in slowly inside its seat. A drawing without an act goes back to the
    illustrator once, never fails. The style whitelist (`art.MOVES`) is the only way to add a motion.
- **One take** (`tt_shorts/onetake.py`): a transition option that lays scenes on a seeded 2D path. The camera moves only during
  cuts; chrome, captions and the safe zone never ride it; zoom stays at or under 1.15. Not for `news`.
- **Motion rules** (`tt_shorts/motion_rules.py`): warnings in `engine plan`; only unreadable text (0.5 s + 0.3 s a
  word) holds a render. A new rule needs a case in `tests/test_motion_rules.py`.
- **Flash** (`tt_shorts/flash.py`, ITU BT.1702): safety, not style. `qa_file` holds a video that flashes more than 3
  times a second over a quarter of the screen, whichever engine drew it. A change needs a case in `tests/test_flash.py`.
- **Data flow:** source → story JSON → `tt_shorts/props.py` (voice, timings, data, the brand pack) → `remotion/`
  composition `NewsShort` → mp4.
  - The writer (an LLM) fills only text fields.
  - Layout, motion, date, sources, QR and colors are code.
- **The brand pack is law** (tbilisi.today: brand v1.2, https://tbilisi.today/brand):
  - Colors: dark canvas, light ink, one accent. The accent is for the dot, an active state or the button, never for text.
  - One font family per pack. No shadows, no frame on the mark, no category colors, no long dashes.
  - The source and the time are always on screen.
  - A new look changes layout or motion, not the palette. Remotion reads colors from `brand.ts` live bindings
    (`applyBrand`): read them inside components, never at module level.
- **News rules are hard rules:** `tt_shorts/ka_style.md` § N and `news_check.py`.
  - Videos are published without a human review. Any rule that code can check goes into `news_check.py` with a
    test in `tests/test_news_check.py`.
  - Never add an opinion scene. Never let the writer set `date` or `sources`.
- **Ideas** (`tt_shorts/concept.py`, `concepts/`, `veasy:direct`): a program with `"concept"` gets one idea per story
  before its script: the model writes from named rungs, code judges and chooses, the story keeps it (code-owned, never
  on screen). `news` has no idea step and may not get one until the owner decides. A new filter needs a case in
  `tests/test_concept.py`; a device names the scene types that can draw it today, or waits with none. History is
  `variety.record_concept`, never a field of the novelty fingerprint.
- **Programs** (`programs/*.json` + `programs/briefs/`, `tt_shorts/programs.py`): what a video is made from and
  what it may claim. `news` (no `"program"` in the story) must stay exactly as it is. A new program is a JSON file
  and a brief; a new rule tier goes in `tt_shorts/claims_check.py` with a test in `tests/test_programs.py`; a new
  source is `tt_shorts/sources/<name>.py` with a test in `tests/test_sources.py`. A story's `program`, `source` and
  `link` come from the data, never from the writer.
- **Georgian:** K1-K22 come from sitech-shorts (`ka_style.md`, `ka_check.py`, `normalize_ka.py`, `lexicon_ka.json`).
  A Latin name's spoken form goes in `lexicon_ka.json` (approved) or in the story's `say` map.
  General Georgian rules belong in **kaeasy**, SiTech's plugin (`tt_shorts/kaeasy.py` loads it from `KAEASY_DIR`):
  - add a new general rule there, not here;
  - keep only video-specific rules in this folder (news rules, timing, the spoken form).
- **Safe zone:**
  - Scene text ends at y=1380 and captions at y=1552.
  - Below y=1100, no text goes right of x=940.
  - The band below the captions carries motion only.
- **Maps:**
  - `assets/maps/georgia.json`, `georgia-detail.json` and `tbilisi.json` are built only by
    `tools/build_georgia_map.py` (sources and licences in `assets/maps/README.md`). The OpenStreetMap layers are
    ODbL: a map that draws them carries "© OpenStreetMap contributors" in its `credit`.
  - Georgia has its 12 regions of Georgian law: Abkhazia and the Tskhinvali region are part of Georgia, drawn as
    no separate entity.
  - Occupied areas (owner, 2026-11-07): they are marked with the pack's label (`strings.occupied`) and a light
    accent tint, and stay inside Georgia's outline, drawn as no separate entity (an overlay in `georgia.json`,
    never a 13th region or a border line).
  - For the crime family the map stops at the region and marks no district, and ships no district outline or
    street (`geo.PRIVATE`, `tests/test_geo.py`).
- **No publisher photos:** tbilisi.today has no reuse grant (tbilisi.today repo: `ingest/src/story-cover-assets/README.md`).
- **Music** is composed by `tools/compose_music.py`; the m4a files are not in git. One constant level: no build-ups,
  no ducking (the owner heard the ducked bed pump). The mix happens in ffmpeg (`props.mix_audio`), not in Remotion.
- **Voices:** shared presets in `voices.py`; a pack's own in its `voices` (SiTech's `Charon` lives only in
  `brands/sitech`). edge-tts is a preview stand-in only.
- **Media** (`tt_shorts/assets.py`, one module per provider in `tt_shorts/media/`): engine-free. Python resolves a
  scene's `show` hint (the writer's only say) into a local file and the story's code-owned `assets` ledger; an
  engine draws only local files, never a URL. Only licences allowing commercial use (`assets.LICENCES`); a new
  provider is one module with a test in `tests/test_assets.py` (no network in tests). No AI generation at render
  time (`media/ai.py` stays disabled); an image baked once by an agent into a local library, with its ledger, is allowed
  (owner, 2026-11-06). N13 (`news_check.imagery`): the pack's „საილუსტრაციო" label, no
  imagery for crime/incidents/deaths, screenshots only from the pack's/program's allow-list.
- **Plates** (`tt_shorts/plates.py`, `plates/run.mjs`, `plates/README.md`, skill `veasy:plates`, tool `veasy_plate`): grey
  clips baked once in the browser on software GL and played behind a scene as local files, so neither engine changes and
  text stays in the DOM. `engine plate <kind>` caches by content under `$VEASY_HOME/cache/plates` and tones the clip onto
  every pack's canvas-to-ink line. A new kind is `plates/<kind>/` and passes `engine plate check`.
  - Refused for `news`, the crime family and words of deaths or incidents, at the command, the brush and the checks.
  - Deterministic, no text, no accent. A queue job never bakes: it picks a baked plate, and a missing one is a warning.
  - The shelf hands a film only kinds that say nothing (`plates.GROUND_KINDS`: `example`, `surface`). `matter` (a count
    proved against one fact), `relief` (a real region), `diorama` (a kind of place) and `ink` (one drawing) carry a claim,
    so a film gets one only by name (`engine plate use`). A plate is never a picture of a real place; `relief` is a map, and
    the Maps rules apply to it (a test proves its anchors against real heights).
  - A surface on a material a model made carries the pack's N13 label (`plates.generated`). `assets/surfaces/` is built only
    by `tools/build_surfaces.py`, within its 15 MB budget and with its ledger.
- **Sound effects** (`tt_shorts/sfx.py`, `tools/compose_sfx.py`, format key `sfx`, default off): cues come from the
  timeline, one constant level, mixed in ffmpeg like the music; no ducking, no risers. `sfx: meaning` places one main and 2-4
  small sounds on the film's main moment and its turns, none on a transition; `music_hits.py` starts the loop so a heavy
  hit lands on that moment, at the same level.
- **Icons** (`tt_shorts/icons.py`):
  - `assets/icons/lucide.json` is built only by `tools/build_icons.py`; Lucide's `LICENSE` (ISC) stays beside it.
  - A new Georgian stem goes in `icons._BY_ICON`, and a look-alike word in `_BLOCK`; either needs a case in
    `tests/test_icons.py`.
  - Pictograms follow news rule N10: a sign's verb is said in its part of the narration, and there are none for
    crime, incidents or deaths. Icons are drawn in ink; the accent is only the dot.
- **Captions** are laid out in Python (`captions.py`, fontTools on the real woff2), never measured in the render tabs.
  One size per video, pages ≥ 1 s, gaps under 1.2 s bridged, position a pure function of time. `tests/test_captions.py`
  holds the jitter rules; a caption change needs a case there.
- **Tests:** `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. A change to dates,
  rules, anchors or the safe zone needs a test.
- **Visual changes** (scenes, looks, captions, `brand.ts`): `python -m tt_shorts.engine selftest` before merging
  (golden stills + the layout probe in every look); `--update` only for a change you meant, committed with it.
  Text in a component is marked by region (`data-probe`) so the probe can judge it; keep new chrome inside one.
- Text on screen is in Georgian. Code, comments and commits are in English.
