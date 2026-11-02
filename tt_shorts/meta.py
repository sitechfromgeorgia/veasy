"""What a video shows that comes from data, not from the writer: the date in the brand's time zone, the category
word, the category family (it picks the look, the voice and the music), the story link and its QR code, and the
call to action. All of it is read from the story's brand pack (brand.py); `b` defaults to the default pack.

Layout lives in remotion/src; colors come from the pack too, so nothing here is a color.
"""
import datetime as dt
import zlib

import segno

from tt_shorts import brand

FAMILIES = brand.FAMILIES


def _b(b):
    return b if isinstance(b, dict) else brand.load(b)


def tz(b=None):
    return dt.timezone(dt.timedelta(hours=_b(b)["utc_offset_hours"]))


def family(category, b=None):
    b = _b(b)
    return b["family_by_category"].get(category, b["default_family"])


def variant_for(category, b=None):
    """The look follows the kind of story (owner, 2026-11-01: "different styles for different kinds of stories")."""
    b = _b(b)
    return b["look_by_family"][family(category, b)]


def category_label(category, b=None):
    b = _b(b)
    return b["categories"].get(category, b["strings"]["category_default"])


def ka_date(iso, b=None):
    """'2026-11-01T18:38:46Z' -> {'date': '1 ნოემბერი 2026', 'time': '22:38', 'weekday': 'კვირა', 'day': date}
    in the brand's time zone (Tbilisi, UTC+4 all year, for the Georgian packs). The video's date is always the
    data's, never the writer's."""
    b = _b(b)
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00").replace(" ", "T"))
    if t.tzinfo is None:  # D1 datetime('now') strings are UTC
        t = t.replace(tzinfo=dt.timezone.utc)
    t = t.astimezone(tz(b))
    return {"date": f"{t.day} {b['months'][t.month - 1]} {t.year}", "time": f"{t:%H:%M}",
            "weekday": b["weekdays"][t.weekday()], "day": t.date()}


def when(d, b=None, now=None):
    """The hook's date chip: always the date, never the pack's word for "today". A video is watched for days, so
    "დღეს" would be wrong tomorrow (the same reason N4 keeps relative days out of the writer's text)."""
    return d["date"]


def cta_for(story_id, b=None):
    """End-card call to action (the accent button: an active action), rotated by story id."""
    ctas = _b(b)["ctas"]
    return ctas[zlib.crc32(str(story_id).encode()) % len(ctas)]


def story_url(story_id, platform="shorts", b=None):
    """The tracked link the QR code opens."""
    return _b(b)["link"]["qr"].format(id=story_id, platform=platform)


def display_url(story_id, b=None):
    """The link as the video shows it."""
    return _b(b)["link"]["display"].format(id=story_id)


def links(story, platform="shorts", b=None):
    """(the link as shown, the URL the QR opens). The pack's story page, unless the story's source gave its own: a
    program with "link": "source" (a law on matsne.gov.ge) sets story["link"] from the data, never from a writer
    (engine.write_story, programs.stamp)."""
    own = story.get("link") if story.get("program") not in (None, "news") else None  # news: always the pack's page
    if isinstance(own, dict) and str(own.get("qr", "")).startswith(("https://", "http://")) and own.get("display"):
        return own["display"], own["qr"]
    return display_url(story["id"], b), story_url(story["id"], platform, b)


def qr_svg(url, dark="#05080F"):
    return segno.make(url, error="m").svg_inline(scale=10, dark=dark, light="#FFFFFF", border=2, omitsize=True)


def sources_line(names, shown=3, b=None):
    """The footer's credit: the outlets the story comes from (the source is always visible)."""
    if not names:
        return ""
    s = _b(b)["strings"]
    more = f" +{len(names) - shown}" if len(names) > shown else ""
    return (s["source_one"] if len(names) == 1 else s["source_many"]) + ": " + ", ".join(names[:shown]) + more
