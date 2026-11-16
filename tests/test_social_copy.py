"""Tests for brand-pack portability in tt_shorts/social_copy.py."""
import json
import pathlib
import tempfile
import unittest

from tt_shorts import brand, social_copy


ROOT = pathlib.Path(__file__).resolve().parent.parent


class SocialCopyBrandPortability(unittest.TestCase):
    def test_sitech_caption_uses_pack_hashtags_wordmark_and_has_no_tbilisi_leak(self):
        cap = social_copy.caption(
            "ახალი ხელსაწყო დეველოპერებისთვის",
            "კომპანია SiTech-მა ახალი ღია ბიბლიოთეკა გამოუშვა.",
            "https://sitech.ge/ka/blog/veasy/?utm_source=facebook",
            kind="video",
            category="ai",
            brand="sitech",
        )
        self.assertIn("🎬 ვიდეო · ხელოვნური ინტელექტი", cap)
        self.assertIn("sitech.ge", cap)
        for tag in brand.load("sitech")["social"]["hashtags"]:
            self.assertIn(tag, cap)
        self.assertIn("#ხელოვნურიინტელექტი", cap)
        self.assertNotIn("tbilisi", cap.lower())
        self.assertNotIn("თბილისი", cap)

    def test_tbilisi_today_caption_keeps_own_tags_and_wordmark(self):
        cap = social_copy.caption(
            "რუსთაველზე მოძრაობა შეიზღუდება",
            "მერიის ცნობით, ცვლილება დილის რვიდან იმოქმედებს.",
            "https://tbilisi.today/stories/33070",
            kind="photo",
            category="politics",
            brand="tbilisi-today",
        )
        self.assertIn("📰 სიახლე · პოლიტიკა", cap)
        self.assertIn("tbilisi.today", cap)
        self.assertIn("#tbilisitoday", cap)
        self.assertIn("#პოლიტიკა", cap)

    def test_pack_without_social_refuses(self):
        bare = json.loads((ROOT / "brands" / "sitech" / "brand.json").read_text(encoding="utf-8"))
        bare.pop("social", None)
        bare["name"] = "bare"
        with self.assertRaisesRegex(brand.BrandError, "this brand has no social config"):
            social_copy.caption("სათაური", "ტექსტი", brand=bare)
        with self.assertRaisesRegex(brand.BrandError, "this brand has no social config"):
            social_copy.hashtags(brand=bare)

    def test_guard_loads_plugins_dir_dynamically_from_pack_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            plug_root = pathlib.Path(tmp) / "plugins"
            (plug_root / "kaeasy").mkdir(parents=True)
            (plug_root / "kaeasy" / "__init__.py").write_text("", encoding="utf-8")
            (plug_root / "kaeasy" / "fix.py").write_text(
                "def fix_text(t):\n    return t.replace('FOO', 'BAR'), ['test']\n",
                encoding="utf-8",
            )
            (plug_root / "kaeasy" / "lint.py").write_text(
                "def check_text(t, mode='social'):\n    return []\n",
                encoding="utf-8",
            )
            social_copy._KAEASY_CACHE.clear()
            fixed, findings = social_copy.guard("ტესტი FOO https://sitech.ge/x", plugins_dir=str(plug_root))
            self.assertIn("BAR", fixed)
            self.assertIn("https://sitech.ge/x", fixed)
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
