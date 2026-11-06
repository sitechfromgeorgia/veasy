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
| 1 | `docs/research/georgia-relief.md` written (20+ real sources with links, what each teaches Veasy, licence table, ranked backlog) and committed before building | **Done** | `docs/research/georgia-relief.md` (24 real sources with links, full licence table, camera/shader architecture, ranked backlog) |
| 2 | `tools/build_relief.py` is the only way `assets/relief/` is built, reproducibly, with its sources in `assets/maps/README.md` | In progress | `tools/build_relief.py`, `assets/maps/README.md`, `.gitignore` |
| 3 | Moves under spec key `move`: `descend`, `ridge`, `reveal`; contour lines & relief in grey; Georgia's outline from `georgia.json`, nothing outside it drawn as a claim; anchors from `geo.py`'s gazetteer (`window.anchors(t)`) | Queued | `plates/relief/index.html`, `plates/relief/README.md` |
| 4 | Three signature flights baked (`kazbegi-jvari`, `svaneti`, `kakheti`) and looked at in two packs (`tbilisi-today` and `sitech`) | Queued | `out/plates/kazbegi-jvari/`, `out/plates/svaneti/`, `out/plates/kakheti/`, look sheets |
| 5 | 48 region and district plates baked and listed (12 regions + 36 unique districts) | Queued | `plates/relief/specs/`, `plates/relief/README.md` |
| 6 | Abkhazia and Tskhinvali region checked on every map in a test, and a critic checks that anchors land on the place | Queued | `tests/test_relief.py`, Fresh-Eye Critic report |
| 7 | The licence table names every source and what a film must credit | **Done** | `docs/research/georgia-relief.md` § 2, `assets/maps/README.md` |

---

## Commit Log

1. `docs(relief): add georgia-relief research, licence audit, and backlog` (initial commit)

---

## Owner Decisions

1. **OpenStreetMap (ODbL 1.0) Road Vectors**: ODbL § 4.3 requires mandatory `"© OpenStreetMap contributors"` attribution on or accompanying produced video works, and ODbL § 4.6 imposes Share-Alike obligations if road vectors are combined with elevation or gazetteer databases. Because plates must contain zero text and Veasy films do not carry OSM road credits, `plates/relief/` builds **without** OpenStreetMap data. Per the map rule (*"A wrong road is a false claim: draw a road only from a licensed source with a test, else a dot and a place name"*), flights use real 3D terrain relief, `georgia.json` outlines/rivers, and `geo.py` gazetteer dots + place names. If road vectors are desired later, the owner can decide whether to license a CC0/commercial road layer or add ODbL credit to post descriptions.

---

## Shared Files Touched

- `.gitignore`: added `assets/relief/` and `plates/relief/data/` at the end of the ignored directories list.
- `assets/maps/README.md`: (pending in Unit 2) additive section documenting `assets/relief/` sources, licences, and `tools/build_relief.py`.
