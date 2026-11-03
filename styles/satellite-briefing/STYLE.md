# Satellite Briefing (`satellite-briefing`)

> Intelligence-style satellite briefing: aerial ground graded to analyst charcoal with thin measurement hairlines, reticles, and geographic telemetry.

## 1. At-a-Glance Signature
- Satellite or high-altitude aerial imagery graded to high-contrast charcoal/slate with thin white measurement hairlines and coordinate reticles.
- Animated target bracket locking onto a focal geographic point (building, port, mountain pass, or infrastructure hub).
- Live telemetry readouts: latitude/longitude coordinates, elevation, timestamp, and scale bar.
- Single brand accent finding pin highlighting the story's subject.

## 2. Veasy Georgia Map Law & Invariants (Strict)
- **Constitutional Integrity**: The map displays Georgia's 12 constitutional regions. **Abkhazia and Tskhinvali region are integral parts of Georgia** and are never delineated with dispute boundaries or separate coloring.
- **Never China-View / Foreign Map Rules**: Only official Georgian sovereign boundaries from `assets/maps/georgia.json` are permitted.
- **Crime News Rule**: In crime or incident stories, maps show only macro city or regional context—never specific residential micro-districts or stigmatized neighborhood outlines.

## 3. Vertical (1080×1920) Geometry & Safe Zones
- Map / satellite viewport occupies the central frame: $y \in [260, 1340]$.
- Header telemetry bar: $y \in [248, 320]$ displays coordinates in `IBM Plex Mono` (e.g. `41°43'N 44°47'E · 480m`).
- Scale bar and legend positioned at bottom left of viewport ($x = 100, y = 1300$).
- Captions remain strictly in lower third: $y \in [1380, 1552]$.
- Right rail ($x > 940$ below $y = 1100$) kept clear of target tags.

## 4. Georgian Mkhedruli Typography
- Geographic place names rendered in `FiraGO 600` with text shadows or semi-transparent backing pills.
- Telemetry figures in tabular monospace font (`IBM Plex Mono 400`).
- Scale markers using Georgian units: „მ“ (meters) or „კმ“ (kilometers).

## 5. Motion & Animation Rules
- Nadir zoom: satellite view slowly zooms inward towards target coordinates over the scene duration.
- Target reticle: square brackets converge inward ($1.4 \to 1.0$ scale) over 15 frames with smooth damping.
- Telemetry numbers roll into final decimal places.

## 6. Sound Craft
- Deep, focused analytical soundscape (world, politics, tech loops).
- Constant audio level, strictly avoiding volume build-ups or ducking.
- SFX: subtle electronic ping or camera relay click (`click`) when target locks.
