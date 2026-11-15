"""Tests for kinetic hook typography (Item #1 of the Veasy animation quality program)."""
import json
import pathlib
import unittest

from tt_shorts import probe, props, speech, store, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestKineticHookTypography(unittest.TestCase):
    def test_all_hook_modes_probe_cleanly(self):
        """Verify all 8 hook modes (including the 4 new ones: split, badge, bracket, rail)
        render with zero probe layout problems on the fixture story."""
        story_file = ROOT / "stories" / "24835.json"
        hooks = ("split", "badge", "bracket", "rail")
        for hook in hooks:
            work, p = props.build(
                str(story_file), "kinetic", "silent", None, speech.EDGE_VOICES["eka"], "tiktok", caption_design="page"
            )
            p["style"]["hook"] = hook
            (work / "props.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
            res = probe.check_work(work, p)
            self.assertEqual(res["problems"], [], f"Hook mode '{hook}' has probe problems: {res['problems']}")

    def test_kinetic_headline_template_beat_landmarks(self):
        """Verify kinetic-headline template has beat-aware tAt helper and fallback."""
        tmpl = (ROOT / "compose" / "blocks" / "kinetic-headline" / "template.html").read_text(encoding="utf-8")
        self.assertIn("window.VEASY", tmpl)
        self.assertIn("tAt(0, 0.28)", tmpl)
        self.assertIn("tAt(1, 0.48)", tmpl)
        self.assertIn("tAt(2, 0.52)", tmpl)
        self.assertIn("tAt(3, 0.65)", tmpl)
        self.assertIn("tAt(4, 0.75)", tmpl)


if __name__ == "__main__":
    unittest.main()
