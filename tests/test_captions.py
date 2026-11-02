"""Caption layout (captions.py): the jitter rules the owner's eye found (2026-11-02: "the captions jump, sometimes
they seem to freeze"). The layout is computed once with the real FiraGO metrics, so these tests see exactly what
the video shows."""
import json
import pathlib
import unittest

from tt_shorts import captions, speech

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORIES = sorted((ROOT / "stories").glob("*.json"))


def sample_words():
    for path in STORIES:
        story = json.loads(path.read_text(encoding="utf-8"))
        yield path.name, speech.estimate_words(story["narration"])


class Layout(unittest.TestCase):
    def test_both_designs_are_sound(self):
        for name, words in sample_words():
            for design in ("page", "roll"):
                cap = captions.layout(words, design, end=words[-1]["end"] + 1.6)
                self.assertEqual(captions.problems(cap, words), [], f"{name} {design}")

    def test_one_size_per_video(self):  # refitting per chunk moved every glyph at every change
        for _, words in sample_words():
            cap = captions.layout(words, "page")
            self.assertGreaterEqual(cap["size"], captions.MIN_SIZE)
            self.assertIsInstance(cap["size"], int)

    def test_pages_stay_up(self):  # the old chunks: 14 of 32 a single word, 6 under 0.5 s
        for name, words in sample_words():
            cap = captions.layout(words, "page")
            starts = [p["start"] for p in cap["pages"]]
            shortest = min(b - a for a, b in zip(starts, starts[1:]))
            self.assertGreaterEqual(shortest, captions.MIN_PAGE - 1e-6, name)
            self.assertLessEqual(len(cap["pages"]), len(words) / 2.5, name)  # pages carry several words

    def test_pages_have_at_most_two_lines_and_lines_fit(self):
        for _, words in sample_words():
            cap = captions.layout(words, "page")
            for p in cap["pages"]:
                self.assertLessEqual(len(p["lines"]), 2)
            for line in cap["lines"]:
                self.assertLessEqual(captions.width(" ".join(w["text"] for w in line["words"]), cap["size"]), captions.MAX_W + 0.5)

    def test_small_gaps_are_bridged(self):  # a caption that blinks off for 0.3 s reads as a stutter
        words = [{"text": t, "start": s, "end": s + 0.4} for t, s in
                 (("ერთი", 0.0), ("ორი.", 0.5), ("სამი", 1.6), ("ოთხი.", 2.1), ("ხუთი", 5.0))]
        cap = captions.layout(words, "page")
        a, b = cap["pages"][0], cap["pages"][1]
        self.assertEqual(a["end"], b["start"])  # 0.7 s of silence: the first page stays until the second
        self.assertLess(cap["pages"][1]["end"], cap["pages"][2]["start"])  # 2.5 s of silence: it fades out

    def test_numbers_and_connectives_do_not_hang(self):
        words = [{"text": t, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, t in
                 enumerate("ვარკეთილსა და ვაზისუბანში 2 ნოემბერს გაზი შეწყდება".split())]
        for line in captions.layout(words, "page")["lines"]:
            self.assertNotIn(line["words"][-1]["text"], captions.HANG | {"2"})

    def test_layout_is_deterministic(self):  # every render tab gets the same props
        for _, words in sample_words():
            self.assertEqual(captions.layout(words, "roll"), captions.layout(words, "roll"))


if __name__ == "__main__":
    unittest.main()
