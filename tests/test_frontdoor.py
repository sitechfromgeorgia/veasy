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

    def test_parse_intent_classifies_all_five_program_types(self):
        # 1. News
        news_req = "ვარკეთილში გაზის მილის დაზიანების გამო 6400 აბონენტს გაზმომარაგება შეუწყდა"
        intent1 = make.parse_intent(news_req)
        self.assertEqual(intent1["program"], "news")
        self.assertEqual(intent1["brand"], "tbilisi-today")
        self.assertTrue(intent1["facts_known"])

        # 2. Explainer
        expl_req = "როგორ იცვლება ფასები და ინფლაცია საქართველოში ბოლო წლებში"
        intent2 = make.parse_intent(expl_req)
        self.assertEqual(intent2["program"], "explainer")
        self.assertEqual(intent2["brand"], "tbilisi-today")
        self.assertTrue(intent2["facts_known"])

        # 3. Law
        law_req = "საქართველოს კონსტიტუციის მე-17 მუხლი იცავს აზრის, სიტყვისა და ინფორმაციის თავისუფლებას"
        intent3 = make.parse_intent(law_req)
        self.assertEqual(intent3["program"], "law")
        self.assertEqual(intent3["source"], "ordo")
        self.assertEqual(intent3["ref"], "constitution:17")
        self.assertTrue(intent3["facts_known"])

        # 4. SiTech Blog
        blog_req = "SiTech-ის ბლოგი: როგორ იყენებენ ჰაკერები AI აგენტებს კიბერთავდასხმების ავტომატიზაციისთვის"
        intent4 = make.parse_intent(blog_req)
        self.assertEqual(intent4["program"], "blog")
        self.assertEqual(intent4["brand"], "sitech")
        self.assertTrue(intent4["facts_known"])

        # 5. Children's story
        story_req = "პატარა რობოტი ბიპი სწავლობს ხატვას და მზეს ხატავს"
        intent5 = make.parse_intent(story_req)
        self.assertEqual(intent5["program"], "story")
        self.assertEqual(intent5["brand"], "sitech")
        self.assertTrue(intent5["facts_known"])

    def test_one_round_of_questions_asks_missing_facts_when_unknown(self):
        intent = make.parse_intent("გააკეთე მოკლე ვიდეო ჩემს უცნობ პროექტზე")
        intent["facts_known"] = False
        resolved, questions, needs_input = make.ask_one_round(intent, interactive=False, yes=False)
        self.assertTrue(needs_input)
        self.assertEqual(len(questions), 3)
        self.assertEqual(questions[0]["id"], "facts")
        self.assertEqual(questions[1]["id"], "assets")
        self.assertEqual(questions[2]["id"], "preview")

    def test_preview_storyboard_runs_plan_and_generates_contact_sheet(self):
        res = make.make_film(
            request="ვარკეთილში გაზის მილის დაზიანების გამო 6400 აბონენტს გაზმომარაგება შეუწყდა",
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
            request="ვარკეთილში გაზის მილის დაზიანების გამო 6400 აბონენტს გაზმომარაგება შეუწყდა",
            style="swiss-motion",
            preview_storyboard=True,
            yes=True,
        )
        self.assertEqual(res["status"], "preview")
        self.assertEqual(res["style"], "swiss-motion")

    def test_queue_mode_adds_to_job_queue(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            res = make.make_film(
                request="ვარკეთილში გაზის მილის დაზიანების გამო 6400 აბონენტს გაზმომარაგება შეუწყდა",
                queue=True,
                yes=True,
            )
            self.assertEqual(res["status"], "queued")
            self.assertTrue(res.get("job_id"))
            self.assertTrue(res.get("created"))


if __name__ == "__main__":
    unittest.main()
