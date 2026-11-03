# Engineering Briefing Board (`briefing-board`)

> Enamel briefing whiteboard featuring photo cutouts, dimensional callout lines, magnetic pins, and authoritative stamped verdict marks.

## 1. At-a-Glance Signature
- Matte enamel whiteboard surface with subtle vignette and directional lighting falloff.
- Cutout documentary images and diagrams affixed with round magnetic pins.
- Technical dimension lines with open arrowheads, measurement callouts, and leader tags.
- Stamped status verdicts (e.g. „დადასტურებული“, „აქტიური“, „შემოწმებული“) applied at slight optical angles.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Board workspace: $x \in [72, 1008]$, $y \in [248, 1380]$.
- Pinned cards and cutouts: sized between 400×300 and 700×500 px, positioned hierarchically down the vertical axis.
- Magnets: 24 px discs placed at card top-left or corners.
- Captions remain strictly in lower third: $y \in [1380, 1552]$.
- Side margin buffer: $x \le 940$ below $y = 1100$.

## 3. Georgian Mkhedruli Typography
- Technical dimension labels in `FiraGO 500` or `IBM Plex Mono 500`.
- Stamped verdict marks use bold condensed Georgian lettering with a textured border frame.
- Proper Georgian unit abbreviations: „მ“ (m), „სმ“ (cm), „კგ“ (kg), „₾“ (GEL).

## 4. Motion & Animation Rules
- Cards snap onto the board with a slight 3D rotation settle (10 frames).
- Dimension lines draw out between points via SVG dashoffset.
- Stamped marks slam down with immediate opaque ink deposit and micro-shake (3 frames).
- Transitions: swift camera pans across board sections.

## 5. Sound Craft
- Tactile, steady engineering loop (tech, economy).
- Constant audio level without ducking.
- SFX: solid magnet snap or documentary thud (`thud`), pen click (`click`), and paper rustle (`pop`).
