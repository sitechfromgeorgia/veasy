# Veasy Ink Brush Engine: Physical Materials, Vector Distance Fields & Hand-Painted Realism

> **The One-Line Interface Command**:
> ```bash
> node plates/run.mjs ink --spec spec.json --seconds 6 --seed 1 --out out/plates/ink_demo
> ```
> **What the user or agent gets back**:
> `plate.mp4` (deterministic tone-only H.264 video, grey on black), `poster.png` (exact middle frame still), `plate.json` (runtime cost in ms/frame, manifest and frame hash), and `anchors.json` (focal dot coordinate tracks for the DOM brand dot).

---

## 1. Executive Summary & Design Contract

Veasy's drawings currently appear as flat SVG path-dash trimming in Remotion (`remotion/src/scenes/more.tsx`). While mathematically functional, vector trimming looks mechanically animated by software rather than drawn by a human hand.

The Ink Brush plate (`plates/ink/`) introduces physical media simulation to Veasy without modifying the core rendering architecture or adding proprietary runtime overhead:
- **Tone-Only Plate**: Rendered in luminance $[0.0, 1.0]$ on black, converted to greyscale by `plates/run.mjs`. The video engine maps black to the brand pack canvas and white to its ink.
- **Pure Determinism**: Zero unseeded randomness (`lib/seeded.mjs` mulberry32 only), zero clock reads (`Date.now()`), frame $t$ is a pure mathematical function of $(t, \text{spec}, \text{seed})$.
- **Six Tactile Materials**:
  1. `woodcut`: Relief woodblock printing with grain anisotropy, chisel chatter, ink squash at borders, and brayer stippling.
  2. `ink_wash`: Porous paper capillary dispersion (Sumi-e / Lavis), Deegan coffee-ring edge darkening, and feibai dry-brush bristle splitting.
  3. `blueprint`: Sir John Herschel (1842) cyanotype photochemistry, crisp white negative lines with soft contact penumbra on exposed Prussian blue vellum.
  4. `halftone`: Industrial Ben-Day AM screening at $45^\circ$, Murray-Davies dot area laws, and Yule-Nielsen optical dot gain.
  5. `chalk`: Dry mineral pigment friction against paper/slate microscopic asperity heightfield, void skipping, and powdery dust halos.
  6. `pencil_hatch`: Hexagonal graphite crystal shear, non-linear opacity layering, and Praun Tonal Art Map (TAM) nested cross-hatching.
- **Physical Line Boil on Twos**: In accordance with traditional hand animation (Williams 2001), line jitter steps at 15 fps on 30 fps playback, avoiding sterile mechanical stability while preventing frantic 30 fps strobe noise.
- **Reveals & Transitions**:
  - `stroke`: Progressive reveal following sanitized SVG element order and `--d` delay tags.
  - `bleed`: Lucas-Washburn ($L \propto \sqrt{t}$) capillary diffusion settling into paper fibers.
  - `scrape`: Subtractive sgraffito gouge exposing white paper substrate through wet ink.
  - `print_through`: Kubelka-Munk show-through of diffuse reverse-side ink.
  - `flood`: Organic fluid ink wavefront expanding to fill the frame, strictly validated against ITU-R BT.1702-3 via `tt_shorts/flash.py`.

---

## 2. Research Foundations: 28 Academic & Technical Sources

### Part I: Non-Photorealistic Rendering (NPR) & Vector Distance Fields

#### 1. Hertzmann (1998) — "Painterly Rendering with Curved Brush Strokes"
* **Citation**: Hertzmann, A. (1998). "Painterly Rendering with Curved Brush Strokes." *Proceedings of SIGGRAPH '98*, pp. 453–460. DOI: [10.1145/280814.280951](https://doi.org/10.1145/280814.280951).
* **What it teaches Veasy**: Human brushwork curves along vector gradient normal fields with progressive coarse-to-fine stroke application. Brush tips taper dynamically at start and end rather than maintaining rigid mechanical width.
* **Algorithmic / Shader Translation**: Quadratic Bézier envelope modulation $w(u) = w_0 \cdot (0.6 + 0.4 \sin(\pi u))$ with seeded lateral stroke jitter along the curve tangent.
* **Commercial License**: Academic publication; clean-room procedural GLSL implementation is unencumbered.

#### 2. Praun et al. (2001) — "Real-Time Hatching" (Tonal Art Maps)
* **Citation**: Praun, E., Hoppe, H., Webb, M., and Finkelstein, A. (2001). "Real-Time Hatching." *Proceedings of SIGGRAPH '01*, pp. 581–586. DOI: [10.1145/383259.383328](https://doi.org/10.1145/383259.383328).
* **What it teaches Veasy**: Tonal Art Maps (TAMs) maintain nested stroke subsets ($T_i \subset T_{i+1}$) across tone thresholds, preventing popping artifacts during continuous shading changes.
* **Algorithmic / Shader Translation**: Nested priority hashing for parallel cross-hatching where darker tones introduce additional strokes without shifting existing lines.
* **Commercial License**: Academic publication; algorithm is public scientific domain.

#### 3. Curtis, Anderson, Seims, Fleischer, Salesin (1997) — "Computer-Generated Watercolor"
* **Citation**: Curtis, C. J. et al. (1997). "Computer-Generated Watercolor." *Proceedings of SIGGRAPH '97*, pp. 421–430. DOI: [10.1145/258734.258896](https://doi.org/10.1145/258734.258896).
* **What it teaches Veasy**: Physical fluid transfer across paper involves shallow water flow, pigment suspension, edge meniscus accumulation, and granulation into paper valleys.
* **Algorithmic / Shader Translation**: Boundary distance power-law profile producing dark edge rings and pigment granulation proportional to paper tooth depth.
* **Commercial License**: Academic publication; physical modeling principles unencumbered.

#### 4. Winkenbach & Salesin (1994) — "Computer-Generated Pen-and-Ink Illustration"
* **Citation**: Winkenbach, G. and Salesin, D. H. (1994). "Computer-Generated Pen-and-Ink Illustration." *Proceedings of SIGGRAPH '94*, pp. 91–100. DOI: [10.1145/192161.192184](https://doi.org/10.1145/192161.192184).
* **What it teaches Veasy**: Formalizes prioritized stroke textures and "indication" (concentrating high-detail marks around focal points while allowing background or peripheral context to fade gracefully).
* **Algorithmic / Shader Translation**: Distance-to-focal-center weighting ($p_{\text{focus}}$) modulating stroke density for `MUTED` and `LINE` secondary drawing elements.
* **Commercial License**: Academic publication; clean-room implementation free for commercial use.

#### 5. Winkenbach & Salesin (1996) — "Rendering Freeform Surfaces with Pen-and-Ink Illustration"
* **Citation**: Winkenbach, G. and Salesin, D. H. (1996). "Rendering Freeform Surfaces with Pen-and-Ink Illustration." *Proceedings of SIGGRAPH '96*, pp. 469–476. DOI: [10.1145/237170.237287](https://doi.org/10.1145/237170.237287).
* **What it teaches Veasy**: Governs stroke alignment along principal curve tangents and clean stroke clipping within element silhouette boundaries.
* **Algorithmic / Shader Translation**: Local tangent vector coordinate rotation aligning procedural hatching with 2D path orientation.
* **Commercial License**: Academic publication; public scientific domain.

#### 6. Salisbury et al. (1997) — "Orientable Textures for Pen-and-Ink Illustration"
* **Citation**: Salisbury, M. et al. (1997). "Orientable Textures for Pen-and-Ink Illustration." *Proceedings of SIGGRAPH '97*, pp. 401–406. DOI: [10.1145/258734.258890](https://doi.org/10.1145/258734.258890).
* **What it teaches Veasy**: Decouples tone control from stroke orientation by mapping 2D direction vector fields onto procedural stroke generators.
* **Algorithmic / Shader Translation**: Direction-field rotation matrix applied to UV coordinates prior to evaluating periodic line profiles.
* **Commercial License**: Academic publication; unencumbered.

#### 7. Deegan et al. (1997) — "Capillary flow as the cause of ring stains from dried liquid drops"
* **Citation**: Deegan, R. D. et al. (1997). "Capillary flow as the cause of ring stains from dried liquid drops." *Nature*, 389, pp. 827–829. DOI: [10.1038/39827](https://doi.org/10.1038/39827).
* **What it teaches Veasy**: Establishes the physical law governing the coffee-ring effect: drying drops with pinned contact lines drive outward capillary replenishment, yielding edge pigment density $J(r) \propto (R - r)^{-\lambda}$.
* **Algorithmic / Shader Translation**: Power-law edge concentration boost $C(d) = 1.0 + 1.8(1.0 - d/R)^{0.45}$ applied to stroke perimeter.
* **Commercial License**: Natural physical law; public domain.

#### 8. Green (2007) — "Improved Alpha-Tested Magnification for Vector Textures" (Valve SDF)
* **Citation**: Green, C. (2007). "Improved Alpha-Tested Magnification for Vector Textures." *ACM SIGGRAPH 2007 Courses*, pp. 9–18. DOI: [10.1145/1281504.1281510](https://doi.org/10.1145/1281504.1281510).
* **What it teaches Veasy**: Signed Distance Fields (SDFs) enable resolution-independent vector rendering in fragment shaders with screen-space antialiasing via `fwidth()`.
* **Algorithmic / Shader Translation**: `smoothstep(threshold - fwidth(d), threshold + fwidth(d), d)` on signed distance fields.
* **Commercial License**: Published technical paper; standard industry practice.

#### 9. Chlumský (2015) — "Multi-Channel Signed Distance Field Generator" (MSDF)
* **Citation**: Chlumský, V. (2015). "Multi-channel signed distance field generator." Master's Thesis, Czech Technical University in Prague. [github.com/Chlumsky/msdfgen](https://github.com/Chlumsky/msdfgen).
* **What it teaches Veasy**: Multi-channel distance fields (RGB) preserve sharp geometric corners and architectural vertices under high zoom using the median operator.
* **Algorithmic / Shader Translation**: $d = \max(\min(R, G), \min(\max(R, G), B))$ for architectural and technical vector shapes.
* **Commercial License**: MIT License.

#### 10. Williams (2001) — "The Animator's Survival Kit" (Line Boil on Twos)
* **Citation**: Williams, R. (2001). *The Animator's Survival Kit*. London: Faber & Faber. ISBN: 978-0571202287.
* **What it teaches Veasy**: Traditional line boil operates on *twos* (12 or 15 fps on a 24 or 30 fps timeline). Stepping frames creates authentic hand-drawn warmth without rapid 30 fps buzzing.
* **Algorithmic / Shader Translation**: Frame-time quantization $t_{\text{boil}} = \lfloor t \cdot 15 \rfloor / 15$ driving deterministic spatial noise offsets.
* **Commercial License**: Traditional craft principle; unencumbered.

---

### Part II: Physical Material Mechanics, Substrates & Optics

#### 11. Mizuno, Okada, Toriyama (1998) & Way & Shih (2001) — Woodcut Relief Mechanics
* **Citations**:
  - Mizuno, S. et al. (1998). "Virtual sculpting and printmaking for woodblock printing." *The Visual Computer*, 14, pp. 386–398.
  - Way, D.-L. and Shih, Z.-C. (2001). "The synthesis of woodblock print and woodcut illustration." *Computer Graphics Forum*, 20(3), pp. 281–290.
* **What it teaches Veasy**: Relief printmaking exhibits chisel chatter along cuts, wood grain fibrous porosity, ink squashing outward to stroke borders, and brayer stippling.
* **Algorithmic / Shader Translation**: Sinusoidal chisel scalloping on edge distance + anisotropic wood grain noise + edge ink squash ridge.
* **Commercial License**: Academic publications; clean-room implementation.

#### 12. Ostromoukhov (1999) — "Digital Facial Engraving"
* **Citation**: Ostromoukhov, V. (1999). "Digital Facial Engraving." *Proceedings of SIGGRAPH '99*, pp. 417–424. DOI: [10.1145/311535.311603](https://doi.org/10.1145/311535.311603).
* **What it teaches Veasy**: Banknote and copperplate engraving maps continuous tone to line width and frequency modulation while maintaining constant overall ink density.
* **Algorithmic / Shader Translation**: Modulating line half-width $w = (1.0 - \text{tone}) \cdot 0.45$ along structured engraving curves.
* **Commercial License**: Academic publication; unencumbered.

#### 13. Sir John Herschel (1842) & Ware (1999) — Blueprint / Cyanotype Photochemistry
* **Citations**:
  - Herschel, Sir J. F. W. (1842). "On the Action of the Rays of the Solar Spectrum..." *Philosophical Transactions of the Royal Society of London*, 132, pp. 181–214.
  - Ware, M. (1999). *Cyanotype*. London: Science Museum. ISBN: 978-1900747073.
* **What it teaches Veasy**: Cyanotype contact printing produces crisp negative white lines where vellum drafting linen blocks UV exposure, leaving insoluble Prussian blue on exposed areas with subtle contact penumbra.
* **Algorithmic / Shader Translation**: Inverting the stroke mask (white strokes, dark ground) with a $0.0035$ UV scattering penumbra and vellum linen fiber tooth.
* **Commercial License**: Historic 1842 scientific treatise; public domain.

#### 14. Benjamin Day (1879) & Murray (1936) / Yule-Nielsen (1951) — Halftone & Optical Dot Gain
* **Citations**:
  - Day, B. (1879). "Improvement in Printing-Films." U.S. Patent No. 214,393.
  - Murray, A. (1936). "Monochrome reproduction in photo-engraving." *J. Franklin Inst.*, 221, pp. 721–744.
  - Yule, J. A. C. and Nielsen, W. J. (1951). "The Penetration of Light into Paper..." *TAGA Proceedings*, 3, pp. 65–76.
* **What it teaches Veasy**: Halftoning discretizes continuous tone into circular dot grids at a $45^\circ$ screen angle. Optical dot gain expands dot coverage via photon scattering in paper fibers.
* **Algorithmic / Shader Translation**: $45^\circ$ rotated UV grid with Yule-Nielsen non-linear dot expansion $a_{\text{optical}} = \text{tone}^{1/n}$ ($n \approx 1.8$).
* **Commercial License**: Patent expired 1896; scientific models public domain.

#### 15. Sousa & Buchanan (1999, 2000) — Computer-Generated Graphite Pencil & Paper Asperity
* **Citations**:
  - Sousa, M. C. and Buchanan, J. W. (1999). "Computer-Generated Graphite Pencil Materials." *Computer Graphics Forum*, 18(3), pp. 195–207.
  - Sousa, M. C. and Buchanan, J. W. (2000). "Observational Models of Graphite Pencil Materials." *Proceedings of NPAR '00*, pp. 27–34.
* **What it teaches Veasy**: Paper asperity heightfield $h(x, y)$ causes dry pigment to deposit only on peaks exceeding a pressure contact threshold, leaving valleys unpainted (void skipping).
* **Algorithmic / Shader Translation**: Microscopic procedural heightfield thresholding: pigment adheres when $h(uv) \ge 1.0 - P \cdot (0.5 + 0.5 \cdot \text{softness})$.
* **Commercial License**: Academic publications; unencumbered.

#### 16. AlMeraj, Kaplan, Asente (2013) — Pencil Hatching with Texture Guidance
* **Citation**: AlMeraj, Z., Kaplan, C. S., and Asente, P. (2013). "Pencil Hatching with Texture Guidance." *Computers & Graphics*, 37(6), pp. 856–864. DOI: [10.1016/j.cag.2013.05.011](https://doi.org/10.1016/j.cag.2013.05.011).
* **What it teaches Veasy**: Multi-layer cross-hatching accumulates non-linearly $O_{\text{total}} = 1 - \prod(1 - O_i)$ with tapered pressure from tip to tail.
* **Algorithmic / Shader Translation**: Non-linear stroke layer accumulation and quadratic stroke pressure envelopes.
* **Commercial License**: Academic publication; free for commercial software.

#### 17. Chu & Tai (2005) — "MoXi: Real-Time Ink Dispersion in Absorbent Paper"
* **Citation**: Chu, N. S.-H. and Tai, C.-L. (2005). "MoXi: Real-Time Ink Dispersion in Absorbent Paper." *ACM TOG (SIGGRAPH '05)*, 24(3), pp. 504–511. DOI: [10.1145/1073204.1073221](https://doi.org/10.1145/1073204.1073221).
* **What it teaches Veasy**: Asian ink wash exhibits anisotropic fiber diffusion in Xuan paper and feibai (dry brush bristle splitting) under rapid stroke velocity.
* **Algorithmic / Shader Translation**: High-frequency bristle hair striation mask triggered when local dryness/velocity exceeds moisture threshold.
* **Commercial License**: Academic publication; physical modeling principles unencumbered.

#### 18. Guo & Kunii (1991) — "'N-Pencil': A Model for Computer Generated Sumi-e Painting"
* **Citation**: Guo, B. and Kunii, T. L. (1991). "'N-Pencil': A model for computer generated sumi-e painting." *The Visual Computer*, 7, pp. 317–332. DOI: [10.1007/BF01905697](https://doi.org/10.1007/BF01905697).
* **What it teaches Veasy**: Dynamic brush footprint width expands with pressure and depletes as a function of total arc length.
* **Algorithmic / Shader Translation**: Stroke radius tapering governed by cumulative path distance $R(s) = R_0 \cdot (1 - \lambda s)$.
* **Commercial License**: Academic publication; public scientific domain.

#### 19. Perlin (1985) & Worley (1996) — Procedural Substrates & Mineral Asperities
* **Citations**:
  - Perlin, K. (1985). "An Image Synthesizer." *ACM SIGGRAPH Computer Graphics*, 19(3), pp. 287–296.
  - Worley, S. (1996). "A Cellular Texture Basis Function." *Proceedings of SIGGRAPH '96*, pp. 291–294.
* **What it teaches Veasy**: Procedural hash-based Simplex and Worley noise generate infinite non-repeating paper tooth and slate textures without image asset downloads or disk bloat.
* **Algorithmic / Shader Translation**: Analytic 2D hash/simplex noise functions executed directly in the fragment shader.
* **Commercial License**: Public domain; original 3D Perlin patent expired 2021.

#### 20. van Wijk (1991) — "Spot Noise: Texture Synthesis with Procedural Noise"
* **Citation**: van Wijk, J. J. (1991). "Spot Noise: Texture Synthesis with Procedural Noise." *ACM SIGGRAPH Computer Graphics*, 25(4), pp. 265–272. DOI: [10.1145/127719.122751](https://doi.org/10.1145/127719.122751).
* **What it teaches Veasy**: Directional filtering of stochastic noise kernels models anisotropic wood fibers and drafting linen weaves.
* **Algorithmic / Shader Translation**: Anisotropic coordinate scaling along directional axes in procedural noise generators.
* **Commercial License**: Academic publication; unencumbered.

---

### Part III: Vector to SDF & Stroke Reconstruction

#### 21. Loop & Blinn (2005) — "Resolution Independent Curve Rendering using Programmable Graphics Hardware"
* **Citation**: Loop, C. and Blinn, J. (2005). "Resolution Independent Curve Rendering..." *ACM TOG (SIGGRAPH '05)*, 24(3), pp. 1000–1009. DOI: [10.1145/1073204.1073303](https://doi.org/10.1145/1073204.1073303).
* **What it teaches Veasy**: Quadratic Bézier curves can be evaluated inside pixel shaders via algebraic invariants without polygon tessellation.
* **Algorithmic / Shader Translation**: Direct evaluation of quadratic curve parameter distance in fragment routines.
* **Commercial License**: Microsoft Research paper; mathematical geometry unencumbered.

#### 22. Bærentzen & Aanæs (2005) — "Signed Distance Computation Using the Angle Weighted Pseudonormal"
* **Citation**: Bærentzen, J. A. and Aanæs, H. (2005). "Signed Distance Computation Using the Angle Weighted Pseudonormal." *IEEE TVCG*, 11(3), pp. 243–253. DOI: [10.1109/TVCG.2005.49](https://doi.org/10.1109/TVCG.2005.49).
* **What it teaches Veasy**: Avoids sign-flip tearing at acute vertices and polygon corners in 2D distance fields using angle-weighted pseudonormals.
* **Algorithmic / Shader Translation**: Computing unambiguous corner distance sign based on incident edge angles.
* **Commercial License**: Academic publication; widely implemented in open source (CGAL).

#### 23. Nehab & Hoppe (2008) — "Random-Access Rendering of General Vector Graphics"
* **Citation**: Nehab, D. and Hoppe, H. (2008). "Random-Access Rendering of General Vector Graphics." *ACM TOG (SIGGRAPH Asia '08)*, 27(5), Art. 135. DOI: [10.1145/1409060.1409088](https://doi.org/10.1145/1409060.1409088).
* **What it teaches Veasy**: Spatial binning of vector primitives into coarse 2D grid cells accelerates fragment evaluation by testing only local segments.
* **Algorithmic / Shader Translation**: 2D grid indexing for vector stroke evaluation on SwiftShader CPU fallback.
* **Commercial License**: Academic publication; unencumbered.

#### 24. Kilgard & Bolz (2012) — "GPU-accelerated Path Rendering" (NVPR)
* **Citation**: Kilgard, M. J. and Bolz, J. (2012). "GPU-accelerated Path Rendering." *ACM TOG (SIGGRAPH '12)*, 31(6), Art. 152. DOI: [10.1145/2366145.2366171](https://doi.org/10.1145/2366145.2366171).
* **What it teaches Veasy**: Stencil-then-cover path rendering decomposes complex paths into fill/stroke coverage passes followed by material shading.
* **Algorithmic / Shader Translation**: Two-pass architecture: 2D Canvas/WebGL stroke coverage buffer + full-screen material shader.
* **Commercial License**: Academic paper; standard WebGL implementation without proprietary extensions.

---

### Part IV: Reveal Dynamics, Capillary Transitions & Flash Safety

#### 25. Lucas (1918) & Washburn (1921) — Capillary Front Dynamics ($L \propto \sqrt{t}$)
* **Citations**:
  - Lucas, R. (1918). "Ueber das Zeitgesetz des kapillaren Aufstiegs..." *Kolloid-Zeitschrift*, 23, pp. 15–22.
  - Washburn, E. W. (1921). "The Dynamics of Capillary Flow." *Physical Review*, 17(3), pp. 273–283.
* **What it teaches Veasy**: Liquid absorption into porous paper slows down with time following a square-root front expansion $L(t) \propto \sigma \sqrt{\Delta t}$.
* **Algorithmic / Shader Translation**: Bleed edge expansion $d_{\text{bleed}}(t) = k_{\text{bleed}} \sqrt{\max(0, t - t_{\text{stroke}})}$ giving natural settling deceleration.
* **Commercial License**: 1921 physics; public domain.

#### 26. Kubelka & Munk (1931) — Print-Through & Paper Translucency
* **Citation**: Kubelka, P. and Munk, F. (1931). "Ein Beitrag zur Optik der Farbanstriche." *Zeitschrift für Technische Physik*, 12, pp. 593–601.
* **What it teaches Veasy**: Two-flux radiative transfer explains print-through (diffuse show-through of ink on the reverse side of thin paper).
* **Algorithmic / Shader Translation**: Diffuse blurred mirror stroke rendered at $\le 10\%$ opacity preceding front-side stroke arrival.
* **Commercial License**: Foundational 1931 optics; public domain.

#### 27. Baxter et al. (2001) — "dAb: Interactive Haptic Painting with 3D Virtual Brushes" (Sgraffito / Scrape)
* **Citation**: Baxter, W. et al. (2001). "dAb: Interactive Haptic Painting with 3D Virtual Brushes." *Proceedings of SIGGRAPH '01*, pp. 461–468. DOI: [10.1145/383259.383313](https://doi.org/10.1145/383259.383313).
* **What it teaches Veasy**: Sgraffito and woodcut scraping remove surface ink to expose the substrate underneath, creating rim shavings along chisel borders.
* **Algorithmic / Shader Translation**: Subtractive gouge mask with procedural wood shaving beads along the furrow edge.
* **Commercial License**: Academic publication; unencumbered.

#### 28. ITU-R BT.1702-3 (2019/2023) — Broadcast Photosensitive Seizure Safety
* **Citation**: ITU-R. (2019/2023). "Recommendation ITU-R BT.1702-3: Guidance for the mitigation of the risk of photosensitive epileptic seizures." Geneva: International Telecommunication Union.
* **What it teaches Veasy**: Video frames must not strobe ($\le 3$ flashes/second, area $\le 25\%$ for transitions $\ge 20\text{ cd/m}^2$). Enforced directly by `tt_shorts/flash.py`.
* **Algorithmic / Shader Translation**: Monotonic ink flood progression ($\partial L/\partial t \le 0$ everywhere), guaranteeing zero flash violations.
* **Commercial License**: International UN treaty standard; public regulatory specification.

---

## 3. Commercial Licensing & IP Risk Assessment

Every mathematical technique and algorithm proposed for Veasy has been evaluated under strict commercial readiness standards (zero GPL/AGPL, zero non-commercial NC restrictions, zero unlicensed Shadertoy code):

| # | Source Reference | Underlying Concept | Legal / License Status | Veasy Implementation Mechanism | Risk Level |
|---|---|---|---|---|---|
| 1 | Hertzmann (1998) | Curved painterly strokes | Academic publication (ACM) | Clean-room GLSL math implementation | **Zero** (Safe) |
| 2 | Praun et al. (2001) | Tonal Art Maps (TAM) | Academic publication (ACM) | Clean-room GLSL nested hatch math | **Zero** (Safe) |
| 3 | Curtis et al. (1997) | Fluid watercolor mechanics | Academic publication (ACM) | Procedural edge-darkening formula | **Zero** (Safe) |
| 4 | Winkenbach & Salesin (1994) | Pen-and-ink illustration | Academic publication (ACM) | Indication falloff logic | **Zero** (Safe) |
| 5 | Winkenbach & Salesin (1996) | Freeform surface hatching | Academic publication (ACM) | Tangent-aligned UV coordinate transforms | **Zero** (Safe) |
| 6 | Salisbury et al. (1997) | Orientable textures | Academic publication (ACM) | Direction-field vector math | **Zero** (Safe) |
| 7 | Deegan et al. (1997) | Coffee-ring effect | Academic scientific discovery (*Nature*) | Natural physical law; power-law decay | **Zero** (Safe) |
| 8 | Green / Valve (2007) | Signed Distance Field textures | Open Valve SIGGRAPH Course | Standard GLSL `fwidth`/`smoothstep` | **Zero** (Safe) |
| 9 | Chlumský (2015) | Multi-channel SDF (MSDF) | MIT License (CTU Master's Thesis) | Standard RGB median operator in shader | **Zero** (Safe) |
| 10 | Williams (2001) | Line boil on twos | Traditional animation principles | Frame-stepped modulo time math | **Zero** (Safe) |
| 11 | Mizuno / Way & Shih (1998, 2001) | Woodcut relief printmaking | Academic publication (Eurographics) | Clean-room procedural squash & grain | **Zero** (Safe) |
| 12 | Ostromoukhov (1999) | Digital facial engraving | Academic publication (ACM) | Line width frequency modulation | **Zero** (Safe) |
| 13 | Herschel (1842) / Ware (1999) | Cyanotype photochemistry | Public Domain (1842 historic treatise) | Negative line contact shader | **Zero** (Safe) |
| 14 | Day (1879) / Yule-Nielsen (1951) | Halftone & optical dot gain | Public Domain (1879 patent expired) | $45^\circ$ grid + Yule-Nielsen power law | **Zero** (Safe) |
| 15 | Sousa & Buchanan (1999, 2000) | Paper asperity & graphite pencil | Academic publication (Eurographics/NPAR) | Microscopic heightfield thresholding | **Zero** (Safe) |
| 16 | AlMeraj et al. (2013) | Pencil texture guidance | Academic publication (Computers & Graphics) | Non-linear opacity compositing formula | **Zero** (Safe) |
| 17 | Chu & Tai / MoXi (2005) | Absorbent paper ink dispersion | Academic publication (ACM TOG) | Bristle striation procedural mask | **Zero** (Safe) |
| 18 | Guo & Kunii (1991) | Sumi-e brush footprint | Academic publication (Visual Computer) | Elliptical footprint math | **Zero** (Safe) |
| 19 | Perlin (1985) / Worley (1996) | Procedural noise & cell texture | Unencumbered / 3D patent expired | 2D analytic hash/simplex functions | **Zero** (Safe) |
| 20 | van Wijk (1991) | Spot noise texture synthesis | Academic publication (ACM) | Anisotropic coordinate scaling | **Zero** (Safe) |
| 21 | Loop & Blinn (2005) | GPU curve resolution independence | Academic publication (ACM TOG) | Quadratic Bézier implicit solver | **Zero** (Safe) |
| 22 | Bærentzen & Aanæs (2005) | Angle-weighted pseudonormal | Academic publication (IEEE TVCG) | Continuous normal calculation | **Zero** (Safe) |
| 23 | Nehab & Hoppe (2008) | Random-access vector graphics | Academic publication (ACM TOG) | 2D uniform grid indexing | **Zero** (Safe) |
| 24 | Kilgard & Bolz (2012) | GPU path rendering | Academic publication (ACM TOG) | Standard WebGL 2-pass framebuffer | **Zero** (Safe) |
| 25 | Lucas (1918) / Washburn (1921) | Capillary square-root diffusion | Public Domain (1921 physical law) | $\sqrt{t - t_{\text{touch}}}$ expansion function | **Zero** (Safe) |
| 26 | Kubelka & Munk (1931) | Radiative transfer print-through | Public Domain (1931 optical theory) | Diffuse mirror show-through layer | **Zero** (Safe) |
| 27 | Baxter et al. (2001) | Sgraffito / subtractive gouge | Academic publication (ACM) | Subtractive mask + border shaving | **Zero** (Safe) |
| 28 | ITU-R BT.1702-3 (2019/2023) | Broadcast flash safety standard | Public international treaty / standard | Monotonic wavefront mathematical rule | **Zero** (Safe) |

---

## 4. Ranked Implementation Backlog

| Priority | Component | Scope & Files | Value / Performance Impact | Estimated Cost (Full / Half) |
|---|---|---|---|---|
| **P0** | **Drawing & SDF Extraction Rig** | Extract and normalize all 44 drawings from `assets/drawings/` via `tt_shorts/art.py:sanitize`, computing element bounding boxes, stroke order, and delays into `plates/ink/drawings_data.mjs`. | Foundational: allows any of Veasy's 44 drawings to be rendered on demand in plates. | Pre-baked offline data ($\le 50\text{ ms}$). |
| **P1** | **Core Material Shader Suite** | Implement 6 core materials in WebGL (`plates/ink/materials.mjs` / `index.html`): `woodcut`, `ink_wash`, `blueprint`, `halftone`, `chalk`, `pencil_hatch`. Paper tooth + seeded line boil on twos (15 fps). | Core requirement: authentic tactile physical media instead of digital SVG stroke trims. | Full: $160\text{–}210\text{ ms}$; Half: $65\text{–}90\text{ ms}$. |
| **P2** | **Reveal Mechanics & Bleed** | Stroke-by-stroke reveal matching sanitized `--d` order; Lucas-Washburn ($\sqrt{t}$) capillary paper bleed; scrape gouge; print-through reverse ink layer. | Visual realism: hand-painted progression rather than instant display. | Overhead: $+15\text{ ms}$ per frame. |
| **P3** | **Monotonic Ink Flood Matte Cut** | Full-frame fluid ink flood transition matte clip with verified `tt_shorts/flash.py` safety compliance. | Production cut transition for composed films and editorial scenes. | Full: $140\text{ ms}$; Half: $55\text{ ms}$. |
| **P4** | **44-Drawing Contact Sheet & Verification** | Contact sheet rendering all 44 drawings across all 6 materials mid-stroke; headless bake testing and determinism audit. | Quality gate: proves complete coverage and repeatability across entire drawing catalog. | Batch offline test run. |
| **P5** | **Fresh-Eye Critic Evaluation** | Isolated critic agent evaluating rendered stills on "painted, not filtered" metric (target $\ge 4/5$). | Human-level quality audit without developer bias. | Automated prompt & evaluation. |
| **P6** | **Skill & Documentation Packaging** | Complete `plates/ink/README.md`, spec options table, cost benchmarks, and device integration proposals. | Final delivery contract. | Complete docs. |

---

## 5. Architectural & System Boundaries

- **Files Owned**: `plates/ink/*`, `docs/research/ink-brush.md`, `docs/research/ink-brush-result.md`.
- **Untouched Core Files**: `plates/run.mjs`, `tt_shorts/engine.py`, `brushes/`, `remotion/` remain strictly read-only. Device integration proposals for `concepts/devices.json` are reported in the result document for Goal 1 integration.
- **Portability**: All materials run entirely in standard WebGL 1.0/2.0 inside headless Chromium with SwiftShader, requiring no proprietary binary native addons or external GPU hardware.
