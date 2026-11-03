"""Lane B spike (tools/compose_scaffold.py, tools/compose_probe.py): the pure parts, without a browser."""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import compose_probe  # noqa: E402
import compose_scaffold  # noqa: E402


class Scaffold(unittest.TestCase):
    def test_map_box_keeps_the_scene_aspect_and_holds_the_box(self):
        x, y, w, h = compose_scaffold.map_box([6937, 3688, 7398, 4013])
        self.assertAlmostEqual(w / h, compose_scaffold.MAP_W / compose_scaffold.MAP_H, places=2)
        self.assertTrue(x <= 6937 and y <= 3688 and x + w >= 7398 and y + h >= 4013)

    def test_beats_resolve_in_order_and_may_share_words(self):
        words = [{"text": t, "start": i * 0.5, "end": i * 0.5 + 0.4}
                 for i, t in enumerate("გაზი შეწყდება . გაზი არ იქნება".split())]
        out = compose_scaffold.resolve([{"id": "a", "at": "გაზი შეწყდება"}, {"id": "b", "at": "შეწყდება"},
                                        {"id": "c", "at": "გაზი არ"}], words)
        self.assertEqual([b["t"] for b in out], [0.0, 0.5, 1.5])

    def test_the_shipped_film_has_a_beat_at_least_every_3s(self):
        sheet = json.loads((ROOT / "compose" / "24835" / "beats.json").read_text(encoding="utf-8"))
        story = json.loads((ROOT / sheet["story"]).read_text(encoding="utf-8"))
        words = compose_scaffold.speech.estimate_words(story["narration"])  # the silent engine's timing
        beats = compose_scaffold.resolve(sheet["beats"], words)
        gaps = [b["t"] - a["t"] for a, b in zip(beats, beats[1:])]
        self.assertLessEqual(max(gaps), 3.0)
        self.assertGreater(min(gaps), 0)

    def test_the_composition_types_no_pack(self):  # every color, logo and link comes from the pack at build time
        src = ROOT / "compose" / "24835"
        for f in [src / "index.html", *(src / "compositions").glob("*.html")]:
            text = f.read_text(encoding="utf-8").lower()
            for word in ("#", "tbilisi.today", "sitech", "rgba("):
                if word == "#":
                    self.assertNotRegex(text, r"#[0-9a-f]{6}\b", f.name)
                else:
                    self.assertNotIn(word, text, f.name)


class Probe(unittest.TestCase):
    def test_settled_times_sit_inside_each_beat(self):
        t = {"duration": 10.0, "beats": [{"id": "a", "t": 0.0}, {"id": "b", "t": 0.5}, {"id": "c", "t": 4.0}]}
        self.assertEqual(compose_probe.settled(t), [("a", 0.45), ("b", 1.2), ("c", 4.7)])

    def test_accent_text_is_caught_but_not_the_wordmark_dot(self):
        rep = {"texts": [{"text": "ოთხი", "color": "rgb(239, 68, 68)", "region": "scene"},
                         {"text": ".", "color": "rgb(239, 68, 68)", "region": "scene"},
                         {"text": "ოთხი", "color": "rgb(248, 250, 252)", "region": "scene"}]}
        found = compose_probe.accent_text(rep, "#EF4444")
        self.assertEqual([f["text"] for f in found], ["ოთხი"])


if __name__ == "__main__":
    unittest.main()
