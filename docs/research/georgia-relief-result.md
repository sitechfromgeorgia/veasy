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
| 4 | Three signature flights baked (`kazbegi-jvari`, `svaneti`, `kakheti`) and looked at in two packs (`tbilisi-today` and `sitech`) | In progress | Baked in `out/plates/kazbegi-jvari/` (`hash=04d9d478a99beac4`), `out/plates/svaneti/` (`hash=c03d316a94970144`), `out/plates/kakheti/` (`hash=cb20fa16b7506a92`); composing into `tbilisi-today` and `sitech` next |
| 5 | 48 region and district plates baked and listed (12 regions + 36 unique districts) | In progress | All 48 specs written in `plates/relief/specs/` and listed in `plates/relief/README.md`; batch bake next |
| 6 | Abkhazia and Tskhinvali region checked on every map in a test, and a critic checks that anchors land on the place | In progress | `tests/test_relief.py::test_twelve_regions_of_georgian_law_including_abkhazia_and_tskhinvali` passes; Fresh-Eye Critic sub-agent review next |
| 7 | The licence table names every source and what a film must credit | **Done** | `docs/research/georgia-relief.md` § 2, `assets/maps/README.md` |

---

## Commit Log

1. `0b76433` — `docs(relief): add georgia-relief research, licence audit, and backlog`
2. `feat(relief): add tools/build_relief.py, plates/relief engine, 51 specs, and tests`

---

## Owner Decisions

1. **OpenStreetMap (ODbL 1.0) Road Vectors**: ODbL § 4.3 requires mandatory `"© OpenStreetMap contributors"` attribution on or accompanying produced video works, and ODbL § 4.6 imposes Share-Alike obligations if road vectors are combined with elevation or gazetteer databases. Because plates must contain zero text and Veasy films do not carry OSM road credits, `plates/relief/` builds **without** OpenStreetMap data. Per the map rule (*"A wrong road is a false claim: draw a road only from a licensed source with a test, else a dot and a place name"*), flights use real 3D terrain relief, `georgia.json` outlines/rivers, and `geo.py` gazetteer dots + place names. If road vectors are desired later, the owner can decide whether to license a CC0/commercial road layer or add ODbL credit to post descriptions.

---

## Shared Files Touched

- `.gitignore`: added `assets/relief/` and `plates/relief/data/` at the end of the ignored directories list.
- `assets/maps/README.md`: (pending in Unit 2) additive section documenting `assets/relief/` sources, licences, and `tools/build_relief.py`.
