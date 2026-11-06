# The Paper Stage (Diorama Engine)

The **Paper Stage** (`plates/diorama/`) is Veasy's theatrical cut-paper diorama plate engine. It translates 2D SVG motifs and architectural cutouts into tactile, multi-layered 3D paper dioramas rendered on software GL via Three.js.

```bash
# Bake a diorama plate:
node plates/run.mjs diorama --spec plates/diorama/sets/museum-hall.json --seconds 6 --seed 1 --out out/plates/museum-hall
```

## Core Design Principles

1. **Generic Archetypes**: A diorama set NEVER depicts or claims to represent a real-world building, city, or proprietary location. Sets are archetypal physical theatre stages (Museum Hall, Layered Street, Bazaar Market, Lecture Classroom, Stone Arch River Crossing).
2. **Tone Only**: Rendered strictly in shades of paper white (`#ffffff` / `#f5f5f0`), light card (`#dcdcd7`), mid-tone kraft grey (`#8a8a86`), slate/charcoal (`#383838`), and deep ink black (`#050505`). No colors, logos, or typography can leak into the baked plate; DOM overlays bind brand palette at render time.
3. **Physical Pop-Up Cutout Physics**: All geometry behaves like die-cut, folded cardstock sheets with laminated edges (`sheets`: 1–4), bevels, slotted tabs, and fold brackets.
4. **Cinematic Parallax Layering**: Every scene is partitioned into three discrete depth tiers (`foreground`, `midground`, `background`) along the Z-axis, creating high-relief stereoscopic parallax during camera movement.
5. **DOM Anchor Telemetry**: Every set exports precise 3D anchor points (`dot`, `headline_label`, `stat_callout`, `vanishing_point`) that project to 2D viewport coordinates for Remotion and HyperFrames DOM element attachment.

---

## The 5 Standard Sets (`plates/diorama/sets/`)

| Set ID | Name | Camera Move | Standee Motifs | Key Architectural Features |
| :--- | :--- | :--- | :--- | :--- |
| `museum-hall.json` | The Grand Museum Colonnade Hall | `push-through` | `wine-qvevri`, `court`, `money`, `graduation` | Monumental fluted columns, vaulted groin arches, clerestory grilles, multi-tier exhibit plinths. |
| `street.json` | The Layered Urban Streetscape | `reveal-behind` | `bus`, `car`, `phone`, `electric-charger` | Townhouse facades, accordion awnings, cobblestone pavement, Victorian streetlamp, tree canopy. |
| `market.json` | The Old Quarter Bazaar | `push-through` | `supermarket-cart`, `price-tag`, `wheat-harvest`, `wine-qvevri`, `tap` | Timber canopy stalls, sloped textile awnings, crate pyramids, banded barrels, layered stone gate arches. |
| `classroom.json` | The Tiered Academy Lecture Hall | `crane` | `graduation`, `laptop-code`, `database-server`, `school` | Semicircular tiered desks, scholar's lectern, sliding slate chalkboard, library book bays, arched side windows. |
| `river-bridge.json` | The Stone Arch River Crossing | `wipe-cut` | `bridge`, `cargo-ship`, `drone-flight`, `forest-nature` | 3-span stone arch bridge with cutwaters, terraced contour riverbed, masonry steps, willow tree, 4-tier hills. |

---

## Spec Format & Schema

Sets are declarative JSON specifications adhering to `plates/diorama/sets/schema.json`.

### Top-Level Structure
```json
{
  "$schema": "./schema.json",
  "id": "museum-hall",
  "name": "The Grand Museum Colonnade Hall",
  "description": "...",
  "duration": 6.0,
  "tone": "greys-blacks-paper-whites",
  "environment": { "background_color": "...", "fog": { ... }, "lighting": { ... } },
  "camera": { "move": "push-through", "duration": 6.0, "easing": "...", "path": { "start": { ... }, "end": { ... } } },
  "depth_layers": { "foreground": { ... }, "midground": { ... }, "background": { ... } },
  "anchors": [ { "id": "dot", "position": [x, y, z], "description": "..." } ],
  "standees": [ { "id": "...", "motif": "...", "drawing_path": "...", "position": [x, y, z], "base_bracket": { ... } } ],
  "components": [ { "id": "...", "type": "...", "layer": "...", "position": [x, y, z], "paper_properties": { ... }, "geometry_params": { ... } } ]
}
```

### Depth Tier Standards
- **Foreground ($z \in [2.5, 6.0]$)**: Framing prosceniums, streetlamps, archways, and foliage that wipe past the lens during moves to emphasize spatial depth and execute camera cuts.
- **Midground ($z \in [-2.0, 2.5]$)**: The theatrical stage plane containing main structural platforms, plinths, desks, stalls, bridges, and standing paper figures (`standees`).
- **Background ($z \in [-15.0, -2.0]$)**: Wall flats, clerestory windows, chalkboard partitions, and contour hill ridges receding into atmospheric paper fog.
