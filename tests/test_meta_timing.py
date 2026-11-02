"""Date, families, QR, credits and scene timing: the parts of a video that come from data and code, not the writer."""
import json
import pathlib
import unittest

from tt_shorts import brand, meta, news_check, speech, voices

TT = brand.load("tbilisi-today")

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORIES = sorted((ROOT / "stories").glob("*.json"))
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "sources.json").read_text(encoding="utf-8"))


class Dates(unittest.TestCase):
    def test_tbilisi_time_and_georgian_month(self):
        d = meta.ka_date("2026-11-01T18:38:46Z")
        self.assertEqual((d["date"], d["time"], d["weekday"]), ("1 ნოემბერი 2026", "22:38", "კვირა"))

    def test_d1_utc_string_crosses_midnight(self):  # D1 datetime('now') has no zone and is UTC
        d = meta.ka_date("2026-12-31 21:30:00")
        self.assertEqual((d["date"], d["time"], d["weekday"]), ("1 იანვარი 2027", "01:30", "პარასკევი"))

    def test_the_date_chip_never_says_today(self):  # a video is watched for days: "დღეს" would be wrong tomorrow
        import datetime as dt
        d = meta.ka_date(dt.datetime.now(dt.timezone.utc).isoformat())
        self.assertEqual(meta.when(d), d["date"])
        self.assertNotEqual(meta.when(d), "დღეს")


class Data(unittest.TestCase):
    def test_every_site_category_has_a_family(self):
        for cat in TT["categories"]:
            self.assertIn(meta.family(cat), meta.FAMILIES)
        self.assertEqual(meta.family("defense"), "politics")
        self.assertEqual(meta.family("medicine"), "society")

    def test_look_follows_the_kind_of_story(self):
        self.assertEqual(meta.variant_for("politics"), "editorial")
        self.assertEqual(meta.variant_for("incidents"), "editorial")
        self.assertEqual(meta.variant_for("sports"), "kinetic")
        self.assertEqual(meta.variant_for("showbusiness"), "kinetic")
        self.assertEqual(meta.variant_for("economy"), "cards")
        self.assertEqual(meta.variant_for("medicine"), "cards")
        self.assertEqual(set(TT["look_by_family"]), set(meta.FAMILIES))

    def test_qr_points_to_the_story_page(self):
        url = meta.story_url(24725, "youtube")
        self.assertEqual(url, "https://tbilisi.today/stories/24725?utm_source=youtube&utm_medium=video")
        self.assertTrue(meta.qr_svg(url).startswith("<svg"))

    def test_cta_rotates_by_story(self):
        self.assertEqual({meta.cta_for(i) for i in range(30)}, set(TT["ctas"]))

    def test_sources_line_credits_the_outlets(self):
        self.assertEqual(meta.sources_line(["ON.ge"]), "წყარო: ON.ge")
        self.assertEqual(meta.sources_line(["a", "b", "c", "d", "e"]), "წყაროები: a, b, c +2")
        self.assertEqual(meta.sources_line([]), "")

    def test_no_long_dashes_in_fixed_text(self):  # brand v1.2: no em or en dash in text
        for t in TT["ctas"] + list(TT["categories"].values()):
            self.assertNotRegex(t, "[–—]")

    def test_voice_presets(self):
        self.assertEqual(voices.preset("anchor")["voice"], "Rasalgethi")
        self.assertEqual(voices.preset("plain")["style"], "")  # Google: try an empty style first
        self.assertEqual(voices.preset("family", "crime")["name"], "anchor")
        self.assertEqual(voices.preset("family", "society")["name"], "warm")
        self.assertTrue(set(TT["voice_by_family"].values()) <= set(voices.APPROVED))  # only tones the owner approved
        self.assertNotIn("Charon", {p["voice"] for p in voices.PRESETS.values()})  # SiTech's voice stays SiTech's


class Timing(unittest.TestCase):
    def test_display_words_from_spoken_timings(self):  # "6400" is said as three words but captioned as one
        spoken = [{"text": t, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, t in enumerate("ექვსი ათას ოთხას აბონენტს".split())]
        words = speech.to_display(spoken, "6400 აბონენტს", None)
        self.assertEqual([w["text"] for w in words], ["6400", "აბონენტს"])
        self.assertEqual((words[0]["start"], words[0]["end"]), (0.0, 1.4))

    def test_sample_stories_fit(self):  # anchors in order, every scene long enough, 28-45 s (a rubric: its format's)
        from tt_shorts import engine, formats
        for path in STORIES:
            story = json.loads(path.read_text(encoding="utf-8"))
            marks = speech.scene_frames(story, speech.estimate_words(story["narration"]))
            self.assertEqual(len(marks), len(story["scenes"]) + 1)
            lo, hi = 28, 45
            if story.get("rubric"):  # number: 20-25 s, the digest: 45-60 s
                f = formats.get(engine.program_format(path))
                lo, hi = f["min_seconds"], f["max_seconds"]
            self.assertTrue(lo <= marks[-1] / speech.FPS <= hi, f"{path.name}: {marks[-1] / speech.FPS:.1f}s")

    def test_news_rules(self):  # the news samples (their articles are in the fixtures); sitech-* is a blog post
        news = [p for p in STORIES if str(json.loads(p.read_text(encoding="utf-8"))["id"]) in FIXTURES]
        self.assertGreaterEqual(len(news), 2)
        for path in news:
            story = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(news_check.problems(story, FIXTURES[str(story["id"])]), [], path.name)
            self.assertNotRegex(story["narration"] + json.dumps(story["scenes"], ensure_ascii=False), "[–—]")


if __name__ == "__main__":
    unittest.main()
