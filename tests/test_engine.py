"""The engine's contract with agents: formats, options and the story check."""
import json
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tt_shorts import engine, formats, meta, voices

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
        for key in ("looks", "captions", "voices", "music", "formats", "scenes", "categories"):
            self.assertIn(key, o)
        self.assertEqual(set(o["categories"]), set(meta.CATEGORY_KA))
        self.assertTrue(all(o["voices"][n]["approved"] for n in voices.APPROVED))
        json.dumps(o, ensure_ascii=False)  # an agent reads it as JSON

    def test_engine_scene_types_match_the_remotion_scenes(self):
        tsx = (ROOT / "remotion" / "src" / "scenes" / "index.tsx").read_text(encoding="utf-8")
        record = re.search(r"export const SCENES[^{]*\{([^}]*)\}", tsx).group(1)
        drawn = set(re.findall(r"(\w+):", record))
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
