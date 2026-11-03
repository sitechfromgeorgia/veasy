# Pictogram Motion (`pictogram-motion`)

> Beat-locked visual catalog where every fact, metric, or entity is represented by a crisp geometric sign or icon on a modular card.

## 1. At-a-Glance Signature
- Centered geometric sign or Isotype icon drawn within a rounded or circular container.
- Clean card modules with subtle border strokes (`line` token), floating on the dark brand canvas.
- Modular stacking: top stage holds the primary symbol, mid stage holds the headline and Georgian stem label, lower stage holds numeric or categorical tags.
- Icon mapping leverages `tt_shorts.icons` to select canonical symbols from Georgian narrative stems.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Card width: 936 px (centered horizontally at $x = 540$, margins $x = 72$).
- Card vertical placement: $y \in [320, 1340]$ with vertical auto-centering.
- Primary symbol container: 240×240 px icon stage centered horizontally.
- Bottom safe boundary: Scene content ends at $y \le 1380$; lower-third captions sit below at $y \in [1380, 1552]$.
- TikTok rail: $x \le 940$ strictly maintained below $y = 1100$.

## 3. Georgian Mkhedruli Typography
- Card labels use medium-weight Mkhedruli (`FiraGO 600`, 48–64 px) with high legibility.
- Subordinate metric captions use `FiraGO 400`, 32 px with generous letter spacing.
- Short stem labels: words must fit single-line horizontal card headers without word hyphenation.

## 4. Motion & Animation Rules
- Card entry: quick pop/rise with subtle overshoot dampening (`cubic-bezier(0.34, 1.56, 0.64, 1)`), 12 frames.
- Icon drawing: stroke-dashoffset reveal or geometric scale up from center ($0.8 \to 1.0$).
- Transitions: cards slide left/right as new cards slide in from right, or swap on whole-beat cuts.

## 5. Sound Craft
- Upbeat, crisp rhythmic bed (tech, society, culture loops) mixed at constant level.
- SFX: subtle wooden or soft plastic pop (`pop`), crisp click (`click`) on card arrival and metric change.
- No ducking, no risers, no artificial sweeps.
