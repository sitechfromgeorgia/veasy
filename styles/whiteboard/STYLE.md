# Whiteboard Explainer (`whiteboard`)

> Dry-erase explainer drawn live stroke by stroke with floating markers and animated rewinds, free of distracting artificial hand cutouts.

## 1. At-a-Glance Signature
- High-contrast dry-erase marker linework on a subtle off-white enamel ground with faint reflection falloff.
- Progressive stroke order: lines, diagrams, arrows, and Georgian lettering are drawn path-by-path.
- Floating pen nib or marker tip guiding the path (strictly **no fake photorealistic human hand cutouts**).
- Dry-erase eraser wiping mistakes with real smudge falloff.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Board surface: 1080×1920 px.
- Camera follows the drawing point vertically down the board ($y = 300 \to 1300$).
- Safe scene content boundary: $y \le 1380$; captions in lower band $y \in [1380, 1552]$.
- Side boundaries: drawings stay within $x \in [80, 940]$ to avoid overlap with vertical mobile feed controls.

## 3. Georgian Mkhedruli Typography
- Continuous single-line stroke font customized for Georgian Mkhedruli characters (33 letters with distinct looped curves and ascenders/descenders).
- Organic stroke variation: slight pressure thickness differences matching a chisel-tip or bullet-tip dry-erase marker.
- Handwriting size: large legible headers (60–80 px) and medium body notes (36–44 px).

## 4. Motion & Animation Rules
- Stroke speed: drawing paths animate at a constant, natural stroke velocity ($1200\text{ px/s}$).
- Smooth camera panning: virtual camera pans downward in continuous sync with active drawing activity.
- Transitions: squeegee dry-erase wipe or fast pan to a clean whiteboard tile.

## 5. Sound Craft
- Friendly, engaging acoustic guitar or melodic rhythmic loop mixed at constant level.
- Constant volume without ducking.
- SFX: subtle dry marker squeak or soft friction whoosh (`whoosh`) during drawing, soft tap (`click`) on pen cap or board strike.
