"""Variety: a run of videos moves through the options instead of repeating one style (owner, 2026-11-02: "1000 videos,
90% the same style, is no good"), and drawings are judged by code because nobody reviews them before publishing."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import art, variety, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Picks(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def run_day(self, n, look="editorial", loops=("politics-1.m4a", "politics-2.m4a", "politics-3.m4a")):
        picks = []
        for i in range(n):
            p = variety.pick("tbilisi-today", 1000 + i, look, "auto", [pathlib.Path(x) for x in loops])
            variety.record("tbilisi-today", 1000 + i, look, p, ["hook", "stat", "end"])
            picks.append(p)
        return picks

    def test_a_run_moves_through_every_option(self):
        picks = self.run_day(20)
        for key, options in variety.OPTIONS.items():
            self.assertEqual({p[key] for p in picks}, set(options), key)  # all used...
            counts = [sum(p[key] == o for p in picks) for o in options]
            self.assertLessEqual(max(counts) - min(counts), 1, key)  # ...and evenly
        self.assertEqual({p["transition"] for p in picks}, set(variety.TRANSITIONS["editorial"]))
        self.assertEqual({p["music"] for p in picks}, {"politics-1.m4a", "politics-2.m4a", "politics-3.m4a"})

    def test_no_two_videos_in_a_row_are_the_same(self):
        picks = self.run_day(12)
        for a, b in zip(picks, picks[1:]):
            self.assertNotEqual((a["hook"], a["motif"], a["enter"]), (b["hook"], b["motif"], b["enter"]))

    def test_a_story_keeps_its_picks(self):  # a re-render (another caption design) looks the same
        first = self.run_day(1)[0]
        self.run_day(3)
        again = variety.pick("tbilisi-today", 1000, "editorial", "auto", [pathlib.Path("politics-1.m4a"),
                                                                           pathlib.Path("politics-2.m4a"),
                                                                           pathlib.Path("politics-3.m4a")])
        self.assertEqual(again, first)

    def test_a_format_s_transition_is_kept(self):
        self.assertEqual(variety.pick("tbilisi-today", 1, "kinetic", "dot")["transition"], "dot")
        self.assertIn(variety.pick("tbilisi-today", 1, "kinetic", "auto")["transition"], variety.TRANSITIONS["kinetic"])
        self.assertIsNone(variety.pick("tbilisi-today", 1, "kinetic")["music"])  # no loops, no music

    def test_brands_have_their_own_history(self):
        self.run_day(5)
        self.assertEqual(variety.history("sitech"), [])

    def test_the_writer_hears_the_recent_scene_orders(self):
        self.run_day(3)
        recent = variety.recent_sequences("tbilisi-today")
        self.assertEqual(recent, ["hook>stat>end x3"])
        prompt = writer._prompt({"headline": "x"}, ["ა 1"], recent)
        self.assertIn("hook>stat>end x3", prompt)
        self.assertNotIn("Scene orders the latest", writer._prompt({"headline": "x"}, ["ა 1"]))

    def test_report_measures_sameness(self):
        self.run_day(8)
        r = variety.report("tbilisi-today")
        self.assertEqual(r["hook"]["distinct"], 4)
        self.assertEqual(r["scenes"]["most_used_share"], 1.0)  # every test video had the same scene order


class DrawingQuality(unittest.TestCase):
    def good(self):
        s = json.loads((ROOT / "stories" / "veasy-scenes.json").read_text(encoding="utf-8"))
        return next(x["svg"] for x in s["scenes"] if x["type"] == "draw")

    def test_the_demo_drawing_passes(self):
        self.assertEqual(art.scene_problems(self.good()), [])

    def test_small_static_or_loud_drawings_are_sent_back(self):
        tiny = ('<rect x="10" y="10" width="40" height="40" stroke="INK"/><circle cx="30" cy="30" r="5" stroke="INK"/>'
                '<line x1="1" y1="1" x2="9" y2="9" stroke="INK"/><line x1="2" y1="1" x2="9" y2="9" stroke="INK"/>'
                '<line x1="3" y1="1" x2="9" y2="9" stroke="INK"/><line x1="4" y1="1" x2="9" y2="9" stroke="INK"/>')
        found = " ".join(art.scene_problems(tiny))
        self.assertIn("small", found)
        self.assertIn("builds up", found)
        loud = self.good().replace('stroke="INK"', 'stroke="ACCENT"').replace('stroke="MUTED"', 'stroke="ACCENT"')
        loud += "".join(f'<circle class="p" style="--d:1s" cx="{100 + i * 10}" cy="100" r="4" fill="ACCENT"/>' for i in range(6))
        self.assertTrue(any("ACCENT is on" in p for p in art.scene_problems(loud)))
        off = self.good() + '<rect x="900" y="600" width="400" height="300" stroke="INK"/>'
        self.assertTrue(any("outside" in p for p in art.scene_problems(off)))

    def test_paths_count_with_relative_commands_and_translations(self):
        pts = art._path_points("M10 10 l 20 0 v 30 h -20 z")
        self.assertEqual(pts[:4], [(10, 10), (30, 10), (30, 40), (10, 40)])
        tree, _ = art.sanitize('<g transform="translate(500 300)"><rect x="0" y="0" width="10" height="10" stroke="INK"/></g>')
        self.assertIn((500.0, 300.0), art._box(tree))

    def test_a_failing_drawing_is_dropped_not_the_video(self):
        s = json.loads((ROOT / "stories" / "veasy-scenes.json").read_text(encoding="utf-8"))
        for x in s["scenes"]:
            if x["type"] == "draw":
                x["svg"] = "<image/>"
        kept, dropped = art.drop_bad(s)
        self.assertEqual(dropped, 1)
        self.assertNotIn("draw", [x["type"] for x in kept["scenes"]])
        self.assertEqual(len(kept["scenes"]), len(s["scenes"]) - 1)
        good = json.loads((ROOT / "stories" / "veasy-scenes.json").read_text(encoding="utf-8"))
        self.assertEqual(art.drop_bad(good)[1], 0)

    def test_drawing_is_on_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(writer.DRAW_ENV, None)
            self.assertTrue(writer.drawing())
            self.assertIn('"svg"', writer._prompt({"headline": "x"}, ["ა 1"]))
        with mock.patch.dict(os.environ, {writer.DRAW_ENV: "0"}):
            self.assertFalse(writer.drawing())


if __name__ == "__main__":
    unittest.main()
