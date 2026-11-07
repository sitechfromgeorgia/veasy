"""The one-take camera (tt_shorts/onetake.py, remotion/src/onetake.tsx; ROADMAP D5): one test per limit of the brief."""
import json
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import motion_rules, onetake, probe, props, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent
TSX = (ROOT / "remotion" / "src" / "onetake.tsx").read_text(encoding="utf-8")
NEWS = (ROOT / "remotion" / "src" / "NewsShort.tsx").read_text(encoding="utf-8")
TYPES = ["hook", "stat", "steps", "where", "bars", "quote", "ranking", "compare", "sign", "end"]


def froms_for(n, length=90):
    return [i * length for i in range(n)]


def film(n=8, seed="b|1"):
    types = TYPES[:n] if n <= len(TYPES) else (TYPES * 3)[:n]
    return types, onetake.layout(types, seed), froms_for(n)


class Path(unittest.TestCase):
    def test_a_story_gets_its_route_again_and_two_stories_get_two(self):
        types = TYPES
        self.assertEqual(onetake.layout(types, "a|1"), onetake.layout(types, "a|1"))
        routes = {json.dumps(onetake.layout(types, f"a|{i}")["points"]) for i in range(40)}
        self.assertGreater(len(routes), 20)  # forty films, at least twenty different routes

    def test_the_route_depends_on_the_count_and_the_shapes(self):
        a = onetake.layout(["hook", "steps", "steps2", "end"], "s")["points"]
        self.assertEqual(len(a), 4)
        self.assertNotEqual(onetake.route(["hook", "steps", "bars", "end"], "s"),
                            onetake.route(["hook", "bars", "steps", "end"], "s")[:4:-1] or [])
        down = [onetake.route(["hook", "steps"], f"x{i}")[1] for i in range(30)]
        across = [onetake.route(["hook", "bars"], f"x{i}")[1] for i in range(30)]
        # a list arrives going down the page, a chart across it, far more often than the other way
        self.assertGreater(sum(c[1] != 0 for c in down), sum(c[1] != 0 for c in across))
        self.assertGreater(sum(c[0] != 0 for c in across), sum(c[0] != 0 for c in down) - 1)

    def test_each_step_is_one_cell_and_the_scenes_never_touch(self):
        for n in range(2, 14):
            for seed in range(30):
                types, cam, _ = film(n, f"k|{seed}")
                for a, b in zip(cam["points"], cam["points"][1:]):
                    dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
                    self.assertTrue(dx >= onetake.W or dy >= onetake.BAND, (n, seed))  # the old scene leaves the view
                    self.assertLessEqual(dx, onetake.CELL[0] + 1e-6)
                    self.assertLessEqual(dy, onetake.CELL[1] + 1e-6)

    def test_the_route_stays_in_its_box_and_crosses_itself_never_in_a_normal_film(self):
        for n in range(2, 13):
            for seed in range(40):
                cells = onetake.route((TYPES * 2)[:n], f"c|{seed}")
                self.assertEqual(len(set(cells)), len(cells), (n, seed))
                self.assertTrue(all(abs(x) <= onetake.BOX and abs(y) <= onetake.BOX for x, y in cells))

    def test_no_turn_back_on_itself(self):  # the thread is one gesture: never more than 90 degrees from the step before
        for n in range(3, 13):
            for seed in range(40):
                cells = onetake.route((TYPES * 2)[:n], f"t|{seed}")
                steps = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(cells, cells[1:])]
                for p, q in zip(steps, steps[1:]):
                    self.assertGreaterEqual(p[0] * q[0] + p[1] * q[1], 0, (n, seed, p, q))

    def test_a_long_film_still_has_a_route(self):  # more scenes than cells in the box: the rules relax, nothing fails
        cells = onetake.route(["hook"] + ["stat", "steps"] * 40, "long")
        self.assertEqual(len(cells), 81)
        self.assertTrue(all(abs(x) <= onetake.BOX and abs(y) <= onetake.BOX for x, y in cells))

    def test_a_single_scene_has_no_cuts(self):
        cam = onetake.layout(["hook"], "one")
        self.assertEqual((cam["points"], cam["cuts"]), ([[0, 0]], []))


class Camera(unittest.TestCase):
    def sweep(self, froms, total):
        return [onetake.position(self.cam, froms, f) for f in range(total)]

    def setUp(self):
        _, self.cam, self.froms = film(8)
        self.total = self.froms[-1] + 90

    def test_zoom_stays_at_or_under_1_15(self):
        pos = self.sweep(self.froms, self.total)
        self.assertLessEqual(max(z for _, _, z in pos), 1.15)
        self.assertGreaterEqual(min(z for _, _, z in pos), 0.85)  # a pull-back is as far
        self.assertLessEqual(onetake.ZOOM_CAP, 1.15)
        for seed in range(200):  # whatever the seed, each cut's depth is inside the cap
            for c in onetake.layout(TYPES, f"z|{seed}")["cuts"]:
                self.assertLessEqual(abs(c["zoom"]), 0.15)
        self.assertIn("Math.min(cam.zoomCap", TSX)  # the picture clamps it too
        self.assertLessEqual(onetake.ZOOM_MAX, 0.15)

    def test_the_camera_moves_only_during_the_cuts(self):
        pos = self.sweep(self.froms, self.total)
        for f in range(1, self.total):
            inside = onetake.moving(self.froms, f) or onetake.moving(self.froms, f - 1)
            if not inside:
                self.assertEqual(pos[f], pos[f - 1], f)  # at rest: not a pixel of drift

    def test_at_rest_it_sits_on_a_scene_with_zoom_exactly_one(self):
        for i, a in enumerate(self.froms):
            x, y, z = onetake.position(self.cam, self.froms, a + onetake.CUT)  # the probe's settled frame
            self.assertEqual((x, y, z), (*self.cam["points"][i], 1.0))
            x, y, z = onetake.position(self.cam, self.froms, a + 89)
            self.assertEqual((x, y, z), (*self.cam["points"][i], 1.0))

    def test_the_settled_frame_of_the_probe_is_at_rest(self):  # so the layout probe sees what a plain cut shows
        scenes = [{"from": f, "duration": 90} for f in self.froms]
        for f in probe.settled(scenes):
            self.assertFalse(onetake.moving(self.froms, f), f)

    def test_a_cut_arrives_exactly_and_is_one_smooth_move(self):
        a = self.froms[3]
        c = self.cam["cuts"][2]
        self.assertEqual(onetake.position(self.cam, self.froms, a - 1)[:2], tuple(c["from"]))
        self.assertEqual(onetake.position(self.cam, self.froms, a + onetake.CUT)[:2], tuple(c["to"]))
        xs = [onetake.position(self.cam, self.froms, a + k)[0] for k in range(onetake.CUT + 1)]
        d = c["to"][0] - c["from"][0]
        if d:  # monotone towards the next scene: no overshoot, no wobble
            steps = [(q - p) * (1 if d > 0 else -1) for p, q in zip(xs, xs[1:])]
            self.assertTrue(all(s >= -1e-9 for s in steps))

    def test_every_position_is_a_pure_function_of_the_frame(self):
        a = [onetake.position(self.cam, self.froms, f) for f in (5, 95, 100, 101, 200)]
        b = [onetake.position(self.cam, self.froms, f) for f in (200, 101, 100, 95, 5)][::-1]
        self.assertEqual(a, b)  # no state between calls, any order
        self.assertNotRegex(TSX, r"Math\.random|Date\.now|new Date|performance\.now")
        self.assertNotRegex((ROOT / "tt_shorts" / "onetake.py").read_text(encoding="utf-8"),
                            r"import random|time\.time|datetime")

    def test_python_and_the_picture_use_the_same_easing_and_window(self):
        self.assertIn("4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2", TSX)
        self.assertIn("(frame - froms[k]) / cam.cut", TSX)
        self.assertIn("1 + c.zoom * Math.sin(Math.PI * u)", TSX)
        self.assertEqual(onetake.ease(0), 0.0)
        self.assertEqual(onetake.ease(1), 1.0)
        self.assertEqual(onetake.ease(0.5), 0.5)


class Chrome(unittest.TestCase):
    """Chrome, source, time, captions and the safe zone stay fixed; the accent stays the dot."""

    def test_only_the_scene_band_rides_the_camera(self):
        self.assertEqual(NEWS.count("<OneTakeBand"), 1)  # one place: around a scene
        body = NEWS[NEWS.index("const SceneSlot"):NEWS.index("const SceneBody")]
        self.assertIn("<OneTakeBand i={i}><SceneBody i={i} /></OneTakeBand>", body)
        for fixed in ("<Header />", "<Ticker />", "<Footer />", "<Captions", "<OutroChip />"):
            at = NEWS.index(fixed)
            self.assertNotIn("OneTakeBand", NEWS[max(0, at - 80):at + 80], fixed)

    def test_the_band_is_clipped_to_the_scene_band_not_past_the_safe_zone(self):
        c = probe.C
        self.assertIn("SCENE_BOTTOM - CLIP_TOP", TSX)
        self.assertIn("const CLIP_TOP = SCENE_TOP - 32", TSX)
        self.assertEqual(onetake.BAND, c["SCENE_BOTTOM"] - c["SCENE_TOP"])
        self.assertLessEqual(c["SCENE_BOTTOM"], 1380)

    def test_the_parallax_layers_sit_behind_the_chrome_and_the_scenes(self):
        order = [NEWS.index(k) for k in ("<Background />\n", "<Parallax />", "<Ticker />", "<Header />", "{props.scenes.map")]
        self.assertEqual(order, sorted(order))

    def test_the_accent_is_only_the_dot(self):
        self.assertNotRegex(TSX, r"\bRED\b|ON_ACCENT|WAITING")
        self.assertRegex(TSX, r"<Dot size=\{\d+\} />")
        self.assertNotRegex(TSX, r"boxShadow|drop-shadow|textShadow")  # no shadows

    def test_the_dot_and_the_thread_exist_only_inside_the_window(self):
        self.assertIn("if (f >= cam.cut) return null;", TSX)

    def test_the_package_is_pinned_to_the_other_remotion_packages(self):
        pk = json.loads((ROOT / "remotion" / "package.json").read_text(encoding="utf-8"))["dependencies"]
        self.assertEqual(pk["@remotion/paths"], pk["remotion"])
        self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", pk["@remotion/paths"]))  # exact, no range


class News(unittest.TestCase):
    """`news` stays exactly as it is: the option doesn't reach it."""

    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def test_the_pools_of_news_are_unchanged(self):
        for look in variety.TRANSITIONS:
            self.assertNotIn("one-take", variety.TRANSITIONS[look])
            self.assertEqual(variety.transitions_for(look), variety.TRANSITIONS[look])
            self.assertEqual(variety.transitions_for(look, "news"), variety.TRANSITIONS[look])
            self.assertIn("one-take", variety.transitions_for(look, "explainer"))

    def test_auto_never_picks_it_for_news(self):
        for i in range(60):
            for look in variety.TRANSITIONS:
                got = variety.pick("tbilisi-today", i, look, "auto", program=None)["transition"]
                self.assertNotEqual(got, "one-take")

    def test_naming_it_for_news_is_refused(self):
        story = {"id": 7, "category": "politics", "scenes": [{"type": "hook"}, {"type": "end"}]}
        with self.assertRaises(ValueError) as e:
            props.choose(story, "editorial", transition="one-take")
        self.assertIn("not for news", str(e.exception))
        story["program"] = "news"
        with self.assertRaises(ValueError):
            props.choose(story, "editorial", transition="one-take")


class Rules(unittest.TestCase):
    def built(self, kind="one-take", n=6, seed="r|1"):
        types, cam, froms = film(n, seed)
        scenes = [{"from": f, "duration": 90, "type": t, "kicker": "ა ბ გ"} for f, t in zip(froms, types)]
        return {"scenes": scenes, "transition": kind, "durationInFrames": froms[-1] + 90, "camera": cam}

    def test_motion_rules_know_its_direction_and_it_never_ping_pongs(self):
        for seed in range(40):
            p = self.built(n=9, seed=f"r|{seed}")
            cuts = motion_rules.cuts(p)
            self.assertTrue(all(c["kind"] == "one-take" and c["direction"] for c in cuts))
            self.assertEqual(motion_rules.pingpong(cuts), [], seed)
            self.assertEqual(motion_rules.kinds(cuts), [])

    def test_a_scene_is_not_faded_out_before_the_camera_takes_it(self):
        row = motion_rules.timeline(self.built())[0]
        self.assertEqual(row["leaves"], row["to"])  # a cut's: no exit frames lost to a fade

    def test_the_motion_rules_pass_on_a_one_take_film(self):
        found = motion_rules.check(self.built())
        self.assertEqual(found["holds"], [])
        self.assertEqual([w for w in found["warnings"] if "pingpong" in w or "kinds" in w], [])

    def test_a_cut_window_is_a_whole_number_of_frames_short_of_the_shortest_scene(self):
        self.assertLess(onetake.CUT, motion_rules.PACING_MIN * motion_rules.FPS)  # a window never outlasts a scene


if __name__ == "__main__":
    unittest.main()


class Thread(unittest.TestCase):
    """The thread lives in the margins between two scenes: it never crosses what is read."""

    def test_the_thread_starts_and_ends_in_the_margin_of_a_scene(self):
        for seed in range(30):
            cam = onetake.layout(TYPES, f"th|{seed}")
            for c in cam["cuts"]:
                for end, scene in ((c["a"], c["from"]), (c["b"], c["to"])):
                    dx, dy = abs(end[0] - scene[0]), abs(end[1] - scene[1])
                    self.assertGreaterEqual(onetake.W / 2 - dx, onetake.INSET[0] - 0.2)  # at least the text margin in
                    self.assertGreaterEqual(onetake.BAND / 2 - dy, onetake.INSET[1] - 0.2)  # inside the scene band
                    self.assertTrue(dx >= onetake.W / 2 - onetake.INSET[0] - 0.2 or dy >= onetake.BAND / 2 - onetake.INSET[1] - 0.2
                                    or (dx == 0 and dy == 0))

    def test_the_bend_is_gentle(self):
        for seed in range(30):
            for c in onetake.layout(TYPES, f"bd|{seed}")["cuts"]:
                chord = ((c["b"][0] - c["a"][0]) ** 2 + (c["b"][1] - c["a"][1]) ** 2) ** 0.5
                off = max(abs(c["c1"][0] - c["a"][0] - (c["b"][0] - c["a"][0]) * .33),
                          abs(c["c1"][1] - c["a"][1] - (c["b"][1] - c["a"][1]) * .33))
                self.assertLessEqual(off, chord * 0.31)
                self.assertIn("c.a[0]", TSX)
