# video/: rules for agents

Read the root [CLAUDE.md](../CLAUDE.md) and [README.md](README.md) first. This folder is Python, not a Worker:
nothing here deploys through Workers Builds, and it never writes to D1.

- **Where it runs:** the tbilisi.today agent server, 84.46.250.149. Setup is `ops/install.sh`; secrets live only
  in `video/data/.env` (chmod 600, git-ignored). Timers, cron and anything installed on the server need the owner's OK.
- **Data flow:** story JSON → per-scene HTML (`templates.py`) → Playwright frames → ffmpeg mp4 (`render.py`).
  The writer (an LLM) fills only text fields; layout, motion, date, sources, QR and colors are code.
- **News rules are hard rules:** `tt_shorts/ka_style.md` § N and `news_check.py`. The videos are published without a
  human review, so a rule that code can check goes into `news_check.py` with a test in `tests/test_news_check.py`.
  Never add a scene type that carries opinion. Never let the writer set `date` or `sources`.
- **Georgian:** K1-K22 come from sitech-shorts (`ka_style.md`, `ka_check.py`, `normalize_ka.py`, `lexicon_ka.json`).
  A Latin name's spoken form goes in `lexicon_ka.json` (approved) or the story's `say` map.
- **Safe zone:** scene text ends at `HERO_BOTTOM` 1300, captions at `CAPTION_BOTTOM` 1420, no words right of
  `RAIL_X` 940 below `RAIL_Y` 1100. `FIT_JS` fails a render that breaks it; `tools/stills.py` shows it in seconds.
- **No publisher photos** in videos: no reuse grant exists (`ingest/src/story-cover-assets/README.md`).
- **Music** is composed by `tools/compose_music.py` (ours, no Content ID); the m4a files are not in git.
- **Voices:** `voices.py` presets. SiTech's `Charon` voice stays SiTech's.
- **Tests:** `python -m unittest discover -s tests`. A change to dates, rules, anchors or the safe zone needs a test.
- UI and on-screen text in Georgian; code, comments and commits in English.
