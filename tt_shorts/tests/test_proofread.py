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


class CorpusTest(unittest.TestCase):
    """The corpus is the material a daily review reads, so its shape matters more than its size."""

    def setUp(self):
        import tempfile, pathlib, os
        self.tmp = tempfile.mkdtemp()
        os.environ["TT_CORPUS_DIR"] = self.tmp
        import importlib
        from tt_shorts import corpus as c
        importlib.reload(c)
        self.c = c

    def tearDown(self):
        import os, shutil
        os.environ.pop("TT_CORPUS_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)
        import importlib
        from tt_shorts import corpus as c
        importlib.reload(c)

    def test_a_record_is_written_once(self):
        first = self.c.record("reel", "1", "test", "ეს არის საკმარისად გრძელი ქართული ტექსტი.")
        second = self.c.record("reel", "1", "test", "ეს არის საკმარისად გრძელი ქართული ტექსტი.")
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(len(self.c.load()), 1)

    def test_a_short_text_is_not_recorded(self):
        self.assertIsNone(self.c.record("reel", "2", "test", "ორი სიტყვა."))

    def test_a_story_records_narration_and_cards(self):
        story = {"id": 7, "narration": "ეს არის საკმარისად გრძელი ქართული წინადადება აქ.",
                 "scenes": [{"type": "stat", "label": "საკმარისად გრძელი იარლიყი ეკრანზე", "at": "ეს"}]}
        got = self.c.record_story(story, surface="test")
        kinds = {r["kind"] for r in got}
        self.assertEqual(kinds, {"reel", "card"})

    def test_digest_is_plain_text(self):
        self.c.record("reel", "3", "test", "პირველი საკმარისად გრძელი ქართული ტექსტი აქ.")
        d = self.c.digest()
        self.assertIn("პირველი", d)
        self.assertNotIn("{", d)


class SingleWordTest(unittest.TestCase):
    """A phrase is never a coined word. The reader named "შუა დერეფანი" (Middle Corridor) as wrong and
    blocked a legitimate story, so a multi-word span is refused in code, not only in the prompt."""

    def test_a_multi_word_span_is_not_a_finding(self):
        answer = '{"findings": [{"span": "შუა დერეფანი", "problem": "არ არსებობს", "fix": "შუა დირექტორი"}]}'
        self.assertEqual(proofread._parse(answer), [])

    def test_a_single_word_still_passes(self):
        answer = '{"findings": [{"span": "მოქცევარი", "problem": "არ არსებობს", "fix": "მამაკაცი"}]}'
        self.assertEqual(len(proofread._parse(answer)), 1)
