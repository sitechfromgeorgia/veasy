"""Brand packs: everything that makes a video one client's and not another's, as data.

    brands/<name>/brand.json   colors, fonts, logo, wordmark, link + QR, footer, calls to action, categories and
                               their families, the look and the voice per family, extra voice presets, on-screen
                               words, the time zone, month and weekday names
    brands/<name>/*            the pack's own files (logo SVGs, fonts...), named in brand.json
    brands/_<base>/brand.json  a base other packs extend ("extends": "_ka"); bases are not packs themselves

A new client is a new folder: no engine code changes. A pack may extend a base: dicts merge key by key, anything
else (lists, strings) is replaced. File paths are relative to the pack that names them, or to the Veasy root when
they start with assets/. `python -m tt_shorts.engine options` lists the packs; a story picks its pack with "brand"
(default tbilisi-today), a queue job with --brand.

A pack is checked on load: a missing key, an unknown family or look, a voice preset that doesn't exist or a file
that isn't there fails loudly, before anything is rendered.

media: the media layer's data (assets.py): "providers", the order a scene's picture is searched in (openverse,
  commons, pexels, pixabay: an empty list means no stock pictures for this pack), and the screenshot allow-list:
  "official" (a base's government sites: matsne.gov.ge, gov.ge and its subdomains) and "own" (the pack's site).
  strings.illustrative is the label every illustrative picture carries (news rule N13), strings.media_credit the
  credit line's template ({author}, {licence}, {source}).

logo.kind:
say: the pack's spoken forms of its own names, merged under every story's "say" map (with_say).
design (optional): the pack's own design rules for films an agent composes (tt_shorts/frame_md.py writes them into
  frame.md; the composed film's probe checks the accent): "accent": {"allowed": [dot | active state | button],
  "never": ["text", ...]} and "rules": [sentences]. Lane A's components keep them by construction.
  "keyword": how the keyword captions (captions.py design "keyword") draw a page's keyword: underline (an accent
  underline: the accent as an active state), block (an ink block, the word in the canvas color) or tint (the word
  in the accent color: refused when design.accent.never has "text"). Default underline (keyword_style()).
package: the words of `engine package`'s texts (package.py): "more" (a link line with {url}), "link_in_bio" (for
  Instagram, where a caption's link can't be clicked) and "hashtags" (3+, after the category's own tag).

  tmark   tbilisi.today's mark (drawn in code) next to the wordmark text
  svg     "header": an SVG for the header (it carries the name, so no wordmark text is drawn next to it),
          "end": an SVG for the end card (default: the header one)
"""
import functools
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "brands"
DEFAULT = "tbilisi-today"
REQUIRED = ("name", "label", "lang", "utc_offset_hours", "colors", "fonts", "logo", "wordmark", "link", "footer",
            "ctas", "categories", "family_by_category", "default_family", "look_by_family", "voice_by_family",
            "strings", "months", "weekdays", "package", "media")
COLORS = ("canvas", "panel", "ink", "muted", "accent", "line", "lineStrong", "grid", "ticker", "waiting", "markBg")
COLOR_DEFAULTS = {"onAccent": "#FFFFFF"}  # text on the accent (the end card's button)
STRINGS = ("outlets", "source_one", "source_many", "covered_by", "today", "preview_edge", "preview_silent",
           "card_meta", "category_default", "at_least", "illustrative", "media_credit")
# media (assets.py): providers, the order a picture is searched in (assets.PROVIDERS, never screenshot or ai);
# official and own, the domains a screenshot may come from (a base's official sites, the pack's own site)
MEDIA_KEYS = ("providers", "official", "own")
DOMAIN = re.compile(r"^(?=.{3,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")
FONT_WEIGHTS = ("400", "500", "600", "700")
LOOKS = ("editorial", "kinetic", "cards")
ACCENT_USES = ("dot", "active state", "button")  # design.accent.allowed: where a pack may put its accent
KEYWORD_STYLES = ("underline", "block", "tint")  # design.keyword: the keyword captions' highlight (captions.py)
KEYWORD_DEFAULT = "underline"
HASHTAG = re.compile(r"^#[^\s#!.,:;?]+$")
# The music moods tools/compose_music.py writes (assets/music/<family>-N.m4a): a family is one of these.
FAMILIES = ("politics", "economy", "world", "crime", "sports", "culture", "tech", "society")


class BrandError(ValueError):
    pass


def names():
    """The packs a story can use (bases, the folders starting with _, are left out)."""
    if not DIR.is_dir():
        return []
    return sorted(p.name for p in DIR.iterdir() if (p / "brand.json").exists() and not p.name.startswith("_"))


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _raw(name, seen=()):
    """(merged json, [pack dirs, nearest first]) of a pack and the bases it extends."""
    path = DIR / name / "brand.json"
    if not path.exists():
        raise BrandError(f"unknown brand {name!r}; known: {', '.join(names())}")
    if name in seen:
        raise BrandError(f"brand {name}: extends itself ({' -> '.join((*seen, name))})")
    own = json.loads(path.read_text(encoding="utf-8"))
    dirs = [path.parent]
    if own.get("extends"):
        base, base_dirs = _raw(own["extends"], (*seen, name))
        return _merge(base, own), dirs + base_dirs
    return own, dirs


def _file(dirs, rel, name):
    """A file named in brand.json: shared assets/ from the Veasy root, else from the pack or one of its bases."""
    candidates = [ROOT / rel] if str(rel).startswith("assets/") else [d / rel for d in dirs]
    for p in candidates:
        if p.is_file():
            return p
    raise BrandError(f"brand {name}: missing file {rel}")


def validate(b, dirs):
    from tt_shorts import voices  # late: voices reads brand packs too
    name = b.get("name", "?")
    missing = [k for k in REQUIRED if k not in b]
    missing += [f"colors.{c}" for c in COLORS if c not in b.get("colors", {})]
    missing += [f"strings.{s}" for s in STRINGS if s not in b.get("strings", {})]
    missing += [f"fonts.{w}" for w in FONT_WEIGHTS if w not in b.get("fonts", {})]
    if missing:
        raise BrandError(f"brand {name}: missing {', '.join(missing)}")
    if len(b["months"]) != 12 or len(b["weekdays"]) != 7:
        raise BrandError(f"brand {name}: 12 months and 7 weekdays (Monday first) are needed")
    if not b["ctas"]:
        raise BrandError(f"brand {name}: at least one call to action (ctas)")
    families = set(b["family_by_category"].values()) | {b["default_family"]}
    bad = sorted(families - set(FAMILIES))
    if bad:
        raise BrandError(f"brand {name}: unknown families {bad}; the music has {', '.join(FAMILIES)}")
    for fam in families:
        if fam not in b["look_by_family"]:
            raise BrandError(f"brand {name}: look_by_family has no look for {fam!r}")
        if fam not in b["voice_by_family"]:
            raise BrandError(f"brand {name}: voice_by_family has no voice for {fam!r}")
    bad = sorted(set(b["look_by_family"].values()) - set(LOOKS))
    if bad:
        raise BrandError(f"brand {name}: unknown looks {bad}; the engine has {', '.join(LOOKS)}")
    for key, p in (b.get("voices") or {}).items():
        if not {"label", "voice", "style"} <= set(p):
            raise BrandError(f"brand {name}: voice preset {key!r} needs label, voice and style")
    known = set(voices.PRESETS) | set(b.get("voices") or {})
    bad = sorted(set(b["voice_by_family"].values()) - known)
    if bad:
        raise BrandError(f"brand {name}: voice_by_family names unknown presets {bad}")
    if "{id}" not in b["link"].get("qr", ""):  # display may leave it out (long slugs don't fit the footer)
        raise BrandError(f"brand {name}: link.qr must contain {{id}}")
    if not b["link"].get("display"):
        raise BrandError(f"brand {name}: link.display is the link as the video shows it")
    if not isinstance(b["footer"], dict) or "text" not in b["footer"]:
        raise BrandError(f"brand {name}: footer is {{\"text\": ..., \"strong\": ...}}")
    pk = b["package"]
    if not isinstance(pk, dict) or "{url}" not in str(pk.get("more", "")) or not str(pk.get("link_in_bio") or "").strip():
        raise BrandError(f"brand {name}: package needs \"more\" (a link line with {{url}}) and \"link_in_bio\"")
    tags = pk.get("hashtags")
    if not isinstance(tags, list) or len(set(tags)) < 3 or not all(isinstance(t, str) and HASHTAG.match(t) for t in tags):
        raise BrandError(f"brand {name}: package.hashtags is a list of 3+ different hashtags like \"#ამბები\" (no spaces)")
    design = b.get("design")
    if design is not None:
        if not isinstance(design, dict):
            raise BrandError(f"brand {name}: design is {{\"accent\": {{\"allowed\": [...], \"never\": [...]}}, \"rules\": [...]}}")
        acc = design.get("accent")
        if acc is not None:
            ok = isinstance(acc, dict) and all(isinstance(acc.get(k, []), list) for k in ("allowed", "never"))
            if not ok or not set(acc.get("allowed", [])) <= set(ACCENT_USES):
                raise BrandError(f"brand {name}: design.accent.allowed is a list of {', '.join(ACCENT_USES)}; "
                                 "design.accent.never a list of words")
        rules = design.get("rules", [])
        if not isinstance(rules, list) or not all(isinstance(r, str) and r.strip() for r in rules):
            raise BrandError(f"brand {name}: design.rules is a list of sentences")
        kw = design.get("keyword", KEYWORD_DEFAULT)
        if kw not in KEYWORD_STYLES:
            raise BrandError(f"brand {name}: design.keyword is one of {', '.join(KEYWORD_STYLES)}")
        if kw == "tint" and "text" in ((design.get("accent") or {}).get("never") or []):
            raise BrandError(f"brand {name}: design.keyword tint colors a word with the accent, and this pack's "
                             "accent is never text (design.accent.never): use underline or block")
    media_problems(b)
    kind = b["logo"].get("kind")
    if kind not in ("tmark", "svg"):
        raise BrandError(f"brand {name}: logo.kind is tmark or svg")
    files = {"fonts": {w: str(_file(dirs, f, name)) for w, f in b["fonts"].items()}}
    if kind == "svg":
        header = _file(dirs, b["logo"]["header"], name)
        files["logo"] = {"header": str(header), "end": str(_file(dirs, b["logo"]["end"], name))
                         if b["logo"].get("end") else str(header)}
    return files


def media_problems(b):
    """Raise BrandError when the pack's media key or its words for pictures are wrong (assets.py, news rule N13)."""
    from tt_shorts import assets  # late: assets reads packs
    name = b.get("name", "?")
    m = b.get("media")
    if not isinstance(m, dict) or set(m) - set(MEDIA_KEYS):
        raise BrandError(f"brand {name}: media is {{{', '.join(MEDIA_KEYS)}}}")
    searchable = [p for p in assets.PROVIDERS if p not in ("screenshot", "ai")]
    provs = m.get("providers", [])
    if not isinstance(provs, list) or not set(provs) <= set(searchable) or len(set(provs)) != len(provs):
        raise BrandError(f"brand {name}: media.providers is an order of some of {', '.join(searchable)}")
    for k in ("official", "own"):
        doms = m.get(k, [])
        if not isinstance(doms, list) or not all(isinstance(d, str) and DOMAIN.match(d) for d in doms):
            raise BrandError(f"brand {name}: media.{k} is a list of domains (matsne.gov.ge), no scheme or path")
    if not str(b["strings"]["illustrative"]).strip():
        raise BrandError(f"brand {name}: strings.illustrative is the label an illustrative picture carries (N13)")
    if "{author}" not in str(b["strings"]["media_credit"]) or "{licence}" not in str(b["strings"]["media_credit"]):
        raise BrandError(f"brand {name}: strings.media_credit names {{author}} and {{licence}} (the credit a licence asks)")


@functools.lru_cache(maxsize=16)
def load(name=None):
    """The resolved pack: its JSON (bases merged in) plus _dir, _fonts {weight: path} and _logo {header, end}."""
    name = name or DEFAULT
    if name.startswith("_"):
        raise BrandError(f"{name} is a base for other packs, not a brand")
    b, dirs = _raw(name)
    if b.get("name") != name:
        raise BrandError(f"brand folder {name} says its name is {b.get('name')}")
    b["colors"] = {**COLOR_DEFAULTS, **b.get("colors", {})}
    files = validate(b, dirs)
    b.pop("extends", None)
    b["_dir"] = str(dirs[0])
    b["_fonts"] = files["fonts"]
    b["_logo"] = files.get("logo")
    return b


def of(story):
    return load(story.get("brand") or DEFAULT)


def with_say(story):
    """The story with the pack's spoken forms under its own "say" map (the story's entry wins): a pack's own names
    (SiTech -> საი-თეჩი) are read right in every script without the writer repeating them."""
    pack = of(story).get("say") or {}
    if not pack:
        return story
    return {**story, "say": {**pack, **(story.get("say") or {})}}


def keyword_style(b):
    """How the pack's keyword captions draw a keyword (design.keyword): underline, block or tint."""
    return (b.get("design") or {}).get("keyword", KEYWORD_DEFAULT)


def summary(b):
    """What `engine options` shows of a pack."""
    return {"label": b["label"], "about": b.get("about", ""), "lang": b["lang"], "logo": b["logo"]["kind"],
            "link": b["link"]["display"], "categories": len(b["categories"]), "voices": sorted(b.get("voices") or {})}


def for_remotion(b):
    """The part of the pack the composition draws with (no paths: props.py copies the files into public/)."""
    return {"name": b["name"], "label": b["label"], "colors": b["colors"], "wordmark": b["wordmark"],
            "logo": b["logo"]["kind"], "footer": b["footer"], "strings": b["strings"]}
