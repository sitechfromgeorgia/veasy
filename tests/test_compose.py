"""The compose lane (tt_shorts/compose.py): the pure parts, without a browser or a render. The engine key and its
precedence, the review tier, facts bound by id, index.html's bindings, our lint (a case per rule), the locked chrome,
templates and slots, the DOM-text checks, the locked-down HyperFrames CLI, what `look` makes of its reports and the
novelty of a composed film."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from tt_shorts import (brand, captions, claims_check, compose, directors, formats, probe, programs, speech, store,
                       variety)

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


class MediaAndSound(unittest.TestCase):
    """The media layer's hooks: the story's pictures through assets.for_props, the sound effects through
    props.mix_audio's props["sfx"], timed by the film's own wipes and beats."""

    def test_cues_come_from_the_wipes_and_the_beats_when_the_format_says_on(self):
        t = {**timing(), "wipes": [2.0, 6.0], "beats": [{"id": "a", "t": 0.0}, {"id": "b", "t": 3.0, "sfx": "pop"},
                                                          {"id": "c", "t": 3.02, "sfx": "pop"},
                                                          {"id": "d", "t": 4.0, "sfx": "nonsense"}]}
        self.assertEqual(compose.sfx_cues(t, "off"), [])
        cues = compose.sfx_cues(t, "on")
        self.assertEqual([c["name"] for c in cues], ["whoosh", "pop", "whoosh"])  # 3.02 is too close, nonsense no sound
        self.assertAlmostEqual(cues[0]["t"], 1.9)

    def test_pictures_come_through_the_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "assets").mkdir()
            drawn = {"a1": {"kind": "image", "src": "media/a1.jpg", "label": "საილუსტრაციო", "credit": "Pexels"}}
            story = {"scenes": [{"type": "hook", "media": {"asset": "a1"}}], "assets": [{"id": "a1"}]}
            with mock.patch("tt_shorts.assets.for_props", return_value=drawn) as fp:
                files = compose.media(story, brand.load("sitech"), p)
            fp.assert_called_once()
            self.assertEqual(files, ["assets/media.json", "assets/media/a1.jpg"])
            m = json.loads((p / "assets" / "media.json").read_text(encoding="utf-8"))
            self.assertEqual(m["pictures"]["a1"]["src"], "assets/media/a1.jpg")
            self.assertEqual(m["scenes"], {"0": "a1"})


class KeywordCaptions(unittest.TestCase):
    """The locked captions draw captions.py's keyword design from its layout data: the page's key, the pack's style."""

    def cap(self, style):
        words = [{"text": w, "from": i * 0.5, "to": i * 0.5 + 0.4} for i, w in enumerate(["გაზი", "6400", "აბონენტს"])]
        return {"design": "keyword", "size": 60, "lineHeight": 1.22, "band": 768, "pad": 26, "keyword": style,
                "lines": [{"start": 0, "words": words}],
                "pages": [{"start": 0, "end": 2, "lines": [0], "key": {"line": 0, "from": 1, "to": 1, "kind": "number"}}]}

    def test_the_page_key_in_the_pack_style(self):
        b = brand.load("tbilisi-today")
        t = {"words": [{"text": w, "start": i * 0.5, "keyword": False} for i, w in enumerate(["გაზი", "6400", "აბონენტს"])]}
        html = compose.captions_html(self.cap("block"), t, b)
        self.assertEqual(html.count('class="w k"'), 1)
        self.assertIn('tl.set("#cap-w1 em", { color: "' + b["colors"]["canvas"], html)  # the block inverts the word
        html = compose.captions_html(self.cap("underline"), t, b)
        self.assertNotIn('tl.set("#cap-w1 .u", { scaleX: 0 }', html)  # its underline stays once said
        self.assertIn('tl.set("#cap-w0 .u", { scaleX: 0 }', html)
        html = compose.captions_html(self.cap("tint"), t, b)
        self.assertIn('tl.set("#cap-w1 em", { color: "' + b["colors"]["accent"], html)


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
        (self.p / "index.html").write_text("﻿" + INDEX, encoding="utf-8")  # bind_index's BOM is no text
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

    def test_timeline(self):
        bad_scene = SCENE.replace('window.__timelines["s1"] = tl;', 'console.log("no timeline registered");')
        self.assertIn("timeline", self.rules(bad_scene))

    def test_prefix(self):
        bad_scene = SCENE.replace('class="x">სიტყვა</div>', 'id="bad-id" class="x">სიტყვა</div>')
        self.assertIn("prefix", self.rules(bad_scene))
        good_scene = SCENE.replace('class="x">სიტყვა</div>', 'id="s1-good" class="x">სიტყვა</div>')
        self.assertNotIn("prefix", self.rules(good_scene))

    def test_template(self):
        bad_scene = SCENE.replace("<template>", "").replace("</template>", "")
        self.assertIn("template", self.rules(bad_scene))
        bad_scene2 = SCENE.replace('data-composition-id="s1"', "")
        self.assertIn("template", self.rules(bad_scene2))

    def styled(self, css):
        return self.rules(SCENE.replace("#root .x { color: var(--ink); }", f"#root .x {{ color: var(--ink); }} {css}"))

    def test_css_content(self):
        for css in ('#root .x::before { content: "6400"; }', "#root .x::after{content:'კვირა'}",
                    "#root .x::before { content: attr(data-n); }", "#root .x::before { content: var(--label); }",
                    '#root .x::before { content: "0" counter(step); }', "#root .x { counter-increment: step; }",
                    "#root .x { list-style-type: decimal; }", "#root .x { list-style: georgian inside; }"):
            self.assertIn("css-content", self.styled(css), css)
        self.assertIn("css-content", self.rules(SCENE.replace('<div class="x">', '<div class="x" style="content: \'6\'">')))
        self.assertIn("css-content", self.rules(SCENE.replace("<div class", "<ol><li>ა</li></ol><div class")))
        self.assertIn("css-content", self.rules(SCENE.replace("<div class", '<input value="6400"><div class')))

    def test_a_shape_in_css_is_no_text(self):
        for css in ('#root .x::before { content: ""; }', "#root .x::after { content: '' !important; }",
                    "#root .x::before { content: none; }", "#root .x { list-style: none; }",
                    "#root .x { align-content: center; justify-content: end; place-content: center; }",
                    '/* content: "6400" */'):
            self.assertNotIn("css-content", self.styled(css), css)

    def test_a_film_with_hidden_text_is_never_rendered(self):
        self.assertTrue("lint css-content: compositions/s1.html: x".startswith(compose.HARD))
        self.assertTrue("probe generated: s1 at 1.00s: x".startswith(compose.HARD))
        self.assertFalse("lint outlined-text: compositions/s1.html: x".startswith(compose.HARD))  # a guess only holds

    def test_no_shipped_film_block_or_template_generates_text(self):
        scenes = [*ROOT.glob("compose/blocks/*/template.html"), *ROOT.glob("templates/*/compositions/*.html"),
                  *(f for name in COMPOSITIONS for f in (ROOT / "compose" / name / "compositions").glob("*.html"))]
        self.assertGreater(len(scenes), 15)
        for f in scenes:
            text = f.read_text(encoding="utf-8")
            self.assertEqual({x for x in compose.CSS_CONTENT.findall(text) if not compose.CSS_EMPTY.match(x.strip())},
                             set(), f)
            self.assertIsNone(compose.GENERATED.search(text), f)
            self.assertEqual(compose.outlined_text(text), 0, f)

    def outline(self, text):
        """`text` in the pack's real font as one SVG path per glyph, the way a font tool writes it."""
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.transformPen import TransformPen
        from fontTools.ttLib import TTFont
        font = TTFont(sorted(brand.load("sitech")["_fonts"].values(), key=str)[0])
        glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
        x, paths = 0, []
        for ch in text:
            pen = SVGPathPen(glyphs)
            glyphs[cmap[ord(ch)]].draw(TransformPen(pen, (1, 0, 0, -1, x, 800)))
            paths.append(f'<path d="{pen.getCommands()}"/>')
            x += hmtx[cmap[ord(ch)]][0]
        return f'<svg viewBox="0 0 {x} 1000">{"".join(paths)}</svg>'

    def test_outlined_text(self):
        for word in ("2026", "12,5", "1000", "წელი", "საქართველო"):
            svg = self.outline(word)
            self.assertIn("outlined-text", self.rules(SCENE.replace("<div class", svg + "<div class")), word)
            one_path = svg.replace('"/><path d="', " ")  # the whole line as one path, as some tools write it
            self.assertGreaterEqual(compose.outlined_text(one_path), compose.LINE_GLYPHS, word)
        (self.p / "assets" / "art").mkdir()
        (self.p / "assets" / "art" / "a.svg").write_text(self.outline("2026"), encoding="utf-8")
        self.assertIn("outlined-text", self.rules(SCENE))

    def test_two_digits_pass_under_the_heuristic(self):  # its known limit: the film is held for a person's eye anyway
        self.assertEqual(compose.outlined_text(self.outline("25")), 0)

    def test_drawings_are_not_text(self):
        dots = "".join(f'<path d="M{x} 0a5 5 0 1 0 10 0a5 5 0 1 0-10 0z"/>' for x in range(0, 60, 15))
        bars = "".join(f'<path d="M{x} 0h10v{20 + x}h-10z"/>' for x in range(0, 60, 15))
        self.assertEqual(compose.outlined_text(f"<svg>{dots}</svg>"), 0)  # equal shapes
        self.assertEqual(compose.outlined_text(f"<svg>{bars}</svg>"), 0)  # no curves
        self.assertEqual(compose.outlined_text('<svg><path d="M0 0L10 10"/><path d="not a path"/></svg>'), 0)
        for f in (ROOT / "assets" / "drawings").glob("*.svg"):
            self.assertEqual(compose.outlined_text(f.read_text(encoding="utf-8")), 0, f.name)

    def test_every_rule_is_named(self):
        self.assertEqual(set(compose.LINT_RULES), {"color", "font", "link", "net", "canvas", "probe", "fact", "host",
                                                   "locked", "art", "timeline", "prefix", "template", "css-content",
                                                   "outlined-text"})

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


LONG_LINK = "tbilisi.today/stories/explainer-inflation"  # at 36 px the footer ran off the frame (chrome v2)


class ChromeFit(unittest.TestCase):
    def chrome(self, url, cta="მეტი ამბავი"):
        b = brand.load("tbilisi-today")
        t = {"duration": 10.0, "end": 9.0, "wipes": [], "beats": [],
             "chapters": [{"n": 1, "of": 1, "title": "ა", "from": 0.0, "to": 9.0}],
             "facts": {"url": url, "cta": cta, "category": "ა", "date": {"date": "1 ნოემბერი"}, "sources": ["ა"]}}
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "assets").mkdir()
            return compose.chrome(t, b, pathlib.Path(d), "film")

    def test_a_short_link_keeps_the_kits_size(self):
        html = self.chrome("tbilisi.today/stories/24835")
        self.assertIn(".footer .url { font-weight: 700; font-size: 36px", html)
        self.assertIn("text-align: center; font-weight: 700; font-size: 40px", html)
        self.assertIn("justify-content: center; font-weight: 600; font-size: 40px", html)

    def test_a_long_link_stays_clear_of_the_pack_line(self):
        b = brand.load("tbilisi-today")
        size = compose.footer_size(LONG_LINK, b)
        fonts, foot = b["_fonts"], b["footer"]
        used = (captions.width(LONG_LINK, size, fonts["700"]) + captions.width(foot["text"], 28, fonts["400"])
                + captions.width(foot["strong"], 28, fonts["700"]))
        self.assertLess(size, 36)
        self.assertLessEqual(used + 32, compose.W - 2 * compose.SIDE)
        self.assertIn(f".footer .url {{ font-weight: 700; font-size: {size}px", self.chrome(LONG_LINK))

    def test_the_link_stops_shrinking_at_the_probes_floor(self):
        self.assertEqual(compose.footer_size("tbilisi.today/stories/" + "ა" * 90, brand.load("tbilisi-today")),
                         probe.MIN_PX["footer"])

    def test_the_end_card_fits_a_long_link_and_cta(self):
        b = brand.load("tbilisi-today")
        url = "tbilisi.today/stories/" + "a" * 40
        size = compose.fit_size(url, 800, 40, 24, b["_fonts"]["700"])
        self.assertLess(size, 40)
        self.assertLessEqual(captions.width(url, size, b["_fonts"]["700"]), 800)
        cta = "გამოიწერე არხი და მიიღე ყოველი ახალი ამბავი პირველმა"
        size = compose.fit_size(cta, 704, 40, 24, b["_fonts"]["600"])
        self.assertLess(size, 40)
        html = self.chrome(url, cta)
        self.assertIn(f"justify-content: center; font-weight: 600; font-size: {size}px", html)


class Cuts(unittest.TestCase):
    """Two scenes on screen at once read as a mistake: only a wipe (chapter cuts, 0.2 s) may cover an overlap."""

    def test_the_fable_and_the_explainer_never_dissolve_one_scene_through_the_next(self):
        for base, n in ((ROOT / "compose" / "bipi-draws", 5), (ROOT / "templates" / "fable-story", 5),
                        (ROOT / "templates" / "tech-explainer", 4)):
            hosts = re.findall(r'<div id="s\d"[^>]*>', (base / "index.html").read_text(encoding="utf-8"))
            self.assertEqual(len(hosts), n, base)
            for a, b in zip(hosts, hosts[1:]):
                self.assertEqual(compose._attr(a, "data-until"), compose._attr(b, "data-beat"), base)
                over = float(compose._attr(a, "data-until-shift") or 0) - float(compose._attr(b, "data-beat-shift") or 0)
                self.assertLessEqual(over, 0.2, (base.name, compose._attr(a, "id"), compose._attr(b, "id")))

    def test_the_news_film_keeps_only_its_blur_swap(self):
        for base in (ROOT / "compose" / "24835", ROOT / "templates" / "news-kinetic"):
            spans = compose.host_spans((base / "index.html").read_text(encoding="utf-8"))
            self.assertEqual([c[:2] for c in compose.cuts(spans)], [("s6", "s7")], base.name)

    def test_a_starter_cuts_on_the_beat(self):
        self.assertEqual(compose._until("s1"), 'data-until="s1"')
        self.assertIn('data-until-shift="0.3"', compose._until("end"))  # the last scene goes under the end's wipe

    def test_a_cut_is_a_host_that_starts_inside_another_and_outlives_it(self):
        spans = {"s1": (0.0, 5.3), "s2": (5.0, 9.0), "s3": (9.0, 12.0), "layer": (0.0, 20.0), "s4": (12.0, 12.5)}
        self.assertEqual(compose.cuts(spans), [("s1", "s2", 5.0, 5.3)])  # s2 touches s3; the layer lasts through all

    def test_a_cut_is_read_every_other_frame_and_a_long_overlap_no_more_than_the_cap(self):
        self.assertEqual(compose.cut_times(4.7, 5.0), [4.7, 4.767, 4.833, 4.9, 4.967])
        self.assertLessEqual(len(compose.cut_times(4.0, 9.0)), compose.CUT_READINGS)
        self.assertEqual(compose.cut_times(5.0, 5.0), [])

    def test_hosts_come_from_the_built_page_not_its_comments_or_the_chrome(self):
        html = ('<!-- <div data-composition-id="s9" data-start="1" data-duration="1"></div> -->'
                '<div data-composition-id="main" data-start="0" data-duration="9"><div data-composition-id="s1" '
                'data-start="1.5" data-duration="2"></div><div data-composition-id="chrome" data-start="0" '
                'data-duration="9"></div></div>')
        self.assertEqual(compose.host_spans(html), {"s1": (1.5, 3.5)})

    @staticmethod
    def text(comp, words, box=(64, 300, 400, 100), **kw):
        return {"comp": comp, "text": words, "box": list(box), "opacity": 1.0, "hidden": 0.0, **kw}

    def read(self, *texts, cells=None, times=(10.0, 10.067, 10.133)):
        rows = [{"t": t, "probe": {"texts": list(texts), "cells": cells or {}}} for t in times]
        return compose.cut_problems("s2", "s3", rows)

    def test_two_texts_on_one_spot_are_a_problem(self):
        problems, _ = self.read(self.text("s2", "ძველი"), self.text("s3", "ახალი", (64, 310, 400, 100)))
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("probe cut: s2 to s3 at 10.00s: „ძველი“ on „ახალი“ for 0.20 s"), problems)

    def test_texts_apart_are_no_collision(self):
        self.assertEqual(self.read(self.text("s2", "ა"), self.text("s3", "ბ", (64, 700, 400, 100))), ([], []))

    def test_what_a_viewer_cant_catch_is_no_collision(self):
        one = self.read(self.text("s2", "ა"), self.text("s3", "ბ"), times=(10.0,))
        self.assertEqual(one, ([], []))

    def test_a_ghost_an_ornament_and_a_text_under_a_wipe_are_no_collision(self):
        new = self.text("s3", "ახალი")
        for old in (self.text("s2", "ა", opacity=0.1), self.text("s2", "ა", decor=True), self.text("s2", "ა", hidden=0.8)):
            self.assertEqual(self.read(old, new), ([], []), old)

    def test_a_text_on_the_other_scenes_drawing_is_a_problem(self):
        cols = 54  # 1080 px on the 20 px grid
        spot = [row * cols + col for row in range(16, 19) for col in range(5, 8)]  # x 100-160, y 320-380
        problems, _ = self.read(self.text("s2", "ძველი"), cells={"s3": spot})
        self.assertTrue(problems and "„ძველი“ on s3's drawing" in problems[0], problems)
        self.assertEqual(self.read(self.text("s2", "ძველი", (64, 900, 400, 100)), cells={"s3": spot}), ([], []))

    def test_two_drawings_on_one_spot_are_a_warning_only(self):
        spot = list(range(200))  # 2% of the 54 x 96 grid: a mistake, or a match cut
        problems, warnings = self.read(cells={"s2": spot, "s3": spot})
        self.assertEqual(problems, [])
        self.assertTrue(warnings and warnings[0].startswith("cut: s2 to s3 at 10.00s: both scenes draw on 4%"), warnings)


class Templates(unittest.TestCase):
    def test_every_shipped_template_is_for_this_chrome(self):
        for f in compose.TEMPLATES.glob("*/manifest.json"):
            self.assertEqual(json.loads(f.read_text(encoding="utf-8"))["chrome"], compose.CHROME_VERSION, f.parent.name)

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

    def test_a_film_never_leaves_the_machine(self):
        for args in (["snapshot", "x", "--describe"], ["snapshot", "x", "--describe=what is this"],
                     ["audio", "f.mp4", "--quality", "best", "--json"], ["audio", "f.mp4", "--quality=best"],
                     ["audio", "f.mp4"], ["audio", "f.mp4", "--quality"], ["audio", "f.mp4", "--provider", "onsets=x"]):
            with self.assertRaisesRegex(compose.ComposeError, "stays on this machine", msg=args):
                compose.hyperframes(args)
        with mock.patch.object(subprocess, "run"), mock.patch.object(pathlib.Path, "exists", return_value=True):
            compose.hyperframes(["audio", "f.mp4", "--quality", compose.AUDIO_QUALITY, "--json"])
            compose.hyperframes(["snapshot", "x", "--review", "--json"])

    def test_renders_are_pinned(self):
        self.assertEqual(compose.RENDER, {"workers": 4, "browser_gpu": False, "quality": "looks", "fps": 30})
        pkg = json.loads((ROOT / "compose" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["dependencies"]["hyperframes"], compose.HF_VERSION)


class Look(unittest.TestCase):
    """engine compose look: its reports, and that it runs only through hyperframes(), the film rebuilt first."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.p = pathlib.Path(self.dir.name)
        (self.p / "index.html").write_text("<html></html>", encoding="utf-8")
        self.video = self.p / "film.mp4"
        self.video.write_bytes(b"x")

    def reply(self, args, **kw):
        self.calls.append([str(a) for a in args])
        stdout = {"snapshot": "progress {" + json.dumps({"contactSheets": [
                      "o/review-beats.jpg", "o/review-seam-01.jpg", "o/review-seam-02.jpg", "o/review-phone.jpg"],
                      "review": {"scenes": [{"id": "s1"}, {"id": "chrome"}]}})[1:],
                  "keyframes": json.dumps({"compositions": [
                      {"source": "index.html", "tweens": [{"ease": "none"}]},
                      {"source": "compositions/s1.html", "tweens": [{"ease": "expo.out"}, {"ease": "expo.out"}, {}]},
                      {"source": "compositions/chrome.html", "tweens": [{"ease": "power3.in"}] * 50}]}),
                  "audio": json.dumps({"loudness": -16})}[args[0]]
        return subprocess.CompletedProcess(args, 0, stdout, "")

    def look(self, **kw):
        self.calls = []
        story = {"id": "x", "brand": "sitech"}
        with mock.patch.object(compose, "_story", return_value=story), \
                mock.patch.object(compose.packs, "of", return_value={"name": "sitech"}), \
                mock.patch.object(compose, "lock_problems", return_value=[]), \
                mock.patch.object(compose, "build", return_value={"timing": {"duration": 9.0}, "work": str(self.p / "w")}), \
                mock.patch.object(compose, "hyperframes", side_effect=self.reply):
            return compose.look("x.json", project=self.p, **kw)

    def test_sheets_timeline_and_sound(self):
        r = self.look(video=self.video)
        self.assertEqual(r["problems"], [])
        self.assertEqual((r["sheets"]["beats"], r["sheets"]["phone"]), (str(pathlib.Path("o/review-beats.jpg")),
                                                                        str(pathlib.Path("o/review-phone.jpg"))))
        self.assertEqual(len(r["sheets"]["seams"]), 2)
        self.assertEqual(r["scenes"], [{"id": "s1"}])  # the chrome is no scene
        self.assertEqual(json.loads(pathlib.Path(r["timeline"]).read_text(encoding="utf-8"))["compositions"][0]["source"],
                         "index.html")
        self.assertEqual(json.loads(pathlib.Path(r["audio"]).read_text(encoding="utf-8")), {"loudness": -16})
        self.assertEqual([c[0] for c in self.calls], ["snapshot", "keyframes", "audio"])
        self.assertIn("--no-browser-gpu", self.calls[0])  # software GL, as at render
        self.assertEqual(self.calls[2][self.calls[2].index("--quality") + 1], compose.AUDIO_QUALITY)

    def test_the_agents_motion_without_the_locked_chrome(self):
        m = self.look(video=self.video)["motion"]
        self.assertEqual(m["tweens"], 4)
        self.assertEqual(m["by_file"], {"index.html": 1, "compositions/s1.html": 3})
        self.assertEqual(m["eases"], {"expo.out": 0.5, "none": 0.25, "default": 0.25})

    def test_no_render_yet_says_so_and_still_looks(self):
        r = self.look()
        self.assertIsNone(r["audio"])
        self.assertEqual(r["problems"], [])
        self.assertTrue(any("sound was not measured" in w for w in r["warnings"]))
        self.assertEqual([c[0] for c in self.calls], ["snapshot", "keyframes"])

    def test_a_failed_snapshot_is_a_problem(self):
        with mock.patch.object(self, "reply", side_effect=lambda args, **kw: subprocess.CompletedProcess(args, 1, "", "boom")):
            r = self.look()
        self.assertIn("boom", r["problems"][0])

    def test_no_project(self):
        (self.p / "index.html").unlink()
        self.assertIn("no composed project", self.look()["problems"][0])

    def test_the_cli_and_the_tool_offer_it(self):
        self.assertIn("look", (ROOT / "tt_shorts" / "engine.py").read_text(encoding="utf-8"))
        self.assertIn("engine compose look", (ROOT / "skills" / "compose" / "SKILL.md").read_text(encoding="utf-8"))


class FilmNovelty(unittest.TestCase):
    """A composed film in variety's words, and the warning it gets."""

    SCENE = '<!-- block {block}: x --><template><script>gsap.to(a, { ease: "expo.out" }); gsap.to(b, { ease: "expo.out" });' \
            'gsap.to(c, { ease: "none" }); gsap.to(d, { ease: "none" }); gsap.to(d, { ease: "none" });</script></template>'

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.p = pathlib.Path(self.dir.name)
        (self.p / "compositions").mkdir()
        hosts = ["s0", "s1", "chrome"]
        (self.p / "index.html").write_text("".join(f'<div data-composition-src="compositions/{h}.html"></div>' for h in hosts),
                                           encoding="utf-8")
        (self.p / "compositions" / "s0.html").write_text(self.SCENE.replace("{block}", "quote"), encoding="utf-8")
        (self.p / "compositions" / "s1.html").write_text("<template><div><svg></svg></div></template>", encoding="utf-8")
        (self.p / "compositions" / "chrome.html").write_text("<template></template>", encoding="utf-8")

    def test_scene_kinds_opening_and_main_ease(self):
        style, kinds = compose.film_style(self.p, "fable-1")
        self.assertEqual(kinds[0], "quote")
        self.assertRegex(kinds[1], r"^own-[0-9a-f]{8}$")
        self.assertEqual(len(kinds), 2)  # the locked chrome is no scene
        self.assertEqual({k: style[k] for k in ("hook", "enter", "music", "template", "transition")},
                         {"hook": "quote", "enter": "expo.out", "music": "fable-1", "template": None,
                          "transition": "composed"})

    def test_a_scene_keeps_its_block_after_an_edit(self):
        path = self.p / "compositions" / "s0.html"
        path.write_text(path.read_text(encoding="utf-8").replace("<template>", "<template><div></div>"), encoding="utf-8")
        self.assertEqual(compose.film_kinds(self.p)[0], "quote")

    def test_notes_are_asked_for_by_name(self):
        self.assertEqual(len(compose.missing_notes(self.p, compose.NOTES)), 2)
        (self.p / "STORYLINES.md").write_text("x", encoding="utf-8")
        (self.p / "SPEC.md").write_text("x", encoding="utf-8")
        self.assertEqual(compose.missing_notes(self.p, compose.NOTES), [])
        self.assertIn("REVIEW.md", compose.missing_notes(self.p, (compose.REVIEW_NOTE,))[0])


class Blocks(unittest.TestCase):
    def test_all_nine_blocks_load_and_validate(self):
        from tt_shorts import blocks
        all_blocks = blocks.list_all()
        expected = {"kinetic-headline", "number-reveal", "map-pin", "comparison",
                    "icon-grid", "quote", "process", "chapter-card", "end-card", "plate"}
        self.assertEqual(set(all_blocks.keys()), expected)
        for bid in expected:
            m, tpl = blocks.get(bid)
            self.assertEqual(m["id"], bid)
            self.assertTrue(m.get("label"))
            self.assertTrue(m.get("about"))
            self.assertIn("slots", m)
            self.assertIn("beats", m)
            rendered = blocks.render_block(bid, "s0", {})
            self.assertIn("<template>", rendered)
            self.assertIn('data-composition-id="s0"', rendered)
            self.assertIn('window.__timelines["s0"] = tl;', rendered)

    def test_scaffold_with_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "proj"
            r = compose.scaffold(ROOT / "stories" / "24835.json", brand="sitech", project=p,
                                 blocks="kinetic-headline,number-reveal,end-card", force=True)
            self.assertTrue(r["built"])
            self.assertEqual(r["origin"], "blocks: kinetic-headline,number-reveal,end-card")
            self.assertTrue((p / "compositions" / "s0.html").exists())
            self.assertTrue((p / "compositions" / "s1.html").exists())
            self.assertTrue((p / "compositions" / "s2.html").exists())
            self.assertTrue((p / "index.html").exists())
            self.assertTrue((p / "beats.json").exists())
            lint_problems = compose.lint(p)
            self.assertEqual(lint_problems, [])


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
