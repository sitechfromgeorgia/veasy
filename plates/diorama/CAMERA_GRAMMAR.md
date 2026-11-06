# Cinematic One-Take Camera Grammar for Veasy Paper Stage

**Module**: `plates/diorama/lib/camera.mjs`  
**Author**: Camera Grammar Author  
**Target Platform**: Three.js r184 on SwiftShader (Headless Chrome, 1080×1920 portrait)  
**Contract**: `step(t)` pure deterministic function of normalized time $p = t / \text{seconds}$. No `Math.random`, no clocks, zero state leakage across frames.

---

## 1. Cinematic Grammar Foundations

### 1.1 Hitchcock's *Rope* (1948) Foreground Wipes
- **Principle**: In Alfred Hitchcock’s *Rope*, continuous 10-minute magazine takes were bridged by panning behind an actor’s dark jacket, a wooden column, or a chest lid, creating full optical occlusion that masked reel changes without an apparent cut.
- **Paper World Implementation (`wipe-pass`)**:
  - In a miniature diorama, a foreground architectural element (e.g. a proscenium arch jamb, fluted Greek column, bridge pier, or weeping willow trunk) sweeps across the lens.
  - At $p = 0.5$, the occluding layer achieves peak occlusion ($1.0$), filling the vertical frame and creating the organic wipe transition (`object-wipe` device in `concepts/devices.json`).
  - Camera near plane is clamped at $0.08$ (8 mm physical miniature distance) so paper surfaces never cross into the camera volume or produce ugly polygon clipping.

### 1.2 Mendes & Deakins (*1917*) & Iñárritu (*Birdman*) Trajectories
- **Principle**: Continuous floating camera motion with $C^1$ and $C^2$ continuity. Roger Deakins' Trinity rig maintained silky, continuous transitions between low-level trench tracking, crane ascents, and interior room entries without abrupt acceleration impulses (jerk).
- **Paper World Implementation (`smootherstep`, `spline`)**:
  - Replaces abrupt cubic easing with Perlin's quintic smootherstep $S_5(p) = p^3(10 - 15p + 6p^2)$ where both velocity and acceleration are strictly zero at the start and end ($S_5'(0)=0, S_5'(1)=0, S_5''(0)=0, S_5''(1)=0$).
  - Gaze vector ($\mathbf{T}$) and eye vector ($\mathbf{C}$) are co-evaluated smoothly. Camera roll is strictly locked to $0^\circ$ to maintain tabletop diorama stability.

### 1.3 Tilt-Shift Miniature Framing & Parallax Cues
- **Optics**:
  - Aspect ratio: Portrait 1080×1920 ($\text{aspect} = 0.5625$).
  - Vertical FOV: $38^\circ$ (mimicking a 65–85mm macro lens on miniature tabletop sets).
  - Low vantage: Camera height $Y_c \in [1.4, 2.4]$ with gentle downward pitch $\theta_{\text{pitch}} \in [-10^\circ, -22^\circ]$ focused on ground plinth ($Y=0$) and character figures ($Y \approx 1.1$).
  - Multilayer Parallax:
    - Foreground layers ($Z \in [2, 4]$): High screen velocity ($\Delta u \propto 1 / (Z_c - Z)$).
    - Focal hero plane ($Z \approx 0$): Stable anchor positioning.
    - Background scrims ($Z \in [-6, -12]$): Slow, majestic drift.
  - Fog as Depth Tone: Linear fog (`near: 8, far: 22`) delivers atmospheric tone graduation without the prohibitive 903 ms cost of software PBR / raymarched depth of field.

---

## 2. Supported Camera Moves (`spec.move`)

| Move | Spec Key | Description | Cinematic Function |
|---|---|---|---|
| **Dolly** | `dolly` | Axial ($Z$) or lateral ($X$) tracking across layered flats. | Reveals depth through differential motion parallax. |
| **Crane** | `crane` | Vertical descent/ascent ($Y$) with radial jib compensation and pitch tilt. | Shifts scale from macro architectural overview to intimate character plinth. |
| **Push-Through** | `push-through` | Forward transit through an arch, portal, or window into an interior chamber. | Seamless transition between exterior and interior stage sets without cuts. |
| **Reveal-Behind** | `reveal-behind` | Curvilinear orbit around a hero foreground occluder to unmask a hidden subject. | Narrative discovery beat; dramatizes revelations and plot twists. |
| **Wipe-Pass** | `wipe-pass` | Foreground pillar/trunk sweeps across lens, hitting 100% occlusion at $p=0.5$. | Hitchcockian scene transition; powers Veasy's `object-wipe` device. |

---

## 3. Mathematical Specifications

### 3.1 Time Normalization
$$p = \mathrm{clamp}\left(\frac{t}{\text{seconds}}, 0, 1\right)$$

### 3.2 Easing Functions
- **Smoothstep (Hermite Cubic, $C^1$)**:
  $$S_3(p) = 3p^2 - 2p^3$$
- **Smootherstep (Perlin Quintic, $C^2$ — Recommended Default)**:
  $$S_5(p) = 6p^5 - 15p^4 + 10p^3 = p^3(10 - 15p + 6p^2)$$
  $$\frac{dS_5}{dp} = 30p^2(1 - p)^2 \implies S_5'(0)=0, S_5'(1)=0$$
  $$\frac{d^2S_5}{dp^2} = 60p(1 - p)(1 - 2p) \implies S_5''(0)=0, S_5''(1)=0$$
- **Cubic Bézier Solver**:
  Evaluates $B(s)$ where $x(s) = p$ via 6-iteration Newton-Raphson:
  $$s_{n+1} = s_n - \frac{x(s_n) - p}{x'(s_n)}, \quad y = y(s)$$

### 3.3 Kinematics by Move
1. **Dolly**:
   $$\mathbf{C}(p) = \mathbf{C}_{\text{start}} + S_5(p) \cdot (\mathbf{C}_{\text{end}} - \mathbf{C}_{\text{start}})$$
   $$\mathbf{T}(p) = \mathbf{T}_{\text{start}} + S_5(p) \cdot (\mathbf{T}_{\text{end}} - \mathbf{T}_{\text{start}})$$
2. **Crane**:
   $$Y_c(p) = Y_{\text{start}} + S_5(p) \cdot (Y_{\text{end}} - Y_{\text{start}})$$
   $$Z_c(p) = Z_{\text{base}} - R_{\text{jib}} \cdot \sin\left(\frac{Y_c(p) - Y_{\text{start}}}{R_{\text{jib}}} \cdot 0.5\right) \cdot 0.8$$
   $$\theta_{\text{pitch}}(p) = \theta_{\text{start}} + S_5(p) \cdot (\theta_{\text{end}} - \theta_{\text{start}})$$
3. **Push-Through**:
   $$\mathbf{C}(p) = \begin{cases}
   \mathbf{C}_{\text{start}} + S_5(2p) \cdot (\mathbf{P}_{\text{portal}} - \mathbf{C}_{\text{start}}), & p < 0.5 \\
   \mathbf{P}_{\text{portal}} + S_5(2p - 1) \cdot (\mathbf{C}_{\text{end}} - \mathbf{P}_{\text{portal}}), & p \ge 0.5
   \end{cases}$$
4. **Reveal-Behind**:
   $$\theta(p) = \theta_0 + S_5(p) \cdot \Delta \theta$$
   $$C_x(p) = P_{\text{occ}, x} + R \cdot \sin(\theta(p))$$
   $$C_z(p) = P_{\text{occ}, z} + R \cdot \cos(\theta(p))$$
   $$\mathbf{T}(p) = \mathbf{T}_{\text{edge}} + S_5(p) \cdot (\mathbf{T}_{\text{subject}} - \mathbf{T}_{\text{edge}})$$
5. **Wipe-Pass**:
   $$C_x(p) = X_{\text{start}} + S_5(p) \cdot (X_{\text{end}} - X_{\text{start}})$$
   $$C_z(p) = Z_{\text{base}} - \delta_{\text{near}} \cdot 4p(1 - p)$$
   $$\mathrm{occlusion}(p) = \begin{cases}
   S_5\left(1 - \frac{|p - 0.5|}{w_{\text{wipe}}}\right), & |p - 0.5| < w_{\text{wipe}} \\
   0, & \text{otherwise}
   \end{cases}$$

---

## 4. Anchor Projection & Safe Zone Integrity
- **Anchor Formula**:
  $$\mathbf{V}_{\text{clip}} = \mathbf{M}_{\text{proj}} \cdot \mathbf{M}_{\text{view}} \cdot \mathbf{V}_{\text{world}}$$
  $$\text{pixel}_x = \frac{V_{\text{clip}, x} + 1}{2} \cdot 1080$$
  $$\text{pixel}_y = \frac{1 - V_{\text{clip}, y}}{2} \cdot 1920$$
- **Safe Zone Rule**:
  - Text ends at $y = 1380$.
  - Captions at $y = 1552$.
  - Under $y = 1100$, no elements right of $x = 940$.
  - All anchors report `.inSafeZone` boolean flag.
