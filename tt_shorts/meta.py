"""What a video shows that comes from data, not from the writer: the date in Tbilisi time, the category word, the
category family (it picks the music), the story link and its QR code, and the call to action.

Colors and layout live in remotion/src (brand.ts): the brand has one palette, so nothing here is a color.
"""
import datetime as dt
import zlib

import segno

TBILISI = dt.timezone(dt.timedelta(hours=4))  # Georgia keeps UTC+4 all year

# Category families: 20 site categories, 8 music moods (tools/compose_music.py PIECES).
FAMILIES = ("politics", "economy", "world", "crime", "sports", "culture", "tech", "society")
CATEGORY_FAMILY = {
    "politics": "politics", "defense": "politics",
    "economy": "economy", "realestate": "economy", "auto": "economy",
    "world": "world",
    "crime": "crime", "incidents": "crime",
    "sports": "sports", "sport": "sports",
    "culture": "culture", "showbusiness": "culture", "showbiz": "culture", "religion": "culture",
    "tech": "tech", "science": "tech",
}  # everything else (society, medicine, education, region, tourism, ecology, general...) is "society"
CATEGORY_KA = {  # web/src/index.ts CATEGORY_KA
    "politics": "პოლიტიკა", "economy": "ეკონომიკა", "society": "საზოგადოება", "world": "მსოფლიო",
    "sports": "სპორტი", "culture": "კულტურა", "tech": "ტექნოლოგია", "general": "ამბები", "crime": "კრიმინალი",
    "defense": "თავდაცვა", "region": "რეგიონი", "science": "მეცნიერება", "lifestyle": "ცხოვრება",
    "showbusiness": "შოუბიზნესი", "religion": "რელიგია", "medicine": "მედიცინა", "education": "განათლება",
    "auto": "ავტო", "realestate": "უძრავი ქონება", "tourism": "ტურიზმი", "ecology": "ეკოლოგია",
    "incidents": "შემთხვევები",
}
MONTHS = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი", "ივლისი", "აგვისტო", "სექტემბერი",
          "ოქტომბერი", "ნოემბერი", "დეკემბერი"]
WEEKDAYS = ["ორშაბათი", "სამშაბათი", "ოთხშაბათი", "ხუთშაბათი", "პარასკევი", "შაბათი", "კვირა"]
# End-card calls to action (the red button: an active action is one of red's three uses); rotated by story id.
CTAS = ["გამოიწერე არხი", "მოიწონე და გააზიარე", "მხარი დაგვიჭირე: tbilisi.today/support"]


def family(category):
    return CATEGORY_FAMILY.get(category, "society")


def category_label(category):
    return CATEGORY_KA.get(category, "ამბები")


def ka_date(iso):
    """'2026-11-01T18:38:46Z' -> {'date': '1 ნოემბერი 2026', 'time': '22:38', 'weekday': 'კვირა', 'day': date}
    in Tbilisi time. The video's date is always the data's, never the writer's."""
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00").replace(" ", "T"))
    if t.tzinfo is None:  # D1 datetime('now') strings are UTC
        t = t.replace(tzinfo=dt.timezone.utc)
    t = t.astimezone(TBILISI)
    return {"date": f"{t.day} {MONTHS[t.month - 1]} {t.year}", "time": f"{t:%H:%M}", "weekday": WEEKDAYS[t.weekday()],
            "day": t.date()}


def cta_for(story_id):
    return CTAS[zlib.crc32(str(story_id).encode()) % len(CTAS)]


def story_url(story_id, platform="shorts"):
    return f"https://tbilisi.today/stories/{story_id}?utm_source={platform}&utm_medium=video"


def qr_svg(url, dark="#05080F"):
    return segno.make(url, error="m").svg_inline(scale=10, dark=dark, light="#FFFFFF", border=2, omitsize=True)


def sources_line(names, shown=3):
    """The footer's credit: the outlets the story comes from (brand v1.2: the source is always visible)."""
    if not names:
        return ""
    more = f" +{len(names) - shown}" if len(names) > shown else ""
    return ("წყარო: " if len(names) == 1 else "წყაროები: ") + ", ".join(names[:shown]) + more
