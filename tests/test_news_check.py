"""The news rules (N1-N5): what an auto-published video must never carry."""
import unittest

from tt_shorts import news_check

SRC = ["„თბილისი ენერჯის“ ცნობით, 2 ნოემბრის 22:00 სთ-დან გაზის მიწოდება 6400 აბონენტს შეუწყდება. "
       "„მსურს, შევხვდე მას“, – განაცხადა ზელენსკიმ."]


def story(narration, scenes=None):
    return {"narration": narration, "scenes": scenes or [{"type": "hook", "at": narration.split()[0], "lines": ["x"]}]}


def rules(problems):
    return sorted({p.split(":")[0] for p in problems})


class NewsRules(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(news_check.problems(story("6400 აბონენტს 2 ნოემბერს გაზი შეუწყდება."), SRC), [])

    def test_take_scene_and_evaluative_words(self):  # N1
        p = news_check.problems(story("სკანდალური გადაწყვეტილება.", [{"type": "take", "at": "სკანდალური"}]), SRC)
        self.assertEqual(rules(p), ["N1"])
        self.assertEqual(len(p), 2)

    def test_invented_number(self):  # N2: on screen too
        p = news_check.problems(story("გაზი 7000 აბონენტს შეუწყდება.",
                                      [{"type": "stat", "at": "გაზი", "value": 12, "label": "საათი"}]), SRC)
        self.assertEqual(sorted(x.split()[2] for x in p), ["12", "7000"])

    def test_quote_must_be_verbatim(self):  # N3: in the narration and in a quote scene
        ok = news_check.problems(story("ზელენსკი ამბობს: „მსურს, შევხვდე მას“."), SRC)
        self.assertEqual(ok, [])
        p = news_check.problems(story("ზელენსკი ამბობს: „მინდა შევხვდე მას“.",
                                      [{"type": "quote", "at": "ზელენსკი", "text": "მსურს, ვნახო ის"}]), SRC)
        self.assertEqual(rules(p), ["N3"])
        self.assertEqual(len(p), 2)

    def test_relative_days(self):  # N4: whole words only (დღესასწაული is fine)
        self.assertEqual(rules(news_check.problems(story("ხვალ გაზი შეწყდება."), SRC)), ["N4"])
        self.assertEqual(news_check.problems(story("დღესასწაული გადაიდო."), SRC), [])

    def test_sensitive_story_is_skipped(self):  # N5
        p = news_check.problems(story("შსს გამოძიებას იწყებს."), SRC + ["არასრულწლოვანზე ძალადობის ფაქტი"])
        self.assertEqual(rules(p), ["N5"])


if __name__ == "__main__":
    unittest.main()
