"""Tests for pre-flight visual critique and dry-run cost estimation."""
import json
import pathlib
import unittest

from tt_shorts import critique, dry_run

ROOT = pathlib.Path(__file__).resolve().parent.parent


class CritiqueTest(unittest.TestCase):
    def test_critique_on_fixture_story(self):
        story = ROOT / "stories" / "24835.json"
        res = critique.critique_story(story)
        self.assertIn(res["grade"], ("PASS", "NEEDS_ATTENTION"))
        self.assertGreaterEqual(res["score"], 80)
        items = {c["item"] for c in res["checklist"]}
        self.assertIn("safe_zone", items)
        self.assertIn("reading_pacing", items)
        self.assertIn("brand_compliance", items)
        self.assertIn("hook_impact", items)
        self.assertTrue(res.get("sheet"))

    def test_critique_missing_file(self):
        res = critique.critique_story("missing_nonexistent_story.json")
        self.assertEqual(res["grade"], "FAIL")
        self.assertEqual(res["score"], 0)
        self.assertTrue(res["problems"])


class DryRunTest(unittest.TestCase):
    def test_dry_run_on_fixture_story(self):
        story = ROOT / "stories" / "24835.json"
        res = dry_run.dry_run(story)
        self.assertEqual(res["story"], str(story))
        self.assertEqual(res["brand"], "tbilisi-today")
        self.assertGreater(res["duration_seconds"], 20.0)
        self.assertGreater(res["narration"]["words"], 20)
        self.assertGreater(res["narration"]["characters"], 100)
        self.assertIn("estimated_tts_usd", res["costs"])
        self.assertTrue(res["costs"]["paid_allowed"])
        self.assertGreater(res["estimated_render_seconds"], 10.0)

    def test_dry_run_missing_file(self):
        res = dry_run.dry_run("missing_nonexistent_story.json")
        self.assertTrue(res["problems"])


if __name__ == "__main__":
    unittest.main()
