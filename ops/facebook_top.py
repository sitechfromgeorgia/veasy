"""Post finished videos to the tbilisi.today Facebook Page as Reels, once each.

The Facebook twin of telegram_top.py, kept as its own module and its own ledger for one reason:
the Telegram video lane skips any cluster already in the news ledger (so a story is not posted
twice on Telegram), while on Facebook the same story must reach both surfaces. Sharing that ledger
would silently mute the Facebook lane for every story the news card already posted.

Selection: the queue's done jobs from the last 12 h, freshest story first, then priority.
Caps: 4 reels per day and a 90 min gap between them. The Reels API itself allows 30 posts in a
rolling 24 h, but a page that fires ten reels into an empty feed reads as spam and earns no reach,
so the lane paces itself well below the platform limit.

The link lives in the first comment, never the caption: a bare outbound URL in the body costs
reach on Facebook.

Usage:
    python -m ops.facebook_top              # dry: what would go out
    python -m ops.facebook_top --live       # publish
    python -m ops.facebook_top --live --max 1
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import facebook, queue, social_copy  # noqa: E402

MARK = ROOT / "data" / "facebook-posted.json"
RECEIPTS = pathlib.Path("/root/sitech/scratch/hourly-audit/fb-video-receipts.jsonl")
LIMIT = 4              # reels per calendar day (+04)
MIN_GAP_MIN = 90
AGE_HOURS = 18         # same freshness rule as the Telegram video lane
MAX_SECONDS = 90       # Reels hard limit; a longer render is not a reel
HASHTAGS = "#თბილისი #tbilisitoday"


def receipt(rec: dict) -> None:
    rec = {"ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **rec}
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _load() -> dict:
    try:
        return json.loads(MARK.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save(state: dict) -> None:
    MARK.parent.mkdir(parents=True, exist_ok=True)
    tmp = MARK.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(MARK)


def _today_count(state: dict, today: str) -> int:
    return len([v for v in (state.get("posted") or {}).values()
                if str(v.get("at", ""))[:10] == today])


def _last_post(state: dict) -> dt.datetime | None:
    times = []
    for v in (state.get("posted") or {}).values():
        try:
            times.append(dt.datetime.strptime(str(v.get("at")), "%Y-%m-%dT%H:%M:%SZ")
                         .replace(tzinfo=dt.timezone.utc))
        except ValueError:
            continue
    return max(times) if times else None


def _clean(s: str) -> str:
    """No em/en dashes in published copy (Edo's rule)."""
    import re
    return re.sub(r"[\u2013\u2014]", "-", " ".join((s or "").split()))


def candidates(state: dict) -> list[tuple[int, dict, str]]:
    posted = set((state.get("posted") or {}))
    cutoff = dt.datetime.now().timestamp() - 12 * 3600
    out = []
    for job in queue.listing("done", 400) or []:
        if not job:
            continue
        result = job.get("result") or {}
        file = result.get("file")
        if not file or not pathlib.Path(file).exists():
            continue
        if pathlib.Path(file).stat().st_mtime < cutoff:
            continue
        if job["id"] in posted:
            continue
        try:
            story = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(story, dict):
            continue
        if story.get("private") is True or story.get("visibility") == "private":
            continue  # an embargoed piece never reaches a social surface
        try:
            when = dt.datetime.fromisoformat(str(story.get("date") or "").replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
            if (dt.datetime.now(dt.timezone.utc) - when).total_seconds() > AGE_HOURS * 3600:
                continue
        except (ValueError, TypeError):
            pass
        seconds = result.get("seconds")
        if isinstance(seconds, (int, float)) and seconds > MAX_SECONDS:
            continue
        out.append((job.get("priority") or 0, job, str(file)))
    # Freshest story first: within a day the newest event is the one worth posting, and priority
    # alone floated older renders above it.
    out.sort(key=lambda x: (-x[0], str(x[1].get("created") or "")))
    return out


def caption_for(job: dict) -> str:
    """Badge, hook in Mtavruli, the story's own lede, the story link, up to ten hashtags."""
    try:
        story = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return social_copy.caption("", "", f"https://tbilisi.today/stories/{job.get('ref')}",
                                   kind="video")
    if not isinstance(story, dict):
        return social_copy.caption("", "", "", kind="video")
    hook = next((s for s in story.get("scenes", []) if s.get("type") == "hook"), {})
    title = " ".join(hook.get("lines") or [])
    if not title:
        title = story.get("narration", "")[:90]
    category = social_copy.CAT_KA.get(str(story.get("category") or ""), None)
    return social_copy.caption(title, story.get("narration", ""),
                               f"https://tbilisi.today/stories/{job.get('ref')}",
                               kind="video", category_ka=category, summary_limit=240)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="publish to the Page (default: dry)")
    ap.add_argument("--max", type=int, default=LIMIT)
    ap.add_argument("--ignore-gap", action="store_true", help="skip the pacing check (testing)")
    a = ap.parse_args()

    state = _load()
    state.setdefault("posted", {})
    # Forget entries older than 30 days: the file is a dedupe ledger, not an archive.
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["posted"] = {k: v for k, v in state["posted"].items() if str(v.get("at", "")) >= cutoff}

    today = dt.datetime.now(dt.timezone.utc).astimezone(
        dt.timezone(dt.timedelta(hours=4))).date().isoformat()
    used = _today_count(state, today)
    budget = max(0, a.max - used)
    if budget == 0:
        print(json.dumps({"skipped": "daily_cap", "used": used}))
        return 0
    last = _last_post(state)
    if not a.ignore_gap and last and (dt.datetime.now(dt.timezone.utc) - last).total_seconds() < MIN_GAP_MIN * 60:
        print(json.dumps({"skipped": "min_gap", "last": last.strftime("%Y-%m-%dT%H:%M:%SZ")}))
        return 0

    todo = candidates(state)
    if not todo:
        print(json.dumps({"skipped": "no_candidates"}))
        return 0

    if a.live:
        try:
            info = facebook.verify()
        except (facebook.MissingCredentials, facebook.GraphError) as e:
            out = {"aborted": f"{type(e).__name__}: {getattr(e, 'message', str(e))[:200]}"}
            receipt({**out, "action": "aborted"})
            print(json.dumps(out, ensure_ascii=False))
            return 2
        if str(info.get("id")) != str(facebook.page_id()):
            out = {"aborted": f"token is for page {info.get('id')}, expected {facebook.page_id()}"}
            receipt({**out, "action": "aborted"})
            print(json.dumps(out, ensure_ascii=False))
            return 2

    results = []
    for _prio, job, file in todo[:budget]:
        caption = caption_for(job)
        cid = job.get("ref")
        link = f"https://tbilisi.today/stories/{cid}"
        try:
            out = facebook.send_video(file, caption, dry=not a.live)
        except Exception as e:  # noqa: BLE001 - a receipt beats a traceback in a cron log
            out = {"ok": False, "error": {"message": f"{type(e).__name__}: {str(e)[:200]}"}}
        rec = {"job": job["id"], "cid": cid, "file": pathlib.Path(file).name,
               "ok": bool(out.get("ok")), "video_id": out.get("video_id"),
               "error": out.get("error"), "status": out.get("status"),
               "action": ("posted" if a.live else "dry") if out.get("ok") else "error"}
        if out.get("ok") and a.live:
            # The link already sits in the description, so no first comment here. If the comment
            # shape comes back (LINK_IN_BODY off), it must target out["post_id"], never video_id.
            state["posted"][job["id"]] = {
                "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cid": cid, "video_id": out.get("video_id")}
            _save(state)
        receipt(rec)
        results.append(rec)

    print(json.dumps({"live": a.live, "results": results}, ensure_ascii=False)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
