"""The engine's contract with agents: formats, options and the story check."""
import json
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, engine, formats, meta, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "sources.json").read_text(encoding="utf-8"))


def story(sid="24725"):
    return json.loads((ROOT / "stories" / f"{sid}.json").read_text(encoding="utf-8"))


class Formats(unittest.TestCase):
    def test_builtins_are_valid(self):
        every = formats.load_all()
        self.assertIn("news", every)
        self.assertEqual(every["news-roll"]["captions"], "roll")
        self.assertEqual(every["news"]["captions"], "page")

    def test_overrides_apply_and_none_is_ignored(self):
        f = formats.get("news", look="kinetic", voice=None)
        self.assertEqual((f["look"], f["voice"]), ("kinetic", "family"))

    def test_bad_choices_are_refused(self):
        for bad in ({"look": "neon"}, {"captions": "karaoke"}, {"voice": "Charon"}, {"music": "rock"}):
            with self.assertRaises(formats.FormatError):
                formats.get("news", **bad)
        with self.assertRaises(formats.FormatError):
            formats.get("no-such-show")

    def test_theme_is_a_format_choice(self):  # brand.json themes; default keeps every current render as it was
        self.assertEqual(formats.get("news")["theme"], "default")
        self.assertTrue(all(f["theme"] == "default" for f in formats.load_all().values()))
        self.assertEqual(formats.get("news", theme="auto")["theme"], "auto")
        self.assertEqual(formats.get("news", theme="light")["theme"], "light")  # a theme some pack has
        with self.assertRaises(formats.FormatError):
            formats.get("news", theme="neon")
        o = engine.options("sitech")
        self.assertEqual(o["themes"]["default"], "dark")
        self.assertEqual(set(o["themes"]["pack"]), {"dark", "light"})
        self.assertFalse(engine.options("tbilisi-today")["themes"]["pack"]["light"]["allowed"])
        self.assertIn("themes", o["brands"]["sitech"])

    def test_style_is_a_format_choice(self):
        self.assertIsNone(formats.get("news").get("style"))
        self.assertEqual(formats.get("news", style="swiss-motion")["style"], "swiss-motion")
        with self.assertRaises(formats.FormatError):
            formats.get("news", style="unknown-style-slug")

    def test_a_render_refuses_a_preview_theme(self):  # tbilisi-today light: allowed false until the owner says yes
        story = ROOT / "stories" / "24835.json"
        with mock.patch.object(engine.props, "build", side_effect=AssertionError("no build for a preview theme")):
            r = engine.render_story(story, formats.get("news", theme="light"), "silent")
        self.assertIn("allowed: false", r["problems"][0])

    def test_a_show_is_added_as_a_json_file(self):  # no code change needed for a new format
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "evening.json").write_text(json.dumps(
                {"label": "საღამოს ამბები", "look": "editorial", "voice": "anchor", "music": "politics", "max_seconds": 40}))
            pathlib.Path(d, "broken.json").write_text(json.dumps({"look": "neon"}))
            with mock.patch.object(formats, "DIR", pathlib.Path(d)):
                pathlib.Path(d, "broken.json").unlink()
                f = formats.get("evening")
                self.assertEqual((f["look"], f["captions"], f["max_seconds"]), ("editorial", "page", 40))
                pathlib.Path(d, "broken.json").write_text(json.dumps({"look": "neon"}))
                with self.assertRaises(formats.FormatError):
                    formats.load_all()


class Options(unittest.TestCase):
    def test_options_describe_every_choice(self):
        o = engine.options()
        for key in ("looks", "captions", "voices", "music", "formats", "scenes", "categories", "styles"):
            self.assertIn(key, o)
        self.assertIn("known", o["styles"])
        self.assertIn("swiss-motion", o["styles"]["known"])
        self.assertEqual(set(o["categories"]), set(brand.load("tbilisi-today")["categories"]))
        self.assertEqual(set(o["brands"]), {"tbilisi-today", "sitech"})
        sitech = engine.options("sitech")
        self.assertEqual(sitech["voices"]["sitech"]["brand"], "sitech")  # Charon is offered to SiTech only
        self.assertNotIn("sitech", o["voices"])
        self.assertTrue(all(o["voices"][n]["approved"] for n in voices.APPROVED))
        json.dumps(o, ensure_ascii=False)  # an agent reads it as JSON

    def test_options_section_filtering(self):
        summary = engine.options(section="summary")
        self.assertEqual(summary["section"], "summary")
        self.assertIn("sections", summary)
        self.assertIn("formats", summary)
        self.assertIn("directors", summary)

        fmts = engine.options(section="formats")
        self.assertEqual(fmts["section"], "formats")
        self.assertIn("news", fmts["formats"])
        self.assertEqual(set(fmts.keys()), {"brand", "section", "formats"})

        with self.assertRaises(ValueError) as ctx:
            engine.options(section="nonexistent")
        self.assertIn("unknown section 'nonexistent'", str(ctx.exception))

    def test_check_missing_file_returns_structured_problem(self):
        import io, sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = captured
            code = engine.main(["check", "missing-story-file.json"])
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 1)
        res = json.loads(captured.getvalue())
        self.assertTrue(any("story file not found" in p for p in res["problems"]))

    def test_engine_scene_types_match_the_remotion_scenes(self):
        tsx = (ROOT / "remotion" / "src" / "scenes" / "index.tsx").read_text(encoding="utf-8")
        record = re.search(r"export const SCENES[^{]*\{([^}]*)\}", tsx).group(1)
        drawn = set(re.findall(r'"?([\w-]+)"?:', record))
        self.assertEqual(set(engine.SCENES), drawn)


class Check(unittest.TestCase):
    def test_samples_pass(self):
        for sid in ("24725", "24835"):
            self.assertEqual(engine.check_story(story(sid), FIXTURES[sid]), [], sid)

    def test_structure_problems_are_named(self):
        s = story()
        s["scenes"][1]["type"] = "opinion"
        del s["scenes"][2]["at"]
        s["scenes"][3].pop("place")
        p = engine.check_story(s)
        self.assertTrue(any("unknown type 'opinion'" in x for x in p))
        self.assertTrue(any("missing 'at'" in x for x in p))
        self.assertTrue(any("missing 'place'" in x for x in p))

    def test_first_scene_is_the_hook(self):
        s = story()
        s["scenes"] = s["scenes"][1:]
        self.assertTrue(any("first scene must be a hook" in x for x in engine.check_story(s)))

    def test_news_rules_run_with_sources(self):
        s = story("24835")
        s["narration"] = s["narration"].replace("6400", "7000")
        self.assertTrue(any(x.startswith("N2") for x in engine.check_story(s, FIXTURES["24835"])))


if __name__ == "__main__":
    unittest.main()
