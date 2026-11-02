---
name: tt-shorts-make-video
description: "Use when asked to make, render or re-render a tbilisi.today Short (a 25-45 s Georgian vertical news video) from a story cluster or a story JSON, in any format, look, caption design or voice. Examples: \"make a video of cluster 24886\", \"render story 24725 in kinetic with roll captions\", \"do today's videos\""
---

# Make a tbilisi.today Short

Everything goes through one entry point; every command prints JSON on stdout and exits 0 (ok), 1 (problems) or 2
(usage). Run from `video/` with the server env loaded: `set -a; . data/.env; set +a`.

```bash
python -m tt_shorts.engine doctor        # first, on a new machine or after an install: everything true?
python -m tt_shorts.engine options       # every look, caption design, voice, music, format and scene type
```

## 1. Get a story JSON

- From a cluster (needs OPENROUTER_API_KEY, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, TT_D1_DATABASE_ID):
  `python -m tt_shorts.engine write --cluster 24886` writes `stories/24886.json` and `stories/24886.sources.json`
  (the articles, kept for re-checks). The result lists any remaining problems; a non-empty list means: don't render.
- By hand or to repair one: follow the `tt-shorts-write-script` skill.
- The daily selection (4+ outlets, last 18 h, category caps, sensitive stories skipped, no repeats):
  `python -m ops.daily --limit 10 --dry-run` shows the picks; without `--dry-run` it writes and renders them.

## 2. Check it (free, seconds)

```bash
python -m tt_shorts.engine check stories/24886.json --sources stories/24886.sources.json
```
`problems` must be empty. Rules named N* are news rules (numbers and quotes from the articles, no relative days,
no sensitive stories), K* and KE are Georgian rules (KE = kaeasy, SiTech's Georgian plugin), `timing:` and
`captions:` are layout. Fix the story, never the rule. `warnings` don't block; read them anyway.

## 3. Render

```bash
python -m tt_shorts.engine render stories/24886.json --format news
```
- `--format` picks a show (see `tt-shorts-formats`); any single choice can be overridden for one render:
  `--look auto|editorial|kinetic|cards`, `--captions page|roll`, `--voice family|plain|anchor|warm|clear|...`,
  `--music family|off|<family>`, `--platform youtube|instagram|tiktok|shorts` (the QR's utm_source).
- `--engine gemini` (default) is the real voice and costs ~$0.01; `edge` (robotic) and `silent` are free previews
  for checking layout and timing only. Never publish an `edge` or `silent` render.
- The voice is cached per story: rendering the same story in another look or caption design costs nothing.
- Output: `out/<id>-<format>-<look>-<captions>.mp4`, or `--out path.mp4`.
- Quick look without a full render: `python -m tt_shorts.engine still stories/24886.json` (one PNG per scene).

## 4. QA before anyone sees it

`python -m tt_shorts.engine qa out/24886-news-cards-page.mp4 --format news`, then follow `tt-shorts-qa`.

## Hard rules (the engine enforces most; don't work around them)

- Brand v1.2: dark canvas, white ink, one red for the dot, the active state and the CTA button; FiraGO only.
- The date, the outlets and the story link come from D1, never from a writer.
- No publisher photos. No opinion. Sensitive stories are skipped, not softened.
- Secrets live only in `video/data/.env` on the server; never print, commit or paste them.
