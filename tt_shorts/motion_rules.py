"""Motion rules: the HyperFrames rules of a watchable short, as checks over a built video's timeline (ROADMAP B5).

They read the props props.build makes (scene frames from the voice's word timings, or the silent engine's estimate,
the scenes' own texts, the transition and the director's current), so they cost nothing and need no render.

    read      every text on screen stays up at least READ_BASE + READ_PER_WORD per word (0.5 s + 0.3 s a word),
              counted per text: from the moment it has come in to the moment its scene starts to leave
    still     no more than STILL_MAX (3 s) with nothing changing in the scene band: after a scene's last entrance
              has settled, the next cut comes within 3 s (the end card is exempt: its QR must hold still); with a
              beat track (beats.py), its beats count as changes and no gap between two of them may be longer
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
    - the call to action is read on the end card, or on the outro chip from its first frame (swipe.py);
    - a text a beat brings in when it is said (beats.py "texts") is in from that beat.
Captions are not counted here: captions.py has its own rules (pages of at least 1 s).
"""
import math
import re

from tt_shorts import art, directors, ka_check, probe, speech

FPS = speech.FPS
EXIT = probe.EXIT  # frames a scene takes to leave (remotion/src/NewsShort.tsx)
READ_BASE, READ_PER_WORD = 0.5, 0.3  # seconds a text needs: 0.5 s + 0.3 s a word
ENTER_BASE = 0.2  # s: the first text of a scene is in once the cut's entrance (10 frames) is mostly done
STAGGER = 0.15  # s: each later text of the scene comes in this much after the one before it
REVEAL_CAP = 0.4  # a scene's texts are all in by this share of the scene
SETTLE = 0.5  # s: an entrance's spring takes about this long to come to rest
BUILD = 1.0  # s: what a scene draws after its last text (a count-up, bars growing, a map zooming) takes about this
STILL_MAX = 3.0
HOLD_MAX = 8.0  # s: a scene type the video's director holds on (directors.py "holds": the data director's number)
STILL_EXEMPT = ("end",)  # the end card holds still: the QR is scanned there
MAX_KINDS = 3
MAX_MOVES = 3  # elements animating at the same moment in a scene
PACING_MIN = 1.5  # seconds: minimum scene duration to allow voice & reader comprehension
# The direction each cut moves in when the video has no director's current (remotion/src/NewsShort.tsx: wipe and the
# sweeps go right, slide and push go left); a plain cut, the dot's iris and the loop's cross-fade have none.
DIRECTION = {
    "line": (1, 0), "panel": (1, 0), "wipe": (1, 0), "slide": (-1, 0), "push": (-1, 0),
    "shutter": (1, 0), "blind": (1, 0), "corner": (1, 0), "object": (1, 0),
}
RULES = {
    "read": f"a text on screen too briefly: each needs {READ_BASE} s + {READ_PER_WORD} s per word (holds a render)",
    "still": f"more than {STILL_MAX:g} s with nothing changing in the scene band (the end card is exempt; a scene "
             f"type the director holds on may stay {HOLD_MAX:g} s)",
    "kinds": f"more than {MAX_KINDS} transition kinds in one video",
    "pingpong": "ping-pong cuts: kinds A-B-A in three cuts in a row, or two cuts in a row moving in opposite directions",
    "repeat": "two scenes of the same type in a row",
    "moves": f"more than {MAX_MOVES} elements animating at once in a scene: stagger them to keep focus",
    "background": "active video or motion behind text being read: quiet the background or use still image",
    "pacing": f"cut comes after less than {PACING_MIN:g} s or cuts off the voice: faster than voice and reading pace",
}
HOLDS = ("read",)
TEXTS_HOLDS = ("read", "safe_zone")


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
    later = {t: f / FPS for t, f in (scene.get("beats") or {}).get("texts", [])}  # beats.py: in when it is said
    for i, t in enumerate(plain):
        at = 0.0 if first else min(ENTER_BASE + STAGGER * i, REVEAL_CAP * dur)
        if scene.get("art") and scene.get("label") == t:
            at = max(at, late)
        at = max(at, later.get(t, 0.0))
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
        beat = (s.get("beats") or {}).get("frames") or []  # beats.py: a change on the words every 1.5-3 s
        if beat:
            built = max(built, beat[-1] / FPS + SETTLE)
        inner = max([(b - a) / FPS - SETTLE for a, b in zip(beat, beat[1:])] or [0.0])
        rows.append({"scene": i, "type": s.get("type"), "from": s["from"], "to": end, "leaves": leaves,
                     "seconds": round(s["duration"] / FPS, 2), "texts": texts, "settled": round(built, 2),
                     "beats": len(beat), "gap": round(inner, 2)})
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


def _finding(rule, detail, scene=None, hold=None):
    return {"rule": rule, "scene": scene, "detail": detail, "hold": hold if hold is not None else rule in HOLDS}


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


def still(rows, holds=()):
    """holds: scene types the video's director holds on (directors.py), which may stay still up to HOLD_MAX."""
    out = []
    for r in rows:
        if r["type"] in STILL_EXEMPT:
            continue
        quiet = max((r["leaves"] - r["from"]) / FPS - r["settled"], r.get("gap", 0.0))  # the tail, or between beats
        most = HOLD_MAX if r["type"] in holds else STILL_MAX
        if quiet > most + 1e-6:
            out.append(_finding("still", f"scene {r['scene']} ({r['type']}): nothing changes for {quiet:.1f} s after "
                                         f"it settles (at most {most:g} s): split it, or give it less narration",
                                r["scene"]))
    return out


def _holds(p):
    """The scene types the video's director holds on (none without a director)."""
    did = (p.get("style") or {}).get("director")
    if not did:
        return ()
    return tuple(directors.get(did).get("holds", ()))


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


def moves(rows):
    out = []
    for r in rows:
        if r["scene"] == 0 or r["type"] in STILL_EXEMPT:
            continue
        ins = [t["in"] for t in r["texts"]]
        for t0 in ins:
            simultaneous = sum(1 for t in ins if abs(t - t0) <= 0.05)
            if simultaneous > MAX_MOVES:
                out.append(_finding("moves", f"scene {r['scene']} ({r['type']}): {simultaneous} elements enter at "
                                             f"the same time (at most {MAX_MOVES}): stagger them to keep focus",
                                    r["scene"]))
                break
    return out


def background(rows, p=None):
    out = []
    scenes = (p.get("scenes") or []) if p else []
    for r in rows:
        if r["scene"] >= len(scenes):
            continue
        s = scenes[r["scene"]]
        med = s.get("media") or {}
        is_video = med.get("kind") == "video" or med.get("video")
        text_need = sum(t["need"] for t in r["texts"])
        if is_video and text_need > 1.5:
            out.append(_finding("background", f"scene {r['scene']} ({r['type']}): video motion behind "
                                              f"{len(r['texts'])} texts being read ({text_need:.1f} s needed): "
                                              f"quiet the background or use still image", r["scene"]))
    return out


def pacing(rows, p=None):
    out = []
    scenes = (p.get("scenes") or []) if p else []
    for r in rows:
        if r["type"] in STILL_EXEMPT:
            continue
        s = scenes[r["scene"]] if r["scene"] < len(scenes) else {}
        narr = s.get("narration") or ""
        voice_need = words(narr) * 0.28
        if r["seconds"] < PACING_MIN:
            out.append(_finding("pacing", f"scene {r['scene']} ({r['type']}): cut comes after only {r['seconds']:.1f} s "
                                          f"(minimum {PACING_MIN:g} s): faster than voice and reading pace",
                                r["scene"]))
        elif narr and r["seconds"] < voice_need:
            out.append(_finding("pacing", f"scene {r['scene']} ({r['type']}): cut comes at {r['seconds']:.1f} s, "
                                          f"faster than voice ({voice_need:.1f} s needed for {words(narr)} words)",
                                r["scene"]))
    return out


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
    found = (read(rows) + still(rows, _holds(p)) + kinds(cut_list) + pingpong(cut_list) + repeat(rows)
             + moves(rows) + background(rows, p) + pacing(rows, p))
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


# ---------------------------------------------------------------- TEXTS(t) contract for composed & canvas films


def check_texts_track(samples, safe_zone=True):
    """Check a series of window.TEXTS(t) samples from a composed or canvas film.

    samples is a dict of {t_float: [ {id, text, x0, y0, x1, y1}, ... ]} or an iterable of (t, [items...])
    where t is timestamp in seconds (float).

    Verifies two core invariants:
    1. Reading time: each continuously visible text element must remain on screen
       for at least READ_BASE + READ_PER_WORD * words(text) (0.5 s + 0.3 s/word).
    2. Safe zone geometry (when safe_zone=True):
       - Scene text must not intrude above y = 248 (header zone), unless id or role is 'header' or 'chrome'
       - Scene text must end above y = 1380 (captions zone), unless id or role is 'captions'
       - Scene text must respect the social rail (x1 <= 940 when y1 > 1100)
       - Content must stay within canvas bounds [0, 0, 1080, 1920]

    Returns {"findings": found, "holds": holds, "warnings": warnings, "spans": spans}.
    """
    if isinstance(samples, dict):
        ordered_samples = sorted(samples.items(), key=lambda kv: kv[0])
    else:
        ordered_samples = sorted(samples, key=lambda kv: kv[0])

    spans = []
    active = {}
    found = []

    for t, items in ordered_samples:
        current_keys = set()
        for it in (items or []):
            tid = str(it.get("id") or it.get("text") or "text")
            text = str(it.get("text") or "")
            key = (tid, text)
            current_keys.add(key)

            x0 = it.get("x0", 0)
            y0 = it.get("y0", 0)
            x1 = it.get("x1", 1080)
            y1 = it.get("y1", 1920)

            if key not in active:
                active[key] = {
                    "id": tid,
                    "text": text,
                    "start_t": t,
                    "end_t": t,
                    "role": it.get("role") or it.get("type"),
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                }
            else:
                active[key]["end_t"] = t
                active[key]["x0"] = min(active[key]["x0"], x0)
                active[key]["y0"] = min(active[key]["y0"], y0)
                active[key]["x1"] = max(active[key]["x1"], x1)
                active[key]["y1"] = max(active[key]["y1"], y1)

            if safe_zone:
                role = str(it.get("role") or it.get("type") or tid).lower()
                is_header = "header" in role or "chrome" in role or tid == "header"
                is_captions = "caption" in role or tid == "captions"

                if not is_header and y0 < 248 - 1e-3:
                    found.append(_finding(
                        "safe_zone",
                        f"text {_quote(text)} (id: {tid}) enters header zone at y={y0:.1f} (min 248) at t={t:.2f}s",
                        hold=True,
                    ))
                if not is_captions and y1 > 1380 + 1e-3:
                    found.append(_finding(
                        "safe_zone",
                        f"text {_quote(text)} (id: {tid}) enters captions zone at y={y1:.1f} (max 1380) at t={t:.2f}s",
                        hold=True,
                    ))
                if y1 > 1100 + 1e-3 and x1 > 940 + 1e-3:
                    found.append(_finding(
                        "safe_zone",
                        f"text {_quote(text)} (id: {tid}) enters social rail at x={x1:.1f} (max 940 below y=1100) at t={t:.2f}s",
                        hold=True,
                    ))
                if x0 < 0 or x1 > 1080 or y0 < 0 or y1 > 1920:
                    found.append(_finding(
                        "safe_zone",
                        f"text {_quote(text)} (id: {tid}) exceeds canvas bounds at t={t:.2f}s",
                        hold=True,
                    ))

        ended_keys = [k for k in active if k not in current_keys]
        for k in ended_keys:
            sp = active.pop(k)
            dur = sp["end_t"] - sp["start_t"]
            w = words(sp["text"])
            req = need(sp["text"])
            spans.append({**sp, "duration": round(dur, 2), "words": w, "need": round(req, 2)})
            if dur + 1e-4 < req and w > 0:
                found.append(_finding(
                    "read",
                    f"text {_quote(sp['text'])} (id: {sp['id']}) is visible for {dur:.1f} s, its {w} words need {req:.1f} s"
                ))

    for k, sp in active.items():
        dur = sp["end_t"] - sp["start_t"]
        w = words(sp["text"])
        req = need(sp["text"])
        spans.append({**sp, "duration": round(dur, 2), "words": w, "need": round(req, 2)})
        if dur + 1e-4 < req and w > 0:
            found.append(_finding(
                "read",
                f"text {_quote(sp['text'])} (id: {sp['id']}) is visible for {dur:.1f} s, its {w} words need {req:.1f} s"
            ))

    text_fn = lambda f: f"motion {f['rule']}: {f['detail']}"
    return {
        "findings": found,
        "holds": [text_fn(f) for f in found if f["hold"]],
        "warnings": [text_fn(f) for f in found if not f["hold"]],
        "spans": spans,
    }

