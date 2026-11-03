---
name: directors
description: "Use when a Veasy video should be a different kind of film (not just another style), when asked which director a story got or why, or when adding or changing a director. Examples: \"make 24835 as a map film\", \"why are all today's videos lists\", \"add a director for sports results\""
---

# Directors (what kind of film a story becomes)

Models told to "be creative" all write the same film, so **code** assigns each story a director before the writer
runs (`tt_shorts/directors.py`, `directors/<id>.json`). A director chooses:
- the scene types (with weights) and the scene count;
- the hook layouts, motifs, entrances and cuts that variety may pick from;
- the motion personality (spring, entrance frames, stagger);
- the **current**, the one direction entrances and cuts move in. With `left`, slides come from the right and move
  left, and push goes the same way. With `up`, things rise.

It never touches the facts, the colors, the fonts, the safe zone or the news rules. It may prefer some of a pack's
themes by name (`"themes": ["light"]`: `draw` does, a drawing on paper); with a format's `theme: auto` variety then
picks among those the pack has and allows.

| id | label | film | current |
|---|---|---|---|
| `data` | ციფრი | a number lands, the frame rebuilds | up |
| `map` | რუკა | the real map carries it | left |
| `type` | სიტყვა-დარტყმა | short type on the beat (light news only) | right |
| `draw` | ესკიზი | the object drawn, then its pictogram | right |
| `chronicle` | ქრონიკა | dated beats in order | left |
| `witness` | ციტატა | the people quoted, verbatim (both sides) | up |
| `brief` | მოკლედ | what, who, when as a service card | right |
| `single` | ერთი კადრი | one fact, few beats | up |

`python -m tt_shorts.engine options` → `directors` lists them with their eligibility and gates. `planned` names
brushes being built (none now: `rail`, `share` and `compare` exist since the brush kit); a director may list one
already, and the writer sees it only once it exists in `engine.SCENES` (`brushes/`). `devices` are not scene
types: a director with `marker` asks the writer to mark the words that matter with `"em"`.

## How a story gets one

- `engine write` / the queue extracts facts from the articles before writing (`directors.facts`):
  - quantities (numbers that are not dates or times), dates, times;
  - places in the gazetteer;
  - quotes of 4+ words and their speakers;
  - icons, deaths, the category family.
- `variety.direct` takes the eligible directors and picks the one used least among the brand's last 20 videos.
- The writer's prompt gets the director's brief, only its scene types, and the fact list.
- The story keeps `"director"`. It is code-owned, like `date`: the writer's is dropped, and `check` refuses an
  unknown one. A re-render keeps it.
- Gates:
  - `type` is never used for politics, world or crime, nor for deaths.
  - `draw` is never used for crime.
  - `witness` must show 2 speakers when the articles quote 2 or more. `check --sources` enforces this.
- `write` returns `warnings` when the writer strayed from the director's types or count. This is not a failure.

## Override

```bash
python -m tt_shorts.engine write  --ref 24835 --director map
python -m tt_shorts.engine render stories/24835-brief.json --director data --engine silent
python -m tt_shorts.engine queue  add --ref 24835 --director chronicle
```
A hand-written story may set `"director"` itself. Render without one and nothing changes: today's motion and the
full variety sets apply.

The demo is one story under three directors, with the same facts:
- `stories/24835-data.json`: the number first, with the longest hold on the stat;
- `stories/24835-map.json`: the place first, the Tbilisi map with both districts, then the gas sign stopping;
- `stories/24835-brief.json`: a service card, points then steps.

## The novelty guard

Inside a director the style picks are few, so two videos can still look alike. Before the voice is paid for,
`variety.choose` compares the planned video with the brand's last 20 (`props.choose`, so render, queue, still,
probe and `engine plan` all pass it; plan shows `novelty` with the fingerprint and records nothing).
- Fingerprint: director, scene sequence, hook, motif, enter, transition, music.
- `similarity`: 1 for each equal field, plus the scene orders' difflib ratio (0-1); 0-7 in all.
  `distance = 1 - similarity / 7`.
- Too close: 5 or more of 7 shared with one recent video (the story's own renders don't count).
- Then the style picks are re-rolled inside the director's subsets: least overused combinations first, at most 64,
  the same for the same story and history. The director, the scenes and a format's fixed cut never change.
- If no re-roll is far enough, the farthest is taken and the render result's `warnings` says so. The video is never
  failed. A re-render keeps its picks.
- `render` returns `novelty` (similarity, distance, nearest story, rerolls). `variety.report()["novelty"]` gives the
  average distance. `variety.assess()` measures a plan without re-rolling.

## Add a director (JSON, no code)

`directors/<id>.json` with every key of `directors.KEYS`:
- `brief`: 6-10 English lines (the device and the form, the first 2 s, what the viewer remembers);
- `scenes {type: weight}`;
- `count [lo, hi]` inside 3-6;
- `hooks`, `motifs`, `enters`, `transitions`: subsets of `options` → `variety`;
- `current`: left, right or up;
- `motion {damping 8-30, stiffness 80-300, enter_frames 6-16, stagger_frames 3-6}`;
- `eligible`: alternatives of minimum fact counts, with `families` to narrow; `{"max": n}` for at most;
- `never`: conditions that rule it out;
- `gates`;
- `holds` (optional): its own scene types it means to hold on. The motion rule lets them stay still for up to 8 s
  instead of 3 s (`motion_rules.HOLD_MAX`). Only `data` has one, `["stat"]`: the owner's call (2026-11-03) is that
  the long hold on the number wins over the 3-second rule.

`tests/test_directors.py` checks that every family keeps at least 2 eligible directors, and that no entrance or
cut opposes the director's current. Run `python -m unittest tests.test_directors` and `engine options`.
