"""Failure memory: the failures table, the rules failing lately, the writer's list of recent mistakes."""
import datetime as dt
import json
import os
import pathlib
import sqlite3
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class Rules(unittest.TestCase):
    def test_rule_of_a_problem(self):
        from tt_shorts.failures import rule_of
        cases = {
            "K9: scene 2 (stat) gets only 4 narration words before the next scene, needs 6": "K9",
            "N2: number 7000 is not in any source article": "N2",
            "kaeasy K-ERG (article): narration: wrong case": "kaeasy:K-ERG",
            "draw: svg is not valid XML: x": "draw",
            "timing: about 70s with an estimated voice; aim for 25-45s": "timing",
            "captions: a page lasts 0.4s": "captions",
            "scene 2 (bars): items[0]: needs {label, value} with a number value": "structure",
            "story: the first scene must be a hook": "structure",
            "probe overflow: scene 3 (where) frame 778: „x“ runs past its box": "probe:overflow",
            "probe rail: captions frame 300: „x“ reaches x=982": "probe:rail",
            "length 52.1s is outside the format's 18-45s": "length",
            "loudness -25 LUFS, expected -19..-13": "loudness",
            "something nobody named": "other",
        }
        for text, rule in cases.items():
            self.assertEqual(rule_of(text), rule, text)


class Table(Home):
    def test_record_and_top(self):
        from tt_shorts import failures
        failures.record("tbilisi-today", "write", ["K9: scene 2 ...", "N2: number 7000 ..."])
        failures.record("tbilisi-today", "check", ["K9: scene 4 ..."])
        failures.record("sitech", "qa", ["loudness -25 LUFS"])
        failures.record("sitech", "render", ["TimeoutError: x"], rule="transient")
        top = failures.top("tbilisi-today")
        self.assertEqual([(o["rule"], o["count"]) for o in top], [("K9", 2), ("N2", 1)])
        self.assertEqual(top[0]["stages"], ["write", "check"])
        self.assertEqual(top[0]["example"], "K9: scene 4 ...")  # the latest message
        self.assertEqual({o["rule"] for o in failures.top()}, {"K9", "N2", "loudness", "transient"})
        self.assertEqual(failures.top(stages=("qa",))[0]["rule"], "loudness")
        con = sqlite3.connect(pathlib.Path(self.tmp.name) / "veasy.db")  # the columns the roadmap names
        cols = [r[1] for r in con.execute("pragma table_info(failures)")]
        con.close()
        self.assertEqual(cols, ["ts", "brand", "stage", "rule", "message"])

    def test_old_failures_age_out(self):
        from tt_shorts import failures
        failures.record("tbilisi-today", "write", ["N3: quote is not verbatim"])
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat(timespec="seconds")
        con = sqlite3.connect(pathlib.Path(self.tmp.name) / "veasy.db")
        with con:
            con.execute("update failures set ts=?", (old,))
        con.close()
        self.assertEqual(failures.top("tbilisi-today", days=7), [])
        self.assertEqual(failures.prompt_block("tbilisi-today"), "")

    def test_nothing_to_record(self):
        from tt_shorts import failures
        self.assertEqual(failures.record("x", "qa", []), 0)
        self.assertEqual(failures.record("x", "qa", None), 0)

    def test_prompt_block_lists_only_what_a_writer_can_fix(self):
        from tt_shorts import failures
        self.assertEqual(failures.prompt_block("tbilisi-today"), "")
        failures.record("tbilisi-today", "write", ["K9: scene 2 (stat) gets only 4 words"] * 3)
        failures.record("tbilisi-today", "render", ["probe overflow: scene 0 (hook) frame 80: „x“ runs past its box"])
        failures.record("tbilisi-today", "qa", ["loudness -25 LUFS"] * 5)
        failures.record("tbilisi-today", "render", ["ConnectionError: x"] * 5, rule="transient")
        failures.record("sitech", "write", ["N2: number 7000 is not in any source article"])
        block = failures.prompt_block("tbilisi-today")
        lines = block.splitlines()
        self.assertIn("Mistakes", lines[0])
        self.assertTrue(lines[1].startswith("- K9 (3x): scene 2"))
        self.assertIn("probe:overflow (1x): a text did not fit its box", block)
        for absent in ("loudness", "transient", "N2"):  # not the writer's, or another brand's
            self.assertNotIn(absent, block)


class Writer(Home):
    """The writer reads the brand's recent mistakes and reports every pass that fails a check."""

    def test_the_prompt_carries_the_mistakes(self):
        from tt_shorts import writer
        with mock.patch.object(writer.kaeasy, "prompt_block", return_value=""):
            p = writer._prompt({"headline": "h"}, ["text 7000"], None, "Mistakes the latest scripts made:\n- K9 (3x)")
            self.assertIn("- K9 (3x)", p)
            self.assertNotIn("Mistakes", writer._prompt({"headline": "h"}, ["text"]))

    def test_failed_passes_are_reported_and_the_last_one_raised(self):
        from tt_shorts import writer
        seen = []
        answer = json.dumps({"narration": "ერთი ორი", "scenes": []})
        with mock.patch.object(writer, "_call", return_value=answer), \
                mock.patch.object(writer, "_checks", return_value=["K9: scene 1 (stat) gets only 2 words"]), \
                mock.patch.object(writer.kaeasy, "prompt_block", return_value=""):
            with self.assertRaises(writer.ChecksFailed) as e:
                writer.write({"headline": "h"}, ["text"], repairs=2, on_problems=seen.append)
        self.assertEqual(len(seen), 2)  # the two passes that went back for a repair
        self.assertEqual(e.exception.problems, ["K9: scene 1 (stat) gets only 2 words"])
        self.assertIsInstance(e.exception, ValueError)  # callers that catch ValueError keep working

    def test_write_story_remembers_the_writers_mistakes(self):
        from tt_shorts import engine, failures, sources, writer
        data = {"cluster": {"id": 1, "headline": "h"}, "articles": ["text"]}
        prompts = []

        def fake_write(cluster, articles, avoid=None, mistakes="", on_problems=None, **_):
            prompts.append(mistakes)
            on_problems(["N2: number 7000 is not in any source article"])
            raise writer.ChecksFailed(["K9: scene 1 (stat) gets only 2 words"])
        failures.record("tbilisi-today", "write", ["K13: every scene \"at\" must be the exact first words"])
        with mock.patch.object(sources, "fetch", return_value=data), mock.patch.object(writer, "write", fake_write):
            with self.assertRaises(writer.ChecksFailed):
                engine.write_story("tbilisi-today", 1)
        self.assertIn("K13", prompts[0])  # the writer was told what went wrong before
        self.assertEqual({o["rule"] for o in failures.top("tbilisi-today")}, {"K13", "N2", "K9"})

    def test_the_queue_remembers_check_failures(self):
        from tt_shorts import engine, failures, queue
        job, _ = queue.add(story=str(ROOT / "stories" / "24725.json"))
        with mock.patch.object(engine, "check_story", return_value=["N3: quote is not verbatim in any source"]):
            queue.run(max_jobs=1)
        self.assertEqual(queue.get(job["id"])["state"], "failed")
        self.assertEqual([(o["rule"], o["stages"]) for o in failures.top()], [("N3", ["check"])])

    def test_the_queue_remembers_an_exception_by_its_class(self):
        from tt_shorts import engine, failures, queue
        job, _ = queue.add(story=str(ROOT / "stories" / "24725.json"))
        with mock.patch.object(engine, "check_story", return_value=[]), \
                mock.patch.object(engine, "render_story", side_effect=RuntimeError("layout QA failed: scene 2")):
            queue.run(max_jobs=1)
        self.assertEqual([(o["rule"], o["stages"]) for o in failures.top()], [("layout", ["render"])])


if __name__ == "__main__":
    unittest.main()
