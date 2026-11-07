---
name: direct
description: "Use before a Veasy film's script or scenes exist, when the film needs its own idea and not a new skin: to get five ideas from the concrete ladder (object, mechanism, place, the number's body, the role's moment, analogy), have code judge them and keep the one it chooses. The program explainer runs this by itself; an agent composing a film runs it by hand. Not for news, which has no idea step."
---

# Direct: one idea per film

Films look alike when the difference starts at the colors. It starts here, before the script: an idea built from this
story's own nouns. You or the model propose, **code judges and code chooses**, and the story keeps the choice.

```bash
python -m tt_shorts.engine options --section concepts                      # the ladder and what the kit can draw today
python -m tt_shorts.engine concept --source url --ref <url>                # the model writes, code chooses; nothing recorded
python -m tt_shorts.engine concept --source url --ref <url> --ideas i.json # your own ideas, judged the same way, no call
python -m tt_shorts.engine concept --batch refs.json                       # [{"source": ..., "ref": ...}]: a run
```

Tool: `veasy_concept`. Results: `summary` (chosen, calls, devices, rungs, repeated_objects, turned_down) and, per story,
every idea with its `verdict` (`ok`, `flagged`, `rejected`), `rule` and `why`, and the chosen `concept`.

## The ladder

Start at the bottom, climb only as far as the story needs. Each candidate comes from a different rung. Never ask for
"something creative": name the rung.

| rung | question | example: a gas cut | example: a budget law |
|---|---|---|---|
| 1 object | what physical thing is it about? | the valve on the street pipe | the printed table |
| 2 mechanism | what does it do, what happens to it? | the flow stops at the valve | one sum splits into lines |
| 3 place | where can a viewer point? | two districts on a map | the parliament, or nothing |
| 4 the number's body | what does the number look like? | 6 400 beside the districts as they go dark | a 10 x 10 grid, a square per percent |
| 5 the role's moment | what does the role touch, not the name? | the stove knob at 22:00 | nothing |
| 6 analogy | what else behaves like this? | not for hard facts | not for hard facts |

A program says which rungs it allows (`"concept": {"rungs": [...], "ideas": 5}`). The explainer allows all six.

## Pick a form

The form is how the film looks and moves; the plot is `veasy:programs`' and the scenarios'. After the idea, read the
one file that fits, in `references/forms/`. If two fit, take the one whose "Choose it when" names the story's own
noun. If none does, `kit-cuts`: a form must earn its cost. Each file lists its devices, route (kit or composed),
whether `news` allows it, what it demands and what to avoid.

| story is mostly | form |
|---|---|
| facts and a few numbers, or news | [kit-cuts](references/forms/kit-cuts.md) |
| a before and after, a state that changes | [one-frame-rebuilds](references/forms/one-frame-rebuilds.md) |
| a sequence in one place or one thing | [one-take](references/forms/one-take.md) |
| a physical thing that can stand for it all | [through-object](references/forms/through-object.md) |
| one figure that needs a size | [number-body](references/forms/number-body.md) |
| a place, a spread, a journey | [map-led](references/forms/map-led.md) |
| a proof, a rule, a timeline | [evidence-board](references/forms/evidence-board.md) |
| how a thing works | [drawn-explainer](references/forms/drawn-explainer.md) |
| a statement, a quote, a message | [voice-on-record](references/forms/voice-on-record.md) |

Put the choice in the idea: `"form": "<file name>"`. Code does not judge it; `veasy:compose` builds the composed ones.

## An idea

```json
{"rung": 2, "device": "state-change", "idea": "one Georgian sentence: what the viewer SEES happen",
 "object": "1-3 Georgian words: a thing that can be drawn and the narration will say", "verb": "drains",
 "facts": ["6 400"], "p": 0.2, "drawing": "optional: a seed's name in assets/drawings"}
```

`device` comes from `options`: only what the kit can draw today, on that rung. `p` is how likely an average writer is
to think of it; ask for at least two under 0.15. Facts are copied from the source, never summed or rounded.

## What code does

The filters, in order: **shape**, **facts** (every fact is in the source, the one reason to ask the model again),
**loaded** (war, disease, flood, beast: they assert what no source says), **generic** (the object is the film's own
tool, a quote, a list, a map, a sign, not the story's thing), **object** (the family's recent films used it), **seen**
(too close to a recent idea), **swap** (the idea doesn't hold its own facts), **cliche** (the first picture of its
family: flagged, taken only when no clean idea is left). A device that does something beats one that is only the usual
scene, then the least used device wins, then the least used rung, ties by the story id's hash. Code rotates, it doesn't
judge taste: don't argue with the choice, write better ideas.

No idea left means no concept: the film is written as before, with a warning. A script that can't carry its idea after
its repairs keeps its place and loses the idea, with a warning. The step never loses a video.

## After the choice

- **The writer's line:** `engine write` runs all this itself for a program with the step. The story keeps `concept`,
  code-owned like `date`, and `check` asks that the narration says the object and a scene of the device carries it.
- **A composed film:** run `concept --ideas`, then build `SPEC.md` on the chosen idea. The device, the form and the
  object are the film; `STORYLINES.md` keeps the ideas turned down (`veasy:compose`).
- **The thread:** a chosen idea's `object` becomes the film's through-line by itself. Code takes a drawing (the story's
  own `draw`, else a seed you name in the idea's `drawing`, else the object's motif), seats it in the scenes, moves it
  over the cuts and changes its state by `verb`: drains, fills, breaks, grows, shrinks (`options --section thread`). You
  pick nothing about layout. A `state` scene does the whole change; `was` and `now` are its two words. A verb outside
  the list keeps the object as it is. No drawing, or under 3 scenes: the kit's film, with a warning.
  `engine thread <story>` shows the plan for free.
- A concept is never on screen, so it can carry no fact. It changes how the film shows the facts, never what it says.

## Hard limits

- `news` has no idea step and `programs.validate` refuses one: its rules stay as they are until the owner decides.
- No opinion, no blame, no cause the source doesn't state. Take the voice away: what does the picture alone assert?
- Brand-neutral: the data in `concepts/` is by family, no client's word goes there.
- A new device goes in `concepts/devices.json` with the scene types that can draw it (empty: it waits for the kit); a
  new cliche in `concepts/cliches.json`. `tests/test_concept.py` checks both.
