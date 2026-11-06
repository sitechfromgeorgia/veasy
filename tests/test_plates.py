"""Plates: the tone line, the refusals, the cache, the ledger. One real bake (quarter scale, one second) is shared."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from tt_shorts import brand as packs
from tt_shorts import plates, store

TOOLS = bool(plates.node() and subprocess.run([plates.ffmpeg(), "-version"], capture_output=True).returncode == 0
             and (plates.PLATES / "node_modules").is_dir())
LINES = [(c, i) for c, i in plates.palettes()]


def ramp_frame():
    """A 1024x64 grey frame: every level 0-255 four columns wide, plus smooth gradients (where banding shows)."""
    row = bytes(min(255, x // 4) for x in range(1024))
    smooth = bytes(int(x * 255 / 1023) for x in range(1024))
    return (row * 32 + smooth * 32), 1024, 64


class Tone(unittest.TestCase):
    def test_lines_cover_both_packs_and_both_themes(self):
        who = {w for ws in plates.palettes().values() for w in ws}
        for pack in ("tbilisi-today", "sitech"):
            self.assertIn(f"{pack}/dark", who)
            self.assertIn(f"{pack}/light", who)

    def test_lut_points_lie_on_the_line(self):
        for canvas, ink in LINES:
            c, i = plates.hex_rgb(canvas), plates.hex_rgb(ink)
            self.assertEqual(plates.line_point(c, i, 0), c)
            self.assertEqual(plates.line_point(c, i, 255), i)

    @unittest.skipUnless(TOOLS, "ffmpeg needed")
    def test_mapped_frame_holds_only_colours_on_the_line(self):
        raw, w, h = ramp_frame()
        for canvas, ink in LINES:
            c, i = plates.hex_rgb(canvas), plates.hex_rgb(ink)
            vf = plates.tone_filter(c, i).split(",scale=")[0]  # up to the lookup: the colours the codec then carries
            r = subprocess.run([plates.ffmpeg(), "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray",
                                "-s", f"{w}x{h}", "-i", "-", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               input=raw, capture_output=True)
            self.assertEqual(r.returncode, 0)
            stats = plates.line_stats(r.stdout, c, i)
            self.assertLessEqual(stats["max"], 3 ** 0.5 / 2 + 1e-9, (canvas, ink, stats))
            self.assertLessEqual(stats["colours"], 256)
            px = r.stdout[:3]  # first pixel is grey 0: the canvas itself
            self.assertEqual(tuple(px), c)

    @unittest.skipUnless(TOOLS, "ffmpeg needed")
    def test_dither_stays_on_the_line_in_a_smooth_gradient(self):
        # gradfun dithers the grey before the colour is assigned: neighbouring levels only, never another channel's noise
        raw, w, h = ramp_frame()
        c, i = plates.hex_rgb("#05080F"), plates.hex_rgb("#F8FAFC")
        vf = plates.tone_filter(c, i).split(",scale=")[0]
        r = subprocess.run([plates.ffmpeg(), "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s",
                            f"{w}x{h}", "-i", "-", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           input=raw, capture_output=True)
        pts = {tuple(plates.line_point(c, i, g)) for g in range(256)}
        seen = {tuple(r.stdout[k:k + 3]) for k in range(0, len(r.stdout), 3)}
        self.assertTrue(seen <= pts, "a pixel left the 256 points of the line")


class Refusals(unittest.TestCase):
    def test_news_is_refused(self):
        self.assertIn("news", plates.refusal(program="news"))

    def test_crime_family_is_refused(self):
        self.assertIn("crime", plates.refusal(family="crime"))

    def test_deaths_and_incidents_are_refused_by_their_words(self):
        for text in ("ხანძარი თბილისში", "ორი ადამიანი დაიღუპა", "a man was killed", "Fire at a market"):
            self.assertIsNotNone(plates.refusal(text=text), text)

    def test_an_ordinary_story_is_allowed(self):
        self.assertIsNone(plates.refusal(program="explainer", family="tech", text="როგორ მუშაობს ბატარეა"))


class Ledger(unittest.TestCase):
    def test_entry_has_kind_hash_seed_licence(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"VEASY_HOME": tmp}):
            h = "0123456789abcdef"
            (store.plate_dir(h) / "plate.mp4").write_bytes(b"x")
            e = plates.ledger_entry({"kind": "example", "hash": h, "seed": 7})
            self.assertEqual((e["kind"], e["hash"], e["seed"], e["licence"]), ("plate", h, 7, "own"))
            self.assertEqual(e["sha"], hashlib.sha256(b"x").hexdigest())
            self.assertEqual(e["file"], f"cache/plates/{h}/plate.mp4")


@unittest.skipUnless(TOOLS, "node, ffmpeg and plates/node_modules needed")
class Baked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = mock.patch.dict(os.environ, {"VEASY_HOME": cls.tmp.name})
        cls.env.start()
        cls.first = plates.make("example", seconds=1, seed=7, scale=0.25)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def test_first_bake_then_every_pack_and_theme_has_a_clip(self):
        self.assertFalse(self.first["cached"])
        self.assertEqual(self.first["frames"], 30)
        for pack in ("tbilisi-today", "sitech"):
            for theme in ("dark", "light"):
                self.assertTrue((store.home() / self.first["clips"][pack][theme]).is_file())
        self.assertEqual(self.first["anchors"], ["dot"])

    def test_second_call_answers_from_the_cache_in_under_a_second(self):
        start = time.time()
        again = plates.make("example", seconds=1, seed=7, scale=0.25)
        self.assertTrue(again["cached"])
        self.assertEqual(again["hash"], self.first["hash"])
        self.assertLess(time.time() - start, 1.0)

    def test_another_seed_is_another_plate(self):
        self.assertNotEqual(plates.hash_of("example", 1, 8, 0.25), self.first["hash"])

    def test_hash_is_a_function_of_the_spec_contents_not_its_path(self):
        a, b = pathlib.Path(self.tmp.name, "a.json"), pathlib.Path(self.tmp.name, "b.json")
        a.write_text('{"k": 1}')
        b.write_text('{"k": 1}')
        self.assertEqual(plates.hash_of("example", 1, 7, 0.25, a), plates.hash_of("example", 1, 7, 0.25, b))
        self.assertNotEqual(plates.hash_of("example", 1, 7, 0.25, a), self.first["hash"])

    def test_toned_clip_is_near_its_line_and_is_deterministic(self):
        d = store.home() / "cache" / "plates" / self.first["hash"]
        c, i = plates.hex_rgb("#05080F"), plates.hex_rgb("#F8FAFC")
        clip = d / plates.clip_name("#05080F", "#F8FAFC")
        w, h, rgb = plates.decode_frame(clip, t=0.5)
        s = plates.line_stats(rgb, c, i)
        self.assertLess(s["mean"], 2.0, s)  # measured 1.0-1.2 at full scale; the codec's noise, not a palette leak
        self.assertLess(s["p999"], 8.0, s)
        out = d / "again.mp4"
        plates.tone_clip(d / "plate.mp4", out, c, i)
        self.assertEqual(out.read_bytes(), clip.read_bytes())

    def test_library_lists_the_plate(self):
        self.assertIn(self.first["hash"], [m["hash"] for m in plates.library()])

    def test_a_missing_kind_is_an_error(self):
        with self.assertRaises(plates.PlateError):
            plates.make("nope", seconds=1)


if __name__ == "__main__":
    unittest.main()
