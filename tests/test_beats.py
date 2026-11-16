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
                read_holds = [h for h in motion_rules.hold_problems(p) if h.startswith("motion read:")]
                self.assertEqual(read_holds, [], f.name)

    def test_the_shipped_stories_have_no_still_scene(self):  # the goal of phase 3's beats
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            for name in ("24835", "24725", "law-constitution-17", "veasy-scenes"):
                _, p = props.build(str(ROOT / "stories" / f"{name}.json"), "auto", "silent", music="off")
                still = [w for w in motion_rules.check(p)["warnings"] if w.startswith("motion still")]
                self.assertEqual(still, [], name)

    def test_ten_remaining_brushes_produce_valid_beat_tracks(self):
        cases = [
            ({"type": "bars", "from": 0, "duration": 8 * FPS,
              "items": [{"label": "თბილისი", "value": 10}, {"label": "ბათუმი", "value": 20}, {"label": "ქუთაისი", "value": 15}]},
             "სვეტები ადარებს მონაცემებს: თბილისი პირველია, ბათუმი მეორეა და ქუთაისი მესამეა დეტალურად",
             ["items.1", "items.2"], None),
            ({"type": "trend", "from": 0, "duration": 8 * FPS, "label": "მნიშვნელოვანი ზრდა",
              "items": [{"label": "დილა", "value": 10}, {"label": "საღამო", "value": 20}]},
             "ტრენდის ხაზი აჩვენებს დინამიკას დროში, მნიშვნელოვანი ზრდა ფიქსირდება ბოლოს",
             ["label"], "line"),
            ({"type": "change", "from": 0, "duration": 8 * FPS,
              "before": {"label": "ძველი", "value": 10}, "after": {"label": "ახალი", "value": 25}},
             "ცვლილების სცენა ადარებს ძველსა და ახალ მაჩვენებელს, მაჩვენებელი საგრძნობლად გაიზარდა",
             [], "roll"),
            ({"type": "share", "from": 0, "duration": 8 * FPS, "value": 75, "label": "მოსახლეობის წილი"},
             "წილის სცენა აჩვენებს პროცენტს, მოსახლეობის წილი შეადგენს სამოცდათხუთმეტ პროცენტს",
             ["label"], "cells"),
            ({"type": "rail", "from": 0, "duration": 8 * FPS,
              "items": [{"when": "10:00", "label": "გახსნა"}, {"when": "14:00", "label": "შეხვედრა"}, {"when": "18:00", "label": "დახურვა"}]},
             "განრიგი ასეთია: გახსნა დილით, შემდეგ შეხვედრა შუადღეს და დახურვა საღამოს",
             ["items.1", "items.2"], None),
            ({"type": "compare", "from": 0, "duration": 8 * FPS,
              "items": [{"label": "ექსპორტი", "value": 40}, {"label": "იმპორტი", "value": 60}]},
             "შედარება აჩვენებს სხვაობას: ექსპორტი ნაკლებია, ხოლო იმპორტი აღემატება მნიშვნელოვნად",
             ["items.1"], None),
            ({"type": "ranking", "from": 0, "duration": 8 * FPS,
              "items": [{"label": "ქართული", "value": 90}, {"label": "ინგლისური", "value": 70}, {"label": "გერმანული", "value": 50}]},
             "რეიტინგი ასეთია: პირველი ქართული ენაა, მეორე ინგლისური და მესამე გერმანული სიაში",
             ["items.1", "items.2"], None),
            ({"type": "route", "from": 0, "duration": 8 * FPS,
              "stops": ["თბილისი", "ბათუმი", "ტრაპიზონი"]},
             "მარშრუტი იწყება თბილისიდან, შემდეგ ბათუმი და საბოლოო გაჩერება ტრაპიზონი იქნება",
             ["stops.1", "stops.2"], "route"),
            ({"type": "budget", "from": 0, "duration": 8 * FPS,
              "items": [{"label": "განათლება", "value": 100}, {"label": "ჯანდაცვა", "value": 80}, {"label": "ინფრასტრუქტურა", "value": 60}]},
             "ბიუჯეტი ნაწილდება შემდეგნაირად: განათლება მთავარია, ჯანდაცვა მეორე და ინფრასტრუქტურა მესამე",
             ["items.1", "items.2"], "bar"),
            ({"type": "chart", "from": 0, "duration": 8 * FPS,
              "items": [{"label": "იანვარი", "value": 10}, {"label": "თებერვალი", "value": 20}, {"label": "მარტი", "value": 30}]},
             "დიაგრამა ასახავს ზრდას: იანვარი იწყება, თებერვალი იზრდება და მარტი პიკს აღწევს",
             ["items.1", "items.2"], None),
        ]
        for scene, narration, expected_reveals, expected_steps in cases:
            ws = words(narration, step=0.35)
            t = beats.track(scene, ws, 0, scene["duration"])
            self.assertIsNotNone(t, f"beats.track was None for {scene['type']}")
            fr = t["frames"]
            self.assertEqual(fr, sorted(set(fr)), f"Frames not sorted/unique for {scene['type']}")
            settled = beats.probe_settled(scene["duration"])
            self.assertLessEqual(fr[-1], settled - beats.SETTLE, f"Last beat exceeds settle for {scene['type']}")
            for rev in expected_reveals:
                self.assertIn(rev, t["reveal"], f"Expected reveal {rev} missing in {scene['type']}")
            if expected_steps:
                self.assertTrue(len(t["steps"]) > 0, f"Expected steps for {scene['type']}")

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
