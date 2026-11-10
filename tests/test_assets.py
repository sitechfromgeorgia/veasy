"""The media layer (assets.py, media/): licences, the ledger, a deterministic pick, local files only. No network:
every provider's HTTP is replaced by fixtures."""
import io
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from tt_shorts import assets, brand, catalog, engine, programs, store
from tt_shorts.media import MediaError, commons, files, openverse, pexels, pixabay, screenshot

ROOT = pathlib.Path(__file__).resolve().parent.parent

OPENVERSE = {"results": [
    {"id": "a1", "title": "Gas pipes", "creator": "Elsie", "license": "by", "license_version": "2.0",
     "url": "https://live.staticflickr.com/1/a1.jpg", "foreign_landing_url": "https://flickr.com/a1", "width": 1024,
     "height": 768, "source": "flickr", "mature": False, "tags": [{"name": "pipe"}]},
    {"id": "a2", "title": "Gas pipeline", "creator": "Bob", "license": "by-nc", "license_version": "2.0",
     "url": "https://live.staticflickr.com/1/a2.jpg", "width": 1200, "height": 1600, "source": "flickr"},
    {"id": "a3", "title": "Natural gas pipeline and a fire", "creator": "NTSB", "license": "pdm",
     "url": "https://live.staticflickr.com/1/a3.jpg", "width": 1024, "height": 1400, "source": "flickr"},
    {"id": "a4", "title": "Gas pipeline, Kakheti", "creator": "", "license": "cc0", "license_version": "1.0",
     "url": "https://live.staticflickr.com/1/a4.jpg", "width": 1200, "height": 1600, "source": "flickr"},
    {"id": "a5", "title": "Gas pipe", "creator": "C", "license": "by-sa", "license_version": "4.0",
     "url": "https://upload.wikimedia.org/a5.jpg", "width": 1200, "height": 1600, "source": "wikimedia"},
    {"id": "a6", "title": "ClimateStrike march", "creator": "D", "license": "by", "license_version": "2.0",
     "url": "https://live.staticflickr.com/1/a6.jpg", "width": 1200, "height": 1600, "source": "flickr"},
]}
COMMONS = {"query": {"pages": {
    "11": {"pageid": 11, "index": 2, "title": "File:Gas pipe bridge.jpg", "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/11.jpg", "thumbwidth": 1600, "thumbheight": 1200,
        "mime": "image/jpeg", "descriptionurl": "https://commons.wikimedia.org/wiki/File:11",
        "extmetadata": {"License": {"value": "cc-by-sa-4.0"}, "Artist": {"value": "<a href='//x'>Szombat &amp; Co</a>"},
                        "ObjectName": {"value": "Gas pipe bridge"}}}]},
    "12": {"pageid": 12, "index": 1, "title": "File:Gas logo.png", "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/12.png", "mime": "image/png",
        "extmetadata": {"License": {"value": "cc0"}, "Restrictions": {"value": "trademarked"}}}]},
    "13": {"pageid": 13, "index": 3, "title": "File:Gas pipe.jpg", "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/13.jpg", "mime": "image/jpeg",
        "extmetadata": {"License": {"value": "gfdl"}}}]},
    "14": {"pageid": 14, "index": 4, "title": "File:Old gas pipe.jpg", "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/14.jpg", "thumbwidth": 1600, "thumbheight": 2000,
        "mime": "image/jpeg", "extmetadata": {"License": {"value": "pd"}, "Artist": {"value": "Unknown"}}}]},
}}}


def jpeg(w=1200, h=1600, color=(90, 120, 150)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG")
    return buf.getvalue()


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()
        for k in ("PEXELS_API_KEY", "PIXABAY_API_KEY"):
            os.environ.pop(k, None)
        brand.load.cache_clear()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
        brand.load.cache_clear()


class Providers(Home):
    def test_openverse_keeps_only_commercial_licences(self):
        with mock.patch.object(openverse, "get_json", return_value=OPENVERSE) as g:
            got = openverse.search("gas pipeline", "photo", 20)
        url = g.call_args[0][0]
        self.assertIn("license=cc0%2Cpdm%2Cby%2Cby-sa", url)
        self.assertEqual([c["id"] for c in got], ["a1", "a3", "a4", "a6"])  # by-nc and Wikimedia's are dropped
        self.assertEqual(got[0]["licence"], "by")
        self.assertEqual(got[0]["source"], "Flickr")
        self.assertEqual(openverse.search("x", "video"), [])

    def test_commons_maps_the_licence_and_drops_restricted_files(self):
        with mock.patch.object(commons, "get_json", return_value=COMMONS):
            got = commons.search("gas pipe", "photo", 10)
        self.assertEqual([(c["id"], c["licence"], c["licence_version"]) for c in got],
                         [("11", "by-sa", "4.0"), ("14", "pdm", "1.0")])  # trademarked and GFDL-only are dropped
        self.assertEqual(got[0]["author"], "Szombat & Co")  # HTML metadata to text
        self.assertTrue(got[0]["url"].startswith("https://upload.wikimedia.org/thumb/"))  # the thumbnail, not 50 MB
        self.assertEqual(commons.licence({"License": "cc-by-3.0-de"}), ("by", "3.0"))
        self.assertEqual(commons.licence({"License": "cc-by-nc-2.0"}), (None, ""))

    def test_keyed_providers_are_skipped_without_a_key(self):
        for mod in (pexels, pixabay):
            self.assertIn("is not set", mod.available())
            with mock.patch.object(mod, "get_json", side_effect=AssertionError("no call without a key")):
                self.assertEqual(mod.search("gas", "photo"), [])
        avail = assets.availability()
        self.assertIsNone(avail["openverse"])
        self.assertIsNotNone(avail["pexels"])
        self.assertIsNotNone(avail["ai"])  # AI imagery: off until the owner decides

    def test_keyed_providers_with_a_key(self):
        with mock.patch.dict(os.environ, {"PEXELS_API_KEY": "k", "PIXABAY_API_KEY": "secret"}):
            vids = {"videos": [{"id": 5, "url": "https://pexels.com/v/5", "duration": 8, "user": {"name": "Ana"},
                                "video_files": [{"file_type": "video/mp4", "link": "https://v/5-hd.mp4", "width": 1080,
                                                 "height": 1920},
                                                {"file_type": "video/mp4", "link": "https://v/5-4k.mp4", "width": 2160,
                                                 "height": 3840}]}]}
            with mock.patch.object(pexels, "get_json", return_value=vids) as g:
                v = pexels.search("gas", "video")[0]
            self.assertEqual(g.call_args[0][1], {"Authorization": "k"})
            self.assertEqual((v["kind"], v["url"], v["licence"], v["duration"]), ("video", "https://v/5-hd.mp4", "pexels", 8))
            hits = {"hits": [{"id": 9, "pageURL": "https://pixabay.com/9", "largeImageURL": "https://cdn.pixabay.com/9.jpg",
                              "imageWidth": 1280, "imageHeight": 1920, "user": "Lu", "tags": "gas, pipe"}]}
            with mock.patch.object(pixabay, "get_json", return_value=hits):
                p = pixabay.search("gas", "photo")[0]
            self.assertEqual((p["licence"], p["author"]), ("pixabay", "Lu"))
            self.assertNotIn("secret", json.dumps(p))  # the key never reaches a candidate (or a ledger)


class Pick(Home):
    def setUp(self):
        super().setUp()
        self.b = brand.load("tbilisi-today")
        self.cmap = assets.font_cmap(self.b["_fonts"]["400"])

    def test_usable_filters_events_text_and_unrelated_pictures(self):
        cands = [openverse.candidate(r) for r in OPENVERSE["results"]]
        why = {c["id"]: assets.usable(c, self.cmap, "gas pipeline") for c in cands if c}
        self.assertIsNone(why["a1"])
        self.assertIn("fire", why["a3"])  # a picture of an incident never illustrates
        self.assertIsNone(why["a4"])  # cc0 needs no author
        self.assertIn("strike", why["a6"])
        unrelated = {**cands[0], "title": "Sunset over the sea", "tags": []}
        self.assertIn("nothing of the query", assets.usable(unrelated, self.cmap, "gas pipeline"))
        noname = {**cands[0], "author": "   "}
        self.assertEqual(assets.usable(noname, self.cmap, "gas"), "no author to credit")  # CC BY needs one
        self.assertIn("not allowed", assets.usable({**cands[0], "licence": "by-nc"}, self.cmap))
        self.assertIn("too small", assets.usable({**cands[0], "width": 300, "height": 200}, self.cmap))

    def test_order_prefers_free_licences_and_tall_pictures(self):
        c = lambda i, lic, w, h: {"id": i, "licence": lic, "width": w, "height": h}  # noqa: E731
        got = assets.order([c("sa", "by-sa", 1000, 1500), c("by", "by", 1000, 1500), c("wide0", "cc0", 1600, 900),
                            c("tall0", "cc0", 1000, 1500)])
        self.assertEqual([x["id"] for x in got], ["tall0", "wide0", "by", "sa"])  # BY-SA last

    def test_the_pick_is_deterministic_per_story(self):
        cands = [{"id": str(i)} for i in range(10)]
        a = assets.pick(cands, "24835|1|gas")
        self.assertEqual(a, assets.pick(cands, "24835|1|gas"))
        self.assertIn(a, cands[:assets.TOP])
        self.assertGreater(len({assets.pick(cands, f"{n}|1|gas")["id"] for n in range(40)}), 1)  # varied

    def test_the_show_hint(self):
        self.assertEqual(assets.parse_show("gas pipeline repair"), ("photo", "gas pipeline repair"))
        self.assertEqual(assets.parse_show("video: city traffic"), ("video", "city traffic"))
        self.assertEqual(assets.parse_show("screenshot"), ("screenshot", None))
        for bad in ("გაზსადენი", "x" * 90, "a b c d e f g", "", "screenshot:matsne.gov.ge"):
            self.assertTrue(assets.show_problems({"show": bad}), bad)
        for ok in ("gas pipeline repair", "screenshot", "screenshot:https://matsne.gov.ge/x | მუხლი 17", "video: buses"):
            self.assertEqual(assets.show_problems({"show": ok}), [], ok)

    def test_the_credit_line(self):
        e = {"kind": "photo", "licence": "by", "licence_version": "2.0", "author": "Elsie esq.", "source": "Flickr"}
        self.assertEqual(assets.credit(e, self.b), "Elsie esq. · CC BY 2.0 · Flickr")
        self.assertEqual(assets.credit({**e, "author": "", "licence": "cc0"}, self.b), "Flickr · CC0 2.0")
        cjk = assets.credit({**e, "author": "山田 太郎 Yamada"}, self.b)
        self.assertEqual(cjk, "Yamada · CC BY 2.0 · Flickr")  # only glyphs the pack's font has (the probe's glyph rule)
        long = assets.credit({**e, "author": "A very long name of a photographer"}, self.b)
        self.assertLessEqual(len(long), assets.CREDIT_MAX)
        shot = {"kind": "screenshot", "licence": "screenshot", "source": "matsne.gov.ge", "url": "https://matsne.gov.ge/x"}
        self.assertEqual(assets.credit(shot, self.b), "matsne.gov.ge")


def story(**more):
    s = json.loads((ROOT / "stories" / "24835.json").read_text(encoding="utf-8"))
    s["scenes"][1]["show"] = "gas pipeline"
    s["scenes"][3]["show"] = "gas pipeline"  # a where scene never carries a picture
    return {**s, **more}


class Resolve(Home):
    def fake(self):
        stack = mock.patch.multiple
        return (stack(openverse, get_json=mock.MagicMock(return_value=OPENVERSE)),
                stack(commons, get_json=mock.MagicMock(return_value=COMMONS)),
                mock.patch.object(files, "request", side_effect=lambda url, headers=None: (jpeg(), "image/jpeg")))

    def resolve(self, s, **kw):
        a, b, c = self.fake()
        kw.setdefault("providers", ["openverse", "commons"])  # a pack that opted in (the shipped packs haven't)
        with a, b, c:
            return assets.resolve(s, **kw)

    def test_the_shipped_packs_resolve_nothing_until_they_opt_in(self):
        a, b, c = self.fake()
        with a, b, c:  # the sitech pack ships without providers (tbilisi-today opts in)
            new, report = assets.resolve(story(brand="sitech"))
        self.assertNotIn("assets", new)
        self.assertFalse(any(sc.get("media") for sc in new["scenes"]))

    def test_the_tbilisi_pack_opts_into_pictures(self):
        a, b, c = self.fake()
        with a, b, c:  # the pack names its providers, so the same hint now resolves
            new, report = assets.resolve(story(brand="tbilisi-today"))
        self.assertTrue(new.get("assets"))
        self.assertTrue(new["scenes"][1].get("media"))

    def test_a_hint_becomes_a_ledger_entry_and_a_local_file(self):
        new, report = self.resolve(story())
        self.assertEqual(list(report["scenes"]), [1])
        self.assertNotIn("media", new["scenes"][3])  # where: the map is its picture (catalog.NO_MEDIA)
        e = new["assets"][0]
        self.assertEqual(new["scenes"][1]["media"], {"asset": e["id"]})
        self.assertIn(e["licence"], ("cc0", "pdm"))  # the freest licence first
        self.assertTrue((store.home() / e["file"]).is_file())
        self.assertEqual(e["sha"], files.sha256(store.home() / e["file"]))
        self.assertEqual(e["query"], "gas pipeline")
        self.assertEqual(assets.problems(new), [])
        from PIL import Image
        with Image.open(store.home() / e["file"]) as im:
            self.assertLessEqual(max(im.size), files.LONG_SIDE)

    def test_resolving_twice_gives_the_same_picture_without_the_network(self):
        new, _ = self.resolve(story())
        with mock.patch.object(openverse, "get_json", side_effect=AssertionError("no search")), \
                mock.patch.object(files, "request", side_effect=AssertionError("no download")):
            again, report = assets.resolve(new)
        self.assertEqual(again, new)
        self.assertTrue(report["scenes"][1]["kept"])
        other, _ = self.resolve(story())  # a fresh resolve of the same story: the cached search, the same pick
        self.assertEqual(other["assets"][0]["id"], new["assets"][0]["id"])

    def test_no_illustrative_imagery_for_crime(self):
        new, report = self.resolve(story(category="crime"))
        self.assertNotIn("assets", new)
        self.assertIn("N13", report["skipped"])

    def test_a_failing_provider_leaves_the_scene_without_a_picture(self):
        with mock.patch.object(openverse, "get_json", side_effect=MediaError("api.openverse.org: HTTP 503")), \
                mock.patch.object(commons, "get_json", side_effect=MediaError("commons: timed out")):
            new, report = assets.resolve(story())
        self.assertNotIn("assets", new)
        self.assertTrue(report["errors"])

    def test_the_writer_never_sets_media(self):
        s = story()
        s["scenes"][1]["media"] = {"asset": "deadbeefdeadbeef"}
        s["assets"] = [{"id": "x"}]
        self.assertTrue(assets.problems(s))
        assets.strip_code_owned(s)
        self.assertNotIn("media", s["scenes"][1])
        self.assertNotIn("assets", s)

    def test_the_ledger_refuses_licences_that_don_t_allow_commercial_use(self):
        new, _ = self.resolve(story())
        e = new["assets"][0]
        for bad, word in (({"licence": "by-nc"}, "commercial"), ({"licence": "by", "author": ""}, "credited"),
                          ({"licence": "screenshot"}, "screenshot"), ({"sha": "x"}, "sha256"),
                          ({"file": "../etc/x"}, "cache/media"), ({"kind": "hologram"}, "kind")):
            broken = {**new, "assets": [{**e, **bad}]}
            self.assertTrue(any(word in x for x in assets.problems(broken)), bad)
        self.assertTrue(any("not in the story's assets" in x for x in assets.problems({**new, "assets": []})))
        self.assertTrue(engine.check_story({**new, "assets": [{**e, "licence": "by-nc"}]}))

    def test_props_get_local_files_with_label_and_credit(self):
        new, _ = self.resolve(story())
        b = brand.load("tbilisi-today")
        with tempfile.TemporaryDirectory() as public:
            drawn = assets.for_props(new, b, public)
            d = drawn[new["assets"][0]["id"]]
            self.assertTrue((pathlib.Path(public) / d["src"]).is_file())
            self.assertEqual(d["label"], "საილუსტრაციო")
            self.assertEqual((d["kind"], d["what"]), ("image", "photo"))
            self.assertTrue(d["credit"])
            self.assertNotIn("http", json.dumps(drawn))  # an engine never sees a URL

    def test_a_collected_file_is_fetched_again_and_checked(self):
        new, _ = self.resolve(story())
        e = new["assets"][0]
        path = store.home() / e["file"]
        path.unlink()
        (path.parent / "asset.json").unlink()
        with mock.patch.object(files, "request", side_effect=lambda url, headers=None: (jpeg(), "image/jpeg")):
            self.assertEqual(assets.local_file(e), path)
        path.unlink()
        with mock.patch.object(files, "request", side_effect=lambda url, headers=None: (jpeg(color=(1, 2, 3)), "x")):
            with self.assertRaises(MediaError):
                assets.local_file(e)  # not the same file: never drawn silently

    def test_gc_keeps_media_for_90_days(self):
        d = store.media_dir("openverse:a1")
        self.assertEqual(d.parent.name, "media")
        self.assertEqual(len(d.name), 16)
        removed = store.gc(dry_run=True, now=d.stat().st_mtime + 89 * 86400)
        self.assertEqual(removed["media"], [])
        removed = store.gc(dry_run=True, now=d.stat().st_mtime + 91 * 86400)
        self.assertEqual(removed["media"], [str(d)])


class Screenshots(Home):
    ALLOW = ["matsne.gov.ge", "gov.ge", "tbilisi.today"]

    def test_the_allow_list(self):
        for url in ("https://matsne.gov.ge/ka/document/view/1", "https://www.mof.gov.ge/x", "https://tbilisi.today/s/1"):
            self.assertTrue(screenshot.allowed(url, self.ALLOW), url)
        for url in ("https://interpressnews.ge/ka/article/1", "https://gov.ge.example.com/", "ftp://matsne.gov.ge/",
                    "https://notgov.ge/", "matsne.gov.ge/x"):
            self.assertFalse(screenshot.allowed(url, self.ALLOW), url)

    def test_capture_refuses_a_publisher_page_before_opening_it(self):
        run = mock.MagicMock()
        with self.assertRaises(MediaError) as e:
            screenshot.capture("https://interpressnews.ge/ka/article/1", self.ALLOW, run=run)
        self.assertIn("N13", str(e.exception))
        run.assert_not_called()

    def test_capture_drives_the_node_script_and_checks_where_it_landed(self):
        def fake(cmd, **kw):
            out = pathlib.Path(cmd[cmd.index("--out") + 1])
            out.write_bytes(b"\x89PNG fake")
            landed = "https://example.com/" if "redirect" in cmd[cmd.index("--url") + 1] else cmd[cmd.index("--url") + 1]
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"ok": True, "url": landed, "title": "მაცნე",
                                                                   "found": True, "box": [1, 2, 3, 4]}) + "\n", "")
        with mock.patch.object(screenshot, "chrome", return_value="chrome.exe"), \
                mock.patch.object(screenshot.shutil, "which", return_value="node"):
            c = screenshot.capture("https://matsne.gov.ge/ka/document/view/30346", self.ALLOW, "მუხლი 17", run=fake)
            self.assertEqual((c["kind"], c["licence"], c["source"], c["box"]), ("screenshot", "screenshot",
                                                                               "matsne.gov.ge", [1, 2, 3, 4]))
            self.assertTrue(pathlib.Path(c["file"]).is_file())
            with self.assertRaises(MediaError):
                screenshot.capture("https://matsne.gov.ge/redirect", self.ALLOW, run=fake)
            self.assertFalse((files.folder({"provider": "screenshot", "id": "https://matsne.gov.ge/redirect|"}) /
                              "shot.png").exists())  # refused, not kept

    def test_the_allow_list_is_data(self):
        s = {"brand": "tbilisi-today", "program": "law", "scenes": []}
        allow = assets.allow_list(s)
        self.assertIn("matsne.gov.ge", allow)
        self.assertIn("tbilisi.today", allow)
        self.assertEqual(programs.get("law")["screenshots"], ["matsne.gov.ge"])
        with self.assertRaises(programs.ProgramError):
            programs.validate("x", {**programs.load_all()["law"], "screenshots": ["https://matsne.gov.ge"]})


class Catalog(unittest.TestCase):
    def test_show_is_every_scene_s_and_media_is_code_s(self):
        self.assertIn("show", catalog.UNIVERSAL)
        self.assertNotIn("media", catalog.UNIVERSAL)
        self.assertIn('"show" (optional', catalog.schema())
        self.assertNotIn('"show" (optional', catalog.schema(["end"]))
        self.assertTrue(set(catalog.NO_MEDIA) <= set(catalog.types()))


if __name__ == "__main__":
    unittest.main()
