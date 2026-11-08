# Plates

A plate is a short grey clip baked once, before any film, and played behind a scene as a local file. It gives a film
frames neither engine draws well (real 3D, shaders, simulated matter) without changing how films render: both engines
read an mp4, and the text stays in the DOM.

```bash
cd plates && npm ci
node plates/run.mjs example --seconds 4 --seed 7 --out out/plates/example
```

From an agent or a script, the front door is one line, which bakes (or answers from the cache), tones the clip for every
pack and theme, and says where everything is (skill `veasy:plates`, tool `veasy_plate`):

```bash
python -m tt_shorts.engine plate example --seconds 6 --seed 3     # or: python -m tt_shorts.plates example ...
python -m tt_shorts.engine plate list | check
```

`node plates/run.mjs <kind> ... --hash` prints the plate's 16-hex content hash and exits (what the cache key is). The hash is
a function of the kind's own files, the spec's contents (not its path), the seed, the seconds and the scale. A kind's
`cache/` is left out: it is what a bake makes from those (matter's solved `sim.bin`), not what the plate is made of.

A kind that must make files before its page can run has its own `plates/<kind>/bake.mjs` (matter: verify the fact, solve
`cache/sim.bin`, then call `run.mjs`). `engine plate <kind>` bakes through it, and asks it for the hash (`bake.mjs ...
--hash`, on the spec as the bake resolves it), so the hash before a bake is the plate's hash after it. Such a kind needs
`--spec`; `run.mjs` called directly on it without its `cache/` says so instead of failing in the page.

The result of a bake is `plate.mp4`, `poster.png` (the middle frame), `plate.json` (what it is a function of, and its cost) and,
if the page exports them, `anchors.json`.

## The contract of a kind

A kind is a folder `plates/<kind>/` with an `index.html`. `run.mjs` serves `plates/`, opens the page at 1080x1920 (times
`--scale`) on software GL, and calls:

```js
window.setup = async (spec, ctx) => {};   // ctx: {width, height, fps, seed, seconds}; spec: the --spec JSON
window.step = (t) => {};                  // draw the frame at t seconds
window.anchors = (t) => ({dot: [x, y]});  // optional: page pixels of what the film's DOM must follow
```

Both engines draw the clip at **page coordinates**: a plate's pixel (x, y) shows at the film's (x, y), so keep the subject
in the scene band (y 248-1380) and write `anchors` in those pixels; the card of a plate scene (top, mid or low) is placed
by code so it never sits on the dot (`plates.free_layouts`). A plate that is longer than its scene is cut; a shorter one loops.

A plate:

- **Is tone only.** Draw in grey on black. `run.mjs` makes every frame grey whatever the page draws; the engine maps
  black to the pack's canvas and white to its ink, so one master serves every pack and no palette can leak.
- **Has no text, no accent, no logo.** Words and the accent dot stay in the DOM, placed from `anchors.json`.
- **Is deterministic.** `step` is a pure function of `t`, `spec` and `seed`. Use `lib/seeded.mjs`, never `Math.random`
  or a clock. A simulation runs once at bake time, into a file the page reads.
- **Reads local files only.** `run.mjs` fails a plate that asks for anything else.
- **Is bounded.** Say what a frame costs (`ms_per_frame` in `plate.json`) and keep to the limits below.

## What it costs

Measured 2026-11-06 with three r184 on SwiftShader, 1080x1920, i7-7700K, ms a frame: relief 187, unlit city 327,
diorama 370, ink shader 276 (half scale 113), 12 000-block pile 674 (half scale 297). A DOM film is 74. Four workers
gained almost nothing. So a plate is baked once, cached and reused, never per video on the queue. The server's speed
is not measured.

A plate is never used for `news`, crime, incidents or deaths, and never as a picture of a real place, which would assert
what it can't prove.
