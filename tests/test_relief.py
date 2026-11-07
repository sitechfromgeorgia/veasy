"""Tests for Georgia 3D relief plates (tools/build_relief.py, assets/relief/, plates/relief/)."""

from __future__ import annotations

import csv
import json
import math
import os
import pathlib
import shutil
import subprocess
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


# Real heights (m, public sources) with a margin wide enough for the 800x418 grid (one cell is about 8 km wide, so a
# valley town reads as its surroundings) and for the zeroing outside Georgia.
HEIGHTS = {  # id: (lowest, highest) the grid may read at the place
    "batumi": (0, 60), "sokhumi": (0, 60), "kutaisi": (80, 300), "mtskheta": (350, 650),
    "sighnaghi": (500, 900), "telavi": (500, 900), "mestia": (1350, 1800), "ushguli": (1900, 2500),
    "stepantsminda": (1500, 2100),  # Kazbegi, about 1,740 m
}
SAMPLES = (0, 45, 90, 135, 179)


def _viewbox(meta, lon, lat):
    pr = meta["projection"]
    return (lon - pr["lon"][0]) * pr["cos"] * pr["k"], (pr["lat"][1] - lat) * pr["k"]


def _world(meta, dem, lon, lat):
    """Three.js world [x, y, z] of a lat/lon by its own arithmetic: projection, bilinear DEM, exaggeration."""
    vx, vy = _viewbox(meta, lon, lat)
    fx, fy = vx / 10000.0 * (dem.shape[1] - 1), vy / 5233.0 * (dem.shape[0] - 1)
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    x1, y1 = min(x0 + 1, dem.shape[1] - 1), min(y0 + 1, dem.shape[0] - 1)
    ax, ay = fx - x0, fy - y0
    z = (dem[y0, x0] * (1 - ax) * (1 - ay) + dem[y0, x1] * ax * (1 - ay)
         + dem[y1, x0] * (1 - ax) * ay + dem[y1, x1] * ax * ay) / 10.0
    return [(vx - 5000.0) / 100.0, float(z) / 1000.0 * meta["projection"]["vert_exag"], (vy - 5233.0 * 0.5) / 100.0]


def _project(pose, w, width=1080, height=1920):
    """Pixel of world point w seen by the pose's camera (pinhole, three.js lookAt with the roll applied to up)."""
    pos, look = np.array(pose["pos"]), np.array(pose["look"])
    f = look - pos
    fn = f / np.linalg.norm(f)
    rl = math.hypot(fn[2], fn[0]) or 1.0
    rn = np.array([-fn[2] / rl, 0.0, fn[0] / rl])
    up0 = np.cross(rn, fn)
    up = up0 * math.cos(pose["roll"]) + rn * math.sin(pose["roll"])
    zc = (pos - look) / np.linalg.norm(pos - look)
    xc = np.cross(up, zc)
    xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    d = np.array(w) - pos
    cx, cy, cz = xc @ d, yc @ d, zc @ d
    t = math.tan(math.radians(pose["fov"]) / 2.0)
    nx, ny = cx / (-cz) / (t * width / height), cy / (-cz) / t
    return (nx + 1) * 0.5 * width, (1 - ny) * 0.5 * height


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

    def test_known_places_stand_at_their_real_height_in_the_grid(self) -> None:
        with (ROOT / "assets" / "maps" / "georgia-places.csv").open(encoding="utf-8") as fh:
            rows = {r["id"]: r for r in csv.DictReader(fh)}
        for pid, (lo, hi) in HEIGHTS.items():
            lon, lat = float(rows[pid]["lon"]), float(rows[pid]["lat"])
            vx, vy = _viewbox(self.meta, lon, lat)
            ix, iy = int(round(vx / 10000.0 * 799)), int(round(vy / 5233.0 * 417))
            near = self.dem[max(0, iy - 1): iy + 2, max(0, ix - 1): ix + 2] / 10.0  # decimeters -> m
            here = float(self.dem[iy, ix]) / 10.0
            if hi <= 60:  # the coast: sea level at the place, and some cell around it
                self.assertLessEqual(here, hi, pid)
                self.assertLessEqual(float(near.min()), 30.0, pid)
            else:
                self.assertTrue(lo <= here <= hi, f"{pid}: {here} m not in {lo}..{hi}")
            self.assertAlmostEqual(self.meta["places"][pid]["world"][1],
                                   _world(self.meta, self.dem, lon, lat)[1], delta=0.02, msg=pid)

    def test_every_gazetteer_place_has_the_world_point_of_its_lat_lon(self) -> None:
        for pid, p in self.meta["places"].items():
            w = _world(self.meta, self.dem, p["lon"], p["lat"])
            for a, b in zip(w, p["world"]):
                self.assertAlmostEqual(a, b, delta=0.02, msg=pid)

    def test_anchors_are_the_projection_of_the_places_lat_lon(self) -> None:
        """Six plates by default (about 50 s); RELIEF_ALL_PLATES=1 checks all 51 (about 6 min)."""
        node = shutil.which("node")
        chrome_ok = (pathlib.Path.home() / ".cache" / "puppeteer" / "chrome-headless-shell").exists() or os.environ.get("VEASY_CHROME")
        if not (node and chrome_ok and (ROOT / "plates" / "node_modules" / "puppeteer-core").exists()
                and (PLATE_DATA_DIR / "relief_meta.json").exists()):
            self.skipTest("needs node, plates/ npm ci, a headless Chrome and the built relief data")
        names = sorted(f.stem for f in SPECS_DIR.glob("*.json"))
        self.assertEqual(len(names), 51)
        if not os.environ.get("RELIEF_ALL_PLATES"):
            names = [n for n in names if n in ("kazbegi-jvari", "svaneti", "kakheti", "region-adjara", "region-abkhazia", "region-imereti")]
        done = subprocess.run([node, str(PLATE_DIR / "pose_dump.mjs"), *[str(SPECS_DIR / f"{n}.json") for n in names]],
                              capture_output=True, text=True, timeout=900, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(done.returncode, 0, done.stderr[-800:])
        dump = json.loads(done.stdout)
        self.assertEqual(sorted(dump), names)
        out = ROOT / "out" / "plates"

        def place_world(key, vex=1.0):
            p = self.meta["places"][key]
            w = _world(self.meta, self.dem, p["lon"], p["lat"])
            w[1] *= vex
            return w

        for name, rows in dump.items():
            spec = json.loads((SPECS_DIR / f"{name}.json").read_text(encoding="utf-8"))
            baked = out / name / "anchors.json"
            tracks = json.loads(baked.read_text(encoding="utf-8"))["tracks"] if baked.exists() else None
            self.assertEqual(len(rows), len(SAMPLES))
            for row in rows:
                pose = row["pose"]
                for key, px in row["anchors"].items():
                    if key == "dot":
                        w = pose["dot"]
                    elif key in self.meta["places"]:
                        w = place_world(key, pose["vEx"])
                    else:
                        continue  # a landmark or a region centre: not a gazetteer place
                    ex, ey = _project(pose, w)
                    if px[0] in (0, 1080) or px[1] in (0, 1920):
                        # the page clamps what is off screen to the edge: it must really be off screen
                        self.assertFalse(0 <= ex <= 1080 and 0 <= ey <= 1920, f"{name}/{key}@{row['frame']}: clamped but projects inside")
                    else:
                        self.assertAlmostEqual(ex, px[0], delta=1.0, msg=f"{name}/{key}@{row['frame']} x")
                        self.assertAlmostEqual(ey, px[1], delta=1.0, msg=f"{name}/{key}@{row['frame']} y")
                    if tracks and key in tracks:  # the baked file is the same projection
                        bx, by = tracks[key][row["frame"]]
                        self.assertAlmostEqual(bx, px[0], delta=1.0, msg=f"{name}/{key}@{row['frame']} baked x")
                        self.assertAlmostEqual(by, px[1], delta=1.0, msg=f"{name}/{key}@{row['frame']} baked y")
            # the flight ends on its place, in frame: the dot is the target's projection at the last frame
            target = spec.get("to") or spec.get("anchor") or spec.get("place")
            if target in self.meta["places"] and spec.get("preset") != "kazbegi-jvari":
                last = rows[-1]
                ex, ey = _project(last["pose"], place_world(target, last["pose"]["vEx"]))
                self.assertTrue(0 < ex < 1080 and 0 < ey < 1920, f"{name}: {target} ends off screen at {ex:.0f},{ey:.0f}")
                self.assertAlmostEqual(last["anchors"]["dot"][0], ex, delta=1.5, msg=name)
                self.assertAlmostEqual(last["anchors"]["dot"][1], ey, delta=1.5, msg=name)


if __name__ == "__main__":
    unittest.main()
