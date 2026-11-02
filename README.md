# Veasy

**Veasy** is SiTech's video engine for agents, the sibling of [kaeasy](https://github.com/sitechfromgeorgia/kaeasy):
kaeasy handles Georgian writing, Veasy handles video.
- **What it does:** turns a story into a checked, voiced, captioned vertical video (1080×1920). It uses Remotion
  frames, a Gemini TTS voice with word-level alignment, composed music and an ffmpeg mix.
- **Who drives it:** an agent, through formats it can choose and extend.
- **Built-in quality gates:** news integrity rules, Georgian quality through kaeasy, and caption stability.
- **First client:** [tbilisi.today](https://tbilisi.today), daily Georgian news Shorts from multi-source stories.
  Its brand (v1.2), categories and D1 story clusters are wired in. Making these a swappable "brand pack" for other
  clients is on the [roadmap](ROADMAP.md).
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
- **Tools:** `veasy_options`, `veasy_check`, `veasy_render`, `veasy_still`, `veasy_qa`, `veasy_write` and
  `veasy_doctor`.
  - Each runs the engine in its own venv and returns its JSON.
  - A render takes a minute or two; the agent needs none of the render libraries.
- **Skills:** `veasy:make-video`, `veasy:write-script`, `veasy:qa`, `veasy:formats`.
- **A one-line hint** on the first turn; turn it off with `VEASY_HINT=0`.


Turns multi-source stories (`story_clusters` with 3+ outlets) into 30-40 second Georgian vertical videos
(1080×1920, 30 fps) for YouTube Shorts, Instagram/Facebook Reels and TikTok. Each video has a voice, background
music, the date, the sources, a QR code to the story page and a tbilisi.today end card.

Frames are rendered with [Remotion](https://github.com/remotion-dev/remotion) (React; `remotion/`). Python
(`tt_shorts/`) handles the voice and its word timings, the scene timing, the news rules and the data. Forked from
`sitechfromgeorgia/sitech-shorts`: the Georgian normalisation, the K rules, the music composer and the timing code.

This is not a Worker: Workers Builds ignores this folder (watch paths are `<worker>/*`). It runs on the tbilisi.today
agent server (84.46.250.149).

## The engine (start here)

One entry point for people and agents; every command prints JSON (`tt_shorts/engine.py`):

```bash
python -m tt_shorts.engine doctor                                  # is this machine ready?
python -m tt_shorts.engine options                                 # every choice: looks, captions, voices, music, formats, scenes
python -m tt_shorts.engine write  --cluster 24886                  # D1 cluster -> stories/24886.json (+ .sources.json)
python -m tt_shorts.engine check  stories/24886.json --sources stories/24886.sources.json
python -m tt_shorts.engine render stories/24886.json --format news [--look kinetic] [--captions roll] [--voice warm]
python -m tt_shorts.engine still  stories/24886.json               # one PNG per scene, no video
python -m tt_shorts.engine qa     out/24886-news-cards-page.mp4    # size, length, loudness + a contact sheet
python -m tt_shorts.engine voices --story stories/24886.json       # Gemini tone samples, by ear
```

- **Formats** (`tt_shorts/formats.py`, `formats/*.json`): a show is a named set of choices (look, captions, voice,
  music, platform, length window). Built-in: `news`, `news-roll`. A new show is a JSON file, no code. Which show
  uses which format is the owner's and the agent's decision.
- **Skills** for agents (`skills/`): `veasy:make-video`, `veasy:write-script`, `veasy:qa`,
  `veasy:formats`.
- The voice is cached per story (`work/<id>-voice-<engine>/`): another look or caption design costs no new TTS.
- What comes next (new visual blocks, render server, more outputs, the decisions needed): [ROADMAP.md](ROADMAP.md).
- **Georgian gate: [kaeasy](https://github.com/sitechfromgeorgia/kaeasy)** (`tt_shorts/kaeasy.py`).
  - It is loaded from the plugin folder every agent shares (`KAEASY_DIR`), so a new rule there reaches the videos.
  - Each text gets its own mode: the narration is checked as an article, the on-screen text as social copy, and
    the spoken text as speech.
  - kaeasy's strict rules block a render; the rest come back as `warnings` from `engine check`.
  - The writer reads kaeasy's ten most-broken rules and the fleet's frequent mistakes before it writes (free).
  - The editor's fixes go back into the shared memory.
  - `SHORTS_REQUIRE_KAEASY=1` on the server: no gate, no video.

## Brand (v1.2, https://tbilisi.today/brand)

- Canvas `#05080F`, panel `#0B0F17`, ink `#F8FAFC`, secondary `#A7B0BD`, one red `#EF4444`, line `rgba(248,250,252,.12)`.
- Red is used only for the dot ("now"), an active state (the progress head, the spoken word's underline, the CTA
  button) and an error mark. Red is never a text color. There are no category colors.
- One font family, FiraGO. Hierarchy comes from size, weight and color. No caps, letter-spacing, italics, shadows,
  or frame around the mark.
- Card radius is 14 and chips are fully round. Distances are multiples of 4.
- The source and the time are always visible (header and footer). Quotes are in „…“ with the speaker's name.
  Numbers are written in digits. No long dashes.
- The look follows the kind of story (`meta.VARIANT_BY_FAMILY`, `--variant auto`): hard news (politics, world,
  crime) is editorial, light news (sports, culture) is kinetic, service news (society, economy, tech) is cards.
- The three looks differ in layout and motion, never in palette:
  - **editorial**: the grid, rising type, a cut line with the dot.
  - **kinetic**: giant type that slams in, inverted ink blocks, a panel wipe at each cut.
  - **cards**: every scene is a story card, like the site's cards.

## Layout of a frame

| Band (px) | What |
|---|---|
| 80-210 | mark + wordmark, date, weekday · time · category, progress rule with the red dot |
| 248-1380 | the scene (story text never goes lower) |
| ~1380-1552 | captions, lower third (`tt_shorts/captions.py` lays them out once with the real font; `remotion/src/Captions.tsx` draws them): `page` = a fixed two-line block whose words light up as they are spoken, `roll` = a three-line teleprompter that scrolls continuously. The spoken word gets a red underline |
| 1580-1760 | moving ticker (category, date, outlets). Platforms draw their UI here, so this band carries no story text |
| 1768-1880 | sources line; story link on the left, „SiTech-ის პროექტი · sitech.ge“ on the right |

Below y=1100, no text goes right of x=940 (the like/share rail).

## Status (2026-11-01)

| Part | State |
|---|---|
| Remotion composition `NewsShort`, 9 scene types, 3 looks | done (`remotion/src`) |
| Voice: Gemini presets (`voices.py`); edge-tts ka-GE as a timing stand-in only (it sounds robotic) | Gemini samples need `GEMINI_API_KEY` |
| Audio mix (ffmpeg): voice levelled on its own, music at one constant level, with no ducking | done |
| News rules N1-N9 (`ka_style.md` § N, `news_check.py`) | done |
| Music: a news bed per category family, written from scratch (clock tick, e-piano, pad), with an even level (≤1 dB bar to bar) | done (`tools/compose_music.py`) |
| Feed endpoint, writer, daily run, server timer | phase 1 |
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
```

The writer falls back from OpenRouter's free daily cap to the NVIDIA lane. Its known weak spot is scene
pacing (K9): a scene that starts too late in the narration is rejected rather than flashed by.

## Story JSON

```json
{"id": 24835, "category": "society", "date": "2026-11-01T14:22:16Z",
 "sources": ["ინტერპრესნიუსი", "BPN", "ფორმულა", "ON.ge"],
 "narration": "…", "say": {"Türk": "თურქ"}, "cta": "…",
 "scenes": [{"type": "hook", "at": "ვარკეთილსა და", "lines": ["…"]}, …]}
```

`id`, `category`, `date` and `sources` come from D1, never from the writer. `at` holds the first words of the scene
in the narration. Scene types and their fields are in `remotion/src/types.ts` and `remotion/src/scenes/index.tsx`:
hook (lines), stat (value, label), timeline (start, end, label), where (place, sub), who (items: name, role),
points (items), quote (text, by, via), sources, end.

## Licences

- Remotion is free for individuals and for companies with up to 3 people. A larger company needs a Remotion
  company licence (remotion.pro); check this before production use.
- The music is composed in code and is ours.
- The fonts are FiraGO (OFL).
