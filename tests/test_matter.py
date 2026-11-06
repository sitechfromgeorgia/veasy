"""
tests/test_matter.py

Unit tests for the plates matter count and spec verifier (plates/matter/verifier.mjs).
Enforces:
  - Exact divisibility: count * unit = fact exactly (no rounding, no approximation)
  - Capacity: count <= 3000 blocks
  - Positive integer facts and units
  - Group partition validation
  - Refusal of forbidden categories (news, crime, incidents, deaths, real place assertions)
  - Story reference resolution
"""

import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "plates" / "matter" / "verifier.mjs"


def run_verifier(spec_or_arg, cwd=ROOT):
    """Run node plates/matter/verifier.mjs with the given spec (dict or string)."""
    arg = json.dumps(spec_or_arg) if isinstance(spec_or_arg, dict) else str(spec_or_arg)
    cmd = ["node", str(VERIFIER), arg]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")



def verify_spec(spec_dict, cwd=ROOT):
    """Run verifier and return parsed JSON result, asserting exit code 0."""
    proc = run_verifier(spec_dict, cwd=cwd)
    if proc.returncode != 0:
        raise AssertionError(f"Verifier failed (code {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(proc.stdout)


class TestMatterVerifier(unittest.TestCase):
    def test_verifier_file_exists(self):
        self.assertTrue(VERIFIER.exists(), f"verifier.mjs missing at {VERIFIER}")

    def test_exact_divisibility_pass(self):
        """Pass when fact is exactly divisible by unit and count <= 3000."""
        # 2.4 billion GEL with unit 1 million GEL -> 2,400 blocks
        res = verify_spec({"fact": 2400000000, "unit": 1000000})
        self.assertEqual(res["fact"], 2400000000)
        self.assertEqual(res["unit"], 1000000)
        self.assertEqual(res["count"], 2400)
        self.assertTrue(res["verified"])
        self.assertEqual(res["form"], "pile")

        # Small exact divisibility
        res_small = verify_spec({"fact": 100, "unit": 10})
        self.assertEqual(res_small["count"], 10)

        # Boundary capacity test: exactly 3000 blocks
        res_max = verify_spec({"fact": 3000, "unit": 1})
        self.assertEqual(res_max["count"], 3000)

    def test_non_divisible_unit_refused(self):
        """Refuse non-divisible unit with remainder in error message."""
        proc = run_verifier({"fact": 2400000000, "unit": 700000})
        self.assertNotEqual(proc.returncode, 0)
        expected_remainder = 2400000000 % 700000  # 400000
        self.assertIn(
            f"unit 700000 does not divide fact 2400000000 exactly (remainder {expected_remainder})",
            proc.stderr,
        )

        # 10 / 3 -> remainder 1
        proc2 = run_verifier({"fact": 10, "unit": 3})
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("unit 3 does not divide fact 10 exactly (remainder 1)", proc2.stderr)

        # 100 / 7 -> remainder 2
        proc3 = run_verifier({"fact": 100, "unit": 7})
        self.assertNotEqual(proc3.returncode, 0)
        self.assertIn("unit 7 does not divide fact 100 exactly (remainder 2)", proc3.stderr)

    def test_cap_over_3000_refused(self):
        """Enforce maximum capacity of 3000 blocks."""
        # 3001 blocks
        proc = run_verifier({"fact": 3001, "unit": 1})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(
            "block count 3001 exceeds maximum capacity of 3000 blocks; choose a larger unit",
            proc.stderr,
        )

        # 30,010 / 10 = 3001 blocks
        proc2 = run_verifier({"fact": 30010, "unit": 10})
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn(
            "block count 3001 exceeds maximum capacity of 3000 blocks; choose a larger unit",
            proc2.stderr,
        )

    def test_negative_or_zero_fact_refused(self):
        """Refuse zero, negative, or non-integer fact and unit."""
        # Zero fact
        proc_zero = run_verifier({"fact": 0, "unit": 1})
        self.assertNotEqual(proc_zero.returncode, 0)
        self.assertIn("fact must be a positive integer, got 0", proc_zero.stderr)

        # Negative fact
        proc_neg = run_verifier({"fact": -50, "unit": 10})
        self.assertNotEqual(proc_neg.returncode, 0)
        self.assertIn("fact must be a positive integer, got -50", proc_neg.stderr)

        # Zero unit
        proc_unit_zero = run_verifier({"fact": 100, "unit": 0})
        self.assertNotEqual(proc_unit_zero.returncode, 0)
        self.assertIn("unit must be a positive integer, got 0", proc_unit_zero.stderr)

        # Negative unit
        proc_unit_neg = run_verifier({"fact": 100, "unit": -10})
        self.assertNotEqual(proc_unit_neg.returncode, 0)
        self.assertIn("unit must be a positive integer, got -10", proc_unit_neg.stderr)

        # Non-integer fact
        proc_float_fact = run_verifier({"fact": 10.5, "unit": 1})
        self.assertNotEqual(proc_float_fact.returncode, 0)
        self.assertIn("fact must be an integer", proc_float_fact.stderr)

        # Non-integer unit
        proc_float_unit = run_verifier({"fact": 10, "unit": 2.5})
        self.assertNotEqual(proc_float_unit.returncode, 0)
        self.assertIn("unit must be an integer", proc_float_unit.stderr)

    def test_group_partitions_validation(self):
        """Validate group partition sums and individual group divisibility."""
        # Valid groups: 600M + 1800M = 2400M
        spec = {
            "fact": 2400000000,
            "unit": 1000000,
            "groups": [
                {"name": "health", "fact": 600000000},
                {"name": "education", "fact": 1800000000},
            ],
        }
        res = verify_spec(spec)
        self.assertEqual(res["count"], 2400)
        self.assertEqual(len(res["groups"]), 2)
        self.assertEqual(res["groups"][0]["count"], 600)
        self.assertEqual(res["groups"][1]["count"], 1800)

        # Mismatched group sum: 600M + 1700M = 2300M != 2400M
        bad_sum_spec = {
            "fact": 2400000000,
            "unit": 1000000,
            "groups": [
                {"name": "health", "fact": 600000000},
                {"name": "education", "fact": 1700000000},
            ],
        }
        proc_sum = run_verifier(bad_sum_spec)
        self.assertNotEqual(proc_sum.returncode, 0)
        self.assertIn(
            "sum of group facts (2300000000) does not equal total fact (2400000000)",
            proc_sum.stderr,
        )

        # Group fact not divisible by unit
        indivisible_group = {
            "fact": 100,
            "unit": 10,
            "groups": [
                {"name": "alpha", "fact": 65},
                {"name": "beta", "fact": 35},
            ],
        }
        proc_grp = run_verifier(indivisible_group)
        self.assertNotEqual(proc_grp.returncode, 0)
        self.assertIn('unit 10 does not divide group "alpha" fact 65 exactly (remainder 5)', proc_grp.stderr)

    def test_refusal_of_forbidden_categories(self):
        """Refuse news, crime, incidents, deaths, and real place assertions under CLAUDE.md § N and plates/README.md."""
        for forbidden in ("news", "crime", "incident", "incidents", "death", "deaths"):
            proc_cat = run_verifier({"fact": 100, "unit": 10, "category": forbidden})
            self.assertNotEqual(proc_cat.returncode, 0)
            self.assertIn(f'plates are strictly forbidden for category "{forbidden}"', proc_cat.stderr)

            proc_prog = run_verifier({"fact": 100, "unit": 10, "program": forbidden})
            self.assertNotEqual(proc_prog.returncode, 0)
            self.assertIn(f'plates are strictly forbidden for program "{forbidden}"', proc_prog.stderr)

        # Real place assertions
        proc_real = run_verifier({"fact": 100, "unit": 10, "real_place": True})
        self.assertNotEqual(proc_real.returncode, 0)
        self.assertIn("plates are strictly forbidden from real place assertions", proc_real.stderr)

        proc_place = run_verifier({"fact": 100, "unit": 10, "place": "Rustaveli Avenue"})
        self.assertNotEqual(proc_place.returncode, 0)
        self.assertIn("plates are strictly forbidden from real place assertions", proc_place.stderr)

    def test_story_reference_resolution(self):
        """Resolve fact from story JSON file via fact_ref or fact.ref."""
        # stories/24835.json has scene 1 with stat value 6400
        spec_fact_ref = {
            "fact_ref": {
                "file": "stories/24835.json",
                "key": "scene-1-value",
            },
            "unit": 100,
        }
        res1 = verify_spec(spec_fact_ref)
        self.assertEqual(res1["fact"], 6400)
        self.assertEqual(res1["unit"], 100)
        self.assertEqual(res1["count"], 64)

        # Alternative syntax: fact as reference object
        spec_fact_obj = {
            "fact": {
                "ref": "stories/24835.json",
                "key": "scene-1-value",
            },
            "unit": 64,
        }
        res2 = verify_spec(spec_fact_obj)
        self.assertEqual(res2["fact"], 6400)
        self.assertEqual(res2["unit"], 64)
        self.assertEqual(res2["count"], 100)

        # Missing story file
        proc_missing = run_verifier({
            "fact_ref": {"file": "stories/does-not-exist.json", "key": "scene-1-value"},
            "unit": 10,
        })
        self.assertNotEqual(proc_missing.returncode, 0)
        self.assertIn("Story file not found", proc_missing.stderr)

    def test_story_forbidden_category_refused(self):
        """Refuse story references if the referenced story belongs to a forbidden category or mentions deaths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Story with category "crime"
            crime_story = {
                "id": 99001,
                "category": "crime",
                "scenes": [{"type": "stat", "value": 500}],
            }
            crime_path = pathlib.Path(tmpdir) / "crime.json"
            crime_path.write_text(json.dumps(crime_story), encoding="utf-8")

            proc = run_verifier({
                "fact_ref": {"file": str(crime_path), "key": "scene-0-value"},
                "unit": 50,
            })
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('plates are strictly forbidden for story category "crime"', proc.stderr)

            # Story with death in narration
            death_story = {
                "id": 99002,
                "category": "society",
                "narration": "ავარიის შედეგად 2 ადამიანი დაიღუპა ადგილზე.",
                "scenes": [{"type": "stat", "value": 1000}],
            }
            death_path = pathlib.Path(tmpdir) / "death.json"
            death_path.write_text(json.dumps(death_story), encoding="utf-8")

            proc_death = run_verifier({
                "fact_ref": {"file": str(death_path), "key": "scene-0-value"},
                "unit": 100,
            })
            self.assertNotEqual(proc_death.returncode, 0)
            self.assertIn("plates are strictly forbidden for stories about deaths", proc_death.stderr)

    def test_esm_module_exports_and_error_classes(self):
        """Verify ESM imports and custom error class instances."""
        node_script = """
import {
  verifySpec,
  resolveFact,
  resolveStoryKey,
  checkForbidden,
  UnitMismatchError,
  BlockCountExceededError,
  ForbiddenCategoryError,
  GroupPartitionError,
  InvalidFactError,
  MAX_BLOCK_COUNT,
  FORBIDDEN_CATEGORIES
} from "./plates/matter/verifier.mjs";

let passed = 0;

// Test UnitMismatchError
try {
  verifySpec({ fact: 10, unit: 3 });
} catch (e) {
  if (e instanceof UnitMismatchError && e.unit === 3 && e.fact === 10 && e.remainder === 1) {
    passed++;
  }
}

// Test BlockCountExceededError
try {
  verifySpec({ fact: 3001, unit: 1 });
} catch (e) {
  if (e instanceof BlockCountExceededError && e.count === 3001 && e.maxCapacity === 3000) {
    passed++;
  }
}

// Test ForbiddenCategoryError
try {
  verifySpec({ fact: 100, unit: 10, category: "news" });
} catch (e) {
  if (e instanceof ForbiddenCategoryError && e.category === "news") {
    passed++;
  }
}

// Test GroupPartitionError
try {
  verifySpec({ fact: 100, unit: 10, groups: [{ name: "a", fact: 50 }] });
} catch (e) {
  if (e instanceof GroupPartitionError && e.sum === 50 && e.fact === 100) {
    passed++;
  }
}

// Test InvalidFactError
try {
  verifySpec({ fact: 0, unit: 10 });
} catch (e) {
  if (e instanceof InvalidFactError) {
    passed++;
  }
}

if (MAX_BLOCK_COUNT === 3000) passed++;
if (FORBIDDEN_CATEGORIES.has("news")) passed++;

console.log(JSON.stringify({ passed }));
"""
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(proc.returncode, 0, f"Node script error: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertEqual(data["passed"], 7)


if __name__ == "__main__":
    unittest.main()
