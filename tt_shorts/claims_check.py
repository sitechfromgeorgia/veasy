"""Rule tiers for programs that aren't news (programs.py): claims and law. Hard rules, like news_check's.

The news tier is news_check.problems (N1-N5) against a cluster's member articles. Any other program explains one
document (a web page, a PDF, a blog post, a provision of a law), and the video may say only what that document says.
`sources` is the document's text (a list of strings, like the member articles).

  claims  N1  no opinion: no take scene; an evaluative word only when the document itself uses it
          N2  every number on screen and in the narration is in the document
          N3  every quote (a quote scene, „…“ in the narration) is verbatim in the document
          N4  no relative days (დღეს, გუშინ, ხვალ, ზეგ)
          C1  every name is in the document: a Latin-script name (Microsoft, GPT-5), a person or body in `who`,
              a quote's speaker; the brand's own names and the outlets from the data are allowed
  law     claims, plus
          L1  the article number is on screen ("მუხლი 17", "17-ე მუხლი")
          L2  no advice: what the provision says and whom it concerns, never what the viewer should do or can do
              in their own case (❌ „უნდა მიმართო“, „გირჩევ“, „შეგიძლია“, „შენი უფლებაა“)
          L3  the narration names the act (კონსტიტუცია, სამოქალაქო კოდექსი, ...)

N1 and N4 and the law rules run without the document too; N2, N3 and C1 need it (`engine check --sources`).

  story   fiction (program story: a fable, a cartoon, an animated tale): no articles, so nothing is compared with
          a document; the Georgian rules, the brand and the probe still run. One rule of its own:
          S1  no real person named as doing something: every name in the film is one of the story's own
              `characters` (a list in the story JSON). Code flags a Latin-script name, a Georgian surname
              (-შვილი, -ძე in any case), a person in `who`/`link` or a quote's speaker that isn't a character, and
              a real office (პრეზიდენტი, პრემიერი, მინისტრი, დეპუტატი, პატრიარქი, სპიკერი).
          Its limit: a bare Georgian first name (ნიკა, ნინო) or a nickname can't be told from a character's name
          by code, and a character may be given a real person's name on purpose; those need the review a composed
          film gets anyway (queue.py, "review").
"""
import re

from tt_shorts import news_check

TIERS = ("news", "claims", "law", "story")
GE = "ა-ჰ"
SURNAME = re.compile(rf"(?<![{GE}])[{GE}]{{2,}}(?:შვილ(?:ი|მა|ს|ის|ით|თან|ზე|ო)?|ძე(?:მ|ს|ის|ით|სთან|ზე)?)(?![{GE}])")
NOT_SURNAME = ("შვილიშვილ",)  # a grandchild, not a family name
OFFICES = ("პრეზიდენტ", "პრემიერ", "მინისტრ", "დეპუტატ", "პატრიარქ", "სპიკერ")
# L2: the viewer told what to do, or told what they personally may do (a law video describes, it doesn't advise).
# Whole-word starts only: "არჩევა" (election) is not "რჩევა" (advice).
ADVICE = re.compile(
    rf"(?<![{GE}])(?:გირჩევ\w*|გირჩიო\w*|რჩევ(?:ა|ას|ის|ები\w*)|სჯობს|აჯობებს|უმჯობესია|ჯობია|"
    rf"შენ\s+უნდა|უნდა\s+[{GE}]+ო(?![{GE}])|უნდა\s+იცოდე|არ\s+დაგავიწყდეს|გახსოვდეს|აუცილებლად|"
    rf"მიმართე|დაუკავშირდი|გაასაჩივრე|მოითხოვე|დაიცავი|წარადგინე|შეიტანე|დარეკე|გამოიყენე|"
    rf"შეგიძლია\w*|გაქვს\s+უფლება|შენი\s+უფლება\w*|შენს\s+უფლებ\w*)(?![{GE}])")
# L3: words of an act's title that don't tell one act from another
GENERIC_TITLE = ("საქართველო", "კანონ", "შესახებ", "კოდექს", "დადგენილება", "ბრძანება", "წესი", "ნორმატიული")
LATIN_NAME = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]*(?:[.+&'][A-Za-z0-9]+|-[A-Za-z0-9]+)*")


def stem(word, keep=3):
    """A Georgian word without its case ending (the last two letters): ზელენსკიმ -> ზელენსკ, კონსტიტუციის ->
    კონსტიტუცი. Enough to find a name in a text that inflects it differently."""
    word = word.strip(".,:;!?„“\"'()«»").lower()
    return word if len(word) <= keep + 1 else word[:max(keep, len(word) - 2)]


def _texts(story):
    """(where, text) of the narration and every on-screen text (ka_check.screen_texts) plus the CTA."""
    from tt_shorts import ka_check
    return [("narration", story.get("narration", ""))] + ka_check.screen_texts(story)


def doc_facts(story, sources, doc=None):
    """The act's title and the article number: from the pipeline's data (story.source, or `doc` while writing),
    else read from the document's own first lines ("საქართველოს კონსტიტუცია" / "მუხლი 17. ...")."""
    facts = {**(story.get("source") or {}), **(doc or {})}
    first = sources[0] if sources else ""
    if not facts.get("article"):
        m = re.search(r"(?m)^(?:მუხლი|Article)\s+(\d+)", first)
        if m:
            facts["article"] = m.group(1)
    if not facts.get("title"):
        line = first.split("\n", 1)[0].strip()
        if line and not re.match(r"(?:მუხლი|Article)\s", line):
            facts["title"] = line
    return facts


def opinion(story, corpus_low):
    out = []
    for s in story.get("scenes", []):
        if s.get("type") not in news_check.SCENE_TYPES | news_check.IDEA_TYPES:
            out.append(f"N1: scene type {s.get('type')!r} is not allowed (no opinion or take scenes)")
    low = story.get("narration", "").lower()
    for w in news_check.EVALUATIVE:
        if w in low and w not in corpus_low:
            out.append(f"N1: evaluative word in the narration: {w}… (say what the document says, don't judge)")
    return out


def numbers(story, corpus):
    seen = news_check.numbers(story.get("narration", "")) | news_check.numbers(news_check.screen_text(story))
    return [f"N2: number {n} is not in the source document"
            for n in sorted(seen - news_check.numbers(corpus), key=lambda x: (len(x), x))]


def quotes(story, corpus):
    found = re.findall(r"„([^“”]+)[“”]", story.get("narration", ""))
    found += [s["text"] for s in story.get("scenes", []) if s.get("type") == "quote" and s.get("text")]
    return [f"N3: quote is not verbatim in the source document: „{q[:60]}“" for q in found
            if news_check.flat(q) not in corpus]


def relative_days(story):
    text = story.get("narration", "") + " " + news_check.screen_text(story)
    return [f"N4: relative day „{w}“: name the date or leave it out" for w in news_check.RELATIVE_DAYS
            if re.search(rf"(?<![{GE}]){w}(?![{GE}])", text)]


def names(story, corpus_low, allow=()):
    """C1: Latin-script names anywhere, and the people/bodies of `who` and a quote's speaker, are in the document."""
    out, allowed = [], {a.lower() for a in allow if a}
    allowed |= {w for a in allowed for w in LATIN_NAME.findall(a)}
    for where, text in _texts(story):
        for name in dict.fromkeys(LATIN_NAME.findall(text)):
            if len(name) <= 2 or name.lower() in allowed or name.lower() in corpus_low:
                continue
            out.append(f"C1: {where}: the name {name!r} is not in the source document")
    people = [it.get("name", "") for s in story.get("scenes", []) if s.get("type") in ("who", "link")
              for it in s.get("items") or [] if isinstance(it, dict)]
    people += [s.get("by", "") for s in story.get("scenes", []) if s.get("type") == "quote"]
    for person in dict.fromkeys(p for p in people if isinstance(p, str) and p.strip()):
        if person.lower() in allowed:
            continue
        words = [w for w in re.findall(rf"[{GE}]+", person) if len(w) >= 3]
        missing = [w for w in words if stem(w) not in corpus_low]
        if missing:
            out.append(f"C1: {person!r} is not in the source document ({', '.join(missing)}): "
                       f"name only who the document names")
    return out


def article_shown(story, facts):
    """L1: the article's number on screen (the viewer must see which provision this is)."""
    num = re.match(r"\d+", str(facts.get("article") or ""))
    if not num:
        return ["L1: the source names no article: a law video explains one article (ref <law>:<article>)"]
    screen = news_check.screen_text(story)
    if not re.search(rf"(?<!\d){num.group(0)}(?!\d)", screen):
        return [f"L1: show the article number on screen, e.g. a hook kicker „მუხლი {num.group(0)}“"]
    return []


def advice(story):
    out = []
    for where, text in _texts(story):
        for m in dict.fromkeys(m.group(0) for m in ADVICE.finditer(text)):
            out.append(f"L2: {where}: advice „{m}“: say what the provision says and whom it concerns "
                       f"(„ყველას აქვს უფლება“), not what the viewer should or can do")
    return out


def act_named(story, facts):
    """L3: the narration names the act: one distinctive word of its title (not საქართველოს, კანონი...)."""
    title = str(facts.get("title") or "")
    words = [w for w in re.findall(rf"[{GE}]+", title) if len(w) >= 5
             and not any(stem(w).startswith(g) or g.startswith(stem(w)) for g in GENERIC_TITLE)]
    if not words:
        return []
    low = story.get("narration", "").lower()
    if any(stem(w, keep=4) in low for w in words):
        return []
    return [f"L3: the narration doesn't name the act ({title}): say which law this is"]


def _character(name, cast):
    """Is `name` (any case ending) one of the story's characters? Matched by stems, word by word."""
    words = [stem(w) for w in re.findall(rf"[{GE}A-Za-z0-9]+", name.lower())]
    return bool(words) and any(all(any(c.startswith(w) or w.startswith(c) for c in cw) for w in words)
                               for cw in cast)


def fiction(story, allow=()):
    """S1: no real person named as doing something; every name is one of the story's `characters` (a story tier
    rule, see the module docstring for what it can't see)."""
    cast = [[stem(w) for w in re.findall(rf"[{GE}A-Za-z0-9]+", str(c).lower())]
            for c in story.get("characters") or [] if isinstance(c, str) and c.strip()]
    allowed = {a.lower() for a in allow if a}
    allowed |= {w for a in allowed for w in LATIN_NAME.findall(a)}
    out = []
    if not isinstance(story.get("characters", []), list):
        out.append("S1: characters is a list of the story's own names")
    for where, text in _texts(story):
        for name in dict.fromkeys(LATIN_NAME.findall(text)):
            if len(name) <= 2 or not name[0].isupper() or name.lower() in allowed or _character(name, cast):
                continue
            out.append(f"S1: {where}: the name {name!r} is not one of the story's characters: fiction names no "
                       "real person (add it to \"characters\" only if it is the story's own)")
        for m in dict.fromkeys(m.group(0) for m in SURNAME.finditer(text)):
            if not m.startswith(NOT_SURNAME) and not _character(m, cast):
                out.append(f"S1: {where}: „{m}“ looks like a family name and is not one of the story's characters")
        low = text.lower()
        for office in OFFICES:
            if re.search(rf"(?<![{GE}]){office}", low):
                out.append(f"S1: {where}: a real office („{office}…“) in a story: fiction names no office-holder")
    people = [it.get("name", "") for s in story.get("scenes", []) if s.get("type") in ("who", "link")
              for it in s.get("items") or [] if isinstance(it, dict)]
    people += [s.get("by", "") for s in story.get("scenes", []) if s.get("type") == "quote"]
    for person in dict.fromkeys(p for p in people if isinstance(p, str) and p.strip()):
        if person.lower() not in allowed and not _character(person, cast):
            out.append(f"S1: {person!r} is not one of the story's characters")
    return out


def problems(story, sources, tier="claims", doc=None, allow=()):
    """Problems of one story under a tier; each names its rule. `doc`: {title, article} while writing."""
    if tier == "news":
        return news_check.problems(story, sources) if sources else []
    if tier not in TIERS:
        raise ValueError(f"unknown rule tier {tier!r}; known: {', '.join(TIERS)}")
    if tier == "story":  # fiction: no document to compare with; S1, and no opinion scene
        return [x for x in opinion(story, "") if "scene type" in x] + fiction(story, allow)
    corpus = news_check.flat(" ".join(sources))
    low = corpus.lower()
    out = opinion(story, low if sources else "") + relative_days(story)
    if sources:
        out += numbers(story, corpus) + quotes(story, corpus) + names(story, low, allow) + news_check.stated(story, sources)
    if tier == "law":
        facts = doc_facts(story, sources, doc)
        out += article_shown(story, facts) + advice(story) + act_named(story, facts)
    return out
