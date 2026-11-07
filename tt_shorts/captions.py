"""Caption layout, computed once per video in Python and handed to Remotion as props.

Why here and not in the browser (owner, 2026-11-02: "the captions jump, sometimes they seem to freeze"):
- a layout measured in the render tabs depends on each tab's font state; measured here with fontTools on the very
  woff2 the video uses, it is the same for every frame and every tab;
- one font size per video: refitting per chunk moved every glyph at every change;
- the old chunks were 1-3 words and changed about once a second (14 of 32 a single word, 6 under 0.5 s); lines here
  are filled to the measured width, pages last at least MIN_PAGE seconds and gaps under BRIDGE seconds are bridged.

Three designs (remotion/src/Captions.tsx draws them):
  page     a fixed two-line block; the words wait in grey and turn white as they are spoken, the red underline marks
           the word being said; the block itself never moves, only a new page fades in.
  roll     a teleprompter: lines in one column that scrolls up continuously with time; the middle line is large,
           its neighbours small and fading. Its position is a pure function of time, so it cannot jump.
  keyword  the page's lines and pages in a dark box (the reference's karaoke captions): the word being said is lit,
           and each page has at most one keyword, picked here: the scene's em phrase when the page says it, else a
           number, else a name from the story (a who's, a link's, a quote's speaker, a where's place). It is drawn
           in the pack's keyword style (brand.keyword_style: underline, block or tint) from the moment it is said.
           Which words and which style are data in the layout, so any engine draws the same keyword.

Times are in seconds; the composition converts them to frames.
"""
import functools
import pathlib
import re

from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = ROOT / "assets" / "fonts" / "firago-bold.ed7553cea8.woff2"  # the default; a brand pack names its own 700
W, RAIL_X = 1080, 940
BAND = 2 * RAIL_X - W - 32  # 768 px: the caption band, left of the like/share rail
PAD = 26  # the box's side padding
MAX_W = BAND - 2 * PAD  # 716 px of text per line
CAPTION_BOTTOM = 1552  # the captions end here (the safe zone)
SIZES = {"page": 60, "roll": 58, "keyword": 60}
DESIGNS = tuple(SIZES)
KEY_KINDS = ("em", "number", "name")  # a page's keyword, in this order of preference
KEY_PAD = 8  # px a keyword's block reaches past its word on each side (it stays inside the box's padding)
MIN_SIZE = 44
LINE_HEIGHT = 1.22
PAUSE = 0.40  # a silence this long starts a new line (and a new page)
MIN_PAGE = 1.0  # seconds a page stays up at least (Netflix: 5/6 s per event; Shorts read faster)
MIN_LINE = 0.7  # seconds a rolling line stays the active one at least
BRIDGE = 1.2  # gaps shorter than this keep the previous page up; longer ones fade it out
LEAD = 0.08  # a page appears a moment before its first word
TAIL = 0.6  # how long the last page stays after its last word
SENTENCE_END = (".", "!", "?", ":", "“", ";")
# words that should not hang at the end of a line: they belong to what follows (typesetting, not grammar)
HANG = {"და", "თუ", "ან", "რომ", "მაგრამ", "ხოლო", "კი", "არ", "ვერ", "ამ", "ის", "ეს", "იმ", "მისი", "მათი"}


@functools.lru_cache(maxsize=8)
def _metrics(font=None):
    f = TTFont(str(font or FONT))
    return f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm


def width(text, size, font=None):
    """Advance width in px of `text` in the caption font (bold) at `size` (kerning ignored: it only narrows Georgian)."""
    cmap, hmtx, upm = _metrics(str(font) if font else None)
    return sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in text) * size / upm


def font_size(words, design, font=None):
    """One size for the whole video: the design's size, smaller only if a single word would not fit a line."""
    size = SIZES[design]
    longest = max((width(w["text"], 100, font) for w in words), default=0)
    if longest:
        size = min(size, int(100 * MAX_W / longest))
    return max(MIN_SIZE, size - size % 2)


def _ends_sentence(text):
    return text.rstrip("»\"'").endswith(SENTENCE_END)


def lines(words, size, font=None):
    """Greedy lines filled to MAX_W at `size`; a pause or a sentence end closes the line."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur:
            gap = w["start"] - cur[-1]["end"]
            too_wide = width(" ".join(x["text"] for x in cur + [w]), size, font) > MAX_W
            if too_wide or gap >= PAUSE or _ends_sentence(cur[-1]["text"]):
                carry = []
                # a bare number or a short connective at a width break moves down with the word it belongs to
                tail = cur[-1]["text"]
                if too_wide and len(cur) > 1 and (tail in HANG or tail.isdigit()):
                    if width(" ".join(x["text"] for x in [cur[-1], w]), size, font) <= MAX_W:
                        carry = [cur.pop()]
                out.append(cur)
                cur = carry
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def _merge_short_lines(ls, size, min_s, font=None):
    """A line on screen for less than min_s joins its neighbour when they still fit one line together."""
    changed = True
    while changed:
        changed = False
        for i in range(len(ls) - 1):
            dur = ls[i + 1][0]["start"] - ls[i][0]["start"]
            joined = ls[i] + ls[i + 1]
            if dur < min_s and width(" ".join(x["text"] for x in joined), size, font) <= MAX_W:
                ls[i:i + 2] = [joined]
                changed = True
                break
    return ls


def pages(ls):
    """Up to two lines per page; a pause or a sentence end after a line closes the page; short pages merge."""
    out, cur = [], []
    for i, line in enumerate(ls):
        cur.append(line)
        last = line[-1]
        nxt = ls[i + 1][0] if i + 1 < len(ls) else None
        gap = (nxt["start"] - last["end"]) if nxt else 0
        if len(cur) == 2 or nxt is None or gap >= PAUSE or _ends_sentence(last["text"]):
            out.append(cur)
            cur = []
    # a page shorter than MIN_PAGE takes the next page's first line when there is room, else joins the previous one
    i = 0
    while i < len(out) - 1:
        dur = out[i + 1][0][0]["start"] - out[i][0][0]["start"]
        if dur < MIN_PAGE and len(out[i]) == 1:
            out[i].append(out[i + 1].pop(0))
            if not out[i + 1]:
                out.pop(i + 1)
            continue
        i += 1
    return out


def _word(w):
    return {"text": w["text"], "from": round(w["start"], 3), "to": round(w["end"], 3)}


def _toks(text):
    from tt_shorts import marks  # the marker's Georgian stems (აბონენტს / აბონენტი)
    return marks.tokens(text)


def _same(a, b):
    from tt_shorts import marks
    return marks.same(a, b)


def candidates(scenes, fps=30):
    """A video's keyword candidates from its built scenes (props["scenes"]): [{kind, text, at}]. em: each scene's
    voice-synced mark (its phrase and the second it is said); name: the names the story shows (a who's or a link's
    item names, a quote's speaker, a where's place), at None. Numbers are found in the words themselves."""
    out = []
    for s in scenes:
        m = s.get("mark")
        if m and m.get("phrase"):
            out.append({"kind": "em", "text": m["phrase"], "at": round((s["from"] + m["at"]) / fps, 3)})
    for s in scenes:
        names = [it.get("name") for it in s.get("items") or [] if isinstance(it, dict) and s.get("type") in ("who", "link")]
        names += [s.get("by")] if s.get("type") == "quote" else []
        names += [s.get("place")] if s.get("type") == "where" else []
        out += [{"kind": "name", "text": n, "at": None} for n in names if isinstance(n, str) and n.strip()]
    return out


def _run(want, toks):
    """Start index of the token run `want` in toks (stems), or None."""
    if not want:
        return None
    for i in range(len(toks) - len(want) + 1):
        if all(_same(w, toks[i + k]) for k, w in enumerate(want)):
            return i
    return None


def _key(page, ls, keys):
    """A page's keyword: {line, from, to, kind} (word indices inside one of the page's lines, to inclusive), or
    None. The scene's em phrase said on this page first, then a number, then a name; always inside one line."""
    for kind in KEY_KINDS:
        for li in page:
            line = ls[li]
            toks = [(_toks(w["text"]) or [""])[0] for w in line]
            if kind == "number":
                for i, w in enumerate(line):
                    if re.search(r"\d", w["text"]):
                        return {"line": li, "from": i, "to": i, "kind": kind}
                continue
            for c in keys or []:
                if c["kind"] != kind:
                    continue
                want = _toks(c["text"])
                i = _run(want, toks)
                if i is None and kind == "name":  # a name said in part, in another case: its surname, ვარკეთილსა
                    i = next((k for k, t in enumerate(toks) for w in want if len(w) >= 5 and _named(w, t)), None)
                    want = want[:1]
                if i is None:
                    continue
                if kind == "em" and c.get("at") is not None and abs(line[i]["start"] - c["at"]) > 1.0:
                    continue  # the phrase said elsewhere, not where the scene marks it
                return {"line": li, "from": i, "to": i + len(want) - 1, "kind": kind}
    return None


def _named(name, said):
    """One word of a name against a spoken word: the same stem, or the same beginning but for a case ending (a
    shared prefix of all but the last three letters, at least five)."""
    if _same(name, said):
        return True
    n = 0
    while n < min(len(name), len(said)) and name[n] == said[n]:
        n += 1
    return n >= max(5, min(len(name), len(said)) - 3)


def reach(layout):
    """The highest y, in frame px, that a layout's caption text reaches: what stands on a scene's foot (a vignette)
    stays above it. The page and keyword boxes hold two lines and start at about the scene band's end (1380); the
    roll box holds three rows, and its upper, fading row stands about 65 px inside the scene band (Captions.tsx)."""
    size = layout.get("size") or SIZES.get(layout.get("design"), 60)
    lh = layout.get("lineHeight") or LINE_HEIGHT
    if layout.get("design") == "roll":
        row = size * lh + 10
        box = 3 * row + 24
        return round(CAPTION_BOTTOM - box + box / 2 - row / 2 - 0.78 * row)
    return round(CAPTION_BOTTOM - (2 * size * lh + 28))


def layout(words, design="page", end=None, font=None, keys=None, style="underline"):
    """-> props["captions"]: {design, size, lineHeight, box, lines:[{start, words}], pages:[{start, end, lines}]}.
    `end` is the video's last second (the last page stays until TAIL after its last word, at most to `end`).
    `font` is the woff2 the captions are drawn in (the brand pack's bold; default FiraGO Bold).
    keyword design: `keys` are the story's candidates (candidates()), `style` the pack's keyword style; each page
    may get "key" {line (index into lines), from, to (word indices in that line), kind}, and the layout "keyword":
    the style."""
    if not words:
        return {"design": design, "size": SIZES[design], "lineHeight": LINE_HEIGHT, "lines": [], "pages": []}
    size = font_size(words, design, font)
    ls = lines(words, size, font)
    if design == "roll":
        ls = _merge_short_lines(ls, size, MIN_LINE, font)
    pg = pages(ls) if design in ("page", "keyword") else [[l] for l in ls]
    index = {id(l): k for k, l in enumerate(ls)}
    out_pages = []
    for k, p in enumerate(pg):
        start = max(0.0, p[0][0]["start"] - LEAD)
        last = p[-1][-1]["end"]
        if k + 1 < len(pg):
            nxt = max(0.0, pg[k + 1][0][0]["start"] - LEAD)
            stop = nxt if nxt - last < BRIDGE else last + TAIL  # bridge small gaps, fade out across long ones
        else:
            stop = last + TAIL if end is None else min(end, last + TAIL)
        out_pages.append({"start": round(start, 3), "end": round(stop, 3), "lines": [index[id(l)] for l in p]})
        if design == "keyword":
            key = _key(out_pages[-1]["lines"], ls, keys)
            if key:
                out_pages[-1]["key"] = key
    out = {
        "design": design,
        "size": size,
        "lineHeight": LINE_HEIGHT,
        "band": BAND,
        "pad": PAD,
        "lines": [{"start": round(max(0.0, l[0]["start"] - LEAD), 3), "words": [_word(w) for w in l]} for l in ls],
        "pages": out_pages,
    }
    if design == "keyword":
        out["keyword"] = style
    return out


def problems(cap, words, font=None):
    """What the jitter tests check, as messages (empty when the layout is sound)."""
    out = []
    size = cap["size"]
    flat = [w["text"] for l in cap["lines"] for w in l["words"]]
    if flat != [w["text"] for w in words]:
        out.append("words are missing, repeated or out of order")
    for l in cap["lines"]:
        text = " ".join(w["text"] for w in l["words"])
        if width(text, size, font) > MAX_W + 0.5:
            out.append(f"line wider than {MAX_W}px: {text}")
    ps = cap["pages"]
    for a, b in zip(ps, ps[1:]):
        if b["start"] < a["start"]:
            out.append("pages out of order")
        if cap["design"] in ("page", "keyword") and b["start"] - a["start"] < MIN_PAGE - 1e-6 and len(cap["lines"]) > 2:
            out.append(f"page at {a['start']}s is up for {b['start'] - a['start']:.2f}s")
        if 0 < b["start"] - a["end"] < BRIDGE - 1e-6:
            out.append(f"hidden gap of {b['start'] - a['end']:.2f}s at {a['end']}s (the caption would blink)")
    for p in ps:  # a keyword sits inside one of its page's lines, and its block inside the box
        k = p.get("key")
        if not k:
            continue
        if k["line"] not in p["lines"] or not 0 <= k["from"] <= k["to"] < len(cap["lines"][k["line"]]["words"]):
            out.append(f"page at {p['start']}s: its keyword is not inside one of its lines")
            continue
        text = " ".join(w["text"] for w in cap["lines"][k["line"]]["words"])
        if width(text, size, font) + 2 * KEY_PAD > MAX_W + 2 * PAD:
            out.append(f"page at {p['start']}s: the keyword's block reaches past the box")
    return out
