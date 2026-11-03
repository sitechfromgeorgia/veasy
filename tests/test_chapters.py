"""Chapters (tt_shorts/chapters.py): "01 / 03" from the scene list, by code; the format key chapters."""
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import chapters, formats, props

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = chapters.FPS


def scenes(types, secs=5):
    out, t = [], 0
    for typ in types:
        out.append({"type": typ, "from": t, "duration": secs * FPS})
        t += secs * FPS
    return out, t


class Split(unittest.TestCase):
    def test_off_by_default_and_auto_from_40_seconds(self):
        sc, total = scenes(["hook", "stat", "where", "who", "points", "quote", "end"], 5)  # 35 s
        self.assertIsNone(chapters.split(sc, total))
        self.assertIsNone(chapters.split(sc, total, "auto"))
        self.assertEqual(len(chapters.split(sc, total, "on")), 2)
        sc, total = scenes(["hook", "stat", "where", "who", "points", "quote", "end"], 6)  # 42 s
        self.assertEqual(len(chapters.split(sc, total, "auto")), 2)

    def test_the_hook_opens_chapter_one_and_each_chapter_has_three_scenes(self):
        for n in range(6, 13):
            sc, total = scenes(["hook"] + ["stat"] * (n - 2) + ["end"])
            ch = chapters.split(sc, total, "on")
            self.assertEqual(ch[0]["from"], 0)
            self.assertEqual(ch[-1]["to"], total)
            self.assertLessEqual(len(ch), chapters.MAX_CHAPTERS)
            for c in ch:
                inside = [s for s in sc if c["from"] <= s["from"] < c["to"]]
                self.assertGreaterEqual(len(inside), chapters.MIN_SCENES, (n, ch))
            for a, b in zip(ch, ch[1:]):
                self.assertEqual(a["to"], b["from"])  # no gap, no overlap

    def test_too_few_scenes_make_no_chapters(self):
        sc, total = scenes(["hook", "stat", "where", "sources", "end"], 9)
        self.assertIsNone(chapters.split(sc, total, "on"))

    def test_the_most_even_split(self):
        sc, t = [], 0
        for secs in (3, 3, 3, 3, 3, 3, 20):  # a long last scene: the first chapter takes four scenes, not three
            sc.append({"type": "stat", "from": t, "duration": secs * FPS})
            t += secs * FPS
        ch = chapters.split(sc, t, "on")
        self.assertEqual(ch[1]["from"], sc[4]["from"])

    def test_a_digest_chapters_at_its_chapter_cards(self):
        sc, total = scenes(["hook", "stat", "chapter", "who", "chapter", "quote", "end"])
        ch = chapters.split(sc, total, "on")
        self.assertEqual([c["from"] for c in ch], [0, sc[2]["from"], sc[4]["from"]])  # stories, not threes

    def test_the_format_key(self):
        self.assertEqual(formats.get("news")["chapters"], "off")
        self.assertEqual(formats.get("news", chapters="auto")["chapters"], "auto")
        with self.assertRaises(formats.FormatError):
            formats.get("news", chapters="sometimes")

    def test_props_carry_them(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            _, p = props.build(str(ROOT / "stories" / "24835.json"), "cards", "silent", music="off", chapters="on")
            _, q = props.build(str(ROOT / "stories" / "24835.json"), "cards", "silent", music="off")
        self.assertEqual(len(p["chapters"]), 2)
        self.assertIsNone(q["chapters"])


if __name__ == "__main__":
    unittest.main()
