"""The one-take camera (ROADMAP D5): the scenes sit on one 2D path and the film reads as one continuous move.

    "transition": "one-take"     in a format, or picked by variety for a film of a program (never for `news`)

The scenes are laid out here, in code, from their count and their shapes (their types), seeded per video, so two films
take two routes and one story always takes its own again. The picture is remotion/src/onetake.tsx; it reads
props["camera"], which attach() writes, and does nothing but arithmetic on the frame.

What the camera does, and what it never does:
    - it moves only in a cut window of CUT frames that starts at the new scene's first frame. Outside the window the
      camera rests on a scene: offset 0, zoom exactly 1, so text never moves while it is read, and the layout probe
      (a scene's settled frame is its first + 12) sees what a plain cut shows;
    - zoom is a bell over the window, 1 + z * sin(pi * u), |z| at most ZOOM_MAX, and never above ZOOM_CAP (1.15);
    - chrome, source, time, captions and the safe zone are not in the camera: only the scene band rides it;
    - every position is a pure function of the frame (position(), mirrored in onetake.tsx);
    - the accent is only the dot that runs the thread between the two scenes.

The path. The world is a grid of cells the size of the scene band plus a gutter; scene i sits in a cell, the next one
in a neighbouring cell (eight compass directions). The direction of each step comes from, in order: no turn of more
than 90 degrees from the step before (the thread stays one gesture), a bias from the shape of the scene it arrives at
(a list or steps come down the page, a chart or a map comes across it), a box of BOX cells round the first scene (the
film doesn't wander off), no cell used twice (so the route never crosses itself), and a seeded jitter that breaks the
rest of the ties; a step may not lead into a cell with no way on (a one-step look-ahead). When no step meets all
of it the rules are relaxed, the look-ahead first, then the turn, then the box and the used cells.
"""
import math
import zlib

from tt_shorts import probe

W, H = probe.C["W"], probe.C["H"]
BAND = probe.C["SCENE_BOTTOM"] - probe.C["SCENE_TOP"]
CUT = 12  # frames of a cut window (0.4 s at 30 fps): the scene's settled frame, 12 frames in, is at rest
GUTTER = 100  # px between two scenes' cells
ZOOM_CAP = 1.15  # the camera never zooms in past this (the ROADMAP's hard-news cap)
ZOOM_MAX = 0.10  # a seeded move's depth is 0.04..ZOOM_MAX, a pull-back or a push-in
ZOOM_MIN = 0.04
BOX = 3  # cells each way from the first scene
CELL = (W + GUTTER, BAND + GUTTER)
DIRECTIONS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
# a scene's shape decides which way it likes to be reached: v: down the page (rows of things read in order),
# h: across it (a comparison, a series, a place); the rest take whatever the seed says
SHAPE = {
    "steps": "v", "timeline": "v", "checklist": "v", "ranking": "v", "rail": "v", "points": "v", "glossary": "v",
    "sources": "v", "calendar": "v",
    "bars": "h", "compare": "h", "versus": "h", "pair": "h", "trend": "h", "where": "h", "route": "h", "change": "h",
    "budget": "h", "impact": "h", "countdown": "h", "stat": "h",
}


def _crc(*parts):
    return zlib.crc32("|".join(str(p) for p in parts).encode())


def _score(d, scene_type, seed, i):
    """How much a step likes this direction (lower is better): the shape's axis first, then the seed."""
    want = SHAPE.get(scene_type)
    miss = 0.0
    if want == "v":
        miss = 0.0 if d[1] != 0 else 1.0
        miss += 0.25 if d[0] != 0 else 0.0  # a diagonal is a little worse than straight down
    elif want == "h":
        miss = 0.0 if d[0] != 0 else 1.0
        miss += 0.25 if d[1] != 0 else 0.0
    return miss + (_crc(seed, i, d) % 1000) / 1000 * 0.9


def _turn_ok(prev, d):
    """No turn of more than 90 degrees from the step before: the dot product is not negative."""
    return prev is None or prev[0] * d[0] + prev[1] * d[1] >= 0


def route(types, seed):
    """Scene types, a seed -> the cell of each scene, [(cx, cy)] (the first is (0, 0)). Pure."""
    cells = [(0, 0)]
    prev = None
    for i in range(1, len(types)):
        here = cells[-1]
        ranked = sorted(DIRECTIONS, key=lambda d: _score(d, types[i], seed, i))
        ahead = [(d, (here[0] + d[0], here[1] + d[1])) for d in ranked]

        def inside(c):
            return abs(c[0]) <= BOX and abs(c[1]) <= BOX

        def alive(d, c):  # the cell has a way on that turns no more than 90 degrees (a walk must not trap itself)
            return i == len(types) - 1 or any(
                _turn_ok(d, e) and inside((c[0] + e[0], c[1] + e[1])) and (c[0] + e[0], c[1] + e[1]) not in cells + [c]
                for e in DIRECTIONS)
        tiers = (
            lambda d, c: _turn_ok(prev, d) and inside(c) and c not in cells and alive(d, c),
            lambda d, c: _turn_ok(prev, d) and inside(c) and c not in cells,
            lambda d, c: inside(c) and c not in cells,
            lambda d, c: _turn_ok(prev, d) and inside(c),
            lambda d, c: inside(c),
        )
        for ok in tiers:
            pick = next(((d, c) for d, c in ahead if ok(d, c)), None)
            if pick:
                break
        d, c = pick
        cells.append(c)
        prev = d
    return cells


def layout(types, seed):
    """The camera of one video: {cut, zoomCap, points [[x, y] px per scene], cuts [{into, from, to, c1, c2, zoom}]}.
    types: the shown scenes' types in order. seed: any string or number (the story's id with its brand).
    Each cut's thread is a cubic bezier between the two scenes' centres, bent sideways by a seeded amount, the bend
    alternating its side so a run of cuts weaves; zoom is that cut's seeded depth (negative: a pull-back)."""
    cells = route(list(types), seed)
    pts = [[c[0] * CELL[0], c[1] * CELL[1]] for c in cells]
    cuts = []
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / n, dx / n  # the sideways unit
        bend = n * (0.18 + 0.22 * (_crc(seed, "bend", i) % 1000) / 1000) * (1 if i % 2 else -1)
        z = ZOOM_MIN + (ZOOM_MAX - ZOOM_MIN) * (_crc(seed, "zoom", i) % 1000) / 1000
        z = z if _crc(seed, "sign", i) % 2 else -z
        cuts.append({"into": i, "from": a, "to": b,
                     "c1": [round(a[0] + dx * 0.33 + nx * bend, 1), round(a[1] + dy * 0.33 + ny * bend, 1)],
                     "c2": [round(a[0] + dx * 0.67 - nx * bend, 1), round(a[1] + dy * 0.67 - ny * bend, 1)],
                     "zoom": round(max(-(ZOOM_CAP - 1), min(ZOOM_CAP - 1, z)), 3)})
    return {"cut": CUT, "zoomCap": ZOOM_CAP, "points": pts, "cuts": cuts}


def attach(props, seed):
    """Put the camera into one video's props (props.build calls it when the transition is one-take): the layout of its
    shown scenes. The scenes' own frames are not changed: the old scene is kept alive CUT frames past its end."""
    props["camera"] = layout([s["type"] for s in props["scenes"]], seed)
    return props["camera"]


# ---------------------------------------------------------------- the camera as a function of the frame (pure)


def ease(u):
    """Cubic ease in and out, exactly 0 at 0 and exactly 1 at 1."""
    u = min(1.0, max(0.0, u))
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def position(cam, froms, frame):
    """The camera at an absolute frame -> (x, y, zoom). froms: each scene's first frame. At rest it is exactly a
    scene's point with zoom 1; only inside a cut window (CUT frames from the new scene's first) does it move. The
    same arithmetic as remotion/src/onetake.tsx camera()."""
    k = 0
    for i in range(1, len(froms)):
        if frame >= froms[i]:
            k = i
    if k == 0:
        return float(cam["points"][0][0]), float(cam["points"][0][1]), 1.0
    c = cam["cuts"][k - 1]
    u = (frame - froms[k]) / cam["cut"]
    if u >= 1:
        return float(c["to"][0]), float(c["to"][1]), 1.0
    e = ease(u)
    x = c["from"][0] + (c["to"][0] - c["from"][0]) * e
    y = c["from"][1] + (c["to"][1] - c["from"][1]) * e
    return x, y, 1 + c["zoom"] * math.sin(math.pi * u)


def moving(froms, frame, cut=CUT):
    """Is the frame inside a cut window?"""
    return any(f <= frame < f + cut for f in froms[1:])


def direction(cam, i):
    """The unit-ish direction of the camera's move into scene i (the sign of each axis), for the motion rules."""
    c = cam["cuts"][i - 1]
    dx, dy = c["to"][0] - c["from"][0], c["to"][1] - c["from"][1]
    return ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
