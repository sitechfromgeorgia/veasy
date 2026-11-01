"""The mechanical part of the Georgian rulebook (ka_style.md): problems(story, art) → ["K12: ...", ...].

script.check() adds these for Georgian scripts, so a broken rule goes back to the writer with its rule number,
like any other failed check. What code can't judge (ergative, calques in context, naturalness) is the editor's
job (script.edit with ka_editor.md).

The SiTech-wide linter ge_ka_lint.py also runs on every text when it is installed (SiTech Hub
/root/sitech/georgian-style, kept up to date by the other SiTech agents; SHORTS_KA_LINT overrides the folder).
"""
import importlib.util
import os
import re
import sys

from tt_shorts import normalize_ka

LINT_DIR = os.environ.get("SHORTS_KA_LINT", "/root/sitech/georgian-style")
# linter rule -> rulebook rule; the linter's high-confidence set plus calques, filler and Latin country names
LINT_RULES = {"translit": "K16", "ending_hyphen": "K16", "cyrillic": "K16", "quotes": "K14", "decimal": "K21",
              "percent": "K21", "ellipsis": "K12", "number_plural": "K6", "space_punct": "K11",
              "double_space": "K11", "calque": "K3", "ai_filler": "K2", "country": "K17"}
# K9: narration words (as written) a scene needs before the next one starts, so the eye can follow it
MIN_WORDS = {"draw": 8, "end": 4}
MIN_WORDS_DEFAULT = 6
FIELDS = ("kicker", "headline", "label", "text", "big", "from", "refused", "ok")
# K20: Latin letters as Russian names them (TPM "ტე-პე-ემ"); a voice reads letters the English way ("ტი პი ემ")
RUSSIAN_LETTERS = {"ა", "ბე", "ცე", "დე", "ე", "გე", "ხა", "კა", "ო", "პე", "კუ", "ერ", "ტე", "უ", "ვე", "ზეტ"}
# K22: imperial units a Georgian viewer doesn't use (a screen's diagonal in დიუმი stays: shops sell it that way)
IMPERIAL = re.compile(r"(?<![ა-ჿ])(ფუნტ|უნცი|მილ|ფუტ|იარდ|გალონ|აკრ|ფარენჰაიტ)(ი|ის|ს|ით|ზე|ამდე|ში|ი?ან[ა-ჿ]*)?"
                      r"(?![ა-ჿ])|°\s?F\b")
# K15: identifiers a voice shouldn't read (CVE-2026-97631, KB5034441)
IDS = re.compile(r"\b(?:[A-Z]{2,}-\d{4}-\d{3,}|KB\d{6,})\b")
_lint = None


def lint():
    """ge_ka_lint.check_text, or None when the linter isn't installed here."""
    global _lint
    if _lint is None:
        path = os.path.join(LINT_DIR, "ge_ka_lint.py")
        _lint = False
        if os.path.exists(path):
            try:
                spec = importlib.util.spec_from_file_location("ge_ka_lint", path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["ge_ka_lint"] = mod
                spec.loader.exec_module(mod)
                _lint = mod.check_text
            except Exception as e:  # a broken linter must not stop the videos
                print(f"ka_check: linter at {path} failed to load: {e}", file=sys.stderr)
    return _lint or None


def screen_texts(story):
    """(where, text) for every on-screen text of the story."""
    out = []
    for i, s in enumerate(story.get("scenes") or []):
        where = f"scene {i} ({s.get('type')})"
        for k in FIELDS:
            if isinstance(s.get(k), str) and s[k].strip():
                out.append((f"{where} {k}", s[k]))
        for k in ("lines", "terminal"):
            out += [(f"{where} {k}", t) for t in s.get(k) or [] if isinstance(t, str)]
        for it in s.get("items") or []:
            out += [(f"{where} items", it[k]) for k in ("text", "title", "status") if isinstance(it, dict) and isinstance(it.get(k), str)]
        if isinstance(s.get("field"), dict):
            out += [(f"{where} field", v) for v in s["field"].values() if isinstance(v, str)]
        out += [(f"{where} svg text", t) for t in re.findall(r">([^<>]+)</text>", s.get("svg") or "")]
    return out


def norm(s):
    return re.sub(r"[\W_]", "", s.lower())


def scene_words(story):
    """[(scene index, type, narration words until the next scene)] from the "at" anchors."""
    toks = normalize_ka.tokens(story.get("narration", ""))
    keys = [norm(t) for t in toks]
    starts, after = [], 0
    for s in story.get("scenes") or []:
        want = [norm(p) for p in normalize_ka.tokens(s.get("at", "")) if norm(p)]
        hit = next((i for i in range(after, len(keys) - len(want) + 1) if want and keys[i:i + len(want)] == want), None)
        if hit is None:
            return []  # check() already reports the bad anchor
        starts.append(hit)
        after = hit + 1
    starts.append(len(toks))
    return [(i, s.get("type"), starts[i + 1] - starts[i]) for i, s in enumerate(story.get("scenes") or [])]


# K10: words that keep a claim a claim; an edit may move them, never lose them
QUALIFIERS = re.compile(r"თქმით|ცნობით|მიხედვით|განცხადებით|მონაცემ\w*|აცხადებ\w*|ამტკიცებ\w*|შესაძლოა|სავარაუდოდ|"
                        r"დაახლოებით|ზოგადად|ვარაუდ\w*|\d[\d.,%]*[-\s]?\w*მდე\b")  # "up to" only after a number


def qualifiers_lost(before, after):
    """K10 problems for qualifiers the edited narration has fewer of than the original."""
    count = lambda t: {q: len(re.findall(re.escape(q), t)) for q in set(QUALIFIERS.findall(t))}
    was, now = count(before), count(after)
    lost = [q for q, n in was.items() if now.get(q, 0) < n]
    return [f'K10: the edit dropped the qualifier "{q}": keep every qualifier of the original next to its claim'
            for q in lost]


def problems(story, art):
    p = []
    narration = story.get("narration", "")
    say = story.get("say") if isinstance(story.get("say"), dict) else {}
    texts = [("narration", narration)] + screen_texts(story)
    known = normalize_ka.names(say)
    known = set(known) | {w for k in known for w in k.split()}  # "1Password for Agents" covers "for"

    for where, t in texts:
        if re.search(r"(?<![ა-ჿ])თქვენ|გამოიწერეთ", t):
            p.append(f'K1: {where}: talk to the viewer as შენ, not თქვენ ("{t[:50]}")')
        if re.search(r"(?<![ა-ჿ])იფიქრებ(?![ა-ჿ])", t):
            p.append(f'K1: {where}: ask in the present tense, "შენ რას ფიქრობ?", not the future "რას იფიქრებ"')
        for m in IMPERIAL.finditer(t):
            p.append(f'K22: {where}: "{m.group(0)}" is not a unit Georgians use: say it in metric '
                     f'(კილოგრამი, გრამი, კილომეტრი, მეტრი, სანტიმეტრი, ლიტრი, °C)')
        if re.search(r"[—–]|!|\.\.\.|…", t):
            p.append(f'K12: {where}: no "!", "...", "…" or dashes (— –); use a comma, a colon or a hyphen ("{t[:50]}")')
        if re.search(r"[ა-ჿ]/[ა-ჿ]", t):
            p.append(f'K12: {where}: no slashes between words ("{t[:50]}")')
        for w in re.findall(r"(?<![A-Za-z0-9.@/_-])[a-z]{3,}(?![A-Za-z0-9.@/_])", t):
            if w not in known:
                p.append(f'K19: {where}: plain English word "{w}" in Georgian text: say it in Georgian or drop it '
                         f'(a real product name goes in "say")')

    article = norm(f'{art.get("title", "")} {art.get("description", "")} {art.get("text", "")}')
    quoted = [q for _, t in texts for q in re.findall(r"„([^“”\"]{3,})[“”\"]", t)]
    quoted += re.findall(r"(?:დაწერა|თქვა|წერს|განაცხადა):\s*„?([^.?„“]{6,})", narration)
    for q in dict.fromkeys(quoted):
        if norm(q) not in article:
            p.append(f'K14: "{q[:60]}" is quoted but not in the article word for word: use the article\'s exact words or drop it')

    for i, typ, n in scene_words(story):
        need = MIN_WORDS.get(typ, MIN_WORDS_DEFAULT)
        if n < need:
            p.append(f"K9: scene {i} ({typ}) gets only {n} narration words before the next scene, needs {need}: "
                     f"start it earlier or merge it with a neighbour, so it doesn't flash by")

    missing = normalize_ka.unspoken(narration, say)
    if missing:
        p.append(f'K20: add the Georgian spoken form of {", ".join(missing)} to "say" '
                 f'(e.g. {{"{missing[0]}": "<as a Georgian speaker says it>"}})')
    bad_say = [k for k, v in say.items() if not isinstance(v, str) or normalize_ka.LATIN.search(v)]
    if bad_say:
        p.append(f'K20: "say" values are Georgian letters only: {", ".join(map(str, bad_say))}')
    russian = [k for k, v in say.items() if isinstance(v, str) and RUSSIAN_LETTERS & set(re.split(r"[\s-]+", v))]
    if russian:
        p.append(f'K20: "say" spells letters the Russian way for {", ".join(russian)}: use the English letter names '
                 f'(E ი, K ქეი, O ოუ, P პი, T ტი: "TPM" = "ტი პი ემ")')
    for cve in dict.fromkeys(IDS.findall(narration)):
        p.append(f'K15: the narration reads the identifier {cve} aloud: say "ხარვეზი" or "განახლება", keep the ID on screen')

    check_text = lint()
    if check_text:
        seen = set()
        for where, t in texts:
            for f in check_text(t):
                rule = LINT_RULES.get(f.check)
                key = (f.check, f.snippet)
                if rule and key not in seen:
                    seen.add(key)
                    p.append(f"{rule}: {where}: {f.message} ({f.snippet[:60]})")
    return p
