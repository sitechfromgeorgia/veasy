"""Director spring physics & flowOf-matched exits/wipes unit tests."""
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import probe, props

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = str(ROOT / "stories" / "24835.json")


class DirectorMotion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_chronicle_and_type_director_motion_and_overlay(self):
        cases = [
            ("chronicle", [-1, 0], 19.6, 120),
            ("type", [1, 0], 17, 240),
        ]
        for director, expected_flow, expected_damping, expected_stiffness in cases:
            with self.subTest(director=director):
                work, p = props.build(
                    STORY,
                    "editorial",
                    "silent",
                    music="off",
                    director=director,
                    outro="overlay",
                )
                self.assertEqual(p["style"]["director"], director)
                self.assertEqual(p["style"]["flow"], expected_flow)
                motion = p["style"]["motion"]
                self.assertEqual(motion["damping"], expected_damping)
                self.assertEqual(motion["stiffness"], expected_stiffness)
                self.assertIn("enter_frames", motion)
                self.assertIn("stagger_frames", motion)
                self.assertEqual(p["outro"], "overlay")
                self.assertIsInstance(p.get("outroFrom"), int)
                self.assertGreater(p["outroFrom"], 0)

                # Layout probe report at settled frames: 0 probe problems or issues
                res = probe.check_work(work, p)
                self.assertEqual(res["problems"], [])
                self.assertEqual(res["issues"], [])


if __name__ == "__main__":
    unittest.main()
