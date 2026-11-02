"""tbilisi.today: story clusters (the same event in several outlets) from its D1 database, read-only.

Needs CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN (D1 read) and TT_D1_DATABASE_ID. `candidates()` is the daily
selection: 4+ outlets, fresh, category caps, sensitive stories skipped, no repeats (`seen`).
"""
import json
import os
import urllib.request

from tt_shorts import news_check

CAPS = {"politics": 4, "world": 2, "economy": 2, "general": 2, "crime": 1}
DEFAULT_CAP = 1
CLUSTER_SQL = """SELECT sc.id, sc.headline, sc.source_count, sc.article_count, sc.created_at,
       COALESCE((SELECT a.category FROM articles a WHERE a.cluster_id = sc.id AND a.category IS NOT NULL
                 GROUP BY a.category ORDER BY count(*) DESC LIMIT 1), 'general') AS category
  FROM story_clusters sc"""


def _env(name):
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def d1(sql, params=None):
    acct, tok, db = _env("CLOUDFLARE_ACCOUNT_ID"), _env("CLOUDFLARE_API_TOKEN"), _env("TT_D1_DATABASE_ID")
    body = {"sql": sql}
    if params:
        body["params"] = params
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acct}/d1/database/{db}/query",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    if not data.get("success"):
        raise RuntimeError(f"D1: {data.get('errors')}")
    return data["result"][0]["results"]


def payload(cluster):
    arts = d1("""SELECT a.title, COALESCE(a.content_text, '') AS body, COALESCE(s.name_ka, a.source_slug) AS outlet
                   FROM articles a LEFT JOIN sources s ON s.slug = a.source_slug
                  WHERE a.cluster_id = ?1 AND length(COALESCE(a.content_text, '')) > 400
                  ORDER BY length(a.content_text) DESC LIMIT 3""", [cluster["id"]])
    outlets = []
    for a in arts:
        if a["outlet"] not in outlets:
            outlets.append(a["outlet"])
    return {"cluster": {**cluster, "sources": outlets}, "articles": [f"{a['title']}\n{a['body']}" for a in arts]}


def fetch(ref):
    rows = d1(CLUSTER_SQL + " WHERE sc.id = ?1", [int(ref)])
    if not rows:
        raise ValueError(f"no cluster {ref}")
    return payload(rows[0])


def candidates(hours=18, limit=10, seen=(), scores=None):
    rows = d1(CLUSTER_SQL + " WHERE sc.created_at >= datetime('now', ?1) AND sc.source_count >= 4 ORDER BY sc.created_at DESC",
              [f"-{hours} hours"])
    sig = scores or {}
    rows.sort(key=lambda r: (sig.get(str(r["id"]), 0) + r["source_count"] * 2), reverse=True)
    picked, per_cat, seen = [], {}, {str(s) for s in seen}
    for r in rows:
        if str(r["id"]) in seen or news_check.sensitive([r["headline"]]):
            continue
        cap = CAPS.get(r["category"], DEFAULT_CAP)
        if per_cat.get(r["category"], 0) >= cap:
            continue
        if len(picked) >= limit:
            break
        per_cat[r["category"]] = per_cat.get(r["category"], 0) + 1
        picked.append(r)
    return picked
