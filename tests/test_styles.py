"""Tests for tt_shorts.styles: schema validation, brand law enforcement, and story resolution."""
import pathlib
import tempfile
import unittest

from tt_shorts import brand, styles

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestStyles(unittest.TestCase):
    def setUp(self):
        styles.get.cache_clear()

    def tearDown(self):
        styles.get.cache_clear()

    def sample_data(self, **overrides):
        data = {
            "slug": "swiss-motion",
            "name_en": "Swiss Motion",
            "name_ka": "შვეიცარიული მოძრაობა",
            "category": "typographic",
            "engine": "both",
            "palette": "pack",
            "fonts": "pack",
            "programs": ["news", "explainer", "law", "digest"],
            "never_families": [],
            "picks": {
                "directors": ["type", "data", "brief"],
                "looks": ["editorial", "kinetic"],
                "motifs": ["grid", "plain"],
                "transitions": ["line", "wipe"],
                "music": ["politics-1"],
                "sfx": ["click", "tick"],
            },
            "uses": "International Typographic Style on a modular grid.",
        }
        data.update(overrides)
        return data

    def test_valid_style_data_passes(self):
        data = self.sample_data()
        self.assertTrue(styles.validate_style_data(data))

    def test_missing_required_keys_raises(self):
        data = self.sample_data()
        del data["name_ka"]
        with self.assertRaises(styles.StyleError) as cm:
            styles.validate_style_data(data)
        self.assertIn("missing required keys", str(cm.exception))

    def test_invalid_slug_raises(self):
        for bad_slug in ("SwissMotion", "swiss_motion", "123", "-bad", "bad-"):
            with self.assertRaises(styles.StyleError):
                styles.validate_style_data(self.sample_data(slug=bad_slug))

    def test_invalid_engine_raises(self):
        with self.assertRaises(styles.StyleError):
            styles.validate_style_data(self.sample_data(engine="unsupported"))

    def test_invalid_palette_raises(self):
        with self.assertRaises(styles.StyleError):
            styles.validate_style_data(self.sample_data(palette="rainbow"))

    def test_invalid_fonts_raises(self):
        with self.assertRaises(styles.StyleError):
            styles.validate_style_data(self.sample_data(fonts="custom"))

    def test_empty_programs_raises(self):
        with self.assertRaises(styles.StyleError):
            styles.validate_style_data(self.sample_data(programs=[]))

    def test_unknown_family_in_never_families_raises(self):
        with self.assertRaises(styles.StyleError):
            styles.validate_style_data(self.sample_data(never_families=["space_travel"]))

    def test_unknown_keys_in_picks_raises(self):
        bad_picks = {"unknown_pick": ["foo"]}
        with self.assertRaises(styles.StyleError):
            styles.validate_style_data(self.sample_data(picks=bad_picks))

    def test_missing_or_empty_style_md_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp) / "swiss-motion"
            tmp_path.mkdir()
            # Missing STYLE.md
            with self.assertRaises(styles.StyleError):
                styles.validate_style_data(self.sample_data(), dir_path=tmp_path)
            # Empty STYLE.md
            (tmp_path / "STYLE.md").write_text("   \n", encoding="utf-8")
            with self.assertRaises(styles.StyleError):
                styles.validate_style_data(self.sample_data(), dir_path=tmp_path)
            # Non-empty STYLE.md passes
            (tmp_path / "STYLE.md").write_text("# Swiss Motion\nInvariants here.", encoding="utf-8")
            self.assertTrue(styles.validate_style_data(self.sample_data(), dir_path=tmp_path))

    def test_brand_allows_palette_pack_everywhere(self):
        pack_style = self.sample_data(palette="pack")
        tt = brand.load("tbilisi-today")
        st = brand.load("sitech")

        # News program
        ok, _ = styles.brand_allows(tt, pack_style, program="news")
        self.assertTrue(ok)
        ok, _ = styles.brand_allows(st, pack_style, program="news")
        self.assertTrue(ok)

        # Other programs
        ok, _ = styles.brand_allows(tt, pack_style, program="explainer")
        self.assertTrue(ok)

    def test_brand_allows_palette_own_rules(self):
        own_style = self.sample_data(slug="blueprint", palette="own")
        tt = brand.load("tbilisi-today")

        # News never uses palette: own
        ok, reason = styles.brand_allows(tt, own_style, program="news")
        self.assertFalse(ok)
        self.assertIn("news programs never permit", reason)

        # Non-news: pack must list the slug in its 'styles' key
        ok, reason = styles.brand_allows(tt, own_style, program="explainer")
        self.assertFalse(ok)
        self.assertIn("does not allow palette: own style", reason)

        # When pack lists it in 'styles', it is allowed for non-news
        allowed_pack = {**tt, "styles": ["blueprint"]}
        ok, reason = styles.brand_allows(allowed_pack, own_style, program="explainer")
        self.assertTrue(ok)

        # But still refused for news!
        ok, reason = styles.brand_allows(allowed_pack, own_style, program="news")
        self.assertFalse(ok)
        self.assertIn("news programs never permit", reason)

    def test_resolve_for_story(self):
        pack_style = self.sample_data(slug="swiss-motion", programs=["news", "explainer"], never_families=["crime"])
        
        # Mock styles.get
        orig_get = styles.get
        try:
            styles.get = lambda slug: pack_style if slug == "swiss-motion" else orig_get(slug)

            # Story with valid style
            story = {"id": "1", "style": "swiss-motion", "family": "tech", "program": "news"}
            res = styles.resolve_for_story(story)
            self.assertEqual(res["slug"], "swiss-motion")

            # Story with unsuited program
            bad_prog_story = {"id": "2", "style": "swiss-motion", "family": "tech", "program": "fiction"}
            with self.assertRaises(styles.StyleError) as cm:
                styles.resolve_for_story(bad_prog_story)
            self.assertIn("does not suit program", str(cm.exception))

            # Story with forbidden family
            bad_fam_story = {"id": "3", "style": "swiss-motion", "family": "crime", "program": "news"}
            with self.assertRaises(styles.StyleError) as cm:
                styles.resolve_for_story(bad_fam_story)
            self.assertIn("cannot be used for family", str(cm.exception))

            # No style requested returns None
            self.assertIsNone(styles.resolve_for_story({"id": "4"}))
        finally:
            styles.get = orig_get

    def test_summary(self):
        data = self.sample_data()
        sm = styles.summary(data)
        self.assertEqual(sm["slug"], "swiss-motion")
        self.assertEqual(sm["name_en"], "Swiss Motion")
        self.assertEqual(sm["name_ka"], "შვეიცარიული მოძრაობა")
        self.assertIn("news", sm["programs"])
        self.assertEqual(sm["palette"], "pack")


if __name__ == "__main__":
    unittest.main()
