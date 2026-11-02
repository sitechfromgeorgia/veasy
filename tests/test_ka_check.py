"""The mechanical Georgian rules (ka_check.py) on the mistakes sitech-shorts' ka10 batch actually made.
The metric-number test moves here with script.py in phase 1."""
import unittest

from tt_shorts import ka_check
from tt_shorts.normalize_ka import speech

ART = {"title": "Eko აგენტები", "description": "",
       "text": "13 აგენტიდან ექვსმა ისწავლა. „ვაი, რგოლი დავკარგე“, დაწერა მან. Eko-ს აგენტებმა ზოგადად აჯობეს."}


def story(narration, scenes=None, say=None):
    return {"narration": narration, "say": say or {"Eko": "ეკო"},
            "scenes": scenes or [{"type": "hook", "at": narration.split()[0], "kicker": "კვლევა", "headline": "აგენტები"}]}


def rules(problems):
    return sorted({p.split(":")[0] for p in problems})


class Rules(unittest.TestCase):
    def setUp(self):
        ka_check._lint = False  # the Hub linter is tested where it lives; these are our own rules

    def test_clean(self):
        s = story("Eko-ს აგენტებმა ზოგადად აჯობეს სხვა აგენტებს კუნძულზე. გამოიწერე tbilisi.today.")
        self.assertEqual(ka_check.problems(s, ART), [])

    def test_register_punctuation_english(self):
        p = ka_check.problems(story("თქვენ რას ფიქრობთ! tethered ჰაკი — userland წვდომა. გამოიწერე tbilisi.today."), ART)
        self.assertEqual([r for r in rules(p) if r != "KE"], ["K1", "K12", "K19", "K20"])  # KE is the plugin linter, tested where it lives

    def test_invented_quote(self):
        p = ka_check.problems(story("Eko-მ დაწერა: „რგოლი მაცვია“. მერე სხვა რამ ითამაშა. გამოიწერე tbilisi.today."), ART)
        self.assertIn("K14", rules(p))
        ok = ka_check.problems(story("Eko-მ დაწერა: „ვაი, რგოლი დავკარგე“. მერე ითამაშა. გამოიწერე tbilisi.today."), ART)
        self.assertNotIn("K14", rules(ok))

    def test_short_draw_scene(self):
        n = "Eko-ს აგენტებმა ითამაშეს. კუნძული პატარა იყო და ზღვა ახლოს იყო ყველგან. გამოიწერე tbilisi.today."
        scenes = [{"type": "hook", "at": "Eko-ს აგენტებმა"}, {"type": "draw", "at": "კუნძული პატარა"},
                  {"type": "end", "at": "გამოიწერე tbilisi.today"}]
        self.assertEqual([x[:2] for x in ka_check.scene_words(story(n, scenes))], [(0, "hook"), (1, "draw"), (2, "end")])
        p = ka_check.problems(story(n, scenes), ART)
        self.assertTrue(any(x.startswith("K9: scene 0") for x in p), p)  # hook: 2 words
        self.assertFalse(any(x.startswith("K9: scene 1") for x in p), p)  # draw: 9 words

    def test_names_need_say(self):
        p = ka_check.problems(story("Zeabur-მა სერვისი დახურა. გამოიწერე tbilisi.today.", say={}), ART)
        self.assertTrue(any(x.startswith("K20") and "Zeabur" in x for x in p), p)
        p = ka_check.problems(story("Zeabur-მა სერვისი დახურა. გამოიწერე tbilisi.today.", say={"Zeabur": "Zibur"}), ART)
        self.assertTrue(any(x.startswith("K20") and "Georgian letters" in x for x in p), p)

    def test_letters_and_ids(self):  # the UEFI script: "TPM": "ტე-პე-ემ", and a CVE number read aloud
        p = ka_check.problems(story("TPM-მა და Zeabur-მა იმუშავეს. გამოიწერე tbilisi.today.",
                                    say={"TPM": "ტე-პე-ემ", "Zeabur": "ზიბური"}), ART)
        self.assertTrue(any(x.startswith("K20") and "Russian" in x and "TPM" in x for x in p), p)
        ok = ka_check.problems(story("TPM-მა და Zeabur-მა იმუშავეს. გამოიწერე tbilisi.today.",
                                     say={"TPM": "ტი პი ემ", "Zeabur": "ზიბური", "PXE": "პიქსი"}), ART)
        self.assertFalse(any("Russian" in x for x in ok), ok)
        p = ka_check.problems(story("ხარვეზი CVE-2026-97631 ყველა სერვერს ეხება. გამოიწერე tbilisi.today."), ART)
        self.assertTrue(any(x.startswith("K15") and "CVE-2026-97631" in x for x in p), p)
        ok = ka_check.problems(story("RTX5090 და Storm-0940 სერვერს ეხება. გამოიწერე tbilisi.today.",
                                     say={"Storm-0940": "სტორმ ნოლ ცხრაას ორმოცი"}), ART)
        self.assertNotIn("K15", rules(ok))

    def test_edit_keeps_qualifiers(self):  # the UEFI edit dropped "მკვლევრის თქმით"
        before = "მკვლევრის თქმით, თავდამსხმელს ქსელზე წვდომა სჭირდება. ზოგადად 15 წლამდე ბავშვები."
        self.assertEqual(ka_check.qualifiers_lost(before, before.replace("მკვლევრის თქმით, ", "")),
                         ['K10: the edit dropped the qualifier "თქმით": keep every qualifier of the original next to its claim'])
        moved = "თავდამსხმელს, მკვლევრის თქმით, ქსელზე წვდომა სჭირდება. 15 წლამდე ბავშვები ზოგადად."
        self.assertEqual(ka_check.qualifiers_lost(before, moved), [])
        self.assertIn("მდე", ka_check.qualifiers_lost(before, before.replace("15 წლამდე", "15 წლის"))[0])
        # "before the OS" is not a qualifier: no number, so rewording it is fine
        self.assertEqual(ka_check.qualifiers_lost("კოდი სისტემამდე მუშაობს.", "კოდი სისტემის ჩატვირთვამდე იწყება."), [])

    def test_multiword_names(self):
        say = {"Hugging Face": "ჰაგინგ ფეისი", "1Password for Agents": "უანფასვორდ ფორ ეიჯენტს"}
        self.assertEqual(speech("Hugging Face-ზე და 1Password for Agents გამოვიდა.", say),
                         "ჰაგინგ ფეისზე და უანფასვორდ ფორ ეიჯენტს გამოვიდა.")
        p = ka_check.problems(story("1Password for Agents გამოვიდა. გამოიწერე tbilisi.today.", say=say), ART)
        self.assertNotIn("K19", rules(p))
        self.assertNotIn("K20", rules(p))

    def test_apple_units_and_question(self):  # the MacBook Short (2026-10-30): pounds, and a future-tense question
        p = ka_check.problems(story("14-დიუმიანი 3 ფუნტს იწონის, წინაზე ნახევარი ფუნტით მსუბუქია. "
                                    "შენ რას იფიქრებ? გამოიწერე tbilisi.today."), ART)
        self.assertEqual(sum(x.startswith("K22") for x in p), 2)
        self.assertTrue(any("რას ფიქრობ" in x for x in p))
        ok = ka_check.problems(story("14-დიუმიანი მოდელი 1,4 კილოგრამს იწონის. 3 მილიონი გაიყიდა, ფუტბოლზე კი "
                                     "აკრძალვა მოქმედებს. შენ რას ფიქრობ? გამოიწერე tbilisi.today."), ART)
        self.assertEqual([x for x in ok if x.startswith(("K1", "K22"))], [])  # დიუმი, მილიონი, ფუტბოლი, აკრძალვა


if __name__ == "__main__":
    unittest.main()
