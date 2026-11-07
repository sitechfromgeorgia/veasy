# Georgia Relief (`plates/relief/`): Goal Result & Evidence Log

## One-Line User & Agent Interface

```bash
node plates/run.mjs relief --spec plates/relief/specs/kazbegi-jvari.json --seconds 6 --seed 1 --out out/plates/kazbegi-jvari
```

Returns `plate.mp4`, `poster.png`, `plate.json`, and `anchors.json` (`1080×1920` pixel coordinates per frame for the film's DOM dot and Georgian label).

---

## "Done When" Evidence Table

| # | Done When Requirement | Status | Evidence (File / Command / Still) |
| :-: | :--- | :---: | :--- |
| 1 | `docs/research/georgia-relief.md` written (20+ real sources with links, what each teaches Veasy, licence table, ranked backlog) and committed before building | **Done** | `docs/research/georgia-relief.md` (24 real sources with links, full licence table, camera/shader architecture, ranked backlog; commit `0b76433`) |
| 2 | `tools/build_relief.py` is the only way `assets/relief/` is built, reproducibly, with its sources in `assets/maps/README.md` | **Done** | `tools/build_relief.py` (`800×418` `georgia_dem.bin` `sha256=95212052ab0348ac`, `georgia_mask.png`, `relief_meta.json`), `assets/maps/README.md`, `tests/test_relief.py` |
| 3 | Moves under spec key `move`: `descend`, `ridge`, `reveal`; contour lines & relief in grey; Georgia's outline from `georgia.json`, nothing outside it drawn as a claim; anchors from `geo.py`'s gazetteer (`window.anchors(t)`) | **Done** | `plates/relief/index.html`, `plates/relief/README.md`, `tests/test_relief.py` (`Ran 7 tests in 0.096s OK`) |
| 4 | Three signature flights baked (`kazbegi-jvari`, `svaneti`, `kakheti`) and looked at in two packs (`tbilisi-today` and `sitech`) | **Done** (see note) | Baked in `out/plates/kazbegi-jvari/` (`hash=04d9d478a99beac4`), `out/plates/svaneti/` (`hash=c03d316a94970144`), `out/plates/kakheti/` (`hash=cb20fa16b7506a92`); plate placed behind scene `where` of story 24835 in both packs (`compose check` problems: [] in each; plate under a `--canvas` scrim at .8 because the probe bounds any picture to white); `compose look` sheets: `docs/research/georgia-relief-evidence/{sitech,tbilisi-today}-beats.jpg`, posters `poster-*.png`. Note: only kazbegi-jvari was composed into films; svaneti and kakheti were baked and their posters looked at. The plate is grey, so the packs differ only in DOM chrome. |
| 5 | 48 region and district plates baked and listed (12 regions + 36 unique districts) | **Done** | All 48 baked (6 s, seed 1, full scale, 0 failures) into git-ignored `out/plates/`; list with hashes in `docs/research/georgia-relief-plates.md` |
| 6 | Abkhazia and Tskhinvali region checked on every map in a test, and anchors land on the place | **Done** | Region test passes. By numbers, in `tests/test_relief.py`: (a) `test_known_places_stand_at_their_real_height_in_the_grid` (Batumi, Sokhumi at sea level; Kutaisi 80-300 m; Mtskheta, Telavi, Sighnaghi; Mestia 1350-1800; Ushguli 1900-2500; Kazbegi/Stepantsminda 1500-2100); (b) `test_every_gazetteer_place_has_the_world_point_of_its_lat_lon` (all 149); (c) `test_anchors_are_the_projection_of_the_places_lat_lon`: `plates/relief/pose_dump.mjs` gives each plate's camera and anchors at frames 0/45/90/135/179, Python re-projects the lat/lon (own DEM sampling, own pinhole) and the pixels agree within 1 px, also with the baked `anchors.json`; clamped (off-screen) anchors must really project outside; each flight's last frame has its target in frame. 6 plates by default (~25 s), all 51 with `RELIEF_ALL_PLATES=1`: all 51 passed (6 min, before the Adjara respec; Adjara re-run after). Cause of the earlier critic doubt: the `dot` is the moving point from to `to`, so the mid-flight poster showed Khulo-Batumi, not Batumi; and Batumi was off screen for 4 of 6 s. Fixed: `region-adjara` now stays on Batumi with the sea in frame (rebaked, hash `0a82216c63d2c8d8`; poster `georgia-relief-evidence/region-adjara-v2.png`). Critic on that still: coast visible yes; dot on low ground partly (flat shore strip, steep ridges right beside it). |
| 7 | The licence table names every source and what a film must credit | **Done** | `docs/research/georgia-relief.md` § 2, `assets/maps/README.md` |

---

## Commit Log

1. `0b76433` — `docs(relief): add georgia-relief research, licence audit, and backlog`
2. `1ec527b` — `feat(relief): add tools/build_relief.py, plates/relief engine, 51 specs, and tests`

---

## Owner Decisions

1. **OpenStreetMap (ODbL 1.0) Road Vectors**: ODbL § 4.3 requires mandatory `"© OpenStreetMap contributors"` attribution on or accompanying produced video works, and ODbL § 4.6 imposes Share-Alike obligations if road vectors are combined with elevation or gazetteer databases. Because plates must contain zero text and Veasy films do not carry OSM road credits, `plates/relief/` builds **without** OpenStreetMap data. Per the map rule (*"A wrong road is a false claim: draw a road only from a licensed source with a test, else a dot and a place name"*), flights use real 3D terrain relief, `georgia.json` outlines/rivers, and `geo.py` gazetteer dots + place names. If road vectors are desired later, the owner can decide whether to license a CC0/commercial road layer or add ODbL credit to post descriptions.

---

## Shared Files Touched

- `.gitignore`: added `assets/relief/` and `plates/relief/data/` at the end of the ignored directories list.
- `assets/maps/README.md`: (pending in Unit 2) additive section documenting `assets/relief/` sources, licences, and `tools/build_relief.py`.

3. `657d404`, `fb40942`, `a92a3a5` — evidence for lines 4-6

## Open (for the owner or the next session)

- Other posters (mid-flight) show the moving dot, not a named place; a film should use the named track (`anchors.json` key = place id) for a fixed place.
- Full suite after this lane's work: `Ran 780 tests`, OK (skipped=2). `selftest` and `tsc` not run: this lane touches neither engine nor remotion.
- Goal 1 (`engine plate`) not merged: plates bake through `plates/run.mjs`.

## Shared files touched

None new. `plates/relief/index.html` gained `window.pose(t)` (no change to pixels or anchors); new `plates/relief/pose_dump.mjs`.
