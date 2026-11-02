"""Stories as a source: 2-3 stories that already passed their checks, for the morning digest (program digest).

    ref = a.json,b.json[,c.json]          story files; each one's articles are the <story>.sources.json beside it
    ref = request.json                    {"stories": [paths], "sources": "tests/fixtures/sources.json"}: the
                                          articles from a {story id: [texts]} file (or one per story: "sources":
                                          [path or [texts], ...]) when there is no file beside a story
    ref = done:<brand>[:<YYYY-MM-DD>]     the brand's news jobs of that day (default: today) that ended done, in
                                          the queue's priority order, at most 3

-> {"cluster": {id (the day), headline, category, created_at (the latest story's date), sources (every story's
   outlets, in order), source_count, url (the brand's home page: the digest's end card opens it)},
   "articles": every story's articles (the digest's narration is checked against them again),
   "stories": [{"story", "articles", "path"}]}

Paths are read as given, then from the Veasy folder. No model, no network: digest.py builds the video from this.
"""
import json
import pathlib
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
MAX = 3


def _path(p):
    path = pathlib.Path(p)
    if not path.is_absolute() and not path.exists():
        path = ROOT / p
    return path


def _articles_beside(path):
    side = path.with_suffix(".sources.json")
    if side.exists():
        data = json.loads(side.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else None
    return None


def _from_map(mapping, story):
    if isinstance(mapping, dict):
        return mapping.get(str(story.get("id")))
    return None


def _done(ref):
    from tt_shorts import queue
    parts = ref.split(":")
    brand = parts[1] if len(parts) > 1 and parts[1] else None
    if not brand:
        raise ValueError("done:<brand>[:<day>]: name the brand")
    from tt_shorts import store
    day = parts[2] if len(parts) > 2 and parts[2] else store.today()
    jobs = [j for j in queue.listing("done", limit=500) if j["brand"] == brand and (j.get("program") or "news") == "news"
            and str(j.get("created", ""))[:10] == day and j.get("story")]
    jobs.sort(key=lambda j: (-(j.get("priority") or 0), j.get("created") or ""))
    return [j["story"] for j in jobs], None


def requested(ref):
    """(story paths, an articles mapping or a list of article files, or None) from a ref."""
    ref = str(ref)
    if ref.startswith("done:"):
        return _done(ref)
    if ref.endswith(".json") and "," not in ref:
        data = json.loads(_path(ref).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "stories" in data:
            src = data.get("sources")
            if isinstance(src, str):
                src = json.loads(_path(src).read_text(encoding="utf-8"))
            elif isinstance(src, list):
                src = [x if isinstance(x, list) else json.loads(_path(x).read_text(encoding="utf-8")) for x in src]
            return list(data["stories"]), src
    return [x.strip() for x in ref.split(",") if x.strip()], None


def home(brand):
    """The brand's front page, from its story link: https://tbilisi.today/."""
    from tt_shorts import brand as packs
    qr = packs.load(brand)["link"]["qr"]
    u = urllib.parse.urlparse(qr.split("{")[0])
    return f"{u.scheme}://{u.netloc}/"


def fetch(ref):
    paths, given = requested(ref)
    if not 2 <= len(paths) <= MAX:
        raise ValueError(f"a digest takes 2-{MAX} checked stories, got {len(paths)}")
    stories = []
    for i, p in enumerate(paths):
        path = _path(p)
        story = json.loads(path.read_text(encoding="utf-8"))
        arts = _articles_beside(path)
        if arts is None and isinstance(given, list) and i < len(given):
            arts = given[i]
        if arts is None:
            arts = _from_map(given, story)
        if not arts:
            raise ValueError(f"{p}: no articles (a <story>.sources.json beside it, or \"sources\" in the request): "
                             "a digest takes only stories it can check again")
        stories.append({"story": story, "articles": list(arts), "path": str(path)})
    brands = {s["story"].get("brand") or "tbilisi-today" for s in stories}
    if len(brands) > 1:
        raise ValueError(f"a digest is one brand's: these stories are {', '.join(sorted(brands))}")
    ids = [str(s["story"].get("id")) for s in stories]
    if len(set(ids)) < len(ids):
        raise ValueError(f"a story appears only once in a digest (ids {', '.join(ids)})")
    brand = brands.pop()
    latest = max(s["story"]["date"] for s in stories)
    outlets = []
    for s in stories:
        for o in s["story"].get("sources") or []:
            if o not in outlets:
                outlets.append(o)
    articles = []
    for s in stories:
        for a in s["articles"]:
            if a not in articles:
                articles.append(a)
    from tt_shorts import meta
    day = meta.ka_date(latest, brand)["day"].isoformat()
    cluster = {"id": day, "headline": "", "category": "general", "created_at": latest, "sources": outlets,
               "source_count": len(outlets), "url": home(brand), "brand": brand}
    return {"cluster": cluster, "articles": articles, "stories": stories}
