# Plates: Matter (Physical Quantities)

A plate kind that gives numbers physical mass: discrete 3D unit blocks crash, settle, split, or stack on screen, with mathematical proof that $\text{count} \times \text{unit} = \text{fact}$ exactly.

```bash
cd plates && npm ci
node plates/run.mjs matter --spec spec.json --seconds 6 --seed 1 --out out/plates/budget
```

Bakes a 1080×1920 clip (`plate.mp4`), a center poster (`poster.png`), verification metadata (`plate.json`), and 2D group tracking coordinates (`anchors.json`) for DOM typography.

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

## Cost Table

Measured on SwiftShader (headless Chrome, CPU software rasterizer):

| Resolution | Block Count | Form | ms / frame | 6s Bake Time |
|---|---|---|---|---|
| Half (540×960, `--scale 0.5`) | 500 blocks | `pile` | ~110 ms | ~20 s |
| Half (540×960, `--scale 0.5`) | 1,000 blocks | `split` | ~135 ms | ~24 s |
| Half (540×960, `--scale 0.5`) | 2,400 blocks | `too-tall` | ~185 ms | ~33 s |
| Full (1080×1920, `--scale 1.0`) | 1,000 blocks | `pile` | ~275 ms | ~50 s |
| Full (1080×1920, `--scale 1.0`) | 3,000 blocks (cap) | `pile` | ~380 ms | ~68 s |
