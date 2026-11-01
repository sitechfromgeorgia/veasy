# video/: tbilisi.today Shorts

Turns multi-source stories (`story_clusters` with 3+ outlets) into 30-40 second Georgian vertical videos
(1080×1920) for YouTube Shorts, Instagram/Facebook Reels and TikTok, with a Gemini voice, background music, the date,
a QR code to the story page and a tbilisi.today end card. Forked from `sitechfromgeorgia/sitech-shorts` (the SiTech
pipeline), with its own look, voices, news rules and server.

Not a Worker: Workers Builds ignores this folder (watch paths are `<worker>/*`). It runs on the tbilisi.today agent
server (84.46.250.149) as Python with ffmpeg and headless Chromium.

## Status (phase 0, 2026-11-01)

| Part | State |
|---|---|
| 3 looks: A ღამის რედაქცია, B გაზეთი, C Kinetic | done: `tt_shorts/templates.py` |
| Scenes: hook, stat, timeline, where, who, points, quote, sources, end (QR) | done |
| Date (Tbilisi time) in the header, the footer and the end card | done |
| 8 category families: accent color + composed music (2 loops each) | done: `tools/compose_music.py` |
| 5 voice tones (Gemini TTS) | presets done; samples need `GEMINI_API_KEY` (`python -m tt_shorts.voices`) |
| News rules N1-N9 (no opinion, numbers/quotes from sources, no relative days, sensitive skip) | done: `ka_style.md` § N, `news_check.py` |
| Preview renders of 2 real stories × 3 looks | `out/` (not in git) |
| Feed endpoint, writer, daily run, server timer | phase 1 |
| Auto-publishing to YouTube / Meta / TikTok | phase 2 |

The plan: phase 1 adds `GET /api/shorts/candidates` on tt-web (Bearer `SHORTS_FEED_TOKEN`), the story picker, the
multi-source script writer (from sitech-shorts `script.py`) and `daily.py`; phase 2 stores the mp4 in R2 and
publishes through the platform APIs with a Telegram kill switch (`/pause`, `/takedown <id>`).

## Commands

```bash
python -m unittest discover -s tests                                # all tests
python tools/stills.py stories/24725.json --themes A,B,C            # every scene's finished frame + a contact sheet
python -m tt_shorts.render stories/24835.json --theme B --silent     # preview video: estimated timings, music only
python -m tt_shorts.render stories/24835.json --theme A --voice anchor   # the real thing (GEMINI_API_KEY, align venv)
python -m tt_shorts.voices                                           # 5 tone samples -> out/voices/*.wav
python tools/compose_music.py                                        # the music loops (once per install)
```

Server setup: `bash video/ops/install.sh [--align]` (venv, Chromium, music, `data/.env` from `ops/env.example`, tests).

## Story JSON

```json
{"id": 24835, "category": "society", "date": "2026-11-01T14:22:16Z",
 "sources": ["ინტერპრესნიუსი", "BPN", "ფორმულა", "ON.ge"],
 "narration": "…", "say": {"Türk": "თურქ"}, "cta": "…",
 "scenes": [{"type": "hook", "at": "ვარკეთილსა და", "lines": ["…"]}, …]}
```

`id`, `category`, `date` and `sources` come from D1, never from the writer. `at` is the first words of the narration
where the scene starts. The scene fields are in the `templates.py` docstring.
