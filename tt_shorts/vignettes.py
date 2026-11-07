"""Vignettes: the film's drawings of what it is about, one to three, each in the room a scene's text leaves.

The owner, 2026-11-07: two films looked alike and leaned on numbered lists; "the visual should follow the topic", the
way SiTech's blog cards draw each post's subject in lines. A vignette is a line drawing of what one part of the story
is about. It draws itself stroke by stroke when its scene comes in and stands there while the voice says it.

    source   the scene's own `art` (an SVG fragment its author drew, art.GUIDE's style), else the library's drawing
             (drawings.candidates: the saved ones and the seeds) of the first motif that scene's part of the narration
             names (icons.find) and the film hasn't drawn yet. The pick is deterministic per story
    words    none: every label is removed (thread._strip), so a vignette carries no number, name or place
    seat     thread.seat: the room at the scene's foot, at least MIN_H high, never the small corner token. The scene keeps it free (Frame's
             reserve), the layout probe checks text against it (rule "seat") and a drawing with text on its seat moves
             below that text, or is given up, before the render (relieve): a vignette never holds a video. fit() shrinks it to the drawing's own shape
             and centres it on the frame (the owner, 2026-11-07: the gauge reads better in the middle)
    count    at most MAX a film and one a scene: the author's first, then the library's in scene order
    who      a scene's `art` comes from an agent, or from the illustrator (illustrator.py): a call of its own after the
             script, with its own guide, for the hook and the scenes the library has nothing for

None where pictograms may not go (news_check.no_pictograms: the crime family, deaths), for the incidents' categories,
in a film with a thread (the object owns the seats), and on a scene that shows its own picture or must stay bare: the
pack's cards, the map, a plate, a draw, state or sign scene, a stat drawn with its icon, a scene with a photo.

    python -m tt_shorts.engine vignettes stories/x.json      # the plan, free: which scene draws what, and where
"""
import xml.etree.ElementTree as ET
import zlib

from tt_shorts import art, drawings, icons, news_check, thread

MAX = 3
SKIP = tuple(dict.fromkeys(thread.NO_SEAT + thread.OWN + thread.HERO + ("sign", "plate")))
PAD = 24  # px of the drawing's own canvas around its strokes
MIN_H = 160  # px: the smallest seat a drawing takes (the thread's object needs 210 to carry a state)
CENTER = 540  # px: the frame's middle, where a drawing stands
MIN_KEEP = 120  # px: a drawing the probe moves below a scene's text keeps at least this height, or is given up
GAP_CAPTIONS = 10  # px between a drawing's foot and the captions' highest row


def eligible(story):
    """(True, None), or (False, why): what the news rules protect gets no drawing; a thread keeps its seats."""
    from tt_shorts import brand, meta
    category = str(story.get("category") or "")
    try:
        family = meta.family(category, brand.of(story))
    except brand.BrandError:
        family = meta.family(category, brand.load())
    if family == "crime" or category in thread.INCIDENTS:
        return False, "vignettes: never for crime or incidents"
    why = news_check.no_pictograms(story)
    if why:
        return False, f"vignettes: never for a story about {why}"
    if thread.has(story):
        return False, None  # the film's object has the seats
    return True, None


def bare(svg):
    """A drawing without its words, or None when it doesn't parse or what is left fails art's checks."""
    if not isinstance(svg, str) or not svg.strip():
        return None
    try:
        out = thread._strip(svg)
    except ET.ParseError:
        return None
    return out if drawings.passes(out) else None


def own_problems(s):
    """What is wrong with a scene's own `art` (engine.shape_problems): art's checks on the drawing without words."""
    svg = s.get("art")
    if svg is None:
        return []
    if not isinstance(svg, str) or not svg.strip():
        return ["art: an SVG fragment of line art (art.GUIDE), or no art"]
    if s.get("type") in SKIP:
        return [f"art: a {s.get('type')} scene shows its own picture or none; put the drawing on another scene"]
    try:
        stripped = thread._strip(svg)
    except ET.ParseError as e:
        return [f"art: the SVG doesn't parse ({e})"]
    return [f"art: {p.removeprefix('draw: ')}" for p in art.scene_problems(stripped)]


def drop_bad(story):
    """The story without the scenes' own drawings that still fail (the writer's last step): a scene without one may
    still get the library's, and a video without any is better than no video."""
    scenes = [{k: v for k, v in s.items() if k != "art"} if own_problems(s) else s for s in story.get("scenes") or []]
    return {**story, "scenes": scenes}


def _library(story, i, used, seed):
    """The library's drawing for scene i: the first motif its part of the narration names that the film hasn't drawn."""
    for motif in icons.find(news_check.scene_part(story, i)):
        if motif in used:
            continue
        pool = [d for d in drawings.candidates(motif) if bare(d["svg"])]
        if pool:
            pick = pool[(seed + i) % len(pool)]
            return {"motif": motif, "drawing": pick.get("name") or pick["id"], "source": pick["source"],
                    "svg": bare(pick["svg"])}
    return None


def box(svg):
    """The drawing's bounds on its own canvas, padded for the strokes: [x0, y0, x1, y1]."""
    tree, _ = art.sanitize(svg)
    pts = art._box(tree)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [round(min(xs) - PAD), round(min(ys) - PAD), round(max(xs) + PAD), round(max(ys) + PAD)]


def seed_of(story):
    return zlib.crc32(f"{story.get('id')}|vignettes".encode())


def seat_for(s, i, look, seed):
    """A scene's room for a drawing -> thread.seat's {x, y, w, h, reserve}, or None: no room, or only the corner."""
    if s.get("type") in SKIP or s.get("media"):
        return None
    seat = thread.seat(s, i, look, seed, low=MIN_H)
    return None if not seat or seat.get("role") == "token" else seat


def fit(seat, bounds, look):
    """The seat shrunk to the drawing's own shape and centred on the frame: as big as its height allows, its foot where
    the seat's is, left of the like/share rail (thread.RIGHT) and inside the scene's box. The reserve stays the seat's."""
    half = min(CENTER - thread.BOXES[look][0], thread.RIGHT - CENTER)
    x0, y0, x1, y1 = bounds
    aspect = (x1 - x0) / max(1, y1 - y0)
    h = seat["h"]
    w = h * aspect
    if w > 2 * half:
        w, h = 2 * half, 2 * half / aspect
    foot = seat["y"] + seat["h"]
    return {**seat, "x": round(CENTER - w / 2), "y": round(foot - h), "w": round(w), "h": round(h)}


def plan(story, scenes=None, look="editorial", foot=None):
    """The film's vignettes -> ({scene index: {motif, drawing, source, svg, box, seat}}, [warnings]). scenes: the scenes
    shown (default the story's). foot: the y a drawing stands on when the captions reach above the scene band's end
    (captions.reach: the roll's upper row), GAP_CAPTIONS clear of them. Pure: the same story gets the same drawings in
    the same seats."""
    ok, why = eligible(story)
    if not ok:
        return {}, [why] if why and any(s.get("art") for s in story.get("scenes") or []) else []
    scenes = story.get("scenes") if scenes is None else scenes
    seed = seed_of(story)
    warnings, picks = [], {}
    for i, s in enumerate(scenes or []):
        if not isinstance(s.get("art"), str):  # none, or a draw scene's own tree on the props
            continue
        drawn = bare(s["art"]) if s.get("type") not in SKIP else None
        if drawn:
            picks[i] = {"motif": None, "drawing": "the scene's own", "source": "story", "svg": drawn}
        else:
            warnings.append(f"vignettes: scene {i}'s own drawing fails the checks: the library's or none")
    used = set()
    for i, s in enumerate(scenes or []):
        if len(picks) >= MAX:
            break
        if i in picks or s.get("type") in SKIP or s.get("media") or s.get("icon"):
            continue
        one = _library(story, i, used, seed)
        if one:
            picks[i] = one
            used.add(one["motif"])
    out = {}
    for i in sorted(picks)[:MAX]:
        seat = seat_for(scenes[i], i, look, seed)
        low = None if foot is None else foot - GAP_CAPTIONS
        if seat and low is not None and seat["y"] + seat["h"] > low:
            seat = {**seat, "h": low - seat["y"]} if low - seat["y"] >= MIN_KEEP else None
        if seat:
            bounds = box(picks[i]["svg"])
            out[i] = {**picks[i], "box": bounds, "seat": fit(seat, bounds, look)}
    return out, warnings


def attach(props, story, foot=None):
    """Put a story's vignettes on its Remotion props: each drawing scene's `vignette` -> [warnings]. foot: see plan."""
    got, warnings = plan(story, props["scenes"], props["variant"], foot)
    for s in props["scenes"]:
        if isinstance(s.get("art"), str):  # the author's SVG: what is drawn is the vignette's checked tree
            s.pop("art")
    for i, v in got.items():
        props["scenes"][i]["vignette"] = {**v["seat"], "role": "seat", "box": v["box"], "art": art.sanitize(v["svg"])[0],
                                          "motif": v["motif"], "source": v["source"]}
    return warnings


def relieve(props, checked):
    """The scenes whose seat the layout probe found text on -> [those scenes], or None. The probe says where that text
    really ends (`bottom`), so the drawing moves below it, smaller and still centred, when MIN_KEEP px are left;
    else, or when the probe doesn't say, it is given up. The shrunk seat lies inside the old one, so no other text
    can be on it."""
    lows = {}
    for x in (checked or {}).get("issues") or []:
        if x.get("rule") == "seat" and x.get("scene") is not None:
            i, low = x["scene"], x.get("bottom")
            lows[i] = None if low is None or lows.get(i, 0) is None else max(lows.get(i, 0), low)
    hit = []
    for i, low in sorted(lows.items()):
        v = props["scenes"][i].get("vignette")
        if not v:
            continue
        hit.append(i)
        foot = v["y"] + v["h"]
        top = None if low is None else low + thread.GAP / 2
        if top is None or foot - top < MIN_KEEP:
            props["scenes"][i].pop("vignette")
            continue
        props["scenes"][i]["vignette"] = {**v, **fit({**v, "y": top, "h": foot - top}, v["box"], props["variant"])}
    return hit or None


def summary(story, look="editorial"):
    """What `engine vignettes` prints: the plan without the SVG, and what the illustrator would be asked to draw."""
    from tt_shorts import illustrator
    got, warnings = plan(story, look=look)
    return {"illustrator": {"on": illustrator.on(), "would_draw": illustrator.wanted(story, look),
                            "model": illustrator.model()},
            "vignettes": [{"scene": i, "type": (story.get("scenes") or [])[i].get("type"), "motif": v["motif"],
                           "drawing": v["drawing"], "source": v["source"],
                           "seat": {k: v["seat"][k] for k in ("x", "y", "w", "h")}} for i, v in got.items()],
            "max": MAX, "warnings": warnings}


def options():
    """What `engine options` shows an agent."""
    return {"about": "1-3 line drawings of what the film is about, each in the room a scene's text leaves, drawn stroke "
                     "by stroke (vignettes.py). A scene's own `art` (an SVG fragment in the draw scene's style, no "
                     "labels: code removes every word) comes first; else code takes the library's drawing of a thing "
                     "that scene's part of the narration names",
            "max": MAX, "never_on": list(SKIP) + ["a stat with an icon", "a scene with a photo"],
            "never_for": ["crime", "incidents", "deaths", "a film with a thread"]}
