"""skills/direct/references/forms: every device the kit knows is in a form file; the skill links each file."""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORMS = ROOT / "skills" / "direct" / "references" / "forms"


class Forms(unittest.TestCase):
    def test_every_device_is_in_a_form(self):
        devices = json.loads((ROOT / "concepts" / "devices.json").read_text(encoding="utf-8"))["devices"]
        text = " ".join(p.read_text(encoding="utf-8") for p in FORMS.glob("*.md"))
        # forms name devices in backticks; a few devices (reconstruction-3d, period-pastiche, rewatch-detail,
        # phone-recreation...) are not in the kit and may be left out until they are, but never a kit one
        for name, d in devices.items():
            if d["scenes"]:
                self.assertIn(f"`{name}`", text, f"{name} draws with {d['scenes']} but no form names it")

    def test_forms_are_short_and_linked(self):
        skill = (ROOT / "skills" / "direct" / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(skill), 12000)
        files = sorted(FORMS.glob("*.md"))
        self.assertGreaterEqual(len(files), 8)
        for f in files:
            self.assertIn(f"references/forms/{f.name}", skill)
            self.assertLess(len(f.read_text(encoding="utf-8")), 1500, f)
        for link in re.findall(r"\]\((references/forms/[^)]+)\)", skill):
            self.assertTrue((ROOT / "skills" / "direct" / link).exists(), link)


if __name__ == "__main__":
    unittest.main()
