"""Date, families, palettes, QR and the sample stories: the parts of a video that come from data, not the writer."""
import json
import pathlib
import unittest

from tt_shorts import news_check, render, templates, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORIES = sorted((ROOT / "stories").glob("*.json"))
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "sources.json").read_text(encoding="utf-8"))


class Dates(unittest.TestCase):
    def test_tbilisi_time_and_georgian_month(self):
        d = templates.ka_date("2026-11-01T18:38:46Z")
        self.assertEqual((d["date"], d["time"], d["weekday"]), ("1 ნოემბერი 2026", "22:38", "კვირა"))

    def test_d1_utc_string_crosses_midnight(self):  # D1 datetime('now') has no zone and is UTC
        d = templates.ka_date("2026-12-31 21:30:00")
        self.assertEqual((d["date"], d["time"], d["weekday"]), ("1 იანვარი 2027", "01:30", "პარასკევი"))


class Brand(unittest.TestCase):
    def test_every_site_category_has_a_family_and_music_name(self):
        for cat in templates.CATEGORY_KA:
            self.assertIn(templates.family(cat), templates.FAMILIES)
        self.assertEqual(templates.family("defense"), "politics")
        self.assertEqual(templates.family("medicine"), "society")

    def test_palettes(self):
        for theme in templates.THEMES:
            for cat in ("politics", "crime", "sports"):
                p = templates.palette(theme, cat)
                for k in ("bg", "ink", "muted", "line", "accent", "cap_fg", "cap_box", "cap_hi"):
                    self.assertRegex(p[k], r"^#[0-9A-Fa-f]{6}$", f"{theme} {cat} {k}")
                self.assertNotEqual(p["cap_fg"], p["cap_box"])

    def test_qr_points_to_the_story_page(self):
        url = templates.story_url(24725, "youtube")
        self.assertEqual(url, "https://tbilisi.today/stories/24725?utm_source=youtube&utm_medium=video")
        self.assertTrue(templates.qr_svg(url).startswith("<svg"))

    def test_cta_rotates_by_story(self):
        self.assertEqual(templates.cta_for(1), templates.cta_for(1))
        self.assertEqual({templates.cta_for(i) for i in range(30)}, set(templates.CTAS))

    def test_voice_presets(self):
        self.assertEqual(voices.preset("anchor")["voice"], "Kore")
        self.assertEqual(voices.preset("family", "crime")["name"], "documentary")
        self.assertNotIn("Charon", {p["voice"] for p in voices.PRESETS.values()})  # SiTech's voice stays SiTech's


class SampleStories(unittest.TestCase):
    def test_anchors_and_scene_lengths(self):  # the same timing QA as a render, on estimated timings
        for path in STORIES:
            story = json.loads(path.read_text(encoding="utf-8"))
            words = render.estimate_words(story["narration"])
            starts, after = [0.0], 0
            for s in story["scenes"][1:]:
                t, after = render.anchor(words, s["at"], after)
                starts.append(t)
            starts.append(words[-1]["end"] + render.END_HOLD)
            starts = render.lend_time(starts, [s["type"] for s in story["scenes"]])
            for s, a, b in zip(story["scenes"], starts, starts[1:]):
                self.assertGreaterEqual(b - a, render.MIN_SCENE.get(s["type"], render.MIN_SCENE_DEFAULT) - 1e-6,
                                        f"{path.name} {s['type']}")
            self.assertTrue(28 <= starts[-1] <= 45, f"{path.name}: {starts[-1]:.1f}s")

    def test_news_rules(self):
        for path in STORIES:
            story = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(news_check.problems(story, FIXTURES[str(story["id"])]), [], path.name)
            self.assertTrue(story["narration"].rstrip().endswith("."))


if __name__ == "__main__":
    unittest.main()
