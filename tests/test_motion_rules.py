"""The motion rules (tt_shorts/motion_rules.py): each rule on a synthetic timeline, then the real stories and the hold."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, engine, motion_rules as m

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = m.FPS


def video(scenes, transition="line", outro="card", flow=None, cta="მოიწონე და გაუზიარე", chip=None):
    """Built props as props.build makes them: scenes [(type, seconds, fields)] laid end to end."""
    out, t = [], 0
    for typ, secs, fields in scenes:
        n = round(secs * FPS)
        out.append({"type": typ, "at": "x", "from": t, "duration": n, **fields})
        t += n
    return {"scenes": out, "durationInFrames": t, "transition": transition, "outro": outro, "outroFrom": chip,
            "style": {"hook": "stack", **({"flow": flow} if flow else {})}, "cta": cta}


def rules(p, rule):
    return [f for f in m.check(p)["findings"] if f["rule"] == rule]


HOOK = ("hook", 3.0, {"lines": ["გაზი შეწყდება"]})
END = ("end", 3.5, {})


class Read(unittest.TestCase):
    def test_need_is_half_a_second_and_a_third_per_word(self):
        self.assertAlmostEqual(m.need("ერთი"), 0.8)
        self.assertAlmostEqual(m.need("22:00 → 10:00"), 1.1)  # the arrow is no word
        self.assertAlmostEqual(m.need("ა ბ გ დ ე ვ ზ თ ი კ"), 3.5)

    def test_a_long_text_in_a_short_scene_holds(self):
        long = "აბონენტს დროებით შეუწყდება გაზის მიწოდება ორშაბათს ღამიდან სამშაბათის დილამდე ვარკეთილში"
        p = video([HOOK, ("stat", 2.5, {"value": 6400, "label": long}), END])
        found = rules(p, "read")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["hold"])
        self.assertEqual(found[0]["scene"], 1)
        self.assertEqual(m.hold_problems(p), [f"motion read: {found[0]['detail']}"])
        ok = video([HOOK, ("stat", 2.5, {"value": 6400, "label": "აბონენტს შეუწყდება"}), END])
        self.assertEqual(rules(ok, "read"), [])

    def test_later_texts_get_less_time_and_the_exit_is_not_reading_time(self):
        p = video([HOOK, ("points", 2.5, {"kicker": "რა", "headline": "ორი", "items": ["ა ბ გ", "დ ე ვ"]}), END])
        texts = m.timeline(p)[1]["texts"]
        shown = [t["shown"] for t in texts]
        self.assertEqual(shown, sorted(shown, reverse=True))  # staggered in
        self.assertAlmostEqual(shown[0], 2.5 - m.EXIT / FPS - m.ENTER_BASE, places=2)
        cut = m.timeline(video([HOOK, ("points", 2.5, {"kicker": "რა"}), END], transition="cut"))
        self.assertAlmostEqual(cut[1]["texts"][0]["shown"], 2.5 - m.ENTER_BASE, places=2)  # a plain cut has no exit

    def test_the_opening_is_readable_at_frame_0(self):
        rows = m.timeline(video([HOOK, END]))
        self.assertEqual({t["in"] for t in rows[0]["texts"]}, {0.0})

    def test_a_drawing_label_that_comes_in_late_holds(self):
        from tt_shorts import art
        svg = ('<g class="s" style="--d:0.2s"><rect x="100" y="100" width="700" height="400" stroke="INK"/></g>'
               '<g class="r" style="--d:2.2s"><text x="476" y="560" font-size="36">გაზი არ იქნება ორ დღე</text></g>')
        tree, _ = art.sanitize(svg)
        p = video([HOOK, ("draw", 3.5, {"art": tree}), END])
        found = rules(p, "read")
        self.assertEqual(len(found), 1, found)
        self.assertIn("გაზი არ იქნება", found[0]["detail"])
        p = video([HOOK, ("draw", 8.0, {"art": tree}), END])  # a longer scene: Draw.tsx keeps the delays, it fits
        self.assertEqual(rules(p, "read"), [])

    def test_the_call_to_action_is_read_on_the_end_card_or_the_chip(self):
        p = video([HOOK, ("points", 4.0, {"items": ["ა", "ბ"]}), ("end", 1.0, {})],
                  cta="მოიწონე გაუზიარე და გამოიწერე არხი ახლავე")
        self.assertTrue(any("მოიწონე" in f["detail"] for f in rules(p, "read")))
        chip = video([HOOK, ("points", 6.0, {"items": ["ა", "ბ"]})], outro="overlay", chip=round(8.5 * FPS),
                     cta="მოიწონე გაუზიარე და გამოიწერე არხი ახლავე")
        self.assertTrue(any("outro chip" in f["detail"] for f in rules(chip, "read")))


class Still(unittest.TestCase):
    def test_a_long_scene_with_nothing_new_is_a_warning(self):
        p = video([HOOK, ("quote", 9.0, {"text": "„ა ბ“", "by": "გ"}), END])
        found = rules(p, "still")
        self.assertEqual([f["scene"] for f in found], [1])
        self.assertFalse(found[0]["hold"])
        self.assertEqual(rules(video([HOOK, ("quote", 4.0, {"text": "„ა ბ“", "by": "გ"}), END]), "still"), [])

    def test_the_end_card_may_hold_still(self):
        self.assertEqual(rules(video([HOOK, ("end", 9.0, {})]), "still"), [])

    def test_the_data_director_holds_on_its_number(self):  # owner, 2026-11-03: the long hold wins for data
        def directed(secs, director="data", typ="stat"):
            p = video([HOOK, (typ, secs, {"value": 6400, "label": "აბონენტი"}), END])
            p["style"]["director"] = director
            return [f["scene"] for f in rules(p, "still")]
        self.assertEqual(directed(7.5), [])  # the number may hold
        self.assertEqual(directed(7.5, director=None), [1])  # without the director it is a warning as before
        self.assertEqual(directed(7.5, director="brief"), [1])  # and for a director that doesn't hold on it
        self.assertEqual(directed(7.5, typ="change"), [1])  # only the types the director names
        self.assertEqual(directed(m.HOLD_MAX + 3.0), [1])  # a hold has a limit too


class Cuts(unittest.TestCase):
    def scenes(self, kinds):
        return [HOOK] + [("points" if i % 2 else "stat", 3.0, {"transition": k}) for i, k in enumerate(kinds)]

    def test_more_than_three_kinds(self):
        self.assertEqual(rules(video(self.scenes(["line", "wipe", "dot", "line"])), "kinds"), [])
        found = rules(video(self.scenes(["line", "wipe", "dot", "cut"])), "kinds")
        self.assertEqual(len(found), 1)
        self.assertIn("4 transition kinds", found[0]["detail"])

    def test_the_loop_cross_fade_is_a_kind_too(self):
        p = video(self.scenes(["line", "wipe", "dot"]), outro="loop")
        self.assertEqual(m.cuts(p)[-1]["kind"], "crossfade")
        self.assertEqual(len(rules(p, "kinds")), 1)

    def test_one_kind_for_the_whole_video_never_ping_pongs(self):
        for tr in ("line", "panel", "wipe", "slide", "push", "dot", "cut"):
            p = video([HOOK, ("stat", 3, {}), ("points", 3, {}), ("quote", 3, {}), END], transition=tr)
            self.assertEqual(rules(p, "pingpong"), [], tr)

    def test_a_b_a(self):
        found = rules(video(self.scenes(["dot", "cut", "dot"])), "pingpong")
        self.assertEqual(len(found), 1)
        self.assertIn("dot, cut, dot: A-B-A", found[0]["detail"])
        self.assertEqual(rules(video(self.scenes(["dot", "cut", "cut"])), "pingpong"), [])

    def test_back_and_forth(self):  # a wipe goes right, a push left (without a director's current)
        found = rules(video(self.scenes(["wipe", "push"])), "pingpong")
        self.assertEqual(len(found), 1)
        self.assertIn("moves right", found[0]["detail"])
        self.assertIn("(push) left", found[0]["detail"])
        self.assertEqual(rules(video(self.scenes(["wipe", "push"]), flow=[-1, 0]), "pingpong"), [])  # one current
        self.assertEqual(rules(video(self.scenes(["wipe", "dot", "push"])), "pingpong"), [])  # not in a row
        self.assertEqual(len(rules(video(self.scenes(["slide", "line"])), "pingpong")), 1)

    def test_a_scene_may_carry_its_own_direction(self):
        sc = self.scenes(["slide", "slide"])
        sc[2] = (sc[2][0], sc[2][1], {**sc[2][2], "flow": [1, 0]})
        self.assertEqual(len(rules(video(sc), "pingpong")), 1)


class Repeat(unittest.TestCase):
    def test_two_of_a_type_in_a_row(self):
        found = rules(video([HOOK, ("where", 3, {}), ("where", 3, {}), END]), "repeat")
        self.assertEqual([f["scene"] for f in found], [2])
        self.assertEqual(rules(video([HOOK, ("where", 3, {}), ("stat", 3, {}), ("where", 3, {}), END]), "repeat"), [])


class Holds(unittest.TestCase):
    def test_only_unreadable_text_holds(self):
        self.assertEqual(m.HOLDS, ("read",))
        p = video([HOOK, ("where", 12, {}), ("where", 3, {"transition": "wipe"}), ("stat", 3, {"transition": "push"}),
                   END])
        r = m.check(p)
        self.assertEqual(r["holds"], [])
        self.assertEqual({w.split(":")[0] for w in r["warnings"]}, {"motion still", "motion repeat", "motion pingpong"})

    def test_options_list_the_rules(self):
        o = engine.options()
        self.assertEqual(set(o["motion_rules"]) - {"about"}, set(m.RULES))
        self.assertIn("plan", o["self_checks"])

    def test_no_shipped_story_is_held(self):
        """Today's stories in every look, with the silent engine's timings: warnings at most, never a hold."""
        from tt_shorts import props
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            for f in sorted((ROOT / "stories").glob("*.json")):
                for look in brand.LOOKS:
                    _, p = props.build(str(f), look, "silent", music="off")
                    self.assertEqual(m.hold_problems(p), [], f"{f.name} {look}")

    def test_render_story_holds_unreadable_text_like_the_probe(self):
        long = "აბონენტს დროებით შეუწყდება გაზის მიწოდება ორშაბათს ღამიდან სამშაბათის დილამდე ვარკეთილში"
        p = video([HOOK, ("stat", 2.5, {"value": 6400, "label": long}), END])
        p.update(variant="cards", music=None)
        story = ROOT / "stories" / "24835.json"
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            work = pathlib.Path(home) / "work"
            work.mkdir()
            with mock.patch.object(engine.props, "build", return_value=(work, p)), \
                    mock.patch.object(engine.props, "render_video"), \
                    mock.patch.object(engine, "_probe_render", return_value=None), \
                    mock.patch.object(engine.variety, "record"):
                r = engine.render_story(story, {**_fmt(), "min_seconds": 1, "max_seconds": 60}, "silent",
                                        out_path=pathlib.Path(home) / "x.mp4")
        self.assertTrue(r["problems"] and r["problems"][0].startswith("motion read:"), r["problems"])
        self.assertEqual(r["motion"]["holds"], r["problems"])


class TextsContract(unittest.TestCase):
    def test_texts_reading_time_holds_when_too_short(self):
        # 5 words: needs 0.5 + 5 * 0.3 = 2.0s
        text = "ერთი ორი სამი ოთხი ხუთი"
        # Visible from 0.0s to 0.8s (duration 0.8s < 2.0s)
        samples = [
            (0.0, [{"id": "card1", "text": text, "x0": 100, "y0": 400, "x1": 800, "y1": 600}]),
            (0.4, [{"id": "card1", "text": text, "x0": 100, "y0": 400, "x1": 800, "y1": 600}]),
            (0.8, [{"id": "card1", "text": text, "x0": 100, "y0": 400, "x1": 800, "y1": 600}]),
            (1.2, []),
        ]
        res = m.check_texts_track(samples)
        self.assertTrue(any("motion read:" in h for h in res["holds"]))
        self.assertTrue(any("visible for 0.8 s" in h for h in res["holds"]))

    def test_texts_reading_time_passes_when_sufficient(self):
        # 2 words: needs 0.5 + 2 * 0.3 = 1.1s
        text = "გაზი შეწყდება"
        # Visible from 0.0s to 1.5s
        samples = [
            (0.0, [{"id": "h1", "text": text, "x0": 100, "y0": 400, "x1": 600, "y1": 500}]),
            (0.5, [{"id": "h1", "text": text, "x0": 100, "y0": 400, "x1": 600, "y1": 500}]),
            (1.0, [{"id": "h1", "text": text, "x0": 100, "y0": 400, "x1": 600, "y1": 500}]),
            (1.5, [{"id": "h1", "text": text, "x0": 100, "y0": 400, "x1": 600, "y1": 500}]),
            (2.0, []),
        ]
        res = m.check_texts_track(samples)
        self.assertEqual(res["holds"], [])

    def test_texts_safe_zone_violations_hold(self):
        # Header violation: y0 < 248
        samples_header = [
            (0.0, [{"id": "t1", "text": "სათაური", "x0": 100, "y0": 150, "x1": 600, "y1": 300}]),
        ]
        res_h = m.check_texts_track(samples_header)
        self.assertTrue(any("enters header zone at y=150.0" in h for h in res_h["holds"]))

        # Captions violation: y1 > 1380
        samples_cap = [
            (0.0, [{"id": "t2", "text": "შინაარსი", "x0": 100, "y0": 1200, "x1": 600, "y1": 1420}]),
        ]
        res_c = m.check_texts_track(samples_cap)
        self.assertTrue(any("enters captions zone at y=1420.0" in h for h in res_c["holds"]))

        # Social rail violation: y1 > 1100 and x1 > 940
        samples_rail = [
            (0.0, [{"id": "t3", "text": "ღილაკი", "x0": 900, "y0": 1150, "x1": 980, "y1": 1250}]),
        ]
        res_r = m.check_texts_track(samples_rail)
        self.assertTrue(any("enters social rail at x=980.0" in h for h in res_r["holds"]))

    def test_tagged_header_and_captions_exempt_from_zone_violation(self):
        samples_ok = [
            (0.0, [
                {"id": "header", "text": "tbilisi.today", "x0": 72, "y0": 80, "x1": 400, "y1": 160},
                {"id": "captions", "text": "ეს არის ტიტრი", "x0": 72, "y0": 1400, "x1": 800, "y1": 1520},
            ]),
        ]
        res = m.check_texts_track(samples_ok)
        safe_holds = [h for h in res["holds"] if "safe_zone" in h]
        self.assertEqual(safe_holds, [])


def _fmt():
    from tt_shorts import formats
    return formats.get("news")


if __name__ == "__main__":
    unittest.main()
