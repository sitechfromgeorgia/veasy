---
name: plates
description: "Use when a Veasy film should have a moving, made ground behind a scene: a slow clip in the pack's own colours with the words still real text on top. Baking a plate, toning it for a pack, listing the shelf, putting a plate scene in a Remotion film or the plate block in a composed film, and why a story was refused a plate. Examples: \"give this explainer a calm moving background\", \"bake a plate\", \"why was my plate refused\", \"use the plate block\""
---

# Plates: a made ground behind a scene

A plate is a short grey clip drawn once in headless Chrome (three.js on software GL) and played behind a scene as a
local file. Both engines only read an mp4, so the words stay DOM text and every Veasy check still sees them. It is free:
no video API, no model.

## The one line

```bash
python -m tt_shorts.engine plate example --seconds 6 --seed 3
```

or the tool `veasy_plate(kind="example", seconds=6, seed=3)`. You get JSON: the plate's `hash`, `cached`, `ms_per_frame`,
`clips[pack][theme]` (one toned mp4 for every pack and theme, relative to `$VEASY_HOME`), `master`, `poster`, `anchors_file`.
The same call again answers from the cache (the plate is a function of the kind's files, spec, seed, seconds and scale).
`python -m tt_shorts.plates example ...` is the same command without the engine's imports.

- `plate list` shows the shelf, `plate check` lints every kind (a clock, `Math.random`, text drawn in pixels, a URL).
- `--scale 0.5` bakes a half-size preview (a different plate, a different hash).
- Kinds on the shelf now: see `engine options --section plates` (`kinds`). A kind is a folder `plates/<kind>/`; how to
  write one is `plates/README.md`.

## Never for news, crime, incidents or deaths

A plate is a made picture; it decorates an idea, it never depicts an event or a place. Three places refuse it, each with
a test: the command (`--program news`, `--family crime`, `--text "..."` with a word of a death or an incident), the
checks (`engine check`: a plate scene in a story with no program, in the crime family, or with such words in its
narration or screen text) and the news rules (`plate` is not in `news_check.SCENE_TYPES`, so N1 refuses it). Do not try to
work round it: change the story's form (an explainer about a mechanism is fine; a report of an accident is not).

## In a Remotion film: the `plate` scene

```json
{"type": "plate", "at": "ეროვნული ბანკი", "kicker": "პოლიტიკა", "headline": "მკაცრი მონეტარული პოლიტიკა",
 "label": "მოდელი", "em": "მკაცრი"}
```

- Only text is yours: `headline` (required, 40), `kicker` (24), `label` (28), and an `em` phrase of the headline. Program must
  allow it (`explainer` does; `news` never). `stories/veasy-plate.json` is a whole working example.
- The plate itself, where the card sits (`top`, `mid`, `low`) and the accent dot that follows the plate's anchors are code's:
  `engine plan` / `engine media` / `write` pick a baked plate from the shelf, the least used lately by the brand, and write
  the scene's `plate` and the story's `assets` ledger (kind `plate`, hash, seed, licence `own`). Never write those by hand.
- An empty shelf is a warning, never a lost video: the scene is the same card on the plain canvas. A queue job never bakes:
  bake ahead (`plate <kind> --seconds 6 --seed n` a few times), then films pick from the shelf.
- The card is solid (92% canvas) with a line: text over a bare plate would fail the probe's black and white grounds.
- Text stays above y=1380; below y=1100 nothing right of x=940 (the `low` card is narrower for that).

## In a composed (HyperFrames) film: the `plate` block

`engine compose scaffold <story> --blocks "kinetic-headline,plate,end-card"` (block *i* is scene *i* of the story, so the
story's scene *i* must be a `plate` scene, and its plate is resolved first: `python -m tt_shorts.engine media <story>`).
Fill the block's three slots (`kicker`, `headline`, `label`: words). Veasy writes `assets/plates/<ledger id>.mp4`
(toned for the film's theme) and `assets/plates.json`. Writing it by hand instead: a plain
`<video muted playsinline loop data-start="0" src="assets/plates/<id>.mp4">` inside a band at y 248-1380, with the words in a
card on `var(--canvas-90)`; no `<canvas>`, no other file. Follow the dot by tweening an element along `tracks.dot` of
`assets/plates.json` (page pixels at 30 fps), a chain of `ease: "none"` tweens.

## What a plate costs

Baking (once, per plate, software GL, 1080x1920, a shared i7 machine): the example is 190-640 ms a frame (a 6 s plate
takes 1 to 4 minutes; half scale about a third of that), plus about 3 s for each pack/theme toning. That is why the shelf
exists and a queue job never bakes: at 50 videos a day a fresh plate each would add 37 to 135 minutes.

Reading a plate (per film, measured on this machine while other jobs ran):
- the cache answer: 0.2 s in process, 1.3-2.4 s as a command here (Python and node start-up under load);
- Remotion (`OffthreadVideo`, frames pulled by ffmpeg): about +0.3 s a frame of the plate's scene (a 29 s film: 218 s with a 5 s plate scene, 167 s without);
- HyperFrames (a `<video>` seeked per frame): no measurable cost (the same film: 137 s with the plate playing 17 s, 146 s without); a plate shorter than its scene loops with `loop`.

Tone: black becomes the pack's canvas and white its ink along the straight line between them (ffmpeg `gradfun` on the grey,
then one lookup per channel): the toned frame holds colours of that line only (tested for both packs and both themes), the
clip after x264 stays within a mean of about 1 colour step of it. The accent is never in a plate; it is the DOM dot.

## Don'ts

- No text, logo, accent or real place in a kind; no `Math.random` or clock (use `plates/lib/seeded.mjs`).
- No generated image in a plate (this lane ships none); no opinion scene; the writer never sets `plate` or `assets`.
- Don't edit `assets/plates/` in a composed film: it is Veasy's (locked); don't bake inside a render or a queue job.
