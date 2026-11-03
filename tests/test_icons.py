"""Icons and pictograms (tt_shorts/icons.py): the vendored Lucide library, the Georgian stem map, the sign scene, the
isotype count of a stat and the icon motif. No person reviews a video before it is published, so the vocabulary is
checked here: every mapped icon exists, a stem survives Georgian case endings and doesn't catch look-alike words, and
nothing draws a number the articles don't have."""
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import engine, icons, props, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sample():
    return json.loads((ROOT / "stories" / "veasy-icons.json").read_text(encoding="utf-8"))


class Library(unittest.TestCase):
    def test_size_licence_and_geometry_only(self):
        lib = icons.library()
        self.assertTrue(200 <= len(lib) <= 260, len(lib))
        self.assertTrue((ROOT / "assets" / "icons" / "LICENSE").exists())
        self.assertIn("ISC", (ROOT / "assets" / "icons" / "LICENSE").read_text(encoding="utf-8"))
        for name, nodes in lib.items():
            self.assertFalse(any(c.isdigit() for c in name), name)  # an icon name is never read as a number (N2)
            for tag, attrs in nodes:
                self.assertIn(tag, {"path", "circle", "rect", "line", "polyline", "polygon", "ellipse"}, name)
                self.assertFalse(set(attrs) - {"d", "cx", "cy", "r", "rx", "ry", "x", "y", "width", "height", "x1",
                                               "y1", "x2", "y2", "points"}, name)

    def test_every_mapped_icon_exists(self):
        self.assertEqual(icons.unknown(), [])
        self.assertGreaterEqual(len([s for s, v in icons.STEMS.items() if v]), 150)

    def test_no_weapons_or_skulls(self):  # Veasy reports; it doesn't dramatize
        for bad in ("skull", "bomb", "sword", "swords", "axe", "pocket-knife", "ghost"):
            self.assertNotIn(bad, icons.library())


class StemMap(unittest.TestCase):
    def test_case_endings(self):
        for text, want in (("გაზი", "flame"), ("გაზის", "flame"), ("გაზით", "flame"), ("გაზზე", "flame"),
                           ("დენის", "zap"), ("ელექტროენერგიის", "zap"), ("წყლის", "droplet"), ("წყალში", "droplet"),
                           ("მეტროში", "train-front"), ("ავტობუსებს", "bus"), ("სკოლებში", "school"),
                           ("საავადმყოფოს", "hospital"), ("სასამართლომ", "scale"), ("ფასები", "tag"),
                           ("ლარის", "banknote"), ("გზაზე", "route"), ("ხიდის", "bridge"), ("თოვლი", "snowflake")):
            self.assertEqual(icons.find(text), [want], text)

    def test_look_alike_words_are_not_icons(self):  # the blockers
        for text in ("გაზრდა", "გაზიარება", "ქართველი", "ზღვარი", "ავტორი", "ავტომატი", "კატეგორია", "მერე",
                     "გამოცდილება", "ოპერაცია", "გულისხმობს", "პორტრეტი", "მზერა", "ტარება", "ენერგიული", "გაზიანი", "ბაზრობა", "სალარო", "კოდირება"):
            self.assertEqual(icons.find(text), [], text)
        self.assertEqual(icons.find("გაზეთი"), ["newspaper"])
        self.assertEqual(icons.find("გაზაფხული"), ["sprout"])
        self.assertEqual(icons.find("ჯარიმა"), ["receipt"])
        self.assertEqual(icons.find("მთავრობამ"), ["landmark"])  # not a mountain (მთა=)
        self.assertEqual(icons.find("მთაში"), ["mountain"])

    def test_expanded_stem_coverage(self):
        cases = (
            ("გაზსადენი", "flame"), ("გაზმომარაგება", "flame"), ("აირი", "flame"), ("ალის", "flame"),
            ("ძაბვა", "zap"), ("ჰიდროენერგია", "zap"), ("გენერაცია", "zap"),
            ("საწვავგასამართი", "fuel"), ("ავტოგასამართი", "fuel"), ("ნავთობპროდუქტები", "fuel"),
            ("გათბობის სისტემა", "heater"), ("დატენვა", "battery-charging"), ("ელექტროდამტენი", "ev-charger"),
            ("ჩართვა", "power"), ("გამორთვა", "power"), ("ძალაუფლება", "power"),
            ("როზეტი", "plug-zap"), ("შტეფსელი", "plug-zap"), ("სასმელი წყალი", "droplet"),
            ("სარწყავი", "droplet"), ("მორწყვა", "droplet"), ("ნალექები", "droplets"),
            ("ტენიანობა", "droplets"), ("ცვარი", "droplets"), ("წყალსაქაჩი", "faucet"),
            ("მილგაყვანილობა", "faucet"), ("შტორმი", "waves-horizontal"), ("ზვირთები", "waves-horizontal"),
            ("ნაგავსაყრელი", "trash"), ("დეველოპერი", "construction"), ("ინფრასტრუქტურა", "construction"),
            ("ავტოპარკი", "bus"), ("რკინიგზელი", "train-front"), ("ავტომანქანა", "car"),
            ("ტრანსპორტი", "car"), ("ჩარტერი", "plane"), ("ავიარეისი", "plane"),
            ("აფრენა", "plane-takeoff"), ("ტერმინალი", "plane-takeoff"), ("ესტაკადა", "bridge"),
            ("ტვირთბრუნვა", "container"), ("ლოგისტიკა", "container"), ("ნიშნული", "signpost"),
            ("მიმართულება", "signpost"), ("შესასვლელი", "door-open"), ("გასასვლელი", "door-closed"),
            ("ამანათი", "package"), ("პაკეტი", "package"), ("სამშობიარო", "hospital"),
            ("პოლიკლინიკა", "hospital"), ("რეანიმობილი", "ambulance"), ("თერაპევტი", "stethoscope"),
            ("პედიატრი", "stethoscope"), ("ექთანი", "stethoscope"), ("რეანიმაცია", "heart-pulse"),
            ("პულსი", "heart-pulse"), ("იმუნიზაცია", "syringe"), ("ფარმაცევტი", "pill"),
            ("ფარმაცია", "pill"), ("ახალშობილები", "baby"), ("დეკრეტი", "baby"),
            ("ჰუმანიტარული", "hand-heart"), ("გიმნაზია", "school"), ("ლიცეუმი", "school"),
            ("მაგისტრატურა", "graduation-cap"), ("ბაკალავრიატი", "graduation-cap"), ("დიპლომი", "graduation-cap"),
            ("ფაკულტეტი", "university"), ("ადვოკატი", "scale"), ("მოსარჩელე", "scale"),
            ("განაჩენი", "gavel"), ("სააპელაციო", "gavel"), ("სააგენტო", "landmark"),
            ("მუნიციპალიტეტი", "landmark"), ("პრემიერ-მინისტრი", "user"), ("თავმჯდომარე", "user"),
            ("პლებისციტი", "vote"), ("საკანონმდებლო", "scroll"), ("ნორმატიული", "scroll"),
            ("მანიფესტაცია", "megaphone"), ("საიდენტიფიკაციო", "id-card"), ("კიბერუსაფრთხოება", "shield-check"),
            ("სანქციები", "ban"), ("ემბარგო", "ban"), ("ხარჯვა", "banknote-arrow-up"),
            ("შემოდინება", "banknote-arrow-down"), ("თეთრი", "coins"), ("უნაღდო", "credit-card"),
            ("ტრანზაქცია", "credit-card"), ("საპენსიო", "piggy-bank"), ("საგადასახადო", "receipt"),
            ("საფასური", "tag"), ("მთვარე", "moon"), ("ღამე", "moon"), ("სეისმური", "activity"),
            ("აგარაკი", "house"), ("კოტეჯი", "house"), ("ჰოსტელი", "hotel"), ("მოსავალი", "wheat"),
            ("ვენახი", "grape"), ("მეღვინეობა", "wine"), ("ქვევრის", "amphora"), ("ბრწყინვალე", "sparkles"),
            ("სისუფთავე", "sparkles"), ("მიკროპროცესორი", "microchip"), ("ნანოტექნოლოგია", "microchip"),
            ("უპილოტო", "drone"), ("კიბერდაცვა", "lock"), ("განბლოკვა", "lock-open")
        )
        self.assertGreaterEqual(len(cases), 60)
        for text, want in cases:
            self.assertEqual(icons.find(text), [want], text)

    def test_order_and_two_word_stems(self):
        self.assertEqual(icons.find("მეტროს და ავტობუსის ფასი"), ["train-front", "bus", "tag"])
        self.assertEqual(icons.find("მზის პანელები"), ["solar-panel"])

    def test_resolve(self):
        self.assertEqual(icons.resolve("flame"), "flame")
        self.assertEqual(icons.resolve("გაზი"), "flame")
        self.assertEqual(icons.resolve("მეტრო"), "train-front")
        for bad in (None, "", "rocket-launcher", "ხატულა", 3):
            self.assertIsNone(icons.resolve(bad), bad)

    def test_verbs(self):
        for verb, word in (("rises", "გაიზარდა"), ("rises", "იზრდება"), ("falls", "შემცირდა"), ("stops", "შეწყდება"),
                           ("stops", "შეუწყდება"), ("opens", "გაიხსნება"), ("closes", "გადაიკეტა"),
                           ("moves", "გადაიდო"), ("splits", "გაიყო"), ("joins", "შეუერთდა")):
            self.assertTrue(icons.said(verb, f"ქუჩა {word}."), (verb, word))
        for verb, word in (("stops", "გადაწყდება"), ("rises", "კლიმატი"), ("falls", "ციკლი"), ("opens", "აღდგომა"),
                           ("splits", "გაიყოლა"), ("rises", "აღზრდა")):
            self.assertFalse(icons.said(verb, word), (verb, word))
        self.assertEqual(set(icons.VERBS), set(icons.VERB_ABOUT))


class Isotype(unittest.TestCase):
    def stat(self, **kw):
        return {"type": "stat", "value": 12, "icon": "bus", "label": "ა", **kw}

    def test_whole_counts_of_2_to_30(self):
        self.assertTrue(icons.isotype(self.stat()))
        self.assertTrue(icons.isotype(self.stat(value=2)))
        self.assertTrue(icons.isotype(self.stat(value=30.0)))
        for v in (1, 31, 2.5, 6400, True, float("inf"), float("nan"), "12"):
            self.assertFalse(icons.isotype(self.stat(value=v)), v)  # falls back to the bar: never "1 icon = N"
        self.assertFalse(icons.isotype(self.stat(suffix="%")))  # a percent is not a count of things
        self.assertFalse(icons.isotype(self.stat(icon="nothing")))
        self.assertFalse(icons.isotype({"type": "stat", "value": 12, "label": "ა"}))

    def test_part_of_whole_isotype(self):
        self.assertTrue(icons.isotype(self.stat(value=7, total=10)))
        self.assertTrue(icons.isotype(self.stat(value=2, total=2)))
        self.assertFalse(icons.isotype(self.stat(value=15, total=10)))  # value > total
        self.assertFalse(icons.isotype(self.stat(value=7, total=35)))  # total > 30
        self.assertFalse(icons.isotype(self.stat(value=7, total="10")))


class Scene(unittest.TestCase):
    def test_shape_problems(self):
        p = engine.shape_problems
        self.assertEqual(p({"type": "sign", "icon": "გაზი", "verb": "stops", "label": "ა"}), [])
        self.assertTrue(any("icon:" in x for x in p({"type": "sign", "icon": "ხატულა", "verb": "stops"})))
        self.assertTrue(any("verb:" in x for x in p({"type": "sign", "icon": "flame", "verb": "explodes"})))
        self.assertTrue(any("icon:" in x for x in p({"type": "stat", "value": 3, "label": "ა", "icon": "nope"})))
        self.assertEqual(p({"type": "stat", "value": 3, "label": "ა"}), [])

    def test_motif_must_resolve(self):
        s = sample()
        s["motif"] = "ხატულა"
        self.assertTrue(any("motif" in x for x in engine.structure_problems(s)))
        s["motif"] = "მეტრო"
        self.assertFalse(any("motif" in x for x in engine.structure_problems(s)))

    def test_the_sample_passes_and_n10_runs_without_articles(self):
        self.assertEqual(engine.check_story(sample()), [])
        s = sample()
        s["scenes"][1]["verb"] = "joins"
        self.assertTrue(any(x.startswith("N10") for x in engine.check_story(s)))
        s = sample()
        s["category"] = "crime"
        self.assertTrue(any("crime family" in x for x in engine.check_story(s)))

    def test_the_writer_knows_the_sign(self):
        from tt_shorts import writer
        self.assertIn('"type": "sign"', writer.SCHEMA)
        self.assertIn("rises|falls|stops|opens|closes|moves|splits|joins", writer.SCHEMA)
        s = sample()
        s["scenes"][1]["icon"] = "ხატულა"
        self.assertTrue(any("scene 1 (sign): icon" in x for x in icons.story_problems(s)))

    def test_motions_and_morph(self):
        p = engine.shape_problems
        self.assertEqual(p({"type": "sign", "icon": "გაზი", "verb": "stops", "motion": "pop", "label": "ა"}), [])
        self.assertEqual(p({"type": "sign", "icon": "გაზი", "verb": "stops", "motion": "pulse", "label": "ა"}), [])
        self.assertEqual(p({"type": "sign", "icon": "გაზი", "verb": "stops", "motion": "sketch", "label": "ა"}), [])
        self.assertEqual(p({"type": "sign", "icon": "გაზი", "verb": "stops", "motion": "morph", "morph_from": "zap", "label": "ა"}), [])
        self.assertTrue(any("motion:" in x for x in p({"type": "sign", "icon": "გაზი", "verb": "stops", "motion": "flying"})))
        self.assertTrue(any("morph_from:" in x for x in p({"type": "sign", "icon": "გაზი", "verb": "stops", "morph_from": "badicon"})))
        self.assertTrue(any("total:" in x for x in p({"type": "stat", "value": 12, "icon": "bus", "total": 5})))

    def test_attach_preserves_motion_and_morph(self):
        scenes = [{"type": "sign", "icon": "flame", "verb": "stops", "motion": "pop", "morph_from": "zap"}]
        attached = icons.attach(scenes, {"category": "society"})
        self.assertEqual(attached[0]["motion"], "pop")
        self.assertEqual(attached[0]["morphGlyph"], icons.nodes("zap"))
        self.assertEqual(attached[0]["glyph"], icons.nodes("flame"))

    def test_options_list_the_icons(self):
        o = engine.options()["icons"]
        self.assertEqual(o["count"], len(icons.library()))
        self.assertEqual(set(o["verbs"]), set(icons.VERBS))
        self.assertEqual(set(o["motions"]), set(icons.MOTIONS))
        self.assertIn("isotype", o["charts"])
        self.assertIn("flame", o["names"])


class MainIcon(unittest.TestCase):
    def test_motif_then_hook_then_scenes(self):
        s = sample()
        self.assertEqual(icons.story_icon(s), "flame")  # the hook names none: the first sign's
        s["scenes"][0]["lines"] = ["მეტროს", "ახალი ხაზი"]
        self.assertEqual(icons.story_icon(s), "train-front")
        s["motif"] = "ხიდი"
        self.assertEqual(icons.story_icon(s), "bridge")

    def test_none_for_crime_or_deaths(self):
        s = sample()
        s["category"] = "incidents"
        self.assertIsNone(icons.story_icon(s))
        s = sample()
        s["narration"] += " ორი ადამიანი გარდაიცვალა."
        self.assertIsNone(icons.story_icon(s))
        plain = {"category": "society", "narration": "ა", "scenes": [{"type": "hook", "lines": ["ხატულები"]}]}
        self.assertIsNone(icons.story_icon(plain))


class Props(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def test_signs_and_stats_carry_their_glyph(self):
        _, p = props.build(str(ROOT / "stories" / "veasy-icons.json"), "cards", "silent", music="off",
                           style={"motif": "icons"})
        sign = next(s for s in p["scenes"] if s["type"] == "sign")
        self.assertEqual((sign["icon"], sign["glyph"]), ("flame", icons.nodes("flame")))
        stat = next(s for s in p["scenes"] if s["type"] == "stat")
        self.assertEqual((stat["icon"], stat["isotype"]), ("bus", True))
        self.assertEqual(p["motifIcon"], icons.nodes("flame"))

    def test_variety_offers_the_icon_motif_only_with_an_icon(self):
        with tempfile.TemporaryDirectory() as d:
            s = sample()
            s["category"] = "crime"  # no pictograms at all
            path = pathlib.Path(d, "crime.json")
            path.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
            for i in range(8):
                s["id"] = f"crime-{i}"
                path.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
                _, p = props.build(str(path), "editorial", "silent", music="off")
                self.assertNotEqual(p["style"]["motif"], "icons")
                self.assertIsNone(p["motifIcon"])
                self.assertFalse(any("glyph" in x for x in p["scenes"]))
                self.assertNotIn("icon", next(x for x in p["scenes"] if x["type"] == "stat"))  # the bar instead
                variety.record("tbilisi-today", s["id"], "editorial", {**p["style"], "transition": p["transition"]}, [])


class BuildTool(unittest.TestCase):
    def tool(self):
        spec = importlib.util.spec_from_file_location("build_icons", ROOT / "tools" / "build_icons.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_the_asset_covers_the_whitelist(self):
        t = self.tool()
        self.assertEqual(sorted(icons.library()), t.wanted())

    def test_only_geometry_is_kept_and_bad_names_are_refused(self):
        t = self.tool()
        self.assertEqual(t.clean([["path", {"d": "M1 1", "fill": "currentColor", "onload": "x()"}]]),
                         [["path", {"d": "M1 1"}]])
        with self.assertRaises(ValueError):
            t.clean([["script", {}]])
        with self.assertRaises(SystemExit):
            t.build({})  # nothing the whitelist wants is there


if __name__ == "__main__":
    unittest.main()
