"""`engine plan` (tt_shorts/plan.py): a free storyboard that never pays for a voice nor uses up the variety history.
The browser part (probe.run_jobs) is replaced by blank stills here; `engine plan` itself is run by hand."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import engine, formats, plan, probe, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = ROOT / "stories" / "24835.json"


def fake_jobs(jobs, timeout=900):
    """Blank 1080x1920 stills and empty layout reports, as remotion/probe.mjs would return them."""
    from PIL import Image
    rows = []
    for job in jobs:
        out = pathlib.Path(job["out"])
        out.mkdir(parents=True, exist_ok=True)
        mine = []
        for f in job["frames"]:
            file = out / f"{job['name']}-{f}.png"
            Image.new("RGB", (1080, 1920), (5, 8, 15)).save(file)
            mine.append({"job": 0, "frame": f, "file": str(file), "probe": {"frame": f, "texts": []}})
        rows.append(mine)
    return rows, {"done": True, "built": False}


class Plan(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def run_plan(self, **kw):
        with mock.patch.object(probe, "run_jobs", side_effect=fake_jobs), \
                mock.patch.object(probe, "cmaps_for", return_value={}):
            return plan.run(STORY, formats.get("news"), **kw)

    def test_a_storyboard_of_24835(self):
        r = self.run_plan()
        self.assertEqual(r["problems"], [])
        self.assertEqual([s["type"] for s in r["scenes"]], ["hook", "stat", "timeline", "where", "sources", "end"])
        self.assertAlmostEqual(r["scenes"][-1]["end"], r["seconds"], places=0)
        for s in r["scenes"]:
            self.assertGreater(s["seconds"], 2)
            self.assertGreaterEqual(s["words"], 1)
            self.assertTrue(all(t["shown"] >= t["need"] for t in s["texts"]), s)
        self.assertEqual(sum(s["words"] for s in r["scenes"]), len(json.loads(STORY.read_text(encoding="utf-8"))
                                                                     ["narration"].split()))
        self.assertGreater(r["captions"]["pages"], 5)
        self.assertEqual(set(r["variety"]), {"hook", "motif", "enter", "transition", "music", "current"})
        self.assertTrue(all(w.startswith("motion ") for w in r["warnings"]))

    def test_the_contact_sheet_is_half_size(self):
        from PIL import Image
        r = self.run_plan()
        self.assertTrue(r["sheet"].endswith(".plan.jpg"), r["sheet"])
        with Image.open(r["sheet"]) as im:
            cols = plan.COLUMNS
            self.assertEqual(im.size[0], cols * plan.HALF[0] + (cols + 1) * plan.GAP)
            self.assertEqual(im.size[1], 2 * (plan.HALF[1] + plan.LABEL) + 3 * plan.GAP)  # 6 scenes: two rows
        out = pathlib.Path(self.home.name) / "mine.png"
        self.assertEqual(self.run_plan(out=out)["sheet"], str(out.resolve()))

    def test_planning_records_no_variety(self):
        before = variety.history("tbilisi-today")
        first = self.run_plan()
        self.assertEqual(variety.history("tbilisi-today"), before)
        self.assertEqual(self.run_plan()["variety"], first["variety"])  # nothing was used up: the same picks again

    def test_the_picks_alone_match_the_storyboard_and_follow_a_director(self):
        r = self.run_plan(director="map")
        got = plan.picks(STORY, director="map")
        self.assertEqual((got["look"], got["director"], got["current"]), (r["look"], "map", r["variety"]["current"]))
        self.assertEqual({k: got[k] for k in ("hook", "motif", "enter", "transition")},
                         {k: r["variety"][k] for k in ("hook", "motif", "enter", "transition")})
        self.assertEqual(r["director"], "map")
        self.assertEqual(plan.picks(STORY, look="kinetic")["look"], "kinetic")
        self.assertEqual(variety.history("tbilisi-today"), [])

    def test_a_probe_problem_or_unreadable_text_is_a_problem(self):
        def bad(jobs, timeout=900):
            rows, done = fake_jobs(jobs)
            rows[0][1]["probe"]["texts"] = [{"region": "scene", "text": "x", "box": [60, 1300, 400, 200], "size": 40,
                                             "family": "Brand", "weight": "700", "opacity": 1}]
            return rows, done
        with mock.patch.object(probe, "run_jobs", side_effect=bad), mock.patch.object(probe, "cmaps_for", return_value={}):
            r = plan.run(STORY, formats.get("news"))
        self.assertTrue(any(p.startswith("probe band") for p in r["problems"]), r["problems"])
        with mock.patch.object(plan.motion_rules, "check", return_value={"timeline": [], "cuts": [], "findings": [],
                                                                          "holds": ["motion read: x"], "warnings": []}):
            r = plan.run(STORY, formats.get("news"), with_probe=False)
        self.assertEqual(r["problems"], ["motion read: x"])

    def test_a_story_that_does_not_time_is_a_problem_not_a_crash(self):
        s = json.loads(STORY.read_text(encoding="utf-8"))
        s["scenes"][2]["at"] = "სიტყვები რომლებიც არსად არის"
        path = pathlib.Path(self.home.name) / "broken.json"
        path.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        r = plan.run(path, formats.get("news"))
        self.assertTrue(r["problems"][0].startswith("timing:"), r)

    def test_the_engine_command(self):
        with mock.patch.object(probe, "run_jobs", side_effect=fake_jobs), \
                mock.patch.object(probe, "cmaps_for", return_value={}), \
                mock.patch("builtins.print") as said:
            code = engine.main(["plan", str(STORY), "--look", "kinetic"])
        self.assertEqual(code, 0)
        out = json.loads(said.call_args[0][0])
        self.assertEqual(out["look"], "kinetic")
        self.assertIn("kinetic", out["sheet"])


if __name__ == "__main__":
    unittest.main()
