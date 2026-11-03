"""Wikimedia Commons (commons.wikimedia.org): free media files, each with its own licence in its file page's
metadata. No key; Wikimedia asks for a descriptive User-Agent (media.USER_AGENT) and a polite rate.

The licence is read from the file's extmetadata (License: cc0, pd, cc-by-4.0, cc-by-sa-3.0...) and mapped onto the
licences that allow commercial reuse (cc0, pdm, by, by-sa); anything else (GFDL only, non-commercial, fair use) is
dropped, and so is a file with Restrictions (personality rights, trademarks, insignia). The file fetched is a 1600 px
thumbnail Commons renders, never the original (which can be 50 MB).
"""
import html
import re
import urllib.parse

from tt_shorts.media import files, get_json

NAME = "commons"
KINDS = ("photo",)
API = "https://commons.wikimedia.org/w/api.php"
WIDTH = 1600
MIMES = ("image/jpeg", "image/png", "image/webp")
META = "LicenseShortName|License|Artist|Restrictions|ObjectName"


def available():
    return None


def licence(meta):
    """Commons' License field -> (licence, version), or (None, "") for one that doesn't allow commercial reuse."""
    raw = (meta.get("License") or "").strip().lower()
    if raw == "cc0":
        return "cc0", "1.0"
    if raw in ("pd", "public domain") or raw.startswith("pd-") or raw.startswith("pd "):
        return "pdm", "1.0"
    m = re.fullmatch(r"cc-by(-sa)?-(\d\.\d)(?:-[a-z]{2,})?", raw)
    if m:
        return ("by-sa" if m.group(1) else "by"), m.group(2)
    return None, ""


def text(value):
    """Commons' HTML metadata -> plain text on one line."""
    s = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def params(query, n):
    return {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6, "gsrlimit": max(1, min(n, 20)), "prop": "imageinfo",
            "iiprop": "url|size|mime|sha1|extmetadata", "iiurlwidth": WIDTH, "iiextmetadatafilter": META}


def candidate(page):
    """One search result page -> a candidate, or None."""
    ii = (page.get("imageinfo") or [{}])[0]
    meta = {k: (v or {}).get("value", "") for k, v in (ii.get("extmetadata") or {}).items()}
    lic, version = licence(meta)
    if not lic or text(meta.get("Restrictions")) or ii.get("mime") not in MIMES or not ii.get("thumburl"):
        return None
    author = text(meta.get("Artist"))
    title = text(meta.get("ObjectName")) or re.sub(r"^File:|\.\w+$", "", page.get("title", ""))
    return {"provider": NAME, "kind": "photo", "id": str(page.get("pageid")), "url": ii["thumburl"],
            "page": ii.get("descriptionurl", ""), "licence": lic, "licence_version": version, "author": author,
            "title": title, "source": "Wikimedia Commons", "width": ii.get("thumbwidth") or ii.get("width") or 0,
            "height": ii.get("thumbheight") or ii.get("height") or 0}


def search(query, kind="photo", n=20):
    if kind not in KINDS:
        return []
    data = get_json(API + "?" + urllib.parse.urlencode(params(query, n)))
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    return [c for c in (candidate(p) for p in pages) if c]


def fetch(c):
    return files.fetch_file(c)
