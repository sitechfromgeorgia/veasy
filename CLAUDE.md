# Veasy: rules for agents

**Veasy** is SiTech's video engine; kaeasy is its sibling for Georgian. It is also a Hermes plugin
(`plugin.yaml`, `__init__.py`, `skills/`). A new tool goes in three places, and `tests/test_plugin.py` checks they
agree: `plugin.yaml`, `__init__.TOOLS` and a skill.

Read [README.md](README.md) first. Veasy is Python plus a Remotion project.

Its first client is tbilisi.today ([sitechfromgeorgia/tbilisi.today](https://github.com/sitechfromgeorgia/tbilisi.today)):
- Veasy only reads that project's D1, never writes to it.
- That repo's rules apply to anything Veasy does there.

- **Where it runs:** the tbilisi.today agent server, 84.46.250.149. Setup is `ops/install.sh`.
  - Secrets live only in `data/.env` (chmod 600, git-ignored).
  - Timers, cron and anything installed on the server need the owner's OK.
- **Entry point:** `python -m tt_shorts.engine` (options, check, render, still, qa, write, voices, doctor; JSON out).
  The skills in `skills/` say how an agent uses it. Keep the engine, the skills and `options` in step: a new
  choice in code must appear in `engine.options()`, `formats.py` validation and the `veasy:formats` skill.
- **Data flow:** story JSON → `tt_shorts/props.py` (voice, timings, data) → `remotion/` composition `NewsShort` → mp4.
  - The writer (an LLM) fills only text fields.
  - Layout, motion, date, sources, QR and colors are code.
- **Brand v1.2 is law** (https://tbilisi.today/brand, `remotion/src/brand.ts`):
  - Colors: dark canvas, white ink, one red. Red is for the dot, an active state or an error, never for text.
  - FiraGO only. No shadows, no frame on the mark, no category colors, no long dashes.
  - The source and the time are always on screen.
  - A new look changes layout or motion, not the palette.
- **News rules are hard rules:** `tt_shorts/ka_style.md` § N and `news_check.py`.
  - Videos are published without a human review. Any rule that code can check goes into `news_check.py` with a
    test in `tests/test_news_check.py`.
  - Never add an opinion scene. Never let the writer set `date` or `sources`.
- **Georgian:** K1-K22 come from sitech-shorts (`ka_style.md`, `ka_check.py`, `normalize_ka.py`, `lexicon_ka.json`).
  A Latin name's spoken form goes in `lexicon_ka.json` (approved) or in the story's `say` map.
  General Georgian rules belong in **kaeasy**, SiTech's plugin (`tt_shorts/kaeasy.py` loads it from `KAEASY_DIR`):
  - add a new general rule there, not here;
  - keep only video-specific rules in this folder (news rules, timing, the spoken form).
- **Safe zone:**
  - Scene text ends at y=1380 and captions at y=1552.
  - Below y=1100, no text goes right of x=940.
  - The band below the captions carries motion only.
- **No publisher photos:** tbilisi.today has no reuse grant (tbilisi.today repo: `ingest/src/story-cover-assets/README.md`).
- **Music** is composed by `tools/compose_music.py`; the m4a files are not in git. One constant level: no build-ups,
  no ducking (the owner heard the ducked bed pump). The mix happens in ffmpeg (`props.mix_audio`), not in Remotion.
- **Voices:** presets in `voices.py`. SiTech's `Charon` stays SiTech's. edge-tts is a preview stand-in only.
- **Captions** are laid out in Python (`captions.py`, fontTools on the real woff2), never measured in the render tabs.
  One size per video, pages ≥ 1 s, gaps under 1.2 s bridged, position a pure function of time. `tests/test_captions.py`
  holds the jitter rules; a caption change needs a case there.
- **Tests:** `python -m unittest discover -s tests` and `(cd remotion && npx tsc --noEmit)`. A change to dates,
  rules, anchors or the safe zone needs a test.
- Text on screen is in Georgian. Code, comments and commits are in English.
