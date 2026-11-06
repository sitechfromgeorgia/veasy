"""Beats inside scenes (docs/plan-v2.md § 6, phase 3): a visible change every 1.5-3 s, landed on the words.

Owner, 2026-11-03: the videos are slow. A scene's texts all arrived by 40 % of it and then nothing happened for
4-10 s (motion_rules "still"); the reference changes something every 1.5-2.5 s. So code splits each scene's part
of the narration at its word timings into beats and gives every beat a change the scene already knows how to draw:

    reveal   a list item (points, steps, who, pair), a stat's or a timeline's label, a where's sub line: it comes
             in when the voice says it, not on a fixed stagger (a quote's speaker is always there with it)
    lit      the words of a text wait dimmed and light up phrase by phrase, a beat at a time, as they are said
             (a quote, a point, a step, a pair's sides, a who's role)
    steps    a stepped device: the hook's rule, a stat's cell bar, a timeline's run, a where's camera (the map zooms
             in in stages; the grid's pin bounces)

Nothing here invents a motion: the components in remotion/src/scenes read `scene.beats` (frames relative to the
scene's start) and fall back to their own timing without it, so a scene without beats renders as before. Every
beat ends SETTLE frames before the scene's settled frame (probe.settled, the golden stills), and each device ends
where the scene ended before (every item in, every word lit, the rule, bar and run full, the map on its focus):
the settled frame is the same picture as before beats.

    track(scene, words, a, b, first)  ->  {"frames": [...], "reveal": {key: frame}, "lit": {field: [frame/word]},
                                          "steps": [frames], "texts": [[text, frame]]} or None

frames are every change (motion_rules reads them for "still"); texts are the on-screen texts that come in later
than the scene's own stagger (motion_rules reads them for "read"). A revealed text always keeps the time it needs to
be read (motion_rules.need) before the scene leaves.
"""
from tt_shorts import marks, motion_rules, probe, speech

FPS = speech.FPS
EXIT = probe.EXIT
MIN_BEAT, IDEAL_BEAT, MAX_BEAT = 1.5, 2.2, 3.0  # seconds between beats
SETTLE = 16  # frames: the last beat is this far before the settled frame, so its spring has come to rest
ENTER = 6  # frames: the scene's own first entrance (ui.tsx In, the first item's delay)
GAP = 18  # frames: two reveals at least this far apart
PIN = 14  # frames: a map's pins drop after its camera's last stage; their spring needs this much more to rest
TAIL = 2.9  # s: a beat is added while the scene has more than this left after its last change
PUNCT = (",", ".", ";", ":", "“", "»")

# per scene type: what its beats may move (remotion/src/scenes draws each one)
#   reveal  "items": each item from the second on, timed by the words in `match` ("": the item's text);
#           a field name: that text, when its words are said
#   lit     the item fields (or fields) whose words light up a beat at a time
#   steps   the stepped device the fillers drive, or None
DEVICES = {
    # the hook is the opening (readable at frame 0, swipe.py): nothing comes in later, its rule steps on
    "hook": {"reveal": [], "lit": [], "steps": "rule"},
    "stat": {"reveal": ["label"], "lit": [], "steps": "cells"},
    "timeline": {"reveal": ["label"], "lit": [], "steps": "run"},
    "where": {"reveal": ["sub"], "lit": [], "steps": "zoom"},
    # map-focus is the where's map drawn for its region: the same camera steps, the label when it is said
    "map-focus": {"reveal": ["label"], "lit": [], "steps": "zoom"},
    # kpi-grid: a cell arrives when its caption is said (its number counts up from that frame)
    "kpi-grid": {"reveal": "items", "match": "label", "lit": [], "steps": None},
    "points": {"reveal": "items", "match": "", "lit": [""], "steps": None},
    "steps": {"reveal": "items", "match": "", "lit": [""], "steps": None},
    "who": {"reveal": "items", "match": "name", "lit": ["role"], "steps": None},
    "pair": {"reveal": "items", "match": "title", "lit": ["title", "sub"], "steps": None},
    # a quote's speaker is on screen with it from the start (a quote is never shown without its name)
    "quote": {"reveal": [], "lit_fields": ["text"], "lit": [], "steps": None},
}


def _toks(text):
    return marks.tokens(text)


def _content(toks):
    """The tokens that say what a text is about: numbers and words of 4+ letters."""
    return [t for t in toks if any(c.isdigit() for c in t) or len(t) >= 4]


def _spoken(words, a, leave):
    """[(frame relative to the scene, token, punctuated)] of the scene's narration, one per token."""
    out = []
    for w in words:
        f = round(w["start"] * FPS) - a
        if 0 <= f < leave:
            ts = _toks(w["text"])
            for k, t in enumerate(ts):
                out.append((f, t, k == len(ts) - 1 and w["text"].rstrip("»\"'").endswith(PUNCT)))
    return out


def _find(text, spoken, after=0):
    """Index in spoken where the text starts being said (its first content word, confirmed by a second one when it
    has several), searching from `after`; None when the narration doesn't say it."""
    want = _content(_toks(text))
    if not want:
        return None
    need = 1 if len(want) <= 2 else 2  # a name may be said by its surname alone
    for i in range(after, len(spoken)):
        if not any(marks.same(w, spoken[i][1]) for w in want):
            continue
        window = [t for _, t, _ in spoken[i:i + len(want) + 4]]
        hit = sum(1 for w in set(want) if any(marks.same(w, t) for t in window))
        if hit >= need:
            return i
    return None


def _need(text):
    return round(motion_rules.need(text) * FPS)


def _text_of(item, field):
    if isinstance(item, str):
        return item if field in ("", "title", "name") else ""
    if not isinstance(item, dict):
        return ""
    if field == "":
        return item.get("title") or item.get("name") or item.get("label") or item.get("text") or ""
    return item.get(field) or ""


def _reveals(scene, dev, spoken, leave, last):
    """[(key, text, frame)] of what comes in when it is said, in order; frames clamped so each text is still read."""
    plan = []
    if dev["reveal"] == "items":
        items = scene.get("items") or []
        for k, it in enumerate(items[1:], 1):
            text = _text_of(it, dev.get("match", ""))
            whole = " ".join(x for x in (_text_of(it, f) for f in (dev["lit"] or [""])) if x) or text
            plan.append((f"items.{k}", text, whole))
    else:
        for f in dev["reveal"]:
            if isinstance(scene.get(f), str) and scene[f].strip():
                plan.append((f, scene[f], scene[f]))
    out, after, prev = [], 0, ENTER
    raw = []
    for key, text, whole in plan:
        i = _find(text, spoken, after)
        if i is None and not key.startswith("items."):
            continue  # a label the voice doesn't say keeps the scene's own timing
        raw.append((key, whole, spoken[i][0] if i is not None else None))
        if i is not None:
            after = i + 1
    # an item the narration doesn't name comes in between its neighbours, evenly
    known = [(k, f) for k, (_, _, f) in enumerate(raw) if f is not None]
    for k, (key, whole, f) in enumerate(raw):
        if f is None:
            lo = max([(j, g) for j, g in known if j < k], default=(-1, ENTER))
            hi = min([(j, g) for j, g in known if j > k], default=(len(raw), leave - 2 * FPS))
            f = lo[1] + (hi[1] - lo[1]) * (k - lo[0]) / max(1, hi[0] - lo[0])
        f = round(max(f, prev + GAP))
        f = min(f, leave - _need(whole), last)
        f = max(f, prev)  # never before the one above it
        mark = scene.get("mark")
        if mark and mark["field"].startswith(key) and f > mark["at"] - 4:
            f = max(prev, mark["at"] - 4)  # the marked phrase is drawn once its text is there
        out.append((key, whole, int(f)))
        prev = f
    return [r for r in out if r[2] > ENTER]


def _fillers(points, spoken, leave, last):
    """Beat frames that split every gap between changes into beats of MIN_BEAT-MAX_BEAT seconds, at word starts
    (a word after a comma or a full stop first); the tail too, while more than TAIL seconds are left."""
    starts = {}
    for f, _, p in spoken:
        starts[f] = starts.get(f, False) or p
    after_punct = {f for f, (g, _, p) in zip([s[0] for s in spoken[1:]], spoken) if p}
    cands = sorted(set(starts))

    def pick(p, q):
        lo, hi, ideal = p + MIN_BEAT * FPS, min(q - MIN_BEAT * FPS * 0.6, p + MAX_BEAT * FPS, last), p + IDEAL_BEAT * FPS
        if lo > hi:
            return None
        pool = [c for c in cands if lo <= c <= hi]
        if not pool:
            return round(min(max(ideal, lo), hi))
        near = [c for c in pool if c in after_punct and abs(c - ideal) <= 0.6 * FPS]
        return min(near or pool, key=lambda c: abs(c - ideal))

    out = []
    pts = sorted(set(points))
    for p, q in zip(pts, pts[1:] + [None]):
        end = q if q is not None else leave
        cur = p
        while (end - cur) > (MAX_BEAT if q is not None else TAIL) * FPS:
            c = pick(cur, end if q is not None else leave + MIN_BEAT * FPS * 0.6)
            if c is None or c <= cur:
                break
            out.append(c)
            cur = c
    return out


def _lit(fields, spoken, span, beats):
    """Per field, the frame each of its words lights up: the beat at or before the moment it is said (or, when the
    narration doesn't say the text, an even share of the beats). span: (from, to) frames the text is the one being
    said; beats: the beat frames inside it, the first being span[0]."""
    words = [(f, w) for f, text in fields for w in text.split()]
    if not words or len(beats) < 2:
        return None, []
    times = [None] * len(words)
    j = next((i for i, (g, _, _) in enumerate(spoken) if g >= span[0] - 2), len(spoken))
    for k, (_, w) in enumerate(words):
        want = _toks(w)
        if not want:
            continue
        for i in range(j, len(spoken)):
            if spoken[i][0] >= span[1]:
                break
            if marks.same(want[0], spoken[i][1]):
                times[k], j = spoken[i][0], i + 1
                break
    if sum(t is not None for t in times) * 2 < len(words):  # not said as written: an even share of the beats
        n, m = len(words), len(beats)
        at = [beats[min(m - 1, k * m // n)] for k in range(n)]
    else:
        at, last = [], beats[0]
        for t in times:
            if t is not None:
                last = max(last, max([b for b in beats if b <= t + 3], default=beats[0]))
            at.append(last)
    used = sorted(set(at))
    out = {}
    for (field, _), f in zip(words, at):
        out.setdefault(field, []).append(f)
    return out, [b for b in used if b > beats[0]]


def track(scene, words, a, b, first=False):
    """The beat track of one built scene (absolute start frame a, end frame b; words: the video's display words) ->
    {"frames", "reveal", "lit", "steps", "texts"}, or None for a type without beats or a scene too short for any."""
    dev = DEVICES.get(scene.get("type"))
    if not dev:
        return None
    dur = b - a
    leave = dur - EXIT
    last = probe_settled(dur) - SETTLE
    if last <= ENTER + MIN_BEAT * FPS:
        return None
    spoken = _spoken(words, a, leave)
    reveal = _reveals(scene, dev, spoken, leave, last)
    mark = scene.get("mark")
    points = [0 if first else ENTER] + [f for _, _, f in reveal] + ([mark["at"]] if mark else [])
    fill = _fillers(points, spoken, leave, last)
    lit, steps = {}, []
    used = set(points)
    # who says what when: the item being said is the latest revealed one
    spans = []
    if dev["reveal"] == "items" and dev["lit"]:
        items = scene.get("items") or []
        starts = [ENTER] + [f for _, _, f in reveal]
        keys = ["items.0"] + [k for k, _, _ in reveal]
        for n, (key, s0) in enumerate(zip(keys, starts)):
            k = int(key.split(".")[1])
            s1 = starts[n + 1] if n + 1 < len(starts) else leave
            fields = [(f"items.{k}" + (f".{f}" if f else ""), _text_of(items[k], f)) for f in dev["lit"]]
            spans.append(([x for x in fields if x[1]], (s0, s1)))
    for f in dev.get("lit_fields", []):
        if isinstance(scene.get(f), str) and scene[f].strip():
            ends = [r[2] for r in reveal] or [leave]
            spans.append(([(f, scene[f])], (ENTER, min(ends + [leave]))))
    for fields, (s0, s1) in spans:
        inside = [s0] + [x for x in fill if s0 < x < s1]
        got, chunks = _lit(fields, spoken, (s0, s1), inside)
        if got and chunks:
            lit.update(got)
            used.update(chunks)
    rest = [x for x in fill if x not in used]  # beats no text took: the scene's stepped device, else no change
    device = dev["steps"]
    if device == "zoom":
        if (scene.get("map") or {}).get("level") == "country":
            device = None  # the whole country is shown: there is no camera move to stage
        elif scene.get("map"):
            rest = [x for x in rest if x <= last - PIN]  # the pins drop after the last stage and rest by the settled frame
    if device and rest:
        steps = rest
        used.update(rest)
    if device == "run":  # the run reaches the end time when it is said
        end = _find(scene.get("end") or "", spoken)
        if end is not None and steps and spoken[end][0] > steps[-1] + GAP and spoken[end][0] <= last:
            steps.append(spoken[end][0])
            used.add(spoken[end][0])
    frames = sorted(x for x in used if 0 <= x <= last)
    if len(frames) <= 1:
        return None
    return {"frames": frames, "reveal": {k: f for k, _, f in reveal}, "lit": lit, "steps": sorted(steps),
            "texts": [[t, f] for _, t, f in reveal]}


def probe_settled(dur):
    """The settled frame of a scene of `dur` frames, relative to its start (probe.settled, for a scene with an exit)."""
    return max(min(dur - 1, 12), dur - 1 - EXIT - 1)


def attach(scenes, words, first_index=0):
    """Every built scene (props["scenes"]) gets its "beats" (none for a type without them)."""
    for i, s in enumerate(scenes):
        t = track(s, words, s["from"], s["from"] + s["duration"], first=i == first_index)
        if t:
            s["beats"] = t
    return scenes
