# video/: tbilisi.today Shorts

Turns multi-source stories (`story_clusters` with 3+ outlets) into 30-40 second Georgian vertical videos
(1080×1920, 30 fps) for YouTube Shorts, Instagram/Facebook Reels and TikTok. Each video has a voice, background
music, the date, the sources, a QR code to the story page and a tbilisi.today end card.

Frames are rendered with [Remotion](https://github.com/remotion-dev/remotion) (React; `remotion/`). Python
(`tt_shorts/`) handles the voice and its word timings, the scene timing, the news rules and the data. Forked from
`sitechfromgeorgia/sitech-shorts`: the Georgian normalisation, the K rules, the music composer and the timing code.

This is not a Worker: Workers Builds ignores this folder (watch paths are `<worker>/*`). It runs on the tbilisi.today
agent server (84.46.250.149).

## Brand (v1.2, https://tbilisi.today/brand)

- Canvas `#05080F`, panel `#0B0F17`, ink `#F8FAFC`, secondary `#A7B0BD`, one red `#EF4444`, line `rgba(248,250,252,.12)`.
- Red is used only for the dot ("now"), an active state (the progress head, the spoken word's underline, the CTA
  button) and an error mark. Red is never a text color. There are no category colors.
- One font family, FiraGO. Hierarchy comes from size, weight and color. No caps, letter-spacing, italics, shadows,
  or frame around the mark.
- Card radius is 14 and chips are fully round. Distances are multiples of 4.
- The source and the time are always visible (header and footer). Quotes are in „…“ with the speaker's name.
  Numbers are written in digits. No long dashes.
- The three looks differ in layout and motion, never in palette:
  - **editorial**: the grid, rising type, a cut line with the dot.
  - **kinetic**: giant type that slams in, inverted ink blocks, a panel wipe at each cut.
  - **cards**: every scene is a story card, like the site's cards.

## Layout of a frame

| Band (px) | What |
|---|---|
| 80-210 | mark + wordmark, date, weekday · time · category, progress rule with the red dot |
| 248-1296 | the scene (story text never goes lower) |
| 1296-1432 | captions: up to 3 words; the spoken word is underlined in red |
| 1468-1760 | moving ticker (category, date, outlets). Platforms draw their UI here, so this band carries no story text |
| 1768-1880 | sources line + story link |

Below y=1100, no text goes right of x=940 (the like/share rail).

## Status (2026-11-01)

| Part | State |
|---|---|
| Remotion composition `NewsShort`, 9 scene types, 3 looks | done (`remotion/src`) |
| Voice: Gemini presets (`voices.py`); edge-tts ka-GE as a preview stand-in | Gemini samples need `GEMINI_API_KEY` |
| News rules N1-N9 (`ka_style.md` § N, `news_check.py`) | done |
| 8 category families → composed music, 2 loops each | done (`tools/compose_music.py`) |
| Feed endpoint, writer, daily run, server timer | phase 1 |
| Auto-publishing to YouTube / Meta / TikTok, Telegram kill switch | phase 2 |

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

Server setup: `bash video/ops/install.sh [--align]` (venv, `npm ci`, chrome-headless-shell, music,
`data/.env` from `ops/env.example`, tests).

Behind a TLS-inspecting proxy, the preview voice needs `SSL_CERT_FILE` pointing at the proxy's CA bundle.

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
