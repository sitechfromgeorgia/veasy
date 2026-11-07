"""The ink plate (plates/ink): a drawing's strokes keep its order, labels and the accent stay out, and the page refuses
what a plate may not be. Baking is left to the plate's own README: a browser has no place in a unit test."""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plates" / "ink"))

import bake  # noqa: E402

from tt_shorts import art  # noqa: E402

SVG = """<g class="s" style="--d:0.8s"><path d="M10 10 L100 10" stroke="INK" stroke-width="6"/></g>
<g class="r" style="--d:0.2s"><rect x="20" y="20" width="80" height="40" rx="8" stroke="MUTED" stroke-width="5" fill="CANVAS"/>
<circle cx="50" cy="40" r="10" stroke="INK" fill="none"/></g>
<g class="s" style="--d:0.4s" transform="translate(100 0)"><line x1="0" y1="0" x2="0" y2="50" stroke="LINE" stroke-width="4"/>
<path d="M0 0 Q 50 50 100 0 T 200 0" stroke="INK"/><path d="M0 0 A 30 30 0 0 1 60 0" stroke="INK"/></g>
<g class="p" style="--d:1.0s"><circle cx="300" cy="200" r="14" fill="ACCENT" stroke="ACCENT"/>
<text x="100" y="100" font-size="30" fill="INK">აბგ</text></g>"""


class Strokes(unittest.TestCase):
    def setUp(self):
        self.d = bake.bake(SVG)

    def test_order_is_the_drawings_delay(self):
        delays = [s["d"] for s in self.d["strokes"]]
        self.assertEqual(delays, sorted(delays))
        self.assertEqual(delays[0], 0.2)
        self.assertEqual(delays[-1], 0.8)

    def test_paint_order_stays_for_the_shapes(self):
        rect, circle = self.d["strokes"][:2]
        self.assertLess(rect["paint"], circle["paint"])
        self.assertEqual((rect["fill"], rect["closed"], circle["fill"]), ("CANVAS", True, "none"))
        self.assertEqual(rect["box"], [20.0, 20.0, 100.0, 60.0])

    def test_no_text_and_no_accent_are_painted(self):
        self.assertEqual(self.d["dots"], [[300.0, 200.0]])
        self.assertFalse([s for s in self.d["strokes"] if "ACCENT" in (s["line"], s["fill"])])

    def test_transform_reaches_the_points(self):
        line = next(s for s in self.d["strokes"] if s["line"] == "LINE")
        self.assertEqual(line["pts"][:2], [100.0, 0.0])

    def test_curves_are_flattened_to_their_end(self):
        arc = self.d["strokes"][-2]["pts"]  # the A path, at x + 100
        self.assertAlmostEqual(arc[-2], 160.0, places=0)
        self.assertAlmostEqual(arc[-1], 0.0, places=0)
        self.assertLess(min(arc[1::2]), -25)  # sweep 1 from left to right bows up
        wave = self.d["strokes"][-3]["pts"]
        self.assertAlmostEqual(wave[-2], 300.0, places=0)  # T mirrors the Q's control point

    def test_ring_and_rect_shapes(self):
        self.assertEqual(len(bake.shape("rect", {"x": "0", "y": "0", "width": "9", "height": "9"})[0][0]), 4)
        rounded = bake.shape("rect", {"x": "0", "y": "0", "width": "90", "height": "90", "rx": "10"})[0][0]
        self.assertGreater(len(rounded), 20)
        self.assertEqual(bake.subpaths("M0 0 L10 0 M5 5 L9 9 Z")[1][1], True)


class Library(unittest.TestCase):
    def test_every_seed_is_baked_and_fresh(self):
        library = bake.library()
        self.assertEqual(len(library), len(list((ROOT / "assets" / "drawings").glob("*.json"))))
        stored = json.loads(bake.OUT.read_text(encoding="utf-8"))
        self.assertEqual(stored, json.loads(json.dumps(library, ensure_ascii=False)))

    def test_all_inside_the_drawing(self):
        w, h = art.VIEW
        for name, d in json.loads(bake.OUT.read_text(encoding="utf-8")).items():
            self.assertTrue(d["strokes"], name)
            for s in d["strokes"]:
                self.assertTrue(all(-60 <= v <= w + 60 for v in s["pts"][::2]), name)
                self.assertTrue(all(-60 <= v <= h + 60 for v in s["pts"][1::2]), name)


class Page(unittest.TestCase):
    """The page's own promises, read from its source: there is no browser here."""

    def setUp(self):
        self.files = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "plates" / "ink").glob("*") if p.suffix in (".mjs", ".html")}

    def test_no_clock_and_no_unseeded_random(self):
        for name in ("core.mjs", "materials.mjs", "index.html"):
            self.assertNotRegex(self.files[name], r"Math\.random|Date\.now|performance\.now|new Date", name)

    def test_six_materials(self):
        names = re.findall(r"^  (\w+)\(m\) \{$", self.files["materials.mjs"], re.M)
        self.assertEqual(sorted(names), sorted(["woodcut", "ink_wash", "blueprint", "halftone", "chalk", "pencil_hatch"]))

    def test_refusals(self):
        page = self.files["index.html"]
        self.assertIn('spec.program === "news"', page)
        for word in ("crime", "incidents", "deaths"):
            self.assertIn(f'"{word}"', page)
        self.assertIn("unknown spec key", page)

    def test_no_client_word_and_no_colour(self):
        for name, text in self.files.items():
            self.assertNotRegex(text, r"(?i)tbilisi|sitech", name)
        self.assertNotRegex(self.files["materials.mjs"], r"#[0-9a-fA-F]{6}")


if __name__ == "__main__":
    unittest.main()
