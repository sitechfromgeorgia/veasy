"""A brand pack -> HyperFrames' `frame.md`: the design spec an agent composing a film (Lane B, docs/plan-v2.md) reads.

HyperFrames reads the first of frame.md / design.md at a project's root: YAML frontmatter that is normative (colors,
typography, spacing, components: "quote hex values, families and weights exactly") and prose that is intent (what
the look is for, Do's and Don'ts). The format is the one of its frame presets (skills/hyperframes/assets/
frame-presets/*/FRAME.md, `version: alpha`). This module writes it from the pack, so a composed film keeps the
pack's palette, font and rules, and nothing about a client is typed twice:

    colors       the pack's palette, verbatim (brand.json "colors" + brand.COLOR_DEFAULTS)
    fonts        one family, registered as "Brand" (the name the layout probe checks), from the pack's four woff2
    typography   Veasy's video ramp (sizes for 1080x1920), every role in "Brand"
    layout       the frame's bands, read from remotion/src/brand.ts (probe.constants), so Lane A and Lane B share them
    components   card, chip, ink chip, dot, button, badge, captions box: their colors are references into `colors`
    accent       where the accent may go (the dot, an active state, the button) and where never (text)
    locked       the chrome the agent places but never restyles (header, chapter bar, ticker, footer, captions)

The frontmatter is written as YAML whose every value is JSON (strings always quoted), so `parse()` reads it back
without a YAML library and any YAML reader agrees. `problems()` is what the test checks for every pack.

    python -m tt_shorts.frame_md [--brand sitech] [--out compose/24835/frame.md]
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
SECTIONS = ("Overview", "The Frame", "Colors", "Typography", "Depth & Surface", "Shapes", "Components",
            "Locked Chrome", "Composition Rules", "Numerals & Claims", "Pre-Render Self-Audit", "Known Gaps")
COLOR = re.compile(r"^(#[0-9A-Fa-f]{6}|rgba\(\d{1,3},\d{1,3},\d{1,3},(0|1|0?\.\d+)\))$")
REF = re.compile(r"\{([a-z-]+)\.([A-Za-z0-9-]+)\}")
LOCKED = ("header", "chapter-bar", "ticker", "footer", "captions")


def family_name(b):
    """The real name of the pack's font (FiraGO), from its woff2's name table."""
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
    fam = family_name(b)
    return {
        "version": "alpha",
        "name": f"{b['label']} · Veasy frame",
        "description": f"{b.get('about', '')} Generated from brands/{b['name']}/brand.json by tt_shorts/frame_md.py: "
                       "change the pack, not this file.",
        "unit": f"the frame: {c['W']}x{c['H']} (9:16), {probe.FPS} fps",
        "principle": "tokens are fixed · composition is free · every fact comes from the story",
        "pack": b["name"],
        "lang": b["lang"],
        "colors": dict(b["colors"]),
        "fonts": {"family": "Brand", "face": fam, "weights": [int(w) for w in brand.FONT_WEIGHTS],
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
                     "rounded": "{rounded.card}", "description": "Every panel: a color step and a 1-2px line, never a shadow."},
            "chip": {"backgroundColor": "{colors.panel}", "border": "2px solid {colors.lineStrong}",
                     "textColor": "{colors.ink}", "rounded": "{rounded.chip}", "typography": "{typography.chip}",
                     "description": "A place, a date, a source: fully round."},
            "chip-ink": {"backgroundColor": "{colors.ink}", "textColor": "{colors.canvas}", "rounded": "{rounded.chip}",
                         "typography": "{typography.chip}",
                         "description": "Inverted ink: the highlight the brand allows (a keyword, the chip being said)."},
            "dot": {"backgroundColor": "{colors.accent}", "rounded": "{rounded.chip}", "size": "16-24px",
                    "description": "'now': the progress head, a live marker. The one accent a still frame may hold."},
            "button": {"backgroundColor": "{colors.accent}", "textColor": "{colors.onAccent}",
                       "rounded": "{rounded.button}", "typography": "{typography.label}",
                       "description": "The call to action on the end card, once per film."},
            "badge": {"backgroundColor": "{colors.panel}", "border": "2px solid {colors.lineStrong}",
                      "iconColor": "{colors.ink}", "rounded": "{rounded.chip}",
                      "description": "A big line icon (Lucide, stroke 2 on 24) in a circle: ink on panel, no tint."},
            "captions-box": {"backgroundColor": "{colors.canvas}", "opacity": 0.8, "border": "2px solid {colors.line}",
                             "rounded": "{rounded.card}", "said": "{colors.ink}", "waiting": "{colors.waiting}",
                             "active": "underline {colors.accent}", "keyword": "{components.chip-ink}",
                             "typography": "{typography.caption}"},
        },
        "accent": {"allowed": ["dot", "active state", "button"],
                   "never": ["text", "a category", "a fill behind text", "an icon", "a chart series"]},
        "locked": list(LOCKED),
    }


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


def prose(b):
    """The intent: the pack's rules in words (the frontmatter holds the numbers)."""
    f = front(b)
    lay, col = f["layout"], f["colors"]
    face = f["fonts"]["face"]
    return f"""# {b['label']} · Veasy frame (video, 1080x1920)

## Overview

A news short for {b['label']}, composed scene by scene and still unmistakably the pack's own. {b.get('about', '')}
The film is one dark canvas ({col['canvas']}), light ink ({col['ink']}), quiet greys ({col['muted']}, panel
{col['panel']}) and one accent ({col['accent']}). Richness comes from layout, scale, icons, maps, numbers and a beat
every 1.5-3 s, never from more colors.

## The Frame

- {lay['frame']['width']}x{lay['frame']['height']} at {lay['frame']['fps']} fps. Distances are multiples of 4; the side margin is {f['spacing']['side']}.
- Header {lay['header']['top']}-{lay['header']['bottom']} (locked chrome). Scene text lives only inside {lay['scene']['top']}-{lay['scene']['bottom']}.
- Captions: a box {lay['captions']['width']} wide from x={lay['captions']['left']}, ending at y={lay['captions']['bottom']} (locked chrome).
- {lay['ticker']['top']}-{lay['ticker']['bottom']} carries motion only (the platforms draw their UI there); the footer {lay['footer']['top']}-{lay['footer']['bottom']} holds the source and the link.
- Below y={lay['rail']['below']}, nothing is drawn right of x={lay['rail']['x']} (the like/share rail).
- Frame 0 is the thumbnail: the hook is already on screen, never black, never a logo alone.

## Colors

Quote the tokens exactly. Hierarchy is ink, muted, waiting and the panel steps. The accent ({col['accent']}) belongs
to the dot ("now"), an active state (the progress head, the spoken word's underline, the current chapter's head)
and the end card's button, and to nothing else: never text, never a category, never a fill behind text, never an
icon. There are no category colors and no tints. Grounds are solid: no full-screen linear gradients (they band).

## Typography

One family: "Brand" ({face}), weights 400/500/600/700, loaded from `assets/brand.css`. Hierarchy comes from size,
weight and color only: no caps, no letter-spacing, no italics, no shadows, no outlines. Numbers are written in
digits with a thin space for thousands (6 400). No text under its region's floor (`typography.floor`, px).

## Depth & Surface

Depth is a color step (canvas, panel) and a 2px line, never a shadow or a blur behind text. Cards may stack and
overlap by layout, not by elevation.

## Shapes

Cards and panels have radius {f['rounded']['card']}; chips, badges, dots and buttons are fully round. The mark is
never framed, recolored or distorted.

## Components

- **card**: panel, line border, radius {f['rounded']['card']}: a source card, a map card, a step of a diagram.
- **chip**: a place, a date, a source, round. **chip-ink**: the inverted chip, for the item being said.
- **badge**: a big Lucide line icon in an ink stroke inside a panel circle (the reference's tinted circle, without the tint).
- **dot**: the accent "now" marker, 16-24 px. **button**: the accent call to action, once, on the end card.
- **captions-box**: drawn by the locked captions component, not by a scene.

## Locked Chrome

`compositions/chrome.html` and `compositions/captions.html` are written by Veasy from the story and its timing:
the pack's mark and wordmark, the date, weekday · time · category, the chapter bar, the ticker, the source line, the
link and the pack's footer line, and the captions laid out by captions.py. Place their hosts in `index.html`; never
edit, restyle, cover or remove them. A scene draws only inside the scene band.

## Composition Rules

### Do

- Give every phrase its own picture: a new element, a highlight or a move every 1.5-3 s, landing on the word that
  says it (`timing.json` holds the words and the beats).
- Build pictures from the story's own facts: the number with its source chip, the place on the map, the time as a
  timeline, the cause as a diagram (icon -> icon).
- Use icons from `assets/icons` (Lucide) in ink; one badge per idea.
- Mark every text element's region with `data-probe` (scene, card) so the layout probe can read it.

### Don't

- No text in the accent color, no second accent, no tints, no gradients behind text, no shadows.
- No text past the scene band, under the captions or right of the rail below y={lay['rail']['below']}.
- No publisher photos, no generated people, no imagery for crime, incidents or deaths.
- No long dashes, no caps, no letter-spacing.

## Numerals & Claims

Every number, name, date and quote on screen comes from the story file, word for word or as the narration says it.
The date, the time and the sources are code's (the chrome), never the scene's. Nothing is claimed that the story
does not say; no opinion.

## Pre-Render Self-Audit

- Squint: one hero per beat, and the accent appears only as a dot, an active state or the button.
- Every text inside its band; the rail and the captions are clear.
- `npx hyperframes check` passes; Veasy's probe reads every text in "Brand" with no missing glyph.
- Something changes at least every 3 s; every text holds long enough to read (0.5 s + 0.3 s a word).

## Known Gaps

- Media (stock, screenshots, illustrations) waits for the media layer (plan-v2 § 4); until then pictures are icons,
  maps, numbers and type.
- Tints for illustrations are an owner decision (plan-v2 § 8, decision 2): not in this pack.
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
    root, stack = {}, [(-1, None)]
    stack[0] = (-1, root)
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
              "components", "accent", "locked"):
        if k not in fm:
            out.append(f"frontmatter misses {k}")
    out += [f"section missing: ## {s}" for s in SECTIONS if s not in sections]
    for k, v in (fm.get("colors") or {}).items():
        if not isinstance(v, str) or not COLOR.match(v.replace(" ", "")):
            out.append(f"colors.{k} is not a #RRGGBB or rgba() value: {v!r}")
    for k, v in (fm.get("typography") or {}).items():
        if k != "floor" and (v.get("fontFamily") != "Brand" or v.get("weight") not in (400, 500, 600, 700)):
            out.append(f"typography.{k} is not in Brand at one of the pack's four weights")
    for name, comp in (fm.get("components") or {}).items():
        for prop, val in comp.items():
            for grp, key in REF.findall(str(val)):
                if _get(fm, [grp, key]) is None:
                    out.append(f"components.{name}.{prop} names {{{grp}.{key}}}, which is not defined")
        if comp.get("textColor") == "{colors.accent}" or comp.get("iconColor") == "{colors.accent}":
            out.append(f"components.{name} sets text or an icon in the accent")
    if "text" not in (_get(fm, ["accent", "never"]) or []):
        out.append("accent.never must name text")
    if set(fm.get("locked") or []) != set(LOCKED):
        out.append(f"locked must be {', '.join(LOCKED)}")
    if "—" in text or "–" in text:
        out.append("long dashes (the brand has none)")
    lay = fm.get("layout") or {}
    c = probe.C
    want = {("scene", "top"): c["SCENE_TOP"], ("scene", "bottom"): c["SCENE_BOTTOM"],
            ("captions", "bottom"): c["CAPTION_BOTTOM"], ("rail", "x"): c["RAIL_X"], ("rail", "below"): c["RAIL_Y"],
            ("frame", "width"): c["W"], ("frame", "height"): c["H"]}
    for path, v in want.items():
        if _get(lay, path) != v:
            out.append(f"layout.{'.'.join(path)} is {_get(lay, path)}, the frame says {v}")
    if b is not None:
        if fm.get("colors") != b["colors"]:
            out.append("colors differ from the pack's")
        if fm.get("pack") != b["name"]:
            out.append(f"pack is {fm.get('pack')!r}, not {b['name']!r}")
    return out


def write(name, path):
    b = brand.load(name)
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(b), encoding="utf-8")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", default=brand.DEFAULT)
    ap.add_argument("--out", help="write here (default: print)")
    a = ap.parse_args()
    if a.out:
        print(write(a.brand, a.out))
    else:
        print(render(brand.load(a.brand)))
