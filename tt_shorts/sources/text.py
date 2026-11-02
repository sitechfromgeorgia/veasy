"""A source any agent can feed: a JSON file with the facts, no database needed.

    {"id": "my-post-1", "headline": "...", "category": "tech", "date": "2026-11-02T10:00:00Z",
     "sources": ["Outlet A", "Outlet B"], "articles": ["title\\nfull text", "..."]}

`id` defaults to the file name; `date` to now. The writer and the news checks use only these texts.
"""
import datetime as dt
import json
import pathlib


def fetch(ref):
    path = pathlib.Path(ref)
    data = json.loads(path.read_text(encoding="utf-8"))
    articles = [a for a in data.get("articles", []) if isinstance(a, str) and a.strip()]
    cluster = {
        "id": data.get("id") or path.stem,
        "headline": data.get("headline", ""),
        "category": data.get("category", "general"),
        "created_at": data.get("date") or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_count": len(data.get("sources", [])),
        "sources": data.get("sources", []),
    }
    return {"cluster": cluster, "articles": articles}
