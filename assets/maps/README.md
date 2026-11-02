# Maps

`georgia.json` is what the `where` scene draws when its place is in Georgia (`tt_shorts/geo.py` reads it; Remotion
gets only one scene's part through `props.py`). It is built by `python tools/build_georgia_map.py` from the sources
below; the build is reproducible (the same downloads give the same bytes) and fails when a place's coordinates
fall outside the region the list gives it.

| File | What |
|---|---|
| `georgia.json` | the outline, the 12 regions, the lines between them, the main rivers (SVG path data in a 10000-unit viewBox, equirectangular at 42.3° N) and the gazetteer (projected points); about 75 KB |
| `georgia-places.csv` | the gazetteer source: 149 cities, towns, villages and Tbilisi districts, hand-checked; Georgian name, kind, region, Wikidata QID, coordinates, other names, syncope stems (ისანი → ისნის) |

## Georgia as Georgian law draws it

Abkhazia and the Tskhinvali region are part of Georgia. The map has the 12 regions of Georgian law and no other
entity. Geostat's data shows the former South Ossetian autonomous oblast as a 13th unit ("Provisional
Administration"). The build gives its Akhalgori part to Mtskheta-Mtianeti, cut along geoBoundaries' Akhalgori
municipality line, and the rest to Shida Kartli, so no border is drawn around it.

## Sources and licences

| Data | Source | Licence | Credit |
|---|---|---|---|
| Regions and outline | OCHA COD-AB Georgia, [data.humdata.org/dataset/cod-ab-geo](https://data.humdata.org/dataset/cod-ab-geo), from the National Statistics Office of Georgia (Geostat), valid 2019-10-18 | CC BY-IGO 3.0 | **needed**: the scene shows `Geostat · OCHA · CC BY-IGO` small under the map (`credit` in `georgia.json`) |
| The Akhalgori cut line | geoBoundaries GEO ADM2 (2007, gbOpen, from Wikimedia Commons) | public domain | none |
| Rivers | Natural Earth 10m rivers and lake centerlines, and its Europe supplement | public domain | none |
| Place names and coordinates | Wikidata (P625, Georgian labels); QIDs in the CSV | CC0 | none |

All four allow commercial use. If the credit should go (e.g. a video description carries it instead), set
`credit` to `""` in the build, and the scene draws nothing there.

## Not here (yet)

- Street-level maps of a district (OpenStreetMap is ODbL and needs a credit on screen) and district polygons in
  Tbilisi: a district is a point, and the camera zooms into the city around it.
- Towns outside Georgia: a foreign place keeps the grid scene with the pin.
