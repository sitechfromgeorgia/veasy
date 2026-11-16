"""Item #6 tests: velocity-gated directional motion blur on fast cuts and starter HyperFrames scenes."""
import pathlib
import subprocess
import tempfile
import unittest

from tt_shorts import compose, formats, probe


ROOT = pathlib.Path(__file__).resolve().parent.parent


class CutMotionBlurContract(unittest.TestCase):
    def test_directional_blur_math_and_hard_bypass(self):
        script = r"""
        const fs = require("fs");
        const ts = require("./remotion/node_modules/typescript");
        const src = fs.readFileSync("./remotion/src/motion_blur.ts", "utf8");
        const js = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
        const m = { exports: {} };
        new Function("exports", "module", js)(m.exports, m);
        const { directionalBlur } = m.exports;
        const res = {
          rest: directionalBlur(0, 0, 0),
          slow: directionalBlur(0.8, 0.5, 0.001),
          fastX: directionalBlur(180, 0, 0),
          fastScale: directionalBlur(0, 0, 0.03),
          capped: directionalBlur(999, 0, 0),
        };
        console.log(JSON.stringify(res));
        """
        out = subprocess.check_output(["node", "-e", script], cwd=str(ROOT), text=True)
        import json
        data = json.loads(out.strip())
        self.assertIsNone(data["rest"])
        self.assertIsNone(data["slow"])
        self.assertEqual(data["fastX"], {"sx": 26, "sy": 0})
        self.assertEqual(data["fastScale"], {"sx": 6.6, "sy": 6.6})
        self.assertEqual(data["capped"], {"sx": 26, "sy": 0})

    def test_starter_scene_enables_motion_blur_without_touching_locked_chrome(self):
        html = compose.starter_scene(1, {"type": "stat", "at": "x", "num": "6 400", "sub": "აბონენტი"})
        self.assertIn('data-motion-blur="on"', html)
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp)
            compose.scaffold(ROOT / "stories" / "vignettes-inflation.json", project=p, engine="silent")
            self.assertTrue((p / "compositions" / "s0.html").exists())
            self.assertIn('data-motion-blur="on"', (p / "compositions" / "s0.html").read_text(encoding="utf-8"))
            for f in compose.LOCKED:
                self.assertTrue((p / f).exists())
                self.assertNotIn('data-motion-blur="on"', (p / f).read_text(encoding="utf-8"))

    def test_fast_push_and_one_take_probe_cleanly(self):
        fmt_push = formats.get("news", transition="push")
        res_push = probe.story(
            ROOT / "stories" / "24835.json",
            fmt_push,
            look="kinetic",
        )
        self.assertEqual(res_push["looks"]["kinetic"]["problems"], [])
        self.assertEqual(res_push["looks"]["kinetic"]["issues"], [])

        fmt_ot = formats.get("explainer", transition="one-take")
        res_ot = probe.story(
            ROOT / "stories" / "vignettes-inflation.json",
            fmt_ot,
            look="editorial",
        )
        self.assertEqual(res_ot["looks"]["editorial"]["problems"], [])
        self.assertEqual(res_ot["looks"]["editorial"]["issues"], [])


if __name__ == "__main__":
    unittest.main()
