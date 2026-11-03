"""Variety: a run of videos moves through the options instead of repeating one style (owner, 2026-11-02: "1000 videos,
90% the same style, is no good"), and drawings are judged by code because nobody reviews them before publishing."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import art, variety, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Picks(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def run_day(self, n, look="editorial", loops=("politics-1.m4a", "politics-2.m4a", "politics-3.m4a"), icon=True):
        picks = []
        for i in range(n):
            p = variety.pick("tbilisi-today", 1000 + i, look, "auto", [pathlib.Path(x) for x in loops], icon=icon)
            variety.record("tbilisi-today", 1000 + i, look, p, ["hook", "stat", "end"])
            picks.append(p)
        return picks

    def test_a_run_moves_through_every_option(self):  # stories with a main icon: every option, the icon motif too
        picks = self.run_day(20)
        for key, options in variety.OPTIONS.items():
            self.assertEqual({p[key] for p in picks}, set(options), key)  # all used...
            counts = [sum(p[key] == o for p in picks) for o in options]
            self.assertLessEqual(max(counts) - min(counts), 1, key)  # ...and evenly
        self.assertEqual({p["transition"] for p in picks}, set(variety.TRANSITIONS["editorial"]))
        self.assertEqual({p["music"] for p in picks}, {"politics-1.m4a", "politics-2.m4a", "politics-3.m4a"})

    def test_the_meter_wipe_is_one_more_cut(self):  # phase 3: added to the looks it fits, never instead of one
        self.assertEqual(variety.TRANSITIONS["editorial"], ("line", "wipe", "dot", "slide", "meter", "fade", "shutter", "iris"))
        self.assertEqual(variety.TRANSITIONS["kinetic"], ("panel", "push", "wipe", "cut", "meter", "split", "corner", "shutter", "blind"))
        for look, n in (("editorial", 16), ("kinetic", 18)):
            picks = self.run_day(n, look)
            counts = [sum(p["transition"] == t for p in picks) for t in variety.TRANSITIONS[look]]
            self.assertEqual(counts, [2] * len(variety.TRANSITIONS[look]), look)  # every cut, evenly
            variety_db = pathlib.Path(self.home.name) / "veasy.db"
            variety_db.unlink()

    def test_the_icon_motif_needs_an_icon(self):  # a story without one moves through the other motifs, evenly
        picks = self.run_day(18, icon=False)
        motifs = [p["motif"] for p in picks]
        self.assertNotIn("icons", motifs)
        others = variety.options_for("motif")
        self.assertEqual(set(motifs), set(others))
        self.assertEqual(max(map(motifs.count, others)) - min(map(motifs.count, others)), 0)

    def test_a_mixed_run_stays_even(self):  # stories with and without icons share one history
        for i in range(24):
            p = variety.pick("tbilisi-today", 2000 + i, "cards", icon=i % 2 == 0)
            variety.record("tbilisi-today", 2000 + i, "cards", p, ["hook", "end"])
        past = variety.history("tbilisi-today", 24)
        counts = [[r["motif"] for r in past].count(o) for o in variety.OPTIONS["motif"]]
        self.assertLessEqual(max(counts) - min(counts), 2, counts)
        self.assertTrue(all(r["motif"] != "icons" for r in past if int(r["story"]) % 2 == 1))

    def test_a_re_render_without_its_icon_gets_another_motif(self):  # the story lost its icon since
        first = variety.pick("tbilisi-today", 77, "kinetic", icon=True)
        variety.record("tbilisi-today", 77, "kinetic", {**first, "motif": "icons"}, ["hook", "end"])
        self.assertEqual(variety.pick("tbilisi-today", 77, "kinetic", icon=True)["motif"], "icons")
        self.assertIn(variety.pick("tbilisi-today", 77, "kinetic", icon=False)["motif"], variety.options_for("motif"))

    def test_no_two_videos_in_a_row_are_the_same(self):
        picks = self.run_day(12)
        for a, b in zip(picks, picks[1:]):
            self.assertNotEqual((a["hook"], a["motif"], a["enter"]), (b["hook"], b["motif"], b["enter"]))

    def test_a_story_keeps_its_picks(self):  # a re-render (another caption design) looks the same
        first = self.run_day(1)[0]
        self.run_day(3)
        again = variety.pick("tbilisi-today", 1000, "editorial", "auto", [pathlib.Path("politics-1.m4a"),
                                                                           pathlib.Path("politics-2.m4a"),
                                                                           pathlib.Path("politics-3.m4a")])
        self.assertEqual(again, first)

    def test_a_format_s_transition_is_kept(self):
        self.assertEqual(variety.pick("tbilisi-today", 1, "kinetic", "dot")["transition"], "dot")
        self.assertIn(variety.pick("tbilisi-today", 1, "kinetic", "auto")["transition"], variety.TRANSITIONS["kinetic"])
        self.assertIsNone(variety.pick("tbilisi-today", 1, "kinetic")["music"])  # no loops, no music

    def test_brands_have_their_own_history(self):
        self.run_day(5)
        self.assertEqual(variety.history("sitech"), [])

    def test_the_writer_hears_the_recent_scene_orders(self):
        self.run_day(3)
        recent = variety.recent_sequences("tbilisi-today")
        self.assertEqual(recent, ["hook>stat>end x3"])
        prompt = writer._prompt({"headline": "x"}, ["ა 1"], recent)
        self.assertIn("hook>stat>end x3", prompt)
        self.assertNotIn("Scene orders the latest", writer._prompt({"headline": "x"}, ["ა 1"]))

    def test_auto_themes_move_evenly_and_a_story_keeps_its_own(self):  # brand.json themes, format theme: auto
        got = []
        for i in range(12):
            t = variety.pick_theme("sitech", 3000 + i, ["dark", "light"])
            variety.record("sitech", 3000 + i, "cards", {**variety.pick("sitech", 3000 + i, "cards"), "theme": t},
                           ["hook", "end"])
            got.append(t)
        self.assertEqual((got.count("dark"), got.count("light")), (6, 6))  # evenly
        self.assertTrue(all(abs(got[:k].count("dark") - got[:k].count("light")) <= 1 for k in range(13)))  # at every point
        self.assertEqual(variety.pick_theme("sitech", 3000, ["dark", "light"]), got[0])  # a re-render keeps it
        self.assertEqual(variety.report("sitech")["theme"]["distinct"], 2)

    def test_auto_themes_stay_in_the_pack_and_the_director_s(self):
        self.assertEqual(variety.pick_theme("tbilisi-today", 1, ["dark"]), "dark")  # one allowed theme: always it
        self.assertEqual({variety.pick_theme("sitech", i, ["dark", "light"], ["light"]) for i in range(5)}, {"light"})
        # a director's preference the pack doesn't have: every allowed theme stays possible
        self.assertIn(variety.pick_theme("sitech", 9, ["dark", "light"], ["sepia"]), ("dark", "light"))

    def test_the_theme_is_not_in_the_fingerprint(self):  # a one-theme pack must not look one field closer
        self.assertNotIn("theme", variety.FIELDS)

    def test_report_measures_sameness(self):
        self.run_day(8)
        r = variety.report("tbilisi-today")
        self.assertEqual(r["hook"]["distinct"], 8)
        self.assertEqual(r["scenes"]["most_used_share"], 1.0)  # every test video had the same scene order


class NoveltyGuard(unittest.TestCase):
    """A planned video too close to one of the brand's last 20 is re-rolled before the voice is paid for (ROADMAP
    D11): fingerprint (director, scenes, hook, motif, enter, transition, music), too close at 5 of 7 shared."""
    SCENES = ["hook", "stat", "timeline", "sources", "end"]

    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()
        from tt_shorts import directors
        self.data = directors.get("data")  # cards: hooks stack|underline, enters rise|scale, cuts line|dot

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def seed_a_repeat(self):
        """Story 1 under data, and other stories that use every other option twice: the plain least used picks for
        the next data story with the same scenes are then exactly story 1's (a repeated plan)."""
        first = {"hook": "stack", "motif": "grid", "enter": "rise", "transition": "line", "music": None, "director": "data"}
        variety.record("tbilisi-today", 1, "cards", first, self.SCENES)
        other = {"hook": "underline", "motif": "rules", "enter": "scale", "transition": "dot", "music": None,
                 "director": "map"}
        for i in range(2):
            variety.record("tbilisi-today", 10 + i, "cards", other, ["hook", "where", "sign", "end"])
            variety.record("tbilisi-today", 20 + i, "cards", {**other, "motif": "plain"}, ["hook", "where", "end"])
        return first

    def test_the_fingerprint_and_its_distance(self):
        a = variety.fingerprint({"hook": "stack", "motif": "grid", "enter": "rise", "transition": "line",
                                 "music": "x.m4a"}, ["hook", "stat", "end"], "data")
        self.assertEqual(variety.similarity(a, a), 7.0)
        self.assertEqual(variety.distance(a, a), 0.0)
        b = {**a, "scenes": ("hook", "stat", "where", "end")}
        self.assertEqual(variety.similarity(a, b), 6.857)  # the orders: difflib ratio 2*3/7
        c = {**b, "hook": "lead", "director": "map"}
        self.assertFalse(variety.too_close(a, c))  # 4.857 shared: not too close
        self.assertTrue(variety.too_close(a, {**c, "director": "data"}))  # 5.857
        row = {"story": "9", "director": "data", "scenes": '["hook", "stat", "end"]', "hook": "stack",
               "motif": "grid", "enter": "rise", "transition": "line", "music": "x.m4a"}
        self.assertEqual(variety.similarity(a, variety.fingerprint(row)), 7.0)  # a history row is a fingerprint
        self.assertEqual(variety.nearest(a, [c, variety.fingerprint(row)])[1]["story"], "9")
        self.assertEqual(variety.nearest(a, []), (0.0, None))

    def test_a_repeated_plan_is_re_rolled(self):
        first = self.seed_a_repeat()
        with mock.patch.object(variety, "TOO_CLOSE", 99):  # the guard off: the plain picks repeat story 1
            plain, _ = variety.choose("tbilisi-today", 2, "cards", director=self.data, scenes=self.SCENES)
        self.assertEqual(plain, {k: first[k] for k in plain})
        style, novelty = variety.choose("tbilisi-today", 2, "cards", director=self.data, scenes=self.SCENES)
        self.assertNotEqual(style, plain)
        self.assertGreaterEqual(novelty["rerolls"], 1)
        self.assertFalse(novelty["too_close"])
        self.assertIsNone(novelty["warning"])
        fp = variety.fingerprint(style, self.SCENES, "data")
        for r in variety.history("tbilisi-today"):
            self.assertLess(variety.similarity(fp, variety.fingerprint(r)), variety.TOO_CLOSE, r["story"])
        for key, sub in (("hook", "hooks"), ("motif", "motifs"), ("enter", "enters"), ("transition", "transitions")):
            self.assertIn(style[key], self.data[sub], key)  # still inside the director's subsets

    def test_a_novel_plan_is_untouched(self):
        variety.record("tbilisi-today", 1, "cards", {"hook": "stack", "motif": "grid", "enter": "rise",
                                                     "transition": "line", "music": None, "director": "map"},
                       ["hook", "where", "end"])
        with mock.patch.object(variety, "TOO_CLOSE", 99):
            plain, _ = variety.choose("tbilisi-today", 2, "cards", director=self.data, scenes=self.SCENES)
        style, novelty = variety.choose("tbilisi-today", 2, "cards", director=self.data, scenes=self.SCENES)
        self.assertEqual(style, plain)
        self.assertEqual((novelty["rerolls"], novelty["too_close"], novelty["warning"]), (0, False, None))
        self.assertEqual(novelty["nearest"], "1")
        self.assertEqual(variety.choose("tbilisi-today", 3, "cards")[1]["rerolls"], 0)

    def test_a_re_render_keeps_its_picks(self):
        self.seed_a_repeat()
        once = variety.choose("tbilisi-today", 2, "cards", director=self.data, scenes=self.SCENES)
        self.assertEqual(variety.choose("tbilisi-today", 2, "cards", director=self.data, scenes=self.SCENES), once)
        style, novelty = once  # a probe, then the render: the same re-rolled picks
        variety.record("tbilisi-today", 2, "cards", {**style, "director": "data"}, self.SCENES, novelty)
        variety.record("tbilisi-today", 30, "cards", {**style, "director": "data"}, self.SCENES)  # a twin since
        again, nov = variety.choose("tbilisi-today", 2, "cards", director=self.data, scenes=self.SCENES)
        self.assertEqual(again, style)
        self.assertTrue(nov["kept"])
        self.assertEqual(nov["rerolls"], 0)
        row = next(r for r in variety.history("tbilisi-today") if r["story"] == "2")
        self.assertEqual((row["rerolls"], row["novelty"]), (novelty["rerolls"], novelty["distance"]))

    def test_re_rolls_are_bounded_and_never_fail_the_video(self):
        # a fixed cut, no music, the same director and scenes: one more shared pick is too close, and these two
        # videos together hold every hook, so no plan is far enough
        for i, hook in enumerate(("stack", "underline")):
            variety.record("tbilisi-today", 40 + i, "cards", {"hook": hook, "motif": "grid", "enter": "rise",
                                                              "transition": "dot", "music": None, "director": "data"},
                           self.SCENES)
        calls = []
        real = variety.nearest
        with mock.patch.object(variety, "REROLLS", 3), \
                mock.patch.object(variety, "nearest", side_effect=lambda *a: calls.append(1) or real(*a)):
            style, novelty = variety.choose("tbilisi-today", 2, "cards", "dot", director=self.data, scenes=self.SCENES)
        self.assertEqual(novelty["rerolls"], 3)
        self.assertEqual(len(calls), 1 + 3)  # the plan and at most REROLLS re-rolls
        self.assertTrue(novelty["too_close"])
        self.assertIn("novelty:", novelty["warning"])
        self.assertEqual(style["transition"], "dot")  # a format's fixed cut is never re-rolled
        self.assertIn(style["hook"], self.data["hooks"])

    def test_an_old_database_is_migrated(self):
        import sqlite3
        con = sqlite3.connect(pathlib.Path(self.home.name) / "veasy.db")
        con.executescript("create table variety(ts text, brand text, story text, look text, hook text, motif text, "
                          "enter text, transition text, music text, scenes text);")
        con.execute("insert into variety values('2026-10-01T00:00:00+00:00', 'tbilisi-today', '7', 'cards', 'stack', "
                    "'grid', 'rise', 'line', null, '[\"hook\", \"stat\", \"end\"]')")
        con.commit()
        con.close()
        old = variety.history("tbilisi-today")
        self.assertEqual(len(old), 1)
        self.assertEqual((old[0]["director"], old[0]["novelty"], old[0]["rerolls"]), (None, None, None))
        style, novelty = variety.choose("tbilisi-today", 8, "cards", scenes=["hook", "stat", "end"])
        self.assertEqual(novelty["nearest"], "7")
        variety.record("tbilisi-today", 8, "cards", style, ["hook", "stat", "end"], novelty)
        self.assertEqual(variety.history("tbilisi-today")[0]["rerolls"], novelty["rerolls"])
        self.assertIn("novelty", variety.report("tbilisi-today"))

    def test_the_guard_runs_before_the_voice(self):
        """props.build is the path of render, the queue, still and probe: the picks (and any re-roll) come first."""
        from tt_shorts import props, speech
        order = []
        choose, voice = variety.choose, speech.voice
        with mock.patch.object(variety, "choose", side_effect=lambda *a, **k: order.append("guard") or choose(*a, **k)), \
                mock.patch.object(speech, "voice", side_effect=lambda *a, **k: order.append("voice") or voice(*a, **k)):
            _, p = props.build(str(ROOT / "stories" / "24835-brief.json"), "cards", "silent", music="off")
        self.assertEqual(order, ["guard", "voice"])
        self.assertEqual(set(p["novelty"]), {"similarity", "distance", "nearest", "too_close", "rerolls", "kept",
                                             "warning"})

    def test_plan_shows_the_fingerprint_and_the_closest_and_records_nothing(self):
        from tt_shorts import plan
        story = ROOT / "stories" / "24835-brief.json"
        scenes = [s["type"] for s in json.loads(story.read_text(encoding="utf-8"))["scenes"]]
        variety.record("tbilisi-today", 99, "cards", {"hook": "stack", "motif": "grid", "enter": "rise",
                                                      "transition": "slide", "music": None, "director": "brief"}, scenes)
        before = variety.history("tbilisi-today")
        got = plan.picks(story, look="cards", music="off")
        nov = got["novelty"]
        self.assertEqual(nov["nearest"], "99")
        self.assertEqual((nov["fingerprint"]["director"], nov["fingerprint"]["scenes"]), ("brief", scenes))
        self.assertEqual({k: nov["fingerprint"][k] for k in ("hook", "motif", "enter", "transition")},
                         {k: got[k] for k in ("hook", "motif", "enter", "transition")})
        self.assertLess(nov["similarity"], variety.TOO_CLOSE)
        self.assertEqual(variety.history("tbilisi-today"), before)  # planning uses nothing up

    def test_a_render_records_the_guard_and_warns(self):
        from tt_shorts import engine, formats, props
        work = pathlib.Path(self.home.name) / "work"
        work.mkdir()
        nov = {"similarity": 5.0, "distance": 0.286, "nearest": "40", "too_close": True, "rerolls": 3, "kept": False,
               "warning": "novelty: after 3 re-roll(s) ..."}
        p = {"durationInFrames": 900, "variant": "cards", "style": {"hook": "stack", "director": "data"},
             "transition": "line", "outro": "card", "music": None, "scenes": [{"type": "hook"}], "novelty": nov}
        target = pathlib.Path(self.home.name) / "out" / "x.mp4"
        touch = lambda w, pr, t: (t.parent.mkdir(parents=True, exist_ok=True), t.touch())  # noqa: E731
        with mock.patch.object(props, "build", return_value=(work, p)), \
                mock.patch.object(props, "render_video", side_effect=touch), \
                mock.patch.dict(os.environ, {"VEASY_PROBE": "0"}):
            r = engine.render_story(ROOT / "stories" / "24835-brief.json", formats.get("news"), "silent", target)
        self.assertEqual((r["problems"], r["warnings"]), ([], [nov["warning"]]))  # a warning, never a problem
        row = variety.history("tbilisi-today")[0]
        self.assertEqual((row["rerolls"], row["novelty"]), (3, 0.286))

    def test_report_shows_the_average_distance(self):
        for i in range(6):
            variety.record("tbilisi-today", 60 + i, "cards", {"hook": "stack", "motif": "grid", "enter": "rise",
                                                              "transition": "line", "music": None}, self.SCENES)
        r = variety.report("tbilisi-today")["novelty"]
        self.assertEqual((r["mean_distance"], r["too_close"], r["videos"]), (0.0, 5, 5))  # six copies
        self.assertEqual(variety.spread([]), None)


class DrawingQuality(unittest.TestCase):
    def good(self):
        s = json.loads((ROOT / "stories" / "veasy-scenes.json").read_text(encoding="utf-8"))
        return next(x["svg"] for x in s["scenes"] if x["type"] == "draw")

    def test_the_demo_drawing_passes(self):
        self.assertEqual(art.scene_problems(self.good()), [])

    def test_small_static_or_loud_drawings_are_sent_back(self):
        tiny = ('<rect x="10" y="10" width="40" height="40" stroke="INK"/><circle cx="30" cy="30" r="5" stroke="INK"/>'
                '<line x1="1" y1="1" x2="9" y2="9" stroke="INK"/><line x1="2" y1="1" x2="9" y2="9" stroke="INK"/>'
                '<line x1="3" y1="1" x2="9" y2="9" stroke="INK"/><line x1="4" y1="1" x2="9" y2="9" stroke="INK"/>')
        found = " ".join(art.scene_problems(tiny))
        self.assertIn("small", found)
        self.assertIn("builds up", found)
        loud = self.good().replace('stroke="INK"', 'stroke="ACCENT"').replace('stroke="MUTED"', 'stroke="ACCENT"')
        loud += "".join(f'<circle class="p" style="--d:1s" cx="{100 + i * 10}" cy="100" r="4" fill="ACCENT"/>' for i in range(6))
        self.assertTrue(any("ACCENT is on" in p for p in art.scene_problems(loud)))
        off = self.good() + '<rect x="900" y="600" width="400" height="300" stroke="INK"/>'
        self.assertTrue(any("outside" in p for p in art.scene_problems(off)))

    def test_paths_count_with_relative_commands_and_translations(self):
        pts = art._path_points("M10 10 l 20 0 v 30 h -20 z")
        self.assertEqual(pts[:4], [(10, 10), (30, 10), (30, 40), (10, 40)])
        tree, _ = art.sanitize('<g transform="translate(500 300)"><rect x="0" y="0" width="10" height="10" stroke="INK"/></g>')
        self.assertIn((500.0, 300.0), art._box(tree))

    def test_a_failing_drawing_is_dropped_not_the_video(self):
        s = json.loads((ROOT / "stories" / "veasy-scenes.json").read_text(encoding="utf-8"))
        for x in s["scenes"]:
            if x["type"] == "draw":
                x["svg"] = "<image/>"
        kept, dropped = art.drop_bad(s)
        self.assertEqual(dropped, 1)
        self.assertNotIn("draw", [x["type"] for x in kept["scenes"]])
        self.assertEqual(len(kept["scenes"]), len(s["scenes"]) - 1)
        good = json.loads((ROOT / "stories" / "veasy-scenes.json").read_text(encoding="utf-8"))
        self.assertEqual(art.drop_bad(good)[1], 0)

    def test_drawing_is_on_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(writer.DRAW_ENV, None)
            self.assertTrue(writer.drawing())
            self.assertIn('"svg"', writer._prompt({"headline": "x"}, ["ა 1"]))
        with mock.patch.dict(os.environ, {writer.DRAW_ENV: "0"}):
            self.assertFalse(writer.drawing())

    def test_variety_rotates_styles_least_used_first(self):
        home = tempfile.TemporaryDirectory()
        with mock.patch.dict(os.environ, {"VEASY_HOME": home.name}):
            picked = []
            for i in range(10):
                s = variety.pick_style("tbilisi-today", 5000 + i, program="news")
                variety.record("tbilisi-today", 5000 + i, "editorial", {"style": s}, ["hook", "end"])
                picked.append(s)
            # Distinct styles are rotated
            self.assertGreater(len(set(picked)), 1)
            # Re-render keeps its style
            self.assertEqual(variety.pick_style("tbilisi-today", 5000, program="news"), picked[0])
        home.cleanup()

    def test_novelty_guard_sees_style(self):
        fp1 = variety.fingerprint({"style": "swiss-motion", "hook": "stack", "motif": "grid", "enter": "rise",
                                   "transition": "line", "music": None}, ["hook", "end"])
        fp2 = variety.fingerprint({"style": "swiss-motion", "hook": "stack", "motif": "grid", "enter": "rise",
                                   "transition": "line", "music": None}, ["hook", "end"])
        fp3 = variety.fingerprint({"style": "dataviz", "hook": "stack", "motif": "grid", "enter": "rise",
                                   "transition": "line", "music": None}, ["hook", "end"])
        # Same style shares +1 similarity compared to different style
        sim_same = variety.similarity(fp1, fp2)
        sim_diff = variety.similarity(fp1, fp3)
        self.assertEqual(round(sim_same - sim_diff, 1), 1.0)


if __name__ == "__main__":
    unittest.main()
