"""Programs (any source in) and their rule tiers: claims and law. The news program stays exactly what it was."""
import copy
import hashlib
import json
import os
import pathlib
import sqlite3
import tempfile
import unittest
from unittest import mock

from tt_shorts import claims_check, engine, meta, programs, queue, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAW = json.loads((ROOT / "stories" / "law-constitution-17.json").read_text(encoding="utf-8"))
LAW_SOURCES = json.loads((ROOT / "tests" / "fixtures" / "law-constitution-17.sources.json").read_text(encoding="utf-8"))
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "sources.json").read_text(encoding="utf-8"))
ARTICLE = json.loads((ROOT / "tests" / "fixtures" / "ordo" / "constitution-17.json").read_text(encoding="utf-8"))


def law(**changes):
    s = copy.deepcopy(LAW)
    s.update(changes)
    return s


def rules(problems):
    return sorted({p.split(":")[0] for p in problems})


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name, "SHORTS_KAEASY_LEARN": "0"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class Loading(unittest.TestCase):
    def test_builtins(self):
        every = programs.load_all()
        self.assertEqual(set(every) >= {"news", "explainer", "law", "blog"}, True)
        news = every["news"]
        self.assertEqual((news["rules"], news["scenes"], news["brief"], news["publish"]), ("news", "all", None, "auto"))
        self.assertEqual(news["sources"][0], "tbilisi-today")  # the default source, as before programs
        self.assertEqual((every["law"]["rules"], every["law"]["category"], every["law"]["publish"],
                          every["law"]["link"], every["law"]["sources"][0]), ("law", "law", "review", "source", "ordo"))
        self.assertEqual(every["explainer"]["rules"], "claims")
        self.assertEqual((every["blog"]["sources"][0], every["blog"]["rules"]), ("sitech", "claims"))
        self.assertNotIn("sources", every["law"]["scenes"])  # one document: no "N outlets" scene
        for p in every.values():
            self.assertTrue(p["brief"] is None or programs.brief(p))

    def test_options_list_programs_and_sources(self):
        o = engine.options()
        self.assertEqual(o["programs"]["law"]["rules"], "law")
        self.assertIn("ordo", o["sources"])
        self.assertIn("explainer", o["formats"])

    def test_a_program_is_a_json_file_and_bad_ones_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "briefs").mkdir()
            (d / "briefs" / "guide.md").write_text("GUIDE: explain a city guide.", encoding="utf-8")
            (d / "news.json").write_text((ROOT / "programs" / "news.json").read_text(encoding="utf-8"), encoding="utf-8")
            good = {"label": "გზამკვლევი", "sources": ["url", "pdf"], "brief": "guide.md", "scenes": ["hook", "where", "end"],
                    "rules": "claims", "format": "news", "publish": "review"}
            (d / "guide.json").write_text(json.dumps(good), encoding="utf-8")
            with mock.patch.object(programs, "DIR", d), mock.patch.object(programs, "BRIEFS", d / "briefs"):
                p = programs.get("guide")
                self.assertEqual((p["link"], p["category"]), ("brand", None))
                self.assertIn("GUIDE", programs.brief(p))
                bad = [{"sources": ["telegram"]}, {"rules": "vibes"}, {"scenes": ["hook", "opinion", "end"]},
                       {"scenes": ["where", "end"]}, {"brief": "missing.md"}, {"publish": "now"}, {"format": "neon"},
                       {"link": "qr"}, {"colour": "red"}, {"category": "Law Stuff"}]
                for change in bad:
                    (d / "guide.json").write_text(json.dumps({**good, **change}), encoding="utf-8")
                    with self.assertRaises(programs.ProgramError, msg=change):
                        programs.load_all()
                (d / "guide.json").unlink()
                (d / "news.json").unlink()
                with self.assertRaises(programs.ProgramError):  # the default must exist
                    programs.load_all()

    def test_sources_a_program_takes(self):
        programs.check_source(programs.get("law"), "ordo")
        with self.assertRaises(programs.ProgramError):
            programs.check_source(programs.get("law"), "tbilisi-today")
        with self.assertRaises(programs.ProgramError):
            programs.check_source(programs.get("news"), "url")  # news stays a cluster program


class Tiers(unittest.TestCase):
    SRC = ["ანგარიში\nკომპანია Acme-ის ცნობით, 2025 წელს 1200 თანამშრომელი ჰყავდა. დირექტორმა ნინო ბერიძემ განაცხადა: "
           "„ვზრდით გუნდს“. ეს ისტორიული გადაწყვეტილებაა."]

    def story(self, narration, scenes=None):
        return {"narration": narration, "scenes": scenes or [{"type": "hook", "at": narration.split()[0], "lines": ["x"]}]}

    def test_claims_clean(self):
        s = self.story("Acme-ს 2025 წელს 1200 თანამშრომელი ჰყავდა. ნინო ბერიძის თქმით, „ვზრდით გუნდს“.",
                       [{"type": "hook", "at": "Acme-ს", "lines": ["x"]},
                        {"type": "who", "at": "ნინო", "items": [{"name": "ნინო ბერიძე", "role": "დირექტორი"}]}])
        self.assertEqual(claims_check.problems(s, self.SRC, "claims"), [])

    def test_a_number_not_in_the_source_is_rejected(self):  # N2, on screen too
        s = self.story("Acme-ს 1300 თანამშრომელი ჰყავდა.",
                       [{"type": "stat", "at": "Acme-ს", "value": 15, "label": "ოფისი"}])
        p = claims_check.problems(s, self.SRC, "claims")
        self.assertEqual(rules(p), ["N2"])
        self.assertEqual(sorted(x.split()[2] for x in p), ["1300", "15"])

    def test_names_quotes_days_and_opinion(self):
        s = self.story("Globex-მა გუშინ თქვა: „გუნდს ვამცირებთ“. სკანდალური ამბავია.",
                       [{"type": "who", "at": "Globex-მა", "items": [{"name": "გიორგი კაპანაძე", "role": "მენეჯერი"}]}])
        self.assertEqual(rules(claims_check.problems(s, self.SRC, "claims")), ["C1", "N1", "N3", "N4"])

    def test_the_documents_own_words_are_not_opinion(self):  # „ისტორიული“ is the source's word
        self.assertEqual(claims_check.problems(self.story("ეს ისტორიული გადაწყვეტილებაა."), self.SRC, "claims"), [])
        self.assertEqual(rules(claims_check.problems(self.story("ეს ისტორიული გადაწყვეტილებაა."), [], "claims")),
                         ["N1"])

    def test_brand_names_and_outlets_are_allowed(self):
        s = self.story("Acme-ს 1200 თანამშრომელი ჰყავდა. მეტი სიახლისთვის გამოიწერე SiTech.")
        self.assertEqual(rules(claims_check.problems(s, self.SRC, "claims")), ["C1"])
        self.assertEqual(claims_check.problems(s, self.SRC, "claims", allow=["SiTech"]), [])

    def test_the_law_demo_passes(self):
        self.assertEqual(claims_check.problems(LAW, LAW_SOURCES, "law"), [])
        self.assertEqual(engine.check_story(LAW, LAW_SOURCES), [])

    def test_advice_is_rejected(self):  # L2
        for advice in ("თუ დაგდევნიან, უნდა მიმართო სასამართლოს.", "შეგიძლია ცენზურა გაასაჩივრო.",
                       "გირჩევ, ეს მუხლი იცოდე.", "შენი უფლებაა, თავისუფლად გაავრცელო ინფორმაცია.",
                       "აუცილებლად მიმართე ადვოკატს."):
            s = law(narration=LAW["narration"].replace("სრული ტექსტი", f"{advice} სრული ტექსტი"))
            p = claims_check.problems(s, LAW_SOURCES, "law")
            self.assertEqual(rules(p), ["L2"], advice)
        s = law(scenes=[*LAW["scenes"][:3], {**LAW["scenes"][3], "headline": "მიმართე სასამართლოს"}, LAW["scenes"][4]])
        self.assertEqual(rules(claims_check.problems(s, LAW_SOURCES, "law")), ["L2"])  # on screen too

    def test_words_that_only_look_like_advice_pass(self):  # არჩევნები is not რჩევა; the CTA is not advice
        s = law(narration=LAW["narration"].replace("სრული ტექსტი", "არჩევნები და არჩევა აქ არ არის. სრული ტექსტი"))
        self.assertEqual(claims_check.problems(s, LAW_SOURCES, "law"), [])

    def test_the_article_number_must_be_on_screen(self):  # L1
        scenes = copy.deepcopy(LAW["scenes"])
        scenes[0]["kicker"] = "კონსტიტუცია"
        scenes[1]["via"] = "პირველი პუნქტი"
        p = claims_check.problems(law(scenes=scenes), LAW_SOURCES, "law")
        self.assertEqual(rules(p), ["L1"])
        no_doc = law(source={"name": "text", "ref": "x.json"})  # the number is read from the article's heading
        self.assertEqual(claims_check.problems(no_doc, LAW_SOURCES, "law"), [])

    def test_the_act_must_be_named(self):  # L3
        s = law(narration=LAW["narration"].replace("საქართველოს კონსტიტუციის 17-ე მუხლი", "17-ე მუხლი"))
        s["scenes"][0]["at"] = "17-ე მუხლი"
        self.assertEqual(rules(claims_check.problems(s, LAW_SOURCES, "law")), ["L3"])

    def test_engine_check_uses_the_programs_tier(self):
        s = law(narration=LAW["narration"].replace("17-ე", "18-ე"))
        self.assertIn("N2: number 18 is not in the source document", engine.check_story(s, LAW_SOURCES))
        s = law(scenes=[*LAW["scenes"][:3], {"type": "bars", "at": "ამ უფლებათა", "unit": "x",
                                             "items": [{"label": "ა", "value": 17}, {"label": "ბ", "value": 1}]},
                        LAW["scenes"][4]])
        self.assertTrue(any("not a scene of program 'law'" in x for x in engine.check_story(s, LAW_SOURCES)))
        self.assertTrue(any("unknown program" in x for x in engine.check_story(law(program="gossip"), LAW_SOURCES)))
        long = law(narration=LAW["narration"].replace("სრული ტექსტი", "ეს წინადადება ძალიან გრძელია. " * 6
                                                      + "სრული ტექსტი"))
        self.assertTrue(any(x.startswith("timing:") and "program law" in x for x in engine.check_story(long, LAW_SOURCES)))

    def test_news_stories_are_checked_as_before(self):
        for sid in ("24725", "24835"):
            s = json.loads((ROOT / "stories" / f"{sid}.json").read_text(encoding="utf-8"))
            self.assertNotIn("program", s)
            self.assertEqual(engine.check_story(s, FIXTURES[sid]), [])
        s["narration"] = s["narration"].replace("6400", "7000")
        self.assertIn("N2: number 7000 is not in any source article", engine.check_story(s, FIXTURES["24835"]))


class Links(unittest.TestCase):
    def test_a_law_video_links_to_the_article_and_news_to_the_brand(self):
        self.assertEqual(meta.links(LAW), ("matsne.gov.ge", LAW["link"]["qr"]))
        news = {**json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8")), "link": LAW["link"]}
        shown, opens = meta.links(news)  # a news story never takes a link from the story file
        self.assertEqual(shown, "tbilisi.today/stories/24835")
        self.assertTrue(opens.startswith("https://tbilisi.today/stories/24835?"))
        self.assertEqual(meta.links(law(link={"display": "x", "qr": "javascript:alert(1)"}))[0],
                         "tbilisi.today/stories/constitution-17")

    def test_stamp_sets_the_data_and_drops_the_writers_link(self):
        cluster = {"id": "constitution-17", "url": LAW["link"]["qr"], "title": "საქართველოს კონსტიტუცია", "article": "17"}
        s = programs.stamp({"link": {"display": "evil.example", "qr": "https://evil.example"}, "category": "politics"},
                           programs.get("law"), cluster)
        self.assertEqual((s["program"], s["category"], s["link"]["display"], s["source"]["article"]),
                         ("law", "law", "matsne.gov.ge", "17"))
        news = programs.stamp({"link": {"qr": "https://evil.example"}}, programs.get("news"), cluster)
        self.assertNotIn("link", news)
        self.assertNotIn("program", news)


class Writer(Home):
    def setUp(self):
        super().setUp()
        self.ordo = tempfile.TemporaryDirectory()
        fixture = ROOT / "tests" / "fixtures" / "ordo" / "constitution-17.json"
        pathlib.Path(self.ordo.name, "matsne_api.py").write_text(
            "import json, pathlib\n"
            "class MatsneAPI:\n"
            "    def get_article(self, article, law='', doc_id=0, part=None, **kw):\n"
            f"        r = json.loads(pathlib.Path({str(fixture)!r}).read_text(encoding='utf-8'))\n"
            "        r.pop('_fetched', None)\n"
            "        return r\n", encoding="utf-8")
        self.env2 = mock.patch.dict(os.environ, {"ORDO_DIR": self.ordo.name})
        self.env2.start()
        from tt_shorts.sources import ordo
        ordo.reset()

    def tearDown(self):
        self.env2.stop()
        self.ordo.cleanup()
        from tt_shorts.sources import ordo
        ordo.reset()
        super().tearDown()

    def test_the_law_prompt_has_the_brief_and_only_the_programs_scenes(self):
        from tt_shorts.sources import ordo
        data = ordo.fetch("constitution:17")
        text = programs.prompt(programs.get("law"), data["cluster"], data["articles"], brand="tbilisi-today")
        self.assertIn("LAW: one provision", text)
        self.assertIn("მუხლი: 17", text)
        self.assertIn("დაუშვებელია ადამიანის დევნა", text)
        self.assertNotIn('"type": "bars"', text)
        self.assertNotIn('"category"', text)  # the program sets it
        self.assertNotIn("## N. News", text)  # the news rules are the news program's
        self.assertNotIn("70-95 words", text)  # the brief sets the length
        blog = programs.prompt(programs.get("blog"), data["cluster"], data["articles"], brand="sitech")
        line = next(x for x in blog.splitlines() if x.lstrip().startswith('"category"'))
        self.assertIn("|security|", line)  # the pack's own categories
        self.assertIn("ბლოგი", blog)

    def test_write_story_runs_the_program_end_to_end(self):
        answer = {k: v for k, v in LAW.items() if k not in ("id", "date", "sources", "source", "program", "brand")}
        answer["link"] = {"display": "evil.example", "qr": "https://evil.example"}  # a writer never sets the link
        prompts = []

        def model(prompt, *a, **k):
            prompts.append(prompt)
            return json.dumps(answer, ensure_ascii=False)
        with mock.patch.object(writer, "_call", side_effect=model):
            result = engine.write_story(None, "constitution:17", "tbilisi-today", program="law")
        self.assertEqual(result["problems"], [])
        self.assertEqual((result["program"], result["rules"], result["publish"]), ("law", "law", "review"))
        path = pathlib.Path(result["story"])
        self.assertEqual(path.name, "law-constitution-17.json")
        story = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual((story["id"], story["program"], story["category"], story["sources"]),
                         ("constitution-17", "law", "law", ["matsne.gov.ge"]))
        self.assertEqual(story["link"], {"display": "matsne.gov.ge", "qr": ARTICLE["url"]})
        self.assertEqual((story["source"]["name"], story["source"]["article"]), ("ordo", "17"))
        self.assertIn("LAW: one provision", prompts[0])
        self.assertEqual([s["type"] for s in story["scenes"]], [s["type"] for s in LAW["scenes"]])

    def test_a_program_draft_with_advice_goes_back_for_repair(self):
        bad = {k: v for k, v in LAW.items() if k not in ("id", "date", "sources", "source", "program", "brand")}
        bad["narration"] = bad["narration"].replace("სრული ტექსტი", "უნდა მიმართო სასამართლოს. სრული ტექსტი")
        good = {k: v for k, v in LAW.items() if k not in ("id", "date", "sources", "source", "program", "brand")}
        answers = iter([bad, good, good])
        prompts = []

        def model(prompt, *a, **k):
            prompts.append(prompt)
            return json.dumps(next(answers), ensure_ascii=False)
        with mock.patch.object(writer, "_call", side_effect=model):
            result = engine.write_story("ordo", "constitution:17", program="law")
        self.assertEqual(result["problems"], [])
        self.assertIn("L2:", prompts[1])  # the repair call names the broken rule


class Queue(Home):
    OLD_SCHEMA = """create table jobs(id text primary key, name text, brand text, source text, ref text, format text,
      overrides text, story text, state text, priority int default 0, attempts int default 0, error_class text,
      error text, result text, created text, updated text, not_before real default 0)"""

    def test_news_job_ids_are_unchanged(self):
        old = hashlib.sha256(json.dumps({"brand": "tbilisi-today", "source": "tbilisi-today", "ref": "24725",
                                         "format": "news", "overrides": {}}, sort_keys=True).encode()).hexdigest()[:12]
        job, _ = queue.add(source="tbilisi-today", ref=24725)
        self.assertEqual((job["id"], job["program"]), (old, "news"))

    def test_the_program_is_in_the_id_and_the_name(self):
        news, _ = queue.add(source="text", ref="doc.json")
        explainer, created = queue.add(source="text", ref="doc.json", program="explainer")
        self.assertTrue(created)
        self.assertNotEqual(news["id"], explainer["id"])
        self.assertEqual((explainer["program"], explainer["format"]), ("explainer", "explainer"))
        law_job, _ = queue.add(ref="constitution:17", program="law")
        self.assertEqual((law_job["source"], law_job["name"]), ("ordo", "tbilisi-today-law-constitution-17-explainer"))
        self.assertEqual(queue.add(ref="constitution:17", program="law")[0]["id"], law_job["id"])
        with self.assertRaises(programs.ProgramError):
            queue.add(source="tbilisi-today", ref=1, program="law")  # law doesn't take clusters
        with self.assertRaises(programs.ProgramError):
            queue.add(source="url", ref="https://x.ge", program="gossip")

    def test_a_story_job_takes_the_storys_program(self):
        job, _ = queue.add(story=str(ROOT / "stories" / "law-constitution-17.json"))
        self.assertEqual((job["program"], job["format"], job["brand"]), ("law", "explainer", "tbilisi-today"))
        with self.assertRaises(ValueError):
            queue.add(story=str(ROOT / "stories" / "law-constitution-17.json"), program="blog")

    def test_an_old_database_gets_the_column(self):
        con = sqlite3.connect(pathlib.Path(self.tmp.name) / "veasy.db")
        con.execute(self.OLD_SCHEMA)
        con.execute("insert into jobs(id, name, state, created) values('abc', 'old-job', 'done', '2026-11-01')")
        con.commit()
        con.close()
        self.assertEqual(queue.get("abc")["program"], "news")
        job, _ = queue.add(ref="constitution:17", program="law")
        self.assertEqual(queue.get(job["id"])["program"], "law")
        queue.db().close()  # opening it again is a no-op

    def test_a_review_program_is_held_after_qa(self):
        job, _ = queue.add(story=str(ROOT / "stories" / "law-constitution-17.json"))
        with mock.patch.object(engine, "render_story", return_value={"file": "/x.mp4", "problems": []}), \
                mock.patch.object(engine, "check_story", return_value=[]), \
                mock.patch.object(engine, "qa_file", return_value={"problems": []}):
            queue.run(max_jobs=1)
        j = queue.get(job["id"])
        self.assertEqual((j["state"], j["error_class"], j["result"]["program"]), ("held", "review", "law"))


STORY = json.loads((ROOT / "stories" / "bipi-draws.json").read_text(encoding="utf-8"))


def tale(**changes):
    s = copy.deepcopy(STORY)
    s.update(changes)
    return s


class StoryTier(unittest.TestCase):
    """Fiction (program story): no articles to compare with; S1 says no real person is named as doing something."""

    def test_the_program_is_fiction_on_hyperframes(self):
        p = programs.get("story")
        self.assertEqual((p["rules"], p["engine"], p["review"], p["chrome"]), ("story", "hyperframes", "always", "film"))
        self.assertIn("story", claims_check.TIERS)

    def test_the_demo_tale_passes_every_check(self):
        self.assertEqual(engine.check_story(STORY), [])
        self.assertEqual(programs.rule_problems(STORY, []), [])

    def test_a_latin_name_or_a_surname_that_is_no_character(self):
        bad = tale(narration=STORY["narration"].replace("ბიპი არ დანებდა", "ბიპი და Elon არ დანებდნენ"))
        self.assertIn("S1", rules(programs.rule_problems(bad, [])))
        bad = tale(narration=STORY["narration"].replace("ბიპი არ დანებდა", "ნიკა ბერიძე არ დანებდა"))
        self.assertTrue(any("ბერიძე" in p for p in programs.rule_problems(bad, [])))
        bad = tale(narration=STORY["narration"].replace("ბიპი არ დანებდა", "გიორგი კაპანაძემ თქვა"))
        self.assertTrue(any("კაპანაძემ" in p for p in programs.rule_problems(bad, [])))

    def test_a_character_may_be_named_in_any_case(self):
        ok = tale(narration=STORY["narration"].replace("ბიპი არ დანებდა", "ბიპიმ და ლუკა ბერიძემ ხატეს"),
                  characters=["ბიპი", "ლუკა ბერიძე"])
        self.assertEqual(claims_check.fiction(ok, allow=["SiTech"]), [])

    def test_a_real_office_or_a_person_in_who(self):
        bad = tale(narration=STORY["narration"].replace("პატარა რობოტი", "პრეზიდენტის რობოტი"))
        self.assertTrue(any("პრეზიდენტ" in p for p in programs.rule_problems(bad, [])))
        bad = tale(scenes=STORY["scenes"][:1] + [{"type": "who", "at": "პირველი წრე",
                                                   "items": [{"name": "ნინო", "role": "მასწავლებელი"}]}] + STORY["scenes"][2:])
        self.assertTrue(any("'ნინო'" in p for p in claims_check.fiction(bad)))

    def test_its_limit_a_bare_first_name_is_not_caught(self):  # documented: the review catches it
        quiet = tale(narration=STORY["narration"].replace("ბიპი არ დანებდა", "ბიპი და ნიკა არ დანებდნენ"))
        self.assertEqual(claims_check.fiction(quiet, allow=["SiTech"]), [])

    def test_the_brand_names_are_allowed(self):
        self.assertEqual(claims_check.fiction(tale(), allow=["SiTech"]), [])
        self.assertIn("S1", rules(claims_check.fiction(tale())))  # SiTech in the CTA, without the brand allowed


if __name__ == "__main__":
    unittest.main()
