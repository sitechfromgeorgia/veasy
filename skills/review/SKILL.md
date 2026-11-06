---
name: review
description: "Use after a Veasy story plans or renders and before it is shown or published, to let the film look at itself: free pixel and pacing checks, a capped repair loop that never changes a fact, and a fresh-eye pass over a contact sheet. Works the same for the Remotion and the HyperFrames film. Examples: \"review this story\", \"does 24886 look dull anywhere\", \"two scenes look the same\", \"the film feels like a metronome\", \"fix the frames before I see them\""
---

# Review a film: its own eyes first

One line: `python -m tt_shorts.engine review <story.json>` (tool `veasy_review`). You get back `status`
(`passed`, `fixed` or `held`), the `holds`, the `warnings`, what it changed (`applied_transforms`), `facts_diff`
(always `[]`) and `notes` you can act on. It costs nothing but local work: no voice, no model, no network. Without `--save` the story file is never
changed: the repaired story is only reported (`applied_transforms`). `rounds_executed` counts audits; `machine_rounds`
and `look_rounds` count repairs. Without `--stills` the pixel rules do not run, and the output says so by having no
`pixel_checks` key.

## What it checks

Only two things hold a film. Everything else is a warning until it has been calibrated on approved films.

| Rule | Gate | What it sees |
|---|---|---|
| `read` | **hold** | text shown for less than 0.5 s + 0.3 s a word |
| `flash` | **hold** | more than 3 flashes a second over a quarter of the screen (ITU BT.1702) |
| `same_picture_twice` | warning | two scenes with the same picture (`golden.dhash`) |
| `empty_middle` | warning | no ink in the scene band, or washed-out ink |
| `no_hero_frame` | warning | no frame is the climax: every scene equally light |
| `metronome_cuts` | warning | scenes cut on a steady beat (std dev under 0.4 s, or 4 cuts within 0.2 s) |
| `spoken_redundancy` | warning | a scene only shows the words the voice says |
| `safe_zone` | warning | ink in the social rail (x>940, y 1100-1552), or a hook line over 26 characters |
| `repeat`, `pingpong`, `still` | warning | the motion rules of `engine plan`: same type twice, back-and-forth cuts, nothing moves for over 3 s |

The pixel rules need frames: `engine still <story> --engine silent --out <dir>` first, then
`engine review <story> --stills <dir>`. A still takes about a minute on a busy machine; the story checks need none.

## The loop

`--rounds 2` (default). Hard caps: 3 machine rounds (pacing, layout, line wrapping) and 2 look rounds (transitions,
hook layout). Each round audits, makes one repair, and then compares facts: numbers, dates, names, quotes, sources,
links. A repair that changes one is rejected and the film is `held`. It repairs:

- the same scene type twice (`points` -> `pair` or `steps`),
- cuts that go back and forth (one steady `transition` and `flow`),
- text shown too briefly (the next scene's anchor moves later, a breathing pause is added),
- a hook line too long for the rail.

It never rewrites a quote, a number or a name. When the only cure is a different text, `status` is `held` and the
note says what to change: that is your job, not the loop's.

## Notes

Every note reads `t=4.2s · where · problem -> change`, for example
`t=6.1s · scene 1 (quote) · the same scene type twice in a row -> swap the second for another type or merge the two`.
Act on the lines with `P0` meaning (a hold or the rail) first. `--packet` adds the review packet: the film's spec,
the beat timeline, the reading load, and the sheets. It never contains code.

## The fresh-eye pass

A model's "looks fine" never passes a film; only the checks above hold. But a fresh pair of eyes finds what pixels
cannot, so for a film you care about:

1. Make a sheet of the stills (`engine still`, or `engine compose look` for a composed film).
2. Give a reader who has not seen the code only the sheet and the spec from `--packet`.
3. Ask for notes in the format above. Apply those that name a scene and a change; ignore praise.
4. Run `engine review` again. Stop when it returns `passed` or `fixed`, or after two look rounds: more rounds make
   a film blander, not better.

## Don't

- Don't loosen a rule to get `passed`; fix the story.
- Don't change the story's `date`, `sources` or numbers to satisfy a check: `facts_diff` must stay empty.
- Don't use `--save` on a story another agent is editing; it rewrites the file.
- Don't treat a warning as a hold. Warnings are advice until the owner decides a rule is calibrated.
