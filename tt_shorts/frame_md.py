"""A brand pack -> HyperFrames' `frame.md`: the design spec an agent reads before composing a film for that pack.

Veasy has two engines: Remotion (the typed brush kit) and HyperFrames (films composed in HTML/CSS/GSAP). HyperFrames
reads the first of frame.md / design.md at a project's root: YAML frontmatter that is normative (colors, typography,
spacing, components: "quote hex values, families and weights exactly") and prose that is intent (Do's and Don'ts).
The format is the one of its frame presets (skills/hyperframes/assets/frame-presets/*/FRAME.md, `version: alpha`).

Everything about a client comes from its pack; Veasy adds only what is the engine's for every pack:

    colors       the palette of the pack's theme the film is made in, verbatim (brand.json "themes", its default
                 or the one asked for, + brand.COLOR_DEFAULTS); "theme" names it, "themes" lists the pack's others
    fonts        the pack's one family, registered as "Brand" (the name the layout probe checks), its four woff2
    typography   Veasy's video ramp (sizes for 1080x1920), every role in "Brand"
    layout       the frame's bands (the platforms' safe zone), read from remotion/src/brand.ts, shared by both engines
    components   card, chip, ink chip, dot, button, badge, captions box: colors are references into `colors`
    accent       only when the pack says where its accent may and may never go (brand.json "design.accent")
    rules        only the pack's own sentences (brand.json "design.rules")
    locked       the chrome the agent places but never restyles (header, chapter bar, ticker, footer, captions, end card)

The frontmatter is written as YAML whose every value is JSON (strings always quoted), so `parse()` reads it back
without a YAML library and any YAML reader agrees. `problems()` is what the test checks for every pack.

    python -m tt_shorts.frame_md [--brand sitech] [--theme light] [--out out/compose/24835-sitech/frame.md]
"""
import argparse
import json
import pathlib
import re

from tt_shorts import brand, captions, probe

TYPE = {  # role -> (px, weight, line height); px at 1080x1920
    "hook": (112, 700, 1.12),
    "number": (240, 700, 1.0),
    "title": (64, 700, 1.2),
    "body": (44, 500, 1.3),
    "label": (32, 600, 1.3),
    "chip": (30, 600, 1.0),
    "meta": (28, 400, 1.4),
}
SECTIONS = ("Overview", "The Frame", "Colors", "Typography", "Components", "Locked Chrome", "Pack Rules",
            "Composition Rules", "Numerals & Claims", "Pre-Render Self-Audit", "Known Gaps")
COLOR = re.compile(r"^(#[0-9A-Fa-f]{6}|rgba\(\d{1,3},\d{1,3},\d{1,3},(0|1|0?\.\d+)\))$")
REF = re.compile(r"\{([a-z-]+)\.([A-Za-z0-9-]+)\}")
LOCKED = ("header", "chapter-bar", "ticker", "footer", "captions", "end-card")


def family_name(b):
    """The real name of the pack's font, from its woff2's name table."""
    from fontTools.ttLib import TTFont
    return TTFont(b["_fonts"]["700"])["name"].getDebugName(1) or "Brand"


def layout(c=None):
    """The frame's bands in px, from remotion/src/brand.ts (the layout probe's constants)."""
    c = c or probe.C
    return {
        "frame": {"width": c["W"], "height": c["H"], "fps": probe.FPS},
        "header": {"top": 80, "bottom": 210},
        "scene": {"top": c["SCENE_TOP"], "bottom": c["SCENE_BOTTOM"], "side": c["SIDE"]},
        "captions": {"left": c["W"] - c["RAIL_X"], "width": captions.BAND, "bottom": c["CAPTION_BOTTOM"]},
        "ticker": {"top": c["CAPTION_BOTTOM"] + 28, "bottom": 1760},
        "footer": {"top": 1768, "bottom": 1880},
        "rail": {"x": c["RAIL_X"], "below": c["RAIL_Y"]},
    }


def front(b):
    """The normative part, as a dict (written in this order)."""
    c = probe.C
    design = b.get("design") or {}
    out = {
        "version": "alpha",
        "name": f"{b['label']} · Veasy frame",
        "description": f"{b.get('about', '')} Generated from brands/{b['name']}/brand.json by tt_shorts/frame_md.py: "
                       "change the pack, not this file.",
        "unit": f"the frame: {c['W']}x{c['H']} (9:16), {probe.FPS} fps",
        "principle": "tokens are the pack's · composition is free · every fact comes from the story",
        "pack": b["name"],
        "theme": b["theme"],
        "themes": {t: {"mode": brand.mode(s["colors"]), "allowed": s["allowed"]} for t, s in b["themes"].items()},
        "lang": b["lang"],
        "colors": dict(b["colors"]),
        "fonts": {"family": "Brand", "face": family_name(b), "weights": [int(w) for w in brand.FONT_WEIGHTS],
                  "files": {w: f"assets/fonts/brand-{w}.woff2" for w in brand.FONT_WEIGHTS},
                  "css": "assets/brand.css"},
        "typography": {
            **{k: {"fontFamily": "Brand", "px": px, "weight": wt, "lineHeight": lh} for k, (px, wt, lh) in TYPE.items()},
            "caption": {"fontFamily": "Brand", "px": captions.SIZES["page"], "weight": 700,
                        "lineHeight": captions.LINE_HEIGHT},
            "floor": dict(probe.MIN_PX),
        },
        "rounded": {"card": c["RADIUS"], "chip": 9999, "button": 9999},
        "spacing": {"unit": 4, "side": c["SIDE"], "card-pad": 48, "gap": 24},
        "layout": layout(c),
        "components": {
            "card": {"backgroundColor": "{colors.panel}", "border": "2px solid {colors.line}",
                     "rounded": "{rounded.card}"},
            "chip": {"backgroundColor": "{colors.panel}", "border": "2px solid {colors.lineStrong}",
                     "textColor": "{colors.ink}", "rounded": "{rounded.chip}", "typography": "{typography.chip}"},
            "chip-ink": {"backgroundColor": "{colors.ink}", "textColor": "{colors.canvas}", "rounded": "{rounded.chip}",
                         "typography": "{typography.chip}", "description": "Inverted ink: the item being said."},
            "dot": {"backgroundColor": "{colors.accent}", "rounded": "{rounded.chip}", "size": "16-24px",
                    "description": "'now': the progress head, a live marker."},
            "button": {"backgroundColor": "{colors.accent}", "textColor": "{colors.onAccent}",
                       "rounded": "{rounded.button}", "typography": "{typography.label}"},
            "badge": {"backgroundColor": "{colors.ticker}", "border": "2px solid {colors.lineStrong}",
                      "iconColor": "{colors.ink}", "rounded": "{rounded.chip}",
                      "description": "A big line icon (Lucide, stroke 2 on 24) in a circle, in the pack's ink."},
            "captions-box": {"backgroundColor": "{colors.canvas}", "opacity": 0.8, "border": "2px solid {colors.line}",
                             "rounded": "{rounded.card}", "said": "{colors.ink}", "waiting": "{colors.waiting}",
                             "active": "underline {colors.accent}", "keyword": "{components.chip-ink}",
                             "typography": "{typography.caption}"},
        },
    }
    if design.get("accent"):
        out["accent"] = design["accent"]
    if design.get("rules"):
        out["rules"] = list(design["rules"])
    out["locked"] = list(LOCKED)
    return out


def _dump(d, indent=0):
    """Top-level maps as YAML blocks, everything below them as one JSON value per line."""
    out = []
    for k, v in d.items():
        if isinstance(v, dict) and v and indent == 0:
            out.append(f"{k}:")
            out += _dump(v, 2)
        else:
            out.append(f"{' ' * indent}{k}: {json.dumps(v, ensure_ascii=False)}")
    return out


def _accent_prose(f):
    acc = f.get("accent")
    if not acc:
        return ("The pack sets no limit on where its accent goes (a pack says so in brand.json "
                "`design.accent`). Veasy's own chrome uses it for the progress dot, the spoken word's underline and "
                "the end card's button.")
    allowed = ", ".join(acc.get("allowed", [])) or "nothing"
    never = ", ".join(acc.get("never", []))
    return (f"The pack's accent ({f['colors']['accent']}) belongs to: {allowed}. Never: {never}. "
            "The layout probe reports any text drawn in the accent.")


def prose(b):
    """The intent, in words: the engine's frame and the pack's own rules (the frontmatter holds the numbers)."""
    f = front(b)
    lay, col = f["layout"], f["colors"]
    rules = f.get("rules") or []
    pack_rules = "\n".join(f"- {r}" for r in rules) if rules else (
        "This pack states no design rules beyond its tokens. A pack writes them in brand.json `design.rules` "
        "(sentences) and `design.accent` (where the accent may go).")
    return f"""# {b['label']} · Veasy frame (video, 1080x1920)

## Overview

A short for {b['label']}, composed scene by scene from the story's facts and drawn only in this pack's tokens.
{b.get('about', '')}
Canvas {col['canvas']}, panel {col['panel']}, ink {col['ink']}, muted {col['muted']}, accent {col['accent']}.
Richness comes from layout, scale, icons, maps, numbers and a beat every 1.5-3 s.

## The Frame

- {lay['frame']['width']}x{lay['frame']['height']} at {lay['frame']['fps']} fps; the side margin is {f['spacing']['side']}.
- Header {lay['header']['top']}-{lay['header']['bottom']} (locked chrome). Scene text lives only inside {lay['scene']['top']}-{lay['scene']['bottom']}.
- Captions: a box {lay['captions']['width']} wide from x={lay['captions']['left']}, ending at y={lay['captions']['bottom']} (locked chrome).
- {lay['ticker']['top']}-{lay['ticker']['bottom']} carries motion only (the platforms draw their UI there); the footer {lay['footer']['top']}-{lay['footer']['bottom']} holds the source and the link.
- Below y={lay['rail']['below']}, no text right of x={lay['rail']['x']} (the platforms' like/share rail).
- Frame 0 is the thumbnail: the hook is already on screen, never black, never a logo alone.

## Colors

Quote the tokens exactly; use them through `assets/brand.css` (`var(--ink)`, `var(--accent)`...), never as typed
hex, so the same scenes render in another pack and in another of its themes. This film is in the pack's
"{f['theme']}" theme ({f['themes'][f['theme']]['mode']} ground); the pack has {', '.join(f'{t} ({s["mode"]})' for t, s in f['themes'].items())}.
Never assume a dark ground: no white or black typed anywhere, text is `--ink` or `--muted` on `--canvas` or `--panel`,
an inverted block is `--ink` behind `--canvas` text. {_accent_prose(f)}

## Typography

One family: "Brand" ({f['fonts']['face']}), weights 400/500/600/700, from `assets/brand.css`. No text under its
region's floor (`typography.floor`, px).

## Components

- **card**: panel, line border, radius {f['rounded']['card']}. **chip**: round, line border. **chip-ink**: inverted ink.
- **badge**: a big Lucide line icon in the pack's ink inside a circle.
- **dot**: the accent "now" marker. **button**: the accent call to action (the end card has it).
- **captions-box**: drawn by the locked captions component, not by a scene.

## Locked Chrome

`compositions/chrome.html` and `compositions/captions.html` are written by Veasy from the pack, the story and its
timing: the pack's logo, the date, weekday · time · category, the chapter bar, the meter wipes, the ticker, the
source line, the link and the pack's footer line, the end card (logo, QR, link, call to action), and the captions
laid out by captions.py. Place their hosts in `index.html`; never edit, restyle, cover or remove them.

## Pack Rules

{pack_rules}

## Composition Rules

### Do

- Give every phrase its own picture: a new element, a highlight or a move every 1.5-3 s, landing on the word that
  says it (`timing.json` holds the words and the beats).
- Build pictures from the story's own facts: a number with its source chip, the place on the map, the time as a
  timeline, the cause as a diagram (icon -> icon).
- Mark every text element's region with `data-probe="scene"` so the layout probe can read it.

### Don't

- No typed colors, fonts, logos or links in a scene: they are the pack's (`assets/brand.css`, the chrome).
- No text past the scene band, under the captions or right of the rail below y={lay['rail']['below']}.
- No media without its licence in the ledger; for the news program, no imagery for crime, incidents or deaths (N10).

## Numerals & Claims

Every number, name, date and quote on screen comes from the story file, as the story or the narration says it. The
date, the time, the sources and the link are code's (the chrome), never the scene's. Nothing the story does not say.

## Pre-Render Self-Audit

- One hero per beat; something changes at least every 3 s; every text holds 0.5 s + 0.3 s a word.
- Every text inside its band; the rail and the captions are clear.
- `npx hyperframes check` passes; Veasy's probe reads every text in "Brand" with no missing glyph.

## Known Gaps

- Media (stock, screenshots, illustrations) waits for the media layer (plan-v2 § 4): pictures are icons, maps,
  numbers and type until then.
- Illustration tints are a pack decision (plan-v2 § 8, decision 2); a pack has no tint tokens yet.
"""


def render(b):
    """The whole frame.md for a resolved pack (brand.load)."""
    return "---\n" + "\n".join(_dump(front(b))) + "\n---\n\n" + prose(b)


def parse(text):
    """frame.md -> (frontmatter dict, [section titles]). Reads the subset render() writes: two-space nesting, every
    value JSON. Raises ValueError on anything else."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("no frontmatter between --- lines")
    root = {}
    stack = [(-1, root)]
    for n, line in enumerate(m.group(1).splitlines(), 2):
        if not line.strip():
            continue
        ind = len(line) - len(line.lstrip(" "))
        key, sep, val = line.strip().partition(":")
        if not sep or ind % 2:
            raise ValueError(f"line {n}: not 'key: value' at an even indent: {line!r}")
        while stack[-1][0] >= ind:
            stack.pop()
        parent = stack[-1][1]
        if val.strip():
            try:
                parent[key] = json.loads(val)
            except ValueError as e:
                raise ValueError(f"line {n}: value is not JSON: {val.strip()!r} ({e})")
        else:
            parent[key] = {}
            stack.append((ind, parent[key]))
    sections = re.findall(r"^## (.+)$", text[m.end():], re.M)
    return root, sections


def _get(d, path):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d


def problems(text, b=None):
    """What makes a frame.md unusable or untrue to its pack: [messages]. b: the pack it must match."""
    try:
        fm, sections = parse(text)
    except ValueError as e:
        return [str(e)]
    out = []
    for k in ("version", "name", "description", "colors", "fonts", "typography", "rounded", "spacing", "layout",
              "components", "locked"):
        if k not in fm:
            out.append(f"frontmatter misses {k}")
    out += [f"section missing: ## {s}" for s in SECTIONS if s not in sections]
    for k, v in (fm.get("colors") or {}).items():
        if not isinstance(v, str) or not COLOR.match(v.replace(" ", "")):
            out.append(f"colors.{k} is not a #RRGGBB or rgba() value: {v!r}")
    for k, v in (fm.get("typography") or {}).items():
        if k != "floor" and (v.get("fontFamily") != "Brand" or v.get("weight") not in (400, 500, 600, 700)):
            out.append(f"typography.{k} is not in Brand at one of the pack's four weights")
    never_text = "text" in (_get(fm, ["accent", "never"]) or [])
    for name, comp in (fm.get("components") or {}).items():
        for prop, val in comp.items():
            for grp, key in REF.findall(str(val)):
                if _get(fm, [grp, key]) is None:
                    out.append(f"components.{name}.{prop} names {{{grp}.{key}}}, which is not defined")
        if never_text and comp.get("textColor") == "{colors.accent}":
            out.append(f"components.{name} sets text in the accent, which the pack forbids")
    if set(fm.get("locked") or []) != set(LOCKED):
        out.append(f"locked must be {', '.join(LOCKED)}")
    lay = fm.get("layout") or {}
    c = probe.C
    want = {("scene", "top"): c["SCENE_TOP"], ("scene", "bottom"): c["SCENE_BOTTOM"],
            ("captions", "bottom"): c["CAPTION_BOTTOM"], ("rail", "x"): c["RAIL_X"], ("rail", "below"): c["RAIL_Y"],
            ("frame", "width"): c["W"], ("frame", "height"): c["H"]}
    for path, v in want.items():
        if _get(lay, path) != v:
            out.append(f"layout.{'.'.join(path)} is {_get(lay, path)}, the frame says {v}")
    if b is not None:
        design = b.get("design") or {}
        if fm.get("colors") != b["colors"]:
            out.append("colors differ from the pack's")
        if fm.get("pack") != b["name"]:
            out.append(f"pack is {fm.get('pack')!r}, not {b['name']!r}")
        if fm.get("accent") != design.get("accent"):
            out.append("accent differs from the pack's design.accent (frame.md states only the pack's own rule)")
        if (fm.get("rules") or []) != (design.get("rules") or []):
            out.append("rules differ from the pack's design.rules")
    return out


def write(name, path, theme=None):
    b = brand.themed(brand.load(name), theme)
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(b), encoding="utf-8")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", default=brand.DEFAULT)
    ap.add_argument("--theme", help="one of the pack's themes (default: its default_theme)")
    ap.add_argument("--out", help="write here (default: print)")
    a = ap.parse_args()
    if a.out:
        print(write(a.brand, a.out, a.theme))
    else:
        print(render(brand.themed(brand.load(a.brand), a.theme)))
