"""Vignettes (tt_shorts/vignettes.py): 1-3 drawings of what the film is about, never where the news rules say none."""
import copy
import json
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import art, catalog, drawings, engine, icons, illustrator, motion_rules, vignettes, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent

STORY = {
    "id": "vg-test", "brand": "tbilisi-today", "category": "society", "lang": "ka",
    "narration": "ავტობუსის ბილეთი ძვირდება ოცდაათ თეთრამდე. სკოლის მოსწავლეები კვლავ უფასოდ იმგზავრებენ. "
                 "მეტროშიც იგივე წესი იმოქმედებს მომავალი თვიდან. დეტალები ბმულზეა.",
    "scenes": [
        {"type": "hook", "at": "ავტობუსის ბილეთი", "lines": ["ბილეთი ძვირდება"]},
        {"type": "quote", "at": "სკოლის მოსწავლეები", "text": "კვლავ უფასოდ", "by": "მერია"},
        {"type": "pair", "at": "მეტროშიც იგივე", "items": [{"title": "ავტობუსი", "sub": "ახალი ფასი"},
                                                          {"title": "მეტრო", "sub": "იგივე წესი"}]},
        {"type": "end", "at": "დეტალები ბმულზეა"},
    ],
}
SEED = next(s["svg"] for s in drawings.seeds() if s["name"] == "bridge")
MOVING = SEED + '<g class="m" style="--d:1.8s"><path d="M400 120 L560 120" stroke="INK" stroke-width="6"/></g>'
STATIC = ('<g class="s" style="--d:0.2s"><rect x="200" y="150" width="550" height="350" rx="20" stroke="INK" '
          'stroke-width="7"/></g><g class="r" style="--d:0.6s"><line x1="250" y1="250" x2="700" y2="250" stroke="MUTED"/>'
          '<line x1="250" y1="330" x2="650" y2="330" stroke="MUTED"/><line x1="250" y1="410" x2="600" y2="410" '
          'stroke="MUTED"/></g><g class="r" style="--d:1.0s"><rect x="560" y="380" width="140" height="80" rx="12" '
          'stroke="INK"/></g><circle class="p" style="--d:1.6s" cx="630" cy="420" r="14" fill="ACCENT" stroke="none"/>')


class Home(unittest.TestCase):
    """Every case runs on an empty $VEASY_HOME: the library is the seeds only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)
        self.story = copy.deepcopy(STORY)


class Picks(Home):
    def test_each_scene_draws_what_its_own_part_names(self):
        got, warnings = vignettes.plan(self.story)
        self.assertEqual({i: v["motif"] for i, v in got.items()}, {0: "bus", 1: "school", 2: "train-front"})
        self.assertEqual(warnings, [])

    def test_a_drawing_carries_no_words(self):
        got, _ = vignettes.plan(self.story)
        for v in got.values():
            self.assertNotIn("<text", v["svg"])

    def test_the_plan_is_pure(self):
        self.assertEqual(vignettes.plan(self.story), vignettes.plan(copy.deepcopy(self.story)))

    def test_never_on_the_end_card_and_at_most_max(self):
        story = self.story
        story["narration"] += " ხიდი და ქარხანა და საავადმყოფო."
        story["scenes"].insert(3, {"type": "pair", "at": "დეტალები", "items": []})
        story["scenes"][4]["at"] = "ხიდი და"
        got, _ = vignettes.plan(story)
        self.assertLessEqual(len(got), vignettes.MAX)
        self.assertNotIn(len(story["scenes"]) - 1, got)

    def test_a_motif_is_drawn_once(self):
        self.story["scenes"][2]["at"] = "მეტროშიც იგივე"
        self.story["narration"] = self.story["narration"].replace("მეტროშიც იგივე", "მეტროშიც იგივე ავტობუსის")
        got, _ = vignettes.plan(self.story)
        motifs = [v["motif"] for v in got.values()]
        self.assertEqual(len(motifs), len(set(motifs)))

    def test_a_scene_with_its_own_picture_gets_none(self):
        for t in ("sign", "where", "draw", "plate", "state", "chapter", "sources"):
            story = copy.deepcopy(self.story)
            story["scenes"][1]["type"] = t
            got, _ = vignettes.plan(story)
            self.assertNotIn(1, got, t)
        story = copy.deepcopy(self.story)
        story["scenes"][1]["media"] = {"file": "x.jpg"}
        self.assertNotIn(1, vignettes.plan(story)[0])


class Own(Home):
    def test_the_authors_drawing_comes_first_and_loses_its_labels(self):
        self.story["scenes"][2]["art"] = SEED
        got, _ = vignettes.plan(self.story)
        self.assertEqual(got[2]["source"], "story")
        self.assertNotIn("<text", got[2]["svg"])

    def test_a_failing_drawing_is_a_problem_and_the_writer_drops_it(self):
        self.story["scenes"][1]["art"] = '<circle cx="10" cy="10" r="4" stroke="INK"/>'
        self.assertTrue(vignettes.own_problems(self.story["scenes"][1]))
        got, warnings = vignettes.plan(self.story)
        self.assertNotEqual(got.get(1, {}).get("source"), "story")
        self.assertTrue(warnings)
        dropped = vignettes.drop_bad(self.story)
        self.assertNotIn("art", dropped["scenes"][1])
        self.assertIn("art", self.story["scenes"][1])  # the story itself is not changed

    def test_art_on_a_scene_that_shows_its_own_picture_is_a_problem(self):
        self.assertTrue(vignettes.own_problems({"type": "end", "art": SEED}))
        self.assertEqual(vignettes.own_problems({"type": "pair", "art": SEED}), [])

    def test_the_engine_checks_a_scenes_art(self):
        s = {"type": "pair", "at": "x", "items": [{"title": "a", "sub": "b"}, {"title": "c", "sub": "d"}],
             "art": "<g><circle cx='1' cy='1' r='2' stroke='INK'/></g>"}
        self.assertTrue(any(p.startswith("art:") for p in engine.shape_problems(s)))
        s["art"] = SEED
        self.assertFalse(any(p.startswith("art:") for p in engine.shape_problems(s)))


class Refused(Home):
    def test_never_for_crime_incidents_or_deaths(self):
        for patch in ({"category": "crime"}, {"category": "incident"}):
            story = {**self.story, **patch}
            self.assertEqual(vignettes.plan(story)[0], {}, patch)
        story = copy.deepcopy(self.story)
        story["narration"] = story["narration"].replace("დეტალები ბმულზეა", "ავარიაში ორი ადამიანი დაიღუპა. დეტალები ბმულზეა")
        self.assertEqual(vignettes.plan(story)[0], {})

    def test_a_film_with_a_thread_keeps_its_seats(self):
        with mock.patch.object(vignettes.thread, "has", lambda story: True):
            self.assertEqual(vignettes.plan(self.story)[0], {})


class Props(Home):
    def _props(self):
        return {"variant": "editorial", "scenes": copy.deepcopy(self.story["scenes"])}

    def test_attach_puts_a_checked_tree_and_no_raw_svg_on_the_props(self):
        self.story["scenes"][2]["art"] = SEED
        p = {"variant": "editorial", "scenes": copy.deepcopy(self.story["scenes"])}
        vignettes.attach(p, self.story)
        self.assertEqual(sorted(i for i, s in enumerate(p["scenes"]) if s.get("vignette")), [0, 1, 2])
        self.assertFalse(any(isinstance(s.get("art"), str) for s in p["scenes"]))
        v = p["scenes"][0]["vignette"]
        self.assertTrue(isinstance(v["art"], list) and v["art"])
        self.assertLessEqual(v["x"] + v["w"], 940)  # left of the like/share rail
        self.assertLessEqual(v["y"] + v["h"], 1380)  # scene text and drawings end above the captions

    def test_a_draw_scenes_own_tree_is_not_taken_for_a_drawing(self):
        p = self._props()
        p["scenes"][1] = {"type": "draw", "at": "სკოლის მოსწავლეები", "art": [{"tag": "path"}]}
        self.assertEqual(vignettes.attach(p, self.story), [])
        self.assertEqual(p["scenes"][1]["art"], [{"tag": "path"}])
        self.assertNotIn("vignette", p["scenes"][1])

    def test_a_seat_with_text_on_it_is_given_up(self):
        p = self._props()
        vignettes.attach(p, self.story)
        lost = vignettes.relieve(p, {"issues": [{"rule": "seat", "scene": 1}, {"rule": "band", "scene": 0}]})
        self.assertEqual(lost, [1])
        self.assertNotIn("vignette", p["scenes"][1])
        self.assertIn("vignette", p["scenes"][0])

    def test_a_drawing_moves_below_the_text_the_probe_measured(self):
        p = self._props()
        vignettes.attach(p, self.story)
        before = dict(p["scenes"][0]["vignette"])
        foot = before["y"] + before["h"]
        low = before["y"] + 40
        self.assertEqual(vignettes.relieve(p, {"issues": [{"rule": "seat", "scene": 0, "bottom": low - 20},
                                                         {"rule": "seat", "scene": 0, "bottom": low}]}), [0])
        after = p["scenes"][0]["vignette"]
        self.assertGreaterEqual(after["y"], low + 18)  # below the lowest text, with half a gap
        self.assertAlmostEqual(after["y"] + after["h"], foot, delta=1)
        self.assertAlmostEqual(after["x"] + after["w"] / 2, vignettes.CENTER, delta=1)
        self.assertLessEqual(after["w"], before["w"])
        self.assertEqual((after["art"], after["box"]), (before["art"], before["box"]))
        vignettes.relieve(p, {"issues": [{"rule": "seat", "scene": 0, "bottom": foot - 60}]})
        self.assertNotIn("vignette", p["scenes"][0])  # under MIN_KEEP left: given up


class Seat(Home):
    def test_a_drawing_stands_in_the_middle_on_the_scenes_foot(self):
        got, _ = vignettes.plan(self.story)
        self.assertTrue(got)
        for i, v in got.items():
            seat = v["seat"]
            self.assertAlmostEqual(seat["x"] + seat["w"] / 2, vignettes.CENTER, delta=1)
            self.assertLessEqual(seat["x"] + seat["w"], 940)
            self.assertGreaterEqual(seat["x"], 64)
            self.assertAlmostEqual(seat["y"] + seat["h"], 1380, delta=1)  # the foot stays where the room ends

    def test_the_seat_takes_the_drawings_own_shape(self):
        for v in vignettes.plan(self.story)[0].values():
            x0, y0, x1, y1 = v["box"]
            self.assertAlmostEqual(v["seat"]["w"] / v["seat"]["h"], (x1 - x0) / (y1 - y0), delta=0.02)

    def test_a_drawing_stands_clear_of_the_rolling_captions(self):  # the owner's tbilisi.today films roll
        p = {"variant": "editorial", "scenes": copy.deepcopy(self.story["scenes"])}
        vignettes.attach(p, self.story, foot=1315)
        seats = [s["vignette"] for s in p["scenes"] if s.get("vignette")]
        self.assertTrue(seats)
        for v in seats:
            self.assertLessEqual(v["y"] + v["h"], 1315 - vignettes.GAP_CAPTIONS)
            self.assertAlmostEqual(v["x"] + v["w"] / 2, vignettes.CENTER, delta=1)
        tight = vignettes.plan(self.story, foot=800)[0]  # no room left above the captions: no drawing
        self.assertEqual(tight, {})

    def test_a_very_wide_drawing_is_narrowed_and_keeps_its_shape(self):
        seat = {"x": 64, "y": 900, "w": 700, "h": 480, "reserve": 498}
        got = vignettes.fit(seat, [0, 0, 900, 200], "editorial")
        self.assertEqual((got["x"], got["w"], got["y"] + got["h"]), (140, 800, 1380))
        self.assertEqual(got["reserve"], 498)


def drew(svg=MOVING, scenes=None):
    """A model that draws `svg` for every scene it is asked for, and the prompts it got."""
    prompts = []

    def call(text):
        prompts.append(text)
        asked = scenes or [int(x) for x in re.findall(r"^- scene (\d+)", text, re.M)]
        return "Here you go:\n" + json.dumps({"drawings": [{"scene": i, "subject": "x", "parts": [], "svg": svg}
                                                         for i in asked]})
    return call, prompts


class Illustrator(Home):
    def gap(self):
        """The story with a quote whose words name nothing the library draws."""
        story = self.story
        story["narration"] = story["narration"].replace("სკოლის მოსწავლეები კვლავ უფასოდ იმგზავრებენ.",
                                                        "ეს ცვლილება ყველას ეხება.")
        story["scenes"][1]["at"] = "ეს ცვლილება"
        return story

    def test_it_asks_for_the_hook_and_what_the_library_cant_draw(self):
        self.assertEqual(illustrator.wanted(self.story), [0])
        self.assertEqual(illustrator.wanted(self.gap()), [0, 1])

    def test_it_asks_for_no_more_than_the_film_may_hold(self):
        story = self.gap()
        story["scenes"][2]["art"] = SEED
        story["scenes"][3]["art"] = SEED  # an end card's drawing counts for nothing, but its scene is no seat either
        self.assertEqual(illustrator.wanted(story), [0, 1])
        story["scenes"][0]["art"] = SEED
        story["scenes"][1]["art"] = SEED
        self.assertEqual(illustrator.wanted(story), [])

    def test_it_asks_for_nothing_where_the_news_rules_say_none(self):
        self.assertEqual(illustrator.wanted({**self.story, "category": "crime"}), [])

    def test_the_prompt_starts_with_the_same_guide_and_wordless_examples(self):
        text = illustrator.prompt(self.gap(), [0, 1])
        self.assertTrue(text.startswith(illustrator.GUIDE))
        self.assertEqual(illustrator.prompt(self.story, [0]).split("The video:")[0], text.split("The video:")[0])
        self.assertNotIn("<text", text.removeprefix(illustrator.GUIDE))
        self.assertIn("- scene 0 (the opening: the video's emblem): „ავტობუსის ბილეთი", text)
        self.assertIn("(its words name: bus", text)
        self.assertIn("Already drawn by the library, so draw other things: train-front (scene 2).", text)
        self.assertEqual(len(illustrator.examples()), 2)
        for _, svg in illustrator.examples():
            self.assertEqual(vignettes.own_problems({"type": "hook", "art": svg}), [])

    def test_the_story_gets_the_drawings_that_pass_and_the_one_passed_in_is_unchanged(self):
        story = self.gap()
        before = copy.deepcopy(story)
        call, prompts = drew()
        out, report = illustrator.draw(story, call=call)
        self.assertEqual(story, before)
        self.assertEqual((report["asked"], report["drawn"], report["calls"]), ([0, 1], [0, 1], 1))
        self.assertEqual([i for i, s in enumerate(out["scenes"]) if s.get("art")], [0, 1])
        got, _ = vignettes.plan(out)
        self.assertEqual({i: v["source"] for i, v in got.items()}, {0: "story", 1: "story", 2: "seed"})

    def test_a_failing_drawing_goes_back_once_with_its_problems(self):
        answers = iter(['{"drawings": [{"scene": 0, "svg": "<circle cx=\\"9\\" cy=\\"9\\" r=\\"4\\" stroke=\\"INK\\"/>"}]}',
                        json.dumps({"drawings": [{"scene": 0, "svg": SEED}]})])
        prompts = []

        def call(text):
            prompts.append(text)
            return next(answers)
        out, report = illustrator.draw(self.story, call=call)
        self.assertEqual((report["calls"], report["drawn"], report["dropped"]), (2, [0], {}))
        self.assertIn("Draw only these scenes again", prompts[1])
        self.assertIn("- scene 0: ", prompts[1])
        self.assertEqual(out["scenes"][0]["art"], SEED)

    def test_a_drawing_where_nothing_moves_goes_back_once_and_is_kept_if_still_still(self):
        self.assertEqual(vignettes.own_problems({"type": "hook", "art": STATIC}), [])
        call, prompts = drew(STATIC)
        out, report = illustrator.draw(self.story, call=call)
        self.assertEqual((report["calls"], report["drawn"], report["still"], report["dropped"]), (2, [0], [0], {}))
        self.assertIn(illustrator.NO_ACT, prompts[1])
        self.assertEqual(out["scenes"][0]["art"], STATIC)
        answers = iter([json.dumps({"drawings": [{"scene": 0, "svg": STATIC}]}),
                        json.dumps({"drawings": [{"scene": 0, "svg": MOVING}]})])
        out, report = illustrator.draw(self.story, call=lambda text: next(answers))
        self.assertEqual((out["scenes"][0]["art"], report["still"]), (MOVING, []))

    def test_the_guide_asks_for_an_act_and_its_examples_move(self):
        self.assertIn('"act"', illustrator.GUIDE)
        self.assertTrue(all(art.acts(art.sanitize(svg)[0]) for _, svg in illustrator.examples()))

    def test_a_drawing_that_still_fails_is_left_out(self):
        call, _ = drew('<circle cx="9" cy="9" r="4" stroke="INK"/>')
        out, report = illustrator.draw(self.story, call=call)
        self.assertEqual((report["drawn"], list(report["dropped"]), report["calls"]), ([], [0], 2))
        self.assertIs(out, self.story)

    def test_a_model_or_network_failure_costs_the_drawings_only(self):
        def broken(text):
            raise RuntimeError("HTTP 500")
        out, report = illustrator.draw(self.story, call=broken)
        self.assertIs(out, self.story)
        self.assertIn("HTTP 500", report["error"])
        out, report = illustrator.draw(self.story, call=lambda text: "no json here")
        self.assertEqual((report["drawn"], report["error"]), ([], None))

    def test_the_writer_leaves_art_to_the_illustrator_unless_it_is_off(self):
        self.assertNotIn(catalog.RULE_ART, writer.schema())
        self.assertIn('never set "art"', writer.schema())
        with mock.patch.dict(os.environ, {illustrator.ENV: "0"}):
            self.assertIn(catalog.RULE_ART, writer.schema())
        with mock.patch.dict(os.environ, {writer.DRAW_ENV: "0"}):
            self.assertFalse(illustrator.on())
            self.assertIn('nor "art"', writer.schema())

    def test_the_writer_calls_it_after_the_words_are_final(self):
        answer = {k: v for k, v in self.story.items() if k != "id"}
        seen = []

        def draw(story, *a, **k):
            seen.append(story["narration"])
            return {**story, "drawn": True}, {}
        with mock.patch.object(writer, "_call", return_value=json.dumps(answer, ensure_ascii=False)), \
                mock.patch.object(writer, "_edit", return_value=None), \
                mock.patch.object(writer, "_anchors_ok", return_value=True), \
                mock.patch.object(illustrator, "draw", side_effect=draw):
            story = writer.write({"id": 7, "category": "society"}, ["text"], repairs=0, run_checks=lambda s, a, c: [])
        self.assertEqual(seen, [self.story["narration"]])
        self.assertTrue(story["drawn"])
        self.assertEqual(story["id"], 7)

    def test_the_engine_draws_into_a_copy(self):
        path = pathlib.Path(self.tmp.name, "s.json")
        path.write_text(json.dumps(self.story, ensure_ascii=False), encoding="utf-8")
        target = pathlib.Path(self.tmp.name, "drawn.json")
        call, _ = drew()
        with mock.patch.object(writer, "_call", side_effect=lambda text, *a, **k: call(text)), mock.patch("sys.stdout"):
            code = engine.main(["vignettes", str(path), "--draw", "--out", str(target)])
        self.assertEqual(code, 0)
        self.assertNotIn("art", json.loads(path.read_text(encoding="utf-8"))["scenes"][0])
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["scenes"][0]["art"], MOVING)


class NewsRules(Home):
    def test_the_cheap_models_demo_passes_the_news_rules(self):
        sources = ROOT / "tests" / "fixtures" / "24835.sources.json"
        with mock.patch("sys.stdout"):
            code = engine.main(["check", str(ROOT / "stories" / "vignettes-gas.json"), "--sources", str(sources)])
        self.assertEqual(code, 0)
        story = json.loads((ROOT / "stories" / "vignettes-gas.json").read_text(encoding="utf-8"))
        self.assertEqual({v["source"] for v in vignettes.plan(story)[0].values()}, {"story"})


class Render(Home):
    def test_a_film_never_writes_its_summary_over_its_own_story(self):
        path = pathlib.Path(self.tmp.name, "gas.json")
        path.write_text(json.dumps(self.story, ensure_ascii=False), encoding="utf-8")
        got = engine.render_any(str(path), {}, "silent", str(path.with_suffix(".mp4")))
        self.assertIn("over its own story", got["problems"][0])
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.story)


class Lists(unittest.TestCase):
    def rows(self, types):
        return [{"scene": i, "type": t} for i, t in enumerate(types)]

    def test_two_lists_in_a_short_film_warn_and_never_hold(self):
        got = motion_rules.lists(self.rows(["hook", "points", "stat", "steps", "end"]))
        self.assertEqual([f["rule"] for f in got], ["lists"])
        self.assertFalse(got[0]["hold"])

    def test_one_list_or_a_long_film_is_fine(self):
        self.assertEqual(motion_rules.lists(self.rows(["hook", "points", "stat", "end"])), [])
        self.assertEqual(motion_rules.lists(self.rows(["hook"] + ["points", "stat"] * 4 + ["end"])), [])


class PointGlyphs(unittest.TestCase):
    def test_every_item_names_an_icon_or_none_gets_one(self):
        self.assertEqual(len(icons.point_glyphs({"items": ["ავტობუსი", "სკოლა", "ხიდი"]}) or []), 3)
        self.assertIsNone(icons.point_glyphs({"items": ["ავტობუსი", "მეტი დრო"]}))
        self.assertIsNone(icons.point_glyphs({"items": ["ავტობუსი", "ავტობუსის ბილეთი"]}))  # the same icon twice


if __name__ == "__main__":
    unittest.main()
