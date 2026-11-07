"""A number on screen is the fact itself: remotion/src/number.ts, run in node with no browser."""
import json
import pathlib
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = """
import("./remotion/src/number.ts").then(({ counted, decimalsOf, group }) => {
  const cases = [3.8, 12.5, 0.05, 6400, 1250000, 7, 2.75];
  console.log(JSON.stringify({
    end: cases.map((n) => counted(n, 1)),
    shown: cases.map((n) => group(counted(n, 1), decimalsOf(n))),
    start: group(counted(3.8, 0), decimalsOf(3.8)),
    middle: counted(3.8, 0.5),
    steps: counted(6400, 0.5),
  }));
});
"""


class OnScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("no node")
        done = subprocess.run([node, "--experimental-strip-types", "--no-warnings", "-e", SCRIPT], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8")
        if done.returncode:
            raise unittest.SkipTest(f"node can't strip types here: {done.stderr[:200]}")
        cls.got = json.loads(done.stdout)

    def test_a_count_up_ends_on_the_fact_never_on_a_rounded_one(self):
        self.assertEqual(self.got["end"], [3.8, 12.5, 0.05, 6400, 1250000, 7, 2.75])

    def test_georgian_writing_a_space_for_thousands_and_a_comma_for_decimals(self):
        self.assertEqual(self.got["shown"], ["3,8", "12,5", "0,05", "6 400", "1 250 000", "7", "2,75"])

    def test_the_width_stays_while_it_counts(self):
        self.assertEqual(self.got["start"], "0,0")
        self.assertEqual(self.got["middle"], 1.9)

    def test_a_whole_number_counts_in_whole_steps(self):
        self.assertEqual(self.got["steps"], 3200)


if __name__ == "__main__":
    unittest.main()
