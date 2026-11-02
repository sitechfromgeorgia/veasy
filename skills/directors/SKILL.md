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

It never touches the facts, the palette, the fonts, the safe zone or the news rules.

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
brushes being built (`marker`, `rail`, `share`, `compare`). A director may list them already, and the writer
sees one only once it exists in `engine.SCENES`.

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
A hand-written story may set `"director"` itself (`stories/24835-brief.json`). Render without one and nothing
changes: today's motion and the full variety sets apply.

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
- `gates`.

`tests/test_directors.py` checks that every family keeps at least 2 eligible directors, and that no entrance or
cut opposes the director's current. Run `python -m unittest tests.test_directors` and `engine options`.
