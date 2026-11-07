"""Tests for Veasy scenarios (tt_shorts/scenarios.py, scenarios/*.json, stories/scenario-*.json).

  - the data: 24 scenarios validate; a bad definition of each kind is refused
  - eligibility is declarative (no code strings); news refuses every scenario; myth-vs-fact is gated
  - fit ranks the plots a story's facts allow, with the reason
  - the free checks at plan: beat order and brushes, word budgets, fact gates, an early payoff
  - every scenario has a Georgian demo story that passes `check` and its own beats
"""
import copy
import json
import pathlib
import unittest

from tt_shorts import engine, scenarios

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORIES = ROOT / "stories"


def demo(name="guess-the-number"):
    return json.loads((STORIES / f"scenario-{name}.json").read_text(encoding="utf-8"))


class TestData(unittest.TestCase):
    def test_there_are_24_scenarios_and_all_validate(self):
        every = scenarios.load_all()
        self.assertEqual(len(every), 24)
        for k, sc in every.items():
            self.assertEqual(sc["id"], k)
            self.assertTrue({b["job"] for b in sc["beats"]} & {"payoff", "turn"} or sc["id"] == "cold-open", k)
            self.assertEqual(sc["beats"][-1]["scene_types"], ["end"], k)  # the end card carries the call to action

    def test_each_plot_has_its_own_order_of_jobs(self):
        orders = {tuple(b["job"] for b in sc["beats"]) for sc in scenarios.load_all().values()}
        self.assertGreaterEqual(len(orders), 8)  # many scenarios share a few job orders, never all one

    def test_sounds_are_synthesized_cues_only(self):
        for sc in scenarios.load_all().values():
            for b in sc["beats"]:
                self.assertIn(b["sound"], scenarios.SOUNDS + (None,))

    def test_validation_catches_invalid_scenarios(self):
        good = scenarios.get("guess-the-number")
        first = good["beats"][0]
        bad_cases = [
            ({"id": "Bad_ID"}, "uppercase or underscore in id"),
            ({"title": ""}, "empty title"),
            ({"label": ""}, "empty label"),
            ({"eligible": [{"big_numbers": "x > 2"}]}, "code expression in eligible"),
            ({"eligible": [{"unknown_fact": 1}]}, "unknown fact in eligible"),
            ({"never": [{"families": ["fantasy"]}]}, "unknown family in never"),
            ({"beats": good["beats"][:2]}, "fewer than 3 beats"),
            ({"beats": [{**first, "job": "punchline"}] + good["beats"][1:]}, "invalid job"),
            ({"beats": [{**first, "scene_types": ["nonexistent_brush"]}] + good["beats"][1:]}, "unknown brush"),
            ({"beats": [{**first, "word_budget": [25, 10]}] + good["beats"][1:]}, "min_words > max_words"),
            ({"beats": [{**first, "sound": "trumpet"}] + good["beats"][1:]}, "unknown sound"),
            ({"beats": [{**first, "fact_gates": {"invalid_fact": 1}}] + good["beats"][1:]}, "unknown fact gate"),
            ({"pacing": {"target_words": 5, "min_seconds": 25.0, "max_seconds": 45.0}}, "target_words < 10"),
            ({"pacing": {"target_words": 80, "min_seconds": 50.0, "max_seconds": 45.0}}, "min_seconds > max_seconds"),
            ({"prefers": {"numbers": 9}}, "weight over 3"),
            ({"prefers": {"mood": 1}}, "unknown preferred fact"),
            ({"extra_unknown_key": True}, "unknown top-level key"),
        ]
        for patch, desc in bad_cases:
            bad = {**copy.deepcopy(good), **patch}
            with self.assertRaises(scenarios.ScenarioError, msg=f"should reject: {desc}"):
                scenarios.validate(bad.get("id", "guess-the-number"), bad)


class TestEligibility(unittest.TestCase):
    def test_holds_evaluates_conditions(self):
        sc = scenarios.get("guess-the-number")
        self.assertTrue(scenarios.holds(sc, {"big_numbers": 1, "facts": 2}))
        self.assertFalse(scenarios.holds(sc, {"big_numbers": 0, "facts": 2}))
        self.assertFalse(scenarios.holds(sc, {"big_numbers": 1, "facts": 2, "deaths": True}))

    def test_news_refuses_every_scenario(self):
        facts = {k: 9 for k in scenarios.FACTS}
        for sc in scenarios.load_all().values():
            self.assertFalse(scenarios.holds(sc, {**facts, "verified_correction": True}, program="news"), sc["id"])
        self.assertEqual(scenarios.eligible(facts, program="news"), [])

    def test_news_story_with_a_scenario_is_a_problem(self):
        story = demo()
        del story["program"]  # a story with no program is news
        self.assertTrue(any("refuses scenarios" in p for p in scenarios.story_problems(story)))
        self.assertTrue(any("refuses scenarios" in p for p in engine.check_story(story)))
        self.assertEqual(scenarios.fit(story), [])
        story["program"] = "news"
        self.assertTrue(any("refuses scenarios" in p for p in scenarios.story_problems(story)))

    def test_code_built_and_fiction_programs_take_none(self):
        for prog in ("digest", "story"):
            story = demo()
            story["program"] = prog
            self.assertTrue(any("refuses scenarios" in p for p in scenarios.story_problems(story)), prog)
            self.assertEqual(scenarios.fit(story), [])
            self.assertFalse(scenarios.holds(scenarios.get("countdown"), {"quantities": 9, "facts": 9}, program=prog))

    def test_news_stamp_is_refused(self):
        story = demo()
        story["program"] = "news"
        with self.assertRaises(scenarios.ScenarioError):
            scenarios.stamp(story, "guess-the-number")

    def test_myth_vs_fact_is_gated(self):
        mvf = scenarios.get("myth-vs-fact")
        self.assertFalse(scenarios.holds(mvf, {"verified_correction": False, "facts": 2}))
        self.assertTrue(scenarios.holds(mvf, {"verified_correction": True, "facts": 2}))
        facts = {k: 9 for k in scenarios.FACTS}
        self.assertNotIn("myth-vs-fact", scenarios.eligible({**facts, "verified_correction": False}))
        self.assertIn("myth-vs-fact", scenarios.eligible({**facts, "verified_correction": True}))

    def test_myth_vs_fact_refused_unless_the_document_corrects(self):
        story = demo("myth-vs-fact")
        self.assertEqual(scenarios.story_problems(story), [])
        story = demo("guess-the-number")
        story["scenario"] = "myth-vs-fact"  # a plot that needs a correction the story does not have
        self.assertTrue(any("does not state a correction" in p for p in scenarios.check_plan_beats(story)))

    def test_every_scenario_is_eligible_for_its_own_demo(self):
        for name, sc in scenarios.load_all().items():
            story = demo(name)
            facts = scenarios.story_facts(story)
            self.assertTrue(scenarios.holds(sc, facts, program="explainer"), f"{name}: {facts}")


class TestFit(unittest.TestCase):
    def test_fit_ranks_with_a_reason(self):
        ranked = scenarios.fit(demo())
        self.assertGreaterEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["scenario"], "guess-the-number")
        for r in ranked:
            self.assertTrue(r["why"])
            self.assertGreater(r["score"], 0)
        self.assertEqual(ranked, sorted(ranked, key=lambda r: (-r["score"], r["scenario"])))

    def test_length_moves_the_ranking(self):
        short = {r["scenario"]: r["score"] for r in scenarios.fit(demo(), seconds=30)}
        far = {r["scenario"]: r["score"] for r in scenarios.fit(demo(), seconds=300)}
        self.assertGreater(short["guess-the-number"], far["guess-the-number"])

    def test_parse_length(self):
        self.assertEqual(scenarios.parse_length("45s"), 45.0)
        self.assertEqual(scenarios.parse_length(40), 40.0)
        self.assertEqual(scenarios.parse_length("short"), 22.0)
        self.assertEqual(scenarios.parse_length("long"), 52.0)
        self.assertIsNone(scenarios.parse_length(None))
        with self.assertRaises(scenarios.ScenarioError):
            scenarios.parse_length("soon")

    def test_brief_names_every_beat(self):
        sc = scenarios.get("false-lead")
        block = scenarios.brief_block(sc)
        for b in sc["beats"]:
            self.assertIn(b["id"], block)
        self.assertIn("NOT said", block)


class TestPlanChecks(unittest.TestCase):
    def test_a_good_story_passes(self):
        self.assertEqual(scenarios.check_plan_beats(demo()), [])

    def test_scene_type_mismatch(self):
        story = demo()
        story["scenes"][3] = {"type": "quote", "at": story["scenes"][3]["at"], "kicker": "x", "text": "„ა“", "by": "ბ"}
        self.assertTrue(any("scene type 'quote' not in allowed types" in p for p in scenarios.check_plan_beats(story)))

    def test_scene_count_must_match_beats(self):
        story = demo()
        del story["scenes"][1]
        self.assertTrue(any("requires 5 beats" in p for p in scenarios.check_plan_beats(story)))

    def test_word_budget(self):
        story = demo()
        story["narration"] = story["narration"].replace("ჰყავს მას?", "ძალიან " * 20 + "ჰყავს მას?")
        self.assertTrue(any("outside budget" in p for p in scenarios.check_plan_beats(story)))

    def test_an_anchor_not_in_the_narration(self):
        story = demo()
        story["scenes"][2]["at"] = "ასეთი სიტყვები არ არის"
        self.assertTrue(any("anchor not in narration" in p for p in scenarios.check_plan_beats(story)))

    def test_fact_gate(self):
        story = demo()
        reveal = story["scenes"][3]
        reveal.pop("value")
        reveal["label"] = "მკითხველი"
        reveal["em"] = "მკითხველი"
        story["narration"] = story["narration"].replace("18 600", "ბევრმა")
        self.assertTrue(any("requires at least 1 numbers" in p for p in scenarios.check_plan_beats(story)))

    def test_early_payoff(self):
        story = demo()
        story["narration"] = story["narration"].replace("რამდენი მკითხველი ჰყავს მას?", "18 600 მკითხველი ჰყავს მას?")
        self.assertTrue(any("early payoff" in p for p in scenarios.check_plan_beats(story)))

    def test_early_payoff_spelled_with_groups(self):
        story = demo()
        story["narration"] = story["narration"].replace("ფონდში 240 000", "ფონდში 18600")
        self.assertTrue(any("early payoff" in p for p in scenarios.check_plan_beats(story)))

    def test_unknown_scenario(self):
        story = demo()
        story["scenario"] = "fictional-mystery"
        self.assertTrue(any("unknown scenario 'fictional-mystery'" in p for p in scenarios.story_problems(story)))

    def test_story_without_a_scenario_is_untouched(self):
        story = demo()
        del story["scenario"]
        self.assertEqual(scenarios.story_problems(story), [])


class TestDemoStories(unittest.TestCase):
    def test_every_scenario_has_a_demo_that_passes_check_and_its_beats(self):
        for name in scenarios.names():
            path = STORIES / f"scenario-{name}.json"
            self.assertTrue(path.exists(), f"missing {path.name}")
            story = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(story["scenario"], name)
            self.assertEqual(story["program"], "explainer")
            self.assertEqual(engine.check_story(story), [], name)
            self.assertEqual(scenarios.check_plan_beats(story), [], name)


class TestEngineWiring(unittest.TestCase):
    def test_writer_never_owns_the_scenario(self):
        from tt_shorts import writer
        self.assertIn("scenario", writer.OWNED)
        story = {"scenario": "countdown", "rubric": "number"}
        writer._drop_owned(story)
        self.assertNotIn("scenario", story)

    def test_options_list_the_scenarios(self):
        self.assertEqual(sorted(engine.options(section="scenarios")["scenarios"]), sorted(scenarios.names()))

    def test_write_story_refuses_news_with_a_scenario(self):
        with self.assertRaises(ValueError):
            engine.write_story("tbilisi-today", "1", scenario="countdown")


class TestFrontDoor(unittest.TestCase):
    """`make --scenario auto --preview-storyboard` shows the plot's storyboard before the writer is called."""

    def fetch(self, source, ref):
        story = demo("guess-the-number")
        return {"cluster": {"id": 1, "category": "society"}, "articles": [story["narration"]]}

    def test_preview_storyboard_before_the_writer(self):
        from unittest import mock
        from tt_shorts import make
        with mock.patch("tt_shorts.sources.fetch", self.fetch),                 mock.patch("tt_shorts.engine.write_story", side_effect=AssertionError("the writer was called")):
            res = make.make_film("https://example.org/doc", source="url", scenario="auto", preview_storyboard=True,
                                 yes=True, length="short")
        self.assertEqual(res["status"], "preview")
        self.assertFalse(res["writer_called"])
        self.assertEqual(len(res["storyboard"]), len(scenarios.get(res["scenario"])["beats"]))
        self.assertTrue(res["ranked"])

    def test_news_refused_at_the_front_door(self):
        from unittest import mock
        from tt_shorts import make
        with mock.patch("tt_shorts.engine.write_story", side_effect=AssertionError("the writer was called")):
            res = make.make_film("24835", scenario="auto", preview_storyboard=True, yes=True)
        self.assertEqual(res["status"], "error")
        self.assertTrue(any("refuses scenarios" in p for p in res["problems"]))

    def test_length_is_no_longer_ignored(self):
        from unittest import mock
        from tt_shorts import make
        with mock.patch("tt_shorts.sources.fetch", self.fetch):
            res = make.make_film("https://example.org/doc", source="url", scenario="auto", preview_storyboard=True,
                                 yes=True, length="soon")
        self.assertEqual(res["status"], "error")  # an unreadable --length is said, not dropped


class TestSoundCues(unittest.TestCase):
    """The beats' own cues, from the story's scenario: synthesized names only, one constant level (sfx.py)."""

    def props(self):
        story = demo()
        scenes, f = [], 0
        for s in story["scenes"]:
            scenes.append({"type": s["type"], "from": f, "duration": 150})
            f += 150
        return {"scenes": scenes, "transition": "line", "scenario": story["scenario"]}

    def test_beat_cues_are_laid_from_the_scenario(self):
        from tt_shorts import sfx
        cues = sfx.cues(self.props())
        names = {c["name"] for c in cues}
        self.assertTrue(names <= set(sfx.NAMES), names)
        self.assertEqual(cues[0]["name"], "whoosh")  # the promise opens with its cue
        self.assertEqual(cues, sorted(cues, key=lambda c: c["t"]))

    def test_a_beat_with_no_cue_has_none(self):
        from tt_shorts import sfx
        p = self.props()
        p["scenario"] = {"id": "x", "beats": [{"job": "promise", "sound": None}] + [{"job": "setup", "sound": None}] * 4}
        self.assertFalse([c for c in sfx.cues(p) if c["t"] < 0.01])

    def test_props_pass_the_scenario_to_the_cues(self):
        import inspect
        from tt_shorts import props
        self.assertIn('"scenario": story.get("scenario")', inspect.getsource(props))


def chapters_story(ids=("guess-the-number", "before-and-after")):
    """A long film of two chapters: the first demo without its end card, the second without its hook."""
    a, b = demo(ids[0]), demo(ids[1])
    cta = "მეტი განმარტებისთვის"
    first = a["narration"][:a["narration"].index(cta)].strip()
    second = b["narration"].split(". ", 1)[1] if False else b["narration"]
    start = b["scenes"][1]["at"].split()[0]
    second = b["narration"][b["narration"].index(start):]
    return {**a, "id": "scenario-chapters", "scenario": list(ids),
            "narration": first + " " + second, "scenes": a["scenes"][:-1] + b["scenes"][1:]}


class TestChapters(unittest.TestCase):
    def test_a_long_film_takes_a_plot_per_chapter(self):
        story = chapters_story()
        self.assertEqual(scenarios.story_problems(story), [])
        # the explainer program's own 25-45 s window is the only thing a two-chapter film trips: a long film needs a
        # longer program or format (owner decision in the result file), never a scenario problem
        self.assertTrue(all(p.startswith("timing:") for p in engine.check_story(story)))

    def test_each_chapter_is_held_to_its_own_plot(self):
        story = chapters_story()
        story["scenes"][5] = {**story["scenes"][5], "type": "quote", "text": "„ა“", "by": "ბ"}  # chapter 2, beat 2
        problems = scenarios.story_problems(story)
        self.assertTrue(any(p.startswith("chapter 2 (before-and-after)") for p in problems), problems)
        self.assertFalse(any(p.startswith("chapter 1") for p in problems), problems)

    def test_scene_count_and_ids_are_checked(self):
        story = chapters_story()
        del story["scenes"][2]
        self.assertTrue(any("chapters' beats need" in p for p in scenarios.story_problems(story)))
        story = chapters_story()
        story["scenario"] = ["guess-the-number"]
        self.assertTrue(any("2 or more" in p for p in scenarios.story_problems(story)))
        story["scenario"] = ["guess-the-number", "nope"]
        self.assertTrue(any("unknown scenario" in p for p in scenarios.story_problems(story)))

    def test_news_refuses_chapters(self):
        story = chapters_story()
        del story["program"]
        self.assertTrue(any("refuses scenarios" in p for p in scenarios.story_problems(story)))
        with self.assertRaises(scenarios.ScenarioError):
            scenarios.stamp(story, ["guess-the-number", "before-and-after"])

    def test_stamp_takes_comma_separated_ids(self):
        story = chapters_story()
        story["scenario"] = "x"
        scenarios.stamp(story, "guess-the-number,before-and-after")
        self.assertEqual(story["scenario"], ["guess-the-number", "before-and-after"])

    def test_sound_cues_follow_the_chapters(self):
        from tt_shorts import sfx
        story = chapters_story()
        scenes = [{"type": s["type"], "from": i * 150, "duration": 150} for i, s in enumerate(story["scenes"])]
        cues = sfx.cues({"scenes": scenes, "transition": "line", "scenario": story["scenario"]})
        self.assertTrue({c["name"] for c in cues} <= set(sfx.NAMES))


class NoProgramIsNews(unittest.TestCase):
    def test_a_bare_cluster_is_news_and_is_offered_nothing(self):
        self.assertEqual(scenarios.facts_of_text(["ტექსტი"])["program"], "news")
        self.assertEqual(scenarios.fit({"scenes": []}), [])


if __name__ == "__main__":
    unittest.main()
