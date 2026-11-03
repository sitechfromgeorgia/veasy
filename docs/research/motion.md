# Veasy Motion Language: Research & Architecture Specification

**Goal:** Give Veasy a far wider motion language across hook layouts, background motifs, entrances, transitions,
kinetic typography, director motion personalities, and readability motion rules so that 1,000 generated videos
never look or feel alike.

---

## 1. Research Sources (26 Sources Analyzed)

### A. Motion Principles & Physics

1. **Disney's 12 Principles of Animation** (*The Illusion of Life*, Frank Thomas & Ollie Johnston)
   - *URL:* https://www.animatortips.com/principles
   - *Core insight:* Staging, timing, follow-through, overlapping action, and secondary action prevent stiff, robotic movement.
   - *What Veasy takes:* Secondary action on accents (e.g. dot settling after a rule extends), overlapping stagger for lines rather than simultaneous snaps, and strict prevention of competing simultaneous motions that distract viewers.

2. **Google Material Design 3 Motion System**
   - *URL:* https://m3.material.io/styles/motion/overview
   - *Core insight:* 4 core transition patterns: Shared Axis (directional translation along one dominant axis), Container Transform, Fade Through, and Fade. Physics-based easing reflects mass and momentum.
   - *What Veasy takes:* Shared Axis continuity: every directional move (slides, wipes, pushes, shutters) inherits the director's `current` vector (`left`, `right`, `up`). Transitions between scenes feel physically linked rather than arbitrary.

3. **IBM Carbon Design System Motion**
   - *URL:* https://carbondesignsystem.com/elements/motion/overview/
   - *Core insight:* Clear division between *productive motion* (100–200ms, linear/standard easing for informative data absorption) and *expressive motion* (200–400ms, energetic easing for hero moments and entrances).
   - *What Veasy takes:* Director motion bifurcation: data/brief directors use productive motion numbers (higher damping, shorter entrance frames, minimal stagger), while type/chronicle directors use expressive motion numbers (punchy spring, distinctive rhythm).

4. **Apple Human Interface Guidelines (Motion)**
   - *URL:* https://developer.apple.com/design/human-interface-guidelines/motion
   - *Core insight:* Purposeful, brief, non-gratuitous animation. Avoid rapid rotations or disorienting camera moves. Preserve spatial consistency across states.
   - *What Veasy takes:* Spatial anchors: safe zones are strictly honored, motion stays bounded within designated bands (no text crossing y=1380 or below y=1100 crossing x=940), and rotations are restricted to subtle perspective tilts without disorienting spins.

5. **Remotion Spring & Physics Theory** (Jonny Burger)
   - *URL:* https://www.remotion.dev/docs/spring
   - *Core insight:* Mass $m$, damping $c$, and stiffness $k$ govern harmonic oscillation: $F = -kx - cv$. Damping ratio $\zeta = \frac{c}{2\sqrt{km}}$. When $\zeta < 1$ the spring overshoots; when $\zeta \ge 1$ it glides into place without bounce.
   - *What Veasy takes:* Precise director tuning: `type` director uses underdamped spring ($\zeta \approx 0.65$, stiffness 240, damping 17) for punchy kinetic snap; `chronicle` uses overdamped spring ($\zeta \approx 1.1$, stiffness 120, damping 24) for stately glide; `data` uses critically damped spring ($\zeta \approx 1.0$) for zero-jitter reading stability.

6. **Mobile Phone Eye-Tracking & Reading Ergonomics** (Keith Rayner; Nielsen Norman Group Mobile Studies)
   - *URL:* https://www.nngroup.com/articles/mobile-content/
   - *Core insight:* On handheld vertical screens (9:16 aspect ratio), gaze fixates near the vertical center. Reading speed averages 200–250 words per minute under static conditions, but drops under motion. 0.5s visual acquisition base + 0.3s per word represents the empirical floor for cognitive comprehension.
   - *What Veasy takes:* Veasy's foundational rule `need = 0.5 + 0.3 * words` is preserved as an inviolable gate (`HOLDS = ("read",)`). Background motion behind active reading text must remain at low contrast ($< 10\%$ opacity ink) to prevent saccadic disruption.

7. **The 1–2 Second Mobile Attention Decision (Meta / TikTok / Shorts Retention Research)**
   - *URL:* https://www.facebook.com/business/news/insights/capturing-attention-in-feed-and-stories
   - *Core insight:* Users on vertical feeds swipe within 400–1200ms if no clear visual thesis or legible text is visible. Frame 0 ($t=0$) must be fully rendered and legible.
   - *What Veasy takes:* The `Opening` context in Remotion: frame 0 renders hook headlines with $100\%$ opacity and settled layouts, using at most a few pixels of settle offset rather than animating in from empty space.

8. **Microsoft Fluent Design System (Motion & Connected Animation)**
   - *URL:* https://fluent2.microsoft.design/motion
   - *Core insight:* Coordinated element cascades: hierarchical staggering where parent containers establish the movement vector and children cascade along that vector with decaying delay.
   - *What Veasy takes:* Stagger formulas in `In` and `FitText`: headline lines cascade smoothly ($t_i = t_{base} + i \cdot \text{stagger}$), maintaining directional alignment with the director's current.

---

### B. Kinetic Typography & Georgian Mkhedruli Dynamics

9. **Georgian Typography & Mkhedruli Script Structural Analysis** (Akaki Shanidze; FiraGO Typographic Metrics)
   - *URL:* https://bidi.org.ge/firago-specimen
   - *Core insight:* Mkhedruli is unicameral (no uppercase letters or small caps). Visual hierarchy cannot rely on all-caps emphasis. Georgian words are agglutinative with prefixes and case suffixes, producing higher average word lengths (7–10 characters vs 4–5 in English).
   - *What Veasy takes:* Kinetic typography in Georgian must rely on weight contrast (400 vs 700), size stepping, inverted ink blocks, and inline line/word reveals. Text bounding boxes must account for generous descenders/ascenders (ქ, ყ, ფ, შ, წ, ჯ).

10. **Saul Bass Geometric Title Sequence Typography**
    - *URL:* https://www.artofthetitle.com/designer/saul-bass/
    - *Core insight:* Striking typographic clarity through pure geometry: sharp rectangular cutouts, moving lines as text anchors, and unified color palette (stark contrast).
    - *What Veasy takes:* Hook layout variations: `split` (asymmetric ink rail with docked lead) and `badge` (solid ink pill wrapping line 0), utilizing pure geometry rather than decorative gradients or dropshadows.

11. **Dan Perri Film Title Choreography**
    - *URL:* https://www.artofthetitle.com/designer/dan-perri/
    - *Core insight:* Controlled scale progression and depth planes using purely 2D transforms and spatial framing.
    - *What Veasy takes:* `bracket` and `rail` hook layouts that enclose typography in architectural ink strokes, plus the `scale` and `drift` entrances that convey cinematic weight without WebGL overhead.

12. **Broadcast & News Channel Motion Design (BBC News, Bloomberg Quicktake, CNN International)**
    - *URL:* https://www.bbc.co.uk/gel/guidelines/motion
    - *Core insight:* Information-dense news graphics demand disciplined lower-third timing, clear kicker badges ("LIVE", "BREAKING"), and consistent directional movement across tickers and straps.
    - *What Veasy takes:* Kicker and rubric chips remain rock-solid; transitions use clean wipes, shutter cuts, and meter bars rather than playful cartoons, honoring news integrity.

13. **Music Lyric & Kinetic Type Video Systems** (Japanese Kinetic Typography & Motion Graphics)
    - *URL:* https://www.youtube.com/results?search_query=kinetic+typography+analysis
    - *Core insight:* Word-by-word reveal along the vocal track; words arrive exactly when spoken, keeping eye focus tightly synchronized with auditory reception.
    - *What Veasy takes:* Word-by-word reveal capability for Georgian headlines and key phrases, mapping beat cues directly to character/word spans with zero layout jump.

14. **Vox & Axios Visual Journalism Style Guides**
    - *URL:* https://www.vox.com/video
    - *Core insight:* Text is emphasized through highlighter wipes, boxed phrases, and stark contrast bars that reveal on key spoken assertions.
    - *What Veasy takes:* Voice-synced `em` marks and mask reveals: an ink block sweeps behind the phrase while maintaining minimum 7:1 contrast.

15. **Swiss Style Typography in Digital Motion** (Josef Müller-Brockmann / Emil Ruder)
    - *URL:* https://www.thinkingwithtype.com/
    - *Core insight:* Asymmetric grid structure, dynamic whitespace, and strict typographic hierarchy without arbitrary decoration.
    - *What Veasy takes:* New hook layouts and background motifs: `split` hook with an architectural vertical rail, `crosses` and `mesh` motifs based on mathematical Swiss modular grids.

---

### C. Toolkits, Animation Engines & Runtimes

16. **Remotion Core Engine (v4.0.539)**
    - *URL:* https://www.remotion.dev/docs/
    - *Core insight:* Frame-exact, deterministic React rendering. All animations are pure mathematical functions of `useCurrentFrame()`.
    - *What Veasy takes:* Zero async operations during render; deterministic clip-paths, transforms, and spring math ensure byte-identical golden frame output.

17. **Remotion Transitions Package (`@remotion/transitions`)**
    - *URL:* https://www.remotion.dev/docs/transitions
    - *Core insight:* Presentation components for slide, wipe, flip, and fade. However, `TransitionSeries` shortens the track duration and breaks external voice timeline synchronization.
    - *What Veasy takes:* We avoid `TransitionSeries` and instead build deterministic scene-motion overlays in `sceneMotion` and `<Cut />`, preserving fixed timeline anchors while achieving diverse visual cuts.

18. **Remotion Paths & Shapes Packages (`@remotion/paths`, `@remotion/shapes`)**
    - *URL:* https://www.remotion.dev/docs/paths
    - *Core insight:* MIT-licensed SVG path calculation and geometric primitives (`evolvePath`, polygon, circle).
    - *What Veasy takes:* SVG path calculations for geometric motif generation and stroke evolution.

19. **Remotion Noise (`@remotion/noise`)**
    - *URL:* https://www.remotion.dev/docs/noise
    - *Core insight:* MIT-licensed deterministic simplex/Perlin noise functions based on numeric coordinates and seed.
    - *What Veasy takes:* Texture drift and subtle wave offsets without loading external textures or assets.

20. **Motion Canvas (MIT)**
    - *URL:* https://motioncanvas.io/
    - *Core insight:* Programmatic vector animation using generator functions, tweening, and declarative spatial layouts.
    - *What Veasy takes:* Procedural layout concepts: computing exact bounding boxes and layout constraints before initiating entrance motion.

21. **Revideo (MIT)**
    - *URL:* https://revideo.dev/
    - *Core insight:* Lightweight headless video engine built on HTML/TS canvas.
    - *What Veasy takes:* Clean separation of audio cue triggers from visual layout nodes.

22. **Manim Community Edition (MIT)**
    - *URL:* https://www.manim.community/
    - *Core insight:* 3b1b's programmatic mathematical animation: dynamic transforms between shapes, line drawing, and coordinate grid evolutions.
    - *What Veasy takes:* Coordinate grid drift and geometric reveal techniques for background motifs (`mesh`, `waves`, `crosses`).

23. **Theatre.js (Apache-2.0)**
    - *URL:* https://www.theatrejs.com/
    - *Core insight:* Separation of high-level animation property curves from DOM presentation.
    - *What Veasy takes:* Parameterized easing curves (`easeOutCubic`, `spring`, `smoothstep`) reused across multiple component primitives.

24. **GreenSock GSAP (GSAP Standard License)**
    - *URL:* https://gsap.com/
    - *Core insight:* Advanced stagger orchestration (`stagger: { amount, from: "center", ease: "power2.out" }`).
    - *What Veasy takes:* Stagger math algorithms for multi-element reveals in React/Remotion without requiring external runtime dependencies.

25. **Rive Vector Animation Runtime**
    - *URL:* https://rive.app/
    - *Core insight:* State machine-driven vector animation with explicit inputs and deterministic state evaluation.
    - *What Veasy takes:* State-based entrance dispatching: component selects entrance style based on `Opening` state vs mid-video sequence.

26. **W3C Web Animations API & CSS Transitions Level 2**
    - *URL:* https://www.w3.org/TR/css-transitions-2/
    - *Core insight:* Hardware-accelerated CSS properties (`transform: translate3d/scale`, `clip-path: inset/polygon/circle`, `opacity`) execute with zero layout thrashing.
    - *What Veasy takes:* All Remotion entrances, transitions, and reveals compile down to pure CSS transforms, clip-paths, and opacities, ensuring 60fps render speed and zero bundle bloat.

---

## 2. Licensing Compliance Matrix

| Asset / Library / Concept | License | Commercial Reuse | Status in Veasy | Notes |
|---|---|---|---|---|
| **Remotion Core & Packages** (4.0.539) | Remotion License | Yes (Free $\le 3$ people) | Approved | Owner decision in ROADMAP.md § Decisions |
| **Motion Canvas** | MIT | Yes | Studied | Concepts only; no code vendored |
| **Revideo** | MIT | Yes | Studied | Concepts only |
| **ManimCE** | MIT | Yes | Studied | Mathematical ideas |
| **Theatre.js** | Apache-2.0 | Yes | Studied | Timeline separation |
| **Lucide Icons** | ISC | Yes | Vendored in assets/icons | Built via tools/build_icons.py |
| **FiraGO Font** | SIL OFL 1.1 | Yes | Vendored in brands/ | Primary Georgian font family |
| **OpenMontage** | AGPL-3.0 | Restricted | **Excluded** | AGPL-3.0 strictly forbidden in Veasy engine |
| **Pure CSS/SVG Transitions** | Public Domain / CC0 | Yes | Shipped | Authored in remotion/src/ |

---

## 3. Analysis of Existing Motion Architecture in Veasy

### A. Current Options Pools (`tt_shorts/variety.py`)
- `hook`: `("stack", "lead", "blocks", "underline")` (4 options)
- `motif`: `("grid", "diagonal", "dots", "rules", "plain", "icons")` (6 options)
- `enter`: `("rise", "slide", "reveal", "scale")` (4 options)
- `transition`:
  - `editorial`: `("line", "wipe", "dot", "slide", "meter")`
  - `kinetic`: `("panel", "push", "wipe", "cut", "meter")`
  - `cards`: `("line", "slide", "dot", "wipe")`

### B. Current Limitations
1. **Hook layouts**: Only 4 variations. After 10 videos of a single brand, repetition is noticeable.
2. **Motifs**: 6 options, but mostly simple lines and dots. Lacks modern geometric micro-patterns (crosses, diamond mesh, subtle waves).
3. **Entrances**: All 4 move upward, from left, or scale. No downward drop, no horizontal expand, no subtle directional drift, no 3D-perspective flip.
4. **Transitions**: Only 5 unique transition mechanics. No shutter blinds, no split masks, no corner sweeps, no centered iris, no pure cinematic fades.
5. **Director Personalities**: 8 directors have numbers in JSON, but several share identical damping (20) or stiffness (120/170), lacking sharp differentiation in feel.
6. **Motion Rules**: `motion_rules.py` only warns on `read`, `still`, `kinds`, `pingpong`, `repeat`. It lacks checks for "too many simultaneous moves", "motion behind text being read", and "cuts faster than the voice".

---

## 4. Ranked Backlog (Top-Down Implementation)

| Rank | Component | Scope / Description | Value | Effort |
|:---:|---|---|:---:|:---:|
| **1** | **New Background Motifs** | Add `crosses`, `mesh`, `waves`, `hash` to `OPTIONS["motif"]` in `variety.py` & `Background` in `NewsShort.tsx` | High | S |
| **2** | **New Hook Layouts** | Add `split`, `badge`, `bracket`, `rail` to `OPTIONS["hook"]` in `variety.py` & `Hook` in `scenes/index.tsx` | Very High | M |
| **3** | **New Entrances** | Add `drop`, `expand`, `drift`, `flip` to `OPTIONS["enter"]` in `variety.py` & `In` in `ui.tsx` | Very High | M |
| **4** | **New Transitions** | Add `fade`, `shutter`, `split`, `corner`, `iris`, `blind` spread across `TRANSITIONS` in `variety.py`, `formats.py`, `props.py`, `types.ts`, and `NewsShort.tsx` | Very High | M |
| **5** | **Georgian Kinetic Typography** | Word-by-word reveal component (`WordReveal`) and mask reveals for `em` / headline words in `ui.tsx` and `scenes/index.tsx` | High | M |
| **6** | **Director Personalities** | Differentiate damping (14–26), stiffness (110–260), enter_frames (7–15), stagger (3–6), and current for all 8 directors; update `skills/directors/SKILL.md` | High | S |
| **7** | **New Motion Rules** | Add `toomany`, `background`, `pacing` warnings to `motion_rules.py` with cases in `tests/test_motion_rules.py` | High | S |
| **8** | **Motion SFX Cues** | Add sound cues in `sfx.py` for new transitions (`shutter`, `split`, `iris`, `blind`), off by default | Medium | S |
| **9** | **Options & Skills Sync** | Update `engine.options()`, `formats.py`, `veasy:formats` skill, verify `options_for` & `choose()` | High | S |
| **10** | **Selftest & Verification** | Golden stills audit, test suite pass, probe check on all looks, result report | Critical | M |

---

## 5. Owner Decisions (Recorded Policy)

1. **Brand Pack Integrity:** All new motifs, hook borders, brackets, and transition panels use exclusively `INK`, `CANVAS`, `LINE`, and `GRID` tokens. No client name, client color, or accent color is ever applied to text or non-standard areas. Accent color remains strictly reserved for the live dot, button active state, or progress indicator.
2. **Safe Zone Invariance:** Scene text ends at $y=1380$; captions at $y=1552$; below $y=1100$ no text extends right of $x=940$. All new hook layouts must verify under the layout probe.
3. **News Rules Non-Relaxation:** News rules only ever tighten. No opinion scenes, no arbitrary writer styling.
4. **Licensing Boundary:** No AGPL code (OpenMontage); no external network asset downloads. All motion is deterministic TypeScript/React and pure Python.
5. **Fingerprint Weight Stability:** The 7 variety fingerprint fields (`director`, `scenes`, `hook`, `motif`, `enter`, `transition`, `music`) are preserved. Expanding options within fields exponentially grows diversity without breaking fingerprint distance calculations.
