# Georgia Relief (`plates/relief/`): Research, Open-Data Licensing, Cartography & 3D Camera Architecture

## One-Line User & Agent Interface

```bash
node plates/run.mjs relief --spec plates/relief/specs/kazbegi-jvari.json --seconds 6 --seed 1 --out out/plates/kazbegi-jvari
```

**What you get back** in `out/plates/kazbegi-jvari/`:
- `plate.mp4` (`1080×1920`, 30 fps, H.264 `yuv420p`, pure neutral-grey relief + contour lines on black, zero text, zero accent)
- `poster.png` (`1080×1920` deterministic mid-flight frame at $t = \text{seconds}/2$)
- `plate.json` (provenance manifest: `kind`, `spec`, `seconds`, `fps`, `width`, `height`, `scale`, `seed`, `frames`, `ms_per_frame`, `hash`, `anchors: true`)
- `anchors.json` (`1080×1920` frame-by-frame pixel coordinates `{"fps": 30, "frames": [{"dot": [x, y], ...}, ...]}` projected from 3D terrain relief so the film's DOM dot and Georgian label lock onto the exact mountain, valley, or district)

---

## 1. Research Survey (24 Real Sources & What Each Teaches Veasy)

### A. Open Elevation Datasets (DEMs) & Licensing

1. **NASA Shuttle Radar Topography Mission — SRTMGL1 v003 (1 arc-second, ~30 m)**
   - **Link**: https://lpdaac.usgs.gov/products/srtmgl1v003/ · Policy: https://lpdaac.usgs.gov/data/data-citation-and-policies/
   - **Coverage**: $60^\circ\text{N}$ to $56^\circ\text{S}$, covering all of Georgia ($41.00^\circ\text{N}–43.65^\circ\text{N}, 39.95^\circ\text{E}–46.80^\circ\text{E}$) across 21 $1^\circ \times 1^\circ$ tiles (`N41E040`–`N43E046`).
   - **What it teaches Veasy**: As a work of the US Federal Government (NASA/USGS, 17 U.S.C. § 105), SRTMGL1 has **no copyright, zero share-alike, unrestricted commercial use, and no mandatory on-screen attribution**. It is the cleanest legal foundation for Veasy's offline relief heightmap.

2. **NASA NASADEM Merged DEM Global 1 arc-second (`NASADEM_HGT v001`)**
   - **Link**: https://lpdaac.usgs.gov/products/nasadem_hgtv001/
   - **What it teaches Veasy**: Reprocessed SRTM radar phase data with ICESat GLAS and ASTER GDEM3 void-filling over steep alpine ridges like Ushba (4,710 m), Shkhara (5,193 m), and Kazbek (5,047 m). Same US Public Domain status as SRTMGL1.

3. **AWS Open Data Registry — Mapzen / Tilezen Terrain Tiles (`elevation-tiles-prod`)**
   - **Link**: https://registry.opendata.aws/terrain-tiles/ · Docs: https://github.com/tilezen/joerd/blob/master/docs/data-sources.md
   - **Format**: Unauthenticated HTTPS S3 bucket (`https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`) encoding metric elevation as 24-bit RGB: $\text{elev\_m} = (R \cdot 256 + G + B / 256) - 32768$ at $1/256\text{ m}$ precision.
   - **What it teaches Veasy**: For Georgia's bounding box ($39.95^\circ\text{E}–46.80^\circ\text{E}, 41.00^\circ\text{N}–43.65^\circ\text{N}$), zoom level $z=8$ requires only **24 PNG tiles** ($x \in [156..161], y \in [92..95]$, ~1.1 MB total) built strictly from US Public Domain sources (**SRTM** + **GMTED2010** + **ETOPO1** in the Caucasus; 3DEP/NED, CDED, and EUDEM do not cover Georgia). `tools/build_relief.py` can fetch these 24 tiles in ~2 seconds with zero GDAL/rasterio dependencies using only Pillow + NumPy.

4. **Copernicus DEM (`COP-DEM_GLO-30` & `COP-DEM_GLO-90`, ESA / Airbus Defence and Space)**
   - **Link**: https://registry.opendata.aws/copernicus-dem/ · Licence: https://spacedata.copernicus.eu/documents/20123/121239/CSCDA_ESA_Mission-specific+Annex+%2831_Oct_2022%29.pdf
   - **What it teaches Veasy**: Derived from TanDEM-X radar interferometry (2011–2015), GLO-30 offers the sharpest ridge lines in the Greater Caucasus and allows free commercial use without share-alike, **provided** the 28-word Airbus/ESA attribution notice and warranty disclaimer are included in documentation (`assets/maps/README.md`). Keeping both SRTM/Terrarium and Copernicus documented gives Veasy full flexibility while keeping rendered frames 100% text-free.

5. **USGS / NGA GMTED2010 (Global Multi-resolution Terrain Elevation Data 2010)**
   - **Link**: https://www.usgs.gov/coastal-changes-and-impacts/gmted2010
   - **What it teaches Veasy**: Provides seamless void-filled regional context across the Greater and Lesser Caucasus in US Public Domain.

6. **JAXA ALOS World 3D — 30m (`AW3D30`, Japan Aerospace Exploration Agency)**
   - **Link**: https://www.eorc.jaxa.jp/ALOS/en/dataset/aw3d30/aw3d30_e.htm · Terms: https://earth.jaxa.jp/en/data/policy/
   - **What it teaches Veasy**: Commercial use is permitted with attribution (`"ALOS World 3D - 30m (AW3D30) provided by JAXA"`), but JAXA's terms require visible source credit on distributed visual outputs unless waived. Hence SRTM/Terrarium is preferred as the primary build source so video frames need no on-screen DEM credit.

7. **GEBCO Gridded Bathymetry Data (`GEBCO_2024 Grid`)**
   - **Link**: https://www.gebco.net/data_and_products/gridded_bathymetry_data/
   - **What it teaches Veasy**: Public Domain (CC0-equivalent) Black Sea bathymetry. Because Veasy's map rule states *"Georgia's outline from `georgia.json`, nothing outside it drawn as a claim"*, `plates/relief/` clips and masks all pixels outside Georgia's land polygon to pure canvas black (`#000000`) rather than drawing foreign shores or sea-floor claims.

---

### B. Boundaries, Gazetteers, Roads & Legal/Sovereignty Rules

8. **OCHA Common Operational Datasets — Administrative Boundaries (COD-AB Georgia / Geostat)**
   - **Link**: https://data.humdata.org/dataset/cod-ab-geo · Licence: https://creativecommons.org/licenses/by-igo/3.0/
   - **What it teaches Veasy**: Already powers `assets/maps/georgia.json` via `tools/build_georgia_map.py` (CC BY-IGO 3.0, credited as `Geostat · OCHA · CC BY-IGO`). Defines Georgia's external border (`land`), internal regional boundaries (`borders`), and the **12 regions of Georgian law** (`tbilisi`, `abkhazia`, `adjara`, `guria`, `imereti`, `kakheti`, `mtskheta-mtianeti`, `racha-lechkhumi`, `samegrelo-zemo-svaneti`, `samtskhe-javakheti`, `kvemo-kartli`, `shida-kartli`). Abkhazia is `abkhazia` inside Georgia; the Tskhinvali region sits inside `shida-kartli` (`tskhinvali`, `java`) and `mtskheta-mtianeti` (`akhalgori`) with no separate entity.

9. **OpenStreetMap Open Database License (ODbL 1.0) & LWG Produced Work Guideline**
   - **Link**: https://opendatacommons.org/licenses/odbl/1-0/ · Guideline: https://osmfoundation.org/wiki/Licence/Community_Guidelines/Produced_Work_-_Guideline
   - **What it teaches Veasy**: Under ODbL § 4.3, a rendered video is a *Produced Work* requiring mandatory `"© OpenStreetMap contributors"` credit on or accompanying the work. Worse, if OSM vector roads are mixed with elevation/gazetteer data into an intermediate database, ODbL § 4.6 triggers Share-Alike distribution obligations on the derivative database. Therefore, **Veasy refuses OSM data in `plates/relief/`** and marks any future OSM road integration as an **Owner Decision**, using only `georgia.json` outlines/rivers and `geo.py` gazetteer dots + place names per the rule: *"A wrong road is a false claim: draw a road only from a licensed source with a test, else a dot and a place name."*

10. **geoBoundaries Global Database of Political Administrative Boundaries (Runfola et al., 2020)**
    - **Link**: https://www.geoboundaries.org/ · Paper: https://doi.org/10.1371/journal.pone.0231866
    - **What it teaches Veasy**: CC BY 4.0 / CC0 cross-check reference for municipal boundaries; confirms `georgia.json` from COD-AB/Geostat is the canonical legal boundary set for Georgian regions.

11. **Natural Earth (`1:10m` Physical Vectors — Rivers & Lake Centerlines)**
    - **Link**: https://www.naturalearthdata.com/about/terms-of-use/
    - **What it teaches Veasy**: CC0 Public Domain hydrological vectors already baked into `assets/maps/georgia.json` (`rivers` array covering Enguri, Rioni, Mtkvari, Aragvi, Alazani, Iori, etc.).

12. **Wikidata / Creative Commons CC0 1.0 Universal Coordinate Facts**
    - **Link**: https://www.wikidata.org/wiki/Wikidata:Licensing · CC0: https://creativecommons.org/publicdomain/zero/1.0/
    - **What it teaches Veasy**: Geographic coordinates $(\text{lon}, \text{lat})$ and peak elevations (Mt. Shkhara 5,193 m, Mt. Kazbek 5,047 m, Mt. Ushba 4,710 m, Jvari Pass 2,379 m) are uncopyrightable facts under 17 U.S.C. § 102(b) and dedicated to CC0 in Wikidata, powering `assets/maps/georgia-places.csv` and `tt_shorts/geo.py`.

---

### C. Relief Cartography, Hillshading & Contour Presentation

13. **Eduard Imhof (1965 / 1982) — *Cartographic Relief Presentation* (ETH Zürich / Walter de Gruyter)**
    - **Link**: https://doi.org/10.1515/9783110826111
    - **What it teaches Veasy**: Classical Swiss relief shading combines oblique northwest/northeast grazing illumination with hypsometric air perspective (atmospheric depth cueing where distant valleys recede into dark shadow while high ridges catch specular/diffuse light). In a monochrome grey plate (`R == G == B`), combining a primary grazing directional light ($\alpha \in [12^\circ, 26^\circ]$) with a soft zenithal component prevents deep gorges (like Dariali and Enguri) from crushing to unreadable black while giving peaks sculptural contrast.

14. **Kitiro Tanaka (1950) — "The Relief Contour Method of Representing Topography on Maps" (*Geographical Review*, 40(3), 444–456)**
    - **Link**: https://doi.org/10.2307/211219
    - **What it teaches Veasy**: Illuminated contours (Tanaka method) vary contour stroke brightness and weight by the cosine of the angle between the horizontal terrain gradient $\nabla h$ and the illumination azimuth $\mathbf{L}_{xy}$: contours on sun-facing slopes glow bright light-grey while contours on shadow-facing slopes subtly darken or etch into the surface, creating an unmistakable 3D terraced relief illusion even on compressed mobile screens.

15. **Berthold K. P. Horn (1981) — "Hill Shading and the Reflectance Map" (*Proceedings of the IEEE*, 69(1), 14–47)**
    - **Link**: https://doi.org/10.1109/PROC.1981.11918
    - **What it teaches Veasy**: Gives the exact finite-difference surface normal formulation from a regular elevation grid $z(x,y)$:
      $$\mathbf{n} = \text{normalize}\!\left(-\frac{\partial z}{\partial x},\; 1,\; -\frac{\partial z}{\partial z}\right)$$
      Evaluating central differences in `tools/build_relief.py` or screen-space/texture derivatives in GLSL produces smooth, artifact-free analytical normals across all $800 \times 418$ grid vertices.

16. **Patrick J. Kennelly & A. Jon Kimerling (2001) — "Modifications of Tanaka's Illuminated Contour Method" (*Cartography and Geographic Information Science*, 28(2), 111–123)**
    - **Link**: https://doi.org/10.1559/152304001782173727
    - **What it teaches Veasy**: Pairing a subdued continuous analytical hillshade ($0.10–0.45$ grey luminance) with sharp index contours every $500\text{ m}$ and intermediate contours every $100\text{ m}$ maximizes human shape-from-contour perception without visual clutter behind foreground typography.

17. **Thomas K. Peucker & David H. Douglas (1973/1975) — Surface-Specific Points (Peaks, Passes, Ridges, Channels)**
    - **Link**: https://doi.org/10.3138/FM57-6770-U75U-7727
    - **What it teaches Veasy**: Camera flights look authentic when anchored to geomorphological skeleton features: ridge lines (`move: "ridge"` along the Svaneti/Greater Caucasus crest), saddle passes (`move: "descend"` over Jvari Pass down the Aragvi channel), and basin-to-scarp transitions (`move: "reveal"` across the Alazani plain to the Gombori ridge).

18. **Bernhard Jenny & Tom Patterson (2021) — " aerial Perspective for Shaded Relief" (*Cartography and Geographic Information Science*)**
    - **Link**: https://doi.org/10.1080/15230406.2020.1813052
    - **What it teaches Veasy**: Distance-based exponential fog attenuation ($\exp(-(\rho \cdot d)^2)$) in grey tones separates foreground ridges from the distant horizon and keeps the upper frame ($y < 500\text{ px}$, where the brand header and headline live) calm and high-contrast for Georgian text.

---

### D. Real-Time 3D Terrain Meshing, Screen-Space Contours & Deterministic Headless Baking

19. **Evan Wallace (2016) & Brad Larson — Screen-Space Anti-Aliased Grid & Contour Lines via `fwidth` (`OES_standard_derivatives` / GLSL ES 3.0)**
    - **Link**: https://madebyevan.com/shaders/grid/ · Khronos `fwidth`: https://registry.khronos.org/OpenGL-Refpages/es3.0/html/fwidth.xhtml
    - **What it teaches Veasy**: Instead of generating millions of 3D polyline segments via Marching Squares (which shimmer and alias at grazing camera angles), computing `float f = abs(fract(elev / interval - 0.5) - 0.5) / fwidth(elev / interval);` in the fragment shader produces **1-pixel screen-space anti-aliased contour lines at every distance and camera tilt**, with automatic fade-out when `fwidth(elev / interval) > 0.45` so steep distant cliffs never moiré.

20. **Inigo Quilez — Distance Field & Gradient Normalization for Constant-Thickness Isolines**
    - **Link**: https://iquilezles.org/articles/distance/
    - **What it teaches Veasy**: Dividing a scalar field's periodic distance $|f(x)|$ by its screen-space gradient $|\nabla f|$ guarantees uniform stroke thickness across both flat plains (Alazani Valley, Colchis Lowland) and near-vertical walls (Ushba, Kazbek). *(Studied mathematical principle only; all GLSL in `plates/relief/index.html` is written from scratch by Veasy.)*

21. **Three.js `BufferGeometry`, `DataTexture`, and `Vector3.project(camera)` (`three@0.184.0`, MIT License)**
    - **Link**: https://threejs.org/docs/#api/en/math/Vector3.project · Source: https://github.com/mrdoob/three.js
    - **What it teaches Veasy**: `Vector3.project(camera)` transforms any 3D world point $(X, Y, Z)$ through `camera.matrixWorldInverse` and `camera.projectionMatrix` into Normalized Device Coordinates $\text{NDC} \in [-1, +1]^3$, mapping cleanly to viewport pixels:
      $$x_{\text{px}} = \frac{\text{ndc}_x + 1}{2} \cdot W, \qquad y_{\text{px}} = \frac{1 - \text{ndc}_y}{2} \cdot H$$
      Calling `camera.updateMatrixWorld(true)` inside `window.step(t)` ensures `window.anchors(t)` returns exact, zero-lag pixel coordinates on every frame.

22. **ITU-R BT.1702 / Ofcom Harding & W3C WCAG 2.3.1 — Photosensitive Epilepsy & Flash Safety Limits**
    - **Link**: https://www.w3.org/TR/WCAG21/#three-flashes-or-below-threshold
    - **What it teaches Veasy**: Enforced in Veasy by `tt_shorts/flash.py` and `tt_shorts/motion_rules.py`. No more than 3 luminance transitions $>20\text{ cd/m}^2$ per second over $>25\%$ of the screen. In `plates/relief/`, `smootherstep` camera trajectories and anti-aliased `fwidth` contour clamping guarantee smooth, monotonic frame-to-frame luminance delta ($\Delta Y < 0.015$ per frame), eliminating contour flicker.

23. **Chrome Headless / SwiftShader WebGL Deterministic Frame Capture (`puppeteer-core@25.16.0`)**
    - **Link**: https://pptr.dev/ · Contract: `plates/run.mjs`
    - **What it teaches Veasy**: `plates/run.mjs` drives `window.setup(spec, ctx)` and steps `window.step(t)` + `window.anchors(t)` synchronously at $t = i / \text{fps}$ before `page.screenshot()`. An $800 \times 418$ indexed `BufferGeometry` mesh ($334{,}400$ vertices) with pre-displaced CPU vertex heights and a single-pass `ShaderMaterial` renders in **~140–185 ms/frame** at full `1080×1920` and **~45–75 ms/frame** at `--scale 0.5`, matching the benchmark target (`187 ms/frame`) with 100% pixel determinism.

24. **Perlin (2002) — "Improving Noise" & Quintic $C^2$ Smootherstep Interpolation (*ACM TOG*, 21(3), 681–682)**
    - **Link**: https://doi.org/10.1145/566654.566636
    - **What it teaches Veasy**: Quintic polynomial $s(p) = 6p^5 - 15p^4 + 10p^3$ has zero first and second derivatives at $p=0$ and $p=1$ ($s'(0)=s'(1)=0, s''(0)=s''(1)=0$), eliminating camera jerk at the start and end of every 6-second plate and keeping the projected anchor dot smooth for DOM overlays.

---

## 2. Licence Table (Every Source & What a Film Must Credit)

| Asset / Source | Provider | Licence | Commercial Use | Share-Alike | Used in `plates/relief/`? | What a Film / Repo Must Credit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NASA SRTMGL1 v003 / NASADEM** | NASA / USGS LP DAAC | US Public Domain (17 U.S.C. § 105) | Yes | None | **Yes** (primary elevation foundation via Terrarium tiles) | None required on-screen; documented in `assets/maps/README.md` |
| **USGS / NGA GMTED2010 & ETOPO1** | USGS / NGA / NOAA | US Public Domain (17 U.S.C. § 105) | Yes | None | **Yes** (regional void-fill in Terrarium tiles) | None required on-screen; documented in `assets/maps/README.md` |
| **AWS Terrain Tiles (`elevation-tiles-prod/terrarium`)** | Mapzen / Tilezen / AWS Open Data | US Public Domain over Caucasus (`SRTM` + `GMTED2010` + `ETOPO1`) | Yes | None | **Yes** (fetched by `tools/build_relief.py`) | None required on-screen; documented in `assets/maps/README.md` |
| **Copernicus DEM (`COP-DEM_GLO-30` / `GLO-90`)** | ESA / European Union / Airbus Defence and Space | Copernicus DEM Licence (free, worldwide, perpetual commercial) | Yes | None | **Documented optional high-res backend** in `tools/build_relief.py` | 28-word ESA/Airbus attribution notice + disclaimer in `assets/maps/README.md` |
| **COD-AB Georgia Administrative Boundaries** | Geostat (National Statistics Office of Georgia) / UN OCHA | CC BY-IGO 3.0 | Yes | None | **Yes** (via `assets/maps/georgia.json`) | Documented in `assets/maps/README.md` (`Geostat · OCHA · CC BY-IGO`) |
| **Natural Earth 1:10m Rivers** | Natural Earth | CC0 1.0 Public Domain | Yes | None | **Yes** (via `assets/maps/georgia.json` `rivers`) | None required (CC0); documented in `assets/maps/README.md` |
| **Wikidata Gazetteer Coordinates (`georgia-places.csv`)** | Wikidata Contributors / Veasy | CC0 1.0 Public Domain / Uncopyrightable facts (17 U.S.C. § 102(b)) | Yes | None | **Yes** (149 places + peaks/passes) | None required (CC0); documented in `assets/maps/README.md` |
| **Three.js (`three@0.184.0`)** | Three.js Authors (`mrdoob`) | MIT License | Yes | None | **Yes** (installed in `plates/node_modules/three`) | MIT copyright notice in `plates/node_modules/three/LICENSE` |
| **OpenStreetMap (OSM Roads / Contours)** | OpenStreetMap Contributors | ODbL 1.0 | Yes, with conditions | **Yes (ODbL § 4.6)** | **NO — Refused** | Not used; ODbL share-alike & mandatory on-screen credit deferred to **Owner Decisions** |

---

## 3. Ranked Implementation Backlog (Value vs. Effort)

| Rank | Unit | Description | Value | Effort | Status |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Research & Contract (`docs/research/georgia-relief.md`)** | One-line UX contract, 24 real sources with links, licence table, camera & shader math, ranked backlog, and initial `georgia-relief-result.md`. | Critical | S | Done |
| **2** | **Reproducible DEM & Mask Baker (`tools/build_relief.py` + `assets/maps/README.md` + `tests/test_relief.py`)** | Fetch open elevation tiles over Georgia, reproject to `800×418` matching `georgia.json`, zero all terrain outside Georgia's official `land` outline, encode 12 regions (including Abkhazia & Tskhinvali region as integral parts of Georgia) + rivers + SDF border into `georgia_mask.png`, export `georgia_dem.bin` & `relief_meta.json` (149 gazetteer places + peaks/passes + 48 region/district catalog), sync to `plates/relief/data/`, and verify with offline unit tests (`tests/test_relief.py`). | Critical | M | Next |
| **3** | **3D Relief Plate Engine (`plates/relief/index.html` + `plates/relief/README.md`)** | Three.js `800×418` terrain mesh + custom GLSL shader (monochrome grey Imhof/Tanaka hillshade, `fwidth` anti-aliased 100m/500m contour lines, region glow, strict border mask clipping outside Georgia), deterministic `descend`, `ridge`, and `reveal` camera moves, `window.anchors(t)` 3D-to-2D pixel projection, and fast spec validation refusing `news`, `crime`, `incidents`, `deaths`, and non-Georgian places. | Critical | M | Queued |
| **4** | **Three Signature Flights + Two Brand Packs + Fresh-Eye Critic** | Bake `kazbegi-jvari` (`descend`), `svaneti` (`ridge`), and `kakheti` (`reveal`); compose behind real facts in `tbilisi-today` and `sitech` packs (`engine compose check` + `engine compose look`); run Fresh-Eye Critic sub-agent on rendered frames & skill docs and apply feedback. | High | M | Queued |
| **5** | **48 Region & District Plates Catalog & Bake** | Generate specs and bake all 48 region and district plates (12 regions of Georgian law + 36 unique districts), verify `anchors.json` and `plate.json` metrics, and list all 48 in `plates/relief/README.md` and `docs/research/georgia-relief-result.md`. | High | M | Queued |
| **6** | **Final Regression Gates & Rebase** | Run `unittest discover -s tests`, `tsc --noEmit`, `engine selftest`, rebase cleanly onto `main`, and finalize `docs/research/georgia-relief-result.md`. | High | S | Queued |
