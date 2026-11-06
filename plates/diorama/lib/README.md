# Paper Stage Part Kit (`plates/diorama/lib/kit.mjs`)

The modular paper architecture library for the Veasy Paper Stage diorama engine.

## Core Design Principles

1. **Paper Aesthetics & Micro-Bevels**:
   - Cardstock sheet thickness: `0.02 - 0.05` units (default `0.035`).
   - Micro-bevel edges: `bevelThickness: 0.006`, `bevelSize: 0.005`, `bevelSegments: 1`. Crisp 45-degree chamfers catch directional light, reading immediately as laser-cut or knife-creased cardstock.
   - Staggered Z-planes: Layer depth offsets (`zStep: 0.06 - 0.12`) model Victorian toy theatre wings, prosceniums, and pop-up books.

2. **Tone-Only Shading on Black Canvas**:
   - Rendered in greyscale on `#000000` canvas; mapped by the Veasy pack engine to canvas (black) and ink (white).
   - Zero shiny specular highlights: all components use calibrated `THREE.MeshLambertMaterial` (`flatShading: true`).

3. **Shadowless Depth (370ms Budget Compliant)**:
   - Cast shadows are completely disabled (`castShadow = false`, `receiveShadow = false`), avoiding the 903ms/frame penalty of shadow maps.
   - Depth is sculpted via:
     - **Key Directional Light**: `[-5.0, 8.0, 4.0]`, intensity `2.0` (high off-axis, sculpts bevel facets).
     - **Hemisphere Fill Light**: `(0xe8e8e8, 0x222222)`, intensity `1.15` (diffuse ceiling bounce with dark floor absorption).
     - **Rim Kicker Light**: `[4.5, 3.0, -6.0]`, intensity `0.9` (opposing backlight catching paper card silhouettes).
     - **Linear Depth Fog**: `THREE.Fog(0x000000, 7.0, 24.0)` (distances gracefully fade into pure stage black).

---

## Calibrated Tone Palette (`TONES`)

| Constant | Hex | Luminance | Purpose |
|---|---|---|---|
| `TONES.WHITE` | `0xf6f6f6` | 96% | Crisp card edge strips, white trim, highlights, keystones |
| `TONES.CARD` | `0xe2e2e2` | 88% | Primary cardstock wall faces, colonnade shafts |
| `TONES.CREAM` | `0xd0d0d0` | 81% | Secondary architectural trim, copings, entablatures |
| `TONES.MUTED` | `0xa2a2a2` | 63% | Roof planes, bridge roadbed, recessed panels |
| `TONES.SHADOW` | `0x6e6e6e` | 43% | Under-arch soffits, plinth flanks, sill undersides |
| `TONES.DARK` | `0x383838` | 22% | Tree trunks, dark reveals, stage ground floor |
| `TONES.VOID` | `0x121212` | 7% | Window aperture void backings, deep recesses |

---

## Component API Reference

### 1. `createPunchedWall(options)`
Creates a modular paper wall with punched window or door apertures.
- `width` (number, default: `4.0`): Total wall span.
- `height` (number, default: `3.0`): Total wall height.
- `thickness` (number, default: `0.035`): Cardstock thickness.
- `apertures` (Array<Object>): Array of aperture objects:
  `{ x, y, width, height, type: "roman"|"pointed"|"horseshoe"|"rect"|"round" }`
- `tone` (hex, default: `TONES.CARD`): Wall face tone.
- `backing` (boolean, default: `true`): Adds a recessed interior void card (`TONES.VOID`) at $Z = -0.09$ to simulate depth.
- `coping` (boolean, default: `true`): Adds a top projecting cap card catching key light.
- `baseboard` (boolean, default: `false`): Optional plinth trim along base.

### 2. `createArchway(options)`
Standalone architectural portal wall.
- `width` (number, default: `2.4`): Outer width.
- `height` (number, default: `3.2`): Outer height.
- `archWidth` (number, default: `1.2`): Clear opening width.
- `archHeight` (number, default: `2.2`): Clear opening height.
- `archType` ("roman"|"pointed"|"horseshoe", default: `"roman"`): Arch curvature geometry.
- `keystone` (boolean, default: `true`): Raised card keystone at the apex.
- `imposts` (boolean, default: `true`): Projecting springline molding blocks.

### 3. `createRecedingPortal(options)`
Concentric Romanesque or Gothic receding portal.
- `layers` (number, default: `3`): Number of concentric stepped arch cards.
- `stepZ` (number, default: `0.072`): Setback depth per card layer.
- `archType` ("roman"|"pointed", default: `"pointed"`).
- Automatically steps down opening dimensions and applies alternating tone gradations.

### 4. `createPlinth(options)`
Multi-tiered stage plinth and display pedestal.
- `width`, `depth`, `height`: Overall bounding dimensions.
- `tiers` (number, default: `2`): Stepped terraces.
- `setback` (number, default: `0.15`): Lateral terrace setback per tier.

### 5. `createStairs(options)`
Papercraft staircases.
- `steps` (number, default: `6`): Riser count.
- `width` (number, default: `1.6`): Lateral span.
- `stepHeight` (number, default: `0.1`), `stepDepth` (number, default: `0.22`).
- `style` ("stepped"|"accordion", default: `"stepped"`):
  - `"stepped"`: Solid stepped block with bevelled tread highlights and lateral stringer cheeks.
  - `"accordion"`: Continuous folded zig-zag card sheet.

### 6. `createFramedWindow(options)`
Detailed window module with mullions and sill.
- `width`, `height`: Window aperture dimensions.
- `archType` ("rect"|"roman"|"pointed"|"horseshoe", default: `"rect"`).
- `rows` (number, default: `3`), `cols` (number, default: `2`): Mullion grid divisions.
- `frameWidth` (number, default: `0.06`), `mullionWidth` (number, default: `0.025`).
- `sillDepth` (number, default: `0.08`): Protruding bevelled sill catching top light.
- `backingTone` (hex, default: `TONES.VOID`).

### 7. `createPaperTree(options)`
Papercraft foliage trees:
- `style` ("disc"|"cutout", default: `"disc"`):
  - `"disc"`: Tapered central trunk with X-interlocking foot and 3-6 horizontal card discs with wavy deckled contours.
  - `"cutout"`: Staggered multi-layer silhouette cards.
- `type` ("cloud"|"cypress"|"pine", default: `"cloud"` for cutout).
- `height` (number, default: `2.2`), `radius` (number, default: `0.7`).
- `tiers` (number, default: `4`).

### 8. `createRollingHills(options)`
Topographic layered contour silhouette planes for backgrounds.
- `width` (number, default: `14.0`): Horizon width.
- `height` (number, default: `2.8`): Maximum hill crest.
- `minHeight` (number, default: `0.6`): Valley floor height.
- `layers` (number, default: `4`): Depth contour planes.
- `zSpacing` (number, default: `0.8`): Setback between layers.
- `seed` (number, default: `42`): Seed for deterministic undulating curves.

### 9. `createColonnade(options)`
Monumental colonnade / arcade.
- `count` (number, default: `6`): Column count.
- `spacing` (number, default: `0.8`): Center-to-center spacing.
- `height` (number, default: `2.4`): Column height.
- `arcade` (boolean, default: `true`): Spans arch panels between column capitals.
- `archType` ("roman"|"pointed"|"horseshoe", default: `"roman"`).
- Includes stepped stylobate base and upper entablature / architrave beam.

### 10. `createPaperRoof(options)`
Modular folded card roofs:
- `style` ("gable"|"mansard"|"accordion"|"dome", default: `"gable"`):
  - `"gable"`: Pitched roof with raked bargeboard fascia, ridge cap strip, and pediments.
  - `"mansard"`: Dual-pitch French profile.
  - `"accordion"`: Origami folded plate roof.
  - `"dome"`: Stepped concentric paper disc cupola.
- `width`, `depth`, `height`.

### 11. `createBridgeDeck(options)`
Segmental arch river bridge.
- `length` (number, default: `6.0`), `width` (number, default: `1.4`), `height` (number, default: `1.4`).
- `archCount` (1, 2, or 3 arches, default: `2`).
- `archType` ("roman"|"segmental"|"pointed", default: `"segmental"`).
- `parapetHeight` (number, default: `0.28`): Guardrails with punched decorative balustrade slots.
- `camber` (number, default: `0.12`): Gentle parabolic crown curvature along deck.
- Pier cutwaters (triangular paper wedge breakwaters).

### 12. `setupPaperStage(scene, options)`
Configures the 3-point lighting rig and linear depth fog.
- Creates `THREE.HemisphereLight`, `keyLight`, `rimLight`, and `THREE.Fog(0x000000, 7.0, 24.0)`.
- All `castShadow` flags set to `false`.
