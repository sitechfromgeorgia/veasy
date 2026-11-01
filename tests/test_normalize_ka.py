"""Golden tests for Georgian normalization (examples from knowledge/.../georgian-tts/1-text-normalization.md)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from tt_shorts.normalize_ka import cardinal, learn, ordinal, speak_token, speech, tokens, unspoken


class Cardinals(unittest.TestCase):
    def test_numbers(self):
        cases = {0: "ნული", 8: "რვა", 9: "ცხრა", 20: "ოცი", 27: "ოცდაშვიდი", 30: "ოცდაათი", 47: "ორმოცდაშვიდი",
                 83: "ოთხმოცდასამი", 99: "ოთხმოცდაცხრამეტი", 100: "ასი", 125: "ას ოცდახუთი", 800: "რვაასი",
                 900: "ცხრაასი", 1000: "ათასი", 1500: "ათას ხუთასი", 2012: "ორი ათას თორმეტი",
                 12345: "თორმეტი ათას სამას ორმოცდახუთი", 1_000_000: "ერთი მილიონი",
                 2_000_500: "ორი მილიონ ხუთასი", 1_000_000_000: "ერთი მილიარდი"}
        for n, words in cases.items():
            self.assertEqual(cardinal(n), words, n)

    def test_ordinals(self):
        for n, words in {1: "პირველი", 2: "მეორე", 8: "მერვე", 9: "მეცხრე", 20: "მეოცე", 21: "ოცდამეერთე",
                         31: "ოცდამეთერთმეტე"}.items():
            self.assertEqual(ordinal(n), words, n)


class Tokens(unittest.TestCase):
    def check(self, cases):
        for (token, nxt), want in cases.items():
            self.assertEqual(speak_token(token, nxt), want, token)

    def test_percent_and_cases(self):
        self.check({("36%-ის", ""): "ოცდათექვსმეტი პროცენტის", ("36%-ს", ""): "ოცდათექვსმეტ პროცენტს",
                    ("36%-ით", ""): "ოცდათექვსმეტი პროცენტით", ("83%", ""): "ოთხმოცდასამი პროცენტი",
                    ("80%-ს", ""): "ოთხმოც პროცენტს", ("47%-ის", ""): "ორმოცდაშვიდი პროცენტის"})

    def test_attached_endings(self):
        self.check({("4-ჯერ", ""): "ოთხჯერ", ("1-ჯერ", ""): "ერთხელ", ("8-ჯერ", ""): "რვაჯერ",
                    ("10-ზე", "მეტი"): "ათზე", ("5-მა", ""): "ხუთმა", ("5-მდე", ""): "ხუთამდე",
                    ("8-მდე", ""): "რვამდე", ("5-დან", ""): "ხუთიდან", ("8-დან", ""): "რვიდან",
                    ("5-ის", ""): "ხუთის", ("8-ის", ""): "რვის", ("21-ე", ""): "ოცდამეერთე",
                    ("1-ელი", ""): "პირველი"})

    def test_before_a_noun(self):
        self.check({("2012", "წელს"): "ორი ათას თორმეტ", ("2025", "წელს"): "ორი ათას ოცდახუთ",
                    ("5", "სერვერს"): "ხუთ", ("5", "სერვერი"): "ხუთი", ("5", "სერვერის"): "ხუთი",
                    ("9", "პირს"): "ცხრა", ("32", "აკრძალული"): "ოცდათორმეტი"})

    def test_other(self):
        self.check({("3.5", ""): "სამი მთელი ხუთი მეათედი", ("1,500", ""): "ათას ხუთასი",
                    ("10–15", ""): "ათიდან თხუთმეტამდე", ("16GB", ""): "თექვსმეტი გიგაბაიტი",
                    ("B300", ""): "ბი სამასი", ("GPT-5", ""): "ჯი პი ტი ხუთი", ("AI-ს", ""): "ეი აის",
                    ("GPU-ები", ""): "ჯი პი იუები", ("NVIDIA-მ", ""): "ენვიდიამ", ("NVIDIA-ს", ""): "ენვიდიას",
                    ("tbilisi.today", ""): "თბილისი თუდეი", ("ჩიპი", ""): None})

    def test_grouped_thousands(self):  # the blog groups thousands with a space: one number, not two
        self.check({("2 250-ზე", "მეტ"): "ორი ათას ორას ორმოცდაათზე", ("2 900", "მცდელობის"): "ორი ათას ცხრაასი",
                    ("151 000-ზე", "მეტი"): "ას ორმოცდათერთმეტი ათასზე", ("3 218 965", "ჩანაწერი"):
                    "სამი მილიონ ორას თვრამეტი ათას ცხრაას სამოცდახუთი"})
        self.assertEqual(speech("AI-აგენტები 2 250-ზე მეტ ტენანტში შევიდნენ."),
                         "ეი აი აგენტები ორი ათას ორას ორმოცდაათზე მეტ ტენანტში შევიდნენ.")
        self.assertEqual(tokens("წუთში 2 900 მცდელობით, 2026 წლის 15 ოქტომბერს"),
                         ["წუთში", "2 900", "მცდელობით,", "2026", "წლის", "15", "ოქტომბერს"])

    def test_names(self):  # the lexicon, the script's "say", case endings after the hyphen
        self.check({("Microsoft-ის", ""): "მაიკროსოფტის", ("Microsoft-მა", ""): "მაიკროსოფტმა",
                    ("Microsoft", ""): "მაიკროსოფტი", ("Huawei-მ", ""): "ჰუავეიმ", ("Tesla-ით", ""): "ტესლათი",
                    ("Claude-ის", ""): "კლოდის", ("GPT-5-ის", ""): "ჯი პი ტი ხუთის",
                    ("ARTEX", ""): None, ("AAIF-ის", ""): "ეი ეი აი ეფის"})
        say = {"ARTEX": "არტექსი", "ConnectWise": "ქონექთვაიზი", "Storm-0940": "სტორმ ნოლ ცხრაას ორმოცი"}
        self.assertEqual(speech("Storm-0940-მა ConnectWise-ის აპლიკაცია ARTEX AI-ით გატეხა.", say),
                         "სტორმ ნოლ ცხრაას ორმოცმა ქონექთვაიზის აპლიკაცია არტექსი ეი აით გატეხა.")
        self.assertEqual(unspoken("Zeabur-მა და Microsoft-მა AI გამოიყენეს.", {}), ["Zeabur"])

    def test_approved_names(self):  # the first learned names Louie confirmed (2026-10-28), and what code spells itself
        self.check({("Oracle-მა", ""): "ორაკლმა", ("PXE", ""): "პიქსი", ("TPM-ის", ""): "ტი პი ემის",
                    ("UEFI", ""): "იუ ი ეფ აი", ("AMI", ""): "ეი ემ აი", ("NVL72", ""): "ენ ვი ელ სამოცდათორმეტი",
                    ("EDK2", ""): "ი დი ქეი ორი", ("macOS", ""): "მაკ ოუ ეს"})
        self.assertEqual(speech("Secure Boot და EDK II გამოიყენება, Vera Rubin კი Oracle AI Workspace-ში."),
                         "სიქიურ ბუტი და ი დი ქეი ორი გამოიყენება, ვერა რუბინი კი ორაკლ ეი-აი უორკსფეისში.")

    def test_ids_are_not_learned(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"SHORTS_DATA": d}):
            new = learn({"CVE-2026-97631": "სი ვი ი", "KB5034441": "ქეი ბი", "Storm-0940": "სტორმ ნოლ ცხრაას ორმოცი",
                         "TPM": "ტი პი ემ", "Oracle": "ორაკლი"}, "test")
            self.assertEqual(new, ["Storm-0940"])  # IDs are one-offs, acronyms are spelled by code, Oracle is approved
            with open(os.path.join(d, "lexicon_learned.json"), "w", encoding="utf-8") as f:  # an older file
                json.dump({"TPM": {"say": "ტე-პე-ემ"}, "CVE-2026-97631": {"say": "სი ვი ი"}, "Zeabur": {"say": "ზიბური"}}, f)
            self.assertEqual(speech("TPM-ის და Zeabur-ის"), "ტი პი ემის და ზიბურის")

    def test_versions(self):
        self.assertEqual(speech("Claude Opus 4.7-ზე მუშაობს, firmware 23.0.1-ზე.", {"Opus": "ოპუსი", "firmware": "ფირმვეარი"}),
                         "კლოდი ოპუსი ოთხი წერტილი შვიდზე მუშაობს, ფირმვეარი ოცდასამი წერტილი ნული წერტილი ერთზე.")

    def test_sentence_keeps_punctuation(self):
        self.assertEqual(speech("მან 83% აჩვენა, ექიმებმა კი 36%. გამოიწერე tbilisi.today."),
                         "მან ოთხმოცდასამი პროცენტი აჩვენა, ექიმებმა კი ოცდათექვსმეტი პროცენტი. გამოიწერე თბილისი თუდეი.")


if __name__ == "__main__":
    unittest.main()
