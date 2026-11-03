"""frame.md (HyperFrames' design spec) from a brand pack: every shipped pack gives a valid file that says exactly what
the pack says, and the checks catch the ways an edited file could break the brand."""
import pathlib
import tempfile
import unittest

from tt_shorts import brand, frame_md, probe


class FrameMd(unittest.TestCase):
    def setUp(self):
        brand.load.cache_clear()

    def test_every_pack_gives_a_valid_frame_md(self):
        for n in brand.names():
            b = brand.load(n)
            text = frame_md.render(b)
            self.assertEqual(frame_md.problems(text, b), [], n)
            fm, sections = frame_md.parse(text)
            self.assertEqual(fm["colors"], b["colors"])  # the palette verbatim, onAccent included
            self.assertEqual(fm["fonts"]["family"], "Brand")  # the family the layout probe checks
            self.assertEqual(fm["fonts"]["face"], "FiraGO")
            self.assertEqual(fm["layout"]["scene"], {"top": 248, "bottom": 1380, "side": 64})
            self.assertEqual(fm["layout"]["rail"], {"x": probe.C["RAIL_X"], "below": probe.C["RAIL_Y"]})
            self.assertEqual(sections, list(frame_md.SECTIONS))
            self.assertIn(b["label"], text)

    def test_the_packs_differ_only_where_the_packs_do(self):
        a, s = (frame_md.parse(frame_md.render(brand.load(n)))[0] for n in ("tbilisi-today", "sitech"))
        self.assertNotEqual(a["colors"]["accent"], s["colors"]["accent"])
        self.assertEqual(a["typography"], s["typography"])
        self.assertEqual(a["layout"], s["layout"])

    def test_the_accent_is_never_text(self):
        b = brand.load()
        text = frame_md.render(b)
        bad = text.replace('"textColor": "{colors.ink}"', '"textColor": "{colors.accent}"', 1)
        self.assertTrue(any("accent" in p for p in frame_md.problems(bad, b)))
        self.assertIn("text", frame_md.parse(text)[0]["accent"]["never"])

    def test_broken_files_are_caught(self):
        b = brand.load()
        text = frame_md.render(b)
        self.assertTrue(frame_md.problems(text.replace("## Locked Chrome", "## Chrome"), b))
        self.assertTrue(frame_md.problems(text.replace('"{colors.panel}"', '"{colors.paper}"', 1), b))
        self.assertTrue(frame_md.problems(text.replace('"#05080F"', '"black"', 1), b))
        self.assertTrue(frame_md.problems(text.replace('"bottom": 1380', '"bottom": 1500', 1), b))
        self.assertTrue(frame_md.problems(text + "\nA long dash — here.\n", b))
        self.assertTrue(frame_md.problems(text, brand.load("sitech")))  # another pack's palette
        self.assertEqual(frame_md.problems("no frontmatter"), ["no frontmatter between --- lines"])

    def test_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = frame_md.write("sitech", pathlib.Path(d) / "film" / "frame.md")
            self.assertEqual(frame_md.problems(p.read_text(encoding="utf-8"), brand.load("sitech")), [])


if __name__ == "__main__":
    unittest.main()
