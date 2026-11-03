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

themes: the pack's palettes (owner, 2026-11-03: "not only on a night background; a white one and others too").
  "themes": {<name>: {"colors": {...}, "logo"?: {...}, "allowed"?: bool, "about"?: "..."}} and "default_theme":
  <name>. Each theme has the full color set (COLORS; onAccent and markInk have defaults) and passes the contrast
  floors (CONTRAST: ink on canvas and on panel, muted, the accent dot, the button's text, the captions box). "logo"
  replaces the pack's logo files on that theme (an svg logo drawn for a dark ground needs a dark-on-light variant);
  the t-mark is drawn in code from the theme's markBg, markInk and accent. "allowed": false keeps a theme out of
  `theme: auto` and out of a render or the queue until the owner approves it (plan, probe, still and selftest may
  still preview it). A pack with "colors" and no "themes" has one theme, named by its canvas ("dark" or "light").
  load() returns the default theme's colors and logo as b["colors"] and b["_logo"]; themed(b, name) another one.
logo.kind:
say: the pack's spoken forms of its own names, merged under every story's "say" map (with_say).
design (optional): the pack's own design rules for films an agent composes (tt_shorts/frame_md.py writes them into
  frame.md; the composed film's probe checks the accent): "accent": {"allowed": [dot | active state | button],
  "never": ["text", ...]} and "rules": [sentences]. Lane A's components keep them by construction.
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
REQUIRED = ("name", "label", "lang", "utc_offset_hours", "fonts", "logo", "wordmark", "link", "footer",
            "ctas", "categories", "family_by_category", "default_family", "look_by_family", "voice_by_family",
            "strings", "months", "weekdays", "package", "media")
COLORS = ("canvas", "panel", "ink", "muted", "accent", "line", "lineStrong", "grid", "ticker", "waiting", "markBg")
# onAccent: text on the accent (the end card's button); markInk: the t of tbilisi.today's mark (drawn in code)
COLOR_DEFAULTS = {"onAccent": "#FFFFFF", "markInk": "#FFFFFF"}
SOLID = ("canvas", "panel", "ink", "muted", "accent", "markBg", "onAccent", "markInk")  # #RRGGBB (the rest may be rgba)
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
RGBA = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(0|1|0?\.\d+|1\.0+)\s*)?\)$")
THEME_KEYS = ("colors", "logo", "allowed", "about", "label")
# Contrast floors (WCAG ratios) a theme must pass, so no palette can make the video unreadable:
#   ink on canvas and on panel 7 (AAA body text), muted on both 4.5 (AA), the accent against both 2 (a dot, not
#   text; saturated colours read as a dot below WCAG's 3:1 for graphics, and SiTech's orange on paper is 2.2), the
#   button's text on the accent 3 (bold, 24 px and up), the captions: spoken words (ink) on the box laid over the
#   worst ground (an ink block) 4.5, waiting words (dimmed) on the box over the canvas 3.
CONTRAST = {"ink": 7.0, "muted": 4.5, "accent": 2.0, "onAccent": 3.0, "captions": 4.5, "waiting": 3.0, "mark": 3.0}
CAPTION_BOX = 0.8  # remotion/src/Captions.tsx: the page box is the canvas at this alpha
STRINGS = ("outlets", "source_one", "source_many", "covered_by", "today", "preview_edge", "preview_silent",
           "card_meta", "category_default", "at_least", "illustrative", "media_credit")
# media (assets.py): providers, the order a picture is searched in (assets.PROVIDERS, never screenshot or ai);
# official and own, the domains a screenshot may come from (a base's official sites, the pack's own site)
MEDIA_KEYS = ("providers", "official", "own")
DOMAIN = re.compile(r"^(?=.{3,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")
FONT_WEIGHTS = ("400", "500", "600", "700")
LOOKS = ("editorial", "kinetic", "cards")
ACCENT_USES = ("dot", "active state", "button")  # design.accent.allowed: where a pack may put its accent
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


# ---------------------------------------------------------------- colors and contrast


def rgba(color):
    """'#RRGGBB' or 'rgb(a)(r,g,b[,a])' -> (r, g, b, a) with r, g, b 0-255 and a 0-1; None when it is neither."""
    c = str(color).strip()
    if HEX.match(c):
        return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 1.0)
    m = RGBA.match(c)
    if not m:
        return None
    r, g, b = (int(m.group(i)) for i in (1, 2, 3))
    if max(r, g, b) > 255:
        return None
    return (r, g, b, float(m.group(4)) if m.group(4) is not None else 1.0)


def over(fg, bg):
    """fg (r, g, b, a) composited over bg (an opaque (r, g, b[, a])) -> (r, g, b, 1.0)."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def luminance(c):
    """WCAG relative luminance of an opaque (r, g, b[, a])."""
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    """WCAG contrast ratio (1-21) of a color drawn over an opaque ground; either may be a CSS string or a tuple."""
    fg = rgba(fg) if isinstance(fg, str) else fg
    bg = rgba(bg) if isinstance(bg, str) else bg
    fg = over(fg, bg) if fg[3] < 1 else fg
    la, lb = luminance(fg), luminance(bg)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def mode(colors):
    """'light' when the canvas is a light ground, else 'dark'."""
    return "light" if luminance(rgba(colors["canvas"])) > 0.4 else "dark"


def qr_colors(colors):
    """(dark, light) of the QR code: always dark modules on a light ground. On a dark theme the modules are the
    canvas on white (as before themes); on a light theme the modules are the ink on the canvas: just a QR on paper."""
    if mode(colors) == "light":
        return colors["ink"], colors["canvas"]
    return colors["canvas"], "#FFFFFF"


def contrast_problems(colors):
    """What makes a theme's palette unreadable: [messages] (CONTRAST's floors)."""
    c = {k: rgba(v) for k, v in colors.items()}
    canvas, panel = c["canvas"], c["panel"]
    box = over(canvas[:3] + (CAPTION_BOX,), canvas)  # the captions' box over the canvas
    box_on_ink = over(canvas[:3] + (CAPTION_BOX,), c["ink"])  # ... over an ink block (kinetic, a panel wipe)
    checks = [("ink", "ink", canvas, "the canvas"), ("ink", "ink", panel, "the panel"),
              ("muted", "muted", canvas, "the canvas"), ("muted", "muted", panel, "the panel"),
              ("accent", "accent", canvas, "the canvas (the dot)"), ("accent", "accent", panel, "the panel (the dot)"),
              ("onAccent", "onAccent", c["accent"], "the accent (the button)"),
              ("captions", "ink", box_on_ink, "the captions box over an ink block"),
              ("waiting", "waiting", box, "the captions box (a word not yet spoken)"),
              ("mark", "markInk", c["markBg"], "markBg (the t-mark)")]
    out = []
    for floor, key, ground, where in checks:
        ratio = contrast(c[key], ground)
        if ratio < CONTRAST[floor] - 1e-9:
            out.append(f"{key} on {where} is {ratio:.2f}:1, under {CONTRAST[floor]:g}:1")
    return out


def _themes_of(b):
    """The pack's raw themes: its "themes", or one theme made of its "colors" (named by its canvas)."""
    if b.get("themes"):
        return b["themes"]
    if "colors" in b:
        colors = {**COLOR_DEFAULTS, **b["colors"]}
        name = mode(colors) if HEX.match(str(colors.get("canvas", ""))) else "dark"
        return {name: {"colors": b["colors"]}}
    return {}


def _validate_themes(b, dirs, name):
    """-> ({theme: {"colors", "allowed", "about", "label", "logo"}}, default name), or a BrandError."""
    raw = _themes_of(b)
    if not isinstance(raw, dict) or not raw:
        raise BrandError(f"brand {name}: needs \"themes\" ({{name: {{\"colors\": ...}}}}) or \"colors\"")
    out = {}
    for t, spec in raw.items():
        where = f"brand {name}: theme {t!r}"
        if not re.match(r"^[a-z][a-z0-9-]*$", str(t)):
            raise BrandError(f"{where}: a theme's name is lowercase letters, digits and dashes")
        if not isinstance(spec, dict) or not isinstance(spec.get("colors"), dict):
            raise BrandError(f"{where}: is {{\"colors\": {{...}}, \"logo\"?, \"allowed\"?, \"about\"?}}")
        unknown = sorted(set(spec) - set(THEME_KEYS))
        if unknown:
            raise BrandError(f"{where}: unknown keys {unknown} (a theme has {', '.join(THEME_KEYS)})")
        colors = {**COLOR_DEFAULTS, **spec["colors"]}
        missing = [f"colors.{k}" for k in COLORS if k not in colors]
        if missing:
            raise BrandError(f"{where}: missing {', '.join(missing)}")
        bad = [k for k, v in colors.items() if not (HEX.match(str(v)) if k in SOLID else rgba(v))]
        if bad:
            raise BrandError(f"{where}: colors {', '.join(bad)} must be #RRGGBB (canvas, panel, ink, muted, accent, "
                             "markBg, onAccent, markInk) or rgba(r,g,b,a)")
        low = contrast_problems(colors)
        if low:
            raise BrandError(f"{where} is not readable: {'; '.join(low)}")
        allowed = spec.get("allowed", True)
        if not isinstance(allowed, bool):
            raise BrandError(f"{where}: allowed is true or false")
        logo = None
        if spec.get("logo") is not None:
            lg = spec["logo"]
            if b["logo"].get("kind") != "svg" or not isinstance(lg, dict) or not lg.get("header"):
                raise BrandError(f"{where}: logo is {{\"header\": <svg>, \"end\"?: <svg>}}, for a pack whose logo.kind "
                                 "is svg (the t-mark takes its colors from markBg, markInk and accent)")
            header = _file(dirs, lg["header"], name)
            logo = {"header": str(header), "end": str(_file(dirs, lg["end"], name)) if lg.get("end") else str(header)}
        out[t] = {"colors": colors, "allowed": allowed, "about": spec.get("about", ""), "label": spec.get("label", t),
                  "logo": logo}
    default = b.get("default_theme") or next(iter(out))
    if default not in out:
        raise BrandError(f"brand {name}: default_theme {default!r} is not one of its themes ({', '.join(out)})")
    if not out[default]["allowed"]:
        raise BrandError(f"brand {name}: the default theme {default!r} must be allowed")
    return out, default


def validate(b, dirs):
    from tt_shorts import voices  # late: voices reads brand packs too
    name = b.get("name", "?")
    missing = [k for k in REQUIRED if k not in b]
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
    media_problems(b)
    kind = b["logo"].get("kind")
    if kind not in ("tmark", "svg"):
        raise BrandError(f"brand {name}: logo.kind is tmark or svg")
    files = {"fonts": {w: str(_file(dirs, f, name)) for w, f in b["fonts"].items()}}
    if kind == "svg":
        header = _file(dirs, b["logo"]["header"], name)
        files["logo"] = {"header": str(header), "end": str(_file(dirs, b["logo"]["end"], name))
                         if b["logo"].get("end") else str(header)}
    files["themes"], files["default_theme"] = _validate_themes(b, dirs, name)
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
    """The resolved pack: its JSON (bases merged in) plus _dir, _fonts {weight: path} and _logo {header, end}, with
    the default theme applied: "theme" (its name), "colors" (its full palette), "_logo" (its files), and "themes"
    resolved ({name: {colors, allowed, about, label, logo}})."""
    name = name or DEFAULT
    if name.startswith("_"):
        raise BrandError(f"{name} is a base for other packs, not a brand")
    b, dirs = _raw(name)
    if b.get("name") != name:
        raise BrandError(f"brand folder {name} says its name is {b.get('name')}")
    files = validate(b, dirs)
    b.pop("extends", None)
    b["_dir"] = str(dirs[0])
    b["_fonts"] = files["fonts"]
    b["_pack_logo"] = files.get("logo")
    b["themes"] = files["themes"]
    b["default_theme"] = files["default_theme"]
    return _apply(b, b["default_theme"])


def _apply(b, theme):
    t = b["themes"][theme]
    return {**b, "theme": theme, "colors": dict(t["colors"]), "_logo": t["logo"] or b["_pack_logo"]}


def theme_names(b, allowed_only=False):
    """The pack's themes in their brand.json order (only the allowed ones: what `theme: auto` picks from)."""
    return [t for t, spec in b["themes"].items() if spec["allowed"] or not allowed_only]


def themed(b, theme=None):
    """The pack with another of its themes applied (None or "default": the default theme). An unknown name fails;
    a not-allowed one is applied all the same: render_story and the queue refuse it (theme_problems)."""
    if theme in (None, "", "default"):
        theme = b["default_theme"]
    if theme not in b["themes"]:
        raise BrandError(f"brand {b['name']}: no theme {theme!r}; it has {', '.join(b['themes'])}")
    return _apply(b, theme)


def theme_problems(b):
    """[a message] when the pack's applied theme may not be published yet (allowed: false), else []."""
    if b["themes"][b["theme"]]["allowed"]:
        return []
    return [f"theme {b['theme']!r} of {b['name']} is a preview (allowed: false in brands/{b['name']}/brand.json): "
            "plan, probe, still and selftest may show it, a render waits for the owner's approval"]


def of(story, theme=None):
    """The story's pack, with `theme` applied (default: the pack's default theme)."""
    b = load(story.get("brand") or DEFAULT)
    return themed(b, theme) if theme not in (None, "", "default") else b


def with_say(story):
    """The story with the pack's spoken forms under its own "say" map (the story's entry wins): a pack's own names
    (SiTech -> საი-თეჩი) are read right in every script without the writer repeating them."""
    pack = of(story).get("say") or {}
    if not pack:
        return story
    return {**story, "say": {**pack, **(story.get("say") or {})}}


def summary(b):
    """What `engine options` shows of a pack."""
    return {"label": b["label"], "about": b.get("about", ""), "lang": b["lang"], "logo": b["logo"]["kind"],
            "link": b["link"]["display"], "categories": len(b["categories"]), "voices": sorted(b.get("voices") or {}),
            "default_theme": b["default_theme"],
            "themes": {t: {"label": s["label"], "about": s["about"], "allowed": s["allowed"], "mode": mode(s["colors"]),
                           "canvas": s["colors"]["canvas"], "ink": s["colors"]["ink"], "accent": s["colors"]["accent"]}
                       for t, s in b["themes"].items()}}


def for_remotion(b):
    """The part of the pack the composition draws with (no paths: props.py copies the files into public/): the
    applied theme's colors, plus the QR's two (qr_colors) and the theme's name and mode."""
    dark, light = qr_colors(b["colors"])
    return {"name": b["name"], "label": b["label"], "theme": b["theme"], "mode": mode(b["colors"]),
            "colors": {**b["colors"], "qrDark": dark, "qrLight": light}, "wordmark": b["wordmark"],
            "logo": b["logo"]["kind"], "footer": b["footer"], "strings": b["strings"]}
