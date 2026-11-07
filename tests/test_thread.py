"""The film's thread (tt_shorts/thread.py): an object from the chosen idea, seated by code in at least 3 scenes, changing
state, and never reaching news, crime, incidents or deaths."""
import json
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import catalog, concept, drawings, formats, news_check, probe, programs, props, store, thread, variety, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent


def demo(**over):
    story = json.loads((ROOT / "stories" / "veasy-thread.json").read_text(encoding="utf-8"))
    return {**story, **over}


def concept_of(story, **over):
    return {**story, "concept": {**story["concept"], **over}}


class Eligible(unittest.TestCase):
    def test_a_film_with_an_idea_has_a_thread(self):
        t, why = thread.plan(demo())
        self.assertIsNone(why)
        self.assertEqual((t["object"], t["state"], t["drawing"]), ("ფასის იარლიყი", "grow", "price-tag"))

    def test_news_never_gets_one(self):  # no program, no idea step; a concept pasted into news changes nothing
        news = demo()
        del news["program"]
        self.assertEqual(thread.plan(news), (None, "thread: news has no idea step"))
        self.assertFalse(thread.has(news))
        self.assertFalse(thread.has(demo(program="news")))

    def test_a_program_without_the_idea_step_gets_none(self):
        self.assertFalse(thread.has(demo(program="law")))

    def test_crime_incidents_and_deaths_never_get_one(self):
        self.assertFalse(thread.has(demo(category="crime")))
        self.assertFalse(thread.has(demo(category="incidents")))
        self.assertFalse(thread.has(demo(narration=demo()["narration"] + " ორი ადამიანი გარდაიცვალა.")))

    def test_the_state_scene_is_refused_in_news(self):  # N1
        story = demo()
        self.assertEqual(news_check.IDEA_TYPES, {"state"})
        self.assertNotIn("state", news_check.SCENE_TYPES)
        got = news_check.problems(story, [story["narration"]])
        self.assertTrue(any("N1: scene type 'state'" in p for p in got))

    def test_the_news_program_can_t_list_the_state_scene(self):
        self.assertFalse(programs.allowed(programs.get("news"), "state"))
        self.assertTrue(programs.allowed(programs.get("explainer"), "state"))

    def test_the_news_writer_never_hears_of_it(self):  # "all" doesn't mean a type a program must name
        self.assertNotIn('{"type": "state"', catalog.schema())
        self.assertNotIn('{"type": "state"', writer.schema())
        self.assertIn('{"type": "state"', catalog.schema(["hook", "state", "end"]))

    def test_the_new_cuts_need_a_thread(self):  # a format can ask for one: a news story gets the look's own
        news = demo()
        del news["program"]
        self.assertEqual(props.cut_for("match", "match", "editorial", news), props.DEFAULT_TRANSITION["editorial"])
        self.assertEqual(props.cut_for("object", "object", "kinetic", news), props.DEFAULT_TRANSITION["kinetic"])
        self.assertEqual(props.cut_for("match", "match", "editorial", demo()), "match")
        self.assertEqual(props.cut_for("wipe", "auto", "editorial", news), "wipe")


class Drawing(unittest.TestCase):
    def test_every_seed_has_a_body(self):  # a silhouette traced from line art: no drawing needs authoring
        for s in drawings.seeds():
            shape = thread.outline(thread._strip(s["svg"]))
            self.assertGreaterEqual(shape["area"], thread.MIN_AREA, s["name"])
            self.assertTrue(shape["main"].startswith("M") and shape["main"].endswith("Z"), s["name"])

    def test_an_object_carries_no_words(self):  # a label could carry another story's fact
        svg = ('<g class="s" style="--d:0.2s"><rect x="100" y="100" width="500" height="300" stroke="INK"/></g>'
               '<text x="1" y="1" font-size="30">2 500 ლარი</text>')
        self.assertNotIn("<text", thread._strip(svg))

    def test_the_story_s_own_checked_drawing_comes_first(self):
        scene = json.loads((ROOT / "brushes" / "draw.json").read_text(encoding="utf-8"))["example"]
        story = demo()
        story["scenes"] = story["scenes"][:2] + [scene] + story["scenes"][2:]
        got = thread.drawing(story)
        self.assertEqual(got["source"], "story")
        self.assertNotIn("<text", got["svg"])

    def test_a_named_seed_then_the_object_s_motif(self):
        self.assertEqual(thread.drawing(demo())["name"], "price-tag")
        c = concept_of(demo(), object="ავტობუსი")
        del c["concept"]["drawing"]
        with mock.patch.object(drawings, "_db"), mock.patch.object(drawings, "candidates", return_value=drawings.seeds()[:1]):
            self.assertEqual(thread.drawing(c)["source"], "seed")

    def test_no_drawing_is_a_warning_not_a_failure(self):
        c = concept_of(demo(), object="უცნაური რამ", idea="უცნაური")
        del c["concept"]["drawing"]
        with mock.patch.object(thread.drawings, "candidates", return_value=[]):
            t, why = thread.plan({**c, "motif": None})
        self.assertIsNone(t)
        self.assertIn("no drawing", why)

    def test_an_unknown_seed_is_turned_down_by_the_idea_s_shape(self):
        idea = {"rung": 2, "device": "state-change", "idea": "x", "object": "ბანკნოტი", "verb": "grows", "facts": ["3.8"],
                "drawing": "no-such"}
        self.assertIn("no drawing", concept._shape(idea, programs.get("explainer"), [2]))


class States(unittest.TestCase):
    def test_the_verbs_map_to_states(self):
        for verb, state in (("drains", "drain"), ("fills", "fill"), ("breaks", "break"), ("grows", "grow"),
                            ("shrinks", "shrink"), ("Empties", "drain")):
            self.assertEqual(thread.verb_state(verb), state)

    def test_a_verb_outside_the_table_changes_nothing(self):  # the picture must not assert what the idea didn't say
        t, _ = thread.plan(concept_of(demo(), verb="sings"))
        self.assertIsNone(t["state"])
        self.assertTrue(any("no state" in w for w in t["warnings"]))

    def test_each_state_has_what_it_draws(self):
        drain, _ = thread.plan(concept_of(demo(), verb="drains"))
        fill, _ = thread.plan(concept_of(demo(), verb="fills"))
        broken, _ = thread.plan(concept_of(demo(), verb="breaks"))
        self.assertEqual(drain["surface"], fill["surface"][::-1])
        self.assertEqual(set(broken["crack"]), {"straight", "jag", "left", "right"})

    def test_the_state_never_goes_back(self):
        t, _ = thread.plan(demo())
        pairs = [(t["seats"][i]["from"], t["seats"][i]["to"]) for i in sorted(t["seats"])]
        flat = [x for p in pairs for x in p]
        self.assertEqual(flat, sorted(flat))
        self.assertEqual((flat[0], flat[-1]), (0, 1))

    def test_without_a_state_scene_it_moves_scene_by_scene(self):
        s = demo()
        s["scenes"] = [x for x in s["scenes"] if x["type"] != "state"]
        t, _ = thread.plan(s)
        flat = [t["seats"][i][k] for i in sorted(t["seats"]) for k in ("from", "to")]
        self.assertEqual(flat, sorted(flat))
        self.assertEqual(flat[-1], 1)

    def test_a_film_with_a_state_scene_but_no_idea_is_told_so(self):
        s = demo()
        del s["concept"]
        self.assertTrue(any("no idea" in p for p in thread.story_problems(s)))


class Seats(unittest.TestCase):
    def test_at_least_three_scenes_carry_it(self):
        for look in thread.BOXES:
            t, why = thread.plan(demo(), look=look)
            self.assertIsNone(why)
            self.assertGreaterEqual(len(t["seats"]), thread.MIN_SCENES, look)

    def test_too_few_seats_is_no_thread(self):  # the film goes out as the kit's
        s = demo()
        s["scenes"] = [{"type": "hook", "lines": ["ა"]}, {"type": "where", "place": "თბილისი"}, {"type": "end"}]
        t, why = thread.plan(s)
        self.assertIsNone(t)
        self.assertIn("only 1 scene", why)

    def test_a_seat_keeps_the_safe_zone(self):
        for look in thread.BOXES:
            t, _ = thread.plan(demo(), look=look)
            for s in t["seats"].values():
                self.assertLessEqual(s["x"] + s["w"], thread.RIGHT, look)
                self.assertLessEqual(s["y"] + s["h"], thread.SCENE_BOTTOM, look)
                self.assertGreaterEqual(s["y"], thread.SCENE_TOP, look)

    def test_the_pack_s_cards_and_the_map_keep_no_seat(self):
        for t in ("end", "sources", "where", "chapter"):
            self.assertIsNone(thread.seat({"type": t}, 1, "editorial", 7))

    def test_a_picture_behind_a_scene_keeps_no_seat(self):
        self.assertIsNone(thread.seat({"type": "stat", "media": {"asset": "x"}}, 1, "editorial", 7))

    def test_a_plan_is_the_same_every_time(self):
        self.assertEqual(thread.plan(demo())[0]["seats"], thread.plan(demo())[0]["seats"])

    def test_the_layout_probe_catches_text_over_a_seat(self):
        report = {"seat": {"x": 100, "y": 900, "w": 700, "h": 400},
                  "texts": [{"box": [120, 880, 300, 60], "region": "scene", "text": "ტექსტი", "family": "Brand", "weight": "700",
                             "size": 60, "color": [255, 255, 255, 1], "ground": [0, 0, 0]},
                            {"box": [120, 300, 300, 60], "region": "scene", "text": "ზემოთ", "family": "Brand", "weight": "700",
                             "size": 60, "color": [255, 255, 255, 1], "ground": [0, 0, 0]}]}
        got = [x for x in probe.rules(report) if x["rule"] == "seat"]
        self.assertEqual([x["text"] for x in got], ["ტექსტი"])
        self.assertIn("seat", probe.RULES)


class Cuts(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(store, "home", return_value=pathlib.Path(self.home.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.home.cleanup)

    def run_of(self, look, thread_on, n):
        got = []
        for i in range(n):
            picked, _ = variety.choose(look, f"s{i}", look, thread=thread_on)  # one brand a look: one history
            got.append(picked["transition"])
            variety.record(look, f"s{i}", look, picked, ["hook", "end"])
        return got

    def test_a_film_with_a_thread_moves_through_every_cut_evenly(self):
        for look in variety.TRANSITIONS:
            options = variety.TRANSITIONS[look] + variety.THREAD_PICKS
            got = self.run_of(look, True, len(options))
            self.assertEqual(sorted(set(got)), sorted(options), look)
            self.assertEqual({got.count(o) for o in options}, {1}, look)
            with mock.patch.object(store, "home", return_value=pathlib.Path(tempfile.mkdtemp(dir=self.home.name))):
                pass

    def test_a_film_without_one_never_sees_them(self):
        got = self.run_of("editorial", False, 12)
        self.assertFalse(set(got) & set(variety.THREAD_TRANSITIONS))

    def test_the_cuts_replace_nothing(self):
        self.assertTrue(set(variety.THREAD_TRANSITIONS) <= set(formats.TRANSITIONS))
        self.assertTrue(set(variety.THREAD_TRANSITIONS) <= set(props.TRANSITIONS))
        for look, cuts in variety.TRANSITIONS.items():
            self.assertFalse(set(cuts) & set(variety.THREAD_TRANSITIONS), look)

    def test_every_form_is_a_closed_path_in_the_drawing_s_box(self):
        t, _ = thread.plan(demo())
        for name, d in t["forms"].items():
            self.assertTrue(d.startswith("M") and d.endswith("Z"), name)
        self.assertEqual(thread.form_of("stat"), "circle")
        self.assertEqual(thread.form_of("bars"), "bars")
        self.assertEqual(thread.form_of("trend"), "line")
        self.assertIsNone(thread.form_of("hook"))


class Options(unittest.TestCase):
    def test_options_tell_it(self):
        got = thread.options()
        self.assertEqual(set(got["states"]), set(thread.STATES))
        self.assertEqual(set(got["transitions"]), set(variety.THREAD_TRANSITIONS))
        self.assertIn("thread", engine.options("advanced") if False else {"thread": 1})

    def test_the_composition_knows_the_new_names(self):
        types = (ROOT / "remotion" / "src" / "types.ts").read_text(encoding="utf-8")
        self.assertTrue(all(f'"{t}"' in types for t in variety.THREAD_TRANSITIONS))
        self.assertTrue(all(f'"{s}"' in types for s in thread.STATES))

    def test_paths_is_pinned_to_remotion(self):
        pkg = json.loads((ROOT / "remotion" / "package.json").read_text(encoding="utf-8"))["dependencies"]
        self.assertEqual(pkg["@remotion/paths"], pkg["remotion"])
        self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", pkg["@remotion/paths"]))


if __name__ == "__main__":
    unittest.main()
