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
- **Entry point:** `python -m tt_shorts.engine` (options, check, plan, render, still, qa, probe, write, queue, gc,
  voices, doctor; JSON out). `plan` is the free storyboard to run before paying for a voice.
  The skills in `skills/` say how an agent uses it. Keep the engine, the skills and `options` in step: a new
  choice in code must appear in `engine.options()`, `formats.py` validation and the `veasy:formats` skill.
- **A new scene type** goes in all of these (`tests/test_scenes.py` and `test_engine.py` check the first three agree):
  `engine.SCENES` (+ `shape_problems`), `news_check.SCENE_TYPES`, `remotion/src/scenes` (`SCENES`), `types.ts`,
  `ka_check.FIELDS` / `MIN_WORDS`, `speech.MIN_SCENE`, the `writer.py` schema and the `veasy:write-script` skill.
- **Variety is a rule** (owner, 2026-11-02: "1000 videos in one style is no good"). `tt_shorts/variety.py` gives
  each video its own hook layout, background motif, entrance, transition and music loop (the least used lately per
  brand, remembered in `veasy.db`), and the writer sees the scene orders used lately. A new layout or motion goes in
  as one more option there (and in `remotion/src`), never as a replacement of the others; `tests/test_variety.py`
  checks a run uses every option evenly. The writer draws (`art.py`: sanitize + quality; a failing drawing is
  swapped for a library one of its motif, `drawings.py`, else dropped, not the video); `VEASY_WRITER_DRAW=0` turns
  it off. A new seed drawing in `assets/drawings/` must pass both (`tests/test_drawings.py`).
- **Motion rules** (`tt_shorts/motion_rules.py`): warnings in `engine plan`; only unreadable text (0.5 s + 0.3 s a
  word) holds a render. A new rule needs a case in `tests/test_motion_rules.py`.
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
  - `assets/maps/georgia.json` is built only by `tools/build_georgia_map.py` (sources and licences in
    `assets/maps/README.md`).
  - Georgia has its 12 regions of Georgian law: Abkhazia and the Tskhinvali region are part of Georgia, drawn as
    no separate entity.
  - For the crime family the map stops at the region and marks no district (`geo.PRIVATE`,
    `tests/test_geo.py`).
- **No publisher photos:** tbilisi.today has no reuse grant (tbilisi.today repo: `ingest/src/story-cover-assets/README.md`).
- **Music** is composed by `tools/compose_music.py`; the m4a files are not in git. One constant level: no build-ups,
  no ducking (the owner heard the ducked bed pump). The mix happens in ffmpeg (`props.mix_audio`), not in Remotion.
- **Voices:** shared presets in `voices.py`; a pack's own in its `voices` (SiTech's `Charon` lives only in
  `brands/sitech`). edge-tts is a preview stand-in only.
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
