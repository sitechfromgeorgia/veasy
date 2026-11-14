"""Vertical 1080x1920 covers for Facebook Reels.

Edo, 2026-11-14: „ვიზუალურად რილსებსაც ხო ქოვერი არის ... ყველა ერთმანეთს ჰგავს ... როგორც
ამბებში სხვადასხვა ფერებით არის მსგავსად აქაც რამე ეგეთი გვჭირდება".

The news cards already colour by category; the reels had no cover at all, so Facebook picked a frame
and the grid read as one long grey wall. This module draws the missing cover: one accent per
category, the headline in Mtavruli, and the wordmark, at 1080x1920 so it fills the reel slot.

    from tt_shorts import reel_cover
    reel_cover.build("33070", "რუსთაველის გამზირზე მოძრაობა შეიზღუდება", "politics",
                     "2026-11-15", "/tmp/cover-33070.jpg")

Then `tt_shorts.facebook.set_thumbnail(video_id, path)` makes it the reel's cover.
"""
from __future__ import annotations

import datetime as dt
import math
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
BG = (10, 13, 18)
INK = (247, 249, 251)
MUTED = (168, 176, 186)

REG = next((f for f in ("/usr/local/share/fonts/truetype/noto/NotoSansGeorgian-Regular.ttf",
                        "/root/sitech/assets/firago-regular.ttf")
            if os.path.exists(f)), "/usr/local/share/fonts/truetype/noto/NotoSansGeorgian-Regular.ttf")
BOLD = next((f for f in ("/usr/local/share/fonts/truetype/noto/NotoSansGeorgian-Bold.ttf",
                         "/root/sitech/assets/firago-bold.ttf")
             if os.path.exists(f)), "/usr/local/share/fonts/truetype/noto/NotoSansGeorgian-Bold.ttf")
# FiraGO, the brand face, carries zero Mtavruli glyphs and only ~32 of 80 Mkhedruli (it is a Latin-first
# subset). A cover set in it prints blanks where the capitals should be. Noto Sans Georgian has 46/48
# Mtavruli, so Georgian display text must use it; FiraGO stays for Latin only.
LAT_BOLD = next((f for f in ("/root/sitech/assets/firago-bold.ttf",
                             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
                 if os.path.exists(f)), "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# One accent per category, so the grid reads as sections instead of one grey column. Kept in the
# same saturation family as the news covers so a reel and a card of the same story look related.
ACCENT = {
    "politics": (239, 68, 68),      # red
    "economy": (34, 197, 94),       # green
    "society": (59, 130, 246),      # blue
    "world": (139, 92, 246),        # violet
    "sports": (249, 115, 22),       # orange
    "culture": (236, 72, 153),      # pink
    "tech": (6, 182, 212),          # cyan
    "crime": (245, 158, 11),        # amber
    "defense": (100, 116, 139),     # slate
    "region": (20, 184, 166),       # teal
    "science": (99, 102, 241),      # indigo
    "showbusiness": (217, 70, 239), # fuchsia
    "religion": (161, 98, 7),       # bronze
    "medicine": (16, 185, 129),     # emerald
    "education": (234, 179, 8),     # gold
    "auto": (71, 85, 105),          # steel
    "realestate": (180, 83, 9),     # rust
    "tourism": (14, 165, 233),      # sky
    "ecology": (132, 204, 22),      # lime
    "incidents": (244, 63, 94),     # rose
    "general": (239, 68, 68),
}
CAT_KA = {
    "politics": "პოლიტიკა", "economy": "ეკონომიკა", "society": "საზოგადოება", "world": "მსოფლიო",
    "sports": "სპორტი", "culture": "კულტურა", "tech": "ტექნოლოგია", "general": "სიახლე",
    "crime": "კრიმინალი", "defense": "თავდაცვა", "region": "რეგიონი",
    "science": "მეცნიერება", "showbusiness": "შოუბიზნესი", "religion": "რელიგია",
    "medicine": "მედიცინა", "education": "განათლება", "auto": "ავტო", "realestate": "უძრავი ქონება",
    "tourism": "ტურიზმი", "ecology": "ეკოლოგია", "incidents": "შემთხვევები",
}


def _clean(s: str) -> str:
    return re.sub(r"[\u2013\u2014]", "-", " ".join((s or "").split()))


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, face, max_w: int, max_lines: int) -> list[str]:
    """Greedy wrap by measured width, then shrink to fit the line budget."""
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=face) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines and draw.textlength(lines[-1] + "…", font=face) > max_w:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "…"
    return lines


def build(slug: str, title: str, category: str, date_str: str, out: str) -> str:
    accent = ACCENT.get(category, ACCENT["general"])
    cat_ka = CAT_KA.get(category, "სიახლე")

    # Reels UI covers the top ~200 px and the bottom ~340 px (caption, buttons), so every element
    # lives inside that safe band or it is invisible on a phone.
    SAFE_L, SAFE_R, SAFE_T, SAFE_B = 84, W - 84, 260, H - 400
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # A soft accent glow behind the text block: enough colour to differ at thumbnail size, not so
    # much that the headline loses contrast.
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, r = int(W * 0.78), int(H * 0.16), int(W * 0.9)
    for step in range(28, 0, -1):
        rr = int(r * step / 28)
        alpha = int(10 + 3 * (28 - step))
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=accent + (alpha,))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(70))).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Category chip: accent fill, dark label, sized to the measured text so it is never empty.
    chip_font = _font(BOLD, 34)
    label = cat_ka.upper()
    tw = draw.textlength(label, font=chip_font)
    pad_x, pad_y = 28, 16
    chip_h = 34 + pad_y * 2
    draw.rounded_rectangle([SAFE_L, SAFE_T, SAFE_L + tw + pad_x * 2, SAFE_T + chip_h],
                           radius=8, fill=accent)
    draw.text((SAFE_L + pad_x, SAFE_T + chip_h / 2), label, font=chip_font,
              fill=(12, 14, 18), anchor="lm")

    # Headline: Mtavruli, wrapped to the safe column, shrunk until it fits six lines.
    text = _clean(title).upper()
    size, lines = 96, []
    while size >= 52:
        face = _font(BOLD, size)
        lines = _wrap(draw, text, face, SAFE_R - SAFE_L, max_lines=6)
        widest = max((draw.textlength(l, font=face) for l in lines), default=0)
        if len(lines) <= 6 and widest <= SAFE_R - SAFE_L:
            break
        size -= 4
    face = _font(BOLD, size)
    y = SAFE_T + chip_h + 90
    for line in lines:
        draw.text((SAFE_L, y), line, font=face, fill=INK, anchor="la")
        y += int(size * 1.18)

    # Rule + kicker under the headline
    y += 24
    draw.rectangle([SAFE_L, y, SAFE_L + 110, y + 7], fill=accent)
    draw.text((SAFE_L, y + 30), "სიახლე", font=_font(REG, 32), fill=MUTED, anchor="la")

    # Wordmark and date, Latin in the brand face, above the caption zone.
    draw.text((SAFE_L, SAFE_B - 92), "tbilisi.today", font=_font(LAT_BOLD, 44), fill=INK, anchor="la")
    draw.text((SAFE_L, SAFE_B - 34), _clean(date_str), font=_font(REG, 30), fill=MUTED, anchor="la")
    # An inset accent bar on the left edge, aligned to the text column: a framing device, not a border.
    draw.rounded_rectangle([26, SAFE_T, 34, SAFE_B], radius=4, fill=accent)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    img.save(out, "JPEG", quality=90, optimize=True)
    return out


def from_story(slug: str, story: dict, out: str) -> str:
    """Convenience: pull title, category and date out of a veasy story dict."""
    hook = next((s for s in story.get("scenes", []) if isinstance(s, dict) and s.get("type") == "hook"), {})
    title = " ".join(hook.get("lines") or []) or str(story.get("narration") or "")[:120]
    date = str(story.get("date") or "")[:10] or dt.date.today().isoformat()
    return build(slug, title, str(story.get("category") or "general"), date, out)
