"""The brush kit's scenes and the voice-synced marker: share, rail, compare, link, stat styles and "em". Videos go out
without a human review, so every rule the new brushes carry is code: a share shows only a percent an article states
with "%", a rail only dates the articles give in time order, a compare only a ratio a square can show, a link only a
verb the voice says, and a mark only words that are on screen and said in the scene."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import engine, ka_check, marks, news_check, props, speech, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO = ROOT / "stories" / "veasy-brushes.json"


def story(narration, *scenes, category="society"):
    return {"id": 7, "category": category, "date": "2026-11-02T10:00:00Z", "narration": narration,
            "scenes": [{"type": "hook", "at": narration.split()[0], "lines": ["x"]}, *scenes]}


class Share(unittest.TestCase):
    def test_the_percent_is_stated_with_the_sign(self):
        s = story("ერთი ორი სამი ოთხი", {"type": "share", "at": "სამი", "value": 34, "label": "ხმა"})
        self.assertEqual(news_check.stated(s, ["ამომრჩეველთა 34% მივიდა"]), [])
        self.assertEqual(news_check.stated(s, ["ამომრჩეველთა 34 % მივიდა"]), [])
        found = news_check.stated(s, ["34 ამომრჩეველი მივიდა, 34 პროცენტი"])
        self.assertTrue(found and found[0].startswith("N2: scene 1 (share) shows 34%"))
        self.assertTrue(news_check.stated(s, ["134% ზრდა"]))  # 134% is not 34%
        dec = story("ერთი ორი სამი ოთხი", {"type": "share", "at": "სამი", "value": 34.5, "label": "ხმა"})
        self.assertEqual(news_check.stated(dec, ["34,5% მივიდა"]), [])
        self.assertTrue(any("(share)" in p for p in news_check.problems(s, ["34 ადამიანი"])))

    def test_a_share_is_a_percent(self):
        self.assertTrue(engine.shape_problems({"type": "share", "value": 140, "label": "ა"}))
        self.assertTrue(engine.shape_problems({"type": "share", "value": 0, "label": "ა"}))
        self.assertEqual(engine.shape_problems({"type": "share", "value": 62, "label": "ა"}), [])


class Rail(unittest.TestCase):
    def test_dates_are_read(self):
        self.assertEqual(news_check.date_key("2 ნოემბერი, 22:00"), (None, 11, 2, 1320))
        self.assertEqual(news_check.date_key("3 ნოემბერს"), (None, 11, 3, None))
        self.assertEqual(news_check.date_key("2025 წლის მარტი"), (2025, 3, None, None))
        self.assertIsNone(news_check.date_key("ხვალ"))

    def test_events_run_in_time_order(self):
        ok = [{"when": "2 ნოემბერი, 22:00", "label": "ა"}, {"when": "3 ნოემბერი, 10:00", "label": "ბ"}]
        self.assertEqual(engine.rail_problems(ok), [])
        same_day = [{"when": "2 ნოემბერი, 09:00", "label": "ა"}, {"when": "2 ნოემბერი, 18:00", "label": "ბ"}]
        self.assertEqual(engine.rail_problems(same_day), [])
        back = engine.rail_problems(list(reversed(ok)))
        self.assertTrue(back and "time order" in back[0])
        self.assertTrue(engine.rail_problems([{"when": "2024", "label": "ა"}, {"when": "2023", "label": "ბ"}]))
        self.assertTrue(any("is not a date" in p for p in engine.rail_problems(
            [{"when": "მალე", "label": "ა"}, {"when": "2025", "label": "ბ"}])))
        self.assertTrue(engine.shape_problems({"type": "rail", "items": ok[:1]}))  # 2-4 events

    def test_dates_must_be_in_the_articles(self):
        s = story("ერთი ორი სამი ოთხი", {"type": "rail", "at": "სამი", "items": [
            {"when": "2 ნოემბერი, 22:00", "label": "ა"}, {"when": "3 ნოემბერი", "label": "ბ"}]})
        self.assertEqual(news_check.stated(s, ["2 ნოემბრის 22:00 სთ-დან 3 ნოემბრის დილამდე"]), [])
        missing = news_check.stated(s, ["2 ნოემბრის 22:00 სთ-დან"])
        self.assertEqual(len(missing), 1)
        self.assertIn("3 ნოემბერი", missing[0])


class Compare(unittest.TestCase):
    def test_one_unit_and_a_ratio_a_square_can_show(self):
        good = {"type": "compare", "unit": "ლარი", "items": [{"label": "ა", "value": 1200}, {"label": "ბ", "value": 300}]}
        self.assertEqual(engine.shape_problems(good), [])
        far = {**good, "items": [{"label": "ა", "value": 4100}, {"label": "ბ", "value": 100}]}
        self.assertTrue(any("show the two values as bars" in p for p in engine.shape_problems(far)))
        self.assertEqual(engine.shape_problems({**good, "items": [{"label": "ა", "value": 40}, {"label": "ბ", "value": 1}]}), [])
        self.assertTrue(engine.shape_problems({**good, "items": good["items"][:1]}))
        self.assertTrue(engine.shape_problems({**good, "items": [{"label": "ა", "value": 0}, {"label": "ბ", "value": 1}]}))
        self.assertIn("unit", engine.SCENES["compare"][0])  # one unit for both, required


class Link(unittest.TestCase):
    def test_the_edge_is_a_verb_the_voice_says(self):
        scene = {"type": "link", "at": "პრემიერი", "edge": "შეხვდა",
                 "items": [{"name": "პრემიერი"}, {"name": "ელჩი"}]}
        said = story("ამბავი ასეთია მოკლედ. პრემიერი შეხვდა ელჩს თბილისში ორშაბათს", scene)
        self.assertEqual(news_check.spoken(said), [])
        silent = story("ამბავი ასეთია მოკლედ. პრემიერი და ელჩი თბილისში იყვნენ ორშაბათს", scene)
        self.assertTrue(any(p.startswith("N11: scene 1 (link)") for p in news_check.spoken(silent)))
        self.assertTrue(engine.shape_problems({**scene, "items": scene["items"] * 2}))  # 2-3 nodes
        self.assertIn(("scene 1 (link) edge", "შეხვდა"), ka_check.screen_texts(said))  # its Georgian is checked


class StatStyle(unittest.TestCase):
    def test_flap_never_for_politics_or_crime(self):
        base = json.loads(DEMO.read_text(encoding="utf-8"))
        for category, bad in (("politics", True), ("crime", True), ("tech", False), ("sports", False)):
            s = {**base, "category": category}
            found = [p for p in engine.structure_problems(s) if "flap" in p]
            self.assertEqual(bool(found), bad, category)
        wheel = {**base, "category": "politics",
                 "scenes": [x if x.get("style") != "flap" else {**x, "style": "wheel"} for x in base["scenes"]]}
        self.assertFalse([p for p in engine.structure_problems(wheel) if "style" in p])

    def test_the_writer_hears_about_it_too(self):
        draft = {"category": "politics", "scenes": [{"type": "stat", "value": 1, "label": "ა", "style": "flap"}]}
        with mock.patch.object(news_check, "problems", return_value=[]), \
                mock.patch.object(ka_check, "problems", return_value=[]):
            found = writer._checks(draft, [], {})
        self.assertTrue(any("flap" in p for p in found))


class Em(unittest.TestCase):
    N = "გაზი შეწყდება ვარკეთილში. თბილისი ენერჯის ცნობით, მიწოდება 6400 აბონენტს შეუწყდება ორი დღით."

    def scene(self, **kw):
        return {"type": "stat", "at": "თბილისი ენერჯის", "value": 6400, "label": "აბონენტს შეუწყდება გაზი", **kw}

    def test_on_screen_and_said(self):
        self.assertEqual(news_check.spoken(story(self.N, self.scene(em="6400"))), [])
        self.assertEqual(news_check.spoken(story(self.N, self.scene(em="აბონენტს შეუწყდება"))), [])
        off_screen = news_check.spoken(story(self.N, self.scene(em="ორი დღით")))
        self.assertTrue(off_screen and "don't show it" in off_screen[0])
        unsaid = news_check.spoken(story(self.N, self.scene(em="შეუწყდება გაზი")))
        self.assertTrue(unsaid and "doesn't say it" in unsaid[0])
        self.assertTrue(news_check.spoken(story(self.N, self.scene(em="აბონენტს შეუწყდება გაზი და კიდევ"))))
        self.assertTrue(news_check.spoken(story(self.N, self.scene(em=["6400"]))))  # one phrase, one mark
        end = story(self.N, self.scene(), {"type": "end", "at": "ორი დღით", "em": "ორი"})
        self.assertTrue(any("takes no em" in p for p in news_check.spoken(end)))

    def test_the_kicker_is_never_marked(self):
        s = self.scene(kicker="რამდენს ეხება", em="რამდენს ეხება")
        self.assertIsNone(marks.locate(s))

    def test_case_endings_still_match_the_voice(self):
        self.assertTrue(marks.said("აბონენტი", "მიწოდება 6400 აბონენტს შეუწყდება"))
        self.assertFalse(marks.said("640", "მიწოდება 6400 აბონენტს"))  # a number must be equal

    def test_code_picks_the_kind_and_the_strokes(self):
        s = self.scene(em="6400")
        self.assertEqual(marks.kind(1, 1, s, "value", "6400"), "underline")  # a big number is underlined
        kinds = {marks.kind(sid, 1, self.scene(em="აბონენტს"), "label", "აბონენტს") for sid in range(40)}
        self.assertTrue(kinds <= {"circle", "box", "underline"} and len(kinds) > 1)  # varied, from the brush's kinds
        long = {marks.kind(sid, 1, self.scene(), "label", "აბონენტს შეუწყდება") for sid in range(40)}
        self.assertNotIn("circle", long)  # a circle only around a short word
        self.assertEqual(marks.strokes("politics")["roughness"], 0)
        self.assertEqual(marks.strokes("society")["roughness"], 0)
        self.assertGreater(marks.strokes("sports")["roughness"], 0)

    def test_the_mark_lands_when_the_voice_says_it(self):
        s = story(self.N, self.scene(em="6400"))
        words = speech.estimate_words(s["narration"])
        frames = speech.scene_frames(s, words)
        m = speech.mark_frames(s["scenes"], words, frames, 7, "society")
        self.assertIsNone(m[0])
        said = next(w for w in words if w["text"] == "6400")
        self.assertEqual(m[1]["field"], "value")
        self.assertLessEqual(abs(frames[1] + m[1]["at"] - round(said["start"] * speech.FPS)), 1)
        self.assertGreaterEqual(m[1]["frames"], marks.MIN_FRAMES)

    def test_props_carry_the_mark_and_nothing_else_changes(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            _, p = props.build(str(DEMO), "editorial", "silent", music="off")
            marked = {s["type"]: s["mark"] for s in p["scenes"] if s.get("mark")}
            self.assertEqual(set(marked), {"hook", "share", "rail", "link", "stat"})
            for m in marked.values():
                self.assertIn(m["kind"], ("underline", "box", "circle", "highlight", "bracket"))
                self.assertEqual(m["roughness"], 0)  # tech: service news, clean strokes
            _, plain = props.build(str(ROOT / "stories" / "veasy-scenes.json"), "editorial", "silent", music="off")
            self.assertFalse(any("mark" in s for s in plain["scenes"]))


class Demo(unittest.TestCase):
    def test_the_demo_uses_every_new_brush_and_passes(self):
        s = json.loads(DEMO.read_text(encoding="utf-8"))
        self.assertEqual(engine.check_story(s), [])
        types = {x["type"] for x in s["scenes"]}
        self.assertTrue({"share", "rail", "compare", "link"} <= types)
        self.assertEqual({x.get("style") for x in s["scenes"] if x["type"] == "stat"}, {"wheel", "flap"})
        self.assertGreaterEqual(sum(1 for x in s["scenes"] if x.get("em")), 3)


if __name__ == "__main__":
    unittest.main()
