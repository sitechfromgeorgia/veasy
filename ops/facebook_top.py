"""Post finished videos to a brand's Facebook Page as Reels, once each.

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
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import brand as packs, facebook, meta, queue, reel_cover, social_copy, store  # noqa: E402

RECEIPTS = store.home() / "logs" / "fb-video-receipts.jsonl"
BATCH = 3              # posts per run
PAUSE_S = 120          # seconds between two posts inside one run
MIN_GAP_MIN = 15       # minutes between runs
LOCAL_TZ = dt.timezone(dt.timedelta(hours=4))   # the owner's calendar day, +04
AGE_HOURS = 18         # same freshness rule as the Telegram video lane
MAX_SECONDS = 90       # Reels hard limit; a longer render is not a reel


def _mark_path(brand_name: str) -> pathlib.Path:
    if brand_name == packs.DEFAULT:
        return ROOT / "data" / "facebook-posted.json"
    return ROOT / "data" / f"facebook-posted-{brand_name}.json"


def receipt(rec: dict) -> None:
    rec = {"ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **rec}
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _load(mark: pathlib.Path) -> dict:
    try:
        return json.loads(mark.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save(mark: pathlib.Path, state: dict) -> None:
    mark.parent.mkdir(parents=True, exist_ok=True)
    tmp = mark.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(mark)


def _today_count(state: dict, today: str) -> int:
    """Posts already published on the owner's calendar day.

    The ledger stamps `at` in UTC while `today` is a +04 date, so comparing the first ten characters
    treated every post made after 20:00 local as yesterday's: the cap read zero and the lane could
    publish past it. Convert before comparing instead of slicing the string.
    """
    n = 0
    for v in (state.get("posted") or {}).values():
        try:
            at = dt.datetime.strptime(str(v.get("at")), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
            if at.astimezone(LOCAL_TZ).strftime("%Y-%m-%d") == today:
                n += 1
        except ValueError:
            continue
    return n


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


def candidates(state: dict, brand_name: str = packs.DEFAULT) -> list[tuple[int, dict, str]]:
    posted = set((state.get("posted") or {}))
    posted_cids = {str((v or {}).get("cid")) for v in (state.get("posted") or {}).values()
                   if (v or {}).get("cid")}
    # This window must be the same one the Telegram lane uses. At 12 h a render made for Telegram
    # stayed visible to Telegram for 18 h but vanished from here after 12, so a file that missed one
    # Facebook batch was silently lost forever even though the Telegram lane would still have posted
    # it. The owner asked for Facebook to publish what Telegram already has; that only holds if both
    # lanes look at the same renders for the same length of time.
    cutoff = dt.datetime.now().timestamp() - AGE_HOURS * 3600
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
        if job["id"] in posted or str(job.get("ref") or "") in posted_cids:
            continue
        try:
            story = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(story, dict):
            continue
        if (story.get("brand") or job.get("brand") or packs.DEFAULT) != brand_name:
            continue
        if story.get("private") is True or story.get("visibility") == "private":
            continue
        stamp = 0.0
        try:
            when = dt.datetime.fromisoformat(str(story.get("date") or "").replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
            if (dt.datetime.now(dt.timezone.utc) - when).total_seconds() > AGE_HOURS * 3600:
                continue
            stamp = when.timestamp()
        except (ValueError, TypeError):
            pass
        seconds = result.get("seconds")
        if isinstance(seconds, (int, float)) and seconds > MAX_SECONDS:
            continue
        out.append((stamp, job, str(file)))
    out.sort(key=lambda x: -float(x[0]))
    return out


def link_for(job: dict, story: dict | None, pack: dict) -> str:
    if isinstance(story, dict):
        own = (story.get("link") or {}).get("qr") or story.get("url")
        if isinstance(own, str) and own.startswith(("http://", "https://")):
            return own
    return meta.story_url(job.get("ref") or (story or {}).get("id") or "", "facebook", pack)


def caption_for(job: dict, pack: dict) -> str:
    """Badge, hook in Mtavruli, the story's own lede, the story link, pack hashtags."""
    try:
        story = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return social_copy.caption("", "", link_for(job, None, pack), kind="video", brand=pack)
    if not isinstance(story, dict):
        return social_copy.caption("", "", "", kind="video", brand=pack)
    hook = next((s for s in story.get("scenes", []) if s.get("type") == "hook"), {})
    title = " ".join(hook.get("lines") or [])
    if not title:
        title = story.get("narration", "")[:90]
    category = str(story.get("category") or "") or None
    return social_copy.caption(title, story.get("narration", ""),
                               link_for(job, story, pack),
                               kind="video", category=category, summary_limit=240, brand=pack)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", default=packs.DEFAULT, help="brand pack name")
    ap.add_argument("--live", action="store_true", help="publish to the Page (default: dry)")
    ap.add_argument("--max", type=int, default=None, help="daily ceiling (default: pack reels_per_day)")
    ap.add_argument("--batch", type=int, default=BATCH, help="posts allowed in this run")
    ap.add_argument("--pause", type=int, default=PAUSE_S, help="seconds between posts in one run")
    ap.add_argument("--ignore-gap", action="store_true", help="skip the pacing check (testing)")
    a = ap.parse_args()

    try:
        pack, _fb = packs.require_social(a.brand, "facebook")
    except packs.BrandError as e:
        print(json.dumps({"aborted": str(e)}, ensure_ascii=False))
        return 2
    daily_limit = a.max if a.max is not None else facebook.daily_target(pack)
    mark = _mark_path(pack["name"])

    state = _load(mark)
    state.setdefault("posted", {})
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["posted"] = {k: v for k, v in state["posted"].items() if str(v.get("at", "")) >= cutoff}

    today = dt.datetime.now(dt.timezone.utc).astimezone(
        dt.timezone(dt.timedelta(hours=4))).date().isoformat()
    used = _today_count(state, today)
    budget = max(0, min(daily_limit - used, a.batch))
    if budget == 0:
        print(json.dumps({"skipped": "daily_cap", "used": used, "cap": daily_limit}))
        return 0
    last = _last_post(state)
    if not a.ignore_gap and last and (dt.datetime.now(dt.timezone.utc) - last).total_seconds() < MIN_GAP_MIN * 60:
        print(json.dumps({"skipped": "min_gap", "last": last.strftime("%Y-%m-%dT%H:%M:%SZ")}))
        return 0

    todo = candidates(state, pack["name"])
    if not todo:
        print(json.dumps({"skipped": "no_candidates"}))
        return 0

    if a.live:
        try:
            info = facebook.verify(brand=pack)
        except (facebook.MissingCredentials, facebook.GraphError, packs.BrandError) as e:
            out = {"aborted": f"{type(e).__name__}: {getattr(e, 'message', str(e))[:200]}"}
            receipt({**out, "action": "aborted"})
            print(json.dumps(out, ensure_ascii=False))
            return 2
        if str(info.get("id")) != str(facebook.page_id(brand=pack)):
            out = {"aborted": f"token is for page {info.get('id')}, expected {facebook.page_id(brand=pack)}"}
            receipt({**out, "action": "aborted"})
            print(json.dumps(out, ensure_ascii=False))
            return 2

    covers_dir = store.home() / "cache" / "covers"
    results = []
    for index, (_prio, job, file) in enumerate(todo[:budget]):
        if index and a.pause:
            time.sleep(a.pause)
        caption = caption_for(job, pack)
        cid = job.get("ref")
        try:
            story_obj = json.loads(pathlib.Path(job["story"]).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            story_obj = None
        link = link_for(job, story_obj if isinstance(story_obj, dict) else None, pack)
        try:
            out = facebook.send_video(file, caption, dry=not a.live, brand=pack)
        except Exception as e:  # noqa: BLE001 - a receipt beats a traceback in a cron log
            out = {"ok": False, "error": {"message": f"{type(e).__name__}: {str(e)[:200]}"}}
        rec = {"job": job["id"], "cid": cid, "brand": pack["name"], "file": pathlib.Path(file).name,
               "ok": bool(out.get("ok")), "video_id": out.get("video_id"),
               "error": out.get("error"), "status": out.get("status"),
               "action": ("posted" if a.live else "dry") if out.get("ok") else "error"}
        if out.get("ok") and a.live:
            state["posted"][job["id"]] = {
                "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cid": cid, "video_id": out.get("video_id")}
            _save(mark, state)
            try:
                cover_path = covers_dir / f"fb-reel-{pack['name']}-{cid}.jpg"
                cover = reel_cover.from_story(
                    job["id"], story_obj if isinstance(story_obj, dict) else {},
                    str(cover_path), brand=pack)
                thumb = facebook.set_thumbnail(out.get("video_id") or "", cover, brand=pack)
                rec["cover"] = bool(thumb.get("ok"))
                if not thumb.get("ok"):
                    rec["cover_error"] = json.dumps(thumb.get("error"), ensure_ascii=False)[:200]
            except Exception as e:  # noqa: BLE001 - a cover failure must not lose the post
                rec["cover_error"] = f"{type(e).__name__}: {str(e)[:160]}"
            target = out.get("post_id")
            if not target and out.get("video_id"):
                resolved = facebook.post_object_id(out["video_id"], brand=pack)
                rec["post_id_resolved"] = resolved.get("object_id")
                if resolved.get("ok"):
                    target = resolved["object_id"]
                else:
                    rec["comment_error"] = json.dumps(resolved.get("error"), ensure_ascii=False)[:180]
            if target:
                cmt = facebook.comment(target, f"სრული სტატია: {link}", brand=pack)
                rec["comment_id"] = cmt.get("id")
                rec["comment_on"] = target
                if not cmt.get("ok"):
                    rec["comment_error"] = json.dumps(cmt.get("error"), ensure_ascii=False)[:180]

        receipt(rec)
        results.append(rec)

    print(json.dumps({"live": a.live, "results": results}, ensure_ascii=False)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
