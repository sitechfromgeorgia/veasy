---
name: media
description: "Use when a Veasy video should have pictures, clips, a screenshot or sound effects: giving scenes a show hint, resolving a story's pictures, checking their licences and credits, screenshots of an official page, or turning sound effects on. Examples: \"put photos behind the gas story\", \"why has this scene no picture\", \"add a screenshot of the law\", \"turn on sound effects\", \"is this image licensed\""
---

# Media: pictures, screenshots and sound effects

The media layer (`tt_shorts/assets.py`, one module per provider in `tt_shorts/media/`) is engine-free: Python
turns everything into local files and a ledger before the voice is made; Remotion (and HyperFrames) only draw
files. The writer only suggests; code finds, checks, labels and credits.

## Pictures behind scenes

1. Give 2-4 scenes a `show` hint: a short English query of 1-5 plain words for an ordinary thing or place.
   - ✅ `"gas pipeline repair"`, `"apartment buildings"`, `"city bus"`, `"video: traffic at night"` (a clip; only
     with a Pexels or Pixabay key).
   - ❌ a person's name, a logo or brand, text, the event itself („the Rustavi explosion“).
   - `"screenshot"`: the story's own official page (a law's article on matsne.gov.ge);
     `"screenshot:https://matsne.gov.ge/... | მუხლი 17"`: that page with a box around the phrase.
   - Not on `where` (the map is its picture), `end` or `chapter`.
2. Resolve it: `python -m tt_shorts.engine media <story.json>` (`write` and `plan` do it on their own). It fills
   the scene's `media` and the story's `assets` ledger in place. Both are code's: never write them by hand.
3. Check: `engine check <story> --sources <articles>`, then `engine plan` / `engine probe --look all` to see it.

How a picture is chosen:
- Pictures are opt-in per pack: `media.providers` is empty in the base (`_ka`), so no story gets a picture until
  a pack lists its providers (2026-11-03: stock relevance is still middling and nobody reviews the daily run).
- Providers in the pack's order (`media.providers`): Openverse and Wikimedia Commons (no key), Pexels and
  Pixabay only when `PEXELS_API_KEY` / `PIXABAY_API_KEY` is set (otherwise skipped, never an error).
- Licences that allow commercial use only: CC0 and public domain first, Pexels and Pixabay, then CC BY, then
  CC BY-SA last (a BY-SA picture may pull the video under the same licence). Commons files with restrictions
  (personality rights, trademarks) are dropped.
- Skipped: titles of events (fire, crash, police, protest...), of text (maps, charts, logos, posters), portraits,
  and pictures whose title or tags name nothing of the query.
- One pick per story among the best four of the freest licence found, seeded by the story: the same picture on
  every re-run (searches are cached in `cache/media/`). A scene keeps its picture while its hint is unchanged.
- A provider that fails leaves the scene without a picture (a warning), never fails the story.

The ledger entry: `{id, kind, provider, url, page, licence, licence_version, author, title, source, query,
fetched, sha, file}`. `engine check` refuses a licence outside the allowed ones, a CC BY one without its author,
a scene whose media is not in the ledger. A file `gc` removed is fetched again and must have the same sha.

On screen: full-bleed under a dark scrim of the pack's canvas (editorial, kinetic), or the card's image (cards),
with a slow push-in. The pack's label („საილუსტრაციო“) and the credit (author · licence · source) sit in a quiet
row at the bottom of the scene. A clip plays muted.

## News rule N13 (`news_check.imagery`)

- Every illustrative picture carries the pack's label; code adds it, nothing turns it off.
- No illustrative imagery for crime, incidents or a story about deaths (code drops the hints; check refuses).
- No AI imagery: `media/ai.py` is the interface, disabled until the owner decides.
- Screenshots only from the allow-list: the pack's `media.official` and `media.own`, plus a program's
  `screenshots` (`veasy:brands`, `veasy:programs`). Never a publisher's article page.
- The scene a picture sits behind never presents it as the event: no „ფოტოზე“, „კადრებში“, „ვიდეოში“.

## Screenshots

`tt_shorts/media/screenshot.py` drives the chrome-headless-shell Remotion already installed through a tiny Node
script (`media/shot.mjs`, the DevTools protocol, no new dependency) at 1080x1920, scrolls to the phrase and draws a
box around it in the pack's accent. The URL is checked before the page opens and again after redirects.

## Sound effects (format key `sfx`)

`--sfx on` on render/plan, or `"sfx": "on"` in a format (`veasy:formats`); default `off`. The sounds are
synthesized by `tools/compose_sfx.py` (click, pop, whoosh, tick, thud, blip; composed on first use). Cues come from
the timeline (`tt_shorts/sfx.py`): a whoosh on each cut (a click on a plain `cut`), a pop when a mark or the outro
chip lands, ticks while a stat counts and a thud as it settles, a blip as each bar grows. One track at one constant
level under the voice, mixed by ffmpeg: no ducking, no risers.

Demo: `stories/24835-media.json` (four pictures from Openverse and Commons, credits on screen).
