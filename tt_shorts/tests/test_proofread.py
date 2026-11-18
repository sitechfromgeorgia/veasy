"""The deepseek proofread gate: it must catch a coined word and stay silent on clean Georgian.

The owner caught "80 წლის მოქცევარი" in a published reel on 2026-11-18. "მოქცევარი" is not a Georgian
word (მოქცევა is behaviour; a man is მამაკაცი or მოხუცი), and no rule had an opinion about it, because
every rule checks a pattern and nobody read the sentence.

The tests below are about the gate's shape, not about the model: the parse, the span check and the
switch. The model's own answers are checked live in the run that follows, because a unit test that
calls a remote model is a flaky test.
"""

import unittest

from tt_shorts import proofread


class ParseTest(unittest.TestCase):
    def test_reads_a_json_array(self):
        answer = '{"findings": [{"span": "მოქცევარი", "problem": "არ არსებობს", "fix": "მოხუცი"}]}'
        found = proofread._parse(answer)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["span"], "მოქცევარი")
        self.assertEqual(found[0]["fix"], "მოხუცი")

    def test_reads_an_empty_answer(self):
        self.assertEqual(proofread._parse('{"findings": []}'), [])

    def test_a_prose_answer_is_not_a_finding(self):
        self.assertEqual(proofread._parse("ტექსტი სუფთაა, შეცდომა არ არის."), [])

    def test_a_one_character_span_is_ignored(self):
        answer = '{"findings": [{"span": "ა", "problem": "x", "fix": "y"}]}'
        self.assertEqual(proofread._parse(answer), [])

    def test_broken_json_is_ignored(self):
        self.assertEqual(proofread._parse('{"findings": [{"span": '), [])


class SpanTest(unittest.TestCase):
    def test_text_of_takes_the_narration_and_the_shown_fields(self):
        story = {"narration": "ერთი წინადადება აქ არის.",
                 "scenes": [{"type": "stat", "label": "იარლიყი", "at": "ერთი"},
                            {"type": "points", "items": ["პირველი", "მეორე"]}]}
        text = proofread._text_of(story)
        self.assertIn("იარლიყი", text)
        self.assertIn("პირველი", text)

    def test_a_text_too_short_to_read_yields_nothing(self):
        """A three-word story is not worth a model call, and the gate must not spend one."""
        self.assertEqual(proofread.findings({"narration": "ორი სიტყვა.", "scenes": []}), [])


class SwitchTest(unittest.TestCase):
    def test_on_by_default(self):
        self.assertTrue(proofread.on())

    def test_off_when_asked(self):
        import os
        os.environ["TT_PROOFREAD"] = "0"
        try:
            self.assertFalse(proofread.on())
        finally:
            os.environ.pop("TT_PROOFREAD", None)


if __name__ == "__main__":
    unittest.main()
