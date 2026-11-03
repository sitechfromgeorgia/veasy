"""Openverse (api.openverse.org): openly licensed images from many collections (Flickr, museums, Commons...), each
with its own Creative Commons licence. No key needed; anonymous calls are rate-limited, so searches are cached
(assets.py) and every call waits its turn (media.request).

Only licences that allow commercial reuse are asked for (`license=cc0,pdm,by,by-sa`) and checked again on every
result: the API's filter is a convenience, the ledger's licence is what `engine check` trusts. Results from
Wikimedia are left to the commons provider, which fetches a sized thumbnail instead of a 20 MB original.
"""
import urllib.parse

from tt_shorts.media import files, get_json

NAME = "openverse"
KINDS = ("photo",)
API = "https://api.openverse.org/v1/images/"
LICENCES = ("cc0", "pdm", "by", "by-sa")  # assets.LICENCES' share of Creative Commons
SOURCES = {"flickr": "Flickr", "wikimedia": "Wikimedia Commons", "nappy": "nappy", "stocksnap": "StockSnap",
           "rawpixel": "rawpixel", "geographorguk": "Geograph"}


def available():
    return None


def params(query, n):
    return {"q": query, "license": ",".join(LICENCES), "page_size": max(1, min(n, 20)), "mature": "false",
            "extension": "jpg,png,webp"}


def candidate(r):
    """One API result -> a candidate, or None (a licence outside LICENCES, a mature or Wikimedia item, no file)."""
    lic = (r.get("license") or "").lower()
    if lic not in LICENCES or r.get("mature") or not r.get("url") or r.get("source") == "wikimedia":
        return None
    source = r.get("source") or r.get("provider") or "openverse"
    return {"provider": NAME, "kind": "photo", "id": str(r.get("id")), "url": r["url"],
            "page": r.get("foreign_landing_url") or "", "licence": lic,
            "licence_version": r.get("license_version") or "",
            "author": (r.get("creator") or "").strip(), "title": (r.get("title") or "").strip(),
            "source": SOURCES.get(source, source.title()), "width": r.get("width") or 0, "height": r.get("height") or 0,
            "tags": [t.get("name", "") for t in (r.get("tags") or [])[:12] if isinstance(t, dict)]}


def search(query, kind="photo", n=20):
    if kind not in KINDS:
        return []
    data = get_json(API + "?" + urllib.parse.urlencode(params(query, n)))
    return [c for c in (candidate(r) for r in data.get("results") or []) if c]


def fetch(c):
    return files.fetch_file(c)
