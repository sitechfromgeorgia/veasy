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


_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE]-?\d+)?")
_ARITY = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}


def _path_points(d):
    """Every end and control point of a path (absolute), for its bounding box."""
    pts, x, y, start, cmd, nums = [], 0.0, 0.0, (0.0, 0.0), None, []
    for tok in _TOKEN.findall(d or ""):
        if tok.isalpha():
            cmd, nums = tok, []
            if cmd in "Zz":
                x, y = start
            continue
        if cmd is None:
            continue
        nums.append(float(tok))
        k = cmd.lower()
        if len(nums) < _ARITY[k]:
            continue
        rel = cmd.islower()
        if k == "h":
            x = x + nums[0] if rel else nums[0]
        elif k == "v":
            y = y + nums[0] if rel else nums[0]
        else:
            pairs = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)] if k != "a" else [(nums[5], nums[6])]
            for px, py in pairs[:-1]:  # control points
                pts.append((x + px, y + py) if rel else (px, py))
            ex, ey = pairs[-1]
            x, y = (x + ex, y + ey) if rel else (ex, ey)
            if k == "m":
                start = (x, y)
                cmd = "l" if rel else "L"  # extra pairs after a move are lines
        pts.append((x, y))
        nums = []
    return pts


def _translate(transform):
    m = re.search(rf"translate\(\s*({_N})(?:\s*[ ,]\s*({_N}))?", transform or "")
    return (float(m.group(1)), float(m.group(2) or 0)) if m else (0.0, 0.0)


def _f(attrs, k, default=0.0):
    try:
        return float(attrs.get(k, default))
    except ValueError:
        return default


def _box(tree, dx=0.0, dy=0.0):
    """(points of every element, shifted by the translations above it)."""
    pts = []
    for n in tree:
        a = n["attrs"]
        tx, ty = _translate(a.get("transform"))
        ox, oy = dx + tx, dy + ty
        t = n["tag"]
        local = []
        if t == "rect":
            x, y = _f(a, "x"), _f(a, "y")
            local = [(x, y), (x + _f(a, "width"), y + _f(a, "height"))]
        elif t in ("circle", "ellipse"):
            rx = _f(a, "r") if t == "circle" else _f(a, "rx")
            ry = _f(a, "r") if t == "circle" else _f(a, "ry")
            local = [(_f(a, "cx") - rx, _f(a, "cy") - ry), (_f(a, "cx") + rx, _f(a, "cy") + ry)]
        elif t == "line":
            local = [(_f(a, "x1"), _f(a, "y1")), (_f(a, "x2"), _f(a, "y2"))]
        elif t in ("polyline", "polygon"):
            nums = [float(v) for v in re.findall(_N, a.get("points", ""))]
            local = list(zip(nums[::2], nums[1::2]))
        elif t == "path":
            local = _path_points(a.get("d"))
        elif t == "text" and n["text"]:
            size = _f(a, "font-size", 32)
            w = len(n["text"]) * size * 0.58
            x0 = {"middle": -w / 2, "end": -w}.get(a.get("text-anchor"), 0)
            local = [(_f(a, "x") + x0, _f(a, "y") - size), (_f(a, "x") + x0 + w, _f(a, "y"))]
        pts += [(px + ox, py + oy) for px, py in local]
        pts += _box(n["children"], ox, oy)
    return pts


def _walk(tree):
    for n in tree:
        yield n
        yield from _walk(n["children"])


def quality(tree):
    """What code can judge of a drawing nobody reviews: it is big enough to read on a phone, stays on its canvas,
    builds up (motion with different delays) and keeps the accent for one focal part."""
    out = []
    pts = _box(tree)
    if not pts:
        return ["draw: the drawing has no visible shapes"]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if w < 0.40 * VIEW[0] or h < 0.35 * VIEW[1]:
        out.append(f"draw: the drawing is small ({w:.0f}x{h:.0f} of {VIEW[0]}x{VIEW[1]}): draw it bigger, use most "
                   f"of the canvas")
    if min(xs) < -40 or min(ys) < -40 or max(xs) > VIEW[0] + 40 or max(ys) > VIEW[1] + 40:
        out.append(f"draw: parts are outside the 0 0 {VIEW[0]} {VIEW[1]} canvas")
    nodes = list(_walk(tree))
    moving = [n for n in nodes if n["motion"]]
    if len(moving) < 3 or len({n["delay"] for n in moving}) < 2:
        out.append("draw: give at least 3 parts a motion class (r, p, s) with different --d delays, so it builds up")
    accent = [n for n in nodes if "ACCENT" in (n["attrs"].get("fill"), n["attrs"].get("stroke"))]
    if len(accent) > 6:
        out.append(f"draw: ACCENT is on {len(accent)} elements: keep it for the one focal part")
    return out


def scene_problems(svg):
    """Everything wrong with one draw scene's SVG: what the whitelist removed and what the quality check found."""
    tree, problems = sanitize(svg)
    return problems + (quality(tree) if tree else [])


def story_problems(story):
    """The drawing problems of a whole story (the writer's checks add these)."""
    draws = [s for s in story.get("scenes") or [] if s.get("type") == "draw"]
    out = [] if len(draws) <= 1 else [f"draw: {len(draws)} drawings; use at most one"]
    for s in draws:
        out += scene_problems(s.get("svg", ""))
    return out


def drop_bad(story):
    """(story without the drawings that still fail, how many were dropped). The scene before a dropped drawing simply
    stays up longer; a video without a drawing is better than no video."""
    kept, dropped, seen = [], 0, False
    for s in story.get("scenes") or []:
        if s.get("type") == "draw" and (seen or scene_problems(s.get("svg", ""))):
            dropped += 1
            continue
        seen = seen or s.get("type") == "draw"
        kept.append(s)
    return {**story, "scenes": kept}, dropped


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
