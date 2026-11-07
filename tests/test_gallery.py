"""The brush book (`engine gallery`): the catalogue is read from data, search finds the right brush, the examples pass
`check`, and every picture the catalogue promises is a real file (once `engine gallery --real` has rendered them)."""
import json
import pathlib
import tempfile
import unittest

import shutil
from unittest import mock

from tt_shorts import brand, catalog, compose, directors, engine, gallery, props, rubrics, styles, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Catalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = gallery.items()
        cls.by_id = {i["id"]: i for i in cls.items}

    def test_every_brush_look_theme_is_promised(self):
        themes = brand.theme_names(brand.load(brand.DEFAULT))
        for t in catalog.types():
            files = self.by_id[f"brush-{t}"]["files"]
            self.assertEqual(set(files), {f"{lk}/{th}" for lk in brand.LOOKS for th in themes}, t)
            self.assertEqual(len(set(files.values())), len(files), "one file each")

    def test_every_other_item_is_listed(self):
        want = {f"hook-{o}" for o in variety.OPTIONS["hook"]} | {f"motif-{o}" for o in variety.OPTIONS["motif"]} \
            | {f"entrance-{o}" for o in variety.OPTIONS["enter"]} | {f"director-{d}" for d in directors.load_all()} \
            | {f"style-{s['slug']}" for s in styles.load_all()} | {f"rubric-{r}" for r in rubrics.load_all()} \
            | {f"transition-{t}" for t in props.TRANSITIONS} | {f"block-{b}" for b in compose.blocks()}             | {f"template-{t}" for t in compose.templates()}
        self.assertEqual(want - set(self.by_id), set())

    def test_ids_and_files_are_unique(self):
        self.assertEqual(len(self.by_id), len(self.items))
        files = gallery.expected_files(self.items)
        self.assertEqual(len(files), len(set(files)))

    def test_every_entry_says_when_and_has_a_command(self):
        for i in self.items:
            self.assertTrue(i["use_when"] and i["command"] and i["what"], i["id"])
            self.assertIsInstance(i["avoid_when"], str, i["id"])

    def test_plate_posters_are_read_from_disk_when_they_exist(self):
        kind = pathlib.Path(gallery.ROOT) / "plates" / "zz-test-kind"
        kind.mkdir()
        try:
            (kind / "poster.png").write_bytes(b"x")
            self.assertIn("plate-zz-test-kind", {i["id"] for i in gallery.items()})
        finally:
            (kind / "poster.png").unlink()
            kind.rmdir()
        self.assertNotIn("plate-zz-test-kind", {i["id"] for i in gallery.items()})


class AddedLater(unittest.TestCase):
    """What another lane merges later (a brush, a block, a template, a plate, a variety option) is in the book after a
    rebuild with no change to gallery.py: each is added here as a throwaway fixture and removed again."""

    def test_new_brush_block_template_plate_and_option_appear_by_themselves(self):
        made = []
        try:
            brush = json.loads((ROOT / "brushes" / "stat.json").read_text(encoding="utf-8"))
            brush["type"], brush["order"] = "zzfixture", 997
            brush["schema"]["type"] = brush["example"]["type"] = "zzfixture"
            (ROOT / "brushes" / "zzfixture.json").write_text(json.dumps(brush, ensure_ascii=False), encoding="utf-8")
            made.append(ROOT / "brushes" / "zzfixture.json")
            shutil.copytree(ROOT / "compose" / "blocks" / "quote", ROOT / "compose" / "blocks" / "zz-block")
            made.append(ROOT / "compose" / "blocks" / "zz-block")
            shutil.copytree(ROOT / "templates" / "news-kinetic", ROOT / "templates" / "zz-template")
            made.append(ROOT / "templates" / "zz-template")
            (ROOT / "plates" / "zz-plate").mkdir()
            (ROOT / "plates" / "zz-plate" / "poster.png").write_bytes(b"x")
            made.append(ROOT / "plates" / "zz-plate")
            catalog._load.cache_clear()  # the engine reads brushes once per process; a rebuild is a new process
            with mock.patch.dict(variety.OPTIONS, {"hook": (*variety.OPTIONS["hook"], "zz-hook")}):
                items = {i["id"]: i for i in gallery.items()}
                page = gallery.build_page(list(items.values()), out_dir=pathlib.Path(__import__("tempfile").mkdtemp()))
            for want in ("brush-zzfixture", "block-zz-block", "template-zz-template", "plate-zz-plate", "hook-zz-hook"):
                self.assertIn(want, items, want)
                self.assertIn(f'id="{want}"', page.read_text(encoding="utf-8"))
            self.assertEqual(len(items["brush-zzfixture"]["files"]), len(brand.LOOKS) * len(gallery.themes()))
            self.assertTrue(items["block-zz-block"]["files"][""].endswith("block-zz-block.jpg"))
            self.assertIn("compose scaffold <story> --blocks zz-block", items["block-zz-block"]["command"])
            self.assertEqual(gallery.find("zzfixture", list(items.values()), n=1)[0]["id"], "brush-zzfixture")
        finally:
            for m in made:
                shutil.rmtree(m) if m.is_dir() else m.unlink()
            catalog._load.cache_clear()
        ids = {i["id"] for i in gallery.items()}
        self.assertFalse({"brush-zzfixture", "block-zz-block", "template-zz-template", "plate-zz-plate"} & ids)


class Search(unittest.TestCase):
    def top(self, q, n=3):
        return [m["id"] for m in gallery.find(q, n=n)]

    def test_a_need_finds_its_brush_in_the_first_three(self):
        for q, want in (("a number", "brush-stat"), ("a place", "brush-where"), ("a process", "brush-steps"),
                        ("a quote", "brush-quote"), ("a ranking", "brush-ranking"), ("percent of a whole", "brush-share"),
                        ("compare two things", "brush-compare"), ("dates and a deadline", "brush-countdown")):
            self.assertIn(want, self.top(q), q)

    def test_a_match_carries_what_an_agent_needs(self):
        m = gallery.find("a number")[0]
        self.assertEqual(set(m), {"id", "type", "need", "command", "still", "when_not_to_use"})

    def test_nonsense_finds_nothing(self):
        self.assertEqual(gallery.find("zzzxqv"), [])


class Page(unittest.TestCase):
    def test_the_page_is_one_file_with_every_entry_and_a_search(self):
        with tempfile.TemporaryDirectory() as td:
            target = gallery.build_page(out_dir=pathlib.Path(td))
            page = target.read_text(encoding="utf-8")
        for i in gallery.items():
            self.assertIn(f'id="{i["id"]}"', page)
        self.assertIn('type="search"', page)
        self.assertIn("width=device-width", page)
        self.assertNotRegex(page, r'(src|href)="https?://', "no network: one file")


class Examples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ROOT / "examples" / "index.json").read_text(encoding="utf-8"))

    def load(self, rel):
        return json.loads((ROOT / "examples" / rel).read_text(encoding="utf-8"))

    def test_twelve_films_across_programs_pass_check(self):
        self.assertEqual(len(self.index["films"]), 12)
        self.assertTrue({"news", "digest", "explainer", "law", "story"} <= {f["program"] for f in self.index["films"]})
        for f in self.index["films"]:
            for key in ("asked", "shape", "turned_down", "learn"):
                self.assertGreater(len(f[key]), 30, f"{f['id']}.{key}")
            story = self.load(f["file"])
            self.assertEqual(engine.check_story(story), [], f["id"])
            self.assertEqual([s["type"] for s in story["scenes"]], f["scenes"])
            self.assertTrue(set(f["scenes"]) <= set(catalog.types()), f["id"])

    def test_six_pairs_bad_fails_with_its_line_and_fixed_passes(self):
        self.assertEqual(len(self.index["pairs"]), 6)
        for p in self.index["pairs"]:
            bad = engine.check_story(self.load(p["bad"]))
            self.assertTrue(any(p["check_says"] in x for x in bad), (p["id"], bad))
            self.assertEqual(engine.check_story(self.load(p["fixed"])), [], p["id"])
            self.assertGreater(len(p["why"]) + len(p["fix"]), 60)

    def test_rotation_is_deterministic_and_varies(self):
        a, b = gallery.examples("s1"), gallery.examples("s1")
        self.assertEqual(a, b)
        firsts = {gallery.examples(str(n))["films"][0]["id"] for n in range(12)}
        self.assertGreater(len(firsts), 4)
        self.assertEqual(len(a["films"]), 3)
        self.assertTrue(all(f["program"] == "law" for f in gallery.examples("x", program="law")["films"]))


class RealFiles(unittest.TestCase):
    """The evidence for "a real file for every brush x look x theme and every other item": needs `engine gallery --real`
    to have run on this machine (minutes of machine time, so the unit run skips it when nothing is rendered)."""

    def test_every_promised_file_is_a_real_picture(self):
        if not (gallery.OUT / "manifest.json").exists():
            self.skipTest("out/gallery is not rendered here: run `python -m tt_shorts.engine gallery --real`")
        from PIL import Image
        missing, small = [], []
        for rel in gallery.expected_files():
            if rel.startswith("plates/"):
                continue
            p = gallery.resolve(rel)
            if not p.is_file():
                missing.append(rel)
                continue
            with Image.open(p) as im:
                if im.size[0] < 200 or im.size[1] < 200:
                    small.append(rel)
        self.assertEqual(missing, [], f"{len(missing)} promised pictures are missing")
        self.assertEqual(small, [])

    def test_the_manifest_names_a_reproduce_command_for_every_brush_still(self):
        man = gallery.OUT / "manifest.json"
        if not man.exists():
            self.skipTest("out/gallery is not rendered here")
        data = json.loads(man.read_text(encoding="utf-8"))
        for rel, row in data.items():
            if rel.startswith("stills/brush-"):
                self.assertRegex(row["command"], r"^python -m tt_shorts\.engine still .+ --frames \d+$", rel)


if __name__ == "__main__":
    unittest.main()
