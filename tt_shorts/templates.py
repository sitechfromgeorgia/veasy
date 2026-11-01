"""tbilisi.today news Short templates: one scene vocabulary, three looks.

  A  ღამის რედაქცია (night desk): the brand's dark canvas and blueprint grid, the category color as the accent
  B  გაზეთი (paper): a light newspaper page, a centered masthead, printed-ink accents, column rules
  C  Kinetic: the category color fills the frame, big type slams in, accent blocks

A story is JSON (see stories/*.json). The writer only fills these fields; layout, motion, brand, date, sources
and QR come from here. Every scene has `type`, `at` (the first spoken words of that scene), `kicker` and
`headline`, plus the fields of its type:

  hook      lines[] (the last one in the accent)
  stat      value (int), prefix, suffix, label
  timeline  big, start, end, label
  where     place, sub
  who       items[{name, role}] (1-3)
  points    items[] (2-3 short lines)
  quote     text (verbatim from a source), by, via
  sources   (the outlets come from the story's `sources`, never from the writer)
  end       (tbilisi.today card: QR to the story page, the date and the call to action)

Motion is CSS, captured frame by frame (render.py): rise, pop, wipe, count-up, settle, ping and a slow drift
of the whole scene. Delays are `--d`. The platform safe zone is sitech-shorts' (approved 2026-10-28).
"""
import datetime as dt
import html
import zlib

import segno

W, H = 1080, 1920
BUILD_UP = 2.4  # seconds: the latest --d a scene's build-up uses
# Platform safe zone: Shorts / Reels / TikTok draw their caption, channel row and like/share rail over the lower
# frame. Scene text ends at HERO_BOTTOM (after the drift), captions at CAPTION_BOTTOM; below RAIL_Y no words go
# right of RAIL_X. The footer (story link, source count) is branding and sits from FOOTER_Y down.
HERO_BOTTOM, CAPTION_BOTTOM, FOOTER_Y = 1300, 1420, 1770
RAIL_X, RAIL_Y = 940, 1100
DRIFT = 1.035
TEXT_RIGHT = round(W / 2 + (RAIL_X - W / 2) / DRIFT)
SIGNAL = "#EF4444"  # the red period of the mark: brand, never a category color
TBILISI = dt.timezone(dt.timedelta(hours=4))  # Georgia keeps UTC+4 all year

# The mark Edo approved (web/src/brand-v2.ts): near-black square, white geometric t, red period.
T_PATH = ("M1881 3408 c-30 -79 -59 -149 -64 -156 -6 -7 -57 -41 -114 -75 l-103 -62 0 -82 0 -83 94 0 95 0 3 -427 "
          "c3 -417 4 -430 26 -492 46 -128 115 -195 237 -234 58 -18 93 -22 205 -21 134 0 210 13 298 49 l32 14 0 140 "
          "c0 78 -3 141 -6 141 -3 0 -34 -7 -68 -16 -33 -9 -95 -17 -136 -18 -86 -1 -125 15 -162 66 -23 33 -23 33 -26 "
          "416 l-3 382 191 0 190 0 0 145 0 145 -190 0 -190 0 0 155 0 155 -128 0 -127 0 -54 -156z")

# Category families: 20 site categories, 8 looks. Each family has its accent and its music (assets/music).
FAMILIES = {
    "politics": "#60A5FA", "economy": "#FBBF24", "world": "#2DD4BF", "crime": "#FB923C",
    "sports": "#A3E635", "culture": "#C084FC", "tech": "#22D3EE", "society": "#F472B6",
}
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
# End-card calls to action; a story gets one by its id, so the channel rotates them.
CTAS = ["გამოიწერე: მთავარი ამბები ყოველდღე", "მოიწონე და გაუზიარე მეგობრებს", "მხარი დაგვიჭირე: tbilisi.today/support"]


def e(s):
    return html.escape(str(s), quote=False)


def family(category):
    return CATEGORY_FAMILY.get(category, "society")


def category_label(category):
    return CATEGORY_KA.get(category, "ამბები")


def mix(a, b, t):
    """Color a moved toward b by t (0..1), as #rrggbb."""
    pa, pb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(pa, pb))


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


THEMES = {
    "A": {"label": "ღამის რედაქცია", "bg": "#05080F", "panel": "#0B0F17", "ink": "#F8FAFC", "muted": "#A7B0BD",
          "line": "#262D3A"},
    "B": {"label": "გაზეთი", "bg": "#F4EFE6", "panel": "#FFFFFF", "ink": "#121419", "muted": "#5F6674",
          "line": "#D6CDBE"},
    "C": {"label": "Kinetic", "panel": "#05080F", "ink": "#FFFFFF"},
}


def palette(theme, category):
    """The colors of one theme for one category family: bg, panel, ink, muted, line, accent, on_accent and the
    caption colors (cap_fg on cap_box, the spoken word in cap_hi)."""
    base = FAMILIES[family(category)]
    p = dict(THEMES[theme])
    if theme == "A":
        p.update(accent=base, on_accent="#05080F", cap_fg=p["ink"], cap_box="#05080F", cap_hi=base)
    elif theme == "B":
        ink = mix(base, "#000000", 0.45)  # a pastel accent would vanish on paper: print it darker
        p.update(accent=ink, on_accent="#FFFFFF", cap_fg=p["ink"], cap_box="#FFFFFF", cap_hi=ink)
    else:
        bg = mix(base, "#05080F", 0.80)
        p.update(bg=bg, muted=mix("#FFFFFF", bg, 0.30), line=mix(base, bg, 0.55), accent=base, on_accent="#05080F",
                 cap_fg="#FFFFFF", cap_box="#05080F", cap_hi=base)
    return p


def css(assets, p, theme):
    fonts = "".join(f"@font-face{{font-family:Fira;font-weight:{w};src:url(file://{assets}/fonts/firago-{n}.woff2)}}"
                    for w, n in ((400, "regular.d8b411bacd"), (500, "medium.aa3a9ffc55"),
                                 (600, "semibold.51e717afa6"), (700, "bold.ed7553cea8")))
    base = fonts + f"""
@font-face{{font-family:Geo;font-weight:100 900;src:url(file://{assets}/fonts/NotoSansGeorgian.ttf)}}
@property --n{{syntax:'<integer>';inherits:false;initial-value:0}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;overflow:hidden;font-family:Geo,Fira;color:{p['ink']};background:{p['bg']};position:relative}}
.a{{position:absolute}}.o{{color:{p['accent']}}}.m{{color:{p['muted']}}}
.f{{font-family:Fira,Geo}}
.kick{{position:absolute;top:258px;left:74px;font-family:Fira,Geo;font-size:28px;font-weight:600;letter-spacing:.04em;color:{p['accent']}}}
.head{{position:absolute;top:310px;left:74px;width:932px;font-family:Fira,Geo;font-size:48px;font-weight:600;line-height:1.24;letter-spacing:-.01em}}
.huge{{font-family:Fira,Geo;font-weight:700;line-height:1.16;letter-spacing:-.025em;white-space:nowrap;padding-bottom:.06em}}
.card{{border:2px solid {p['line']};border-radius:26px;padding:30px 36px;background:{p['panel']}}}
.chip{{display:inline-block;border:2px solid {p['line']};border-radius:999px;padding:10px 26px;font-size:32px;font-weight:600;white-space:nowrap;background:{p['panel']}}}
.num{{flex:none;width:96px;height:96px;border-radius:50%;border:4px solid {p['accent']};color:{p['accent']};display:flex;align-items:center;justify-content:center;font-family:Fira;font-size:48px;font-weight:700}}
.ini{{flex:none;width:132px;height:132px;border-radius:50%;border:5px solid {p['accent']};color:{p['accent']};display:flex;align-items:center;justify-content:center;font-family:Fira,Geo;font-size:52px;font-weight:700}}
.r,.p,.w,.z,.cnt,.g{{animation-delay:calc(var(--d,0s) * var(--k,1));animation-fill-mode:both}}
.r{{animation-name:rise;animation-duration:.6s;animation-timing-function:cubic-bezier(.16,1,.3,1)}}
.p{{animation-name:pop;animation-duration:.55s;animation-timing-function:cubic-bezier(.34,1.56,.64,1);transform-box:fill-box;transform-origin:center}}
.w{{animation-name:wipe;animation-duration:.7s;animation-timing-function:cubic-bezier(.65,0,.35,1)}}
.z{{animation-name:settle;animation-duration:1.4s;animation-timing-function:cubic-bezier(.16,1,.3,1)}}
.g{{animation-name:ping;animation-duration:1.8s;animation-iteration-count:4;animation-timing-function:cubic-bezier(.16,1,.3,1);transform-box:fill-box;transform-origin:center;animation-fill-mode:backwards}}
.cnt{{animation-name:count;animation-duration:1.3s;animation-timing-function:cubic-bezier(.16,1,.3,1);counter-reset:n var(--n)}}
.cnt::after{{content:counter(n)}}
#hero{{position:absolute;inset:0;transform-origin:50% 45%;animation:drift var(--dur) linear both}}
#bg{{position:absolute;left:0;top:-60px;animation:pan var(--dur) linear both}}
@keyframes rise{{from{{opacity:0;transform:translateY(54px)}}to{{opacity:1;transform:none}}}}
@keyframes pop{{from{{opacity:0;transform:scale(.4)}}to{{opacity:1;transform:none}}}}
@keyframes wipe{{from{{clip-path:inset(-20% 100% -20% 0)}}to{{clip-path:inset(-20% -2% -20% 0)}}}}
@keyframes settle{{from{{opacity:0;transform:scale(1.14)}}to{{opacity:1;transform:none}}}}
@keyframes ping{{from{{opacity:.9;transform:scale(.2)}}to{{opacity:0;transform:scale(1.6)}}}}
@keyframes count{{from{{--n:0}}to{{--n:var(--to)}}}}
@keyframes drift{{from{{transform:none}}to{{transform:scale({DRIFT})}}}}
@keyframes pan{{from{{transform:none}}to{{transform:translateY(54px)}}}}
"""
    if theme == "B":  # paper: section label with a bar, bolder ink, square number blocks, no card borders
        base += f"""
.kick{{color:{p['ink']};font-weight:700;padding-left:22px;border-left:9px solid {p['accent']};line-height:1}}
.head{{font-weight:700;font-size:50px}}
.card{{border:none;border-radius:6px;box-shadow:0 3px 0 {p['line']},0 0 0 2px {p['line']}}}
.chip{{border-radius:6px;border-color:{p['ink']}}}
.num{{border-radius:6px;border:none;background:{p['accent']};color:#fff}}
.ini{{border:none;background:{p['accent']};color:#fff;border-radius:8px}}
"""
    if theme == "C":  # kinetic: blocks of color, type slams in from the left
        base += f"""
.kick{{background:{p['accent']};color:{p['on_accent']};padding:8px 18px 10px;font-weight:700;letter-spacing:.02em}}
.head{{font-weight:700;font-size:52px}}
.huge{{font-weight:700;letter-spacing:-.03em}}
.card{{border:none;background:{p['panel']};border-radius:0;box-shadow:12px 12px 0 {p['accent']}}}
.chip{{border:none;border-radius:0;background:{p['panel']}}}
.num{{border:none;border-radius:0;background:{p['panel']}}}
.ini{{border:none;border-radius:0;background:{p['accent']};color:{p['on_accent']}}}
.r{{animation-name:slam;animation-duration:.5s;animation-timing-function:cubic-bezier(.2,1.2,.3,1)}}
@keyframes slam{{from{{opacity:0;transform:translateX(-140px) skewX(-10deg)}}to{{opacity:1;transform:none}}}}
.blk{{background:{p['accent']};color:{p['on_accent']};padding:0 .14em;margin-left:-.14em}}
"""
    return base


def mark(size):
    return (f'<svg width={size} height={size} viewBox="0 0 512 512"><rect width=512 height=512 rx=112 fill="#0B0B0E" '
            f'stroke="#2A3140" stroke-width=6 /><g transform="translate(0,512) scale(0.1,-0.1)"><path d="{T_PATH}" '
            f'fill="#FFFFFF"/></g><circle cx=323 cy=295 r=34 fill="{SIGNAL}"/></svg>')


def wordmark(size, ink):
    return (f'<span class=f style="font-size:{size}px;font-weight:700;letter-spacing:-.02em;color:{ink}">tbilisi'
            f'<span style="color:{SIGNAL}">.</span>today</span>')


def background(p, theme, category):
    if theme == "A":  # blueprint grid, as on the brand guide
        cell = 54
        motif = f'<path d="M{cell} 0H0V{cell}" fill=none stroke="{p["line"]}" stroke-opacity=".55" stroke-width=1 />'
        return (f'<svg id=bg width={W} height={H + 120}><defs><pattern id=g width={cell} height={cell} '
                f'patternUnits=userSpaceOnUse>{motif}</pattern></defs><rect width={W} height={H + 120} fill="url(#g)" />'
                f'<rect width={W} height={H + 120} fill="url(#v)" /><defs><radialGradient id=v cx=".5" cy=".42" r=".75">'
                f'<stop offset=".55" stop-color="{p["bg"]}" stop-opacity="0"/><stop offset="1" stop-color="{p["bg"]}"/>'
                f'</radialGradient></defs></svg>')
    if theme == "B":  # column rules of a broadsheet
        rules = "".join(f'<line x1={x} y1=0 x2={x} y2={H + 120} stroke="{p["line"]}" stroke-width=2 />' for x in (360, 720))
        return f'<svg id=bg width={W} height={H + 120} style="opacity:.55">{rules}</svg>'
    # C: a wide accent band across the frame and the category word as a watermark
    word = category_label(category)
    return (f'<svg id=bg width={W} height={H + 120}>'
            f'<rect x=-300 y=1180 width=1800 height=260 fill="{p["accent"]}" fill-opacity=".14" transform="rotate(-12 540 1300)" />'
            f'<rect x=-300 y=1500 width=1800 height=40 fill="{p["accent"]}" fill-opacity=".30" transform="rotate(-12 540 1520)" />'
            f'<text x=-20 y=1690 font-family="Fira,Geo" font-weight=700 font-size=260 fill="#FFFFFF" fill-opacity=".05">{e(word)}</text>'
            f'</svg>')


def chrome(ctx, p, theme):
    """Persistent header (brand, date, category) and footer (story link, source count) on every scene."""
    d = ka_date(ctx["date"])
    cat = category_label(ctx["category"])
    n = len(ctx.get("sources") or [])
    url = f'tbilisi.today/stories/{ctx["id"]}'
    if theme == "B":  # masthead: wordmark centered, a double rule, the full date line under it
        head = (f'<div class="a" style="left:0;width:{W}px;top:84px;text-align:center">{wordmark(62, p["ink"])}</div>'
                f'<div class=a style="left:74px;right:74px;top:172px;height:3px;background:{p["ink"]}"></div>'
                f'<div class=a style="left:74px;right:74px;top:179px;height:1px;background:{p["ink"]}"></div>'
                f'<div class="a f" style="left:74px;top:192px;font-size:25px;font-weight:600;color:{p["ink"]}">'
                f'{d["weekday"]}, {d["date"]} &middot; {d["time"]}</div>'
                f'<div class="a f" style="right:74px;top:192px;font-size:25px;font-weight:700;color:{p["accent"]}">{e(cat)}</div>')
    else:
        dot = f'<span style="color:{p["accent"]}">&#9679;</span>'
        head = (f'<div class=a style="left:72px;top:96px;display:flex;align-items:center;gap:20px">{mark(76)}'
                f'{wordmark(40, p["ink"])}</div>'
                f'<div class="a f" style="right:80px;top:98px;text-align:right;line-height:1.3">'
                f'<div style="font-size:31px;font-weight:700;color:{p["ink"]}">{d["date"]}</div>'
                f'<div style="font-size:24px;font-weight:600;color:{p["muted"]}">{d["time"]} &middot; {dot} {e(cat)}</div></div>'
                f'<div class=a style="left:76px;right:80px;top:200px;height:2px;background:{p["line"]}"></div>'
                f'<div class="a w" style="left:76px;width:300px;top:200px;height:2px;background:{p["accent"]}"></div>')
    foot = (f'<div class=a style="left:76px;right:80px;top:{FOOTER_Y}px;height:2px;background:{p["line"]}"></div>'
            f'<div class="a f" style="left:74px;top:{FOOTER_Y + 22}px;font-size:30px;font-weight:700;color:{p["ink"]}">'
            f'{e(url)}</div>'
            f'<div class="a f m" style="right:80px;top:{FOOTER_Y + 26}px;font-size:25px;font-weight:600">'
            f'{n} წყარო &middot; {e(d["date"])}</div>')
    return background(p, theme, ctx["category"]) + head + foot


def lines_html(lines, accent, top, size, step=0.14, start=0.35, lh=1.16, width=944, theme="A"):
    def one(i, t):
        if i in accent and theme == "C":  # kinetic: the accent line is a color block, not colored text
            return f'<div class=r style="--d:{start + i * step:.2f}s"><span class=blk>{e(t)}</span></div>'
        return f'<div class="r{" o" if i in accent else ""}" style="--d:{start + i * step:.2f}s">{e(t)}</div>'
    out = "".join(one(i, t) for i, t in enumerate(lines))
    return (f'<div class="a huge" style="left:68px;top:{top}px;width:{width}px;font-size:{size}px;line-height:{lh}" '
            f'data-fit>{out}</div>')


def hook(s, ctx, p, theme):
    n = len(ctx.get("sources") or [])
    d = ka_date(ctx["date"])
    when = "დღეს" if d["day"] == dt.datetime.now(TBILISI).date() else d["date"]
    under = (f'<div style="height:10px;width:340px;background:{p["accent"]};margin-top:18px" class=w></div>'
             if theme == "B" else "")
    chips = (f'<div class="r" style="display:flex;gap:18px;margin-top:64px;--d:1.0s">'
             f'<span class=chip><span class=o>&#9679;</span> {n} წყარო</span><span class="chip m">{e(when)}</span></div>')
    return (f'<div class=a style="left:68px;top:500px;width:944px">'
            + lines_html(s["lines"], {len(s["lines"]) - 1}, 0, 132, start=0.4, theme=theme).replace('class="a huge"', 'class="huge"', 1)
            + under + chips + "</div>")


def stat(s, ctx, p, theme):
    value = int(s["value"])
    if value < 1000:  # counts up from 0
        number = f'<span class=cnt style="--to:{value};--d:.25s"></span>'
    else:  # a CSS counter can't group digits: big numbers rise in, grouped as Georgian writes them ("6 400")
        number = f'<span class="r" style="display:inline-block;--d:.25s">{f"{value:,}".replace(",", " ")}</span>'
    return (f'<div class="a huge o" style="left:56px;top:430px;width:968px;font-size:330px;line-height:1.05" data-fit>'
            f'{e(s.get("prefix", ""))}{number}{e(s.get("suffix", ""))}</div>'
            f'<div class="a r f" style="left:74px;top:820px;width:932px;font-size:54px;font-weight:700;line-height:1.25;--d:.6s" '
            f'data-fit-h=210>{e(s["label"])}</div>')


def timeline(s, ctx, p, theme):
    a, ink = p["accent"], p["ink"]
    return (f'<div class="a huge o r" style="left:62px;top:440px;width:956px;font-size:150px;--d:.3s" data-fit>{e(s["big"])}</div>'
            f'<svg class="a w" style="left:74px;top:740px;--d:.75s" width=932 height=150>'
            f'<line x1=12 y1=40 x2=920 y2=40 stroke="{a}" stroke-width=6 stroke-dasharray="18 14" />'
            f'<circle cx=14 cy=40 r=13 fill="{ink}" /><circle cx=916 cy=40 r=15 fill="{a}" />'
            f'<text x=0 y=112 font-family="Fira,Geo" font-weight=700 font-size=38 fill="{ink}">{e(s["start"])}</text>'
            f'<text x=932 y=112 text-anchor=end font-family="Fira,Geo" font-weight=700 font-size=38 fill="{a}">{e(s["end"])}</text></svg>'
            f'<div class="a r f" style="left:74px;top:940px;width:932px;font-size:50px;font-weight:700;line-height:1.25;--d:1.3s" '
            f'data-fit-h=140>{e(s["label"])}</div>')


def where(s, ctx, p, theme):
    a = p["accent"]
    rings = "".join(f'<circle class=g cx=180 cy=180 r=150 fill=none stroke="{a}" stroke-width=4 style="--d:{0.3 + i * 0.45:.2f}s" />'
                    for i in range(3))
    pin = (f'<g class=p style="--d:.2s"><path d="M180 70c-50 0-88 38-88 86 0 64 88 150 88 150s88-86 88-150c0-48-38-86-88-86z" '
           f'fill="{a}" /><circle cx=180 cy=156 r=32 fill="{p["bg"]}" /></g>')
    return (f'<svg class=a style="left:360px;top:400px" width=360 height=360 viewBox="0 0 360 360">{rings}{pin}</svg>'
            f'<div class="a huge r" style="left:68px;top:790px;width:944px;font-size:104px;text-align:center;--d:.6s" data-fit>{e(s["place"])}</div>'
            f'<div class="a r f m" style="left:74px;top:940px;width:932px;font-size:44px;font-weight:600;text-align:center;--d:.85s" data-fit>{e(s.get("sub", ""))}</div>')


def initials(name):
    parts = [w for w in name.split() if w]
    return "".join(w[0] for w in parts[:2])


def who(s, ctx, p, theme):
    items = s["items"][:3]
    gap = 250 if len(items) < 3 else 222
    out = ""
    for i, it in enumerate(items):
        out += (f'<div class="a card r" style="left:74px;top:{490 + i * gap}px;width:{TEXT_RIGHT - 74}px;display:flex;align-items:center;gap:34px;--d:{0.3 + i * 0.4:.2f}s">'
                f'<div class=ini>{e(initials(it["name"]))}</div><div style="min-width:0;flex:1">'
                f'<div class="huge" style="font-size:58px;overflow:hidden" data-fit>{e(it["name"])}</div>'
                f'<div class="m f" style="font-size:34px;font-weight:600;margin-top:4px;white-space:nowrap;overflow:hidden" data-fit>{e(it.get("role", ""))}</div></div></div>')
    return out


def points(s, ctx, p, theme):
    out = ""
    for i, t in enumerate(s["items"][:3]):
        out += (f'<div class="a r" style="left:74px;top:{500 + i * 220}px;width:{TEXT_RIGHT - 74}px;display:flex;align-items:center;gap:34px;--d:{0.3 + i * 0.45:.2f}s">'
                f'<div class=num>{i + 1}</div><div class=f style="font-size:56px;font-weight:700;line-height:1.2;flex:1;min-width:0" data-fit-h=150>{e(t)}</div></div>')
    return out


def quote(s, ctx, p, theme):
    # Georgian opens a quote low („): the big mark sits above the text, never on its first line
    mark_ = (f'<div class="a p f" style="left:62px;top:378px;font-size:200px;line-height:1;font-weight:700;color:{p["accent"]};--d:.1s">&bdquo;</div>'
             if theme != "C" else
             f'<div class="a p" style="left:74px;top:470px;width:18px;height:540px;background:{p["accent"]};--d:.1s"></div>')
    left = 74 if theme != "C" else 130
    by = e(s.get("by", ""))
    via = e(s.get("via", ""))
    return (mark_ +
            f'<div class="a r f" style="left:{left}px;top:{610 if theme != "C" else 480}px;width:{1006 - left}px;font-size:66px;font-weight:600;line-height:1.3;--d:.35s" '
            f'data-fit-h=440>&bdquo;{e(s["text"])}&ldquo;</div>'
            f'<div class="a r f" style="left:{left}px;top:1090px;width:{TEXT_RIGHT - left}px;font-size:38px;font-weight:700;--d:1.0s" data-fit>'
            f'<span class=o>&mdash;</span> {by}<span class=m style="font-weight:600">{", " + via if via else ""}</span></div>')


def sources(s, ctx, p, theme):
    names = ctx.get("sources") or []
    chips = "".join(f'<span class="chip r" style="--d:{0.7 + i * 0.12:.2f}s">{e(n)}</span>' for i, n in enumerate(names[:8]))
    more = f'<span class="chip m r" style="--d:1.7s">+{len(names) - 8}</span>' if len(names) > 8 else ""
    return (f'<div class="a huge o" style="left:62px;top:420px;font-size:300px;line-height:1"><span class=cnt style="--to:{len(names)};--d:.2s"></span></div>'
            f'<div class="a r f" style="left:74px;top:740px;width:932px;font-size:50px;font-weight:700;--d:.5s" data-fit>მედია აშუქებს ამ ამბავს</div>'
            f'<div class=a style="left:74px;top:850px;width:{TEXT_RIGHT - 74}px;display:flex;flex-wrap:wrap;gap:16px">{chips}{more}</div>')


def end(s, ctx, p, theme):
    d = ka_date(ctx["date"])
    c = f"left:0;width:{W}px;text-align:center"
    url = f'tbilisi.today/stories/{ctx["id"]}'
    qr = qr_svg(story_url(ctx["id"], ctx.get("platform", "shorts")))
    frame = ("border-radius:28px" if theme == "A" else "border-radius:6px" if theme == "B"
             else f"border-radius:0;box-shadow:16px 16px 0 {p['accent']}")
    return (f'<div class="a p" style="left:440px;top:270px;--d:.15s">{mark(200)}</div>'
            f'<div class="a r" style="{c};top:490px;--d:.35s">{wordmark(76, p["ink"])}</div>'
            f'<div class="a z" style="left:340px;top:610px;width:400px;height:400px;background:#fff;padding:14px;{frame};--d:.5s">{qr}</div>'
            f'<div class="a r f" style="{c};top:1036px;font-size:34px;font-weight:700;--d:.8s">{e(url)}</div>'
            f'<div class="a r f o" style="left:150px;width:780px;text-align:center;top:1110px;font-size:40px;font-weight:700;line-height:1.25;--d:1.0s" data-fit-h=110>'
            f'{e(ctx.get("cta") or cta_for(ctx["id"]))}</div>'
            f'<div class="a r f m" style="{c};top:1232px;font-size:28px;font-weight:600;--d:1.15s">{d["date"]}</div>')


TEMPLATES = {"hook": hook, "stat": stat, "timeline": timeline, "where": where, "who": who, "points": points,
             "quote": quote, "sources": sources, "end": end}
NO_HEAD = {"hook", "end"}  # these scenes carry their own big text instead of the kicker + headline


def scene_page(s, ctx, duration):
    theme = ctx.get("theme", "A")
    p = palette(theme, ctx["category"])
    hero = TEMPLATES[s["type"]](s, ctx, p, theme)
    top = ""
    if s["type"] not in NO_HEAD:
        top = (f'<div class="kick w" style="--d:.05s">{e(s.get("kicker", ""))}</div>'
               f'<div class="head r" style="--d:.15s" data-fit-h=124>{e(s.get("headline", ""))}</div>')
    elif s["type"] == "hook":
        top = f'<div class="kick w" style="--d:.05s">{e(s.get("kicker") or category_label(ctx["category"]))}</div>'
    body = chrome(ctx, p, theme) + f"<div id=hero>{top}{hero}</div>"
    # --k squeezes the build-up delays into the first 55% of a short scene, so the finished picture stays up
    k = min(1.0, 0.55 * duration / BUILD_UP)
    return (f"<!doctype html><html><head><meta charset=utf-8><style>{css(ctx['assets'], p, theme)}</style></head>"
            f"<body style='--dur:{duration:.3f}s;--k:{k:.3f}'>{body}</body></html>")
