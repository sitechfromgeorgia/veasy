"""Story-specific drawings (the "draw" scene): the writer draws, code keeps it safe and on-brand.

From sitech-shorts (shorts/art.py), where a drawing per story is what makes each video different. A draw scene
carries an SVG fragment the writer made for this story (a gas pipe, a bus, a court building, a chip...). sanitize()
keeps only whitelisted elements and attributes, keeps colors as brand tokens and turns the motion classes into
data, so remotion/src/scenes/Draw.tsx can animate it as a pure function of the frame (CSS animations would not be
frame-accurate in a render). The problems it finds go back to the writer like any other check.

    tree, problems = sanitize(svg)
    tree: [{"tag": "path", "attrs": {"d": "...", "stroke": "INK"}, "motion": "s", "delay": 0.4,
            "children": [...], "text": None}, ...]

Tokens (the brand pack picks the colors): ACCENT (the ONE focal part), INK, MUTED, LINE, CANVAS, none.
sitech-shorts' PAPER and COAL are read as INK and CANVAS.
"""
import re
import xml.etree.ElementTree as ET

VIEW = (952, 640)  # the drawing's canvas, below the headline
TAGS = {"g", "path", "line", "polyline", "polygon", "rect", "circle", "ellipse", "text"}
ATTRS = {"d", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "width", "height", "points", "transform",
         "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "opacity",
         "fill-opacity", "stroke-opacity", "font-size", "font-weight", "text-anchor", "class", "style"}
TOKENS = ("ACCENT", "INK", "MUTED", "LINE", "CANVAS", "none")
ALIASES = {"PAPER": "INK", "COAL": "CANVAS"}
MOTION = {"r", "p", "s"}  # rise, pop, stroke-draw
MAX_CHARS = 6000
MAX_DELAY = 3.0
MIN_ELEMENTS, MAX_ELEMENTS = 6, 60
MAX_LABEL = 22
_N = r"-?\d+(?:\.\d+)?"
TRANSFORM = re.compile(rf"(\s*(translate|rotate|scale)\(\s*{_N}(\s*[ ,]\s*{_N}){{0,2}}\s*\)\s*)+")

GUIDE = """"draw" scene: draw what THIS story is about, as an SVG fragment in "svg" (no <svg> tag):
- Something a viewer recognizes without the narration: a gas pipe with a valve for a gas cut, a bus at a stop
  for a transport change, a court building, a phone with a notification, a bridge, a ballot box. Never a generic
  abstract shape, never a real logo or a face (draw a generic object).
- Style: clean line art like a technical schematic. Mostly strokes (fill "none"), stroke-width 4-8, round caps
  and joins. Rounded rects (rx 10-24) for devices and buildings. 8-35 elements.
- Colors: ONLY these tokens in fill and stroke: INK (main lines), MUTED (secondary details), LINE (faint
  structure), CANVAS (solid fills that hide what is behind), ACCENT (the ONE focal part, small), none.
- Canvas: 0 0 952 640. Use most of it.
- Labels: up to 4 <text>, font-size 26-40, font-weight 600-700, up to 18 characters, fill INK or MUTED, Georgian.
  A number in a label must be in the articles.
- Motion: class "r" (rises in), "p" (pops in) or "s" (the stroke draws itself), with style "--d:0.4s"; delays
  0.2s-2.2s so it builds in a sensible order (structure first, the focal part and labels last). Group parts with
  <g class="r" style="--d:0.6s">.
- Allowed: g path line polyline polygon rect circle ellipse text. No images, gradients, filters or scripts.
  Under 5000 characters."""


def _token(v):
    v = ALIASES.get(v, v)
    return v if v in TOKENS else None


def _num(v, lo, hi):
    try:
        return str(max(lo, min(float(v), hi)))
    except ValueError:
        return None


def sanitize(fragment):
    """SVG fragment -> (tree, problems). The tree is safe to draw; the problems go back to the writer."""
    problems = []
    if not isinstance(fragment, str) or not fragment.strip():
        return [], ["draw: svg is empty"]
    if len(fragment) > MAX_CHARS:
        problems.append(f"draw: svg is {len(fragment)} characters, keep it under 5000")
    fragment = re.sub(r"^\s*<svg[^>]*>|</svg>\s*$", "", fragment.strip())
    try:
        root = ET.fromstring(f"<g>{fragment}</g>")
    except ET.ParseError as e:
        return [], problems + [f"draw: svg is not valid XML: {e}"]
    count = [0]

    def node(el):
        tag = el.tag.split("}")[-1]
        if tag not in TAGS:
            problems.append(f"draw: <{tag}> is not allowed")
            return None
        count[0] += 1
        attrs, motion, delay = {}, None, 0.0
        for k, v in el.attrib.items():
            k = k.split("}")[-1]
            if k not in ATTRS:
                problems.append(f'draw: attribute "{k}" is not allowed')
                continue
            if k in ("fill", "stroke"):
                t = _token(v.strip())
                if not t:
                    problems.append(f'draw: {k}="{v}": use only {", ".join(TOKENS)}')
                    t = "INK" if k == "stroke" or tag == "text" else "none"
                attrs[k] = t
            elif k == "class":
                bad = set(v.split()) - MOTION
                if bad:
                    problems.append(f'draw: class "{v}": use only r, p or s')
                ok = [c for c in v.split() if c in MOTION]
                motion = ok[0] if ok else None
            elif k == "style":
                m = re.fullmatch(r"\s*--d\s*:\s*(\d+(?:\.\d+)?)s\s*;?\s*", v)
                if not m:
                    problems.append(f'draw: style "{v}": only "--d:0.5s" is allowed')
                    continue
                delay = min(float(m.group(1)), MAX_DELAY)
            elif k == "font-size":
                n = _num(v, 20, 56)
                if n:
                    attrs[k] = n
            elif k in ("opacity", "fill-opacity", "stroke-opacity"):
                n = _num(v, 0, 1)
                if n:
                    attrs[k] = n
            elif k == "transform":
                if not TRANSFORM.fullmatch(v):
                    problems.append(f'draw: transform "{v}": only translate, rotate and scale with numbers')
                    continue
                attrs[k] = v.strip()
            else:
                if re.search(r"[<>\"'`]|url\(|javascript", v, re.I):
                    problems.append(f'draw: attribute "{k}" has an unsafe value')
                    continue
                attrs[k] = v
        text = None
        if tag == "text":
            text = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
            if len(text) > MAX_LABEL:
                problems.append(f'draw: label "{text[:30]}" is longer than 18 characters')
                text = text[:MAX_LABEL]
            attrs.setdefault("fill", "INK")
            children = []
        else:
            children = [c for c in (node(ch) for ch in el) if c]
        return {"tag": tag, "attrs": attrs, "motion": motion, "delay": delay, "children": children, "text": text}

    tree = [c for c in (node(ch) for ch in root) if c]
    if count[0] < MIN_ELEMENTS:
        problems.append(f"draw: the drawing has only {count[0]} elements, draw a recognizable object (8-35 elements)")
    if count[0] > MAX_ELEMENTS:
        problems.append(f"draw: {count[0]} elements is too many, keep it under 35")
    labels = [t for t in labels_of(tree)]
    if len(labels) > 4:
        problems.append(f"draw: {len(labels)} labels, use at most 4")
    return tree, problems


def labels_of(tree):
    """Every label (<text>) of a sanitized tree, in order: the only on-screen words in a drawing."""
    for n in tree:
        if n["text"]:
            yield n["text"]
        yield from labels_of(n["children"])


def labels(fragment):
    """The labels of an unsanitized fragment (for the Georgian and number checks); [] when it doesn't parse."""
    tree, _ = sanitize(fragment)
    return list(labels_of(tree))
