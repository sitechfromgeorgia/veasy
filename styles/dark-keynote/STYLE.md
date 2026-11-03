# Dark Tech Keynote (`dark-keynote`)

> Precision dark-mode product keynote featuring near-black gradient backgrounds, hairline UI grids, soft luminous glow accents, and generous negative space.

## 1. At-a-Glance Signature
- Deep charcoal or near-black backdrop (`canvas` token, e.g. `#171817` or `#05080F`) with subtle radial illumination.
- Floating dark UI cards with 1 px semi-transparent borders (`line` token) and soft specular edge highlights.
- Luminous status dot indicator in the single brand accent color, pulsating gently on state changes.
- Large typographic focal points (product features, benchmark numbers) surrounded by generous negative space.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Vertical UI card stack: cards are 920 px wide, centered at $x = 540$.
- Content area: $y \in [260, 1340]$ with vertical spacing between cards $\ge 32$ px.
- Lower-third captions: $y \in [1380, 1552]$.
- Right social margin: $x \le 940$ strictly maintained below $y = 1100$.

## 3. Georgian Mkhedruli Typography
- Clean technical weights: `FiraGO 700` for hero feature titles, `FiraGO 400` for crisp explanatory subtitles.
- Numbers in tabular monospace font (`IBM Plex Mono 600`).
- Accent underline or subtle glowing pill around highlighted terms.

## 4. Motion & Animation Rules
- Cards slide upward into view with crisp exponential deceleration (`cubic-bezier(0.16, 1, 0.3, 1)`), 14 frames.
- Glowing indicator dots pulse gently ($1.0 \to 1.15 \to 1.0$).
- Benchmark numbers roll upward to settled figures.
- Transitions: swift horizontal card slides or hairline wipes.

## 5. Sound Craft
- Polished, modern minimalist electronic bed (tech, economy loops).
- Mix maintained at a constant, steady level without ducking.
- SFX: subtle synthetic click (`click`), soft UI pop (`pop`), low blip (`blip`).
