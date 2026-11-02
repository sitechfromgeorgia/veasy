"""The news rules (N1-N5, N10): what an auto-published video must never carry."""
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


def signed(narration, verb="stops", category="society", **extra):
    """A story with a hook and one sign scene that starts at the second sentence."""
    first, second = narration.split(". ", 1)
    return {"category": category, "narration": narration, **extra,
            "scenes": [{"type": "hook", "at": first.split()[0], "lines": ["x"]},
                       {"type": "sign", "at": " ".join(second.split()[:2]), "icon": "გაზი", "verb": verb, "label": "ა"}]}


class Pictograms(unittest.TestCase):  # N10
    def test_the_sign_s_verb_is_said_in_its_part(self):
        ok = signed("2 ნოემბერს გაზი შეწყდება. ვაკეში გაზის მიწოდება 6400 აბონენტს შეუწყდება.")
        self.assertEqual(news_check.pictograms(ok), [])
        p = news_check.pictograms(signed("2 ნოემბერს გაზი შეწყდება. ვაკეში გაზის მიწოდება 6400 აბონენტს აქვს."))
        self.assertEqual(rules(p), ["N10"])  # said only in the hook's part: the sign shows what its own part says
        self.assertIn("„stops“", p[0])
        rises = signed("2 ნოემბერს გაზი შეწყდება. ვაკეში გაზის მიწოდება 6400 აბონენტს შეუწყდება.", verb="rises")
        self.assertEqual(rules(news_check.pictograms(rises)), ["N10"])

    def test_look_alike_words_don_t_count(self):  # გადაწყდება is "will be decided", not "stops"
        p = news_check.pictograms(signed("2 ნოემბერს გაზი შეწყდება. ვაკეში გაზის საკითხი 6400 აბონენტისთვის გადაწყდება."))
        self.assertEqual(rules(p), ["N10"])

    def test_no_pictograms_for_the_crime_family(self):
        for category in ("crime", "incidents"):
            p = news_check.pictograms(signed("2 ნოემბერს გაზი შეწყდება. ვაკეში გაზის მიწოდება შეწყდება.",
                                             category=category))
            self.assertTrue(any("crime family" in x for x in p), category)
        stat = {"category": "crime", "narration": "6400 აბონენტი.",
                "scenes": [{"type": "stat", "at": "6400", "value": 6400, "icon": "users", "label": "ა"}]}
        self.assertEqual(rules(news_check.pictograms(stat)), ["N10"])
        motif = {"category": "crime", "narration": "ა ბ.", "motif": "flame", "scenes": []}
        self.assertEqual(rules(news_check.pictograms(motif)), ["N10"])
        plain = {"category": "crime", "narration": "ა ბ.", "scenes": [{"type": "stat", "value": 2, "label": "ა"}]}
        self.assertEqual(news_check.pictograms(plain), [])  # a crime story without icons is fine

    def test_no_pictograms_for_deaths(self):
        p = news_check.pictograms(signed("2 ნოემბერს ხიდი ჩამოინგრა. ხიდის ავარიისას ორი ადამიანი დაიღუპა, ხიდი დაიხურა.",
                                         verb="closes"))
        self.assertTrue(any("deaths (დაიღუპ)" in x for x in p), p)
        self.assertEqual(news_check.deaths("გარდაიცვალა 2 ადამიანი"), ["გარდაიცვალ"])
        self.assertEqual(news_check.deaths("გზა მოკლეა და სწრაფი"), [])  # მოკლე is "short", not "killed"

    def test_an_icon_name_and_a_verb_are_not_screen_text(self):  # they are drawn, never read (N2, N4)
        s = signed("2 ნოემბერს გაზი შეწყდება. ვაკეში გაზის მიწოდება შეწყდება.")
        s["scenes"][1]["icon"] = "x-2"
        self.assertNotIn("x-2", news_check.screen_text(s))
        self.assertNotIn("stops", news_check.screen_text(s))

    def test_problems_include_n10(self):
        s = signed("2 ნოემბერს გაზი შეწყდება. ვაკეში გაზის მიწოდება 6400 აბონენტს აქვს.")
        self.assertIn("N10", rules(news_check.problems(s, SRC)))


if __name__ == "__main__":
    unittest.main()
