# Transit Map (`transit-map`)

> Octilinear schematic route map growing along 8 directions with rounded fillets, interchange capsules, and animated station stops.

## 1. At-a-Glance Signature
- Strict octilinear geometry: lines run exclusively along 0°, 45°, and 90° angles with circular arc fillets at turns.
- Station nodes drawn as pills or circular capsules; interchange stations drawn as linked capsule rings.
- Dynamic route growth: colored route vectors trace forward from origin to destination.
- Clean geographical context (river or coastline vector) drawn in muted brand background lines.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Vertical alignment naturally accommodates Georgian transit corridors (e.g. Tbilisi Metro M1 north-south line or East-West highway).
- Map schematic viewport: $x \in [80, 940]$, $y \in [300, 1340]$.
- Station name labels: placed 45° or 0° with generous text halo clearance to ensure legibility over vector lines.
- Captions remain strictly in lower band $y \in [1380, 1552]$.

## 3. Georgian Mkhedruli Typography
- Station names rendered in clean, legible `FiraGO 500` (28–36 px).
- Line numbers and terminal identifiers in bold monospace (`IBM Plex Mono 600`).
- Text halos rendered in canvas background color (`rgba(canvas, 0.9)`) to prevent line crossing illegibility.

## 4. Motion & Animation Rules
- Progressive vector tracing: route paths grow along route waypoints over 30–45 frames.
- Station drops: station markers drop into place with slight 2-frame scale recoil as the route head reaches them.
- Camera moves: smooth pan/zoom tracking the growing route tip.

## 5. Sound Craft
- Smooth ambient pulse or modern acoustic loop mixed at constant level.
- SFX: soft relay click (`click`) as each station registers, subtle air whoosh (`whoosh`) on camera reframing.
- No volume dipping or ducking.
