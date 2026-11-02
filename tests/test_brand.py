"""Brand packs: a new client is a folder in brands/, and a broken pack fails on load, not halfway through a render."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, meta, props, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent


def pack(d, name, data):
    (d / name).mkdir(parents=True, exist_ok=True)
    (d / name / "brand.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class Packs(unittest.TestCase):
    def setUp(self):
        brand.load.cache_clear()

    def tearDown(self):
        brand.load.cache_clear()

    def test_shipped_packs_load(self):
        self.assertEqual(brand.names(), ["sitech", "tbilisi-today"])  # _ka is a base, not a pack
        for n in brand.names():
            b = brand.load(n)
            self.assertEqual(set(b["_fonts"]), set(brand.FONT_WEIGHTS))
            self.assertTrue(all(pathlib.Path(f).is_file() for f in b["_fonts"].values()))

    def test_a_base_is_not_a_brand(self):
        with self.assertRaises(brand.BrandError):
            brand.load("_ka")

    def test_the_packs_differ_only_in_data(self):
        tt, st = brand.load("tbilisi-today"), brand.load("sitech")
        self.assertEqual(meta.display_url(24725, tt), "tbilisi.today/stories/24725")
        self.assertEqual(meta.story_url("x", "tiktok", st), "https://sitech.ge/ka/blog/x/?utm_source=tiktok&utm_medium=video")
        self.assertEqual(tt["colors"]["accent"], "#EF4444")  # tbilisi.today v1.2: one red
        self.assertEqual(st["colors"]["accent"], "#FF792E")  # SiTech orange
        self.assertEqual(pathlib.Path(st["_logo"]["header"]).name, "logo-horizontal.svg")
        self.assertIsNone(tt["_logo"])  # the t-mark is drawn in code

    def test_package_words_come_from_the_base_and_the_pack(self):
        tt, st = brand.load("tbilisi-today"), brand.load("sitech")
        self.assertIn("{url}", tt["package"]["more"])  # from _ka
        self.assertEqual(tt["package"]["link_in_bio"], st["package"]["link_in_bio"])
        self.assertIn("#tbilisitoday", tt["package"]["hashtags"])
        self.assertIn("#SiTech", st["package"]["hashtags"])
        self.assertNotIn("#tbilisitoday", st["package"]["hashtags"])  # a pack's tags stay its own

    def test_base_months_reach_both_packs(self):
        for n in brand.names():
            self.assertEqual(meta.ka_date("2026-11-01T18:38:46Z", n)["date"], "1 ნოემბერი 2026")

    def test_charon_is_sitech_only(self):  # SiTech's voice stays SiTech's
        st, tt = brand.load("sitech"), brand.load("tbilisi-today")
        self.assertEqual(voices.preset("family", "security", st)["voice"], "Charon")
        with self.assertRaises(ValueError):
            voices.preset("sitech", "politics", tt)
        self.assertNotIn("Charon", {voices.preset("family", c, tt)["voice"] for c in tt["categories"]})

    def test_pack_spoken_forms_sit_under_the_story_say(self):
        s = brand.with_say({"brand": "sitech", "say": {"Straiker": "სტრაიკერი"}})
        self.assertEqual(s["say"], {"SiTech": "საი-თეჩი", "Straiker": "სტრაიკერი"})
        own = brand.with_say({"brand": "sitech", "say": {"SiTech": "საითეჩი"}})
        self.assertEqual(own["say"]["SiTech"], "საითეჩი")  # the story's entry wins
        self.assertEqual(brand.with_say({"say": {}}), {"say": {}})  # tbilisi-today has no pack say

    def test_unknown_or_broken_packs_fail_loudly(self):
        with self.assertRaises(brand.BrandError):
            brand.load("no-such-client")
        good = json.loads((ROOT / "brands" / "tbilisi-today" / "brand.json").read_text(encoding="utf-8"))
        cases = {
            "nofooter": {k: v for k, v in good.items() if k != "footer"},
            "badfamily": {**good, "family_by_category": {"politics": "jazz"}},
            "badlook": {**good, "look_by_family": {**{f: "cards" for f in brand.FAMILIES}, "politics": "neon"}},
            "badvoice": {**good, "voice_by_family": {f: "Charon" for f in brand.FAMILIES}},
            "nologo": {**good, "logo": {"kind": "svg", "header": "missing.svg"}},
            "noid": {**good, "link": {"display": "x", "qr": "https://x.ge/"}},
            # engine package's words: a link line needs {url}; hashtags start with # and are 3+ different ones
            "nourl": {**good, "package": {"more": "დეტალები საიტზე"}},
            "badtags": {**good, "package": {"hashtags": ["#ამბები", "საქართველო", "#ა ბ"]}},
            "fewtags": {**good, "package": {"hashtags": ["#ამბები", "#ამბები", "#x"]}},
        }
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "_ka").mkdir()
            (d / "_ka" / "brand.json").write_text((ROOT / "brands" / "_ka" / "brand.json").read_text(encoding="utf-8"),
                                                  encoding="utf-8")
            for name, data in cases.items():
                pack(d, name, {**data, "name": name})
            with mock.patch.object(brand, "DIR", d):
                for name in cases:
                    brand.load.cache_clear()
                    with self.assertRaises(brand.BrandError, msg=name):
                        brand.load(name)

    def test_a_new_client_is_a_folder(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "_ka").mkdir()
            (d / "_ka" / "brand.json").write_text((ROOT / "brands" / "_ka" / "brand.json").read_text(encoding="utf-8"),
                                                  encoding="utf-8")
            tt = json.loads((ROOT / "brands" / "tbilisi-today" / "brand.json").read_text(encoding="utf-8"))
            pack(d, "acme", {**tt, "name": "acme", "label": "Acme", "link": {"display": "acme.ge/{id}",
                                                                              "qr": "https://acme.ge/{id}"}})
            with mock.patch.object(brand, "DIR", d):
                self.assertEqual(brand.names(), ["acme"])
                self.assertEqual(meta.display_url(7, "acme"), "acme.ge/7")


class Props(unittest.TestCase):
    def test_props_carry_the_pack(self):
        story = ROOT / "stories" / "sitech-cybercartel.json"
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            work, p = props.build(str(story), "auto", "silent", music="off")
            self.assertEqual(p["brand"]["name"], "sitech")
            self.assertEqual(p["brand"]["colors"]["accent"], "#FF792E")
            self.assertEqual(p["url"], "sitech.ge/ka/blog")
            self.assertEqual(p["category"], "უსაფრთხოება")
            self.assertEqual(p["previewNote"], "ხმის გარეშე · პრევიუ")
            self.assertEqual(sorted(f.name for f in (work / "public" / "fonts").iterdir()),
                             [f"brand-{w}.woff2" for w in brand.FONT_WEIGHTS])
            self.assertTrue((work / "public" / "brand" / "header.svg").is_file())
            self.assertNotIn("_fonts", json.dumps(p["brand"]))  # no server paths in the props


if __name__ == "__main__":
    unittest.main()
