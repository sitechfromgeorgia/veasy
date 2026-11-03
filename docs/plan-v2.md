# Veasy v2: from templates to directed films

Written 2026-11-03 at the owner's request: "every video looks alike: white text on black and set scripts; agents
should be able to build their own templates." The reference is a friend's 90 s Short (a Georgian tech explainer,
analysed below). This is the plan; `docs/next.md` holds the briefs an agent starts from.

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

## 3. The target: three lanes on one media layer

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

### Lane A, the kit (Remotion, today's engine, made richer)
Stays the volume lane: cheap, safe, automatic. It gains what the media layer brings (a picture under every
scene), beats instead of scenes, the chapter bar, keyword captions and sound effects (phases 1 and 3).

### Lane B, composed (HyperFrames)
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

### Lane H, host (optional, SiTech first)
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
| 3. Lane A upgrades | beat sheet writer, chapter bar, keyword captions, SFX, picture-in-picture cards, meter wipes as one more transition | the 3 s still warning gone from the shipped stories; a/b of old vs new at the same facts |
| 4. Templates + rollout | promote an approved composed film to `templates/<id>`, variety rotation, the Hub agents (mark, then sizmara, then sitech), the host lane if wanted | two agent-made templates in rotation; mark makes a video from a chat request |
| 5. Measure | retention per beat and per lane (ROADMAP D8), the bandit over lanes and directors | the choice of lane is driven by watch time |

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

## 9. What we don't do

- No avatar, no face-swap, no cloning of other people's videos (hypit), no publisher photos.
- No OpenMontage code inside Veasy (AGPL-3.0); it can be a separate tool an agent runs.
- No generated imagery of real people or of the news event itself.
