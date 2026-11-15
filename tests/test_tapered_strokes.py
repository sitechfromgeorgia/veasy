"""Unit and smoke tests for tapered brush-pen strokes via perfect-freehand (Item #4)."""
import json
import pathlib
import shutil
import unittest

from tt_shorts import formats, probe, props, speech

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestTaperedStrokes(unittest.TestCase):
    def test_vignettes_gas_probes_cleanly_editorial_and_kinetic(self):
        """stories/vignettes-gas.json probes cleanly with 0 problems in editorial and kinetic looks."""
        story_file = str(ROOT / "stories" / "vignettes-gas.json")
        fmt = formats.get("news")

        res_ed = probe.story(story_file, fmt, look="editorial")
        self.assertEqual(res_ed["problems"], [], f"editorial probe problems: {res_ed['problems']}")
        self.assertIn("editorial", res_ed["looks"])
        self.assertEqual(res_ed["looks"]["editorial"]["problems"], [])

        res_kin = probe.story(story_file, fmt, look="kinetic")
        self.assertEqual(res_kin["problems"], [], f"kinetic probe problems: {res_kin['problems']}")
        self.assertIn("kinetic", res_kin["looks"])
        self.assertEqual(res_kin["looks"]["kinetic"]["problems"], [])

    def test_determinism_props_build_and_check_work(self):
        """Two consecutive props.build / probe.check_work checks pass cleanly and deterministically."""
        story_file = str(ROOT / "stories" / "vignettes-gas.json")
        voice = speech.EDGE_VOICES["eka"]

        work1, p1 = props.build(story_file, "editorial", "silent", None, voice, "tiktok")
        try:
            chk1 = probe.check_work(work1, p1)
            probe.relieve_seats(p1, chk1)
            (work1 / "props.json").write_text(json.dumps(p1, ensure_ascii=False), encoding="utf-8")
            res1 = probe.check_work(work1, p1)
            self.assertEqual(res1["problems"], [], f"run 1 problems: {res1['problems']}")
        finally:
            shutil.rmtree(work1, ignore_errors=True)

        work2, p2 = props.build(story_file, "editorial", "silent", None, voice, "tiktok")
        try:
            chk2 = probe.check_work(work2, p2)
            probe.relieve_seats(p2, chk2)
            (work2 / "props.json").write_text(json.dumps(p2, ensure_ascii=False), encoding="utf-8")
            res2 = probe.check_work(work2, p2)
            self.assertEqual(res2["problems"], [], f"run 2 problems: {res2['problems']}")
        finally:
            shutil.rmtree(work2, ignore_errors=True)

        self.assertEqual(res1["problems"], res2["problems"])
        self.assertEqual(res1["frames"], res2["frames"])
        self.assertEqual(res1["texts"], res2["texts"])
        self.assertEqual(p1["scenes"], p2["scenes"])

    def test_ink_source_code_determinism_and_purity(self):
        """remotion/src/ink.ts must not use Math.random or Date.now."""
        ink_path = ROOT / "remotion" / "src" / "ink.ts"
        self.assertTrue(ink_path.exists(), "remotion/src/ink.ts must exist")
        code = ink_path.read_text(encoding="utf-8")

        self.assertNotIn("Math.random", code, "ink.ts must not use Math.random")
        self.assertNotIn("Date.now", code, "ink.ts must not use Date.now")
        self.assertIn("export const svgPathFromStroke", code)
        self.assertIn("export const isCurvedStroke", code)
        self.assertIn("export const taperedOutline", code)


if __name__ == "__main__":
    unittest.main()
