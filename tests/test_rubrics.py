"""Rubrics (named recurring shows, rubrics/<id>.json) and the morning digest: data and validation, eligibility on the
facts, the episode counter, the "continues" comparison, the agree counting (N12), the digest builder and source, and
the wiring (write, queue, ops/daily.py)."""
import copy
import json
import os
import pathlib
import sqlite3
import tempfile
import unittest
from unittest import mock

from tt_shorts import digest, engine, news_check, programs, queue, rubrics, store, writer
from tt_shorts.sources import stories as stories_src

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "sources.json").read_text(encoding="utf-8"))
AGREE = json.loads((ROOT / "tests" / "fixtures" / "rubric-agree.json").read_text(encoding="utf-8"))
AGREE_SOURCES = json.loads((ROOT / "tests" / "fixtures" / "rubric-agree.sources.json").read_text(encoding="utf-8"))
NUMBER = json.loads((ROOT / "stories" / "rubric-24835-number.json").read_text(encoding="utf-8"))
DIGEST = json.loads((ROOT / "stories" / "digest-2026-11-01.json").read_text(encoding="utf-8"))
DIGEST_SOURCES = json.loads((ROOT / "tests" / "fixtures" / "digest-2026-11-01.sources.json").read_text(encoding="utf-8"))


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def answer_of(story):
    """A model's answer for a story: no data fields, every anchor word for word (writer._anchors_ok)."""
    out = {k: v for k, v in copy.deepcopy(story).items() if k not in ("id", "date", "sources")}
    for sc in out["scenes"]:
        if sc["at"] not in out["narration"]:
            sc["at"] = "„" + sc["at"].replace(" ცნობით", "“ ცნობით")
    return out


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name, "SHORTS_KAEASY_LEARN": "0"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class Data(unittest.TestCase):
    def test_the_five_rubrics_load_in_slot_order(self):
        self.assertEqual([r["id"] for r in rubrics.by_slot()], ["digest", "changes", "number", "agree", "continues"])
        self.assertEqual(rubrics.get("number")["label"], "დღის ციფრი")
        self.assertEqual(rubrics.get("digest")["program"], "digest")
        self.assertIn("rubrics", engine.options()["rubrics"])
        self.assertEqual(set(engine.options()["rubrics"]["rubrics"]), set(rubrics.names()))

    def test_bad_rubrics_are_refused(self):
        good = load("rubrics/number.json")
        for bad in ({"eligible": [{"big_numbers": "len(x) > 2"}]},  # no expression strings: a count or {"max": n}
                    {"eligible": [{"vibes": 1}]}, {"never": [{"families": ["gossip"]}]},
                    {"label": "Number of the day"}, {"label": "დღის 1 ციფრი"},  # Georgian, no digit of its own
                    {"label": "ადასტურებს {n}"},  # "{n}" needs its count
                    {"numbering": "season"}, {"program": "gossip"}, {"format": "neon"}, {"slot": "25:00"},
                    {"shape": [{"types": ["stat"]}, {"types": ["end"]}]},  # starts with a hook
                    {"shape": [{"types": ["hook"]}, {"types": ["take"]}, {"types": ["end"]}]},
                    {"shape": [{"types": ["hook"]}, {"types": "any", "min": 3, "max": 1}, {"types": ["end"]}]},
                    {"brief": []}, {"extra": 1}):
            with self.assertRaises(rubrics.RubricError, msg=str(bad)):
                rubrics.validate("number", {**good, **bad})
        with self.assertRaises(rubrics.RubricError):
            rubrics.validate("other", good)  # the id is its file name
        with self.assertRaises(rubrics.RubricError):
            rubrics.get("gossip")


class Eligibility(unittest.TestCase):
    def facts(self, articles, sources=("ა", "ბ", "გ", "დ"), category="society", **cluster):
        return rubrics.facts({"cluster": {"sources": list(sources), "category": category, **cluster},
                              "articles": articles}, "tbilisi-today")

    def test_the_gas_cut_is_a_number_and_a_change_not_an_agree(self):
        f = self.facts(FIXTURES["24835"])
        self.assertEqual((f["big_numbers"], f["dates"] >= 1, f["members"], f["agreed"]), (1, True, 1, 0))
        self.assertEqual(rubrics.eligible(f), ["changes", "number"])

    def test_a_world_story_without_a_big_number_is_neither(self):
        f = self.facts(FIXTURES["24725"], category="world")
        self.assertEqual(rubrics.eligible(f), [])

    def test_agree_needs_facts_in_three_members(self):
        f = self.facts(AGREE_SOURCES, sources=AGREE["sources"], category="education")
        self.assertEqual((f["members"], f["agreed"]), (5, 3))  # the place, the date, the number
        self.assertIn("agree", rubrics.eligible(f))

    def test_never_rules_it_out(self):
        f = self.facts(["6400 ადამიანი დაიღუპა 2 ნოემბერს."])
        self.assertTrue(f["deaths"])
        self.assertNotIn("number", rubrics.eligible(f))

    def test_the_digest_counts_stories(self):
        self.assertEqual(rubrics.eligible({"stories": 2}, "digest"), ["digest"])
        self.assertEqual(rubrics.eligible({"stories": 1}, "digest"), [])

    def test_assign_gives_each_rubric_once_and_a_grown_cluster_only_continues(self):
        num = {"big_numbers": 1, "quantities": 1, "family": "society"}
        grown = {**num, "had_video": True, "new_outlets": 2, "new_facts": 1}
        got = rubrics.assign([("a", num, None), ("b", num, None), ("c", grown, ("continues",))])
        self.assertEqual(got, {"c": "continues", "a": "number"})


class Shape(unittest.TestCase):
    def test_shapes_match(self):
        n = rubrics.get("number")["shape"]
        self.assertTrue(rubrics._match(["hook", "stat", "timeline", "end"], n))
        self.assertTrue(rubrics._match(["hook", "change", "where", "points", "end"], n))
        self.assertFalse(rubrics._match(["hook", "stat", "end"], n))  # 1-2 scenes after the number
        self.assertFalse(rubrics._match(["hook", "where", "stat", "end"], n))  # the number first
        d = rubrics.get("digest")["shape"]
        self.assertTrue(rubrics._match(["hook", "stat", "chapter", "quote", "end"], d))  # story 1 opens on the hook
        self.assertTrue(rubrics._match(["hook", "chapter", "stat", "chapter", "quote", "end"], d))  # three stories
        self.assertFalse(rubrics._match(["hook", "chapter", "chapter", "chapter", "end"], d))  # at most three
        self.assertFalse(rubrics._match(["hook", "stat", "end"], d))  # at least two stories

    def test_the_demos_pass(self):
        self.assertEqual(rubrics.story_problems(NUMBER), [])
        self.assertEqual(rubrics.story_problems(DIGEST), [])
        self.assertEqual(rubrics.story_problems(AGREE), [])
        self.assertEqual(engine.check_story(NUMBER, FIXTURES["24835"]), [])
        self.assertEqual(engine.check_story(DIGEST, DIGEST_SOURCES), [])
        self.assertEqual(engine.check_story(AGREE, AGREE_SOURCES), [])

    def test_code_owned_fields_and_the_shape_are_checked(self):
        s = copy.deepcopy(NUMBER)
        s["scenes"] = [x for x in s["scenes"] if x["type"] != "timeline"]
        self.assertTrue(any("don't fit its shape" in p for p in rubrics.story_problems(s)))
        self.assertTrue(engine.structure_problems({**NUMBER, "episode": "12"}))
        self.assertTrue(engine.structure_problems({**NUMBER, "rubric": "gossip"}))
        plain = {k: v for k, v in NUMBER.items() if k != "rubric"}
        self.assertIn("story: 'episode' without a rubric (code sets it with the rubric)", rubrics.story_problems(plain))
        cont = {**NUMBER, "rubric": "continues"}
        self.assertTrue(any("needs its part" in p for p in rubrics.story_problems(cont)))

    def test_the_rubrics_length_window(self):
        self.assertEqual(rubrics.length_problems(NUMBER), [])
        long = {**NUMBER, "narration": NUMBER["narration"].replace("დეტალები", "გაზსადენზე სარეკონსტრუქციო "
                                                                   "სამუშაოები მიმდინარეობს და მისამართების სია "
                                                                   "ბმულზეა. დეტალები")}
        self.assertTrue(rubrics.length_problems(long)[0].startswith("timing:"))

    def test_the_chip(self):
        self.assertEqual(rubrics.chip(NUMBER), "დღის ციფრი · #1")
        self.assertEqual(rubrics.chip({**NUMBER, "episode": 12}), "დღის ციფრი · #12")
        self.assertEqual(rubrics.chip(AGREE), "ადასტურებს 4 გამოცემა · #1")
        self.assertEqual(rubrics.chip(DIGEST), "დილის 2 ამბავი · #1")  # the real count, never three
        three = {**DIGEST, "digest": {"stories": [1, 2, 3]}}
        self.assertEqual(rubrics.chip(three), "დილის 3 ამბავი · #1")
        self.assertEqual(rubrics.chip({**NUMBER, "rubric": "continues", "part": 2}), "ამბავი გრძელდება · ნაწ. 2")
        self.assertIsNone(rubrics.chip({"id": 1}))

    def test_the_writer_never_sets_them(self):
        answer = answer_of(NUMBER)  # rubric and episode stay in the answer
        with mock.patch.object(writer, "_call", return_value=json.dumps(answer, ensure_ascii=False)):
            story = writer.write({"id": 24835, "created_at": "2026-11-01T14:22:16Z", "sources": NUMBER["sources"]},
                                 FIXTURES["24835"])
        self.assertNotIn("rubric", story)
        self.assertNotIn("episode", story)


class Episodes(Home):
    def test_reserve_is_idempotent_per_story_and_counts_up(self):
        self.assertEqual(rubrics.reserve("tbilisi-today", "number", "24835-number"), 1)
        self.assertEqual(rubrics.reserve("tbilisi-today", "number", "24835-number"), 1)  # a re-run, another look
        self.assertEqual(rubrics.reserve("tbilisi-today", "number", "24900-number"), 2)
        self.assertEqual(rubrics.reserve("sitech", "number", "x"), 1)  # per brand
        self.assertEqual(rubrics.reserve("tbilisi-today", "changes", "x"), 1)  # per rubric
        rubrics.finish("tbilisi-today", "number", "24835-number")
        self.assertEqual(rubrics.episodes("tbilisi-today")["number"], {"last": 2, "done": 1})

    def test_a_failed_last_episode_gives_its_number_back_and_an_earlier_one_leaves_a_gap(self):
        for k in ("a", "b", "c"):
            rubrics.reserve("tbilisi-today", "number", k)
        rubrics.release("tbilisi-today", "number", "c")  # the last: the next video takes #3
        self.assertEqual(rubrics.reserve("tbilisi-today", "number", "d"), 3)
        rubrics.release("tbilisi-today", "number", "b")  # not the last: #2 stays unused, never given twice
        self.assertEqual(rubrics.reserve("tbilisi-today", "number", "e"), 4)
        rubrics.finish("tbilisi-today", "number", "a")
        self.assertFalse(rubrics.release("tbilisi-today", "number", "a"))  # done is never released
        self.assertEqual(rubrics.reserve("tbilisi-today", "number", "a"), 1)

    def test_stamp_sets_the_fields(self):
        s = rubrics.stamp(copy.deepcopy(NUMBER), "number", "tbilisi-today", "k")
        self.assertEqual((s["rubric"], s["episode"]), ("number", 1))
        s = rubrics.stamp({"id": 5}, "continues", "tbilisi-today", "k2", part=3)
        self.assertEqual((s["episode"], s["part"]), (1, 3))


class Continues(Home):
    def test_compare_is_pure(self):
        before = {"part": 1, "outlets": ["ა", "ბ"], "numbers": ["6400"], "quotes": []}
        now = {"outlets": ["ა", "ბ", "გ", "დ"], "numbers": ["6400", "7000"], "quotes": ["ახალი ციტატა აქ არის"]}
        got = rubrics.compare(before, now)
        self.assertEqual(got, {"had_video": True, "part": 2, "new_outlets": ["გ", "დ"], "new_numbers": ["7000"],
                               "new_quotes": ["ახალი ციტატა აქ არის"]})
        self.assertFalse(rubrics.compare(None, now)["had_video"])

    def test_the_stored_part_one_against_the_cluster_now(self):
        story = load("stories/24835.json")
        rubrics.remember("tbilisi-today", {**story, "sources": story["sources"][:2]}, FIXTURES["24835"])
        grown_text = FIXTURES["24835"][0] + " სამუშაოებს 120 სპეციალისტი ასრულებს."
        data = {"cluster": {"id": 24835, "sources": story["sources"], "category": "society"},
                "articles": [grown_text]}
        g = rubrics.growth("tbilisi-today", data)
        self.assertEqual((g["had_video"], g["part"], g["new_outlets"], g["new_numbers"]),
                         (True, 2, story["sources"][2:], ["120"]))
        f = rubrics.facts(data, "tbilisi-today", g)
        self.assertIn("continues", rubrics.eligible(f))
        self.assertEqual(rubrics.gate_problems({"rubric": "continues", "narration": "120 სპეციალისტი",
                                                "scenes": []}, g), [])
        self.assertTrue(rubrics.gate_problems({"rubric": "continues", "narration": "იგივე ამბავი", "scenes": []}, g))
        unchanged = rubrics.growth("tbilisi-today", {"cluster": {"id": 24835, "sources": story["sources"][:2]},
                                                     "articles": FIXTURES["24835"]})
        self.assertNotIn("continues", rubrics.eligible(rubrics.facts(
            {"cluster": {"id": 24835, "sources": story["sources"][:2]}, "articles": FIXTURES["24835"]},
            "tbilisi-today", unchanged)))


class Agree(unittest.TestCase):
    def test_counts_per_outlet_literally(self):
        members = [{"outlet": "ა", "text": "1200 მოსწავლე ისწავლის"}, {"outlet": "ა", "text": "1200 მოსწავლეს"},
                   {"outlet": "ბ", "text": "იქ 1200 მოსწავლე"}, {"outlet": "გ", "text": "1200 მასწავლებელი"}]
        got = rubrics.agreed(members, 2)
        self.assertEqual([(x["text"], x["count"]) for x in got], [("1200 მოსწავლე", 2)])  # one outlet counts once
        self.assertEqual(rubrics.agreed(members, 3), [])  # 1200 მასწავლებელი is another fact

    def test_the_scene_says_the_smallest_count(self):
        made = rubrics.agree_scene(AGREE_SOURCES)
        self.assertEqual((made["n"], made["total"]), (4, 5))
        self.assertEqual([x["count"] for x in made["items"]], [5, 4, 4])
        self.assertIsNone(rubrics.agree_scene(FIXTURES["24725"]))  # nothing three of them state alike
        s = copy.deepcopy(AGREE)
        s["scenes"][1]["items"] = [{"text": "invented", "count": 9}]
        self.assertEqual(rubrics.fill_agree(s, AGREE_SOURCES), [])
        self.assertEqual(s["scenes"][1]["items"], AGREE["scenes"][1]["items"])  # the writer's items are replaced

    def test_n12(self):
        self.assertEqual(news_check.agreed(AGREE, AGREE_SOURCES), [])
        s = copy.deepcopy(AGREE)
        s["scenes"][1]["n"] = 5
        self.assertTrue(any("is in 4 member article(s)" in p for p in news_check.agreed(s, AGREE_SOURCES)))
        s = copy.deepcopy(AGREE)
        s["scenes"][1]["items"].append({"text": "ახალი სკოლა", "count": 4})
        self.assertTrue(any("no fact code can count" in p for p in news_check.agreed(s, AGREE_SOURCES)))
        s = copy.deepcopy(AGREE)
        s["narration"] = s["narration"].replace("მინიმუმ ოთხი", "ოთხი")
        s["scenes"][1]["at"] = "ოთხი გამოცემა"
        self.assertTrue(any("„მინიმუმ“" in p for p in news_check.agreed(s, AGREE_SOURCES)))
        s = copy.deepcopy(AGREE)
        s["scenes"][1]["headline"] = "ტესტ-გამოცემა 2 წერს"
        self.assertTrue(any("never names them" in p for p in news_check.agreed(s, AGREE_SOURCES)))
        s = copy.deepcopy(AGREE)
        s["narration"] = s["narration"].replace("ერთსა და იმავეს", "პროსამთავრობო მედიაც")
        self.assertTrue(any(p.startswith("N12: „პროსამთავრობო") for p in news_check.problems(s, AGREE_SOURCES)))

    def test_counts_on_screen_are_not_numbers_of_the_articles(self):  # N2 reads the facts' texts, not n or count
        self.assertNotIn(" 5 ", f" {news_check.screen_text(AGREE)} ")


class Digest(Home):
    def items(self, *paths):
        out = []
        for p, arts in paths:
            out.append({"story": load(p), "articles": arts, "path": p})
        return out

    def data(self, items):
        arts = [a for it in items for a in it["articles"]]
        return {"cluster": {"id": "2026-11-02", "created_at": "2026-11-02T08:00:00Z", "sources": ["ა"],
                            "brand": "tbilisi-today"}, "articles": arts, "stories": items}

    def test_sentences_keep_quotes_whole(self):
        self.assertEqual(digest.sentences("ერთი. მან თქვა: „ეს. ის“. ბოლო"), ["ერთი.", "მან თქვა: „ეს. ის“.", "ბოლო"])
        self.assertEqual(digest.body(load("stories/24835.json"))[-1], "მისამართების სრული სია ბმულზეა.")  # before the outlets line

    def test_two_stories_in_the_window(self):
        items = self.items(("stories/24835.json", FIXTURES["24835"]), ("stories/24725.json", FIXTURES["24725"]))
        s = digest.build(self.data(items), rubrics.get("digest"), "tbilisi-today")
        self.assertTrue(s["narration"].startswith("დილის ორი ამბავი ერთ ვიდეოში. ვარკეთილსა და ვაზისუბანში"))
        hook = s["scenes"][0]  # frame 0 is the first story's own headline, not a list of categories
        self.assertEqual((hook["type"], hook["kicker"], hook["lines"]),
                         ("hook", "საზოგადოება", load("stories/24835.json")["scenes"][0]["lines"]))
        self.assertEqual([(x["n"], x["of"]) for x in s["scenes"] if x["type"] == "chapter"], [(2, 2)])
        secs = digest._seconds(s)
        self.assertTrue(47 <= secs <= 57, secs)
        s.update(program="digest", rubric="digest", episode=1)
        self.assertEqual(engine.check_story(s, self.data(items)["articles"]), [])
        self.assertEqual(rubrics.chip(s), "დილის 2 ამბავი · #1")

    def test_three_stories_with_a_synthetic_third(self):  # test-only: a real third needs a cluster from D1
        items = self.items(("stories/24835.json", FIXTURES["24835"]), ("stories/24725.json", FIXTURES["24725"]),
                           ("tests/fixtures/rubric-agree.json", AGREE_SOURCES))
        s = digest.build(self.data(items), rubrics.get("digest"), "tbilisi-today")
        s.update(program="digest", rubric="digest", episode=1)
        self.assertIn("დილის სამი ამბავი", s["narration"])
        self.assertEqual([(x["n"], x["of"]) for x in s["scenes"] if x["type"] == "chapter"], [(2, 3), (3, 3)])
        self.assertTrue(45 <= digest._seconds(s) <= 60)
        self.assertEqual(engine.check_story(s, self.data(items)["articles"]), [])
        self.assertEqual(rubrics.chip(s), "დილის 3 ამბავი · #1")

    def test_what_a_digest_refuses(self):
        one = self.items(("stories/24835.json", FIXTURES["24835"]))
        with self.assertRaises(digest.DigestError):
            digest.build(self.data(one), rubrics.get("digest"))
        bad = self.items(("stories/24835.json", FIXTURES["24835"]), ("stories/24725.json", FIXTURES["24725"]))
        bad[1]["story"]["narration"] = bad[1]["story"]["narration"].replace("შეხვედრას", "საშინელ შეხვედრას")
        with self.assertRaisesRegex(digest.DigestError, "does not pass its checks"):
            digest.build(self.data(bad), rubrics.get("digest"))

    def test_the_stories_source(self):
        data = stories_src.fetch("tests/fixtures/digest-demo.json")
        self.assertEqual([s["story"]["id"] for s in data["stories"]], [24835, 24725])
        self.assertEqual((data["cluster"]["id"], data["cluster"]["url"]), ("2026-11-01", "https://tbilisi.today/"))
        self.assertEqual(data["cluster"]["sources"][:4], load("stories/24835.json")["sources"])
        with self.assertRaisesRegex(ValueError, "one brand"):
            req = pathlib.Path(self.tmp.name, "mixed.json")
            req.write_text(json.dumps({"stories": ["stories/24835.json", "stories/sitech-cybercartel.json"],
                                       "sources": [FIXTURES["24835"], ["x"]]}), encoding="utf-8")
            stories_src.fetch(str(req))
        with self.assertRaisesRegex(ValueError, "only once"):
            req = pathlib.Path(self.tmp.name, "twice.json")
            req.write_text(json.dumps({"stories": ["stories/24835.json", "stories/24835-data.json"],
                                       "sources": "tests/fixtures/sources.json"}), encoding="utf-8")
            stories_src.fetch(str(req))
        with self.assertRaisesRegex(ValueError, "2-3"):
            stories_src.fetch("stories/24835.json")

    def test_the_brands_done_videos_of_a_day(self):
        jobs = [{"brand": "tbilisi-today", "program": "news", "created": "2026-11-02T06:00:00", "priority": p,
                 "story": f"s{p}.json"} for p in (1, 5, 3)]
        with mock.patch.object(queue, "listing", return_value=jobs):
            paths, _ = stories_src.requested("done:tbilisi-today:2026-11-02")
        self.assertEqual(paths, ["s5.json", "s3.json", "s1.json"])

    def test_write_story_builds_it_without_a_model(self):
        with mock.patch.object(writer, "_call", side_effect=AssertionError("no model")):
            r = engine.write_story("stories", "tests/fixtures/digest-demo.json", rubric="digest",
                                   out_path=str(pathlib.Path(self.tmp.name, "d.json")))
        self.assertEqual((r["problems"], r["program"], r["rubric"], r["episode"], r["chip"]),
                         ([], "digest", "digest", 1, "დილის 2 ამბავი · #1"))
        story = json.loads(pathlib.Path(r["story"]).read_text(encoding="utf-8"))
        self.assertEqual(story["link"], {"display": "tbilisi.today", "qr": "https://tbilisi.today/"})
        self.assertNotIn("director", story)


class Wiring(Home):
    def test_write_story_with_a_rubric(self):
        answer = answer_of(NUMBER)
        answer["episode"] = 99  # a writer's episode is dropped
        prompts = []

        def model(prompt, *a, **k):
            prompts.append(prompt)
            return json.dumps(answer, ensure_ascii=False)
        src = pathlib.Path(self.tmp.name, "c.json")
        src.write_text(json.dumps({"id": 24835, "headline": "გაზი", "category": "society",
                                   "date": "2026-11-01T14:22:16Z", "sources": NUMBER["sources"],
                                   "articles": FIXTURES["24835"]}, ensure_ascii=False), encoding="utf-8")
        with mock.patch.object(writer, "_call", side_effect=model):
            r = engine.write_story("text", str(src), rubric="number")
        self.assertEqual((r["problems"], r["rubric"], r["episode"], r["chip"], r["format"]),
                         ([], "number", 1, "დღის ციფრი · #1", "number"))
        self.assertTrue(r["story"].endswith("-number.json"))  # the news name + the rubric
        self.assertIn("Rubric (code chose it; follow it): number", prompts[0])
        with mock.patch.object(writer, "_call", side_effect=model):
            again = engine.write_story("text", str(src), rubric="number")
        self.assertEqual(again["episode"], 1)  # the same story keeps its number
        with self.assertRaisesRegex(ValueError, "does not fit"):
            engine.write_story("text", str(src), rubric="agree")  # one article: nothing three outlets state

    def test_queue_takes_a_rubric(self):
        job, _ = queue.add(source="tbilisi-today", ref=24835, overrides={"rubric": "number"})
        plain, _ = queue.add(source="tbilisi-today", ref=24835)
        self.assertNotEqual(job["id"], plain["id"])
        self.assertEqual((job["format"], job["program"]), ("number", "news"))
        dig, _ = queue.add(ref="done:tbilisi-today", overrides={"rubric": "digest"})
        self.assertEqual((dig["program"], dig["source"], dig["format"]), ("digest", "stories", "digest"))
        with self.assertRaises(rubrics.RubricError):
            queue.add(source="tbilisi-today", ref=1, overrides={"rubric": "gossip"})
        with self.assertRaises(ValueError):
            queue.add(source="tbilisi-today", ref=1, program="law", overrides={"rubric": "number"})

    def test_a_done_job_uses_its_episode_and_stores_the_cluster(self):
        path = pathlib.Path(self.tmp.name, "rubric-24835-number.json")
        story = rubrics.stamp(copy.deepcopy(NUMBER), "number", "tbilisi-today", "rubric-24835-number")
        path.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
        store.sources_path(path).write_text(json.dumps(FIXTURES["24835"], ensure_ascii=False), encoding="utf-8")
        job, _ = queue.add(story=str(path), overrides={"rubric": "number"})
        with mock.patch.object(engine, "render_story", return_value={"file": "/x.mp4", "problems": []}), \
                mock.patch.object(engine, "qa_file", return_value={"problems": []}):
            queue.run(max_jobs=1, engine="gemini")
        self.assertEqual(queue.get(job["id"])["state"], "done")
        self.assertEqual(rubrics.episodes("tbilisi-today")["number"], {"last": 1, "done": 1})
        self.assertEqual(rubrics.last_state("tbilisi-today", 24835)["numbers"], ["6400"])

    def test_a_failed_job_releases_its_episode(self):
        path = pathlib.Path(self.tmp.name, "rubric-24835-number.json")
        story = rubrics.stamp(copy.deepcopy(NUMBER), "number", "tbilisi-today", "rubric-24835-number")
        story["narration"] = story["narration"].replace("6400", "6500")  # N2 fails at the check
        path.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
        store.sources_path(path).write_text(json.dumps(FIXTURES["24835"], ensure_ascii=False), encoding="utf-8")
        job, _ = queue.add(story=str(path), overrides={"rubric": "number"})
        queue.run(max_jobs=1)
        self.assertEqual(queue.get(job["id"])["state"], "failed")
        self.assertEqual(rubrics.episodes("tbilisi-today"), {})

    def test_a_story_job_must_carry_its_rubric(self):
        job, _ = queue.add(story=str(ROOT / "stories" / "24835.json"), overrides={"rubric": "number"})
        with mock.patch.object(engine, "render_story", side_effect=AssertionError("no render")):
            queue.run(max_jobs=1)
        j = queue.get(job["id"])
        self.assertEqual(j["state"], "failed")
        self.assertIn("stamp it first", j["error"])

    def test_engine_rubrics_stamp_and_list(self):
        path = pathlib.Path(self.tmp.name, "a.json")
        a = {k: v for k, v in AGREE.items() if k not in ("rubric", "episode")}
        a["scenes"] = copy.deepcopy(a["scenes"])
        for k in ("items", "n", "total"):
            a["scenes"][1].pop(k)
        path.write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
        out = []
        with mock.patch.object(engine, "out", side_effect=lambda o, c=0: out.append(o) or c):
            code = engine.main(["rubrics", "stamp", str(path), "--rubric", "agree", "--sources",
                                str(ROOT / "tests" / "fixtures" / "rubric-agree.sources.json")])
            self.assertEqual(code, 0, out)
            engine.main(["rubrics", "list"])
        self.assertEqual(out[0]["chip"], "ადასტურებს 4 გამოცემა · #1")
        self.assertEqual(out[1]["episodes"], {"agree": {"last": 1, "done": 0}})
        stamped = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stamped["scenes"][1]["n"], 4)

    def test_an_old_database_is_untouched(self):
        con = sqlite3.connect(pathlib.Path(self.tmp.name) / "veasy.db")
        con.execute("create table jobs(id text primary key)")
        con.commit()
        con.close()
        self.assertEqual(rubrics.reserve("tbilisi-today", "number", "x"), 1)


class Daily(Home):
    def test_rubric_plan_and_slots(self):
        from ops import daily
        rows = [{"id": 1}, {"id": 2}, {"id": 3}]
        data = {1: {"cluster": {"id": 1, "sources": ["ა", "ბ", "გ", "დ"], "category": "world"},
                    "articles": FIXTURES["24725"]},
                2: {"cluster": {"id": 2, "sources": ["ა", "ბ", "გ", "დ"], "category": "society"},
                    "articles": FIXTURES["24835"]},
                3: {"cluster": {"id": 3, "sources": AGREE["sources"], "category": "education"},
                    "articles": AGREE_SOURCES, "members": [{"outlet": o, "text": t}
                                                           for o, t in zip(AGREE["sources"], AGREE_SOURCES)]}}
        chosen, parts, found = daily.rubric_plan(rows, [], "tbilisi-today", fetch=lambda r: data[r["id"]])
        self.assertEqual(chosen, {"3": "agree", "2": "number"})
        self.assertEqual(parts, {})
        self.assertEqual(found["3"]["agreed"], 3)
        self.assertGreater(daily.slot_priority("digest"), daily.slot_priority("number"))


class Programs(unittest.TestCase):
    def test_the_digest_program(self):
        p = programs.get("digest")
        self.assertEqual((p["writer"], p["sources"], p["rules"], p["format"]), ("digest", ["stories"], "news", "digest"))
        with self.assertRaises(programs.ProgramError):
            programs.validate("x", {**load("programs/digest.json"), "writer": "magic"})


if __name__ == "__main__":
    unittest.main()
