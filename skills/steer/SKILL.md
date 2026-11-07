---
name: steer
description: "Use when a finished or planned Veasy film needs one small change: a wrong label, a number, a word on a card, a scene that rushes or drags. Redraws only that scene and says the cost first. Examples: \"fix the date on scene 1\", \"scene 3 is too slow\", \"what will this change cost\", \"show me every scene of the film\""
---

# Steer a film (the edit room)

One wrong label used to mean a full render. Now a film is cut by scene into cached pieces (`segments.py`, keyed by a
hash of what each scene depends on), so a change redraws only the scenes it touches. Voice and music are never cut
by scene: they are mixed once over the joined picture.

## The line

```
python -m tt_shorts.engine steer <story.json|render.mp4> --scene 1 --set label="..." --dry
```
(tool `veasy_steer`). Run it with `--dry` first. Read `cost`, then run it again without `--dry`.

| You want | Say | `--dry` answers |
|---|---|---|
| a word, label or number on a card | `--scene 1 --set label="..."` | `4.8 s of picture (scene 1 of 11, frames 297-440), $0` |
| a scene shorter / longer / its payoff held | `--scene 3 --tighter` / `--breathe` / `--land` | the scene and its neighbour (the cut moves), `$0` |
| the spoken words | `--set narration="..."` | `new voice, every frame` (later frames move, so it is a full render) |

- Slots are the brush's own (`engine options`, skill `veasy:write-script`): `label`, `headline`, `lines`,
  `items[0]`, `items[1].label`. Repeat `--set`. A list or object is given as JSON.
- `--tighter` takes 0.4 s off the scene, `--breathe` adds 0.5 s, `--land` adds 0.3 s and marks the key phrase
  (`em`) when the voice says it. Each is checked by `motion_rules`: a scene never goes below the time its text
  needs to be read; if it would, the dry run lists the hold under `problems` and nothing renders.
- `problems` lists only what this change broke. Older problems are `check`'s.
- Date, sources, QR, colours and layout are code: steer never changes them. Never change a fact to fit a label:
  the news rules (`news_check`) run again on the new story.

## The room

`engine room <story.json|render.mp4>` (or any steer) writes `<render>.room.html`: every scene's still, its words,
timing, rhythm (RUSHED / SLACK / DENSE / BALANCED), whether it is cached, and a ready command to copy. Open it,
pick the scene, copy the command, add `--dry`. A story with no render yields a schematic still per scene, free.

## After a steer

`check`, the probe (on the redrawn scenes), flash and QA still apply: `engine qa <file>.mp4`. Both film engines
work (Remotion and HyperFrames); the story's `engine` decides. The saved story is the new truth: the next steer
starts from it. Related: `veasy:qa`, `veasy:write-script`, `veasy:compose`.

Whatever changes the film's total length (a timing verb on the last scene, a narration change) moves the progress
bar and the pan on every frame, so its `--dry` says every scene: that is the true cost, not a bug.
