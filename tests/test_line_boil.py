"""Unit and determinism tests for 15 fps on-twos line boil on vector drawings (Item #5)."""
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import formats, probe, props, speech

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestLineBoilOnTwos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)

    def test_program_propagated_for_explainer_and_none_for_news(self):
        voice = speech.EDGE_VOICES["eka"]
        w1, p_exp = props.build(str(ROOT / "stories" / "vignettes-inflation.json"), "editorial", "silent", None, voice)
        self.assertEqual(p_exp.get("program"), "explainer")
        w2, p_news = props.build(str(ROOT / "stories" / "24835.json"), "editorial", "silent", None, voice)
        self.assertIsNone(p_news.get("program"))

    def test_explainer_drawings_and_thread_probe_cleanly(self):
        fmt = formats.get("explainer")
        for sid in ("vignettes-inflation", "veasy-thread"):
            with self.subTest(story=sid):
                res = probe.story(str(ROOT / "stories" / f"{sid}.json"), fmt, look="editorial")
                self.assertEqual(res["problems"], [], f"{sid} problems: {res['problems']}")
                self.assertEqual(res["looks"]["editorial"]["problems"], [])
                self.assertEqual(res["looks"]["editorial"]["issues"], [])

    def test_build_determinism(self):
        story = str(ROOT / "stories" / "vignettes-inflation.json")
        voice = speech.EDGE_VOICES["eka"]
        w1, p1 = props.build(story, "editorial", "silent", None, voice)
        w2, p2 = props.build(story, "editorial", "silent", None, voice)
        self.assertEqual(p1["scenes"], p2["scenes"])
        self.assertEqual(probe.check_work(w1, p1)["texts"], probe.check_work(w2, p2)["texts"])

    def test_ink_and_scene_boil_contracts(self):
        ink = (ROOT / "remotion" / "src" / "ink.ts").read_text(encoding="utf-8")
        self.assertNotIn("Math.random", ink)
        self.assertNotIn("Date.now", ink)
        for sym in ("export const boilFrame", "export const boilTickFor", "export const boilPoint", "export const boilPathD"):
            self.assertIn(sym, ink)
        self.assertIn("Math.floor(Math.max(0, frame) / 2)", ink)
        self.assertIn('p.program !== "news"', ink)

        for rel in ("remotion/src/scenes/more.tsx", "remotion/src/vignette.tsx", "remotion/src/thread.tsx"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("boilTick", src, rel)


if __name__ == "__main__":
    unittest.main()
