"""Veasy as a Hermes plugin (plugin.yaml + __init__.py): what an agent gets when the plugin is enabled."""
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ("make-video", "write-script", "qa", "formats", "queue", "brands", "package", "programs", "directors", "rubrics",
          "media", "compose")


def load_plugin():
    spec = importlib.util.spec_from_file_location("veasy", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["veasy"] = mod
    spec.loader.exec_module(mod)
    return mod


def manifest_list(key):
    text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    block = re.search(rf"^{key}:\n((?:  - .+\n)+)", text, re.M).group(1)
    return re.findall(r"  - (\S+)", block)


class FakeCtx:
    def __init__(self):
        self.skills, self.tools, self.hooks = {}, {}, {}

    def register_skill(self, name, path, description="", frontmatter=None):
        assert pathlib.Path(path).exists()
        self.skills[name] = pathlib.Path(path)

    def register_tool(self, name, toolset, schema, handler, **kw):
        assert toolset == "veasy" and schema["name"] == name and schema["parameters"]["type"] == "object"
        self.tools[name] = (schema, handler)

    def register_hook(self, name, cb):
        self.hooks[name] = cb


class Plugin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = load_plugin()
        cls.ctx = FakeCtx()
        cls.plugin.register(cls.ctx)

    def test_registers_what_the_manifest_promises(self):
        self.assertEqual(set(self.ctx.tools), set(manifest_list("provides_tools")))
        self.assertEqual(set(self.ctx.hooks), set(manifest_list("provides_hooks")))
        self.assertEqual(set(self.ctx.skills), set(SKILLS))

    def test_skills_are_small_and_link_only_to_real_siblings(self):
        for md in (ROOT / "skills").glob("*/SKILL.md"):
            text = md.read_text(encoding="utf-8")
            self.assertEqual(re.search(r"^name: (\S+)", text, re.M).group(1), md.parent.name)
            self.assertGreater(len(re.search(r"^description: (.+)$", text, re.M).group(1)), 40)
            self.assertLess(len(text), 12000, md)  # a cheap model's context
            for sib in re.findall(r"veasy:([a-z-]+)", text):
                self.assertTrue((ROOT / "skills" / sib / "SKILL.md").exists(), f"{md.parent.name}: unknown veasy:{sib}")

    def test_claude_code_sees_the_same_skills(self):
        for name in SKILLS:
            entry = ROOT / ".claude" / "skills" / name
            if entry.is_file() and not entry.is_symlink():
                # On Windows with core.symlinks=false, git checks out symlinks as text files pointing to target
                target = entry.read_text(encoding="utf-8").strip()
                self.assertEqual(target.replace("\\", "/"), f"../../skills/{name}")
                resolved = (entry.parent / target).resolve()
                self.assertTrue((resolved / "SKILL.md").exists(), f"{name} -> {resolved}")
            else:
                self.assertTrue((ROOT / ".claude" / "skills" / name / "SKILL.md").exists(), name)

    def test_options_tool_returns_the_engine_json(self):
        out = json.loads(self.ctx.tools["veasy_options"][1]({}))
        self.assertIn("news", out["formats"])
        self.assertIn("page", out["captions"])

    def test_options_tool_takes_a_brand(self):
        out = json.loads(self.ctx.tools["veasy_options"][1]({"brand": "sitech"}))
        self.assertEqual(out["brand"], "sitech")
        self.assertIn("security", out["categories"])
        out = json.loads(self.ctx.tools["veasy_options"][1]({"brand": "nobody"}))
        self.assertTrue(out.get("problems") or out.get("error"))

    def test_queue_tool_lists_jobs(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            out = json.loads(self.ctx.tools["veasy_queue"][1]({"action": "add", "story": "stories/24725.json"}))
            self.assertTrue(out["created"], out)
            again = json.loads(self.ctx.tools["veasy_queue"][1]({"action": "add", "story": "stories/24725.json"}))
            self.assertFalse(again["created"])  # the same request is the same job
            out = json.loads(self.ctx.tools["veasy_queue"][1]({"action": "list"}))
            self.assertEqual(out["counts"], {"queued": 1})

    def test_write_and_queue_take_a_program_and_any_source(self):
        from tt_shorts import programs, sources
        for tool in ("veasy_write", "veasy_queue"):
            props = self.ctx.tools[tool][0]["parameters"]["properties"]
            self.assertIn("program", props)
            self.assertEqual(set(props["source"]["enum"]), set(sources.KNOWN))
        self.assertTrue(set(programs.load_all()) >= {"news", "explainer", "law", "blog"})
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            out = json.loads(self.ctx.tools["veasy_queue"][1]({"action": "add", "program": "law",
                                                                "ref": "constitution:17"}))
            self.assertEqual((out["job"]["program"], out["job"]["source"]), ("law", "ordo"), out)
            out = json.loads(self.ctx.tools["veasy_queue"][1]({"action": "add", "program": "law", "source": "url",
                                                                "ref": "https://x.ge/a", "format": "neon"}))
            self.assertTrue(out.get("problems") or out.get("error"))

    def test_check_tool_runs_the_checks(self):
        out = json.loads(self.ctx.tools["veasy_check"][1]({"story": "stories/24835.json",
                                                           "sources": "tests/fixtures/24835.sources.json"}))
        self.assertEqual(out.get("problems"), [], out)

    def test_handlers_never_raise(self):
        out = json.loads(self.ctx.tools["veasy_check"][1]({}))
        self.assertIn("error", out)
        out = json.loads(self.ctx.tools["veasy_qa"][1]({"video": "out/no-such-file.mp4"}))
        self.assertTrue(out.get("problems"))
        out = json.loads(self.ctx.tools["veasy_package"][1]({"render": "out/no-such-render.json"}))
        self.assertTrue(out.get("problems") and "no render manifest" in out["problems"][0], out)
        self.assertIn("error", json.loads(self.ctx.tools["veasy_package"][1]({})))

    def test_hint_once_per_session(self):
        hint = self.ctx.hooks["pre_llm_call"]
        self.assertIn("veasy:make-video", hint(is_first_turn=True)["context"])
        self.assertIsNone(hint(is_first_turn=False))


if __name__ == "__main__":
    unittest.main()
