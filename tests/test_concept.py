"""The idea step (tt_shorts/concept.py): the ladder's data, the filters in order, code's choice, the writer's link, and
that the news program never meets any of it."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, catalog, concept, engine, meta, news_check, programs, variety, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPLAINER = programs.get("explainer")
SOURCE = ("საქსტატის ანგარიშის მიხედვით, წლიური ინფლაცია 3.8 პროცენტია. სურსათზე ფასები გაიზარდა, "
          "ეროვნული ბანკი კი განაკვეთს ინარჩუნებს. მომხმარებლის კალათა თვეში გაძვირდა.")
STORY = json.loads((ROOT / "stories" / "explainer-inflation.json").read_text(encoding="utf-8"))


def idea(**kw):
    return {"rung": 1, "device": "drawn-reveal", "idea": "კალათა 3.8 ნაბიჯით ივსება და სურსათზე ფასები იზრდება",
            "object": "მომხმარებლის კალათა", "verb": "fills", "facts": ["3.8"], "p": 0.1, **kw}


def judged(*ideas, past=(), family="economy", story="s1"):
    return concept.judge(list(ideas), EXPLAINER, SOURCE, family, past, story)


class Data(unittest.TestCase):
    def test_the_catalogue_is_whole_and_says_what_it_can_draw(self):
        self.assertEqual(len(concept.devices()), 34)
        for did, d in concept.devices().items():
            self.assertTrue({"use", "scenes", "rungs", "news"} <= set(d) <= {"use", "scenes", "rungs", "news", "plain"}, did)
            self.assertIn(d["news"], ("yes", "cond", "no"), did)
            self.assertTrue(set(d["rungs"]) <= set(concept.RUNGS), did)
            self.assertTrue(set(d["scenes"]) <= set(catalog.types()), did)

    def test_every_rung_of_the_explainer_can_be_drawn_today(self):
        for rung in EXPLAINER["concept"]["rungs"]:
            self.assertTrue(concept.usable(EXPLAINER, rung), rung)

    def test_a_device_that_needs_the_kit_to_grow_is_never_offered(self):
        self.assertNotIn("one-take-world", concept.usable(EXPLAINER))
        self.assertNotIn("one-take-world", concept.options()["devices"])
        self.assertIn("one-take-world", concept.options()["later"])

    def test_the_data_is_brand_neutral(self):
        text = "".join((ROOT / "concepts" / f).read_text(encoding="utf-8").lower() for f in ("devices.json", "cliches.json"))
        for name in brand.names():
            self.assertNotIn(name.lower(), text)
        self.assertNotIn("sitech", text)

    def test_the_cliches_name_only_real_families(self):
        real = {f for n in brand.names() for f in brand.load(n)["family_by_category"].values()} | \
            {brand.load(n)["default_family"] for n in brand.names()}
        self.assertTrue(set(concept.cliches()["families"]) <= real)


class Program(unittest.TestCase):
    def test_the_explainer_has_the_step_and_news_stays_as_it_is(self):
        self.assertEqual(EXPLAINER["concept"], {"rungs": [1, 2, 3, 4, 5, 6], "ideas": 5})
        for name, p in programs.load_all().items():
            self.assertEqual(bool(p.get("concept")), name == "explainer", name)

    def test_news_can_not_be_given_the_step(self):
        with self.assertRaisesRegex(programs.ProgramError, "stays as it is"):
            programs.validate(programs.DEFAULT, {**programs.get(programs.DEFAULT), "concept": {"rungs": [1, 2]}})

    def test_a_bad_ladder_is_refused(self):
        for bad in ({"rungs": [9, 1]}, {"rungs": [1, 1]}, {"rungs": []}, {"rungs": [1, 2], "ideas": 3}, {"steps": 1}, 5):
            with self.assertRaises(concept.ConceptError, msg=bad):
                concept.validate(bad)


class Stems(unittest.TestCase):
    def test_a_word_is_found_under_its_endings(self):
        self.assertTrue(concept.said("გაზის ვენტილი", "ხელოსანი ვენტილს ხურავს"))
        self.assertTrue(concept.said("მილი", "გაზი მილში ჩერდება"))
        self.assertFalse(concept.said("ვენტილი", "გაზი მილში ჩერდება"))
        self.assertFalse(concept.said("", "ტექსტი"))

    def test_a_token_is_a_number_or_a_longer_word(self):
        self.assertIn("6400", concept.tokens("6400 აბონენტი"))
        self.assertTrue(concept.tokens("ინფლაცია") & concept.tokens("ინფლაციამ იმატა"))  # under its endings
        self.assertEqual(concept.tokens("და ის"), set())


class Filters(unittest.TestCase):
    def rule(self, one, **kw):
        return judged(one, **kw)[0]["rule"]

    def test_an_idea_of_this_story_passes(self):
        self.assertEqual(judged(idea())[0]["verdict"], "ok")

    def test_shape(self):
        for bad in (idea(device="nope"), idea(rung=9), idea(object=""), idea(object="ერთი ორი სამი ოთხი"), idea(object="3 კალათა"),
                    idea(device="one-take-world"), idea(rung=3)):  # later, and a device off its rung
            self.assertEqual(self.rule(bad), "shape", bad)
        self.assertEqual(judged("not an idea")[0]["rule"], "shape")

    def test_every_fact_is_in_the_source(self):
        self.assertEqual(self.rule(idea(facts=[])), "facts")
        self.assertEqual(self.rule(idea(facts=["7.5"])), "facts")
        self.assertEqual(self.rule(idea(facts=["3.8", "ჰოლანდია"])), "facts")
        self.assertIsNone(self.rule(idea(facts=["3.8", "ინფლაცია"])))

    def test_a_latin_name_is_a_fact_too(self):
        source = SOURCE + " კომპანია GM PHARMA და Visa-ს მენეჯერი."
        one = idea(idea="GM PHARMA და Visa სურსათზე", facts=["GM PHARMA", "visa"])
        self.assertEqual(concept.judge([one], EXPLAINER, source, "economy")[0]["verdict"], "ok")
        self.assertEqual(concept.judge([idea(facts=["Mastercard"])], EXPLAINER, source, "economy")[0]["rule"], "facts")

    def test_the_films_own_tool_is_no_object(self):
        for word in ("ციტატა", "სამი ნიშანი", "სკოლების რუკა", "ცარიელი ფურცელი", "გადასახადების სია"):
            self.assertEqual(self.rule(idea(object=word)), "generic", word)

    def test_a_loaded_metaphor_is_never_taken(self):
        self.assertEqual(self.rule(idea(idea="ფასები ბრძოლაში შედიან და კალათა ივსება")), "loaded")
        self.assertEqual(self.rule(idea(object="მონსტრი კალათაში")), "loaded")

    def test_a_short_stem_is_a_word_not_a_prefix(self):
        self.assertEqual(self.rule(idea(idea="ომი 3.8 ნაბიჯით მიდის")), "loaded")
        self.assertIsNone(self.rule(idea(idea="ომბუდსმენი 3.8 ნაბიჯით მიდის")))

    def test_one_idea_per_rung(self):
        out = judged(idea(), idea(idea="სხვა კალათა ივსება ინფლაცია და სურსათზე", object="სურსათი"))
        self.assertEqual([x["verdict"] for x in out], ["ok", "rejected"])

    def test_the_family_does_not_repeat_an_object(self):
        past = [{"story": "s0", "family": "economy", "object": "კალათა", "device": "yardstick", "rung": 4, "idea": "სხვა ამბავი"}]
        self.assertEqual(self.rule(idea(), past=past), "object")
        self.assertIsNone(self.rule(idea(), past=[{**past[0], "family": "culture"}]))
        self.assertIsNone(self.rule(idea(), past=[{**past[0], "story": "s1"}]))  # a story's own earlier idea

    def test_an_idea_close_to_a_recent_one_is_turned_down(self):
        past = [{"story": "s0", "family": "culture", "object": "ტილო", "device": "yardstick", "rung": 4,
                 "idea": idea()["idea"].replace("კალათა", "კალათი")}]
        self.assertEqual(self.rule(idea(), past=past), "seen")

    def test_swap_an_idea_that_doesnt_hold_its_facts_is_turned_down(self):
        self.assertEqual(self.rule(idea(idea="მთავარი თემა ნელ-ნელა იცვლება თვალწინ")), "swap")
        self.assertEqual(self.rule(idea(idea="ფასები ძალიან სწრაფად იზრდება", facts=["3.8"])), "swap")
        self.assertIsNone(self.rule(idea(idea="ფასები 3.8 ნაბიჯით იზრდება", facts=["3.8"])))

    def test_swap_takes_away_what_the_family_already_said(self):
        one = idea(idea="სურსათზე ფასები მაღლა მიდის", facts=["სურსათი"])
        past = [{"story": "s0", "family": "economy", "object": "ტილო", "device": "yardstick", "rung": 4,
                 "idea": "სურსათზე ფასები სულ სხვანაირად გამოიყურება ამბავში"}]
        self.assertEqual(self.rule(one, past=past), "swap")

    def test_a_cliche_is_flagged_not_rejected(self):
        one = idea(idea="მონეტა 3.8 ნაბიჯით ვარდება", object="მონეტა")
        out = judged(one)[0]
        self.assertEqual((out["verdict"], out["rule"]), ("flagged", "cliche"))
        self.assertEqual(judged(one, family="culture")[0]["verdict"], "ok")


class Choose(unittest.TestCase):
    A = idea(idea="კალათა 3.8 ნაბიჯით ივსება, სურსათზე ფასები იზრდება")
    B = idea(rung=4, device="empty-hold", idea="3.8 ცარიელ ეკრანზე რჩება, სურსათზე ფასები ქრება", object="ინფლაცია")
    C = idea(rung=3, device="map-flight", idea="ეროვნული ბანკი 3.8 მონეტა რუკაზე", object="მონეტა")

    def test_the_least_used_device_wins(self):
        past = [{"device": "drawn-reveal", "rung": 1}]
        self.assertEqual(concept.choose(judged(self.A, self.B), "s1", past)["device"], "empty-hold")

    def test_a_clean_idea_comes_before_a_flagged_one(self):
        past = [{"device": "drawn-reveal", "rung": 1}] * 5
        self.assertEqual(concept.choose(judged(self.A, self.C), "s1", past)["device"], "drawn-reveal")

    def test_a_flagged_idea_is_taken_when_nothing_clean_is_left(self):
        self.assertEqual(concept.choose(judged(self.C), "s1")["device"], "map-flight")

    def test_a_device_that_is_only_the_usual_scene_comes_last(self):
        quote = idea(rung=5, device="verbatim-quote", idea="ეროვნული ბანკი 3.8 სურსათზე ამბობს", object="განაკვეთი")
        past = [{"device": "drawn-reveal", "rung": 1}] * 5
        self.assertEqual(concept.choose(judged(self.A, quote), "s1", past)["device"], "drawn-reveal")

    def test_one_story_always_gets_the_same_choice(self):
        one = judged(self.A, self.B)
        self.assertEqual(concept.choose(one, "s1"), concept.choose(list(reversed(one)), "s1"))

    def test_nothing_left_is_none(self):
        self.assertIsNone(concept.choose(judged(idea(facts=[])), "s1"))


class Direct(unittest.TestCase):
    def run_it(self, answers, ideas=None):
        asked = []

        def call(text):
            asked.append(text)
            return json.dumps({"ideas": answers.pop(0)}, ensure_ascii=False)
        cluster = {"headline": "ინფლაცია"}
        return concept.direct(EXPLAINER, cluster, [SOURCE], "tbilisi-today", "economy", "s1", (), ideas, call), asked

    def test_the_model_writes_and_code_chooses(self):
        r, asked = self.run_it([[idea()]])
        self.assertEqual((r["calls"], r["concept"]["object"], r["concept"]["roll"]["kind"]), (1, "მომხმარებლის კალათა", "assigned"))
        self.assertIn("different rung", asked[0])
        self.assertIn("კალათა თვეში გაძვირდა", asked[0])  # the source

    def test_only_a_factual_reason_asks_again(self):
        r, asked = self.run_it([[idea(facts=["7.5"])], [idea()]])
        self.assertEqual((r["calls"], bool(r["concept"])), (2, True))
        self.assertIn("7.5", asked[1])
        r, _ = self.run_it([[idea(idea="ფასები ბრძოლაშია და კალათა ივსება")]])
        self.assertEqual((r["calls"], r["concept"]), (1, None))
        self.assertIn("loaded", r["warning"])

    def test_it_asks_again_once(self):
        r, _ = self.run_it([[idea(facts=["7.5"])], [idea(facts=["7.5"])]])
        self.assertEqual((r["calls"], r["concept"]), (2, None))

    def test_a_failing_model_is_a_warning_never_a_lost_video(self):
        def call(text):
            raise RuntimeError("writer model failed")
        r = concept.direct(EXPLAINER, {}, [SOURCE], "tbilisi-today", "economy", "s1", (), None, call)
        self.assertIsNone(r["concept"])
        self.assertIn("writer model failed", r["warning"])

    def test_an_answer_without_ideas_is_a_warning(self):
        r = concept.direct(EXPLAINER, {}, [SOURCE], "tbilisi-today", "economy", "s1", (), None, lambda t: "{}")
        self.assertIsNone(r["concept"])
        self.assertTrue(r["warning"])

    def test_an_agents_ideas_are_judged_the_same_with_no_call(self):
        r, asked = self.run_it([], ideas=[idea()])
        self.assertEqual((asked, r["concept"]["roll"]["kind"]), ([], "agent"))
        r, _ = self.run_it([], ideas=[idea(facts=["7.5"])])
        self.assertIsNone(r["concept"])

    def test_what_was_turned_down_stays_on_the_record(self):
        r, _ = self.run_it([[idea(), idea(rung=4, device="empty-hold", facts=["7.5"])]])
        self.assertEqual(r["concept"]["rejected"][0]["why"], "facts")


class StoryProblems(unittest.TestCase):
    CONCEPT = {"idea": "x", "object": "ინფლაცია", "verb": "rises", "rung": 4, "device": "empty-hold", "facts": ["3.8"]}

    def test_a_film_that_carries_its_idea(self):
        self.assertEqual(concept.story_problems({**STORY, "concept": self.CONCEPT}), [])
        self.assertEqual(concept.story_problems(STORY), [])

    def test_the_narration_says_the_object(self):
        found = concept.story_problems({**STORY, "concept": {**self.CONCEPT, "object": "ვენტილი"}})
        self.assertTrue(found and "never says" in found[0], found)

    def test_a_scene_carries_the_device(self):
        found = concept.story_problems({**STORY, "concept": {**self.CONCEPT, "device": "route-arc"}})
        self.assertTrue(found and "route" in found[0], found)

    def test_a_program_without_the_step_can_not_have_one(self):
        found = concept.story_problems({**STORY, "program": "law", "concept": self.CONCEPT})
        self.assertTrue(found and "no idea step" in found[0], found)
        self.assertTrue(concept.story_problems({"narration": "", "scenes": [], "concept": self.CONCEPT}))  # news

    def test_the_writer_can_not_set_it(self):
        self.assertIn("concept", writer.OWNED)

    def test_the_brief_says_the_object_and_the_scene(self):
        text = concept.brief_block(self.CONCEPT, EXPLAINER)
        self.assertIn("ინფლაცია", text)
        self.assertIn("stat", text)

    def test_the_writer_is_told_only_the_programs_scenes(self):
        text = concept.brief_block({**self.CONCEPT, "device": "persistent-object"}, EXPLAINER)
        self.assertIn("of type draw,", text)  # sign isn't an explainer's scene


class Provider(unittest.TestCase):
    def sent(self, env):
        seen = {}

        class Answer:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

        def opened(req, timeout=None):
            seen.update(url=req.full_url, body=json.loads(req.data), auth=req.get_header("Authorization"),
                        agent=req.get_header("User-agent"))
            return Answer()
        clean = {k: v for k, v in os.environ.items() if not k.startswith(("SHORTS_WRITER", "OPENROUTER"))}
        with mock.patch.dict(os.environ, {**clean, **env}, clear=True), mock.patch("urllib.request.urlopen", opened):
            self.assertEqual(writer._call("p", "m"), "ok")
        return seen

    def test_the_default_is_exactly_what_it_was(self):
        s = self.sent({"OPENROUTER_API_KEY": "k"})
        self.assertEqual(s["url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(s["body"], {"model": "m", "messages": [{"role": "user", "content": "p"}], "temperature": 0.3,
                                     "max_tokens": 1800, "reasoning": {"enabled": False}})

    def test_any_openai_format_server_can_write(self):
        s = self.sent({"SHORTS_WRITER_URL": "https://api.example.test/provider/v1/", "SHORTS_WRITER_KEY": "k2"})
        self.assertEqual(s["url"], "https://api.example.test/provider/v1/chat/completions")
        self.assertEqual(s["auth"], "Bearer k2")
        self.assertEqual(s["agent"], "veasy-writer")  # not Python-urllib's default, which Cloudflare refuses
        self.assertEqual(s["body"]["max_tokens"], writer.THINKING_TOKENS)  # thinking counts: too few, an empty answer
        self.assertNotIn("reasoning", s["body"])

    def test_a_missing_key_names_itself(self):
        clean = {k: v for k, v in os.environ.items() if not k.startswith(("SHORTS_WRITER", "OPENROUTER"))}
        with mock.patch.dict(os.environ, {**clean, "SHORTS_WRITER_URL": "https://a.test/v1"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SHORTS_WRITER_KEY"):
                writer._call("p", "m")


class WriteStory(unittest.TestCase):
    """engine.write_story on the explainer: the idea first, the script after, the idea kept and remembered."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name, "SHORTS_KAEASY_LEARN": "0"})
        self.env.start()
        self.draft = {k: v for k, v in STORY.items() if k not in ("id", "date", "sources", "source", "program", "brand")}
        self.article = STORY["narration"] + " " + " ".join(STORY["sources"]) + " სურსათი ბანკი"
        self.data = {"cluster": {"id": "doc-1", "headline": "ინფლაცია", "sources": STORY["sources"], "category": "economy",
                                 "created_at": "2026-11-03T12:00:00Z"},
                     "articles": [self.article]}

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def write(self, answers, program="explainer"):
        prompts = []

        def model(prompt, *a, **k):
            prompts.append(prompt)
            return json.dumps(answers.pop(0), ensure_ascii=False)
        with mock.patch.object(writer, "_call", side_effect=model), \
                mock.patch("tt_shorts.sources.fetch", return_value=self.data):
            return engine.write_story("text", "doc-1", "tbilisi-today", program=program), prompts

    def ideas(self):
        return {"ideas": [idea(rung=4, device="empty-hold", object="ინფლაცია", facts=["3.8"],
                               idea="წლიური ინფლაცია 3.8 ცარიელ ეკრანზე რჩება")]}

    def test_the_idea_comes_first_and_the_story_keeps_it(self):
        result, prompts = self.write([self.ideas(), self.draft, self.draft])
        self.assertEqual(result["problems"], [])
        self.assertIn("different rung", prompts[0])
        self.assertIn("THE FILM'S IDEA", prompts[1])
        story = json.loads(pathlib.Path(result["story"]).read_text(encoding="utf-8"))
        self.assertEqual((story["concept"]["object"], story["concept"]["device"]), ("ინფლაცია", "empty-hold"))
        self.assertEqual(result["concept"], story["concept"])
        rows = variety.recent_concepts("tbilisi-today")
        self.assertEqual([(r["story"], r["object"], r["family"]) for r in rows],
                         [(story["id"], "ინფლაცია", meta.family("economy", brand.load("tbilisi-today")))])

    def test_a_writer_cant_slip_its_own_idea_in(self):
        result, _ = self.write([self.ideas(), {**self.draft, "concept": {"object": "ჩემი"}}, self.draft])
        story = json.loads(pathlib.Path(result["story"]).read_text(encoding="utf-8"))
        self.assertEqual(story["concept"]["object"], "ინფლაცია")

    def test_a_script_that_drops_the_object_goes_back_for_repair(self):
        ideas = {"ideas": [idea(rung=4, device="empty-hold", object="სურსათი", facts=["3.8"], idea="სურსათი 3.8 ფასებში")]}
        no = {**self.draft, "narration": self.draft["narration"].replace("სურსათ", "პროდუქტ")}
        result, prompts = self.write([ideas, no, self.draft, self.draft])
        self.assertEqual(result["problems"], [])
        self.assertIn("never says", prompts[2])  # the repair call names it

    def test_a_script_that_can_not_carry_the_idea_keeps_its_place(self):
        ideas = {"ideas": [idea(rung=1, device="persistent-object", object="კალათა", facts=["3.8"], idea="კალათა 3.8 ნაბიჯით")]}
        result, prompts = self.write([ideas, self.draft, self.draft, self.draft, self.draft])
        self.assertEqual(result["problems"], [])
        self.assertIn("no scene carries", prompts[2])  # it went back for repairs like any problem
        self.assertIsNone(result["concept"])
        self.assertTrue(any(w.startswith("concept: dropped") for w in result["warnings"]), result["warnings"])
        self.assertNotIn("concept", json.loads(pathlib.Path(result["story"]).read_text(encoding="utf-8")))
        self.assertEqual(variety.recent_concepts("tbilisi-today"), [])

    def test_a_motif_no_icon_knows_goes_back_for_repair(self):
        result, prompts = self.write([self.ideas(), {**self.draft, "motif": "ოქრო"}, self.draft, self.draft])
        self.assertEqual(result["problems"], [])
        self.assertIn("motif", prompts[2])

    def test_a_failed_idea_step_never_loses_the_video(self):
        result, _ = self.write([{"ideas": []}, self.draft, self.draft])
        self.assertEqual(result["problems"], [])
        self.assertIsNone(result["concept"])
        self.assertTrue(any(w.startswith("concept:") for w in result["warnings"]))
        self.assertNotIn("concept", json.loads(pathlib.Path(result["story"]).read_text(encoding="utf-8")))
        self.assertEqual(variety.recent_concepts("tbilisi-today"), [])

    def test_engine_concept_chooses_without_recording_a_thing(self):
        out = {}
        with mock.patch.object(writer, "_call", return_value=json.dumps(self.ideas(), ensure_ascii=False)), \
                mock.patch("tt_shorts.sources.fetch", return_value=self.data), \
                mock.patch.object(engine, "out", side_effect=lambda r, code=0: out.update(r) or code):
            a = mock.Mock(program=None, source="text", ref="doc-1", batch=None, brand="tbilisi-today", ideas=None)
            self.assertEqual(engine.concept_cmd(a), 0)
        self.assertEqual((out["summary"]["chosen"], out["summary"]["calls"]), (1, 1))
        self.assertEqual(variety.recent_concepts("tbilisi-today"), [])

    def test_a_batch_sees_its_own_earlier_stories(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([{"source": "text", "ref": "a"}, {"source": "text", "ref": "b"}], f)
        out = {}
        datas = iter([{**self.data, "cluster": {**self.data["cluster"], "id": i}} for i in ("a", "b")])
        with mock.patch.object(writer, "_call", return_value=json.dumps(self.ideas(), ensure_ascii=False)), \
                mock.patch("tt_shorts.sources.fetch", side_effect=lambda *a: next(datas)), \
                mock.patch.object(engine, "out", side_effect=lambda r, code=0: out.update(r) or code):
            engine.concept_cmd(mock.Mock(program=None, source=None, ref=None, batch=f.name, brand="tbilisi-today", ideas=None))
        os.unlink(f.name)
        self.assertEqual(out["summary"]["chosen"], 1)  # the second story's object is taken: the family doesn't repeat it
        self.assertEqual(out["summary"]["repeated_objects"], [])

    def test_news_never_meets_the_step(self):
        self.assertFalse(programs.get(programs.DEFAULT).get("concept"))
        self.assertNotIn("concept", json.dumps(programs.get(programs.DEFAULT)))
        with mock.patch.object(concept, "direct") as step, \
                mock.patch.object(writer, "write", side_effect=writer.ChecksFailed(["stop here"])), \
                mock.patch("tt_shorts.sources.fetch", return_value=self.data):
            with self.assertRaises(writer.ChecksFailed):
                engine.write_story("text", "doc-1", "tbilisi-today", program=None)
        step.assert_not_called()


class Options(unittest.TestCase):
    def test_options_list_the_ladder(self):
        section = engine.options()
        self.assertIn("concepts", json.dumps(section, ensure_ascii=False))

    def test_news_check_scene_types_cover_the_devices(self):
        for d in concept.devices().values():
            self.assertTrue(set(d["scenes"]) <= set(news_check.SCENE_TYPES) | news_check.IDEA_TYPES)


if __name__ == "__main__":
    unittest.main()
