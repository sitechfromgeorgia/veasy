"""Tests for brand-pack portability in tt_shorts/reel_cover.py."""
import json
import pathlib
import tempfile
import unittest

from PIL import Image

from tt_shorts import brand, reel_cover


ROOT = pathlib.Path(__file__).resolve().parent.parent


class ReelCoverBrandPortability(unittest.TestCase):
    def test_builds_brand_styled_cover_for_sitech_and_tbilisi_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_sitech = pathlib.Path(tmp) / "sitech.jpg"
            reel_cover.build(
                "veasy-blog",
                "ხელოვნური ინტელექტის ვიდეო ძრავა",
                "ai",
                "2026-11-16",
                str(out_sitech),
                brand="sitech",
            )
            self.assertTrue(out_sitech.is_file())
            with Image.open(out_sitech) as im:
                self.assertEqual(im.size, (1080, 1920))
                # Bottom-right corner (far from top-right radial glow) matches SiTech coal (#171817 = 23, 24, 23)
                r, g, b = im.getpixel((1070, 1910))
                self.assertLess(max(abs(r - 23), abs(g - 24), abs(b - 23)), 8)

            out_tt = pathlib.Path(tmp) / "tt.jpg"
            story = json.loads((ROOT / "stories" / "sitech-cybercartel.json").read_text(encoding="utf-8"))
            reel_cover.from_story("cybercartel", story, str(out_tt))
            self.assertTrue(out_tt.is_file())
            with Image.open(out_tt) as im:
                self.assertEqual(im.size, (1080, 1920))

    def test_pack_without_social_refuses(self):
        bare = json.loads((ROOT / "brands" / "sitech" / "brand.json").read_text(encoding="utf-8"))
        bare.pop("social", None)
        bare["name"] = "bare"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(brand.BrandError, "this brand has no social config"):
                reel_cover.build("x", "სათაური", "ai", "2026-11-16", str(pathlib.Path(tmp) / "c.jpg"), brand=bare)


if __name__ == "__main__":
    unittest.main()
