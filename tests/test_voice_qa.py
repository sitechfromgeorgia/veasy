"""Tests for Georgian numeral extraction and value checking in speech.voice_qa."""
import unittest

from tt_shorts import speech


class TestVoiceQANumerals(unittest.TestCase):
    def test_extract_numbers_digits(self):
        self.assertEqual(speech.extract_numbers("ფასი 250 ლარი იქნება"), [250])
        self.assertEqual(speech.extract_numbers("სულ 12.5 პროცენტი"), [12.5])
        self.assertEqual(speech.extract_numbers("2025 წელი"), [2025])

    def test_extract_numbers_georgian_words(self):
        self.assertEqual(speech.extract_numbers("ფასი ორას ორმოცდაათი ლარი იქნება"), [250])
        self.assertEqual(speech.extract_numbers("ორი ათას ოცდახუთი წელი"), [2025])
        self.assertEqual(speech.extract_numbers("ხუთი მილიონი ლარი"), [5000000])
        self.assertEqual(speech.extract_numbers("ოცდახუთი ადამიანი"), [25])
        self.assertEqual(speech.extract_numbers("ასი კილომეტრი"), [100])

    def test_matching_numbers_pass_qa(self):
        # Digits to digits
        res = speech.voice_qa("გაზის ფასი 250 ლარი იქნება", "გაზის ფასი 250 ლარი იქნება")
        self.assertFalse(any(r.get("number_mismatch") for r in res))

        # Digits in spoken, Georgian words in heard (aligner transcript)
        res = speech.voice_qa("გაზის ფასი 250 ლარი იქნება", "გაზის ფასი ორას ორმოცდაათი ლარი იქნება")
        self.assertFalse(any(r.get("number_mismatch") for r in res))

        # Words in spoken, digits in heard
        res = speech.voice_qa("გაზის ფასი ორას ორმოცდაათი ლარი იქნება", "გაზის ფასი 250 ლარი იქნება")
        self.assertFalse(any(r.get("number_mismatch") for r in res))

    def test_number_mismatch_fails_qa(self):
        # Spoken 250, but heard 25: must fail with score 0.0
        res = speech.voice_qa("გაზის ფასი 250 ლარი იქნება", "გაზის ფასი 25 ლარი იქნება")
        mismatches = [r for r in res if r.get("number_mismatch")]
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["score"], 0.0)
        self.assertEqual(mismatches[0]["expected"], 250)
        self.assertIn(25, mismatches[0]["heard"])

        # Spoken 1000, heard 100
        res2 = speech.voice_qa("სულ 1000 მოქალაქე", "სულ ასი მოქალაქე")
        mismatches2 = [r for r in res2 if r.get("number_mismatch")]
        self.assertEqual(len(mismatches2), 1)
        self.assertEqual(mismatches2[0]["expected"], 1000)

        # Spoken has multiple numbers, one missing or changed
        res3 = speech.voice_qa("პირველი 10 და მეორე 20", "პირველი 10 და მეორე 30")
        mismatches3 = [r for r in res3 if r.get("number_mismatch")]
        self.assertEqual(len(mismatches3), 1)
        self.assertEqual(mismatches3[0]["expected"], 20)


if __name__ == "__main__":
    unittest.main()
