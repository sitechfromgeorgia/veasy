"""Directors: code assigns each video a creative direction before writing (owner, 2026-11-02: "we give the AI
brushes, and separate agents each choose a different direction"); a director never touches facts or rules."""
import json
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, directors, engine, variety, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "sources.json").read_text(encoding="utf-8"))


def typical(family, **over):
    """Typical facts of a story of a family (what directors.facts gives for an ordinary cluster)."""
    base = {"numbers": 4, "quantities": 1, "percents": 0, "dates": 1, "times": 0, "places": 1, "regions": 1,
            "quotes": 1, "speakers": 1, "icons": 1, "deaths": False, "family": family}
    base.update(over)
    base["facts"] = base["quantities"] + base["dates"] + base["places"] + base["quotes"]
    return base


class Data(unittest.TestCase):
    def test_the_eight_directors_validate(self):
        every = directors.load_all()
        self.assertEqual(set(every), {"data", "map", "type", "draw", "chronicle", "witness", "brief", "single"})
        for name, d in every.items():
            self.assertRegex(d["label"], r"[ა-ჰ]", name)
            self.assertTrue(6 <= len(d["brief"]) <= 10, name)
            self.assertTrue(set(d["scenes"]) <= set(engine.SCENES) | set(directors.PLANNED) | set(directors.DEVICES),
                            name)
            self.assertTrue(set(d["hooks"]) <= set(variety.OPTIONS["hook"]), name)
            self.assertTrue(set(d["motifs"]) <= set(variety.OPTIONS["motif"]), name)
            self.assertTrue(set(d["enters"]) <= set(variety.OPTIONS["enter"]), name)
            types = directors.scene_types(d)
            self.assertEqual((types[0], types[-1]), ("hook", "end"))
            self.assertFalse(set(types) & set(directors.planned(d)), name)  # planned brushes wait until they exist

    def test_bad_directors_are_refused(self):
        good = json.loads((ROOT / "directors" / "data.json").read_text(encoding="utf-8"))
        for bad in ({"scenes": {"opinion": 1, "stat": 1, "bars": 1}}, {"current": "down"}, {"brief": ["one line"]},
                    {"motion": {**good["motion"], "stiffness": 900}}, {"eligible": [{"vibes": 2}]},
                    {"count": [2, 9]}, {"hooks": ["spiral"]}, {"label": "The Number"}, {"gates": ["balance"]}):
            with self.assertRaises(directors.DirectorError, msg=str(bad)):
                directors.validate("data", {**good, **bad})
        with self.assertRaises(directors.DirectorError):
            directors.validate("other", good)  # the id is its file name

    def test_a_director_may_prefer_themes_by_name(self):  # never colors: the pack's themes (brand.json)
        self.assertEqual(directors.get("draw")["themes"], ["light"])  # a drawing on paper
        self.assertEqual(directors.get("data")["themes"], [])
        good = json.loads((ROOT / "directors" / "data.json").read_text(encoding="utf-8"))
        for bad in ({"themes": "light"}, {"themes": ["#FFFFFF"]}, {"themes": ["Light"]}):
            with self.assertRaises(directors.DirectorError, msg=str(bad)):
                directors.validate("data", {**good, **bad})

    def test_a_planned_brush_is_offered_once_it_exists(self):
        raw = json.loads((ROOT / "directors" / "data.json").read_text(encoding="utf-8"))
        with mock.patch.object(directors, "PLANNED", ("tally",)):
            d = directors.validate("data", {**raw, "scenes": {**raw["scenes"], "tally": 1}})
            self.assertIn("tally", directors.planned(d))
            self.assertNotIn("tally", directors.scene_types(d))
            with mock.patch.dict(engine.SCENES, {"tally": (["items"], [], "facts in N outlets")}):
                self.assertIn("tally", directors.scene_types(d))

    def test_the_brushes_once_planned_are_offered_and_the_marker_is_a_device(self):
        d = directors.get("data")
        self.assertIn("share", directors.scene_types(d))  # share, rail and compare exist since the brush kit
        self.assertNotIn("marker", directors.scene_types(d))
        self.assertNotIn("marker", directors.planned(d))
        self.assertIn('"em"', directors.brief_block(d))  # the marker: the writer marks the words that matter

    def test_options_list_the_directors(self):
        o = engine.options()
        self.assertEqual(set(o["directors"]["directors"]), set(directors.names()))
        self.assertEqual(o["directors"]["planned"], list(directors.PLANNED))


class Facts(unittest.TestCase):
    def test_the_gas_cut(self):  # 24835: 6400 subscribers, 2 Nov 22:00 -> 3 Nov 10:00, Vazisubani, gas
        f = directors.facts(FIXTURES["24835"], "society")
        self.assertEqual(f["found"]["quantities"], ["6400"])  # dates and times are not quantities
        self.assertEqual(f["found"]["times"], ["10:00", "22:00"])
        self.assertEqual(f["dates"], 2)
        self.assertIn("ვაზისუბანი", f["found"]["places"])
        self.assertEqual(f["quotes"], 0)  # „თბილისი ენერჯი“ is a name in quotes, not a quote
        self.assertIn("flame", f["found"]["icons"])
        self.assertTrue({"data", "map", "brief", "chronicle"} <= set(directors.eligible(f)))

    def test_a_quote_and_its_speaker(self):  # 24725: „…“, – განაცხადა ზელენსკიმ.
        f = directors.facts(FIXTURES["24725"], "world")
        self.assertEqual(f["found"]["speakers"], ["ზელენს"])
        self.assertIn("witness", directors.eligible(f))
        self.assertNotIn("type", directors.eligible(f))  # world is hard news

    def test_every_family_has_two_directors(self):
        for fam in brand.FAMILIES:
            for f in (typical(fam), typical(fam, quotes=0, speakers=0), typical(fam, places=0, regions=0)):
                self.assertGreaterEqual(len(directors.eligible(f)), 2, (fam, f))

    def test_hard_news_gates(self):
        for fam in ("politics", "crime"):
            self.assertNotIn("type", directors.eligible(typical(fam)))
            self.assertNotIn("brief", directors.eligible(typical(fam)))
        self.assertNotIn("type", directors.eligible(typical("sports", deaths=True)))
        self.assertIn("type", directors.eligible(typical("sports")))
        self.assertNotIn("draw", directors.eligible(typical("crime")))
        self.assertNotIn("data", directors.eligible(typical("crime", quantities=3, deaths=True)))
        self.assertNotIn("single", directors.eligible(typical("society", quantities=3, dates=2)))  # too many facts

    def test_witness_shows_both_sides(self):
        f = typical("politics", quotes=2, speakers=2)
        one = {"director": "witness", "scenes": [{"type": "hook"}, {"type": "quote", "by": "ა"}, {"type": "end"}]}
        self.assertTrue(directors.story_problems(one, f))
        two = {**one, "scenes": one["scenes"][:2] + [{"type": "quote", "by": "ბ"}, {"type": "end"}]}
        self.assertEqual(directors.story_problems(two, f), [])
        self.assertEqual(directors.story_problems(one, typical("politics")), [])  # one side quoted: one is enough


class Assignment(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def test_a_run_rotates_the_eligible_directors_evenly(self):
        f = directors.facts(FIXTURES["24835"], "society")
        pool = directors.eligible(f)
        got = []
        for i in range(3 * len(pool)):
            d = variety.direct("tbilisi-today", 5000 + i, f)
            variety.record("tbilisi-today", 5000 + i, "cards", {"director": d}, ["hook", "end"])
            got.append(d)
        self.assertEqual(set(got), set(pool))
        counts = [got.count(n) for n in pool]
        self.assertLessEqual(max(counts) - min(counts), 1, counts)
        self.assertEqual(variety.direct("tbilisi-today", 5000, f), got[0])  # a story keeps its director
        self.assertEqual(variety.direct("tbilisi-today", 9, f, forced="witness"), "witness")
        with self.assertRaises(directors.DirectorError):
            variety.direct("tbilisi-today", 9, f, forced="nobody")

    def test_the_director_is_code_owned(self):
        s = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))
        self.assertEqual(engine.structure_problems({**s, "director": "map"}), [])
        self.assertTrue(any("unknown director" in p for p in engine.structure_problems({**s, "director": "auteur"})))

    def test_the_writer_gets_the_brief_and_only_its_scenes(self):
        f = directors.facts(FIXTURES["24835"], "society")
        d = directors.get("data")
        p = writer._prompt({"headline": "x"}, FIXTURES["24835"], director=d, facts=f)
        self.assertIn(d["brief"][0], p)
        self.assertIn("6400", p.split("Direction for this video")[1])
        shown = set(re.findall(r'\{"type": "([\w-]+)"', p))
        self.assertEqual(shown, set(directors.scene_types(d)) - {"sources"})  # sources has no example line
        plain = writer._prompt({"headline": "x"}, FIXTURES["24835"])
        self.assertNotIn("Direction for this video", plain)
        # sources, agree and chapter have no example line (code fills them; agree comes with its rubric's brief)
        self.assertEqual(set(re.findall(r'\{"type": "([\w-]+)"', plain)), set(engine.SCENES) - {"sources", "agree", "chapter"})

    def test_a_writer_set_director_is_dropped(self):
        answer = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))
        answer = {k: v for k, v in answer.items() if k not in ("id", "date", "sources")}
        answer["director"] = "type"
        with mock.patch.object(writer, "_call", return_value=json.dumps(answer, ensure_ascii=False)), \
                mock.patch.object(writer, "_edit", return_value=None), \
                mock.patch.object(writer, "_anchors_ok", return_value=True):
            story = writer.write({"id": 24835, "category": "society"}, FIXTURES["24835"], repairs=0,
                                 run_checks=lambda s, a, c: [])
        self.assertNotIn("director", story)


class Demo(unittest.TestCase):
    """24835 (the gas cut) hand-written under three directors: the same facts, three different films."""
    NAMES = ("data", "map", "brief")

    def stories(self):
        return {n: json.loads((ROOT / "stories" / f"24835-{n}.json").read_text(encoding="utf-8")) for n in self.NAMES}

    def test_each_passes_check_with_the_articles(self):
        for name, s in self.stories().items():
            self.assertEqual(s["director"], name)
            self.assertEqual(engine.check_story(s, FIXTURES["24835"]), [], name)
            self.assertEqual(directors.warnings(s), [], name)  # its own scene types and count
            with mock.patch("sys.stdout"):  # the CLI takes the fixtures' {story id: articles} map too
                self.assertEqual(engine.main(["check", str(ROOT / "stories" / f"24835-{name}.json"), "--sources",
                                              str(ROOT / "tests" / "fixtures" / "sources.json")]), 0, name)

    def test_three_different_films_of_the_same_facts(self):
        every = self.stories()
        orders = {n: tuple(x["type"] for x in s["scenes"]) for n, s in every.items()}
        self.assertEqual(len(set(orders.values())), 3, orders)
        self.assertEqual(len({s["narration"].split(".")[0] for s in every.values()}), 3)  # three different hooks
        for name, s in every.items():
            for fact in ("6400", "ვარკეთილ", "ვაზისუბან", "თბილისი ენერჯის", "გაზსადენზე", "2 ნოემბრის", "3 ნოემბრის"):
                self.assertIn(fact, s["narration"], (name, fact))


class Motion(unittest.TestCase):
    def test_the_style_carries_motion_and_a_current(self):
        for name, d in directors.load_all().items():
            st = directors.style(d)
            self.assertEqual(st["flow"], list(directors.CURRENTS[d["current"]]))
            self.assertEqual(set(st["motion"]), set(directors.MOTION))

    def test_props_carry_the_director_and_pick_inside_it(self):
        from tt_shorts import props
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            _, p = props.build(str(ROOT / "stories" / "24835.json"), "cards", "silent", music="off", director="map")
            d = directors.get("map")
            self.assertEqual((p["style"]["director"], p["style"]["current"], p["style"]["flow"]), ("map", "left", [-1, 0]))
            self.assertEqual(p["style"]["motion"], d["motion"])
            self.assertIn(p["style"]["hook"], d["hooks"])
            self.assertIn(p["style"]["enter"], d["enters"])
            self.assertIn(p["transition"], d["transitions"])
            _, plain = props.build(str(ROOT / "stories" / "24835.json"), "cards", "silent", music="off")
            self.assertNotIn("director", plain["style"])  # no director: today's motion, unchanged

    def test_entrances_and_cuts_never_oppose_the_current(self):
        """ui.tsx / NewsShort.tsx move a slide entrance and every directional cut along style.flow (rise and reveal
        always go up, scale and dot have no direction); no director's choice moves against its current."""
        up = (0, -1)
        moves = {"rise": up, "reveal": up, "scale": (0, 0), "expand": (0, 0), "flip": (0, 0), "drop": (0, 0)}
        tsx = (ROOT / "remotion" / "src" / "NewsShort.tsx").read_text(encoding="utf-8")
        ui = (ROOT / "remotion" / "src" / "ui.tsx").read_text(encoding="utf-8")
        self.assertTrue("flowOf" in tsx and "flowOf" in ui, "the cuts and the entrance read style.flow")
        for name, d in directors.load_all().items():
            c = directors.CURRENTS[d["current"]]
            for e in d["enters"]:
                v = c if e in ("slide", "drift") else moves[e]
                self.assertGreaterEqual(v[0] * c[0] + v[1] * c[1], 0, (name, e))
            for t in d["transitions"]:
                v = c if t in ("line", "panel", "wipe", "slide", "push", "shutter", "blind", "corner") else (0, 0)
                self.assertGreaterEqual(v[0] * c[0] + v[1] * c[1], 0, (name, t))


if __name__ == "__main__":
    unittest.main()
