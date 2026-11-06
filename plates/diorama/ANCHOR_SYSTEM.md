# Veasy Paper Stage — 3D-to-2D Anchor Exporter System

## 1. Purpose & Overview

Veasy films display pure DOM typography, category kickers, headlines, stat callouts, and the brand accent dot layered cleanly over the baked 3D plate video. The 3D plate is tone-only (greyscale on black void), holding no text and no baked color.

The DOM elements must follow moving points of interest in the 3D world as the camera pushes, cranes, or dollies through the diorama. For example:
- **`dot`**: The brand accent dot hovering over the primary exhibit artifact, standee figure head, or focal center.
- **`kicker`**: A context label resting above an architectural archway apex.
- **`headline`**: The main title card anchored in the upper clerestory clearance.
- **`stat`**: Data/metric callout badges hovering over display pedestals or podiums.
- **`label`**: Secondary descriptive text tracking midground elements.

The Anchor Exporter (`plates/diorama/lib/anchors.mjs`) provides the mathematical projection pipeline and export contract connecting Three.js world space to screen pixels, producing `anchors.json` at bake time.

---

## 2. Projection Mathematics

```
                       [ 3D World Space Point P(X, Y, Z) ]
                                       │
                                       ▼ camera.matrixWorldInverse
                       [ View / Camera Space (Xc, Yc, Zc) ]
                                       │
                                       ▼ camera.projectionMatrix
                       [ Clip Space Coordinates (Xclip, Yclip, Zclip, Wclip) ]
                                       │
                                       ▼ Perspective Divide (/ Wclip)
                       [ Normalized Device Coordinates (ndc.x, ndc.y, ndc.z) ]
                                       │
               ┌───────────────────────┴────────────────────────┐
               ▼                                                ▼
     [ Frustum & Occlusion Checks ]                  [ Normalized Viewport (u, v) ]
     - inFront: ndc.z < 1.0                          - u = (ndc.x + 1) / 2
     - inBounds: u, v ∈ [-0.1, 1.1]                  - v = (1 - ndc.y) / 2
     - visible = inFront && inBounds                            │
                                                                ▼
                                                     [ Viewport Screen Pixels ]
                                                     - x = u * viewportWidth
                                                     - y = v * viewportHeight
                                                                │
                                                                ▼ (/ job.scale)
                                                     [ Canonical Reference Frame ]
                                                     - (1080 × 1920)
```

### 2.1 World Space to NDC
For any world point $P = (X, Y, Z)^T$:
$$P_{\text{clip}} = M_{\text{proj}} \cdot M_{\text{view}} \cdot \begin{pmatrix} X \\ Y \\ Z \\ 1 \end{pmatrix}$$
In Three.js perspective camera, perspective division by $W_{\text{clip}} = -Z_{\text{camera}}$ yields Normalized Device Coordinates:
$$\text{ndc}.x = \frac{X_{\text{clip}}}{W_{\text{clip}}}, \quad \text{ndc}.y = \frac{Y_{\text{clip}}}{W_{\text{clip}}}, \quad \text{ndc}.z = \frac{Z_{\text{clip}}}{W_{\text{clip}}}$$

### 2.2 NDC to Viewport Pixels
In normalized viewport space:
- $u = \frac{\text{ndc}.x + 1}{2} \in [0, 1]$ (left to right)
- $v = \frac{1 - \text{ndc}.y}{2} \in [0, 1]$ (top to bottom)

Mapped to viewport pixels:
$$x = u \cdot \text{width}$$
$$y = v \cdot \text{height}$$

### 2.3 Frustum & Occlusion Checks
1. **In Front of Camera**:
   In Three.js perspective projection, points behind the camera plane have negative clip-space $W_{\text{clip}} < 0$. Dividing by negative $W$ mirrors the $X$ and $Y$ coordinates and forces $\text{ndc}.z > 1.0$.
   $$\text{inFront} \iff \text{ndc}.z < 1.0 \quad (\text{and } Z_{\text{camera}} < 0)$$
2. **Viewport Frustum Bounds**:
   To prevent abrupt popping when elements enter or exit the screen, a 10% bleed margin is applied:
   $$\text{inBounds} \iff u \in [-0.1, 1.1] \quad \text{and} \quad v \in [-0.1, 1.1]$$
3. **Visibility**:
   $$\text{visible} = \text{inFront} \land \text{inBounds}$$

### 2.4 Scale Invariance
When `plates/run.mjs` executes headless Chrome at scale $s \in (0, 2]$:
- Viewport is sized to $(1080 \cdot s) \times (1920 \cdot s)$.
- `window.anchors(t)` outputs page pixels $[x_{\text{page}}, y_{\text{page}}]$.
- `run.mjs` normalizes coordinates:
  $$x_{\text{ref}} = \frac{x_{\text{page}}}{s} = u \cdot 1080$$
  $$y_{\text{ref}} = \frac{y_{\text{page}}}{s} = v \cdot 1920$$
Coordinates stored in `anchors.json` are strictly guaranteed to be in the canonical $1080 \times 1920$ reference frame regardless of render scale.

---

## 3. Export Contract

### 3.1 Per-Frame Contract: `window.anchors(t)`
Called by `run.mjs` on every frame $i$ with $t = i / \text{FPS}$:
```js
window.anchors(t) -> {
  "dot": [540.0, 960.0],
  "kicker": [540.0, 480.0],
  "headline": [540.0, 720.0],
  "stat": [280.0, 1150.0]
}
```

### 3.2 Output File Contract: `anchors.json`
Exported alongside `plate.mp4` and `plate.json`:
```json
{
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "tracks": {
    "dot": [
      [540.0, 960.0],
      [540.2, 959.8],
      [540.5, 959.5]
    ],
    "kicker": [
      [540.0, 480.0],
      [540.1, 480.2],
      [540.3, 480.5]
    ]
  }
}
```

---

## 4. API Reference (`plates/diorama/lib/anchors.mjs`)

### 4.1 Standalone Projection
```js
import { projectWorldToScreen, projectToReferenceScreen } from "./lib/anchors.mjs";

const result = projectWorldToScreen(point, camera, 1080, 1920);
// returns {
//   x, y, u, v, ndc, cameraSpaceZ, inFront, inBounds, visible, inSafeZone, pixel: [x, y]
// }
```

### 4.2 AnchorSystem Class
```js
import { AnchorSystem } from "./lib/anchors.mjs";

const anchorSystem = new AnchorSystem(camera, ctx, {
  defaultPolicy: 'clamp', // 'clamp' | 'omit' | 'lastKnown' | 'always'
});

// 1. Static 3D coordinate
anchorSystem.add('dot', [0, 1.2, -0.9]);

// 2. Object3D hierarchy attachment with local offset
anchorSystem.add('standee_head', standeeMesh, { offset: [0, 1.5, 0] });

// 3. Bounding box keypoints ('top', 'center', 'bottom', 'apex', 'base')
anchorSystem.addKeypoint('pedestal_surface', pedestalMesh, 'top');
anchorSystem.addKeypoint('arch_apex', archMesh, 'apex');

// 4. Dynamic trajectory function of time t
anchorSystem.add('sweeping_focus', (t) => [Math.sin(t), 1.2, -1.0]);

// 5. Load directly from set JSON (e.g. museum-hall.json)
anchorSystem.loadFromSet(setSpec);

// 6. Auto-scan scene graph for tagged objects
anchorSystem.scanScene(scene);

// 7. Bind to window.anchors
anchorSystem.bindToWindow();
```

---

## 5. Verification Suite
Run the test suite directly:
```bash
node plates/diorama/test_anchors.mjs
```
The test suite validates:
1. Core projection math (center point optical axis, vector formats).
2. Frustum & occlusion checks (behind camera, outside bleed bounds).
3. Scale invariance across 0.5x, 1.0x, and 2.0x scales.
4. Target types (static vectors, dynamic hierarchies, keypoint bounding boxes, trajectories).
5. Scene graph scanning (`anchor:*`, `userData.anchor`, `userData.anchors`).
6. Diorama set JSON loading (`sets/museum-hall.json`).
7. Export contract & `anchors.json` schema validation.
8. Safe zone rule compliance (text $Y \le 1380$).
