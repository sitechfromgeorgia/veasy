"""The layout probe's rules on synthetic boxes, and how a probe problem reaches the render, the queue and qa."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tt_shorts import probe

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = {"400": "loaded", "500": "loaded", "600": "loaded", "700": "loaded"}


def text(t="ტექსტი", box=(100, 400, 300, 60), region="scene", **kw):
    return {"region": region, "text": t, "box": list(box), "size": kw.pop("size", 60), "weight": kw.pop("weight", "700"),
            "family": kw.pop("family", "Brand, sans-serif"), "opacity": kw.pop("opacity", 1), "svg": False,
            "overflow": kw.pop("overflow", None), "clipOk": kw.pop("clipOk", False)}


def report(*texts, frame=100, scene=1, typ="stat", fonts=FONTS, early=FONTS):
    return {"frame": frame, "scene": scene, "type": typ, "fonts": fonts, "fontsAtRender": early, "texts": list(texts)}


def rules_of(rep, cmaps=None):
    return [i["rule"] for i in probe.rules(rep, cmaps)]


def public_dir():
    """A render's public dir with the brand font, as props.build leaves it."""
    tmp = tempfile.mkdtemp()
    (pathlib.Path(tmp) / "fonts").mkdir()
    for w, name in (("400", "regular.d8b411bacd"), ("700", "bold.ed7553cea8")):
        src = ROOT / "assets" / "fonts" / f"firago-{name}.woff2"
        (pathlib.Path(tmp) / "fonts" / f"brand-{w}.woff2").write_bytes(src.read_bytes())
    return tmp


class Constants(unittest.TestCase):
    def test_bands_come_from_brand_ts_and_match_the_rules(self):  # CLAUDE.md: the safe zone
        c = probe.constants()
        self.assertEqual((c["W"], c["H"]), (1080, 1920))
        self.assertEqual((c["SCENE_TOP"], c["SCENE_BOTTOM"], c["CAPTION_BOTTOM"]), (248, 1380, 1552))
        self.assertEqual((c["RAIL_X"], c["RAIL_Y"]), (940, 1100))

    def test_settled_frames_are_inside_each_scene_before_its_exit(self):
        scenes = [{"from": 0, "duration": 100}, {"from": 100, "duration": 20}, {"from": 120, "duration": 90}]
        f = probe.settled(scenes)
        self.assertEqual(f[0], 100 - probe.EXIT - 2)
        self.assertTrue(100 <= f[1] < 120 and f[1] >= 100 + 12)  # a short scene: after its entrance
        self.assertEqual(f[2], 209)  # the last scene has no exit: its last frame


class Rules(unittest.TestCase):
    def test_a_clean_frame_has_no_issues(self):
        rep = report(text(), text("2 წყარო", (64, 1148, 300, 46), size=38),
                     text("სიტყვა", (220, 1400, 600, 72), region="captions"),
                     text("SiTech-ის პროექტი · sitech.ge", (620, 1833, 396, 33), region="footer", size=28))
        self.assertEqual(probe.rules(rep), [])

    def test_scene_text_stays_in_the_scene_band(self):
        self.assertEqual(rules_of(report(text(box=(100, 1340, 300, 60)))), ["band"])  # ends at 1400 > 1380
        self.assertEqual(rules_of(report(text(box=(100, 200, 300, 60)))), ["band"])  # starts above 248
        self.assertEqual(rules_of(report(text(box=(100, 1320, 300, 61)))), [])  # 1381: within the tolerance

    def test_nothing_right_of_the_rail_below_1100(self):
        self.assertEqual(rules_of(report(text(box=(700, 1150, 260, 60)))), ["rail"])
        self.assertEqual(rules_of(report(text(box=(700, 1000, 300, 60)))), [])  # above y=1100 the full width is free
        self.assertEqual(rules_of(report(text(box=(300, 1400, 660, 72), region="captions"))), ["rail"])
        self.assertEqual(rules_of(report(text(box=(400, 1300, 600, 40), region="card", size=30))), ["rail"])
        # the footer's pack line sits bottom right by design (the brand's chrome)
        self.assertEqual(rules_of(report(text(box=(620, 1833, 396, 33), region="footer", size=28))), [])

    def test_captions_end_at_their_band(self):
        self.assertEqual(rules_of(report(text(box=(200, 1500, 500, 72), region="captions"))), ["captions"])

    def test_no_text_outside_the_frame(self):
        self.assertEqual(rules_of(report(text(box=(-30, 80, 200, 50), region="header", size=40))), ["frame"])
        self.assertEqual(rules_of(report(text(box=(900, 500, 300, 60)))), ["frame"])

    def test_overflow_across_always_down_beyond_the_line_box(self):
        over = {"x": 24, "y": 0, "xIn": "div", "yIn": "", "clipped": True}
        self.assertEqual(rules_of(report(text(overflow=over))), ["overflow"])
        tight = {"x": 0, "y": 6, "xIn": "", "yIn": "div", "clipped": False}  # a glyph a little past a tight line
        self.assertEqual(rules_of(report(text(size=56, overflow=tight))), [])
        tall = {"x": 0, "y": 78, "xIn": "", "yIn": "div[scene]", "clipped": False}  # a line on the card's footer
        self.assertEqual(rules_of(report(text(size=44, overflow=tall))), ["overflow"])
        self.assertEqual(rules_of(report(text(overflow=over, clipOk=True))), [])  # roll captions clip by design

    def test_the_brand_font_and_its_glyphs(self):
        self.assertEqual(rules_of(report(text(family="Times New Roman"))), ["font"])
        self.assertEqual(rules_of(report(text(weight="700"), fonts={**FONTS, "700": "error"})), ["font"])
        cmaps = {w: {ord(c) for c in "ტექსტი ★"} for w in FONTS}
        self.assertEqual(rules_of(report(text("ტექსტი ★")), cmaps), [])
        issues = probe.rules(report(text("ტექსტი 😀")), cmaps)
        self.assertEqual([i["rule"] for i in issues], ["glyph"])
        self.assertIn("U+1F600", issues[0]["detail"])

    def test_a_frame_laid_out_before_the_font_loaded(self):  # measure()/fitSize got a fallback font's sizes
        issues = probe.rules(report(text(), early={"400": "loaded"}))
        self.assertEqual([i["rule"] for i in issues], ["font"])
        self.assertIn("500, 600, 700", issues[0]["detail"])

    def test_text_shrunk_below_the_minimum(self):
        self.assertEqual(rules_of(report(text(size=18))), ["size"])
        self.assertEqual(rules_of(report(text(size=24))), [])  # a drawing's label in a card
        self.assertEqual(rules_of(report(text(size=30, region="captions"))), ["size"])
        self.assertEqual(rules_of(report(text(size=30, region="captions", opacity=0.45))), [])  # a fading roll line

    def test_missing_glyphs_skip_spaces_and_format_characters(self):
        self.assertEqual(probe.missing_glyphs("ა ბ​გ ", {ord("ა"), ord("ბ"), ord("გ")}), [])
        self.assertEqual(probe.missing_glyphs("აxx", {ord("ა")}), ["x"])

    def test_the_brand_font_has_what_the_videos_write(self):
        cmaps = probe.cmaps_for(public_dir())
        line = "ზელენსკი „ციტატა“ 6 400 · 22:00 -> 10:00, 1,5% SiTech"
        self.assertEqual(probe.missing_glyphs(line, cmaps["700"]), [])
        self.assertEqual(probe.missing_glyphs("😀", cmaps["400"]), ["😀"])
        # the shipped FiraGO subset has no lari sign, though normalize_ka speaks "₾5": on screen it would be another
        # font's glyph, so the probe flags it
        self.assertEqual(probe.missing_glyphs("5 ₾", cmaps["700"]), ["₾"])


class Reports(unittest.TestCase):
    def test_chrome_issues_are_reported_once_scene_issues_per_scene(self):
        bad_footer = text("x", (1000, 1833, 120, 33), region="footer", size=28)
        bad_scene = text("long", (700, 1150, 260, 60))
        reps = [report(bad_footer, bad_scene, frame=100, scene=1), report(bad_footer, bad_scene, frame=200, scene=2)]
        strings, issues = probe.problems(reps)
        self.assertEqual(sum(1 for s in strings if s.startswith("probe frame: footer")), 1)
        self.assertEqual(sum(1 for s in strings if s.startswith("probe rail: scene")), 2)
        self.assertTrue(all(s.startswith("probe ") for s in strings))  # failures.rule_of reads "probe <rule>"

    def test_a_frame_without_a_report_is_a_problem(self):
        tmp = public_dir()
        rows = [{"job": 0, "frame": 10, "file": None, "probe": report(text(), frame=10)}]
        r = probe.judge(rows, tmp, [10, 20])
        self.assertTrue(any("no layout report for frames [20]" in p for p in r["problems"]), r["problems"])
        r = probe.judge([{"job": 0, "error": "Error: boom\n at x"}], tmp, [10])
        self.assertEqual(r["problems"], ["probe error: Error: boom"])

    def test_looks(self):
        story = {"category": "politics"}
        self.assertEqual(probe.looks("all", story), ["editorial", "kinetic", "cards"])
        self.assertEqual(probe.looks("kinetic,cards", story), ["kinetic", "cards"])
        self.assertEqual(len(probe.looks("auto", story)), 1)
        with self.assertRaises(ValueError):
            probe.looks("neon", story)


def _touch(path):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).touch()


class Wiring(unittest.TestCase):
    """A probe problem holds the video: render_story reports it, qa repeats it, the queue holds the job."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def _render(self, checked=None, boom=None):
        from tt_shorts import engine, formats, props
        work = pathlib.Path(self.tmp.name) / "work"
        work.mkdir(exist_ok=True)
        p = {"durationInFrames": 900, "variant": "cards", "style": {}, "transition": "line", "music": None,
             "scenes": [{"type": "hook"}]}
        found = {"problems": ["probe rail: scene 0 (hook) frame 80: „x“ reaches x=982 below y=1100"], "issues": [],
                 "frames": [80], "texts": 9, "seconds": 1.0} if checked is None else checked
        with mock.patch.object(props, "build", return_value=(work, p)), \
                mock.patch.object(props, "render_video", side_effect=lambda w, pr, t: _touch(t)), \
                mock.patch.object(probe, "check_work", side_effect=boom or (lambda *a, **k: found)):
            return engine.render_story(ROOT / "stories" / "24725.json", formats.get("news"), "silent",
                                       pathlib.Path(self.tmp.name) / "out" / "x.mp4")

    def test_render_story_reports_the_probe(self):
        r = self._render()
        self.assertTrue(any(p.startswith("probe rail:") for p in r["problems"]))
        side = json.loads((pathlib.Path(self.tmp.name) / "out" / "x.json").read_text(encoding="utf-8"))
        self.assertEqual(side["probe"]["problems"], r["probe"]["problems"])

    def test_a_probe_that_cannot_run_holds_the_video(self):
        r = self._render(boom=probe.ProbeError("node: not found"))
        self.assertEqual(r["problems"], ["probe error: node: not found"])

    def test_the_probe_can_be_turned_off(self):
        with mock.patch.dict(os.environ, {"VEASY_PROBE": "0"}):
            r = self._render()
        self.assertEqual((r["problems"], r["probe"]), ([], None))

    def test_qa_repeats_the_probe_problems_of_the_render(self):
        from tt_shorts import engine, formats
        self._render()
        mp4 = pathlib.Path(self.tmp.name) / "out" / "x.mp4"
        info = {"format": {"duration": "30"}, "streams": [{"codec_type": "video", "width": 1080, "height": 1920},
                                                         {"codec_type": "audio"}]}
        with mock.patch.object(engine, "_probe", return_value=info), \
                mock.patch.object(engine, "_loudness", return_value={"I": -16.0}), \
                mock.patch.object(engine.subprocess, "run"):
            q = engine.qa_file(mp4, formats.get("news"))
        self.assertEqual([p for p in q["problems"] if p.startswith("probe")], q["probe"]["problems"])
        self.assertTrue(q["problems"])

    def test_the_queue_holds_a_video_the_probe_flagged_and_remembers_it(self):
        from tt_shorts import engine, failures, queue
        job, _ = queue.add(story=str(ROOT / "stories" / "24725.json"))
        bad = {"file": "/x.mp4", "problems": ["probe overflow: scene 3 (where) frame 778: „x“ runs past its box"]}
        with mock.patch.object(engine, "render_story", return_value=bad), \
                mock.patch.object(engine, "check_story", return_value=[]), \
                mock.patch.object(engine, "qa_file", return_value={"problems": []}):
            queue.run(max_jobs=1, engine="gemini")
        j = queue.get(job["id"])
        self.assertEqual((j["state"], j["error_class"]), ("held", "qa"))
        self.assertEqual(failures.top()[0]["rule"], "probe:overflow")


if __name__ == "__main__":
    unittest.main()
