# One-line Drawing (`one-line`)

> Continuous fluid line drawing that never leaves the paper, where figures and conceptual diagrams morph seamlessly from one form to the next.

## 1. At-a-Glance Signature
- A single, unbroken fluid vector line that traces across the canvas without lifting the pen.
- Seamless morphing: faces, architectural landmarks, natural landscapes, and abstract concepts transform through continuous topological deformation.
- Smooth ink line on clean dark or paper canvas using the brand pack's ink color.
- Traveling camera subtly tracking the leading tip of the pen.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Centered vertical drawing stage: $x \in [100, 940]$, $y \in [300, 1340]$.
- Line paths curl and weave within the vertical canvas bounds, avoiding abrupt edge clipping.
- Safe zone: drawing tip stays within $y \le 1380$; captions sit below at $y \in [1380, 1552]$.
- Right margin clearance: $x \le 940$ below $y = 1100$.

## 3. Georgian Mkhedruli Typography
- Complementary geometric sans-serif in `FiraGO 400` or `FiraGO 500`.
- Text reveals in synchronization with the arrival of the drawing line at designated station stops.
- Mkhedruli lettering loops harmonize naturally with continuous single-stroke flourishes.

## 4. Motion & Animation Rules
- Continuous line growth via path length interpolation at smooth constant velocity ($900–1400\text{ px/s}$).
- Shape morphs execute via smooth cubic splines without harsh vertex jumping.
- Transitions: the continuous line sweeps off-screen to draw the opening outline of the next scene.

## 5. Sound Craft
- Elegant, fluid acoustic or minimalist piano loop (culture, society).
- Constant audio level without ducking.
- SFX: soft paper friction whoosh (`whoosh`), delicate pen touch click (`click`).
