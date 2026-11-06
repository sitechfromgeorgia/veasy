"""Tests for tt_shorts/review.py: Review Packet Builder for Veasy's film-eyes lane."""
import json
import os
from unittest import mock
import pathlib
import unittest

from tt_shorts import formats, review

ROOT = pathlib.Path(__file__).resolve().parent.parent


class NoteFormatTest(unittest.TestCase):
    def test_format_finding_matches_specification(self):
        note = review.format_finding(
            time_s=4.2,
            where="scene 1 (stat)",
            problem="numbers match previous frame",
            change="vary card layout or consolidate",
        )
        self.assertEqual(
            note,
            "t=4.2s · scene 1 (stat) · numbers match previous frame -> vary card layout or consolidate",
        )

    def test_format_examples_from_user_requirements(self):
        # Example 1
        n1 = review.format_finding(2.1, "scene 1 (stat)", "numbers match previous frame", "vary card layout or consolidate")
        self.assertEqual(n1, "t=2.1s · scene 1 (stat) · numbers match previous frame -> vary card layout or consolidate")

        # Example 2
        n2 = review.format_finding(6.8, "scene 3 (points)", "text extends into social rail (x=960, y=1240)", "trim line or reduce font size")
        self.assertEqual(n2, "t=6.8s · scene 3 (points) · text extends into social rail (x=960, y=1240) -> trim line or reduce font size")

        # Example 3
        n3 = review.format_finding(10.5, "scene 4 (quote)", "text needs 3.2s but scene ends at 1.8s", "expand narration or trim quote")
        self.assertEqual(n3, "t=10.5s · scene 4 (quote) · text needs 3.2s but scene ends at 1.8s -> expand narration or trim quote")

    def test_parse_finding_roundtrip(self):
        original = "t=6.8s · scene 3 (points) · text extends into social rail (x=960, y=1240) -> trim line or reduce font size"
        parsed = review.parse_finding(original)
        self.assertEqual(parsed["time"], 6.8)
        self.assertEqual(parsed["where"], "scene 3 (points)")
        self.assertEqual(parsed["problem"], "text extends into social rail (x=960, y=1240)")
        self.assertEqual(parsed["change"], "trim line or reduce font size")
        self.assertEqual(parsed["formatted"], original)

    def test_parse_finding_with_unicode_arrow(self):
        line = "t=10.5s · scene 4 (quote) · text needs 3.2s but scene ends at 1.8s → expand narration or trim quote"
        parsed = review.parse_finding(line)
        self.assertEqual(parsed["time"], 10.5)
        self.assertEqual(parsed["where"], "scene 4 (quote)")
        self.assertEqual(parsed["change"], "expand narration or trim quote")
        # Canonical formatted string uses ->
        self.assertIn("->", parsed["formatted"])

    def test_parse_invalid_finding_raises_value_error(self):
        with self.assertRaises(ValueError):
            review.parse_finding("scene 1 has a bug")
        with self.assertRaises(ValueError):
            review.parse_finding("t=2.1s - scene 1 - problem")


class RawConversionTest(unittest.TestCase):
    def test_convert_motion_read_finding(self):
        raw = {
            "rule": "read",
            "scene": 4,
            "detail": "scene 4 (quote): „დეტალები“ is readable for 1.8 s, its 12 words need 3.2 s",
            "hold": True,
        }
        scenes = [
            {"scene": 0, "type": "hook", "start": 0.0},
            {"scene": 1, "type": "stat", "start": 3.0},
            {"scene": 2, "type": "timeline", "start": 5.5},
            {"scene": 3, "type": "points", "start": 8.0},
            {"scene": 4, "type": "quote", "start": 10.5},
        ]
        note = review.convert_motion_finding(raw, scenes)
        self.assertEqual(note["priority"], "P0")
        self.assertEqual(note["time"], 10.5)
        self.assertIn("scene 4 (quote)", note["where"])
        self.assertIn("needs 3.2s but scene ends at 1.8s", note["problem"])
        self.assertEqual(note["change"], "expand narration or trim quote")
        self.assertEqual(
            note["formatted"],
            "t=10.5s · scene 4 (quote) · text needs 3.2s but scene ends at 1.8s -> expand narration or trim quote",
        )

    def test_convert_probe_rail_issue(self):
        issue = {
            "rule": "rail",
            "region": "scene",
            "scene": 3,
            "type": "points",
            "frame": 204,  # 204 / 30 = 6.8s
            "detail": "text „ქართული მედია“ (x=960.0, y=1240.0) right of rail (max 940 below y=1100)",
        }
        note = review.convert_probe_issue(issue)
        self.assertEqual(note["priority"], "P0")
        self.assertEqual(note["time"], 6.8)
        self.assertEqual(note["where"], "scene 3 (points)")
        self.assertEqual(note["problem"], "text extends into social rail (x=960, y=1240)")
        self.assertEqual(note["change"], "trim line or reduce font size")
        self.assertEqual(
            note["formatted"],
            "t=6.8s · scene 3 (points) · text extends into social rail (x=960, y=1240) -> trim line or reduce font size",
        )

    def test_convert_raw_string(self):
        s = "t=2.1s · scene 1 (stat) · numbers match previous frame -> vary card layout or consolidate"
        note = review.convert_raw_string(s)
        self.assertEqual(note["time"], 2.1)
        self.assertEqual(note["where"], "scene 1 (stat)")
        self.assertEqual(note["problem"], "numbers match previous frame")
        self.assertEqual(note["change"], "vary card layout or consolidate")


class ZeroCodeLeakageContractTest(unittest.TestCase):
    def test_assert_zero_code_leakage_blocks_html_files(self):
        bad_packet = {
            "sheets": {"index_file": "compositions/scene1.html"},
        }
        with self.assertRaises(review.CodeLeakageError) as ctx:
            review.assert_zero_code_leakage(bad_packet)
        self.assertIn(".html", str(ctx.exception))

    def test_assert_zero_code_leakage_blocks_tsx_files(self):
        bad_packet = {
            "component": "remotion/src/scenes/stat.tsx",
        }
        with self.assertRaises(review.CodeLeakageError) as ctx:
            review.assert_zero_code_leakage(bad_packet)
        self.assertIn(".tsx", str(ctx.exception))

    def test_assert_zero_code_leakage_blocks_script_tags(self):
        bad_packet = {
            "spec": {"goal": "<script>alert('pwn')</script>"},
        }
        with self.assertRaises(review.CodeLeakageError) as ctx:
            review.assert_zero_code_leakage(bad_packet)
        self.assertIn("Code pattern detected", str(ctx.exception))

    def test_assert_zero_code_leakage_blocks_dom_templates(self):
        bad_packet = {
            "spec": {"template": "<template id='s1'><div class='box'></div></template>"},
        }
        with self.assertRaises(review.CodeLeakageError):
            review.assert_zero_code_leakage(bad_packet)

    def test_assert_zero_code_leakage_blocks_javascript_functions(self):
        bad_packet = {
            "motion": {"code": "function animate() { gsap.to('#box', {x: 100}); }"},
        }
        with self.assertRaises(review.CodeLeakageError):
            review.assert_zero_code_leakage(bad_packet)

    def test_valid_visual_spec_passes(self):
        good_packet = {
            "packet_version": "1.0",
            "created_at": "2026-11-06T19:30:00Z",
            "film_id": "24835",
            "brand": "tbilisi-today",
            "engine": "remotion",
            "round": 1,
            "spec": {
                "goal": "Explain gas shutoff schedule in Varketili.",
                "output": {"engine": "remotion", "width": 1080, "height": 1920, "fps": 30},
                "time": {"seconds": 24.5, "frames": 735, "bpm": None},
                "look": {"theme": "dark", "canvas": "#171817", "ink": "#F1EDE4", "accent": "#FF792E"},
                "shots": [{"index": 0, "type": "hook", "hero_move": "Hook settles typography"}],
                "banned": ["No floating particles", "No dark voids"],
            },
            "sheets": {
                "contact_sheet": "renders/tbilisi-today/2026-11-06/24835-news.plan.jpg",
                "review_beats": None,
                "review_phone": None,
                "review_seams": [],
                "stills": [{"scene": 0, "type": "hook", "time": 0.0, "path": "stills/scene-0.png"}],
            },
            "timeline": {"duration_seconds": 24.5, "beats": []},
            "reading_load": {"overall_load": 0.82, "scenes": []},
            "findings": {
                "summary": {"p0_count": 0, "p1_count": 1, "p2_count": 0, "verdict": "fix"},
                "notes": [{
                    "priority": "P1",
                    "time": 2.1,
                    "where": "scene 1 (stat)",
                    "problem": "numbers match previous frame",
                    "change": "vary card layout or consolidate",
                    "formatted": "t=2.1s · scene 1 (stat) · numbers match previous frame -> vary card layout or consolidate",
                }],
            },
            "comparison": {"has_comparison": False},
        }
        is_valid, errors = review.verify_contract_adherence(good_packet)
        self.assertTrue(is_valid, errors)
        self.assertEqual(errors, [])


class ReviewPacketBuilderTest(unittest.TestCase):
    def test_build_review_packet_on_fixture_story(self):
        story = ROOT / "stories" / "24835.json"
        packet = review.build_review_packet(story, fmt_name="news", round_num=1)

        # Basic packet structure
        self.assertEqual(packet["packet_version"], "1.0")
        self.assertEqual(packet["film_id"], "24835")
        self.assertEqual(packet["brand"], "tbilisi-today")
        self.assertEqual(packet["round"], 1)

        # Spec checks (contract adherence: no code)
        self.assertIn("goal", packet["spec"])
        self.assertIn("look", packet["spec"])
        self.assertIn("banned", packet["spec"])
        self.assertIn("shots", packet["spec"])

        # Timeline and reading load
        self.assertGreater(packet["timeline"]["duration_seconds"], 15.0)
        self.assertGreaterEqual(len(packet["timeline"]["beats"]), 5)
        self.assertGreater(packet["reading_load"]["overall_load"], 0.0)

        # Findings structure
        self.assertIn("summary", packet["findings"])
        self.assertIn("notes", packet["findings"])

        # Render Markdown summary
        md = review.render_review_markdown(packet)
        self.assertIn("# Review Packet: tbilisi-today · Film #24835", md)
        self.assertIn("Visual Review Sheets", md)
        self.assertIn("Film Spec (Director's Contract)", md)
        self.assertIn("Beat Timeline & Reading Load", md)
        self.assertIn("Review Notes & Prescribed Changes", md)


class ComparisonRepresentationTest(unittest.TestCase):
    def test_before_and_after_comparison(self):
        # Round 1 packet with a P0 and a P1
        r1_packet = {
            "round": 1,
            "sheets": {"contact_sheet": "out/round1.plan.jpg", "review_phone": "out/round1-phone.jpg"},
            "reading_load": {
                "overall_load": 1.12,
                "scenes": [
                    {"scene": 0, "type": "hook", "duration_s": 3.0, "words": 6, "words_per_second": 2.0, "load": 0.8, "status": "pass"},
                    {"scene": 3, "type": "points", "duration_s": 2.0, "words": 10, "words_per_second": 5.0, "load": 1.4, "status": "overloaded"},
                ],
            },
            "findings": {
                "summary": {"p0_count": 1, "p1_count": 1, "p2_count": 0, "verdict": "fix"},
                "notes": [
                    {
                        "priority": "P0",
                        "time": 6.8,
                        "where": "scene 3 (points)",
                        "problem": "text extends into social rail (x=960, y=1240)",
                        "change": "trim line or reduce font size",
                        "formatted": "t=6.8s · scene 3 (points) · text extends into social rail (x=960, y=1240) -> trim line or reduce font size",
                    },
                    {
                        "priority": "P1",
                        "time": 2.1,
                        "where": "scene 1 (stat)",
                        "problem": "numbers match previous frame",
                        "change": "vary card layout or consolidate",
                        "formatted": "t=2.1s · scene 1 (stat) · numbers match previous frame -> vary card layout or consolidate",
                    },
                ],
            },
        }

        # Round 2 packet: P0 resolved, P1 persists
        r2_packet = {
            "round": 2,
            "sheets": {"contact_sheet": "out/round2.plan.jpg", "review_phone": "out/round2-phone.jpg"},
            "reading_load": {
                "overall_load": 0.85,
                "scenes": [
                    {"scene": 0, "type": "hook", "duration_s": 3.0, "words": 6, "words_per_second": 2.0, "load": 0.8, "status": "pass"},
                    {"scene": 3, "type": "points", "duration_s": 3.5, "words": 8, "words_per_second": 2.3, "load": 0.85, "status": "pass"},
                ],
            },
            "findings": {
                "summary": {"p0_count": 0, "p1_count": 1, "p2_count": 0, "verdict": "fix"},
                "notes": [
                    {
                        "priority": "P1",
                        "time": 2.1,
                        "where": "scene 1 (stat)",
                        "problem": "numbers match previous frame",
                        "change": "vary card layout or consolidate",
                        "formatted": "t=2.1s · scene 1 (stat) · numbers match previous frame -> vary card layout or consolidate",
                    },
                ],
            },
        }

        comparison = review.compare_review_packets(r1_packet, r2_packet)
        self.assertTrue(comparison["has_comparison"])
        self.assertEqual(comparison["previous_round"], 1)
        self.assertEqual(comparison["current_round"], 2)
        self.assertEqual(comparison["verdict"], "improved")

        # P0 note is in resolved_notes
        resolved = comparison["resolved_notes"]
        self.assertEqual(len(resolved), 1)
        self.assertIn("social rail", resolved[0]["problem"])

        # P1 note is in persisting_notes
        persisting = comparison["persisting_notes"]
        self.assertEqual(len(persisting), 1)
        self.assertIn("numbers match", persisting[0]["problem"])

        # Sheet diff is tracked
        self.assertEqual(comparison["sheets"]["before_contact_sheet"], "out/round1.plan.jpg")
        self.assertEqual(comparison["sheets"]["after_contact_sheet"], "out/round2.plan.jpg")

        # Load delta is tracked
        self.assertAlmostEqual(comparison["load_deltas"]["3"]["diff"], -0.55)

        # Markdown rendering with comparison
        r2_full = {
            "packet_version": "1.0",
            "created_at": "2026-11-06T19:35:00Z",
            "film_id": "24835",
            "brand": "tbilisi-today",
            "engine": "remotion",
            "round": 2,
            "spec": {
                "goal": "Explain gas shutoff schedule in Varketili.",
                "output": {"engine": "remotion", "width": 1080, "height": 1920, "fps": 30},
                "time": {"seconds": 24.5, "frames": 735, "bpm": None},
                "look": {"theme": "dark", "canvas": "#171817", "ink": "#F1EDE4", "accent": "#FF792E"},
                "shots": [{"index": 0, "type": "hook", "hero_move": "Hook settles typography"}],
                "banned": ["No floating particles", "No dark voids"],
            },
            "sheets": r2_packet["sheets"],
            "timeline": {"duration_seconds": 24.5, "beats": []},
            "reading_load": r2_packet["reading_load"],
            "findings": r2_packet["findings"],
            "comparison": comparison,
        }
        md = review.render_review_markdown(r2_full)
        self.assertIn("Before-and-After Comparison (Round 1 -> Round 2)", md)
        self.assertIn("Resolved Findings (1)", md)
        self.assertIn("social rail", md)
        self.assertIn("Before Sheet", md)


class ReviewFactsDiffTest(unittest.TestCase):
    def setUp(self):
        self.story = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))

    def test_facts_diff_identical(self):
        diff = review.facts_diff(self.story, self.story)
        self.assertEqual(diff, [])

    def test_facts_diff_number_changed(self):
        import copy
        modified = copy.deepcopy(self.story)
        # Change 6400 to 6500 in stat scene
        for sc in modified["scenes"]:
            if sc.get("type") == "stat":
                sc["value"] = 6500
        diff = review.facts_diff(self.story, modified)
        self.assertTrue(any("quantities/numbers mismatch" in d for d in diff))

    def test_facts_diff_date_changed(self):
        import copy
        modified = copy.deepcopy(self.story)
        modified["date"] = "2026-11-05T14:22:16Z"
        diff = review.facts_diff(self.story, modified)
        self.assertTrue(any("dates mismatch" in d for d in diff))

    def test_facts_diff_quote_changed(self):
        import copy
        modified = copy.deepcopy(self.story)
        modified["narration"] = modified["narration"].replace("„თბილისი ენერჯის“", "„ენერჯი კორპის“")
        diff = review.facts_diff(self.story, modified)
        self.assertTrue(any("quotes mismatch" in d for d in diff))

    def test_facts_diff_proper_name_changed(self):
        import copy
        modified = copy.deepcopy(self.story)
        modified["narration"] = modified["narration"].replace("ვარკეთილსა", "საბურთალოს")
        diff = review.facts_diff(self.story, modified)
        self.assertTrue(any("proper names mismatch" in d or "dates mismatch" in d for d in diff))

    def test_facts_diff_sources_changed(self):
        import copy
        modified = copy.deepcopy(self.story)
        modified["sources"] = ["ახალი წყარო"]
        diff = review.facts_diff(self.story, modified)
        self.assertTrue(any("sources mismatch" in d for d in diff))

    def test_facts_diff_cluster_id_changed(self):
        import copy
        modified = copy.deepcopy(self.story)
        modified["id"] = 99999
        diff = review.facts_diff(self.story, modified)
        self.assertTrue(any("story id changed" in d for d in diff))

    def test_allowed_line_split_preserves_facts(self):
        import copy
        modified = copy.deepcopy(self.story)
        hook = modified["scenes"][0]
        hook["lines"] = ["ვარკეთილსა და ვაზისუბანში", "გაზი შეწყდება"]
        diff = review.facts_diff(self.story, modified)
        self.assertEqual(diff, [])


class ReviewLoopTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from unittest import mock
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()
        self.story = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def test_review_story_24835_baseline(self):
        res = review.review_story(self.story, rounds=2)
        self.assertIn(res["status"], ("passed", "fixed"))
        self.assertEqual(res["holds"], [])
        self.assertEqual(res["facts_diff"], [])

    def test_review_story_repairs_duplicate_scenes(self):
        import copy
        story = copy.deepcopy(self.story)
        story["narration"] = story["narration"].replace(
            "მისამართების სრული სია ბმულზეა.",
            "მისამართების სრული სია ბმულზეა. აბონენტებს ურჩევენ წინასწარ მოამზადონ წყალი და თბილი ტანსაცმელი. "
            "ამასთან მომსახურების ცენტრი ღამითაც უპასუხებს ყველა ზარს და დაგეხმარებათ.",
        )
        story["scenes"].insert(4, {
            "type": "points",
            "at": "მისამართების სრული",
            "items": ["პირველი დეტალი", "მეორე დეტალი"]
        })
        story["scenes"].insert(5, {
            "type": "points",
            "at": "აბონენტებს ურჩევენ წინასწარ",
            "items": ["მესამე დეტალი", "მეოთხე დეტალი"]
        })
        res = review.review_story(story, rounds=2)
        self.assertIn(res["status"], ("fixed", "passed"))
        self.assertEqual(res["holds"], [])
        self.assertEqual(res["facts_diff"], [])
        scene_types = [s["type"] for s in res["story"]["scenes"]]
        self.assertFalse(any(a == b == "points" for a, b in zip(scene_types, scene_types[1:])))

    def test_review_story_cap_enforcement(self):
        import copy
        story = copy.deepcopy(self.story)
        story["scenes"][1]["at"] = "არარსებული ფრაზა ნარაციაში"
        res = review.review_story(story, rounds=2, max_machine_rounds=2)
        self.assertEqual(res["status"], "held")
        self.assertTrue(res["holds"])
        self.assertLessEqual(res["machine_rounds"], 2)


if __name__ == "__main__":
    unittest.main()


class SeededDefectTest(unittest.TestCase):
    """Done-when 1: 12 seeded-broken stories sit in tests/fixtures/review/ and every one is caught by its own rule."""

    FIX = sorted((ROOT / "tests" / "fixtures" / "review").glob("defect_*.json"))

    def setUp(self):
        import tempfile
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def test_twelve_fixtures(self):
        self.assertEqual(len(self.FIX), 12)
        self.assertEqual(sorted({p.name[7:9] for p in self.FIX}), [f"{i:02d}" for i in range(1, 13)])

    def test_every_defect_is_caught_by_its_own_rule(self):
        import tempfile
        missed = []
        for path in self.FIX:
            story = json.loads(path.read_text(encoding="utf-8"))
            with tempfile.TemporaryDirectory() as tmp:
                got = review.detect(story, tmp)
            want = story["defect"]["catch"]
            if want not in got["rules"]:
                missed.append((path.name, want, got["rules"]))
            if story["defect"]["gate"] == "hold":
                self.assertTrue(got["holds"], path.name)
            else:
                self.assertFalse(got["holds"], f"{path.name} is a warning-only defect but held: {got['holds']}")
        self.assertEqual(missed, [])
