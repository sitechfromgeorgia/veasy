"""Motion rules: the HyperFrames rules of a watchable short, as checks over a built video's timeline (ROADMAP B5).

They read the props props.build makes (scene frames from the voice's word timings, or the silent engine's estimate,
the scenes' own texts, the transition and the director's current), so they cost nothing and need no render.

    read      every text on screen stays up at least READ_BASE + READ_PER_WORD per word (0.5 s + 0.3 s a word),
              counted per text: from the moment it has come in to the moment its scene starts to leave
    still     no more than STILL_MAX (3 s) with nothing changing in the scene band: after a scene's last entrance
              has settled, the next cut comes within 3 s (the end card is exempt: its QR must hold still)
    kinds     no more than MAX_KINDS (3) kinds of transition in one video
    pingpong  no ping-pong cuts: (a) three cuts in a row of kinds A, B, A (A != B), the eye is thrown back to a cut
              it just left; (b) two cuts in a row that move in opposite directions (their direction vectors point
              against each other: a wipe to the right, then a push to the left)
    repeat    no two scenes of the same type in a row

`plan` reports all of them as warnings; only `read` holds a render (engine.render_story puts it in the render's
problems, like the layout probe: the job ends `held` and a person looks), because unreadable text is the one a
viewer can't recover from; the others are style. A text's time on screen is a model, not a measurement:
    - a scene's texts come in one after another: the k-th (ka_check.screen_texts order: kicker, headline, label...,
      lines, items) after ENTER_BASE + k * STAGGER seconds, at most REVEAL_CAP of the scene; the opening scene's
      texts are there at frame 0 (swipe.py: the hook is readable at frame 0);
    - a drawing's labels come in at their own --d delay, scaled the way remotion/src/scenes/more.tsx Draw scales it
      (the drawing is complete by about 55% of the scene), and the draw scene's label after the drawing;
    - a scene leaves EXIT frames before the next one starts (none for a plain cut); the last scene stays to the end;
    - the call to action is read on the end card, or on the outro chip from its first frame (swipe.py).
Captions are not counted here: captions.py has its own rules (pages of at least 1 s).
"""
import math
import re

from tt_shorts import art, ka_check, probe, speech

FPS = speech.FPS
EXIT = probe.EXIT  # frames a scene takes to leave (remotion/src/NewsShort.tsx)
READ_BASE, READ_PER_WORD = 0.5, 0.3  # seconds a text needs: 0.5 s + 0.3 s a word
ENTER_BASE = 0.2  # s: the first text of a scene is in once the cut's entrance (10 frames) is mostly done
STAGGER = 0.15  # s: each later text of the scene comes in this much after the one before it
REVEAL_CAP = 0.4  # a scene's texts are all in by this share of the scene
SETTLE = 0.5  # s: an entrance's spring takes about this long to come to rest
BUILD = 1.0  # s: what a scene draws after its last text (a count-up, bars growing, a map zooming) takes about this
STILL_MAX = 3.0
STILL_EXEMPT = ("end",)  # the end card holds still: the QR is scanned there
MAX_KINDS = 3
# The direction each cut moves in when the video has no director's current (remotion/src/NewsShort.tsx: wipe and the
# sweeps go right, slide and push go left); a plain cut, the dot's iris and the loop's cross-fade have none.
DIRECTION = {"line": (1, 0), "panel": (1, 0), "wipe": (1, 0), "slide": (-1, 0), "push": (-1, 0)}
RULES = {
    "read": f"a text on screen too briefly: each needs {READ_BASE} s + {READ_PER_WORD} s per word (holds a render)",
    "still": f"more than {STILL_MAX:g} s with nothing changing in the scene band (the end card is exempt)",
    "kinds": f"more than {MAX_KINDS} transition kinds in one video",
    "pingpong": "ping-pong cuts: kinds A-B-A in three cuts in a row, or two cuts in a row moving in opposite directions",
    "repeat": "two scenes of the same type in a row",
}
HOLDS = ("read",)


def words(text):
    """Words a viewer reads: tokens with a letter or a digit ("22:00 → 10:00" is two)."""
    return sum(1 for t in str(text).split() if re.search(r"\w", t))


def need(text):
    """Seconds a text must stay on screen to be read."""
    return READ_BASE + READ_PER_WORD * words(text)


def _draw_scale(scene):
    """(k, the drawing's last delay) as remotion/src/scenes/more.tsx Draw sets them for this scene's length."""
    last = max((n["delay"] for n in _walk(scene.get("art") or []) if n["motion"]), default=0.0)
    room = scene["duration"] / FPS * 0.55 - 0.5
    return (max(0.2, min(1.0, room / last)) if last > 0 else 1.0), last


def _walk(tree, delay=0.0):
    """Every node of a sanitized drawing with "shown": the latest motion delay on its path (a group's delay holds back
    what is inside it)."""
    for n in tree:
        d = max(delay, n["delay"] if n["motion"] else 0.0)
        yield {**n, "shown": d}
        yield from _walk(n["children"], d)


def scene_texts(scene, first=False):
    """[(text, seconds after the scene starts that it is in)] of one built scene."""
    dur = scene["duration"] / FPS
    plain = [t for _, t in ka_check.screen_texts({"scenes": [{k: v for k, v in scene.items() if k != "art"}]})]
    out = []
    late = 0.0
    if scene.get("art"):  # a drawing: its labels at their own delay, the scene's label after the drawing
        k, last = _draw_scale(scene)
        labels = [n for n in _walk(scene["art"]) if n.get("text")]
        out += [(n["text"], n["shown"] * k + 0.25) for n in labels]
        late = last * k + 6 / FPS
    for i, t in enumerate(plain):
        at = 0.0 if first else min(ENTER_BASE + STAGGER * i, REVEAL_CAP * dur)
        if scene.get("art") and scene.get("label") == t:
            at = max(at, late)
        out.append((t, at))
    return out


def timeline(p):
    """Built props -> one row per shown scene: {scene, type, from, to (frames), seconds, leaves (frame the exit starts),
    texts: [{text, words, need, shown}], settled (seconds into the scene its last entrance has come to rest)}."""
    scenes = p["scenes"]
    total = p["durationInFrames"]
    rows = []
    for i, s in enumerate(scenes):
        end = s["from"] + s["duration"]
        last = i == len(scenes) - 1
        kind = _kind(p, scenes, i + 1) if not last else None
        leaves = end if last or kind == "cut" else end - EXIT
        texts = []
        for t, at in scene_texts(s, first=i == 0):
            shown = (leaves - s["from"]) / FPS - at
            texts.append({"text": t, "words": words(t), "need": round(need(t), 2), "in": round(at, 2),
                          "shown": round(shown, 2)})
        if s.get("type") == "end" and p.get("cta"):
            texts.append({"text": p["cta"], "words": words(p["cta"]), "need": round(need(p["cta"]), 2), "in": 0.0,
                          "shown": round((leaves - s["from"]) / FPS - ENTER_BASE, 2)})
        built = max([x["in"] for x in texts] or [0.0]) + SETTLE + BUILD
        if s.get("art"):
            k, art_last = _draw_scale(s)
            built = max(built, art_last * k + SETTLE)
        if s.get("type") == "rail" and len(s.get("items") or []) > 1:  # the dot travels the rail (scenes/brushes.tsx)
            n = len(s["items"])
            step = min(30, max(10, (s["duration"] * 0.6 - 10) / (n - 1)))
            built = max(built, (10 + (n - 1) * step) / FPS + SETTLE)
        if s.get("mark"):  # a voice-synced mark draws in the scene band until it lands (marks.py)
            built = max(built, (s["mark"]["at"] + s["mark"]["frames"]) / FPS)
        rows.append({"scene": i, "type": s.get("type"), "from": s["from"], "to": end, "leaves": leaves,
                     "seconds": round(s["duration"] / FPS, 2), "texts": texts, "settled": round(built, 2)})
    if p.get("outroFrom") is not None and p.get("cta") and not any(r["type"] == "end" for r in rows):
        shown = (total - p["outroFrom"]) / FPS
        rows[-1]["texts"].append({"text": p["cta"], "words": words(p["cta"]), "need": round(need(p["cta"]), 2),
                                  "in": round((p["outroFrom"] - rows[-1]["from"]) / FPS, 2), "shown": round(shown, 2),
                                  "chip": True})
    return rows


def _kind(p, scenes, i):
    """The transition into scene i: the scene's own (a per-cut choice) or the video's."""
    return scenes[i].get("transition") or p.get("transition") or "cut"


def cuts(p):
    """Every cut of the video in order: [{into (scene), frame, kind, direction (x, y) or None}]."""
    scenes = p["scenes"]
    flow = (p.get("style") or {}).get("flow")
    out = []
    for i in range(1, len(scenes)):
        kind = _kind(p, scenes, i)
        own = scenes[i].get("flow")
        direction = tuple(own) if own else (tuple(flow) if flow and kind in DIRECTION else DIRECTION.get(kind))
        out.append({"into": i, "frame": scenes[i]["from"], "kind": kind, "direction": direction})
    if p.get("outro") == "loop":  # the last half second cross-fades into the hook's first frame
        out.append({"into": 0, "frame": p["durationInFrames"] - FPS // 2, "kind": "crossfade", "direction": None})
    return out


# ---------------------------------------------------------------- the rules: each -> [finding]


def _finding(rule, detail, scene=None):
    return {"rule": rule, "scene": scene, "detail": detail, "hold": rule in HOLDS}


def _quote(text, n=40):
    t = " ".join(str(text).split())
    return f"„{t[:n]}{'…' if len(t) > n else ''}“"


def read(rows):
    out = []
    for r in rows:
        for t in r["texts"]:
            if t["shown"] + 1e-6 < t["need"]:
                where = "the outro chip" if t.get("chip") else f"scene {r['scene']} ({r['type']})"
                out.append(_finding("read", f"{where}: {_quote(t['text'])} is readable for {max(0, t['shown']):.1f} s, "
                                            f"its {t['words']} words need {t['need']:.1f} s", r["scene"]))
    return out


def still(rows):
    out = []
    for r in rows:
        if r["type"] in STILL_EXEMPT:
            continue
        quiet = (r["leaves"] - r["from"]) / FPS - r["settled"]
        if quiet > STILL_MAX + 1e-6:
            out.append(_finding("still", f"scene {r['scene']} ({r['type']}): nothing changes for {quiet:.1f} s after "
                                         f"it settles (at most {STILL_MAX:g} s): split it, or give it less narration",
                                r["scene"]))
    return out


def kinds(cut_list):
    used = list(dict.fromkeys(c["kind"] for c in cut_list))
    if len(used) > MAX_KINDS:
        return [_finding("kinds", f"{len(used)} transition kinds ({', '.join(used)}): use at most {MAX_KINDS}")]
    return []


def _opposite(a, b):
    return bool(a and b) and a[0] * b[0] + a[1] * b[1] < 0


def pingpong(cut_list):
    out = []
    for a, b, c in zip(cut_list, cut_list[1:], cut_list[2:]):
        if a["kind"] == c["kind"] != b["kind"]:
            out.append(_finding("pingpong", f"cuts into scenes {a['into']}, {b['into']}, {c['into']} go "
                                            f"{a['kind']}, {b['kind']}, {c['kind']}: A-B-A", c["into"]))
    for a, b in zip(cut_list, cut_list[1:]):
        if _opposite(a["direction"], b["direction"]):
            out.append(_finding("pingpong", f"the cut into scene {a['into']} ({a['kind']}) moves {_way(a['direction'])}, "
                                            f"the next ({b['kind']}) {_way(b['direction'])}: back and forth", b["into"]))
    return out


def _way(v):
    x, y = v
    if abs(x) >= abs(y):
        return "right" if x > 0 else "left"
    return "down" if y > 0 else "up"


def repeat(rows):
    return [_finding("repeat", f"scenes {a['scene']} and {b['scene']} are both {a['type']}: one type twice in a row",
                     b["scene"])
            for a, b in zip(rows, rows[1:]) if a["type"] == b["type"]]


def _laid_out(p):
    """Props whose scenes all have from and duration (a scene without them runs from the previous one's end; the last
    to the end of the video), so partial props can be checked too."""
    total, at, scenes = p.get("durationInFrames") or 0, 0, []
    for i, s in enumerate(p.get("scenes") or []):
        start = s.get("from", at)
        rest = [x.get("from") for x in p["scenes"][i + 1:] if x.get("from") is not None]
        dur = s.get("duration", (rest[0] if rest else total) - start)
        scenes.append({**s, "from": start, "duration": max(1, dur)})
        at = start + dur
    return {**p, "scenes": scenes, "durationInFrames": max(total, at)}


def check(p):
    """Every motion rule over one video's built props -> {"timeline", "cuts", "findings", "holds", "warnings"}:
    holds are the findings that hold a render (HOLDS), warnings all the rest."""
    p = _laid_out(p)
    rows, cut_list = timeline(p), cuts(p)
    found = read(rows) + still(rows) + kinds(cut_list) + pingpong(cut_list) + repeat(rows)
    text = lambda f: f"motion {f['rule']}: {f['detail']}"  # noqa: E731
    return {"timeline": rows, "cuts": cut_list, "findings": found,
            "holds": [text(f) for f in found if f["hold"]], "warnings": [text(f) for f in found if not f["hold"]]}


def hold_problems(p):
    """The findings that hold a render (engine.render_story): only unreadable text."""
    return check(p)["holds"]


def load(row):
    """A scene's reading load: the seconds its texts need, read one after another, per second it is up (> 1: more text
    than time)."""
    up = (row["leaves"] - row["from"]) / FPS
    return round(sum(t["need"] for t in row["texts"]) / up, 2) if up > 0 else math.inf
