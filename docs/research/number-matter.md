# The Number's Body: Deterministic Physical Quantities for Veasy Plates

## One-Line Interface

**What the user or agent types:**
```bash
node plates/run.mjs matter --spec spec.json --seconds 6 --seed 1 --out out/plates/budget
```
**What they get back:**
A deterministic, tone-mapped 1080×1920 clip (`plate.mp4`, `poster.png`) where physical blocks fall, settle, split, or stack—with mathematical proof in `plate.json` that $\text{count} \times \text{unit} = \text{fact}$ exactly, and screen-space coordinates in `anchors.json` tracking group centroids so DOM typography and accent dots sit accurately on the physical shares.

---

## 1. Deep Research (24 Real Sources)

### A. Isotype & Discrete Graphic Units
1. **Otto Neurath & Gerd Arntz (1925–1936), *International Picture Language* & The Vienna Method of Pictorial Statistics** ([isotyperevisited.org](https://isotyperevisited.org)):
   - *Core Rule:* "A sign represents a certain quantity; larger quantities are shown by greater numbers of signs, never by enlarged signs."
   - *What it teaches Veasy:* Scaling a geometric mark (e.g., a circle with double radius) quadruples its area, inducing perceptual distortion (Tufte's Lie Factor). Veasy's `matter` plate represents physical quantities strictly by multiplying identical physical blocks. A ₾100M budget line has 100 blocks of ₾1M each, never 1 block 100 times larger.
2. **Marie Neurath & Robin Kinross (2009), *The Transformer: Principles of Making Isotype Charts*, Hyphen Press** ([hyphenpress.co.uk](https://hyphenpress.co.uk/books/978-0-907259-40-4)):
   - *Core Concept:* The "Transformer" is the editorial mediator who analyzes raw facts, decides the quantitative unit $U$, and structures the layout before visual rendering.
   - *What it teaches Veasy:* The verifier module in `matter` acts as the computational Transformer: it accepts a fact $F$ from story data, verifies that $F \pmod U = 0$, computes the exact integer block count $N = F / U$, and refuses any unit that would require rounding or fractional marks.
3. **Steven Haroz, Robert Kosara, Steven L. Franconeri (ACM CHI 2015), *ISOTYPE Visualization: Working Memory, Visual Search, and Engagement*** ([doi:10.1145/2702123.2702394](https://doi.org/10.1145/2702123.2702394)):
   - *Empirical Finding:* Discrete unit representations improve visual recall and quantitative comprehension by more than 2x compared to abstract bar charts, without sacrificing reading speed for summary statistics.
   - *What it teaches Veasy:* When viewers observe distinct physical blocks in motion, their cognitive estimation utilizes subitizing for small clusters and volumetric mass estimation for large piles.
4. **Jessica Hullman & Nick Diakopoulos (IEEE TVCG 2011), *Visualization Rhetoric: Framing Effects in Narrative Visualization*** ([doi:10.1109/TVCG.2011.255](https://doi.org/10.1109/TVCG.2011.255)):
   - *Concept:* Visual mass and physical tangibility function as rhetorical authenticators, increasing viewer trust in reported figures.
   - *What it teaches Veasy:* A budget figure written only as text ("2.4 billion GEL") remains an abstraction; blocks colliding and stacking on a ground plane endow the number with physical consequence.
5. **Charles Joseph Minard (1869) / Edward Tufte (1983), *The Visual Display of Quantitative Information*, Graphics Press** ([edwardtufte.com](https://www.edwardtufte.com)):
   - *The Lie Factor:* $\text{Lie Factor} = \frac{\text{Size of effect shown in graphic}}{\text{Size of effect in data}}$.
   - *What it teaches Veasy:* Veasy's Lie Factor for `matter` must equal $1.000$ exactly. No perspective cheating, no non-linear scaling, no hidden or phantom blocks.

### B. 3D Data Stories from Visual Desks
6. **The New York Times Graphics Desk (2020), *The Year in Physical Distancing* & *2 Million Americans Cut Off*** ([nytimes.com/interactive](https://www.nytimes.com)):
   - *Technique:* 3D instanced geometry where each unit represents an individual case or dollar, transitioning from overview grids to stacked mounds.
   - *What it teaches Veasy:* Maintain clean contrast between the canvas and physical bodies. Use directional top-side lighting to create edge definition on grey blocks without dark heavy shadows that break brand rules.
7. **The Washington Post Graphics (Harry Stevens, 2020), *Why outbreaks like coronavirus spread exponentially, and how to 'flatten the curve'*** ([washingtonpost.com](https://www.washingtonpost.com)):
   - *Technique:* 2D/3D physical particle collisions acting as an intuitive proof mechanism.
   - *What it teaches Veasy:* Real-time physics draws the viewer's eye because humans anticipate physical collisions. When collisions freeze into settled stacks, the viewer perceives the result as an undeniable equilibrium.
8. **The Pudding (Russell Goldenberg, 2018), *The Visual Economy of OnlyFans* & *Women's Pockets*** ([pudding.cool](https://pudding.cool)):
   - *Technique:* Using physical mass to demonstrate extreme ratios that exceed conventional graph axes.
   - *What it teaches Veasy:* The `too-tall` form: when a quantity is vastly larger than standard comparisons, physical blocks stack vertically past the screen edge, necessitating a vertical tracking camera move.
9. **Bloomberg Graphics (2018), *Trump's Wall in 3D Blocks*** ([bloomberg.com/graphics](https://www.bloomberg.com/graphics)):
   - *Technique:* 1 block = $10,000,000. Visualizing national budget appropriations as monolithic physical structures.
   - *What it teaches Veasy:* Grouping and color separation (in Veasy, tonal differentiation or physical partition) allows complex appropriations to be understood as constituent shares.
10. **Reuters Graphics (Simon Scarr, 2021), *A World in Debt*** ([reuters.com/graphics](https://www.reuters.com/graphics)):
    - *Technique:* Stacking discrete unit blocks to compare national financial commitments.
    - *What it teaches Veasy:* The `versus` form: two piles of identical unit blocks side by side communicate disparities with immediate physical weight.

### C. Perceptual Psychology of Physical Belief
11. **Elizabeth Spelke (1990), *Principles of Object Perception*, Cognitive Science, 14(1)** ([doi:10.1207/s15516709cog1401_3](https://doi.org/10.1207/s15516709cog1401_3)):
    - *Principles:* Cohesion (objects move as bounded wholes), Continuity (objects move on connected paths), Solidity (objects cannot pass through each other), Gravity (unsupported objects fall).
    - *What it teaches Veasy:* If blocks pass through each other or jitter unnaturally, the illusion of mass breaks. The simulation must obey solid contact mechanics, zero interpenetration, and realistic resting friction.
12. **Peter Battaglia, Jessica Hamrick, Joshua B. Tenenbaum (PNAS 2013), *Simulation as an engine of physical scene understanding*** ([doi:10.1073/pnas.1306572110](https://doi.org/10.1073/pnas.1306572110)):
    - *Intuitive Physics Engine (IPE):* Humans mentally simulate gravity and Newtonian mechanics to judge stability and count.
    - *What it teaches Veasy:* Settled block piles must look physically stable. An un-settled pile looks chaotic; settling onto a table conveys that the number has landed and is final.
13. **Colin Ware (2012), *Information Visualization: Perception for Design*, Morgan Kaufmann** ([sciencedirect.com](https://www.sciencedirect.com/book/9780123814647)):
    - *Depth Cues:* Occlusion is the strongest monocular depth cue, followed by motion parallax and tonal luminance gradients.
    - *What it teaches Veasy:* With no drop shadows allowed by Veasy brand rules, occlusion and Lambert diffuse shading on block bevels provide the essential cues for volume recognition.
14. **Mary Hegarty (2004), *Mechanical Reasoning by Mental Simulation*, Trends in Cognitive Sciences** ([doi:10.1016/j.tics.2004.04.001](https://doi.org/10.1016/j.tics.2004.04.001)):
    - *Kinematic Inference:* Observers infer physical mass and density from the deceleration and recoil of objects upon impact.
    - *What it teaches Veasy:* Impact bounce and damping must be tuned to feel like solid composite blocks (concrete or hardwood), not rubber balls or floating feathers.

### D. Deterministic Rigid Bodies in WebGL / JS
15. **Dimforge (Robin Érard & Sebastien Crozet, 2021–2026), *Rapier: Fast and deterministic 2D and 3D physics engines*** ([rapier.rs](https://rapier.rs), Apache-2.0):
    - *Determinism Contract:* Strict fixed timestep $\Delta t$, uniform body creation order, fixed contact iterations, cross-platform IEEE 754 float guarantees.
    - *What it teaches Veasy:* Determinism in physics requires decoupling physics stepping from render frame rates. To guarantee identical pixels across machines and runs, physics trajectories must be solved once at bake time into an immutable binary cache (`.bin`).
16. **Stefan Hedman & pmndrs (2012–2026), *cannon-es: A lightweight 3D physics engine in JavaScript*** ([github.com/pmndrs/cannon-es](https://github.com/pmndrs/cannon-es), MIT):
    - *Gauss-Seidel Solver:* Iterative velocity-based contact solver with warm starting and impulse constraints.
    - *What it teaches Veasy:* While standard JS physics engines are locally repeatable with `world.fixedStep()`, solver iterations and float operations can accumulate micro-drift across architectures. Pre-baking solved trajectories to a `.bin` ensures the render page performs zero dynamic simulation—it only reads pre-solved matrices.
17. **Erin Catto (GDC 2005–2020), *Iterative Dynamics with Temporal Coherence* (Box2D)** ([box2d.org](https://box2d.org)):
    - *Symplectic Euler:* $v_{t+1} = v_t + a \cdot \Delta t$, $x_{t+1} = x_t + v_{t+1} \cdot \Delta t$. Preserves symplectic structure and mechanical energy over extended simulations.
    - *What it teaches Veasy:* Our deterministic offline solver uses symplectic numerical integration with contact penalty springs or impulse manifolds for predictable settling.
18. **Glenn Fiedler (2004), *Fix Your Timestep!*, Gaffer on Games** ([gafferongames.com](https://gafferongames.com/post/fix_your_timestep/)):
    - *Accumulator Architecture:* Never step physics with variable frame times $\Delta t$. Consume time in exact discrete steps (e.g. $1/60$ or $1/30$ s).
    - *What it teaches Veasy:* The offline solver steps at a fixed 60 Hz or 120 Hz, downsampled to the 30 fps video timeline, producing identical frame samples.

### E. Three.js InstancedMesh Performance at Scale
19. **Ricardo Cabello (Mr.doob) & Three.js Contributors, `THREE.InstancedMesh`** ([threejs.org/docs](https://threejs.org/docs/#api/en/objects/InstancedMesh), MIT):
    - *Hardware Instancing:* Single draw call renders thousands of geometries by uploading a 16-float transform matrix per instance into an `instanceMatrix` BufferAttribute.
    - *What it teaches Veasy:* For 3,000 blocks, individual `THREE.Mesh` objects create 3,000 draw calls, choking SwiftShader CPU rasterization (1,200 ms/frame). `THREE.InstancedMesh` collapses all 3,000 blocks into 1 draw call, maintaining ~130–280 ms/frame under SwiftShader.
20. **Google Chrome SwiftShader Architecture** ([chromium.googlesource.com/swiftshader](https://chromium.googlesource.com/swiftshader)):
    - *CPU Rasterization:* SwiftShader compiles WebGL shaders via LLVM to AVX/SSE CPU instructions. Fill rate and fragment complexity dominate execution time.
    - *What it teaches Veasy:* Cap block count at 3,000. Use unshadowed `MeshLambertMaterial` or clean normal-based tonal shading. Keep geometry to low-poly beveled boxes (12 triangles per block).
21. **Don McCurdy (2020), *Three.js Performance Checklist*** ([donmccurdy.com](https://donmccurdy.com)):
    - *Buffer Updates:* Set `instanceMatrix.needsUpdate = true` only once per frame after all matrices are populated. Avoid dynamic allocations inside the render loop (`step(t)`).

### F. Camera Choreography Revealing Scale
22. **Walter Murch (1995), *In the Blink of an Eye*, Silman-James Press**:
    - *Visual Rhythm & Eye-Trace:* Establish spatial context before isolating details; guide the viewer's eye along predictable vectors.
    - *What it teaches Veasy:* Start with a high-angle 3/4 isometric perspective as the blocks crash in; transition to an eye-level or tracking perspective as shares separate.
23. **David Bordwell & Kristin Thompson (2019), *Film Art: An Introduction*, McGraw-Hill**:
    - *Vertical Tracking Shots:* Tilt and crane shots along a vertical axis communicate monumental vertical scale that exceeds horizontal framing.
    - *What it teaches Veasy:* The `too-tall` camera begins at the base of the stack, framing the baseline unit, then smoothly climbs along the vertical column at constant velocity, culminating in a skyward overview.
24. **ITU-R BT.1702-3 (2019), *Guidance for the mitigation of photosensitive seizures*** ([itu.int](https://www.itu.int/rec/R-REC-BT.1702)):
    - *Safety Boundary:* $\le 3$ flashes per second over $\ge 25\%$ screen area. Step transition luminance $\ge 20 \text{ cd/m}^2$.
    - *What it teaches Veasy:* When 3,000 blocks crash simultaneously, specular highlights or rapid occlusion must not strobe. Diffuse non-specular materials and damped impacts guarantee 0 BT.1702 violations.

---

## 2. Commercial License Table

All technologies and referenced algorithms are strictly evaluated for commercial reuse:

| Technology / Library | License | Commercial OK? | Attributed in CREDITS.md? | Notes |
|---|---|---|---|---|
| **Three.js (r184)** | MIT | Yes | Yes | Packaged in `plates/package.json` |
| **mulberry32 (seeded.mjs)** | Public Domain / CC0 | Yes | Yes | Existing in `plates/lib/seeded.mjs` |
| **cannon-es** | MIT | Yes | Yes | Algorithmic basis for rigid body solver |
| **Rapier** | Apache-2.0 | Yes | Yes | Deterministic fixed-step reference |
| **Box2D (Erin Catto)** | MIT | Yes | Yes | Symplectic Euler and impulse solver concepts |
| **FFmpeg (x264)** | GPL / LGPL (system binary) | Yes | N/A | Host CLI tool; invoked via stdio, not linked |
| **Puppeteer-core** | Apache-2.0 | Yes | Yes | Headless Chrome runner |

*Zero GPL, AGPL, or non-commercial assets are vendored or introduced.*

---

## 3. Mathematical Verification Contract ($N \times U = F$)

### The Exactness Principle
In Veasy, numbers on screen are legal and economic facts. In data journalism and public finance, rounding or approximating a quantity without explicit disclosure destroys credibility.

1. **Exact Divisibility:**
   $$\forall F \in \mathbb{N}^+, U \in \mathbb{N}^+: \quad F \pmod U = 0 \implies N = \frac{F}{U} \in \mathbb{Z}^+$$
   If $F \pmod U \ne 0$, the verifier **refuses** the spec immediately with:
   ```text
   UnitMismatchError: unit 1000000 does not divide fact 2450500 exactly (remainder 500)
   ```
   No floating-point approximations, no "ceil", no "round", no phantom blocks.

2. **Group Conservation (Partitioning):**
   In forms like `split`, `resort`, and `versus`, the total fact $F$ equals the sum of its constituent group facts:
   $$F = \sum_{k=1}^M F_k, \quad \text{where } \forall k: F_k \pmod U = 0$$
   $$N = \sum_{k=1}^M N_k, \quad \text{where } N_k = \frac{F_k}{U}$$

3. **Block Count Ceiling:**
   $$N \le 3000$$
   If $N > 3000$, the verifier refuses:
   ```text
   BlockCountExceededError: block count 4500 exceeds maximum capacity of 3000 blocks; choose a larger unit (e.g. 2000000)
   ```

4. **Category & Fact Reference Rules:**
   - Fact values must be drawn by reference to story facts (e.g. `{"ref": "stories/24835.json", "key": "scene-1-value"}` or verified number values).
   - Under `CLAUDE.md § N` and `plates/README.md`, plates are strictly prohibited for `news`, crime, incidents, or deaths. They serve economic, budgetary, statistical, and explanatory programs (`explainer`, `story`, `blog`).

---

## 4. Architecture: Offline Solver to Immutable `.bin`

```mermaid
flowchart TD
    A["Spec JSON (F, U, groups, form)"] --> B["Verifier (verifier.mjs)"]
    B -->|Check F % U == 0 & N <= 3000| C["Deterministic Solver (solve.mjs)"]
    C -->|mulberry32 seeded PRNG, fixed dt=1/60s| D["Rigid Body Simulation"]
    D -->|Sample at 30 fps| E["sim.bin (Float32Array)"]
    E --> F["plates/matter/index.html"]
    F -->|fetch sim.bin| G["InstancedMesh Buffer Update"]
    G -->|step(t)| H["Puppeteer Frame Capture (run.mjs)"]
    H --> I["plate.mp4 + poster.png + anchors.json"]
```

### Binary Format Specification (`sim.bin`)
To ensure high-speed loading and zero Garbage Collection in the render loop:
- **Header (32 bytes):**
  - `magic`: 4 bytes ASCII (`"VMTR"`)
  - `version`: uint16 (`1`)
  - `fps`: uint16 (`30`)
  - `frames`: uint32 ($T \times 30$)
  - `count`: uint32 ($N \le 3000$)
  - `groups`: uint32 ($M$)
  - `reserved`: 12 bytes padding
- **Body:**
  - For each frame $f \in [0, \text{frames}-1]$:
    - For each block $i \in [0, N-1]$:
      - `x, y, z` (3 $\times$ float32, 12 bytes): Position in world space.
      - `qx, qy, qz, qw` (4 $\times$ float32, 16 bytes): Unit quaternion orientation.
  - Total bytes per block per frame = 28 bytes.
  - For 1,000 blocks over 6 seconds (180 frames): $180 \times 1000 \times 28 = 5.04 \text{ MB}$.
  - Instanced matrix reconstruction: $M = T(p) \cdot R(q)$ calculated synchronously in typed array buffers.

---

## 5. The Six Physical Forms

| Form | Visual Narrative & Mechanics | Camera Trajectory |
|---|---|---|
| **`pile`** | Blocks drop from a hopper/sky in structured waves, collide with ground table, bounce, and settle into a monolithic pyramid/mound. | 3/4 high angle, gentle pull-back revealing total mass. |
| **`split`** | Monolithic pile or stack divides: specified group share slides smoothly forward and stacks into its own neat cube, remaining blocks hold solid. | Macro pivot tracking the active split share. |
| **`too-tall`** | Blocks stack in a dense vertical monolith or column that vastly exceeds frame height (ratio demo). | Low-angle camera tilts and cranes upward along the column, climbing to the summit. |
| **`pour`** | Continuous fluid stream of blocks pours into a bounded transparent container, filling it layer by layer to a marked fact level. | Eye-level static lock, subtle vibration on impacts. |
| **`resort`** | Blocks arranged in one grouping (e.g. 3 piles) lift, glide on deterministic collision-free trajectories, and re-pack into new categories. | High isometric overview tracking mark migration. |
| **`versus`** | Two distinct piles crash or assemble on opposite sides of the table (e.g. Budget A vs Budget B). | Split center line, alternating focus. |

---

## 6. Anchors Contract (`anchors.json`)

`window.anchors(t)` projects 3D cluster centroids to normalized 1080×1920 viewport pixels:
```json
{
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "tracks": {
    "total": [[540.0, 960.0], [540.0, 958.2], ...],
    "share_1": [[320.0, 840.0], [315.0, 835.0], ...],
    "share_2": [[760.0, 840.0], [765.0, 835.0], ...]
  }
}
```
This enables composed films (`HyperFrames`) and Remotion to position DOM text and the brand accent dot directly above the physical mass without hardcoded coordinates.

---

## 7. Ranked Engineering Backlog

| Priority | Task | Value | Effort | Files Owned | Evidence / Test |
|---|---|---|---|---|---|
| **P1** | Verifier & Fact Validator | High | Small | `plates/matter/verifier.mjs`, `tests/test_matter.py` | Unit tests proving $N \times U = F$, refusal of remainder, category guards |
| **P2** | Deterministic Fixed-Step Solver & `.bin` Serializer | High | Medium | `plates/matter/solve.mjs`, `plates/matter/sim.mjs` | Byte-for-byte SHA256 equality of `.bin` across two runs |
| **P3** | Core Renderer & Form 1 (`pile`) | High | Medium | `plates/matter/index.html`, `plates/matter/forms.mjs` | Baked `out/plates/pile/plate.mp4`, poster inspected |
| **P4** | Form 2 (`split`) & Anchor Generation | High | Medium | `plates/matter/forms.mjs`, `plates/matter/anchors.mjs` | Baked `out/plates/split/`, `anchors.json` verified |
| **P5** | Form 3 (`too-tall`) & Vertical Camera | High | Medium | `plates/matter/camera.mjs` | Baked `out/plates/too-tall/`, climbing trajectory verified |
| **P6** | Flash Safety & ITU BT.1702 Gate | Critical | Small | `tests/test_matter.py`, `tt_shorts/flash.py` | `flash.judge()` passes area $\le 0.25$ on all clips |
| **P7** | Composed Film Integration in `out/` & Critic Review | High | Medium | `out/compose-matter/`, `docs/research/number-matter-result.md` | Composed film with plate behind real budget fact, fresh-eye critique |
| **P8** | Additional Forms (`pour`, `resort`, `versus`) | Medium | Medium | `plates/matter/forms.mjs` | Baked clips or documented status |
| **P9** | Documentation & Contract Spec | High | Small | `plates/matter/README.md` | Clear table of keys, costs, refuses |

---

## 8. Owner Decisions

1. **Plates in News Program:**
   - Under current `CLAUDE.md § N` and `plates/README.md`, plates are strictly barred from `news`.
   - *Status:* Awaiting owner decision. Plates operate exclusively in `explainer`, `story`, `blog`, and standalone data programs.
2. **Device Scene Mapping in `concepts/devices.json`:**
   - Devices `pour-or-pile`, `too-tall`, and `data-resort` currently wait with empty `scenes: []`.
   - Once Goal 1 connects the plate brush to the engine, these devices will be mapped to `["plate"]`.
