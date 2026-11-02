"""The real map of Georgia (assets/maps/georgia.json, tt_shorts/geo.py): the data is whole and de jure, place names
are found in any case, a shared name never guesses, and a crime story never points at a district."""
import json
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import engine, geo, props

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGIONS = {"tbilisi", "abkhazia", "adjara", "guria", "imereti", "kakheti", "kvemo-kartli", "mtskheta-mtianeti",
           "racha-lechkhumi", "samegrelo-zemo-svaneti", "samtskhe-javakheti", "shida-kartli"}


def rings(path):
    """Our path data (M x y, relative l moves, z) -> [[(x, y)]]; anything else in it fails the test."""
    out, cur, mode, nums = [], None, None, []
    for t in re.findall(r"[A-Za-z]|-?\d+|\S", path):
        if t in "Mlz":
            mode = t
            continue
        if not re.fullmatch(r"-?\d+", t):
            raise AssertionError(f"unexpected {t!r} in path data")
        nums.append(int(t))
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
        self.assertLess(geo.DATA.stat().st_size, 80_000)


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
                                  "credit"})
        self.assertEqual(len(m["regions"]), 1)
        self.assertLess(len(json.dumps(m, ensure_ascii=False)), 30_000)  # no gazetteer, no other regions' shapes
        x0, y0, x1, y1 = m["focus"]
        self.assertTrue(x0 < m["pins"][0][0] < x1 and y0 < m["pins"][0][1] < y1)

    def test_the_demo_passes(self):
        s = json.loads((ROOT / "stories" / "veasy-map.json").read_text(encoding="utf-8"))
        self.assertEqual(engine.check_story(s), [])
        maps = [geo.scene_map(x, "tech") for x in s["scenes"] if x["type"] == "where"]
        self.assertEqual([m["level"] for m in maps], ["region", "district", "region"])


if __name__ == "__main__":
    unittest.main()
