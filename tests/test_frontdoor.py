"""Tests for the front door (`engine make`, `tt_shorts.make`, `engine options`, `veasy_make`)."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import engine, make, styles


class FrontDoor(unittest.TestCase):
    def test_options_leads_with_brands_and_styles_and_advanced(self):
        o = engine.options()
        keys = list(o.keys())
        # First keys are brand, brands, styles, advanced
        self.assertEqual(keys[:4], ["brand", "brands", "styles", "advanced"])
        self.assertIn("still", o["brands"]["tbilisi-today"])
        self.assertIn("still", o["brands"]["sitech"])
        self.assertIn("still", o["styles"]["known"]["swiss-motion"])
        self.assertIn("looks", o["advanced"])
        self.assertIn("formats", o["advanced"])
        self.assertIn("scenes", o["advanced"])

        # Advanced section filtering works
        adv = engine.options(section="advanced")
        self.assertEqual(adv["section"], "advanced")
        self.assertIn("looks", adv["advanced"])

        # Backward compatibility for direct access
        self.assertIn("looks", o)
        self.assertIn("formats", o)

    def test_a_sentence_names_no_facts(self):
        # A bare sentence is never matched to a story by its words: that would film another story
        for req in ("ვარკეთილში გაზის მილის დაზიანების გამო 6400 აბონენტს გაზმომარაგება შეუწყდა",
                    "როგორ იცვლება ფასები და ინფლაცია საქართველოში", "ვიდეო ამ ამბავზე 24835"):
            intent = make.parse_intent(req)
            self.assertFalse(intent["facts_known"], req)
            self.assertFalse(intent["write"], req)
            self.assertIsNone(intent["story_path"], req)

    def test_a_story_file_or_name_is_the_story(self):
        for req in ("stories/24835.json", "ვიდეო stories/24835.json-ის მიხედვით", "bipi-draws"):
            intent = make.parse_intent(req.replace("-ის მიხედვით", ""))
            self.assertTrue(intent["facts_known"], req)
            self.assertTrue(pathlib.Path(intent["story_path"]).is_file())
        self.assertEqual(make.parse_intent("bipi-draws")["program"], "story")

    def test_a_source_ref_is_written_and_its_program_comes_from_the_source(self):
        cluster = make.parse_intent("24835")  # a bare number is a cluster id, not the demo file of that name
        self.assertTrue(cluster["write"])
        self.assertFalse(cluster["facts_known"])
        self.assertEqual(cluster["ref"], "24835")
        url = make.parse_intent("ახსენი ეს სტატია https://example.com/a")
        self.assertEqual((url["source"], url["ref"], url["program"]), ("url", "https://example.com/a", "explainer"))
        law = make.parse_intent("კონსტიტუციის მე-17 მუხლი constitution:17", source="ordo")
        self.assertEqual((law["ref"], law["program"]), ("constitution:17", "law"))
        self.assertEqual(make.parse_intent("x 1", source="sitech")["program"], "blog")

    def test_unknown_facts_are_never_defaulted(self):
        # Not even with --yes: the agent gets the question back
        res = make.make_film("გააკეთე ვიდეო ინფლაციაზე", yes=True)
        self.assertEqual(res["status"], "needs_input")
        self.assertEqual(res["questions"][0]["id"], "facts")

    def test_preview_storyboard_runs_plan_and_generates_contact_sheet(self):
        res = make.make_film(
            request="stories/24835.json",
            preview_storyboard=True,
            yes=True,
        )
        self.assertEqual(res["status"], "preview")
        self.assertEqual(res["brand"], "tbilisi-today")
        self.assertEqual(res["program"], "news")
        self.assertTrue(res.get("sheet"))
        self.assertTrue(pathlib.Path(res["sheet"]).is_file())
        self.assertTrue(res.get("questions_log"))

    def test_style_override_is_respected(self):
        res = make.make_film(
            request="stories/24835.json",
            style="swiss-motion",
            preview_storyboard=True,
            yes=True,
        )
        self.assertEqual(res["status"], "preview")
        self.assertEqual(res["style"], "swiss-motion")

    def test_queue_mode_adds_to_job_queue(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            res = make.make_film(
                request="stories/24835.json",
                queue=True,
                yes=True,
            )
            self.assertEqual(res["status"], "queued")
            self.assertTrue(res.get("job_id"))
            self.assertTrue(res.get("created"))

    def test_queue_mode_takes_a_source_ref_for_the_worker_to_write(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            res = make.make_film(request="24835", queue=True, yes=True)
            self.assertEqual(res["status"], "queued")
            self.assertEqual(res["program"], "news")


if __name__ == "__main__":
    unittest.main()
