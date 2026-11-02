"""A web page as a source: its main text, title, date and site name.

    python -m tt_shorts.engine write --program explainer --source url --ref https://example.ge/news/123

The text comes from trafilatura when it is installed (`pip install trafilatura`), else from a readability-like
extractor on the stdlib html.parser: site chrome (nav, header, footer, aside, forms, share and comment boxes) is
dropped, the element with the most paragraph text wins (an <article>, <main> or articleBody first), and link lists
are left out. Title, date and site name come from the page's own metadata (og:*, ld+json, <time>), so the header
shows the page's date. A PDF URL is handed to the pdf source; a saved .html file works as a ref too (tests, offline).
"""
import collections
import json
import os
import pathlib
import re
from html.parser import HTMLParser

from tt_shorts.sources import SourceError, web

MIN_TEXT = 200  # characters: less is a cookie wall or an index page, not a document
BLOCK = {"p", "h1", "h2", "h3", "h4", "li", "blockquote", "pre", "dd"}
SKIP = {"script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside", "form", "button",
        "select", "iframe", "object", "canvas", "dialog", "figure", "menu"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NEGATIVE = re.compile(r"comment|share|social|related|promo|sidebar|footer|navbar|menu|cookie|subscribe|newsletter|"
                      r"advert|banner|breadcrumb|popup|modal|widget|recommend|author-bio", re.I)
CONTAINERS = ("articlebody", "article", "main")  # most specific first


class _Page(HTMLParser):
    """One pass over the page: text blocks with their ancestors, and the metadata."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []  # (tag, node id, skipped)
        self.nodes = []  # node id -> container kind ("articlebody", "article", "main") or ""
        self.blocks = []  # {"tag", "text", "anc", "link"}
        self.meta, self.ld, self.times = {}, [], []
        self.title, self.h1 = "", ""
        self._block = self._ld_buf = self._title_buf = None
        self._links = 0

    def _skipped(self):
        return bool(self.stack) and self.stack[-1][2]

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key and a.get("content") and key not in self.meta:
                self.meta[key] = a["content"].strip()
            return
        if tag == "br" and self._block is not None:
            self._block["parts"].append(" ")
        if tag in VOID:
            return
        if tag == "time" and a.get("datetime"):
            self.times.append(a["datetime"])
        if tag == "script" and "ld+json" in a.get("type", ""):
            self._ld_buf = []
        if tag == "title" and not self.title:
            self._title_buf = []
        top = self.stack[-1][0] if self.stack else None
        if (top == "p" and tag in BLOCK | {"div", "ul", "ol", "table", "section"}) or (top == "li" and tag == "li"):
            self.handle_endtag(top)  # an unclosed <p> (or <li>) ends where the next block (or item) starts
        hint = f"{a.get('class', '')} {a.get('id', '')}"
        semantic = tag in ("article", "main", "body", "html") or a.get("role") == "main" or \
            a.get("itemprop", "").lower() == "articlebody"
        skipped = self._skipped() or tag in SKIP or "hidden" in a or a.get("aria-hidden") == "true" or \
            (not semantic and bool(NEGATIVE.search(hint))) or "display:none" in a.get("style", "").replace(" ", "")
        kind = ("articlebody" if a.get("itemprop", "").lower() == "articlebody" else
                "article" if tag == "article" else "main" if tag == "main" or a.get("role") == "main" else "")
        nid = len(self.nodes)
        self.nodes.append(kind)
        self.stack.append((tag, nid, skipped))
        if tag in BLOCK and self._block is None and not skipped:
            self._block = {"tag": tag, "parts": [], "anc": tuple(n for _, n, _ in self.stack[:-1]), "link": 0,
                           "nid": nid}
        if tag == "a" and self._block is not None:
            self._links += 1

    def handle_endtag(self, tag):
        if not any(t == tag for t, _, _ in self.stack):
            return
        while self.stack:
            t, nid, _ = self.stack.pop()
            if t == "a" and self._links:
                self._links -= 1
            if self._block is not None and self._block["nid"] == nid:
                text = " ".join("".join(self._block["parts"]).split())
                if text:
                    self.blocks.append({"tag": self._block["tag"], "text": text, "anc": self._block["anc"],
                                        "link": self._block["link"]})
                self._block = None
            if t == "script" and self._ld_buf is not None:
                self.ld.append("".join(self._ld_buf))
                self._ld_buf = None
            if t == "title" and self._title_buf is not None:
                self.title = " ".join("".join(self._title_buf).split())
                self._title_buf = None
            if t == tag:
                break

    def handle_data(self, data):
        if self._ld_buf is not None:
            self._ld_buf.append(data)
            return
        if self._title_buf is not None:
            self._title_buf.append(data)
        if self._block is not None and not self._skipped():
            self._block["parts"].append(data)
            if self._links:
                self._block["link"] += len(data.strip())
            if self._block["tag"] == "h1" and not self.h1:
                self.h1 = data.strip()


def _ld_objects(raw):
    """Every dict in the page's ld+json blocks (lists and @graph unrolled)."""
    out = []
    for text in raw:
        try:
            data = json.loads(text)
        except ValueError:
            continue
        todo = [data]
        while todo:
            x = todo.pop()
            if isinstance(x, list):
                todo += x
            elif isinstance(x, dict):
                out.append(x)
                todo += x.get("@graph", []) if isinstance(x.get("@graph"), list) else []
    return out


def _ld(objs, key):
    for o in objs:
        t = o.get("@type")
        t = " ".join(t) if isinstance(t, list) else str(t or "")
        if re.search(r"Article|BlogPosting|Report|Legislation|WebPage|CreativeWork", t) and o.get(key):
            return o[key]
    return None


def _good(b):
    if b["tag"] in ("h1",):
        return False
    words = len(b["text"].split())
    if b["link"] > 0.5 * len(b["text"]):
        return False  # a list of links: navigation, tags, "read more"
    return words >= 3 or b["tag"] in ("h2", "h3", "h4")


def main_text(page):
    """The page's main text from its blocks: the semantic container with the most paragraph text, else the element
    whose paragraphs (and its children's, at half weight) score highest."""
    paras = [b for b in page.blocks if b["tag"] == "p" and len(b["text"]) >= 25 and b["link"] <= 0.5 * len(b["text"])]
    best = None
    for kind in CONTAINERS:
        sizes = collections.Counter()
        for b in paras:
            for nid in b["anc"]:
                if page.nodes[nid] == kind:
                    sizes[nid] += len(b["text"])
        if sizes and sizes.most_common(1)[0][1] >= MIN_TEXT:
            best = sizes.most_common(1)[0][0]
            break
    if best is None:
        score = collections.Counter()
        for b in paras:
            pts = 1 + min(len(b["text"]), 600) / 100 + b["text"].count(",")
            if b["anc"]:
                score[b["anc"][-1]] += pts
            if len(b["anc"]) > 1:
                score[b["anc"][-2]] += pts / 2
        if not score:
            return ""
        best = score.most_common(1)[0][0]
    keep = [b["text"] for b in page.blocks if best in b["anc"] and _good(b)]
    return "\n".join(dict.fromkeys(keep))


def _trafilatura(html, url):
    """trafilatura's text, or None when it isn't installed or finds too little."""
    try:
        import trafilatura
    except ImportError:
        return None
    try:
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False,
                                   favor_precision=True, deduplicate=True)
    except Exception:  # noqa: BLE001 - a parser crash falls back to the stdlib extractor
        return None
    return text if text and len(text) >= MIN_TEXT else None


def _clean_title(title, site):
    """'Headline | Site' -> 'Headline' when one side is the site's name."""
    for sep in (" | ", " - ", " – ", " — ", " :: "):
        parts = [p.strip() for p in title.split(sep)]
        if len(parts) > 1 and site and any(p.lower() == site.lower() for p in parts):
            return sep.join(p for p in parts if p.lower() != site.lower())
    return title


def page_id(url):
    """A short stable id for a page: host + last path segment (example-ge-my-article)."""
    from tt_shorts import store
    if os.path.isfile(url):
        return store.safe(pathlib.Path(url).stem)[:60]
    m = re.match(r"https?://([^/?#]+)([^?#]*)", url)
    host, path = (m.group(1), m.group(2)) if m else (url, "")
    last = next((p for p in reversed(path.split("/")) if p), "")
    last = re.sub(r"\.(html?|php|aspx?)$", "", last)
    return store.safe(f"{host.removeprefix('www.')}-{last}" if last else host)[:60].strip("-")


def parse(html, url="", extractor=None):
    """A page's HTML -> the source payload. extractor: None (trafilatura when installed, else stdlib) or "stdlib"."""
    page = _Page()
    page.feed(html)
    page.close()
    objs = _ld_objects(page.ld)
    m = page.meta
    publisher = _ld(objs, "publisher")
    site = m.get("og:site_name") or (publisher.get("name") if isinstance(publisher, dict) else "") or \
        m.get("application-name") or web.host(url) or pathlib.Path(url).stem
    title = m.get("og:title") or m.get("twitter:title") or _ld(objs, "headline") or page.title or page.h1
    title = _clean_title(" ".join(str(title or "").split()), site)
    stated = (m.get("article:published_time") or m.get("og:published_time") or m.get("datepublished") or
              _ld(objs, "datePublished") or m.get("pubdate") or m.get("publishdate") or m.get("date") or
              m.get("dc.date.issued") or (page.times[0] if page.times else ""))
    text, used = None, "stdlib"
    if extractor != "stdlib":
        text = _trafilatura(html, url)
        used = "trafilatura" if text else used
    if not text:
        text = main_text(page)
    if len(text or "") < MIN_TEXT:
        raise SourceError(f"url {url}: no readable text ({len(text or '')} characters)")
    first, _, rest = text.partition("\n")
    if title and first.strip() == title and rest.strip():
        text = rest  # trafilatura keeps the page's h1; the title goes first once
    lead = m.get("og:description") or m.get("description") or ""
    head = title + (f"\n{lead}" if lead and lead[:60] not in text else "")
    cluster = {"id": page_id(url) or "page", "headline": title, "category": "general",
               "created_at": web.iso_utc(stated) or web.now_iso(), "published": web.day(stated),
               "source_count": 1, "sources": [site], "url": url if url.startswith("http") else "",
               "title": title, "extractor": used}
    return {"cluster": cluster, "articles": [f"{head}\n{text}"]}


def fetch(ref):
    ref = str(ref)
    if os.path.isfile(ref):
        body, ctype, final = pathlib.Path(ref).read_bytes(), "", ref
    else:
        if not re.match(r"https?://", ref):
            raise SourceError(f"url: {ref!r} is neither a web address nor a file")
        body, ctype, final = web.get(ref)
    if "pdf" in ctype.lower() or body[:5] == b"%PDF-":
        from tt_shorts.sources import pdf
        return pdf.from_bytes(body, final)
    return parse(web.decode(body, ctype), final)
