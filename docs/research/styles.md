# Research: Film Styles for Veasy

**Author**: Veasy Styles Agent (SiTech)  
**Date**: 2026-11-03  
**Branch**: `goal/styles`  
**Status**: Pre-build Research & Spike Report

---

## 1. Executive Summary & Goals

Veasy is SiTech's video engine for autonomous and pair-programmed agents, currently producing vertical 1080×1920 Georgian videos with Gemini TTS, word-level caption alignment, composed music, and multi-tier quality checks. While Veasy v1 and early v2 introduced 3 looks (`editorial`, `kinetic`, `cards`), 8 directors (`data`, `map`, `type`, `draw`, `chronicle`, `witness`, `brief`, `single`), rubrics, motifs, and variety rotation, all automated videos still share a limited visual envelope.

Learning from **lemomo-ai/lemo-opuscar** (MIT), which provides a library of 66 film styles made in pure code without video generation models, this work gives Veasy a library of **named film styles as data**. 
- A user or an agent can specify the visual character in **one word** (`--style swiss-motion`, `--style dataviz`, `--style blueprint`), or let variety rotate among allowed styles.
- Under the style, code automatically selects the engine (`remotion` vs `hyperframes`), layout rules, motion numbers, director constraints, transitions, sound palette, and check invariants.
- Crucially, the system is re-thought for **vertical 1080×1920 framing**, **Georgian Mkhedruli typography**, **Veasy's strict safe zones**, **brand law**, and **news integrity rules**.

---

## 2. The Determinism Spike Report

### The Question
Can a HyperFrames composition drive a Canvas 2D or WebGL `render(t)` page deterministically—rendering twice to produce byte-identical or identical-hash frames? If yes, canvas-based styles run cleanly inside **Lane B (HyperFrames)** without requiring a third engine. If no, a third engine or alternative execution environment would be required (which is an owner decision).

### Experimental Setup
We designed two test compositions inside the pinned HyperFrames 0.9.8 environment (`compose/node_modules/hyperframes/bin/hyperframes.mjs`):
1. **Canvas 2D Spike (`spike-canvas`)**:
   - Canvas 1080×1920 with 2D rendering context.
   - A deterministic `render(t)` function drawing background fills, trigonometric circle movement, radius breathing, and an animated progress bar based on time $t \in [0, 2.0]$.
   - Paused GSAP timeline driving `{ t: 0 }` to `t: 2.0` with `onUpdate: () => render(state.t)`.
   - Rendered with pinned flags: `--fps 30 --workers 4 --no-browser-gpu --quality looks -o run1.mp4` and `-o run2.mp4`.
2. **WebGL Shader Spike (`spike-webgl`)**:
   - Canvas 1080×1920 with WebGL rendering context.
   - Vertex and fragment shader computing dynamic distance fields and smoothstep color pulses parameterized by `u_time`.
   - Paused GSAP timeline driving `{ t: 0 }` to `t: 2.0` with `onUpdate: () => render(state.t)`.
   - Rendered with identical pinned flags under software GL.

### Results
- **Canvas 2D**:
  - Run 1 exit code: `0`, file size: `49,974 bytes`
  - Run 2 exit code: `0`, file size: `49,974 bytes`
  - Run 1 SHA256: `1f05ef1b16c08a2530ce8e3ce84b9b561fdc25c48c7515b901f7697318b4eaa6`
  - Run 2 SHA256: `1f05ef1b16c08a2530ce8e3ce84b9b561fdc25c48c7515b901f7697318b4eaa6`
  - **Identical MP4s: TRUE** (Byte-for-byte identical output).
- **WebGL**:
  - Run 1 exit code: `0`, file size: `51,200 bytes`
  - Run 2 exit code: `0`, file size: `51,200 bytes`
  - Run 1 SHA256: `689af10651056eeb68cfae817b4dfcea9164616d08df5f7f5c7ca08f8e16e008`
  - Run 2 SHA256: `689af10651056eeb68cfae817b4dfcea9164616d08df5f7f5c7ca08f8e16e008`
  - **Identical MP4s: TRUE** (Byte-for-byte identical output).

### Conclusion & Architectural Ruling
**HyperFrames compositions can deterministically drive Canvas 2D and WebGL rendering.**
Canvas and shader-driven styles run inside **Lane B (HyperFrames)**. No third engine is required.
However, because Canvas/WebGL pixels are opaque to DOM inspection:
1. All essential on-screen text must either be rendered as DOM elements within `data-probe` regions (e.g. locked chrome and captions, or DOM overlays) OR
2. Compositions must provide the `window.TEXTS(t)` contract so that reading-time checks (0.5 s + 0.3 s a word) and safe zone geometry are verified before rendering.
3. In `tt_shorts/compose.py`, the `CANVAS` lint rule ("no `<canvas>`, 2D/WebGL context") was designed to prevent undetectable untyped text. For canvas styles, the lint allows `<canvas>` provided that text is either in the DOM or reported via `TEXTS(t)` and verified by the probe.

---

## 3. Comparative Analysis of Styles

We analyzed 22 styles (11 first-wave brand-safe styles, 10 second-wave styles, and 1 proposed Georgian cultural style). Each style is adapted to vertical 1080×1920 video and Georgian Mkhedruli script.

### First Wave (Brand-Safe for News & Explainers)

| # | Style | Essence in One Line | At-a-Glance Signature | Palette & Font | Vertical (1080×1920) & Mkhedruli Adaptation | Engine | Programs |
|---|---|---|---|---|---|---|---|
| 1 | **Swiss Motion** (`swiss-motion`) | International Typographic Style on a modular grid where every move snaps on a beat without bounce. | Flush-left geometric type, stark scale contrast (huge numeral next to tiny notes), single signal accent. | `palette: pack`<br>`fonts: pack` | In vertical 1080×1920, the 12-column spread becomes a 6-column vertical rhythm. Mkhedruli has no capital letters, so hierarchy relies on extreme weight/size ratios (e.g. FiraGO 900 vs 300) and optical flush alignment. | Remotion & HyperFrames | `news`, `explainer`, `law`, `digest` |
| 2 | **Pictogram Motion** (`pictogram-motion`) | Beat-locked catalog or story where every item is a geometric sign and rows slide past on a modular grid. | Square grid pattern with discs/half-discs, round-capped geometric pictograms, large bold title + mono index. | `palette: pack`<br>`fonts: pack` | Vertical format stacks the card: pattern header/stage top, pictogram center, title and index in middle, safe from captions (below y=1380). Georgian stem mapping (`icons.py`) matches stems directly to Lucide/Isotype pictograms. | Remotion & HyperFrames | `news`, `explainer`, `blog` |
| 3 | **Caption News** (`caption-news`) | Social-video news built to be understood with sound off: bold captions slam in chunks with one keyword block over footage/cards. | Heavy subtitle cards with yellow/accent keyword wipe, rolling counters, documentary/screenshot ground, source tags. | `palette: pack`<br>`fonts: pack` | Replaced horizontal 16:9 banner with Veasy's lower-third band (y: 1380–1552). Chunk slams must accommodate Georgian word lengths (average 7–9 chars vs 4–5 in English). Keyword emphasis maps to `marked(s, field, text)`. | Remotion | `news`, `digest` |
| 4 | **Data Storytelling** (`dataviz`) | A chart that tells a human story: data points drawn mark by mark with handwritten annotations and sonification. | Diverging or sequential data series, pinned callout notes with leaders, pencil/stylus marker, value sonification. | `palette: pack`<br>`fonts: pack` | In 1080×1920, the plot box is taller than wide (aspect ratio ~1:1.2). Value axes run vertically, time/category horizontally. Annotations stack vertically in memory zones left of the like/share rail (x < 940). | Remotion & HyperFrames | `news`, `explainer`, `blog` |
| 5 | **Transit Map** (`transit-map`) | Octilinear metro schematic printed on paper, growing along 8 directions with falling interchange capsules. | 0/45/90° routes, round fillets, interchange capsules, mechanical counter, river/coastline clearance. | `palette: pack`<br>`fonts: pack` | Vertical format naturally represents north-south corridors (e.g. Tbilisi M1 Akhmeteli–Varketili line, or national highway routes). Station labels require halo clearances and strict x < 940 boundary checks. | HyperFrames | `explainer`, `news`, `story` |
| 6 | **Satellite Briefing** (`satellite-briefing`) | Real satellite imagery graded to analyst grey with thin white measurement hairlines, reticles, and readings. | Grey-graded aerial/satellite ground, thin measurement vectors, coordinate readouts, single amber/accent finding. | `palette: pack`<br>`fonts: pack` | **Veasy Georgia Map Law enforced**: Georgia's 12 constitutional regions only; Abkhazia and Tskhinvali drawn as integral parts of Georgia. Never China-view rules. Nadir zoom centers on Georgian municipalities. Coordinates in IBM Plex Mono. | HyperFrames | `news`, `explainer`, `law` |
| 7 | **Engineering Briefing Board** (`briefing-board`) | An enamel whiteboard in a room with cutout real photos, dimension lines, magnets, and stamped verdicts. | Enamel falloff/reflection, cut-out photos casting soft shadows, dimension lines, stamped verdict marks. | `palette: pack`<br>`fonts: pack` | Board coordinates scaled to 1080×1920. Photos placed within the safe zone (y: 248–1380). Georgian dimension markers („მ“, „კმ“, „ლარი“). Photo cutouts strictly verified against commercial reuse licences. | HyperFrames | `explainer`, `blog`, `story` |
| 8 | **Whiteboard Explainer** (`whiteboard`) | An explainer drawn live in dry-erase marker stroke by stroke with floating pens and magnets, no hands. | Live-drawn stroke order, chisel-tip width, dry-erase sheen/ghosts, eraser rewinds, travelling camera. | `palette: pack`<br>`fonts: pack` | Single-line stroke font adapted for Georgian Mkhedruli (33 letters with characteristic loops and descenders). The camera travels vertically down the board rather than panning across an 8000px horizontal expanse. | HyperFrames | `explainer`, `law`, `story` |
| 9 | **Blueprint** (`blueprint`) | Orthographic engineering drawings in white line work on Prussian blue cyanotype paper with live dimensions. | White lines on cyanotype paper, centre lines, hatching, balloons, title block, stamped approval/rejection. | `palette: own` (blue/white)<br>`fonts: pack` | Allowed only where brand explicitly opts in (e.g. SiTech). Prussian blue `#18336B` ground with white ink `#E7F0F9`. In 1080×1920, title block sits in bottom safe area (y: 1280–1380) above captions. Technical Georgian abbreviations. | HyperFrames | `explainer`, `blog`, `story` |
| 10 | **Isometric Infographic** (`iso-infographic`) | True isometric system diorama with three-tone blocks, cutaway sections, and Isotype icon counts. | 30° isometric projection, top/mid/dark facet shading, floating strata plinth, icon grids, leader pins. | `palette: pack`<br>`fonts: pack` | In 1080×1920, the diorama plinth is viewed from high-angle 30° isometric, fitting vertical flow (e.g. high-to-low process, floors of a building, or layered infrastructure). | HyperFrames | `explainer`, `blog`, `story` |
| 11 | **Countdown** (`countdown`) | Real-time multi-camera split-screen counting down to a known zero, merging into one frame at ignition. | Ticking whole-second clock, increasing grid cells (1→2→4→8), live sync badges, explosive merge at T-0. | `palette: pack`<br>`fonts: pack` | Vertical split-screen grid: 2×1, 2×2, 3×2, or 3×3 stacked cards. Central clock occupies prominent mid-band. Fixed-width numerals prevent jitter. Spoken Georgian audio drives real call sync. | Remotion & HyperFrames | `news`, `explainer` |

---

### Second Wave (For Explainers, SiTech & Fiction)

| # | Style | Essence in One Line | At-a-Glance Signature | Palette & Font | Vertical & Georgian Fit | Engine | Programs |
|---|---|---|---|---|---|---|---|
| 12 | **Dark Tech Keynote** (`dark-keynote`) | Precision software keynote: near-black gradient, hairline grid, soft cool glow, one luminous accent. | Dark UI cards, snap-grid animations, glowing status dot, scramble-to-number rolls, generous negative space. | `palette: pack`<br>`fonts: pack` | Natural fit for SiTech tech explainers and modern dark mode. UI components stack vertically; toasts and badges adhere to safe zones. | Remotion & HyperFrames | `blog`, `explainer`, `story` |
| 13 | **Living Screencast** (`living-screencast`) | Software walkthrough where the cursor and windows come alive with sound effects and zoom punches. | Real application windows on clean desktop, cursor acting as protagonist, highlighted regions. | `palette: pack`<br>`fonts: pack` | 1080×1920 mobile or vertical desktop framing. Tested with official allowed domains only (e.g. matsne.gov.ge for law). | HyperFrames | `explainer`, `law`, `blog` |
| 14 | **Sci-fi Hologram HUD** (`hologram-hud`) | Object scanned as glowing wireframe with target locks, local explodes, and rolling telemetry. | Additive cyan/amber wireframes, rotating projector pad, depth fog, target brackets, rolling digits. | `palette: own` (HUD wireframe)<br>`fonts: pack` | Vertical cylinder/turntable view. Coordinates and telemetry fit top/bottom margin gutters. | HyperFrames | `story`, `blog` |
| 15 | **Circuit Board** (`circuit-board`) | Top-down PCB with green solder mask, copper traces, gold pads, and flowing current light. | FR-4 laminate, copper clearances, mitred traces, ENIG gold pads, light pulses representing flow. | `palette: own` (PCB green/gold)<br>`fonts: pack` | 1080×1920 layout routes traces along vertical buses. Current light streams represent logistical or financial flow. | HyperFrames | `explainer`, `story` |
| 16 | **Crayon Picture Book** (`crayon-book`) | Children's book page drawn live in wax crayon with paper tooth boil and watercolor resist. | Heavy wax crayon ribbons, boil on twos (12 fps), child-logic perspective, watercolor wash. | `palette: own` (crayon box)<br>`fonts: own` | Fiction/story only. Patrick Hand or custom Mkhedruli handwriting. Warm off-white paper. | HyperFrames | `story` |
| 17 | **One-line Drawing** (`one-line`) | Continuous ink line that never leaves paper; figures and scenes morph without cutting. | Single unbroken ink line, nib shadow, morphing geometry, live pen-following camera. | `palette: pack`<br>`fonts: pack` | Vertical pathing keeps drawing centered. Single-stroke Georgian script loops. | HyperFrames | `story`, `blog` |
| 18 | **Risograph Print** (`risograph`) | Multi-pass spot-color print with ink overlay multiply, halftone screens, and mechanical misregistration. | Grainy soy ink textures, overprint multiply, slight misregistration offset (1–3 px), paper grain. | `palette: own` (spot inks)<br>`fonts: pack` | 2–3 spot colors. In 1080×1920 reads like a printed vertical indie poster. | HyperFrames | `blog`, `story` |
| 19 | **Halftone Dossier** (`halftone-dossier`) | Investigative case file with high-contrast halftone photostats, redactions, paperclips, and typewriter type. | Coarse halftone dots, stamped REDACTED bars, manila folder ground, typewriter mono. | `palette: pack`<br>`fonts: pack` | Investigative pieces, law violations, historical briefs. Safe zone respected for stamped evidence. | HyperFrames | `law`, `explainer`, `story` |
| 20 | **Silkscreen Poster** (`silkscreen-poster`) | Bold flat-color screenprinted travel or propaganda poster with sharp papercut masks. | 3–4 solid spot color layers, paper cutout geometry, deckled paper borders, high contrast. | `palette: own` (poster inks)<br>`fonts: pack` | Vertical poster tradition fits 9:16 natively. Dramatic graphic landmarks. | HyperFrames | `story`, `blog` |
| 21 | **Mid-century Cartoon** (`midcentury-toon`) | 1950s UPA-style flat animation with asymmetrical abstract shapes, drybrush textures, and boomerang forms. | Boomerang and kidney-bean shapes, misaligned color fills outside outlines, syncopated jazz rhythm. | `palette: own`<br>`fonts: own` | Fiction/entertainment. Highly stylized character designs without realistic rendering. | HyperFrames | `story` |
| 22 | **Paper Pop-up Book** (`paper-popup`) | Dimensional papercraft diorama where folded paper tabs pop out and crease as the page turns. | Folded polygonal paper geometry, cast shadows, score lines, paper hinge mechanics. | `palette: pack`<br>`fonts: pack` | Vertical book spread opening. Layered card stock depth along z-axis. | HyperFrames | `story` |

---

### Proposed Georgian Cultural Style (Owner Proposal)

| Style | Essence in One Line | At-a-Glance Signature | Palette & Font | Vertical & Georgian Fit | Engine | Programs |
|---|---|---|---|---|---|---|
| 23 | **Pirosmani Naive** (`pirosmani-naive`) | Deep black oilcloth canvas with luminous hand-painted figures, animals, and feasts in the spirit of Niko Pirosmani (public domain). | Matte black oilcloth background (`#0D0D0E`), chalk-white and ochre brushwork, bold primitive silhouettes, honest direct gaze, handcrafted Georgian lettering. | `palette: own` (black oilcloth, chalk white, raw umber, ochre, cinnabar red)<br>`fonts: own` | Perfectly fits Georgian cultural history, tourism, wine, national heritage, and historical features. Mkhedruli lettering painted with visible bristle texture. Public domain artistic heritage. | HyperFrames | `story`, `blog`, `explainer` |

---

## 4. Sound Craft & Instrument Modeling

### The Rules
1. **Lemo-Opuscar vs Veasy Invariant**: Lemo-Opuscar heavily advocates music ducking under voice (-10 dB to -18 dB) and riser sweeps. **Veasy's Owner Law explicitly overrides this**:
   > *"One constant level: no build-ups, no ducking (the owner heard the ducked bed pump). The mix happens in ffmpeg (props.mix_audio), not in Remotion."*
   All music and SFX tracks must maintain constant level throughout the video. No pumping, no ducking under speech, no rising risers.
2. **Mastering Standard**: -14 LUFS integrated loudness, true peak ≤ -1.2 dBTP.

### Physical Modeling for Georgian Folk Instruments (`tools/pluck.py` & `tools/sampler.py`)
In Lemo-Opuscar, `pluck.py` implements an extended Karplus-Strong digital waveguide with fractional delay, one-pole damping filter, allpass dispersion, pluck position comb filter, and body resonances. It ships with presets for Chinese (guqin, pipa), Japanese (shamisen, koto), Western folk (banjo, acoustic guitar), and modal percussion (kalimba, music box).

For Veasy, we design physical models and presets for the two canonical Georgian folk string instruments:
1. **Panduri (ფანდური)**:
   - 3-string folk lute popular across eastern and highland Georgia (Kartli, Kakheti, Khevsureti, Tusheti).
   - Tuned typically to a triad or second/fourth: e.g. G4, A4, C5 or E4, B4, A4.
   - Timbre: light, wooden, dry body resonance (conical mulberry or walnut soundbox), bright initial transient from rapid finger strumming or plucking, short decay (~1.8–2.2 s), moderate damping.
   - Waveguide parameters: `t60=2.0`, `damp=0.22`, `pos=0.12`, `exc='finger'`, `nap=1`, `ap=-0.08`, `bright=0.7`, `body=[(180, 6, 1.0), (340, 7, 0.8), (720, 5, 0.5), (1450, 4, 0.3)]`, `bmix=0.48`, `noise=0.04`.
2. **Chonguri (ჩონგური)**:
   - 4-string lute native to western Georgia (Samegrelo, Guria, Adjara).
   - Features 3 long playing strings and a 4th short half-string drone (zilli) tuned an octave or fifth above.
   - Traditional silk or thin nylon strings on a delicate pear-shaped resonant body.
   - Timbre: warm, liquid, soft attack, longer singing sustain, airy resonance, gentle strum rolls.
   - Waveguide parameters: `t60=3.2`, `damp=0.32`, `pos=0.20`, `exc='finger'`, `nap=1`, `ap=-0.04`, `bright=0.45`, `body=[(140, 5, 1.0), (280, 6, 0.85), (580, 5, 0.6), (1100, 4, 0.35)]`, `bmix=0.55`, `noise=0.02`.

### CC0 / CC-BY Instrument Sampler Integration
- Integrated into `tools/sampler.py` and `tools/compose_music.py`.
- Samples are fetched on demand via `fetch.sh` / Python fetchers into local cache, never committed to git.
- Full credits and attribution recorded in `CREDITS`.

---

## 5. Quality Checks & Verification

### 1. `TEXTS(t)` Contract for Composed & Canvas Films
In Remotion, DOM elements are measured by `Probe.tsx`. In composed and canvas films, any element on screen must be readable and conform to reading load standards:
- Contract: `window.TEXTS(t)` returns `[{ id, text, x0, y0, x1, y1 }]` for all visible on-screen text at second $t$.
- Invariants checked:
  1. **Reading Time**: Each text block must remain continuously visible and unchanged for at least:
     $$\text{duration} \ge 0.5\text{ s} + 0.3\text{ s} \times \text{word\_count}$$
  2. **Safe Zone Geometry**:
     - Scene text must end above $y = 1380\text{ px}$.
     - Below $y = 1100\text{ px}$, no text may cross right of $x = 940\text{ px}$ (the like/share rail).
     - Captions must sit above $y = 1552\text{ px}$.
     - No text may sit outside viewport $[0, 0, 1080, 1920]$.

### 2. Georgian Numeral Value Check in Speech QA (`speech.voice_qa()`)
In Lemo-Opuscar, `asr_check.py` converts Chinese and English numbers to numerical values to ensure that numbers are checked by value rather than literal character match.

In Veasy, automated publishing without human review makes numerical accuracy critical. A misspoken number in news is a severe factual failure.
We extend `speech.voice_qa()` to parse Georgian number words and digit expressions:
- Digits: `0`–`9` (ნული, ერთი, ორი, სამი, ოთხი, ხუთი, ექვსი, შვიდი, რვა, ცხრა)
- Teens: `11`–`19` (თერთმეტი, თორმეტი, ცამეტი, თოთხმეტი, თხუთმეტი, თექვსმეტი, ჩვიდმეტი, თვრამეტი, ცხრამეტი)
- Vigesimal bases: `20` (ოცი), `40` (ორმოცი), `60` (სამოცი), `80` (ოთხმოცი), `100` (ასი)
- Scale words: ათასი (1,000), მილიონი (1,000,000), მილიარდი (1,000,000,000)
- Units: პროცენტი (%), ლარი (₾)
- **Check Rule**: If a number in the script (e.g. 19, 6400, 2026) is recognized by ASR as another distinct numeric value (e.g. 15, 6200, 2025), `voice_qa()` flags an unrecoverable failure and blocks the video.

---

## 6. Architecture & Implementation Plan

### `styles/<slug>/style.json` Specification
Each style in `styles/<slug>/style.json` must be declarative data validated by `tt_shorts/styles.py`:
```json
{
  "slug": "swiss-motion",
  "name_en": "Swiss Motion",
  "name_ka": "შვეიცარიული გრაფიკა",
  "category": "graphic-type",
  "engine": "hyperframes",
  "palette": "pack",
  "fonts": "pack",
  "programs": ["news", "explainer", "law", "digest"],
  "deny_families": [],
  "director_picks": ["type", "data", "brief"],
  "look": "editorial",
  "motion": {
    "spring": 0.8,
    "enter_frames": 8,
    "stagger_frames": 2
  },
  "transition": "panel",
  "music_family": "minimal",
  "sfx": true,
  "uses": ["poster-grid", "snap-beat", "extreme-scale"]
}
```

### Brand Law Enforcement
- `palette: pack` styles use the brand pack's tokens (`--canvas`, `--ink`, `--accent`) and brand font (`Brand`). They are allowed for all brands and all programs.
- `palette: own` styles bring their own color schemes. They are **forbidden** in hard news (`news` program) and allowed only if:
  1. The program is not `news` (e.g. `explainer`, `blog`, `story`).
  2. The brand pack explicitly lists the style in its `styles` key (e.g. `brands/sitech/brand.json` lists `"styles": ["blueprint", "dark-keynote"]`).
- `brand.py` and `tests/test_brand.py` validate this allow-list.

### Variety Integration
- `variety.py` rotates styles per brand and program (least used among recent videos).
- The novelty guard fingerprint includes the style slug:
  $$\text{fingerprint} = (\text{style}, \text{director}, \text{scene sequence}, \text{hook}, \text{motif}, \text{enter}, \text{transition}, \text{music})$$
- Ensures that out of 1,000 videos, styles are rotated evenly and no two consecutive videos share identical treatment.

---

## 7. Open Owner Decisions

1. **`palette: own` Styles**:
   - Proposal: Allowed for `sitech` and future commercial brand packs for non-news programs (`explainer`, `blog`, `story`). Strictly disallowed for `tbilisi-today` and any hard news publication.
2. **First Georgian Cultural Style**:
   - Proposal: `pirosmani-naive` (in the spirit of Niko Pirosmani's black oilcloth paintings, public domain) as a premier style for culture, food, wine, and history programs.
3. **Third Engine Decision**:
   - Confirmed by Spike: HyperFrames successfully drives Canvas 2D and WebGL deterministically. No third engine is required.
