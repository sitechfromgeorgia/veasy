"""Sources: where a story's facts come from. A source turns a reference into what the writer needs:

    fetch(ref) -> {"cluster": {"id", "headline", "category", "created_at", "sources": [outlet names], ...},
                   "articles": ["title\\nbody", ...]}

The writer (writer.py) and every check work only from that, so a new client is a new source module, not engine work.
A document source may add "url" (the end card's link when the program says "link": "source"), "title" and, for law,
"article" to the cluster. Which program takes which source: programs/<name>.json "sources".

  tbilisi-today   ref = a story cluster id in tbilisi.today's D1 (CLOUDFLARE_* + TT_D1_DATABASE_ID)
  text            ref = a JSON file any agent can write: {"headline", "category", "date", "sources", "articles"}
  url             ref = a web page (or a saved .html file): the main text, title, date and site name
  pdf             ref = a PDF file or URL: its text (pypdf, else pdftotext), title and date from its metadata
  ordo            ref = <law>:<article>[:<part>] (constitution:17, 31702:361): Georgian law from matsne.gov.ge
                  through Ordo's matsne_api.py (ORDO_DIR)
  sitech          ref = a sitech.ge blog post's slug (or its URL): the Georgian post, its date and its source
"""
import importlib

KNOWN = {"tbilisi-today": "tt_shorts.sources.tbilisi_today", "text": "tt_shorts.sources.text",
         "url": "tt_shorts.sources.url", "pdf": "tt_shorts.sources.pdf", "ordo": "tt_shorts.sources.ordo",
         "sitech": "tt_shorts.sources.sitech"}
ABOUT = {
    "tbilisi-today": "ref = a tbilisi.today story cluster id (D1, read only)",
    "text": "ref = a JSON file {id, headline, category, date, sources, articles: [text, ...]}",
    "url": "ref = a web page URL (or a saved .html file): main text, title, date, site name",
    "pdf": "ref = a PDF file or URL: its text, title and date",
    "ordo": "ref = <law>:<article>[:<part>], e.g. constitution:17 or 31702:361 (matsne.gov.ge via Ordo, ORDO_DIR)",
    "sitech": "ref = a sitech.ge blog post slug or URL (the Georgian post)",
}


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
