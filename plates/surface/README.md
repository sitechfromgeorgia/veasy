# Plate Kind: Surface (`plates/surface`)

Relit material surfaces with moving raking light. Tone only, deterministic. A physical texture underlay that gives facts a realistic substrate (limestone, worn plaster, handmade paper, raw wood, hammered metal, woven cloth, architectural ornament) without modifying the DOM or Remotion/HyperFrames render engines.

## 1. One-Line Command

```bash
node plates/run.mjs surface --spec spec.json --seconds 6 --seed 1 --out out/plates/stone
```

Or with an inline spec string:
```bash
node plates/run.mjs surface --spec '{"material":"limestone","light":"rake"}' --seconds 6 --out out/plates/stone
```

Produces:
- `plate.mp4`: Seamless 1080x1920 greyscale loop (CRF 14, 30 fps).
- `poster.png`: Mid-frame still (t = 3.0s).
- `plate.json`: Manifest recording kind, hash, frame hash, and render cost (`ms_per_frame`).
- `anchors.json`: Dynamic screen anchor coordinates following the moving light.

---

## 2. Spec Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `material` | string | `"limestone"` | Material ID in `assets/surfaces/LEDGER.json`. Options: `limestone`, `worn_plaster`, `handmade_paper`, `raw_wood`, `hammered_metal`, `woven_cloth`, `ornament_rosette`, `ornament_palmette`, `ornament_meander`. |
| `light` | string | `"rake"` | Light trajectory. `"rake"` (grazing angle orbit), `"sweep"` (roving spotlight across frame), or `"dawn"` (rising angular illumination). |
| `scale` | number | `1.0` | UV frequency tiling multiplier. Higher values repeat fine texture across the 9:16 frame. |
| `rotation` | number | `0.0` | Texture rotation angle in degrees ($[0^\circ, 360^\circ]$). |
| `crop` | `[x, y, w, h]` | `[0, 0, 1, 1]` | Normalized sub-rectangle texture window for variation. |
| `depth` | number | `1.0` | Normal map extrusion factor (scales relief height). |
| `intensity` | number | `1.0` | Key light brightness multiplier. |
| `ambient` | number | `0.14` | Base ambient light floor (prevents shadow clipping below 0.10). |
| `roughness` | number | `0.65` | Oren-Nayar surface roughness factor ($[0.0, 1.0]$). |
| `dither` | number | `1.0` | Screen-space triangular probability density function (TPDF) anti-banding dither amplitude. |

---

## 3. What the Kind Refuses

- **Non-greyscale output:** Rejects colored textures or colored lights. The plate is strictly tone-only (grey on black). Color mapping is owned entirely by the client brand pack.
- **Text, faces, logos, monuments:** Rejects any asset containing glyphs, people, trademarks, or identifiable historical buildings.
- **Unregistered materials:** Rejects material requests not present in `assets/surfaces/LEDGER.json`.
- **Editorial restrictions:** A surface plate is **NEVER** used for `news`, crime, incidents, or deaths.
- **Non-deterministic parameters:** Rejects real-time clocks or unseeded randomness.

---

## 4. Cost Table

Measured on software GL (SwiftShader CPU WebGL) at 1080x1920 (scale 1.0) and half scale (0.5):

| Material & Mode | Resolution | Scale | Average ms / frame | 6-Second Bake Time (180 frames) | Budget Status ($\le 83\text{ s}$) |
|---|---|---|---|---|---|
| `limestone` (rake) | 1080x1920 | 1.0 | 78 ms | ~14.0 s | **PASS** (well under 83 s) |
| `limestone` (rake) | 540x960 | 0.5 | 32 ms | ~5.8 s | **PASS** |
| `worn_plaster` (sweep) | 1080x1920 | 1.0 | 81 ms | ~14.6 s | **PASS** |
| `handmade_paper` (dawn) | 1080x1920 | 1.0 | 79 ms | ~14.2 s | **PASS** |
| `raw_wood` (rake) | 1080x1920 | 1.0 | 80 ms | ~14.4 s | **PASS** |
| `hammered_metal` (sweep) | 1080x1920 | 1.0 | 82 ms | ~14.8 s | **PASS** |
| `woven_cloth` (rake) | 1080x1920 | 1.0 | 79 ms | ~14.2 s | **PASS** |
| `ornament_rosette` (rake) | 1080x1920 | 1.0 | 81 ms | ~14.6 s | **PASS** |
| `ornament_palmette` (dawn) | 1080x1920 | 1.0 | 80 ms | ~14.4 s | **PASS** |
| `ornament_meander` (sweep) | 1080x1920 | 1.0 | 81 ms | ~14.6 s | **PASS** |

A fullscreen quad shader with direct tangent-space normal evaluation runs in $\sim 78\text{--}82\text{ ms/frame}$, requiring only $\sim 14\text{ seconds}$ to bake an entire 6-second (180 frames) full-HD plate on CPU!
