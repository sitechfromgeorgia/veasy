# Plates: Matter (Physical Quantities)

A plate kind that gives numbers physical mass: discrete 3D unit blocks crash, settle, split, or stack on screen, with mathematical proof that $\text{count} \times \text{unit} = \text{fact}$ exactly.

```bash
cd plates && npm ci
node plates/matter/bake.mjs --spec spec.json --seconds 6 --seed 1 --out out/plates/budget
```

`bake.mjs` verifies the fact, solves once into `cache/sim.bin` (git-ignored), then runs `plates/run.mjs matter`. It bakes a 1080×1920 clip (`plate.mp4`), a center poster (`poster.png`), verification metadata (`plate.json`), and 2D group tracking coordinates (`anchors.json`) for DOM typography.

---

## Spec Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `form` | string | `"pile"` | The physical choreography: `"pile"`, `"split"`, `"too-tall"`, `"pour"`, `"resort"`, `"versus"`. |
| `fact` | number \| object | *required* | The factual quantity (e.g. `2400000000`) or reference `{"ref": "stories/24835.json", "key": "scene-1-value"}`. |
| `unit` | number | *required* | The discrete value of one single block. Must divide `fact` exactly with zero remainder. |
| `unit_label` | string | `""` | Optional display label for the unit (e.g. `"₾1M"`). |
| `groups` | array | `[]` | Optional partition of constituent shares: `[{"name": "health", "fact": 600000000}, ...]`. Sum of group facts must equal `fact`. |
| `camera` | string | `"auto"` | Camera movement: `"auto"`, `"reveal"`, `"climb"`, `"orbit"`, `"overview"`. |
| `block_size` | number | `0.42` | Dimension of individual unit cube in 3D scene units. |

---

## What the Kind Refuses

1. **Non-dividing units:**
   If `fact % unit !== 0`, the bake aborts immediately with `UnitMismatchError: unit X does not divide fact Y exactly (remainder Z)`. No rounding, no ceil/floor, no phantom blocks.
2. **Block counts over 3,000:**
   If `fact / unit > 3000`, the bake aborts with `BlockCountExceededError: block count N exceeds maximum capacity of 3000 blocks; choose a larger unit`.
3. **Invalid or mismatched groups:**
   If `groups` are specified, every group fact must be divisible by `unit`, and $\sum \text{group.fact}$ must equal `fact` exactly.
4. **Forbidden categories:**
   Under `CLAUDE.md § N` and `plates/README.md`, plates are strictly refused for `news`, crime, incidents, or deaths. They operate exclusively in `explainer`, `story`, `blog`, and data pieces.
5. **Real place assertions:**
   A plate is an abstract physical model; it never claims to be a photograph or simulation of a real physical building or landscape.

---

## Spec keys added in the build

| Key | Default | Meaning |
|---|---|---|
| `scale` | 1 | Lifts a story's decimals to whole units (`8.0` x 100 = 800). The product must be a whole number or the bake is refused, never rounded. Applies to `fact` and every group fact. |
| `exposure` | 0.4 | Light level of the grey master. A dim master is what `flash.py` wants: at 0.5 a 800-block pile in free fall measured 0.198 of the screen, at full light 0.33 (limit 0.25). `pour` uses 0.3. |
| `gravity` | 9.81 | Passed to the solver. |

Fact refs: `{"ref": "stories/x.json", "key": "scenes[3].items.0.value"}` (scene index and dot paths both work).

---

## Cost Table

Measured 2026-11-07 on a machine shared with four other sessions, so every time runs high. Half scale
(540x960), 6 s, 800 blocks, one bake each, `ms_per_frame` as `plate.json` records it, wall time includes the solve,
browser start and ffmpeg:

| Form | ms / frame | Wall time | Solve |
|---|---|---|---|
| `pile` | 98 | 22 s | 0.3 s |
| `too-tall` | 154 | 32 s | 0.02 s |
| `versus` | 177 | 44 s | 1.4 s |
| `pour` | 203 | 54 s | 0.5 s |
| `split` | 230 | 48 s | 0.03 s |
| `resort` | 241 | 48 s | 0.1 s |

Full scale was not measured. The earlier table in this file was written before any bake and is removed.

## Known limits

- `split` slides every group after the first; with three groups it reads as stepped terraces more than one share leaving.
- `pour` pours into a heap, not a container. `resort` is framed close and some blocks interpenetrate while they glide.
- A story's decimal total (`budget.total`) is not a fact id in `compose`'s `facts.json`, so a film cannot bind it as text.
- The compose probe treats any `<video>` as an unknown picture (worst case white): text over a plate needs solid bands or chips.
