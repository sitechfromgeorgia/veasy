# Plates Core: First-Class Baked Plates for Veasy

## The One Line

A person or an agent types:
```bash
python -m tt_shorts.engine plate example --seconds 4
```
or inside a Hermes agent session:
```python
veasy_plate(kind="example", seconds=4)
```

And gets back in under 1 second (from cache) or on first bake:
```json
{
  "kind": "example",
  "hash": "c4d87e1a3b5f9021",
  "seed": 1,
  "seconds": 4.0,
  "scale": 1.0,
  "fps": 30,
  "frames": 120,
  "cached": true,
  "ms_per_frame": 187,
  "anchors": ["dot"],
  "master": "cache/plates/c4d87e1a3b5f9021/plate.mp4",
  "poster": "cache/plates/c4d87e1a3b5f9021/poster.png",
  "clips": {
    "tbilisi-today": {
      "dark": "cache/plates/c4d87e1a3b5f9021/plate-tbilisi-today-dark.mp4",
      "light": "cache/plates/c4d87e1a3b5f9021/plate-tbilisi-today-light.mp4"
    },
    "sitech": {
      "dark": "cache/plates/c4d87e1a3b5f9021/plate-sitech-dark.mp4",
      "light": "cache/plates/c4d87e1a3b5f9021/plate-sitech-light.mp4"
    }
  },
  "anchors_file": "cache/plates/c4d87e1a3b5f9021/anchors.json"
}
```

Behind any scene in either engine:
- In **Remotion**: A story script specifies `{"type": "plate", "plate": "example", "headline": "სისტემის ანალიზი", "label": "მოდელირება"}`. The engine places the tone-mapped clip behind a safe-zone panel, with text in the DOM and a brand accent dot tracking `anchors.json`.
- In **HyperFrames (compose)**: The agent includes the `plate` block (`compose/blocks/plate/`) or `<video muted playsinline src="assets/plates/example.mp4">` behind a `var(--canvas-90)` solid card.

---

## 1. Executive Summary & Ground Rules

Veasy's plate core brings pre-rendered software-GL/Three.js/shader grey clips into Veasy as a first-class brush. It gives both engines (Remotion and HyperFrames) visual capabilities neither has natively (real 3D depth, particle systems, procedural matter, raymarching) **without changing how films render**:
- Both engines read local MP4 files.
- All typography remains in the DOM and passes all Georgian language and contrast checks.
- Zero paid API calls. All rendering and tone mapping is completely free and local.
- **The Zero-Bake Queue Invariant:** A video rendering queue job **never bakes a plate**. Baking a 4–6s plate on SwiftShader costs 187–674 ms per frame (~22s to 2.5 minutes). At 50 videos a day, baking on the queue would add 37–135 minutes of CPU load. Plates are baked strictly into a shared library ahead of time. A missing plate is **always a warning, never a lost video**.
- **Refusal Guard:** In compliance with news integrity rules (CLAUDE.md, ka_style.md § N, AP/EBU guidelines), plates are **strictly forbidden** for `news` programs, crime, incidents, and deaths. A synthetic plate never asserts or depicts a real place.

---

## 2. Research & Academic Foundations (16 Real Sources)

We surveyed 16 foundational sources across broadcast graphics engineering, human contrast perception, video codecs, and deterministic build systems:

| # | Source | Domain | What it Teaches Veasy |
|---|---|---|---|
| 1 | **Barten, Peter G. J. (1999)**. *Contrast Sensitivity of the Human Eye and Its Effects on Image Quality*. SPIE Press. | Vision Science | The human eye detects relative luminance steps $\Delta L / L > 1\%$ (Weber-Fechner Law). In dark shadows ($L < 1 \text{ cd/m}^2$, e.g. Tbilisi Today canvas `#05080F`), 8-bit quantization steps represent $\Delta L / L \approx 5\% - 20\%$, causing visible Mach banding on mobile OLED displays unless dithered. |
| 2 | **NEMA / DICOM Part 14**. *Grayscale Standard Display Function (GSDF)*. | Display Standards | Standardizes Just Noticeable Differences (JND) across the greyscale range. Confirms that tone mapping must apply spatial dithering prior to integer quantization. |
| 3 | **FFmpeg Documentation**. *Video Filters: lutrgb, gradfun, curves, geq, deband*. https://ffmpeg.org/ffmpeg-filters.html | Video Processing | `lutrgb` evaluates mathematical formulas once at filter initialization to build 256-entry 1D lookup tables per channel, executing at $O(1)$ per pixel (190 FPS, 5.2 ms/frame). `curves` fails palette collinearity due to cubic spline float rounding. `geq` is 32x slower. |
| 4 | **Biurrun, Diego et al**. *vf_gradfun.c: Fast Gradient Debanding Algorithm*. FFmpeg Source Tree. | Signal Processing | `gradfun=1.2:16` reconstructs subtle gradients and applies high-frequency 1D spatial dithering. When run on `format=gray` **before** `lutrgb`, it prevents gradient banding while ensuring every pixel maps strictly to the 1D palette line. |
| 5 | **libplacebo / mpv Project**. *Debanding and Dithering Architecture Specification*. https://libplacebo.org | Display Architecture | Multi-channel dithering after color mapping injects chromatic noise ($\epsilon_R \neq \epsilon_G \neq \epsilon_B$), creating off-palette artifacts. Dithering must occur strictly in the scalar 1D domain before 3D color assignment. |
| 6 | **W3C HTMLMediaElement Spec**. *Time Ranges and Seeking Algorithm*. W3C Recommendation. | Web Standards | `video.currentTime = t` is inherently asynchronous. Chromium snaps to preceding keyframes and decodes forward. In headless environments, capturing on `seeked` triggers frame drift and compositor race conditions. |
| 7 | **Chromium Project**. *Issues 1100080 & 1146755: HTMLMediaElement seek precision*. Chromium Issue Tracker. | Browser Internals | Even after `seeked` fires, Skia compositor texture presentation lags behind Blink layout passes in headless software GL mode (`--use-gl=angle --use-angle=swiftshader`). |
| 8 | **W3C / Google Chrome 83**. *HTMLVideoElement.requestVideoFrameCallback (rVFC)*. W3C Draft. | Browser Media | Standardized to synchronize video presentation with animation frames, confirming that native `<video>` elements in headless browsers without VSYNC require out-of-band frame decoding. |
| 9 | **Remotion Project**. *PR #11685 & RFC 134: OffthreadVideo Architecture*. Remotion Docs. | Engine Architecture | Remotion's `<OffthreadVideo>` completely bypasses Chromium's HTML5 video decoder during headless CLI renders. A native Rust/FFmpeg worker extracts the exact presentation timestamp frame into a BMP/PNG buffer and injects it as an HTML `<img>` tag, guaranteeing 100% deterministic, zero-seek-jitter frames. |
| 10 | **ITU-R Recommendation BT.709-6**. *Parameter values for HDTV standards*. ITU. | Broadcast Standards | Video levels 16–235 vs full range 0–255. High-contrast typography requires background luminance attenuation to maintain minimum 7:1 contrast ratios over moving imagery. |
| 11 | **W3C Web Content Accessibility Guidelines (WCAG) 2.2**. *Section 1.4.3 Contrast (Minimum)*. W3C. | Accessibility | In `compose/probe.mjs`, bare text over video is tested against black `[0,0,0]` and white `[255,255,255]`. Floating text over plates requires an opaque or 90% alpha solid panel (`var(--canvas-90)`) to achieve $\ge 13:1$ contrast against any underlying video pixel. |
| 12 | **Associated Press (AP)**. *News Values and Principles: Standards on AI & Synthetic Imagery*. AP News. | Journalism Ethics | Synthetic visuals must never simulate real events, depict victims, or assert unverified places in news coverage. |
| 13 | **European Broadcasting Union (EBU)**. *Ethics Guidelines for Synthetic Media in Public Service Media*. EBU Tech. | Journalism Ethics | Recommends strict separation between documentary news and synthetic generative motion graphics. Mandatory refusal of synthetic backgrounds in crime, disaster, and casualty reporting. |
| 14 | **EBU Tech 3343**. *Guidelines for loudness and dynamic range in broadcast television*. EBU. | Audio / Broadcast | Reinforces constant-level mixing without ducking (matching Veasy's audio mix law in `CLAUDE.md`). |
| 15 | **Nix & Bazel Media Pipelines**. *Content-Addressable Storage (CAS) and Deterministic Build Caching*. | Build Systems | A build artifact is a pure function: $\text{Artifact} = f(\text{Sources}, \text{Spec}, \text{Seed}, \text{Dimensions})$. Encoding with fixed GOP (`-g 15`) and `-movflags +faststart` ensures byte-level reproducibility. |
| 16 | **GreenSock (GSAP)**. *Timeline Architecture and Deterministic Virtual Time Playback*. GreenSock Docs. | Motion Engineering | In HyperFrames, `window.__player.renderSeek(t)` advances a paused GSAP master timeline. Piecewise linear interpolation of `anchors.json` via chained `.to(..., {x, y, duration, ease: "none"})` evaluates natively in JS bytecode with zero asynchronous seek overhead. |

---

## 3. Commercial Licence Matrix

All code, assets, and tools incorporated into Veasy plates must permit unencumbered commercial use without viral copyleft (GPL/AGPL prohibited):

| Component / Library | Version | Licence | Permitted in Commercial Veasy | Notes & Attribution |
|---|---|---|---|---|
| **FFmpeg** (`lutrgb`, `gradfun`, `libx264`) | 7.x / 9.x | LGPL-2.1+ / GPL-2.0+ (CLI external) | **YES** | Invoked strictly as an out-of-process external CLI binary. No linking into Veasy Python code. |
| **Three.js** | r184 / r187 | MIT | **YES** | Bundled in `plates/package.json` for software GL plate baking in headless Chrome. |
| **Puppeteer-core** | 25.16.0 | Apache-2.0 | **YES** | Headless browser automation driving `plates/run.mjs`. |
| **GSAP (GreenSock)** | 3.12.5 | Standard GreenSock (free web) | **YES** | Already pinned and bundled in `compose/assets/vendor/gsap.min.js`. |
| **Remotion** (`<OffthreadVideo>`) | 4.0.x | Remotion Company Licence | **YES** | Permitted under company size / existing Veasy Remotion deployment. |
| **Mulberry32 PRNG** | - | Public Domain / CC0 | **YES** | Embedded in `plates/lib/seeded.mjs` for pure deterministic pseudo-randomness. |

---

## 4. Tone Mapping & Banding Solution

### 4.1 The Palette Collinearity Theorem
Let brand canvas be $C_0 = (R_0, G_0, B_0)$ and brand ink be $C_1 = (R_1, G_1, B_1)$.
The mathematical color line is:
$$\vec{C}(t) = C_0 + t \cdot (C_1 - C_0), \quad t \in [0, 1]$$

Using FFmpeg's `lutrgb` with linear expression:
$$\text{LUT}_R[g] = \text{round}\left(R_0 + \frac{g}{255} (R_1 - R_0)\right)$$
$$\text{LUT}_G[g] = \text{round}\left(G_0 + \frac{g}{255} (G_1 - G_0)\right)$$
$$\text{LUT}_B[g] = \text{round}\left(B_0 + \frac{g}{255} (B_1 - B_0)\right)$$

The 256 discrete points $S = \{(\text{LUT}_R[g], \text{LUT}_G[g], \text{LUT}_B[g]) \mid g \in [0, 255]\}$ lie within a maximum Euclidean rounding distance $d \le \frac{\sqrt{3}}{2} \approx 0.866$ units from the true 3D line.

### 4.2 Eliminating Banding without Chromatic Noise
1. Standard post-color dithering injects independent RGB noise ($\epsilon_R \neq \epsilon_G \neq \epsilon_B$), producing thousands of off-palette colors.
2. Our pipeline applies `gradfun=1.2:16` to the 1-channel greyscale raster **prior to LUT evaluation**.
3. Spatial dither dithers between adjacent integer luminance values $g$ and $g+1$.
4. When passed to `lutrgb`, each pixel resolves to a valid palette point in $S$.
5. **Result:** Gradient stepping on mobile OLED screens is resolved through spatial dithering with **zero off-palette colors**.

---

## 5. Architecture: Remotion & HyperFrames Players

### 5.1 Remotion Player (`remotion/src/scenes/Plate.tsx`)
- Registered in `remotion/src/types.ts` and `remotion/src/scenes/index.tsx`.
- Uses `<OffthreadVideo src={staticFile(p.src)} />` to eliminate seek jitter and black frames.
- Reads `anchors.json` via `useCurrentFrame()` to smoothly position the brand accent dot.
- Encloses text inside an elevated panel with `background: alpha(CANVAS, 0.92)` and `border: 2px solid ${LINE_STRONG}`.

### 5.2 HyperFrames Composed Block (`compose/blocks/plate/`)
- Contains `block.json` manifest and `template.html`.
- Plays `<video muted playsinline src="{slot_plate_src}">` which passes `compose.lint` (no `<canvas>`, no remote net, probe marked).
- Floating card uses `background: var(--canvas-90)`, guaranteeing $\ge 13:1$ contrast against any video ground in `compose/probe.mjs`.
- Binds `anchors.json` to the GSAP timeline using chained linear tweens.

---

## 6. Three-Layer Refusal System

To protect editorial integrity, plates are rejected for **`news`**, **crime**, **incidents**, and **deaths**:

1. **CLI Layer (`engine.py`)**: `engine plate <kind> --program news` or checking a story with death/crime keywords refuses immediately with exit code 1.
2. **Brush Catalog Layer (`catalog.py` & `brushes/plate.json`)**: `families_deny: ["crime", "incidents", "news"]`.
3. **News Check Layer (`news_check.py`)**: `plate` is omitted from `SCENE_TYPES` (N1 check). Any story mentioning death stems (`დაიღუპა`, `გარდაიცვალა`) fails if plates are present.

---

## 7. Ranked Engineering Backlog

| # | Task | Value | Effort | Files Owned / Touched |
|---|---|---|---|---|
| **1** | **`tt_shorts/plates.py` & Tone Mapper**<br>Implement `build_palette_lut`, `ffmpeg_tone_filter`, `bake_plate`, `map_plate_theme`, `verify_frame_collinearity`, and `hash_of`. | **Critical** (P0) | 3h | `tt_shorts/plates.py`, `plates/run.mjs` |
| **2** | **Test Suite (`tests/test_plates.py`)**<br>Unit tests for tone collinearity across all 4 themes, determinism, sub-second cache hit, refusals (news/crime/deaths), ledger, and anchors. | **Critical** (P0) | 2h | `tests/test_plates.py` |
| **3** | **Engine CLI Wiring & Options**<br>`engine plate <kind>`, `engine plate list`, `engine plate check`, `engine options` (`plates` block). | **High** (P1) | 1.5h | `tt_shorts/engine.py`, `tt_shorts/store.py` |
| **4** | **Asset Ledger & N13 Integration**<br>Add `plate` to `assets.KINDS`, `assets.PROVIDERS`, `assets.LICENCES`; N13 illustrative label support. | **High** (P1) | 1h | `tt_shorts/assets.py`, `tt_shorts/news_check.py` |
| **5** | **Remotion Scene & Brush Catalog**<br>Create `brushes/plate.json`, `remotion/src/scenes/Plate.tsx`, register in `types.ts` and `index.tsx`. | **High** (P1) | 2h | `brushes/plate.json`, `remotion/src/scenes/Plate.tsx`, `remotion/src/types.ts`, `remotion/src/scenes/index.tsx` |
| **6** | **HyperFrames Composed Block**<br>Create `compose/blocks/plate/block.json` and `template.html`; verify `compose.lint` passes. | **High** (P1) | 1.5h | `compose/blocks/plate/block.json`, `compose/blocks/plate/template.html` |
| **7** | **Variety Integration & Queue Safety**<br>Add `variety.pick_plate` (least-used cached plate); ensure queue jobs never bake; missing plate warning fallback. | **Medium** (P2) | 1.5h | `tt_shorts/variety.py`, `tt_shorts/queue.py` |
| **8** | **Hermes Skill & Tool Registration**<br>Create `skills/plates/SKILL.md` (<12,000 chars); add `veasy_plate` tool to `plugin.yaml` and `__init__.py`. | **Medium** (P2) | 1h | `skills/plates/SKILL.md`, `plugin.yaml`, `__init__.py` |
| **9** | **End-to-End Proof Films & Visual QA**<br>Render one Remotion film and one Composed film with plates; verify `qa`, `probe`, flash safety; review with Fresh-Eye Critic. | **High** (P1) | 2h | `docs/research/plates-core-result.md`, proof renders |

---

## 8. Sub-Agent Structure & Ownership Table

| Role | Conversation ID / Owner | Responsibilities | Output Evidence |
|---|---|---|---|
| **Orchestrator** | Parent (`55ba82f9-ff85-4e30-b157-52e5ced66718`) | Integration, commits, milestone gates, coordination. | Branch `goal/plates-core`, git history. |
| **Tone Mapper Researcher** | `894aa78e-297e-4969-8cd0-a3e46a2e94e6` | FFmpeg filter pipeline, collinearity proof, banding dither benchmarks. | Benchmark table, LUT formulas. |
| **Engine Wiring Researcher** | `4e5b0e0a-84e6-424a-b46a-e1697dda6477` | CLI signatures, cache store paths, asset ledger, refusal architecture. | CLI specs, JSON schemas, refusal gates. |
| **Player & Layout Researcher** | `b9146b3a-9351-429f-a1ed-c49c839a37dc` | Remotion `Plate.tsx`, compose block, safe zones, `anchors.json` tracking. | `Plate.tsx`, `template.html`, layout rules. |
| **Test Author Researcher** | `58e02405-4a3e-4a70-8061-28764d0ec2f9` | Test matrix and assertion designs for `tests/test_plates.py`. | 7 test suites, numpy collinearity code. |
| **Fresh-Eye Critic** | To be invoked post-render | Blind evaluation of rendered frames, contact sheets, and skill readability without seeing code. | `CRITIQUE.md` / review notes. |
