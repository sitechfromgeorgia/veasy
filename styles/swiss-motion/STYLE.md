# Swiss Motion (`swiss-motion`)

> International Typographic Style on a strict modular vertical grid where every element snaps into place without bounce or wobble.

## 1. At-a-Glance Signature
- Flush-left, rag-right typography strictly snapped to a 6-column vertical module rhythm.
- Extreme scale contrast: giant focal numerals or words (FiraGO 900, 160–220 px) paired with disciplined metadata (FiraGO 400, 28–36 px).
- Fine geometric hairline guides (1–2 px, line tokens), hairline crosshairs, and disciplined negative space.
- Single signal accent (from the brand pack), strictly used as an indicator dot or active state line—**never on text**.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- **Vertical Canvas**: 1080×1920 px.
- **Top Safe Line**: $y \ge 248$ (header, brand mark, category pill, and date).
- **Scene Text Area**: $y \in [248, 1380]$. No primary scene headlines or body text below $y = 1380$.
- **Lower Third & Captions**: $y \in [1380, 1552]$ reserved for synchronized word-level captions.
- **Side Rails**: Left margin $x = 72$, right margin $x = 1008$. Below $y = 1100$, no interactive or crucial text right of $x = 940$ (reserving the TikTok/Instagram like/share rail).

## 3. Georgian Mkhedruli Typography
- Mkhedruli lacks capital letters: contrast is created strictly through font weights (`FiraGO 900` vs `FiraGO 400`) and scale (ratios of 4:1 to 6:1), never faux all-caps.
- Optical alignment: letters with ascending (`ქ`, `ჩ`, `ქ`) or descending (`ყ`, `ფ`, `შ`) strokes are optically aligned to baseline grids.
- Tight line-height ratios: 1.05 to 1.15 for giant lead headers, 1.35 for explanatory narrative body copy.

## 4. Motion & Animation Rules
- Zero spring bounce, zero wobble, zero overshoot. Easing is crisp linear or steep cubic-bezier (`cubic-bezier(0.16, 1, 0.3, 1)`).
- Durations are fast and authoritative: cuts are instantaneous, wipe lines move across in 8–12 frames (0.26–0.4 s at 30 fps).
- Staggered entrances: elements slide 40 px upward into position with 3-frame offsets.
- Transitions: crisp horizontal hairlines slicing across the canvas or clean modular cuts.

## 5. Sound Craft
- Music bed: structured, rhythmic acoustic or minimalist electronic loop at constant mix volume.
- **Owner Law**: Constant level throughout the video. Absolutely **no ducking**, no pumping, no riser sweeps.
- SFX: mechanical typewriter tick (`tick`), subdued click (`click`) exactly synchronized to line transitions.
