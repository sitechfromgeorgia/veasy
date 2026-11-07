# Ink plates

A drawing painted on screen mark by mark, in a real material. Every hatch and every drag of the stick is its own mark,
laid at its own moment, so a film looks made by a hand and not by a template. It is a plate (see
[../README.md](../README.md)): a grey clip baked once and played behind a scene.

```bash
echo '{"material": "chalk", "drawing": "house"}' > s.json
node plates/run.mjs ink --spec s.json --seconds 4 --seed 1 --out out/plates/house
```

Run `npm ci` in `plates/` once first. You get `plate.mp4`, `poster.png` (the middle frame), `plate.json` (the cost in
`ms_per_frame`) and `anchors.json` (`dot`: where the film's accent dot goes, if the drawing has one). Add `--scale 0.5`
for a draft in half the time. Words stay in the DOM: put them over the plate in the film.

## Spec keys

Every key is optional. An unknown key stops the bake.

| Key | Value | Default | What it does |
|---|---|---|---|
| `material` | `chalk`, `pencil_hatch` | `chalk` | The hand that paints it |
| `drawing` | a name from `assets/drawings` (`bus`, `bridge`, `factory`...) | `bridge` | One of the 44 library drawings |
| `strokes` | written by `bake.py --svg` | | A writer's own drawing, in place of `drawing` |
| `reveal` | `stroke`, `scrape`, `print_through`, `flood` | `stroke` | How it arrives (below) |
| `box` | `[x, y, width]` in 1080x1920 pixels | `[40, 640, 1000]` | Where the drawing sits; its height is 0.672 of the width |
| `draw` | seconds | 72% of the clip | How long the painting takes; the rest is a hold, still boiling |
| `start` | seconds | 0.15 | When the first mark lands |
| `boil` | `0` | on | `0` stops the line boil (a still needs no boil) |
| `origin` | `[x, y]`, 0 to 1 of the frame | `[0.5, 0.42]` | `flood` only: where the ink is poured |
| `drain` | `false` | `true` | `flood` only: `false` leaves the frame full, a plain matte |

To paint a writer's own SVG fragment (one that passes `art.sanitize`), write it into the spec first:

```bash
python plates/ink/bake.py --svg drawing.svg --spec s.json
```

## The materials

Light pigment on a dark sheet. Black becomes the pack's canvas and white its ink, so one master serves every pack.
Woodcut, ink wash, blueprint and halftone were built and cut: a fresh-eye critic never gave them 4 of 5
(`docs/research/ink-brush-result.md`).

| Material | The sheet | The marks |
|---|---|---|
| `chalk` | a slate wiped many times | side-of-the-stick tone, a pressed line that skips, dust |
| `pencil_hatch` | toned paper | searching lines, overlapping pulls, nested hatch sets |

## The reveals

| Reveal | What happens |
|---|---|
| `stroke` | The drawing's own order (its `--d` delays), mark by mark |
| `scrape` | A cover dragged off in streaks: the picture was there all along |
| `print_through` | A blurred picture rises through the sheet, then comes sharp in patches, as under a baren |
| `flood` | No drawing: ink poured on, running in fingers, filling the frame and draining away. This is a cut |

### The flood as a cut

`{"reveal": "flood"}` for about 1.5 seconds. Play it over the scene, full frame, `mix-blend-mode: screen`: it covers the
old scene in the pack's ink, and in a 1.5-second clip the frame is fully covered from about 0.8 to 0.9 seconds. Change scene in that gap. Each
part of the frame changes once on the way in and once on the way out, so it passes the flash check
(`tt_shorts/flash.py`). Don't play it shorter than 1 second, and run `flash.measure` on the film.

## What it costs

Measured 2026-11-07 on the i7-7700K, software GL, with other lanes running on the same machine, so these run high. Run
once at full size with no other load before relying on a limit.

| Clip | ms a frame, full size | Half scale | A 4-second clip, full size |
|---|---|---|---|
| `chalk` | 133 to 235 | 101 | 16 to 28 s, plus setup |
| `pencil_hatch` | 153 to 250 | 125 | 18 to 30 s, plus setup |
| `chalk` with `scrape` | 312 | | 37 s, plus setup |
| `pencil_hatch` with `print_through` | 185 | | 22 s, plus setup |
| `flood`, 1.5 seconds | 149 to 191 | | 7 to 9 s, plus setup |

The low figure had the machine least loaded. In the busiest run a chalk clip took 519 ms a frame.

The cost of a frame barely depends on the drawing: every mark is laid once in setup, then a frame only asks which
pigment has landed by `t`. Setup adds 2 to 5 seconds at full size. A clip is baked once and reused, never on the queue.

For a sheet of everything: `python plates/ink/sheet.py` (88 stills, about 30 seconds at a third of full size).

## What it refuses

- A spec with an unknown key, material, reveal or drawing stops the bake.
- `"program": "news"`, and `"family"` of `crime`, `incidents` or `deaths`: a plate never goes to them.
- Text: `<text>` in a drawing is dropped, labels stay in the DOM.
- The accent: an ACCENT dot isn't painted, it comes back in `anchors.json`.
- Colour: the clip is grey whatever happens.

Same spec and same seed give the same mp4 byte for byte, on the same Chrome and ffmpeg.

Different seed, different sheet and different marks. Keep the seed in the film's spec: it is what makes two films of one
drawing different.

## Files

`bake.py` turns drawings into ordered strokes (`drawings.json`, regenerate it when `assets/drawings` changes).
`core.mjs` holds the noise, distance fields, regions, the tone plan and the brush. `materials.mjs` holds the materials,
the reveals and the flood. `index.html` is the page `run.mjs` steps. `stills.mjs` and `sheet.py` make stills
without a clip. A new material is one function in `MATERIALS`, plus a case in `tests/test_ink_plate.py`.
