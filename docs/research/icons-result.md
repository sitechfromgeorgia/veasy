# Veasy Visual Vocabulary: Icons, Pictograms & Seed Drawings (Goal 2 Result)

> **Branch:** `goal/icons`  
> **Worktree:** `D:\MyStaff\Veasy-icons`  
> **Baseline:** Commit `3a6ce8a`  
> **Status:** All deliverables complete, all gates passing green.

---

## 1. Executive Summary

Goal 2 expands Veasy's visual vocabulary across four interlocking dimensions:
1. **Stem & Blocker Coverage:** Expanded Georgian word stem mappings in `tt_shorts/icons.py` from 618 to 890 stems (+272 new stems), mapped all 13 previously unmapped library icons, and established strict blocker filters for false-friend look-alikes.
2. **Icon Motion Vocabulary:** Implemented 6 deterministic, frame-exact animation styles (`draw`, `pop`, `pulse`, `count`, `morph`, `sketch`) in `tt_shorts/icons.py`, `remotion/src/icons.tsx`, and `remotion/src/scenes/sign.tsx`, adhering strictly to the brand rule that accent is only applied to the dot focal point.
3. **Isotype & Pictogram Charts:** Added part-of-whole pictogram charts ($n$ lit items out of $total$, e.g., "7 out of 10") and standalone unit charts, strictly gated by News Rule N10 (no pictograms for crime, incidents, or deaths; action verbs must be spoken in the narration).
4. **Seed Drawings Library:** Authored 26 new hand-crafted SVG seed drawings in `assets/drawings/` (total library grown from 18 to 44 seeds), covering transport, aviation, maritime, energy, telecommunications, agriculture, and civic infrastructure. Every drawing passes `art.py` (`sanitize` and `quality`) and `tests/test_drawings.py`.
5. **Contact Sheet Tooling:** Created `python -m tt_shorts.engine contact-sheet`, generating a responsive, interactive HTML catalog of all 250 icons and all 44 drawings across all 4 brand themes (`sitech:dark`, `sitech:light`, `tbilisi-today:dark`, `tbilisi-today:light`).

---

## 2. Commit List

| Commit | Summary | Scope |
|---|---|---|
| `bb5781c` | `docs(icons): research icon systems, pictogram traditions and SVG animation` | Research document covering 28 sources, licensing matrix, Isotype traditions, and ranked backlog |
| `8f32f33` | `feat(icons): add 100+ Georgian stems and look-alike blockers in icons.py` | Added 272 Georgian stems, mapped 13 unmapped icons, added false-friend blockers |
| `6db76f1` | `feat(icons): add icon motion vocabulary (pop, pulse, count, morph, sketch) and part-of-whole isotype charts` | Remotion icon motion engines, shape extractors, morph interpolation, part-of-whole isotype |
| `91e196f` | `feat(drawings): add 26 new seed drawings for common civic, transport, and infrastructure motifs` | 26 new seed drawings in `assets/drawings/`, updated `test_drawings.py` |
| `4f4c6ed` | `feat(tools): add contact-sheet generator for icons and seed drawings across all themes` | Contact sheet generator module `tt_shorts/contact_sheet.py` & CLI subcommand in `engine.py` |
| `2645cee` | `test(demo): demo new icon motions and part-of-whole isotype in veasy-icons` | Enhanced `stories/veasy-icons.json` exercising draw, pop, count, sketch, morph |

---

## 3. Shipped Components & Capabilities

### 3.1. Georgian Stem Coverage (`tt_shorts/icons.py`)
- **Stems Count:** Total stems increased from 618 to 890 (+44% expansion).
- **Domain Coverage:**
  - *Energy & Utilities:* Hydro dams (`კაშხალ`, `ჰეს`), solar energy (`მზის_პანელ`), gas pipes, grid power (`დენ`, `ქვესადგურ`).
  - *Transport & Logistics:* Aviation (`თვითმფრინავ`, `ავიარეის`), maritime (`გემ`, `ბორან`, `საზღვაო`), freight (`სატვირთო`, `ტრაილერ`), rail (`მატარებელ`, `რკინიგზ`).
  - *Civic & Legal:* Courts (`სასამართლო`, `მოსამართლ`), town hall (`მერია`, `საკრებულო`), embassies (`საელჩო`).
  - *Finance & Economy:* Contactless cards (`საბანკო_ბარათ`, `ტერმინალ`), currency (`ლარ`, `ვალუტ`), inflation/pricing (`გაძვირებ`, `ფასდაკლებ`).
  - *Technology & IT:* Silicon chips (`მიკროჩიპ`, `პროცესორ`), servers (`სერვერ`, `მონაცემთა_ბაზ`), satellites (`თანამგზავრ`).
  - *Agriculture & Culture:* Grain harvest (`მარცვლეულ`, `მოსავალ`), Georgian qvevri wine (`ქვევრ`, `ღვინ`).
- **All 13 Unmapped Icons Resolved:**
  - `moon` (ღამ, მთვარ), `power` (ჩართვ, გამორთვ), `plug-zap` (შტეფსელ), `droplets` (ნალექ), `battery-charging` (დამუხტვ), `door-open` (ღია_კარ), `door-closed` (დაკეტილ_კარ), `package` (ამანათ), `sparkles` (განახლებ), `banknote-arrow-up` (შემოსავალ), `banknote-arrow-down` (ხარჯ), `signpost` (მიმართულებ), `lock-open` (განბლოკვ).
- **False-Friend Blockers Added to `_BLOCK`:**
  - `ტარებ` (prevented false vehicle match on general action verbs), `ენერგიულ` (prevented false zap match on personality trait), `გაზიან` (prevented false flame match on carbonated water), `ბაზრობ` (prevented false database match on market fairs), `სალარო` (prevented false tag match on cash register), `კოდირებ` (prevented false code match on medical coding).

### 3.2. Icon Motion Vocabulary (`remotion/src/icons.tsx` & `tt_shorts/icons.py`)
Deterministic, frame-exact animations evaluated as pure functions of `frame`:
- **`draw` (default):** Stroke draw-on using `strokeDasharray` and `strokeDashoffset`, revealing paths in ink rhythm over 15–20 frames.
- **`pop`:** Spring dynamic scale punch (`popScale`: $0 \to 1.14 \to 1.0$), giving tactile emphasis to breaking alerts.
- **`pulse`:** Subtle breathing oscillation (`pulseScale`: $\pm 4\%$, period 40 frames) for ongoing status indicators.
- **`count`:** Staggered unit reveal for isotype arrays, sequential delay per item ($k \times 3$ frames) with soundblip sync.
- **`morph`:** Shape interpolation from `morph_from` glyph to target `icon` glyph (matching path point counts and coordinates smoothly).
- **`sketch`:** Hand-drawn micro-jitter offset using pseudo-random deterministic noise based on glyph shape indices.
- **Brand Rule Compliance:** The brand accent is never applied to icon line strokes or text; accent is strictly reserved for the focal dot.

### 3.3. Isotype & Part-of-Whole Charts (`remotion/src/icons.tsx`, `remotion/src/scenes/sign.tsx`)
- **Part-of-Whole Isotype:** Displays $n$ illuminated icons against $total - n$ muted icons (e.g. 7 filled, 3 muted for 70%).
- **Standalone Unit Chart:** Responsive multi-row pictogram matrix with dynamic cell sizing (up to 30 units).
- **News Rule N10 Strictness:** Gated against crime, casualty, and death stories; verbs must match spoken narration.

### 3.4. Seed Drawings (`assets/drawings/`)
26 new line-art schematic drawings added (44 total in repository):
1. `airplane.json` (`plane`): Passenger airliner on runway preparing for departure.
2. `ambulance-car.json` (`ambulance`): Emergency medical vehicle with lightbar and red cross emblem.
3. `cargo-ship.json` (`ship`): Container cargo ship navigating waves.
4. `credit-card.json` (`credit-card`): Contactless smart card and payment terminal with PIN pad.
5. `dam-hydro.json` (`dam`): Hydroelectric dam wall with spillway flumes and powerhouse.
6. `database-server.json` (`database`): Server rack cabinet with blade units and cable run.
7. `drone-flight.json` (`drone`): Multirotor aerial drone with camera gimbal and spinning propeller disks.
8. `electric-charger.json` (`ev-charger`): EV fast charger station with heavy cable and plug handle.
9. `fire-truck.json` (`siren`): Emergency fire engine with folding rescue ladder and equipment shutters.
10. `forest-nature.json` (`tree-pine`): Mountain evergreen forest conservation reserve.
11. `graduation.json` (`graduation-cap`): Academic mortarboard cap with hanging tassel and rolled diploma scroll.
12. `hotel-building.json` (`hotel`): Multi-story urban hotel with glass canopy entrance.
13. `laptop-code.json` (`laptop`): Portable notebook computer displaying syntax code lines.
14. `microchip-circuit.json` (`microchip`): Semiconductor silicon processor package with motherboard bus traces.
15. `police-car.json` (`shield`): Patrol vehicle with security shield door badge and roof beacon.
16. `radio-antenna.json` (`radio-tower`): Steel broadcast mast emitting concentric signal waves.
17. `satellite-orbit.json` (`satellite`): Communication satellite with photovoltaic solar arrays and parabolic dish.
18. `solar-farm.json` (`solar-panel`): Ground-mounted photovoltaic solar panel array with inverter box.
19. `supermarket-cart.json` (`shopping-cart`): Supermarket retail shopping trolley with packaged goods.
20. `traffic-barrier.json` (`traffic-cone`): Roadworks striped barrier and reflective cone.
21. `truck-freight.json` (`truck`): Heavy freight semi-trailer for logistics transit.
22. `warehouse-logistics.json` (`warehouse`): Logistics fulfillment center with high-bay loading docks.
23. `weather-station.json` (`cloud-rain`): Meteorological monitoring station measuring rain and wind speed.
24. `wheat-harvest.json` (`wheat`): Agricultural ear of wheat spikelets with awns.
25. `wind-turbine.json` (`wind`): Renewable wind generator turbine on hillside.
26. `wine-qvevri.json` (`amphora`): Traditional Georgian clay qvevri wine vessel with cellar base.

### 3.5. Contact Sheet Tool (`tt_shorts/contact_sheet.py`)
- Generated interactive HTML contact sheet: `D:\MyStaff\Veasy-icons\out\contact-sheet.html`.
- Displays all 250 Lucide icons and all 44 seed drawings in all 4 brand themes:
  - `sitech:dark` (Coal `#171817` canvas, Paper `#F1EDE4` ink, Orange `#FF792E` accent)
  - `sitech:light` (Paper `#F1EDE4` canvas, Coal `#171817` ink, Orange `#FF792E` accent)
  - `tbilisi-today:dark` (Night `#05080F` canvas, White `#F8FAFC` ink, Red `#EF4444` accent)
  - `tbilisi-today:light` (Slate `#F8FAFC` canvas, Night `#05080F` ink, Red `#EF4444` accent)
- Features instant client-side theme switching and live Georgian stem/English search filtering.

---

## 4. Visual Verification & Generated Stills

### 4.1. Layout Probe
Executed across all three looks:
`python -m tt_shorts.engine probe stories/veasy-icons.json --look all`
- **Results:**
  - `editorial`: 0 problems, 0 issues, safe zone compliant (text ends at $y=1380$, captions at $y=1552$, no text right of $x=940$ below $y=1100$).
  - `kinetic`: 0 problems, 0 issues, safe zone compliant.
  - `cards`: 0 problems, 0 issues, safe zone compliant.

### 4.2. Rendered Stills
Rendered via `python -m tt_shorts.engine still stories/veasy-icons.json --look <look> --engine silent`:
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-icons-cards-page-silent-148.png` (Hook)
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-icons-cards-page-silent-379.png` (Sign: Flame, draw-on motion)
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-icons-cards-page-silent-532.png` (Sign: Price tag, pop motion)
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-icons-cards-page-silent-693.png` (Stat: 7/10 Bus isotype part-of-whole chart)
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-icons-cards-page-silent-857.png` (Sign: School, sketch motion)
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-icons-cards-page-silent-1054.png` (Sign: Sun, morphing from moon)
- `data/renders/tbilisi-today/2026-11-03/stills/tbilisi-today-veasy-icons-cards-page-silent-1253.png` (End card)
- Equivalent sets generated for `editorial` and `kinetic` looks (total 21 still frames).

---

## 5. Files Touched Outside Lane (For Coordination)

All changes were strictly additive to prevent conflicts with concurrent goals:
1. `remotion/src/types.ts` (Goal 1 & Goal 3 overlap):
   - Added `IconMotion = "draw" | "pop" | "pulse" | "count" | "morph" | "sketch"`.
   - Added `motion?: IconMotion`, `morphGlyph?: Node[]`, `chart?: "isotype" | "part_of_whole" | "unit_chart"` to `Scene`.
2. `remotion/src/scenes/sign.tsx` (Goal 1 overlap):
   - Added support for `motion`, `morphGlyph`, and part-of-whole isotype in `Sign` and `Isotype`.
   - Added standalone `UnitChart` component.
3. `tt_shorts/engine.py` (Goal 5 overlap):
   - Added CLI subcommand `contact-sheet` (`contact_sheet_cmd`) and help parser.
4. `stories/veasy-icons.json`:
   - Updated test story to exercise new icon motions and part-of-whole isotype chart.

---

## 6. What Was NOT Done & Why

1. **Category Tints (plan-v2 § 8.2):**
   - Ground rules explicitly state: *"Tints (plan-v2 § 8.2) are an owner decision: don't add them."*
   - Strictly preserved monochrome light ink on dark canvas with the single brand accent dot.
2. **Mixing Secondary Icon Sets:**
   - Lucide was preserved as the single canonical stroke style (24px grid, 2px stroke, round caps/joins).
   - Mixing multiple icon libraries within a video violates visual consistency ("*one stroke style per video: never mix sets in one film*").
3. **Overriding Baseline Windows Failures:**
   - The 1 baseline failure in `tests/test_plugin.py` (`test_claude_code_sees_the_same_skills`) is a known Windows git symlink issue owned by Goal 5 and was not touched.

---

## 7. Open Owner Decisions

1. **Tint Color Policy:**
   - Whether to allow optional category tints (e.g. muted cyan for water, soft amber for energy) or enforce strict brand monochrome ink.
2. **Alternative Stroke Sets at Brand Level:**
   - If a brand pack ever requests an alternate style (e.g. geometric sharp corners or dual-tone strokes), whether to support switching the entire set at the brand level via `assets/icons/<set>.json`.
3. **Contact Sheet Surfacing in Hermes Plugin (Goal 5):**
   - Goal 5 can expose `python -m tt_shorts.engine contact-sheet` as an agent tool or UI panel for live review.
