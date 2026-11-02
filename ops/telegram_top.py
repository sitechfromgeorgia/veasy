"""Post the day's most significant finished videos to Telegram, once each.

Reads the queue's done jobs from the last 24 hours, highest priority first, and stops at ten.
A small marker file keeps a second run (the 01:00 batch) from posting the same video again.
"""
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import queue, telegram  # noqa: E402

MARK = ROOT / "data" / "telegram-posted.json"
LIMIT = 50


def main() -> int:
    cutoff = dt.datetime.now().timestamp() - 24 * 3600
    today = dt.date.today().isoformat()
    state = json.loads(MARK.read_text(encoding="utf-8")) if MARK.exists() else {}
    if state.get("date") != today:
        state = {"date": today, "ids": []}
    posted_ids = set(state.get("ids") or [])
    if len(posted_ids) >= LIMIT:
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
        done.append((job.get("priority") or 0, job, file))
    done.sort(key=lambda x: -x[0])
    sent = 0
    for _, job, file in done:
        if sent >= LIMIT:
            break
        title = ""
        try:
            story = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
            hook = next((s for s in story.get("scenes", []) if s.get("type") == "hook"), {})
            title = " ".join(hook.get("lines") or []) or story.get("narration", "")[:90]
        except Exception:
            pass
        link = f"https://tbilisi.today/stories/{job.get('ref')}"
        caption = f"{title}\n\n{link}"
        buttons = [[{"text": "სრულად წაკითხვა", "url": link}],
                   [{"text": "tbilisi.today", "url": "https://tbilisi.today"}]]
        try:
            if telegram.send_video(file, caption, buttons=buttons):
                posted_ids.add(job["id"])
                state["ids"] = sorted(posted_ids)
                MARK.parent.mkdir(parents=True, exist_ok=True)
                MARK.write_text(json.dumps(state), encoding="utf-8")
                sent += 1
        except Exception as e:
            print(f"telegram: {type(e).__name__}: {e}")
    print(f"telegram: {sent} posted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
