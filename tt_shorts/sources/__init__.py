"""Sources: where a story's facts come from. A source turns a reference into what the writer needs:

    fetch(ref) -> {"cluster": {"id", "headline", "category", "created_at", "sources": [outlet names], ...},
                   "articles": ["title\\nbody", ...]}

The writer (writer.py) and every check work only from that, so a new client is a new source module, not engine work.

  tbilisi-today   ref = a story cluster id in tbilisi.today's D1 (CLOUDFLARE_* + TT_D1_DATABASE_ID)
  text            ref = a JSON file any agent can write: {"headline", "category", "date", "sources", "articles"}
"""
import importlib

KNOWN = {"tbilisi-today": "tt_shorts.sources.tbilisi_today", "text": "tt_shorts.sources.text"}


class SourceError(ValueError):
    pass


def get(name):
    if name not in KNOWN:
        raise SourceError(f"unknown source {name!r}; known: {', '.join(KNOWN)}")
    return importlib.import_module(KNOWN[name])


def fetch(name, ref):
    data = get(name).fetch(ref)
    if not data.get("articles"):
        raise SourceError(f"{name} {ref}: no readable articles")
    return data
