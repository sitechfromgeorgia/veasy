"""The caption one structure for every tbilisi.today social post.

Edo, 2026-11-14, after the first Reel: „აღწერა უნდა გავაფორმოთ ... რამე სტრუქტურა თუ გვექნება".
So the shape lives in one place and both lanes (news cards, Reels) build from it:

    📰 სიახლე · პოლიტიკა      badge line, one emoji
    <HEADLINE>                 Georgian Mtavruli: the script's own capitals, not a fake font
    <lede>                     one sentence
    🔗 სრული სტატია: <url>     the link in the body, as the owner asked
    #tags                      up to ten

Georgian uppercase is U+1C90.. (Mtavruli). Python's str.upper() maps Georgian there, which is why
the result reads as a designed headline rather than a hack: it is a real script form, so it stays
selectable, searchable and readable by a screen reader, unlike the pseudo-fonts that rewrite Latin
into symbols.
"""
from __future__ import annotations

import re

CAT_KA = {
    "politics": "პოლიტიკა", "economy": "ეკონომიკა", "society": "საზოგადოება", "world": "მსოფლიო",
    "sports": "სპორტი", "culture": "კულტურა", "tech": "ტექნოლოგია", "general": "ზოგადი",
    "crime": "კრიმინალი", "defense": "თავდაცვა", "region": "რეგიონი",
    "science": "მეცნიერება", "showbusiness": "შოუბიზნესი", "religion": "რელიგია",
    "medicine": "მედიცინა", "education": "განათლება", "auto": "ავტო", "realestate": "უძრავი ქონება",
    "tourism": "ტურიზმი", "ecology": "ეკოლოგია", "incidents": "შემთხვევები",
}

HASHTAG_LIMIT = 10
BASE_TAGS = ["#თბილისი", "#საქართველო", "#სიახლეები", "#tbilisitoday", "#georgia"]
# A headline longer than this reads as a wall in capitals: the eye loses the words.
UPPER_MAX = 96

_BADGE_EMOJI = {"photo": "📰", "video": "🎬"}


def clean(text: str) -> str:
    """Collapse whitespace and kill em/en dashes: Edo's rule, and sources ship them constantly."""
    return re.sub(r"[\u2013\u2014]", "-", " ".join((text or "").split()))


def mtavruli(text: str) -> str:
    """Georgian capitals (Mtavruli, U+1C90..). Latin and digits pass through unchanged."""
    return (text or "").upper()


def headline(title: str) -> str:
    """The headline as it should read on Facebook: capitals when short enough to stay legible."""
    t = clean(title)
    return mtavruli(t) if len(t) <= UPPER_MAX else t


def hashtags(category_ka: str | None = None, extra: list[str] | None = None) -> list[str]:
    """Up to ten, brand first, then the category. No wall of tags: ten is the ceiling, not a target."""
    tags: list[str] = list(BASE_TAGS)
    if category_ka:
        tag = "#" + re.sub(r"\s+", "", category_ka)
        if tag not in tags:
            tags.append(tag)
    for t in extra or []:
        t = t if t.startswith("#") else "#" + t
        if t not in tags:
            tags.append(t)
    return tags[:HASHTAG_LIMIT]


def _summary_line(summary: str, limit: int) -> str:
    s = clean(summary)
    if not s:
        return ""
    if len(s) <= limit:
        return s
    cut = s[:limit]
    # Prefer the last full sentence that fits; fall back to a word boundary, never a mid-word cut.
    dot = cut.rfind(". ")
    if dot >= 40:
        return cut[:dot + 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > 40 else cut).rstrip(",;:") + "…"


def first_sentences(text: str, limit: int = 300) -> str:
    """The opening of a story as whole sentences, capped at `limit` characters.

    Feed excerpts arrive with an ellipsis already baked in (the Telegram helper caps at 250), and
    re-capping that produced „...თანხა ამოღ…” on a live post. Build the lede from the raw text here
    instead, and never end in the middle of a word.
    """
    s = clean(text)
    if not s:
        return ""
    if len(s) <= limit:
        return s
    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+", s):
        candidate = (out + " " + sentence).strip()
        if len(candidate) > limit:
            break
        out = candidate
        if out.count(".") >= 2:
            break
    if out:
        return out
    space = s[:limit].rfind(" ")
    return (s[:space] if space > 40 else s[:limit]).rstrip(",;:") + "…"


def caption(title: str, summary: str = "", link: str = "", *, kind: str = "photo",
            category_ka: str | None = None, summary_limit: int = 320,
            extra_tags: list[str] | None = None) -> str:
    """Build the full caption. Empty pieces disappear instead of leaving blank lines."""
    emoji = _BADGE_EMOJI.get(kind, "📰")
    badge = f"{emoji} {'ვიდეო' if kind == 'video' else 'სიახლე'}"
    if category_ka:
        badge += f" · {category_ka}"

    blocks = [badge, headline(title)]
    lede = _summary_line(summary, summary_limit)
    if lede:
        blocks.append(lede)
    if link:
        blocks.append(f"🔗 სრული სტატია: {link}")
    tags = hashtags(category_ka, extra_tags)
    if tags:
        blocks.append(" ".join(tags))
    return "\n\n".join(blocks)
