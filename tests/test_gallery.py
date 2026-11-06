"""Tests for `engine gallery`: static HTML visual catalogue."""
import pathlib
import tempfile
import unittest

from tt_shorts import catalog, gallery


class Gallery(unittest.TestCase):
    def test_build_gallery_creates_html_file(self):
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "test_gallery.html"
            res = gallery.build_gallery(target)
            self.assertTrue(target.is_file())
            self.assertEqual(res["styles"], 18)
            self.assertEqual(res["looks"], 3)
            self.assertEqual(res["scenes"], len(catalog.types()))
            self.assertEqual(res["directors"], 8)

            content = target.read_text(encoding="utf-8")
            self.assertIn("Veasy Visual Catalogue", content)
            self.assertIn("swiss-motion", content)
            self.assertIn("editorial", content)
            self.assertIn("hook", content)
            self.assertIn("brief", content)


if __name__ == "__main__":
    unittest.main()
