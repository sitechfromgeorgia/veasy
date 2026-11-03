"""The drawing library (tt_shorts/drawings.py): the seeds, what is kept, and how a failing drawing is mended."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import art, drawings, icons, news_check, writer

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "24835.sources.json").read_text(encoding="utf-8"))


def gas_story(svg="<image/>"):
    """24835 with a draw scene in place of its stat."""
    s = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))
    s["scenes"][1] = {"type": "draw", "at": s["scenes"][1]["at"], "kicker": "რა ხდება",
                      "headline": "გაზის მიწოდება შეწყდება", "svg": svg}
    return s


class Seeds(unittest.TestCase):
    def test_every_seed_passes_and_names_a_known_motif(self):
        seeds = drawings.seeds()
        self.assertGreaterEqual(len(seeds), 40)
        self.assertLessEqual(len(seeds), 60)
        for s in seeds:
            self.assertEqual(art.scene_problems(s["svg"]), [], s["name"])
            self.assertEqual(icons.resolve(s["motif"]), s["motif"], s["name"])
            self.assertTrue(s["about"], s["name"])
        self.assertEqual(len({s["id"] for s in seeds}), len(seeds))

    def test_seeds_cover_the_everyday_motifs(self):
        motifs = {s["motif"] for s in drawings.seeds()}
        self.assertTrue({"flame", "bus", "school", "hospital", "scale", "bridge", "zap", "droplet", "house", "car",
                         "vote", "smartphone", "banknote", "factory"} <= motifs, motifs)

    def test_seed_labels_are_few_and_georgian(self):
        for s in drawings.seeds():
            labels = art.labels(s["svg"])
            self.assertLessEqual(len(labels), 1, s["name"])
            for label in labels:
                self.assertRegex(label, r"^[ა-ჰ ]+$", s["name"])


class Library(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.home.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.home.cleanup()

    def test_the_motif_is_an_icon_name(self):
        self.assertEqual(drawings.motif_of(gas_story()), "flame")
        self.assertEqual(drawings.motif_of({**gas_story(), "motif": "ავტობუსი"}), "bus")
        self.assertIsNone(drawings.motif_of({"scenes": [{"type": "draw", "headline": "ის"}]}))

    def test_a_done_video_keeps_its_drawing(self):
        bus = next(s for s in drawings.seeds() if s["name"] == "bus")
        story = {**gas_story(bus["svg"]), "motif": "bus", "id": 7}
        self.assertEqual(drawings.keep(story, "tbilisi-today"), [bus["id"]])
        self.assertEqual(drawings.keep(story, "tbilisi-today"), [bus["id"]])  # once
        got = drawings.candidates("bus")
        self.assertEqual([c["source"] for c in got], ["done"])  # the seed with the same svg is that one
        self.assertEqual(drawings.keep(gas_story(), "tbilisi-today"), [])  # a failing drawing is not kept
        self.assertEqual(drawings.candidates(None), [])

    def test_a_failing_drawing_gets_a_library_one_of_its_motif(self):
        story, swapped = drawings.mend(gas_story())
        self.assertEqual(len(swapped), 1)
        self.assertEqual((swapped[0]["motif"], swapped[0]["source"]), ("flame", "seed"))
        self.assertEqual(art.scene_problems(story["scenes"][1]["svg"]), [])
        self.assertEqual(story["scenes"][1]["headline"], "გაზის მიწოდება შეწყდება")  # only the drawing changes
        self.assertEqual(drawings.mend(story)[1], [])  # a passing drawing is left alone

    def test_labels_the_new_story_does_not_say_are_removed(self):
        svg = next(s for s in drawings.seeds() if s["name"] == "gas-pipe")["svg"]
        self.assertEqual(art.labels(svg), ["გაზი"])
        kept, removed = drawings.fit(svg, gas_story())  # 24835 says „გაზი“
        self.assertEqual((art.labels(kept), removed), (["გაზი"], []))
        other = {**gas_story(), "narration": "ვაკეში ბუნებრივი აირის მიწოდება შეწყდება 3 ნოემბერს.",
                 "scenes": [{"type": "hook", "at": "ვაკეში", "lines": ["ვაკე"]}]}
        kept, removed = drawings.fit(svg, other)
        self.assertEqual((art.labels(kept), removed), ([], ["გაზი"]))
        self.assertEqual(art.scene_problems(kept), [])

    def test_a_label_with_another_storys_number_never_comes_along(self):
        svg = next(s for s in drawings.seeds() if s["name"] == "bus")["svg"]
        svg += '<text class="r" style="--d:1.8s" x="476" y="600" font-size="36" fill="INK">500 ავტობუსი</text>'
        story = {**gas_story(svg + "<image/>"), "motif": "bus"}
        self.assertEqual(art.labels(drawings.fit(svg, story)[0]), [])
        with mock.patch.object(drawings, "seeds", return_value=[{"id": "x", "name": "bus-500", "motif": "bus",
                                                                 "svg": svg, "source": "seed"}]):
            mended, _ = drawings.mend(story)
        self.assertNotIn("500", news_check.screen_text(mended))

    def test_without_a_fitting_drawing_the_scene_is_dropped_as_before(self):
        story = {**gas_story(), "motif": None, "scenes": gas_story()["scenes"]}
        story["scenes"][1]["headline"] = "ის"
        story["scenes"][0]["lines"] = ["ის"]
        mended, swapped = drawings.mend(story)
        self.assertEqual(swapped, [])
        self.assertEqual(art.drop_bad(mended)[1], 1)

    def test_the_writer_mends_before_it_drops(self):
        answer = {k: v for k, v in gas_story().items() if k not in ("id", "date", "sources")}
        with mock.patch.object(writer, "_call", return_value=json.dumps(answer, ensure_ascii=False)), \
                mock.patch.object(writer, "_edit", return_value=None), \
                mock.patch.object(writer, "_anchors_ok", return_value=True):
            story = writer.write({"id": 24835, "category": "society"}, FIXTURE, repairs=0,
                                 run_checks=lambda s, a, c: art.story_problems(s))
        self.assertEqual([s["type"] for s in story["scenes"]][1], "draw")
        self.assertEqual(art.scene_problems(story["scenes"][1]["svg"]), [])

    def test_the_queue_keeps_a_done_jobs_drawing(self):
        from tt_shorts import queue
        bus = next(s for s in drawings.seeds() if s["name"] == "bus")
        path = pathlib.Path(self.home.name) / "s.json"
        path.write_text(json.dumps({**gas_story(bus["svg"]), "motif": "bus"}, ensure_ascii=False), encoding="utf-8")
        queue._keep_drawings(path, "tbilisi-today")
        self.assertEqual(drawings.candidates("bus")[0]["source"], "done")
        queue._keep_drawings(pathlib.Path(self.home.name) / "missing.json", "tbilisi-today")  # never raises


if __name__ == "__main__":
    unittest.main()
