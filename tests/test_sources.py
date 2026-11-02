"""The document sources: a web page, a PDF, Georgian law through Ordo, a SiTech blog post. No network: saved pages,
a PDF built here, and a fake Ordo module that answers like the real one (its answer is a real one, saved)."""
import importlib.util
import json
import os
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from tt_shorts import sources
from tt_shorts.sources import ordo, pdf, sitech, url, web

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ROOT / "tests" / "fixtures" / "pages"
ARTICLE = json.loads((ROOT / "tests" / "fixtures" / "ordo" / "constitution-17.json").read_text(encoding="utf-8"))
CHROME = ("მთავარი", "ქუქი", "გაზიარება", "კომენტარები", "მივალ შაბათს", "ყველაზე კითხვადი", "გზების შეკეთება",
          "ყველა უფლება დაცულია", "tracking", "ყველაზე ახალი ამბები")


class Url(unittest.TestCase):
    html = (PAGES / "article.html").read_text(encoding="utf-8")
    link = "https://www.city-news.ge/news/batumi-library.html"

    def check(self, data, extractor):
        c, text = data["cluster"], data["articles"][0]
        self.assertEqual(c["extractor"], extractor)
        self.assertEqual(c["headline"], "ბათუმში ახალი ბიბლიოთეკა გაიხსნა")  # the site's name cut off the title
        self.assertEqual(c["sources"], ["ქალაქის ამბები"])
        self.assertEqual((c["created_at"], c["published"]), ("2026-10-30T10:20:00Z", "2026-10-30"))  # +04:00 -> UTC
        self.assertEqual((c["id"], c["url"]), ("city-news-ge-batumi-library", self.link))
        for fact in ("12 000 წიგნი", "10:00-დან 20:00-მდე", "15 კომპიუტერი", "რა იქნება შემდეგ", "2027 წელს"):
            self.assertIn(fact, text)
        for junk in CHROME:
            self.assertNotIn(junk, text, junk)
        self.assertNotIn("ბათუმი", text.split("\n"))  # the tag links
        self.assertEqual(text.count("ბათუმში ახალი ბიბლიოთეკა გაიხსნა"), 1)

    def test_the_stdlib_extractor_keeps_the_article_and_drops_the_chrome(self):
        self.check(url.parse(self.html, self.link, extractor="stdlib"), "stdlib")

    @unittest.skipUnless(importlib.util.find_spec("trafilatura"), "trafilatura not installed")
    def test_trafilatura_when_installed(self):
        self.check(url.parse(self.html, self.link), "trafilatura")

    def test_without_trafilatura_the_fallback_runs(self):
        with mock.patch.object(url, "_trafilatura", return_value=None):
            self.check(url.parse(self.html, self.link), "stdlib")

    def test_a_saved_file_is_a_ref_and_an_empty_page_is_refused(self):
        data = url.fetch(str(PAGES / "article.html"))
        self.assertEqual((data["cluster"]["id"], data["cluster"]["url"]), ("article", ""))  # no link to a local file
        with self.assertRaises(sources.SourceError):
            url.parse("<html><body><nav><p>მთავარი გვერდი და ძიება</p></nav></body></html>", "https://x.ge/a")
        with self.assertRaises(sources.SourceError):
            url.fetch("not a url")

    def test_dates(self):
        self.assertEqual(web.iso_utc("Mon, 02 Nov 2026 16:03:00 GMT"), "2026-11-02T16:03:00Z")
        self.assertEqual(web.iso_utc("2026-11-02T20:03:00+04:00"), "2026-11-02T16:03:00Z")
        self.assertIsNone(web.iso_utc("2026-11-02"))  # a bare date has no time for the header


def tiny_pdf(text):
    """A one-page PDF with Helvetica text (enough for pypdf and pdftotext)."""
    stream = f"BT /F1 12 Tf 72 720 Td 14 TL ({text[0]}) Tj " + " ".join(f"T* ({t}) Tj" for t in text[1:]) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            "<< /Title (City Library Report) /CreationDate (D:20261030142000+04'00') >>"]
    out, offsets = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


@unittest.skipUnless(importlib.util.find_spec("pypdf") or shutil.which("pdftotext"), "no PDF reader")
class Pdf(unittest.TestCase):
    LINES = ["The city library opened on 30 October 2026 with 12000 books.",
             "It has 40 reading places and 15 computers for visitors.",
             "The library is open every day from 10:00 to 20:00 and entry is free.",
             "Two smaller branches are planned for 2027 in other districts of the city."]

    def test_a_pdf_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d, "library-report.pdf")
            path.write_bytes(tiny_pdf(self.LINES))
            data = pdf.fetch(str(path))
        c, text = data["cluster"], data["articles"][0]
        self.assertEqual((c["id"], c["headline"], c["created_at"]),
                         ("library-report", "City Library Report", "2026-10-30T10:20:00Z"))
        for fact in ("12000 books", "15 computers", "2027"):
            self.assertIn(fact, text)

    def test_from_bytes_and_a_non_pdf(self):
        data = pdf.from_bytes(tiny_pdf(self.LINES), "https://city.ge/docs/report.pdf?x=1")
        self.assertEqual((data["cluster"]["id"], data["cluster"]["sources"], data["cluster"]["url"]),
                         ("report", ["city.ge"], "https://city.ge/docs/report.pdf?x=1"))
        with self.assertRaises(sources.SourceError):
            pdf.fetch("no-such-file.pdf")

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext not installed")
    def test_pdftotext_when_pypdf_is_missing(self):
        with mock.patch.object(pdf, "_pypdf", return_value=None):
            data = pdf.from_bytes(tiny_pdf(self.LINES), "https://city.ge/report.pdf")
        self.assertIn("15 computers", data["articles"][0])

    def test_pdf_dates(self):
        self.assertEqual(pdf.pdf_date("D:20261102143000+04'00'"), "2026-11-02T10:30:00Z")
        self.assertEqual(pdf.pdf_date("D:20261102143000Z"), "2026-11-02T14:30:00Z")
        self.assertIsNone(pdf.pdf_date("D:2026"))


class Ordo(unittest.TestCase):
    """The adapter around Ordo's matsne_api.py, with a fake module that records its calls."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        fixture = ROOT / "tests" / "fixtures" / "ordo" / "constitution-17.json"
        pathlib.Path(self.dir.name, "matsne_api.py").write_text(
            "import json, pathlib\n"
            "CALLS = []\n"
            "ANSWER = None\n"
            "class MatsneAPI:\n"
            "    def __init__(self, lang='ka', rate_limit=0.3):\n"
            "        pass\n"
            "    def get_article(self, article, law='', doc_id=0, part=None, publication=None, as_of_date='', lang='ka'):\n"
            "        CALLS.append(dict(article=article, law=law, doc_id=doc_id, part=part))\n"
            "        if ANSWER is not None:\n"
            "            return ANSWER\n"
            f"        r = json.loads(pathlib.Path({str(fixture)!r}).read_text(encoding='utf-8'))\n"
            "        r.pop('_fetched', None)\n"
            "        if part is not None:\n"
            "            r['part'], r['part_text'] = part, '4. ყველას აქვს ინტერნეტზე წვდომისა და ინტერნეტით თავისუფლად სარგებლობის უფლება.'\n"
            "        return r\n", encoding="utf-8")
        pathlib.Path(self.dir.name, "pyproject.toml").write_text('[project]\nname = "ordo-mcp"\nversion = "0.3.0"\n')
        self.env = mock.patch.dict(os.environ, {"ORDO_DIR": self.dir.name})
        self.env.start()
        ordo.reset()

    def tearDown(self):
        self.env.stop()
        ordo.reset()
        self.dir.cleanup()

    def test_constitution_article_17(self):
        data = sources.fetch("ordo", "constitution:17")
        c, text = data["cluster"], data["articles"][0]
        self.assertEqual(ordo.module().CALLS[-1], {"article": "17", "law": "constitution", "doc_id": 0, "part": None})
        self.assertEqual((c["id"], c["category"], c["sources"], c["article"], c["title"], c["doc_id"]),
                         ("constitution-17", "law", ["matsne.gov.ge"], "17", "საქართველოს კონსტიტუცია", 30346))
        self.assertEqual((c["url"], c["version_date"], c["publication"]), (ARTICLE["url"], "29/06/2020", 36))
        self.assertTrue(text.startswith("საქართველოს კონსტიტუცია\nმუხლი 17. აზრის"))
        self.assertIn("2. ყოველ ადამიანს აქვს უფლება თავისუფლად მიიღოს და გაავრცელოს ინფორმაცია.", text)
        self.assertNotIn("#", text)  # matsne's page furniture
        self.assertNotIn("№1324", text)  # the amending acts are metadata, not the article
        self.assertEqual(len(c["amended_by"]), 2)
        self.assertEqual(ordo.version(), "0.3.0")

    def test_refs(self):
        self.assertEqual(ordo.parse_ref("constitution:17"), ("constitution", "17", None))
        self.assertEqual(ordo.parse_ref("სამოქალაქო კოდექსი:361:2"), ("სამოქალაქო კოდექსი", "361", 2))
        self.assertEqual(ordo.parse_ref("31702:1507^1"), ("31702", "1507^1", None))
        for bad in ("constitution", "constitution:", "constitution:seventeen"):
            with self.assertRaises(sources.SourceError):
                ordo.parse_ref(bad)
        sources.fetch("ordo", "30346:17")
        self.assertEqual(ordo.module().CALLS[-1]["doc_id"], 30346)  # a matsne id goes as doc_id

    def test_one_part(self):
        data = sources.fetch("ordo", "constitution:17:4")
        self.assertEqual(data["cluster"]["id"], "constitution-17-4")
        self.assertEqual(data["articles"][0].split("\n")[2], "4. ყველას აქვს ინტერნეტზე წვდომისა და ინტერნეტით "
                                                             "თავისუფლად სარგებლობის უფლება.")
        self.assertNotIn("ცენზურა", data["articles"][0])

    def test_errors(self):
        mod = ordo.module()
        mod.ANSWER = {"doc_id": 30346, "error": "HTML fetch failed: ERROR: <urlopen error timed out>"}
        with self.assertRaises(ConnectionError):  # the queue retries it later
            ordo.fetch("constitution:17")
        mod.ANSWER = {"doc_id": 30346, "error": "Article 999 not found in this version"}
        with self.assertRaises(sources.SourceError):
            ordo.fetch("constitution:999")
        mod.ANSWER = {**ARTICLE, "status": "expired"}
        with self.assertRaises(sources.SourceError):
            ordo.fetch("constitution:17")
        with mock.patch.dict(os.environ, {"ORDO_DIR": "/nonexistent/ordo"}):
            ordo.reset()
            self.assertFalse(ordo.available())
            with self.assertRaises(RuntimeError) as e:
                ordo.fetch("constitution:17")
            self.assertIn("requires", str(e.exception))  # the queue classes it as config


class Sitech(unittest.TestCase):
    page = (PAGES / "sitech-post.html").read_text(encoding="utf-8")

    def test_a_post(self):
        data = sitech.parse(self.page, "acme-chip", published="2026-11-02T16:03:00Z")
        c, text = data["cluster"], data["articles"][0]
        self.assertEqual((c["id"], c["url"], c["created_at"]), ("acme-chip", "https://sitech.ge/ka/blog/acme-chip/",
                                                              "2026-11-02T16:03:00Z"))
        self.assertEqual(c["headline"], "Acme-მ ახალი ჩიპი წარადგინა, რომელიც 40%-ით სწრაფია")
        self.assertEqual(c["sources"], ["sitech.ge", "example-news.com"])  # the outlet the post reports from
        self.assertEqual(c["category"], "hardware")
        for fact in ("16 ბირთვი", "20 საათამდე", "2027 წლიდან"):
            self.assertIn(fact, text)
        for junk in ("იტვირთება", "SiTech ბლოგი", "ვქმნით სწრაფ"):
            self.assertNotIn(junk, text)

    def test_slugs_and_the_feed(self):
        self.assertEqual(sitech.slug_of("https://sitech.ge/ka/blog/acme-chip/"), "acme-chip")
        self.assertEqual(sitech.slug_of("acme-chip"), "acme-chip")
        with self.assertRaises(sources.SourceError):
            sitech.slug_of("../../etc/passwd")
        rss = (b'<?xml version="1.0"?><rss><channel><item><link>https://sitech.ge/ka/blog/acme-chip/</link>'
               b'<pubDate>Mon, 02 Nov 2026 16:03:00 GMT</pubDate></item></channel></rss>')
        self.assertEqual(sitech.rss_times(rss), {"acme-chip": "2026-11-02T16:03:00Z"})
        self.assertEqual(sitech.rss_times(b"not xml"), {})


class Registry(unittest.TestCase):
    def test_every_source_is_known_and_described(self):
        self.assertEqual(set(sources.KNOWN), set(sources.ABOUT))
        for name in sources.KNOWN:
            self.assertTrue(callable(sources.get(name).fetch), name)
        with self.assertRaises(sources.SourceError):
            sources.get("telegram")


if __name__ == "__main__":
    unittest.main()
