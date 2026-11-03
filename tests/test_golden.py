"""Golden stills: the hash and its distance, the comparison, and goldens that cover the fixtures. The selftest
itself renders (about half a minute): run `python -m tt_shorts.engine selftest` before merging a visual change."""
import json
import pathlib
import tempfile
import unittest

from PIL import Image, ImageDraw

from tt_shorts import brand, golden

ROOT = pathlib.Path(__file__).resolve().parent.parent


def frame(path, text_at=None, noise=0):
    """A dark 1080x1920 frame, a light block where text would be, optional ±noise grey levels everywhere."""
    im = Image.new("L", (1080, 1920), 12)
    if noise:
        im.putdata([12 + (noise if (i * 7919) % 3 == 0 else 0) for i in range(1080 * 1920)])
    if text_at:
        ImageDraw.Draw(im).rectangle(text_at, fill=230)
    im.save(path)
    return path


class Hash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_picture_same_hash_and_noise_does_not_count(self):
        a = golden.hashes(frame(self.d / "a.png", (100, 600, 700, 700)))
        b = golden.hashes(frame(self.d / "b.png", (100, 600, 700, 700), noise=1))
        self.assertEqual(len(a["hash"]), golden.SIZE ** 2 // 4)
        self.assertEqual(len(a["band"]), golden.BAND_SIZE ** 2 // 4)
        self.assertEqual(a, golden.hashes(frame(self.d / "a2.png", (100, 600, 700, 700))))
        # a grey level of noise everywhere (another machine's anti-aliasing) stays under the thresholds
        self.assertLessEqual(golden.distance(a["hash"], b["hash"]), golden.THRESHOLD["frame"])
        self.assertLessEqual(golden.distance(a["band"], b["band"]), golden.THRESHOLD["band"])

    def test_moved_or_missing_text_counts(self):
        a = golden.hashes(frame(self.d / "a.png", (100, 600, 700, 700)))
        moved = golden.hashes(frame(self.d / "b.png", (100, 760, 700, 860)))
        gone = golden.hashes(frame(self.d / "c.png"))
        for other in (moved, gone):
            self.assertGreater(golden.distance(a["band"], other["band"]), golden.THRESHOLD["band"])

    def test_distance(self):
        self.assertEqual(golden.distance("ff", "ff"), 0)
        self.assertEqual(golden.distance("f0", "0f"), 8)
        self.assertEqual(golden.distance("ff", "ffff"), 8)  # hashes of another size never match

    def test_compare(self):
        old = [{"scene": 0, "type": "hook", "hash": "00", "band": "00"},
               {"scene": 1, "type": "stat", "hash": "00", "band": "00"}]
        same = [dict(s) for s in old]
        self.assertEqual(golden.compare(old, same), [])
        band = [old[0], {**old[1], "band": "ff"}]  # 8 bits in the band only
        self.assertEqual([(c["scene"], c["distance"]) for c in golden.compare(old, band)],
                         [(1, {"frame": 0, "band": 8})])
        other = [old[0], {**old[1], "type": "where"}]  # another scene list: every scene changed
        self.assertEqual([c["distance"] for c in golden.compare(old, other)], [None, None])


class Goldens(unittest.TestCase):
    def test_every_fixture_has_a_golden_in_every_look(self):
        for name in golden.STORIES:
            story = json.loads((ROOT / "stories" / f"{name}.json").read_text(encoding="utf-8"))
            for look in brand.LOOKS:
                g = json.loads(golden.golden_path(name, look).read_text(encoding="utf-8"))
                self.assertEqual((g["story"], g["look"], g["style"]), (name, look, golden.style_for(look)))
                self.assertEqual([s["type"] for s in g["scenes"]], [s["type"] for s in story["scenes"]],
                                 f"{name}.{look}: the fixture changed; run selftest --update")
                for s in g["scenes"]:
                    self.assertEqual((len(s["hash"]), len(s["band"])), (golden.SIZE ** 2 // 4, golden.BAND_SIZE ** 2 // 4))

    def test_themed_goldens_sit_beside_the_default_ones(self):  # brand.json themes: one pack's light theme
        self.assertIn(("sitech", "light"), golden.THEMED)
        self.assertEqual(golden.golden_path("veasy-demo", "cards").name, "veasy-demo.cards.json")
        self.assertEqual(golden.golden_path("veasy-demo", "cards", ("sitech", "light")).name,
                         "veasy-demo.sitech-light.cards.json")
        self.assertEqual(golden.themes_arg(None), [None, *golden.THEMED])
        self.assertEqual(golden.themes_arg("default,sitech:light"), [None, ("sitech", "light")])
        for bad in ("light", "sitech:neon", "nobody:light"):
            with self.assertRaises(ValueError, msg=bad):
                golden.themes_arg(bad)
        for pk, th in golden.THEMED:  # made per machine with --update; when present, they match the fixtures
            for name in golden.STORIES:
                for look in brand.LOOKS:
                    gp = golden.golden_path(name, look, (pk, th))
                    if gp.exists():
                        g = json.loads(gp.read_text(encoding="utf-8"))
                        self.assertEqual((g["story"], g["brand"], g["theme"], g["look"]), (name, pk, th, look))


if __name__ == "__main__":
    unittest.main()
