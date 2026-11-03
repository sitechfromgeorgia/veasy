"""Pexels (pexels.com): free photos and clips for commercial use, no attribution required (Pexels' licence; the
video still credits the photographer). Used only when PEXELS_API_KEY is set; without it the provider is skipped,
never an error. The key goes in a header and is never written to a ledger, a log or a cache file.
"""
import os
import urllib.parse

from tt_shorts.media import files, get_json

NAME = "pexels"
KINDS = ("photo", "video")
ENV = "PEXELS_API_KEY"
PHOTOS = "https://api.pexels.com/v1/search"
VIDEOS = "https://api.pexels.com/videos/search"
MAX_HEIGHT = 1920


def available():
    return None if os.environ.get(ENV) else f"{ENV} is not set"


def _headers():
    return {"Authorization": os.environ.get(ENV, "")}


def photo(p):
    src = p.get("src") or {}
    url = src.get("large2x") or src.get("original")
    if not url:
        return None
    return {"provider": NAME, "kind": "photo", "id": str(p.get("id")), "url": url, "page": p.get("url", ""),
            "licence": "pexels", "licence_version": "", "author": (p.get("photographer") or "").strip(),
            "title": (p.get("alt") or "").strip(), "source": "Pexels", "width": p.get("width") or 0,
            "height": p.get("height") or 0}


def clip(v):
    """A Pexels video -> a candidate with its best mp4 up to MAX_HEIGHT px, or None."""
    mp4 = [f for f in v.get("video_files") or [] if f.get("file_type") == "video/mp4" and f.get("link") and
           (f.get("height") or 0) <= MAX_HEIGHT]
    if not mp4:
        return None
    best = max(mp4, key=lambda f: (f.get("height") or 0, f.get("width") or 0))
    return {"provider": NAME, "kind": "video", "id": f"v{v.get('id')}", "url": best["link"], "page": v.get("url", ""),
            "licence": "pexels", "licence_version": "", "author": ((v.get("user") or {}).get("name") or "").strip(),
            "title": "", "source": "Pexels", "width": best.get("width") or 0, "height": best.get("height") or 0,
            "duration": v.get("duration") or 0}


def search(query, kind="photo", n=20):
    if kind not in KINDS or available():
        return []
    q = urllib.parse.urlencode({"query": query, "per_page": max(1, min(n, 40)), "orientation": "portrait"})
    if kind == "video":
        data = get_json(f"{VIDEOS}?{q}", _headers())
        return [c for c in (clip(v) for v in data.get("videos") or []) if c]
    data = get_json(f"{PHOTOS}?{q}", _headers())
    return [c for c in (photo(p) for p in data.get("photos") or []) if c]


def fetch(c):
    return files.fetch_file(c)
