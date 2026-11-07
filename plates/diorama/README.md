# The paper stage

A set is a tunnel book filmed in one take: parallel cut sheets a short way apart, seen on a long lens, lit by one lamp
whose shadow is baked once. The camera moves, nothing else does. It gives a film one place for its steps, in place of a
row of cards.

```bash
node plates/run.mjs diorama --spec plates/diorama/sets/market.json --seconds 6 --seed 1 --scale 0.75 --out out/plates/market
```

You get `plate.mp4`, `poster.png`, `plate.json` and `anchors.json`. To look before you bake (three frames, seconds):

```bash
node plates/diorama/tools/stills.mjs plates/diorama/sets/market.json --at 0.1,0.5,0.95 --scale 0.5 --out out/stills
```

## The sets

| Set | A stranger names it by | Move |
|---|---|---|
| `museum-hall` | arches, columns, framed pictures, a jar and two busts on pedestals, a rope | `push-through`, through two sheets |
| `street` | house fronts, a road with a crossing, lamps, a bus, a car | `reveal-behind`, out from behind a lamp post |
| `market` | striped stalls, heaped fruit, a hanging scale, bunting, shoppers | `dolly` |
| `classroom` | a blackboard of chalk shapes, a clock, a globe, rows of desks | `crane`, down to eye level |
| `river-bridge` | a stone bridge, cut water, hills, a low sun, a paper boat | `wipe-pass` |

## Spec keys

| Key | What it does |
|---|---|
| `id`, `about` | the file's name, one line on what it shows |
| `move` | `dolly`, `crane`, `push-through`, `reveal-behind`, `wipe-pass`, or `spline` with `waypoints` |
| `easing` | a name in `EASING_PRESETS` (`lib/camera.mjs`): `smoothstep`, `smootherstep`, `linear`, `cinematic` |
| `camera.vFov` | degrees, 30 for the long lens. Wider starts to read as a modelled room |
| `fromEye`, `toEye`, `fromTarget`, `toTarget` | `dolly` and `push-through`: the run |
| `startY`, `endY`, `startPitch`, `endPitch`, `baseZ`, `targetY` | `crane` |
| `occluder`, `orbitRadius`, `startAngleDeg`, `sweepAngleDeg`, `subject` | `reveal-behind` |
| `travelX`, `baseZ`, `baseY`, `nearDip`, `targetY` | `wipe-pass`, with a `wipe` part near the lens |
| `stage.key`, `aim`, `angle`, `power`, `fill`, `pool`, `soft`, `map` | the one lamp: where, how wide, how strong, the ambient, the pool's soft edge, shadow softness and map size |
| `stage.fog`, `fogTone` | `[near, far]` and the tone it falls to |
| `anchors` | `{name: [x, y, z]}`: the film's DOM follows these in `anchors.json`; `dot` is always there |
| `antialias` | `false` to save a little on a slow machine |
| `parts` | the list below, back to front, each with `part` and `at: [x, y, z]` |

**Parts.** Shapes: `sheet`, `glow`, `window-set`, `ground-row`, `column`, `painting`, `amphora`, `bust`, `pedestal`, `rope`,
`standee` (`drawing`: any of the 44 in `assets/drawings`). Places: `house`, `lamp`, `tree`, `traffic-light`, `road-row`,
`sky`, `stall`, `bunting`, `figure`, `blackboard`, `clock`, `desk-row`, `teacher-desk`, `bookcase`, `pendant`, `plank-floor`,
`hill`, `bridge`, `water-row`, `bank`, `paper-boat`, `wipe`.

A new set is a new JSON file; a new thing in one is one function in `lib/parts.mjs` or `lib/props.mjs`. `tests`:
`node plates/diorama/test_sets.mjs`, `test_camera.mjs`, `test_extruder.mjs`. When `assets/drawings` changes, run
`node plates/diorama/tools/bundle_drawings.mjs`: `run.mjs` serves `plates/` only, so a page reads a copy.

## What keeps it paper

Seven rounds with a critic taught these, and modelling a room undoes all of them (`docs/research/paper-stage.md` §5):

- **No room.** No floor plane, no solids, no perspective walls. Ground rows hide each other's feet. A jar is a contour cut.
- **A long lens** (30°). Parallax between sheets does the depth.
- **Every card is hand-cut:** a wavering edge, a slow warp, a small spin, a pale cut edge that takes the light on one side.
- **Every sheet has its own tooth,** and it shows where the light rakes, far less in the shade.
- **The lamp stands above the open top,** so each sheet is lit and shadows fall sheet to sheet. Keep sheets low enough
  for it, and keep front sheets dark: value separates the layers.

## What it costs

A frame is one draw call and a small tone shader: one grain fetch and four shadow fetches. The shadow map is rendered once
at setup, which is why a cast shadow is affordable here (redrawn every frame, it cost 903 ms). Three's own Lambert, spot and
PCF chunks cost 820 ms a frame on the same set. Bake times are in `docs/research/paper-stage-result.md`.

## What it refuses

A plate is grey, holds no text and no accent, and never goes to `news`, crime, incidents or deaths. A set is generic: it
never claims to be a real place, so no landmark, no skyline of a named city, no flag. No word or digit anywhere, chalk
included: `test_sets.mjs` fails a set that names a real place or carries a text key. A missing `part` or `drawing` fails the
bake with its name. It does not draw people's faces: `figure` is a silhouette from behind.
