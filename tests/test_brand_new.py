"""Tests for automated brand book ingestion (engine brand new)."""
import json
import pathlib
import tempfile
import unittest

from tt_shorts import brand, brand_new

ROOT = pathlib.Path(__file__).resolve().parent.parent


class BrandNewTest(unittest.TestCase):
    def test_create_brand_from_markdown_spec(self):
        spec_text = """
# Apex Tech Brand System
--accent: #10B981;
--canvas: #0A0E17;
--panel: #131A29;
--ink: #F9FAFB;
--muted: #94A3B8;
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_brands = pathlib.Path(tmpdir)
            spec_file = tmp_brands / "design.md"
            spec_file.write_text(spec_text, encoding="utf-8")

            res = brand_new.create_brand("apex-tech", str(spec_file), output_dir=tmp_brands, render_sheets=False)
            self.assertEqual(res["brand"], "apex-tech")
            self.assertEqual(res["validation"], "valid")
            self.assertEqual(res["accent"], "#10B981")
            self.assertIn("dark", res["themes"])
            self.assertIn("light", res["themes"])

            brand_json_path = tmp_brands / "apex-tech" / "brand.json"
            self.assertTrue(brand_json_path.is_file())
            data = json.loads(brand_json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["extends"], "_ka")
            self.assertEqual(data["themes"]["dark"]["colors"]["accent"], "#10B981")

    def test_create_brand_contrast_self_heals(self):
        # A spec with a very low contrast ink that would normally fail WCAG
        bad_spec = """
--accent: #E11D48;
--canvas: #111827;
--ink: #1F2937;  /* low contrast on dark canvas! */
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_brands = pathlib.Path(tmpdir)
            spec_file = tmp_brands / "bad_contrast.md"
            spec_file.write_text(bad_spec, encoding="utf-8")

            res = brand_new.create_brand("repaired-brand", str(spec_file), output_dir=tmp_brands, render_sheets=False)
            self.assertEqual(res["validation"], "valid")
            data = json.loads((tmp_brands / "repaired-brand" / "brand.json").read_text(encoding="utf-8"))
            # Ink was self-healed to high-contrast white
            dark_c = data["themes"]["dark"]["colors"]
            self.assertGreaterEqual(brand.contrast(dark_c["ink"], dark_c["canvas"]), 7.0)


if __name__ == "__main__":
    unittest.main()
