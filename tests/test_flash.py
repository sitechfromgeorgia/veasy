"""The flash check (tt_shorts/flash.py, ITU-R BT.1702-3): the limits on arrays, a slow change staying one change, red
at any luminance, and qa_file holding a real file over the limit."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import numpy as np

from tt_shorts import engine, flash, formats

HAVE_FFMPEG = shutil.which("ffmpeg") is not None
CELLS = 100
FPS = 30


def gray(level):
    """A sRGB byte for a luminance in cd/m2 on the reference display (gray: R = G = B)."""
    return int(np.abs(flash._LINEAR * flash.PEAK - level).argmin())


def strobe(hz, share=1.0, low=0.0, high=200.0, seconds=2, color=None):
    """frames x cells x 3 bytes: `share` of the cells swing low <-> high `hz` times a second, the rest stay at low."""
    n = seconds * FPS
    out = np.full((n, CELLS, 3), gray(low), dtype=np.uint8)
    period = FPS / hz
    moving = int(CELLS * share)
    for i in range(n):
        if int(i / (period / 2)) % 2:
            out[i, :moving] = color if color is not None else gray(high)
    return out


class Limits(unittest.TestCase):
    def test_a_strobe_over_a_quarter_of_the_screen_fails(self):
        r = flash.judge(strobe(5))
        self.assertEqual(r["area"], 1.0)
        self.assertEqual(len(flash.problems(r)), 1)
        self.assertIn("more than 3 times", flash.problems(r)[0])

    def test_three_flashes_a_second_pass(self):
        r = flash.judge(strobe(3))
        self.assertEqual(r["area"], 0.0)
        self.assertEqual(flash.problems(r), [])

    def test_the_area_limit_is_a_quarter(self):
        self.assertEqual(flash.problems(flash.judge(strobe(5, share=0.25))), [])
        self.assertTrue(flash.problems(flash.judge(strobe(5, share=0.26))))

    def test_a_swing_under_the_step_is_no_change(self):
        r = flash.judge(strobe(5, low=100, high=115))
        self.assertEqual(r["area"], 0.0)

    def test_a_swing_with_its_darker_side_too_bright_is_no_change(self):
        r = flash.judge(strobe(5, low=170, high=200))
        self.assertEqual(r["area"], 0.0)

    def test_a_slow_change_is_one_change(self):
        ramp = np.linspace(0, 200, 30, dtype=np.float32)
        wave = np.concatenate([ramp, ramp[::-1]])[:, None]
        self.assertEqual(int(flash.changes(wave).sum()), 2)

    def test_a_dark_red_strobe_counts_at_any_luminance(self):
        red = (150, 0, 0)  # under STEP in luminance, far over it on the red measure
        lift = float(flash.luminance(np.array([[red]], dtype=np.uint8))[0, 0])
        self.assertLess(lift, flash.STEP)
        r = flash.judge(strobe(5, color=red))
        self.assertEqual(r["signal"], "red")
        self.assertIn("saturated red", flash.problems(r)[0])

    def test_one_frame_is_not_a_measurement(self):
        self.assertEqual(flash.judge(strobe(1)[:1])["checked"], False)
        self.assertIn("not checked", flash.problems({"checked": False})[0])


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class Files(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="veasy-flash-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def video(self, name, every):
        """2 s of 1080x1920 black with a white screen `every` frames on, `every` frames off."""
        out = self.dir / name
        box = f"drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(n\\,{every * 2})\\,{every})'"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30:d=2",
                        "-vf", box, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)],
                       check=True)
        return out

    def test_qa_holds_a_file_over_the_limit(self):
        q = engine.qa_file(self.video("strobe.mp4", 3), {**formats.get("news"), "min_seconds": 1})
        self.assertGreater(q["flash"]["area"], flash.AREA)
        self.assertTrue(any(p.startswith("flash:") for p in q["problems"]), q["problems"])

    def test_qa_passes_a_file_under_it(self):
        q = engine.qa_file(self.video("calm.mp4", 15), {**formats.get("news"), "min_seconds": 1})
        self.assertEqual(q["flash"]["area"], 0.0)
        self.assertFalse([p for p in q["problems"] if p.startswith("flash:")])

    def test_a_file_that_cant_be_read_is_a_problem(self):
        bad = self.dir / "broken.mp4"
        bad.write_bytes(b"not a video")
        self.assertIn("not checked", flash.problems(flash.measure(bad))[0])


if __name__ == "__main__":
    unittest.main()
