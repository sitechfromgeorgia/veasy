"""Unit tests for tt_shorts.eyes: free pixel checks, pacing metrics, and safety gates."""
import json
import pathlib
import tempfile
import unittest

import numpy as np
from PIL import Image

from tt_shorts import eyes, golden

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestEyes(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_synthetic_still(self, name: str, pattern: str = "normal") -> pathlib.Path:
        """Create a 1080x1920 test frame with specified layout pattern."""
        img = Image.new("RGB", (1080, 1920), color=(5, 8, 15))  # dark canvas #05080F
        arr = np.array(img)

        # Chrome headers and footers
        arr[80:160, 100:980] = (248, 250, 252)    # header ink
        arr[1760:1840, 100:980] = (167, 176, 189) # footer line

        if pattern == "normal":
            # Rich central content (hook/stat)
            arr[400:600, 150:900] = (248, 250, 252)
            arr[700:850, 200:800] = (248, 250, 252)
        elif pattern == "empty_middle":
            # Absolutely zero ink in central safe zone (y=248..1380)
            pass
        elif pattern == "faint":
            # Low contrast / washed out ink
            arr[400:600, 150:900] = (20, 25, 35)
        elif pattern == "hero":
            # Massive visual mass (e.g. big hero stat)
            arr[300:900, 120:960] = (248, 250, 252)
        elif pattern == "low_mass":
            # Tiny label only
            arr[500:520, 400:460] = (248, 250, 252)

        out_path = self.tmp_path / f"{name}.png"
        Image.fromarray(arr).save(out_path)
        return out_path

    # 1. same_picture_twice tests
    def test_same_picture_twice_consecutive(self):
        still_1 = self._create_synthetic_still("still_1", "normal")
        # Duplicate still
        still_2 = self.tmp_path / "still_2.png"
        still_2.write_bytes(still_1.read_bytes())

        hashes = eyes.hashes_of_stills([still_1, still_2])
        findings = eyes.same_picture_twice(hashes)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "same_picture_twice")
        self.assertFalse(findings[0]["hold"])
        self.assertIn("scenes 0 and 1 share near-identical composition", findings[0]["detail"])

    def test_same_picture_twice_different_compositions(self):
        still_1 = self._create_synthetic_still("still_1", "normal")
        still_2 = self._create_synthetic_still("still_2", "empty_middle")

        hashes = eyes.hashes_of_stills([still_1, still_2])
        findings = eyes.same_picture_twice(hashes)
        self.assertEqual(len(findings), 0)

    # 2. empty_middle tests
    def test_empty_middle_detects_dead_center(self):
        still_empty = self._create_synthetic_still("empty", "empty_middle")
        findings = eyes.empty_middle([still_empty], ["points"])
        self.assertTrue(len(findings) >= 1)
        self.assertEqual(findings[0]["rule"], "empty_middle")
        self.assertIn("empty or missing content", findings[0]["detail"])

    def test_empty_middle_passes_normal_content(self):
        still_normal = self._create_synthetic_still("normal", "normal")
        findings = eyes.empty_middle([still_normal], ["hook"])
        self.assertEqual(len(findings), 0)

    def test_empty_middle_detects_washed_out(self):
        still_faint = self._create_synthetic_still("faint", "faint")
        findings = eyes.empty_middle([still_faint], ["card"])
        self.assertTrue(len(findings) >= 1)
        self.assertEqual(findings[0]["rule"], "empty_middle")

    # 3. no_hero_frame tests
    def test_no_hero_frame_warns_on_uniform_low_mass(self):
        stills = [self._create_synthetic_still(f"low_{i}", "low_mass") for i in range(4)]
        story = {
            "id": 9999,
            "scenes": [{"type": "points"} for _ in range(4)],
        }
        findings = eyes.no_hero_frame(stills, story)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "no_hero_frame")
        self.assertIn("lacks a dominant hero anchor moment", findings[0]["detail"])

    def test_no_hero_frame_passes_with_hero_scene(self):
        stills = [
            self._create_synthetic_still("s0", "hero"),
            self._create_synthetic_still("s1", "low_mass"),
            self._create_synthetic_still("s2", "low_mass"),
        ]
        story = {
            "id": 9999,
            "scenes": [{"type": "stat", "value": 145000}, {"type": "points"}, {"type": "points"}],
        }
        findings = eyes.no_hero_frame(stills, story)
        self.assertEqual(len(findings), 0)

    # 4. metronome_cuts tests
    def test_metronome_cuts_warns_on_identical_durations(self):
        # 5 scenes each exactly 3.0s (std dev = 0.0)
        durations = [3.0, 3.0, 3.0, 3.0, 3.0]
        findings = eyes.metronome_cuts(durations)
        self.assertTrue(len(findings) >= 1)
        self.assertEqual(findings[0]["rule"], "metronome_cuts")
        self.assertIn("robotic metronome pacing", findings[0]["detail"])

    def test_metronome_cuts_passes_varied_rhythm(self):
        durations = [2.2, 4.5, 1.8, 3.6, 2.8]
        findings = eyes.metronome_cuts(durations)
        self.assertEqual(len(findings), 0)

    # 5. spoken_redundancy tests
    def test_spoken_redundancy_catches_verbatim_copy(self):
        story = {
            "id": 1001,
            "scenes": [
                {
                    "type": "hook",
                    "lines": ["საქართველოში ახალი კანონი მიიღეს"],
                },
                {
                    "type": "points",
                    "narration": "პარლამენტმა ახალი საგადასახადო შეღავათები დაამტკიცა მცირე ბიზნესისთვის",
                    "items": ["პარლამენტმა ახალი საგადასახადო შეღავათები დაამტკიცა მცირე ბიზნესისთვის"],
                },
            ],
        }
        findings = eyes.spoken_redundancy(story)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "spoken_redundancy")
        self.assertEqual(findings[0]["scene"], 1)
        self.assertIn("verbatim repeats spoken narration", findings[0]["detail"])

    def test_spoken_redundancy_exempts_quotes_and_short_hooks(self):
        story = {
            "id": 1002,
            "scenes": [
                {
                    "type": "quote",
                    "text": "ეს გადაწყვეტილება ისტორიულია ჩვენი ქვეყნისთვის",
                    "by": "მინისტრი",
                    "narration": "ეს გადაწყვეტილება ისტორიულია ჩვენი ქვეყნისთვის განაცხადა მინისტრმა",
                },
            ],
        }
        findings = eyes.spoken_redundancy(story)
        self.assertEqual(len(findings), 0)

    # 6. Safety holds tests
    def test_reading_time_holds_flags_unreadable_text(self):
        # Heavy text with very short duration
        story = {
            "id": 1003,
            "durationInFrames": 60,  # 2.0s
            "scenes": [
                {
                    "type": "points",
                    "duration": 60,
                    "from": 0,
                    "items": [
                        "ეს არის ძალიან გრძელი წინადადება რომელიც შეიცავს ოცზე მეტ სიტყვას და შეუძლებელია მისი წაკითხვა ერთ წამში"
                    ],
                }
            ],
        }
        findings = eyes.reading_time_holds(story)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(findings[0]["hold"])
        self.assertEqual(findings[0]["rule"], "read")

    # 7. Composite check_eyes test
    def test_check_eyes_composite(self):
        still_1 = self._create_synthetic_still("c1", "normal")
        still_2 = self._create_synthetic_still("c2", "normal")
        story = {
            "id": 2001,
            "scenes": [
                {"type": "hook", "lines": ["მოკლე სათაური"]},
                {"type": "stat", "value": "1200", "label": "აბონენტი", "narration": "ათას ორასზე მეტი აბონენტი დარჩა"},
            ],
        }
        rep = eyes.check_eyes(story, stills=[still_1, still_2])
        self.assertIn("findings", rep)
        self.assertIn("holds", rep)
        self.assertIn("warnings", rep)
        self.assertIn("metrics", rep)
        self.assertEqual(rep["metrics"]["stills_checked"], 2)


if __name__ == "__main__":
    unittest.main()
