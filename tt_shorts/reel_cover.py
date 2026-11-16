"""Vertical 1080x1920 covers for Facebook Reels, driven by the brand pack."""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from tt_shorts import brand as packs

W, H = 1080, 1920
ROOT = pathlib.Path(__file__).resolve().parent.parent
BUNDLED_KA = ROOT / "assets" / "fonts" / "NotoSansGeorgian.ttf"
BUNDLED_LAT = ROOT / "assets" / "fonts" / "firago-bold.ed7553cea8.woff2"

SYSTEM_KA_REG = (
    "/usr/local/share/fonts/truetype/noto/NotoSansGeorgian-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansGeorgian-Regular.ttf",
    str(BUNDLED_KA),
)
SYSTEM_KA_BOLD = (
    "/usr/local/share/fonts/truetype/noto/NotoSansGeorgian-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansGeorgian-Bold.ttf",
    str(BUNDLED_KA),
)
SYSTEM_LAT_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    str(BUNDLED_LAT),
    str(BUNDLED_KA),
)

# Category accents when a category has a distinct section colour; unmapped categories fall back
# to the pack's own primary accent colour.
ACCENT = {
    "politics": (239, 68, 68),
    "economy": (34, 197, 94),
    "society": (59, 130, 246),
    "world": (139, 92, 246),
    "sports": (249, 115, 22),
    "culture": (236, 72, 153),
    "tech": (6, 182, 212),
    "crime": (245, 158, 11),
    "defense": (100, 116, 139),
    "region": (20, 184, 166),
    "science": (99, 102, 241),
    "showbusiness": (217, 70, 239),
    "religion": (161, 98, 7),
    "medicine": (16, 185, 129),
    "education": (234, 179, 8),
    "auto": (71, 85, 105),
    "realestate": (180, 83, 9),
    "tourism": (14, 165, 233),
    "ecology": (132, 204, 22),
    "incidents": (244, 63, 94),
}


def _clean(s: str) -> str:
    return re.sub(r"[\u2013\u2014]", "-", " ".join((s or "").split()))


def _font(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, face, max_w: int, max_lines: int) -> list[str]:
    """Greedy wrap by measured width, then truncate cleanly to the line budget."""
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


def _rgb(color: str) -> tuple[int, int, int]:
    return packs.rgba(color)[:3]


def build(slug: str, title: str, category: str, date_str: str, out: str, *, brand=None) -> str:
    """Render a 1080x1920 JPEG Reel cover styled from the brand pack's social & theme config."""
    b, cover_cfg = packs.require_social(brand, "cover")
    colors = b["colors"]
    bg = _rgb(colors["canvas"])
    ink = _rgb(colors["ink"])
    muted = _rgb(colors["muted"])
    pack_accent = _rgb(colors["accent"])
    accent = ACCENT.get(category, pack_accent)

    kicker = cover_cfg["kicker"]
    wordmark = cover_cfg["wordmark"]
    cat_ka = (b.get("categories") or {}).get(category) or kicker

    pack_bold = (b.get("_fonts") or {}).get("700", "")
    lat_faces = (pack_bold, *SYSTEM_LAT_BOLD)

    SAFE_L, SAFE_R, SAFE_T, SAFE_B = 84, W - 84, 260, H - 400
    img = Image.new("RGB", (W, H), bg)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, r = int(W * 0.78), int(H * 0.16), int(W * 0.9)
    for step in range(28, 0, -1):
        rr = int(r * step / 28)
        alpha = int(10 + 3 * (28 - step))
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=accent + (alpha,))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(70))).convert("RGB")
    draw = ImageDraw.Draw(img)

    chip_font = _font(SYSTEM_KA_BOLD, 34)
    label = cat_ka.upper()
    tw = draw.textlength(label, font=chip_font)
    pad_x, pad_y = 28, 16
    chip_h = 34 + pad_y * 2
    chip_ink = (12, 14, 18) if packs.luminance(accent + (1.0,)) > 0.18 else (247, 249, 251)
    draw.rounded_rectangle([SAFE_L, SAFE_T, SAFE_L + tw + pad_x * 2, SAFE_T + chip_h],
                           radius=8, fill=accent)
    draw.text((SAFE_L + pad_x, SAFE_T + chip_h / 2), label, font=chip_font,
              fill=chip_ink, anchor="lm")

    text = _clean(title).upper()
    size, lines = 96, []
    while size >= 52:
        face = _font(SYSTEM_KA_BOLD, size)
        lines = _wrap(draw, text, face, SAFE_R - SAFE_L, max_lines=6)
        widest = max((draw.textlength(l, font=face) for l in lines), default=0)
        if len(lines) <= 6 and widest <= SAFE_R - SAFE_L:
            break
        size -= 4
    face = _font(SYSTEM_KA_BOLD, size)
    y = SAFE_T + chip_h + 90
    for line in lines:
        draw.text((SAFE_L, y), line, font=face, fill=ink, anchor="la")
        y += int(size * 1.18)

    y += 24
    draw.rectangle([SAFE_L, y, SAFE_L + 110, y + 7], fill=accent)
    draw.text((SAFE_L, y + 30), kicker, font=_font(SYSTEM_KA_REG, 32), fill=muted, anchor="la")

    draw.text((SAFE_L, SAFE_B - 92), wordmark, font=_font(lat_faces, 44), fill=ink, anchor="la")
    draw.text((SAFE_L, SAFE_B - 34), _clean(date_str), font=_font(SYSTEM_KA_REG, 30), fill=muted, anchor="la")
    draw.rounded_rectangle([26, SAFE_T, 34, SAFE_B], radius=4, fill=accent)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    img.save(out, "JPEG", quality=90, optimize=True)
    return out


def from_story(slug: str, story: dict, out: str, *, brand=None) -> str:
    """Build a cover straight from a resolved or raw story dict."""
    target_brand = brand if brand is not None else story.get("brand")
    hook = next((s for s in story.get("scenes", []) if isinstance(s, dict) and s.get("type") == "hook"), {})
    title = " ".join(hook.get("lines") or []) or str(story.get("narration") or "")[:120]
    date = str(story.get("date") or "")[:10] or dt.date.today().isoformat()
    return build(slug, title, str(story.get("category") or "general"), date, out, brand=target_brand)
