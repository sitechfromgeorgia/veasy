"""Code's own repairs to a written story, in one defined order, run until nothing changes.

    normalise(story, articles, ctx, rounds=5) -> Result(story, status, log)

The writer (writer.write) calls this after every model answer; nothing here calls a model. Each pass settles a rule
the checks enforce that code can settle on its own (ka_check.py, news_check.py, engine.structure_problems): it never
changes a rule, it only changes the story until the rule holds, or removes what can't be made to hold.

The narration is held as tokens (normalize_ka.tokens) plus cuts[i], the token scene i starts at, with cuts[0] = 0.
Every narration rewrite runs per slice, so a rewrite can't move a scene boundary; dropping a scene drops its cut (its
words join a neighbour) or its cut and its slice together. "at" is written only on exit, and the exit asserts that
normalize_ka.segments(narration, [at...]) == cuts: the one splitter the checks use finds exactly the cuts made here.

One round runs every pass in PASSES, in order:

  shape    _fix_change_scenes, _fix_schema_gaps, _fix_first_scene    every scene has its brush's shape; a hook opens
  media    _drop_pictograms, _drop_unknown_icons                     N10 (family), every icon resolves
  surface  _no_dashes, _fix_separators, _drop_stray_latin,           K12, K21, K19, N4 and the known wrong forms, on
           _spell_relative_days, _ka_forms                           the narration's slices and every text field
  sourced  _drop_unverbatim_quotes, _drop_unsupported                N3, K14; a quote with no speaker goes
  spoken   _fix_unspoken_names, fix_say_letters                      K20
  clamp    _fix_long_text, _clamp_texts                              slot lengths, before marks are judged
  repeats  _fix_repeats                                              no two scenes of one type in a row
  seat     seat (replaces _fix_anchors, _hard_anchor,                every slice has its type's words (K9) and seconds,
           _drop_short_scenes, _tidy_end, _shorten_story)            holds its em, edge, sign verb and stat value, and
                                                                     the film fits its length window
  marks    _fix_em_marks, _fix_sign_verbs, _drop_unsaid_stats        N11, N10 (verb) on the final slices

The rounds repeat until one changes nothing ("settled"). A state seen before is a "cycle", and a story still changing
after `rounds` is "unsettled": both are code bugs to fix here, never a reason to call the model. Every structural
action only removes or moves toward a fixed target (the inserted hook is inserted once), so a well-behaved story
settles in two or three rounds.
"""
import copy
import json
import re
from collections import namedtuple

from tt_shorts import catalog, icons, marks, news_check, normalize_ka, speech

Result = namedtuple("Result", "story status log")
STATUSES = ("settled", "cycle", "unsettled")
SEP = ""  # a private-use character between slices while a narration pass rewrites them all at once

# Voice pace against the draft estimator (speech.estimate_words), measured over 150 renders on 2026-11-18: the real
# voice runs estimate/1.37 (10th-90th percentile 1.23-1.50). A minimum is judged at the fastest pace, a maximum at the
# slowest, so the real voice can neither fall short of a scene's seconds nor run past the length window.
PACE_FAST = 1.50
PACE_SLOW = 1.23
# The story format's window (formats/story.json); ctx["min_seconds"/"max_seconds"] carries a program's own.
MIN_SECONDS = 18
MAX_SECONDS = 45  # the format's window at the voice's pace; used when ctx carries a window
GATE_MAX_ESTIMATE = 60  # engine.check_story: "timing: about Ns with an estimated voice" above this
# A scene's slice beyond this many tokens holds one frame too long (motion still); a cost in seat, not a limit.
MAX_WORDS = 12
LAMBDA = 1  # seat's cost per token a cut moves from where the writer put it
SKIP = ("at", "type", "art", "svg", "say", "icon", "motif", "morph_from", "verb", "show", "media", "kind", "id")
NOT_TEXT = ("num", "enum", "icon", "verb", "svg", "area")  # catalog slot kinds the text passes never rewrite
TOP_TEXT = ("headline", "hook", "title", "cta")


class NormaliseError(AssertionError):
    """The anchors written on exit don't split the narration where the cuts are: a bug in this module."""


# ---------------------------------------------------------------- the draft: a story, its tokens and its cuts


def _spans(text):
    return [(m.start(), m.end()) for m in normalize_ka.TOKENS.finditer(text or "")]


class Draft:
    """A story whose scenes are held as cuts into the narration's tokens. Passes edit draft.story and use the
    methods here to rewrite the narration or drop a scene, which keep the cuts true."""

    def __init__(self, story, cuts):
        self.story = story
        self.cuts = cuts

    @classmethod
    def of(cls, story):
        story = copy.deepcopy(story)
        if not isinstance(story.get("narration"), str):
            story["narration"] = str(story.get("narration") or "")
        if not isinstance(story.get("scenes"), list):
            story["scenes"] = []
        story["scenes"] = [s for s in story["scenes"] if isinstance(s, dict)]
        return cls(story, soft_cuts(story["narration"], [s.get("at") for s in story["scenes"]]))

    @property
    def scenes(self):
        return self.story["scenes"]

    @property
    def narration(self):
        return self.story["narration"]

    def toks(self):
        return normalize_ka.tokens(self.narration)

    def bounds(self, i):
        n = len(self.toks())
        return self.cuts[i], (self.cuts[i + 1] if i + 1 < len(self.cuts) else n)

    def part(self, i):
        """Scene i's part of the narration, exactly as news_check.scene_part reads it."""
        a, b = self.bounds(i)
        return " ".join(self.toks()[a:b])

    def raw_slices(self):
        text, spans = self.narration, _spans(self.narration)
        edges = [spans[c][0] if c < len(spans) else len(text) for c in self.cuts] + [len(text)]
        return [text[edges[i]:edges[i + 1]].strip() for i in range(len(self.cuts))]

    def set_slices(self, texts):
        """A new narration from one text per scene; the cuts follow the texts."""
        narration, starts = "", []
        for t in (str(x or "").strip() for x in texts):
            if narration and t:
                narration += " "
            starts.append(len(narration))
            narration += t
        self.story["narration"] = narration
        spans = _spans(narration)
        self.cuts = [next((k for k, (s, _) in enumerate(spans) if s >= c), len(spans)) for c in starts]
        if self.cuts:
            self.cuts[0] = 0

    def rewrite(self, fix):
        """Apply a text fix to the narration slice by slice, so no boundary moves. The slices go through the fix as
        one text (a rule that reads the next word still sees it); a fix that eats a separator runs on each alone."""
        if not self.scenes:
            self.story["narration"] = fix(self.narration)
            self.cuts = []
            return
        texts = self.raw_slices()
        out = fix(f" {SEP} ".join(texts))
        parts = out.split(SEP) if isinstance(out, str) else []
        if len(parts) != len(texts):
            parts = [fix(t) for t in texts]
        self.set_slices(parts)

    def drop(self, i, keep_words=True):
        """Remove scene i. keep_words: its words join the scene before (the next one, for scene 0); otherwise its
        slice leaves the narration with it."""
        if keep_words:
            del self.scenes[i]
            del self.cuts[i]
            if self.cuts:
                self.cuts[0] = 0
            return
        texts = self.raw_slices()
        del texts[i]
        del self.scenes[i]
        self.set_slices(texts)

    def state(self):
        """What a round can change: the story without its (stale) anchors, and the cuts."""
        scenes = [{k: v for k, v in s.items() if k != "at"} for s in self.scenes]
        return json.dumps({**self.story, "scenes": scenes, "_cuts": self.cuts}, ensure_ascii=False, sort_keys=True,
                          default=str)

    def out(self):
        if self.toks():  # no narration: there is nothing to anchor to, and the checks say so
            write_anchors(self)
        return self.story


def soft_cuts(narration, anchors):
    """Where the writer's anchors put each scene: exact through segments(), else each anchor (or its longest
    prefix) searched in order, else spread between the found ones. cuts[0] is 0."""
    toks = normalize_ka.tokens(narration)
    n = len(toks)
    if not anchors:
        return []
    exact = normalize_ka.segments(narration, [str(a or "") for a in anchors])
    if exact is not None:
        cuts = exact
    else:
        keys = [normalize_ka.key(t) for t in toks]
        cuts, after = [], 0
        for at in anchors:
            want = [k for k in (normalize_ka.key(p) for p in normalize_ka.tokens(str(at or ""))) if k]
            hit = None
            for size in range(len(want), 0, -1):  # the whole anchor, else its longest prefix that is there
                if size < min(2, len(want)):
                    break
                hit = _find(keys, want[:size], after)
                if hit is not None:
                    break
            cuts.append(hit)
            if hit is not None:
                after = hit + 1
        known = [(i, c) for i, c in enumerate(cuts) if c is not None]
        for i, c in enumerate(cuts):
            if c is None:
                lo = max(((j, x) for j, x in known if j < i), default=(-1, 0))
                hi = min(((j, x) for j, x in known if j > i), default=(len(cuts), n))
                cuts[i] = lo[1] + (hi[1] - lo[1]) * (i - lo[0]) // max(1, hi[0] - lo[0])
    cuts = [min(max(0, c), n) for c in cuts]
    cuts[0] = 0
    for i in range(1, len(cuts)):
        cuts[i] = max(cuts[i], cuts[i - 1])
    return cuts


def _find(keys, want, after):
    return next((i for i in range(after, len(keys) - len(want) + 1) if want and keys[i:i + len(want)] == want), None)


def write_anchors(d):
    """Write every scene's "at": the shortest prefix of its slice (4 tokens, or the whole slice if shorter) that
    segments() finds exactly at its cut, searching as the checks do from one token after the previous scene's start.
    A slice no prefix of which is unique there (it repeats words just before it) is merged into its neighbour."""
    i = 0
    while i < len(d.scenes):
        text, spans = d.narration, _spans(d.narration)
        keys = [normalize_ka.key(text[s:e]) for s, e in spans]
        a, b = d.bounds(i)
        if b <= a:  # an empty slice: the scene has no words to start on
            d.drop(i)
            continue
        after = d.cuts[i - 1] + 1 if i else 0
        size = b - a
        whole = next((k for k in range(size) if not keys[a + k]), size)  # an anchor never spans a letterless token
        ks = [k for k in range(min(4, size), size + 1) if k <= whole] + list(range(min(3, whole), 0, -1))
        chosen = next((k for k in ks if keys[a] and _find(keys, keys[a:a + k], after) == a), None)
        if chosen is None:
            first = next((k for k in range(a, b) if keys[k]), None)
            if not keys[a] and first is not None:  # the slice opens on a token with no letters ("„", "-"): the
                d.cuts[i] = first  # scene starts at its first word, which the checks' search can find
                continue
            d.drop(i)  # no prefix is unique there: the scene's words join its neighbour
            continue
        d.scenes[i]["at"] = text[spans[a][0]:spans[a + chosen - 1][1]]
        i += 1
    ats = [s["at"] for s in d.scenes]
    if d.scenes and normalize_ka.segments(d.narration, ats) != d.cuts:
        raise NormaliseError(f"anchors {ats!r} don't split the narration at {d.cuts}")


def anchors_ok(story):
    """K13: every scene's "at" is non-empty, sits in the narration in order word for word, and segments() places
    every scene (the splitter the checks read)."""
    narration = story.get("narration") or ""
    ats, pos = [], 0
    for s in story.get("scenes") or []:
        at = str((s or {}).get("at") or "").strip()
        if not at:
            return False
        i = narration.find(at, pos)
        if i < 0:
            return False
        pos = i + len(at)
        ats.append(at)
    return normalize_ka.segments(narration, ats) is not None


# ---------------------------------------------------------------- text helpers


def _walk(d, fix, narration=True, item_skip=()):
    """Apply fix to the narration (slice by slice) and every text a viewer sees: the story's titles, every scene's
    string fields, list items and the string fields of item and object slots (which ka_check.screen_texts reads)."""
    if narration:
        d.rewrite(fix)
    for key in TOP_TEXT:
        if isinstance(d.story.get(key), str):
            d.story[key] = fix(d.story[key])

    def inner(obj):
        for k, v in list(obj.items()):
            if isinstance(v, str) and k not in SKIP and k not in item_skip:
                obj[k] = fix(v)

    brushes = catalog.load_all()
    for sc in d.scenes:
        slots = (brushes.get(str(sc.get("type"))) or {}).get("slots") or {}
        for key, v in list(sc.items()):
            if key in SKIP or (slots.get(key) or {}).get("kind") in NOT_TEXT:
                continue  # an svg, an icon name, an enum value: markup and names, not words a viewer reads
            if isinstance(v, str):
                sc[key] = fix(v)
            elif isinstance(v, list):
                for j, x in enumerate(v):
                    if isinstance(x, str):
                        v[j] = fix(x)
                    elif isinstance(x, dict):
                        inner(x)
            elif isinstance(v, dict):
                inner(v)


def _has_figure(scene):
    return any(ch.isdigit() for k, v in scene.items() if k not in SKIP for ch in json.dumps(v, ensure_ascii=False))


# ---------------------------------------------------------------- shape


def _fix_change_scenes(d, articles, ctx):
    """A "change" brush needs a before and an after object; a model that sends only a target loses the job.

    Measured 2026-11-18: the scene carried type/at/kicker/target/change/when/unit and no "before", so the
    catalogue's own structure check rejected it and four repairs kept sending the same shape. Downgrading to a plain
    stat keeps the figure on screen with the fields the model did provide; with no number the scene goes (its words
    stay with a neighbour)."""
    i = 0
    while i < len(d.scenes):
        sc = d.scenes[i]
        if sc.get("type") != "change" or (isinstance(sc.get("before"), dict) and isinstance(sc.get("after"), dict)):
            i += 1
            continue
        value = None
        for key in ("target", "change", "value", "after"):
            v = sc.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                value = v
                break
            if isinstance(v, dict) and isinstance(v.get("value"), (int, float)):
                value = v["value"]
                break
        if value is None:
            d.drop(i)
            continue
        label = sc.get("label") or sc.get("kicker") or ""
        d.scenes[i] = {"type": "stat", "at": sc.get("at"), "value": value, **({"label": label} if label else {}),
                       **({"unit": sc["unit"]} if sc.get("unit") else {})}
        i += 1


def _fix_schema_gaps(d, articles, ctx):
    """A brush's required slots, filled where a stand-in is honest, or the scene goes. Measured 2026-11-18: a
    timeline without "end": its last item's label is the end of a timeline."""
    i = 0
    while i < len(d.scenes):
        sc = d.scenes[i]
        if sc.get("type") == "timeline":
            if not sc.get("start"):
                sc["start"] = sc.get("from") or sc.get("first") or ""
            if not sc.get("end"):
                items = sc.get("items") or []
                last = items[-1] if items and isinstance(items[-1], dict) else {}
                sc["end"] = last.get("label") or last.get("when") or ""
            if not str(sc.get("start") or "").strip() or not str(sc.get("end") or "").strip():
                d.drop(i)
                continue
        i += 1


# Georgian has no hyphenation, so a broken head has to be typeset by hand: a line that holds one word leaves a
# hole in the block, and a line that ends on a word belonging to what follows („და", „რომ") reads as a mistake.
# The limit stays in characters because the hook renders at a fixed width and the composition shrinks the size.
HANG = {"და", "თუ", "ან", "რომ", "მაგრამ", "ხოლო", "კი", "არ", "ვერ", "ამ", "ის", "ეს", "იმ", "მისი", "მათი",
        "როცა", "რადგან", "თუმცა", "ასევე", "მერე"}


def _width(words, i, j):
    """Characters a line of words[i:j] takes, spaces included."""
    return sum(len(w) for w in words[i:j]) + (j - i - 1)


def hook_lines(lines, limit=22, max_lines=4):
    """A hook headline as balanced lines: the fewest lines that read evenly, each within `limit` characters.

    The old wrap was `len(cand) <= limit`, which splits wherever the count runs out: it produced a line of one
    word and lines ending on „და". Here every split of 1..max_lines lines is scored (widest line + a penalty for
    a one-word line and for a hanging ending), and the cheapest split wins; a head that fits on one line stays on
    one line. Words are never changed or reordered.
    """
    words = " ".join(lines).split()
    if not words:
        return []
    n = len(words)
    if n == 1 or _width(words, 0, n) <= limit:
        return [" ".join(words)]
    best = None
    for k in range(1, min(max_lines, n) + 1):
        INF = float("inf")
        # dp[i][j]: (bad, widest) for the first i words in j lines; bad counts a one-word line and a hanging ending.
        # Compared lexicographically, so a split with no hole wins over a narrower one that has a hole.
        dp = [[(INF, INF)] * (k + 1) for _ in range(n + 1)]
        back = [[0] * (k + 1) for _ in range(n + 1)]
        dp[0][0] = (0, 0)
        for j in range(1, k + 1):
            for i in range(j, n + 1):
                for p in range(j - 1, i):
                    if dp[p][j - 1][0] == INF or _width(words, p, i) > limit:
                        continue
                    bad = dp[p][j - 1][0] + ((i - p == 1) and i < n) + ((i < n) and words[i - 1] in HANG)
                    cand = (bad, max(dp[p][j - 1][1], _width(words, p, i)))
                    if cand < dp[i][j]:
                        dp[i][j], back[i][j] = cand, p
        if dp[n][k][0] == INF:
            continue
        key = (dp[n][k][0], k, dp[n][k][1])  # no holes first, then fewer lines (bigger type), then the narrowest
        if best is None or key < best[0]:
            best = (key, k, [row[:] for row in back])
    if best is None:
        return [" ".join(words)]  # nothing fits the limit; the composition shrinks the size
    _, k, back = best
    out, i = [], n
    while i > 0:
        p = back[i][k]
        out.append(" ".join(words[p:i]))
        i, k = p, k - 1
    return out[::-1]


def _opening_lines(narration, limit=22, max_lines=4):
    """Hook lines from the narration's first sentence, as the voice says it: the whole sentence when it fits four
    lines, else its first clause, else the longest run of its first words that fits and doesn't end on a hanging
    word. Nothing is written that the voice doesn't say, so no fact and no number is new."""
    words = narration.split()
    end = next((k + 1 for k, w in enumerate(words) if w[-1] in ".?!"), len(words))
    sentence = [w.rstrip(".?!:;,") if k == end - 1 else w for k, w in enumerate(words[:end])]

    def fits(ws):
        lines = hook_lines(ws, limit, max_lines)
        return bool(lines) and len(lines) <= max_lines and all(len(x) <= 24 for x in lines)

    clause = next((k + 1 for k, w in enumerate(sentence) if w.endswith((",", ";", ":"))), None)
    for cand in (sentence, [w.rstrip(",;:") for w in sentence[:clause]] if clause else None):
        if cand and fits(cand):
            return hook_lines(cand, limit, max_lines)
    for size in range(len(sentence), 0, -1):
        cand = [w.rstrip(",;:") for w in sentence[:size]]
        if cand[-1] not in HANG and fits(cand):
            return hook_lines(cand, limit, max_lines)
    return []


def _fix_first_scene(d, articles, ctx):
    """The first scene must be a hook (engine.structure_problems). A story that opens on another scene gets a hook
    inserted before it, its lines from the narration's first sentence: renaming the opening scene to a hook left it
    without the hook's required "lines" and kept a mark that belonged to another brush. The hook's slice is taken
    from the opening words by seat, which never drops it."""
    if not d.scenes or d.scenes[0].get("type") == "hook":
        return
    lines = _opening_lines(d.narration)
    if not lines:
        return
    d.scenes.insert(0, {"type": "hook", "lines": lines})
    n = len(d.toks())
    first = min(len(normalize_ka.tokens(" ".join(lines))), n)
    nxt = d.cuts[1] if len(d.cuts) > 1 else n
    d.cuts = [0, min(first, nxt)] + d.cuts[1:]


# ---------------------------------------------------------------- media


def _drop_pictograms(d, articles, ctx):
    """N10: a story about a death or the crime family carries no pictograms: its sign scenes go (their words stay),
    a stat loses its icon and the story its motif. Measured 2026-11-18: four repair passes each returned a sign."""
    if not news_check.no_pictograms(d.story):
        return
    for i in range(len(d.scenes) - 1, -1, -1):
        if d.scenes[i].get("type") == "sign":
            d.drop(i)
    for sc in d.scenes:
        if sc.get("type") == "stat":
            sc.pop("icon", None)
    d.story.pop("motif", None)


def _drop_unknown_icons(d, articles, ctx):
    """An icon or motif the library can't resolve is a dead scene, not a style choice: the decoration goes and the
    scene keeps its text. The story's own motif too (icons.motif_problems: 9 jobs on 2026-11-18)."""
    top = d.story.get("motif")
    if isinstance(top, str) and top.strip() and not icons.resolve(top):
        d.story.pop("motif", None)
    for sc in d.scenes:
        for key in ("icon", "motif", "morph_from"):
            v = sc.get(key)
            if isinstance(v, str) and v.strip() and not icons.resolve(v):
                sc.pop(key, None)
        art = sc.get("art")
        if isinstance(art, list):
            kept = [node for node in art if not (isinstance(node, dict) and isinstance(node.get("icon") or node.get(
                "motif"), str) and (node.get("icon") or node.get("motif")).strip() and not icons.resolve(
                node.get("icon") or node.get("motif")))]
            if kept:
                sc["art"] = kept
            else:
                sc.pop("art", None)


# ---------------------------------------------------------------- surface


_DASH_RE = re.compile(r"\s*[–—]\s*")


def no_dashes(text):
    """The house rule bans the en and em dash everywhere we publish. A dash between digits, or between a digit and
    a Georgian suffix, is a range or an ordinal and becomes a hyphen ("24–ე" is ოცდამეოთხე; "24, ე" can't be read);
    any other dash becomes a comma, the reading the model meant."""
    if not isinstance(text, str) or not _DASH_RE.search(text):
        return text
    out = re.sub(r"(?<=\d)\s*[–—]\s*(?=[\dა-ჰ])", "-", text)
    out = re.sub(r"(?<=[ა-ჰ])\s*[–—]\s*(?=\d)", "-", out)
    out = _DASH_RE.sub(", ", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def _no_dashes(d, articles, ctx):
    _walk(d, no_dashes)


def separators(text):
    """K12 and K21 by rewriting: "!" becomes a full stop, an ellipsis a comma, 7.3% becomes 7,3%. Nothing here
    changes what a sentence means, only how it is punctuated."""
    if not isinstance(text, str):
        return text
    out = re.sub(r"(?<=\d)\.(?=\d)", ",", text)
    out = out.replace("…", ",").replace("...", ",")
    out = out.replace("!", ".")
    out = re.sub(r"\s*[,;]\s*(?=[.!?]|$)", "", out)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()


def _fix_separators(d, articles, ctx):
    _walk(d, separators, item_skip=("when",))  # a rail's "when" is a date: news_check.date_key reads its points


def _drop_stray_latin(d, articles, ctx):
    """K19: a plain lowercase English word in Georgian text is dropped (measured 2026-11-18: "ardi" survived four
    repairs). A word K19 itself accepts, a known name's word from the lexicon or the script's "say", stays."""
    say = d.story.get("say") if isinstance(d.story.get("say"), dict) else {}
    known = normalize_ka.names(say)
    known = set(known) | {w for k in known for w in k.split()}  # as ka_check reads it

    def fix(text):
        if not isinstance(text, str) or not text or not re.search(r"[ა-ჰ]", text):
            return text  # a Latin-only string is a name or a code, not Georgian text with a stray word
        out = re.sub(r"(?<![A-Za-z0-9.@/_-])[a-z]{3,}(?![A-Za-z0-9.@/_])",
                     lambda m: m.group(0) if m.group(0) in known else "", text)
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([,.;:!?])", r"\1", out)
        return out.strip()

    _walk(d, fix)


RELATIVE_DAYS = ("დღეს", "გუშინ", "გუშინწინ", "ხვალ", "ზეგ")


def _spell_relative_days(d, articles, ctx):
    """N4: a relative day („დღეს", „გუშინ") is dropped. A video is watched for days; naming the date instead would
    add a numeral the source never said, which N2 rejects (measured 2026-11-18)."""
    def fix(text):
        if not isinstance(text, str) or not text:
            return text
        out = text
        for word in RELATIVE_DAYS:
            out = re.sub(rf"(?<![ა-ჰ]){word}(?![ა-ჰ])[,\s]*", "", out)
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([,.;:])", r"\1", out)
        return out.strip()

    _walk(d, fix)


# Georgian word forms a model gets wrong often enough that a person has had to correct them; each entry is one the
# owner flagged or kaeasy records as a common error. Longest first, so a longer form isn't half-replaced.
KA_WRONG_FORMS = [
    ("გაეცნა", "გაეცნო"),  # owner, 2026-11-16, after a live reel printed it in the hook
]


def _ka_forms(d, articles, ctx):
    def fix(text):
        if not isinstance(text, str):
            return text
        for wrong, right in KA_WRONG_FORMS:
            text = text.replace(wrong, right)
        return text

    _walk(d, fix)


# ---------------------------------------------------------------- sourced


def _corpus(articles):
    return news_check.flat(" ".join(str(a.get("text") or a.get("content_text") or "") if isinstance(a, dict)
                                    else str(a) for a in (articles or [])))


def _drop_unverbatim_quotes(d, articles, ctx):
    """N3, K14: a quote must appear word for word in a source. In the narration a quote mark around words no
    article has is removed (the words stay); a quote scene whose quote no article has goes, with the sentence where
    the narration repeats it."""
    corpus = _corpus(articles)
    if not corpus:
        return

    def unwrap(text):
        def repl(m):
            inner = m.group(1)
            return m.group(0) if news_check.flat(inner.replace(SEP, " ")) in corpus else inner
        return re.sub(r"„([^“”„]+)[“”]", repl, text)

    d.rewrite(unwrap)
    i = 0
    while i < len(d.scenes):
        sc = d.scenes[i]
        if sc.get("type") == "quote":
            q = str(sc.get("quote") or sc.get("text") or "")
            if q and news_check.flat(q) not in corpus:
                d.rewrite(lambda t, q=q: t.replace(q, "").replace(",,", ",").strip())
                d.drop(i)
                continue
        i += 1


def _drop_unsupported(d, articles, ctx):
    """A quote scene the sources don't contain, or with no speaker, goes (its words stay with a neighbour). This was
    writer._repair_scenes, which also dropped every sign scene whenever three scenes were left; that blanket drop is
    gone: a sign stays when its part of the narration says its verb (seat, _fix_sign_verbs)."""
    if not articles:
        return

    def norm(t):
        return re.sub(r"\s+", " ", t or "").strip().lower().strip("„“\"'«».,;:!?")

    joined = norm("\n".join(str(a.get("text") or "") if isinstance(a, dict) else str(a) for a in articles))
    for i in range(len(d.scenes) - 1, -1, -1):
        sc = d.scenes[i]
        if sc.get("type") != "quote" or len(d.scenes) <= 3:
            continue
        q = norm(sc.get("text") or "")
        if (q and q not in joined) or not str(sc.get("by") or "").strip():
            d.drop(i)


# ---------------------------------------------------------------- spoken


_LATIN_KA = {
    "a": "ა", "b": "ბ", "c": "კ", "d": "დ", "e": "ე", "f": "ფ", "g": "გ", "h": "ჰ", "i": "ი",
    "j": "ჯ", "k": "კ", "l": "ლ", "m": "მ", "n": "ნ", "o": "ო", "p": "პ", "q": "ქ", "r": "რ",
    "s": "ს", "t": "ტ", "u": "უ", "v": "ვ", "w": "ვ", "x": "ქს", "y": "ი", "z": "ზ",
}
# A known brand keeps its conventional Georgian spelling. CLAUDE.md wants these in lexicon_ka.json (approved); they
# move there with the lexicon review, so this table is not grown further.
_BRANDS = {"wildberries": "ვაილდბერიზ", "openai": "ოუფენეი", "google": "გუგლი", "facebook": "ფეისბუქი",
           "youtube": "იუთუბი", "tiktok": "ტიკტოკი", "instagram": "ინსტაგრამი", "telegram": "ტელეგრამი",
           "amazon": "ამაზონი", "meta": "მეტა", "apple": "ეფლი", "microsoft": "მაიკროსოფტი"}


def _spoken_form(name):
    low = name.lower()
    if low in _BRANDS:
        return _BRANDS[low]
    ka = "".join(_LATIN_KA.get(ch, ch) for ch in low)
    return ka if ka and not normalize_ka.LATIN.search(ka) else None


def _fix_unspoken_names(d, articles, ctx):
    """K20: a Latin name gets a Georgian spoken form in "say" (the written name stays Latin on screen), and a "say"
    value in Latin letters is spelled in Georgian ones. Measured 2026-11-18: "Wildberries" survived every repair."""
    narration = d.narration
    say = d.story.get("say") if isinstance(d.story.get("say"), dict) else {}
    for k, v in list(say.items()):
        if isinstance(v, str) and normalize_ka.LATIN.search(v):
            fixed = _spoken_form(v) if v.isascii() else None
            if fixed:
                say[k] = fixed
    if narration:
        for name in normalize_ka.unspoken(narration, say):
            if name and name.isascii():
                ka = _spoken_form(name)
                if ka:
                    say[name] = ka
    if say:
        d.story["say"] = say


def _fix_say_letters(d, articles, ctx):
    normalize_ka.fix_say_letters(d.story)


# ---------------------------------------------------------------- clamp


def _limits():
    """field -> the smallest limit any brush sets for it, plus a floor for fields the catalogue omits."""
    out = {"kicker": 24, "headline": 40, "text": 200, "big": 12, "place": 30, "sub": 30,
           "end": 24, "weekday": 20, "change": 24, "value": 12, "start": 24, "finish": 24,
           "to": 24, "from": 24, "when": 24, "where": 30, "via": 32}
    for brush in (catalog.load_all() or {}).values():
        for field, spec in ((brush or {}).get("slots") or {}).items():
            lim = None
            if isinstance(spec, dict):
                lim = spec.get("max")
                for inner in (spec.get("of") or {}).values():
                    if isinstance(inner, dict) and inner.get("max"):
                        lim = min(lim or inner["max"], inner["max"])
            if isinstance(lim, int) and lim > 0:
                out[field] = min(out.get(field, lim), lim)
    return out


LIMITS = _limits()


def clamp(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:—-")


def _fix_long_text(d, articles, ctx):
    """A quote or point that runs into the like/share rail is clipped (measured 2026-11-18: x=956 below y=1100);
    the fuller wording stays in the narration."""
    RAIL_SAFE = 24
    for sc in d.scenes:
        for key in ("text", "quote", "sub", "label", "headline"):
            v = sc.get(key)
            if isinstance(v, str) and len(v) > 90 and sc.get("type") in ("quote", "points", "stat"):
                cut = v[:90]
                if " " in cut:
                    cut = cut.rsplit(" ", 1)[0]
                # a quote's clip stays a verbatim prefix: an added full stop made it a quote no source has, and
                # the next round's N3 pass dropped the scene (_drop_unverbatim_quotes)
                sc[key] = cut.rstrip(" ,.") + ("" if sc.get("type") == "quote" else ".")
        for key in ("items", "lines"):
            v = sc.get(key)
            if isinstance(v, list):
                sc[key] = [(x[:RAIL_SAFE * 2].rstrip() if isinstance(x, str) and len(x) > RAIL_SAFE * 2 else x)
                           for x in v]


def _clamp_texts(d, articles, ctx):
    """A text over its slot's limit is clamped at a word boundary: the scene's own brush's limit, else the floor in
    LIMITS for a field the brush doesn't set."""
    brushes = catalog.load_all() or {}
    for sc in d.scenes:
        slots = (brushes.get(str(sc.get("type"))) or {}).get("slots") or {}
        for key, floor in LIMITS.items():
            v = sc.get(key)
            if not isinstance(v, str):
                continue
            spec = slots.get(key)
            limit = None
            if isinstance(spec, dict):
                limit = spec.get("max")
                if not isinstance(limit, int):
                    inner = [i.get("max") for i in (spec.get("of") or {}).values() if isinstance(i, dict)]
                    inner = [i for i in inner if isinstance(i, int)]
                    limit = min(inner) if inner else None
            if not isinstance(limit, int):
                limit = floor
            if len(v) > limit:
                sc[key] = clamp(v, limit)
        lines = sc.get("lines")
        if isinstance(lines, list):
            sc["lines"] = [clamp(x, 24) if isinstance(x, str) else x for x in lines]


# ---------------------------------------------------------------- repeats


def _fix_repeats(d, articles, ctx):
    """Two scenes of one type in a row read as one long beat (motion repeat): the second merges into the first. Its
    fields fill any the first left empty and its words join the first's slice."""
    guard = _director_guard(d, articles, ctx)
    i = 1
    while i < len(d.scenes):
        if d.scenes[i - 1].get("type") == d.scenes[i].get("type") and d.scenes[i].get("type") not in ("hook", "end"):
            merged = _merged(d, i)
            if guard and guard(merged) > guard(d):
                i += 1  # merging would break the director's own gate (two speakers): the checks name the repeat
                continue
            d.story, d.cuts = merged.story, merged.cuts
            continue
        i += 1


def _merged(d, i):
    """The draft with scene i merged into scene i - 1 (as a copy)."""
    trial = Draft(copy.deepcopy(d.story), list(d.cuts))
    prev = trial.scenes[i - 1]
    for k, v in trial.scenes[i].items():
        if k not in ("at", "type") and (k not in prev or not prev[k]):
            prev[k] = v
    trial.drop(i)
    return trial


# ---------------------------------------------------------------- seat


def _said_rules(scene):
    """[(what, test(text) -> bool)]: what a scene's own part of the narration must say. what is "em" or "edge" (a
    decoration that can go) or "scene" (the scene can't stand without it)."""
    out = []
    t = scene.get("type")
    em = scene.get("em")
    b = catalog.load_all().get(t) or {}
    if (isinstance(em, str) and em.strip() and (b.get("em") or {}).get("fields")
            and len(em.split()) <= marks.MAX_WORDS and len(em) <= marks.MAX_CHARS and marks.locate(scene)):
        out.append(("em", lambda text, em=em: marks.said(em, text)))
    if t == "link" and isinstance(scene.get("edge"), str) and scene["edge"].strip():
        out.append(("edge", lambda text, e=scene["edge"]: marks.said(e, text)))
    if t == "sign" and scene.get("verb") in icons.VERBS:
        out.append(("scene", lambda text: any(icons.said(v, text) for v in icons.VERBS)))
    if t == "stat" and str(scene.get("value") or "").strip():
        out.append(("scene", lambda text, v=scene.get("value"): value_said(v, text)))
    return out


# Case endings a spelled numeral takes in a sentence: „სამი", „ორ პროცენტამდე", „ათიდან"
_NUM_ENDINGS = ("", "ი", "ის", "ს", "ით", "ად", "ზე", "ში", "მა", "მდე", "ამდე", "იდან", "დან", "ც", "იც", "ისა", "სა")


def value_said(value, text):
    """Does the text say a stat's value? Its digits ("57,6" for 57.6, "1 500" for 1500), or for a whole number its
    Georgian word with a case ending: the owner's rule spells numerals in speech, so „სამი" says 3."""
    v = _norm_value(marks._value_text(value) or str(value))
    if v and v in _norm_value(text):
        return True
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) != int(value) or value < 0:
        return False
    word = normalize_ka.cardinal(int(value))
    stem = word[:-1] if word.endswith("ი") else word
    return any(normalize_ka.key(w) in {stem + e for e in _NUM_ENDINGS} for w in normalize_ka.tokens(text))


def _norm_value(t):
    """A stat's value or a narration as numbers compare: "57,6" is 57.6 (the Georgian decimal comma), "1 500" is
    1500 (a space-grouped number), 3.0 is 3."""
    t = re.sub(r"\s+", " ", str(t or "")).strip().lower()
    t = re.sub(r"(?<=\d)[   ](?=\d{3}(?!\d))", "", t)
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    t = re.sub(r"(?<=\d)\.0+(?!\d)", "", t)
    return t.strip("„“\"'«».,;:!?")


def _min_end(toks, test):
    """min_end[a]: the smallest b with test(toks[a:b]) (len(toks) + 1 when none): a slice [a, b) says it iff
    min_end[a] <= b. Saying it in a longer slice can't stop, so min_end never falls as a rises."""
    n = len(toks)
    out, b = [], 1
    for a in range(n + 1):
        b = max(b, a + 1)
        while b <= n and not test(" ".join(toks[a:b])):
            b += 1
        out.append(b)
    return out


def _times(narration, n):
    """t[k]: the estimated second token k starts at (t[n]: the end), from the estimator the gate uses."""
    words = speech.estimate_words(narration)
    if not words:
        return [0.0] * (n + 1)
    toks = normalize_ka.tokens(narration)
    out, w = [], 0
    for tok in toks:
        out.append(words[min(w, len(words) - 1)]["start"])
        w += max(1, len(tok.split()))
    out.append(words[-1]["end"])
    return out


def _judge(d, rules, mins, secs):
    """(tokens, their keys, ok(i, a, b)): does tokens[a:b] meet scene i's hard constraints."""
    toks = d.toks()
    n, S = len(toks), len(d.scenes)
    keys = [normalize_ka.key(t) for t in toks]
    times = _times(d.narration, n)
    ends = [[_min_end(toks, test) for _, test in rules[i]] for i in range(S)]

    def ok(i, a, b):
        hold = speech.END_HOLD if b == n else 0.0  # the last scene stays up after the last word (scene_frames)
        return (b - a >= mins[i] and (times[b] - times[a] + hold) / PACE_FAST >= secs[i]
                and all(e[a] <= b for e in ends[i]))

    return toks, keys, ok


def _meets(d, rules, mins, secs, cuts):
    """Do these cuts already meet every hard constraint (with a letter at every cut, so they can be anchored)?"""
    toks, keys, ok = _judge(d, rules, mins, secs)
    bounds = list(zip(cuts, cuts[1:] + [len(toks)]))
    return (bool(cuts) and cuts[0] == 0 and all(keys[c] for c in cuts[1:] if c < len(toks))
            and all(ok(i, a, b) for i, (a, b) in enumerate(bounds)))


def _stills(d, cuts):
    """How many "motion still" findings the draft gate (motion_rules.draft_problems) gives these cuts."""
    from tt_shorts import motion_rules
    trial = Draft(copy.deepcopy(d.story), list(cuts))
    try:
        write_anchors(trial)
        return sum(1 for p in motion_rules.draft_problems(trial.story) if p.startswith("motion still"))
    except Exception:  # a draft the motion rules can't read (a string "art"): no judgement either way
        return 0


def _partition(d, rules, mins, secs, targets):
    """The cheapest tiling of the tokens into len(d.scenes) slices that meets every constraint, or None.

    Constraints per slice: at least its type's words (K9) and, at the fastest voice, its seconds; one occurrence of
    everything its scene must say (rules). Cost: a cut after a sentence is free, after a comma 1, mid-clause 4; each
    token over MAX_WORDS costs 1 (the end card is exempt); each token a cut moves from targets costs LAMBDA. Ties go
    to the smaller move, so the seat of a seated story is itself."""
    toks, keys, ok = _judge(d, rules, mins, secs)
    n, S = len(toks), len(d.scenes)

    def bcost(c):
        last = toks[c - 1][-1] if c > 0 and toks[c - 1] else ""
        return 0 if last in ".?!:“" else 1 if last in ",;" else 4

    def over(i, size):
        return 0 if d.scenes[i].get("type") == "end" else max(0, size - MAX_WORDS)

    valid = [c for c in range(1, n) if keys[c]]
    layer = {0: (0, 0, None)}
    back = [layer]
    for i in range(1, S):
        nxt = {}
        for c in valid:
            best = None
            for p, (cost, dist, _) in layer.items():
                if p >= c or not ok(i - 1, p, c):
                    continue
                move = abs(c - targets[i])
                cand = (cost + bcost(c) + over(i - 1, c - p) + LAMBDA * move, dist + move, p)
                if best is None or cand[:2] < best[:2]:
                    best = cand
            if best is not None:
                nxt[c] = best
        layer = nxt
        back.append(layer)
        if not layer:
            return None
    best = None
    for p, (cost, dist, _) in layer.items():
        if ok(S - 1, p, n):
            cand = (cost + over(S - 1, n - p), dist, p)
            if best is None or cand[:2] < best[:2]:
                best = cand
    if best is None:
        return None
    cuts, p = [], best[2]
    for i in range(S - 1, -1, -1):
        cuts.append(p)
        p = back[i][p][2] if i else None
    return cuts[::-1]


def _droppable(d):
    """Scenes seat may remove: never the hook that opens the film, never the end card that closes it."""
    last = len(d.scenes) - 1
    return [i for i, s in enumerate(d.scenes)
            if not (i == 0 and s.get("type") == "hook") and not (i == last and s.get("type") == "end")]


def seat(d, articles, ctx):
    """Place every scene's cut (replaces _fix_anchors, _hard_anchor, _drop_short_scenes, _tidy_end and
    _shorten_story). When no tiling meets every constraint, one removal at a time restores it: a mark or an edge the
    voice can't say there goes first, then a scene that needs words no slice can give it, then (too few words for
    every scene's minimum) the least-needed scene, keeping its words. Never below three scenes. Then the length
    window: whole sentence-aligned slices leave with their scenes until the film fits."""
    if not d.scenes or not d.toks():
        return
    words, seconds = catalog.min_words(), catalog.min_scene()
    for _ in range(len(d.scenes) * 3 + 3):
        n = len(d.toks())
        rules = [_said_rules(s) for s in d.scenes]
        mins = [max(1, words.get(str(s.get("type")), catalog.MIN_WORDS_DEFAULT)) for s in d.scenes]
        secs = [seconds.get(str(s.get("type")), catalog.MIN_SECONDS_DEFAULT) for s in d.scenes]
        cuts = _partition(d, rules, mins, secs, d.cuts)
        if cuts is not None:
            # The cost only approximates stillness (MAX_WORDS): where the writer's own cuts already meet every
            # constraint, seat's are taken only if the draft gate finds no more stills in them.
            if cuts != d.cuts and _meets(d, rules, mins, secs, d.cuts) and _stills(d, cuts) > _stills(d, d.cuts):
                break
            d.cuts = cuts
            break
        if not _relax(d, rules, mins, secs, n, _director_guard(d, articles, ctx)):
            return  # nothing code may remove makes it fit: the checks name what is left
    _fit_length(d, ctx, articles)


def _relax(d, rules, mins, secs, n, guard=None):
    """One removal that brings seat closer to a tiling; False when there is none. guard(draft): the director's
    problems; a scene whose removal adds one stays."""
    now = guard(d) if guard else 0
    keeps = (lambda i: guard(_without(d, i)) <= now) if guard else (lambda i: True)
    actions = [(i, what) for i, r in enumerate(rules) for what, _ in r if what in ("em", "edge")]
    if len(d.scenes) > 3:
        actions += [(i, "scene") for i, r in enumerate(rules) if any(w == "scene" for w, _ in r)
                    and i in _droppable(d) and keeps(i)]

    def feasible(relaxed):
        trial = [list(r) for r in rules]
        for k in relaxed:
            i, what = actions[k]
            trial[i] = [] if what == "scene" else [x for x in trial[i] if x[0] != what]
        return _partition(d, trial, mins, secs, d.cuts) is not None

    relaxed = set(range(len(actions)))
    if actions and feasible(relaxed):  # a said-constraint is in the way: find a minimal set of them, remove one
        for k in reversed(range(len(actions))):  # keep a scene before a mark: restore the costliest removals first
            if feasible(relaxed - {k}):
                relaxed.discard(k)
        _apply(d, *actions[min(relaxed)])
        return True
    cand = [i for i in _droppable(d) if keeps(i)] if len(d.scenes) > 3 else []
    if cand:  # too few words or seconds for every scene: the least-needed goes, no figure first, then the shortest
        i = min(cand, key=lambda k: (_joins_twins(d, k), _has_figure(d.scenes[k]), d.bounds(k)[1] - d.bounds(k)[0], k))
        d.drop(i)
        return True
    return False


def _apply(d, i, what):
    if what == "scene":
        d.drop(i)
    else:
        d.scenes[i].pop(what, None)


def _joins_twins(d, i):
    """Removing scene i would put two scenes of one type side by side (A X A -> A A), which _fix_repeats then
    merges into one: a second removal nobody chose."""
    return 0 < i < len(d.scenes) - 1 and d.scenes[i - 1].get("type") == d.scenes[i + 1].get("type")


def _without(d, i, keep_words=True):
    trial = Draft(copy.deepcopy(d.story), list(d.cuts))
    trial.drop(i, keep_words)
    return trial


def _director_guard(d, articles, ctx):
    """f(draft) -> the director's own gates (directors.story_problems) for this story, or None without a director.
    A removal seat makes must not add one: a witness film keeps its two quotes."""
    from tt_shorts import directors
    name = d.story.get("director") or ctx.get("director")
    if isinstance(name, dict):
        name = name.get("id")
    if not isinstance(name, str) or not name:
        return None
    try:
        if not directors.get(name).get("gates"):
            return None  # a director with no gates of its own has nothing a removal could break
    except directors.DirectorError:
        return None
    category = d.story.get("category", "")

    def problems(draft):
        if ctx.get("facts") is None:  # read the articles once per normalise call, and only when a removal asks
            ctx["facts"] = directors.facts([a for a in articles or [] if isinstance(a, str)], category) or {}
        if not ctx["facts"]:
            return 0
        return len(directors.story_problems({**draft.story, "director": name}, ctx["facts"]))

    return problems


def _fit_length(d, ctx, articles=()):
    """The length window at the slowest voice: while the film would run past max_seconds, remove the scene (never
    the hook or the end) whose slice is whole sentences, preferring one with no figure, then the longest, as long as
    the film stays above min_seconds at the fastest voice. With no such slice the length is left to the checks."""
    ctx = ctx or {}
    # Without a window from the caller the ceiling is the one engine.check_story applies today (60 s on the
    # estimate, the end card's hold included), so nothing the gate accepts is cut. The calibrated format window
    # (max_seconds at the slowest voice) comes in with the gate parity stage, when check_story reads it too.
    if ctx.get("max_seconds"):
        top = float(ctx["max_seconds"]) * PACE_SLOW
    else:
        top = GATE_MAX_ESTIMATE - speech.END_HOLD
    bottom = float(ctx.get("min_seconds") or MIN_SECONDS) * PACE_FAST
    while len(d.scenes) > 3:
        toks = d.toks()
        times = _times(d.narration, len(toks))
        if times[-1] <= top:
            return

        def whole(i):
            a, b = d.bounds(i)
            return a > 0 and b > a and toks[a - 1][-1] in ".?!" and toks[b - 1][-1] in ".?!"

        cand = [i for i in _droppable(d) if whole(i) and not _joins_twins(d, i)
                and times[-1] - (times[d.bounds(i)[1]] - times[d.bounds(i)[0]]) >= bottom]
        guard = _director_guard(d, articles, ctx)
        if guard:
            now = guard(d)
            cand = [i for i in cand if guard(_without(d, i, keep_words=False)) <= now]
        if not cand:
            return
        i = min(cand, key=lambda k: (_has_figure(d.scenes[k]), -(d.bounds(k)[1] - d.bounds(k)[0]), k))
        d.drop(i, keep_words=False)


# ---------------------------------------------------------------- marks


def _fix_em_marks(d, articles, ctx):
    """N11: an em mark is one phrase, in a brush that takes one, short, on the scene's own text and said in its
    part of the narration; a link's edge is said there. A mark that fails any of these goes (the scene stays)."""
    brushes = catalog.load_all()
    for i, sc in enumerate(d.scenes):
        if "em" in sc:
            em = sc["em"]
            where = ((brushes.get(sc.get("type")) or {}).get("em") or {}).get("fields") or []
            if (not isinstance(em, str) or not em.strip() or not where or len(em.split()) > marks.MAX_WORDS
                    or len(em) > marks.MAX_CHARS or not marks.locate(sc) or not marks.said(em, d.part(i))):
                sc.pop("em", None)
        edge = sc.get("edge")
        if sc.get("type") == "link" and isinstance(edge, str) and edge.strip() and not marks.said(edge, d.part(i)):
            sc.pop("edge", None)


def _fix_sign_verbs(d, articles, ctx):
    """N10: a sign's verb is one its part of the narration says: another verb the part says replaces it, else the
    sign goes (its words stay)."""
    i = 0
    while i < len(d.scenes):
        sc = d.scenes[i]
        if sc.get("type") == "sign" and sc.get("verb") in icons.VERBS:
            part = d.part(i)
            if not icons.said(sc["verb"], part):
                chosen = next((v for v in icons.VERBS if icons.said(v, part)), None)
                if chosen is None:
                    d.drop(i)
                    continue
                sc["verb"] = chosen
        i += 1


def _drop_unsaid_stats(d, articles, ctx):
    """A stat whose value its part of the narration doesn't say goes (its words stay), while three scenes remain:
    writer._repair_scenes' stat rule, judged on the seated slices."""
    for i in range(len(d.scenes) - 1, -1, -1):
        sc = d.scenes[i]
        if sc.get("type") != "stat" or len(d.scenes) <= 3 or not str(sc.get("value") or "").strip():
            continue
        if not value_said(sc.get("value"), d.part(i)):
            d.drop(i)


# ---------------------------------------------------------------- the loop


PASSES = (
    ("shape", _fix_change_scenes), ("shape", _fix_schema_gaps), ("shape", _fix_first_scene),
    ("media", _drop_pictograms), ("media", _drop_unknown_icons),
    ("surface", _no_dashes), ("surface", _fix_separators), ("surface", _drop_stray_latin),
    ("surface", _spell_relative_days), ("surface", _ka_forms),
    ("sourced", _drop_unverbatim_quotes), ("sourced", _drop_unsupported),
    ("spoken", _fix_unspoken_names), ("spoken", _fix_say_letters),
    ("clamp", _fix_long_text), ("clamp", _clamp_texts),
    ("repeats", _fix_repeats),
    ("seat", seat),
    ("marks", _fix_em_marks), ("marks", _fix_sign_verbs), ("marks", _drop_unsaid_stats),
)


def _change(before, after):
    """A short account of what one pass changed."""
    out = []
    if len(before.scenes) != len(after.scenes):
        out.append(f"scenes {len(before.scenes)}->{len(after.scenes)}")
    elif [s.get("type") for s in before.scenes] != [s.get("type") for s in after.scenes]:
        out.append("scene types")
    if before.narration != after.narration:
        out.append(f"narration {len(before.toks())}->{len(after.toks())} tokens")
    if before.cuts != after.cuts:
        out.append(f"cuts {before.cuts}->{after.cuts}")
    return ", ".join(out) or "fields"


def normalise(story, articles=(), ctx=None, rounds=5):
    """story after every pass has run to a fixpoint -> Result(story, status, log). status: "settled", "cycle" or
    "unsettled"; log: [{"round", "pass", "change"}] for every pass that changed something. The input isn't
    modified. ctx: {"cluster", "min_seconds", "max_seconds"} (the format's window; the story format's by default)."""
    ctx = dict(ctx or {})
    d = Draft.of(story)
    log, seen = [], {}
    status = "unsettled"
    for r in range(rounds):
        key = d.state()
        if key in seen:
            status = "cycle"
            break
        seen[key] = r
        for group, p in PASSES:
            before = Draft(copy.deepcopy(d.story), list(d.cuts))
            p(d, articles or [], ctx)
            if d.state() != before.state():
                log.append({"round": r, "pass": f"{group}:{p.__name__.lstrip('_')}", "change": _change(before, d)})
        if d.state() == key:
            status = "settled"
            break
    return Result(d.out(), status, log)
