# Sci-fi Hologram HUD (`hologram-hud`)

> Futuristic volumetric holographic HUD: glowing cyan/amber wireframe models rotating over telemetry rings with animated coordinate grids.

## 1. At-a-Glance Signature
- Deep space-black background (`#06080D`) with luminous cyan wireframe vectors (`#06B6D4`) and amber focal highlights (`#F59E0B`).
- Central volumetric wireframe model rotating on a projected base pedestal ring.
- Concentric telemetry rings, arc gauges, dynamic rangefinders, and animated coordinate hairlines.
- Additive blending glows and subtle scanline raster lines.

## 2. Brand & Program Rules (Strict)
- **Palette: Own**: Cyan wireframe glow (`#06B6D4`), amber focal accents (`#F59E0B`), and deep void black (`#06080D`).
- **Brand Law Invariant**: **Forbidden for news programs (`news`)**. Allowed only for technology explainers, fiction, and tech blog posts, and **only when explicitly listed in `brand.json` under `"styles"`** (e.g. SiTech).

## 3. Vertical (1080×1920) Geometry & Safe Zones
- Volumetric projection chamber: $x \in [100, 940]$, $y \in [300, 1340]$.
- Circular base emitter ring: centered at $x = 540, y = 1260$.
- Telemetry gutters: top telemetry bar at $y \in [248, 320]$, lateral gauges along left margin $x \in [72, 180]$.
- Captions strictly in lower third: $y \in [1380, 1552]$.
- Right social margin: $x \le 940$ below $y = 1100$.

## 4. Georgian Mkhedruli Typography
- Monospace telemetry and system diagnostics in `IBM Plex Mono 500`.
- Section headers in sharp, technical `FiraGO 600`.
- Status readouts: `სკანირება დასრულდა`, `ტელემეტრია`, `კოორდინატები`.

## 5. Motion & Animation Rules
- Continuous wireframe rotation along Y-axis ($15^\circ/\text{s}$).
- Concentric HUD rings rotate in counter-clockwise and clockwise opposition.
- Target reticles sweep and lock onto focal components with instantaneous cyan flares.
- Transitions: holographic scanline wipe or digital pixel-sort cut.

## 6. Sound Craft
- Sci-fi atmospheric drone and crisp rhythmic telemetry pulse.
- Constant volume without ducking.
- SFX: digital radar blip (`blip`), laser telemetry tick (`tick`), capacitor click (`click`).
