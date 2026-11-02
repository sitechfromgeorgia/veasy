---
name: make-video
description: "Use when asked to make, render or re-render a vertical video (a Short or reel of 25-45 s, Georgian voice) from a story cluster, an article or a story JSON, for tbilisi.today, SiTech or any brand pack, in any format, look, caption design or voice. Examples: \"make a video of cluster 24886\", \"render story 24725 in kinetic with roll captions\", \"make this post a SiTech video\""
---

# Make a video with Veasy

Everything goes through one entry point; every command prints JSON on stdout and exits 0 (ok), 1 (problems) or 2
(usage). Run from the Veasy folder (the repo root) with the server env loaded: `set -a; . data/.env; set +a`.

```bash
python -m tt_shorts.engine doctor        # first, on a new machine or after an install: everything true?
python -m tt_shorts.engine options       # every brand pack, look, caption design, voice, music, format, scene type
```
Which client the video is for is the story's `"brand"` (default tbilisi-today; see `veasy:brands`). Several videos,
a daily batch or retries: use the queue (`veasy:queue`); it runs these same steps per job.

## 1. Get a story JSON

- From a source: `python -m tt_shorts.engine write --source tbilisi-today --ref 24886 [--brand tbilisi-today]`
  (a cluster; needs OPENROUTER_API_KEY, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, TT_D1_DATABASE_ID), or
  `--source text --ref articles.json` (`{"cluster": {"id", "headline", "category", "date", "sources"},
  "articles": ["text", ...]}`, any client). It writes `stories/<brand>/<day>/<ref>.json` under VEASY_HOME and the
  articles beside it as `.sources.json` (kept for re-checks); the JSON result gives both paths. A non-empty
  `problems` list means: don't render.
- Not a news cluster (a web page, a PDF, an article of Georgian law, a SiTech post): pick a program,
  `write --program explainer|law|blog --source url|pdf|ordo|sitech --ref ...` (see `veasy:programs`). A program
  brings its own brief, scenes, rules and default format; law and explainer videos are held for a person's review.
- By hand or to repair one: follow the `veasy:write-script` skill.
- The daily selection (4+ outlets, last 18 h, category caps, sensitive stories skipped, no repeats):
  `python -m ops.daily --limit 10 --dry-run` shows the picks; without `--dry-run` it writes and renders them.

## 2. Check it (free, seconds)

```bash
python -m tt_shorts.engine check <story.json> --sources <story>.sources.json
```
`problems` must be empty. Rules named N* are news rules (numbers and quotes from the articles, no relative days,
no sensitive stories), K* and KE are Georgian rules (KE = kaeasy, SiTech's Georgian plugin), `timing:` and
`captions:` are layout. Fix the story, never the rule. `warnings` don't block; read them anyway.

## 3. Plan before you render (free, ~5 s)

```bash
python -m tt_shorts.engine plan <story.json> [--format news] [--look kinetic] [--director map]
```
Tool `veasy_plan`. A storyboard with no voice and no model call, and it uses up nothing (the variety picks are
shown, not recorded):
- per scene: start, end, narration words, caption pages, and every text on screen with the seconds it `need`s
  (0.5 s + 0.3 s a word) and the seconds it is `shown`; `load` above 1 means more text than time;
- `variety`: the hook layout, motif, entrance, transition and music the render will get (inside the director's);
- the motion rules as `warnings` (a still stretch over 3 s, more than 3 transition kinds, ping-pong cuts, two
  scenes of one type in a row): fix them when the facts allow;
- the layout probe and `sheet`, a contact sheet of every scene's settled frame at half size: look at it.

`problems` must be empty before you render: a text on screen too briefly to read holds the render too (the job
ends `held`), so shorten the text or give its scene more narration. Then render.

## 4. Render

```bash
python -m tt_shorts.engine render <story.json> --format news
```
- `--format` picks a show (see `veasy:formats`); any single choice can be overridden for one render:
  `--look auto|editorial|kinetic|cards`, `--captions page|roll`, `--voice family|plain|anchor|warm|clear|...`,
  `--music family|off|<family>`, `--platform youtube|instagram|tiktok|shorts` (the QR's utm_source),
  `--outro card|overlay|loop` (the end card, a QR/link/CTA chip over the last scene, or a seamless loop back into
  the hook; see `veasy:formats`).
- `--engine gemini` (default) is the real voice and costs ~$0.01; `edge` (robotic) and `silent` are free previews
  for checking layout and timing only. Never publish an `edge` or `silent` render.
- The voice is cached per story: rendering the same story in another look or caption design costs nothing.
- Output: `renders/<brand>/<day>/<ref>-<format>-<look>-<captions>.mp4` under VEASY_HOME, with a `.json` beside it
  (what was rendered: voice, look, kaeasy version), or `--out path.mp4`.
- Quick look without a full render: `python -m tt_shorts.engine still <story.json>` (one PNG per scene).
- Every render first runs the layout probe (where each text really is, per scene); its problems are the
  render's `problems` and hold the video. Free on its own, before paying for a voice:
  `python -m tt_shorts.engine probe <story.json> --look all` (see `veasy:qa`).

## 5. QA before anyone sees it

`python -m tt_shorts.engine qa <file.mp4> --format news`, then follow `veasy:qa`.

## 6. Every other surface (free, seconds)

`python -m tt_shorts.engine package <file>.json` (the render's manifest): subtitles, a cover, a 4:5 carousel, a
teaser, the platforms' titles and captions and a Telegram post, from the same render with no new voice. See
`veasy:package`.

## Hard rules (the engine enforces most; don't work around them)

- The brand pack draws the colors, logo, link and words: one accent color for the dot, the active state and the
  CTA button, never for text. Don't restyle a video by hand; change or add a pack (`veasy:brands`).
- The date, the outlets and the story link come from the source's data, never from a writer.
- No publisher photos. No opinion. Sensitive stories are skipped, not softened.
- Secrets live only in `data/.env` on the server; never print, commit or paste them.
