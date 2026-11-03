# Countdown (`countdown`)

> Real-time split-screen multi-feed counting down whole seconds to a pivotal moment, merging dramatically into one unified frame at zero.

## 1. At-a-Glance Signature
- Ticking whole-second digital clock counting down in giant tabular figures.
- Dynamic split-screen grid: frame divides into $1 \to 2 \to 4$ synchronized camera cells tracking multiple perspectives or countdown stages.
- Live sync status badges in each cell (e.g. `კამერა 1 · პირდაპირი`).
- Explosive snap merge: grid cell borders collapse at T-0, merging all perspectives into a single heroic frame.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Vertical split-screen configurations:
  - 2-cell: stacked top and bottom ($y = 260\dots 800$ and $y = 820\dots 1360$).
  - 4-cell: 2×2 grid with 8 px dividing hairlines.
- Central countdown clock badge: centered at $x = 540, y = 810$ or anchored at top right.
- Captions remain strictly in lower safe band: $y \in [1380, 1552]$.
- Side rail clear zone: $x \le 940$ below $y = 1100$.

## 3. Georgian Mkhedruli Typography
- Countdown digits use bold fixed-width monospace figures (`IBM Plex Mono 700`, 120–180 px) to prevent width jitter during decrements.
- Synchronized Georgian status badges: `პირდაპირი ეთერი`, `დაწყებამდე დარჩა`, `T-0`.
- Headline text rendered in authoritative `FiraGO 700`.

## 4. Motion & Animation Rules
- Clock updates on exact second intervals with sharp 1-frame snaps.
- Grid partition lines slide open from screen edges.
- At T-0, border lines snap out and the target frame scales rapidly to fill the vertical canvas ($0.95 \to 1.0$).
- Transitions: hard flash cuts on countdown beats.

## 5. Sound Craft
- Driving, suspenseful, rhythmic electronic or orchestral pulse (sports, politics, tech).
- Constant audio level without ducking or artificial volume drops.
- SFX: heavy mechanical clock tick (`tick`) on every second, powerful low-end impact thud (`thud`) at T-0.
