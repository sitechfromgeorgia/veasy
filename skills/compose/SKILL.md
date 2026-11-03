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
- **captions**: never write captions; the locked `captions.html` is captions.py's layout. No caption blocks.
- **media**: only files from Veasy's media layer (the story's `assets` ledger, copied to `assets/media/`). Never
  `media-use`, never HeyGen, never a download or a CDN.
- **the CLI**: run HyperFrames only through `engine compose`. `hyperframes publish|cloud|lambda|tts|media-use|
  feedback|add|skills|auth` are refused; skip the skills' advice to report usage or send feedback.
- **registry blocks**: `add` is refused (it fetches code and brings its own fonts, colors and CDN scripts). To use a
  block's idea, read it and rewrite it into your scene with `var(--token)` colors, the "Brand" face, local scripts.
- **sound**: no `<audio>` in a film; the mix is Veasy's (music bed at one level, sound effects from beat cues).

## The workflow

```bash
python -m tt_shorts.engine compose scaffold <story.json> [--brand sitech] [--template auto]   # a project
python -m tt_shorts.engine compose check <story.json> [--sources <story>.sources.json] [--shots out/shots]
python -m tt_shorts.engine compose render <story.json> --engine silent      # a free preview, then the real voice
```
Tool `veasy_compose` (action scaffold|check|render|promote|templates). Every command prints JSON.

1. **A story** (`veasy:write-script`; fiction: program `story`, `veasy:programs`): narration, `cta`, `characters`
   for fiction, and `scenes` with `at` anchors (they are the storyboard and the words the film may show).
   `engine check <story>` must pass first.
2. **Scaffold.** The project is `$VEASY_HOME/cache/compose/<brand>-<ref>/` (or `--project`). Its agent files come
   from `--template <id>`, `--from <dir>`, the repo's `compose/<story id>/`, or a plain starter (one scene per
   story scene). Re-scaffolding keeps your files and rewrites Veasy's.
3. **Read** `frame.md` (the pack's tokens, type ramp, the frame's bands, the pack's own rules), `facts.json` (every
   fact you may show, by id) and `timing.json` (the words, chapters and beats in seconds).
4. **Write** `beats.json` (chapters, an `end` anchor, and a beat every 1.5-3 s, each anchored to the words that say
   it), `index.html` (background + one host per scene) and `compositions/<scene>.html`. Your own SVG files go in
   `assets/art/`.
5. **Check until `problems` is empty**, and look: `--shots DIR` saves the page at every beat's settled frame.
6. **Render**: `--engine silent` first (free); the real voice (`gemini`) re-times the beats on its words. Through the
   queue: `engine queue add --story <story> [--renderer hyperframes]`.
7. **Review.** A composed film that passed QA ends `held` (error_class review) until a person watches it:
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
- **Text is data.** Every text inside a `data-probe="scene"` region, in the DOM (HTML or inline SVG `<text>`);
  never in a `<canvas>`, WebGL or an image.
- **The pack draws.** Colors only `var(--canvas|panel|ink|muted|accent|line|line-strong|grid|ticker|...)`, tints
  `--ink-10/20/40`, `--canvas-0/90`; SVG colors through CSS classes (`.k { stroke: var(--ink) }`), not attributes.
  Face "Brand" only. No logo, link or domain in a scene: the chrome has them. The pack's design rules in frame.md
  (tbilisi.today: the accent is never text).
- **The frame.** Scene text inside y 248-1380; below y 1100 nothing right of x 940; the captions end at 1552 and the
  band under them carries motion only. Sizes from the type ramp; nothing under 24 px.
- **The chrome is locked.** index.html hosts `compositions/chrome.html` (z-index 30) and `captions.html` (40); scene
  hosts stay under 30. Never edit, restyle, cover or remove them: they are hashed (`lint locked`); scaffold
  restores them. `film` chrome (program story): logo, chapter bar, meter wipes, link, end card; `news` adds the
  date, the source line and the ticker.
- **Frame 0 is the thumbnail**: the hook is on screen at 0 (settling a few px, never fading in from nothing).
- Network: only files inside the project; the only scripts are `assets/vendor/gsap.min.js` and
  `assets/vendor/veasy.js` in index.html.

## What `compose check` runs

The story's own checks (`engine check`), Veasy's files against their hashes, our **lint** (rules: color, font,
link, net, canvas, probe, fact, host, locked, art), the **layout probe** at every beat's settled frame (band,
rail, captions, frame, overflow, glyph, font, size, the pack's accent rule, a text outside a region, any network
request), the **story's rule tier** + K rules + kaeasy on every text the DOM shows (news: numbers, quotes, no
relative days against the articles; claims and law; story: S1, no real person), slots filled, and `hyperframes
check` (its errors are problems, its warnings shown). A bound fact still counting at a settled frame is a warning.

## Templates

`engine compose promote <project> --as <id> [--label "..."]` saves a film **the owner approved** as `templates/<id>/`:
its scenes with every fact and typed word turned into a slot, its beats without anchors, and `manifest.json` (each
slot's kind and example). `compose scaffold <story> --template <id>` (or `auto`: the least used for the brand)
starts a new film from it: fill `slots.json` (a fact slot `"=<fact id>"`, a words slot the words) and the beats'
anchors, then scaffold again and check.

## Don'ts

Never type a fact, a color, a font or a link; never fetch; never draw text in a canvas; never touch the chrome;
never publish a film whose check or QA has problems, or a silent or edge preview.
