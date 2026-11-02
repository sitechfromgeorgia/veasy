"""News rules (N1-N6 in ka_style.md) for a story JSON, checked against the story's member articles.

Videos go out without a human review, so what code can see, code checks. Each problem names its rule and goes back
to the writer, like ka_check's K rules. `sources` is the list of member article texts (title + body).

  N1  no opinion: there is no "take" scene, and the narration has no evaluative words
  N2  numbers: every number in the narration and on screen is in at least one member article
  N3  quotes: a quote scene's text and every „…“ in the narration appear verbatim in a member article
  N4  no relative days (დღეს, გუშინ, ხვალ, ზეგ): a video is watched for days; the screen carries the date
  N5  sensitive stories are skipped, not written (sexual violence, children as victims, suicide)
  N6  the outlets and the date come from the data: the pipeline sets `sources` and `date` after the writer
      (not checked here; the writer's JSON never carries them)
  N10 pictograms (icons.py) show only what the voice says: a sign's verb is said in its part of the narration, and
      a story of the crime family (crime, incidents) or about deaths has no sign, no stat icon and no icon motif.
      pictograms() needs no articles, so engine.check_story runs it even without --sources.
"""
import re

SCENE_TYPES = {"hook", "stat", "timeline", "where", "who", "points", "quote", "sources", "draw", "pair", "steps", "bars",
               "trend", "change", "sign", "end"}
RELATIVE_DAYS = ("დღეს", "გუშინ", "ხვალ", "ზეგ", "გუშინწინ")
# Words that judge instead of report (stems: Georgian adds case endings). Extend from the edits log.
EVALUATIVE = ("სკანდალურ", "შოკისმომგვრელ", "სამარცხვინო", "საოცარ", "გასაოცარ", "უპრეცედენტო", "საშინელ",
              "სენსაციურ", "ისტორიულ", "ბრწყინვალე", "კატასტროფულ", "აღმაშფოთებელ")
SENSITIVE = ("გაუპატიურ", "სექსუალურ ძალადობ", "სექსუალური ძალადობ", "თვითმკვლელ", "სუიციდ", "არასრულწლოვან",
             "ბავშვზე ძალადობ", "პედოფილ")
# N10: a story that tells of deaths gets no pictograms (an icon next to a death reads as making light of it)
DEATHS = ("გარდაიცვალ", "გარდაცვალ", "გარდაცვლ", "დაიღუპ", "დაღუპ", "იღუპებ", "სიკვდილ", "ცხედ", "მკვლელობ",
          "მოკლეს", "მოკლულ", "მოიკლ", "დაიხრჩო", "მსხვერპლ")
NOT_SCREEN = ("type", "at", "icon", "verb")  # an icon's name and a sign's verb are drawn, not read
NUM = re.compile(r"\d+")


def flat(text):
    """Text for verbatim matching: one kind of quote, single spaces, no HTML entities."""
    text = text.replace("&bdquo;", "„").replace("&ldquo;", "“").replace("&quot;", '"')
    text = re.sub(r"[„“”\"«»]", '"', text)
    return re.sub(r"\s+", " ", text).strip()


def numbers(text):
    return set(NUM.findall(text))


def _walk(v):
    """Every string and number at any depth (a chart's values sit inside items and before/after)."""
    if isinstance(v, bool):
        return
    if isinstance(v, str):
        yield v
    elif isinstance(v, (int, float)):
        yield f"{v:g}" if isinstance(v, float) else str(v)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _walk(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk(x)


def screen_text(story):
    """Every word and number the writer put on screen (sources and date come from the data, not the writer).
    A drawing's on-screen words are its labels; its coordinates are not numbers anyone reads."""
    from tt_shorts import art
    out = []
    for s in story.get("scenes", []):
        for k, v in s.items():
            if k in NOT_SCREEN:
                continue
            if k == "svg":
                out += art.labels(v) if isinstance(v, str) else []
                continue
            out += list(_walk(v))
    return " ".join(out)


def sensitive(texts):
    """N5: the stems found in a story's titles and texts; any hit means the story is skipped before writing."""
    joined = " ".join(texts).lower()
    return sorted({s for s in SENSITIVE if s in joined})


def deaths(text):
    low = (text or "").lower()
    return sorted({s for s in DEATHS if s in low})


def no_pictograms(story):
    """N10: why a story may carry no pictograms (the crime family, deaths in its text), or None."""
    from tt_shorts import brand, meta
    try:
        pack = brand.of(story)
    except brand.BrandError:  # the structure check names the unknown brand; judge by the default pack meanwhile
        pack = brand.load()
    if meta.family(story.get("category", ""), pack) == "crime":
        return f"the crime family (category {story.get('category')})"
    hits = deaths(f"{story.get('narration', '')} {screen_text(story)}")
    return f"deaths ({', '.join(hits)})" if hits else None


def _norm(s):
    return re.sub(r"[\W_]", "", s.lower())


def scene_part(story, i):
    """The narration of scene i, from its anchor to the next scene's; the whole narration when an anchor is off
    (the timing check reports that)."""
    from tt_shorts import normalize_ka
    narration = story.get("narration", "")
    toks = normalize_ka.tokens(narration)
    keys = [_norm(t) for t in toks]
    starts, after = [], 0
    for s in story.get("scenes") or []:
        want = [_norm(p) for p in normalize_ka.tokens(s.get("at") or "") if _norm(p)]
        hit = next((k for k in range(after, len(keys) - len(want) + 1) if want and keys[k:k + len(want)] == want), None)
        if hit is None:
            return narration
        starts.append(hit)
        after = hit + 1
    starts.append(len(toks))
    return " ".join(toks[starts[i]:starts[i + 1]])


def pictograms(story):
    """N10 problems: a sign shows only what its part of the narration says; no pictograms for crime or deaths."""
    from tt_shorts import icons
    scenes = story.get("scenes") or []
    used = [i for i, s in enumerate(scenes) if s.get("type") == "sign" or (s.get("type") == "stat" and s.get("icon"))]
    out = []
    why = no_pictograms(story) if used or story.get("motif") else None
    if why:
        out.append(f"N10: no pictograms in a story about {why}: drop the sign scene, the stat's icon and the motif")
    for i in used:
        verb = scenes[i].get("verb")
        if scenes[i].get("type") == "sign" and verb in icons.VERBS and not icons.said(verb, scene_part(story, i)):
            out.append(f"N10: scene {i} (sign) shows „{verb}“ but its part of the narration doesn't say it "
                       f"({icons.VERB_WORDS[verb]}...): say it there, or choose the verb the narration says")
    return out


def problems(story, sources):
    out = []
    narration = story.get("narration", "")
    scenes = story.get("scenes", [])
    corpus = flat(" ".join(sources))
    corpus_numbers = numbers(corpus)

    for s in scenes:
        if s.get("type") not in SCENE_TYPES:
            out.append(f"N1: scene type {s.get('type')!r} is not allowed (no opinion or take scenes)")
    low = narration.lower()
    for w in EVALUATIVE:
        if w in low:
            out.append(f"N1: evaluative word in the narration: {w}… (report, don't judge)")

    seen = numbers(narration) | numbers(screen_text(story))
    for n in sorted(seen - corpus_numbers, key=lambda x: (len(x), x)):
        out.append(f"N2: number {n} is not in any source article")

    quotes = re.findall(r"„([^“”]+)[“”]", narration)
    quotes += [s["text"] for s in scenes if s.get("type") == "quote" and s.get("text")]
    for q in quotes:
        if flat(q) not in corpus:
            out.append(f"N3: quote is not verbatim in any source: „{q[:60]}“")

    for w in RELATIVE_DAYS:
        if re.search(rf"(?<![ა-ჰ]){w}(?![ა-ჰ])", narration + " " + screen_text(story)):
            out.append(f"N4: relative day „{w}“: name the date (2 ნოემბერს) or leave it out")

    hits = sensitive(sources + [narration])
    if hits:
        out.append(f"N5: sensitive story ({', '.join(hits)}): skip it")
    return out + pictograms(story)
