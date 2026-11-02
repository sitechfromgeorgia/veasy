"""Daily tbilisi.today Shorts: pick the day's multi-source stories, write them, render them.

Selection is deliberately small and explainable (owner rule 2026-11-02: start with 10 a day):
- a cluster needs 4+ outlets and must be fresh (default 18 hours);
- a significance score (story_significance) ranks them, with the outlet count as a tie-break;
- category caps keep the feed from turning into one topic (politics max 4, world 2, economy 2,
  general 2, crime 1, everything else 1);
- sensitive stories (N5) are skipped before a model ever sees them;
- a story is never rendered twice (state file).

  python -m ops.daily --limit 10 --batch 1          # write + render the first five
  python -m ops.daily --limit 10 --batch 2          # the next five (the 19:00 run)
  python -m ops.daily --limit 1 --dry-run           # selection only, no model, no render
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import news_check, props, writer  # noqa: E402

CAPS = {"politics": 4, "world": 2, "economy": 2, "general": 2, "crime": 1}
DEFAULT_CAP = 1
SIG = pathlib.Path("/root/sitech/scratch/story-significance/significance-map.json")
OUT = ROOT / "out" / "daily"
STATE = ROOT / "out" / "daily-state.json"


def env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def d1(sql: str, params: list | None = None) -> list[dict]:
    acct, tok, db = env("CLOUDFLARE_ACCOUNT_ID"), env("CLOUDFLARE_API_TOKEN"), env("TT_D1_DATABASE_ID")
    body = {"sql": sql}
    if params:
        body["params"] = params
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{acct}/d1/database/{db}/query",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    if not data.get("success"):
        raise RuntimeError(f"D1: {data.get('errors')}")
    return data["result"][0]["results"]


def scores() -> dict[str, float]:
    try:
        return json.loads(SIG.read_text(encoding="utf-8")).get("scores", {})
    except Exception:
        return {}


def done() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"ids": [], "runs": []}


def save_done(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def candidates(hours: int, limit: int) -> list[dict]:
    rows = d1(
        """SELECT sc.id, sc.headline, sc.source_count, sc.article_count, sc.created_at,
                  COALESCE((SELECT a.category FROM articles a
                             WHERE a.cluster_id = sc.id AND a.category IS NOT NULL
                             GROUP BY a.category ORDER BY count(*) DESC LIMIT 1), 'general') AS category
             FROM story_clusters sc
            WHERE sc.created_at >= datetime('now', ?1)
              AND sc.source_count >= 4
            ORDER BY sc.created_at DESC""",
        [f"-{hours} hours"],
    )
    seen, picked, per_cat = set(done().get("ids", [])), [], {}
    sig = scores()
    rows.sort(key=lambda r: (sig.get(str(r["id"]), 0) + r["source_count"] * 2), reverse=True)
    for r in rows:
        if r["id"] in seen:
            continue
        if news_check.sensitive([r["headline"]]):
            continue
        cap = CAPS.get(r["category"], DEFAULT_CAP)
        if per_cat.get(r["category"], 0) >= cap:
            continue
        if len(picked) >= limit:
            break
        per_cat[r["category"]] = per_cat.get(r["category"], 0) + 1
        picked.append(r)
    return picked


def payload(cluster: dict) -> dict:
    arts = d1(
        """SELECT a.title, COALESCE(a.content_text, '') AS body, COALESCE(s.name_ka, a.source_slug) AS outlet
             FROM articles a LEFT JOIN sources s ON s.slug = a.source_slug
            WHERE a.cluster_id = ?1 AND length(COALESCE(a.content_text, '')) > 400
            ORDER BY length(a.content_text) DESC LIMIT 3""",
        [cluster["id"]],
    )
    outlets = []
    for a in arts:
        if a["outlet"] not in outlets:
            outlets.append(a["outlet"])
    cluster = {**cluster, "sources": outlets}
    return {"cluster": cluster, "articles": [f"{a['title']}\n{a['body']}" for a in arts]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--hours", type=int, default=18)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    chunk = max(1, args.limit)
    pool = candidates(args.hours, chunk * max(1, args.batch))
    start = (args.batch - 1) * chunk
    picks = pool[start:start + chunk]
    print(f"candidates: {len(pool)}; this batch: {len(picks)}")
    for c in picks:
        print(f"  {c['id']} [{c['category']}] {c['source_count']} src · {c['headline'][:70]}")
    if args.dry_run or not picks:
        return 0

    state = done()
    day_dir = OUT / dt.date.today().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    for c in picks:
        sid = c["id"]
        try:
            data = payload(c)
            if not data["articles"]:
                print(f"skip {sid}: no readable articles")
                continue
            story = writer.write(data["cluster"], data["articles"])
            path = ROOT / "stories" / f"{sid}.json"
            path.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
            work, built = props.build(str(path), variant="auto", engine="gemini")
            target = day_dir / f"{sid}.mp4"
            props.render_video(work, built, target)  # build() only writes the props; this renders and mixes
            if not target.exists() or target.stat().st_size < 500_000:
                raise RuntimeError(f"render output is empty or too small ({target})")
            state["ids"].append(sid)
            state["runs"].append({"id": sid, "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                  "file": str(target), "category": c["category"]})
            save_done(state)
            print(f"done {sid} -> {target}")
        except Exception as e:
            print(f"fail {sid}: {type(e).__name__}: {e}")
            state["runs"].append({"id": sid, "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                  "error": f"{type(e).__name__}: {e}"})
            save_done(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
