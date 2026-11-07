"""Sound effects (sfx.py, tools/compose_sfx.py, props.mix_audio): cues from the timeline, one level, deterministic."""
import hashlib
import pathlib
import subprocess
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np

from tt_shorts import formats, props, sfx

ROOT = pathlib.Path(__file__).resolve().parent.parent


def timeline(transition="line", **more):
    return {"durationInFrames": 600, "transition": transition, "outroFrom": None, "scenes": [
        {"type": "hook", "from": 0, "duration": 120},
        {"type": "stat", "from": 120, "duration": 150, "mark": {"at": 60}},
        {"type": "bars", "from": 270, "duration": 150, "items": [{}, {}, {}]},
        {"type": "end", "from": 420, "duration": 180}], **more}


class Cues(unittest.TestCase):
    def test_cuts_marks_counts_and_bars(self):
        c = sfx.cues(timeline())
        names = [x["name"] for x in c]
        self.assertEqual(names.count("whoosh"), 3)  # one per cut, none before the first scene
        self.assertEqual(c[0], {"t": round(120 / 30 - sfx.WHOOSH_LEAD, 3), "name": "whoosh"})
        self.assertIn({"t": 6.0, "name": "pop"}, c)  # the mark lands at 120 + 60 frames
        ticks = [x["t"] for x in c if x["name"] == "tick"]
        self.assertGreaterEqual(len(ticks), 8)
        self.assertTrue(all(4.1 <= t <= 5.2 for t in ticks))  # while the number counts (frames 4-36 of the scene)
        self.assertEqual(names.count("thud"), 1)  # it settles
        self.assertEqual(names.count("blip"), 3)  # one per bar
        self.assertEqual([x["t"] for x in c], sorted(x["t"] for x in c))
        self.assertTrue(all(b["t"] - a["t"] >= sfx.MIN_GAP - 1e-9 for a, b in zip(c, c[1:])))

    def test_a_plain_cut_clicks_and_the_outro_chip_pops(self):
        c = sfx.cues(timeline("cut", outroFrom=500))
        self.assertNotIn("whoosh", [x["name"] for x in c])
        self.assertIn({"t": 4.0, "name": "click"}, c)
        self.assertIn({"t": round(500 / 30, 3), "name": "pop"}, c)

    def test_nothing_on_the_last_frames_and_a_flap_clicks(self):
        p = timeline()
        p["scenes"][1]["style"] = "flap"
        c = sfx.cues(p)
        self.assertNotIn("tick", [x["name"] for x in c])
        self.assertTrue(all(x["t"] < 600 / 30 for x in c))

    def test_cues_for_new_transitions(self):
        self.assertEqual(sfx.cues(timeline("iris"))[0]["name"], "pop")
        self.assertEqual(sfx.cues(timeline("shutter"))[0]["name"], "click")
        self.assertEqual(sfx.cues(timeline("blind"))[0]["name"], "click")
        self.assertEqual(sfx.cues(timeline("split"))[0]["name"], "whoosh")
        self.assertEqual(sfx.cues(timeline("corner"))[0]["name"], "whoosh")
        self.assertNotIn("whoosh", [x["name"] for x in sfx.cues(timeline("fade"))])


def story(kind):
    """30 seconds, three ways: a big number, an idea's turn (the object said), a hook's mark and nothing else."""
    t = timeline(outroFrom=780)
    t["durationInFrames"] = 900
    t["scenes"] = [{"type": "hook", "from": 0, "duration": 150}, {"type": "text", "from": 150, "duration": 150},
                   {"type": "text", "from": 300, "duration": 150, "mark": {"at": 50}},
                   {"type": "bars", "from": 450, "duration": 150, "items": [{}, {}]},
                   {"type": "text", "from": 600, "duration": 150}, {"type": "end", "from": 750, "duration": 150}]
    if kind == "number":
        t["scenes"][1] = {"type": "stat", "from": 150, "duration": 150}
    if kind == "idea":
        t["words"] = [{"text": "აქ", "start": 2.0, "end": 2.2}, {"text": "გასაღებმა", "start": 11.0, "end": 11.5}]
    if kind == "hook":
        t["scenes"][0]["mark"] = {"at": 40}
    return t


OBJECT = {"object": "გასაღები", "device": "d"}
CUT_SOUNDS = ("whoosh", "click", "tick", "thud")


class Meaning(unittest.TestCase):
    def test_one_main_and_two_to_four_small_in_thirty_seconds_on_three_stories(self):
        for kind in ("number", "idea", "hook"):
            c = sfx.cues(story(kind), OBJECT, "meaning")
            names = [x["name"] for x in c]
            self.assertEqual(names.count("impact"), 1, kind)
            self.assertIn(len(c) - 1, (2, 3, 4), kind)
            self.assertEqual(len(c) - 1, sfx.small_count(30.0), kind)  # three in 30 s
            self.assertEqual([x["t"] for x in c], sorted(x["t"] for x in c))
            main = next(x for x in c if x["name"] == "impact")
            self.assertEqual(main["t"], sfx.moment(story(kind), OBJECT)["t"])
            self.assertTrue(all(0 <= x["t"] < 30 for x in c))

    def test_the_main_moment_is_found_by_code_in_a_fixed_order_with_a_fallback(self):
        self.assertEqual(sfx.moment(story("number"), OBJECT), {"t": round((150 + 36) / 30, 3), "why": "number"})
        self.assertEqual(sfx.moment(story("idea"), OBJECT), {"t": 11.0, "why": "idea"})
        self.assertEqual(sfx.moment(story("hook"), None), {"t": round(40 / 30, 3), "why": "hook"})
        plain = sfx.moment(story("none"), None)
        self.assertEqual(plain, {"t": 13.5, "why": "fallback"})  # 45 % of the film
        self.assertEqual(sfx.moment({"durationInFrames": 90, "scenes": []}, None)["t"], 1.35)  # 45 % of a 3 s film, inside the margins

    def test_a_transition_gets_no_sound_of_its_own(self):
        for kind in ("number", "idea", "hook", "none"):
            p = story(kind)
            cuts = [s["from"] / 30 for s in p["scenes"][1:]]
            c = sfx.cues(p, OBJECT, "meaning")
            self.assertFalse([x for x in c if x["name"] in CUT_SOUNDS], kind)  # not the cut sounds
            self.assertFalse([x for x in c if any(abs(x["t"] - k) < sfx.NEAR_CUT for k in cuts)], kind)  # none on a cut
        for tr in ("line", "cut", "iris", "fade"):  # whatever the transition is
            self.assertEqual(sfx.cues({**story("idea"), "transition": tr}, OBJECT, "meaning"),
                             sfx.cues(story("idea"), OBJECT, "meaning"))

    def test_a_word_at_a_cut_still_gets_the_objects_sound_just_after_it(self):
        p = story("idea")
        p["words"][1]["start"] = 10.0  # scene 4 starts at 10 s: the object is the first word of a scene
        c = sfx.cues(p, OBJECT, "meaning")
        self.assertIn({"t": round(10.0 + sfx.NEAR_CUT, 3), "name": "obj-metal"}, c)
        self.assertIn({"t": round(10.0 + sfx.NEAR_CUT, 3), "name": "impact"}, c)  # and so does the main sound

    def test_the_object_has_one_sound_of_its_own_chosen_by_code(self):
        self.assertEqual(sfx.object_sound(OBJECT), "obj-metal")  # a key
        self.assertEqual(sfx.object_sound({"object": "ძველი ბოთლი"}), "obj-glass")  # by the last word
        self.assertEqual(sfx.object_sound({"object": "ყუთი"}), "obj-wood")
        self.assertEqual(sfx.object_sound({"object": "წყალი"}), "obj-water")
        odd = {"object": "მზესუმზირა"}  # no material known: a hash, the same every time
        self.assertEqual(sfx.object_sound(odd), sfx.object_sound(odd))
        self.assertTrue(sfx.object_sound(odd).startswith("obj-"))
        self.assertIsNone(sfx.object_sound(None))
        own = [x for x in sfx.cues(story("idea"), OBJECT, "meaning") if x["name"].startswith("obj-")]
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]["t"], 11.0)
        self.assertEqual([x for x in sfx.cues(story("idea"), None, "meaning") if x["name"].startswith("obj-")], [])
        self.assertIn("obj-metal", sfx.NAMES)

    def test_one_constant_level_no_ducking(self):
        with tempfile.TemporaryDirectory() as d:
            work = pathlib.Path(d)
            (work / "public").mkdir()
            p = {"durationInFrames": 900, "voice": "v.wav", "voiceTrim": 0, "music": "politics-1.m4a", "outro": "card",
                 "sfx": sfx.cues(story("idea"), OBJECT, "meaning"), "sfxMoment": sfx.moment(story("idea"), OBJECT)}
            with mock.patch.object(subprocess, "run") as run:
                props.mix_audio(work, p, work / "raw.mp4", work / "out.mp4")
            graph = run.call_args[0][0][run.call_args[0][0].index("-filter_complex") + 1]
            self.assertEqual(graph.count(f"volume={sfx.LEVEL_DB}dB[sfx]"), 1)  # the whole track, one static level
            self.assertNotIn("sidechain", graph)
            self.assertNotIn("eval=frame", graph)
            self.assertNotIn("compand", graph)
            self.assertEqual([m for m in __import__("re").findall(r"volume=([^,\[]+)", graph)],
                             ["-13.0dB", f"{sfx.LEVEL_DB}dB"])  # bed and effects: one number each, never an envelope
        # every meaning sound is levelled to the same loudness (Sounds.test_compose_...), and none is a riser
        for n in ("impact", "obj-wood", "obj-glass", "obj-metal", "obj-paper", "obj-water", "obj-soft"):
            self.assertIn(n, sfx.NAMES)

    def test_off_and_on_are_as_before_and_meaning_is_a_format_value(self):
        self.assertEqual(sfx.cues(timeline()), sfx.cues(timeline(), None, "on"))
        self.assertEqual(formats.get("news", sfx="meaning")["sfx"], "meaning")
        self.assertIn("meaning", sfx.OPTIONS)
        self.assertTrue(set(sfx.OPTIONS) == set(formats.SFX))
        from tt_shorts import compose
        t = {"duration": 20.0, "wipes": [2.0], "beats": [{"id": "a", "t": 5.0, "sfx": "pop"}]}
        self.assertEqual(compose.sfx_cues(t, "meaning"), [{"t": 5.0, "name": "pop"}])  # a wipe is a cut: no whoosh


class Sounds(unittest.TestCase):
    def test_compose_is_deterministic_short_and_level(self):
        compose = __import__("runpy").run_path(str(ROOT / "tools" / "compose_sfx.py"), run_name="t")
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            compose["main"](a)
            compose["main"](b)
            for n in sfx.NAMES:
                fa, fb = pathlib.Path(a, f"{n}.wav"), pathlib.Path(b, f"{n}.wav")
                self.assertEqual(hashlib.sha256(fa.read_bytes()).digest(), hashlib.sha256(fb.read_bytes()).digest(), n)
                with wave.open(str(fa)) as w:
                    self.assertEqual((w.getframerate(), w.getnchannels()), (sfx.SR, 1))
                    x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2") / 32767
                self.assertLessEqual(len(x) / sfx.SR, 0.4, n)  # short accents, never a riser
                active = x[np.abs(x) > 0.05 * np.max(np.abs(x))]
                rms_db = 20 * np.log10(np.sqrt(np.mean(active ** 2)))
                self.assertAlmostEqual(rms_db, compose["RMS_DB"], delta=1.0, msg=n)  # one loudness for every sound
                self.assertLessEqual(float(np.max(np.abs(x))), compose["PEAK"] + 0.01, n)

    def test_the_track_places_the_cues(self):
        with tempfile.TemporaryDirectory() as d:
            out = sfx.track([{"t": 1.0, "name": "pop"}, {"t": 2.5, "name": "tick"}], 4.0, pathlib.Path(d) / "s.wav")
            with wave.open(str(out)) as w:
                self.assertEqual((w.getnchannels(), w.getnframes()), (2, 4 * sfx.SR))
                x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2)[:, 0]
            loud = np.flatnonzero(np.abs(x) > 300) / sfx.SR
            self.assertAlmostEqual(loud[0], 1.0, delta=0.01)
            self.assertTrue(any(2.49 < t < 2.56 for t in loud))
            self.assertFalse(any(1.2 < t < 2.4 for t in loud))  # silence between: no bed, no pumping


class Mix(unittest.TestCase):
    def test_sfx_is_one_more_input_at_one_level(self):
        with tempfile.TemporaryDirectory() as d:
            work = pathlib.Path(d)
            (work / "public").mkdir()
            p = {"durationInFrames": 300, "voice": "v.wav", "voiceTrim": 0, "music": "m.m4a", "outro": "card",
                 "sfx": [{"t": 1.0, "name": "pop"}]}
            with mock.patch.object(subprocess, "run") as run:
                props.mix_audio(work, p, work / "raw.mp4", work / "out.mp4")
            cmd = run.call_args[0][0]
            graph = cmd[cmd.index("-filter_complex") + 1]
            self.assertEqual(cmd.count("-i"), 4)  # picture, voice, music, effects
            self.assertIn(f"[3:a]aresample=48000", graph)  # the effects are input 3, after the looped music
            self.assertIn(f"volume={sfx.LEVEL_DB}dB[sfx]", graph)
            self.assertIn("amix=inputs=3", graph)
            self.assertNotIn("sidechain", graph)  # no ducking
            with mock.patch.object(subprocess, "run") as run:
                props.mix_audio(work, {**p, "sfx": []}, work / "raw.mp4", work / "out.mp4")
            self.assertNotIn("[sfx]", run.call_args[0][0][run.call_args[0][0].index("-filter_complex") + 1])


class FormatKey(unittest.TestCase):
    def test_sfx_is_a_format_key_off_by_default(self):
        every = formats.load_all()
        self.assertTrue(all(f["sfx"] == "off" for f in every.values() if f.get("engine") != "hyperframes"))  # nothing
        # changes for current renders; the story format (a new, composed film) has its accents on
        self.assertEqual(every["story"]["sfx"], "on")
        self.assertEqual(formats.get("news", sfx="on")["sfx"], "on")
        with self.assertRaises(formats.FormatError):
            formats.get("news", sfx="loud")


if __name__ == "__main__":
    unittest.main()
