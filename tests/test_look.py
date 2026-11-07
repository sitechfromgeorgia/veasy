"""`engine look` / `veasy_look`: free, read-only, on a real job and on a story with no job."""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from tt_shorts import look, queue, store

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = ROOT / "stories" / "24835.json"


class Look(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_a_story_with_no_job(self):
        r = look.look(story="stories/24835.json")
        self.assertEqual((r["kind"], r["state"]), ("story", None))
        self.assertTrue(r["numbers"]["scenes"] > 2)
        self.assertIn("veasy_plan", r["next"])
        self.assertTrue(any("motion" in m for m in r["missing"]))  # no props yet: named, never rendered
        self.assertEqual(r["sheets"], {})
        by_name = look.look(story="24835")  # a name in stories/
        self.assertEqual(by_name["story"], r["story"])  # the same file, the same path, on every OS

    def test_a_real_job_lists_its_cached_files(self):
        job, created = queue.add(story=str(STORY))
        self.assertTrue(created)
        video = store.render_path("tbilisi-today", "24835", "news", "editorial", "page")
        video.write_bytes(b"x")
        video.with_suffix(".sheet.jpg").write_bytes(b"x")
        store.props_path(video).write_text("{}", encoding="utf-8")
        queue._set(job["id"], state="done", result={"file": str(video), "problems": [], "qa": {"problems": []}})
        before = sorted(p.name for p in pathlib.Path(self.tmp.name).rglob("*"))
        r = look.look(job=job["id"])
        self.assertEqual((r["kind"], r["state"]), ("job", "done"))
        self.assertIn("qa_sheet", r["sheets"])
        self.assertIn("plan_sheet", r["missing"])  # not made, so named, not rendered
        self.assertIn("veasy_package", r["next"])
        self.assertEqual(before, sorted(p.name for p in pathlib.Path(self.tmp.name).rglob("*")))  # wrote nothing

    def test_missing_siblings_never_fail(self):
        with mock.patch.object(look, "_have", return_value=False):
            r = look.look(story="stories/24835.json")
        self.assertEqual(set(r["tools"]["absent"]), set(look.SIBLINGS))
        with mock.patch.object(look, "_have", return_value=True):
            r = look.look(story="stories/24835.json")
        self.assertIn("veasy_review", r["tools"]["present"])

    def test_bad_input_is_a_clear_error(self):
        for kw in ({}, {"job": "nope"}, {"story": "stories/none.json"}):
            with self.assertRaises(ValueError):
                look.look(**kw)

    def test_the_plugin_tool_returns_the_engine_json(self):
        spec = importlib.util.spec_from_file_location("veasy", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
        mod = importlib.util.module_from_spec(spec)
        sys.modules["veasy"] = mod
        spec.loader.exec_module(mod)
        out = json.loads(mod.TOOLS["veasy_look"][2]({"story": "stories/24835.json"}))
        self.assertEqual(out["kind"], "story", out)


if __name__ == "__main__":
    unittest.main()
