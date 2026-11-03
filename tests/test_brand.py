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

    def test_the_agree_count_string_reaches_both_packs(self):  # rubrics: „მინიმუმ N“ (remotion scenes/rubrics.tsx)
        for n in brand.names():
            self.assertEqual(brand.load(n)["strings"]["at_least"], "მინიმუმ {n}")
        self.assertEqual(brand.for_remotion(brand.load())["strings"]["at_least"], "მინიმუმ {n}")

    def test_media_words_and_allow_list_come_from_the_base_and_the_pack(self):  # assets.py, news rule N13
        for n, own in (("tbilisi-today", "tbilisi.today"), ("sitech", "sitech.ge")):
            b = brand.load(n)
            self.assertEqual(b["strings"]["illustrative"], "საილუსტრაციო")
            self.assertIn("{author}", b["strings"]["media_credit"])
            self.assertEqual(b["media"]["own"], [own])  # the pack's own site
            self.assertIn("matsne.gov.ge", b["media"]["official"])  # the base's official sites, merged
            self.assertEqual(b["media"]["providers"], [])  # pictures are opt-in per pack (2026-11-03): none by default
            self.assertIn("illustrative", brand.for_remotion(b)["strings"])

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

    def test_design_rules_are_the_packs_own(self):  # frame.md says what a pack says, nothing more
        tt, st = brand.load("tbilisi-today"), brand.load("sitech")
        self.assertIn("text", tt["design"]["accent"]["never"])  # brand v1.2: the accent is never text
        self.assertTrue(tt["design"]["rules"])
        self.assertNotIn("accent", st["design"])  # SiTech's pack sets no such rules (yet)
        self.assertNotIn("rules", st["design"])

    def test_the_keyword_style_is_the_packs(self):  # captions.py design "keyword": how a page's keyword is drawn
        tt, st = brand.load("tbilisi-today"), brand.load("sitech")
        self.assertEqual(brand.keyword_style(tt), "underline")  # brand v1.2: the accent only as an active state
        self.assertEqual(brand.keyword_style(st), "tint")  # SiTech's orange may color a word
        self.assertEqual(brand.keyword_style({"name": "x"}), brand.KEYWORD_DEFAULT)
        self.assertIn(brand.KEYWORD_DEFAULT, brand.KEYWORD_STYLES)

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
            # design: the pack's own rules for composed films (frame.md): lists of words, a known accent use
            "baddesign": {**good, "design": ["no caps"]},
            "badaccent": {**good, "design": {"accent": {"allowed": ["glow"], "never": ["text"]}}},
            "badrules": {**good, "design": {"rules": "no caps"}},
            # the media layer (assets.py, N13): known providers only, domains not URLs, the label never empty
            "badprovider": {**good, "media": {"providers": ["openverse", "midjourney"]}},
            "aiprovider": {**good, "media": {"providers": ["ai"]}},
            "urlnotdomain": {**good, "media": {"own": ["https://tbilisi.today/stories"]}},
            "badmediakey": {**good, "media": {"stock": True}},
            "nolabel": {**good, "strings": {"illustrative": " "}},
            "nocredit": {**good, "strings": {"media_credit": "{source}"}},
            # the keyword captions' highlight: a known style, and never the accent as text where the pack forbids it
            "badkeyword": {**good, "design": {**good["design"], "keyword": "glow"}},
            "tintedtext": {**good, "design": {**good["design"], "keyword": "tint"}},
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


DARK = {  # the palettes before themes (2026-11-03): a pack's dark theme must stay exactly these
    "tbilisi-today": {"canvas": "#05080F", "panel": "#0B0F17", "ink": "#F8FAFC", "muted": "#A7B0BD", "accent": "#EF4444",
                      "line": "rgba(248,250,252,.12)", "lineStrong": "rgba(248,250,252,.24)",
                      "grid": "rgba(248,250,252,.045)", "ticker": "rgba(248,250,252,.06)",
                      "waiting": "rgba(248,250,252,.42)", "markBg": "#0B0B0E", "onAccent": "#FFFFFF", "markInk": "#FFFFFF"},
    "sitech": {"canvas": "#171817", "panel": "#1F201E", "ink": "#F1EDE4", "muted": "#B6B4AC", "accent": "#FF792E",
               "line": "rgba(241,237,228,.14)", "lineStrong": "rgba(241,237,228,.26)", "grid": "rgba(241,237,228,.05)",
               "ticker": "rgba(241,237,228,.06)", "waiting": "rgba(241,237,228,.42)", "markBg": "#171817",
               "onAccent": "#171817", "markInk": "#FFFFFF"},
}


class Themes(unittest.TestCase):
    """A pack's palettes (owner, 2026-11-03: "not only on a night background; a white one too")."""

    def setUp(self):
        brand.load.cache_clear()

    def tearDown(self):
        brand.load.cache_clear()

    def test_the_default_is_today_s_dark_palette_unchanged(self):
        for n, colors in DARK.items():
            b = brand.load(n)
            self.assertEqual((b["theme"], b["default_theme"]), ("dark", "dark"))
            self.assertEqual(b["colors"], colors, n)  # zero visual change for every render that names no theme
            self.assertEqual(brand.mode(b["colors"]), "dark")
            r = brand.for_remotion(b)
            self.assertEqual((r["theme"], r["mode"], r["colors"]["qrDark"], r["colors"]["qrLight"]),
                             ("dark", "dark", colors["canvas"], "#FFFFFF"))  # the QR as before: canvas on white

    def test_both_packs_ship_a_light_theme(self):
        st, tt = brand.load("sitech"), brand.load("tbilisi-today")
        light = brand.themed(st, "light")
        self.assertEqual((light["colors"]["canvas"], light["colors"]["ink"]), ("#F1EDE4", "#171817"))  # paper, coal
        self.assertEqual(light["colors"]["accent"], "#FF792E")  # one accent in every theme
        self.assertEqual(brand.mode(light["colors"]), "light")
        self.assertEqual(pathlib.Path(light["_logo"]["header"]).name, "logo-horizontal-coal.svg")
        self.assertEqual(pathlib.Path(light["_logo"]["end"]).name, "logo-stacked-coal.svg")
        self.assertEqual(brand.qr_colors(light["colors"]), ("#171817", "#F1EDE4"))  # a QR on paper, dark on light
        for f in light["_logo"].values():  # the coal logo is the white one, recolored, nothing else
            src = pathlib.Path(f.replace("-coal", ""))
            self.assertEqual(pathlib.Path(f).read_text(encoding="utf-8"),
                             src.read_text(encoding="utf-8").replace("#FFFFFF", "#171817"))
        self.assertEqual(brand.theme_names(st, allowed_only=True), ["dark", "light"])
        self.assertEqual(brand.theme_problems(light), [])
        tl = brand.themed(tt, "light")
        self.assertEqual(brand.mode(tl["colors"]), "light")
        self.assertEqual(tl["colors"]["accent"], "#EF4444")  # brand v1.2's one red
        self.assertEqual((tl["colors"]["markBg"], tl["colors"]["markInk"]), ("#0B0B0E", "#FFFFFF"))  # the mark unchanged
        self.assertIsNone(tl["_logo"])  # the t-mark is drawn in code

    def test_tbilisi_today_light_waits_for_the_owner(self):  # brand v1.2 is dark: the light theme is a preview
        tt = brand.load("tbilisi-today")
        self.assertEqual(brand.theme_names(tt, allowed_only=True), ["dark"])
        self.assertIn("allowed: false", brand.theme_problems(brand.themed(tt, "light"))[0])
        self.assertEqual(brand.theme_problems(tt), [])

    def test_unknown_theme_fails(self):
        with self.assertRaises(brand.BrandError):
            brand.themed(brand.load("sitech"), "neon")
        self.assertEqual(brand.themed(brand.load("sitech"), "default")["theme"], "dark")
        self.assertEqual(brand.of({"brand": "sitech"}, "light")["colors"]["canvas"], "#F1EDE4")

    def test_contrast_is_wcag(self):
        self.assertAlmostEqual(brand.contrast("#FFFFFF", "#000000"), 21.0, places=2)
        self.assertAlmostEqual(brand.contrast("#777777", "#777777"), 1.0, places=6)
        self.assertAlmostEqual(brand.contrast("rgba(255,255,255,0)", "#000000"), 1.0, places=6)  # alpha over ground
        self.assertGreater(brand.contrast("#F1EDE4", "#171817"), 7)
        self.assertIsNone(brand.rgba("white"))
        self.assertEqual(brand.rgba("rgba(5,8,15,.5)"), (5, 8, 15, 0.5))

    def test_every_shipped_theme_passes_the_floors(self):
        for n in brand.names():
            b = brand.load(n)
            for t, spec in b["themes"].items():
                self.assertEqual(brand.contrast_problems(spec["colors"]), [], f"{n}:{t}")
                c = spec["colors"]
                self.assertGreaterEqual(brand.contrast(c["ink"], c["canvas"]), brand.CONTRAST["ink"])
                self.assertGreaterEqual(brand.contrast(c["muted"], c["panel"]), brand.CONTRAST["muted"])

    def test_unreadable_or_broken_themes_fail_loudly(self):
        good = json.loads((ROOT / "brands" / "sitech" / "brand.json").read_text(encoding="utf-8"))
        light = good["themes"]["light"]

        def with_theme(**over):
            return {**good, "themes": {**good["themes"], "light": {**light, **over}}}

        def colors(**over):
            return with_theme(colors={**light["colors"], **over})
        cases = {
            "darkondark": colors(canvas="#3A3B39", panel="#3F403E"),  # a dark ground under the coal ink
            "lightonlight": colors(ink="#E8E4DA"),  # light ink on paper
            "mutedlow": colors(muted="#A9A69E"),  # muted under 4.5:1
            "accentgone": colors(accent="#EDE8DE"),  # the dot vanishes into the paper
            "buttontext": colors(onAccent="#FF9050"),  # the button's text on the accent
            "waiting": colors(waiting="rgba(23,24,23,.12)"),  # a caption word not yet spoken can't be read
            "missing": with_theme(colors={k: v for k, v in light["colors"].items() if k != "panel"}),
            "notcolor": colors(canvas="paper"),
            "rgbacanvas": colors(canvas="rgba(241,237,228,1)"),  # the canvas is #RRGGBB (alpha() in brand.ts)
            "badallowed": with_theme(allowed="yes"),
            "badkey": with_theme(tint="#00FF00"),
            "badname": {**good, "themes": {**good["themes"], "Light Mode": light}},
            "nologo": with_theme(logo={"header": "missing.svg"}),
            "nodefault": {**good, "default_theme": "sepia"},
            "defaultpreview": {**good, "default_theme": "light", "themes": {**good["themes"],
                                                                           "light": {**light, "allowed": False}}},
            "nothemes": {k: v for k, v in good.items() if k not in ("themes",)},
        }
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "_ka").mkdir()
            (d / "_ka" / "brand.json").write_text((ROOT / "brands" / "_ka" / "brand.json").read_text(encoding="utf-8"),
                                                  encoding="utf-8")
            for name, data in cases.items():
                pack(d, name, {**data, "name": name})
                for f in ("logo-horizontal.svg", "logo-stacked.svg", "logo-horizontal-coal.svg", "logo-stacked-coal.svg"):
                    (d / name / f).write_bytes((ROOT / "brands" / "sitech" / f).read_bytes())
            with mock.patch.object(brand, "DIR", d):
                for name in cases:
                    brand.load.cache_clear()
                    with self.assertRaises(brand.BrandError, msg=name):
                        brand.load(name)

    def test_a_pack_with_colors_alone_has_one_theme(self):  # a new client's first pack needs no themes block
        tt = json.loads((ROOT / "brands" / "tbilisi-today" / "brand.json").read_text(encoding="utf-8"))
        flat = {k: v for k, v in tt.items() if k not in ("themes", "default_theme")}
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "_ka").mkdir()
            (d / "_ka" / "brand.json").write_text((ROOT / "brands" / "_ka" / "brand.json").read_text(encoding="utf-8"),
                                                  encoding="utf-8")
            pack(d, "flat", {**flat, "name": "flat", "colors": tt["themes"]["dark"]["colors"]})
            pack(d, "paper", {**flat, "name": "paper", "colors": tt["themes"]["light"]["colors"]})
            with mock.patch.object(brand, "DIR", d):
                self.assertEqual(list(brand.load("flat")["themes"]), ["dark"])
                self.assertEqual(brand.load("flat")["colors"], DARK["tbilisi-today"])
                self.assertEqual(brand.load("paper")["theme"], "light")  # named by its canvas

    def test_remotion_reads_the_theme_through_tokens(self):  # no color typed in a component (CLAUDE.md)
        import re
        src = ROOT / "remotion" / "src"
        typed = []
        for f in sorted(src.rglob("*.tsx")):
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if line.strip().startswith(("//", "/*", "*")):
                    continue  # a comment
                for m in re.finditer(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgba?\(|\"(white|black)\"", line):
                    if m.group(0) == "#000" and "linear-gradient(" in line:
                        continue  # a mask's alpha (Captions.tsx, map.tsx), not a color
                    typed.append(f"{f.name}:{i}: {line.strip()[:80]}")
        self.assertEqual(typed, [])
        ts = (src / "brand.ts").read_text(encoding="utf-8")
        for token in ("MARK_INK", "QR_LIGHT"):
            self.assertRegex(ts, rf"export let {token} = ")


class Props(unittest.TestCase):
    def test_a_theme_reaches_the_props_and_the_files(self):
        story = ROOT / "stories" / "sitech-cybercartel.json"
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            work, p = props.build(str(story), "auto", "silent", music="off", theme="light")
            self.assertEqual((p["theme"], p["brand"]["theme"], p["brand"]["mode"]), ("light", "light", "light"))
            self.assertEqual(p["brand"]["colors"]["canvas"], "#F1EDE4")
            self.assertIn('fill="#171817"', (work / "public" / "brand" / "header.svg").read_text(encoding="utf-8"))
            self.assertIn("#171817", p["qrSvg"])  # the QR's modules are the coal ink
            self.assertNotIn("#FFFFFF", p["qrSvg"])  # ... on the paper, not on a white box
            _, d = props.build(str(story), "auto", "silent", music="off")
            self.assertEqual((d["theme"], d["brand"]["colors"]["canvas"]), ("dark", "#171817"))

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
