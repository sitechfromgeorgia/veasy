"""Post the day's most significant finished videos to Telegram, once each.

Reads the queue's done jobs from the last 24 hours, highest priority first, and stops at ten.
A small marker file keeps a second run (the 01:00 batch) from posting the same video again.
"""
import datetime as dt
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import queue, telegram  # noqa: E402

MARK = ROOT / "data" / "telegram-posted.json"
LIMIT = 50
AGE_HOURS = 18  # a story older than this is stale: the video lane must not post yesterday's news
TG_NEWS_STATE = pathlib.Path(os.environ.get("TG_NEWS_STATE", "/root/sitech/scripts/analysis/.tg_news_posted.json"))


def main() -> int:
    cutoff = dt.datetime.now().timestamp() - 12 * 3600
    today = dt.date.today().isoformat()
    state = json.loads(MARK.read_text(encoding="utf-8")) if MARK.exists() else {}
    posted_ids = set(state.get("ids") or [])  # survives midnight: an id is posted once, ever
    # One shared ledger across the two lanes: the news cards (tg_news.py) and the video lane
    # used to post the same cluster twice (audit 2026-11-04: 25515/25527/25534).
    news_clusters: set[int] = set()
    try:
        news_clusters = {int(k) for k in (json.loads(TG_NEWS_STATE.read_text(encoding="utf-8")).get("posted") or {})}
    except Exception:
        pass
    count = state.get("count", 0) if state.get("day") == today else 0
    if count >= LIMIT:
        print(f"telegram: 0 posted (daily limit {LIMIT} reached)")
        return 0
    done = []
    for job in queue.listing("done", 400):
        result = job.get("result") or {}
        file = result.get("file")
        if not file or not pathlib.Path(file).exists():
            continue
        if pathlib.Path(file).stat().st_mtime < cutoff:
            continue
        if job["id"] in posted_ids:
            continue
        if int(job.get("ref") or 0) in news_clusters:
            continue
        # The 12 h gate above reads the render's mtime, which is the post time, not the story's
        # age; the story's own date is the honest freshness signal.
        try:
            st = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
            when = dt.datetime.fromisoformat(str(st.get("date") or "").replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
            if (dt.datetime.now(dt.timezone.utc) - when).total_seconds() > AGE_HOURS * 3600:
                continue
        except Exception:
            pass
        done.append((job.get("priority") or 0, job, file))
    done.sort(key=lambda x: -x[0])
    sent = 0
    for _, job, file in done:
        if count >= LIMIT:
            break
        title = ""
        private = False
        try:
            story = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
            private = story.get("private") is True or story.get("visibility") == "private"
            hook = next((s for s in story.get("scenes", []) if s.get("type") == "hook"), {})
            title = " ".join(hook.get("lines") or []) or story.get("narration", "")[:90]
        except Exception:
            pass
        if private:
            # An embargoed piece never reaches the channel: the owner publishes it himself or not at all.
            continue
        link = f"https://tbilisi.today/stories/{job.get('ref')}"
        caption = f"{title}\n\n{link}"
        buttons = [[{"text": "სრულად წაკითხვა", "url": link}],
                   [{"text": "tbilisi.today", "url": "https://tbilisi.today"}]]
        try:
            if telegram.send_video(file, caption, buttons=buttons):
                posted_ids.add(job["id"])
                count += 1
                sent += 1
                MARK.parent.mkdir(parents=True, exist_ok=True)
                MARK.write_text(json.dumps({"ids": sorted(posted_ids), "day": today, "count": count}),
                                encoding="utf-8")
        except Exception as e:
            print(f"telegram: {type(e).__name__}: {e}")
    print(f"telegram: {sent} posted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
