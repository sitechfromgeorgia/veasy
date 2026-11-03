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
