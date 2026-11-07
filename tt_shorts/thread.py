"""The film's thread: one object that carries the story's idea from scene to scene and changes state on the way.

A film's idea (concept.py) used to stay on paper while its scenes looked like the kit. Here the idea's `object` gets a
body: code takes a drawing, gives each scene a seat for it, and a layer above the scenes (remotion/src/thread.tsx) draws
it, gliding from seat to seat across every cut. The writer picks nothing about any of that.

    drawing     the story's own checked draw scene, else the concept's named seed (`drawing`), else the library's
                drawings of the object's motif (drawings.candidates), one per story. A thread shows no words: every
                label of a drawing is removed, so an object can carry no fact
    outline     the drawing's silhouette, traced from its line art (no drawing needs authoring, the writer's works too)
    state       what the concept's `verb` does to the object (VERBS -> STATES): drain, fill, break, grow, shrink. A verb
                outside the table gets no state: the picture must not assert what the idea didn't say. It warns
    seats       one rectangle per scene in frame px, from the scene's type and its text load (content()), never
                measured in the render tabs (the captions' rule): the scene keeps it free (Frame, `reserve`) and
                the layout probe checks text against it (probe.rules, rule "seat")
    t           the state's progress per scene: the `state` scene does the whole change, else it moves scene by scene

Refused for what the news rules protect: no thread without a program's idea step (news has none), none for the crime
family, for a story about deaths (news_check.no_pictograms) or for the incidents' categories. `plan` is pure: same story,
same thread. A film without one is the kit's film, with a warning when a concept couldn't get its object: the thread
never fails a video.

    python -m tt_shorts.engine thread stories/veasy-thread.json      # the plan, free: drawing, state, scenes, seats
"""
import functools
import math
import re
import zlib

from tt_shorts import art, concept, drawings, icons, news_check, programs

MIN_SCENES = 3  # the object is in at least this many scenes, or there is no thread
MIN_AREA = 0.04  # of the drawing's box: under this a silhouette is a few lines, not a body
ASPECT = 952 / 640
CELL = 4  # px of the silhouette's grid
SEAT_MIN, SEAT_MAX = 210, 560  # px high
HERO_MAX = 700
GAP = 36  # between the scene's text and its seat
RIGHT = 940  # the drawing stays left of the like/share rail
SCENE_TOP, SCENE_BOTTOM = 248, 1380
BOXES = {"editorial": (64, 1016, 1380), "kinetic": (64, 1016, 1380), "cards": (96, 984, 1252)}  # left, right, bottom
CARD_TOP = 48  # the cards look's scene box starts this far below SCENE_TOP
STATES = ("drain", "fill", "break", "grow", "shrink")
VERBS = {
    "drain": ("drain", "drains", "empties", "empty", "emptied", "runs out", "runs-out", "dries", "dry", "leaks", "leak",
              "falls", "fall", "drops", "drop", "declines", "decline", "decreases", "melts", "stops", "stop"),
    "fill": ("fill", "fills", "filled", "rises", "rise", "piles", "pile", "accumulates", "accumulate", "pours", "pour",
             "floods-in", "loads", "increases", "climbs", "climb", "gathers"),
    "break": ("break", "breaks", "broken", "cracks", "crack", "splits", "split", "divides", "divide", "shatters",
              "separates", "separate", "fractures", "tears", "tear", "cuts"),
    "grow": ("grow", "grows", "swells", "swell", "expands", "expand", "doubles", "double", "widens", "widen", "enlarges",
             "multiplies", "multiply", "stretches", "stretch"),
    "shrink": ("shrink", "shrinks", "narrows", "narrow", "contracts", "contract", "reduces", "reduce", "halves", "halve",
               "tightens", "tighten", "squeezes", "squeeze", "compresses"),
}
ABOUT = {"drain": "full to empty: the level inside the object's silhouette falls",
         "fill": "empty to full: the level inside the object's silhouette rises",
         "break": "whole to broken: a crack runs through, the halves part",
         "grow": "small to huge", "shrink": "huge to small"}
NO_SEAT = ("end", "sources", "where", "chapter")  # the pack's cards, and the map, which is the scene's own picture
HERO = ("state",)  # the object is what the scene shows
OWN = ("draw",)  # the scene draws the object itself
# the shape a scene opens on, for the match cut: the form of what it shows
FORMS = {"circle": ("stat", "share", "countdown", "impact", "quote"),
         "bars": ("bars", "ranking", "budget", "compare", "versus", "change"),
         "line": ("trend", "timeline", "rail", "route", "calendar", "steps")}
INCIDENTS = ("crime", "incident", "incidents", "accident", "accidents", "security")  # categories, as stories file them
LINE_H = 1.2


class ThreadError(ValueError):
    pass


def verb_state(verb):
    """A concept's verb (free English) -> one of STATES, or None."""
    v = str(verb or "").strip().lower()
    return next((k for k, words in VERBS.items() if v in words), None)


def eligible(story):
    """(True, None), or (False, why): what the news rules protect never gets a thread."""
    from tt_shorts import brand, meta
    c = story.get("concept")
    if not c or not c.get("object"):
        return False, None  # the kit's film: nothing to say
    if programs.name_of(story) == programs.DEFAULT:
        return False, "thread: news has no idea step"
    try:
        if not programs.of(story).get("concept"):
            return False, f"thread: program {programs.name_of(story)!r} has no idea step"
    except programs.ProgramError as e:
        return False, f"thread: {e}"
    category = str(story.get("category") or "")
    if meta.family(category, brand.of(story)) == "crime" or category in INCIDENTS:
        return False, "thread: never for crime or incidents"
    if news_check.no_pictograms(story):
        return False, "thread: never for a story about deaths"
    return True, None


# ---------------------------------------------------------------- the silhouette


def _matrix(transform):
    """An SVG transform (art.TRANSFORM's three functions) -> (a, b, c, d, e, f)."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, body in re.findall(r"(translate|rotate|scale)\(([^)]*)\)", transform or ""):
        v = [float(x) for x in re.split(r"[\s,]+", body.strip()) if x]
        if name == "translate":
            n = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            n = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        else:
            a = math.radians(v[0])
            cx, cy = (v[1], v[2]) if len(v) > 2 else (0, 0)
            c, s = math.cos(a), math.sin(a)
            n = (c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy)
        m = (m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
             m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5])
    return m


def _apply(m, p):
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


def _compose(a, b):
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
            a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def _f(attrs, k):
    try:
        return float(attrs.get(k) or 0)
    except ValueError:
        return 0.0


def _shape_points(tag, attrs):
    """An element's outline as points, for the raster."""
    if tag == "path":
        return art._path_points(attrs.get("d", ""))
    if tag == "line":
        return [(_f(attrs, "x1"), _f(attrs, "y1")), (_f(attrs, "x2"), _f(attrs, "y2"))]
    if tag in ("polyline", "polygon"):
        v = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", attrs.get("points", ""))]
        pts = list(zip(v[::2], v[1::2]))
        return pts + pts[:1] if tag == "polygon" else pts
    if tag == "rect":
        x, y, w, h = _f(attrs, "x"), _f(attrs, "y"), _f(attrs, "width"), _f(attrs, "height")
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    if tag in ("circle", "ellipse"):
        cx, cy = _f(attrs, "cx"), _f(attrs, "cy")
        rx = _f(attrs, "r") or _f(attrs, "rx")
        ry = _f(attrs, "r") or _f(attrs, "ry")
        return [(cx + rx * math.cos(i * math.pi / 8), cy + ry * math.sin(i * math.pi / 8)) for i in range(17)]
    return []


def _strokes(tree, m=(1, 0, 0, 1, 0, 0)):
    for n in tree:
        here = _compose(m, _matrix(n["attrs"].get("transform")))
        if n["tag"] != "text":
            pts = _shape_points(n["tag"], n["attrs"])
            if len(pts) > 1:
                yield [_apply(here, p) for p in pts]
        yield from _strokes(n.get("children") or [], here)


def _simplify(pts, tol):
    """Ramer-Douglas-Peucker on an open chain of points."""
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x0, y0), (x1, y1) = pts[a], pts[b]
        dx, dy = x1 - x0, y1 - y0
        norm = math.hypot(dx, dy) or 1.0
        best, at = 0.0, None
        for i in range(a + 1, b):
            d = abs(dy * (pts[i][0] - x0) - dx * (pts[i][1] - y0)) / norm
            if d > best:
                best, at = d, i
        if at is not None and best > tol:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(pts, keep) if k]


def _trace(mask):
    """The outer boundary of one filled blob of a boolean grid -> [(row, col)] of grid corners, clockwise."""
    edges = {}
    rows, cols = mask.shape
    for r in range(rows):
        for c in range(cols):
            if not mask[r, c]:
                continue
            if r == 0 or not mask[r - 1, c]:
                edges.setdefault((r, c), []).append((r, c + 1))
            if c == cols - 1 or not mask[r, c + 1]:
                edges.setdefault((r, c + 1), []).append((r + 1, c + 1))
            if r == rows - 1 or not mask[r + 1, c]:
                edges.setdefault((r + 1, c + 1), []).append((r + 1, c))
            if c == 0 or not mask[r, c - 1]:
                edges.setdefault((r + 1, c), []).append((r, c))
    if not edges:
        return []
    start = min(edges)
    out, at = [start], edges[start].pop()
    while at != start:
        out.append(at)
        nexts = edges.get(at)
        if not nexts:
            break
        at = nexts.pop()
    return out


@functools.lru_cache(maxsize=128)
def outline(svg):
    """A drawing's silhouette -> {"path": "M..Z", "box": [x0, y0, x1, y1], "area": share of the box}, or None. Its
    strokes on a CELL px grid, closed by a little, holes filled; the blobs' outer edges, simplified."""
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage

    tree, problems = art.sanitize(svg)
    lines = list(_strokes(tree)) if not problems or tree else []
    if not lines:
        return None
    w, h = art.VIEW[0] // CELL + 8, art.VIEW[1] // CELL + 8  # a margin: a drawing may reach a little past its canvas
    img = Image.new("1", (w, h), 0)
    pen = ImageDraw.Draw(img)
    for pts in lines:
        pen.line([(x / CELL + 4, y / CELL + 4) for x, y in pts], fill=1, width=2)
    grid = np.array(img, dtype=bool)
    near = np.ones((3, 3), dtype=bool)
    closed = ndimage.binary_dilation(grid, near, iterations=3)
    filled = ndimage.binary_fill_holes(closed)
    filled = ndimage.binary_erosion(filled, near, iterations=2)
    labels, n = ndimage.label(filled)
    parts, cells = [], 0
    for k in range(1, n + 1):
        blob = labels == k
        size = int(blob.sum())
        if size < 80:  # a stray line
            continue
        chain = _trace(blob)
        if len(chain) < 8:
            continue
        pts = [((c - 4) * CELL, (r - 4) * CELL) for r, c in chain]
        far = max(range(len(pts)), key=lambda i: math.dist(pts[0], pts[i]))  # a closed chain, cut in two
        parts.append(_simplify(pts[:far + 1], CELL * 0.75)[:-1] + _simplify(pts[far:] + pts[:1], CELL * 0.75)[:-1])
        cells += size
    if not parts:
        return None
    xs = [p[0] for part in parts for p in part]
    ys = [p[1] for part in parts for p in part]
    box = [min(xs), min(ys), max(xs), max(ys)]
    area = cells * CELL * CELL / max(1.0, (box[2] - box[0]) * (box[3] - box[1]))
    d = lambda part: "M" + " L".join(f"{x:g} {y:g}" for x, y in part) + " Z"  # noqa: E731
    main = max(parts, key=lambda part: (max(p[0] for p in part) - min(p[0] for p in part)) *
               (max(p[1] for p in part) - min(p[1] for p in part)))
    return {"path": " ".join(map(d, parts)), "main": d(main), "box": box, "area": round(area, 3)}


def _body(box, level, wave, seed):
    """The level inside the silhouette: everything under a wavy surface at `level` (0 the box's foot, 1 its top)."""
    x0, y0, x1, y1 = box
    y = y1 - (y1 - y0) * level
    n = 8
    step = (x1 - x0 + 40) / n
    pts = [(x0 - 20 + i * step, y + (wave if (i + seed) % 2 else -wave)) for i in range(n + 1)]
    top = " ".join(f"Q{p[0] + step / 2:.1f} {p[1]:.1f} {p[0] + step:.1f} {pts[i + 1][1]:.1f}"
                   for i, p in enumerate(pts[:-1]))
    return (f"M{pts[0][0]:.1f} {pts[0][1]:.1f} {top} L{x1 + 20:.1f} {y1 + 20:.1f} L{x0 - 20:.1f} {y1 + 20:.1f} Z")


def _crack(box, seed):
    """A jagged line down the object and its straight start -> (the straight path, the jagged path, the two sides)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    n = 7
    mid = x0 + w * (0.42 + 0.16 * ((seed >> 3) % 8) / 7)
    pts = []
    for i in range(n + 1):
        swing = 0 if i in (0, n) else (((seed >> (i * 2)) & 3) + 1) * w * 0.022 * (1 if i % 2 else -1)
        pts.append((mid + swing, y0 - 8 + (h + 16) * i / n))
    jag = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    straight = "M" + " L".join(f"{mid:.1f} {y:.1f}" for _, y in pts)
    left = (f"M{x0 - 40:.1f} {y0 - 40:.1f} L{pts[0][0]:.1f} {y0 - 40:.1f} L" +
            " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) +
            f" L{pts[-1][0]:.1f} {y1 + 40:.1f} L{x0 - 40:.1f} {y1 + 40:.1f} Z")
    right = (f"M{x1 + 40:.1f} {y0 - 40:.1f} L{pts[0][0]:.1f} {y0 - 40:.1f} L" +
             " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) +
             f" L{pts[-1][0]:.1f} {y1 + 40:.1f} L{x1 + 40:.1f} {y1 + 40:.1f} Z")
    return straight, jag, left, right


def _circle(box):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    r = min(box[2] - box[0], box[3] - box[1]) * 0.44
    return f"M{cx - r:.1f} {cy:.1f} A{r:.1f} {r:.1f} 0 1 1 {cx + r:.1f} {cy:.1f} A{r:.1f} {r:.1f} 0 1 1 {cx - r:.1f} {cy:.1f} Z"


def _bars(box):
    x0, y0, x1, y1 = box
    w = (x1 - x0) / 7
    out = []
    for i, k in enumerate((0.45, 1.0, 0.7)):
        x = x0 + w * (1 + 2 * i)
        top = y1 - (y1 - y0) * k
        out.append(f"M{x:.1f} {y1:.1f} L{x:.1f} {top:.1f} L{x + w:.1f} {top:.1f} L{x + w:.1f} {y1:.1f} Z")
    return " ".join(out)


def _line(box):
    x0, y0, x1, y1 = box
    y = (y0 + y1) / 2
    h = (y1 - y0) * 0.05
    return f"M{x0:.1f} {y - h:.1f} L{x1:.1f} {y - h:.1f} L{x1:.1f} {y + h:.1f} L{x0:.1f} {y + h:.1f} Z"


def forms(box):
    """The shapes a match cut can land on, in the drawing's own box."""
    return {"circle": _circle(box), "bars": _bars(box), "line": _line(box)}


def form_of(scene_type):
    return next((k for k, types in FORMS.items() if scene_type in types), None)


# ---------------------------------------------------------------- the drawing


def _seed(name):
    from tt_shorts import drawings as d
    return next((s for s in d.seeds() if s["name"] == name), None)


def _strip(svg):
    """A drawing without its words: the object carries no fact."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(f"<g>{svg}</g>")

    def strip(el):
        for ch in list(el):
            if ch.tag.split("}")[-1] == "text":
                el.remove(ch)
            else:
                strip(ch)

    strip(root)
    return (root.text or "") + "".join(ET.tostring(ch, encoding="unicode") for ch in root)


def drawing(story):
    """The object's drawing -> {"svg", "name", "source"}, or None."""
    own = next((s.get("svg") for s in story.get("scenes") or [] if s.get("type") == "draw" and drawings.passes(s.get("svg"))),
               None)
    if own:
        return {"svg": _strip(own), "name": "the story's own", "source": "story"}
    c = story.get("concept") or {}
    named = _seed(c.get("drawing")) if c.get("drawing") else None
    if named:
        return {"svg": _strip(named["svg"]), "name": named["name"], "source": "seed"}
    motifs = [icons.resolve(c.get("object"))] + [icons.resolve(story.get("motif"))] + \
             [m for m in icons.find(str(c.get("idea") or ""))]
    for motif in filter(None, motifs):
        pool = drawings.candidates(motif)
        if pool:
            pick = pool[zlib.crc32(f"{story.get('id')}|{c.get('object')}".encode()) % len(pool)]
            return {"svg": _strip(pick["svg"]), "name": pick.get("name") or pick["id"], "source": pick["source"]}
    return None


# ---------------------------------------------------------------- the seats


def _items(s):
    return len(s.get("items") or []) or 3


def content(s, look="editorial"):
    """How high a scene's own content stands, in px. Calibrated on the layout probe's boxes in every look
    (docs/research/thread-object-result.md); a seat is what is left, and the probe checks the result."""
    t = s.get("type")
    head = 76 if s.get("kicker") else 0
    if s.get("headline"):
        head += 92 * (1 + (len(s["headline"]) > 22))
    if t == "hook":
        lines = len(s.get("lines") or []) or 2
        return 124 + 190 * lines
    if t == "stat":
        return head + 300 + (90 if s.get("label") else 0)
    if t == "state":
        return head + 150
    if t == "quote":
        return head + 120 + 78 * max(2, len(s.get("text") or "") // 26 + 1)
    if t in ("points", "steps", "checklist", "glossary"):
        return head + 150 * _items(s)
    if t in ("pair", "versus", "compare"):
        return head + 520
    if t in ("bars", "ranking", "budget", "impact"):
        return head + 90 + 100 * _items(s)
    if t in ("trend", "timeline", "rail", "route", "calendar", "countdown", "change", "share"):
        return head + 460
    if t in ("who", "link", "agree"):
        return head + 170 * _items(s)
    if t == "sign":
        return head + 520
    return 10000  # a type nobody calibrated keeps its room


def _align(i, seed):
    return ("center", "left", "right", "center")[(seed + i) % 4]


def seat(s, i, look, seed):
    """One scene's seat -> {x, y, w, h, reserve} in frame px, or None. The object stands on the scene's foot; reserve is
    the room the scene leaves free for it, measured from the bottom of its box."""
    t = s.get("type")
    if t in NO_SEAT or s.get("media") or t in OWN:
        return None
    left, right, bottom = BOXES[look]
    top = SCENE_TOP + (CARD_TOP if look == "cards" else 0)
    room = bottom - top - content(s, look) - GAP
    h = min(HERO_MAX if t in HERO else SEAT_MAX, room)
    if h < SEAT_MIN:
        return None
    span = min(right, RIGHT) - left
    w = min(span, h * ASPECT)
    h = w / ASPECT
    side = "center" if t in HERO else _align(i, seed)
    x = {"left": left, "center": left + (span - w) / 2, "right": left + span - w}[side]
    y = bottom - h
    reserve = bottom - y + GAP / 2
    return {"x": round(x), "y": round(y), "w": round(w), "h": round(h), "reserve": round(reserve)}


# ---------------------------------------------------------------- the plan


def _steps(scenes, carried):
    """The state's progress per carrying scene: [(from, to)], never back. A `state` scene does the whole change; without
    one it moves scene by scene."""
    pivot = next((i for i in carried if scenes[i].get("type") in HERO), None)
    out = {}
    if pivot is not None:
        for i in carried:
            out[i] = (0.0, 0.0) if i < pivot else (1.0, 1.0) if i > pivot else (0.0, 1.0)
        return out
    n = max(1, len(carried) - 1)
    for k, i in enumerate(carried):
        out[i] = (round(max(0, k - 1) / n, 3), round(k / n, 3))
    return out


def plan(story, scenes=None, look="editorial"):
    """The story's thread -> ({object, verb, state, drawing, source, seed, svg, outline, box, area, forms, surface,
    crack, seats: {scene index: seat with from, to, role, form}, warnings}, None), or (None, warning or None). scenes:
    the scenes shown (default the story's)."""
    ok, why = eligible(story)
    if not ok:
        return None, why
    c = story["concept"]
    found = drawing(story)
    if not found:
        return None, f"thread: no drawing of „{c['object']}“ in the library: the film goes out without its object"
    shape = outline(found["svg"])
    if not shape or shape["area"] < MIN_AREA:
        return None, f"thread: {found['name']} has no body to carry a state"
    scenes = story.get("scenes") if scenes is None else scenes
    seed = zlib.crc32(f"{story.get('id')}|{c['object']}".encode())
    seats = {}
    for i, s in enumerate(scenes or []):
        one = seat(s, i, look, seed)
        if one:
            seats[i] = {**one, "role": "hero" if s.get("type") in HERO else "seat", "form": form_of(s.get("type"))}
    own = [i for i, s in enumerate(scenes or []) if s.get("type") in OWN]
    if len(seats) + len(own) < MIN_SCENES:
        return None, (f"thread: only {len(seats) + len(own)} scene(s) have room for „{c['object']}“ (at least "
                      f"{MIN_SCENES}): the film goes out without its object")
    state = verb_state(c.get("verb"))
    warnings = []
    if not state:
        warnings.append(f"thread: no state for the verb {c.get('verb')!r}: the object stays as it is")
    steps = _steps(scenes, sorted(set(seats) | set(own)))
    for i, (a, b) in steps.items():
        if i in seats:
            seats[i].update({"from": a, "to": b})
    box = shape["box"]
    out = {"object": c["object"], "verb": c.get("verb"), "state": state, "drawing": found["name"], "source": found["source"],
           "seed": seed % 100000, "svg": found["svg"], "outline": shape["path"], "main": shape["main"], "box": box, "area": shape["area"],
           "forms": forms(box), "seats": seats, "own": {i: {"role": "own", "from": steps[i][0], "to": steps[i][1]} for i in own},
           "warnings": warnings}
    if state in ("drain", "fill"):
        full, empty = _body(box, 1.04, 3, seed), _body(box, 0.1, 16, seed)
        out["surface"] = [full, empty] if state == "drain" else [empty, full]
    if state == "break":
        out["crack"] = dict(zip(("straight", "jag", "left", "right"), _crack(box, seed)))
    return out, None


def for_props(t):
    """What the composition needs of a plan: a safe tree instead of the SVG, no seats (they sit on the scenes)."""
    if not t:
        return None
    return {**{k: t[k] for k in ("object", "state", "seed", "outline", "main", "box", "forms") if k in t},
            **{k: t[k] for k in ("surface", "crack") if k in t}, "art": art.sanitize(t["svg"])[0]}


def attach(props, story):
    """Put a story's thread on its Remotion props: props["thread"] and each carrying scene's `thread` -> [warnings]."""
    t, warning = plan(story, props["scenes"], props["variant"])
    props["thread"] = for_props(t)
    if not t:
        return [warning] if warning else []
    for i, one in t["seats"].items():
        props["scenes"][i]["thread"] = one
    for i, one in t["own"].items():
        props["scenes"][i]["thread"] = one
    return list(t["warnings"])


def has(story):
    """Can this story get a thread at all? Cheap: the variety picks ask before any voice is made."""
    return eligible(story)[0] and drawing(story) is not None


def text_over(thread_seats, boxes):
    """The texts over a seat: seats {scene index: seat}, boxes [(scene index, [x, y, w, h], text)] -> [(index, text)]."""
    out = []
    for i, box, text in boxes:
        s = thread_seats.get(i)
        if not s:
            continue
        x, y, w, h = box
        if x < s["x"] + s["w"] and x + w > s["x"] and y < s["y"] + s["h"] and y + h > s["y"]:
            out.append((i, text))
    return out


def story_problems(story):
    """A `state` scene needs an object to change: a story without a thread says so in `check`."""
    if not any(s.get("type") in HERO for s in story.get("scenes") or []):
        return []
    if programs.name_of(story) == programs.DEFAULT:
        return []  # N1 refuses the type itself
    ok, why = eligible(story)
    if not story.get("concept"):
        return ["state: no idea, no object: a state scene needs the story's `concept`"]
    if not ok:
        return [why] if why else []
    return [] if drawing(story) else [f"state: no drawing of „{story['concept']['object']}“ in the library"]


def options():
    """engine options: what a film's thread can do."""
    return {"about": "a film with a chosen idea (concept.py) gets its object as a through-line: code draws it across "
                     "at least 3 scenes, moves it over the cuts and changes its state. Never for news, crime, incidents "
                     "or deaths",
            "states": ABOUT, "verbs": {k: list(v) for k, v in VERBS.items()}, "min_scenes": MIN_SCENES,
            "transitions": {"match": "the object's shape becomes the shape the next scene opens on",
                            "object": "the object crosses the frame and carries the cut"},
            "devices": sorted(k for k, v in concept.devices().items() if "state" in v["scenes"])}


def summary(story, look=None):
    """`engine thread`: the plan, without the drawing's body."""
    from tt_shorts import brand, meta
    look = look or meta.variant_for(story.get("category", ""), brand.of(story))
    t, why = plan(story, look=look)
    if not t:
        return {"thread": None, "warning": why}
    scenes = story.get("scenes") or []
    carried = sorted(set(t["seats"]) | set(t["own"]))
    return {"thread": {k: t[k] for k in ("object", "verb", "state", "drawing", "source", "area")}, "look": look,
            "scenes": [{"scene": i, "type": scenes[i].get("type"), **t["seats"].get(i, {"role": "own"})} for i in carried],
            "changes_state": bool(t["state"]), "warnings": t["warnings"]}
