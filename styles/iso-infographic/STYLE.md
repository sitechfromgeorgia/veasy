# Isometric Infographic (`iso-infographic`)

> True 30-degree isometric system diorama with layered three-tone blocks, cutaway strata, and modular isometric icon units.

## 1. At-a-Glance Signature
- Strict 30° axonometric projection with mathematical consistency across all objects.
- Three-tone lighting: top facet (lightest), left facet (mid-tone), right facet (shadowed).
- Floating geological or architectural strata plinth with clean cutaway edge layers.
- Isometric Isotype icon arrays (servers, buildings, shipping containers, solar cells, or people).

## 2. Vertical (1080×1920) Geometry & Safe Zones
- High-angle camera view optimized for vertical 9:16 aspect ratio: strata layers stack vertically in depth.
- Isometric diorama viewport: $x \in [100, 940]$, $y \in [300, 1340]$.
- Floating callout pins: leader lines extend at 30°/90°/150° angles from objects to readable 2D text cards.
- Safe zone: scene text ends at $y \le 1380$; lower-third captions sit at $y \in [1380, 1552]$.
- Right margin clear zone: $x \le 940$ below $y = 1100$.

## 3. Georgian Mkhedruli Typography
- Explanatory callout labels sit on non-rotated 2D billboard cards in `FiraGO 500`.
- Metric numbers use bold monospace or tabular figures (`IBM Plex Mono 600`).
- Directional arrow labels follow the 30° isometric plane axes.

## 4. Motion & Animation Rules
- Isometric blocks rise or fall into the diorama with staggered vertical drops (4-frame offsets) and subtle spring damping.
- Strata plinths slide open to reveal internal underground or backend layers.
- Rotations strictly maintain 30° projection angles.

## 5. Sound Craft
- Modern, layered electronic or acoustic modular loop.
- Constant volume without ducking or pumping.
- SFX: solid block landing thud (`thud`), modular unit pop (`pop`), leader card click (`click`).
