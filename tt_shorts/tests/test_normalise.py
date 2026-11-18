"""normalise.py: the writer's mechanical passes in one order, to a fixpoint, with the narration held as cuts.

What is under test: the run settles and running it again changes nothing; the anchors it writes split the narration
exactly where its cuts are, through the one splitter the checks use (normalize_ka.segments); and every pair of
passes that used to undo each other (the design's table) now ends in one state.

Run: /root/.hermes/shared-plugins/veasy/.venv/bin/python -m pytest tt_shorts/tests/test_normalise.py -q
The corpus case (every story under data/stories) runs with VEASY_NORMALISE_CORPUS=1.
"""
import glob
import json
import os
import pathlib
import unittest

from tt_shorts import catalog, ka_check, news_check, normalise, normalize_ka

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Sentences of a plain city story, each long enough for any one scene's minimum (catalog min_words, min_seconds).
HOOK = "თბილისში ახალი ავტობუსები გამოჩნდა და მგზავრებმა ისინი უკვე გამოსცადეს."
FLEET = "ქალაქის მერიის ცნობით, ხაზზე ოცდაათი ახალი ავტობუსი გავიდა ამ კვირაში."
FARE = "ბილეთის ფასი არ შეცვლილა და მგზავრობა ისევ ერთ ლარად დარჩა."
GREEN = "მერიის თქმით, ახალი ავტობუსები გარემოსთვის უფრო უსაფრთხოა და ნაკლებ ხმაურს გამოსცემს."
PLAIN = "ახალი ავტობუსები ლურჯი ფერისაა და ქალაქის გერბი ახატია მათზე."  # says no sign verb
GROW = "მგზავრების რაოდენობა ბოლო თვეებში საგრძნობლად გაიზარდა ყველა მთავარ მარშრუტზე."
END = "ყველა დეტალი tbilisi.today-ზე, გამოიწერე არხი და გაიგე მეტი."


def story(*pairs, **top):
    """A story from (scene, its sentence) pairs; each anchor is its sentence's first three words."""
    scenes = []
    for scene, text in pairs:
        scenes.append({**scene, "at": " ".join(text.split()[:3])})
    return {"category": "society", "narration": " ".join(t for _, t in pairs), "scenes": scenes, **top}


def hook():
    return {"type": "hook", "lines": ["ახალი ავტობუსები", "თბილისში"]}


def end():
    return {"type": "end"}


def types(s):
    return [x["type"] for x in s["scenes"]]


def cuts_of(s):
    return normalize_ka.segments(s["narration"], [x["at"] for x in s["scenes"]])


class Fixpoint(unittest.TestCase):
    def assertExit(self, s):
        """The exit assertion: the anchors are exact text, segments() places every scene, scene 0 starts at 0."""
        self.assertTrue(normalise.anchors_ok(s), s)
        cuts = cuts_of(s)
        self.assertIsNotNone(cuts)
        self.assertEqual(cuts[0], 0)
        self.assertEqual(cuts, sorted(set(cuts)))

    def stories(self):
        for p in sorted((ROOT / "stories").glob("*.json")):
            yield p.name, json.loads(p.read_text(encoding="utf-8"))

    def test_every_demo_story_settles_and_a_second_run_changes_nothing(self):
        for name, s in self.stories():
            with self.subTest(name):
                first = normalise.normalise(s, [])
                self.assertEqual(first.status, "settled")
                again = normalise.normalise(first.story, [])
                self.assertEqual(again.story, first.story)
                self.assertEqual(again.log, [])

    def test_the_exit_assertion_holds_on_every_demo_story(self):
        for name, s in self.stories():
            with self.subTest(name):
                out = normalise.normalise(s, []).story
                if out["scenes"] and normalize_ka.tokens(out["narration"]):
                    self.assertExit(out)

    @unittest.skipUnless(os.environ.get("VEASY_NORMALISE_CORPUS"), "the stored corpus is slow; opt in")
    def test_every_stored_story_settles_idempotently_with_exact_anchors(self):
        for p in sorted(glob.glob(str(ROOT / "data" / "stories" / "**" / "*.json"), recursive=True)):
            if p.endswith(".sources.json"):
                continue
            s = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
            side = pathlib.Path(p[:-5] + ".sources.json")
            arts = json.loads(side.read_text(encoding="utf-8")) if side.exists() else []
            with self.subTest(p):
                first = normalise.normalise(s, arts)
                self.assertEqual(first.status, "settled")
                self.assertEqual(normalise.normalise(first.story, arts).story, first.story)
                if first.story["scenes"] and normalize_ka.tokens(first.story["narration"]):
                    self.assertExit(first.story)

    def test_the_input_is_not_modified_and_the_log_names_the_pass(self):
        s = story((hook(), HOOK), ({"type": "points", "items": ["ფასი — ერთი ლარი", "ახალი ხაზები"]}, FARE),
                  (end(), END))
        before = json.dumps(s, ensure_ascii=False)
        out = normalise.normalise(s, [])
        self.assertEqual(json.dumps(s, ensure_ascii=False), before)
        self.assertIn("surface:no_dashes", [e["pass"] for e in out.log])
        self.assertEqual(out.story["scenes"][1]["items"][0], "ფასი, ერთი ლარი")


class Splitter(unittest.TestCase):
    """normalize_ka.segments is the one splitter: K9 and the news rules read slices through it."""

    def test_segments_matches_whole_tokens_only(self):
        n = "ახალი წლები დაიწყო. ები არ არის სიტყვა."
        self.assertEqual(normalize_ka.segments(n, ["ახალი", "ები არ"]), [0, 3])
        self.assertIsNone(normalize_ka.segments(n, ["ახალი", "ზეგ"]))
        self.assertIsNone(normalize_ka.segments(n, ["ახალი", ""]))

    def test_a_space_grouped_number_is_one_token_for_every_reader(self):
        n = "ფასი 2 250 ლარი გახდა და ეს ბევრია ყველასთვის."
        s = {"narration": n, "scenes": [{"type": "hook", "at": "ფასი 2 250"}, {"type": "end", "at": "და ეს"}]}
        self.assertEqual(normalize_ka.segments(n, ["ფასი 2 250", "და ეს"]), [0, 4])
        self.assertEqual(ka_check.scene_words(s), [(0, "hook", 4), (1, "end", 4)])
        self.assertEqual(news_check.scene_part(s, 0), "ფასი 2 250 ლარი გახდა")

    def test_ka_check_and_news_check_read_the_same_slices(self):
        s = normalise.normalise(story((hook(), HOOK), ({"type": "points", "items": ["ა", "ბ"]}, FARE),
                                      (end(), END)), []).story
        cuts = cuts_of(s) + [len(normalize_ka.tokens(s["narration"]))]
        words = [n for _, _, n in ka_check.scene_words(s)]
        self.assertEqual(words, [b - a for a, b in zip(cuts, cuts[1:])])
        self.assertEqual([len(news_check.scene_part(s, i).split()) for i in range(3)], words)


class FightingPairs(unittest.TestCase):
    """One case per pair of passes that used to undo each other (design, section 2)."""

    def test_a_relative_day_is_dropped_never_turned_into_digits(self):
        # _fix_dates / _spell_relative_days vs N2: naming the date adds a numeral the source never said
        s = story((hook(), HOOK), ({"type": "points", "items": ["ხაზზე ახალი ავტობუსები", "დღეს ფასი უცვლელია"]},
                                   FLEET.replace("ხაზზე", "დღეს ხაზზე")), (end(), END))
        out = normalise.normalise(s, []).story
        self.assertNotIn("დღეს", out["narration"])
        self.assertEqual(out["scenes"][1]["items"][1], "ფასი უცვლელია")
        self.assertEqual(news_check.numbers(out["narration"]), news_check.numbers(s["narration"]))
        self.assertTrue(normalise.anchors_ok(out))

    def test_a_dash_after_a_digit_becomes_a_hyphen_the_voice_can_read(self):
        # _no_dashes vs speech (KE): „24, ე" can't be read aloud
        self.assertEqual(normalise.no_dashes("24–ე სხდომა"), "24-ე სხდომა")
        self.assertEqual(normalise.no_dashes("2020—2022 წლებში"), "2020-2022 წლებში")
        self.assertEqual(normalise.no_dashes("ფასი — ერთი ლარი"), "ფასი, ერთი ლარი")

    def test_a_known_names_word_is_not_a_stray_english_word(self):
        # _drop_stray_latin vs _fix_unspoken_names and K19's own known names
        s = story((hook(), HOOK), ({"type": "points", "items": ["1Password for Agents ახლა ხელმისაწვდომია",
                                                                "ახალი ardi ფუნქცია"]}, FARE),
                  ({"type": "who", "items": [{"name": "ნინო", "role": "მინისტრი ardi"}]}, GREEN), (end(), END),
                  say={"1Password for Agents": "უანფასვორდ ფორ ეიჯენთს"})
        out = normalise.normalise(s, []).story
        self.assertEqual(out["scenes"][1]["items"], ["1Password for Agents ახლა ხელმისაწვდომია", "ახალი ფუნქცია"])
        self.assertEqual(out["scenes"][2]["items"][0]["role"], "მინისტრი")  # an item object's text too

    def test_a_short_hook_keeps_its_place_and_takes_its_words(self):
        # _fix_first_scene vs _drop_short_scenes: the hook was dropped, then "the first scene must be a hook"
        s = story((hook(), HOOK), ({"type": "points", "items": ["ა", "ბ"]}, FARE), (end(), END))
        s["scenes"][1]["at"] = " ".join(HOOK.split()[3:6])  # the writer gave the hook three words
        out = normalise.normalise(s, []).story
        self.assertEqual(types(out), ["hook", "points", "end"])
        self.assertGreaterEqual(ka_check.scene_words(out)[0][2], catalog.min_words()["hook"])
        self.assertEqual(cuts_of(out)[0], 0)

    def test_a_story_that_opens_on_another_scene_gets_a_hook_inserted_with_lines(self):
        # _fix_first_scene vs N11 and the hook's required lines: renaming left a hook without lines
        stat = {"type": "stat", "value": 30, "label": "ახალი ავტობუსი", "em": "ახალი ავტობუსი"}
        s = story((stat, HOOK + " " + FLEET), ({"type": "points", "items": ["ა", "ბ"]}, FARE), (end(), END))
        out = normalise.normalise(s, []).story
        self.assertEqual(types(out), ["hook", "stat", "points", "end"])
        lines = out["scenes"][0]["lines"]
        self.assertTrue(lines and all(len(x) <= 24 for x in lines), lines)
        self.assertTrue(" ".join(lines) in HOOK)  # the voice's own first words: nothing new on screen
        self.assertNotIn("em", out["scenes"][0])
        self.assertEqual(out["scenes"][1]["value"], 30)

    def test_marks_are_judged_after_the_clamp(self):
        # _clamp_texts / _fix_long_text vs _fix_em_marks: a mark on words the clamp removed goes, one it kept stays
        label = "ქალაქის მერიის ცნობით ხაზზე ოცდაათი ახალი ავტობუსი გავიდა ამ კვირაში და კიდევ მეტი გავა"
        s = story((hook(), HOOK), ({"type": "stat", "value": 30, "label": label, "em": "კიდევ მეტი გავა"}, FLEET),
                  ({"type": "points", "headline": "ბილეთის ფასი", "items": ["ა", "ბ"], "em": "ბილეთის ფასი"}, FARE),
                  (end(), END))
        out = normalise.normalise(s, []).story
        self.assertEqual(types(out), ["hook", "stat", "points", "end"])
        self.assertLessEqual(len(out["scenes"][1]["label"]), catalog.get("stat")["slots"]["label"]["max"])
        self.assertNotIn("em", out["scenes"][1])
        self.assertEqual(out["scenes"][2]["em"], "ბილეთის ფასი")

    def test_a_clipped_quote_stays_a_verbatim_quote(self):
        # _fix_long_text vs _drop_unverbatim_quotes: the clip added a full stop no source has, and the next round
        # dropped the quote scene
        said = ("ახალი ავტობუსები გარემოსთვის უფრო უსაფრთხოა და ნაკლებ ხმაურს გამოსცემს, ამიტომ ქალაქი "
                "მომავალ წელს კიდევ ორმოცდაათ ასეთ ავტობუსს შეიძენს")
        s = story((hook(), HOOK), ({"type": "quote", "text": said, "by": "მერი"}, GREEN), (end(), END))
        out = normalise.normalise(s, [HOOK + " " + said + " " + GREEN]).story
        self.assertEqual(types(out), ["hook", "quote", "end"])
        self.assertIn(news_check.flat(out["scenes"][1]["text"]), news_check.flat(said))

    def test_seat_keeps_a_mark_in_the_scene_that_shows_it(self):
        # _hard_anchor / _drop_short_scenes vs em: the writer's cut put the marked words in the scene before
        stat = {"type": "stat", "value": 30, "label": "ავტობუსი ხაზზე", "em": "ხაზზე"}
        s = story((hook(), HOOK), (stat, FLEET), ({"type": "points", "items": ["ა", "ბ"]}, FARE), (end(), END))
        s["scenes"][1]["at"] = "ოცდაათი ახალი ავტობუსი"  # after „ხაზზე"
        s["narration"] = s["narration"].replace(FLEET, FLEET + " " + GROW)
        out = normalise.normalise(s, []).story
        self.assertEqual(out["scenes"][1]["em"], "ხაზზე")
        self.assertIn("ხაზზე", news_check.scene_part(out, 1))

    def test_length_is_cut_with_whole_slices_and_the_anchors_stay_exact(self):
        # _shorten_story vs every slice-based pass: it cut by the anchor's words and the wrong occurrence
        s = story((hook(), HOOK), ({"type": "points", "items": ["ა", "ბ"]}, FLEET),
                  ({"type": "stat", "value": 1, "label": "ფასი"}, FARE), ({"type": "who", "items": [{"name": "მერი"}]},
                                                                         GREEN),
                  ({"type": "pair", "items": [{"title": "ა"}, {"title": "ბ"}]}, GROW), (end(), END))
        out = normalise.normalise(s, [], {"max_seconds": 22, "min_seconds": 10}).story
        self.assertLess(len(out["scenes"]), len(s["scenes"]))
        self.assertEqual(types(out)[0], "hook")
        self.assertEqual(types(out)[-1], "end")
        kept = [x for x in (HOOK, FLEET, FARE, GREEN, GROW, END) if x in out["narration"]]
        self.assertEqual(" ".join(kept), out["narration"])  # whole sentences left, nothing cut mid-sentence
        self.assertTrue(normalise.anchors_ok(out))
        self.assertEqual(cuts_of(out)[0], 0)

    def test_a_drop_between_two_stats_ends_in_one_stat(self):
        # any drop vs _fix_repeats: A X A -> A A must merge in a later round, which is why the loop runs again
        sign = {"type": "sign", "icon": "bus", "verb": "falls", "label": "ავტობუსები"}  # no verb of it is said
        s = story((hook(), HOOK), ({"type": "stat", "value": 30, "label": "ავტობუსი"}, FLEET), (sign, PLAIN),
                  ({"type": "stat", "value": 1, "label": "ლარი"}, FARE), (end(), END))
        result = normalise.normalise(s, [])
        self.assertEqual(result.status, "settled")
        self.assertEqual(types(result.story), ["hook", "stat", "end"])
        self.assertEqual(result.story["scenes"][1]["value"], 30)
        self.assertGreaterEqual(max(e["round"] for e in result.log), 1)

    def test_a_sign_whose_verb_is_said_stays(self):
        # writer._repair_scenes dropped every sign while three scenes remained, so _fix_sign_verbs never ran
        sign = {"type": "sign", "icon": "bus", "verb": "falls", "label": "მგზავრები"}
        s = story((hook(), HOOK), ({"type": "stat", "value": 30, "label": "ავტობუსი"}, FLEET), (sign, GROW),
                  ({"type": "points", "items": ["ა", "ბ"]}, FARE), (end(), END))
        out = normalise.normalise(s, ["ტექსტი"]).story
        self.assertEqual(types(out), ["hook", "stat", "sign", "points", "end"])
        self.assertEqual(out["scenes"][2]["verb"], "rises")  # the verb its part says (გაიზარდა)

    def test_an_unsourced_quote_mark_goes_and_the_anchors_follow(self):
        # _drop_unverbatim_quotes rewrote the narration under the anchors
        text = FARE.replace("ისევ ერთ ლარად დარჩა", "„ისევ ერთ ლარად დარჩა“")
        s = story((hook(), HOOK), ({"type": "points", "items": ["ა", "ბ"]}, text), (end(), END))
        out = normalise.normalise(s, [HOOK + " ბილეთის ფასი არ შეცვლილა"]).story
        self.assertNotIn("„", out["narration"])
        self.assertIn("ისევ ერთ ლარად დარჩა", out["narration"])
        self.assertTrue(normalise.anchors_ok(out))

    def test_a_value_said_in_words_or_with_a_decimal_comma_is_said(self):
        # the stat rule compared digits only, and dropped stats whose narration spells the number (owner's rule)
        self.assertTrue(normalise.value_said(3, "საბჭო სამი წევრისგან შედგება"))
        self.assertTrue(normalise.value_said(2, "მხოლოდ ორ პროცენტამდე"))
        self.assertTrue(normalise.value_said(57.6, "ხმების 57,6% მიიღო"))
        self.assertTrue(normalise.value_said(1500, "1 500 ლარი"))
        self.assertFalse(normalise.value_said(2, "ორგანიზაცია"))
        self.assertFalse(normalise.value_said(40, "ორი"))

    def test_a_removal_never_breaks_the_directors_two_sides(self):
        # seat's length fit took the scene between two quotes; _fix_repeats then merged the two speakers into one
        q1 = {"type": "quote", "text": "ავტობუსები უსაფრთხოა", "by": "მერი"}
        q2 = {"type": "quote", "text": "ფასი არ შეცვლილა", "by": "მინისტრი"}
        s = story((hook(), HOOK), (q1, GREEN), ({"type": "who", "items": [{"name": "მერი"}]}, FLEET), (q2, FARE),
                  (end(), END), director="witness")
        arts = [f"{HOOK} {GREEN} {FLEET} {FARE} {END} მერი: „ავტობუსები უსაფრთხოა“ მინისტრი: „ფასი არ შეცვლილა“"]
        out = normalise.normalise(s, arts, {"max_seconds": 22, "min_seconds": 10, "facts": {"speakers": 2}}).story
        self.assertEqual({x.get("by") for x in out["scenes"] if x["type"] == "quote"}, {"მერი", "მინისტრი"})


class SeatInfeasible(unittest.TestCase):
    """When no tiling meets every constraint, seat removes one thing at a time, least first, never the frame."""

    def test_a_mark_the_voice_never_says_goes_and_its_scene_stays(self):
        stat = {"type": "stat", "value": 30, "label": "ავტობუსი სულ", "em": "სულ"}
        s = story((hook(), HOOK), (stat, FLEET), ({"type": "points", "items": ["ა", "ბ"]}, FARE), (end(), END))
        out = normalise.normalise(s, []).story
        self.assertEqual(types(out), ["hook", "stat", "points", "end"])
        self.assertNotIn("em", out["scenes"][1])

    def test_too_few_words_drops_the_least_needed_scene_never_the_hook_or_the_end(self):
        short = "ხაზზე ახალი ავტობუსი გავიდა."
        s = story((hook(), HOOK), ({"type": "stat", "value": 30, "label": "ავტობუსი"}, FLEET),
                  ({"type": "points", "items": ["ა", "ბ"]}, short), ({"type": "who", "items": [{"name": "მერი"}]}, short),
                  (end(), END))
        out = normalise.normalise(s, []).story
        self.assertEqual(types(out)[0], "hook")
        self.assertEqual(types(out)[-1], "end")
        self.assertIn("stat", types(out))  # a scene with a figure goes last
        mins = catalog.min_words()
        self.assertTrue(all(n >= mins[t] for _, t, n in ka_check.scene_words(out)), ka_check.scene_words(out))

    def test_below_three_scenes_nothing_is_removed_and_the_checks_name_what_is_left(self):
        s = story((hook(), "ახალი ავტობუსები."), ({"type": "points", "items": ["ა", "ბ"]}, "ფასი უცვლელია."),
                  (end(), "გამოიწერე არხი."))
        result = normalise.normalise(s, [])
        self.assertEqual(result.status, "settled")
        self.assertEqual(types(result.story), ["hook", "points", "end"])
        self.assertTrue(normalise.anchors_ok(result.story))
        self.assertTrue(any(p.startswith("K9") for p in ka_check.problems(result.story, {"text": ""})))


if __name__ == "__main__":
    unittest.main()
