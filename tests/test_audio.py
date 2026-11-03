"""Tests for tools.pluck, tools.sampler, and tools.compose_music."""
import numpy as np
import unittest

from tools import compose_music, pluck, sampler


class TestPluck(unittest.TestCase):
    def test_midi_and_hz_pitch_conversion(self):
        self.assertEqual(pluck.midi("C4"), 60.0)
        self.assertEqual(pluck.midi("A4"), 69.0)
        self.assertEqual(pluck.midi("D4"), 62.0)
        self.assertAlmostEqual(pluck.hz("A4"), 440.0, places=2)
        self.assertAlmostEqual(pluck.hz(69), 440.0, places=2)

    def test_panduri_synthesis(self):
        snd = pluck.pluck("panduri", "D4", dur=1.0, vel=0.7)
        self.assertIsInstance(snd, np.ndarray)
        self.assertEqual(snd.dtype, np.float32)
        self.assertEqual(len(snd), int(1.0 * pluck.SR))
        self.assertTrue(np.all(np.isfinite(snd)))
        self.assertLessEqual(np.max(np.abs(snd)), 1.0)
        self.assertGreater(np.max(np.abs(snd)), 0.05)

    def test_chonguri_synthesis(self):
        snd = pluck.pluck("chonguri", "G4", dur=1.0, vel=0.7)
        self.assertIsInstance(snd, np.ndarray)
        self.assertEqual(snd.dtype, np.float32)
        self.assertEqual(len(snd), int(1.0 * pluck.SR))
        self.assertTrue(np.all(np.isfinite(snd)))
        self.assertLessEqual(np.max(np.abs(snd)), 1.0)
        self.assertGreater(np.max(np.abs(snd)), 0.05)

    def test_strum_chord(self):
        chord = ["D4", "G4", "A4"]
        snd = pluck.strum("panduri", chord, dur=1.5, speed=0.03, vel=0.6)
        self.assertEqual(len(snd), int(1.5 * pluck.SR))
        self.assertTrue(np.all(np.isfinite(snd)))
        self.assertGreater(np.max(np.abs(snd)), 0.05)

    def test_panduri_loop(self):
        loop = pluck.panduri_loop(bpm=100, bars=2, root="D4")
        self.assertIsInstance(loop, np.ndarray)
        self.assertEqual(loop.dtype, np.float32)
        self.assertGreater(len(loop), 0)
        self.assertTrue(np.all(np.isfinite(loop)))
        self.assertLessEqual(np.max(np.abs(loop)), 1.0)


class TestSampler(unittest.TestCase):
    def test_note_synthesis_fallbacks(self):
        for inst in ("piano", "violins", "flute", "trumpet"):
            snd = sampler.note(inst, "C4", dur=0.5, vel=0.6)
            self.assertEqual(snd.dtype, np.float32)
            self.assertEqual(len(snd), int(0.5 * sampler.SR))
            self.assertTrue(np.all(np.isfinite(snd)))
            self.assertGreater(np.max(np.abs(snd)), 0.01)

    def test_note_routes_to_pluck_for_folk_instruments(self):
        snd = sampler.note("panduri", "D4", dur=0.5, vel=0.6)
        self.assertEqual(snd.dtype, np.float32)
        self.assertEqual(len(snd), int(0.5 * sampler.SR))
        self.assertTrue(np.all(np.isfinite(snd)))

    def test_percussion_hits(self):
        for h in ("snare", "kick", "hihat", "woodblock"):
            snd = sampler.hit(h, vel=0.7)
            self.assertEqual(snd.dtype, np.float32)
            self.assertGreater(len(snd), 0)
            self.assertTrue(np.all(np.isfinite(snd)))

    def test_render_multi_event(self):
        events = [
            (0.0, "piano", "C4", 0.5, 0.7, -0.2),
            (0.2, "violins", "G4", 0.5, 0.6, 0.2),
        ]
        mix = sampler.render(events, total_dur=1.0)
        self.assertEqual(mix.shape, (2, int(1.0 * sampler.SR)))
        self.assertTrue(np.all(np.isfinite(mix)))
        self.assertGreater(np.max(np.abs(mix)), 0.01)


class TestComposeWithPluckAndSampler(unittest.TestCase):
    def test_compose_culture_with_panduri(self):
        piece = dict(compose_music.PIECES["culture"])
        piece["pluck"] = "panduri"
        # Test 1 bar composing
        piece["prog"] = piece["prog"][:2]
        mix, bar = compose_music.compose(piece)
        self.assertEqual(mix.ndim, 2)
        self.assertEqual(mix.shape[0], 2)
        self.assertTrue(np.all(np.isfinite(mix)))
        spread = compose_music.bar_spread_db(mix, bar)
        # Owner sound law: spread must stay <= 1.0 dB
        self.assertLessEqual(spread, 1.0)

    def test_compose_tech_with_sampled_piano(self):
        piece = dict(compose_music.PIECES["tech"])
        piece["sample"] = "piano"
        piece["prog"] = piece["prog"][:2]
        mix, bar = compose_music.compose(piece)
        self.assertEqual(mix.ndim, 2)
        self.assertTrue(np.all(np.isfinite(mix)))
        spread = compose_music.bar_spread_db(mix, bar)
        self.assertLessEqual(spread, 1.0)


if __name__ == "__main__":
    unittest.main()
