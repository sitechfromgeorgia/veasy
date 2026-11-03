---
name: styles
description: "Use when choosing, previewing, or customizing a named film style (styles/<slug>) for a video or a brand pack, adapting a style to a brand pack, or when asked which visual styles Veasy has. Examples: \"render this in swiss-motion style\", \"make a style for SiTech based on blueprint\", \"which film styles do we have\", \"customize countdown style for our brand\""
---

# Named film styles

Film styles in Veasy (`styles/<slug>/`) define named visual and motion aesthetics as pure data that a person or an agent
can specify with a single parameter (`--style <slug>`). Adapted from the principles of `lemo-opuscar`, every style is
re-engineered for vertical (1080×1920) Georgian Mkhedruli video, Veasy's brand law, safe zones, and news law.

Styles require **no video model** (pure deterministic code animation via Remotion or HyperFrames).

```bash
python -m tt_shorts.engine options                  # "styles": every known film style and summary
python -m tt_shorts.engine render <story> --style swiss-motion
python -m tt_shorts.engine still <story> --style blueprint --format explainer
python -m tt_shorts.engine plan <story> --style countdown
```

## The 18 Shipped Film Styles

### Wave 1: Brand-Safe Styles (Pack Palette & Typography)
Every brand-safe style operates in `palette: pack` mode, respecting the active brand pack's colors and fonts:

| Slug | Georgian Name | English Name | Visual Essence | Primary Engine |
|---|---|---|---|---|
| `swiss-motion` | შვეიცარიული მოძრაობა | Swiss Motion | Rigid asymmetrical grid, bold typography, mathematical spacing | `remotion` |
| `pictogram-motion` | პიქტოგრამული ანიმაცია | Pictogram Motion | Clean geometric pictograms, narrative transformations | `remotion` |
| `caption-news` | ტიტრების ამბავი | Caption News | Kinetic typography hero, word-by-word visual emphasis | `remotion` |
| `data-storytelling` | მონაცემთა თხრობა | Data Storytelling | Dynamic statistics, animated comparative charts and dissection | `remotion` |
| `transit-map` | სატრანზიტო რუკა | Transit Map | Metro/rail topology, animated route paths, interchange nodes | `hyperframes` |
| `satellite-briefing` | სატელიტური ბრიფინგი | Satellite Briefing | Cartographic briefing respecting Georgia's constitutional regions | `hyperframes` |
| `engineering-briefing` | საინჟინრო დაფა | Engineering Briefing | Telemetry HUD, technical grids, monospace data readouts | `hyperframes` |
| `whiteboard-explainer` | თეთრი დაფა | Whiteboard Explainer | High-contrast marker aesthetics, organic sketched reveals | `hyperframes` |
| `blueprint` | საინჟინრო ნახაზი | Blueprint | Architectural drafting blueprint, cyan lines, dimension marks | `hyperframes` |
| `isometric-infographic` | იზომეტრიული ინფოგრაფიკა | Isometric Infographic | 30-degree isometric projection, stacked volumetric layers | `hyperframes` |
| `countdown` | ათვლა | Countdown | Large central numeric counter, urgent cadence, dramatic holds | `remotion` |

### Wave 2: Expressive Styles
| Slug | Georgian Name | English Name | Visual Essence | Primary Engine |
|---|---|---|---|---|
| `terminal-ascii` | ტერმინალი | Terminal ASCII | Retro CRT terminal phosphor glow, monospace character grid | `hyperframes` |
| `risograph` | რიზოგრაფი | Risograph | Ink misregistration, vibrant duotone overlays, grain texture | `hyperframes` |
| `paper-cutout` | ქაღალდის აპლიკაცია | Paper Cutout | Multi-plane paper collage, tactile stop-motion shadow depth | `hyperframes` |
| `circuit-board` | მიკროსქემა | Circuit Board | Copper PCB traces, pulsing routed signals, illuminated ICs | `hyperframes` |
| `crayon-book` | ცვილის ფანქარი | Crayon Book | Expressive wax crayon strokes, tactile storybook sketch fills | `hyperframes` |
| `hologram-hud` | ჰოლოგრამა | Hologram HUD | Translucent sci-fi HUD projection, reticles, scanline telemetry | `hyperframes` |

### Cultural Proposal
| Slug | Georgian Name | English Name | Visual Essence | Primary Engine |
|---|---|---|---|---|
| `pirosmani-naive` | ფიროსმანის სტილი | Pirosmani Naive Art | Niko Pirosmani aesthetic: black oilcloth, earthen pigments, monumental stillness | `hyperframes` |

---

## Brand Law and Palette Modes

1. **`palette: pack`**:
   The style adapts directly to the client's brand pack tokens (`canvas`, `ink`, `accent`, etc.) and the brand font family.
   Allowed for all brands and all programs including news.

2. **`palette: own`**:
   The style specifies its own unique aesthetic palette (`blueprint`, `circuit-board`, `crayon-book`, `hologram-hud`, `pirosmani-naive`).
   - **Hard Rule**: Strictly prohibited for news programs (`news`).
   - **Brand Allow-List**: For non-news programs (`explainer`, `blog`), allowed only if explicitly listed in the brand's `brand.json` under `"styles": ["blueprint", ...]`.

3. **Variety Rotation**:
   When no style is explicitly requested, `variety.pick_style()` automatically selects the least recently used eligible style
   for that brand, program, and family. The novelty guard monitors style choices and prevents repetitive rendering.

---

## "Make a Style Your Own" (Pack Customization Interview)

When an agent or user wants to customize a style for a brand pack (`brands/<name>/styles/<slug>/`):

The agent conducts an interactive interview, asking **one question at a time**:

### 1. Inquire on "Safe to Change"
Aspects that tune the style to the brand without altering its identity:
- Subtle accent color adjustments within the brand palette.
- Background grid opacity or watermark intensity.
- Typography scale ratio (e.g. 1.2 vs 1.25 for headings).

### 2. Inquire on "Changes the Character"
Aspects that shift the mood or pacing:
- Animation timing curves (snappy cubic-bezier vs smooth linear deceleration).
- Corner rounding (sharp architectural corners vs rounded friendly corners).
- Layout density (compact dashboard vs spacious poster layout).

### 3. Guard the "Can't Change" (Hard Veasy Laws)
The agent strictly enforces:
- **Safe Zone**: Scene text ends at $y=1380$; captions at $y=1552$; below $y=1100$ no text right of $x=940$.
- **News Law**: News programs never use opinion scenes or unverified numbers; sources and time remain on screen.
- **Sound Law**: Constant audio level, loudness spread $\le 0.8\text{ dB}$, no ducking under voice, no risers.
- **Typography**: Text on screen is Georgian Mkhedruli using the approved brand font (FiraGO).

### 4. Verification & Save
1. Generate preview stills:
   ```bash
   python -m tt_shorts.engine still <story> --style <slug> --format <format> --out <preview_dir>
   ```
2. Display the generated still next to the base style frame.
3. Save to `brands/<name>/styles/<slug>/style.json` and `STYLE.md` **only when the user explicitly approves**.

---

## Related Skills

- For brand pack configuration and colors: see skill `veasy:brands`.
- For show formats and lengths: see skill `veasy:formats`.
- For composing custom HyperFrames films: see skill `veasy:compose`.
- For directors and fact-based framing: see skill `veasy:directors`.
- For video creation commands: see skill `veasy:make-video`.
