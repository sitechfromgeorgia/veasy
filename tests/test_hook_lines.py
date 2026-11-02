"""The hook's line breaks: no hole in the block, no line ending on a word that belongs to what follows."""
import unittest

from tt_shorts.writer import HANG, hook_lines


class HookLines(unittest.TestCase):
    def test_short_head_stays_on_one_line(self):
        self.assertEqual(hook_lines(["რატომ ნელა?"]), ["რატომ ნელა?"])

    def test_words_are_never_changed_or_reordered(self):
        head = ["ახალი კვლევა აჩვენებს", "რომ ხელოვნური", "ინტელექტი სამუშაოს ცვლის"]
        self.assertEqual(" ".join(hook_lines(head)), " ".join(head))

    def test_every_line_fits_the_limit(self):
        head = ["ახალი კვლევა აჩვენებს რომ ხელოვნური ინტელექტი სამუშაოს ცვლის"]
        for line in hook_lines(head, limit=22):
            self.assertLessEqual(len(line), 22, line)

    def test_no_single_word_line_when_another_split_avoids_it(self):
        # the old character wrap produced ['თბილისში', 'ახალი', 'ტრანსპორტის ხაზი', ...] style holes
        lines = hook_lines(["Veasy ამბიდან", "ვიდეოს", "თავად აწყობს"])
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(len(l.split()) > 1 for l in lines), lines)

    def test_a_line_does_not_end_on_a_hanging_word(self):
        lines = hook_lines(["ახალი მოდელი გამოვიდა და ბაზარზე ძვირდება"])
        for line in lines[:-1]:
            self.assertNotIn(line.split()[-1], HANG, lines)

    def test_a_long_head_is_split_into_at_most_four_lines(self):
        head = ["ერთი ძალიან გრძელი სათაური რომელიც აუცილებლად რამდენიმე ხაზად უნდა დაიშალოს"]
        self.assertLessEqual(len(hook_lines(head)), 4)


if __name__ == "__main__":
    unittest.main()
