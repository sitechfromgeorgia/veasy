# `plates/relief/` — 3D Contour-Line Terrain Relief of Georgia

## One-Line Command

```bash
node plates/run.mjs relief --spec plates/relief/specs/kazbegi-jvari.json --seconds 6 --seed 1 --out out/plates/kazbegi-jvari
```

**Output in `out/plates/kazbegi-jvari/`**:
- `plate.mp4` — `1080×1920`, 30 fps, H.264 `yuv420p` grey contour-line relief flight on `#000000` canvas
- `poster.png` — `1080×1920` mid-flight still frame ($t = \text{seconds}/2$)
- `plate.json` — provenance manifest (`kind`, `spec`, `seconds`, `fps`, `width`, `height`, `scale`, `seed`, `frames`, `ms_per_frame`, `hash`, `anchors: true`)
- `anchors.json` — `1080×1920` pixel coordinates per frame (`{"fps": 30, "frames": [{"dot": [x, y], ...}, ...]}`) projected from the 3D terrain surface so the film's DOM dot and Georgian place label lock onto the mountain, valley, region, or district

Build or refresh the local elevation and border data first with:
```bash
python tools/build_relief.py
```

---

## Spec Keys (`--spec <path-or-json>`)

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `move` | `"descend" \| "ridge" \| "reveal"` | `"descend"` | Camera choreography: `descend` falls off a high ridge to a place/valley; `ridge` flies along a mountain crest line with coordinated banking; `reveal` raises a region out of dark shadow into grazing contour light. |
| `preset` | `"kazbegi-jvari" \| "svaneti" \| "kakheti"` | `undefined` | Optional signature corridor flight preset (`kazbegi-jvari` over Mt. Kazbek & Jvari Pass to Mtskheta/Jvari; `svaneti` along Mestia → Ushguli beneath Ushba & Shkhara; `kakheti` across Telavi, Alazani Valley & Gombori Ridge to Sighnaghi). |
| `region` | `string` (1 of 12 regions) | inferred from `place`/`to` | Spotlights one of the 12 regions of Georgian law (`tbilisi`, `abkhazia`, `adjara`, `guria`, `imereti`, `kakheti`, `mtskheta-mtianeti`, `racha-lechkhumi`, `samegrelo-zemo-svaneti`, `samtskhe-javakheti`, `kvemo-kartli`, `shida-kartli`). |
| `place` | `string` (gazetteer ID) | `undefined` | Single-target place ID from `tt_shorts/geo.py` (`assets/maps/georgia-places.csv`, 149 places). |
| `from` | `string` (gazetteer/landmark ID) | `place` or `region` | Starting place or peak ID for `descend`, `ridge`, or `reveal`. |
| `via` | `string` (gazetteer/landmark ID) | `undefined` | Optional mid-flight waypoint pass or peak (e.g. `"jvari-pass"`). |
| `to` | `string` (gazetteer/landmark ID) | `from` | Destination place or peak ID. |
| `anchor` | `string` (gazetteer/landmark ID) | `to` or `place` | Primary target exported as `dot` (and under its own key) in `anchors.json`. |
| `anchors` | `string[]` | `[anchor]` | Additional gazetteer place IDs to project into `anchors.json` on every frame. |
| `rStart`, `rEnd` | `number` | move-dependent | Optional start/end horizontal orbital standoff in world units (`1 unit ≈ 5.7 km`). |
| `hStart`, `hEnd` | `number` | move-dependent | Optional start/end camera elevation clearance above target in world units. |

---

## Cost Table

| Bake Mode | Viewport Capture | Output Resolution | Mean `ms_per_frame` | 6s (180 frames) Bake Time | Determinism |
| :--- | :--- | :--- | :---: | :---: | :--- |
| Full scale (`--scale 1`) | `1080×1920` | `1080×1920` (30 fps) | `~145–185 ms` | `~27–33 s` | 100% deterministic (`step(t)`, `seed`) |
| Half scale (`--scale 0.5`) | `540×960` | `1080×1920` (30 fps) | `~45–75 ms` | `~9–14 s` | 100% deterministic (`step(t)`, `seed`) |

---

## What `plates/relief/` Refuses

1. **Never for `news`, `crime`, `incidents`, or `deaths`**: Any spec with `program`, `category`, `family`, `kind`, `topic`, or `story_kind` set to `"news"`, `"crime"`, `"incident"`, `"incidents"`, `"death"`, or `"deaths"` (or `crime: true` / `news: true`) throws immediately at setup.
2. **No text, no accent color, no brand mark in the plate**: The WebGL fragment shader outputs strictly neutral grey (`R == G == B`, luminance `0.00..0.88`) on `#000000`. All Georgian typography, source/date chrome, and the pack's single accent dot stay in the film's DOM/SVG layer.
3. **Nothing outside Georgia drawn as a claim**: Outlines come solely from `assets/maps/georgia.json`. All elevation and mask texels outside Georgia's official `land` polygon are zeroed in `tools/build_relief.py` and discarded in the fragment shader.
4. **No separate entity for Abkhazia or the Tskhinvali region**: Georgia has its 12 regions of Georgian law. Abkhazia (`abkhazia`) and the Tskhinvali region (`tskhinvali` and `java` in `shida-kartli`, `akhalgori` in `mtskheta-mtianeti`) are integral parts of Georgia.
5. **No unverified roads or live network tiles**: Zero network requests at render time; refuses unknown/foreign place IDs not in `assets/maps/georgia-places.csv`.

---

## Signature Flights (3) & Region/District Plate Catalog (48)

### Signature Flights (3)
1. `plates/relief/specs/kazbegi-jvari.json` — `move: "descend"`, Stepantsminda / Mt. Kazbek → Jvari Pass → Mtskheta / Jvari (`mtskheta-mtianeti`)
2. `plates/relief/specs/svaneti.json` — `move: "ridge"`, Mestia → Ushguli along the Ushba–Tetnuldi–Shkhara wall (`samegrelo-zemo-svaneti`)
3. `plates/relief/specs/kakheti.json` — `move: "reveal"`, Telavi → Sighnaghi across the Alazani Valley & Gombori Ridge (`kakheti`)

### 48 Region & District Plates (`plates/relief/specs/`)

#### 12 Regions of Georgian Law
1. `region-tbilisi.json` — თბილისი (`tbilisi`, `move: "descend"`, `mtatsminda` → `old-tbilisi`)
2. `region-abkhazia.json` — აფხაზეთი (`abkhazia`, `move: "ridge"`, `gagra` → `sokhumi`)
3. `region-adjara.json` — აჭარა (`adjara`, `move: "ridge"`, `khulo` → `batumi`)
4. `region-guria.json` — გურია (`guria`, `move: "descend"`, `bakhmaro` → `ozurgeti`)
5. `region-imereti.json` — იმერეთი (`imereti`, `move: "reveal"`, `chiatura` → `kutaisi`)
6. `region-kakheti.json` — კახეთი (`kakheti`, `move: "reveal"`, `telavi` → `sighnaghi`)
7. `region-mtskheta-mtianeti.json` — მცხეთა-მთიანეთი (`mtskheta-mtianeti`, `move: "descend"`, `stepantsminda` → `mtskheta`)
8. `region-racha-lechkhumi.json` — რაჭა-ლეჩხუმი და ქვემო სვანეთი (`racha-lechkhumi`, `move: "descend"`, `oni` → `ambrolauri`)
9. `region-samegrelo-zemo-svaneti.json` — სამეგრელო-ზემო სვანეთი (`samegrelo-zemo-svaneti`, `move: "ridge"`, `mestia` → `ushguli`)
10. `region-samtskhe-javakheti.json` — სამცხე-ჯავახეთი (`samtskhe-javakheti`, `move: "ridge"`, `bakuriani` → `borjomi`)
11. `region-kvemo-kartli.json` — ქვემო ქართლი (`kvemo-kartli`, `move: "reveal"`, `bolnisi` → `rustavi`)
12. `region-shida-kartli.json` — შიდა ქართლი (`shida-kartli`, `move: "reveal"`, `tskhinvali` → `gori`)

#### 36 Districts (`kind == "district"` in `assets/maps/georgia-places.csv`)
13. `district-vake.json` — ვაკე (`vake`, `move: "descend"`)
14. `district-saburtalo.json` — საბურთალო (`saburtalo`, `move: "reveal"`)
15. `district-mtatsminda.json` — მთაწმინდა (`mtatsminda`, `move: "ridge"`)
16. `district-krtsanisi.json` — კრწანისი (`krtsanisi`, `move: "descend"`)
17. `district-chughureti.json` — ჩუღურეთი (`chughureti`, `move: "reveal"`)
18. `district-didube.json` — დიდუბე (`didube`, `move: "ridge"`)
19. `district-nadzaladevi.json` — ნაძალადევი (`nadzaladevi`, `move: "descend"`)
20. `district-gldani.json` — გლდანი (`gldani`, `move: "reveal"`)
21. `district-isani.json` — ისანი (`isani`, `move: "ridge"`)
22. `district-samgori.json` — სამგორი (`samgori`, `move: "descend"`)
23. `district-varketili.json` — ვარკეთილი (`varketili`, `move: "reveal"`)
24. `district-vazisubani.json` — ვაზისუბანი (`vazisubani`, `move: "ridge"`)
25. `district-dighomi.json` — დიღომი (`dighomi`, `move: "descend"`)
26. `district-vashlijvari.json` — ვაშლიჯვარი (`vashlijvari`, `move: "reveal"`)
27. `district-mukhiani.json` — მუხიანი (`mukhiani`, `move: "ridge"`)
28. `district-avchala.json` — ავჭალა (`avchala`, `move: "descend"`)
29. `district-zahesi.json` — ზაჰესი (`zahesi`, `move: "reveal"`)
30. `district-avlabari.json` — ავლაბარი (`avlabari`, `move: "ridge"`)
31. `district-sololaki.json` — სოლოლაკი (`sololaki`, `move: "descend"`)
32. `district-ortachala.json` — ორთაჭალა (`ortachala`, `move: "reveal"`)
33. `district-abanotubani.json` — აბანოთუბანი (`abanotubani`, `move: "ridge"`)
34. `district-old-tbilisi.json` — ძველი თბილისი (`old-tbilisi`, `move: "descend"`)
35. `district-vera.json` — ვერა (`vera`, `move: "reveal"`)
36. `district-bagebi.json` — ბაგები (`bagebi`, `move: "ridge"`)
37. `district-delisi.json` — დელისი (`delisi`, `move: "descend"`)
38. `district-vedzisi.json` — ვეძისი (`vedzisi`, `move: "reveal"`)
39. `district-navtlughi.json` — ნავთლუღი (`navtlughi`, `move: "ridge"`)
40. `district-ponichala.json` — ფონიჭალა (`ponichala`, `move: "descend"`)
41. `district-lilo.json` — ლილო (`lilo`, `move: "reveal"`)
42. `district-didi-lilo.json` — დიდი ლილო (`didi-lilo`, `move: "ridge"`)
43. `district-okrokana.json` — ოქროყანა (`okrokana`, `move: "descend"`)
44. `district-tskneti.json` — წყნეთი (`tskneti`, `move: "reveal"`)
45. `district-kojori.json` — კოჯორი (`kojori`, `move: "ridge"`)
46. `district-shindisi.json` — შინდისი (`shindisi`, `move: "descend"`)
47. `district-tabakhmela.json` — ტაბახმელა (`tabakhmela`, `move: "reveal"`)
48. `district-tsavkisi.json` — წავკისი (`tsavkisi`, `move: "ridge"`)
