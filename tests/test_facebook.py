"""Tests for brand-pack portability in tt_shorts/facebook.py."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, facebook


ROOT = pathlib.Path(__file__).resolve().parent.parent


def _temp_pack(d: pathlib.Path, source: str, *, include_social: bool = True,
               tok_path: pathlib.Path | None = None, pid_path: pathlib.Path | None = None,
               reels_per_day: int = 5):
    data = json.loads((ROOT / "brands" / source / "brand.json").read_text(encoding="utf-8"))
    if include_social:
        data["social"] = {
            **data["social"],
            "facebook": {
                "page_id_file": str(pid_path),
                "token_file": str(tok_path),
                "reels_per_day": reels_per_day,
            },
        }
    else:
        data.pop("social", None)
    (d / source).mkdir(parents=True, exist_ok=True)
    (d / source / "brand.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for f in (d / source).parent.glob("*"):
        pass
    for fn in ("logo-horizontal.svg", "logo-stacked.svg", "logo-horizontal-coal.svg", "logo-stacked-coal.svg"):
        src = ROOT / "brands" / source / fn
        if src.exists():
            (d / source / fn).write_bytes(src.read_bytes())


class FacebookBrandPortability(unittest.TestCase):
    def test_pack_without_social_refuses_instead_of_using_default_credentials(self):
        bare = json.loads((ROOT / "brands" / "sitech" / "brand.json").read_text(encoding="utf-8"))
        bare.pop("social", None)
        bare["name"] = "bare"
        bare["_dir"] = str(ROOT / "brands" / "sitech")

        self.assertFalse(facebook.armed(brand=bare))
        with self.assertRaisesRegex(brand.BrandError, "this brand has no social config"):
            facebook.page_id(brand=bare)
        with self.assertRaisesRegex(brand.BrandError, "this brand has no social config"):
            facebook.page_token(brand=bare)
        with self.assertRaisesRegex(brand.BrandError, "this brand has no social config"):
            facebook.send_video("missing.mp4", "cap", dry=True, brand=bare)

    def test_reads_brand_credentials_daily_target_and_routes_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            packs_dir = tmp_dir / "brands"
            (packs_dir / "_ka").mkdir(parents=True)
            (packs_dir / "_ka" / "brand.json").write_text(
                (ROOT / "brands" / "_ka" / "brand.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            sitech_tok = tmp_dir / "sitech-token.txt"
            sitech_pid = tmp_dir / "sitech-pid.txt"
            sitech_tok.write_text("SITECH_SECRET_TOK", encoding="utf-8")
            sitech_pid.write_text("999000111", encoding="utf-8")

            tt_tok = tmp_dir / "tt-token.txt"
            tt_pid = tmp_dir / "tt-pid.txt"
            tt_tok.write_text("TT_SECRET_TOK", encoding="utf-8")
            tt_pid.write_text("111222333", encoding="utf-8")

            _temp_pack(packs_dir, "sitech", tok_path=sitech_tok, pid_path=sitech_pid, reels_per_day=7)
            _temp_pack(packs_dir, "tbilisi-today", tok_path=tt_tok, pid_path=tt_pid, reels_per_day=3)

            with mock.patch.object(brand, "DIR", packs_dir):
                brand.load.cache_clear()
                self.assertEqual(facebook.page_id(brand="sitech"), "999000111")
                self.assertEqual(facebook.page_token(brand="sitech"), "SITECH_SECRET_TOK")
                self.assertEqual(facebook.daily_target("sitech"), 7)
                self.assertEqual(facebook.page_id(brand="tbilisi-today"), "111222333")
                self.assertEqual(facebook.daily_target("tbilisi-today"), 3)
                self.assertTrue(facebook.armed(brand="sitech"))

                calls = []

                def fake_call(method, url, *, data=None, headers=None, timeout=120, idempotent=False):
                    calls.append((method, url, data))
                    return 200, {}, {"id": "999000111_42"}

                with mock.patch.object(facebook, "_call", side_effect=fake_call):
                    res = facebook.send_text("SiTech test post", brand="sitech")
                self.assertTrue(res["ok"])
                self.assertIn("/999000111/feed", calls[0][1])
                self.assertIn(b"SITECH_SECRET_TOK", calls[0][2])

                # CLI refuses a pack with missing social config cleanly with exit code 2
                bare_dir = packs_dir / "bare"
                _temp_pack(packs_dir, "sitech", include_social=False)
                # Copy into bare
                bare_data = json.loads((packs_dir / "sitech" / "brand.json").read_text(encoding="utf-8"))
                bare_data["name"] = "bare"
                bare_dir.mkdir(exist_ok=True)
                (bare_dir / "brand.json").write_text(json.dumps(bare_data, ensure_ascii=False), encoding="utf-8")
                for fn in ("logo-horizontal.svg", "logo-stacked.svg", "logo-horizontal-coal.svg", "logo-stacked-coal.svg"):
                    (bare_dir / fn).write_bytes((ROOT / "brands" / "sitech" / fn).read_bytes())
                brand.load.cache_clear()
                self.assertEqual(facebook.main(["verify", "--brand", "bare"]), 2)


if __name__ == "__main__":
    unittest.main()
