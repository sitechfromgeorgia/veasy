# Veasy roadmap: from one news Short to a general generator

Written 2026-11-02 from two research passes (visual building blocks; engine and product layer). It is the shared plan
for the owner, the agents and whoever codes it. Ranked: quick wins first.

**Done on 2026-11-02** (the owner: "the system must not belong to one project"):
- **Brand packs** (`brands/`, `tt_shorts/brand.py`): every client-specific thing is data; `tbilisi-today` and
  `sitech` ship, `brands/_ka` is the Georgian base. Remotion draws from `props.brand`.
- **Storage and names** (`tt_shorts/store.py`, `$VEASY_HOME`), retention with `engine gc`.
- **The job queue** (`tt_shorts/queue.py`, B4 below in a simpler form): idempotent jobs, states queued → writing →
  rendering → done / held / failed, transient retries with backoff, one worker per machine.
- **Sources** (`tt_shorts/sources/`): `tbilisi-today` and `text`.
- A4 and A6 below.
- **New scenes and transitions** (the owner, 2026-11-02): `draw` ported from sitech-shorts (the writer's drawing,
  sanitized into a tree and animated by frame), `pair`, `steps` (C6), `bars` (C4), `trend` (C5), `change` (C3, as a
  roll-up rather than an odometer), and C1 transitions as a format key. A1 (numbers at any depth in N2) and a light A2
  (counts and number types per new scene in `engine.shape_problems`).

- **Variety** (the owner, 2026-11-02: "1000 videos in one style"): `tt_shorts/variety.py` (hook layouts, motifs,
  entrances, transitions, music loops; least used per brand), the writer told the recent scene orders, drawings on
  with `art.quality` and a drop-not-fail fallback, four music loops per family.

Next for other clients:
- **B12. The writer per pack.** `writer.py`'s prompt is written for multi-source news (tbilisi.today). A pack
  should name its writer style (news cluster, blog post, product update) so `write --brand sitech` writes from a
  SiTech post the way sitech-shorts does. Until then a SiTech story is written by the agent and queued with
  `--story`.
- **B13. A `sitech` source.** Read a post from sitech.ge (RSS + the page's ld+json, as sitech-shorts'
  `articles.py` does), so `queue add --source sitech --ref <slug> --brand sitech` works end to end.

## Decisions only the owner can make (blocking some items)

1. ~~**Remotion licence.**~~ Owner's decision (2026-11-02): no licence is bought. Remotion's terms make it free for
   companies of up to 3 people (contractors count); if the team grows past that, revisit.
2. **Narration length:** one number for all of these: rule N9 says 55-70 words, `writer.SCHEMA` 70-95, the
   make-video skill 55-75.
3. **World map point of view** (needed only for item C9):
   - The common open data (Natural Earth / world-atlas) draws Crimea as Russia; it does keep Abkhazia inside Georgia.
   - Either use a de jure point-of-view file, if one fits, or patch the data. This is an editorial call.

## A. Fix first (small, prevents silent errors)

- ~~**A1. Nested numbers in N2.**~~ Done (`news_check._walk`).
  - `news_check.screen_text()` reads only strings and a top-level int `value`.
  - A future `items:[{value:1450}]` would skip the number check.
  - Read every number at any depth; add a test.
- **A2. A typed scene spec.**
  - `engine.structure_problems()` checks only that fields exist.
  - Give each field a type, a length, an enum or a count, e.g. `"items": ["list", 2, 5, {"label": ["str", 18], "value": "num"}]`.
- **A3. One source of truth for the scene vocabulary.**
  - Today a new scene type must be added in 7 places: `news_check.SCENE_TYPES`, `ka_check.FIELDS`/`MIN_WORDS`,
    `speech.MIN_SCENE`, the `writer.py` prompt, `types.ts`, `engine.SCENES`/`options()`, and the skills.
  - Generate them from one spec (see B6).
- ~~**A4. The daily run through the engine.**~~ Done: `ops/daily.py` queues its picks; the queue renders and runs QA.
  - `ops/daily.py` calls props directly, ignores formats, runs no `qa` and only checks the file size.
  - Route it through `engine render` + `engine qa`, and hold anything that fails QA.
- **A5. The cost ledger.**
  - `writer.py` logs no tokens.
  - Nothing calls `costs.paid_allowed()`, so the monthly limit is not enforced.
  - Log every model call and gate paid voices on the limit.
- ~~**A6. The voice cache keeps one voice per story.**~~ Done: `cache/voices/<sha16>/` per (engine, voice, style, text).
  - Switching the tone overwrites it.
  - Make it content-addressed (`work/voices/<sha(engine|voice|style|spoken)>/`), so trying tones and looks is free
    after the first time.

## B. Engine and product layer

- **B1. A render server (S-M; the biggest speed win).**
  - Each render or still now runs `npx remotion`, which rebuilds the bundle.
  - Measured in the sandbox:
    - a CLI still takes 13-19 s;
    - with one bundle and one open browser: 11.5 s once, then 7 stills in 2.8 s;
    - about 17 fps full size and 25 fps half size at concurrency 3.
  - `remotion/render-server.mjs`: `@remotion/bundler` `bundle()` once (rebuilt when `src/` changes), then
    `@remotion/renderer` `selectComposition`/`renderMedia`/`renderStill` for JSON jobs on stdin or 127.0.0.1.
  - It supports `scale: 0.5` previews, `onProgress` and `cancelSignal`.
  - Render one video at a time (Remotion's advice). Prepare the next voice while a video renders. Keep the CLI as a
    fallback.
- **B2. `engine plan`, a free storyboard (S).**
  - Returns timings, words per scene, caption pages, and a half-size contact sheet of mid-scene stills.
  - Costs no voice; about 15 s with B1. The agent and the owner review this before paying for a render.
- **B3. Outputs that cost no extra voice (S).**
  - SRT/VTT subtitles from `words` and the caption pages.
  - A cover PNG (`renderStill`).
  - A 6-10 s teaser: the hook plus the end card, using `renderMedia` `frameRange` and a word-timed cut of the same
    voice.
  - A Telegram album of stills.
- ~~**B4. A jobs table (S-M).**~~ Done in a simpler form (`tt_shorts/queue.py`, `veasy.db`); still open: the git
  commit in the id, cost rows with the job id, a `published` state.
  - `jobs` in `state.db`. The id is a hash of spec, format, output, voice engine and git commit, so the same request
    returns the same file.
  - States: planned → voiced → framed → mixed → qa_ok/qa_failed → published/held.
  - Error classes as in sitech-shorts: transient, content, layout, config.
  - Cost rows carry the job id. This replaces `out/daily-state.json`.
- **B5. A free quality score (S-M):** clipped text is done, without OCR: the layout probe (D13) reads every text's
  real box from the page, so no Tesseract is needed. Still open:
  - ffmpeg `silencedetect` (on the voice track before the mix: the music hides a gap), `freezedetect`;
    `blackdetect` does not suit a dark canvas;
  - reading load (words and characters per second per scene; the probe already has the scene's text and length);
  - `voice_qa` in the score.
- **B6. One versioned spec (M).**
  - Grow the story JSON into `{spec_version, program, data_ref, narration, say, segments:[{component, at, props}]}`.
  - Write a zod schema per component in `remotion/src/spec/` (zod 4 is already present; add it explicitly).
  - Export `schema/spec.vN.json` with `z.toJSONSchema`; the Python checks, the writer prompt and
    `engine options` all read it. Attach it to `<Composition schema>` so the controls show in Studio.
  - Data-owned fields (id, date, sources) stay out of the writer's schema, so N6 holds by construction.
  - Add an upgrader for v1 stories.
  - Keep the `at` anchors; avoid absolute track times, free x/y/colour fields and LLM-written TSX.
- **B7. Daily digest, "5 stories in 60 s" (M).**
  - Code joins 5 hooks that already passed their checks: one TTS call (~$0.015) and no LLM. A weekly recap works the
    same way.
- **B8. An MCP server (S, after B4).**
  - `tt_shorts/mcp_server.py` (FastMCP, stdio) with options, check, plan, render, status and qa.
  - Remotion has no official MCP. Its Agent Skills (`remotion-dev/skills`) are for developers, not for the news agent.
- **B9. Data cards without an LLM (M):**
  - "figure of the day" from the site's entity pages (initials, no photos);
  - weather (Open-Meteo, as tt-web uses);
  - NBG exchange rates;
  - a weekly quiz built from checked stories.
- **B10. Other aspect ratios (M-L).**
  - `layouts.ts` with bands per ratio and several `<Composition>`s sharing one component.
  - `calculateMetadata` returns the size per composition. Do 4:5 first, then 16:9 and 1:1; this touches every scene.
- **B11. Analytics and A/B (after publishing).**
  - Sources: YouTube `audienceWatchRatio` × `elapsedVideoTimeRatio` (Shorts filter), IG `ig_reels_avg_watch_time`,
    TikTok `average_time_watched`.
  - Lay retention over each job's scene timeline. Formats are the A/B arms, assigned by story-id hash; judge only
    after 30+ videos per arm.

## C. Visual building blocks (the agent fills small JSON; code draws)

- **Rules for every block:**
  - Heavy work (layout, projection, cue frames) runs in Python.
  - Remotion animation is a pure function of the frame.
  - Brand v1.2: one red, only for the dot, an active state or the CTA.
  - Every number on screen must come from the articles.
- **Packages at 4.0.539:**
  - **Use:** `@remotion/paths` (MIT) and `@remotion/shapes` (MIT). Optionally `layout-utils`, `animation-utils`
    and `noise`.
  - **CSS transitions are fine:** fade, slide, wipe, flip, clockWipe, iris, pushCut.
  - **Skip:**
    - the 12 shader transitions (they need a Chrome flag);
    - `TransitionSeries` overlaps, which shorten the timeline and break the voice anchors;
    - motion-blur (multiplies the CPU cost);
    - light-leaks (colour);
    - lottie and rive (authoring tools; licence and brand risk);
    - three (WebGL on CPU).
  - Check the licence of `@remotion/transitions` (its package.json says UNLICENSED).

1. ~~**C1. Transitions as a format key (S).**~~ Done.
   - `"transition": "auto|cut|line|panel|wipe|slide|push|dot"`, drawn with clip-path and transform.
   - `dot`: the progress dot drops and an ink iris opens from it.
   - Wire it into `formats.validate`, `options()` and the formats skill.
2. **C2. Emphasis synced to the voice (S-M; the most visible gain per unit of effort).**
   - `"em": "6400 აბონენტს"` on any scene. `speech.py` resolves the phrase to a frame from the word timings.
   - At that frame an ink block sweeps behind the phrase and the red dot lands at its end.
   - The same cue mechanism reveals list items as they are spoken.
3. ~~**C3. Odometer numbers and a `change` scene (S).**~~ Done (`change`).
   - `{"type":"change","from":{"label":"2024","value":1.2},"to":{"label":"2025","value":1.5},"unit":"ლარი"}`.
   - No computed differences (N2). `pct` is allowed only when the article states it.
4. ~~**C4. `bars` / `results` (S-M).**~~ Done (`bars`).
   - 2-5 items, one unit, values above zero, a linear axis from zero.
   - Bars grow as they are spoken.
   - An optional threshold line only if the article states it; no party colours.
5. ~~**C5. `trend` (S-M).**~~ Done (drawn with pathLength, no extra package).
   - 3-8 points.
   - `evolvePath` draws the line; the red "now" dot sits on the last point.
6. **C6. Small blocks (S each):** `steps` done; the rest open:
   - `events`: 2-4 dated items on a rail;
   - `steps`: 2-4 steps with arrows;
   - `figures`: 2-4 number tiles;
   - `share`: a 10×10 grid, only for percents stated in the article; replaces a pie.
7. **C7. Icons from a whitelist (M).**
   - About 80 Lucide (ISC) or Tabler (MIT) icons, with a Georgian keyword map (გაზი→flame, დენი→zap, მეტრო→train-front…).
   - They draw on with `evolvePath`.
   - Off for the crime family and for deaths.
8. **C8. Georgia region map (M).**
   - geoBoundaries ADM1 (12 units, CC BY 3.0: needs a small credit), projected once to ~30 KB of SVG paths.
   - Georgian names from Wikidata (CC0).
   - `"area": "ge:imereti"` on `where`.
   - Tbilisi districts: a hand-made schematic (ours, no licence) rather than OSM (ODbL credit).
9. **C9. World map and `route` (M-L), after decision 3.**
   - Gazetteer keys from Natural Earth populated places (public domain).
   - An arc draws on and the red dot rides it.
   - No distances unless the article states them.
10. **C10. `link` diagram, who meets whom (M).**
    - The `verb` must appear in the narration, so no relationship is implied that the article didn't state.
11. **C11. `compose` layout grammar (L, last).**
    - Up to 3 layouts (top-bottom, split, grid) with fixed slots inside the safe zone.
    - The validator rejects combinations that don't fit.

## D. Fifteen ideas from three research passes (2026-11-02)

The owner asked for 3 agents with 5 ideas each: visuals and motion, audience and formats, engine and agent tooling.
Kept here so they outlive the session. Two facts from the research change priorities:
- YouTube's July 2025 "inauthentic content" rule makes channels of videos "made from a single template with
  minimal differences" ineligible for monetization
  ([TechCrunch](https://techcrunch.com/2025/07/09/youtube-prepares-crackdown-on-mass-produced-and-repetitive-videos-as-concern-over-ai-slop-grows)).
  Variety is a requirement, not a taste.
- Instagram allows 50 API posts per rolling 24 h, exactly today's daily volume
  ([Meta](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit)).

Visuals and motion:
1. **Drawings, checked by picture:** a CLIP (open_clip ViT-B/32, MIT, CPU) yes/no on a late still ("a line drawing
   of a {motif}" against decoys), plus a library of drawings that passed, reused per motif when a new one fails.
2. **Art direction from the story's content** (beyond variety.py): compositions (a number running off the edge,
   asymmetric stacks), word-by-word type on the voice timings, noise textures (`@remotion/noise`, MIT), a slow
   camera drift; a perceptual hash of contact sheets re-rolls a video too close to a recent one.
3. **Pictogram grammar (Isotype):** ~250 Lucide/Tabler icons with a Georgian stem map; the writer picks a motif and
   one of 8 verbs (rises, falls, stops, opens, closes, moves, splits, joins); code draws the tiled motif, a `sign`
   scene and counts as repeated icons timed to the spoken number (counts only from the articles).
4. **Real geography:** a Wikidata gazetteer (CC0), Georgia → region → place zooms, OSM street maps of a ~1 km window
   for Tbilisi, Batumi, Kutaisi districts (credit in the corner); the Natural Earth Ukraine point-of-view file for
   the world map (decision 3: check Abkhazia and Tskhinvali stay in Georgia).
5. **One-take camera:** scenes laid on a 2D path; the camera moves only during the cuts (anchors intact), the red
   dot travels the thread (`@remotion/paths`), parallax layers; zoom capped at 1.15 for hard news.

Audience and formats:
6. **Rubrics:** named recurring shows with a shape, a slot and an episode number: „რა იცვლება", „დღის ციფრი",
   „ამბავი გრძელდება · ნაწ. 2" (a cluster that grew since its first video), „ადასტურებს N გამოცემა" (an `agree`
   scene: facts literally in at least N members), „დილის 3 ამბავი" (the B7 digest at 08:00).
7. **Built for the swipe and the loop:** the hook fully on screen at frame 0 (today the last hook line is readable
   at ~0.7 s), no dead tail, `outro: card|overlay|loop` as an A/B arm (Shorts count every replay as a view since
   2025-03-31).
8. **Measure, then choose:** a metrics table per job (YouTube engaged views and average view %, Instagram sends and
   saves), Thompson sampling over form only (rubric, outro, hook type, captions, length), drop-off mapped onto scene
   types, politics routed to YouTube, Facebook and Telegram (Meta doesn't recommend political content to
   non-followers), a volume test per platform.
9. **One story, every surface, Facebook first** (88% of Georgians who get news on social media use Facebook,
   IREX/CRRC 2024): `engine package` writes titles and descriptions by code, a 4:5 carousel, a Telegram post and SRT.
10. **„თქვენ იკითხეთ":** viewers' factual questions answered from the articles (anonymized, checked by news_check);
    a weekly Telegram quiz from checked facts.

Engine and agent tooling:
11. **Recipe director with a novelty guard** (merges with 2): fingerprints of recent videos, re-roll before the
    voice is paid for, a bandit over recipe dimensions fed by retention with an exploration floor.
12. **Programs: any source in, many outputs out:** url (trafilatura), pdf, github-release, csv/sql sources; rule
    tiers news / claims / data; deliverables: carousel, audiogram, EN/RU versions with identical facts, a two-voice
    dialogue (Gemini multi-speaker TTS); `publish: auto|review` per program.
13. ~~**Self-checking renders:**~~ Mostly done (2026-11-02): the layout probe (`tt_shorts/probe.py`: band, rail,
    captions, frame, overflow, glyph, font, size; every render, a problem holds the job), golden stills
    (`engine selftest`, `tests/golden/`), the failures table that feeds the writer (`tt_shorts/failures.py`,
    `engine learn`). Still open: a vision rubric that can only hold (Workers AI vision, two calls must agree), and
    retiring variety options that fail often (`failures` has the data; `variety.pick` doesn't read it yet).
    What the probe found on its first run, fixed: the cards' page count and any `low` width in a card reached under
    the like/share rail (a card's content starts 32 px further right); a long `where` place or sub line crossed the
    rail, and in a card its sub line sat on the card's footer; a long CTA crossed the rail; and a frame could be laid
    out before the brand font loaded, so text sized by measuring got a fallback font's sizes (3 stills in 24; now
    `remotion/src/fonts.tsx` holds the layout until the four weights are in). Not fixed: the FiraGO subset has no
    lari sign ₾ (normalize_ka speaks "₾5"; on screen it would be another font's glyph: the probe flags it).
14. **Publishing with a canary window and a watchdog:** states scheduled → published → unlisted; a Telegram ⛔/✅
    window before auto-publishing; re-check the source at +1 h, +6 h, +24 h and unlist when the cluster is gone or
    the facts no longer hold; start the TikTok audit now.
15. **Scene kit:** scenes as JSON (typed slots, layout grid, motion presets) drawn by one component, registries
    generated from them (solves A3), a fuzz gate in every look × brand, `trial` until the owner approves an album.

## One combined first week

| Day | Work |
|---|---|
| 1 | A1 nested-number N2 + tests; A2 typed scene spec; C1 transition format key |
| 2 | B1 render server (CLI fallback) and a concurrency benchmark on the server; B2 `engine plan` |
| 3 | C2 voice-synced emphasis; C3 odometer + `change`; A6 content-addressed voice cache |
| 4 | C4 `bars`, C5 `trend` (add `@remotion/paths@4.0.539`); B3 SRT/VTT + cover + teaser |
| 5 | A4/A5 daily through engine + QA gate, ledger, `paid_allowed`; skills/options/writer prompt updated; stills of every new block in all 3 looks; render time before/after |

## Not verified (check before relying on it)

- Server CPU and speed: all timings above are from a 4-vCPU sandbox.
- Licensing and data: current remotion.pro prices; the `@remotion/transitions` licence; which Natural Earth
  point-of-view files exist; OSM Tbilisi district polygons; whether ADM2 boundaries match today's municipalities.
- Platform analytics: YouTube and TikTok analytics field names (third-party docs).
- On the server: Tesseract `kat`; the NBG API; whether the free models accept a JSON-schema response format.
