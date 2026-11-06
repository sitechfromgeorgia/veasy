"""The scenes added on 2026-11-02: draw (the writer's drawing, made safe), pair, steps, bars, trend, change, and the
transitions between scenes. Videos go out without a human review: a drawing can't carry a script or a foreign color,
and a chart can't show a number the articles don't have."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import art, engine, formats, ka_check, news_check, props, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOOD = ('<g class="s" style="--d:0.2s"><rect x="236" y="210" width="480" height="300" rx="24" stroke="INK" '
        'stroke-width="7"/></g><g class="r" style="--d:0.6s"><path d="M236 210 L262 120 L742 120" stroke="PAPER"/>'
        '<line x1="1" y1="2" x2="3" y2="4" stroke="MUTED"/></g><circle class="p" style="--d:1.2s" cx="476" cy="345" '
        'r="40" fill="ACCENT" stroke="none"/><rect x="96" y="250" width="96" height="220" fill="COAL" stroke="LINE" '
        'transform="translate(10 0) rotate(5)"/><text class="r" style="--d:1.6s" x="476" y="590" font-size="36">'
        'გაზის მილი 2026</text>')


def story(**scene):
    return {"id": "t", "category": "tech", "date": "2026-11-02T10:00:00Z", "narration": "ერთი ორი სამი ოთხი ხუთი ექვსი",
            "scenes": [{"type": "hook", "at": "ერთი", "lines": ["x"]}, {"at": "ოთხი", **scene}]}


class Draw(unittest.TestCase):
    def test_a_good_drawing_becomes_a_tree_of_tokens_and_motion(self):
        tree, problems = art.sanitize(GOOD)
        self.assertEqual(problems, [])
        self.assertEqual([n["tag"] for n in tree], ["g", "g", "circle", "rect", "text"])
        self.assertEqual((tree[0]["motion"], tree[0]["delay"]), ("s", 0.2))
        self.assertEqual(tree[1]["children"][0]["attrs"]["stroke"], "INK")  # sitech-shorts' PAPER is the ink
        self.assertEqual(tree[3]["attrs"]["fill"], "CANVAS")  # and COAL the canvas
        self.assertEqual(tree[3]["attrs"]["transform"], "translate(10 0) rotate(5)")
        self.assertEqual(tree[4]["text"], "გაზის მილი 2026")
        self.assertEqual(tree[4]["attrs"]["fill"], "INK")  # a label without a fill is ink

    def test_the_accent_is_only_ever_a_dot(self):  # owner, 2026-11-03: red fills in drawings are ink
        tree, problems = art.sanitize(
            '<circle cx="40" cy="40" r="14" fill="ACCENT" stroke="ACCENT"/>'  # a dot keeps its accent
            '<ellipse cx="80" cy="40" rx="10" ry="12" fill="ACCENT"/>'
            '<circle cx="40" cy="40" r="60" fill="ACCENT"/>'  # a big red disc is not the dot
            '<path d="M0 0 L10 10" fill="ACCENT" stroke="ACCENT"/><rect x="1" y="1" width="9" height="9" fill="ACCENT"/>'
            '<g stroke="ACCENT"><line x1="0" y1="0" x2="5" y2="5" stroke="INK"/></g>'
            '<text x="1" y="1" fill="ACCENT">წითელი</text>')
        self.assertEqual(problems, [])  # repainted, not sent back
        paint = [(n["tag"], n["attrs"].get("fill"), n["attrs"].get("stroke")) for n in art._walk(tree)]
        self.assertEqual(paint, [("circle", "ACCENT", "ACCENT"), ("ellipse", "ACCENT", None), ("circle", "INK", None),
                                 ("path", "INK", "INK"), ("rect", "INK", None), ("g", None, "INK"),
                                 ("line", None, "INK"), ("text", "INK", None)])
        four = "".join(f'<circle class="p" style="--d:{i}s" cx="{100 + i * 10}" cy="100" r="6" fill="ACCENT"/>'
                       for i in range(art.MAX_DOTS + 1))
        self.assertTrue(any("ACCENT is on 4 dots" in p for p in art.quality(art.sanitize(four)[0])))

    def test_unsafe_or_off_brand_parts_are_removed_and_reported(self):
        bad = GOOD + ('<image href="x.png"/><script>alert(1)</script><rect onload="x()" x="1" y="1" width="2" height="2" '
                      'fill="#ff0000" class="spin" style="color:red" transform="matrix(1 0 0 1 0 0)"/>'
                      '<path d="url(javascript:x)" stroke="INK"/>')
        tree, problems = art.sanitize(bad)
        text = " ".join(problems)
        for want in ("<image>", "<script>", '"onload"', "#ff0000", 'class "spin"', 'style "color:red"', "matrix",
                     "unsafe value"):
            self.assertIn(want, text)
        flat = json.dumps(tree)
        for gone in ("image", "script", "onload", "#ff0000", "matrix", "javascript"):
            self.assertNotIn(gone, flat)

    def test_size_and_count_limits(self):
        self.assertTrue(any("only 1 elements" in p for p in art.sanitize('<circle cx="1" cy="1" r="2"/>')[1]))
        self.assertTrue(art.sanitize("<g><rect")[1][0].startswith("draw: svg is not valid XML"))
        long = GOOD + '<text x="1" y="1">ეს წარწერა ძალიან ძალიან გრძელია</text>'
        self.assertTrue(any("longer than 18" in p for p in art.sanitize(long)[1]))
        self.assertTrue(art.sanitize("")[1])

    def test_only_labels_are_on_screen_words(self):  # coordinates are not numbers a viewer reads (N2)
        s = story(type="draw", svg=GOOD)
        self.assertEqual(news_check.numbers(news_check.screen_text(s)), {"2026"})
        self.assertIn(("scene 1 (draw) svg text", "გაზის მილი 2026"), ka_check.screen_texts(s))

    def test_engine_checks_the_drawing(self):
        self.assertEqual(engine.shape_problems({"type": "draw", "svg": GOOD}), [])
        self.assertTrue(engine.shape_problems({"type": "draw", "svg": "<image/>"}))

    def test_props_carry_the_tree_not_the_svg(self):
        out = props._scene({"type": "draw", "svg": GOOD, "at": "x"}, 0, 90)
        self.assertNotIn("svg", out)
        self.assertEqual(out["art"], art.sanitize(GOOD)[0])
        self.assertEqual((out["from"], out["duration"]), (0, 90))


class Writer(unittest.TestCase):
    def test_the_switch_decides_whether_the_writer_draws(self):  # on by default since art.quality; 0 turns it off
        from tt_shorts import writer
        with mock.patch.dict("os.environ", {writer.DRAW_ENV: "0"}):
            off = writer._prompt({"headline": "x"}, ["ა 1"])
            self.assertNotIn('"svg"', off)
            self.assertNotIn(art.GUIDE[:40], off)
            self.assertIn('never use a "draw" scene', off)
            self.assertIn('"type": "bars"', off)  # the other new scenes are always on
        with mock.patch.dict("os.environ", {writer.DRAW_ENV: "1"}):
            on = writer._prompt({"headline": "x"}, ["ა 1"])
            self.assertIn('"svg"', on)
            self.assertIn(art.GUIDE[:40], on)


class Shapes(unittest.TestCase):
    def test_counts_items_and_numbers(self):
        p = engine.shape_problems
        self.assertEqual(p({"type": "bars", "items": [{"label": "a", "value": 3}, {"label": "b", "value": 1.5}]}), [])
        self.assertTrue(p({"type": "bars", "items": [{"label": "a", "value": 3}]}))  # 2-5
        self.assertTrue(p({"type": "bars", "items": [{"label": "a", "value": 3}, {"label": "b", "value": -1}]}))
        self.assertTrue(p({"type": "bars", "items": [{"label": "a", "value": "3"}, {"label": "b", "value": 1}]}))
        self.assertTrue(p({"type": "trend", "items": [{"label": "a", "value": 1}, {"label": "b", "value": 2}]}))  # 3-8
        self.assertTrue(p({"type": "pair", "items": [{"title": "a"}, {"sub": "b"}]}))
        self.assertTrue(p({"type": "steps", "items": ["a", "b", "c", "d", "e"]}))
        self.assertTrue(p({"type": "change", "before": {"label": "a", "value": 1}, "after": {"label": "b"}}))
        self.assertEqual(p({"type": "change", "before": {"label": "a", "value": 1}, "after": {"label": "b", "value": 2}}), [])
        # new scene types shape checks
        self.assertEqual(p({"type": "ranking", "items": [{"label": "a", "rank": 1}, {"label": "b", "rank": 2}, {"label": "c", "rank": 3}]}), [])
        self.assertTrue(p({"type": "ranking", "items": [{"rank": 1}, {"label": "b"}]}))  # missing label
        self.assertEqual(p({"type": "versus", "items": [{"title": "a"}, {"title": "b"}]}), [])
        self.assertTrue(p({"type": "versus", "items": [{"title": "a"}]}))  # needs 2
        self.assertEqual(p({"type": "countdown", "value": 14, "label": "ვადა"}), [])
        self.assertTrue(p({"type": "countdown", "value": -1, "label": "ვადა"}))
        self.assertEqual(p({"type": "calendar", "day": 15, "month": "მაისი", "event": "სხდომა"}), [])
        self.assertTrue(p({"type": "calendar", "day": 35, "month": "მაისი", "event": "სხდომა"}))  # day > 31
        self.assertEqual(p({"type": "glossary", "term": "კანონი", "definition": "წესი"}), [])
        self.assertTrue(p({"type": "glossary", "term": "", "definition": "წესი"}))
        self.assertEqual(p({"type": "checklist", "items": [{"text": "დოკუმენტი", "state": "done"}, {"text": "ფორმა", "state": "pending"}]}), [])
        self.assertTrue(p({"type": "checklist", "items": [{"state": "done"}]}))
        self.assertEqual(p({"type": "impact", "target": "მგზავრები", "change": "ტარიფი", "when": "ხვალ"}), [])
        self.assertTrue(p({"type": "impact", "target": "", "change": "ტარიფი", "when": "ხვალ"}))
        self.assertEqual(p({"type": "route", "stops": ["თბილისი", "ბათუმი"]}), [])
        self.assertTrue(p({"type": "route", "stops": ["თბილისი"]}))  # needs >= 2
        self.assertEqual(p({"type": "budget", "items": [{"label": "ა", "value": 10}, {"label": "ბ", "value": 20}]}), [])
        self.assertTrue(p({"type": "budget", "items": [{"label": "ა", "value": -5}, {"label": "ბ", "value": 20}]}))

    def test_chart_numbers_must_be_in_the_articles(self):  # N2 reads numbers at any depth now
        s = story(type="bars", items=[{"label": "ა", "value": 120}, {"label": "ბ", "value": 7.5}])
        s["scenes"].append({"type": "change", "at": "ხუთი", "before": {"label": "2024", "value": 3},
                            "after": {"label": "2025", "value": 4}})
        found = " ".join(news_check.problems(s, ["120 და 7.5, 2024 წელს 3"]))
        self.assertIn("N2: number 2025", found)
        self.assertIn("N2: number 4", found)
        self.assertNotIn("number 120", found)

    def test_georgian_rules_see_the_new_fields(self):
        s = story(type="pair", between="versus", items=[{"title": "ა", "sub": "გამოიწერეთ"}, {"title": "ბ"}])
        s["scenes"].append({"type": "change", "at": "ხუთი", "unit": "ლარი", "before": {"label": "თქვენ", "value": 1},
                            "after": {"label": "ბ", "value": 2}})
        found = " ".join(ka_check.problems(s, {}))
        self.assertIn("pair) items", found)  # the sub
        self.assertIn("change) before", found)
        self.assertIn('plain English word "versus"', found)

    def test_every_type_is_allowed_by_the_news_rules(self):
        self.assertEqual(set(engine.SCENES), news_check.SCENE_TYPES)

    def test_sample_stories_pass(self):  # the demos use every scene type, old and new
        used = set()
        for name in ("veasy-demo", "veasy-scenes", "veasy-icons", "sitech-cybercartel", "veasy-brushes",
                     "digest-2026-11-01", "../tests/fixtures/rubric-agree", "veasy-new-01", "veasy-new-02",
                     "visual-context-demo"):  # agree: a synthetic test fixture
            s = json.loads((ROOT / "stories" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(engine.check_story(s), [], name)
            used |= {x["type"] for x in s["scenes"]}
        self.assertEqual(used, set(engine.SCENES))


class Transitions(unittest.TestCase):
    def test_one_list(self):
        self.assertEqual(formats.TRANSITIONS, ("auto",) + props.TRANSITIONS)
        self.assertEqual(set(engine.options()["transitions"]), set(formats.TRANSITIONS))

    def test_auto_is_the_look_s_own(self):
        self.assertEqual(props.transition_for("auto", "kinetic"), "panel")
        self.assertEqual(props.transition_for(None, "editorial"), "line")
        self.assertEqual(props.transition_for("dot", "cards"), "dot")

    def test_a_format_can_choose_one(self):
        self.assertEqual(formats.get("news", transition="push")["transition"], "push")
        with self.assertRaises(formats.FormatError):
            formats.get("news", transition="spin")

    def test_props_carry_it(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            _, p = props.build(str(ROOT / "stories" / "veasy-scenes.json"), "kinetic", "silent", music="off")
            self.assertIn(p["transition"], variety.TRANSITIONS["kinetic"])  # auto: variety picks one that suits the look
            _, p = props.build(str(ROOT / "stories" / "veasy-scenes.json"), "cards", "silent", music="off", transition="wipe")
            self.assertEqual(p["transition"], "wipe")
            draw = next(s for s in p["scenes"] if s["type"] == "draw")
            self.assertTrue(draw["art"])


if __name__ == "__main__":
    unittest.main()
