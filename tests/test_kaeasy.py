"""kaeasy as the engine's Georgian gate: loading from KAEASY_DIR, which findings block, the writer's free brief and
the learning loop. A fake plugin keeps these tests independent of the server; KAEASY_TEST_DIR (a real clone) adds
an end-to-end check."""
import json
import os
import pathlib
import tempfile
import textwrap
import unittest
from unittest import mock

from tt_shorts import ka_check, kaeasy

ROOT = pathlib.Path(__file__).resolve().parent.parent

FAKE_LINT = textwrap.dedent('''
    from dataclasses import asdict, dataclass
    STRICT = {"dash"}
    CALLS = []

    @dataclass
    class Finding:
        check: str
        severity: str
        message: str
        snippet: str
        start: int = 0
        end: int = 0
        def as_dict(self):
            return asdict(self)

    def check_text(text, mode="article", title=None, strict=False):
        CALLS.append(mode)
        out = []
        if "—" in text:
            out.append(Finding("dash", "error", "no dashes", text[:20]))
        if "ძალიან ძალიან" in text:
            out.append(Finding("dup_word", "warn", "repeated word", "ძალიან ძალიან"))
        if "Microsoftმა" in text:
            out.append(Finding("ending_hyphen", "error", "Microsoft-მა", "Microsoftმა"))
        return out
''')
FAKE_MEMORY = textwrap.dedent('''
    ROWS = []
    def learn(wrong, right, reason="", category="other", agent=""):
        ROWS.append({"wrong": wrong, "right": right, "category": category, "agent": agent})
        return ROWS[-1]
    def top(limit=20, category=None):
        return [{"wrong": "გააკეთა გადაწყვეტილება", "right": "მიიღო გადაწყვეტილება", "category": "calque", "count": 3}]
    def as_markdown(rows):
        return "\\n".join(f"- ❌ {r['wrong']} → ✅ {r['right']}" for r in rows)
''')
SKILL = "# Georgian writing\n\n## The ten rules broken most often\n\n1. Rule one.\n2. Rule two.\n\n## Language\n\nx\n"


def story():
    return json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))


class FakeKaeasy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.tmp.name)
        (d / "lint.py").write_text(FAKE_LINT, encoding="utf-8")
        (d / "memory.py").write_text(FAKE_MEMORY, encoding="utf-8")
        (d / "plugin.yaml").write_text("name: kaeasy\nversion: 9.9.9\n", encoding="utf-8")
        (d / "skills" / "georgian-writing").mkdir(parents=True)
        (d / "skills" / "georgian-writing" / "SKILL.md").write_text(SKILL, encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {"KAEASY_DIR": str(d), "SHORTS_KAEASY_LEARN": "1"})
        self.env.start()
        kaeasy.reset()

    def tearDown(self):
        self.env.stop()
        kaeasy.reset()
        self.tmp.cleanup()

    def test_loads_and_reports_its_version(self):
        self.assertTrue(kaeasy.available())
        self.assertEqual(kaeasy.version(), "9.9.9")

    def test_each_text_is_checked_in_its_own_mode(self):
        ka_check.problems(story(), {"title": "", "description": "", "text": ""})
        calls = kaeasy._load("lint").CALLS
        self.assertIn("article", calls)  # the narration
        self.assertIn("social", calls)   # the on-screen text
        self.assertIn("speech", calls)   # what the voice reads

    def test_strict_and_mapped_rules_block_the_rest_warn(self):
        s = story()
        s["narration"] = s["narration"].replace("დროებით შეუწყდება.", "დროებით — ძალიან ძალიან შეუწყდება.")
        s["scenes"][0]["kicker"] = "Microsoftმა"
        p = ka_check.problems(s, {"title": "", "description": "", "text": ""})
        self.assertTrue(any(x.startswith("KE: narration") for x in p))  # kaeasy strict, no K number
        self.assertTrue(any(x.startswith("K16: scene 0") for x in p))   # mapped to the rulebook
        self.assertFalse(any("dup_word" in x or "repeated word" in x for x in p))
        self.assertTrue(any("dup_word" in w for w in ka_check.warnings(s)))

    def test_new_scene_fields_are_checked(self):
        s = story()
        s["scenes"][3]["place"] = "Microsoftმა"
        self.assertTrue(any("place" in x for x in ka_check.problems(s, {"title": "", "description": "", "text": ""})))

    def test_writer_brief_is_free_and_includes_the_fleet_mistakes(self):
        brief = kaeasy.prompt_block()
        self.assertIn("1. Rule one.", brief)
        self.assertIn("მიიღო გადაწყვეტილება", brief)
        self.assertNotIn("## Language", brief)

    def test_editor_fixes_are_learned_as_short_phrases(self):
        before = "კომპანიამ გააკეთა გადაწყვეტილება და სამი ახალი სერვისი გამოუშვა დღეს."
        after = "კომპანიამ მიიღო გადაწყვეტილება და სამი ახალი სერვისი გამოუშვა დღეს."
        saved = kaeasy.learn_edit(before, after)
        self.assertEqual([(r["wrong"], r["right"], r["agent"]) for r in saved], [("გააკეთა", "მიიღო", "tt-shorts")])

    def test_learning_can_be_switched_off(self):
        with mock.patch.dict(os.environ, {"SHORTS_KAEASY_LEARN": "0"}):
            self.assertEqual(kaeasy.learn_edit("ერთი ორი", "ერთი სამი"), [])


class Missing(unittest.TestCase):
    def test_nothing_breaks_without_kaeasy(self):
        with mock.patch.dict(os.environ, {"KAEASY_DIR": "/nonexistent/kaeasy", "SHORTS_KA_LINT": "/nonexistent"}):
            kaeasy.reset()
            self.assertFalse(kaeasy.available())
            self.assertIsNone(kaeasy.version())
            self.assertEqual(kaeasy.prompt_block(), "")
            self.assertEqual(ka_check.warnings(story()), [])
            ka_check.problems(story(), {"title": "", "description": "", "text": ""})
        kaeasy.reset()

    def test_an_unreadable_plugin_folder_counts_as_missing(self):  # GitHub runners can't stat /root/...
        with mock.patch.object(pathlib.Path, "is_file", side_effect=PermissionError(13, "Permission denied")):
            kaeasy.reset()
            self.assertFalse(kaeasy.available())
            ka_check.problems(story(), {"title": "", "description": "", "text": ""})
        kaeasy.reset()

    def test_long_rewrites_are_not_lessons(self):
        a = "ერთი ორი სამი ოთხი ხუთი ექვსი შვიდი"
        b = "რვა ცხრა ათი თერთმეტი თორმეტი ცამეტი თოთხმეტი"
        self.assertEqual(kaeasy.changed_phrases(a, b), [])


@unittest.skipUnless(os.environ.get("KAEASY_TEST_DIR"), "set KAEASY_TEST_DIR to a kaeasy clone for the end-to-end check")
class RealKaeasy(unittest.TestCase):
    def test_samples_pass_the_real_gate(self):
        with mock.patch.dict(os.environ, {"KAEASY_DIR": os.environ["KAEASY_TEST_DIR"]}):
            kaeasy.reset()
            self.assertTrue(kaeasy.available())
            fx = json.loads((ROOT / "tests" / "fixtures" / "sources.json").read_text(encoding="utf-8"))
            for sid in ("24725", "24835"):
                s = json.loads((ROOT / "stories" / f"{sid}.json").read_text(encoding="utf-8"))
                self.assertEqual(ka_check.problems(s, {"title": "", "description": "", "text": " ".join(fx[sid])}), [], sid)
        kaeasy.reset()


if __name__ == "__main__":
    unittest.main()
