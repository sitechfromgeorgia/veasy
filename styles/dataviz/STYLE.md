# Data Storytelling (`dataviz`)

> Data visualization that tells an analytical story: charts drawn point by point with animated leader lines and callout badges.

## 1. At-a-Glance Signature
- Dynamic chart surface: tall vertical plot area with animated bars, diverging lines, or stepped histograms.
- Callout pins with hairline leaders pointing directly to the pivotal data inflection point.
- Rolling numerical counter animating from base to target value in exact sync with voiceover announcement.
- Value sonification or subtle acoustic blips marking each threshold crossing.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Vertical plot container: $x \in [100, 920]$, $y \in [360, 1280]$.
- Y-axis labels positioned cleanly at left margin ($x \in [72, 160]$).
- X-axis category labels spaced across bottom of plot box ($y \in [1240, 1300]$).
- All callout annotation cards stay within $y \le 1380$ and $x \le 940$.
- Captions strictly in lower band: $y \in [1380, 1552]$.

## 3. Georgian Mkhedruli Typography
- Monospace or tabular figures for numeric values (`IBM Plex Mono` or tabular numerals) to prevent layout jitter during count-up animation.
- Currency symbols: official Georgian Lari symbol „₾“ or word „ლარი“ placed after the number with a non-breaking space (e.g. `250 ₾` or `12,5%`).
- Georgian percentage formatting: `%` symbol follows the numeral directly without space (`15%`).

## 4. Motion & Animation Rules
- Chart lines drawn via SVG `strokeDashoffset` from left to right over 20–30 frames.
- Bars grow upward from zero baseline using smooth decelerating easing (`cubic-bezier(0, 0, 0.2, 1)`).
- Counters roll synchronously with the drawing of the graphical elements.
- Transitions: meter sweeps or horizontal line cuts.

## 5. Sound Craft
- Clean, inquisitive analytical music bed (economy, tech loops).
- Constant audio level, strictly avoiding volume pumps.
- SFX: light acoustic blip (`blip`) on milestone thresholds, soft click (`click`) when final value locks into place.
