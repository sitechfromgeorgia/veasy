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


class ScenarioCues(unittest.TestCase):
    def test_job_mappings(self):
        # 1. Promise (hook) -> whoosh / pop
        self.assertEqual(sfx.sound_for_beat("promise"), "whoosh")
        self.assertEqual(sfx.sound_for_beat("promise", alternate=True), "pop")
        self.assertEqual(sfx.allowed_sounds_for_beat("promise"), ("whoosh", "pop"))

        # 2. Setup / Context -> click / whoosh
        self.assertEqual(sfx.sound_for_beat("setup"), "click")
        self.assertEqual(sfx.sound_for_beat("setup", alternate=True), "whoosh")
        self.assertEqual(sfx.sound_for_beat("context"), "click")
        self.assertEqual(sfx.allowed_sounds_for_beat("context"), ("click", "whoosh"))

        # 3. False lead -> blip / click
        self.assertEqual(sfx.sound_for_beat("false_lead"), "blip")
        self.assertEqual(sfx.sound_for_beat("false_lead", alternate=True), "click")
        self.assertEqual(sfx.sound_for_beat("false lead"), "blip")
        self.assertEqual(sfx.allowed_sounds_for_beat("false_lead"), ("blip", "click"))

        # 4. Complication / Evidence -> tick / blip
        self.assertEqual(sfx.sound_for_beat("complication"), "tick")
        self.assertEqual(sfx.sound_for_beat("complication", alternate=True), "blip")
        self.assertEqual(sfx.sound_for_beat("evidence"), "tick")
        self.assertEqual(sfx.allowed_sounds_for_beat("evidence"), ("tick", "blip"))

        # 5. Turn (peripeteia) -> pop / whoosh
        self.assertEqual(sfx.sound_for_beat("turn"), "pop")
        self.assertEqual(sfx.sound_for_beat("turn", alternate=True), "whoosh")
        self.assertEqual(sfx.sound_for_beat("peripeteia"), "pop")
        self.assertEqual(sfx.allowed_sounds_for_beat("peripeteia"), ("pop", "whoosh"))

        # 6. Payoff (climax / answer) -> thud / pop
        self.assertEqual(sfx.sound_for_beat("payoff"), "thud")
        self.assertEqual(sfx.sound_for_beat("payoff", alternate=True), "pop")
        self.assertEqual(sfx.sound_for_beat("climax"), "thud")
        self.assertEqual(sfx.sound_for_beat("answer"), "thud")
        self.assertEqual(sfx.allowed_sounds_for_beat("payoff"), ("thud", "pop"))

        # 7. Resolution -> click / pop
        self.assertEqual(sfx.sound_for_beat("resolution"), "click")
        self.assertEqual(sfx.sound_for_beat("resolution", alternate=True), "pop")
        self.assertEqual(sfx.sound_for_beat("resolve"), "click")
        self.assertEqual(sfx.allowed_sounds_for_beat("resolution"), ("click", "pop"))

    def test_explicit_sound_override(self):
        self.assertEqual(sfx.sound_for_beat("promise", sound="pop"), "pop")
        self.assertEqual(sfx.sound_for_beat("payoff", sound="pop"), "pop")
        self.assertEqual(sfx.sound_for_beat("setup", sound="whoosh"), "whoosh")
        # Invalid sound name falls back to job default
        self.assertEqual(sfx.sound_for_beat("payoff", sound="screaming_guitar"), "thud")

    def test_scenario_timeline_synchronization(self):
        # A 7-beat complete dramatic arc story
        p = {
            "durationInFrames": 1200,
            "transition": "line",
            "scenario": {
                "id": "mystery_reveal",
                "beats": [
                    {"job": "promise", "sound_cue": "whoosh"},
                    {"job": "setup", "sound_cue": "click"},
                    {"job": "false_lead", "sound_cue": "blip"},
                    {"job": "complication", "sound_cue": "tick"},
                    {"job": "turn", "sound_cue": "pop"},
                    {"job": "payoff", "sound_cue": "thud"},
                    {"job": "resolution", "sound_cue": "click"},
                ]
            },
            "scenes": [
                {"type": "hook", "from": 0, "duration": 120, "mark": {"at": 60}},
                {"type": "text", "from": 120, "duration": 150, "mark": {"at": 45}},
                {"type": "text", "from": 270, "duration": 150, "mark": {"at": 45}},
                {"type": "text", "from": 420, "duration": 150, "mark": {"at": 45}},
                {"type": "text", "from": 570, "duration": 150, "mark": {"at": 45}},
                {"type": "stat", "from": 720, "duration": 150, "mark": {"at": 60}},
                {"type": "end", "from": 870, "duration": 180, "mark": {"at": 30}},
            ]
        }
        c = sfx.cues(p)
        # 1. Promise: whoosh at t=0.0 (opening sweep)
        self.assertEqual(c[0], {"t": 0.0, "name": "whoosh"})
        # Hook mark at frame 60 (2.0s): pop
        self.assertIn({"t": 2.0, "name": "pop"}, c)

        # 2. Setup: cut at frame 120 (4.0s) clicks instead of whoosh
        self.assertIn({"t": 4.0, "name": "click"}, c)

        # 3. False lead: cut at frame 270 whooshes (270/30 - 0.1 = 8.9s); mark at 270+45=315 frames (10.5s) blips!
        self.assertIn({"t": 8.9, "name": "whoosh"}, c)
        self.assertIn({"t": 10.5, "name": "blip"}, c)

        # 4. Complication: mark at 420+45=465 frames (15.5s) ticks!
        self.assertIn({"t": 15.5, "name": "tick"}, c)

        # 5. Turn: mark at 570+45=615 frames (20.5s) pops!
        self.assertIn({"t": 20.5, "name": "pop"}, c)

        # 6. Payoff: mark at 720+60=780 frames (26.0s) thuds!
        self.assertIn({"t": 26.0, "name": "thud"}, c)

        # 7. Resolution: cut at 870 frames (29.0s) clicks!
        self.assertIn({"t": 29.0, "name": "click"}, c)

        # Verify determinism, ascending time, and minimum gap
        times = [x["t"] for x in c]
        self.assertEqual(times, sorted(times))
        for a, b in zip(c, c[1:]):
            self.assertGreaterEqual(b["t"] - a["t"], sfx.MIN_GAP - 1e-9)

    def test_scene_level_beat_tags(self):
        # Scenes tagged individually with beat jobs
        p = {
            "durationInFrames": 600,
            "transition": "line",
            "scenes": [
                {"type": "hook", "from": 0, "duration": 150, "beat": "promise"},
                {"type": "text", "from": 150, "duration": 150, "beat": {"job": "payoff", "sound_cue": "thud"}, "mark": {"at": 45}},
                {"type": "end", "from": 300, "duration": 180, "beat": "resolution"},
            ]
        }
        c = sfx.cues(p)
        # Promise at t=0
        self.assertEqual(c[0], {"t": 0.0, "name": "whoosh"})
        # Payoff mark at (150+45)/30 = 6.5s thuds
        self.assertIn({"t": 6.5, "name": "thud"}, c)
        # Resolution cut at 300/30 = 10.0s clicks
        self.assertIn({"t": 10.0, "name": "click"}, c)

    def test_sync_modes(self):
        # sync="cut" forces cue to the scene cut
        p_cut = {
            "durationInFrames": 400,
            "transition": "line",
            "scenes": [
                {"type": "hook", "from": 0, "duration": 120},
                {"type": "text", "from": 120, "duration": 150, "beat": {"job": "payoff", "sound_cue": "thud", "sync": "cut"}, "mark": {"at": 30}}
            ]
        }
        c = sfx.cues(p_cut)
        # Cut at 120/30 = 4.0s gets thud, mark at 150/30 = 5.0s stays pop
        self.assertIn({"t": 4.0, "name": "thud"}, c)
        self.assertIn({"t": 5.0, "name": "pop"}, c)

        # sync="mark" keeps cut transition and directs beat cue to mark
        p_mark = {
            "durationInFrames": 400,
            "transition": "line",
            "scenes": [
                {"type": "hook", "from": 0, "duration": 120},
                {"type": "text", "from": 120, "duration": 150, "beat": {"job": "setup", "sound_cue": "click", "sync": "mark"}, "mark": {"at": 30}}
            ]
        }
        c_m = sfx.cues(p_mark)
        self.assertIn({"t": 3.9, "name": "whoosh"}, c_m)  # cut at 4.0 - 0.1 lead
        self.assertIn({"t": 5.0, "name": "click"}, c_m)   # mark at 5.0 gets click


if __name__ == "__main__":
    unittest.main()
