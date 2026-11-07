---
name: draw
description: "Use when a Veasy film needs its own drawings: 1-3 line drawings of what the story is about (a cart for prices, a gauge for a rate, a valve for gas) that draw themselves under a scene's text. Draw them by hand as a scene's \"art\", or let the illustrator draw them with one cheap model call. Examples: \"draw something for scene 2\", \"the film has no pictures\", \"this drawing failed the checks\", \"make the films look less alike\""
---

# Draw the film's pictures

Two films with the same scenes and a list look alike. What tells them apart is a drawing of the story's own thing
(owner, 2026-11-07: "the visual follows the topic"). A film gets 1-3 of them (`tt_shorts/vignettes.py`): each stands
centred in the room under a scene's text and draws itself stroke by stroke while the voice says that part.

Where a scene's drawing comes from, first match wins:
1. its own `"art"`: an SVG fragment you (or the illustrator) wrote;
2. the library: a hand-made drawing of a thing its part of the narration names (`assets/drawings/`, 44 of them);
3. none.

None at all for crime, incidents or deaths, in a film with a thread (`veasy:direct`), or on an `end`, `sources`,
`where`, `chapter`, `draw`, `sign`, `plate` or `state` scene, a stat with an icon, or a scene with a photo.

## See what a film will draw (free)

```
python -m tt_shorts.engine vignettes <story.json>
```
`vignettes`: which scene draws what (`source`: `story` is its own art, `seed`/`done` the library's) and its seat.
`illustrator.would_draw`: the scenes the illustrator would be asked for (the hook, then the scenes the library has
nothing for). `warnings`: a scene's own drawing that failed and was replaced.

## Let the illustrator draw (one cheap call)

```
python -m tt_shorts.engine vignettes <story.json> --draw [--out drawn.json]
```
One model call (two when a drawing fails and goes back once with its problems). It writes the drawings that pass
into the story; a failing one is left out, and the film still goes out. The writer runs this step by itself after
every script. The model is `VEASY_ILLUSTRATOR_MODEL` (default: the writer's), any OpenAI-format server, so a cheap
one; `VEASY_ILLUSTRATOR=0` turns it off. Its full guide is `tt_shorts/illustrator.py` `GUIDE`.

## Draw one by hand

Put it on the scene as `"art": "<g ...>...</g>"`. Work in this order.

1. **The subject.** ONE thing a viewer recognizes in a second, from that scene's part of the narration:
   | the part says | draw |
   |---|---|
   | food prices rise | a shopping cart with a price tag and a small arrow up |
   | inflation against a target | a gauge, its needle just past the mark |
   | a gas cut | a pipe with a closed valve |
   | a fare, a route | a bus at a stop |
   | a bank, a ministry, a court keeps or decides | the building, columns and steps |
   | a new road, a bridge opens | the bridge over water |
   Never an abstract shape, a chart, a map, a flag, a logo, a face or a person. A drawing has no words, so it can't
   carry a fact: the number stays in the scene's text.
2. **The parts.** Write down 4-8 parts, biggest first, each with its box on the 952x640 canvas
   ("dial: arc centre 476,470 r 300"). The thing fills the canvas: at least 60% wide or high.
3. **The SVG.** Draw exactly those parts:
   - `rect circle ellipse line polyline polygon path` (path: M L Q C A Z); 8-30 elements, under 4000 characters;
   - fill `none`, stroke-width 6-8 for outlines and 4-5 for details;
   - colours are tokens only: `INK` main lines, `MUTED` details, `LINE` a faint floor or grid, `CANVAS` a solid fill
     that hides lines behind it, and `ACCENT` for ONE small dot (a circle r 8-24) on the focal part;
   - no `<text>`: code removes every word anyway.
4. **The motion.** Wrap parts in `<g class="s|r|p" style="--d:0.4s">`: `s` draws the line, `r` rises, `p` pops.
   At least 3 groups with different delays: body first (0.2-0.6 s), details next (0.8-1.4 s), the act and the dot
   last (1.4-2.2 s).
5. **The act** (owner: "moving drawings, not static ones"). ONE part does what the words say, and it plays when the
   voice says the scene's key phrase (`em`):
   | class | does | style | e.g. |
   |---|---|---|---|
   | `t` | turns in to where you drew it | `--turn:-60` degrees, `--at:x,y` its pivot | a needle swings to its mark, a valve wheel closes |
   | `m` | moves in to where you drew it | `--from:0,120` (dx,dy px; default 0,80) | an arrow climbs, a car drives in |
   | `g` | grows from its foot | `--at:x,y` (default its foot) | a bar, a pile, a column |

   One part may also keep moving while the drawing is on screen: `--spin:90` (degrees a second: wheels, a fan,
   clock hands), `--swing:5` (sways around `--at`, where it hangs: a tag, a lamp), `--bob:10` (floats: a boat) or
   `--pulse:1` (breathes: a flame, a signal). Without `--at` code takes the part's own centre (its top for a
   swing). Every drawing also pushes in slowly, so nothing stands still.
6. **Check it**: `engine check <story.json>` lists `scene N (type): art: ...`; `engine vignettes` shows the seat.

A worked example: the gauge for „inflation 3.8% against a 3% target" (the library's `gauge`):
```
<g class="s" style="--d:0.2s"><path d="M176 470 A300 300 0 0 1 776 470" stroke="INK" stroke-width="8"/></g>
<g class="r" style="--d:0.5s"><path d="M186 470 L226 470 M225 325 L260 345 M331 219 L351 254 M476 180 L476 220
  M621 219 L601 254 M727 325 L692 345 M766 470 L726 470" stroke="MUTED" stroke-width="6"/></g>
<g class="r" style="--d:0.9s"><path d="M416 248 A230 230 0 0 1 536 248" stroke="INK" stroke-width="8"/>
  <path d="M156 470 H796" stroke="LINE" stroke-width="6"/></g>
<g class="t" style="--d:1.3s;--turn:-75;--at:476,470"><path d="M476 470 L518 234" stroke="INK" stroke-width="8"/></g>
<circle class="p" style="--d:1.7s" cx="476" cy="470" r="22" fill="ACCENT" stroke="none"/>
```
Dial, ticks, the target band, then the needle swings up from the left to just past the band when the voice says
„3,8", then the dot on the pivot: it builds the way you would explain it.

## What the checks say

| problem | fix |
|---|---|
| `art: the drawing is small (300x200 of 952x640)` | scale the coordinates up; the thing fills the canvas |
| `art: give at least 3 parts a motion class` | split it into 3+ `<g class>` groups with different `--d` |
| `art: style "...": only --d (its delay ...)` | a style says only `--d`, `--at`, `--turn`, `--from`, `--swing`, `--spin`, `--bob`, `--pulse` |
| `art: ACCENT is on 4 dots` | one dot on the focal part; the rest INK or MUTED |
| `art: <image> is not allowed`, a colour that isn't a token | only the shapes and tokens above |
| `art: a end scene shows its own picture or none` | move the drawing to a scene that can hold one |
| `vignettes: scene N's own drawing fails the checks` (warning) | the library's drawing or none is shown instead |

## Choose well

- A different thing on each scene, and not one the library already draws in this film (`engine vignettes`).
- The hook's drawing is the film's emblem, like a SiTech blog card: the one thing the whole story is about.
- A list scene is not a drawing: `points` only when the article itself names separate things (`veasy:write-script`).
- A new drawing that should serve every film goes in `assets/drawings/<name>.json` with its `motif` (an icon name)
  and must pass `tests/test_drawings.py`.
