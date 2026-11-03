"""The compose lane (tt_shorts/compose.py): the pure parts, without a browser or a render. The engine key and its
precedence, the review tier, facts bound by id, index.html's bindings, our lint (a case per rule), the locked chrome,
templates and slots, the DOM-text checks and the locked-down HyperFrames CLI."""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from tt_shorts import brand, claims_check, compose, directors, formats, programs, speech

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPOSITIONS = ("24835", "bipi-draws")


def timing(beats=(("a", 0.0), ("b", 2.0), ("c", 4.5)), end=6.0, duration=8.0):
    return {"beats": [{"id": i, "t": t} for i, t in beats], "chapters": [{"n": 1, "from": 0.0, "to": end}],
            "end": end, "duration": duration}


class Timing(unittest.TestCase):
    def test_map_box_keeps_the_scene_aspect_and_holds_the_box(self):
        x, y, w, h = compose.map_box([6937, 3688, 7398, 4013])
        self.assertAlmostEqual(w / h, compose.MAP_W / compose.MAP_H, places=2)
        self.assertTrue(x <= 6937 and y <= 3688 and x + w >= 7398 and y + h >= 4013)

    def test_beats_resolve_in_order_and_may_share_words(self):
        words = [{"text": t, "start": i * 0.5, "end": i * 0.5 + 0.4}
                 for i, t in enumerate("გაზი შეწყდება . გაზი არ იქნება".split())]
        out = compose.resolve([{"id": "a", "at": "გაზი შეწყდება"}, {"id": "b", "at": "შეწყდება"},
                               {"id": "c", "at": "გაზი არ"}], words)
        self.assertEqual([b["t"] for b in out], [0.0, 0.5, 1.5])

    def test_a_beat_without_an_anchor_is_named(self):
        with self.assertRaisesRegex(compose.ComposeError, "beat 'x' has no anchor"):
            compose.resolve([{"id": "x", "at": None}], [{"text": "a", "start": 0, "end": 1}])

    def test_the_shipped_films_have_a_beat_at_least_every_3s(self):
        for name in COMPOSITIONS:
            sheet = json.loads((ROOT / "compose" / name / "beats.json").read_text(encoding="utf-8"))
            story = json.loads((ROOT / "stories" / f"{name}.json").read_text(encoding="utf-8"))
            beats = compose.resolve(sheet["beats"], speech.estimate_words(story["narration"]))
            gaps = [b["t"] - a["t"] for a, b in zip(beats, beats[1:])]
            self.assertLessEqual(max(gaps), 3.0, name)
            self.assertGreater(min(gaps), 0, name)

    def test_settled_times_sit_inside_each_beat(self):
        t = {"duration": 10.0, "beats": [{"id": "a", "t": 0.0}, {"id": "b", "t": 0.5}, {"id": "c", "t": 4.0}]}
        self.assertEqual(compose.settled(t), [("a", 0.45), ("b", 1.2), ("c", 4.7)])


class EngineKey(unittest.TestCase):
    def test_precedence_director_program_format_pack_default(self):
        story = {"id": 1, "brand": "sitech"}
        self.assertEqual(compose.engine_for(story), ("remotion", "default"))
        with mock.patch.dict(brand.load("sitech"), {"engine": "hyperframes"}):
            self.assertEqual(compose.engine_for(story)[0], "hyperframes")  # the pack's
            self.assertEqual(compose.engine_for(story, {"name": "f", "engine": "remotion"})[0], "remotion")  # format
        story = {"id": 1, "brand": "sitech", "program": "story"}
        self.assertEqual(compose.engine_for(story, {"name": "news", "engine": "remotion"}),
                         ("hyperframes", "program story"))  # the program's over the format's
        d = {**directors.get("data"), "engine": "remotion"}
        with mock.patch.object(directors, "get", return_value=d):
            self.assertEqual(compose.engine_for({**story, "director": "data"})[0], "remotion")  # the director's wins
        self.assertEqual(compose.engine_for(story, override="remotion"), ("remotion", "override"))

    def test_the_key_is_validated_everywhere(self):
        with self.assertRaises(formats.FormatError):
            formats.validate("x", {**formats.DEFAULTS, "engine": "flash"})
        with self.assertRaises(programs.ProgramError):
            programs.validate("x", {**json.loads((ROOT / "programs" / "story.json").read_text(encoding="utf-8")),
                                    "engine": "flash"})
        with self.assertRaises(directors.DirectorError):
            raw = json.loads((ROOT / "directors" / "data.json").read_text(encoding="utf-8"))
            directors.validate("data", {**raw, "engine": "flash"})
        self.assertEqual(formats.get("story")["engine"], "hyperframes")
        self.assertEqual(programs.get("story")["engine"], "hyperframes")

    def test_review_policy(self):
        self.assertEqual(formats.review_policy("always"), ("always", None))
        self.assertEqual(formats.review_policy("until:20"), ("until", 20))
        for bad in ("sometimes", "until:", "until:-1", 20):
            with self.assertRaises(ValueError):
                formats.review_policy(bad)
        story = {"id": 1, "program": "story"}
        self.assertEqual(compose.review_for(story)[:2], ("always", None))
        self.assertEqual(compose.review_for(story, {"name": "f", "review": "until:3"})[:2], ("until", 3))
        self.assertEqual(compose.review_for({"id": 1})[:2], (formats.DEFAULT_REVIEW, None))


def fake_props(sources=("ინტერპრესნიუსი", "ON.ge")):
    return {"date": {"date": "1 ნოემბერი 2026", "time": "18:22", "weekday": "კვირა"}, "category": "საზოგადოება",
            "url": "tbilisi.today/stories/1", "cta": "მოიწონე", "sourcesLine": "წყაროები: ...",
            "sources": list(sources)}


class Facts(unittest.TestCase):
    def test_facts_are_the_data_and_the_story(self):
        story = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))
        fx = compose.facts(story, brand.load(), fake_props(), {"map": {"credit": "Geostat"}})
        self.assertEqual(fx["date"]["kind"], "code")
        self.assertEqual(fx["sources-n"]["value"], "2")
        self.assertEqual(fx["source-2"]["value"], "ON.ge")
        self.assertEqual(fx["map-credit"]["kind"], "code")
        self.assertIn("6400", [v["value"] for k, v in fx.items() if k.startswith("num-")])
        self.assertIn("22:00", [v["value"] for k, v in fx.items() if k.startswith("time-")])
        self.assertEqual(fx["quote-1"]["value"], "„თბილისი ენერჯის“")
        self.assertEqual(fx["scene-1-value"]["value"], "6400")
        self.assertEqual(fx["scene-0-lines-1"]["value"], "ვაზისუბანში")

    def test_slots_bind_facts_or_words(self):
        fx = {"num-1": {"value": "6400", "kind": "num", "from": "x"}}
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "slots.json").write_text(json.dumps({
                "_template": "t", "slot-a": {"kind": "num", "value": "=num-1"}, "slot-b": {"kind": "words", "value": "სიტყვა"},
                "slot-c": {"kind": "num", "value": "7"}, "slot-d": {"kind": "words", "value": None},
                "slot-e": {"kind": "num", "value": "=num-9"}}), encoding="utf-8")
            vals, bad = compose.slot_values(p, fx)
        self.assertEqual(vals, {"slot-a": "6400", "slot-b": "სიტყვა"})
        self.assertEqual(len(bad), 3)  # a typed number, an empty slot, an unknown fact
        self.assertTrue(any("never type it" in b for b in bad))


INDEX = """<!doctype html>
<!-- a comment that names <html> and <div data-beat="a"> -->
<html lang="ka">
<head><script src="assets/vendor/gsap.min.js"></script><link rel="stylesheet" href="assets/brand.css" /></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="1" data-probe-root>
<div id="s1" data-composition-id="s1" data-composition-src="compositions/s1.html" data-beat="b" data-beat-shift="-0.5" data-until="c" style="z-index: 10"></div>
<div id="chrome" data-composition-id="chrome" data-composition-src="compositions/chrome.html" data-start="0" data-duration="1" style="z-index: 30"></div>
<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="1" style="z-index: 40"></div>
</div></body></html>"""


class Bind(unittest.TestCase):
    def test_hosts_durations_and_variables(self):
        fx = {"num-1": {"value": "6'4", "kind": "num", "from": "x"}}
        text, hosts = compose.bind_index(INDEX, timing(), fx)
        self.assertEqual(hosts, {"s1": 1.5})
        self.assertIn("data-start='1.5'", text)
        self.assertIn("data-duration='3.0'", text)  # c (4.5) - 1.5
        self.assertEqual(text.count("data-duration='8.0'"), 3)  # the root, the chrome, the captions
        self.assertIn('<!-- a comment that names <html> and <div data-beat="a"> -->', text)  # comments untouched
        decl = json.loads(text.split("data-composition-variables='")[1].split("'")[0].replace("&#39;", "'"))
        ids = {d["id"]: d for d in decl}
        self.assertEqual(ids["num-1"]["default"], "6'4")
        self.assertEqual(ids["beat-b"]["default"], 2.0)
        self.assertEqual(ids["host-s1"]["default"], 1.5)
        self.assertIn('<script src="assets/vendor/veasy.js"></script>', text)
        again, _ = compose.bind_index(text, timing(), fx)  # idempotent
        self.assertEqual(again, text)

    def test_an_unknown_beat_or_a_host_that_ends_before_it_starts(self):
        with self.assertRaisesRegex(compose.ComposeError, "beat 'zz'"):
            compose.bind_index(INDEX.replace('data-until="c"', 'data-until="zz"'), timing(), {})
        with self.assertRaisesRegex(compose.ComposeError, "ends before"):
            compose.bind_index(INDEX.replace('data-until="c"', 'data-until="a"'), timing(), {})

    def test_veasy_js_gives_facts_and_beats(self):
        js = compose.veasy_js({"num-1": {"value": "6400", "kind": "num", "from": "x"}}, timing(), {"s1": 1.5},
                              {"slot-a": "x"})
        self.assertIn('"num-1": "6400"', js)
        self.assertIn("window.VEASY", js)
        self.assertIn('"s1": 1.5', js)


SCENE = """<template><style>#root .x { color: var(--ink); }</style>
<div id="root" data-composition-id="s1"><div data-probe="scene"><div class="x">სიტყვა</div>
<div data-var-text="num-1">…</div></div></div>
<script>(function () { const tl = gsap.timeline({ paused: true }); window.__timelines["s1"] = tl; })();</script>
</template>"""


class Lint(unittest.TestCase):
    """One case per rule: a clean project passes, each planted fault is named by its rule."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.p = pathlib.Path(self.dir.name)
        (self.p / "compositions").mkdir()
        (self.p / "assets" / "vendor").mkdir(parents=True)
        (self.p / "assets" / "vendor" / "gsap.min.js").write_text("//", encoding="utf-8")
        (self.p / "assets" / "brand.css").write_text(":root{}", encoding="utf-8")
        (self.p / "index.html").write_text(INDEX, encoding="utf-8")
        (self.p / "beats.json").write_text("{}", encoding="utf-8")
        for f in compose.LOCKED:
            (self.p / f).write_text("<template></template>", encoding="utf-8")
        self.scene(SCENE)
        self.lock()

    def tearDown(self):
        self.dir.cleanup()

    def scene(self, text, name="s1.html"):
        (self.p / "compositions" / name).write_text(text, encoding="utf-8")

    def lock(self):
        (self.p / ".veasy").mkdir(exist_ok=True)
        (self.p / compose.DONE_FILE).write_text(json.dumps({"chrome": compose.CHROME_VERSION, "files": {
            f: compose.sha(self.p / f) for f in compose.LOCKED}}), encoding="utf-8")

    def rules(self, text):
        self.scene(text)
        return {x.split(":")[0].split()[1] for x in compose.lint(self.p, brand.load("sitech"))}

    def test_a_clean_scene_passes(self):
        self.assertEqual(compose.lint(self.p, brand.load("sitech")), [])

    def test_color(self):
        for bad in ("color: #EF4444;", "background: rgba(0,0,0,.5);", "fill: hsl(10, 50%, 50%);", "color: white;"):
            self.assertIn("color", self.rules(SCENE.replace("color: var(--ink);", bad)), bad)
        self.assertNotIn("color", self.rules(SCENE.replace("#root .x", "#root #face .x")))  # an id is no color

    def test_font(self):
        self.assertIn("font", self.rules(SCENE.replace("color: var(--ink);", "font-family: Inter, sans-serif;")))
        self.assertIn("font", self.rules(SCENE.replace("<style>", "<style>@font-face { src: url(x.woff2) }")))
        self.assertNotIn("font", self.rules(SCENE.replace("color: var(--ink);", 'font-family: "Brand", sans-serif;')))

    def test_link(self):
        self.assertIn("link", self.rules(SCENE.replace("სიტყვა", "იხილე sitech.ge-ზე")))
        self.assertIn("link", self.rules(SCENE.replace("const tl", "const u = 'https://example.com'; const tl")))
        self.assertNotIn("link", self.rules(SCENE.replace("const tl", "const NS = 'http://www.w3.org/2000/svg'; const tl")))

    def test_net(self):
        self.assertIn("net", self.rules(SCENE.replace("<div class", '<img src="https://cdn.x.com/a.png"><div class')))
        self.assertIn("net", self.rules(SCENE.replace("<div class", '<img src="assets/none.png"><div class')))
        self.assertIn("net", self.rules(SCENE.replace("<div class", '<img src="../../secret.png"><div class')))
        self.assertIn("net", self.rules(SCENE.replace("const tl", "fetch('x'); const tl")))
        self.assertIn("net", self.rules(SCENE.replace("<template>", '<template><script src="assets/vendor/gsap.min.js"></script>')))

    def test_canvas(self):
        self.assertIn("canvas", self.rules(SCENE.replace("<div class", "<canvas id=c></canvas><div class")))
        self.assertIn("canvas", self.rules(SCENE.replace("const tl", "c.getContext('2d').fillText('x', 0, 0); const tl")))

    def test_probe(self):
        self.assertIn("probe", self.rules(SCENE.replace('<div data-probe="scene">', "<div>")))

    def test_fact(self):
        self.assertIn("fact", self.rules(SCENE.replace("სიტყვა", "6400 აბონენტს")))
        self.assertIn("fact", self.rules(SCENE.replace("სიტყვა", "„ციტატა“")))
        self.assertNotIn("fact", self.rules(SCENE.replace("…", "6400")))  # a bound element's fallback

    def test_host(self):
        (self.p / "index.html").write_text(INDEX.replace("z-index: 10", "z-index: 35"), encoding="utf-8")
        self.assertIn("host", self.rules(SCENE))
        (self.p / "index.html").write_text(INDEX.replace('data-composition-src="compositions/captions.html"', ""),
                                           encoding="utf-8")
        self.assertIn("host", self.rules(SCENE))

    def test_locked(self):
        (self.p / compose.LOCKED[0]).write_text("<template>mine now</template>", encoding="utf-8")
        found = compose.lint(self.p)
        self.assertTrue(any(x.startswith("lint locked") and "chrome.html was edited" in x for x in found), found)
        self.assertTrue(compose.lock_problems(self.p))
        lock = json.loads((self.p / compose.DONE_FILE).read_text(encoding="utf-8"))
        (self.p / compose.DONE_FILE).write_text(json.dumps({**lock, "chrome": 1}), encoding="utf-8")
        self.assertTrue(any("v1" in x for x in compose.lock_problems(self.p)))  # an older locked set

    def test_art(self):
        (self.p / "assets" / "art").mkdir()
        (self.p / "assets" / "art" / "a.svg").write_text('<svg><text>სიტყვა</text></svg>', encoding="utf-8")
        self.assertIn("art", self.rules(SCENE))

    def test_every_rule_is_named(self):
        self.assertEqual(set(compose.LINT_RULES), {"color", "font", "link", "net", "canvas", "probe", "fact", "host",
                                                  "locked", "art"})

    def test_the_shipped_compositions_type_no_pack(self):  # every color, logo and link comes from the pack
        for name in COMPOSITIONS:
            src = ROOT / "compose" / name
            for f in [src / "index.html", *(src / "compositions").glob("*.html")]:
                text = f.read_text(encoding="utf-8").lower()
                self.assertNotRegex(text, r"#[0-9a-f]{6}\b", f.name)
                for word in ("tbilisi.today", "sitech", "rgba("):
                    self.assertNotIn(word, text, f"{name}/{f.name}")


class Screen(unittest.TestCase):
    def test_bound_and_code_texts_are_not_claims(self):
        fx = {"date": {"value": "1 ნოემბერი 2026", "kind": "code", "from": "data"},
              "num-1": {"value": "6400", "kind": "num", "from": "x"}}
        rep = {"frame": 30, "scene": "a", "texts": [
            {"text": "1 ნოემბერი 2026", "bound": "date", "region": "scene"},
            {"text": "6 400", "bound": "num-1", "region": "scene"},
            {"text": "2 982", "bound": "num-1", "region": "scene"},
            {"text": "სიტყვა", "region": "scene"}, {"text": "წყარო", "region": "footer", "code": True},
            {"text": "ნარაცია", "region": "captions"}]}
        notes = []
        self.assertEqual(compose.screen_texts([rep], fx, notes), ["სიტყვა"])
        self.assertEqual(len(notes), 1)  # the count still running

    def test_numbers_on_screen_go_through_the_story_tier(self):
        story = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))
        arts = json.loads((ROOT / "tests" / "fixtures" / "24835.sources.json").read_text(encoding="utf-8"))
        self.assertEqual(compose.text_problems(story, ["6 400 აბონენტს"], arts), [])  # a thousands space
        found = compose.text_problems(story, ["7777 აბონენტს"], arts)
        self.assertTrue(any("N2" in x and "7777" in x for x in found), found)
        found = compose.text_problems(story, ["ეს საოცარია!"], arts)
        self.assertTrue(any("K12" in x for x in found), found)

    def test_fiction_texts_go_through_s1(self):
        story = json.loads((ROOT / "stories" / "bipi-draws.json").read_text(encoding="utf-8"))
        self.assertEqual(compose.text_problems(story, ["ბიპი ხატავს"]), [])
        self.assertTrue(any("S1" in x for x in compose.text_problems(story, ["ბიპი და ნიკა ბერიძე"])))


class Templates(unittest.TestCase):
    def test_promote_then_start_from_it(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            proj, tmpl = d / "film", d / "templates"
            shutil.copytree(ROOT / "compose" / "bipi-draws", proj)
            for f in compose.LOCKED:
                (proj / f).write_text("<template></template>", encoding="utf-8")
            (proj / ".veasy").mkdir()
            (proj / compose.DONE_FILE).write_text(json.dumps({"chrome": compose.CHROME_VERSION, "files": {}}),
                                                  encoding="utf-8")
            (proj / "assets" / "vendor").mkdir(parents=True)
            (proj / "assets" / "vendor" / "gsap.min.js").write_text("//", encoding="utf-8")
            (proj / "assets" / "brand.css").write_text(":root{}", encoding="utf-8")
            fx = {"character-1": {"value": "ბიპი", "kind": "name", "from": "x"},
                  "scene-0-lines-0": {"value": "პატარა რობოტი", "kind": "words", "from": "x"},
                  "date": {"value": "1 ნოემბერი", "kind": "code", "from": "data"}}
            (proj / "facts.json").write_text(json.dumps({"facts": fx}), encoding="utf-8")
            (proj / "story.json").write_text(json.dumps({"id": "bipi-draws", "brand": "sitech", "program": "story"}),
                                             encoding="utf-8")
            with mock.patch.object(compose, "TEMPLATES", tmpl):
                dest, manifest = compose.promote(proj, "little-hero", "პატარა გმირი")
                s1 = (dest / "compositions" / "s1-bipi.html").read_text(encoding="utf-8")
                self.assertIn('data-var-text="slot-s1-bipi-character-1"', s1)  # a fact -> a slot of its kind
                self.assertEqual(manifest["slots"]["slot-s1-bipi-character-1"]["kind"], "name")
                self.assertIn('data-var-text="slot-s1-bipi-scene-0-lines-0"', s1)
                words = [s for s in manifest["slots"].values() if s["kind"] == "words"]
                self.assertTrue(any(s["example"] == "პირველი წრე" for s in words))  # typed words -> words slots
                beats = json.loads((dest / "beats.json").read_text(encoding="utf-8"))
                self.assertTrue(all(b["at"] is None for b in beats["beats"]))  # anchors are the new story's
                self.assertNotIn("data-composition-variables", (dest / "index.html").read_text(encoding="utf-8"))
                self.assertEqual(sorted(compose.templates()), ["little-hero"])
                with self.assertRaises(compose.ComposeError):
                    compose.promote(proj, "little-hero")  # exists
                new = d / "new"
                new.mkdir()
                compose.use_template("little-hero", new)
                slots = json.loads((new / "slots.json").read_text(encoding="utf-8"))
                self.assertEqual(slots["_template"], "little-hero")
                self.assertIsNone(slots["slot-s1-bipi-character-1"]["value"])
                self.assertEqual(compose.template_of(new), "little-hero")
                with mock.patch("tt_shorts.variety.history", return_value=[{"template": "little-hero"}]):
                    self.assertEqual(compose.pick_template("sitech", "x"), "little-hero")

    def test_a_bad_id_or_a_film_that_fails_the_lint_is_not_promoted(self):
        with self.assertRaises(compose.ComposeError):
            compose.promote(ROOT / "compose" / "24835", "Bad Id")
        with tempfile.TemporaryDirectory() as d, mock.patch.object(compose, "TEMPLATES", pathlib.Path(d) / "t"):
            with self.assertRaisesRegex(compose.ComposeError, "lint"):
                compose.promote(ROOT / "compose" / "24835", "news-card")  # no hosts' chrome written, no lock


class HyperFrames(unittest.TestCase):
    def test_refused_and_unknown_subcommands(self):
        for sub in ("publish", "cloud", "lambda", "tts", "media-use", "feedback", "add", "skills", "nonsense"):
            with self.assertRaises(compose.ComposeError, msg=sub):
                compose.hyperframes([sub])

    def test_every_call_has_telemetry_and_updates_off(self):
        with mock.patch.object(subprocess, "run") as run, mock.patch.object(pathlib.Path, "exists", return_value=True):
            compose.hyperframes(["lint", "x"])
        env = run.call_args.kwargs["env"]
        for k in ("HYPERFRAMES_NO_TELEMETRY", "DO_NOT_TRACK", "HYPERFRAMES_NO_UPDATE_CHECK", "HYPERFRAMES_SKIP_SKILLS",
                  "HYPERFRAMES_NO_AUTO_INSTALL"):
            self.assertEqual(env[k], "1", k)
        self.assertNotIn("npx", " ".join(run.call_args.args[0]))  # the pinned bin, never npx

    def test_renders_are_pinned(self):
        self.assertEqual(compose.RENDER, {"workers": 4, "browser_gpu": False, "quality": "looks", "fps": 30})
        pkg = json.loads((ROOT / "compose" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["dependencies"]["hyperframes"], compose.HF_VERSION)


class SkillsInstall(unittest.TestCase):
    """ops/install.sh --skills, as a dry run into a temp folder: pinned, media-use left out, nothing global."""

    def test_dry_run(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("no bash")
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([bash, "ops/install.sh", "--skills", "--target", d, "--dry-run"], cwd=ROOT,
                               capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            self.assertRegex(out, r"skills@\d+\.\d+\.\d+ add https://github.com/remotion-dev/skills/tree/[0-9a-f]{40}/skills")
            self.assertIn("-a hermes-agent", out)
            self.assertNotIn(" -g", out)
            self.assertIn("dist/skills/hyperframes-cli", out)
            self.assertNotIn("dist/skills/media-use", out)
            self.assertIn(f"rm -rf {d}/media-use", out)
        r = subprocess.run([bash, "ops/install.sh", "--skills"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)  # it never guesses where


if __name__ == "__main__":
    unittest.main()
