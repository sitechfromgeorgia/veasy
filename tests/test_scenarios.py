"""Tests for Veasy Scenarios (Goal 6, tt_shorts/scenarios.py).

Covers:
  - Data loading and declarative validation against brushes and brand families
  - Bad scenario definitions refused (bad jobs, sound cues, word budgets, code expressions)
  - Program gating: 'news' program strictly refused
  - Eligibility and condition evaluation (reusing rubrics.holds grammar)
  - Fit ranking with clear 'why' explanations
  - Engine plan beat checks:
      a) Scene types match beat scene_types
      b) Word budget per beat is respected
      c) Fact gates for each beat are satisfied
      d) Early payoff check (payoff fact not spoiled before payoff beat)
      e) myth-vs-fact gate (ensures document itself makes the correction)
"""
import copy
import json
import pathlib
import unittest

from tt_shorts import catalog, scenarios

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sample_story():
    """A clean Georgian explainer story matching guess-the-number structure."""
    return {
        "id": "test-scenario-story",
        "brand": "tbilisi-today",
        "program": "explainer",
        "category": "economy",
        "date": "2026-11-06T12:00:00Z",
        "scenario": "guess-the-number",
        "sources": ["საქსტატი"],
        "narration": (
            "როგორ იცვლება წლიური ინფლაცია საქართველოში ბოლო თვეებში? "
            "ფასების ზრდის ტემპი ეტაპობრივად დასტაბილურდა რამდენიმე სექტორში. "
            "სურსათზე ფასები ოდნავ შეიცვალა და ბაზარზე სტაბილურობა შენარჩუნდა. "
            "საბოლოო მაჩვენებელი სამ მთელ რვა მეათედ პროცენტს შეადგენს. "
            "დეტალური ინფორმაცია ხელმისაწვდომია ოფიციალურ პორტალზე."
        ),
        "scenes": [
            {
                "type": "hook",
                "at": "როგორ იცვლება",
                "kicker": "ეკონომიკა",
                "lines": ["როგორ იცვლება", "წლიური ინფლაცია", "საქართველოში"]
            },
            {
                "type": "points",
                "at": "ფასების ზრდის",
                "kicker": "კონტექსტი",
                "items": ["ეტაპობრივი დასტაბილურება", "სტაბილური ტენდენცია"]
            },
            {
                "type": "bars",
                "at": "სურსათზე ფასები",
                "kicker": "მაჩვენებლები",
                "items": [{"label": "სურსათი", "value": 2}, {"label": "მომსახურება", "value": 1}]
            },
            {
                "type": "stat",
                "at": "საბოლოო მაჩვენებელი",
                "kicker": "ინფლაცია",
                "value": 3.8,
                "unit": "%",
                "label": "წლიური მაჩვენებელი",
                "em": "3.8"
            },
            {
                "type": "end",
                "at": "დეტალური ინფორმაცია"
            }
        ]
    }


class TestData(unittest.TestCase):
    def test_scenarios_load_and_validate(self):
        every = scenarios.load_all()
        self.assertIn("guess-the-number", every)
        self.assertIn("myth-vs-fact", every)
        self.assertIn("before-and-after", every)
        self.assertIn("countdown", every)

        gn = scenarios.get("guess-the-number")
        self.assertEqual(gn["title"], "Guess the Number")
        self.assertEqual(gn["label"], "გამოიცანი რიცხვი")
        self.assertEqual(len(gn["beats"]), 5)
        self.assertEqual(gn["beats"][0]["job"], "promise")
        self.assertEqual(gn["beats"][3]["job"], "payoff")

    def test_validation_catches_invalid_scenarios(self):
        good = scenarios.get("guess-the-number")

        bad_cases = [
            ({"id": "Bad_ID"}, "uppercase or underscore in id"),
            ({"title": ""}, "empty title"),
            ({"label": ""}, "empty label"),
            ({"eligible": [{"big_numbers": "x > 2"}]}, "code expression in eligible"),
            ({"eligible": [{"unknown_fact": 1}]}, "unknown fact in eligible"),
            ({"never": [{"families": ["fantasy"]}]}, "unknown family in never"),
            ({"beats": good["beats"][:2]}, "fewer than 3 beats"),
            ({"beats": [{**good["beats"][0], "job": "punchline"}] + good["beats"][1:]}, "invalid job"),
            ({"beats": [{**good["beats"][0], "scene_types": ["nonexistent_brush"]}] + good["beats"][1:]}, "unknown brush"),
            ({"beats": [{**good["beats"][0], "word_budget": [25, 10]}] + good["beats"][1:]}, "min_words > max_words"),
            ({"beats": [{**good["beats"][0], "sound": "trumpet"}] + good["beats"][1:]}, "unknown sound"),
            ({"beats": [{**good["beats"][0], "fact_gates": {"invalid_fact": 1}}] + good["beats"][1:]}, "unknown fact gate"),
            ({"pacing": {"target_words": 5, "min_seconds": 25.0, "max_seconds": 45.0}}, "target_words < 10"),
            ({"pacing": {"target_words": 80, "min_seconds": 50.0, "max_seconds": 45.0}}, "min_seconds > max_seconds"),
            ({"extra_unknown_key": True}, "unknown top-level key"),
        ]

        for patch, desc in bad_cases:
            bad_data = copy.deepcopy(good)
            bad_data.update(patch)
            name = bad_data.get("id", "guess-the-number")
            with self.assertRaises(scenarios.ScenarioError, msg=f"Should reject: {desc}"):
                scenarios.validate(name, bad_data)


class TestEligibilityAndHolds(unittest.TestCase):
    def test_holds_evaluates_conditions(self):
        sc = scenarios.get("guess-the-number")
        facts_ok = {"big_numbers": 1, "facts": 2, "deaths": False}
        self.assertTrue(scenarios.holds(sc, facts_ok, program="explainer"))

        facts_no_big = {"big_numbers": 0, "facts": 2, "deaths": False}
        self.assertFalse(scenarios.holds(sc, facts_no_big, program="explainer"))

        facts_deaths = {"big_numbers": 1, "facts": 2, "deaths": True}
        self.assertFalse(scenarios.holds(sc, facts_deaths, program="explainer"))

    def test_news_program_strictly_refused(self):
        sc = scenarios.get("guess-the-number")
        facts_ok = {"big_numbers": 1, "facts": 2, "deaths": False}
        self.assertFalse(scenarios.holds(sc, facts_ok, program="news"))
        self.assertEqual(scenarios.eligible(facts_ok, program="news"), [])

    def test_myth_vs_fact_requires_verified_correction(self):
        mvf = scenarios.get("myth-vs-fact")
        without_corr = {"verified_correction": False, "facts": 2}
        with_corr = {"verified_correction": True, "facts": 2}

        self.assertFalse(scenarios.holds(mvf, without_corr, program="explainer"))
        self.assertTrue(scenarios.holds(mvf, with_corr, program="explainer"))


class TestFitAndRanking(unittest.TestCase):
    def test_fit_ranks_fitting_scenarios(self):
        story = sample_story()
        ranked = scenarios.fit(story)
        self.assertTrue(len(ranked) >= 1)
        top = ranked[0]
        self.assertEqual(top["scenario"], "guess-the-number")
        self.assertTrue(top["score"] > 0)
        self.assertIn("why", top)
        self.assertTrue(len(top["why"]) > 0)

    def test_fit_refuses_news_program(self):
        story = sample_story()
        story["program"] = "news"
        ranked = scenarios.fit(story)
        self.assertEqual(ranked, [])


class TestCheckPlanBeats(unittest.TestCase):
    def test_check_plan_beats_passes_valid_story(self):
        story = sample_story()
        problems = scenarios.check_plan_beats(story)
        self.assertEqual(problems, [])

    def test_check_plan_beats_refuses_news_program(self):
        story = sample_story()
        story["program"] = "news"
        problems = scenarios.check_plan_beats(story)
        self.assertTrue(any("refuses scenarios" in p for p in problems))

    def test_check_plan_beats_catches_scene_type_mismatch(self):
        story = sample_story()
        # Change scene 3 (reveal) from stat to quote, which is not in ["stat"]
        story["scenes"][3]["type"] = "quote"
        story["scenes"][3]["text"] = "„ციტატა“"
        problems = scenarios.check_plan_beats(story)
        self.assertTrue(any("scene type 'quote' not in allowed types" in p for p in problems))

    def test_check_plan_beats_catches_word_budget_violation(self):
        story = sample_story()
        # Inflate scene 0 words over max_words (budget [10, 20])
        story["narration"] = (
            "როგორ იცვლება წლიური ინფლაცია საქართველოში ბოლო თვეებში ძალიან სწრაფად "
            "და მოულოდნელად როდესაც ფასები ყოველდღიურად იზრდება და მოსახლეობას უჭირს "
            "გარკვევა რეალურ ეკონომიკურ ვითარებაში? "
            + story["narration"]
        )
        problems = scenarios.check_plan_beats(story)
        self.assertTrue(any("outside budget" in p for p in problems))

    def test_check_plan_beats_catches_fact_gate_failure(self):
        story = sample_story()
        # Remove numbers from the reveal scene (requires numbers: 1)
        story["scenes"][3]["value"] = None
        story["scenes"][3].pop("value", None)
        story["scenes"][3]["em"] = "ინფლაცია"
        story["narration"] = story["narration"].replace("სამ მთელ რვა მეათედ", "სხვადასხვა")
        problems = scenarios.check_plan_beats(story)
        self.assertTrue(any("requires at least 1 numbers" in p for p in problems))

    def test_check_plan_beats_catches_early_payoff(self):
        story = sample_story()
        # Spoil "3.8" in the opening hook sentence!
        story["narration"] = "როგორ იცვლება 3.8% ინფლაცია საქართველოში? " + story["narration"]
        problems = scenarios.check_plan_beats(story)
        self.assertTrue(any("early payoff: fact '3.8' is spoken before payoff beat" in p for p in problems))

    def test_check_plan_beats_catches_unverified_myth_vs_fact(self):
        story = sample_story()
        story["scenario"] = "myth-vs-fact"
        story["doc_correction"] = False
        problems = scenarios.check_plan_beats(story)
        self.assertTrue(any("document itself does not state a correction" in p for p in problems))


class TestStoryProblems(unittest.TestCase):
    def test_story_problems_ignores_stories_without_scenario(self):
        story = sample_story()
        del story["scenario"]
        self.assertEqual(scenarios.story_problems(story), [])

    def test_story_problems_flags_unknown_scenario(self):
        story = sample_story()
        story["scenario"] = "fictional-mystery"
        problems = scenarios.story_problems(story)
        self.assertTrue(any("unknown scenario 'fictional-mystery'" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
