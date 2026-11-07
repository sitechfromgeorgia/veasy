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
    def test_every_design_is_sound(self):
        for name, words in sample_words():
            for design in captions.DESIGNS:
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


def timed(text, step=0.4):
    return [{"text": t, "start": round(i * step, 3), "end": round(i * step + 0.3, 3)} for i, t in enumerate(text.split())]


class Reach(unittest.TestCase):
    def test_how_high_the_caption_text_reaches(self):  # what stands on a scene's foot (a vignette) stays above it
        words = timed("ერთი ორი სამი ოთხი ხუთი ექვსი შვიდი რვა ცხრა ათი")
        page, roll = captions.layout(words, "page"), captions.layout(words, "roll")
        self.assertGreaterEqual(captions.reach(page), 1370)  # two lines: about where the scene band ends (1380)
        self.assertEqual(captions.reach(captions.layout(words, "keyword")), captions.reach(page))
        # the roll's three rows: its upper, fading row stands inside the scene band (Captions.tsx RollCaptions)
        row = roll["size"] * roll["lineHeight"] + 10
        self.assertEqual(captions.reach(roll), round(1552 - (3 * row + 24) / 2 - row / 2 - 0.78 * row))
        self.assertLess(captions.reach(roll), 1330)


class Keyword(unittest.TestCase):
    """The keyword design: the page design's lines and pages, plus one keyword a page, picked by code."""

    def test_same_lines_and_pages_as_page(self):  # one size, the same geometry: only the drawing differs
        for name, words in sample_words():
            page, kw = captions.layout(words, "page"), captions.layout(words, "keyword")
            self.assertEqual(page["size"], kw["size"], name)
            self.assertEqual(page["lines"], kw["lines"], name)
            self.assertEqual([p["lines"] for p in page["pages"]], [p["lines"] for p in kw["pages"]], name)
            self.assertNotIn("key", " ".join(map(str, page["pages"])))  # page never carries a keyword

    def test_em_first_then_a_number_then_a_name(self):
        words = timed("ზელენსკი ამბობს რომ 6400 აბონენტს გაზი შეუწყდება.")
        em = [{"kind": "em", "text": "გაზი შეუწყდება", "at": 2.4}]
        name = [{"kind": "name", "text": "ვოლოდიმირ ზელენსკი", "at": None}, {"kind": "name", "text": "ზელენსკი", "at": None}]
        cap = captions.layout(words, "keyword", keys=em + name)
        k = cap["pages"][-1]["key"]  # the page that says the em phrase
        said = [w["text"] for w in cap["lines"][k["line"]]["words"][k["from"]:k["to"] + 1]]
        self.assertEqual((k["kind"], said), ("em", ["გაზი", "შეუწყდება."]))
        k = cap["pages"][0]["key"]  # the page with the number and the name: the number
        self.assertEqual(k["kind"], "number")
        k = captions.layout(timed("ზელენსკი ამბობს რომ შეხვედრა იქნება."), "keyword", keys=name)["pages"][0]["key"]
        self.assertEqual((k["kind"], k["from"], k["to"]), ("name", 0, 0))  # a name said by its surname alone
        place = [{"kind": "name", "text": "ვარკეთილი · ვაზისუბანი", "at": None}]
        k = captions.layout(timed("ვარკეთილსა და ვაზისუბანში გაზი შეწყდება."), "keyword", keys=place)["pages"][0]["key"]
        self.assertEqual((k["kind"], k["from"], k["to"]), ("name", 0, 0))  # a place in another case
        self.assertNotIn("key", captions.layout(timed("გაზი შეწყდება ღამით."), "keyword", keys=place)["pages"][0])

    def test_an_em_phrase_said_elsewhere_is_not_this_pages(self):
        words = timed("გაზი შეწყდება. ორშაბათს კი გაზი შეწყდება ვაკეშიც.", step=0.6)
        key = captions.layout(words, "keyword", keys=[{"kind": "em", "text": "გაზი შეწყდება", "at": 2.4}])
        kinds = [(p.get("key") or {}).get("kind") for p in key["pages"]]
        self.assertNotEqual(kinds[0], "em")  # said at 0 s, the scene marks it at 2.4 s

    def test_at_most_one_keyword_a_page_and_always_inside_a_line(self):
        for name, words in sample_words():
            cap = captions.layout(words, "keyword", keys=[{"kind": "name", "text": "თბილისი", "at": None}])
            self.assertEqual(captions.problems(cap, words), [], name)
            for p in cap["pages"]:
                if "key" in p:
                    self.assertIn(p["key"]["line"], p["lines"])
                    self.assertIn(p["key"]["kind"], captions.KEY_KINDS)

    def test_the_style_is_the_packs(self):
        from tt_shorts import brand
        words = timed("6400 აბონენტს გაზი შეუწყდება.")
        for pack in ("tbilisi-today", "sitech"):
            style = brand.keyword_style(brand.load(pack))
            self.assertEqual(captions.layout(words, "keyword", style=style)["keyword"], style)
        self.assertNotIn("keyword", captions.layout(words, "page"))

    def test_candidates_come_from_the_built_scenes(self):
        scenes = [{"type": "who", "from": 0, "items": [{"name": "ირაკლი კობახიძე", "role": "პრემიერი"}]},
                  {"type": "stat", "from": 90, "value": 6400, "label": "აბონენტი",
                   "mark": {"phrase": "6400", "at": 30, "field": "value"}},
                  {"type": "quote", "from": 200, "text": "...", "by": "ზელენსკი"}]
        c = captions.candidates(scenes, 30)
        self.assertEqual(c[0], {"kind": "em", "text": "6400", "at": 4.0})
        self.assertEqual([x["text"] for x in c if x["kind"] == "name"], ["ირაკლი კობახიძე", "ზელენსკი"])


if __name__ == "__main__":
    unittest.main()
