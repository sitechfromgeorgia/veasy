"""The morning digest (ROADMAP B7, rubric „დილის N ამბავი“): 2-3 checked stories in one 45-60 s video, no writer.

Code joins what already passed the checks; nothing new is written about the news:
  - each story is checked again with its own articles (engine.check_story); one with problems is refused;
  - the narration is a short intro (the rubric's words: „დილის ორი ამბავი ერთ ვიდეოში.“), then each story's
    first sentences, then the outro („დეტალები იხილე <site>-ზე.“) and the brand's call to action; a story's
    sentences are taken only from its narration before its outlets line (the sources scene) or its end card;
  - the opening is the first story's own hook (its category and its checked lines), so frame 0 shows a real
    headline, not a list of categories; the rubric's chip above it says „დილის N ამბავი“. Every later story opens
    with a chapter card (its number of the total, its category, its own hook lines) at its first words;
  - each story keeps its own content scenes whose first words fall in the sentences taken (at most 2 per story;
    one whose part became too short for its brush, or whose mark the part no longer says, loses it);
  - length control: every story starts with its first sentence; while the estimated length (speech.estimate_words,
    the timing the checks use) is under the format's minimum + 2 s, the story that has said the least gets its
    next sentence, as long as the video stays under the maximum - 3 s (digest: 45-60 s, so 47-57 s);
  - the result is a story like any other (program digest, rubric digest) and goes through every check again:
    the news rules against all the stories' articles, Georgian, timing, captions.
The count is the real one: two stories make „დილის 2 ამბავი“, never three.
"""
import re

from tt_shorts import catalog, formats, marks, meta, news_check, speech

MAX_SCENES = 2  # a story's own content scenes in the digest
SKIP = ("hook", "sources", "end")


class DigestError(ValueError):
    pass


def sentences(text):
    """The sentences of a narration (a full stop outside „…“ ends one)."""
    out, cur, depth = [], [], 0
    for i, ch in enumerate(text):
        cur.append(ch)
        if ch == "„":
            depth += 1
        elif ch in "“”" and depth:
            depth -= 1
        elif ch == "." and depth == 0 and (i + 1 == len(text) or text[i + 1].isspace()):
            s = "".join(cur).strip()
            if s:
                out.append(s)
            cur = []
    rest = "".join(cur).strip()
    if rest:
        out.append(rest)
    return out


def body(story):
    """A story's sentences before its outlets line or its end card (what it says about the news)."""
    narration = story.get("narration", "")
    pos, stop = 0, len(narration)
    for s in story.get("scenes") or []:
        at = (s.get("at") or "").strip()
        i = narration.find(at, pos) if at else -1
        if i < 0:
            continue
        if s.get("type") in ("sources", "end"):
            stop = i
            break
        pos = i + len(at)
    return sentences(narration[:stop])


def _plain(text):
    """Text as an anchor matches it (speech.anchor ignores the quote marks): no „“”, single spaces."""
    return " ".join(re.sub(r'[„“”"]', "", text).split())


def _words(text):
    return len(text.split())


def _first_words(text, n=3):
    return " ".join(text.replace("„", "").replace("“", "").split()[:n]).rstrip(".,:")


def _part_words(story, i):
    return len(news_check.scene_part(story, i).split())


def _seconds(story):
    try:
        return speech.scene_frames(story, speech.estimate_words(story["narration"]))[-1] / speech.FPS
    except (ValueError, RuntimeError, IndexError):
        return None


def compose(items, counts, rubric, brand, cluster):
    """One digest story from the checked stories (items: [{"story", "articles"}]) taking counts[i] sentences of
    story i. Pure apart from the brand pack."""
    from tt_shorts import brand as packs
    b = packs.load(brand)
    words = rubric.get("words") or {}
    n = len(items)
    labels = [meta.category_label(it["story"].get("category", ""), b) for it in items]
    intro = words["intro"].format(count=(words.get("count") or {}).get(str(n), str(n)))
    outro = words["outro"].format(site=b["wordmark"]["text"])
    sid = f"digest-{cluster['id']}"
    cta = meta.cta_for(sid, b)
    scenes, parts, say = [], [intro], {}
    for k, (it, take) in enumerate(zip(items, counts)):
        st = it["story"]
        said = body(st)[:take]
        text = " ".join(said)
        say.update(st.get("say") or {})
        hook = next((s for s in st.get("scenes") or [] if s.get("type") == "hook"), {})
        lines = list(hook.get("lines") or [said[0]])
        if k == 0:  # the opening is the first story's own headline, from the intro on
            scenes.append({"type": "hook", "at": _first_words(intro, 2), "kicker": labels[0], "lines": lines})
        else:
            scenes.append({"type": "chapter", "at": _first_words(said[0]), "kicker": labels[k], "n": k + 1, "of": n,
                           "lines": lines})
        rest = " ".join(said[1:])
        own = 0
        for s in st.get("scenes") or []:
            at = (s.get("at") or "").strip()
            if s.get("type") in SKIP or not at or own >= MAX_SCENES:
                continue
            if _plain(at) in _plain(rest):
                scenes.append({key: v for key, v in s.items()})
                own += 1
        parts.append(text)
    parts += [outro, f"{cta}."]
    story = {"id": sid, "lang": "ka", "brand": b["name"], "category": "general", "date": cluster["created_at"],
             "sources": list(cluster.get("sources") or []), "cta": cta, "narration": " ".join(parts),
             "scenes": scenes + [{"type": "end", "at": _first_words(outro, 2)}],
             "digest": {"stories": [it["story"].get("id") for it in items], "sentences": list(counts)}}
    if say:
        story["say"] = say
    return _tidy(story)


def _tidy(story):
    """Drop a copied scene whose part became too short for its brush, and a mark its part no longer says."""
    brushes = catalog.load_all()
    while True:
        for i, s in enumerate(story["scenes"]):
            if s["type"] in ("hook", "chapter", "end"):
                continue
            if _part_words(story, i) < brushes[s["type"]]["min_words"]:
                del story["scenes"][i]
                break
            if s.get("em") and not marks.said(s["em"], news_check.scene_part(story, i)):
                s.pop("em")
        else:
            return story


def build(data, rubric, brand=None):
    """The source's data (sources/stories.py) -> the digest story, its length inside the rubric's format."""
    from tt_shorts import engine
    items = data.get("stories") or []
    if not 2 <= len(items) <= 3:
        raise DigestError(f"a digest takes 2-3 checked stories, got {len(items)}")
    for it in items:
        bad = engine.check_story(it["story"], it["articles"])
        if bad:
            raise DigestError(f"story {it['story'].get('id')} does not pass its checks, so it is not in a digest: "
                              + "; ".join(bad[:3]))
        if it["story"].get("program") not in (None, "news"):
            raise DigestError(f"story {it['story'].get('id')} is a {it['story']['program']} video; a digest is news")
        if not body(it["story"]):
            raise DigestError(f"story {it['story'].get('id')} has no sentence before its outlets line")
    brand = brand or data["cluster"].get("brand")
    fmt = formats.get(rubric["format"])
    lo, hi = fmt["min_seconds"] + 2, fmt["max_seconds"] - 3
    counts = [1] * len(items)
    story = compose(items, counts, rubric, brand, data["cluster"])
    while (_seconds(story) or 0) < lo:
        grown = False
        order = sorted(range(len(items)), key=lambda i: (sum(_words(x) for x in body(items[i]["story"])[:counts[i]]), i))
        for i in order:
            if counts[i] >= len(body(items[i]["story"])):
                continue
            trial = counts[:i] + [counts[i] + 1] + counts[i + 1:]
            cand = compose(items, trial, rubric, brand, data["cluster"])
            secs = _seconds(cand)
            if secs is not None and secs <= hi:
                counts, story, grown = trial, cand, True
                break
        if not grown:
            break
    return story
