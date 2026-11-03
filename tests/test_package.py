"""engine package: one render -> captions, cover, carousel, teaser and every platform's text, by code."""
import json
import os
import pathlib
import re
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from tt_shorts import brand, captions, meta, package, speech, store

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLES = ("24725", "24835", "sitech-cybercartel", "veasy-demo", "veasy-scenes")


def story(name):
    return json.loads((ROOT / "stories" / f"{name}.json").read_text(encoding="utf-8"))


def scenes_of(s, seconds=3.0):
    """Render-props-like scenes: the story's scenes with frames."""
    n = int(seconds * package.FPS)
    return [{**x, "from": k * n, "duration": n} for k, x in enumerate(s["scenes"])]


def clip(path, secs, audio=True):
    """A small synthetic video (and tone) to cut teasers from."""
    args = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size=108x192:rate=30:duration={secs}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}", "-c:a", "aac"]
    subprocess.run(args + ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-shortest", str(path)],
                   check=True)


class Captions(unittest.TestCase):
    def layout(self, design="page"):
        words = speech.estimate_words(story("24725")["narration"])
        return words, captions.layout(words, design, end=words[-1]["end"] + 1)

    def test_srt_cues_are_numbered_timed_and_in_order(self):
        words, cap = self.layout()
        blocks = package.srt(cap).strip().split("\n\n")
        self.assertEqual(len(blocks), len(cap["pages"]))
        last_end = 0.0
        shown = []
        for k, block in enumerate(blocks, 1):
            lines = block.split("\n")
            self.assertEqual(lines[0], str(k))
            m = re.fullmatch(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})", lines[1])
            self.assertTrue(m, lines[1])
            h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
            a, b = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000, h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
            self.assertLess(a, b)
            self.assertGreaterEqual(a, last_end - 1e-9)  # no cue starts before the last one ended
            last_end = b
            self.assertTrue(1 <= len(lines) - 2 <= 2)  # a page is one or two lines
            shown += " ".join(lines[2:]).split()
        self.assertEqual(shown, [w["text"] for w in words])  # every word once, in order
        first = cap["pages"][0]
        self.assertTrue(blocks[0].split("\n")[1].startswith(package._ts(first["start"], ",")))  # the video's own times

    def test_vtt_is_webvtt_with_dots(self):
        _, cap = self.layout("roll")
        text = package.vtt(cap)
        self.assertTrue(text.startswith("WEBVTT\n\n"))
        times = re.findall(r"^(\S+) --> (\S+)$", text, re.M)
        self.assertEqual(len(times), len(cap["pages"]))
        self.assertTrue(all(re.fullmatch(r"\d\d:\d\d:\d\d\.\d{3}", t) for pair in times for t in pair))

    def test_timestamps_round_to_milliseconds(self):
        self.assertEqual(package._ts(3661.2346, ","), "01:01:01,235")
        self.assertEqual(package._ts(0.0004, "."), "00:00:00.000")
        self.assertEqual(package._ts(-1, ","), "00:00:00,000")

    def test_no_pages_no_cues(self):
        self.assertEqual(package.srt(None), "")
        self.assertEqual(package.vtt({"pages": [], "lines": []}), "WEBVTT\n\n")


class Texts(unittest.TestCase):
    def setUp(self):
        brand.load.cache_clear()

    def test_limits_links_and_hashtags(self):
        for name in SAMPLES:
            s = story(name)
            b = brand.of(s)
            t = package.texts(s, b)
            self.assertLessEqual(len(t["youtube"]["title"]), package.LIMITS["youtube_title"], name)
            self.assertLessEqual(len(t["tiktok"]["caption"]), package.LIMITS["tiktok"], name)
            self.assertTrue(3 <= len(t["hashtags"]) <= 5, (name, t["hashtags"]))
            self.assertEqual(len(set(t["hashtags"])), len(t["hashtags"]))
            self.assertTrue(t["hashtags"][0].startswith("#" + meta.category_label(s["category"], b).split()[0]), name)
            d = t["youtube"]["description"]
            self.assertIn(meta.story_url(s["id"], "youtube", b), d)
            self.assertIn("utm_source=youtube", d)
            self.assertIn(meta.ka_date(s["date"], b)["date"], d)
            for outlet in s["sources"]:
                self.assertIn(outlet, d)
            self.assertNotIn("http", t["instagram"]["caption"])  # Instagram: the link is in the bio
            self.assertIn(b["package"]["link_in_bio"], t["instagram"]["caption"])
            self.assertIn("utm_source=facebook", t["facebook"]["caption"])
            self.assertIn("utm_source=telegram", t["telegram"])
            self.assertTrue(t["telegram"].startswith("*"))

    def test_posts_leave_the_videos_outro_out(self):
        s = story("24835")  # its stat anchor leaves out the narration's „quotes“
        t = package.texts(s, brand.of(s))
        for text in (t["youtube"]["description"], t["instagram"]["caption"], t["telegram"]):
            self.assertNotIn("აშუქებს", text)  # "covered by N outlets": the sources scene
            self.assertNotIn("მოიწონე", text)  # the call to action belongs to the video

    def test_the_headline_is_not_repeated_by_the_first_sentence(self):
        s = story("24725")
        t = package.texts(s, brand.of(s))
        self.assertNotIn("უკრაინის პრეზიდენტი ზელენსკი", t["instagram"]["caption"])
        self.assertIn("უკრაინის პრეზიდენტი ზელენსკი", t["youtube"]["description"])  # the description has it all

    def test_long_titles_are_cut_at_a_word(self):
        s = story("24725")
        s["scenes"][0]["lines"] = ["ძალიან გრძელი სათაური"] * 8
        t = package.texts(s, brand.of(s))
        self.assertLessEqual(len(t["youtube"]["title"]), 100)
        self.assertGreater(len(t["youtube"]["title"]), 85)
        self.assertTrue((" ".join(s["scenes"][0]["lines"]) + " ").startswith(t["youtube"]["title"] + " "))  # whole words
        self.assertLessEqual(len(t["tiktok"]["caption"]), 150)
        self.assertTrue(t["tiktok"]["caption"].endswith(" ".join(t["hashtags"][:3])))
        self.assertNotIn("…", t["youtube"]["title"])

    def test_generated_texts_pass_the_georgian_screen_rules(self):
        for name in SAMPLES:
            s = story(name)
            self.assertEqual(package.texts_problems(package.texts(s, brand.of(s)), s), [], name)

    def test_the_rules_catch_a_bad_text(self):
        s = story("24725")
        bad = {"!": "K12", "თქვენ გამოიწერეთ": "K1", " — ": "K12"}
        for insert, rule in bad.items():
            broken = json.loads(json.dumps(s))
            broken["scenes"][0]["lines"][0] += insert + "ახალი"
            p = package.texts_problems(package.texts(broken, brand.of(broken)), broken)
            self.assertTrue(any(x.startswith(rule) and "youtube.title" in x for x in p), (insert, p))

    def test_links_and_hashtags_are_not_stray_english(self):
        s = story("24725")
        self.assertEqual(package.text_problems("x", "ამბავი https://tbilisi.today/stories/1?utm_source=youtube #tbilisitoday "
                                                    "[tbilisi.today/stories/1](https://tbilisi.today/x)", s), [])
        self.assertTrue(package.text_problems("x", "ეს არის breaking ამბავი", s))  # K19 still reads the prose


class Carousel(unittest.TestCase):
    def test_every_sample_has_five_to_seven_slides(self):
        for name in SAMPLES:
            s = story(name)
            slides = package.slide_plan(scenes_of(s), s, brand.of(s))
            types = [x["type"] for x in slides]
            self.assertTrue(package.MIN_SLIDES <= len(slides) <= package.MAX_SLIDES, (name, types))
            self.assertEqual(types[0], "hook")
            self.assertEqual(types[-2:], ["sources", "end"])
            self.assertTrue(all(x["freeze"] == x["duration"] - 1 for x in slides))  # each at its final frame

    def test_many_scenes_keep_the_first_four(self):
        s = story("veasy-scenes")  # hook, 6 content scenes, end; no sources scene of its own
        slides = package.slide_plan(scenes_of(s), s, brand.of(s))
        self.assertEqual([x["type"] for x in slides], ["hook", "draw", "pair", "steps", "bars", "sources", "end"])
        self.assertEqual(slides[-2]["kicker"], brand.of(s)["strings"]["source_many"])

    def test_few_scenes_get_narration_slides(self):
        s = story("24725")
        s["scenes"] = [x for x in s["scenes"] if x["type"] in ("hook", "quote", "end")]
        slides = package.slide_plan(scenes_of(s), s, brand.of(s))
        self.assertEqual(len(slides), package.MIN_SLIDES)
        summary = [x for x in slides if x["type"] == "summary"]
        self.assertTrue(summary and all(x["text"] and x["text"] in s["narration"] for x in summary))
        self.assertNotIn("უკრაინის პრეზიდენტი ზელენსკი", " ".join(x["text"] for x in summary))  # the hook's sentence

    def test_the_slide_box_matches_the_composition(self):
        tsx = (ROOT / "remotion" / "src" / "Slide.tsx").read_text(encoding="utf-8")
        for name in ("BOX_W", "BOX_H", "BAND_TOP", "BAND_BOTTOM", "FOOTER_TOP", "SLIDE_H"):
            self.assertEqual(int(re.search(rf"export const {name} = (\d+);", tsx).group(1)), getattr(package, name), name)
        self.assertEqual((1080 - package.BOX_W) // 2, package.BOX_LEFT)
        self.assertEqual(package.BAND_TOP + (package.BAND_BOTTOM - package.BAND_TOP - package.BOX_H) // 2, package.BOX_TOP)

    def test_fit_check_sees_ink_outside_the_box(self):
        with tempfile.TemporaryDirectory() as d:
            ok, bad = pathlib.Path(d, "ok.png"), pathlib.Path(d, "bad.png")
            base = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x05080F:s=1080x1350"]
            subprocess.run(base + ["-vf", "drawbox=x=200:y=400:w=600:h=80:color=white:t=fill", "-frames:v", "1", str(ok)],
                           check=True)
            subprocess.run(base + ["-vf", "drawbox=x=200:y=1180:w=600:h=30:color=white:t=fill", "-frames:v", "1", str(bad)],
                           check=True)
            self.assertEqual(package.fit_problems(ok, "who"), [])
            self.assertTrue(package.fit_problems(bad, "who"))
            self.assertTrue(package.fit_problems(bad, "end"))

    def test_fit_check_on_a_light_theme(self):  # paper canvas, coal ink: the ink is the dark pixels
        with tempfile.TemporaryDirectory() as d:
            ok, bad = pathlib.Path(d, "ok.png"), pathlib.Path(d, "bad.png")
            base = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0xF1EDE4:s=1080x1350"]
            subprocess.run(base + ["-vf", "drawbox=x=200:y=400:w=600:h=80:color=0x171817:t=fill", "-frames:v", "1",
                                   str(ok)], check=True)
            subprocess.run(base + ["-vf", "drawbox=x=200:y=1180:w=600:h=30:color=0x171817:t=fill", "-frames:v", "1",
                                   str(bad)], check=True)
            self.assertEqual(package.fit_problems(ok, "who", light=True), [])
            self.assertTrue(package.fit_problems(bad, "who", light=True))
            self.assertTrue(package.fit_problems(ok, "who"))  # read as a dark theme, paper is all "ink"


class Teaser(unittest.TestCase):
    def props(self, hook_s, total_s=30.0, end_s=4.0):
        fps = package.FPS
        words = speech.estimate_words(story("24725")["narration"])
        scale = (total_s - 1.6) / words[-1]["end"]
        words = [{**w, "start": w["start"] * scale, "end": w["end"] * scale} for w in words]
        scenes = [{"type": "hook", "from": 0, "duration": int(hook_s * fps)},
                  {"type": "points", "from": int(hook_s * fps), "duration": int((total_s - end_s - hook_s) * fps)},
                  {"type": "end", "from": int((total_s - end_s) * fps), "duration": int(end_s * fps)}]
        return {"durationInFrames": int(total_s * fps), "scenes": scenes, "words": words}

    def test_plan_stays_in_the_window(self):
        for hook in (1.5, 3.0, 5.0, 7.0, 12.0):
            cut, tail_from, secs = package.teaser_plan(self.props(hook))
            self.assertTrue(package.TEASER[0] <= secs <= package.TEASER[1], (hook, cut, tail_from, secs))
            self.assertGreaterEqual(tail_from, 30.0 - 4.0)  # the tail is the end card
            self.assertLess(cut, tail_from)
        cut, _, _ = package.teaser_plan(self.props(5.0))
        self.assertAlmostEqual(cut, 5.0, places=2)  # a hook that fits is kept whole

    def test_cut_clip_is_six_to_ten_seconds(self):
        with tempfile.TemporaryDirectory() as d:
            for audio in (True, False):
                src, out = pathlib.Path(d, f"src{audio}.mp4"), pathlib.Path(d, f"teaser{audio}.mp4")
                clip(src, 14, audio)
                package.cut_teaser(src, out, 5.0, 11.0)
                secs = package.seconds(out)
                self.assertTrue(6 <= secs <= 10, secs)
                self.assertAlmostEqual(secs, 5.0 + 3.0 - package.XFADE, delta=0.15)
                self.assertEqual(package._has_audio(out), audio)


class Storage(unittest.TestCase):
    def test_package_dir_sits_beside_the_render(self):
        r = pathlib.Path("/x/renders/tt/2026-11-02/24725-news-cards-page.mp4")
        for p in (r, r.with_suffix(".json"), store.props_path(r)):
            self.assertEqual(store.package_dir(p), r.with_name("24725-news-cards-page-package"))
        self.assertEqual(store.props_path(r).name, "24725-news-cards-page.props.json")

    def test_gc_deletes_old_packages_with_their_render(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"VEASY_HOME": home}):
            mp4 = store.render_path("tbilisi-today", 1, "news", "cards", "page", day="2026-09-01")
            mp4.write_bytes(b"x")
            pkg = store.package_dir(mp4)
            pkg.mkdir()
            (pkg / "texts.json").write_text("{}")
            past = time.time() - 40 * 86400
            for p in (mp4, pkg):
                os.utime(p, (past, past))
            removed = store.gc()
            self.assertIn(str(pkg), removed["renders"])
            self.assertFalse(pkg.exists())

    def test_a_render_without_props_is_refused_clearly(self):
        with tempfile.TemporaryDirectory() as d:
            m = pathlib.Path(d, "x-news-cards-page.json")
            m.write_text(json.dumps({"file": str(m.with_suffix(".mp4")), "story": str(ROOT / "stories" / "24725.json")}))
            with self.assertRaises(package.PackageError) as e:
                package.load(m.with_suffix(".mp4"))
            self.assertIn("render it again", str(e.exception))


if __name__ == "__main__":
    unittest.main()
