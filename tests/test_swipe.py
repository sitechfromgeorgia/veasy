"""Built for the swipe and the loop (ROADMAP D7, tt_shorts/swipe.py): the voice starts at once and the captions and
anchors move with it, the outro (card | overlay | loop) is a format choice that reaches the props, and QA fails a
render whose frame 0 has no readable hook."""
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from tt_shorts import captions, engine, formats, props, queue, speech, swipe

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = speech.FPS
NARRATION = ("ზელენსკი პუტინს თურქეთში შეხვედრას სთავაზობს. ამის შესახებ მან ინტერვიუში განაცხადა. "
             "სტამბოლში ის ერდოღანს შეხვდა და ლიდერებმა ბევრი საკითხი განიხილეს ერთად. "
             "დეტალები იხილე საიტზე. გამოიწერე არხი.")
STORY = {"id": 1, "category": "world", "date": "2026-11-01T18:38:46Z", "narration": NARRATION,
         "scenes": [{"type": "hook", "at": "ზელენსკი პუტინს", "lines": ["x"]},
                    {"type": "points", "at": "ამის შესახებ", "items": ["ა", "ბ"]},
                    {"type": "where", "at": "სტამბოლში ის", "place": "სტამბოლი"},
                    {"type": "end", "at": "დეტალები იხილე"}]}
HAVE_FFMPEG = shutil.which("ffmpeg") is not None


def words(start=0.9):
    """A synthetic voice: the estimated pace, the first word `start` seconds in."""
    return speech.estimate_words(NARRATION, start=start)


class VoiceStartsAtOnce(unittest.TestCase):
    def test_leading_silence_is_cut_to_at_most_120_ms(self):
        w = words(0.9)
        trim = swipe.lead_trim(w, silence=0.85)  # the track is silent until 0.85 s, the aligner says 0.9 s
        self.assertAlmostEqual(trim, 0.73)
        moved = swipe.shift(w, trim)
        self.assertAlmostEqual(moved[0]["start"], 0.17)  # 0.12 s of silence before the sound, as kept
        for a, b in zip(w, moved):  # every word moves by the same amount: the durations and the order stay
            self.assertAlmostEqual(a["start"] - b["start"], trim, places=3)
            self.assertAlmostEqual(a["end"] - a["start"], b["end"] - b["start"], places=3)
            self.assertEqual(a["text"], b["text"])

    def test_nothing_is_cut_when_the_voice_starts_at_once_or_cant_be_measured(self):
        self.assertEqual(swipe.lead_trim(words(0.1), silence=0.1), 0.0)
        self.assertEqual(swipe.lead_trim(words(0.6), silence=0.0), 0.0)  # sound from the start: a breath, keep it
        self.assertEqual(swipe.lead_trim(words(0.9), silence=None), 0.0)  # no measurement: never guess
        self.assertEqual(swipe.lead_trim([], silence=0.5), 0.0)
        self.assertEqual(swipe.shift(words(), 0.0), words())

    def test_scene_anchors_and_captions_move_with_the_voice(self):
        w = words(0.9)
        trim = swipe.lead_trim(w, silence=0.9)
        before, after = speech.scene_frames(STORY, w), speech.scene_frames(STORY, swipe.shift(w, trim))
        self.assertEqual(after[0], 0)
        for a, b in zip(before[1:], after[1:]):
            self.assertLessEqual(abs((a - b) - trim * FPS), 1)  # one frame of rounding at most
        cap_a, cap_b = captions.layout(w, "page"), captions.layout(swipe.shift(w, trim), "page")
        for pa, pb in zip(cap_a["pages"], cap_b["pages"]):
            self.assertAlmostEqual(pa["start"] - pb["start"], trim, places=2)
        self.assertEqual([l["words"][0]["text"] for l in cap_a["lines"]], [l["words"][0]["text"] for l in cap_b["lines"]])

    def test_props_carry_the_trim_and_the_moved_timings(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            audio = pathlib.Path(home) / "voice.mp3"
            audio.write_bytes(b"fake")
            story = pathlib.Path(home) / "s.json"
            story.write_text(json.dumps(STORY, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(speech, "voice", return_value=(audio, words(0.9))), \
                    mock.patch.object(swipe, "leading_silence", return_value=0.85):
                _, p = props.build(str(story), "editorial", "edge", music="off")
            self.assertAlmostEqual(p["voiceTrim"], 0.73)
            self.assertAlmostEqual(p["words"][0]["start"], 0.17)
            self.assertLessEqual(p["captions"]["pages"][0]["start"], 0.12)
            with mock.patch.object(swipe, "leading_silence") as never:  # silent: no track, nothing to trim
                _, p = props.build(str(story), "editorial", "silent", music="off")
                never.assert_not_called()
            self.assertEqual(p["voiceTrim"], 0.0)

    def test_the_mix_cuts_the_same_seconds_from_the_track(self):
        p = {"durationInFrames": 900, "voice": "voice.wav", "music": "world-1.m4a", "voiceTrim": 0.73, "outro": "card"}
        with mock.patch.object(subprocess, "run") as run:
            props.mix_audio(pathlib.Path("/w"), p, "raw.mp4", "out.mp4")
        graph = run.call_args.args[0][run.call_args.args[0].index("-filter_complex") + 1]
        voice = graph.split(";")[0]
        self.assertTrue(voice.startswith("[1:a]atrim=start=0.730,asetpts=PTS-STARTPTS,"), voice)
        self.assertIn("afade=t=in:d=1.2", graph)  # the card keeps its music fades
        with mock.patch.object(subprocess, "run") as run:
            props.mix_audio(pathlib.Path("/w"), {**p, "voiceTrim": 0}, "raw.mp4", "out.mp4")
        self.assertNotIn("atrim=start", run.call_args.args[0][run.call_args.args[0].index("-filter_complex") + 1])

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg")
    def test_leading_silence_is_measured_on_the_track(self):
        with tempfile.TemporaryDirectory() as d:
            wav = pathlib.Path(d) / "v.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.6", "-f", "lavfi",
                            "-i", "sine=f=220:r=24000:d=1", "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", str(wav)],
                           check=True)
            self.assertAlmostEqual(swipe.leading_silence(wav), 0.6, delta=0.03)
            loud = pathlib.Path(d) / "s.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=220:r=24000:d=1", str(loud)], check=True)
            self.assertEqual(swipe.leading_silence(loud), 0.0)
            self.assertIsNone(swipe.leading_silence(pathlib.Path(d) / "missing.wav"))


class Outro(unittest.TestCase):
    def test_card_is_the_default_and_keeps_the_end_card(self):
        self.assertEqual(formats.get("news")["outro"], "card")
        w = words(0.3)
        shown, marks, chip = swipe.plan(STORY, w)
        self.assertEqual([s["type"] for s in shown], ["hook", "points", "where", "end"])
        self.assertEqual(marks, speech.scene_frames(STORY, w))  # exactly as before
        self.assertIsNone(chip)

    def test_overlay_drops_the_end_card_and_brings_the_chip_with_its_words(self):
        w = words(0.3)
        shown, marks, chip = swipe.plan(STORY, w, "overlay")
        self.assertEqual([s["type"] for s in shown], ["hook", "points", "where"])
        self.assertEqual(len(marks), len(shown) + 1)
        self.assertEqual(marks[-1], round((w[-1]["end"] + swipe.HOLD["overlay"]) * FPS))  # a shorter tail
        end_words = speech.anchor(w, "დეტალები იხილე", 0)[0]
        self.assertEqual(chip, min(round((end_words - 0.08) * FPS), marks[-1] - round(swipe.CHIP_SECONDS * FPS)))
        self.assertGreaterEqual(marks[-1] - chip, swipe.CHIP_SECONDS * FPS)  # on screen long enough to read
        self.assertGreater(chip, marks[-2])  # the last scene is in before the chip

    def test_loop_has_the_shortest_tail_and_a_story_without_an_end_scene_still_gets_the_chip(self):
        w = words(0.3)
        _, marks, _ = swipe.plan(STORY, w, "loop")
        self.assertEqual(marks[-1], round((w[-1]["end"] + swipe.HOLD["loop"]) * FPS))
        self.assertLess(swipe.HOLD["loop"], swipe.HOLD["overlay"])
        self.assertLess(swipe.HOLD["overlay"], swipe.HOLD["card"])
        bare = {**STORY, "scenes": STORY["scenes"][:-1]}
        shown, marks, chip = swipe.plan(bare, w, "overlay")
        self.assertEqual(len(shown), 3)
        self.assertEqual(chip, marks[-1] - round(swipe.CHIP_SECONDS * FPS))
        with self.assertRaises(ValueError):
            swipe.plan(STORY, w, "fade")

    def test_a_loop_keeps_the_music_steady_to_the_last_frame(self):
        p = {"durationInFrames": 900, "voice": None, "music": "world-1.m4a", "outro": "loop"}
        with mock.patch.object(subprocess, "run") as run:
            props.mix_audio(pathlib.Path("/w"), p, "raw.mp4", "out.mp4")
        graph = run.call_args.args[0][run.call_args.args[0].index("-filter_complex") + 1]
        self.assertIn("afade=t=in:d=0.03,afade=t=out:st=29.970:d=0.03", graph)  # a de-click, not a fade
        self.assertEqual(swipe.music_fades("overlay"), (1.2, 2.5))

    def test_a_format_and_a_render_can_choose_it(self):
        self.assertEqual(formats.OUTROS, ("card", "overlay", "loop"))
        self.assertEqual(formats.get("news", outro="loop")["outro"], "loop")
        with self.assertRaises(formats.FormatError):
            formats.get("news", outro="fade")
        self.assertEqual(set(engine.options()["outros"]), set(formats.OUTROS))
        with tempfile.TemporaryDirectory() as d:  # a show can fix it in its JSON
            (pathlib.Path(d) / "loopy.json").write_text('{"label": "x", "outro": "overlay"}', encoding="utf-8")
            with mock.patch.object(formats, "DIR", pathlib.Path(d)):
                self.assertEqual(formats.get("loopy")["outro"], "overlay")

    def test_queue_overrides_carry_it(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            job, created = queue.add(story=str(ROOT / "stories" / "24725.json"), overrides={"outro": "loop"})
            self.assertTrue(created)
            self.assertEqual(formats.get(job["format"], **job["overrides"])["outro"], "loop")
            with self.assertRaises(formats.FormatError):
                queue.add(story=str(ROOT / "stories" / "24725.json"), overrides={"outro": "fade"})

    def test_the_cli_and_the_plugin_offer_it(self):
        with mock.patch.object(engine, "still", side_effect=lambda a: a.outro) as still:
            self.assertEqual(engine.main(["still", "x.json", "--outro", "overlay"]), "overlay")
            still.assert_called_once()
        from tests.test_plugin import load_plugin
        plugin = load_plugin()
        self.assertEqual(plugin.CHOICE_PROPS["outro"]["enum"], list(formats.OUTROS))
        self.assertIn("outro", plugin.CHOICES)
        self.assertIn("outro", plugin.TOOLS["veasy_queue"][0]["properties"])

    def test_props_carry_it(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict("os.environ", {"VEASY_HOME": home}):
            story = str(ROOT / "stories" / "24725.json")
            _, card = props.build(story, "editorial", "silent", music="off")
            self.assertEqual((card["outro"], card["outroFrom"], card["scenes"][-1]["type"]), ("card", None, "end"))
            for outro in ("overlay", "loop"):
                _, p = props.build(story, "editorial", "silent", music="off", outro=outro)
                self.assertEqual(p["outro"], outro)
                self.assertNotIn("end", [s["type"] for s in p["scenes"]])
                last = p["scenes"][-1]
                self.assertEqual(last["from"] + last["duration"], p["durationInFrames"])  # the last scene runs to the end
                self.assertLess(p["durationInFrames"], card["durationInFrames"])  # no dead tail
                self.assertTrue(last["from"] < p["outroFrom"] <= p["durationInFrames"] - swipe.CHIP_SECONDS * FPS)

    def test_remotion_agrees(self):  # the chip's place is the safe zone's; the loop's length is swipe's
        src = (ROOT / "remotion" / "src" / "outro.tsx").read_text(encoding="utf-8")
        self.assertEqual(int(re.search(r"export const LOOP = (\d+);", src).group(1)), round(swipe.LOOP_SECONDS * FPS))
        self.assertGreaterEqual(int(re.search(r"CHIP_BOTTOM = SCENE_BOTTOM - (\d+);", src).group(1)), 0)  # above the captions
        self.assertIn("RAIL_X - left", src)  # left of the like/share rail
        types = (ROOT / "remotion" / "src" / "types.ts").read_text(encoding="utf-8")
        self.assertIn('export type Outro = "card" | "overlay" | "loop";', types)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg")
class OpeningFrame(unittest.TestCase):
    def clip(self, d, vf):
        out = pathlib.Path(d) / "c.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x05080F:s=1080x1920:r=30:d=0.4",
                        "-vf", vf, "-pix_fmt", "yuv420p", str(out)], check=True)
        return out

    def test_an_empty_opening_is_a_problem(self):
        with tempfile.TemporaryDirectory() as d:
            empty = self.clip(d, "null")
            self.assertEqual(swipe.opening_ink(empty), 0.0)
            self.assertIn("frame 0", " ".join(swipe.opening_problems(empty)))

    def test_a_hook_on_screen_at_frame_0_passes(self):
        with tempfile.TemporaryDirectory() as d:  # three ink lines in the hook band, as a hook draws them
            hook = self.clip(d, ",".join(f"drawbox=x=64:y={300 + k * 190}:w=800:h=120:color=0xF8FAFC:t=fill" for k in range(3)))
            self.assertGreater(swipe.opening_ink(hook), swipe.INK_SHARE)
            self.assertEqual(swipe.opening_problems(hook), [])

    def test_only_frame_0_counts_and_faded_ink_is_not_ink(self):
        with tempfile.TemporaryDirectory() as d:  # the old opening: nothing at frame 0, the hook a few frames later
            late = self.clip(d, "drawbox=x=64:y=300:w=800:h=500:color=0xF8FAFC:t=fill:enable='gte(n,3)'")
            self.assertTrue(swipe.opening_problems(late))
        with tempfile.TemporaryDirectory() as d:  # text at a third of its opacity, mid fade-in
            faded = self.clip(d, "drawbox=x=64:y=300:w=800:h=500:color=0x55585E:t=fill")
            self.assertTrue(swipe.opening_problems(faded))
        with tempfile.TemporaryDirectory() as d:  # ink outside the hook band (the header, the ticker) doesn't count
            outside = self.clip(d, "drawbox=x=0:y=1580:w=1080:h=300:color=0xF8FAFC:t=fill")
            self.assertTrue(swipe.opening_problems(outside))

    def test_qa_reports_it(self):
        with tempfile.TemporaryDirectory() as d:
            result = engine.qa_file(self.clip(d, "null"), formats.get("news"))
            self.assertEqual(result["opening_ink"], 0.0)
            self.assertTrue(any(p.startswith("frame 0:") for p in result["problems"]))


if __name__ == "__main__":
    unittest.main()
