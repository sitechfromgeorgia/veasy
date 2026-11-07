"""Unit tests for Veasy lit-surfaces builder and asset pipeline."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from tools import surface_procedural as sp
from tools.build_surfaces import (
    MAX_GIT_MB,
    MATERIALS_CATALOG,
    build_all,
    calculate_dir_mb,
    compute_scharr_normals,
    compute_sha256,
    make_seamless_tile,
    process_material,
    process_procedural,
    validate_record,
    to_normalized_greyscale,
)


class TestBuildSurfaces(unittest.TestCase):
    """Test suite for tools/build_surfaces.py functions and invariants."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="veasy_surf_test_"))
        self.raw_dir = self.temp_dir / "raw"
        self.out_dir = self.temp_dir / "assets" / "surfaces"
        self.plates_dir = self.temp_dir / "plates" / "surface" / "textures"
        self.raw_dir.mkdir(parents=True)
        self.out_dir.mkdir(parents=True)
        self.plates_dir.mkdir(parents=True)

        # Create synthetic test image (256x256)
        x = np.linspace(0, 4 * np.pi, 256)
        y = np.linspace(0, 4 * np.pi, 256)
        xx, yy = np.meshgrid(x, y)
        test_pattern = (np.sin(xx) * np.cos(yy) * 0.5 + 0.5) * 255.0
        self.synth_img = Image.fromarray(test_pattern.astype(np.uint8), mode="L").convert("RGB")
        self.synth_path = self.raw_dir / "synth_raw.png"
        self.synth_img.save(self.synth_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_greyscale_normalization(self):
        """Greyscale conversion maps to normalized [0, 1] range."""
        grey = to_normalized_greyscale(self.synth_img)
        self.assertEqual(grey.shape, (256, 256))
        self.assertGreaterEqual(float(grey.min()), 0.0)
        self.assertLessEqual(float(grey.max()), 1.0)
        self.assertTrue(np.issubdtype(grey.dtype, np.floating))

    def test_seamless_tiling_bounds(self):
        """Seamless tiling produces valid [0, 1] values without NaNs."""
        grey = to_normalized_greyscale(self.synth_img)
        seamless = make_seamless_tile(grey)
        self.assertEqual(seamless.shape, grey.shape)
        self.assertFalse(np.isnan(seamless).any())
        self.assertGreaterEqual(float(seamless.min()), 0.0)
        self.assertLessEqual(float(seamless.max()), 1.0)

    def test_scharr_normals_opengl_convention(self):
        """Scharr normal calculation generates valid unit vectors with +Z outward."""
        grey = to_normalized_greyscale(self.synth_img)
        normals = compute_scharr_normals(grey, depth_scale=1.0)
        self.assertEqual(normals.shape, (256, 256, 3))
        self.assertEqual(normals.dtype, np.uint8)

        # Unpack normalized float vectors
        nx = (normals[:, :, 0].astype(np.float32) / 255.0) * 2.0 - 1.0
        ny = (normals[:, :, 1].astype(np.float32) / 255.0) * 2.0 - 1.0
        nz = (normals[:, :, 2].astype(np.float32) / 255.0) * 2.0 - 1.0

        length = np.sqrt(nx * nx + ny * ny + nz * nz)
        # Vector lengths must be near 1.0 (allowing for 8-bit quantization)
        self.assertTrue(np.allclose(length, 1.0, atol=0.08))

        # Nz must always be positive (pointing towards viewer out of surface plane)
        self.assertTrue((nz > 0.0).all())
        # Blue channel (encoded Nz) must be >= 127
        self.assertGreaterEqual(int(normals[:, :, 2].min()), 127)

    def test_process_material_outputs(self):
        """Processing a single material creates height.png, normal.png, meta.json and mirrors to plates."""
        record = process_material(
            material_id="limestone",
            raw_path=self.synth_path,
            out_dir=self.out_dir,
            plates_dir=self.plates_dir,
            size=128,
            prompt="limestone test prompt",
            model="imagen-3.0",
        )
        self.assertEqual(record["id"], "limestone")
        self.assertEqual(record["dimensions"], [128, 128])
        self.assertTrue(record["n13_label_required"])
        self.assertEqual(record["license"], "ai")

        mat_dir = self.out_dir / "limestone"
        self.assertTrue((mat_dir / "height.png").exists())
        self.assertTrue((mat_dir / "normal.png").exists())
        self.assertTrue((mat_dir / "meta.json").exists())

        # Check mirror in plates_dir
        self.assertTrue((self.plates_dir / "limestone" / "height.png").exists())
        self.assertTrue((self.plates_dir / "limestone" / "normal.png").exists())

    def test_build_all_and_ledger(self):
        """build_all creates a valid LEDGER.json and respects budget constraint."""
        manifest = {
            "limestone": {"path": str(self.synth_path), "prompt": "stone test", "model": "test-v1"},
            "raw_wood": {"path": str(self.synth_path), "prompt": "wood test", "model": "test-v1"},
        }
        ledger = build_all(manifest, out_dir=self.out_dir, plates_dir=self.plates_dir, size=128)
        self.assertIn("materials", ledger)
        self.assertEqual(ledger["material_count"], 2)
        self.assertTrue(ledger["budget_pass"])
        self.assertLess(ledger["total_disk_mb"], MAX_GIT_MB)

        ledger_file = self.out_dir / "LEDGER.json"
        self.assertTrue(ledger_file.exists())
        with open(ledger_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("limestone", data["materials"])
        self.assertIn("raw_wood", data["materials"])

    def test_catalog_completeness(self):
        """Materials catalog defines required core materials with appropriate parameters."""
        required = ["limestone", "worn_plaster", "handmade_paper", "raw_wood"]
        for mat in required:
            self.assertIn(mat, MATERIALS_CATALOG)
            entry = MATERIALS_CATALOG[mat]
            self.assertIn("depth", entry)
            self.assertIn("roughness", entry)
            self.assertTrue(entry.get("n13_label_required", False))


class TestProcedural(unittest.TestCase):
    """The code-drawn materials: deterministic, seamless, never marked ai."""

    N = 128

    def test_at_least_fifteen_materials(self):
        self.assertGreaterEqual(len(sp.MATERIALS), 15)

    def test_same_seed_same_bytes(self):
        for mid in sp.MATERIALS:
            a = sp.generate(mid, sp.default_seed(mid), self.N)
            b = sp.generate(mid, sp.default_seed(mid), self.N)
            self.assertEqual(a.tobytes(), b.tobytes(), mid)
            self.assertEqual(a.shape, (self.N, self.N))
            self.assertGreaterEqual(float(a.min()), 0.0)
            self.assertLessEqual(float(a.max()), 1.0)

    def test_seed_changes_result(self):
        for mid in ("slate", "bark", "linen"):
            a = sp.generate(mid, 1, self.N)
            b = sp.generate(mid, 2, self.N)
            self.assertNotEqual(a.tobytes(), b.tobytes(), mid)

    def test_tiles_are_seamless_and_not_flat(self):
        for mid in sp.MATERIALS:
            h = sp.generate(mid, sp.default_seed(mid), self.N)
            self.assertLessEqual(sp.seam_ratio(h), 1.25, mid)
            self.assertGreater(float(h.std()), 0.08, mid)  # real relief, not a flat field

    def test_seam_check_catches_a_cut_tile(self):
        ramp = np.tile(np.linspace(0.0, 1.0, self.N, dtype=np.float32), (self.N, 1))  # not periodic: wraps with a jump
        cut = 0.8 * ramp + 0.2 * sp.generate("slate", 5, self.N)
        self.assertGreater(sp.seam_ratio(cut), 1.5)

    def test_materials_are_distinct(self):
        # different matter must not be near-duplicates: compare normalised spectra of every pair
        specs = {}
        for mid in sp.MATERIALS:
            h = sp.generate(mid, sp.default_seed(mid), self.N)
            f = np.abs(np.fft.fft2(h - h.mean()))
            specs[mid] = (f / np.linalg.norm(f)).ravel()
        ids = sorted(specs)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                self.assertLess(float(specs[a] @ specs[b]), 0.995, (a, b))

    def test_process_procedural_ledger_record(self):
        tmp = Path(tempfile.mkdtemp(prefix="veasy_proc_"))
        try:
            rec1 = process_procedural("wax", tmp / "a", tmp / "pa", size=self.N)
            rec2 = process_procedural("wax", tmp / "b", None, size=self.N)
            self.assertEqual(rec1["license"], "procedural")
            self.assertEqual(rec1["seed"], sp.default_seed("wax"))
            self.assertIn("surface_procedural", rec1["generator"])
            self.assertNotIn("model", rec1)
            self.assertEqual(rec1["sha256"], rec2["sha256"])  # byte-identical files
            self.assertTrue((tmp / "pa" / "wax" / "normal.png").exists())
            self.assertTrue(rec1["n13_label_required"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_procedural_entry_cannot_be_marked_ai(self):
        good = {"id": "x", "license": "procedural", "generator": "g", "seed": 1}
        validate_record(good)
        with self.assertRaises(ValueError):
            validate_record({**good, "license": "ai"})
        with self.assertRaises(ValueError):
            validate_record({**good, "model": "imagen-3.0"})
        with self.assertRaises(ValueError):
            validate_record({"id": "y", "license": "procedural"})  # no generator or seed
        with self.assertRaises(ValueError):
            validate_record({"id": "z", "license": "stock"})

    def test_shipped_ledger_is_valid_and_complete(self):
        root = Path(__file__).resolve().parent.parent
        data = json.loads((root / "assets" / "surfaces" / "LEDGER.json").read_text(encoding="utf-8"))
        for mid, rec in data["materials"].items():
            validate_record(rec)
            self.assertTrue(rec["n13_label_required"], mid)
            if rec["license"] == "procedural":
                self.assertIn(mid, sp.MATERIALS)
                self.assertTrue((root / "plates" / "surface" / "textures" / mid / "normal.png").exists(), mid)


if __name__ == "__main__":
    unittest.main()
