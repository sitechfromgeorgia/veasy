# Veasy v2: from templates to directed films, on two engines

Written 2026-11-03 at the owner's request: "every video looks alike: white text on black and set scripts; agents
should be able to build their own templates." The reference is a friend's 90 s Short (a Georgian tech explainer,
analysed below). This is the plan; `docs/next.md` holds the briefs an agent starts from.

Three things the owner set the same day, which the whole plan follows:
- **Veasy belongs to no client.** It is a general video engine for agents, like Remotion and HyperFrames are
  general tools. tbilisi.today is its first client and one brand pack; its rules (one accent, never on text) are
  that pack's, not Veasy's.
- **Two engines, both first-class: Remotion and HyperFrames.** Neither is "the main one plus a lane". Veasy chooses
  the engine per video and shares everything around it.
- **Both engines' own skills come with Veasy.** An agent can make any video, not only news: a cartoon, an animated
  story, a product film, an explainer, a data piece. It works with Remotion's and HyperFrames' skills directly,
  and together with Veasy's (voice, captions, media, music, checks, queue). That is what makes it a strong engine.

## 1. Why the videos look alike

Directors, brushes and variety change the layout and the rhythm. They do not change what is on screen:
- **No pictures.** tbilisi.today's photos have no reuse grant, and nothing else feeds the frame, so every scene is
  type, numbers and line art on the canvas.
- **One look per pack.** Dark canvas, light ink, one accent, the same header and footer in every video.
- **A fixed kit.** The agent fills text slots in 20 components; it can't compose anything the kit doesn't have.
- **Slow beats.** A scene holds 5-8 s; the reference changes something every 1.5-2.5 s.
- **No sound design.** Voice and a constant music bed; nothing lands with a sound.

## 2. What the reference does (90 s, 720x1280)

| Device | What it is | Ours today |
|---|---|---|
| Presenter bookends | a talking head opens, cuts away, comes back as picture-in-picture, closes | none (no avatar wanted) |
| Chapter bar | "01 / 03" with a segmented bar, top left, the whole video | progress rule only |
| Stacked cards | a real screenshot of the source on top, an icon illustration below | one scene, one card |
| Icon badges | big icons in tinted circles (blue, orange, green, yellow) with chips under them | ink icons, no tint |
| Process diagrams | folder -> waveform, robot -> person, a file list with the outputs | steps, link |
| Proof shots | the README, the release page, the numbers with their source chip | sources scene |
| Big number + source | "5 000 000+" with "Openverse · 1 ნოემბერი" | stat |
| Meter wipes | equaliser bars rise and fall between chapters | line, panel, wipe... |
| Karaoke captions | bold white on a dark box, the keyword in yellow | page/roll, red underline |
| A beat every ~2 s | something new enters, moves or highlights on every phrase | a scene every 5-8 s |
| Sound | the subject is sound effects; cuts and pops are heard | voice + bed |
| CTA | "comment the word ხმა" | end card |

Its frame is grey panels on near-black, rounded cards, one font, a few tints. It's richer than ours not because of
a presenter but because **every phrase has its own picture**, and the pictures are real (screenshots) or iconic.

## 3. The target: two engines, three ways to make a film, one media layer

**What the two engines share** (Veasy's part, engine-free): the story and its facts, programs and rule tiers,
brand packs, the voice and its word timings, caption pages (laid out in Python), the media layer, music and sound
effects, the ffmpeg mix, the checks (news, Georgian, probe, motion, brand, provenance), QA, package and the queue.

**What each engine is best at:** Remotion, the typed kit (brushes in React, high volume, every video checked the
same way). HyperFrames, films an agent composes in HTML/CSS/GSAP, its ~450-block registry, 3D and camera moves.
A video's engine comes from its format, program, pack or director (`"engine": "remotion" | "hyperframes"`), and a
film can mix them (HyperFrames clips inside a Remotion film, or the other way round) where phase 0 shows it works.

### The engines' own skills, with Veasy's

Veasy installs and keeps, pinned, the skills both products publish for agents:
- **Remotion** (`remotion-dev/skills`): `remotion-create`, `remotion-best-practices`, `remotion-captions`,
  `remotion-maps`, `remotion-multimedia`, `remotion-render` and the rest. The repo has no licence file, so Veasy
  doesn't copy them; `ops/install.sh --skills` installs them with `npx skills add remotion-dev/skills` at a pinned
  commit.
- **HyperFrames** (`heygen-com/hyperframes`, Apache-2.0): `/hyperframes`, `/hyperframes-cli`,
  `/hyperframes-registry`, and on demand `/remotion-to-hyperframes`, `/reverse-any-video`, `/figma`, `/slideshow`.
  `/media-use` stays off by default: it can call HeyGen's paid APIs, and Veasy's media layer does that job.
- **Motion design references** (MIT): `charlie947/motion-graphics-skills` (`vox-explainer`, `animated-chart`,
  `title-sequence-3d`), for the agent to read when it composes.

Veasy's own skills say how they fit together. `veasy:make-video` routes the request:
- news and data go through Veasy's programs (facts, checks, queue);
- anything else (a cartoon, an animated story, a product or brand film, a tutorial) is built with the engine's
  own skills;
- either way, the film gets Veasy's voice, captions, media, music, mix, QA and package, and the brand pack.

A new kind of film doesn't need a change in Veasy: a program (`programs/<id>.json` with its rule tier: `news`,
`claims`, or a new `story` tier for fiction, where nothing is checked against articles but the brand, the
Georgian and the probe still are), a format, and the engine's skills.

### The three ways to make a film

```
                 story (facts, code-owned identity)
                              |
           director + rubric + beat sheet (writer)
                              |
        +---------------------+----------------------+
        |                     |                      |
   Lane A: kit           Lane B: composed       Lane H: host (optional)
   Remotion brushes      HyperFrames HTML       a recorded talking head,
   ~50/day, auto         the agent composes     composed cutaways
        |                     |                      |
        +---------- media layer (assets.py) ---------+
           stock, AI illustration, screenshots, maps, icons, SFX
                              |
        checks: news, Georgian, probe, motion, brand, provenance
                              |
            mix (ffmpeg) -> QA -> package -> publish/hold
```

#### Lane A, the kit (Remotion, today's engine, made richer)
Stays the volume lane: cheap, safe, automatic. It gains what the media layer brings (a picture under every
scene), beats instead of scenes, the chapter bar, keyword captions and sound effects (phases 1 and 3).

#### Lane B, composed (HyperFrames)
The agent writes the film. HyperFrames (HeyGen, Apache-2.0, v0.9.8, pinned) renders HTML/CSS/GSAP to MP4 and ships
skills for agents and a registry of ~450 editable blocks (titles, kinetic type, charts, maps, transitions, camera
moves). Veasy gives the agent a project, not a blank page:
- `frame.md`, generated from the brand pack (HyperFrames' design-system format: tokens are fixed, composition is
  free), so a composed film keeps the pack's font, palette and rules;
- `timing.json`: the voice's word timings and the beat anchors, so motion lands on the words;
- `assets/`: only media from the media layer, each with its provenance;
- locked chrome components (logo, date, source line, captions, the chip of a rubric) the agent places but can't
  remove or restyle;
- the story's facts, and nothing else to say.

The agent writes `scenes/*.html`. `engine compose check` then lints, renders the settled frames, reads every text
from the DOM and runs the same checks as Lane A. A composed film that the owner approves can be **promoted to a
template**: its scenes become slots (`templates/<id>/`), it joins variety's rotation, and Lane A or another agent
can reuse it. That is how agents add new forms without anyone writing a brush by hand.

#### Lane H, host (optional, SiTech first)
The reference's format: the owner records himself talking (a phone is enough); Veasy cuts the pauses (silencedetect
plus word timings), lays composed cutaways between the takes and picture-in-picture over them. No avatar. Only
when the owner wants to be on camera.

## 4. The media layer (`tt_shorts/assets.py`, one module per provider)

Every asset carries `{kind, provider, url, licence, author, fetched, sha}` in the story's code-owned `assets` list.
No asset without a licence that allows commercial reuse.

| Kind | Providers | Use | Rule |
|---|---|---|---|
| stock video, photo | Pexels, Pixabay (free, commercial use), Openverse and Wikimedia Commons (per-file CC0/CC BY: credit shown) | b-roll under a scene: a gas pipe, a bus, a street | labelled „საილუსტრაციო"; never presented as the event |
| AI illustration | one image model per pack, one house style (a fixed style prompt + seed) | a picture of what the story is about when stock has none | never a real person, logo or the event itself; never crime, deaths, incidents |
| screenshot | Playwright on the source page (the story's own page, a ministry notice, matsne.gov.ge for law) | proof shots, highlighted line | only the official or the client's own pages, never a publisher's article page |
| map | MapLibre + OSM tiles (credit in the corner), today's Georgia map | a street-level zoom, a route | the crime family stops at the region (`geo.PRIVATE`) |
| icons | Lucide today; more sets (Tabler, Phosphor: MIT) | badges, diagrams | ink, the pack's tints (decision 2) |
| SFX | synthesized by code like the music (clicks, whooshes, ticks, pops), plus CC0 sets | cuts, chips, counts | short accents at one level; no risers, no ducking (the owner's music rule) |

A new news rule, **N13**, says it in code: illustrative imagery carries the chip; AI imagery never shows a person;
no imagery at all for crime, incidents and deaths (as N10 does for pictograms); a screenshot only from an
allow-listed domain.

## 5. Guardrails: why a composed film can still publish without a person

- **Text is data.** Every text in a composed scene carries `data-probe`; Veasy reads them from the DOM at the
  settled frames and runs `news_check`, `ka_check` and kaeasy on them. Text in an image (an AI picture with
  letters) fails.
- **No network at render.** Only local files under the project; scripts only from HyperFrames' runtime and GSAP;
  `hyperframes check` plus our lint.
- **The layout probe** runs on the HyperFrames page with the same rules (safe zone, rail, overflow, glyphs, sizes).
- **Brand.** `frame.md` fixes the tokens; a palette check on the rendered frames (outside the media regions) flags
  colors the pack doesn't have.
- **Motion rules** run on the beat timeline (unreadable text holds).
- **Provenance** is checked: every file in `assets/` is in the ledger with an allowed licence.
- **Review first.** Lane B publishes as `review` (the queue's `held`, a Telegram approve button) until the owner has
  approved, say, 20 in a row; then automatic with sampling.
- **Costs** go to `costs.py` with a daily cap per provider (images, generated video, TTS).

## 6. Writing: a beat sheet instead of scenes

The writer still writes only words. It returns beats: every 1.5-3 s a phrase and the picture it lands on
(`{"say": "...", "show": "screenshot|stock:<query>|illustration:<subject>|icon:<name>|number|map|diagram"}`). Code
picks the media, the director picks the grammar, the beats fill the chapters ("01 / 03" for 45 s and more). The
motion rule "nothing changes for 3 s" is met by construction. The CTA can ask a question for the comments where the
pack allows it.

## 7. Phases

| Phase | What | Done when |
|---|---|---|
| 0. Spike (2 days) | HyperFrames 0.9.8 on this PC and on the server; one composed 24835 by hand from a `frame.md` made from the pack; render time on the server's CPU; FiraGO and determinism | the film renders twice to the same frames; time per second of video known; integration decided (a whole film, or scene clips placed by Remotion) |
| 1. Media layer (1 week) | `assets.py`, Pexels/Pixabay/Openverse/Commons, screenshots, MapLibre, one illustration model, SFX synth, the ledger, N13 | 24835 in Lane A with a picture under every scene, all licensed, N13 tests |
| 2. Compose lane (1 week) | `engine compose` (scaffold, check, render), locked chrome, DOM text checks, probe on HyperFrames, review tier, `veasy:compose` skill | an agent makes a composed 24835 from the skill alone and it passes every check |
| 2b. Both engines' skills (2-3 days) | `ops/install.sh --skills` (Remotion's and HyperFrames' skills, pinned), `"engine"` as a format/program key, `veasy:make-video` routing, a `story` rule tier for fiction | an agent makes a short animated story (no news) from a chat request with the engines' skills plus Veasy's voice, captions and checks, in two packs |
| 3. Lane A upgrades | beat sheet writer, chapter bar, keyword captions, SFX, picture-in-picture cards, meter wipes as one more transition | the 3 s still warning gone from the shipped stories; a/b of old vs new at the same facts |
| 4. Templates + rollout | promote an approved composed film to `templates/<id>`, variety rotation, the Hub agents (mark, then sizmara, then sitech), the host lane if wanted | two agent-made templates in rotation; mark makes a video from a chat request |
| 5. Measure | retention per beat and per lane (ROADMAP D8), the bandit over lanes and directors | the choice of lane is driven by watch time |

## Phase 0 result (2026-11-03): two engines, one Veasy

Built on the Windows PC (i7-7700K, 4 cores/8 threads, 32 GB; nothing installed or run on the server): HyperFrames
0.9.8 pinned in `compose/`, `tt_shorts/frame_md.py`, a composed 24835 (`compose/24835`: 7 scenes, 28 beats on the
silent engine's words, a beat every 0.5-1.9 s), `tools/compose_scaffold.py` (builds it for any pack) and
`tools/compose_probe.py` + `compose/probe.mjs` (the layout probe on a HyperFrames page).

**One composition, two clients.** The agent's source types no color, font, logo or link: scenes use `var(--ink)`,
`var(--accent)`... and the family "Brand". The scaffold builds it per pack (`--brand sitech`): `assets/brand.css`
(the pack's tokens and font), `frame.md`, `timing.json`, and the locked chrome (logo, date, chapter bar, meter
wipes, ticker, footer, end card) and captions. 24835 renders in tbilisi-today (night, white, red, the t-mark) and
in sitech (coal, paper, orange, the SiTech logo) from the same files. A pack's design rules beyond its tokens are
now its own: brand.json `design.accent` (where the accent may go) and `design.rules` (sentences). tbilisi-today
states brand v1.2 there (the accent is never text: the probe checks it for that pack only); sitech states none,
and its frame.md says which key would hold them.

**Numbers** (36.9 s, 1080x1920, 30 fps, `--quality looks`):

| | HyperFrames | Remotion (same story, cards look) |
|---|---|---|
| render, Chrome on the GPU, default 3 workers | 66.5-71.7 s = **1.8-1.95 s per video second** (cold first run 79 s) | 64.4 s, 7 workers = 1.75 s/s |
| 6 workers | 60.6 s = 1.64 s/s | |
| software GL (`--no-browser-gpu`, as on a GPU-less server), 4 workers | 82.1 s = **2.22 s/s** | |
| file | 6.7-6.9 MB (1.56 Mbit/s, H.264) | 4.3 MB |
| two renders | byte-identical mp4 in both packs; all 1107 decoded frames equal | |

Determinism holds for one machine and one setting. Changing the worker count (3 vs 6) changed 831 of 1107 decoded
frames by at most 27/255 in 0.002 % of the pixels; software and GPU GL differ by 0.57/255 on average. So: pin the
workers and the GL mode on the server, and keep goldens per machine. FiraGO: all four weights load (no fallback),
and the probe found no glyph missing from the woff2's cmap in 561 texts at 28 settled frames, Georgian included.

**The probe works on a HyperFrames page unchanged.** `compose/probe.mjs` serves the built project with HyperFrames'
own runtime and the vendored GSAP, seeks each beat's settled time with `__player.renderSeek` (the call the
renderer makes), and measures every text exactly as `remotion/src/Probe.tsx` does; `probe.rules()` judges band,
rail, captions, frame, overflow, glyph, font and size. 28 frames in 6.6 s; planted faults (text under the rail, a
✓ outside FiraGO, Arial at 18 px, accent text) were all caught, a real one too (a 36 px label 23 px past its box).
Every network request is refused and listed: none. Its screenshots match the render (mean difference 1-4/255).
What a HyperFrames-side probe still needs: `data-probe-root` and `data-probe` regions (the chrome has them; frame.md
asks scenes to mark theirs), the text color in the report (added, for a pack's accent rule), and a rule for what
the DOM can't read: text drawn in `<canvas>`, WebGL or an image (forbid it in scenes, or OCR it).
`npx hyperframes check` adds its own audits (contrast, unreadable lines, overlap); its type floor is 28 px, ours 24.

**Registry.** Used: `count-up` (its frame-row counting, adapted for 6 400 with the pack's font; mounted as-is it
brings its own colors and Inter) and the `svg-line-draw-loader` technique (icons draw themselves). Looked at, not
used: `caption-pill-karaoke` (measures text in the browser and loads Google Fonts; our captions are laid out in
Python), `waveform` (the equaliser is a WebGPU shader: no GPU on the server; the meter wipe is hand-built). Items
load Google Fonts and CDN GSAP (3.14.2 next to the vendored 3.15.0), so an item an agent adds must be rewritten to
Brand, the tokens and local scripts.

**The decision: a whole film per engine, chosen per video.** Each film is rendered whole by one engine, then goes
through the same Veasy: `props.mix_audio` took the HyperFrames mp4 unchanged (tried with a stand-in voice track:
36.9 s, audio and video aligned), and QA, package and the queue follow. What is shared and engine-free: the story and
its facts, programs and rule tiers, the brand pack (as props for Remotion, as `brand.css` + `frame.md` for
HyperFrames), the voice and its word timings, the caption pages from `captions.py`, the media layer, the checks
(news, Georgian, the probe's rules, motion, provenance), the mix, QA, package and the queue. What each engine is
better at: Remotion, the typed brush kit and the volume (every video checked the same way, about 50 a day);
HyperFrames, films an agent composes in HTML/GSAP, the registry, camera moves and 3D. The engine comes from the
video's `"engine"` (a director's, else the program's, else the format's, else the pack's; default `remotion`).
HyperFrames clips placed by Remotion's `OffthreadVideo` stay possible, but not as the way in: two renders for one
film, the probe can't read text inside a clip (pixels only), captions and chrome would sit in a different engine
from the scene text, and transparent clips need alpha video (VP9 or ProRes). A whole film keeps chrome, captions,
scene text and the checks in one DOM.

**Phase 2 must build:**
1. `engine compose scaffold|check|render` in `tt_shorts/` from the two spike tools, with the `"engine"` key and
   its precedence; the render pins workers, GL mode and `--quality`.
2. Facts bound, not typed: scenes read the story's numbers, names and dates through HyperFrames variables
   (`data-var-text`), and every text the probe collects goes through `news_check`, `ka_check` and kaeasy.
3. Our lint: no typed colors, fonts, logos or links in a scene (a test checks it today), no `https` script or
   font, no text in `<canvas>`, `data-probe` on every text, the locked files unchanged (hashed).
4. The locked chrome as a versioned set (chrome, captions, end card, rubric chip) with goldens in every pack, and
   one chrome spec both engines draw from (the same bands as `NewsShort`).
5. The probe and `hyperframes check` as gates (a problem holds the job), and the review tier for composed films.
6. The package from a HyperFrames film (cover, carousel stills per scene, teaser) and sound effects in the ffmpeg
   mix.
7. Registry hygiene: an allow-list, and `add` followed by a rewrite to Brand, tokens and local scripts.
8. Locked-down CLI: `HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1 HYPERFRAMES_NO_UPDATE_CHECK=1 HYPERFRAMES_SKIP_SKILLS=1
   HYPERFRAMES_NO_AUTO_INSTALL=1`; agents never run `publish`, `cloud`, `lambda`, `tts`, `media-use` or `feedback`.
9. sitech's `design` rules (the owner's), and tints (decision 2) as a pack key if wanted.

**Surprises.** HyperFrames sends telemetry to PostHog unless `HYPERFRAMES_NO_TELEMETRY=1` or `DO_NOT_TRACK=1`;
`doctor` asks npm for the latest version even with the update check off; `add` fetches from GitHub and copies to the
clipboard; every render prints an ad for HeyGen's desktop app; its skills tell an agent to report usage and send a
`feedback` rating; `publish` uploads a project to HeyGen. A `<script src="https://cdn.jsdelivr.net/...gsap">`
stays a CDN fetch at render (the compiler keeps https sources), so the scaffold copies GSAP from the pinned package.
Local fonts are embedded by the compiler, so FiraGO needs nothing online. Licences: HyperFrames Apache-2.0, GSAP
under its own no-charge licence (vendored by the package), FiraGO OFL, Lucide ISC, the map's Geostat/OCHA CC BY-IGO
credit on screen. Windows was no obstacle (Docker mode isn't available here).

**Both products' skills side by side.** Their names don't clash: Remotion's thirteen are all `remotion-*`
(`remotion-best-practices`, `-captions`, `-create`, `-docs`, `-interactivity`, `-license`, `-maps`, `-markup`,
`-multimedia`, `-render`, `-saas`, `-studio`, `-upgrade`); HyperFrames' are `hyperframes`, `hyperframes-cli`,
`hyperframes-registry`, `media-use`, `figma`, `slideshow`, `remotion-to-hyperframes`, `reverse-any-video`. Both
install with `npx skills add <repo>` into the agent's skills folder, and HyperFrames' `skills update` leaves skills
another publisher installed alone (its docs; `HYPERFRAMES_SKIP_SKILLS=1` keeps a pinned set pinned). The overlap
is in topics, not names: captions (`remotion-captions`, HyperFrames' captions reference, Veasy's `captions.py`) and
media (`media-use`, Veasy's media layer), so `veasy:make-video` must say which wins. Not installed side by side
here (it writes outside the repo); phase 2b tries it.

## 8. Decisions only the owner can make

1. **Lane B's review period:** how many approved films before composed videos publish on their own.
2. **Tints:** the reference's tinted badges break tbilisi.today's "one accent, no category colors". Options: keep it
   strict; or add a pack key `illustration` with 2-4 muted tints for icons and illustrations only (never text, never
   per category). SiTech's own brand (ink, night, mist, cyan) already has them.
3. **AI imagery in news:** allowed with the chip, or only in explainers, law and SiTech videos.
4. **Providers and budget:** which image model, whether generated video (Kling, Veo, Seedance) is in at all, and a
   monthly cap.
5. **The host lane:** whether the owner wants to be on camera for SiTech.
6. **HyperFrames' own media** (`media-use` can call HeyGen's paid APIs): off by default; only our media layer.
7. **Which agents get which skills:** all of Veasy plus both engines' skills on every agent that makes videos, or
   the engines' skills only where an agent composes (sizmara for design, mark for SMM).

## 9. What we don't do

- No avatar, no face-swap, no cloning of other people's videos (hypit), no publisher photos.
- No OpenMontage code inside Veasy (AGPL-3.0); it can be a separate tool an agent runs.
- No generated imagery of real people or of the news event itself.

## 10. Any brand book in (owner, 2026-11-03)

"We make tools; whoever has a brand book fits the tool to it." A client brings their own brand, and Veasy must make
that easy without code:
- `engine brand new <name> --from <url|pdf|design.md|frame.md>`: reads a brand page, a brand-book PDF or a design
  file and drafts `brands/<name>/brand.json` (fonts, palette per theme, logo files, words, rules under `design`),
  then validates it and renders a contact sheet in every theme and both engines for a person to check.
- Everything the engines draw comes from the pack: themes (dark, light and more), the accent rule, tints, caption
  style, chrome, voice, words. Nothing about a client lives in `tt_shorts/`, `remotion/src/` or `compose/`.
- The `veasy:brands` skill walks an agent through it; a new pack key always gets validation in `brand.py` and a
  case in `tests/test_brand.py`.
