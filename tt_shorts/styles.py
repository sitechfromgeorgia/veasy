"""Film styles for Veasy: named styles as data that a person or an agent names in one word.

Learning from lemomo-ai/lemo-opuscar (MIT), styles re-engineered for vertical (1080x1920) Georgian Mkhedruli video,
Veasy's brand law, safe zones, and news integrity rules.

A style is stored in:
    styles/<slug>/style.json   metadata, schema constraints, engine, palette & font mode, program & family filters,
                               and narrowed variety picks (directors, looks, motifs, transitions, music, sfx)
    styles/<slug>/STYLE.md     the invariants, directing rules, typography and motion specs written for vertical
                               Georgian video and Veasy's rules (used by composed lane agents as prompt)

Brand law:
    - palette: pack styles draw in the brand pack's palette and fonts; allowed for all brands and programs.
    - palette: own styles bring their own palette and fonts; allowed ONLY when the pack lists the style slug in its
      "styles" key (brand.json) AND the program allows it. News never uses a palette: own style.
"""
import builtins
import functools
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "styles"

VALID_SLUG = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$")
ENGINES = ("remotion", "hyperframes", "both")
PALETTE_MODES = ("pack", "own")
FONT_MODES = ("pack", "own")
REQUIRED_KEYS = (
    "slug", "name_en", "name_ka", "category", "engine", "palette", "fonts",
    "programs", "never_families", "picks", "uses"
)
PICKS_KEYS = ("directors", "looks", "motifs", "transitions", "music", "sfx")


class StyleError(ValueError):
    """Raised when a style definition, schema, or style selection violates Veasy style rules."""
    pass


def names():
    """All style slugs present in styles/ directory, sorted."""
    if not DIR.is_dir():
        return []
    return sorted(
        p.name for p in DIR.iterdir()
        if p.is_dir() and (p / "style.json").is_file() and not p.name.startswith((".", "_"))
    )


def validate_style_data(data, dir_path=None):
    """Validate a parsed style dict and its corresponding STYLE.md file if dir_path is provided."""
    if not isinstance(data, dict):
        raise StyleError("style definition must be a JSON object")

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise StyleError(f"style is missing required keys: {', '.join(missing)}")

    slug = data["slug"]
    if not isinstance(slug, str) or not VALID_SLUG.match(slug):
        raise StyleError(f"invalid style slug {slug!r}; must match [a-z0-9][a-z0-9-]*")

    if dir_path is not None and dir_path.name != slug:
        raise StyleError(f"style slug {slug!r} does not match directory name {dir_path.name!r}")

    for str_key in ("name_en", "name_ka", "category", "uses"):
        val = data.get(str_key)
        if not isinstance(val, str) or not val.strip():
            raise StyleError(f"style {slug}: {str_key} must be a non-empty string")

    engine = data.get("engine")
    if engine not in ENGINES:
        raise StyleError(f"style {slug}: engine {engine!r} must be one of {', '.join(ENGINES)}")

    palette = data.get("palette")
    if palette not in PALETTE_MODES:
        raise StyleError(f"style {slug}: palette {palette!r} must be one of {', '.join(PALETTE_MODES)}")

    fonts = data.get("fonts")
    if fonts not in FONT_MODES:
        raise StyleError(f"style {slug}: fonts {fonts!r} must be one of {', '.join(FONT_MODES)}")

    programs = data.get("programs")
    if not isinstance(programs, list) or not programs or not builtins.all(isinstance(p, str) and p.strip() for p in programs):
        raise StyleError(f"style {slug}: programs must be a non-empty list of program strings")

    never_families = data.get("never_families")
    if not isinstance(never_families, list) or not builtins.all(isinstance(f, str) for f in never_families):
        raise StyleError(f"style {slug}: never_families must be a list of family strings")

    from tt_shorts import brand
    bad_fam = sorted(set(never_families) - set(brand.FAMILIES))
    if bad_fam:
        raise StyleError(f"style {slug}: never_families contains unknown families: {bad_fam}")

    picks = data.get("picks")
    if not isinstance(picks, dict):
        raise StyleError(f"style {slug}: picks must be a dict")
    bad_picks_keys = sorted(set(picks) - set(PICKS_KEYS))
    if bad_picks_keys:
        raise StyleError(f"style {slug}: picks has unknown keys: {bad_picks_keys}")
    for pk, pval in picks.items():
        if not isinstance(pval, list) or not builtins.all(isinstance(item, str) for item in pval):
            raise StyleError(f"style {slug}: picks.{pk} must be a list of strings")

    if dir_path is not None:
        md_file = dir_path / "STYLE.md"
        if not md_file.is_file():
            raise StyleError(f"style {slug}: missing STYLE.md in {dir_path}")
        text = md_file.read_text(encoding="utf-8").strip()
        if not text:
            raise StyleError(f"style {slug}: STYLE.md must not be empty")

    return True


@functools.lru_cache(maxsize=64)
def get(slug):
    """Load and return style dict for slug, including its STYLE.md content under 'style_md'."""
    if not isinstance(slug, str) or not VALID_SLUG.match(slug):
        raise StyleError(f"unknown or invalid style slug {slug!r}")
    style_dir = DIR / slug
    json_path = style_dir / "style.json"
    if not json_path.is_file():
        raise StyleError(f"unknown style {slug!r}; known styles: {', '.join(names())}")

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise StyleError(f"style {slug}: broken JSON in {json_path}: {err}") from err

    validate_style_data(data, style_dir)
    md_path = style_dir / "STYLE.md"
    style_md = md_path.read_text(encoding="utf-8")

    out = dict(data)
    out["_dir"] = str(style_dir)
    out["style_md"] = style_md
    return out


def load_all():
    """Return all valid styles as a list of dicts, sorted by slug."""
    return [get(s) for s in names()]


all = load_all


def brand_allows(brand_pack, style_or_slug, program="news"):
    """Check whether a brand pack and program allow a given style.

    Returns (allowed: bool, reason: str).
    Rules:
    1. palette: pack styles are always allowed for any brand and any program.
    2. palette: own styles are forbidden for news programs ('news').
    3. palette: own styles require the brand pack to list the style slug in its 'styles' list.
    """
    style = get(style_or_slug) if isinstance(style_or_slug, str) else style_or_slug
    slug = style["slug"]
    palette = style.get("palette", "pack")

    if palette == "pack":
        return True, ""

    # palette == "own":
    if program == "news":
        return False, f"style {slug!r} has palette: own, which news programs never permit"

    bname = brand_pack.get("name", "unknown") if brand_pack else "unknown"
    allowed_list = brand_pack.get("styles") or [] if brand_pack else []
    if slug not in allowed_list:
        return False, f"brand {bname!r} does not allow palette: own style {slug!r} in brand.json 'styles'"

    return True, ""


def for_story(story, brand_pack=None, program=None, engine=None):
    """Return all styles eligible for this story, ordered by slug.

    Filters by:
    - program (from argument, story.get("program"), or 'news')
    - family (story.get("family"), cannot be in style.never_families)
    - engine (if provided: style engine must be 'both' or match)
    - brand allow rules (via brand_allows)
    """
    from tt_shorts import brand
    b = brand_pack or brand.of(story)
    prog = program or story.get("program") or "news"
    fam = story.get("family")
    eng = engine or story.get("engine")

    eligible = []
    for s in all():
        if prog not in s["programs"]:
            continue
        if eng and eng not in (s.get("engine"), "both"):
            continue
        if fam and fam in s.get("never_families", []):
            continue
        ok, _ = brand_allows(b, s, prog)
        if not ok:
            continue
        eligible.append(s)

    return eligible


def resolve_for_story(story, style_slug=None, brand_pack=None, program=None):
    """Resolve and validate the style for a story.

    If style_slug (or story['style']) is provided:
        Verifies that it exists, suits the program, does not reject the family, and is permitted by brand law.
        Raises StyleError on any violation.
    If no style is requested:
        Returns None (indicating variety or default rotation should choose).
    """
    from tt_shorts import brand
    requested = style_slug or story.get("style")
    if not requested:
        return None

    s = get(requested)
    b = brand_pack or brand.of(story)
    prog = program or story.get("program") or "news"
    fam = story.get("family")

    if prog not in s["programs"]:
        raise StyleError(
            f"style {s['slug']!r} does not suit program {prog!r}; suits: {', '.join(s['programs'])}"
        )
    if fam and fam in s.get("never_families", []):
        raise StyleError(
            f"style {s['slug']!r} cannot be used for family {fam!r} (in never_families)"
        )
    ok, reason = brand_allows(b, s, prog)
    if not ok:
        raise StyleError(f"style {s['slug']!r} not permitted for this story: {reason}")

    return s


def summary(style):
    """Dictionary representation of a style suitable for 'engine options'."""
    return {
        "slug": style["slug"],
        "name_en": style["name_en"],
        "name_ka": style["name_ka"],
        "category": style["category"],
        "engine": style["engine"],
        "palette": style["palette"],
        "fonts": style["fonts"],
        "programs": list(style["programs"]),
        "never_families": list(style.get("never_families", [])),
        "picks": dict(style.get("picks", {})),
        "uses": style["uses"],
        "still": f"out/gallery/stills/style-{style['slug']}.jpg",  # `engine gallery --real` renders it (gallery.py)
    }
