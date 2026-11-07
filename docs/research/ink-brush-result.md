# The ink brush: result

Lane `goal/ink-brush`, `plates/ink/`, 2026-11-07. Base commit 587cd49. Antigravity wrote the research; the build is from
this run. Not rebased onto main, not pushed.

**Shipped:** `chalk` and `pencil_hatch`, four reveals (`stroke`, `scrape`, `print_through`, `flood`), the bake step, the
contact sheet, the README. **Cut:** `woodcut`, `ink_wash`, `blueprint`, `halftone`: built, tuned through four critic
rounds, and none reached 4 of 5, so they are not in the code. Commit 2c044f6 holds all six.

```bash
echo '{"material": "chalk", "drawing": "house"}' > s.json
node plates/run.mjs ink --spec s.json --seconds 4 --seed 1 --out out/plates/house
```

## Done when

| Line | Status | Evidence |
|---|---|---|
| One sheet shows all 44 drawings in all 6 materials, mid-stroke, and you have looked at it | Done | `out/plates/ink/sheet-six.png` (2184x11176, 264 cells, made at 1bb33a0, before the last ink and halftone tuning); `sheet.png` is the 88 cells that ship. Both are also in the shared notes folder. Looked at: all four quarters of the six-column sheet (two of them on an earlier build, two on the final one). No frame broken. The shipped sheet: looked at whole, every drawing recognisable and mid-stroke. `out/` is not in git; `python plates/ink/sheet.py` rebuilds the shipped one |
| Six 4-second clips are baked, and `plate.json` shows each cost | Done, with a caveat | `out/plates/ink/<material>/plate.json` for all six at 1bb33a0 (table below). Four of them are of materials now cut, and they predate the last tuning of ink wash and halftone. The two shipped clips were baked again after the cut: `out/plates/ink/final/` |
| The critic scores each material at least 4 of 5, reasons kept; a material that can't is cut | Done for 2 of 6, 4 cut | Scores and reasons below |
| A second bake of the same spec gives the same mp4 | Done | chalk, house, seed 1, baked twice: both sha256 `ee963204fe9e2e5d950c3888d2328469b22d415f6ece9887eeb6d6679ea3fc90` (`out/plates/ink/final/chalk`, `repeat`). One spec only |
| plates/ink/README.md is complete, and a sub-agent got a good clip from it on the first try | Done | A Haiku sub-agent given only the README, asked for a school in pencil set higher on the frame: wrote `{"material": "pencil_hatch", "drawing": "school", "box": [40, 480, 1000]}`, baked at full size in 28 s, first try. `out/plates/ink/cold/poster.png`: I looked at it, a good clip. It didn't need `../README.md` |

Gates: see the end of this file.

## The critic

A new Sonnet sub-agent each round, shown only frames, asked to score "painted, not filtered" from 1 to 5, with no sight of
the code or of earlier rounds.

| Material | Round 1 | Round 2 | Round 3 | Round 4 | Verdict |
|---|---|---|---|---|---|
| `chalk` | 4 | 4 | 4 | | Shipped |
| `pencil_hatch` | 3.5 | 4 | 4 | | Shipped |
| `ink_wash` | 3.5 | 3 to 3.5 | 3.5 | 2.5 | Cut |
| `halftone` | 2.5 | 2 | 3.5 | 3 | Cut |
| `blueprint` | 2 | 3 | 2.5 | | Cut |
| `woodcut` | 2 | 2 | 2.5 | | Cut |

Reasons kept from the last round each material was seen:

- **chalk, 4:** "grainy broken edge", skipping on the board's tooth, dusty ghosting in the board; pressure believable,
  subjects clear. Tell: the fill is a little random and speckled.
- **pencil_hatch, 4:** hatch lines vary in length, angle and pressure, overlapping crosshatch, a wobbly contour. Tell: the
  contour is a little too evenly bright; faint at small size.
- **ink_wash, 2.5:** the wash read as a noise-textured layer with the same bleed edge on every blob, and the lines float
  over it with no ink-on-wet interaction. Round 3 liked the pooled edges and blooms (3.5); round 4, after the pool was
  made smaller and drier, did not.
- **halftone, 3:** worn, broken ink edges are convincing; dots on a regular grid and uniform outlines still read as a
  filter. A halftone is a machine's output, so "made by a hand" is a hard test for it.
- **blueprint, 2.5:** reads as an SVG with a grain overlay; regular hatch, little pressure variation. A ruled drawing
  is exact by nature, which works against this test too.
- **woodcut, 2.5:** the marks are hand-cut (gouge flecks, plank grain), but it is too busy and the subjects merge; the
  hospital and the price tag were barely recognisable.

Two limits of this measure: the same work moved by up to a point between critics, and a critic's eye is not the owner's.
My own look at the frames disagreed with the round 4 score for ink wash: I thought it the most beautiful of the six, and
it is cut because the rule says so, not because I agree (Owner decisions).

## Cost

Baked with other lanes on the same 8 cores, so every figure runs high, and the numbers move a lot with load. No limit
depends on them, so I did not re-measure on an idle machine.

| Clip | ms a frame | Where |
|---|---|---|
| chalk, house | 235 (133 and 519 in other runs) | `final/chalk/plate.json` |
| pencil_hatch, airplane | 248 (153 to 250 in other runs) | `final/pencil_hatch/plate.json` |
| chalk, bus, `scrape` | 312 | `final/chalk-scrape/plate.json` |
| pencil_hatch, factory, `print_through` | 185 | `final/pencil-print/plate.json` |
| flood, 1.5 s | 201 (107 to 191 in other runs) | `final/flood/plate.json` |
| chalk / pencil_hatch at `--scale 0.5` | 101 / 125 | `final/half`, `final/half2` |
| Six at 1bb33a0: woodcut, ink_wash, blueprint, halftone, chalk, pencil_hatch | 165, 214, 272, 258, 519, 250 | `out/plates/ink/<material>/plate.json` |

That is under the 276 of the shader in `plates/README.md`, because a frame only asks which pigment has landed: the marks
are laid once in setup (2 to 5 s at full size). All of it on the i7-7700K; the server isn't measured.

## Flash

`flash.measure` on the two shipped clips, `scrape`, `print_through` and the flood: area 0.0, no problems. The flood fills
the frame once and drains once. It is fully covered from about 0.8 to 0.9 s of 1.5.

## How it works

`bake.py` turns a drawing into ordered strokes through `art.sanitize`: `--d` is the order, `<text>` is dropped, an ACCENT
dot goes to `anchors.json`. The distance field is built in the page from those strokes, with a flood fill that finds what
the lines enclose, and a tone plan lit from the upper left. Each material lays its own marks once, in setup, into four
layers holding pigment and the moment each pixel is touched. A frame is a small shader asking what has landed by `t`. A
reveal only changes that moment. The boil is three real redraws of every mark, shown on twos, on a sheet that never moves.

The critic's most useful finding, in round 1: the outline was the giveaway in every material. Whatever the fill did, a
clean even line said "vector". Every gain after that came from redrawing the line.

## What I didn't do, and why

- **Four of six materials.** Cut, see above.
- **Bleed into the paper.** It was built in the brush for `ink_wash` and went with it: chalk and graphite don't bleed.
  The research's square-root front exists only in 2c044f6. Build step 3's bleed is not in what ships.
- **The flood in a film, and any plate behind real facts.** `engine compose check` on a copy of `compose/24835` in
  `out/` failed with a Windows PermissionError on the folder, and that proof is optional, so I stopped rather than dig.
  The README's `mix-blend-mode: screen` advice is therefore untested. The flood is checked as a clip only.
- **`print_through` is not mirrored.** The research says a reverse-side mirror; a blurred upright picture reads better.
- **Multi-channel SDF, Bézier solver, spatial grid** from the research: not needed, the marks are polylines laid on the CPU.
- **More materials.** Not attempted.
- **`tsc` and `selftest`.** Not run: no Remotion or scene code was touched.
- **Look targets.** Off for this run.

## Bugs found on the way

- The flood's times were `Float32Array`: rounding made the search skip cells, seen as pinholes. Fixed in 74c62c6.
- `tests` importing `bake.py` left `__pycache__` in `plates/ink/`, which `run.mjs` hashes. Fixed in 2d6b486.

## Owner decisions

1. **Keep the cut, or overrule the critic?** All six are at 2c044f6 (`plates/ink/materials.mjs`, `core.mjs` for the
   brush's `rim` and `bleed`). Ink wash is the one I would look at first: `out/plates/ink/ink_wash/` is its clip at
   1bb33a0, and the critics split 3.5 to 2.5. If you overrule, the material goes back in as it is, no rework needed.
2. **A full frame of ink on a dark pack:** the flood covers the frame in the pack's ink for about 0.1 s. It passes the
   flash check. Whether a film may do that is your call.
3. **`news` and the devices:** I propose opening `material-film` and `drawn-reveal` with the plate, but `material-film`
   is `"news": "cond"` and a plate never goes to `news`, so the plate scene stays off that program whatever the device says.

## For the integrating session

- **Goal 1 (`engine plate`):** the spec keys are in `plates/ink/README.md`. A plate needs black mapped to canvas and white
  to ink; `anchors.json` gives `dot` when the drawing has one. `hashOf` reads every file in the kind, so an edit to its
  README changes the hash and re-bakes: consider hashing only what the page loads.
- **Devices of `concepts/devices.json` this kind can draw:** `material-film` (one film in chalk or pencil),
  `drawn-reveal` (add the plate scene beside `draw` and `sign`). `period-pastiche` and `treated-picture` were claimed
  by the earlier draft for woodcut, halftone and paper textures; with those cut they should wait.
- **Merge:** `plates/ink/` and `tests/test_ink_plate.py` are new. `npm ci` in `plates/` is enough to bake.

Proposed for `CLAUDE.md`:

> - **Ink plates** (`plates/ink/`, its README): a drawing painted mark by mark on a plate, in `chalk` or `pencil_hatch`,
>   with `stroke`, `scrape`, `print_through` and `flood` reveals. Marks are laid once in setup; a frame only asks which
>   have landed. A new material must score at least 4 of 5 from a fresh critic on "painted, not filtered", shown frames
>   only, or it isn't shipped; it needs a case in `tests/test_ink_plate.py`. `drawings.json` is built only by `bake.py`.

## Shared files touched

None. New files only: `plates/ink/*`, `tests/test_ink_plate.py`, and `docs/research/ink-brush*.md`. `plates/run.mjs`,
`tt_shorts/`, `brushes/`, `remotion/` and `CLAUDE.md` are untouched.

## Commits

e7d0300 drawings into strokes and the page; 701daad six materials, three reveals, the flood, the sheet; c7a6bd2 two-plate
halftone; 3713238 redrawn lines after round 1; 1bb33a0 block-printed woodcut after round 2; 35b5f76 flood timing;
2c044f6 last ink and halftone pass, **all six here**; 1f21943 the cut; 2bd7236 cost table; 2d6b486 no bytecode in the
plate folder; 74c62c6 the flood fix; then this file.

## Gates

`python -m unittest discover -s tests`, run once on 74c62c6 with `npm ci` done in `remotion/`, `compose/` and `plates/`: 785 tests, OK, 2 skipped, exit 0 (773 before, plus 12 in `tests/test_ink_plate.py`). Only this file, `docs/research/ink-brush.md` and `plates/ink/README.md` changed after it. `tsc` and `selftest` not run: no Remotion or scene code touched.
