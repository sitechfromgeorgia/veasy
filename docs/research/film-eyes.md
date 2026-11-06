# Research: The Film's Eyes — Autonomous Pixel Verification, Review Packets, and Self-Repair Loops

**Document:** `docs/research/film-eyes.md`  
**Author:** Veasy Film-Eyes Orchestrator (Lane: The Film's Eyes)  
**Date:** 2026-11-06  
**Branch:** `goal/film-eyes`  
**Scope:** `tt_shorts/eyes.py`, `tt_shorts/review.py`, `skills/review/`, `tests/test_eyes.py`, `tests/fixtures/review/`

---

## 0. The User's Level First: The One Line

### What a person or an agent types:
```bash
python -m tt_shorts.engine review stories/24835.json --rounds 2
```
*(or as an agent Hermes tool: `veasy_review({"story": "stories/24835.json", "rounds": 2})`)*

### What they get back:
```json
{
  "story": "stories/24835.json",
  "status": "fixed",
  "rounds_run": 2,
  "holds": [],
  "warnings": ["motion pacing: scene 1 (stat) pace slightly brisk (2.2 w/s)"],
  "facts_diff": [],
  "before_sheet": "cache/review/24835-round0.sheet.jpg",
  "after_sheet": "cache/review/24835-round2.sheet.jpg",
  "notes": [
    "t=3.2s · scene 1 (stat) · unreadable text hold -> duration expanded by 0.6s to satisfy 0.5s + 0.3s/word floor",
    "t=8.4s · scene 3 (points) · text extended into social rail (x=958, y=1210) -> lines wrapped to 22ch within safe zone"
  ],
  "recommendations": []
}
```
**The contract in one sentence:** A story in, a reviewed and self-repaired film out—with verified zero fact alteration (`facts_diff == []`), zero paid API calls, and before/after contact sheets showing every visual fix.

---

## 1. What Was Studied & What Each Teaches Veasy (24 Concrete Sources)

### A. Editorial & Motion Design Final Passes: Rhythm, Hierarchy, and Negative Space

1. **Walter Murch, *In the Blink of an Eye: A Perspective on Film Editing* (2nd ed., Silman-James Press, 2001)**  
   *Link:* [Silman-James Press Catalog](https://www.silmanjamespress.com/shop/in-the-blink-of-an-eye-2nd-edition/)  
   *What it teaches Veasy:* Murch's famous "Rule of Six" prioritizes emotion (51%), story (23%), rhythm (10%), eye-trace (7%), two-dimensional plane of screen (5%), and three-dimensional space of action (4%). For automated shorts, **rhythm** and **eye-trace** are paramount: cuts must not land on a mechanical metronome. If every scene cuts after exactly 2.50s, human viewers experience cognitive habituation and drop off. Pacing requires breathing room: a dense stat scene must be followed by a lighter thematic sign or quote.
   *Veasy formulation:* The `metronome_cuts` check in `eyes.py` computes the standard deviation of scene durations $\sigma(\Delta t)$. When $\sigma(\Delta t) < 0.20\,\text{s}$ across 4+ cuts, the video is flagged for robotic cut monotony.

2. **Frank Thomas & Ollie Johnston, *The Illusion of Life: Disney Animation* (Hyperion, 1981)**  
   *Link:* [Disney Publishing Archive](https://thewaltdisneycompany.com/)  
   *What it teaches Veasy:* The 12 core animation principles, especially **Staging** and **Secondary Action**. Staging directs the audience's attention to what is of greatest importance in a scene, eliminating any confusing detail. A vertical frame (1080×1920) cannot support competing focal points.
   *Veasy formulation:* In `eyes.py`, simultaneous entrance counts (`moves`) and focal density are evaluated. If text enters simultaneously with an icon animation and a background shift, visual clarity degrades.

3. **Austin Shaw, *Design for Motion: Fundamentals and Techniques of Motion Design* (2nd ed., Routledge, 2019)**  
   *Link:* [Routledge Motion Design](https://www.routledge.com/Design-for-Motion-Fundamentals-and-Techniques-of-Motion-Design/Shaw/p/book/9781138318649)  
   *What it teaches Veasy:* **Hero Frames** anchor motion design projects. A hero frame is the climactic visual frame that encapsulates the core concept, characterized by highest typographic scale, maximum visual mass, or striking contrast. Sequences consisting solely of mid-tier, uniformly weighted cards feel lifeless.
   *Veasy formulation:* The `no_hero_frame` check inspects the distribution of ink mass and typographic peak across scenes. A video must feature at least one scene with typographic prominence (e.g. hook headline $\ge 56\,\text{px}$ or stat value $\ge 84\,\text{px}$) that stands $\ge 1.4\times$ above the sequence median.

4. **Robin Williams, *The Non-Designer's Design Book* (4th ed., Peachpit Press, 2014)**  
   *Link:* [Peachpit Press](https://www.peachpit.com/store/non-designers-design-book-9780133966107)  
   *What it teaches Veasy:* The C.R.A.P. principles: **Contrast, Repetition, Alignment, Proximity**. Crucially, negative space (white space / dark canvas) must be deliberate, not accidental dead void. An accidental "empty middle" (where content clings exclusively to header and footer bands, leaving a gaping void between $y=400$ and $y=1200$) signals layout collapse.
   *Veasy formulation:* The `empty_middle` check measures the ink share in the central vertical zone ($y \in [450, 1150]$). If central ink density is $< 1.5\%$ while outer zones carry text, it triggers an empty-middle warning.

5. **Karen Sullivan, Kate Alexander, Aubry Mintz, Ellen Besen, *Ideas for the Animated Short* (Focal Press, 2013)**  
   *Link:* [Routledge Focal Press](https://www.routledge.com/Ideas-for-the-Animated-Short-Finding-and-Building-Stories/Sullivan-Alexander-Mintz-Besen/p/book/9780240818733)  
   *What it teaches Veasy:* Structural pacing in micro-shorts. Visual information density must correspond to auditory delivery. If a voiceover delivers an intricate explanation while the screen remains fixed on a simple title, viewer attention wanders.
   *Veasy formulation:* `spoken_redundancy` evaluates the semantic token ratio between voiceover and on-screen text. If on-screen text merely repeats 100% of spoken words verbatim, the screen is acting as an audio teleprompter rather than an informational brush.

6. **Roy Thompson & Christopher J. Bowen, *Grammar of the Edit* (3rd ed., Focal Press, 2013)**  
   *Link:* [Grammar of the Edit](https://www.routledge.com/Grammar-of-the-Edit/Bowen/p/book/9781138632103)  
   *What it teaches Veasy:* Metric cutting vs. Rhythmic cutting vs. Tonal cutting. Metric cutting cuts to strict pre-determined frame counts; rhythmic cuts match the cadence of speech and visual action. Pacing fatigue occurs when cuts violate spatial or directional continuity (e.g. ping-ponging directions).
   *Veasy formulation:* Builds on `motion_rules.pingpong` and `motion_rules.pacing` to ensure cuts feel motivated by the voice's cadential phrases rather than arbitrary fixed timers.

7. **Apple Inc., *Human Interface Guidelines: Typography, Layout & Motion* (Apple Developer, 2025)**  
   *Link:* [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/)  
   *What it teaches Veasy:* Legibility on high-density mobile OLED/LCD displays at arm's length (30–45 cm). Small text under 24 px becomes illegible in ambient glare; safe zones are strictly bounded by mobile hardware notches and dynamic island overlays.
   *Veasy formulation:* Enforces the safe zone floors ($y \in [248, 1380]$, $x \le 940$ below $y=1100$) and confirms font scaling floors across all rendered text.

8. **Google LLC, *Material Design 3: Motion & Ergonomics* (2024)**  
   *Link:* [Material Design 3 Motion](https://m3.material.io/styles/motion/overview)  
   *What it teaches Veasy:* Motion choreography: shared axes of motion reduce cognitive load. When elements enter from the left, subsequent wipes should not violently jar to the right unless communicating contrast or reversal.
   *Veasy formulation:* Aligns with Veasy's director current (`directors.py`), ensuring that automated repair choices preserve directional momentum.

---

### B. Automated Video Quality Measures & Pixel Metrics

9. **ITU-R Recommendation BT.1702-3 (2020), *Guidance for the reduction of photosensitive epileptic seizures caused by television***  
   *Link:* [ITU-R BT.1702-3](https://www.itu.int/rec/R-REC-BT.1702/en)  
   *What it teaches Veasy:* Strict biological safety bounds: no more than 3 flashes (6 transitions) per second exceeding $20\,\text{cd/m}^2$ across $>25\%$ of the screen. Red saturation transitions ($R/(R+G+B) \ge 0.8$) pose heightened seizure risk.
   *Veasy formulation:* `tt_shorts/flash.py` already implements exact BT.1702 checks; `review.py` treats flash violations as an unconditional **HOLD** that can never be downgraded to a warning.

10. **ITU-T Recommendation P.910 (2022), *Subjective video quality assessment methods for multimedia applications***  
    *Link:* [ITU-T P.910](https://www.itu.int/rec/T-REC-P.910/en)  
    *What it teaches Veasy:* Mathematical definitions of **Spatial Information (SI)** and **Temporal Information (TI)**. SI measures edge energy via Sobel filters across the frame; TI measures frame-to-frame difference energy $|F_n - F_{n-1}|$. A video whose TI drops to near zero for extended periods indicates a freeze/stall.
    *Veasy formulation:* `eyes.py` uses lightweight inter-frame difference and dHash distance to measure visual momentum without heavy native OpenCV dependencies.

11. **Zhou Wang, Alan C. Bovik, Hamid R. Sheikh, Eero P. Simoncelli, "Image Quality Assessment: From Error Visibility to Structural Similarity", *IEEE Transactions on Image Processing*, 13(4):600–612, 2004**  
    *Link:* [IEEE Xplore / SSIM](https://doi.org/10.1109/TIP.2003.819861)  
    *What it teaches Veasy:* Structural similarity separates luminance, contrast, and structural comparison. Pixel-by-pixel MSE fails to capture perceptual changes; structural comparison captures true image degradation.
    *Veasy formulation:* Rather than pixel diffing, `eyes.py` computes perceptual gradient hashing (dHash) on 16×16 and 32×32 grids, matching the proven approach of `golden.py`.

12. **Zhi Li, Anne Aaron, Ioannis Katsavounidis, Florian Manalo, Mo Chen, "Toward A Practical Perceptual Video Quality Metric", *Netflix Technology Blog*, 2016**  
    *Link:* [Netflix TechBlog VMAF](https://netflixtechblog.com/toward-a-practical-perceptual-video-quality-metric-653f208b9652)  
    *What it teaches Veasy:* Multi-metric fusion: combining detail loss (VIF), motion difference, and temporal masking produces reliable quality scores. A single metric is prone to gaming; composite scoring protects against edge cases.
    *Veasy formulation:* Composite grading in `review.py`: grade is an evaluation of safe zone, reading pacing, flash safety, metric variety, and rhythm.

13. **Neal Krawetz, "Kind of Like That", *Hacker Factor Solutions*, 2011**  
    *Link:* [Hacker Factor dHash](https://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html)  
    *What it teaches Veasy:* Difference Hash (dHash) computes relative luminance gradients between adjacent pixels. It is invariant to brightness scaling, contrast adjustments, and minor font anti-aliasing artifacts, while being extraordinarily fast (bit shift operations).
    *Veasy formulation:* `golden.dhash` (16×16 for full frame, 32×32 for scene band) is repurposed in `eyes.same_picture_twice` to detect consecutive scenes with identical visual compositions ($\text{Hamming distance} \le 3$).

14. **Claude Shannon, "A Mathematical Theory of Communication", *Bell System Technical Journal*, 27:379–423, 1948**  
    *Link:* [Bell System Technical Journal](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x)  
    *What it teaches Veasy:* Information entropy $H = -\sum p_i \log_2 p_i$ applied to luminance histograms. An empty or flat background has near-zero entropy; a visually rich graphic has balanced entropy ($3.5 \le H \le 6.5$). Extremely high entropy ($>7.5$) signifies visual noise.
    *Veasy formulation:* Used in `eyes.empty_middle` to detect dead frames where the middle band lacks structural information.

---

### C. Multi-Agent Review Loops, Stall, and Over-Correction

15. **Jie Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet", *ICLR*, 2024 (arXiv:2310.01798)**  
    *Link:* [arXiv:2310.01798](https://arxiv.org/abs/2310.01798)  
    *What it teaches Veasy:* Unconstrained LLMs attempting self-correction without external ground-truth verifiers suffer from **drift, oscillation, and hallucinated fixes**. An agent told "make it more lively" will hallucinate extra characters, rewrite factual numbers, or cycle endlessly between conflicting styles.
    *Veasy formulation:* Review loops MUST be bounded by **deterministic code verifiers**. The repair loop never allows an ungrounded model to rewrite facts; every repair passes through `facts_diff(before, after) == []`. If a fact is altered, the step is rejected immediately.

16. **MoVer: Multi-modal Verification and Self-Refinement for Grounded Video Generation, 2025 (arXiv:2502.13372)**  
    *Link:* [arXiv:2502.13372](https://arxiv.org/abs/2502.13372)  
    *What it teaches Veasy:* Verification precision: general feedback ("improve the pacing") achieves only 12.1% repair success; binary pass/fail achieves 19.2%; but **precise localized spatio-temporal bug reports** (`t=4.2s · where · problem -> change`) achieve **34.8% repair success**.
    *Veasy formulation:* The review packet contract enforces the exact format: `t={time}s · {where} · {problem} -> {change}`, providing unambiguous coordinates and actionable change targets.

17. **Code2Video: Autonomous Visual Program Synthesis via Decoupled Planning and Critic Architecture, 2025 (arXiv:2510.01174)**  
    *Link:* [arXiv:2510.01174](https://arxiv.org/abs/2510.01174)  
    *What it teaches Veasy:* Ablation studies demonstrate that removing the Planner drops visual aesthetics drastically (79.0 $\to$ 38.1), whereas removing the Critic only drops aesthetics by 6.5 points. **The Critic must NOT attempt to be the primary creator; its optimal role is a safety gate and hold mechanism.**
    *Veasy formulation:* In Veasy, planning and brush selection create the film; `review.py` acts strictly as an auditor and bounded repair regulator. A critic's pass is never a gate, but a critic's hold stops publication.

18. **OmniManim: Decoupled Spatial Planning for Programmatic Animation, 2026 (arXiv:2605.15585)**  
    *Link:* [arXiv:2605.15585](https://huggingface.co/papers/2605.15585.md)  
    *What it teaches Veasy:* Separating spatial coordinate bounding from procedural code generation prevents layout thrashing. Bounding boxes must be checked before rendering pixels.
    *Veasy formulation:* The layout probe (`probe.py`) verifies exact DOM bounding rectangles in browser memory, pre-empting visual collisions before final video mixing.

19. **Pedro Bakaus, *Impeccable: The Craft Floor & Critique Architecture* (github.com/pbakaus/impeccable, 2026)**  
    *Link:* [Impeccable Reference](https://github.com/pbakaus/impeccable)  
    *What it teaches Veasy:* Two-round maximum critique cap (`critique.md`); separation of builder reasoning from critic evaluation; deterministic rules vs. taste. When a builder acts as its own critic, it confirms its own biases. A fresh-eye reviewer must see only the outputs, not the code or prompt history.
    *Veasy formulation:* Our review packet provides contact sheets and story spec only—never code. Review iterations are strictly capped at 3 machine rounds and 2 look rounds.

20. **Tejash Makwana, *motionmaxxing: Motion Design Rules and Velocity Curves* (github.com/Tejashmakwana/motionmaxxing, 2026)**  
    *Link:* [motionmaxxing](https://github.com/Tejashmakwana/motionmaxxing)  
    *What it teaches Veasy:* Hard negative rule catalogs produce clean but lifeless videos when over-applied. In tests, a small vision model marked a 15-second completely black video as "clean pass" because it saw no forbidden elements!
    *Veasy formulation:* Quality is not the absence of errors; positive structural invariants (e.g. minimum ink mass, hero frame presence, dynamic cut variance) must be evaluated alongside negative constraints.

---

### D. Multimodal Vision Models on Contact Sheets

21. **MotionBlind: Assessing the Perception of Motion and Speed in Video Vision-Language Models, 2026 (arXiv:2609.09528)**  
    *Link:* [arXiv:2609.09528](https://www.alphaxiv.org/abs/2609.09528)  
    *What it teaches Veasy:* Vision-language models (e.g. Gemini 1.5/2.0, GPT-4o) exhibit severe blindness when estimating temporal motion speeds (accuracy only 14.3% across motion benchmark suites). They cannot reliably detect 12-frame pacing hitches from video files. However, on static contact sheets, their spatial comprehension (color harmony, text legibility, visual clutter) is high (>85%).
    *Veasy formulation:* We calculate motion and timing mathematically from timelines ($0.5\,\text{s} + 0.3\,\text{s/word}$, cut variance); we reserve visual sheet inspection for spatial, typographic, and compositional auditing.

22. **Chris Echols, *Gauntlet: Fresh-Eye Motion Video Review and Freeze Detection* (echris6/motion-video-kit, 2026)**  
    *Link:* [Gauntlet](https://github.com/echris6/motion-video-kit/blob/main/business-motion-film/references/gauntlet.md)  
    *What it teaches Veasy:* A fresh-eye pass on contact sheets caught 10 out of 36 frozen seconds that automated text linters missed. To make contact sheets interpretable in 5 seconds, each thumbnail requires: timestamp $t$, scene index, reading load badge, and safe-zone border indicators.
    *Veasy formulation:* Review contact sheets (`review.py`) generate structured visual contact sheets containing frame timestamps, scene indices, and overlay annotations.

23. **Anthropic Engineering, *Improving Frontend Design Through Skills and Verifiable Guards* (2025)**  
    *Link:* [Anthropic Research](https://www.claude.com/blog/improving-frontend-design-through-skills)  
    *What it teaches Veasy:* Default LLM tendencies regress to generic "slop" (purple gradients, generic cards, centered sans-serif text) when unguided. Explicit brand tokens, hard palette floors, and deterministic linting force distinctive, premium output.
    *Veasy formulation:* Veasy's brand pack contract (dark canvas, light ink, single accent never on text, FiraGO font) is enforced on all review repairs.

24. **Wenger & Kenett, "The Homogeneity of Generative AI Outputs Across Conceptual Domains", 2025 (arXiv:2501.19361)**  
    *Link:* [arXiv:2501.19361](https://arxiv.org/abs/2501.19361)  
    *What it teaches Veasy:* Machine outputs cluster tightly around statistical means. Automated repair loops tend to converge toward identical safe shapes unless variety entropy is injected from the story's own specific factual nouns.
    *Veasy formulation:* Repairs must derive visual brush selection from the story's actual facts (e.g. quantities $\to$ `stat`/`bars`; dates $\to$ `timeline`/`rail`; locations $\to$ `where`).

---

## 2. License Table: Third-Party Tools, Code & Concepts

Every tool, library, and intellectual property touched or referenced in this lane complies with commercial open-source licensing.

| Component / Reference | Origin / Source | License | Commercial Use Permitted? | Veasy Compliance Treatment |
|---|---|---|---|---|
| **Pillow (PIL Fork)** | Python Packaging Authority (PyPA) | HPND | Yes | Built-in stdlib/venv dependency for dHash image hashing and contact sheet cropping. |
| **NumPy** | NumPy Developers | BSD-3-Clause | Yes | Array operations for luminance, redness, and histogram entropy calculations in `flash.py` and `eyes.py`. |
| **Remotion Core** | Remotion Dev (Jonny Burger) | Remotion License (Free $\le 3$ employees) | Yes (Owner confirmed 2026-11-02) | Used for composition rendering and headless DOM probing. No paid API used. |
| **HyperFrames 0.9.8** | HyperFrames Authors | Apache-2.0 | Yes | Headless HTML/CSS/GSAP renderer. Pinned in `compose/package.json`. |
| **Lucide Icons** | Lucide Project | ISC | Yes | 250 SVG line icons vendored in `assets/icons/lucide.json`. |
| **FiraGO Font** | BPG InfoTech / Georgian Law | OFL-1.1 | Yes | Shipped in `brands/_ka/fonts/` for clean Georgian typography. |
| **motionmaxxing** | Tejash Makwana (2026) | Apache-2.0 | Yes | Ideas and empirical curves referenced with attribution in `CREDITS.md`. No GSAP code vendored. |
| **Impeccable** | Pedro Bakaus (2026) | Apache-2.0 | Yes | Two-round cap and fresh-eye critic isolation pattern adapted into `review.py`. |
| **Gauntlet** | Chris Echols (2026) | MIT | Yes | Contact sheet timestamp and badge visualization patterns adopted. |
| **ITU-R BT.1702-3** | International Telecommunication Union | Public Standard | Yes | Broadcast seizure protection formulas implemented in pure NumPy in `tt_shorts/flash.py`. |

---

## 3. Ranked Backlog: Value, Effort, and Dependencies

| Rank | Item | Module / Path | Value | Effort | Description & Acceptance Criteria |
|---|---|---|---|---|---|
| **1** | **Free Pixel Checks (`eyes.py`)** | `tt_shorts/eyes.py`, `tests/test_eyes.py` | **Highest** | **M (2 days)** | Pure pixel & timeline metric suite: `same_picture_twice` (dHash), `empty_middle` (ink density), `no_hero_frame` (contrast peak), `metronome_cuts` (cut variance), `spoken_redundancy` (token overlap). Unit tests pass 100%. |
| **2** | **12 Seeded-Defect Test Fixtures** | `tests/fixtures/review/*.json` | **Highest** | **S (1 day)** | 12 realistic Georgian story JSON fixtures isolating exact defects (unreadable text hold, flash hold, same picture, empty middle, metronome cuts, etc.). |
| **3** | **Review Packet Generator** | `tt_shorts/review.py` | **High** | **S (1 day)** | Generates review packet (JSON + Markdown) with contact sheets, beat timeline, and formatted notes: `t=... · where · problem -> change`. Zero code leakage. |
| **4** | **Automated Repair Loop (`engine review`)** | `tt_shorts/review.py`, `tt_shorts/engine.py` | **High** | **M (2 days)** | 3 machine rounds, 2 look rounds. Applies targeted non-destructive transforms. Validates `facts_diff(before, after) == []`. |
| **5** | **Calibration on Approved Demos** | `tests/test_eyes.py`, `tt_shorts/review.py` | **High** | **S (0.5 day)** | Guarantees ZERO false holds across `24835.json`, `veasy-demo.json`, `veasy-scenes.json`, `24725.json`, `sitech-cybercartel.json`, `law-constitution-17.json`. |
| **6** | **Before/After Fix Demonstrator** | `docs/research/film-eyes-result.md` | **High** | **S (0.5 day)** | Runs review loop on 3 broken films, saves before/after contact sheets, verifies real fixes with empty facts diff. |
| **7** | **Hermes Tool & Skill (`veasy:review`)** | `plugin.yaml`, `__init__.py`, `skills/review/SKILL.md` | **Medium** | **S (0.5 day)** | Registers `veasy_review` tool in plugin and Hermes, links `.claude/skills/review`, passes `test_plugin.py`. Sub-agent cold test verified. |

---

## 4. Architecture & Data Flow

```
                      +-----------------------------+
                      |      Input Story JSON       |
                      +-----------------------------+
                                     |
                                     v
                       +---------------------------+
                       |   tt_shorts/eyes.py       |
                       |  (Free Pixel & Plan QAs)  |
                       +---------------------------+
                                     |
            +------------------------+------------------------+
            |                        |                        |
            v                        v                        v
   [same_picture_twice]       [empty_middle]          [no_hero_frame]
   (golden.dhash <= 3)        (central ink < 1.5%)    (peak < 1.4x median)
            |                        |                        |
            +------------------------+------------------------+
            |                        |                        |
            v                        v                        v
     [metronome_cuts]       [spoken_redundancy]       [read / flash holds]
     (std dev < 0.20s)      (token overlap == 1.0)    (BT.1702 / 0.5s+0.3s/w)
                                     |
                                     v
                       +---------------------------+
                       |    tt_shorts/review.py    |
                       |  - Review Packet Builder  |
                       |  - Format: t=.. · where   |
                       |  - Facts Diff Invariant   |
                       |  - Capped Repair Loop     |
                       +---------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |     Output Review Result    |
                      |   status: passed / fixed    |
                      |   facts_diff: [] (ZERO)     |
                      |   before & after sheets     |
                      +-----------------------------+
```
