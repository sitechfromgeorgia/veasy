"""A SiTech blog post (sitech.ge) as a source, read the way sitech-shorts' articles.py reads it (ROADMAP B13).

    python -m tt_shorts.engine write --program blog --source sitech --ref <slug> --brand sitech

ref is the post's slug (or its URL). The post is read in Georgian (/ka/blog/<slug>/: the blog publishes every post in
8 languages, sitech-shorts' "variant A" writes from the Georgian one): the BlogPosting ld+json gives the headline,
lead and date, the page's classless <p>/<h2> are the body (styled ones are site chrome), and its "Sources:" line
names the outlet the post reports from. The RSS feed gives the exact publishing time when the post is still in it.
The cluster id is the slug, so the sitech pack's QR opens the post (link.qr ".../blog/{id}/").
"""
import html as html_lib
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from tt_shorts.sources import SourceError, web

SITE = "https://sitech.ge"
RSS = f"{SITE}/rss.xml"
DOMAIN = "sitech.ge"
# A first guess at the pack's category (brands/sitech); the writer may choose another of the pack's categories.
CATEGORY_HINTS = (
    ("security", r"უსაფრთხოებ|კიბერ|ჰაკერ|ხარვეზ|შეტევ|გაჟონ|გამომძალველ|ფიშინგ|\bSSH\b|\bCVE-|ransomware|breach"),
    ("ai", r"ხელოვნურ\w* ინტელექტ|\bAI\b|ChatGPT|OpenAI|Anthropic|Claude|Gemini|\bLLM\b|ენობრივ\w* მოდელ"),
    ("hardware", r"ჩიპ|\bGPU\b|პროცესორ|სმარტფონ|iPhone|ლეპტოპ|ეკრან|\bAMD\b|Intel|Qualcomm"),
    ("development", r"დეველოპერ|პროგრამირ|GitHub|\bAPI\b|Linux|ღია კოდ|ბიბლიოთეკ|ფრეიმვორკ"),
    ("business", r"ინვესტიცი|დაფინანსებ|შემოსავ|აქციებ|გარიგებ|შეიძენს|შეძენ|ბაზრის|ღირებულებ|\bIPO\b"),
)


class _Body(HTMLParser):
    """The post's h2/p text: classless paragraphs only (styled ones are the site's chrome)."""

    def __init__(self):
        super().__init__()
        self.parts, self._tag, self._buf = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "h2") and not dict(attrs).get("class") and not dict(attrs).get("style"):
            self._tag, self._buf = tag, []

    def handle_endtag(self, tag):
        if tag == self._tag:
            text = " ".join("".join(self._buf).split())
            if text:
                self.parts.append(text)
            self._tag = None

    def handle_data(self, data):
        if self._tag:
            self._buf.append(data)


def slug_of(ref):
    m = re.search(r"/blog/([^/?#]+)/?", str(ref))
    slug = m.group(1) if m else str(ref).strip().strip("/")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise SourceError(f"sitech: {ref!r} is not a blog post slug (lowercase letters, digits, hyphens)")
    return slug


def page_url(slug, lang="ka"):
    return f"{SITE}/{lang}/blog/{slug}/"


def rss_times(xml_bytes):
    """{slug: published UTC ISO} from the feed."""
    out = {}
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return out
    for item in root.iter("item"):
        m = re.search(r"/blog/([^/]+)/?$", item.findtext("link") or "")
        when = web.iso_utc(item.findtext("pubDate"))
        if m and when:
            out[m.group(1)] = when
    return out


def category(text):
    for cat, pattern in CATEGORY_HINTS:
        if re.search(pattern, text):
            return cat
    return "other"


def parse(page, slug, published=None):
    """The post's HTML -> the source payload. published: the RSS time, when known."""
    meta = {}
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "BlogPosting":
            meta = data
    body = _Body()
    body.feed(page)
    paras = [p for p in body.parts if not re.match(r"(Sources|წყაროები?):", p)]
    title = html_lib.unescape(meta.get("headline", "")).strip()
    if not title:
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
        title = " ".join(re.sub(r"<[^>]+>", "", html_lib.unescape(h1.group(1))).split()) if h1 else ""
    lead = html_lib.unescape(meta.get("description", "")).strip()
    text = "\n".join(paras)
    if not title or len(text) < 200:
        raise SourceError(f"sitech {slug}: no readable post ({len(text)} characters of text)")
    src = re.search(r'(?:Sources|წყაროები?):.*?href=\\?"(https?://[^"\\]+)', page, re.S)
    outlet = web.host(src.group(1)) if src else ""
    outlets = [DOMAIN] + ([outlet] if outlet and outlet != DOMAIN else [])
    cluster = {"id": slug, "headline": title, "category": category(f"{title} {lead} {text[:1500]}"),
               "created_at": published or web.iso_utc(meta.get("datePublished")) or web.now_iso(),
               "published": web.day(meta.get("datePublished")), "source_count": len(outlets), "sources": outlets,
               "url": page_url(slug), "title": title}
    return {"cluster": cluster, "articles": [f"{title}\n{lead}\n{text}" if lead and lead not in text else
                                             f"{title}\n{text}"]}


def fetch(ref):
    slug = slug_of(ref)
    body, ctype, _ = web.get(page_url(slug))
    try:
        published = rss_times(web.get(RSS)[0]).get(slug)
    except Exception:  # noqa: BLE001 - the feed only adds the exact time; the post itself is what matters
        published = None
    return parse(web.decode(body, ctype), slug, published)
