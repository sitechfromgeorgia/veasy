"""Beats inside scenes (tt_shorts/beats.py): a change every 1.5-3 s on the words, ending where the scene ended before
(owner, 2026-11-03: "slow scenes"; docs/plan-v2.md phase 3)."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import beats, motion_rules, probe, props

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = beats.FPS
STORIES = sorted((ROOT / "stories").glob("*.json"))


def words(text, start=0.0, step=0.4):
    return [{"text": w, "start": round(start + i * step, 3), "end": round(start + i * step + 0.3, 3)}
            for i, w in enumerate(text.split())]


class Track(unittest.TestCase):
    def test_a_point_comes_in_when_it_is_said(self):
        narration = ("პირველი ბიუჯეტი იზრდება მნიშვნელოვნად წელს, მეორე საშემოსავლო გადასახადი რჩება, "
                     "მესამე პენსიები ინდექსირდება ყოველწლიურად ახალი წესით")
        ws = words(narration)
        scene = {"type": "points", "from": 0, "duration": 10 * FPS,
                 "items": ["ბიუჯეტი იზრდება", "საშემოსავლო გადასახადი რჩება", "პენსიები ინდექსირდება"]}
        t = beats.track(scene, ws, 0, 10 * FPS)
        said = {w["text"].strip(","): round(w["start"] * FPS) for w in ws}
        self.assertEqual(t["reveal"]["items.1"], said["საშემოსავლო"])
        self.assertEqual(t["reveal"]["items.2"], said["პენსიები"])
        self.assertEqual(t["texts"], [["საშემოსავლო გადასახადი რჩება", said["საშემოსავლო"]],
                                      ["პენსიები ინდექსირდება", said["პენსიები"]]])

    def test_a_long_quote_lights_up_a_phrase_a_beat(self):
        text = "დაუშვებელია ადამიანის დევნა აზრისა და მისი გამოხატვის გამო ნებისმიერ დროს და ნებისმიერ ადგილას"
        ws = words("პირველი პუნქტი ამბობს: " + text, step=0.6)
        scene = {"type": "quote", "from": 0, "duration": 12 * FPS, "text": text, "by": "კონსტიტუცია"}
        t = beats.track(scene, ws, 0, 12 * FPS)
        lit = t["lit"]["text"]
        self.assertEqual(len(lit), len(text.split()))  # one frame per word
        self.assertEqual(lit, sorted(lit))  # in reading order
        self.assertGreaterEqual(len(set(lit)), 3)  # in several beats, not word by word all at once
        self.assertNotIn("by", t["reveal"])  # the speaker is there with the quote from the start

    def test_beats_are_1_5_to_3_seconds_apart_and_end_before_the_settled_frame(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            for f in STORIES:
                _, p = props.build(str(f), "editorial", "silent", music="off")
                for s, settled in zip(p["scenes"], probe.settled(p["scenes"])):
                    b = s.get("beats")
                    if not b:
                        continue
                    fr = b["frames"]
                    self.assertEqual(fr, sorted(set(fr)), f"{f.name} {s['type']}")
                    self.assertLessEqual(fr[-1], settled - s["from"] - beats.SETTLE, f"{f.name} {s['type']}")
                    for a, c in zip(fr, fr[1:]):
                        self.assertLessEqual((c - a) / FPS, beats.MAX_BEAT + 0.6, f"{f.name} {s['type']} {fr}")
                    for field, at in b["lit"].items():
                        self.assertTrue(all(x <= fr[-1] for x in at), field)
                    for key, at in b["reveal"].items():
                        self.assertIn(at, fr, key)

    def test_every_revealed_text_is_still_read(self):  # the read rule holds with the beats' later entrances
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            for f in STORIES:
                _, p = props.build(str(f), "cards", "silent", music="off")
                self.assertEqual(motion_rules.hold_problems(p), [], f.name)

    def test_the_shipped_stories_have_no_still_scene(self):  # the goal of phase 3's beats
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            for name in ("24835", "24725", "law-constitution-17"):
                _, p = props.build(str(ROOT / "stories" / f"{name}.json"), "auto", "silent", music="off")
                still = [w for w in motion_rules.check(p)["warnings"] if w.startswith("motion still")]
                self.assertEqual(still, [], name)

    def test_beats_off_renders_as_before(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            _, p = props.build(str(ROOT / "stories" / "24835.json"), "cards", "silent", music="off", beats="off")
        self.assertFalse(any("beats" in s for s in p["scenes"]))

    def test_a_type_without_devices_gets_none(self):
        self.assertIsNone(beats.track({"type": "end", "from": 0, "duration": 300}, words("ა ბ გ"), 0, 300))
        self.assertIsNone(beats.track({"type": "stat", "from": 0, "duration": 40, "value": 3, "label": "x"},
                                      words("ა ბ გ"), 0, 40))  # too short for a beat

    def test_deterministic(self):
        story = json.loads((ROOT / "stories" / "law-constitution-17.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            a = props.build(str(ROOT / "stories" / "law-constitution-17.json"), "editorial", "silent", music="off")[1]
            b = props.build(str(ROOT / "stories" / "law-constitution-17.json"), "editorial", "silent", music="off")[1]
        self.assertEqual([s.get("beats") for s in a["scenes"]], [s.get("beats") for s in b["scenes"]])
        self.assertEqual(len(a["scenes"]), len(story["scenes"]))


if __name__ == "__main__":
    unittest.main()
