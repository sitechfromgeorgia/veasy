"""The music loop's start, chosen so a heavy hit lands on the film's main moment (music_hits.py, props.mix_audio):
the hit lands within TOLERANCE on three stories, measured on the mixed audio, and the bed's level is unchanged."""
import pathlib
import re
import subprocess
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np
from scipy.signal import fftconvolve

from tt_shorts import music_hits, props, sfx

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = 30


def film(**more):
    return {"durationInFrames": 30 * FPS, "transition": "line", "outroFrom": None, "outro": "card", "voice": None,
            "music": "politics-1.m4a", "scenes": [
                {"type": "hook", "from": 0, "duration": 150},
                {"type": "text", "from": 150, "duration": 150},
                {"type": "end", "from": 300, "duration": 600}], **more}


def three_stories():
    """A big number, an idea's turn (the narration says the object), a hook's mark: three different moments."""
    number = film()
    number["scenes"][1] = {"type": "stat", "from": 150, "duration": 150}
    idea = film(words=[{"text": "ქალაქში", "start": 1.0, "end": 1.4}, {"text": "გასაღებს", "start": 13.37, "end": 13.9}])
    hook = film()
    hook["scenes"][0]["mark"] = {"at": 83}
    return [(number, None), (idea, {"object": "გასაღები", "device": "x"}), (hook, None)]


def decode(path, seconds=None):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "8000", "-f", "s16le"]
    cmd += ["-t", str(seconds)] if seconds else []
    raw = subprocess.run([*cmd, "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32767


def lufs(path):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True,
                         text=True).stderr
    return float(re.findall(r"I:\s+(-?\d+\.\d+) LUFS", out)[-1])


class Grid(unittest.TestCase):
    def test_the_hits_are_the_composers_own(self):
        length, bar, beat = music_hits.grid("politics-1.m4a")
        self.assertAlmostEqual(bar, 4 * 60 / 94)
        self.assertEqual(music_hits.heavy("politics-1")[:3], [0.0, round(bar, 4), round(2 * bar, 4)])
        self.assertIn(round(2 * beat, 4), music_hits.hits("politics-1"))  # its kick on beat 3
        self.assertNotIn(round(2 * beat, 4), music_hits.hits("crime-1"))  # crime has no kick: only the bar openings
        self.assertEqual(music_hits.offset("nothing.m4a", 9.0), 0.0)  # an unknown bed is left alone
        self.assertEqual(music_hits.offset("politics-1.m4a", None), 0.0)

    def test_the_graph_trims_the_looped_stream_and_never_seeks_it(self):
        with tempfile.TemporaryDirectory() as d:
            work = pathlib.Path(d)
            (work / "public").mkdir()
            p = film(sfxMoment={"t": 9.0, "why": "number"})
            with mock.patch.object(subprocess, "run") as run:
                props.mix_audio(work, p, work / "raw.mp4", work / "out.mp4")
            cmd = run.call_args[0][0]
            graph = cmd[cmd.index("-filter_complex") + 1]
            self.assertNotIn("-ss", cmd)  # -ss on a -stream_loop input would restart every later loop at the offset
            self.assertIn(f"atrim=start={music_hits.offset('politics-1.m4a', 9.0):.3f}", graph)
            with mock.patch.object(subprocess, "run") as run:
                props.mix_audio(work, film(), work / "raw.mp4", work / "out.mp4")
            self.assertNotIn("atrim=start", run.call_args[0][0][run.call_args[0][0].index("-filter_complex") + 1])


class Audio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.work = pathlib.Path(cls.tmp.name)
        (cls.work / "public").mkdir()
        c = music_hits.composer()
        mix, _ = c.compose(c.variation(c.PIECES["politics"], c.VARIANTS[0]))  # about 12 s of numpy
        wav = cls.work / "politics-1.wav"
        c.write(wav, mix)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-af", "loudnorm=I=-16:TP=-1.5:LRA=4:linear=true",
                        "-c:a", "aac", "-b:a", "128k", str(cls.work / "public" / "politics-1.m4a")], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=30:r=30",
                        "-pix_fmt", "yuv420p", str(cls.work / "raw.mp4")], check=True)
        cls.loop = decode(cls.work / "public" / "politics-1.m4a")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def mixed(self, p, name):
        return props.mix_audio(self.work, p, self.work / "raw.mp4", self.work / name)

    def test_a_heavy_hit_lands_on_the_main_moment_within_tolerance_on_three_stories(self):
        sr, length, bar = 8000, music_hits.grid("politics-1")[0], music_hits.grid("politics-1")[1]
        for p, concept in three_stories():
            m = sfx.moment(p, concept)
            out = self.mixed({**p, "sfxMoment": m}, f"{m['why']}.mp4")
            x = decode(out, 12)[int(3 * sr):int(11 * sr)]  # past the fade-in, before the fade-out
            # where in the loop the film's audio was taken from: the lag that matches it best (the real mix, measured)
            c = fftconvolve(np.tile(self.loop, 2), x[::-1], mode="valid")
            start = (int(np.argmax(c)) / sr - 3.0) % length  # loop time of film time 0
            landed = min(((h - start) % length for h in music_hits.heavy("politics-1")), key=lambda t: abs(t - m["t"]))
            self.assertLessEqual(abs(landed - m["t"]), music_hits.TOLERANCE, f"{m} landed at {landed:.3f}")
        self.assertEqual({sfx.moment(p, c)["why"] for p, c in three_stories()}, {"number", "idea", "hook"})

    def test_the_offset_does_not_change_the_beds_level(self):
        plain = lufs(self.mixed(film(), "plain.mp4"))
        shifted = lufs(self.mixed(film(sfxMoment={"t": 13.37, "why": "idea"}), "shifted.mp4"))
        self.assertLessEqual(abs(plain - shifted), 0.3, f"{plain} LUFS vs {shifted} LUFS")


if __name__ == "__main__":
    unittest.main()
