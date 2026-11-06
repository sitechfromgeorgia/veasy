"""Plates: the tone line, the refusals, the cache, the ledger. One real bake (quarter scale, one second) is shared."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from tt_shorts import brand as packs
from tt_shorts import plates, store

TOOLS = bool(plates.node() and subprocess.run([plates.ffmpeg(), "-version"], capture_output=True).returncode == 0
             and (plates.PLATES / "node_modules").is_dir())
LINES = [(c, i) for c, i in plates.palettes()]


def ramp_frame():
    """A 1024x64 grey frame: every level 0-255 four columns wide, plus smooth gradients (where banding shows)."""
    row = bytes(min(255, x // 4) for x in range(1024))
    smooth = bytes(int(x * 255 / 1023) for x in range(1024))
    return (row * 32 + smooth * 32), 1024, 64


class Tone(unittest.TestCase):
    def test_lines_cover_both_packs_and_both_themes(self):
        who = {w for ws in plates.palettes().values() for w in ws}
        for pack in ("tbilisi-today", "sitech"):
            self.assertIn(f"{pack}/dark", who)
            self.assertIn(f"{pack}/light", who)

    def test_lut_points_lie_on_the_line(self):
        for canvas, ink in LINES:
            c, i = plates.hex_rgb(canvas), plates.hex_rgb(ink)
            self.assertEqual(plates.line_point(c, i, 0), c)
            self.assertEqual(plates.line_point(c, i, 255), i)

    @unittest.skipUnless(TOOLS, "ffmpeg needed")
    def test_mapped_frame_holds_only_colours_on_the_line(self):
        raw, w, h = ramp_frame()
        for canvas, ink in LINES:
            c, i = plates.hex_rgb(canvas), plates.hex_rgb(ink)
            vf = plates.tone_filter(c, i).split(",scale=")[0]  # up to the lookup: the colours the codec then carries
            r = subprocess.run([plates.ffmpeg(), "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray",
                                "-s", f"{w}x{h}", "-i", "-", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               input=raw, capture_output=True)
            self.assertEqual(r.returncode, 0)
            stats = plates.line_stats(r.stdout, c, i)
            self.assertLessEqual(stats["max"], 3 ** 0.5 / 2 + 1e-9, (canvas, ink, stats))
            self.assertLessEqual(stats["colours"], 256)
            px = r.stdout[:3]  # first pixel is grey 0: the canvas itself
            self.assertEqual(tuple(px), c)

    @unittest.skipUnless(TOOLS, "ffmpeg needed")
    def test_dither_stays_on_the_line_in_a_smooth_gradient(self):
        # gradfun dithers the grey before the colour is assigned: neighbouring levels only, never another channel's noise
        raw, w, h = ramp_frame()
        c, i = plates.hex_rgb("#05080F"), plates.hex_rgb("#F8FAFC")
        vf = plates.tone_filter(c, i).split(",scale=")[0]
        r = subprocess.run([plates.ffmpeg(), "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s",
                            f"{w}x{h}", "-i", "-", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           input=raw, capture_output=True)
        pts = {tuple(plates.line_point(c, i, g)) for g in range(256)}
        seen = {tuple(r.stdout[k:k + 3]) for k in range(0, len(r.stdout), 3)}
        self.assertTrue(seen <= pts, "a pixel left the 256 points of the line")


class Refusals(unittest.TestCase):
    def test_news_is_refused(self):
        self.assertIn("news", plates.refusal(program="news"))

    def test_crime_family_is_refused(self):
        self.assertIn("crime", plates.refusal(family="crime"))

    def test_deaths_and_incidents_are_refused_by_their_words(self):
        for text in ("ხანძარი თბილისში", "ორი ადამიანი დაიღუპა", "a man was killed", "Fire at a market"):
            self.assertIsNotNone(plates.refusal(text=text), text)

    def test_an_ordinary_story_is_allowed(self):
        self.assertIsNone(plates.refusal(program="explainer", family="tech", text="როგორ მუშაობს ბატარეა"))


def run_engine(*argv):
    import contextlib
    import io
    from tt_shorts import engine
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = engine.main(list(argv))
    return code, json.loads(buf.getvalue())


class Command(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_the_command_refuses_news_crime_and_deaths_before_baking(self):
        for flags in (["--program", "news"], ["--family", "crime"], ["--text", "ორი ადამიანი დაიღუპა"]):
            code, got = run_engine("plate", "example", *flags)
            self.assertEqual(code, 1, flags)
            self.assertIn("refused", got)
        self.assertEqual(plates.library(), [])  # nothing was baked

    def test_unknown_kind_is_a_problem_not_a_crash(self):
        code, got = run_engine("plate", "nope")
        self.assertEqual(code, 1)
        self.assertTrue(got["problems"])

    def test_list_and_check_read_only(self):
        code, got = run_engine("plate", "list")
        self.assertEqual((code, got["plates"]), (0, []))
        self.assertIn("example", got["kinds"])
        code, got = run_engine("plate", "check")
        self.assertEqual((code, got["problems"]), (0, []))

    def test_options_has_a_plates_section(self):
        from tt_shorts import engine
        o = engine.options(section="plates")["plates"]
        self.assertIn("example", o["kinds"])
        self.assertEqual(o["refused"]["programs"], ["news"])
        self.assertEqual(o["tool"], "veasy_plate")

    def test_check_kind_finds_a_clock_and_text(self):
        d = plates.PLATES / "zz_bad"
        d.mkdir()
        try:
            (d / "index.html").write_text("<script>window.setup=()=>{};window.step=()=>Math.random()+Date.now();"
                                          "ctx.fillText('x')</script>")
            got = " ".join(plates.check_kind("zz_bad"))
            for needle in ("Math.random", "Date.now", "fillText"):
                self.assertIn(needle, got)
        finally:
            import shutil
            shutil.rmtree(d)


class Ledger(unittest.TestCase):
    def test_entry_has_kind_hash_seed_licence(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"VEASY_HOME": tmp}):
            h = "0123456789abcdef"
            (store.plate_dir(h) / "plate.mp4").write_bytes(b"x")
            e = plates.ledger_entry({"kind": "example", "hash": h, "seed": 7})
            self.assertEqual((e["kind"], e["hash"], e["seed"], e["licence"]), ("plate", h, 7, "own"))
            self.assertEqual(e["sha"], hashlib.sha256(b"x").hexdigest())
            self.assertEqual(e["file"], f"cache/plates/{h}/plate.mp4")


ROOT = pathlib.Path(__file__).resolve().parent.parent


def demo(**over):
    st = json.loads((ROOT / "stories" / "veasy-plate.json").read_text(encoding="utf-8"))
    st.update(over)
    return st


def fake_shelf(home, *hashes, dot=None):
    for h in hashes:
        d = pathlib.Path(home) / "cache" / "plates" / h
        d.mkdir(parents=True)
        (d / "plate.mp4").write_bytes(h.encode())
        (d / "plate.json").write_text(json.dumps({"kind": "example", "hash": h, "seed": 1, "seconds": 4, "scale": 1,
                                                  "fps": 30, "frames": 120, "ms_per_frame": 200,
                                                  "anchors": ["dot"] if dot else []}))
        if dot:
            (d / "anchors.json").write_text(json.dumps({"fps": 30, "tracks": {"dot": [list(dot)] * 120}}))


class InTheStory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_the_demo_explainer_passes_every_check(self):
        from tt_shorts import engine
        self.assertEqual(engine.check_story(demo()), [])

    def test_news_refuses_a_plate_scene(self):
        got = plates.story_problems(demo(program="news"))
        self.assertTrue(got and "news" in got[0], got)
        st = demo()
        del st["program"]  # a story with no program is news
        self.assertTrue(plates.story_problems(st))

    def test_the_crime_family_refuses_it(self):
        got = plates.story_problems(demo(category="crime"))
        self.assertTrue(got, "crime must refuse")

    def test_a_death_in_the_words_refuses_it(self):
        st = demo()
        st["narration"] += " ორი ადამიანი დაიღუპა."
        self.assertTrue(plates.story_problems(st))

    def test_news_check_does_not_allow_the_type_so_n1_refuses_it(self):
        from tt_shorts import news_check
        self.assertNotIn("plate", news_check.SCENE_TYPES)
        got = news_check.problems(demo(program="news"), ["ტექსტი"])
        self.assertTrue(any("N1" in x and "plate" in x for x in got), got)

    def test_the_brush_denies_the_crime_family_and_carries_no_media(self):
        from tt_shorts import catalog
        self.assertIn("crime", catalog.get("plate")["families_deny"])
        self.assertIn("plate", catalog.NO_MEDIA)

    def test_resolve_picks_from_the_shelf_and_writes_the_ledger(self):
        from tt_shorts import assets
        fake_shelf(self.tmp.name, "aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb")
        story, rep = plates.resolve(demo())
        scene = next(s for s in story["scenes"] if s["type"] == "plate")
        self.assertIn(scene["plate"]["asset"], {e["id"] for e in story["assets"]})
        self.assertIn(scene["plate"]["layout"], ("top", "mid", "low"))
        e = next(e for e in story["assets"] if e["kind"] == "plate")
        self.assertEqual((e["licence"], e["provider"], e["seed"]), ("own", "plates", 1))
        self.assertEqual(assets.problems(story), [])
        self.assertEqual(plates.story_problems(story), [])

    def test_free_layouts_leave_the_dot_uncovered(self):
        self.assertEqual(plates.free_layouts({"dot": [[540, 960]] * 3}), ["top"])
        self.assertEqual(plates.free_layouts({"dot": [[540, 300]] * 3}), ["mid", "low"])
        self.assertEqual(plates.free_layouts({}), ["top", "mid", "low"])
        self.assertEqual(plates.free_layouts({"dot": [[540, 300], [540, 1200]]}), ["top", "mid", "low"])  # none free: all

    def test_the_card_never_sits_on_the_plates_dot(self):
        fake_shelf(self.tmp.name, "aaaaaaaaaaaaaaaa", dot=(540, 960))
        for n in range(6):
            story, _ = plates.resolve(demo(id=f"d{n}"))
            self.assertEqual(next(s for s in story["scenes"] if s["type"] == "plate")["plate"]["layout"], "top")

    def test_resolve_is_stable_and_never_bakes(self):
        fake_shelf(self.tmp.name, "aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb")
        first, _ = plates.resolve(demo())
        again, rep = plates.resolve(first)
        self.assertEqual(first, again)
        self.assertEqual(rep["plates"], {})
        with mock.patch.object(plates, "bake", side_effect=AssertionError("a queue job never bakes")):
            plates.resolve(demo(id="another"))

    def test_least_used_plate_is_picked_next(self):
        fake_shelf(self.tmp.name, "aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb")
        picked = []
        for n in range(4):
            story, _ = plates.resolve(demo(id=f"s{n}"))
            picked.append(next(e["hash"] for e in story["assets"] if e["kind"] == "plate"))
        self.assertEqual(sorted(picked), ["aaaaaaaaaaaaaaaa"] * 2 + ["bbbbbbbbbbbbbbbb"] * 2)

    def test_an_empty_shelf_is_a_warning_never_a_lost_film(self):
        story, rep = plates.resolve(demo())
        self.assertTrue(rep["warnings"])
        self.assertEqual(plates.story_problems(story), [])  # still a valid story: the scene draws the plain canvas
        self.assertNotIn("assets", story)

    def test_resolve_refuses_a_refused_story_without_picking(self):
        fake_shelf(self.tmp.name, "aaaaaaaaaaaaaaaa")
        story, rep = plates.resolve(demo(category="crime"))
        self.assertTrue(rep["warnings"])
        self.assertNotIn("assets", story)

    def test_a_forged_ledger_entry_is_caught(self):
        from tt_shorts import assets
        fake_shelf(self.tmp.name, "aaaaaaaaaaaaaaaa")
        story, _ = plates.resolve(demo())
        story["assets"][0]["file"] = "cache/media/x.mp4"
        self.assertTrue(assets.problems(story))


@unittest.skipUnless(TOOLS, "node, ffmpeg and plates/node_modules needed")
class Baked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = mock.patch.dict(os.environ, {"VEASY_HOME": cls.tmp.name})
        cls.env.start()
        cls.first = plates.make("example", seconds=1, seed=7, scale=0.25)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def test_first_bake_then_every_pack_and_theme_has_a_clip(self):
        self.assertFalse(self.first["cached"])
        self.assertEqual(self.first["frames"], 30)
        for pack in ("tbilisi-today", "sitech"):
            for theme in ("dark", "light"):
                self.assertTrue((store.home() / self.first["clips"][pack][theme]).is_file())
        self.assertEqual(self.first["anchors"], ["dot"])

    def test_second_call_answers_from_the_cache_in_under_a_second(self):
        start = time.time()
        again = plates.make("example", seconds=1, seed=7, scale=0.25)
        self.assertTrue(again["cached"])
        self.assertEqual(again["hash"], self.first["hash"])
        self.assertLess(time.time() - start, 1.0)

    def test_another_seed_is_another_plate(self):
        self.assertNotEqual(plates.hash_of("example", 1, 8, 0.25), self.first["hash"])

    def test_hash_is_a_function_of_the_spec_contents_not_its_path(self):
        a, b = pathlib.Path(self.tmp.name, "a.json"), pathlib.Path(self.tmp.name, "b.json")
        a.write_text('{"k": 1}')
        b.write_text('{"k": 1}')
        self.assertEqual(plates.hash_of("example", 1, 7, 0.25, a), plates.hash_of("example", 1, 7, 0.25, b))
        self.assertNotEqual(plates.hash_of("example", 1, 7, 0.25, a), self.first["hash"])

    def test_toned_clip_is_near_its_line_and_is_deterministic(self):
        d = store.home() / "cache" / "plates" / self.first["hash"]
        c, i = plates.hex_rgb("#05080F"), plates.hex_rgb("#F8FAFC")
        clip = d / plates.clip_name("#05080F", "#F8FAFC")
        w, h, rgb = plates.decode_frame(clip, t=0.5)
        s = plates.line_stats(rgb, c, i)
        self.assertLess(s["mean"], 2.0, s)  # measured 1.0-1.2 at full scale; the codec's noise, not a palette leak
        self.assertLess(s["p999"], 8.0, s)
        out = d / "again.mp4"
        plates.tone_clip(d / "plate.mp4", out, c, i)
        self.assertEqual(out.read_bytes(), clip.read_bytes())

    def test_for_props_copies_the_toned_clip_for_the_theme(self):
        ledger = plates.ledger_entry(self.first)
        story = demo(assets=[ledger])
        for sc in story["scenes"]:
            if sc["type"] == "plate":
                sc["plate"] = {"asset": ledger["id"], "layout": "low"}
        for pack, theme in (("tbilisi-today", "dark"), ("sitech", "light")):
            b = packs.themed(packs.load(pack), theme)
            with tempfile.TemporaryDirectory() as pub:
                got = plates.for_props(story, b, pub)[ledger["id"]]
                self.assertTrue((pathlib.Path(pub) / got["src"]).is_file())
                self.assertEqual(got["frames"], 30)
                self.assertIn("dot", got["tracks"])
                self.assertIn(b["colors"]["canvas"].lstrip("#").lower(), got["src"])

    def test_library_lists_the_plate(self):
        self.assertIn(self.first["hash"], [m["hash"] for m in plates.library()])

    def test_a_missing_kind_is_an_error(self):
        with self.assertRaises(plates.PlateError):
            plates.make("nope", seconds=1)


if __name__ == "__main__":
    unittest.main()
