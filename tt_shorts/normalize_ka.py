"""Georgian narration → what the voice should read, word by word.

The script keeps compact notation for the screen ("83%-ით", "4-ჯერ", "GPU-ები"); the voice gets Georgian
words ("ოთხმოცდასამი პროცენტით", "ოთხჯერ", "ჯი პი იუ-ები"). pairs() works per whitespace token, so every
caption word keeps its own timing after alignment.

Rules follow knowledge/video-brainstorm/georgian-tts/1-text-normalization.md: base-20 cardinals, the case
ending belongs to the noun (36%-ის → ოცდათექვსმეტი პროცენტის), a numeral before a noun in the dative or
with a postposition loses its final ი (2012 წელს → ორი ათას თორმეტ წელს), ordinals მე-…-ე.

Latin names are read from Georgian letters too (4-brands-style-guide.md, "two texts + lexicon"): the screen keeps
"Microsoft-მა", the voice gets "მაიკროსოფტმა". The spoken form comes from lexicon_ka.json (approved), then the
script's own "say" map, then names learned from earlier scripts (data/lexicon_learned.json); plain letter
acronyms are spelled. That keeps every name sounding the same in every video, and the Georgian aligner can hear
it (it only knows Georgian letters), so captions and scene cuts on a name stay on time.
"""
import json
import os
import pathlib
import re

SMALL = ("ნული", "ერთი", "ორი", "სამი", "ოთხი", "ხუთი", "ექვსი", "შვიდი", "რვა", "ცხრა", "ათი", "თერთმეტი",
         "თორმეტი", "ცამეტი", "თოთხმეტი", "თხუთმეტი", "თექვსმეტი", "ჩვიდმეტი", "თვრამეტი", "ცხრამეტი")
TWENTIES = {1: "ოცი", 2: "ორმოცი", 3: "სამოცი", 4: "ოთხმოცი"}
SCALES = ((1_000_000_000_000, "ტრილიონ"), (1_000_000_000, "მილიარდ"), (1_000_000, "მილიონ"), (1_000, "ათას"))
ORDINAL_SMALL = {1: "პირველი", 2: "მეორე", 3: "მესამე", 4: "მეოთხე", 5: "მეხუთე", 6: "მეექვსე", 7: "მეშვიდე",
                 8: "მერვე", 9: "მეცხრე", 10: "მეათე"}
DENOMINATORS = {1: "მეათედი", 2: "მეასედი", 3: "მეათასედი"}
LETTERS = {"A": "ეი", "B": "ბი", "C": "სი", "D": "დი", "E": "ი", "F": "ეფ", "G": "ჯი", "H": "ეიჩ", "I": "აი",
           "J": "ჯეი", "K": "ქეი", "L": "ელ", "M": "ემ", "N": "ენ", "O": "ოუ", "P": "პი", "Q": "ქიუ", "R": "არ",
           "S": "ეს", "T": "ტი", "U": "იუ", "V": "ვი", "W": "დაბლიუ", "X": "ექს", "Y": "უაი", "Z": "ზედ"}
HERE = pathlib.Path(__file__).resolve().parent
WORDS = json.loads((HERE / "lexicon_ka.json").read_text(encoding="utf-8"))["words"]  # approved spoken forms
VOWELS = "აეიოუ"
CURRENCY = {"$": "დოლარ", "€": "ევრო", "₾": "ლარ", "£": "ფუნტ"}
UNITS = {"GB": "გიგაბაიტ", "TB": "ტერაბაიტ", "MB": "მეგაბაიტ", "GHz": "გიგაჰერც", "km": "კილომეტრ", "W": "ვატ",
         "nm": "ნანომეტრ"}

GEO = re.compile(r"[ა-ჿ]")


def cardinal(n):
    """Nominative cardinal, 0..999 trillion."""
    if n < 20:
        return SMALL[n]
    if n < 100:
        q, r = divmod(n, 20)
        return TWENTIES[q] if r == 0 else TWENTIES[q][:-1] + "და" + SMALL[r]
    if n < 1000:
        q, r = divmod(n, 100)
        stem = ("" if q == 1 else _drop_i(SMALL[q])) + "ას"
        return stem + "ი" if r == 0 else stem + " " + cardinal(r)
    for scale, stem in SCALES:
        if n >= scale:
            q, r = divmod(n, scale)
            head = ("" if scale == 1000 and q == 1 else cardinal(q) + " ") + stem
            return head + "ი" if r == 0 else head + " " + cardinal(r)
    raise ValueError(n)


def ordinal(n):
    if n in ORDINAL_SMALL:
        return ORDINAL_SMALL[n]
    if n < 20:
        return "მე" + _drop_i(SMALL[n]) + "ე"
    if n < 100:
        q, r = divmod(n, 20)
        if r == 0:
            return "მე" + _drop_i(TWENTIES[q]) + "ე"
        return TWENTIES[q][:-1] + "და" + ("მეერთე" if r == 1 else ordinal(r))
    return "მე" + _drop_i(cardinal(n)) + "ე" if " " not in cardinal(n) else cardinal(n)


def _drop_i(word):
    return word[:-1] if word.endswith("ი") else word


def stem(word):
    """Stem a phrase's last word takes before an ending: ხუთი → ხუთ, რვა/ცხრა (vowel stems) stay."""
    return _drop_i(word)


def inflect(words, suffix):
    """A cardinal (independent use) + a Georgian case ending or postposition."""
    s = stem(words)
    vowel = not words.endswith("ი")  # რვა, ცხრა, ოცდარვა...
    if suffix in ("ჯერ",):
        return "ერთხელ" if words == "ერთი" else s + "ჯერ"
    table = {"ის": ("ის", "ის"), "ს": ("ს", "ს"), "მა": ("მა", "მ"), "მ": ("მა", "მ"), "ით": ("ით", "ით"),
             "ად": ("ად", "დ"), "დ": ("ად", "დ"), "მდე": ("ამდე", "მდე"), "ამდე": ("ამდე", "მდე"),
             "დან": ("იდან", "დან"), "იდან": ("იდან", "დან"), "ზე": ("ზე", "ზე"), "ში": ("ში", "ში"),
             "თან": ("თან", "სთან"), "ზეც": ("ზეც", "ზეც"), "ც": ("იც", "ც"), "იც": ("იც", "ც")}
    if suffix not in table:
        return words + suffix
    cons, vow = table[suffix]
    if vowel and suffix in ("ის", "ით", "იდან", "დან"):  # რვის, რვით, რვიდან (the final ა drops)
        return s[:-1] + {"ის": "ის", "ით": "ით", "იდან": "იდან", "დან": "იდან"}[suffix]
    return s + (vow if vowel else cons)


def attributive(words, next_word):
    """A numeral before a noun: dative/adverbial/postpositional nouns take the stem (ხუთ სერვერს)."""
    w = next_word.strip(".,;:!?„“\"()")
    if re.search(r"(ზე|ში|თან|ად|ამდე|მდე)$", w) or (w.endswith("ს") and not w.endswith("ის")):
        return stem(words)
    if w.endswith("მა"):
        return stem(words) + "მა"
    return words


def spell(latin):
    return " ".join(LETTERS[c.upper()] for c in latin if c.upper() in LETTERS)


def attach(nominative, suf):
    """A Georgian spoken name (nominative) + the case ending written after its hyphen.

    მაიკროსოფტი + მა → მაიკროსოფტმა (the nominative ი is an ending, it drops); ენვიდია + ის → ენვიდიას,
    + მა → ენვიდიამ, + ით → ენვიდიათი (vowel stems, like spelled acronyms: ეი აი + ს → ეი აის); a root ი after
    a vowel stays (ჰუავეი + მა → ჰუავეიმ)."""
    last = nominative.split()[-1]
    if nominative.endswith("ი") and len(last) > 1 and last[-2] not in VOWELS:
        return nominative[:-1] + suf
    if nominative[-1] in VOWELS:  # research table: vowel stems don't truncate (ტესლამ, ტესლას, ენვიდიას)
        return nominative + {"ის": "ს", "მა": "მ", "ით": "თ" if nominative[-1] == "ი" else "თი", "ად": "დ"}.get(suf, suf)
    return nominative + suf


def number(text):
    """'1,500' / '2 250' / '3.5' / '36' → words (nominative)."""
    text = re.sub(r"[   ]", "", text)  # thousands grouped with a space ("2 250")
    text = text.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", text) else text
    if "." in text or ("," in text and not text.endswith(",")):
        whole, frac = re.split(r"[.,]", text, maxsplit=1)
        return f"{cardinal(int(whole))} მთელი {cardinal(int(frac))} {DENOMINATORS.get(len(frac), 'მეათასედი')}"
    return cardinal(int(text))


def version(text):
    """'4.7' after a product name, '23.0.1' → ოთხი წერტილი შვიდი (a version is not a decimal)."""
    return " წერტილი ".join(cardinal(int(p)) for p in text.split("."))


GROUPED = r"\d{1,3}(?:[   ]\d{3})+(?!\d)"
NUM = rf"{GROUPED}|\d{{1,3}}(?:,\d{{3}})+|\d+(?:[.,]\d+)?"
TOKEN = re.compile(rf"^(?P<pre>[„“\"(]*)(?P<core>.*?)(?P<post>[.,;:!?“\")]*)$")
# Whitespace tokens, except that a number grouped with spaces ("2 250-ზე", "151 000") stays one token, so the
# voice reads one number and the caption shows it as one word.
TOKENS = re.compile(rf"(?<!\S)[„“\"(]*{GROUPED}\S*|\S+")
LATIN = re.compile(r"[A-Za-z]")
# What may follow a name's hyphen as a case ending; anything else is a compound ("AI-აგენტები").
ENDING = re.compile(r"ებ(?:ი|ს|ის|მა|ით|ზე|ში|თან|ისთვის)?|ის(?:ა|თვის|გან)?|ს(?:თან|თვის)?|მა|მ|ით|ად|დ|ზე|ში|თან|"
                    r"თვის|ზეც|შიც|იც|ც|ამდე|მდე|იდან|დან|კენ|ივით|ი|ელი|ელმა|ელს")


def tokens(text):
    return TOKENS.findall(text)


def learned_path():
    return pathlib.Path(os.environ.get("SHORTS_DATA", HERE.parent / "data")) / "lexicon_learned.json"


def learned():
    """Names learned from earlier scripts' "say" maps: {name: spoken}. Approved entries live in lexicon_ka.json."""
    try:  # acronyms and IDs from older files are skipped: code spells them, learn() no longer keeps them
        return {k: v["say"] for k, v in json.loads(learned_path().read_text(encoding="utf-8")).items()
                if not is_acronym(k) and not is_id(k)}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def learn(say, slug):
    """Keeps a script's new spoken forms for later videos (status auto, for Louie to confirm). Returns the new names."""
    path = learned_path()
    try:
        known = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = {}
    import datetime as dt
    new = [k for k, v in (say or {}).items() if k not in WORDS and k not in known and not is_acronym(k)
           and not is_id(k) and isinstance(v, str) and v.strip()]  # letter acronyms stay spelled the same way everywhere
    for k in new:
        known[k] = {"say": say[k].strip(), "status": "auto", "first": dt.date.today().isoformat(), "slug": slug}
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
    return new


def names(say=None):
    """Spoken forms for this narration, approved first: lexicon > the script's "say" > learned."""
    return {**learned(), **{k: v for k, v in (say or {}).items() if isinstance(v, str) and v.strip()}, **WORDS}


def is_id(word):
    """A one-off identifier, not a name to learn: CVE-2026-97631, KB5034441 (5+ digits; Storm-0940 and B300 are names)."""
    return sum(c.isdigit() for c in word) >= 5


def is_acronym(word):
    """Spelled letter by letter: AI, GPU, AWS, AAIF (up to 4 capitals). Longer all-caps words are names (ARTEX)."""
    return bool(re.fullmatch(r"[A-Z]{2,4}", word)) and word not in ("OK",)


def speak_token(core, next_word="", prev_word="", known=None):
    """One token without surrounding punctuation → spoken form (None = keep as is).
    known: name → spoken nominative (names()); prev_word tells a version ("Opus 4.7") from a decimal."""
    if not core:
        return None
    known = WORDS if known is None else known
    if core in known:
        return known[core]
    m = re.fullmatch(r"(?P<w>.*[A-Za-z0-9.])-(?P<suf>[ა-ჿ]+)", core)  # NVIDIA-ს, AI-ს, GPU-ები, Storm-0940-მა
    if m and LATIN.search(m["w"]):
        w, suf = m["w"], m["suf"]
        base = known.get(w) or (spell(w) if is_acronym(w) else speak_token(w, prev_word=prev_word, known=known))
        if not base:
            return None
        return attach(base, suf) if ENDING.fullmatch(suf) else base + " " + suf  # AI-აგენტები: a compound
    m = re.fullmatch(r"(?P<n>\d+(?:\.\d+){2,})(?:-(?P<suf>[ა-ჿ]+))?", core)  # 23.0.1, 23.0.1-ზე
    if m or (prev_word and LATIN.search(prev_word) and re.fullmatch(r"\d+\.\d+(?:-[ა-ჿ]+)?", core)):  # Opus 4.7
        n, _, suf = core.partition("-")
        v = version(n)
        return inflect(v, suf) if suf else v
    m = re.fullmatch(r"(?P<a>\d+)[–-](?P<b>\d+)", core)  # 10–15 (not a model name like GPT-5)
    if m:
        return inflect(cardinal(int(m["a"])), "დან") + " " + inflect(cardinal(int(m["b"])), "მდე")
    m = re.fullmatch(rf"(?P<cur>[$€₾£])(?P<n>{NUM})", core)
    if m:
        unit = CURRENCY[m["cur"]]
        tail = next_word.strip(".,;:!?")
        if tail in ("მილიონი", "მილიარდი", "ათასი", "million", "billion"):
            return number(m["n"])  # the scale word follows; the currency is spoken after it by the writer
        return number(m["n"]) + " " + unit + ("ი" if not unit.endswith("ო") else "")
    m = re.fullmatch(rf"(?P<n>{NUM})%(?:-(?P<suf>[ა-ჿ]+))?", core)  # 36%, 36%-ის
    if m:
        n, suf = number(m["n"]), m["suf"]
        if not suf:
            return n + " პროცენტი"
        if suf in ("ს", "ზე", "ში", "მდე", "ამდე", "თან"):
            return stem(n) + " პროცენტ" + {"მდე": "ამდე", "ამდე": "ამდე"}.get(suf, suf)
        if suf in ("მა", "მ"):
            return stem(n) + "მა პროცენტმა"
        return n + " პროცენტ" + {"ის": "ის", "ით": "ით", "დან": "იდან", "იდან": "იდან", "ად": "ად", "ც": "იც"}.get(suf, suf)
    m = re.fullmatch(rf"(?P<n>{NUM})\s?(?P<u>GB|TB|MB|GHz|km|W|nm)", core)
    if m:
        return number(m["n"]) + " " + UNITS[m["u"]] + "ი"
    m = re.fullmatch(r"(?P<n>\d+)-(?:ე|ელი|ლი)", core)  # 21-ე, 1-ელი
    if m:
        return ordinal(int(m["n"]))
    m = re.fullmatch(r"მე-(?P<n>\d+)(?:-ე)?", core)  # მე-2
    if m:
        return ordinal(int(m["n"]))
    m = re.fullmatch(rf"(?P<n>{NUM})-(?P<suf>[ა-ჿ]+)", core)  # 4-ჯერ, 2012-ში, 5-მა
    if m:
        return inflect(number(m["n"]), m["suf"])
    m = re.fullmatch(rf"(?P<n>{NUM})", core)
    if m:
        words = number(m["n"])
        return attributive(words, next_word) if GEO.search(next_word or "") else words
    m = re.fullmatch(r"(?P<w>[A-Za-z]+)-?(?P<n>\d+)(?P<rest>[A-Za-z]*)", core)  # B300, GPT-5, M4
    if m and m["w"].isupper():
        return f'{spell(m["w"])} {cardinal(int(m["n"]))}' + (f' {spell(m["rest"])}' if m["rest"] else "")
    if is_acronym(core):  # AI, GPU, AMD, TSMC
        return spell(core)
    return None


def pairs(text, say=None):
    """[(display token, spoken text)] for every token of the narration (tokens()). say: the script's own
    spoken forms for names the lexicon doesn't know ({"ARTEX": "არტექსი"})."""
    toks, known = tokens(text), names(say)
    multi = multiword(toks, known)
    out = []
    for i, tok in enumerate(toks):
        m = TOKEN.match(tok)
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        prev = TOKEN.match(toks[i - 1])["core"] if i else ""
        spoken = multi.get(i) or speak_token(m["core"], nxt, prev, known)
        out.append((tok, tok if spoken is None else m["pre"] + spoken + m["post"]))
    return out


def multiword(toks, known):
    """{token index: spoken} for names of several words ("Hugging Face": "ჰაგინგ ფეისი"), one spoken word per
    written word (the last one takes any extra words and the case ending: "Hugging Face-ზე")."""
    out = {}
    for name, said in known.items():
        parts, words = name.split(), said.split()
        if len(parts) < 2 or len(words) < len(parts):
            continue
        spoken = words[:len(parts) - 1] + [" ".join(words[len(parts) - 1:])]
        for i in range(len(toks) - len(parts) + 1):
            cores = [TOKEN.match(t)["core"] for t in toks[i:i + len(parts)]]
            last, suf = cores[-1], ""
            m = re.fullmatch(r"(?P<w>.*[A-Za-z0-9.])-(?P<suf>[ა-ჿ]+)", last)
            if m and m["w"] == parts[-1]:
                last, suf = m["w"], m["suf"]
            if cores[:-1] + [last] == parts:
                tail = spoken[-1] if not suf else attach(spoken[-1], suf) if ENDING.fullmatch(suf) else spoken[-1] + " " + suf
                out.update({i + j: w for j, w in enumerate(spoken[:-1] + [tail])})
    return out


def speech(text, say=None):
    return " ".join(s for _, s in pairs(text, say))


def unspoken(text, say=None):
    """Latin words the voice would get in Latin letters (no lexicon entry, no "say", not a letter acronym)."""
    out = [re.sub(r"-[ა-ჿ]+$", "", TOKEN.match(tok)["core"]) for tok, said in pairs(text, say) if LATIN.search(said)]
    return list(dict.fromkeys(out))
