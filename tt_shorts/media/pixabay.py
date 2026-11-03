"""Pixabay (pixabay.com): free photos and clips under the Pixabay Content License (commercial use, no attribution
required; the video still credits the uploader). Used only when PIXABAY_API_KEY is set; without it the provider is
skipped, never an error. The key is a query parameter of the search only: the file URLs it returns carry no key,
and the key is never written to a ledger, a log or a cache file. Pixabay asks that results are cached (assets.py
keeps every search) and files downloaded, not hot-linked.
"""
import os
import urllib.parse

from tt_shorts.media import files, get_json

NAME = "pixabay"
KINDS = ("photo", "video")
ENV = "PIXABAY_API_KEY"
PHOTOS = "https://pixabay.com/api/"
VIDEOS = "https://pixabay.com/api/videos/"


def available():
    return None if os.environ.get(ENV) else f"{ENV} is not set"


def photo(h):
    url = h.get("largeImageURL") or h.get("webformatURL")
    if not url:
        return None
    return {"provider": NAME, "kind": "photo", "id": str(h.get("id")), "url": url, "page": h.get("pageURL", ""),
            "licence": "pixabay", "licence_version": "", "author": (h.get("user") or "").strip(),
            "title": (h.get("tags") or "").strip(), "source": "Pixabay", "width": h.get("imageWidth") or 0,
            "height": h.get("imageHeight") or 0}


def clip(h):
    sizes = h.get("videos") or {}
    best = next((sizes[k] for k in ("large", "medium", "small") if (sizes.get(k) or {}).get("url")), None)
    if not best:
        return None
    return {"provider": NAME, "kind": "video", "id": f"v{h.get('id')}", "url": best["url"],
            "page": h.get("pageURL", ""),
            "licence": "pixabay", "licence_version": "", "author": (h.get("user") or "").strip(),
            "title": (h.get("tags") or "").strip(), "source": "Pixabay", "width": best.get("width") or 0,
            "height": best.get("height") or 0, "duration": h.get("duration") or 0}


def search(query, kind="photo", n=20):
    if kind not in KINDS or available():
        return []
    common = {"key": os.environ[ENV], "q": query[:100], "safesearch": "true", "per_page": max(3, min(n, 50))}
    if kind == "video":
        data = get_json(VIDEOS + "?" + urllib.parse.urlencode(common))
        return [c for c in (clip(h) for h in data.get("hits") or []) if c]
    data = get_json(PHOTOS + "?" + urllib.parse.urlencode({**common, "image_type": "photo", "orientation": "vertical"}))
    return [c for c in (photo(h) for h in data.get("hits") or []) if c]


def fetch(c):
    return files.fetch_file(c)
