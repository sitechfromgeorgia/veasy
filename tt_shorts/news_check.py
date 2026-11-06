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
  N11 marks and links show only what the voice says (marks.py): an "em" phrase is word for word in its scene's
      markable on-screen text and said in its part of the narration; a link's edge (its verb) is said there too.
      spoken() needs no articles either.
  N2 also reads the brushes' facts: a share's percent is stated with "%" in an article, and every date on a rail
      is in an article (stated()).
  N12 what several outlets state alike (agreed(), the agree scene of the rubric „ადასტურებს N გამოცემა“): each of
      its facts is literally in at least n of the member articles (rubrics.claims: the same number and word, date,
      time, place or quote), its part of the narration says „მინიმუმ“, and no outlet is named in it or called by
      a side anywhere in the video (SIDES). A digest's chapter cards show only the stories' own checked lines.
  N13 imagery (assets.py, the story's code-owned `assets` ledger): an illustrative picture (stock photo or clip,
      illustration, AI) is drawn with the pack's „საილუსტრაციო“ label, which code adds and nothing can turn off;
      no illustrative imagery at all for the crime family or a story about deaths (as N10 for pictograms); AI
      imagery is off until the owner decides; a screenshot only from the allow-list (the pack's official and own
      sites, the program's), never a publisher's page; and no asset is presented as the event: the scene it sits
      behind never says „ფოტოზე“, „კადრებში“, „ვიდეოში“... (CLAIMS). imagery() needs no articles.
"""
import re

# The news rules' own allowlist of scene types (N1: no opinion or take scene), kept by hand on purpose: a new brush
# (brushes/<type>.json) is allowed in news only once it is named here too.
SCENE_TYPES = {"hook", "stat", "timeline", "where", "who", "points", "quote", "sources", "draw", "pair", "steps", "bars",
               "trend", "change", "sign", "end", "share", "rail", "compare", "link", "agree", "chapter", "ranking", "versus", "countdown", "calendar", "glossary", "checklist", "impact", "route", "budget",
               "map-focus", "kpi-grid", "ticker"}
RELATIVE_DAYS = ("დღეს", "გუშინ", "ხვალ", "ზეგ", "გუშინწინ")
# Words that judge instead of report (stems: Georgian adds case endings). Extend from the edits log.
EVALUATIVE = ("სკანდალურ", "შოკისმომგვრელ", "სამარცხვინო", "საოცარ", "გასაოცარ", "უპრეცედენტო", "საშინელ",
              "სენსაციურ", "ისტორიულ", "ბრწყინვალე", "კატასტროფულ", "აღმაშფოთებელ")
SENSITIVE = ("გაუპატიურ", "სექსუალურ ძალადობ", "სექსუალური ძალადობ", "თვითმკვლელ", "სუიციდ", "არასრულწლოვან",
             "ბავშვზე ძალადობ", "პედოფილ")
# N10: a story that tells of deaths gets no pictograms (an icon next to a death reads as making light of it)
DEATHS = ("გარდაიცვალ", "გარდაცვალ", "გარდაცვლ", "დაიღუპ", "დაღუპ", "იღუპებ", "სიკვდილ", "ცხედ", "მკვლელობ",
          "მოკლეს", "მოკლულ", "მოიკლ", "დაიხრჩო", "მსხვერპლ")
# an icon's name and a sign's verb are drawn, not read; em points at a text already on screen; style is a stat's motion
NOT_SCREEN = ("type", "at", "icon", "verb", "em", "style", "n", "of", "total", "show", "media", "rank", "status", "state")  # counts code makes (agree,
# chapter) are not claims of the articles
# N12: words that label an outlet by its side; a video never sorts outlets (stems: Georgian adds case endings)
SIDES = ("პროსამთავრობო", "სამთავრობო მედი", "ოპოზიციურ", "პროსახელისუფლებო", "სახელისუფლებო მედი", "პრორუსულ",
         "პროდასავლურ")
# N13: words that present a picture as the event ("in the photo", "the footage shows"); a scene with an illustrative
# picture behind it never says them (stems: Georgian adds case endings)
CLAIMS = ("ფოტოზე", "ფოტოში", "ფოტოებზე", "ფოტოებში", "სურათზე", "კადრებ", "კადრზე", "კადრში", "ვიდეოზე",
          "ვიდეოში", "ვიდეოჩანაწერ", "ჩანაწერში", "გადაღებულ")
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
        for k, x in v.items():
            if k not in NOT_SCREEN:
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
            if k == "items" and s.get("type") == "agree" and isinstance(v, list):  # an item's count is code's
                out += [it["text"] for it in v if isinstance(it, dict) and isinstance(it.get("text"), str)]
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


def no_imagery(story):
    """N13: why a story may carry no illustrative imagery (the crime family, deaths), or None: N10's reasons."""
    return no_pictograms(story)


def imagery(story):
    """N13 problems: the ledger's pictures are labelled, allowed for the story, allow-listed and never the event."""
    from tt_shorts import assets, brand
    ledger = {e.get("id"): e for e in story.get("assets") or [] if isinstance(e, dict)}
    scenes = story.get("scenes") or []
    used = [(i, ledger.get(s["media"].get("asset"))) for i, s in enumerate(scenes)
            if isinstance(s, dict) and isinstance(s.get("media"), dict)]
    used = [(i, e) for i, e in used if e]
    if not used:
        return []
    out = []
    try:
        pack = brand.of(story)
    except brand.BrandError:
        pack = brand.load()
    why = no_imagery(story)
    allow = assets.allow_list(story, pack)
    for i, e in used:
        kind = e.get("kind")
        if kind in assets.ILLUSTRATIVE and why:
            out.append(f"N13: scene {i} carries an illustrative {kind} in a story about {why}: no imagery there "
                       "(drop its show hint)")
        if kind == "ai":
            out.append(f"N13: scene {i}: AI imagery is off until the owner decides (docs/plan-v2.md § 8.3)")
        if kind == "screenshot":
            from tt_shorts.media import screenshot
            for url in dict.fromkeys(u for u in (e.get("url"), e.get("landed")) if u):
                if not screenshot.allowed(url, allow):
                    out.append(f"N13: scene {i}: a screenshot of {screenshot.host(url)}, which is not on the "
                               f"allow-list ({', '.join(allow) or 'empty'}): only official or the pack's own pages")
        if kind in assets.ILLUSTRATIVE:
            said = f"{scene_part(story, i)} {screen_text({'scenes': [scenes[i]]})}".lower()
            hits = [w for w in CLAIMS if w in said]
            if hits:
                out.append(f"N13: scene {i} shows an illustrative picture but says „{hits[0]}…“: an illustration is "
                           "never presented as the event")
    return out


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
    return out + stated(story, sources) + agreed(story, sources) + pictograms(story) + spoken(story) + imagery(story)


# ---------------------------------------------------------------- the brushes' own facts (N2) and marks (N11)

MONTHS = ("იანვ", "თებერვ", "მარტ", "აპრილ", "მაის", "ივნის", "ივლის", "აგვისტ", "სექტემბ", "ოქტომბ", "ნოემბ", "დეკემბ")
_YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)")
_DAY_MONTH = re.compile(r"(?<!\d)(\d{1,2})\s+(" + "|".join(MONTHS) + r")[ა-ჰ]*")
_MONTH = re.compile(r"(?<![ა-ჰ])(" + "|".join(MONTHS) + r")[ა-ჰ]*")
_TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")


def date_key(text):
    """A rail's when -> (year, month, day, minutes), None where the text doesn't say it; None when it is no date.
    „2 ნოემბერი, 22:00“ -> (None, 11, 2, 1320); „2025“ -> (2025, None, None, None); „მარტში“ -> (None, 3, ...)."""
    text = text or ""
    y, dm, t = _YEAR.search(text), _DAY_MONTH.search(text), _TIME.search(text)
    m = dm or _MONTH.search(text)
    month = MONTHS.index(m.group(2 if dm else 1)) + 1 if m else None
    day = int(dm.group(1)) if dm and 1 <= int(dm.group(1)) <= 31 else None
    key = (int(y.group(1)) if y else None, month, day, int(t.group(1)) * 60 + int(t.group(2)) if t else None)
    return key if any(k is not None for k in key) else None


def date_before(a, b):
    """True when date key a is earlier than b, judged on the first part both name (year, month, day, time)."""
    for x, y in zip(a, b):
        if x is not None and y is not None and x != y:
            return x < y
    return False


def _date_parts(when):
    """The pieces of a rail date as an article would write them: „2 ნოემბ“, „2025“, „22:00“."""
    out = []
    dm, y, t = _DAY_MONTH.search(when), _YEAR.search(when), _TIME.search(when)
    if dm:
        out.append((dm.group(0), re.compile(rf"(?<!\d)0?{int(dm.group(1))}\s+{dm.group(2)}")))
    elif _MONTH.search(when):
        m = _MONTH.search(when)
        out.append((m.group(0), re.compile(m.group(1))))
    if y:
        out.append((y.group(1), re.compile(rf"(?<!\d){y.group(1)}(?!\d)")))
    if t:
        out.append((t.group(0), re.compile(rf"(?<!\d)0?{int(t.group(1))}:{t.group(2)}(?!\d)")))
    return out


def _percent(v):
    """A share's value as an article states it: 34 -> 34%, 34 %; 34.5 -> 34.5% or 34,5%."""
    whole, _, dec = f"{v:g}".partition(".")
    num = whole + (rf"[.,]{dec}" if dec else r"(?:[.,]0+)?")
    return re.compile(rf"(?<![\d.,]){num}\s*%")


def stated(story, sources):
    """N2 for the brushes' facts: a share's percent is in an article with "%"; every rail date is in an article."""
    corpus = flat(" ".join(sources))
    out = []
    for i, s in enumerate(story.get("scenes") or []):
        if s.get("type") == "share" and isinstance(s.get("value"), (int, float)) and not isinstance(s["value"], bool):
            if not _percent(s["value"]).search(corpus):
                out.append(f"N2: scene {i} (share) shows {s['value']:g}% but no source article states „{s['value']:g}%“ "
                           "with the % sign: a share shows only a percent the articles give")
        if s.get("type") == "rail":
            for k, it in enumerate(s.get("items") or []):
                when = it.get("when") if isinstance(it, dict) else None
                if not isinstance(when, str):
                    continue
                missing = [shown for shown, pat in _date_parts(when) if not pat.search(corpus)]
                if missing:
                    out.append(f"N2: scene {i} (rail) items[{k}]: the date „{', '.join(missing)}“ is not in any source "
                               "article")
    return out


def spoken(story):
    """N11 problems: an em phrase is on screen in its scene and said in its part of the narration; a link's edge is
    said there (no relationship the voice didn't state). Needs no articles."""
    from tt_shorts import catalog, marks
    out = []
    for i, s in enumerate(story.get("scenes") or []):
        t = s.get("type")
        em = s.get("em")
        if em is not None:
            b = catalog.load_all().get(t)
            where = (b or {}).get("em", {}).get("fields") or []
            if not isinstance(em, str) or not em.strip():
                out.append(f"N11: scene {i} ({t}): em is one phrase, a text (at most one mark per scene)")
            elif not where:
                out.append(f"N11: scene {i} ({t}): a {t} scene takes no em: drop it")
            elif len(em.split()) > marks.MAX_WORDS or len(em) > marks.MAX_CHARS:
                out.append(f"N11: scene {i} ({t}): em „{em}“ is too long: mark 1-{marks.MAX_WORDS} words")
            elif not marks.locate(s):
                out.append(f"N11: scene {i} ({t}) marks „{em}“ but its {', '.join(where)} don't show it word for word: "
                           "copy the words exactly from its on-screen text")
            elif not marks.said(em, scene_part(story, i)):
                out.append(f"N11: scene {i} ({t}) marks „{em}“ but its part of the narration doesn't say it: mark "
                           "words the voice says in this scene")
        if t == "link" and isinstance(s.get("edge"), str) and s["edge"].strip():
            if not marks.said(s["edge"], scene_part(story, i)):
                out.append(f"N11: scene {i} (link) joins them with „{s['edge']}“ but its part of the narration doesn't "
                           "say it: the edge is the verb the voice says (შეხვდა, მოაწერა ხელი...)")
    return out


# ---------------------------------------------------------------- N12: what several outlets state alike


def sides(story):
    """N12: an outlet called by its side, anywhere in the narration or on screen."""
    low = f"{story.get('narration', '')} {screen_text(story)}".lower()
    return [f"N12: „{w}…“ labels an outlet by its side: say what is stated, never who stands where"
            for w in SIDES if w in low]


def agreed(story, sources):
    """N12 problems of the agree scenes (none in a story without one): every fact in at least n member articles,
    „მინიმუმ“ said in the scene's part, no outlet named there; and no side label anywhere."""
    from tt_shorts import rubrics
    scenes = story.get("scenes") or []
    idx = [i for i, s in enumerate(scenes) if s.get("type") == "agree"]
    if not idx:
        return []
    have = [set(rubrics.claims(t)) for t in sources]
    out = sides(story)
    for i in idx:
        s = scenes[i]
        n = s.get("n")
        for k, it in enumerate(s.get("items") or []):
            text = it.get("text") if isinstance(it, dict) else None
            keys = set(rubrics.claims(text or ""))
            if not keys:
                out.append(f"N12: scene {i} (agree) items[{k}]: „{text}“ is no fact code can count (a number with "
                           "its word, a date, a time, a place, a quote)")
                continue
            count = sum(1 for h in have if keys <= h)
            if not isinstance(n, int) or count < n:
                out.append(f"N12: scene {i} (agree) items[{k}]: „{text}“ is in {count} member article(s), the scene "
                           f"says at least {n}")
        part = scene_part(story, i)
        if "მინიმუმ" not in part:
            out.append(f"N12: scene {i} (agree): its part of the narration says „მინიმუმ“ and the count (at least N "
                       "outlets), never all of them")
        shown = f"{part} {screen_text({'scenes': [s]})}".lower()
        named = [o for o in story.get("sources") or [] if o and re.search(rf"(?<![\w]){re.escape(o.lower())}(?![\w])", shown)]
        if named:
            out.append(f"N12: scene {i} (agree) names {', '.join(named)}: it counts outlets, it never names them")
    return out
