---
name: compose
description: "Use when a video is composed by the agent itself for the HyperFrames engine instead of the Remotion brush kit: an animated story or fable, a cartoon, a product or brand film, a tutorial, or a news story told in a form the kit doesn't have. Also for turning an approved composed film into a reusable template. Examples: \"make a short cartoon about a robot for SiTech\", \"compose 24835 as a film\", \"make a product film\", \"promote this film to a template\""
---

# Compose a film (HyperFrames, through Veasy)

Veasy has two film engines, both first-class: **Remotion** (the typed brush kit: you fill text slots, code draws)
and **HyperFrames** (you write the film in HTML/CSS/GSAP). Either way the film gets Veasy's voice and word timings,
captions (`captions.py`), the brand pack, the music and the ffmpeg mix, the checks, QA and the queue. Which engine a
video uses is its `"engine"`: the director's, else the program's, else the format's, else the pack's, else remotion
(`engine render --renderer hyperframes` overrides). The `story` program (fiction) is `hyperframes` by default.

## The engines' own skills, and which wins

`ops/install.sh --skills --profile <name>` installs, pinned, Remotion's skills (`remotion-*`) and HyperFrames'
(`hyperframes`, `hyperframes-cli`). Read `hyperframes` for the composition format, motion and craft. Where they
overlap with Veasy, **Veasy wins**:
- **captions**: never write captions; the locked `captions.html` is captions.py's layout in the format's design
  (page, roll, or keyword: one keyword a page in the pack's style). No caption blocks of HyperFrames' own.
- **media**: only the story's pictures from Veasy's media layer (`veasy:media`: its `assets` ledger and a scene's
  `media`), copied to `assets/media/<id>.<ext>` and listed in `assets/media.json` with each one's label and credit
  (show both with the picture). Never `media-use`, never HeyGen, never a download or a CDN.
- **the CLI**: run HyperFrames only through `engine compose`. `hyperframes publish|cloud|lambda|tts|media-use|
  feedback|add|skills|auth` are refused; skip the skills' advice to report usage or send feedback.
- **registry blocks**: `add` is refused (it fetches code and brings its own fonts, colors and CDN scripts). To use a
  block's idea, read it and rewrite it into your scene with `var(--token)` colors, the "Brand" face, local scripts.
- **sound**: no `<audio>` in a film; the mix is Veasy's (`props.mix_audio`: the voice, the music bed at one level,
  and, when the format says `sfx: on`, a whoosh on every meter wipe plus the sound a beat names: `"sfx": "pop"`,
  one of click, pop, whoosh, tick, thud, blip).

## The workflow

A film is made twice: in words, then in scenes. Build nothing before an idea is picked, and pay for no voice before
someone has looked.

```bash
python -m tt_shorts.engine compose blocks                                      # list all available blocks
python -m tt_shorts.engine compose scaffold <story.json> [--blocks b1,b2,b3]   # assemble from blocks
python -m tt_shorts.engine compose scaffold <story.json> [--template auto]     # or start from a template
python -m tt_shorts.engine compose check <story.json> [--sources <story>.sources.json] [--shots out/shots]
python -m tt_shorts.engine compose look <story.json> [--video <file.mp4>]      # free: see the film, frame by frame
python -m tt_shorts.engine compose render <story.json> --engine silent         # a free preview, then the real voice
```
Tool `veasy_compose` (action scaffold|check|look|render|promote|templates|blocks). Every command prints JSON.

1. **A story** (`veasy:write-script`; fiction: program `story`, `veasy:programs`): narration, `cta`, `characters`
   for fiction, and `scenes` with `at` anchors (they are the storyboard and the words the film may show).
   `engine check <story>` must pass first.
2. **The idea, in `STORYLINES.md`.** First a line: what the viewer keeps. Then three different films, not three skins
   on one: each has its own *object* (the one thing from this story that can be shown and can change), its own
   *device* (what the film does with it) and its own *form* (how the cuts or the camera carry it), plus its first 2
   seconds exactly, its beats in a line, its look inside the pack and its sound. Test each: swap in another story; if
   it still works, it is a format, not an idea. One of the three is the bold one you wouldn't pick first. Pick the one
   a stranger would follow and say why. News and law: the picture shows the fact and adds no meaning (the object
   itself, how it works, its place, a number's real size), never a metaphor that argues.
3. **The shots, in `SPEC.md`.** For each beat: its words, what is on screen when it settles, what changed, what
   carries over from the last scene. Then the one hero moment, and the defaults this film refuses.
4. **Scaffold.** The project is `$VEASY_HOME/cache/compose/<brand>-<ref>/` (or `--project`). Its agent files come
   from `--blocks <b1,b2,...>` (reusable blocks assembled in order), `--template <id>`, `--from <dir>`, the repo's
   `compose/<story id>/`, or a plain starter (one scene per story scene). Re-scaffolding keeps your files and
   rewrites Veasy's.
5. **Read** `frame.md` (the pack's tokens, type ramp, the frame's bands, the pack's own rules), `facts.json` (every
   fact you may show, by id) and `timing.json` (the words, chapters and beats in seconds).
6. **Write** `beats.json` (chapters, an `end` anchor, and a beat every 1.5-3 s, each anchored to the words that say
   it), `index.html` (background + one host per scene) and `compositions/<scene>.html`. Your own SVG files go in
   `assets/art/`.
7. **Check until `problems` is empty.** A `novelty` warning names the recent film this one resembles: change the
   film, not the wording. `--shots DIR` saves the page at every beat's settled frame.
8. **Look.** `engine compose look <story>` saves in `.veasy/look/` a sheet of every scene and beat, a strip
   across every cut, the beat frames at phone width and `timeline.json`, and says which eases the film leans on; with
   `--video <file>` it measures the sound too (`audio.json`). Open every sheet. Then a fresh eye: a sub-agent gets only
   `SPEC.md` and the sheets, never your reasoning, and says what a stranger sees in each frame, whether the pictures
   alone tell the story, what can't be read at phone width and what jumps at a cut. Its notes, one a line:
   `t=4.2s · where · problem -> change`, P0 (breaks the read) or P1 (weakens the film), never a score. Fix the P0s and
   write `REVIEW.md`: the notes, what you kept on purpose, the weakest shot, what nobody checked (sound is measured,
   not heard). Look again only at what you changed.
9. **Render**: `--engine silent` first (free); the real voice (`gemini`) re-times the beats on its words. Through the
   queue: `engine queue add --story <story> [--renderer hyperframes]`.
10. **Review.** A composed film that passed QA ends `held` (error_class review) until a person watches it:
   `engine queue approve <id>` or `reject <id>`. A format's or program's `review: until:<n>` lets a brand's films
   through after n approved in a row.

## The contract of a scene

- One HyperFrames composition in `<template>`; its root `data-composition-id` = the host's id = its timeline key
  (`window.__timelines["s3"]`). Prefix every id with the scene's (`s3-num`). `fromTo`, never `from`.
- **Facts are bound, not typed.** A number, a date, a time, a quote, a name, a source: `<span data-var-text="num-1">…
  </span>` with the id from facts.json (`scene-<i>-<field>` are the story's own scene texts). In a script:
  `VEASY.fact("scene-1-value")`. A digit or „“ typed in a text node fails the lint.
- **Time by beats, not seconds.** Host: `data-beat="number" data-until="when"` (+ `data-beat-shift`,
  `data-until-shift`); Veasy writes `data-start`/`data-duration`. In a scene script:
  `const A = (b) => VEASY.at(b, "s3")` gives a beat in the scene's own seconds, so the film keeps its timing under
  another voice. `VEASY.beat(id)`, `VEASY.duration`, `VEASY.end` too.
- **One scene at a time.** A scene has left by the beat the next starts; hosts overlap only under a chapter's wipe.
  `probe cut`: text on the other scene's text or drawing is a problem, two drawings a warning (a match cut).
- **Text is data.** Every text inside a `data-probe="scene"` region, in the DOM (HTML or inline SVG `<text>`); never
  in a `<canvas>`, WebGL or an image, in CSS `content` (a shape's is `""`), a counter, a list's numbers or an input,
  and never as letters or digits outlined into SVG paths. No check can read those.
- **The pack draws.** Colors only `var(--canvas|panel|ink|muted|accent|line|line-strong|grid|ticker|...)`, tints
  `--ink-10/20/40`, `--canvas-0/90`; SVG colors through CSS classes (`.k { stroke: var(--ink) }`), not attributes.
  Face "Brand" only. No logo, link or domain in a scene: the chrome has them. The pack's design rules in frame.md
  (tbilisi.today: the accent is never text). A pack may have several themes (dark, light: `--theme`, a format's
  `theme`); tokens only, and the same scenes draw in every theme (the probe's contrast rule checks each).
- **The frame.** Scene text inside y 248-1380; below y 1100 nothing right of x 940; the captions end at 1552 and the
  band under them carries motion only. Sizes from the type ramp; nothing under 24 px.
- **The chrome is locked.** index.html hosts `compositions/chrome.html` (z-index 30) and `captions.html` (40); scene
  hosts stay under 30. Never edit, restyle, cover or remove them: they are hashed (`lint locked`); scaffold
  restores them. `film` chrome (program story): logo, chapter bar, meter wipes, link, end card; `news` adds the
  date, the source line and the ticker.
- **Frame 0 is the thumbnail**: the hook is on screen at 0 (settling a few px, never fading in from nothing).
- Network: only files inside the project; the only scripts are `assets/vendor/gsap.min.js` and
  `assets/vendor/veasy.js` in index.html.

## The Block Library (`compose/blocks/`)

Reusable, verified scenes (`engine compose blocks` describes them): `kinetic-headline`, `number-reveal`, `map-pin`,
`comparison`, `icon-grid`, `quote`, `process`, `chapter-card`, `end-card`. `--blocks <id1,id2,...>` stitches them into
`index.html` hosts and `beats.json`. A block is a start, not a film: rewrite it to carry the idea.

## What `compose check` runs

The story's own checks (`engine check`), Veasy's files against their hashes, our **lint** (15 rules, in
`engine options`), the **layout probe** at every beat's settled frame (the frame's bands, overflow,
glyph, font, size, the accent rule, stray or generated text, any network request) and through every cut, the
**story's rule tier** + K rules + kaeasy
on every text the DOM shows (news: numbers, quotes, no relative days against the articles; claims and law;
story: S1, no real person), slots filled, and `hyperframes check`.
A bound fact still counting at a settled frame is a warning, as are a film close to the brand's recent composed films
(`novelty`) and a missing `STORYLINES.md` or `SPEC.md`.

## Templates

`engine compose promote <project> --as <id> [--label "..."] [--about "..."]` saves an approved film
as `templates/<id>/`: its scenes with every fact and typed word turned into a slot, its beats without anchors,
and `manifest.json` (each slot's kind and example).
`compose scaffold <story> --template <id>` (or `auto`: the least used for the brand) starts a new film from it:
fill `slots.json` (a fact slot `"=<fact id>"`, a words slot the words) and the beats' anchors, then scaffold
again and check.

Agents prepare template candidates; the owner marks a film approved.

## Don'ts

Never type a fact, a color, a font or a link; never fetch; never draw text in a canvas, in CSS or as paths; never touch
the chrome; never publish a film whose check or QA has problems, or a silent or edge preview.
