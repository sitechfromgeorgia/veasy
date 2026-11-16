"""Pack-driven social caption builder for every brand.

Format:
    📰 <kicker> · <category>   badge line, one emoji
    <HEADLINE>                 Georgian Mtavruli capitals (<= UPPER_MAX chars)
    <lede>                     opening sentences
    🔗 სრული სტატია (<mark>): <url>
    #tags                      pack hashtags first, then category, up to HASHTAG_LIMIT
"""
from __future__ import annotations

import os
import re
import sys

from tt_shorts import brand as packs

HASHTAG_LIMIT = 10
# A headline longer than this reads as a wall in capitals: the eye loses the words.
UPPER_MAX = 96

_BADGE_EMOJI = {"photo": "📰", "video": "🎬"}
_KAEASY_CACHE: dict[str, tuple[object | None, object | None]] = {}


def clean(text: str) -> str:
    """Collapse whitespace and replace em/en dashes with hyphens."""
    return re.sub(r"[\u2013\u2014]", "-", " ".join((text or "").split()))


def mtavruli(text: str) -> str:
    """Georgian capitals (Mtavruli, U+1C90..). Latin and digits pass through untouched."""
    out = []
    for ch in text or "":
        code = ord(ch)
        out.append(chr(code + 0xBC0) if 0x10D0 <= code <= 0x10FF else ch)
    return "".join(out)


def headline(title: str) -> str:
    """Headlines in Mtavruli when short enough to stay legible."""
    t = clean(title)
    return mtavruli(t) if len(t) <= UPPER_MAX else t


def category_label(category: str | None, *, brand=None) -> str | None:
    """Resolve a category key against the brand pack's categories map."""
    if not category:
        return None
    b = brand if isinstance(brand, dict) else packs.load(brand)
    return (b.get("categories") or {}).get(category) or category


def hashtags(category_ka: str | None = None, extra: list[str] | None = None,
             *, brand=None, category: str | None = None) -> list[str]:
    """Up to ten hashtags from the pack's social config, followed by category and extras."""
    b, soc = packs.require_social(brand)
    tags: list[str] = list(soc.get("hashtags") or b["package"]["hashtags"])
    cat_label = category_ka or (b["categories"].get(category) if category else None)
    if cat_label:
        tag = "#" + re.sub(r"\s+", "", cat_label)
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
    dot = cut.rfind(". ")
    if dot >= 40:
        return cut[:dot + 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > 40 else cut).rstrip(",;:") + "…"


def first_sentences(text: str, limit: int = 300) -> str:
    """Opening of a story as whole sentences, capped cleanly at a word boundary."""
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


def _kaeasy_mods(plugins_dir: str | None):
    parent = os.environ.get("KAEASY_DIR")
    if parent:
        p = os.path.dirname(os.path.abspath(parent))
    else:
        p = plugins_dir or ""
    if p in _KAEASY_CACHE:
        return _KAEASY_CACHE[p]
    if p and p not in sys.path:
        sys.path.insert(0, p)
    try:
        from kaeasy import fix as ka_fix_mod
        from kaeasy import lint as ka_lint_mod
        mods = (ka_fix_mod, ka_lint_mod)
    except Exception:  # noqa: BLE001 - degrades to a no-op when optional plugin is absent
        mods = (None, None)
    _KAEASY_CACHE[p] = mods
    return mods


def guard(text: str, mode: str = "social", *, plugins_dir: str | None = None,
          brand=None) -> tuple[str, list]:
    """Run optional kaeasy mechanical fixer and linter over published copy."""
    if not text:
        return text, []
    if plugins_dir is None and brand is not None:
        _, soc = packs.require_social(brand)
        plugins_dir = soc.get("kaeasy_plugins")
    ka_fix_mod, ka_lint_mod = _kaeasy_mods(plugins_dir)
    masked, urls = text, []

    def _stash(match):
        urls.append(match.group(0))
        return f" ‹URL{len(urls) - 1}› "

    masked = re.sub(r"https?://\S+", _stash, text)
    if ka_fix_mod is not None:
        masked, _changes = ka_fix_mod.fix_text(masked)
    findings = ka_lint_mod.check_text(masked, mode=mode) if ka_lint_mod is not None else []
    for i, url in enumerate(urls):
        masked = masked.replace(f"‹URL{i}›", url)
    return masked, findings


def caption(title: str, summary: str = "", link: str = "", *, kind: str = "photo",
            category: str | None = None, category_ka: str | None = None, summary_limit: int = 320,
            extra_tags: list[str] | None = None, brand=None) -> str:
    """Build a full social caption using the brand pack's social config."""
    b, soc = packs.require_social(brand)
    cover = soc.get("cover") or {}
    kicker = cover.get("kicker") or "სიახლე"
    wordmark = cover.get("wordmark") or b["wordmark"]["text"]
    plugins_dir = soc.get("kaeasy_plugins")
    cat_label = category_ka or (b["categories"].get(category) if category else None)

    title, _f1 = guard(title, plugins_dir=plugins_dir)
    summary, _f2 = guard(summary, plugins_dir=plugins_dir)
    emoji = _BADGE_EMOJI.get(kind, "📰")
    badge = f"{emoji} {'ვიდეო' if kind == 'video' else kicker}"
    if cat_label:
        badge += f" · {cat_label}"

    blocks = [badge, headline(title)]
    lede = _summary_line(summary, summary_limit)
    if lede:
        blocks.append(lede)
    if link:
        blocks.append(f"🔗 სრული სტატია ({wordmark}): {link}")
    else:
        cta = (b.get("ctas") or [""])[0]
        blocks.append(f"📌 {wordmark} · {cta}" if cta else f"📌 {wordmark}")
    tags = hashtags(cat_label, extra_tags, brand=b)
    if tags:
        blocks.append(" ".join(tags))
    return "\n\n".join(blocks)
