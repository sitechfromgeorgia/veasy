# Maps

`georgia.json` is what the `where` scene draws when its place is in Georgia (`tt_shorts/geo.py` reads it; Remotion
gets only one scene's part through `props.py`). It is built by `python tools/build_georgia_map.py` from the sources
below; the build is reproducible (the same downloads give the same bytes) and fails when a place's coordinates
fall outside the region the list gives it. The OpenStreetMap layers sit in two more files, built by the same tool.

| File | What |
|---|---|
| `georgia.json` | the outline, the 12 regions, the lines between them, the occupied territories (an overlay), the main rivers (Natural Earth, kept as the fallback) (SVG path data in a 10000-unit viewBox, equirectangular at 42.3° N) and the gazetteer (projected points); about 80 KB |
| `georgia-detail.json` | OpenStreetMap, the whole country: lakes and reservoirs, named rivers, motorway/trunk/primary roads, main railways; a coarse `overview` (for the country frame) and fine pieces (`[x0, y0, x1, y1, "path"]`, at most 40 points each) that a region view picks by its window; about 170 KB. **ODbL** |
| `tbilisi.json` | OpenStreetMap, Tbilisi: the 10 districts (admin_level 10, matched to the gazetteer ids), trunk/primary/secondary streets, the Mtkvari and streams, lakes (Tbilisi Sea, Lisi, Turtle Lake...), metro lines and stations, rail; one decimal of a viewBox unit (about 2 px at a district view); about 80 KB. **ODbL** |
| `georgia-places.csv` | the gazetteer source: 149 cities, towns, villages and Tbilisi districts, hand-checked; Georgian name, kind, region, Wikidata QID, coordinates, other names, syncope stems (ისანი → ისნის) |

All the map files together stay under 1.5 MB (`tests/test_geo.py`).

## Georgia as Georgian law draws it

Abkhazia and the Tskhinvali region are part of Georgia. The map has the 12 regions of Georgian law and no other
entity. Geostat's data shows the former South Ossetian autonomous oblast as a 13th unit ("Provisional
Administration"). The build gives its Akhalgori part to Mtskheta-Mtianeti, cut along geoBoundaries' Akhalgori
municipality line, and the rest to Shida Kartli, so no border is drawn around it.

### The occupied territories (owner, 2026-11-07)

The Law on Occupied Territories (2008) names the Autonomous Republic of Abkhazia and the Tskhinvali region (the
territory of the former South Ossetian AO). The map marks both: a light tint of the pack's accent over the region
and the pack's label („ოკუპირებულია რუსეთის მიერ", `strings.occupied` in `brands/_ka/brand.json`) written on the
territory itself (owner, 2026-11-10): two balanced lines in the pack's font, no outline, straight or tilted up to 15°
along the area where that is what fits, the hatch cleared behind the words (`remotion/src/scenes/mapgeo.ts`
`seatInside`), 22-20 px, and 16 px only where nothing bigger fits (the Tskhinvali region at the country view).
Behind the words a clearing of the plain tint covers the hatch, rivers, roads and region lines; the territory's own
edge stays on top. Where even 16 px cannot fit, the words sit straight where most of them land on the area. They are an overlay (`occupied` in `georgia.json`), not regions: the 12 regions, the outline and the
lines are unchanged, no border is drawn around them, and they lie inside Georgia's outline. Abkhazia is the
`abkhazia` region's own ring. The Tskhinvali ring is cut from the same arcs as the regions (Geostat's GE48 unit),
so it meets their lines exactly. `at` is the pole of inaccessibility (the point farthest from the edges) and `r`
that distance, in viewBox units, for sizing a label.

## What a scene gets

`geo.scene_map(scene, family, strings)` (`geo.attach` in `props.py`, with the brand's `strings`) puts a `map` in a
`where` scene. All numbers are in the map's viewBox units (`viewBox`, 10000 wide; one unit is about 56 m); a path is
SVG path data (`M x y` then relative `l` moves, `z` when closed) and, in `layers.city`, may carry one decimal.
`tt_shorts/geo.py` is the code; `remotion/src/types.ts` has the types (`GeoMap`).

| Key | What |
|---|---|
| `viewBox`, `start`, `focus`, `pins`, `level` | as before. `start` is the whole country (the camera's first view), `focus` the last view, `level` is `country`, `region` or `district` (a district only outside the crime family) |
| `land`, `borders`, `regions[]` | as before: the outline, the lines between the regions, the highlighted region(s) |
| `rivers` | now OpenStreetMap's major named rivers (> 70 km in Georgia), coarse, the whole country; draw inside the outline as before (Natural Earth's if the OSM files are not built) |
| `credit` | `Geostat · OCHA · CC BY-IGO · © OpenStreetMap contributors` when `layers` is set (OSMF attribution guidelines: show "© OpenStreetMap contributors" where the map is shown; it is ODbL) |
| `occupied[]` | always both overlays: `{id: "abkhazia" \| "tskhinvali", name, path (closed ring), bbox, at: [x, y], r, label, in_focus}`. Tint the path with the pack's accent at low opacity, draw `label` at `at` (about `r` units of room) when `in_focus` (and at the country level); `in_focus` is whether the camera's last view meets the territory. `label` is `""` when no pack's strings were given |
| `layers.overview` | `{lakes, roads}`, the whole country, coarse (tolerance 9 units): always. `lakes` closed paths (4 km² and up), `roads` motorway and trunk. Draw it at the zoomed-out view and fade it out as the camera zooms in |
| `layers.detail` | a **region** view (also the crime family in Tbilisi): `{box, lakes?, rivers?: {major?, minor?}, roads?: {motorway?, trunk?, primary?}, rail?}`, fine (1.4 units), clipped to `box` (the camera's last window plus 5%). A class that would not fit the budget is missing, the least important first (lakes, major rivers, motorway, trunk, minor rivers, primary, rail). Fade it in as the camera zooms in |
| `layers.city` | Tbilisi, for a **district** view, and for a view of Tbilisi itself (`თბილისი`), never in the crime family: `{box, decimals: 1, districts: [{id, name, path, at, r, named}], streets: {trunk?, primary?, secondary?}, metro?, stations?: [[x, y]], rivers? (the Mtkvari), streams?, lakes?, rail?}`. `districts` are the 10 districts' outlines (ids are the gazetteer's; `named` marks the districts the scene names: highlight those); the rest are clipped to `box` and fitted to the budget like `detail`. `stations` are points |

Budget: the path data of a scene's map (`geo.weight`, everything under `land`, `borders`, `rivers`, `regions`,
`occupied` and `layers`) is at most 80,000 characters; a country view is about 40,000, a region 50,000-75,000, a
district view about 79,000.

Privacy (the crime family, `geo.PRIVATE`): the map stops at the region, no pin on a district, and no district
outline, street, metro or stream is shipped, in any key (`tests/test_geo.py`).

## Sources and licences

| Data | Source | Licence | Credit |
|---|---|---|---|
| Regions and outline | OCHA COD-AB Georgia, [data.humdata.org/dataset/cod-ab-geo](https://data.humdata.org/dataset/cod-ab-geo), from the National Statistics Office of Georgia (Geostat), valid 2019-10-18 | CC BY-IGO 3.0 | **needed**: the scene shows `Geostat · OCHA · CC BY-IGO` small under the map (`credit` in `georgia.json`) |
| The occupied territories | the same Geostat geometry (the `abkhazia` region; unit GE48, the former South Ossetian AO), law: Georgia's Law on Occupied Territories (2008) | CC BY-IGO 3.0 | with the regions |
| The Akhalgori cut line | geoBoundaries GEO ADM2 (2007, gbOpen, from Wikimedia Commons) | public domain | none |
| Lakes, rivers, roads, railways, Tbilisi's districts, streets, metro and water | **OpenStreetMap** through the [Overpass API](https://overpass-api.de) (queries in `tools/build_georgia_map.py`, `osm_queries`; the extract's timestamp and each download's hash are in the `extract` key of both files) | **ODbL 1.0** | **needed**: `© OpenStreetMap contributors` in the map's `credit` whenever these layers are drawn (OSMF attribution guidelines); the film's description should link <https://www.openstreetmap.org/copyright> |
| Rivers (the fallback, `georgia.json`) | Natural Earth 10m rivers and lake centerlines, and its Europe supplement | public domain | none |
| Place names and coordinates | Wikidata (P625, Georgian labels); QIDs in the CSV | CC0 | none |

All of it allows commercial use. ODbL is share-alike for the **derived database**: `georgia-detail.json` and
`tbilisi.json` are derived databases of OpenStreetMap, so they stay under ODbL 1.0 (each file says so in its
`license` key) and anyone who gets them may use and share them on the same terms, with the credit. A film (a
produced work) that draws them needs the credit, not the licence. The other files are not made of OSM data, and
the build keeps them apart. If a credit should go (e.g. a video description carries it instead), set `credit` to `""`
in the build for the Geostat part; the OSM credit is the licence's condition and stays on screen.

Coverage: OSM's data of Abkhazia and the Tskhinvali region is there (the layers are cut to a box, then to Georgia's
outline, not to a country extract that might leave them out), and `tests/test_geo.py` checks that lakes, rivers,
roads and rail lie inside both overlays.

## Rebuilding

`python tools/build_georgia_map.py --cache work/maps-cache` downloads the sources into `work/maps-cache` (git-ignored,
one folder per source: `osm-overpass/` holds the OpenStreetMap answers) and writes the three JSON files; with the
cache kept, the same bytes come out again. A new download is a new extract (OSM changes daily): the files'
`extract` keys say which one a build used. `--no-osm` builds only `georgia.json`.

## Not here (yet)

- Street-level maps of other cities (Batumi, Kutaisi...): only Tbilisi has street and district detail.
- Street, river and district names on the map: the layers draw lines, the labels are only the districts' `name`s and
  the occupied territories' label.
- Towns outside Georgia: a foreign place keeps the grid scene with the pin.

## 3D relief (`assets/relief/`, git-ignored)

`assets/relief/` holds the local elevation grid, border/region mask and 3D gazetteer metadata for `plates/relief/`.
It is built reproducibly by `python tools/build_relief.py` (which also syncs the runtime files into git-ignored
`plates/relief/data/` for the local `plates/run.mjs` server):

| File | What |
|---|---|
| `assets/relief/georgia_dem.bin` | `800×418` little-endian `uint16` elevation grid in decimeters (`0.1 m`), aligned to `georgia.json`'s `[0, 0, 10000, 5233]` equirectangular projection and zeroed outside Georgia's `land` outline |
| `assets/relief/georgia_mask.png` | `800×418` RGBA mask from `georgia.json` (`R` = land mask, `G` = border SDF and outline, `B` = rivers and internal regional borders, `A` = `128 + region_index * 8` for the 12 regions of Georgian law) |
| `assets/relief/relief_meta.json` | grid bounds, source metadata, 12 regions, 149 gazetteer places with 3D world coordinates and elevations, alpine summits/passes and the 48 region/district plate specs |

### Relief sources and licences

| Data | Source | Licence | Credit |
|---|---|---|---|
| Elevation (`georgia_dem.bin`) | NASA SRTMGL1 v003 & USGS GMTED2010 via [AWS Open Data Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (`elevation-tiles-prod/terrarium`, zoom 8 tiles `x=156..161, y=92..95`) | US Public Domain (17 U.S.C. § 105) | none required on screen |
| Optional high-res elevation backend | Copernicus DEM (`COP-DEM_GLO-30` / `GLO-90`), [registry.opendata.aws/copernicus-dem](https://registry.opendata.aws/copernicus-dem/) | Copernicus DEM Licence (commercial use allowed, no share-alike) | repo notice below when GLO-30/90 is used: *"© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved."* |
| Outlines, 12 regions, rivers & gazetteer | `assets/maps/georgia.json` and `assets/maps/georgia-places.csv` (Geostat / UN OCHA COD-AB, Natural Earth 10m, Wikidata) | CC BY-IGO 3.0 / CC0 | same as `georgia.json` above; plates themselves carry zero text |

