"""Item #7 tests: cut-window directional carry-over & non-news micro-camera breath."""
import pathlib
import tempfile
import unittest

from tt_shorts import compose, formats, probe, props


ROOT = pathlib.Path(__file__).resolve().parent.parent


class CutMicroCameraContract(unittest.TestCase):
    def test_program_propagated_to_remotion_props(self):
        _, p_exp = props.build(
            ROOT / "stories" / "vignettes-inflation.json",
            variant="editorial",
            engine="silent",
            music="off",
        )
        self.assertEqual(p_exp["program"], "explainer")

        _, p_news = props.build(
            ROOT / "stories" / "24835.json",
            variant="editorial",
            engine="silent",
            music="off",
        )
        self.assertIsNone(p_news["program"])

    def test_starter_scene_cut_continuity_and_news_gate(self):
        s = {"type": "stat", "at": "x", "num": "3.8%", "sub": "ინფლაცია"}
        s0 = compose.starter_scene(0, s, program="explainer")
        self.assertNotIn("scale: 1.03", s0)

        s1_news = compose.starter_scene(1, s, program="news")
        self.assertIn('tl.fromTo("#root .stack", { y: 18 }, { y: 0, duration: 0.34', s1_news)
        self.assertNotIn("scale: 1.03", s1_news)

        s1_exp = compose.starter_scene(1, s, program="explainer")
        self.assertIn('tl.fromTo("#root .stack", { y: 18 }, { y: 0, duration: 0.34', s1_exp)
        self.assertIn("scale: 1.03, duration: 0.17", s1_exp)
        self.assertIn("scale: 1, duration: 0.17", s1_exp)

        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp)
            compose.scaffold(ROOT / "stories" / "vignettes-inflation.json", project=p, engine="silent")
            self.assertIn("scale: 1.03", (p / "compositions" / "s1.html").read_text(encoding="utf-8"))
            for f in compose.LOCKED:
                self.assertNotIn("scale: 1.03", (p / f).read_text(encoding="utf-8"))

    def test_settled_probes_stay_clean_for_explainer_and_news(self):
        res_exp = probe.story(
            ROOT / "stories" / "vignettes-inflation.json",
            formats.get("explainer"),
            look="editorial",
        )
        self.assertEqual(res_exp["looks"]["editorial"]["problems"], [])
        self.assertEqual(res_exp["looks"]["editorial"]["issues"], [])

        res_news = probe.story(
            ROOT / "stories" / "24835.json",
            formats.get("news"),
            look="editorial",
        )
        self.assertEqual(res_news["looks"]["editorial"]["problems"], [])
        self.assertEqual(res_news["looks"]["editorial"]["issues"], [])


if __name__ == "__main__":
    unittest.main()
