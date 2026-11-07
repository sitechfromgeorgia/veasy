"""The real map of Georgia (assets/maps/georgia.json, tt_shorts/geo.py): the data is whole and de jure, place names
are found in any case, a shared name never guesses, and a crime story never points at a district."""
import json
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, engine, geo, props

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGIONS = {"tbilisi", "abkhazia", "adjara", "guria", "imereti", "kakheti", "kvemo-kartli", "mtskheta-mtianeti",
           "racha-lechkhumi", "samegrelo-zemo-svaneti", "samtskhe-javakheti", "shida-kartli"}


def rings(path):
    """Our path data (M x y, relative l moves, z; a number has at most one decimal) -> [[(x, y)]]; anything else in
    it fails the test."""
    out, cur, mode, nums = [], None, None, []
    for t in re.findall(r"[A-Za-z]|-?\d+(?:\.\d)?|\S", path):
        if t in "Mlz":
            mode = t
            continue
        if not re.fullmatch(r"-?\d+(?:\.\d)?", t):
            raise AssertionError(f"unexpected {t!r} in path data")
        nums.append(float(t) if "." in t else int(t))
        if len(nums) == 2:
            (x, y), nums = nums, []
            if mode == "M":
                cur = [(x, y)]
                out.append(cur)
                mode = "l"
            else:
                cur.append((cur[-1][0] + x, cur[-1][1] + y))
    if nums:
        raise AssertionError("odd number of coordinates")
    return out


def inside(pt, ring):
    x, y = pt
    c, j = False, len(ring) - 1
    for i in range(len(ring)):
        (xi, yi), (xj, yj) = ring[i], ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def where(place, sub="", **kw):
    return {"type": "where", "at": "x", "place": place, "sub": sub, **kw}


class Data(unittest.TestCase):
    d = geo.data()

    def test_the_12_regions_of_georgian_law(self):
        self.assertEqual(set(self.d["regions"]), REGIONS)  # no separate entity for Abkhazia or the Tskhinvali region
        self.assertEqual(self.d["regions"]["abkhazia"]["name"], "აფხაზეთი")
        self.assertEqual(self.d["land"].count("M"), 1)  # one outline: Georgia, nothing cut out of it
        by_id = {p["id"]: p for p in self.d["places"]}
        self.assertEqual(by_id["sokhumi"]["region"], "abkhazia")
        self.assertEqual(by_id["tskhinvali"]["region"], "shida-kartli")
        self.assertEqual(by_id["java"]["region"], "shida-kartli")
        self.assertEqual(by_id["akhalgori"]["region"], "mtskheta-mtianeti")

    def test_paths_are_valid_and_inside_the_view(self):
        _, _, w, h = self.d["viewBox"]
        for name in ("land", "borders", "rivers"):
            self.assertTrue(rings(self.d[name]), name)
        for rid, r in self.d["regions"].items():
            rs = rings(r["path"])
            self.assertTrue(r["path"].endswith("z"), rid)
            pts = [p for ring in rs for p in ring]
            self.assertGreater(len(pts), 30, rid)
            box = [min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)]
            self.assertEqual(box, r["bbox"], rid)
            self.assertTrue(0 <= box[0] and 0 <= box[1] and box[2] <= w and box[3] <= h, rid)

    def test_every_place_is_in_georgia_and_in_its_region(self):
        land = rings(self.d["land"])[0]
        box = [min(x for x, _ in land), min(y for _, y in land), max(x for x, _ in land), max(y for _, y in land)]
        ids = [p["id"] for p in self.d["places"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(80 <= len(ids) <= 150)
        for p in self.d["places"]:
            x, y = p["point"]
            self.assertTrue(box[0] <= x <= box[2] and box[1] <= y <= box[3], p["id"])
            self.assertTrue(inside(p["point"], land), p["id"])
            self.assertTrue(any(inside(p["point"], r) for r in rings(self.d["regions"][p["region"]]["path"])), p["id"])
            self.assertIn(p["kind"], ("city", "town", "village", "district"))
            self.assertTrue(re.fullmatch(r"[ა-ჰ][ა-ჰ -]*", p["name"]), p["id"])  # Georgian names on screen
            self.assertEqual(p["kind"] == "district", p["region"] == "tbilisi", p["id"])

    def test_small_enough(self):
        self.assertLess(geo.DATA.stat().st_size, 90_000)
        total = sum(f.stat().st_size for f in (ROOT / "assets" / "maps").iterdir() if f.is_file())
        self.assertLess(total, 1_500_000)  # all the map files together


class Locate(unittest.TestCase):
    def test_case_endings(self):
        for text, region, place in (("თბილისში", "tbilisi", None), ("ბათუმიდან", "adjara", "batumi"),
                                    ("ქუთაისის", "imereti", "kutaisi"), ("ვაკეში", "tbilisi", "vake"),
                                    ("მცხეთაში", "mtskheta-mtianeti", "mtskheta"), ("საბურთალოზე", "tbilisi", "saburtalo"),
                                    ("ახალ ათონში", "abkhazia", "akhali-atoni"), ("დიღმის მასივი", "tbilisi", "dighomi"),
                                    ("ისნის რაიონში", "tbilisi", "isani"), ("ყვარლის", "kakheti", "kvareli"),
                                    ("ბათუმშიც", "adjara", "batumi"), ("ᲒᲝᲠᲘ", "shida-kartli", "gori"),
                                    ("ცხინვალის რეგიონი", "shida-kartli", "tskhinvali"),
                                    ("იმერეთში", "imereti", None), ("ქვემო ქართლის სოფელი", "kvemo-kartli", None)):
            loc = geo.locate(text)
            self.assertIsNotNone(loc, text)
            self.assertEqual(loc["region"], region, text)
            self.assertEqual(loc["places"][0]["id"] if loc["places"] else None, place, text)
            self.assertEqual(loc["point"] is None, place is None, text)
        loc = geo.locate("ბათუმიდან")
        self.assertEqual((loc["name"], loc["kind"]), ("ბათუმი", "city"))

    def test_only_exact_names_match(self):  # a word that starts like a name is not the name
        for text in ("სტამბოლი", "ვერ მოხერხდა", "ონლაინ", "ბათუმელი", "ვაკანსია", "", "Batumi"):
            self.assertIsNone(geo.locate(text), text)

    def test_two_places_and_two_regions(self):
        loc = geo.locate("ვარკეთილი · ვაზისუბანი")
        self.assertEqual([p["id"] for p in loc["places"]], ["varketili", "vazisubani"])
        self.assertEqual(geo.locate("ქუთაისი · ბათუმი")["regions"], ["imereti", "adjara"])

    def test_a_shared_name_takes_the_named_region_or_nothing(self):
        self.assertIsNone(geo.locate("ახალდაბა"))  # Samtskhe-Javakheti or Tbilisi: no guess
        self.assertEqual(geo.locate("ახალდაბა, ბორჯომი")["places"][0]["id"], "akhaldaba-borjomi")
        self.assertEqual(geo.locate("ახალდაბა", context="სამცხე-ჯავახეთი")["region"], "samtskhe-javakheti")
        self.assertEqual(geo.locate("ახალდაბა · თბილისი")["places"][0]["id"], "akhaldaba-tbilisi")
        with mock.patch.object(geo, "_index", return_value=[  # same name, same region: zoom to the region only
                (("სოფელი",), (), "place", [{"id": "a", "name": "სოფელი", "kind": "village", "region": "guria",
                                             "point": [1, 1]}, {"id": "b", "name": "სოფელი", "kind": "village",
                                                                "region": "guria", "point": [2, 2]}])]):
            loc = geo.locate("სოფელში")
            self.assertEqual((loc["region"], loc["point"], loc["places"]), ("guria", None, []))

    def test_area(self):
        self.assertEqual(geo.locate("სოფელი", area="ge:imereti")["region"], "imereti")
        self.assertEqual(geo.locate("", area="ge:kutaisi")["places"][0]["id"], "kutaisi")
        self.assertEqual(geo.locate("ბათუმი", area="ge:imereti")["places"], [])  # the area wins
        self.assertEqual(geo.locate("", area="ge")["kind"], "country")
        with self.assertRaises(ValueError):
            geo.locate("ბათუმი", area="ge:atlantis")
        self.assertEqual(engine.shape_problems(where("ბათუმი", area="ge:adjara")), [])
        self.assertTrue(engine.shape_problems(where("ბათუმი", area="imereti")))
        self.assertIn("ge:imereti", engine.options()["areas"])
        self.assertIn("area", engine.SCENES["where"][1])


class Privacy(unittest.TestCase):
    """Crime and incidents: the map stops at the region and never marks a district (a part of a city where people
    live); other stories may zoom into the city and mark it."""

    def test_a_district_in_a_crime_story(self):
        tbilisi = geo.data()["regions"]["tbilisi"]["bbox"]
        crime = geo.scene_map(where("ვაკე", "თბილისი"), "crime")
        self.assertEqual((crime["level"], crime["pins"]), ("region", []))
        self.assertEqual(crime["focus"], [round(v) for v in geo._pad(tbilisi, geo.PAD)])
        news = geo.scene_map(where("ვაკე", "თბილისი"), "society")
        self.assertEqual(news["level"], "district")
        self.assertEqual(news["pins"], [next(p["point"] for p in geo.data()["places"] if p["id"] == "vake")])
        self.assertLess(news["focus"][2] - news["focus"][0], crime["focus"][2] - crime["focus"][0])

    def test_no_district_is_ever_marked_in_crime(self):
        for p in geo.data()["places"]:
            m = geo.scene_map(where(p["name"]), "crime")
            if m is None:  # a shared name with no region named: no map at all
                continue
            self.assertNotEqual(m["level"], "district", p["id"])
            if p["kind"] == "district":
                self.assertEqual(m["pins"], [], p["id"])
        self.assertEqual(len(geo.scene_map(where("ქუთაისში"), "crime")["pins"]), 1)  # a town may be marked

    def test_incidents_render_as_crime(self):  # the category's family decides, in props
        s = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            for category, level, pins in (("incidents", "region", 0), ("society", "district", 2)):
                path = pathlib.Path(home) / f"{category}.json"
                path.write_text(json.dumps({**s, "category": category}, ensure_ascii=False), encoding="utf-8")
                _, p = props.build(str(path), "editorial", "silent", music="off")
                m = next(x for x in p["scenes"] if x["type"] == "where")["map"]
                self.assertEqual((m["level"], len(m["pins"])), (level, pins), category)
                self.assertEqual("city" in m["layers"], category == "society", category)  # no district detail in crime
                self.assertEqual({o["label"] for o in m["occupied"]}, {"დროებით ოკუპირებული"})  # props pass the pack's


class Scene(unittest.TestCase):
    def test_an_unknown_place_keeps_the_grid(self):
        self.assertIsNone(geo.scene_map(where("სტამბოლი", "დოლმაბაჰჩეს რეზიდენცია, თურქეთი")))
        self.assertIsNone(geo.scene_map(where("ბათუმი", area="ge:nowhere")))  # check reports it; a render never fails
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            _, p = props.build(str(ROOT / "stories" / "24725.json"), "editorial", "silent", music="off")
        self.assertNotIn("map", next(s for s in p["scenes"] if s["type"] == "where"))

    def test_props_carry_only_what_the_scene_draws(self):
        m = geo.scene_map(where("ბათუმი"))
        self.assertEqual(set(m), {"viewBox", "land", "borders", "rivers", "regions", "start", "focus", "pins", "level",
                                  "credit", "occupied", "layers"})
        self.assertEqual(len(m["regions"]), 1)
        self.assertLess(geo.weight(m), geo.BUDGET)  # no gazetteer, no other regions' shapes
        self.assertLess(len(json.dumps(m, ensure_ascii=False)), 90_000)
        x0, y0, x1, y1 = m["focus"]
        self.assertTrue(x0 < m["pins"][0][0] < x1 and y0 < m["pins"][0][1] < y1)

    def test_the_demo_passes(self):
        s = json.loads((ROOT / "stories" / "veasy-map.json").read_text(encoding="utf-8"))
        self.assertEqual(engine.check_story(s), [])
        maps = [geo.scene_map(x, "tech") for x in s["scenes"] if x["type"] == "where"]
        self.assertEqual([m["level"] for m in maps], ["region", "district", "region"])


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0 if not (dx or dy) else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def near_or_in(p, ring, tol=2.0):
    """Inside the ring, or on its line (the occupied territories' vertices lie on Georgia's outline)."""
    return inside(p, ring) or min(seg_dist(p, a, b) for a, b in zip(ring, ring[1:] + ring[:1])) <= tol


LABEL = "დროებით ოკუპირებული"
PACK = {"occupied": LABEL}


class Occupied(unittest.TestCase):
    """The territories Georgian law calls occupied (owner, 2026-11-07): an overlay inside Georgia's outline with the
    pack's label; never a 13th region."""
    d = geo.data()

    def test_two_overlays_inside_georgias_outline(self):
        self.assertEqual(set(self.d["occupied"]), {"abkhazia", "tskhinvali"})
        self.assertEqual(set(self.d["regions"]), REGIONS)  # still the 12 regions: no 13th, no new border
        land = rings(self.d["land"])[0]
        for oid, o in self.d["occupied"].items():
            rs = rings(o["path"])
            self.assertEqual(len(rs), 1, oid)  # one outline each
            self.assertTrue(o["path"].endswith("z"), oid)
            box = [min(x for x, _ in rs[0]), min(y for _, y in rs[0]), max(x for x, _ in rs[0]), max(y for _, y in rs[0])]
            self.assertEqual(box, o["bbox"], oid)
            self.assertTrue(all(near_or_in(p, land) for p in rs[0]), oid)  # inside Georgia (or on its outline)
            self.assertTrue(inside(o["at"], rs[0]) and inside(o["at"], land), oid)  # the label's spot
            self.assertGreater(o["r"], 100, oid)  # room for a label
            self.assertTrue(re.fullmatch(r"[ა-ჰ ]+", o["name"]), oid)

    def test_the_territories_are_what_the_law_names(self):
        by_id = {p["id"]: p for p in self.d["places"]}
        ab, ts = (rings(self.d["occupied"][k]["path"])[0] for k in ("abkhazia", "tskhinvali"))
        for pid in ("sokhumi", "gagra", "gali"):
            self.assertTrue(inside(by_id[pid]["point"], ab), pid)
        for pid in ("tskhinvali", "akhalgori", "java"):  # the former South Ossetian AO, Akhalgori and Java included
            self.assertTrue(inside(by_id[pid]["point"], ts), pid)
        for pid, ring in (("zugdidi", ab), ("gori", ts), ("sokhumi", ts), ("tskhinvali", ab), ("batumi", ab),
                          ("mtskheta", ts), ("tbilisi", ts)):
            if pid in by_id:
                self.assertFalse(inside(by_id[pid]["point"], ring), pid)
        abkhazia = rings(self.d["regions"]["abkhazia"]["path"])[0]
        self.assertTrue(inside(self.d["occupied"]["abkhazia"]["at"], abkhazia))  # Abkhazia's own region, the same line
        # Tskhinvali's outline is drawn from the regions' own arcs: every sample inside it is in Shida Kartli or
        # Mtskheta-Mtianeti, none in another region
        homes = [rings(self.d["regions"][r]["path"])[0] for r in ("shida-kartli", "mtskheta-mtianeti")]
        other = [rings(r["path"])[0] for k, r in self.d["regions"].items() if k not in ("shida-kartli", "mtskheta-mtianeti")]
        x0, y0, x1, y1 = self.d["occupied"]["tskhinvali"]["bbox"]
        n = 0
        for i in range(30):
            for j in range(30):
                p = (x0 + (x1 - x0) * i / 29, y0 + (y1 - y0) * j / 29)
                if inside(p, ts):
                    n += 1
                    self.assertTrue(any(inside(p, h) for h in homes), p)
                    self.assertFalse(any(inside(p, o) for o in other), p)
        self.assertGreater(n, 100)

    def test_the_label_comes_from_the_pack_not_the_engine(self):
        m = geo.scene_map(where("სოხუმი"), None, PACK)
        self.assertEqual({o["label"] for o in m["occupied"]}, {LABEL})
        self.assertEqual({o["label"] for o in geo.scene_map(where("სოხუმი"))["occupied"]}, {""})  # no pack, no word
        self.assertEqual(brand.load("tbilisi-today")["strings"]["occupied"], LABEL)
        self.assertEqual(brand.load("sitech")["strings"]["occupied"], LABEL)
        for folder in ("tt_shorts", "remotion/src"):  # CLAUDE.md: no word of a pack in engine code
            for f in (ROOT / folder).rglob("*"):
                if f.suffix in (".py", ".ts", ".tsx"):
                    self.assertNotIn("ოკუპირებ", f.read_text(encoding="utf-8"), str(f))

    def test_both_overlays_always_and_in_focus_when_the_camera_ends_on_them(self):
        def focus(place):
            return {o["id"]: o["in_focus"] for o in geo.scene_map(where(place), None, PACK)["occupied"]}
        self.assertEqual(focus("საქართველო"), {"abkhazia": True, "tskhinvali": True})
        self.assertEqual(focus("სოხუმი"), {"abkhazia": True, "tskhinvali": False})
        self.assertEqual(focus("ცხინვალი"), {"abkhazia": False, "tskhinvali": True})
        self.assertEqual(focus("ბათუმი"), {"abkhazia": False, "tskhinvali": False})
        for o in geo.scene_map(where("ბათუმი"), None, PACK)["occupied"]:
            self.assertEqual(set(o), {"id", "name", "path", "bbox", "at", "r", "label", "in_focus"})

    def test_osm_covers_both_territories(self):  # an extract that cut them out of Georgia would leave them blank
        det, ab, ts = geo.detail(), *(rings(self.d["occupied"][k]["path"])[0] for k in ("abkhazia", "tskhinvali"))

        def count(chunks, ring):
            return sum(1 for c in chunks if any(inside(p, ring) for r in rings(c[4]) for p in r[::2]))
        for ring, name in ((ab, "abkhazia"), (ts, "tskhinvali")):
            self.assertGreater(count(det["lakes"], ring), 0, f"{name} lakes")
            self.assertGreater(count(det["rivers"]["major"] + det["rivers"]["minor"], ring), 3, f"{name} rivers")
            self.assertGreater(count(det["roads"]["trunk"] + det["roads"]["primary"], ring), 0, f"{name} roads")
        self.assertGreater(count(det["rail"], ab), 0)  # the coast line


class Layers(unittest.TestCase):
    """OpenStreetMap layers (ODbL): each level ships only its own, inside the budget; the credit follows them."""

    def map(self, place, family=None, sub=""):
        return geo.scene_map(where(place, sub), family, PACK)

    def test_each_level_ships_only_its_layers(self):
        country, region = self.map("საქართველო"), self.map("ქუთაისი")
        district, crime = self.map("ვაკე", "society", "თბილისი"), self.map("ვაკე", "crime", "თბილისი")
        self.assertEqual(set(country["layers"]), {"overview"})
        self.assertEqual(set(region["layers"]), {"overview", "detail"})
        self.assertEqual(set(district["layers"]), {"overview", "city"})
        self.assertEqual(set(crime["layers"]), {"overview", "detail"})  # the region's own detail, not the city's
        self.assertEqual(set(country["layers"]["overview"]), {"lakes", "roads"})
        self.assertTrue(country["rivers"] and country["rivers"] != geo.data()["rivers"])  # OSM's major rivers
        for m in (country, region, district, crime):
            self.assertLess(geo.weight(m), geo.BUDGET, m["level"])
        self.assertLess(geo.weight(country), geo.weight(region))

    def test_a_region_view_is_clipped_to_its_window(self):
        batumi, kakheti = self.map("ბათუმი"), self.map("კახეთი")
        box = batumi["layers"]["detail"]["box"]
        for a, b in zip(box, geo._pad(batumi["focus"], geo.DETAIL_PAD)):  # the camera's window, a little wider
            self.assertAlmostEqual(a, b, delta=2)
        self.assertTrue(batumi["layers"]["detail"]["rivers"]["major"])
        for m in (batumi, kakheti):  # every piece's first point lies near the window (a piece is at most 40 points)
            x0, y0, x1, y1 = m["layers"]["detail"]["box"]
            for path in (m["layers"]["detail"]["roads"].get("trunk", ""), m["layers"]["detail"]["rivers"]["major"]):
                for ring in rings(path):
                    self.assertTrue(x0 - 400 <= ring[0][0] <= x1 + 400 and y0 - 400 <= ring[0][1] <= y1 + 400)
        chunks = [[0, 0, 10, 10, "Ma"], [100, 100, 110, 110, "Mb"], [5, 5, 200, 200, "Mc"]]
        self.assertEqual(geo._join(chunks, [0, 0, 20, 20]), "MaMc")

    def test_a_district_view_has_the_districts_and_the_streets(self):
        m = self.map("ვაკე", "society", "თბილისი")
        city = m["layers"]["city"]
        self.assertEqual(m["level"], "district")
        self.assertEqual({x["id"] for x in city["districts"]},
                         {"vake", "saburtalo", "mtatsminda", "krtsanisi", "chughureti", "didube", "nadzaladevi", "gldani",
                          "isani", "samgori"})  # Tbilisi's 10 districts, matched to the gazetteer
        self.assertEqual([x["id"] for x in city["districts"] if x["named"]], ["vake"])
        self.assertEqual(city["decimals"], 1)
        by_id = {p["id"]: p for p in geo.data()["places"]}
        for x in city["districts"]:
            ring = rings(x["path"])[0]
            self.assertTrue(x["path"].endswith("z") and len(ring) > 8, x["id"])
            self.assertTrue(inside(x["at"], ring), x["id"])
            self.assertEqual(by_id[x["id"]]["kind"], "district")
            self.assertEqual(x["name"], by_id[x["id"]]["name"])
            self.assertTrue(re.fullmatch(r"[ა-ჰ ]+", x["name"]), x["id"])
        self.assertTrue(city["streets"].get("trunk") and city["streets"].get("primary"))
        self.assertTrue(city["rivers"])  # the Mtkvari through the city
        self.assertTrue(city["metro"] and city["stations"])  # railway=subway
        for key in ("trunk", "primary"):
            self.assertTrue(rings(city["streets"][key]))
        self.assertTrue(rings(city["rivers"]))
        x0, y0, x1, y1 = geo.data()["regions"]["tbilisi"]["bbox"]
        self.assertTrue(all(x0 - 80 <= x <= x1 + 80 and y0 - 80 <= y <= y1 + 80 for x, y in city["stations"]))
        # a view of Tbilisi itself (not a district) shows the same city, the named district marked none
        whole = self.map("თბილისი")
        self.assertEqual(set(whole["layers"]), {"overview", "city"})
        self.assertEqual([x for x in whole["layers"]["city"]["districts"] if x["named"]], [])

    def test_the_crime_family_gets_no_district_detail(self):
        for p in geo.data()["places"]:
            if p["region"] != "tbilisi":
                continue
            m = self.map(p["name"], "crime", "თბილისი")
            self.assertEqual(m["level"], "region", p["id"])
            self.assertNotIn("city", m["layers"], p["id"])
            text = json.dumps(m, ensure_ascii=False)
            for word in ('"districts"', '"streets"', '"metro"', '"stations"', '"streams"', '"city"'):
                self.assertNotIn(word, text, p["id"])
            self.assertEqual(m["pins"], [], p["id"])
        for text in ("თბილისი", "თბილისში", "ვაკეში"):
            m = geo.scene_map(where(text), "crime", PACK)
            self.assertNotIn("city", m["layers"], text)
            self.assertNotIn("districts", json.dumps(m, ensure_ascii=False), text)

    def test_every_place_stays_in_the_budget(self):
        for p in geo.data()["places"]:
            for family in (None, "crime"):
                m = geo.scene_map(where(p["name"], "თბილისი" if p["region"] == "tbilisi" else ""), family, PACK)
                if m:
                    self.assertLess(geo.weight(m), geo.BUDGET, f"{p['id']} {family}")
        for place in ("საქართველო", "კახეთი", "ქუთაისი · ბათუმი", "სოხუმი", "ცხინვალი"):
            self.assertLess(geo.weight(self.map(place)), geo.BUDGET, place)

    def test_the_credit_names_openstreetmap_when_its_layers_are_drawn(self):
        for m in (self.map("საქართველო"), self.map("ბათუმი"), self.map("ვაკე", "society", "თბილისი")):
            self.assertIn("© OpenStreetMap contributors", m["credit"])
            self.assertIn("CC BY-IGO", m["credit"])  # the boundary data's credit stays
        with mock.patch.object(geo, "detail", return_value=None):  # without the layers the credit is the old one
            m = self.map("ბათუმი")
            self.assertNotIn("layers", m)
            self.assertEqual(m["credit"], geo.data()["credit"])
            self.assertEqual(m["rivers"], geo.data()["rivers"])
        det = geo.detail()
        self.assertEqual(det["credit"], "© OpenStreetMap contributors")
        self.assertIn("ODbL", det["license"])
        self.assertIn("ODbL", geo.city()["license"])

    def test_layer_data_is_valid_path_data_inside_the_view(self):
        _, _, w, h = geo.data()["viewBox"]
        det = geo.detail()
        for path in (det["overview"]["lakes"], det["overview"]["rivers"], det["overview"]["roads"]):
            self.assertTrue(rings(path))
        for chunk in det["lakes"] + det["rail"] + det["roads"]["trunk"] + det["rivers"]["major"]:
            self.assertEqual(len(chunk[:4]), 4)
            pts = [p for r in rings(chunk[4]) for p in r]
            self.assertTrue(chunk[0] <= min(x for x, _ in pts) and max(x for x, _ in pts) <= chunk[2], chunk[4][:20])
            self.assertTrue(0 <= chunk[0] and chunk[2] <= w and 0 <= chunk[1] and chunk[3] <= h)
        names = {p["id"]: p["name"] for p in geo.data()["places"]}
        self.assertTrue(set(names))
        self.assertEqual(det["lakes"][0][5], max(c[5] for c in det["lakes"]))  # the largest first


class Tool(unittest.TestCase):
    """tools/build_georgia_map.py's own pieces (no network)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_georgia_map", ROOT / "tools" / "build_georgia_map.py")
        cls.t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.t)

    def test_land_tests_points_like_a_polygon(self):
        square = [(10, 10), (90, 10), (90, 90), (10, 90)]
        land = self.t.Land([square], cell=20)
        for p, want in (((50, 50), True), ((5, 50), False), ((95, 50), False), ((89, 11), True), ((91, 11), False),
                        ((12, 88), True), ((9, 88), False), ((500, 500), False), ((-5, -5), False)):
            self.assertEqual(p in land, want, p)
        box = self.t.Box([0, 0, 10, 10])
        self.assertTrue((5, 5) in box and (11, 5) not in box)

    def test_lines_join_only_where_no_third_line_touches(self):
        a, b, c, d = [(0, 0), (1, 0)], [(1, 0), (2, 0)], [(2, 0), (3, 0)], [(2, 0), (2, 1)]
        self.assertEqual(sorted(len(l) for l in self.t.merge_lines([a, b])), [3])
        self.assertEqual(sorted(len(l) for l in self.t.merge_lines([b[::-1], a])), [3])  # either direction
        self.assertEqual(sorted(len(l) for l in self.t.merge_lines([a, b, c, d])), [2, 2, 3])  # a junction stays a break
        ring = [(0, 0), (1, 0), (1, 1), (0, 0)]
        self.assertEqual(self.t.merge_lines([ring]), [ring])

    def test_ways_join_into_rings(self):
        ways = [[(0, 0), (1, 0)], [(1, 1), (1, 0)], [(1, 1), (0, 1)], [(0, 0), (0, 1)]]  # mixed directions
        rs = self.t.join_rings(ways)
        self.assertEqual(len(rs), 1)
        self.assertEqual(rs[0][0], rs[0][-1])
        self.assertEqual(len(rs[0]), 5)
        self.assertEqual(self.t.join_rings([[(0, 0), (1, 0)], [(5, 5), (6, 6)]]), [])  # an open way is dropped

    def test_decimals_are_short_and_exact(self):
        self.assertEqual(self.t.fmt(0, 1), "0")
        self.assertEqual(self.t.fmt(5, 1), "0.5")
        self.assertEqual(self.t.fmt(-5, 1), "-0.5")
        self.assertEqual(self.t.fmt(12340, 1), "1234")
        self.assertEqual(self.t.fmt(-17, 1), "-1.7")
        self.assertEqual(self.t.line_path([[(1.04, 2.0), (1.96, 2.51), (3.0, 0.0)]], close=False, nd=1), "M1 2l1 0.5 1-2.5")
        self.assertEqual(self.t.line_path([[(1.2, 2.3), (4.4, 2.3), (4.4, 7.1), (1.2, 2.3)]], nd=1), "M1.2 2.3l3.2 0 0 4.8z")
        rs = rings(self.t.line_path([[(10.04, 20.0), (19.96, 25.5), (30.0, 0.0)]], close=False, nd=1))
        self.assertEqual(rs, [[(10, 20), (20, 25.5), (30, 0)]])

    def test_the_label_goes_where_there_is_room(self):
        ring = [(0, 0), (100, 0), (100, 100), (0, 100)]
        (x, y), r = self.t.pole(ring)
        self.assertTrue(40 <= x <= 60 and 40 <= y <= 60 and 45 <= r <= 50)
        c_shape = [(0, 0), (100, 0), (100, 30), (30, 30), (30, 70), (100, 70), (100, 100), (0, 100)]
        (x, y), r = self.t.pole(c_shape)
        self.assertTrue(inside((x, y), c_shape) and 14 <= r <= 22)  # inside the bar, not in the notch

    def test_the_osm_queries_cover_the_whole_country_box(self):
        qs = self.t.osm_queries()
        self.assertEqual(set(qs), {"lakes", "rivers", "roads", "rail", "tbilisi-districts", "tbilisi-streets",
                                   "tbilisi-metro", "tbilisi-water", "tbilisi-rail"})
        self.assertIn("(41.0,39.95,43.65,46.8)", qs["roads"])  # south, west, north, east: Abkhazia and the Tskhinvali region
        self.assertIn('"railway"="subway"', qs["tbilisi-metro"])  # not cut out by a country polygon
        self.assertIn('"admin_level"="10"', qs["tbilisi-districts"])


class Focus(unittest.TestCase):
    """map-focus: one of the same 12 regions, by Georgian name or id, highlighted without a pin."""

    def test_a_region_by_name_case_ending_or_id(self):
        for text in ("კახეთი", "კახეთში", "kakheti", "KAKHETI"):
            m, name = geo.focus_map({"region": text})
            self.assertIsNotNone(m, text)
            assert m is not None
            self.assertEqual(name, "კახეთი", text)
            self.assertEqual(m["level"], "region", text)
            self.assertEqual(len(m["regions"]), 1, text)
            self.assertEqual(m["pins"], [], text)
            self.assertNotEqual(m["start"], m["focus"], text)  # the camera moves from the country onto the region
            self.assertLess(m["focus"][0], m["focus"][2])

    def test_a_long_region_name_is_the_data_s_name(self):
        self.assertEqual(geo.focus_map({"region": "rachel"}), (None, None))
        _, name = geo.focus_map({"region": "რაჭა-ლეჩხუმი"})
        self.assertEqual(name, "რაჭა-ლეჩხუმი და ქვემო სვანეთი")

    def test_an_unknown_region_is_named_by_the_check_and_never_breaks_a_render(self):
        self.assertTrue(geo.region_problems("ატლანტის ოკეანე"))
        self.assertEqual(geo.region_problems("იმერეთი"), [])
        self.assertEqual(engine.shape_problems({"type": "map-focus", "region": "ატლანტის ოკეანე"}),
                         [geo.region_problems("ატლანტის ოკეანე")[0]])
        scenes = [{"type": "map-focus", "region": "ატლანტის ოკეანე"}]
        self.assertEqual(geo.attach(scenes, "tech"), scenes)
        self.assertNotIn("map", scenes[0])

    def test_props_show_the_region_s_name_and_the_highlight(self):
        scenes = [{"type": "map-focus", "from": 0, "duration": 90, "region": "kakheti", "value": 310000,
                   "label": "მოსახლეობა"}]
        geo.attach(scenes, "tech")
        self.assertEqual(scenes[0]["place"], "კახეთი")
        # the merge with origin/main's rebuilt map: map-focus goes through the same view() as a where scene, so it
        # carries the occupied overlay and the OpenStreetMap layers, inside the same budget as a where scene's map
        self.assertEqual(set(scenes[0]["map"]), {"viewBox", "land", "borders", "rivers", "regions", "start", "focus",
                                                "pins", "level", "credit", "occupied", "layers"})
        self.assertLess(geo.weight(scenes[0]["map"]), geo.BUDGET)
        self.assertLess(len(json.dumps(scenes[0]["map"], ensure_ascii=False)), 90_000)

    def test_the_focus_map_has_the_occupied_overlay_with_the_pack_s_label(self):
        scenes = [{"type": "map-focus", "from": 0, "duration": 90, "region": "shida-kartli"}]
        geo.attach(scenes, "tech", PACK)
        occ = {o["id"]: o for o in scenes[0]["map"]["occupied"]}
        self.assertEqual(set(occ), {"abkhazia", "tskhinvali"})
        self.assertEqual({o["label"] for o in occ.values()}, {LABEL})
        self.assertTrue(occ["tskhinvali"]["in_focus"])  # the camera ends on Shida Kartli
        self.assertEqual(scenes[0]["map"]["pins"], [])
        self.assertIn("© OpenStreetMap contributors", scenes[0]["map"]["credit"])


if __name__ == "__main__":
    unittest.main()
