# Veasy

**Veasy** is SiTech's video engine for agents, the sibling of [kaeasy](https://github.com/sitechfromgeorgia/kaeasy):
kaeasy handles Georgian writing, Veasy handles video.
- **What it does:** turns a story into a checked, voiced, captioned vertical video (1080×1920). It uses Remotion
  frames, a Gemini TTS voice with word-level alignment, composed music and an ffmpeg mix.
- **Where it is going** ([docs/plan-v2.md](docs/plan-v2.md)): a general engine that belongs to no client, with two
  first-class renderers, Remotion and HyperFrames, and both products' own agent skills installed beside Veasy's.
  An agent can then make any video (news, explainers, data pieces, animated stories, product films), composing its
  own forms and templates, while Veasy supplies the voice, captions, media, music, mix, checks and queue.
- **For any client:** what makes a video one client's (colors, logo, link, footer, voice, categories, words) is a
  **brand pack**, a folder in `brands/`. Shipped: `tbilisi-today` (the default) and `sitech`. A new client is a new
  folder, no code.
- **Who drives it:** an agent, through formats it can choose and extend and a **job queue** that makes each video
  once, retries what failed for a passing reason and keeps every file in one place under one naming scheme.
- **Built-in quality gates:** news integrity rules, Georgian quality through kaeasy, caption stability, and renders
  that check themselves (a layout probe on every render, golden stills, a memory of what failed).
- **First client:** [tbilisi.today](https://tbilisi.today), daily Georgian news Shorts from multi-source stories
  (D1 story clusters, read only).
- **Layout:** the repo root is a Hermes plugin (`plugin.yaml`, `__init__.py`, `skills/`), like kaeasy. Claude Code
  sees the same skills through `.claude/skills/` (symlinks).

## Install as a Hermes plugin (next to kaeasy)

```bash
git clone https://github.com/sitechfromgeorgia/veasy /root/.hermes/shared-plugins/veasy
ln -s /root/.hermes/shared-plugins/veasy /root/.hermes/profiles/<profile>/plugins/veasy
bash /root/.hermes/shared-plugins/veasy/ops/install.sh --align    # the engine's own venv, Remotion, music, data/.env
# enable it (hermes plugins enable veasy, or plugins.enabled in config.yaml), restart the gateway, check: hermes plugins list
```

What the agent gets:
- **Tools:** `veasy_options`, `veasy_check`, `veasy_render`, `veasy_still`, `veasy_qa`, `veasy_probe`, `veasy_plan`,
  `veasy_package`, `veasy_write`, `veasy_rubrics`, `veasy_queue`, `veasy_compose` and `veasy_doctor`.
  - Each runs the engine in its own venv and returns its JSON.
  - A render takes a minute or two; the agent needs none of the render libraries.
- **Skills:** `veasy:make-video`, `veasy:write-script`, `veasy:qa`, `veasy:package`, `veasy:formats`, `veasy:queue`,
  `veasy:brands`, `veasy:programs`, `veasy:directors`, `veasy:rubrics`, `veasy:media`, `veasy:compose`; and the
  engines' own (`ops/install.sh --skills --profile <profile>`: Remotion's `remotion-*`, HyperFrames'
  `hyperframes` and `hyperframes-cli`, pinned).
- **A one-line hint** on the first turn; turn it off with `VEASY_HINT=0`.

Frames are rendered with [Remotion](https://github.com/remotion-dev/remotion) (React; `remotion/`). Python
(`tt_shorts/`) handles the voice and its word timings, the scene timing, the rules, the data, the brand packs, the
queue and the storage. Forked from `sitechfromgeorgia/sitech-shorts`: the Georgian normalisation, the K rules, the
music composer and the timing code. It runs on the tbilisi.today agent server (84.46.250.149).

## The engine (start here)

One entry point for people and agents; every command prints JSON (`tt_shorts/engine.py`):

```bash
python -m tt_shorts.engine doctor                                  # is this machine ready? (brands load, keys, tools)
python -m tt_shorts.engine options [--brand sitech]                # every choice: brands, looks, captions, voices, music, formats, scenes
python -m tt_shorts.engine write  --source tbilisi-today --ref 24886 [--brand tbilisi-today]
                                                                   # a story from a source -> stories/<brand>/<day>/<ref>.json
python -m tt_shorts.engine write  --program law --source ordo --ref constitution:17   # any source in: explainer, law, blog
python -m tt_shorts.engine check  <story.json> --sources <story>.sources.json
python -m tt_shorts.engine render <story.json> --format news [--look kinetic] [--captions roll] [--voice warm] [--outro loop]
python -m tt_shorts.engine still  <story.json>                     # one PNG per scene, no video
python -m tt_shorts.engine qa     <file.mp4>                       # size, length, loudness, the probe + a contact sheet
python -m tt_shorts.engine probe  <story.json> [--look all]        # where every text really is, per scene (free)
python -m tt_shorts.engine plan   <story.json> [--look kinetic]    # a storyboard before paying for a voice (free, ~5 s)
python -m tt_shorts.engine selftest [--update]                     # golden stills: run before merging a visual change
python -m tt_shorts.engine learn  [--brand sitech]                 # the rules failing most lately
python -m tt_shorts.engine package <file>.json [--only srt,texts]  # one render -> every surface (below), no new voice
python -m tt_shorts.engine queue  add --ref 24886 | list | run | show <id> | retry <id> | cancel <id>
python -m tt_shorts.engine gc     [--dry-run]                      # retention (below)
python -m tt_shorts.engine voices --story <story.json>             # Gemini tone samples, by ear
```

- **Two film engines** (`tt_shorts/compose.py`, skill `veasy:compose`): a video's `"engine"` is `remotion` (the
  brush kit below) or `hyperframes` (a film the agent composes in HTML/CSS/GSAP, HyperFrames 0.9.8 pinned in
  `compose/`): the director's, else the program's, else the format's, else the pack's, else remotion; `engine render`
  follows it (`--renderer` overrides). Both get the same voice, captions, pack, mix, checks, QA and queue.
  ```bash
  python -m tt_shorts.engine compose scaffold <story> [--brand sitech] [--template auto] [--from DIR]  # a project
  python -m tt_shorts.engine compose check    <story> [--sources <story>.sources.json] [--shots DIR]   # every check
  python -m tt_shorts.engine compose look     <story> [--video FILE]             # free: its sheets and timeline
  python -m tt_shorts.engine compose render   <story> [--engine silent]          # pinned render, mix, QA
  python -m tt_shorts.engine compose promote  <project> --as <id>                # an approved film -> templates/<id>
  python -m tt_shorts.engine review <story> [--rounds 2] [--stills DIR] [--packet]  # the film's eyes: free checks, capped repair loop, facts untouched
  ```
  - The project (`$VEASY_HOME/cache/compose/<brand>-<ref>/`) holds the agent's `index.html`, `compositions/*.html`
    and `beats.json`, and Veasy's files: `frame.md` and `assets/brand.css` from the pack, `facts.json`,
    `timing.json` (the voice's words, the chapters, the beats), `assets/vendor/veasy.js` (`VEASY.fact`,
    `VEASY.at`), the locked `chrome.html` and `captions.html` (v2, hashed in `.veasy/lock.json`).
  - **Facts are bound, not typed**: a scene shows a number, date, name, quote or source through
    `data-var-text="<fact id>"` (HyperFrames variables declared from facts.json); hosts are timed by beats
    (`data-beat`, `data-until`), so a film keeps its timing under another voice.
  - **`compose check`**: our lint (no typed color, font, link or fact; nothing from the network; no canvas/WebGL
    text; every text in a `data-probe` region; the chrome hosted and unchanged), the layout probe at every beat's
    settled frame (`compose/probe.mjs`), the story's rule tier + K rules + kaeasy on every text the DOM shows, and
    `hyperframes check`. Problems hold the film; a film that would fetch, hide text or lose its chrome is not
    rendered.
  - **`compose look`**: the film as a viewer gets it, before any voice is paid for: a sheet of its scenes and beats, a
    strip across every cut, the frames at phone width, its timeline and, with a rendered file, its sound
    (`hyperframes snapshot --review`, `keyframes`, `audio`, on this machine). The skill starts from an idea
    (`STORYLINES.md`, `SPEC.md`) and ends with a fresh eye's notes on those sheets (`REVIEW.md`).
  - **Render**: `hyperframes render` with pinned settings (4 workers, software GL, `--quality looks`, 30 fps),
    then `props.mix_audio`, QA and the same result JSON as `engine render`. HyperFrames only runs through
    Veasy, with telemetry, update checks, skill installs and auto-installs off; `publish`, `cloud`, `lambda`, `tts`,
    `media-use`, `feedback`, `add` (and other upload or fetch commands) are refused.
  - **Review tier**: a composed film that passed QA ends `held` (error_class review) until a person
    `queue approve`s or `reject`s it, unless its format's or program's `review: until:<n>` lets a brand's films
    through after n approved in a row (default `always`).
  - **Templates**: `compose promote` turns an approved film's facts and typed words into slots
    (`templates/<id>/manifest.json`); `compose scaffold --template <id>|auto` (least used for the brand) starts a
    new film from it.
  - Demos: `compose/24835` (the gas cut, in either pack) and `compose/bipi-draws` (program `story`: a fable about a
    small robot learning to draw, brand sitech).
- **The engines' own skills**: `bash ops/install.sh --skills --profile <name>` (or `--target DIR`) installs, pinned,
  Remotion's `remotion-*` skills (remotion-dev/skills at a fixed commit, through `npx skills@1.7.6`; never copied
  into this repo: it has no licence file) and HyperFrames' `hyperframes` and `hyperframes-cli` from the pinned npm
  package (`media-use` left out). `veasy:make-video` says which way a request goes and which skill wins where they
  overlap (captions: `captions.py`; media: Veasy's media layer).
- **Formats** (`tt_shorts/formats.py`, `formats/*.json`): a show is a named set of choices (look, captions,
  transition, outro, voice, music, platform, length window). Built-in: `news`, `news-roll`. A new show is a JSON
  file, no code. Which show uses which format is the owner's and the agent's decision. A format works for every
  brand.
- **Sources** (`tt_shorts/sources/`): where a story's facts come from. `tbilisi-today` (ref = a D1 cluster id),
  `text` (ref = a JSON file `{"cluster": {...}, "articles": [...]}`, for any client), `url` (a web page: trafilatura
  or a stdlib extractor), `pdf` (pypdf or pdftotext), `ordo` (Georgian law from matsne.gov.ge through
  [Ordo](https://github.com/sitechfromgeorgia/ordo-mcp)'s `matsne_api.py`, `ORDO_DIR`; ref `constitution:17`) and
  `sitech` (a sitech.ge blog post by slug). A new source is one module with `fetch(ref)`.
- **Programs** (`tt_shorts/programs.py`, `programs/*.json` + `programs/briefs/`): what a video is made from and
  what it may claim. `news` (the default, unchanged), `explainer` (any document, 30-45 s), `law` (one article of
  Georgian law), `blog` (a SiTech post) and `story` (fiction composed for HyperFrames: tier `story`, S1 "no real
  person": every name is one of the story's `characters`). A program names its sources, the writer's brief, its scene types, a rule
  tier (`news`; `claims`: every number, name and quote in the document; `law`: claims plus the article number on
  screen, the act named and no advice; `tt_shorts/claims_check.py`), its default format and `publish: auto|review`
  (review jobs end `held` for a person). A new program is a JSON file and a brief. Skill: `veasy:programs`.
  `stories/law-constitution-17.json` is a law example (article 17 of the Constitution, fetched through Ordo).
- **One story, every surface** (`tt_shorts/package.py`, `veasy:package`): from a finished render, with no TTS and
  no model call, `<render>-package/` gets `captions.srt`/`.vtt` (the video's caption pages), `cover.png` (the hook
  at its most complete frame), a 4:5 carousel `carousel-01..0N.png` (5-7 slides, Remotion composition `Slide`:
  each scene's own component at its final frame, checked pixel by pixel for anything outside its box),
  `teaser.mp4` (6-10 s: the hook and the end card, cut by ffmpeg), `texts.json` (YouTube title and description,
  Instagram, Facebook and TikTok captions, by code, through `ka_check`'s screen rules) and `telegram.md`. The
  pack's `package` key holds the words and hashtags.
- What comes next (new visual blocks, render server, more outputs, the decisions needed): [ROADMAP.md](ROADMAP.md).
- **Georgian gate: [kaeasy](https://github.com/sitechfromgeorgia/kaeasy)** (`tt_shorts/kaeasy.py`).
  - It is loaded from the plugin folder every agent shares (`KAEASY_DIR`), so a new rule there reaches the videos.
  - Each text gets its own mode: the narration is checked as an article, the on-screen text as social copy, and
    the spoken text as speech.
  - kaeasy's strict rules block a render; the rest come back as `warnings` from `engine check`.
  - The writer reads kaeasy's ten most-broken rules and the fleet's frequent mistakes before it writes (free).
  - The editor's fixes go back into the shared memory.
  - `SHORTS_REQUIRE_KAEASY=1` on the server: no gate, no video.

## Storage and names (`tt_shorts/store.py`)

One home, `$VEASY_HOME` (default `<veasy>/data`; `SHORTS_DATA` is still read), with the same layout on every machine:

```
.env                                         secrets (chmod 600), never in git
veasy.db                                     the job queue, the cost ledger, variety and failures (SQLite)
stories/<brand>/<day>/<ref>.json             a story; <ref>.sources.json beside it (the articles)
renders/<brand>/<day>/<ref>-<format>-<look>-<captions>.mp4   + .json (what was rendered) + .sheet.jpg (QA)
                                             + .props.json (what Remotion drew) + -package/ (engine package)
                                             + .plan.jpg (engine plan's contact sheet, made before the render)
cache/voices/<sha16>/                        one voice per (engine, voice, style, spoken text): re-renders are free
cache/work/<job>/                            render scratch, deleted after a good render
cache/bundles/<sha16>/                       the Remotion bundle per version of remotion/src (probe, selftest)
cache/media/<sha16>/                         the media layer: one search's candidates, or one fetched picture + its
                                             ledger entry (assets.py)
cache/compose/<brand>-<ref>/                 a composed film's HyperFrames project (engine compose), 30 days
logs/<day>.jsonl                             one JSON line per event (queued, written, rendered, failed, gc)
```
Names are lowercase ASCII with hyphens (Georgian and spaces become hyphens); `day` is the server's date. A job is
`<brand>-<ref>-<format>`, e.g. `tbilisi-today-24725-news`. Retention (`engine gc`, safe for cron): scratch 2 days,
bundles 14, renders 30, voices, media and logs 90; stories are kept, they are the record of what was published.

## The queue (`tt_shorts/queue.py`)

A job is one video: (brand, source, ref, format, overrides); its id is a hash of exactly that, so the same request
twice is the same job. `queue run` takes the oldest highest-priority job, writes the story if it has none, checks
it (news rules, Georgian, kaeasy), renders, runs QA and ends `done` (ready to publish) or `held` (QA or layout
probe problems, or a preview voice; a person looks). Errors are classed: `transient` ones (network, 429, 5xx) are re-queued after 5, 10 and 20 minutes;
`config`, `content`, `layout` and `render` ones fail with the reason, for a fix and `queue retry`. One worker at a
time per machine (a lock), so cron can call `queue run` every few minutes. `ops/daily.py` picks the day's
tbilisi.today stories and queues them.

## Renders that check themselves (`probe.py`, `golden.py`, `failures.py`)

About fifty videos a day go out without a person looking, so the engine looks for what a person would catch.
- **Layout probe** (`tt_shorts/probe.py`, `remotion/src/Probe.tsx`, `remotion/probe.mjs`): every render first
  renders each scene's settled frame (entrances done, exit not begun) in one browser, and the page reports the real
  box of every text it draws. The rules: scene text inside 248-1380; nothing right of x=940 below y=1100 (scene
  text and captions); captions above 1552; nothing outside the frame; no text past its box (`scrollWidth >
  clientWidth`, a line on a card's footer); every glyph in the brand font (checked against the woff2's cmap); the
  pack's font, loaded before the frame was laid out; nothing shrunk under 24 px (40 in captions); every text
  readable on what is really under it (its color against the backgrounds and fills the page paints there, read from
  the DOM: 3:1, 4.5:1 for small regular text), so no theme can put dark on dark or light on light. A problem holds
  the job; `engine probe <story> --look all` runs it alone in ~5 s a look (the bundle is cached per version of
  `remotion/src`). `VEASY_PROBE=0` turns it off.
- **Golden stills** (`engine selftest`): the two fixture stories in every look with one fixed style, each scene's
  still hashed (a 16x16 dHash of the frame and a 32x32 one of the scene band) and compared with `tests/golden/`.
  It names the scenes that changed and fails on any probe problem; `--update` accepts a deliberate change. The
  fixtures are drawn in their own pack's default theme and again in `golden.THEMED` (sitech's `light`:
  `<story>.sitech-light.<look>.json`); `--theme default|sitech:light` picks. Run it
  before merging a visual change; it is not a unit test (half a minute).
- **Failure memory** (`failures` in `veasy.db`): every failed check (the writer's passes, the checks, render and
  QA problems, errors by class) is a row (ts, brand, stage, rule, message). `engine learn` lists the rules failing
  most lately; the writer's prompt carries the brand's recent mistakes (`failures.prompt_block`).
- **A storyboard before paying** (`engine plan`, `tt_shorts/plan.py`, tool `veasy_plan`): with the silent engine's
  estimated timings and no model call, each scene's times, narration words, caption pages and reading load (every
  text on screen needs 0.5 s + 0.3 s a word), the variety picks the render will get (shown, not recorded: planning
  uses nothing up; `plan.picks()` alone for other code), the motion rules, the layout probe and a half-size
  contact sheet (`<render>.plan.jpg`). About 5 s (20 s when `remotion/src` changed and the bundle is rebuilt).
- **Motion rules** (`tt_shorts/motion_rules.py`, HyperFrames' rules as checks over the timeline): a text on screen
  too briefly to read; more than 3 s with nothing changing (the end card is exempt); more than 3 transition kinds;
  ping-pong cuts (kinds A-B-A in three cuts in a row, or two cuts in a row moving in opposite directions); two
  scenes of one type in a row. Warnings in `plan`; only unreadable text holds a render (in its `problems`, like the
  probe: the job ends `held`).

## Beats and chapters (phase 3 of docs/plan-v2.md)

The reference changes something every 1.5-2.5 s; our scenes had all their text in by 40 % and then held still.
- **Beats** (`tt_shorts/beats.py`, format key `beats: on|off`, on by default): code splits each scene's part of the
  narration at the word timings into beats of 1.5-3 s and gives each a change the scene already draws: a list
  item, a label or a sub line comes in when it is said; a quote's or a point's words light up a phrase a beat;
  the hook's rule, a stat's cell bar, a timeline's run and a map's camera (or the grid's pin) step on. Remotion
  reads `scene.beats` (frames); every device ends where the scene ended before, so the settled frames (probe,
  golden stills) are unchanged. `motion_rules` counts the beats, so `still` is met by construction.
- **Chapters** (`tt_shorts/chapters.py`, format key `chapters: off|on|auto`, off by default, auto from 40 s; the
  digest's format has auto): „01 / 03“ and a segmented bar in the header, chapters of 3+ scenes by code.
- **Keyword captions** (`captions: keyword`) and the **meter** wipe (`transition: meter`; variety offers it in
  editorial and kinetic, the data and type directors allow it).

## Variety (`tt_shorts/variety.py`)

So that a thousand videos don't look alike (the owner, 2026-11-02), each video gets its own combination inside the
brand and the look: hook layout (stack, lead, blocks, underline), background motif (grid, diagonal, dots, rules,
plain, and `icons`, the story's own icon tiled, when it has one), entrance (rise, slide, reveal, scale), transition
(when the format says `auto`) and music loop (four per family, `tools/compose_music.py`). Each choice is the least
used one among the brand's last 20 videos, remembered in `veasy.db`; one story keeps its picks on a re-render. The
writer is told the scene orders used lately and asked for another shape when the facts allow, and it draws a picture
of the story (`art.py`: whitelist + quality check). A drawing that fails is swapped for one from the drawing library
of its motif (`tt_shorts/drawings.py`: every drawing of a video that ended `done`, in `veasy.db`, plus 18 hand-made
seeds in `assets/drawings/`; only the labels the new story itself says are kept), else dropped, not the video.
`variety.report()` measures how alike the last videos were, with the average distance of each to its nearest.

**Novelty guard** (`variety.choose`). Least used per choice still lets two videos share almost everything, so a
planned video has a fingerprint: director, scene sequence, hook, motif, enter, transition, music.
- Similarity counts the shared fields, 1 each, with the scene orders as their difflib ratio. A plan sharing 5 of 7
  with one of the brand's last 20 videos is too close.
- Then its style picks are re-rolled inside the director's subsets, least overused first, at most 64 tries,
  deterministic per story. This happens in `props.choose`, which `props.build` runs before the voice is made, so
  render, the queue, still, probe and `engine plan` all pass it before any TTS (plan shows the fingerprint and the
  closest recent video, and records nothing).
- If nothing is far enough, the farthest plan is taken and the render result carries a warning: it never fails a
  video. A re-render keeps its picks. The distance and the re-rolls are kept in `veasy.db`.

**Directors** (`tt_shorts/directors.py`, `directors/*.json`, `veasy:directors`) decide what kind of film a story
becomes.
- There are eight: data, map, type, draw, chronicle, witness, brief and single.
- One is assigned before the writer runs: the least used eligible one for the brand (`variety.direct`), judged
  from facts code extracts from the articles. Those facts are quantities, dates and times, gazetteer places,
  quotes and their speakers, icons, deaths and the family.
- The writer gets the director's brief, only its scene types, and the fact list. The story keeps `"director"` as
  a code-owned field.
- In the render, the director narrows variety's choices and sets the motion numbers (`ui.tsx` `useIn`/`In`). It
  also sets the current: the slide entrance and every directional cut move one way.
- `--director` on `write`, `render`, `still` and `queue add` overrides it. A story without one renders exactly as
  before.
- `stories/24835-data.json`, `24835-map.json` and `24835-brief.json` are the gas cut as three films with the same
  facts: the number first (stat), the place first (the Tbilisi map, then a sign), and a service card (points, steps).

**Rubrics** (`tt_shorts/rubrics.py`, `rubrics/*.json`, `veasy:rubrics`) are named recurring shows with a shape, a
time slot and an episode number, drawn as a chip in the hook („დღის ციფრი · #12“):
- „დილის N ამბავი“ (08:00, the digest), „რა იცვლება“ (10:00), „დღის ციფრი“ (13:00, 20-25 s), „ადასტურებს N
  გამოცემა“ (16:00, an `agree` scene) and „ამბავი გრძელდება · ნაწ. N“ (18:00).
- Eligibility is data (`{fact: min}` alternatives and `never`), evaluated by code on the facts it finds: big numbers,
  prices, rule words, dates, places, members, the facts 3+ members state alike, and what a cluster gained since its
  last video (every done news job stores what its cluster had). A rubric that doesn't fit is refused before writing.
- The writer gets the rubric's brief and shape; code stamps `rubric`, `episode` (reserved per brand and rubric,
  idempotent per story, released when the job fails) and `part`, never the writer.
- The **digest** (program `digest`, source `stories`) has no writer: code joins 2-3 checked stories' first sentences
  (it opens on the first story's own hook, every later story on a `chapter` card), grows them to 47-57 s and checks
  the whole again; the label states the real count.
- `write --rubric`, `queue add --rubric`, `engine rubrics list|facts|stamp`, `ops/daily.py --rubrics`.
  `stories/rubric-24835-number.json` and `stories/digest-2026-11-01.json` (24835 + 24725) are the demos.

## Pictures and sound effects (`tt_shorts/assets.py`, `tt_shorts/media/`, `tt_shorts/sfx.py`)

The media layer is engine-free: Python resolves every picture into a local file and a ledger entry before the
voice is made, and an engine (Remotion today, HyperFrames next) only draws local files.
- **A hint, not a picture.** The writer may give a scene a `show` hint (a short English query, "gas pipeline
  repair"; or `screenshot`). `engine media <story>` (and `write`, `plan`) searches the pack's providers in order (none by default: a pack opts
  in with `media.providers`),
  picks one per story (seeded by the story, among the best four of the freest licence found: the same picture on
  every re-run; searches are cached), fetches it into `cache/media/` (a photo upright, at most 1920 px) and writes
  the story's code-owned `assets` ledger (`{kind, provider, url, licence, author, title, fetched, sha, file}`) and
  the scene's `media`. A provider that fails leaves that scene without a picture, never fails the story.
- **Providers** (one module each in `tt_shorts/media/`, `search(query, kind, n)` and `fetch(candidate)`):
  Openverse and Wikimedia Commons (no key; per-file licences, only cc0, pdm, CC BY and CC BY-SA, BY-SA picked
  last; Commons files with restrictions are dropped), Pexels and Pixabay (photos and clips, only when
  `PEXELS_API_KEY` / `PIXABAY_API_KEY` is set). Titles of events (fire, crash, police...), of text (maps, charts,
  logos, posters) and portraits are skipped, and a picture's title or tags must name a word of the query.
  `media/ai.py` is the interface for AI imagery, disabled until the owner decides.
- **Screenshots** (`media/screenshot.py`): the chrome-headless-shell Remotion already installs, driven by a tiny
  Node script over the DevTools protocol (`media/shot.mjs`; no Playwright, no new dependency), at 1080x1920, with
  a box around a given phrase. Only pages on the allow-list: the pack's `media.official` and `media.own` and a
  program's `screenshots` (law: matsne.gov.ge), checked before the page opens and after redirects.
- **On screen** (`remotion/src/media.tsx`, used by every scene's `Frame`): editorial and kinetic draw it full-bleed
  across the frame's width under a scrim of the pack's canvas (ink keeps about 7:1 contrast), fading into the
  canvas at both edges, with a slow push-in; cards draw it as the card's image under the card's panel color. The
  pack's „საილუსტრაციო" label and the credit (author · licence · source, set in the pack's font's glyphs only) sit
  in a quiet row at the scene's bottom, left of the rail. A clip plays muted (`OffthreadVideo`).
- **N13** (`news_check.imagery`): the label on every illustrative picture; no illustrative imagery for crime,
  incidents or deaths; no AI imagery; screenshots only from the allow-list; the scene never presents the picture as
  the event („ფოტოზე", „კადრებში"...). `engine check` also refuses a ledger entry without an allowed licence, or a
  CC BY one without its author.
- **Sound effects** (format key `sfx: on|off`, default off): `tools/compose_sfx.py` synthesizes click, pop,
  whoosh, tick, thud and blip (deterministic, one loudness, none longer than 0.34 s, no risers; composed on first
  use into `assets/sfx/`, not in git). `sfx.cues(props)` places them from the timeline: a whoosh on every cut (a
  click on a plain `cut`), a pop when a mark or the outro chip lands, ticks while a stat counts and a thud as it
  settles, a blip as each bar grows. `props.mix_audio` lays them as one track under the voice at one constant
  level (no ducking). `sfx: meaning` is the other way: one `impact` on the film's main moment, 2-4 small sounds, the
  story's object's own (`obj-wood|glass|metal|paper|water|soft`, by code), nothing on a cut, and the music loop
  starts where a bar's heavy hit lands on that moment (`music_hits.py`, level unchanged).
  `stories/24835-media.json` is the demo (four pictures from Openverse and Commons).

## Icons and pictograms (`tt_shorts/icons.py`)

A visual vocabulary without photos: 250 Lucide line icons (`assets/icons/lucide.json`, ISC; rebuilt by
`tools/build_icons.py`) and a map of ~600 Georgian stems that reads case endings (გაზი, გაზის, გაზით → flame;
გაზეთი stays a newspaper). An icon is named in English or by the Georgian word.
- `sign` scene: the icon draws itself stroke by stroke, then its verb plays: rises, falls, stops (a bar closes
  across it), opens, closes (doors), moves, splits, joins.
- `stat` with `icon`: a whole count of 2-30 is drawn as that many icons, in step with the number (no "1 icon = N").
- The `icons` motif: the story's main icon (`motif`, else the hook's, else the first sign's) tiled in the grid color.
- N10 (`news_check.pictograms`): a sign's verb is said in its part of the narration; no pictograms at all for crime,
  incidents or deaths. `stories/veasy-icons.json` is the demo.

## Built for the swipe and the loop (`tt_shorts/swipe.py`)

On Shorts, Reels and TikTok the first frame decides the swipe, and Shorts count every replay as a view.
- **The hook is readable at frame 0** in every hook layout, entrance and look: scene 0 is the opening
  (`remotion/src/ui.tsx` `Opening`), where things only settle by a few px instead of coming in from nothing.
  `engine qa` fails a render whose frame 0 has no ink in the hook band (y 250-1100).
- **The voice starts at once:** leading silence on the voice track (measured with ffmpeg, and never past the first
  word's timing) is cut to 0.12 s in `props.mix_audio`; the word timings move by the same amount, so the captions
  and the scene cuts stay in sync.
- **`outro`, a format key:** `card` (the end card, the default), `overlay` (no end card; a chip with the QR, the
  link and the CTA slides in over the last scene for its final seconds, left of the rail and above the captions,
  while the scene shrinks to make room) or `loop` (the same, then the last 0.5 s cross-fade into the hook's first
  frame, the ticker comes back to where it began and the music keeps one level to the end).
- Nothing in `remotion/` is measured before the brand font is in (`remotion/src/fonts.ts`): the first frame a
  render tab drew could set the hook with the fallback font's widths.

## Brand packs (`brands/`, `tt_shorts/brand.py`)

`brands/<name>/brand.json` holds the palettes (`themes`), fonts, logo (tbilisi.today's t-mark drawn in code, or SVG files),
wordmark, link and QR URL, footer line, calls to action, categories and their families, the look and the voice per
family, the pack's own voice presets and spoken forms, the on-screen words, the time zone and the month and weekday
names. `brands/_ka` is a base with the Georgian defaults; a pack `"extends": "_ka"` and overrides what differs.
`props.py` hands the pack to Remotion (`props.brand`; `remotion/src/brand.ts` applies it) and copies its fonts and
logo into the render. A pack is validated on load: a missing key, an unknown family, look or voice, or a missing
file fails before anything renders. The `veasy:brands` skill explains adding one.

| Pack | Look | Voice |
|---|---|---|
| `tbilisi-today` | brand v1.2 below: black, white, one red, the t-mark, FiraGO | anchor / warm / clear / plain by family |
| `sitech` | coal `#171817`, paper `#F1EDE4`, SiTech orange `#FF792E`, the SiTech logo, FiraGO | `sitech`: Charon with SiTech's tech-news delivery |

**Themes** (owner, 2026-11-03: "not only on a night background; a white one and others too"). A pack has one or
more palettes, `"themes": {"dark": {"colors": {...}}, "light": {"colors": {...}, "logo": {...}}}` with a
`default_theme`; each theme is a full color set, checked for contrast on load (`brand.CONTRAST`: ink 7:1 on canvas
and panel, muted 4.5:1, the accent dot, the button, the captions box), and may bring logo files for its ground.
Both packs keep `dark` as the default (zero change for every render that names no theme) and ship `light`:
sitech's paper (`#F1EDE4` canvas, coal ink, the orange, the white logo recolored to coal), and a proposed
tbilisi.today day theme with `"allowed": false` until the owner approves it (its brand v1.2 is dark). A format's
or `--theme`'s `default`, `auto` (variety alternates the allowed themes, least used lately; a director may prefer
some by name) or a name chooses. Remotion gets the theme through `props.brand` (`applyBrand`), HyperFrames through
`brand.css` and `frame.md`. The QR code is always dark on light (on paper, the ink on the canvas).

## tbilisi.today's brand (v1.2, https://tbilisi.today/brand)

- Canvas `#05080F`, panel `#0B0F17`, ink `#F8FAFC`, secondary `#A7B0BD`, one red `#EF4444`, line `rgba(248,250,252,.12)`.
- Red is used only for the dot ("now"), an active state (the progress head, the spoken word's underline, the CTA
  button) and an error mark. Red is never a text color. There are no category colors.
- One font family, FiraGO. Hierarchy comes from size, weight and color. No caps, letter-spacing, italics, shadows,
  or frame around the mark.
- Card radius is 14 and chips are fully round. Distances are multiples of 4.
- The source and the time are always visible (header and footer). Quotes are in „…“ with the speaker's name.
  Numbers are written in digits. No long dashes.
- The look follows the kind of story (the pack's `look_by_family`, `--look auto`): hard news (politics, world,
  crime) is editorial, light news (sports, culture) is kinetic, service news (society, economy, tech) is cards.
- The three looks differ in layout and motion, never in palette (in every pack and every theme):
  - **editorial**: the grid, rising type, a cut line with the dot.
  - **kinetic**: giant type that slams in, inverted ink blocks, a panel wipe at each cut.
  - **cards**: every scene is a story card, like the site's cards.

## Layout of a frame

| Band (px) | What |
|---|---|
| 80-210 | the pack's logo (mark + wordmark, or its header SVG), date, weekday · time · category, progress rule with the accent dot (with `chapters`: „01 / 03“ and one segment a chapter) |
| 248-1380 | the scene (story text never goes lower) |
| ~1380-1552 | captions, lower third (`tt_shorts/captions.py` lays them out once with the real font; `remotion/src/Captions.tsx` draws them): `page` = a fixed two-line block whose words light up as they are spoken, `roll` = a three-line teleprompter that scrolls continuously, `keyword` = the page's lines in a dark box, the spoken word lit and one keyword a page (em phrase, number or name) in the pack's `design.keyword` style. The spoken word gets a red underline |
| 1580-1760 | moving ticker (category, date, outlets). Platforms draw their UI here, so this band carries no story text |
| 1768-1880 | sources line; the pack's link on the left and its footer line on the right (tbilisi.today: „SiTech-ის პროექტი · sitech.ge“) |

Below y=1100, no text goes right of x=940 (the like/share rail).

## Status (2026-11-02)

| Part | State |
|---|---|
| Remotion composition `NewsShort`, 22 scene types (`brushes/`), 3 looks, voice-synced marks | done (`remotion/src`) |
| Voice: Gemini presets (`voices.py`); edge-tts ka-GE as a timing stand-in only (it sounds robotic) | Gemini samples need `GEMINI_API_KEY` |
| Audio mix (ffmpeg): voice levelled on its own, music at one constant level, with no ducking | done |
| News rules N1-N13 (`ka_style.md` § N, `news_check.py`) | done |
| Media layer: Openverse, Commons, Pexels, Pixabay, screenshots, the ledger, pictures behind scenes, SFX (`assets.py`, `sfx.py`) | done (2026-11-03); AI imagery waits for the owner |
| Icons: `sign` scene, isotype counts on `stat`, the icon motif (`icons.py`, 250 Lucide icons) | done (2026-11-02) |
| Music: a news bed per category family, written from scratch (clock tick, e-piano, pad), with an even level (≤1 dB bar to bar) | done (`tools/compose_music.py`) |
| Brand packs (`brands/`: tbilisi-today, sitech), storage layout, job queue, sources (tbilisi-today, text) | done (2026-11-02) |
| A real map of Georgia for `where` (12 regions by Georgian law, rivers, 149 places, Tbilisi districts; crime stops at the region) | done (`tt_shorts/geo.py`, `assets/maps/`) |
| Writer, daily run | done; the server timer waits for the owner's OK |
| `engine package`: SRT/VTT, cover, 4:5 carousel, teaser, platform texts, Telegram post | done (2026-11-02) |
| Programs (news, explainer, law, blog), rule tiers claims and law, sources url, pdf, ordo, sitech | done (2026-11-02); `ordo` needs Ordo on the server (`ORDO_DIR`) |
| Rubrics (number, changes, continues, agree, digest), episode counters, the morning digest (program digest, source stories) | done (2026-11-03); a real 3-story digest needs a third cluster's articles (D1) |
| Auto-publishing to YouTube / Meta / TikTok, Telegram kill switch | phase 2 |

## The writer (phase 1): free first, DeepSeek v4.1 Flash only when needed

The owner set the rule on 2026-11-01: a free model writes the scripts, and `deepseek/deepseek-v4.1-flash` is used
minimally.
- **Order:**
  1. Workers AI `@cf/deepseek-ai/deepseek-v4-flash-0731` (free daily allowance; the same model ingest already
     falls back to);
  2. sitech-shorts' gateway lane of free models (branch `feat/workers-ai-gateway-lane`);
  3. `deepseek/deepseek-v4.1-flash` (Command Code), only when the free lanes fail or are out of quota.
- **One call per video:**
  - The input is the 3 most trusted member articles, cut to ~2 500 characters each (~3k tokens in, ~600 out).
  - The prompt is `ka_style.md` (K1-K22, N1-N9).
- **Code checks first, for free:**
  - `news_check` (numbers, quotes, no relative days, sensitive skip) and `ka_check` (K rules, K9 words per scene);
  - the Georgian normalisation;
  - the timing QA (`speech.scene_frames`).
- **Repairs:** only a failed check costs another call, at most 1 repair. Then the story is skipped, not forced.
  There is no separate LLM editor pass by default (sitech-shorts runs one; here it is opt-in).
- Every call's tokens go to `costs.py`, and the daily report shows them.

## Commands

```bash
python -m unittest discover -s tests                                  # Python tests
(cd remotion && npx tsc --noEmit)                                      # type-check the compositions
python -m tt_shorts.props stories/24835.json --variant editorial       # video, preview voice -> out/24835-editorial.mp4
python -m tt_shorts.props stories/24835.json --variant cards --still 120,400   # PNG frames
python -m tt_shorts.props stories/24835.json --variant kinetic --voice gemini --tone anchor   # production voice
python -m tt_shorts.voices                                             # 5 Gemini tone samples -> out/voices/
(cd remotion && npx remotion studio)                                   # live editor (props from work/<run>/props.json)
python tools/compose_music.py                                          # music loops (once per install)
```

Server setup: `bash ops/install.sh [--align]` (venv, `npm ci`, chrome-headless-shell, music,
`data/.env` from `ops/env.example`, tests).

Behind a TLS-inspecting proxy, the preview voice needs `SSL_CERT_FILE` pointing at the proxy's CA bundle.


## Writer and daily run (2026-11-02)

`tt_shorts/writer.py` turns a cluster into a story JSON: the free model writes, `news_check` and `ka_check`
judge it, one repair call and one editor pass fix what the checks named, and identity (id, date, outlets)
comes from D1. `ops/daily.py` selects the day's stories (4+ outlets, 18 hours, category caps, sensitive
stories skipped, no repeats) and renders up to ten of them with the Gemini voice.

```bash
python -m tt_shorts.writer --cluster 24886 --out stories/24886.json   # needs SHORTS_CLUSTER_JSON
python -m ops.daily --limit 10 --dry-run                               # selection only
python -m ops.daily --limit 10                                         # write and render
python -m ops.daily --limit 10 --rubrics                               # + the day's rubrics and the digest
```

The writer falls back from OpenRouter's free daily cap to the NVIDIA lane. Its known weak spot is scene
pacing (K9): a scene that starts too late in the narration is rejected rather than flashed by.

## Story JSON

```json
{"id": 24835, "brand": "tbilisi-today", "category": "society", "date": "2026-11-01T14:22:16Z",
 "sources": ["ინტერპრესნიუსი", "BPN", "ფორმულა", "ON.ge"],
 "narration": "…", "say": {"Türk": "თურქ"}, "cta": "…",
 "scenes": [{"type": "hook", "at": "ვარკეთილსა და", "lines": ["…"]}, …]}
```

`id`, `category`, `date` and `sources` come from the source's data, never from the writer. `brand` picks the pack
(default tbilisi-today); `stories/sitech-cybercartel.json` is a SiTech sample. `at` holds the first words of the scene
in the narration. Scene types and their fields are in `remotion/src/types.ts` and `remotion/src/scenes/index.tsx`:
hook (lines), stat (value, label), timeline (start, end, label), where (place, sub, area: a place in Georgia gets the
real map, see below), who (items: name, role),
points (items), quote (text, by, via), sources, end, and since 2026-11-02: draw (svg: the writer's drawing, made safe
by `tt_shorts/art.py`), pair (items: title, sub; between), steps (items), bars (items: label, value; unit), trend
(items: label, value; unit), change (before, after: label, value; unit), sign (icon, verb, label; `icons.py`), and
an optional `icon` on stat. Any scene may carry `show`, a few English words for the picture behind it (the media
layer's; never shown as text). Formats also choose the cut between scenes (`transition`: auto, cut, line, panel,
wipe, slide, push, dot, meter) and the ending (`outro`: card, overlay, loop; the `end` scene is always written, the outro
decides whether it is shown). `stories/veasy-demo.json`, `stories/veasy-scenes.json`,
`stories/veasy-icons.json` and `stories/veasy-brushes.json` use every scene type.

### The brush kit (`brushes/`, `tt_shorts/catalog.py`, `tt_shorts/marks.py`)

- **One catalog.** Every scene type is a brush, `brushes/<type>.json`: what it shows, when to use it and when not,
  what it pairs with, typed slots with Georgian length limits, the families it is never used for, its minimum
  seconds and narration words, where a mark may land, the writer's line and rules, and a real example.
  `catalog.py` generates the tables the engine reads (`engine.SCENES`, `speech.MIN_SCENE`, `ka_check.MIN_WORDS`, the
  writer's schema, `options` → `scenes`); `catalog.schema(types)` shows the writer only a director's or a program's
  menu. A new type is one brush file plus its component (CLAUDE.md).
- **Marks synced to the voice** (`"em"`, ROADMAP C2): a scene may name 1-4 words of its on-screen text that its part
  of the narration says. `speech.mark_frames` finds the frame from the word timings and `@remotion/rough-notation`
  draws the mark then. Code picks the kind (underline, box, circle, highlight, bracket) from the brush and the
  strokes (clean for hard and service news, a little rough for sports and culture); the mark is ink, one per
  scene, and N11 checks the words are on screen and said.
- **The new brushes** (2026-11-02):
  - `share`: a 10x10 grid for a percent an article states with "%";
  - `rail`: 2-4 dated events in time order, every date in the articles, a dot that travels them;
  - `compare`: two values of one unit as squares of true proportion, the ratio at most 40;
  - `link`: who meets whom, initials joined by an edge whose verb the voice says;
  - `stat.style`: count, wheel (an odometer) or flap (a split-flap board, never for politics or crime).

### The map of Georgia (`where`)

- **What it finds.** `tt_shorts/geo.py` reads the place, in any Georgian case (ბათუმიდან, ვაკეში, ისნის), from
  `assets/maps/georgia.json`.
- **What the scene shows.** Georgia's outline draws itself, the camera zooms to the region, which fills in a quiet
  ink tint (rivers and region lines for context), and the pin with the red dot drops on the town.
  - A Tbilisi district zooms into the city.
  - Several places get a marker each.
  - An unknown or foreign place keeps the grid scene.
- **The privacy rule.** For the crime family (crime, incidents) the camera stops at the region and no district is
  marked.
- **How the data reaches Remotion.** `props.py` resolves the place in Python. Each where scene's props carry only
  what it draws (about 20 KB).
- **The data.** The map has the 12 regions of Georgian law: Abkhazia and the Tskhinvali region are part of
  Georgia, drawn as no separate entity. It is rebuilt with `tools/build_georgia_map.py`; sources and licences
  are in `assets/maps/README.md`. `stories/veasy-map.json` is the demo.

## Licences

- Remotion is free for individuals and for companies with up to 3 people. SiTech is within that (owner,
  2026-11-02); a larger team would need a company licence (remotion.pro).
- The music is composed in code and is ours.
- The fonts are FiraGO (OFL).
- The map (`assets/maps/README.md`):
  - The region lines are Geostat's, via OCHA, CC BY-IGO 3.0. The scene shows the credit small under the map.
  - The rest is public domain (geoBoundaries ADM2, Natural Earth) or CC0 (Wikidata).
- The icons are Lucide (ISC; the Feather-derived ones MIT): `assets/icons/LICENSE`, no on-screen credit needed.
- Pictures carry their own licence in the story's `assets` ledger (CC0, public domain, CC BY, CC BY-SA, Pexels,
  Pixabay) and their credit on screen; the sound effects are synthesized in code and are ours.
