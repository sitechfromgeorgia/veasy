"""Tests for Georgia 3D relief plates (tools/build_relief.py, assets/relief/, plates/relief/)."""

from __future__ import annotations

import json
import pathlib
import unittest

import numpy as np
from PIL import Image

from tt_shorts import geo

ROOT = pathlib.Path(__file__).resolve().parent.parent
RELIEF_DIR = ROOT / "assets" / "relief"
PLATE_DIR = ROOT / "plates" / "relief"
PLATE_DATA_DIR = PLATE_DIR / "data"
SPECS_DIR = PLATE_DIR / "specs"
MAP_JSON = ROOT / "assets" / "maps" / "georgia.json"


class TestGeorgiaRelief(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.map_data = json.loads(MAP_JSON.read_text(encoding="utf-8"))
        cls.meta = json.loads((RELIEF_DIR / "relief_meta.json").read_text(encoding="utf-8"))
        cls.dem_bytes = (RELIEF_DIR / "georgia_dem.bin").read_bytes()
        cls.dem = np.frombuffer(cls.dem_bytes, dtype="<u2").reshape(
            (cls.meta["grid"]["height"], cls.meta["grid"]["width"])
        )
        cls.mask_img = Image.open(RELIEF_DIR / "georgia_mask.png").convert("RGBA")
        cls.mask = np.asarray(cls.mask_img, dtype=np.uint8)

    def test_relief_artifacts_exist_and_sync_with_plate_data(self) -> None:
        for fname in ("georgia_dem.bin", "georgia_mask.png", "relief_meta.json"):
            src = RELIEF_DIR / fname
            dst = PLATE_DATA_DIR / fname
            self.assertTrue(src.exists(), f"Missing {src}")
            self.assertTrue(dst.exists(), f"Missing {dst}")
            self.assertEqual(src.read_bytes(), dst.read_bytes(), f"Out-of-sync {fname}")

        self.assertEqual(self.dem.shape, (418, 800))
        self.assertEqual(self.mask.shape, (418, 800, 4))
        max_m = float(self.dem.max()) / 10.0
        self.assertGreater(max_m, 4500.0)
        self.assertLess(max_m, 5300.0)

    def test_nothing_outside_georgia_outline_is_drawn_as_a_claim(self) -> None:
        land_r = self.mask[:, :, 0]
        outside = land_r <= 16
        self.assertGreater(int(outside.sum()), 100_000)
        # Every texel outside Georgia's land polygon from georgia.json must have 0 elevation and 0 hydro/border claim
        self.assertEqual(int(self.dem[outside].max()), 0)
        self.assertEqual(int(self.mask[:, :, 1][outside].max()), 0)
        self.assertEqual(int(self.mask[:, :, 2][outside].max()), 0)
        # Outside Georgia alpha code is 128 (region index 0)
        self.assertTrue(np.all(self.mask[:, :, 3][outside] == 128))

    def test_twelve_regions_of_georgian_law_including_abkhazia_and_tskhinvali(self) -> None:
        expected_regions = set(self.map_data["regions"].keys())
        self.assertEqual(len(expected_regions), 12)
        self.assertEqual(set(self.meta["regions"].keys()), expected_regions)

        # Only region indices 0 (outside) and 1..12 (the 12 regions of Georgian law) may exist in the mask
        alpha_vals = set(np.unique(self.mask[:, :, 3]).tolist())
        valid_alphas = {128 + i * 8 for i in range(13)}
        self.assertTrue(alpha_vals.issubset(valid_alphas), f"Unexpected region alpha codes: {alpha_vals - valid_alphas}")
        for i in range(1, 13):
            self.assertIn(128 + i * 8, alpha_vals, f"Region index {i} missing from georgia_mask.png")

        # Abkhazia is an integral region of Georgia with all 10 Abkhazian gazetteer places inside the land mask
        abk = self.meta["regions"]["abkhazia"]
        self.assertEqual(abk["name_ka"], "აფხაზეთი")
        self.assertGreater(abk["pixel_count"], 15_000)
        self.assertGreater(abk["max_elev_m"], 3000.0)
        abk_places = [p for p in self.meta["places"].values() if p["region"] == "abkhazia"]
        self.assertEqual(len(abk_places), 10)
        for p in abk_places:
            vx, vy = p["viewbox"]
            ix = min(799, max(0, int(round(vx / 10000.0 * 799))))
            iy = min(417, max(0, int(round(vy / 5233.0 * 417))))
            self.assertGreater(int(self.mask[iy, ix, 0]), 50, f"Abkhazia place {p['id']} not in Georgia land mask")

        # Tskhinvali region sits inside Shida Kartli (tskhinvali, java, qornisi) and Mtskheta-Mtianeti (akhalgori)
        # with no separate entity anywhere in metadata, regions, or mask
        for forbidden in ("south-ossetia", "samachablo", "provisional", "tskhinvali-region"):
            self.assertNotIn(forbidden, self.meta["regions"])
        self.assertEqual(self.meta["places"]["tskhinvali"]["region"], "shida-kartli")
        self.assertEqual(self.meta["places"]["java"]["region"], "shida-kartli")
        self.assertEqual(self.meta["places"]["qornisi"]["region"], "shida-kartli")
        self.assertEqual(self.meta["places"]["akhalgori"]["region"], "mtskheta-mtianeti")
        for pid, expected_reg in (
            ("tskhinvali", "shida-kartli"),
            ("java", "shida-kartli"),
            ("qornisi", "shida-kartli"),
            ("akhalgori", "mtskheta-mtianeti"),
        ):
            p = self.meta["places"][pid]
            self.assertGreater(p["elev_m"], 500.0, f"{pid} must have real terrain elevation")
            vx, vy = p["viewbox"]
            ix = min(799, max(0, int(round(vx / 10000.0 * 799))))
            iy = min(417, max(0, int(round(vy / 5233.0 * 417))))
            self.assertGreater(int(self.mask[iy, ix, 0]), 128)
            expected_alpha = self.meta["regions"][expected_reg]["alpha_code"]
            self.assertEqual(int(self.mask[iy, ix, 3]), expected_alpha, f"{pid} mask alpha must belong to {expected_reg}")

    def test_all_149_gazetteer_places_match_geo_py_and_project_to_3d_world(self) -> None:
        geo_places = {p["id"]: p for p in geo.data()["places"]}
        self.assertEqual(len(self.meta["places"]), 149)
        self.assertEqual(set(self.meta["places"].keys()), set(geo_places.keys()))
        for pid, gplace in geo_places.items():
            rplace = self.meta["places"][pid]
            self.assertEqual(rplace["ka"], gplace["name"])
            self.assertEqual(rplace["region"], gplace["region"])
            self.assertEqual(rplace["kind"], gplace["kind"])
            # ViewBox coordinates must match geo.py's rounded integer point within 1 viewBox unit
            self.assertAlmostEqual(rplace["viewbox"][0], gplace["point"][0], delta=1.0)
            self.assertAlmostEqual(rplace["viewbox"][1], gplace["point"][1], delta=1.0)
            wx, wy, wz = rplace["world"]
            self.assertTrue(-50.0 <= wx <= 50.0)
            self.assertTrue(-26.2 <= wz <= 26.2)
            self.assertGreaterEqual(wy, 0.0)

    def test_48_region_and_district_specs_and_3_signature_specs_are_valid(self) -> None:
        catalog = self.meta["catalog_48"]
        self.assertEqual(len(catalog), 48)
        regions_in_cat = [c for c in catalog if c["category"] == "region"]
        districts_in_cat = [c for c in catalog if c["category"] == "district"]
        self.assertEqual(len(regions_in_cat), 12)
        self.assertEqual(len(districts_in_cat), 36)

        for item in catalog:
            spec_file = SPECS_DIR / f"{item['slug']}.json"
            self.assertTrue(spec_file.exists(), f"Missing spec file {spec_file}")
            spec = json.loads(spec_file.read_text(encoding="utf-8"))
            self.assertIn(spec["move"], ("descend", "ridge", "reveal"))
            self.assertIn(spec["region"], self.meta["regions"])

        for sig in ("kazbegi-jvari", "svaneti", "kakheti"):
            spec_file = SPECS_DIR / f"{sig}.json"
            self.assertTrue(spec_file.exists(), f"Missing signature spec {spec_file}")
            spec = json.loads(spec_file.read_text(encoding="utf-8"))
            self.assertEqual(spec["preset"], sig)
            self.assertIn(spec["move"], ("descend", "ridge", "reveal"))

    def test_plate_html_contract_and_refusals(self) -> None:
        html = (PLATE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn("window.setup", html)
        self.assertIn("window.step", html)
        self.assertIn("window.anchors", html)
        self.assertIn("gl_FragColor = vec4(lum, lum, lum, 1.0);", html)
        for move in ("descend", "ridge", "reveal"):
            self.assertIn(f'"{move}"', html)
        for forbidden in ("news", "crime", "incidents", "deaths"):
            self.assertIn(f'"{forbidden}"', html)

        readme = (PLATE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("node plates/run.mjs relief", readme)
        self.assertIn("kazbegi-jvari.json", readme)
        for item in self.meta["catalog_48"]:
            self.assertIn(f"{item['slug']}.json", readme)

    def test_baked_signature_flights_have_monochrome_posters_and_safe_anchors(self) -> None:
        out_plates = ROOT / "out" / "plates"
        for sig in ("kazbegi-jvari", "svaneti", "kakheti"):
            pdir = out_plates / sig
            if not pdir.exists():
                continue
            pjson = json.loads((pdir / "plate.json").read_text(encoding="utf-8"))
            self.assertEqual(pjson["kind"], "relief")
            self.assertEqual(pjson["frames"], 180)
            self.assertIn("dot", pjson["anchors"])

            ajson = json.loads((pdir / "anchors.json").read_text(encoding="utf-8"))
            self.assertEqual(ajson["width"], 1080)
            self.assertEqual(ajson["height"], 1920)
            dot_track = ajson["tracks"]["dot"]
            self.assertEqual(len(dot_track), 180)
            for x, y in dot_track:
                self.assertTrue(150.0 <= x <= 930.0, f"{sig} dot x={x} out of safe horizontal bounds")
                self.assertTrue(300.0 <= y <= 1350.0, f"{sig} dot y={y} out of safe vertical bounds")

            poster = Image.open(pdir / "poster.png").convert("RGB")
            arr = np.asarray(poster, dtype=np.int16)
            # Every pixel in poster.png must be strictly grey (R == G == B within 1 LSB from JPEG/PNG roundtrip)
            self.assertLessEqual(int(np.abs(arr[:, :, 0] - arr[:, :, 1]).max()), 1)
            self.assertLessEqual(int(np.abs(arr[:, :, 1] - arr[:, :, 2]).max()), 1)
            # Top header band (y < 60) is pure dark sky (#000000) and middle terrain has rich relief contrast
            self.assertLess(float(arr[:60, :, 0].mean()), 5.0)
            self.assertGreater(float(arr[400:1300, :, 0].std()), 15.0)


if __name__ == "__main__":
    unittest.main()
