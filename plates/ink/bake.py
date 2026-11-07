#!/usr/bin/env python
"""A drawing into what the ink plate paints: ordered strokes, the closed shapes and the dots, all from art.sanitize.

    python plates/ink/bake.py                             all of assets/drawings into plates/ink/drawings.json
    python plates/ink/bake.py --svg d.svg --spec s.json   one writer's drawing into a spec the plate can read
    python plates/ink/bake.py --check                     fail if drawings.json is stale

The tree art.sanitize keeps is walked in order: a group's --d is the stroke order, so "structure first, the focal part
last" survives. Every path, line and shape is flattened to polylines in the drawing's own 952x640 space, transforms
applied. <text> is dropped (a plate holds no text: labels stay in the DOM) and an ACCENT circle is not painted, it
comes back as a dot for anchors.json. The distance field is built from these strokes in the page (field.mjs), at the
size of the bake.
"""
import argparse
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tt_shorts import art  # noqa: E402

OUT = ROOT / "plates" / "ink" / "drawings.json"
CURVE_STEP = 6.0  # px between the points of a flattened curve


def _matmul(a, b):
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
            a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def _apply(m, p):
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


def transform(text, base):
    """art.TRANSFORM's language (translate, rotate, scale) as a matrix on top of `base`."""
    m = base
    for name, args in re.findall(r"(translate|rotate|scale)\(([^)]*)\)", text or ""):
        n = [float(v) for v in re.split(r"[\s,]+", args.strip()) if v]
        if name == "translate":
            step = (1, 0, 0, 1, n[0], n[1] if len(n) > 1 else 0)
        elif name == "scale":
            step = (n[0], 0, 0, n[1] if len(n) > 1 else n[0], 0, 0)
        else:
            c, s = math.cos(math.radians(n[0])), math.sin(math.radians(n[0]))
            step = (c, s, -s, c, 0, 0)
            if len(n) == 3:
                step = _matmul(_matmul((1, 0, 0, 1, n[1], n[2]), step), (1, 0, 0, 1, -n[1], -n[2]))
        m = _matmul(m, step)
    return m


def _bezier(points, out):
    """Flatten one cubic or quadratic, from out[-1], into out."""
    length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    steps = max(2, min(64, math.ceil(length / CURVE_STEP)))
    for i in range(1, steps + 1):
        t = i / steps
        pts = list(points)
        while len(pts) > 1:
            pts = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(pts, pts[1:])]
        out.append(pts[0])


def _arc(p0, rx, ry, phi, large, sweep, p1, out):
    """SVG's endpoint arc, flattened (SVG 1.1 F.6.5)."""
    if not rx or not ry:
        out.append(p1)
        return
    rx, ry = abs(rx), abs(ry)
    cos, sin = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cos * dx + sin * dy, -sin * dx + cos * dy
    grow = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if grow > 1:
        rx, ry = rx * math.sqrt(grow), ry * math.sqrt(grow)
    top = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    bottom = rx * rx * y1 * y1 + ry * ry * x1 * x1
    k = math.sqrt(max(0.0, top / bottom)) if bottom else 0.0
    if large == sweep:
        k = -k
    cx1, cy1 = k * rx * y1 / ry, -k * ry * x1 / rx
    cx, cy = cos * cx1 - sin * cy1 + (p0[0] + p1[0]) / 2, sin * cx1 + cos * cy1 + (p0[1] + p1[1]) / 2
    a0 = math.atan2((y1 - cy1) / ry, (x1 - cx1) / rx)
    a1 = math.atan2((-y1 - cy1) / ry, (-x1 - cx1) / rx)
    delta = a1 - a0
    if sweep and delta < 0:
        delta += 2 * math.pi
    elif not sweep and delta > 0:
        delta -= 2 * math.pi
    steps = max(4, min(96, math.ceil(abs(delta) * max(rx, ry) / CURVE_STEP)))
    for i in range(1, steps + 1):
        a = a0 + delta * i / steps
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cos * x - sin * y + cx, sin * x + cos * y + cy))


_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ARITY = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}


def subpaths(d):
    """A path's d into [(points, closed)]."""
    out, cur = [], []
    tokens, i = _TOKEN.findall(d or ""), 0
    x, y, cmd, ctrl = 0.0, 0.0, None, None

    def finish(close):
        nonlocal cur
        if len(cur) > 1:
            out.append((cur, close))
        cur = []

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if cur:
                    x, y = cur[0]
                finish(True)
                cmd = None
                continue
        if cmd is None:
            i += 1
            continue
        k, rel = cmd.lower(), cmd.islower()
        n = [float(v) for v in tokens[i:i + _ARITY[k]]]
        if len(n) < _ARITY[k]:
            break
        i += _ARITY[k]
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if k == "m":
            finish(False)
            x, y = n[0] + ox, n[1] + oy
            cur = [(x, y)]
            cmd = "l" if rel else "L"
            ctrl = None
            continue
        if not cur:
            cur = [(x, y)]
        if k in "lhv":
            if k == "l":
                x, y = n[0] + ox, n[1] + oy
            elif k == "h":
                x = n[0] + ox
            else:
                y = n[0] + oy
            cur.append((x, y))
            ctrl = None
        elif k in "cs":
            if k == "c":
                first = (n[0] + ox, n[1] + oy)
            else:
                first = (2 * x - ctrl[0], 2 * y - ctrl[1]) if ctrl and ctrl[2] == "c" else (x, y)
            rest = n[2:] if k == "c" else n
            second, end = (rest[0] + ox, rest[1] + oy), (rest[2] + ox, rest[3] + oy)
            _bezier([(x, y), first, second, end], cur)
            x, y = end
            ctrl = (second[0], second[1], "c")
        elif k in "qt":
            if k == "q":
                first = (n[0] + ox, n[1] + oy)
            else:
                first = (2 * x - ctrl[0], 2 * y - ctrl[1]) if ctrl and ctrl[2] == "q" else (x, y)
            end = (n[2] + ox, n[3] + oy) if k == "q" else (n[0] + ox, n[1] + oy)
            _bezier([(x, y), first, end], cur)
            x, y = end
            ctrl = (first[0], first[1], "q")
        else:
            end = (n[5] + ox, n[6] + oy)
            _arc((x, y), n[0], n[1], n[2], bool(n[3]), bool(n[4]), end, cur)
            x, y = end
            ctrl = None
    finish(False)
    return out


def _nums(attrs, *names):
    return [float(attrs.get(n, 0) or 0) for n in names]


def _ellipse(cx, cy, rx, ry):
    steps = max(16, min(96, math.ceil(2 * math.pi * max(rx, ry) / CURVE_STEP)))
    return [(cx + rx * math.cos(2 * math.pi * i / steps), cy + ry * math.sin(2 * math.pi * i / steps)) for i in range(steps)]


def _rect(x, y, w, h, rx, ry):
    if not rx and not ry:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    rx, ry = min(rx or ry, w / 2), min(ry or rx, h / 2)
    out = []
    for cx, cy, a0 in ((x + w - rx, y + ry, -90), (x + w - rx, y + h - ry, 0), (x + rx, y + h - ry, 90), (x + rx, y + ry, 180)):
        for i in range(7):
            a = math.radians(a0 + i * 15)
            out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def shape(tag, a):
    """A sanitized element into [(points, closed)], or [] for one that draws no line."""
    try:
        if tag == "path":
            return subpaths(a.get("d"))
        if tag == "line":
            x1, y1, x2, y2 = _nums(a, "x1", "y1", "x2", "y2")
            return [([(x1, y1), (x2, y2)], False)]
        if tag in ("polyline", "polygon"):
            v = [float(n) for n in re.split(r"[\s,]+", a.get("points", "").strip()) if n]
            return [(list(zip(v[::2], v[1::2])), tag == "polygon")]
        if tag == "rect":
            x, y, w, h = _nums(a, "x", "y", "width", "height")
            return [(_rect(x, y, w, h, *_nums(a, "rx", "ry")), True)]
        if tag == "circle":
            cx, cy, r = _nums(a, "cx", "cy", "r")
            return [(_ellipse(cx, cy, r, r), True)]
        if tag == "ellipse":
            cx, cy, rx, ry = _nums(a, "cx", "cy", "rx", "ry")
            return [(_ellipse(cx, cy, rx, ry), True)]
    except (ValueError, IndexError):
        return []
    return []


def _width(attrs):
    try:
        return float(attrs.get("stroke-width", 4))
    except ValueError:
        return 4.0


def flatten(tree):
    """Sanitized tree -> {"strokes": [...], "dots": [[x, y]...]}: paint order, then stable-sorted by delay."""
    found, dots = [], []

    def walk(nodes, matrix, delay, inherited):
        for node in nodes:
            own = node["attrs"]
            style = {**inherited, **{k: own[k] for k in ("fill", "stroke", "stroke-width") if k in own}}
            m = transform(own.get("transform"), matrix)
            d = delay + node["delay"]
            if node["tag"] == "g":
                walk(node["children"], m, d, style)
                continue
            rings = shape(node["tag"], own)
            if not rings:
                continue  # <text> stays in the DOM
            if style.get("fill") == "ACCENT" or style.get("stroke") == "ACCENT":
                pts = [_apply(m, p) for p in rings[0][0]]
                dots.append([round(sum(p[0] for p in pts) / len(pts), 1), round(sum(p[1] for p in pts) / len(pts), 1)])
                continue
            scale = math.sqrt(abs(m[0] * m[3] - m[1] * m[2])) or 1.0
            element = len(found)
            for points, closed in rings:
                pts = [_apply(m, p) for p in points]
                found.append({"e": element, "paint": len(found), "d": round(d, 2), "line": style.get("stroke", "none"),
                              "fill": style.get("fill", "none"), "w": round(_width(style) * scale, 1), "closed": bool(closed),
                              "pts": [round(v, 1) for p in pts for v in p]})
                if node["tag"] == "rect" and m[1] == 0 and m[2] == 0:  # a draughtsman rules a box square
                    x, y, w, h = _nums(own, "x", "y", "width", "height")
                    a, b = _apply(m, (x, y)), _apply(m, (x + w, y + h))
                    found[-1]["box"] = [round(v, 1) for v in (*a, *b)]

    walk(tree, (1, 0, 0, 1, 0, 0), 0.0, {})
    return {"strokes": sorted(found, key=lambda s: s["d"]), "dots": dots}  # sorted() keeps paint order inside a delay


def bake(svg):
    tree, problems = art.sanitize(svg)
    drawing = flatten(tree)
    drawing["problems"] = problems
    return drawing


def library():
    out = {}
    for f in sorted((ROOT / "assets" / "drawings").glob("*.json")):
        seed = json.loads(f.read_text(encoding="utf-8"))
        d = bake(seed["svg"])
        if d.pop("problems"):
            raise SystemExit(f"{f.name}: does not pass art.sanitize")
        out[f.stem] = {"about": seed.get("about", ""), **d}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--svg", help="one drawing's SVG fragment")
    p.add_argument("--spec", help="the spec to write the drawing into (its other keys stay)")
    p.add_argument("--check", action="store_true", help="fail if drawings.json is stale")
    a = p.parse_args()
    if a.svg:
        d = bake(pathlib.Path(a.svg).read_text(encoding="utf-8"))
        problems = d.pop("problems")
        if not d["strokes"]:
            raise SystemExit(f"the drawing has no strokes: {problems}")
        target = pathlib.Path(a.spec or "spec.json")
        spec = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
        spec["strokes"] = d
        target.write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
        print(target)
        return
    text = json.dumps(library(), ensure_ascii=False, separators=(",", ":")) + "\n"
    if a.check:
        raise SystemExit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == text else "drawings.json is stale")
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(OUT, len(text))


if __name__ == "__main__":
    main()
