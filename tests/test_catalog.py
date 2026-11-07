"""The brush catalog (brushes/<type>.json, tt_shorts/catalog.py): one file per scene type generates the tables the
engine used to keep by hand in seven places. The generated tables must equal the hand-written ones for the 16 types
that existed before the catalog (tests/fixtures/scenes_before.json, captured from the code of 2026-11-02)."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from tt_shorts import catalog, engine, ka_check, news_check, speech, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent
BEFORE = json.loads((ROOT / "tests" / "fixtures" / "scenes_before.json").read_text(encoding="utf-8"))
OLD = list(BEFORE["scenes"])
NEW = ("share", "rail", "compare", "link", "agree", "chapter", "ranking", "versus", "countdown", "calendar", "glossary", "checklist", "impact", "route", "budget", "plate")
# Kit-only types: a brush with no writer line, not on news_check.SCENE_TYPES (an owner decides; ROADMAP C6, docs/research/forms-look-result.md).
KIT_ONLY = ("figures",)
# The changes made on purpose: stat takes a style (count, wheel, flap); the draw line's SVG quotes are escaped, so
# the line the writer copies is JSON.
STAT_STYLE = "style"
DRAW_LINE_BEFORE = '   {"type": "draw", "at": "...", "kicker": "...", "headline": "...", "svg": "<g class="s" style="--d:0.3s">...</g>", "label": "..."},'


class Tables(unittest.TestCase):
    def test_every_scene_type_has_a_brush(self):
        self.assertEqual(set(catalog.types()), set(OLD) | set(NEW) | set(KIT_ONLY))
        self.assertEqual(catalog.types()[0], "hook")
        self.assertEqual(catalog.types()[-1], "end")

    def test_scenes_equal_the_hand_written_table(self):
        for t in OLD:
            req, opt, what = BEFORE["scenes"][t]
            got = engine.SCENES[t]
            want_opt = opt + [STAT_STYLE] if t == "stat" else opt
            self.assertEqual((list(got[0]), list(got[1]), got[2]), (req, want_opt, what), t)
        self.assertEqual([t for t in engine.SCENES if t in OLD], OLD)  # the menu keeps its order

    def test_counts_seconds_and_words_equal_today(self):
        self.assertEqual({t: list(v) for t, v in engine.COUNTS.items() if t in OLD}, BEFORE["counts"])
        self.assertEqual({t: speech.MIN_SCENE.get(t, speech.MIN_SCENE_DEFAULT) for t in OLD}, BEFORE["min_scene"])
        self.assertEqual({t: ka_check.MIN_WORDS.get(t, ka_check.MIN_WORDS_DEFAULT) for t in OLD}, BEFORE["min_words"])
        self.assertEqual((speech.MIN_SCENE_DEFAULT, ka_check.MIN_WORDS_DEFAULT), (2.5, 6))

    def test_the_georgian_check_reads_every_text_slot(self):
        self.assertEqual(list(ka_check.FIELDS[:len(BEFORE["ka_fields"])]), BEFORE["ka_fields"])
        self.assertEqual(list(ka_check.ITEM_FIELDS[:len(BEFORE["ka_item_fields"])]), BEFORE["ka_item_fields"])
        top, inner = catalog.text_fields()
        self.assertTrue(set(top) - {"prefix", "suffix"} <= set(ka_check.FIELDS))
        self.assertTrue(set(inner) <= set(ka_check.ITEM_FIELDS))
        self.assertIn("edge", ka_check.FIELDS)  # link's verb is Georgian on screen

    def test_the_writer_s_lines_equal_today(self):
        now = catalog.schema().splitlines()
        for line in BEFORE["schema"]:
            if line.startswith('   {"type": "draw"'):
                self.assertEqual(line, DRAW_LINE_BEFORE)
                fixed = line.replace('class="s" style="--d:0.3s"', 'class=\\"s\\" style=\\"--d:0.3s\\"').rstrip(",")
                self.assertIn(fixed, [x.rstrip(",") for x in now])
                json.loads(fixed.strip())  # the line the writer copies is JSON now
            elif line.startswith('   {"type"'):
                self.assertIn(line.rstrip(","), [x.rstrip(",") for x in now], line)
        head = BEFORE["schema"][:BEFORE["schema"].index(' "scenes": [') + 1]
        self.assertEqual(now[:len(head)], head)  # the story's own keys, unchanged
        generic = [x for x in BEFORE["schema"] if x.startswith("- ") and "scene" in x and '"' not in x[:14]]
        for rule in generic + ["- every number on screen and in the narration must appear in the articles;"]:
            self.assertIn(rule, now)
        self.assertEqual(writer.SCHEMA, catalog.schema())

    def test_a_menu_shows_only_its_lines_and_rules(self):
        some = catalog.schema(["hook", "share", "end"])
        shown = {json.loads(x.strip().rstrip(","))["type"] for x in some.splitlines() if x.startswith('   {"type"')}
        self.assertEqual(shown, {"hook", "share", "end"})
        self.assertIn('"share": one percent', some)
        self.assertNotIn('"sign": one pictogram', some)
        self.assertIn('"em" (optional', some)  # hook and share take a mark
        self.assertNotIn('"em" (optional', catalog.schema(["end"]))
        every = catalog.schema()
        self.assertTrue(all(f'{{"type": "{t}"' in every for t in catalog.types() if catalog.get(t)["schema"]))
        self.assertNotIn('{"type": "sources"', every)  # the outlets come from the data: no line to copy


class Brushes(unittest.TestCase):
    def test_every_example_is_a_valid_scene(self):
        for t, b in catalog.load_all().items():
            ex = b["example"]
            self.assertEqual(engine.shape_problems(ex), [], t)
            self.assertEqual([f for f in engine.SCENES[t][0] if ex.get(f) in (None, "", [])], [], t)
            if ex.get("em"):
                from tt_shorts import marks
                self.assertTrue(marks.locate(ex), t)

    def test_options_carry_every_card(self):
        o = engine.options()["scenes"]
        self.assertEqual(set(o), set(catalog.types()))
        for t, card in o.items():
            for k in ("required", "optional", "shows", "use_when", "avoid_when", "pairs_with", "slots", "min_seconds",
                      "min_words", "families_deny", "em", "example"):
                self.assertIn(k, card, t)
        self.assertEqual(engine.options()["em"]["kinds"], list(catalog.MARKS))

    def test_bad_brushes_are_refused(self):
        good = json.loads((ROOT / "brushes" / "share.json").read_text(encoding="utf-8"))
        bads = [
            {"order": 0}, {"what": ""}, {"slots": {**good["slots"], "x": {"kind": "colour"}}},
            {"slots": {"kicker": {"kind": "text", "max": 24}, "value": {"kind": "num", "required": True}}},  # order
            {"slots": {**good["slots"], "em": {"kind": "text", "max": 9}}},  # em belongs to every scene
            {"families_deny": ["opinion"]}, {"min_seconds": 9}, {"em": {"fields": ["nope"], "kinds": ["circle"]}},
            {"em": {"fields": ["label"], "kinds": ["scribble"]}}, {"schema": {"type": "stat", "at": "..."}},
            {"example": {**good["example"], "label": "ძალიან " * 12}},  # past its 48 characters
            {"color": "#ff0000"},
        ]
        for bad in bads:
            with self.assertRaises(catalog.CatalogError, msg=str(bad)):
                catalog.validate("share", {**good, **bad})
        with self.assertRaises(catalog.CatalogError):
            catalog.validate("other", good)  # the type is its file name
        missing = dict(good)
        missing.pop("use_when")
        with self.assertRaises(catalog.CatalogError):
            catalog.validate("share", missing)

    def test_slots_are_typed(self):
        p = catalog.slot_problems
        self.assertEqual(p({"type": "stat", "value": 6400, "label": "აბონენტი"}), [])
        self.assertTrue(any("needs a number" in x for x in p({"type": "stat", "value": "6400", "label": "ა"})))
        self.assertTrue(any("at most 24" in x for x in p({"type": "stat", "value": 1, "label": "ა", "kicker": "ა" * 30})))
        self.assertTrue(any("use one of count, wheel, flap" in x for x in p({"type": "stat", "value": 1, "label": "ა",
                                                                             "style": "spin"})))
        self.assertTrue(any("items[1].label" in x for x in p({"type": "bars", "items": [
            {"label": "ა", "value": 1}, {"label": "ა" * 30, "value": 2}]})))
        self.assertEqual(p({"type": "bars", "items": [{"label": "a", "value": 3}]}), ["items: 1, needs 2-5"])

    def test_a_family_can_deny_a_value(self):
        flap = {"type": "stat", "value": 1, "label": "ა", "style": "flap"}
        self.assertTrue(catalog.family_problems(flap, "politics"))
        self.assertTrue(catalog.family_problems(flap, "crime"))
        self.assertEqual(catalog.family_problems(flap, "sports"), [])
        self.assertEqual(catalog.family_problems({**flap, "style": "wheel"}, "politics"), [])


class AddingAType(unittest.TestCase):
    """What brief 2 (agree, chapter) does: one brush file is the whole Python side of a new type."""

    def test_a_new_brush_reaches_every_table(self):
        with tempfile.TemporaryDirectory() as d:
            for f in (ROOT / "brushes").glob("*.json"):
                shutil.copy(f, d)
            tally = {"type": "tally", "order": 45, "what": "facts counted across outlets", "use_when": "x",
                     "avoid_when": "y", "pairs_with": ["sources"], "families_deny": ["crime"],
                     "slots": {"items": {"kind": "list", "count": [2, 4], "of": {"fact": {"kind": "text", "max": 30}},
                                         "required": True}, "kicker": {"kind": "text", "max": 24}},
                     "min_seconds": 3.4, "min_words": 7, "em": {"fields": [], "kinds": []},
                     "schema": {"type": "tally", "at": "...", "items": [{"fact": "..."}]}, "rules": ["\"tally\": z;"],
                     "example": {"type": "tally", "at": "ოთხი მედია", "items": [{"fact": "ა"}, {"fact": "ბ"}]}}
            pathlib.Path(d, "tally.json").write_text(json.dumps(tally, ensure_ascii=False), encoding="utf-8")
            from unittest import mock
            catalog._load.cache_clear()
            try:
                with mock.patch.object(catalog, "DIR", pathlib.Path(d)):
                    self.assertEqual(catalog.scenes()["tally"], (["items"], ["kicker"], "facts counted across outlets"))
                    self.assertEqual(catalog.counts()["tally"], (2, 4))
                    self.assertEqual((catalog.min_scene()["tally"], catalog.min_words()["tally"]), (3.4, 7))
                    self.assertIn("fact", catalog.text_fields()[1])
                    self.assertIn('{"type": "tally"', catalog.schema())
                    self.assertNotIn('{"type": "tally"', catalog.schema(["hook", "end"]))
                    self.assertEqual(catalog.types().index("tally"), catalog.types().index("where") + 1)  # order 45
                    self.assertTrue(catalog.family_problems({"type": "tally"}, "crime"))
            finally:
                catalog._load.cache_clear()

    def test_the_catalog_imports_no_engine(self):  # engine, writer, speech and ka_check import it: no cycle
        code = ("import sys; import tt_shorts.catalog as c; c.load_all(); "
                "bad = [m for m in ('tt_shorts.engine', 'tt_shorts.writer', 'tt_shorts.speech', 'tt_shorts.ka_check', "
                "'tt_shorts.news_check') if m in sys.modules]; print(bad); sys.exit(1 if bad else 0)")
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_news_keeps_its_own_allowlist(self):  # N1: a brush reaches the news only when SCENE_TYPES names it
        self.assertEqual(set(catalog.types()) - news_check.MADE_PICTURE_TYPES - set(KIT_ONLY), news_check.SCENE_TYPES)
        for t in KIT_ONLY:  # and the news writer is never offered one
            self.assertIsNone(catalog.load_all()[t]["schema"])
            self.assertNotIn(f'"type": "{t}"', catalog.schema())


if __name__ == "__main__":
    unittest.main()
