# Circuit Board (`circuit-board`)

> Detailed top-down printed circuit board with dark green solder mask, ENIG gold pads, routed copper traces, and flowing current pulses.

## 1. At-a-Glance Signature
- Deep forest green solder mask ground (`#0A1D13`) with subtle FR-4 woven glass epoxy texture.
- 45° mitred copper traces running along vertical and horizontal buses.
- ENIG electroless nickel immersion gold pads (`#F59E0B`), surface-mount component footprints, and thermal vias.
- Dynamic current pulses of light flowing along traces to represent data, logic, or financial transactions.

## 2. Brand & Program Rules (Strict)
- **Palette: Own**: PCB green ground (`#0A1D13`), gold pad highlights (`#F59E0B`), bright signal copper (`#34D399`), and silkscreen white (`#F9FAFB`).
- **Brand Law Invariant**: **Forbidden for news programs (`news`)**. Allowed only for technology explainers, infrastructure analysis, and tech blog posts, and **only when explicitly listed in `brand.json` under `"styles"`** (e.g. SiTech).

## 3. Vertical (1080×1920) Geometry & Safe Zones
- PCB canvas: 1080×1920 px. Primary IC chip or processor package centered in mid-frame ($y \in [600, 950]$).
- Bus lanes route vertically along left and right margins ($x \in [80, 200]$ and $x \in [840, 940]$).
- Safe boundary: all silkscreen text and circuit callouts stay within $y \le 1380$; captions occupy $y \in [1380, 1552]$.
- Right social clearance: $x \le 940$ below $y = 1100$.

## 4. Georgian Mkhedruli Typography
- Technical silkscreen white labels rendered in `IBM Plex Mono 500` or `FiraGO 600`.
- Component designators (e.g. `U1`, `R12`, `C4`) and bus labels (e.g. `მონაცემთა ავტობანი 64-bit`).
- Copper layer text mirrored where appropriate.

## 5. Motion & Animation Rules
- Current flow: illuminated light beads travel along circuit traces from power/input terminals to the processor.
- Component pop: microchips and capacitors drop onto pads with microscopic solder reflow flashes.
- Transitions: signal trace wipe or vertical PCB panning.

## 6. Sound Craft
- Focused analog electronic synthesizer pulse.
- Constant volume without ducking or pumping.
- SFX: subtle capacitor discharge click (`click`), data bus blip (`blip`), relay pop (`pop`).
