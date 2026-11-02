"""Marks synced to the voice (ROADMAP C2): a scene's `"em": "<phrase>"` is drawn over on screen as the voice says it.

The writer only names the phrase. Code does the rest:
  - where:  the phrase must be word for word in one of the scene's markable fields (its brush's em fields,
            brushes/<type>.json: "lines", "label", "value", "items.name"...; never the kicker) and said in the
            scene's part of the narration (news_check.marks, N11). locate() finds the field and the offset.
  - when:   speech.mark_frames() reads the word timings (Gemini's alignment, edge's boundaries, or the silent
            engine's estimate) and sets the frame the phrase starts being said; the stroke takes as long as the
            phrase is spoken (10-22 frames) and never starts before the scene has come in.
  - which:  the kind (underline, box, circle, highlight, bracket: @remotion/rough-notation) is code's, from the
            brush's kinds varied per story and scene (crc32), never the writer's: a big number (a stat's or a
            share's value) and a link's edge are underlined, a circle goes only around a short word, a bracket
            only around a whole item.
  - how:    clean strokes for hard and service news, a little roughness for light news (sports, culture: the
            families the packs give the kinetic look); in ink (the accent is never a mark: it is for the dot);
            at most one per scene (em is one phrase).
"""
import re
import zlib

from tt_shorts import catalog, normalize_ka

MAX_WORDS = 4
MAX_CHARS = 40
LIGHT = ("sports", "culture")  # light news: the strokes may wobble a little
STROKES = {"clean": {"roughness": 0.0, "bowing": 0.0}, "light": {"roughness": 1.3, "bowing": 1.0}}
ENTER = 14  # frames: the scene's text is in (ui.tsx In springs settle in ~12)
MIN_FRAMES, MAX_FRAMES = 10, 22


def _norm(s):
    return re.sub(r"[\W_]", "", s.lower())


def tokens(text):
    return [n for n in (_norm(t) for t in normalize_ka.tokens(text or "")) if n]


def _stem(t):
    return t if any(c.isdigit() for c in t) or len(t) <= 4 else t[:max(4, len(t) - 2)]


def same(a, b):
    """One word of the phrase against one spoken word: equal, or the same stem (Georgian case endings:
    აბონენტს / აბონენტი); a number must be equal."""
    return a == b or (len(a) >= 4 and len(b) >= 4 and _stem(a) == _stem(b))


def find(want, toks):
    """Index in toks where the token sequence want starts (same() per word), or None."""
    if not want:
        return None
    for i in range(len(toks) - len(want) + 1):
        if all(same(w, toks[i + k]) for k, w in enumerate(want)):
            return i
    return None


def said(phrase, text):
    return find(tokens(phrase), tokens(text)) is not None


def _value_text(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return f"{v:g}" if isinstance(v, float) else str(v)


def fields(scene):
    """[(path, text)] of the scene's markable texts, in the brush's em order."""
    b = catalog.load_all().get(scene.get("type"))
    out = []
    for f in (b["em"]["fields"] if b else []):
        top, _, sub = f.partition(".")
        v = scene.get(top)
        if top == "value":
            t = _value_text(v)
            if t:
                out.append(("value", t))
        elif isinstance(v, list):
            for i, it in enumerate(v):
                x = it.get(sub) if sub and isinstance(it, dict) else (None if sub else it)
                if isinstance(x, str):
                    out.append((f"{top}.{i}" + (f".{sub}" if sub else ""), x))
        elif isinstance(v, str):
            out.append((top, v))
    return out


def locate(scene, phrase=None):
    """(path, start, the phrase as it is written there) of the first markable field showing the phrase, or None."""
    phrase = scene.get("em") if phrase is None else phrase
    if not isinstance(phrase, str) or not phrase.strip():
        return None
    pattern = re.compile(r"\s+".join(re.escape(w) for w in phrase.split()), re.I)  # any run of spaces between words
    for path, text in fields(scene):
        m = pattern.search(text)
        if m:
            return path, m.start(), m.group(0)
    return None


def kind(story_id, i, scene, path, phrase):
    """The mark's kind: the brush's kinds, varied per story and scene; a number or an edge underlined, a circle only
    around a short word (else a box), a bracket only around a whole item text (else an underline)."""
    b = catalog.get(scene["type"])
    kinds = b["em"]["kinds"] or ["underline"]
    k = kinds[zlib.crc32(f"{story_id}:{i}".encode()) % len(kinds)]
    if path in ("value", "edge"):  # a stat's number fills the width and an edge sits in a chip: only a line fits
        return "underline"
    if k == "circle" and len(phrase) > 10:
        k = "box"
    if k == "bracket" and not (path.startswith("items.") and dict(fields(scene)).get(path, "").strip() == phrase.strip()):
        k = "underline"
    return k


def strokes(family):
    """Clean for hard and service news, a little rough for light news."""
    return dict(STROKES["light" if family in LIGHT else "clean"])


def timing(words, phrase, start, end, fps):
    """(frame the phrase starts being said, frames it takes) inside [start, end) seconds of the word timings, or None
    when the voice doesn't say it there."""
    toks, owner = [], []
    for k, w in enumerate(words):
        if start - 0.05 <= w["start"] < end:
            for t in tokens(w["text"]):
                toks.append(t)
                owner.append(k)
    want = tokens(phrase)
    i = find(want, toks)
    if i is None:
        return None
    first, last = words[owner[i]], words[owner[i + len(want) - 1]]
    return first["start"] * fps, (last["end"] - first["start"]) * fps


def resolve(scene, i, story_id, family, words, frm, duration, fps):
    """The props a marked scene carries ({field, start, phrase, kind, at, frames, seed, ...strokes}), or None."""
    hit = locate(scene)
    if not hit:
        return None
    path, start, phrase = hit
    t = timing(words, scene["em"], frm / fps, (frm + duration) / fps, fps)
    if t:
        at, frames = round(t[0] - frm), round(t[1])
    else:  # the check makes this rare (a voice that skipped the words): mark it once the scene is in
        at, frames = ENTER + 6, 16
    frames = max(MIN_FRAMES, min(MAX_FRAMES, frames))
    at = max(ENTER, min(at, duration - frames - 8))
    return {"field": path, "start": start, "phrase": phrase, "kind": kind(story_id, i, scene, path, phrase),
            "at": at, "frames": frames, "seed": zlib.crc32(f"{story_id}:{i}:mark".encode()) % 9973 + 1,
            **strokes(family)}
