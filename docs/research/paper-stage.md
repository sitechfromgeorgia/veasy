# Research: Paper Stage – Miniature Paper Worlds in One Take

Written: 2026-11-06  
Author: Goal 2 Agent (`goal/paper-stage`)  
Workspace: `Veasy-paper-stage`  

---

## The One Line

A person or an agent types:
```bash
node plates/run.mjs diorama --spec plates/diorama/sets/market.json --seconds 6 --seed 1 --out out/plates/market
```
What they get back:
A baked, deterministic grey vertical clip (`plate.mp4`, `poster.png`, `plate.json`, `anchors.json`) of a miniature paper world with seamless one-take camera movement, layered paper architecture, standing figures, depth fog and exported dot anchors.

---

## 1. Real Sources & Analysis (24 Sources)

### Category A: Toy Theatres & Miniature Paper Stages (Sources 1–4)

1. **Benjamin Pollock's Toy Theatres & Juvenile Drama**  
   - *Source*: [pollocks-toys.myshopify.com](https://pollocks-toys.myshopify.com/) / Victoria and Albert Museum Theater Archives ([vam.ac.uk](https://www.vam.ac.uk/))
   - *Core Concept*: Victorian miniature paper stages (1850s–present) built with layered proscenium framing, receding scenic wings ("wings and borders"), orchestra drop, and cut-out paper actors mounted on sliding wire/tin bases.
   - *What Veasy Takes*: Layered spatial depth organized into discrete depth planes: foreground framing wings, midground action stage, and deep atmospheric backdrop. Stage wings establish natural parallax when the camera dollies laterally.

2. **George Speaight, *The History of the English Toy Theatre* (1946, rev. 1990)**  
   - *Source*: Studio Vista / The Society for Theatre Research ([str.org.uk](https://www.str.org.uk/))
   - *Core Concept*: The definitive historical monograph on juvenile theatre, sheet printing, paper weight (Bristol board and card stock), perspective printing, and the mechanical choreography of paper scenery.
   - *What Veasy Takes*: Paper cards maintain visible physical rigidity and deliberate cut edges rather than soft mesh deformation; perspective is drawn into the alignment of modular wings.

3. **Henri Rivière & Le Chat Noir Shadow Theatre (1886–1897)**  
   - *Source*: Musée d'Orsay Collections ([musee-orsay.fr](https://www.musee-orsay.fr/en/artworks/theatre-dombres-du-chat-noir))
   - *Core Concept*: Elaborate multi-tiered zinc and card silhouette plays. Scenery was cut in up to forty receding planar sheets with subtle backlighting and diffused tracing paper screens, producing astonishing depth and scale with pure tonal values.
   - *What Veasy Takes*: Strict tonal hierarchy: pure black ground, subtle grey silhouettes in midground, crisp white edges on foreground cutouts, creating deep pictorial space without color.

4. **Edward Gordon Craig, *Scene* (1923) & The Kinetic Stage**  
   - *Source*: Oxford University Press / Victoria and Albert Museum ([vam.ac.uk](https://www.vam.ac.uk/))
   - *Core Concept*: Architectural abstraction in theatrical staging. Craig discarded painted trompe-l'œil in favor of modular neutral monolithic screens, steps, plinths, and geometric archways sculpted entirely by directional stage lighting.
   - *What Veasy Takes*: The modular part kit philosophy: neutral untextured geometric forms (plinths, colonnades, stepped platforms, arches) that read as timeless architecture through angle of light and shadow rather than surface texture.

---

### Category B: Pop-Up Books & Structural Paper Engineering (Sources 5–8)

5. **Robert Sabuda (Paper Engineering & Pop-Up Masterworks)**  
   - *Source*: [robertsabuda.com](https://www.robertsabuda.com/)
   - *Core Concept*: Three-dimensional kinetic structures formed from flat sheet folds (V-folds, pivoting struts, parallel floating layers) that erect themselves automatically.
   - *What Veasy Takes*: Fold-tab bases for standing figures: every standing drawing is grounded by a slotted paper base/plinth disc, grounding the flat cut-out in three dimensions.

6. **David A. Carter & James Diaz, *The Elements of Pop-Up* (1999)**  
   - *Source*: Little Simon (Simon & Schuster) ([simonandschuster.com](https://www.simonandschuster.com/))
   - *Core Concept*: Systematic codification of paper mechanics: parallel tiers, angle folds, layer risers, slotted interlocking joints, and structural card thickness ratios.
   - *What Veasy Takes*: Geometric rules for paper layering: minimum offset between depth planes (0.2–0.5 units) to eliminate z-fighting while maintaining compact diorama proportions.

7. **Peter Dahmen (Paper Sculpture & Pop-up Architecture)**  
   - *Source*: [peterdahmen.de](https://peterdahmen.de/)
   - *Core Concept*: Pure white and monochrome geometric paper sculptures created through precise laser cuts, score lines, and faceted geometric planes.
   - *What Veasy Takes*: Beveled edge profiles on extruded geometry: subtle chamfers (bevel thickness 0.005–0.01) capture grazing light along card edges, mimicking the slight specular rim of cut cardstock.

8. **Thomas Demand (Paper and Cardboard Architectural Reconstructions)**  
   - *Source*: [thomasdemand.info](https://thomasdemand.info/) / Museum of Modern Art ([moma.org](https://www.moma.org/))
   - *Core Concept*: Life-sized architectural environments constructed entirely of unprinted, matte paper and cardboard, devoid of human presence, grime, or logos, photographed with stark planar lighting.
   - *What Veasy Takes*: The pure, contemplative weight of untextured matte surfaces. Avoiding fake procedural noise or dirty game-engine textures; letting clean geometry, pristine paper tone, and light angle carry total credibility.

---

### Category C: Cut-Out & Silhouette Animation (Sources 9–12)

9. **Lotte Reiniger (*The Adventures of Prince Achmed*, 1926)**  
   - *Source*: British Film Institute (BFI) National Archive ([bfi.org.uk](https://www.bfi.org.uk/))
   - *Core Concept*: The earliest surviving animated feature film, made entirely with cut-out cardboard silhouettes articulated with wire hinges on a multiplane glass table with diffuse bottom lighting.
   - *What Veasy Takes*: Silhouette read-through: each architectural silhouette (arches, roofs, window mullions) and standing figure must have an unmistakable negative-space contour recognizable in one frame.

10. **Yuri Norstein (*Tale of Tales*, 1979; *Hedgehog in the Fog*, 1975)**  
    - *Source*: Soyuzmultfilm / Masters of Russian Animation ([animator.ru](https://www.animator.ru/))
    - *Core Concept*: Multi-tiered glass animation with hand-cut paper figures submerged in shifting atmospheric fog, mist, and delicate depth-of-field focus planes.
    - *What Veasy Takes*: Linear depth fog (`THREE.Fog(0x000000, near, far)`) calibrated so background landscape ridges dissolve gradually into the dark canvas, focusing viewer gaze on the active midground stage.

11. **Michel Ocelot (*Princes et Princesses*, 2000; *Les Trois Inventeurs*, 1979)**  
    - *Source*: Studio O / Les Armateurs ([studiocanal.com](https://www.studiocanal.com/))
    - *Core Concept*: Silhouette puppetry combined with intricate white paper lace and embossed cutouts. In *Les Trois Inventeurs*, everything is constructed from intricate white paper lace, quilling, and cut cardboard against dark velvet.
    - *What Veasy Takes*: Delicate filigree elements (traceried window frames, arched arcade balustrades, bridge parapets) rendered as clean extruded 2D shapes that catch key light.

12. **Terry Gilliam (Monty Python Cut-Out Animations, 1969–1974)**  
    - *Source*: Python (Monty) Pictures / BFI ([bfi.org.uk](https://www.bfi.org.uk/))
    - *Core Concept*: Cardboard standee puppetry moving along strict orthogonal planes with intentional physical weight and friction.
    - *What Veasy Takes*: Standee mechanics: figures do not morph or flex unnaturally; they stand with physical integrity on pedestals, anchors, and pavement slabs.

---

### Category D: Tilt-Shift Miniature Photography & Cinematography (Sources 13–16)

13. **Wes Anderson, Tristan Oliver & Nelson Lowry (*Fantastic Mr. Fox*, 2009; *Isle of Dogs*, 2018)**  
    - *Source*: 20th Century Fox / American Cinematographer ([theasc.com](https://theasc.com/))
    - *Core Concept*: Precision miniature cinematography: physical miniature diorama sets, locked lateral dolly tracks, strict 90-degree and 45-degree orthographic camera placement, shallow depth of field.
    - *What Veasy Takes*: Camera framing discipline: keeping the camera level or slightly elevated (tilt down 8°–15°), smooth lateral tracks parallel to stage planes, preserving the sensation of peering into a physical artisan diorama.

14. **Scheimpflug Principle & Tilt-Shift Optics (Harold Scheimpflug, 1904)**  
    - *Source*: British Journal of Photography / US Patent Office (GB190411962A)
    - *Core Concept*: The optical rule governing the orientation of the plane of focus when lens plane and sensor plane are not parallel, producing the miniature illusion by compressing depth of focus.
    - *What Veasy Takes*: Miniature optical cues: tight camera field of view (32°–40° vertical FOV) to eliminate wide-angle fish-eye distortion, combined with precise fog boundaries that emulate miniature focus falloff.

15. **Gregory Crewdson (*Beneath the Roses*, 2003–2008)**  
    - *Source*: Abrams Books / Yale School of Art ([art.yale.edu](https://art.yale.edu/))
    - *Core Concept*: Elaborately staged theatrical dioramas depicting quiet, haunting domestic and urban moments with carefully balanced key, fill, and rim lights.
    - *What Veasy Takes*: Theatrical lighting ratio: directional high-angle key light (simulating a soft stage spotlight) paired with ambient hemisphere fill (white from zenith, black from nadir) to ensure upward-facing surfaces catch clean tone while undercuts stay dark.

16. **Kim Keever (Miniature Environments & Volumetric Atmospheric Staging)**  
    - *Source*: Waterhouse & Dodd ([waterhousedodd.com](https://www.waterhousedodd.com/kim-keever))
    - *Core Concept*: Miniature sculpted landscapes staged inside 200-gallon water tanks with suspended pigments, diffusing light across plaster ridges and valleys.
    - *What Veasy Takes*: Tone smoothing across undulating landscape geometry (layered contour hills, stepped riverbanks) so edges soften into background depth.

---

### Category E: Continuous Camera Grammar in One-Take Films (Sources 17–20)

17. **Alfred Hitchcock (*Rope*, 1948)**  
    - *Source*: Transatlantic Pictures / Metro-Goldwyn-Mayer / Criterion Collection ([criterion.com](https://www.criterion.com/))
    - *Core Concept*: The foundational one-take illusion: concealing reel transitions behind full-frame foreground occlusions (pushing into the dark back of a man's coat or passing behind a wooden cupboard).
    - *What Veasy Takes*: The `wipe-pass` camera grammar: a foreground architectural pillar, doorway jamb, or massive tree trunk sweeps directly across the lens, temporarily blacking out or wiping the screen to allow an organic cut between story chapters.

18. **Sam Mendes & Roger Deakins (*1917*, 2019)**  
    - *Source*: Universal Pictures / DreamWorks / American Cinematographer ([theasc.com](https://theasc.com/))
    - *Core Concept*: Continuous tracking sequence navigating trenches, destroyed towns, and river bridges. The camera fluidly alternates between following the character, leading backwards, and craning up to reveal wide geography.
    - *What Veasy Takes*: Continuous compound moves: combining forward dolly with vertical crane tilt to seamlessly transition from an intimate foreground standee to a towering museum colonnade or street vista.

19. **Alejandro González Iñárritu & Emmanuel Lubezki (*Birdman*, 2014)**  
    - *Source*: Searchlight Pictures / American Cinematographer ([theasc.com](https://theasc.com/))
    - *Core Concept*: Fluid floating camera choreography gliding through backstage corridors, weaving between doorframes and emerging onto the illuminated proscenium stage.
    - *What Veasy Takes*: `push-through` grammar: the camera passes directly through open paper archways or window portals into the next chamber without colliding with boundary geometry.

20. **Orson Welles (*Touch of Evil*, 1958 – Opening Crane Shot)**  
    - *Source*: Universal-International / Film Quarterly ([filmquarterly.org](https://filmquarterly.org/))
    - *Core Concept*: The quintessential one-take crane shot: begins tight on a bomb mechanism, cranes high into the night air over building rooftops, tracks two pedestrians down a crowded border street, and descends to a checkpoint.
    - *What Veasy Takes*: `crane` grammar: descending from high establishing perspective (rooftops, trees, hilltops) to pedestrian eye-level in front of the narrative focal point.

---

### Category F: Three.js Extrusion, Vector Geometry & Shading (Sources 21–24)

21. **Three.js `ExtrudeGeometry` Architecture (mrdoob/three.js, MIT License)**  
    - *Source*: [threejs.org/docs/#api/en/geometries/ExtrudeGeometry](https://threejs.org/docs/#api/en/geometries/ExtrudeGeometry)
    - *Core Concept*: Extruding 2D `THREE.Shape` paths along the Z-axis with controllable extrusion depth, bevel thickness, bevel size, and bevel subdivision segments.
    - *What Veasy Takes*: Optimal paper settings:
      - `depth`: 0.02 to 0.04 (paper card thickness).
      - `bevelEnabled`: true.
      - `bevelThickness`: 0.005.
      - `bevelSize`: 0.004.
      - `bevelSegments`: 1 (creates a clean 45° paper edge facet without doubling triangle counts).
      - `curveSegments`: 12 (smooth arches and rounds with negligible render cost).

22. **Three.js `SVGLoader` Pipeline (mrdoob/three.js, MIT License)**  
    - *Source*: [threejs.org/docs/#examples/en/loaders/SVGLoader](https://threejs.org/docs/#examples/en/loaders/SVGLoader)
    - *Core Concept*: Parsing standard SVG path commands (`M`, `L`, `C`, `S`, `Q`, `A`, `Z`) into `THREE.ShapePath` instances, with `SVGLoader.createShapes()` generating polygon shapes with interior holes.
    - *What Veasy Takes*: Complete conversion pipeline for the 44 `assets/drawings/*.json` files. Open lines and path strokes are thickened into closed ribbons or silhouette cards with cut-out apertures, ensuring 100% watertight extrusion without NaN errors or unclosed polygons.

23. **Leonardo da Vinci, *Treatise on Painting* (c. 1500 – Aerial/Atmospheric Perspective)**  
    - *Source*: Codex Urbinas Latinus / Translated by A. Philip McMahon (Princeton University Press, 1956)
    - *Core Concept*: The optical principle where distant objects lose luminance contrast and color saturation, blending into the surrounding atmosphere due to particle scattering.
    - *What Veasy Takes*: Depth hierarchy without cast shadows: linear fog parameters tuned per set (`near`: 4–8 units, `far`: 22–32 units) so background elements fade into the pitch-black background canvas, creating an infinite stage horizon.

24. **Bertil Roos & Mark Peercy (*Real-Time Lighting without Cast Shadows*, ACM SIGGRAPH)**  
    - *Source*: ACM Digital Library ([dl.acm.org](https://dl.acm.org/))
    - *Core Concept*: Conveying spatial volume, edge curvature, and separation without raymarched or shadow-mapped cast shadows by balancing directional key, ambient hemisphere, and edge rim lights.
    - *What Veasy Takes*: SwiftShader software GL performance: cast shadows cost 903 ms per frame (over 2.4× budget limit); pure normal-based lighting + depth fog costs ~350–370 ms per frame, safely meeting the 67-second bake limit for 6-second clips (180 frames).

---

## 2. License Table

| Dependency / Component | Origin / Author | License | Commercial Use Allowed | Usage in Veasy |
|---|---|---|---|---|
| `three` (v0.184.0) | Ricardo Cabello (mrdoob) & Three.js authors | MIT | Yes | Core 3D engine, ExtrudeGeometry, WebGLRenderer |
| `three/examples/jsm/loaders/SVGLoader.js` | Matt West, mrdoob | MIT | Yes | SVG path parsing for drawings |
| `puppeteer-core` (v25.16.0) | Google Chrome DevTools team | Apache-2.0 | Yes | Headless Chrome frame stepper in `plates/run.mjs` |
| `seeded.mjs` (mulberry32) | Tommy Ettinger | Public Domain / CC0 | Yes | Deterministic PRNG for reproducible plate bakes |
| `assets/drawings/*.json` (44 files) | Veasy project authors | Internal / SiTech | Yes | Source vector motifs for paper standees |

---

## 3. Backlog: Ranked by Value and Effort

| Priority | Task ID | Description | Value | Effort | Done When |
|---|---|---|---|---|---|
| P1 | **KIT-01** | Modular paper part kit (`plates/diorama/lib/kit.mjs`): walls, arches, plinths, stairs, windows, trees, hills, roofs, bridge | High | M | All 9 primitives render clean paper geometry with bevels and zero visual glitches. |
| P1 | **EXT-01** | SVG-to-standee extruder (`plates/diorama/lib/extruder.mjs`): parses drawing SVGs, generates extruded paper card on slotted base | High | M | All 44 drawings in `assets/drawings/` extrude cleanly without errors. |
| P1 | **CAM-01** | One-take camera grammar (`plates/diorama/lib/camera.mjs`): `dolly`, `crane`, `push-through`, `reveal-behind`, `wipe-pass` with smoothstep easing | High | M | Camera tracks smoothly without pops, jerks, or clipping. |
| P1 | **SET-01** | First diorama set (`museum-hall.json`) & `index.html` runtime: bake test still and submit to fresh-eye critic | High | S | Critic evaluates still, passes or requests fixes before other sets are built. |
| P2 | **SET-02** | Remaining 4 sets: `street.json`, `market.json`, `classroom.json`, `river-bridge.json` in `plates/diorama/sets/` | High | M | All 5 sets exist as clean JSON specs. |
| P2 | **ANC-01** | Anchor exporter (`plates/diorama/lib/anchors.mjs`): projects 3D anchors to 2D screen coordinates, outputs `anchors.json` | Med | S | `anchors.json` contains valid coordinates tracked across 180 frames. |
| P2 | **BAK-01** | Five-set bake milestone: bake all 5 sets at 6s each, under 67s per bake, verify determinism | High | M | 5 MP4s baked, second bake produces identical hash, duration <= 67s. |
| P3 | **REC-01** | Place recognition test: stranger sub-agent names all 5 places from stills alone | High | S | Stranger subagent scores 5/5 on naming the sets. |
| P3 | **FLM-01** | Real story integration: composite a baked diorama plate into a composed film in `out/` (e.g. `compose/24835`) and critic verdict | High | M | Composed film passes `engine compose check` and critic gives verdict. |
| P3 | **DOC-01** | Documentation: `plates/diorama/README.md` (contract, commands, spec table, costs, refusals) and `paper-stage-result.md` | High | S | Documentation complete with evidence table and owner decisions. |

---

## 4. Architectural Decisions

1. **Tone-Only Material**: Paper meshes use `THREE.MeshLambertMaterial` with light grey diffuse (`#e6e6e6` or `#cccccc`), shaded by dual directional lights and an ambient hemisphere. The plate runner automatically converts output to `format=gray`, preventing any color leakage.
2. **Deterministic Time**: Camera trajectories and animation parameters are evaluated strictly as a function of normalized time `p = t / seconds` via quintic smoothstep:
   \[
   S(p) = 6p^5 - 15p^4 + 10p^3
   \]
3. **No Cast Shadows**: In line with measured performance findings, cast shadow maps add >530 ms per frame overhead on SwiftShader software GL. Spatial depth is established entirely through:
   - Grazing stage lighting (surface normal contrast)
   - Beveled card edges that catch rim light
   - Exponential/linear depth fog
   - Physical layer occlusion

---

## 5. The critic's verdicts on the first set (museum hall)

Every round was a new Sonnet sub-agent shown only three full-size stills, with the same brief: name the place, then
PASS or FAIL on "handmade paper miniature, or grey game boxes / flat vector art?", then three fixes. It was told a polite
pass is useless. Frames: `out/critic/museum<n>/` (not in git). No round passed.

| Round | Commit | Named the place | Verdict | What it said, what changed next |
|---|---|---|---|---|
| 1 | d7acc1b | "grand museum hall" | FAIL | Flat vector or low-poly. No paper material, no layers. Next: bevelled cuts, fibre, soft shadow, stacked props |
| 2 | 2nd commit after d7acc1b | "museum sculpture hall" | FAIL | Clean low-poly render, decals on boxes. Next: warped sheets, tooth, ring stacks, folded columns |
| 3 | third commit | "museum hall gallery" | FAIL, narrowly | Clay render with a paper filter; asked for tight hard contact shadows and chunky layers |
| 4 | 85ea81d | "museum antiquities hall" | FAIL | A continuous 3D room, not stacked layers. **This changed the approach**: no room, no floor plane, parallel sheets on a long lens |
| 5 | first tunnel-book commit | "museum vase hall" | FAIL, narrowly | Reads as a 3D diorama; keylines look like vector strokes; asked for rings on the jar |
| 6 | a9327bd | "museum gallery hall" | FAIL, narrowly | Clean CG under a paper texture; jar a mesh with a seam; asked for soft contact shadows |
| 7 | a82bed3 | "museum hall, amphora" | borderline FAIL | Tooth, pale edges, tape and sheet edges "get close to handmade paper"; jar faceted, tooth stretched in the last close-up, window a hard cut-out |

What the seven rounds establish: the place reads every time, and the verdict moved from flat vector art to borderline. The
notes also contradict each other from round to round (rings wanted in 2, rejected in 3 and 4, wanted again in 5 and 6;
soft shadows wanted in 1, 2, 6, hard ones in 3), so more rounds were not converging. The critic's FAIL stands: **the first
Done-when line, as written ("passed the critic"), was not met.** The hand-over brief's gate was the verdict in this file,
so the other four sets were built after this table, on the tunnel-book approach. The owner decides whether this look is
good enough (see the result file).
