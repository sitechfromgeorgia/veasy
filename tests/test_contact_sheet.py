"""Tests for the contact-sheet command and generator (tt_shorts/contact_sheet.py)."""
import json
import pathlib
import tempfile
import unittest

from tt_shorts import contact_sheet, engine

ROOT = pathlib.Path(__file__).resolve().parent.parent


class ContactSheetTest(unittest.TestCase):
    def test_generate_contact_sheet_html(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = pathlib.Path(tmpdir) / "sheet.html"
            res = contact_sheet.generate_contact_sheet_html(out_path=out_file)
            self.assertTrue(out_file.exists())
            self.assertEqual(res["icons"], 250)
            self.assertEqual(res["drawings"], len(list((pathlib.Path(__file__).resolve().parent.parent / "assets" / "drawings").glob("*.json"))))
            self.assertEqual(len(res["themes"]), 4)

            content = out_file.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("Veasy Visual Vocabulary", content)
            self.assertIn("airplane", content)
            self.assertIn("wine-qvevri", content)
            self.assertIn("pane-sitech-dark", content)
            self.assertIn("pane-sitech-light", content)
            self.assertIn("pane-tbilisi-today-dark", content)
            self.assertIn("pane-tbilisi-today-light", content)

    def test_engine_contact_sheet_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = pathlib.Path(tmpdir) / "sheet.html"
            code = engine.main(["contact-sheet", "--out", str(out_file)])
            self.assertEqual(code, 0)
            self.assertTrue(out_file.exists())
