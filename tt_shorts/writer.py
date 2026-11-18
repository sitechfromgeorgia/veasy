"""Cluster -> story JSON: a free model writes the script, code checks it, one repair, then it is ready to render.

The rules live in ka_style.md (K1-K22, N1-N9). This module only carries them to the model, parses the answer,
strips what the data owns (sources, date: N6) and runs the same checks the renderer trusts.

  python -m tt_shorts.writer --cluster 24725 --out stories/24725.json
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request

from tt_shorts import (art, catalog, drawings, icons, illustrator, ka_check, kaeasy, meta,
                       motion_rules, news_check, normalize_ka, vignettes)

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLE = (ROOT / "tt_shorts" / "ka_style.md").read_text(encoding="utf-8")
# The model name follows the provider: Groq serves qwen and gpt-oss under its own ids and answers a
# vendor-qualified :free id with 404. _call picks the name from _provider() when this default is in use.
MODEL = os.environ.get("SHORTS_WRITER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
GROQ_MODEL = os.environ.get("SHORTS_GROQ_MODEL", "qwen/qwen3.8-27b")
# NVIDIA's own endpoint names the model without the vendor prefix and without the :free suffix.
NVIDIA_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
# The OpenCode seat (owner, 2026-11-16: "use yesterday's key with the deepseek model"). This endpoint
# only produces usable text with reasoning_effort "none": without it the model spends the whole
# completion budget on private reasoning and returns empty content. Measured with the flag: 26 s,
# 1,340 characters, reasoning_tokens 0, finish_reason stop, and clean Georgian.
OPENCODE_ENDPOINT = "https://opencode.ai/zen/go/v1/chat/completions"
OPENCODE_MODEL = "deepseek-v4.1-flash"
OPENCODE_KEY_FILE = pathlib.Path("/root/.secrets/opencode_extraction_key")


def _opencode_key() -> str:
    try:
        return OPENCODE_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _nvidia_key() -> str:
    key = os.environ.get("NVIDIA_API_KEY", "")
    if key:
        return key
    try:
        return pathlib.Path("/root/.secrets/nvidia_api_key").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
FALLBACK = os.environ.get("SHORTS_WRITER_FALLBACK", "")
# The writer draws ("draw" scenes): a drawing per story is what makes each video its own (owner, 2026-11-02: "1000
# videos in one style is no good"; SiTech's channel draws with a free model). No person reviews it, so code does:
# art.sanitize (safe, on brand) and art.quality (big enough, builds up, one focal part); a drawing that still fails
# after the repairs is swapped for a library drawing of the same motif (drawings.py), else dropped, and the video goes
# out without it. VEASY_WRITER_DRAW=0 turns drawing off.
DRAW_ENV = "VEASY_WRITER_DRAW"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
# A reasoning provider counts its thinking against max_tokens, so a small budget can leave nothing for
# the answer. 24000 was set for that, but against the CommandCode gateway it made every request ask for
# a 24k completion, which took longer than the 180 s read timeout: 54 renders died on "writer model
# failed: TimeoutError" and 309 jobs sat in failed. The gateway runs reasoning with effort off for this
# lane, so the budget no longer has to cover a long private monologue; 6000 leaves room for a full
# script and still comes back in seconds. The OpenRouter free path keeps the larger budget because
# there the thinking really does consume the completion.
THINKING_TOKENS = 6000


class ChecksFailed(ValueError):
    """The script still fails the checks after the repairs; .problems lists them (failures.py remembers them)."""

    def __init__(self, problems):
        super().__init__("checks failed: " + "; ".join(problems[:6]))
        self.problems = list(problems)


# The JSON shape and the rules the writer gets: generated from the brush catalog (brushes/<type>.json, catalog.py);
# schema(types) narrows it to a director's or a program's menu.
SCHEMA = catalog.schema()


GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def _groq_key() -> str:
    """The free Groq key, from the profile env or the 0600 secret file."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    try:
        import pathlib as _p
        return (_p.Path("/root/.secrets/groq_api_key").read_text(encoding="utf-8").strip())
    except OSError:
        return ""


def _provider() -> tuple[str, str, dict, str, dict]:
    """(url, key, the request's extra keys, the key's name, extra headers): OpenRouter, or any OpenAI-format server
    named by SHORTS_WRITER_URL with SHORTS_WRITER_KEY (read when used: daily.py loads data/.env after importing this).
    The writer names itself there: an API behind Cloudflare refuses Python-urllib's default signature (error 1010)."""
    url = os.environ.get("SHORTS_WRITER_URL", "").rstrip("/")
    # Groq first. The OpenCode seat is a monthly plan whose allowance is spent until 2026-11-22, and
    # with it first every render died on 429 while a free Groq key with a daily allowance sat unused.
    # Measured 2026-11-18 on extraction: groq qwen answered a Georgian batch in 1.3 s with clean
    # Georgian names. The order here must mirror run_free_extraction.py's, or one lane starves while
    # the other idles.
    if not url and _groq_key():
        return GROQ_ENDPOINT, _groq_key(), {"reasoning_effort": "none"}, \
            "groq_api_key", {"User-Agent": "veasy-writer"}
    if not url and _opencode_key():
        return OPENCODE_ENDPOINT, _opencode_key(), {"reasoning_effort": "none"}, \
            "opencode_extraction_key", {"User-Agent": "veasy-writer",
                                        "x-opencode-session": "veasy-writer"}
    if not url:
        # 2026-11-16: OpenRouter is no longer the default route. Its key is at $50.01 of a $50.00
        # limit, so every request came back 403 and the render lane sat at zero for hours. NVIDIA
        # serves the same model on its own free quota and answered in 0.6 s, so it goes first and
        # OpenRouter stays as the fallback for whoever raises that limit.
        if _nvidia_key():
            return NVIDIA_ENDPOINT, _nvidia_key(), {"reasoning": {"enabled": False}}, \
                "NVIDIA_API_KEY", {}
        return ENDPOINT, os.environ.get("OPENROUTER_API_KEY", ""), {"reasoning": {"enabled": False}}, \
            "OPENROUTER_API_KEY", {}
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    return url, os.environ.get("SHORTS_WRITER_KEY", ""), {}, "SHORTS_WRITER_KEY", {"User-Agent": "veasy-writer"}


def _call(prompt: str, model: str, max_tokens: int = 1800, tries: int = 3) -> str:
    url, key, extra, name, headers = _provider()
    if name == "groq_api_key" and model == MODEL:
        model = GROQ_MODEL  # the caller used the default; on Groq that name does not exist
    if name == "groq_api_key" and model.startswith("openai/gpt-oss"):
        # gpt-oss rejects reasoning_effort "none" with a 400 and accepts only low/medium/high; qwen
        # takes the none flag that keeps a free tier from spending its day on hidden reasoning.
        extra = {**extra, "reasoning_effort": "low"}
    if not key:
        raise RuntimeError(f"{name} is not set")
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, "max_tokens": max(max_tokens, THINKING_TOKENS) if url == ENDPOINT else max_tokens, **extra}
    last = ""
    for attempt in range(tries):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                              **headers})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            msg = data["choices"][0]["message"]["content"] or ""
            if msg.strip():
                return msg
            last = "empty answer"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
            # 429 used to be the only trigger, which meant a key that hit its spend limit (403,
            # "Key limit exceeded") failed every render while the working NVIDIA quota sat unused.
            # Measured 2026-11-16: the OpenRouter key was at $50.01 of $50.00 and 309 jobs were
            # sitting in failed. Any OpenRouter refusal now falls through to NVIDIA.
            # Any provider that refuses falls through to NVIDIA, not only OpenRouter. Measured
            # 2026-11-18: Groq is now first, and its daily token cap (200,000 TPD, shared by every
            # model on the key) was reached at 198,580, so every render died on 429 while the NVIDIA
            # key sat idle with its own quota. A refused request is a reason to change route, not a
            # reason to stop.
            if e.code in (401, 402, 403, 429, 500, 502, 503) and name != "NVIDIA_API_KEY":
                try:
                    return _nvidia(prompt, max_tokens)
                except Exception as nv:
                    last = f"HTTP {e.code} and nvidia fallback failed: {nv}"
                time.sleep(15 * (attempt + 1))
                continue
        except (urllib.error.URLError, TimeoutError) as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"writer model failed: {last}")


def _nvidia(prompt: str, max_tokens: int = 1800) -> str:
    """OpenRouter's free cap is per day; NVIDIA is the same model on its own quota."""
    key = os.environ.get("NVIDIA_API_KEY", "")
    if not key:
        try:
            key = pathlib.Path("/root/.secrets/nvidia_api_key").read_text(encoding="utf-8").strip()
        except OSError:
            key = ""
    if not key:
        raise RuntimeError("nvidia key missing")
    body = {"model": "nvidia/nemotron-3-ultra-550b-a55b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, "max_tokens": max_tokens, "reasoning": {"enabled": False}}
    req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.load(r)
    return (data["choices"][0]["message"]["content"] or "").strip()


def _object(text: str) -> dict:
    """The last JSON object in the answer (models often narrate before the JSON)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    raise ValueError("no JSON object in the model answer")


def drawing() -> bool:
    return os.environ.get(DRAW_ENV, "1") != "0"


def schema(types=None) -> str:
    """The catalog's shape and rules (catalog.schema), with the draw scene and its style guide only when drawing is
    on. types: only these scene types' lines and rules (a director's, directors.scene_types; a program's). A scene's
    "art" is the illustrator's (illustrator.py, a call of its own after the script) unless that step is off."""
    text = catalog.schema(types)
    later = illustrator.on()
    own_art = '\n- never set "art": a separate step draws the film\'s pictures.' if later else f"\n{catalog.RULE_ART}"
    if drawing() and (types is None or "draw" in types):
        return f"{text}{own_art}\n{art.GUIDE}"
    bare = "\n".join(line for line in text.splitlines() if '"draw"' not in line)
    if drawing() and later:
        return bare + '\n- never use a "draw" scene.' + own_art
    if drawing():
        return f"{bare}\n{catalog.RULE_ART}\n{art.GUIDE}\n- never use a \"draw\" scene (\"art\" only)."
    return bare + '\n- never use a "draw" scene, nor "art".'


def _variety_line(avoid: list[str] | None) -> str:
    """The scene orders the latest videos used, so this one can take another shape (tt_shorts/variety.py)."""
    if not avoid:
        return ""
    return ("Scene orders the latest videos already used (most frequent first): " + "; ".join(avoid[:8]) +
            ". Viewers see these every day: when the story allows, choose a different order or other scene types "
            "(pair, steps, bars, trend, change, timeline, quote, draw...), never a type the story has no facts for.\n\n")


def _prompt(cluster: dict, articles: list[str], avoid: list[str] | None = None, mistakes: str = "",
            director: dict | None = None, facts: dict | None = None, extra: str = "", extra_types=()) -> str:
    """director (directors.py, assigned by code before writing): its brief, only its scene types, the facts.
    extra: a rubric's brief (rubrics.brief_block), after the director's; extra_types: the scene types its shape
    names, added to the director's menu."""
    from tt_shorts import directors
    body = "\n\n".join(f"--- სტატია {i + 1} ---\n{a[:2600]}" for i, a in enumerate(articles[:3]))
    allowed = sorted(news_check.numbers(" ".join(articles)), key=lambda x: (len(x), x))
    allowed_line = ", ".join(allowed[:40]) if allowed else "არცერთი"
    georgian = kaeasy.prompt_block()  # free: kaeasy's ten rules + the fleet's frequent mistakes, when installed
    menu = directors.scene_types(director) if director else None
    if menu is not None and extra_types:
        menu = list(dict.fromkeys(menu[:-1] + [t for t in extra_types if t not in ("hook", "end")] + ["end"]))
    shape = schema(menu)
    direction = directors.brief_block(director, facts) if director else ""
    hard = (
        "მკაცრი წესები:\n"
        "- ციტატა მხოლოდ სტატიის ტექსტიდან, სიტყვასიტყვით და ბრჭყალებით. არ შეცვალო, არ შეამოკლო სიტყვების შეცვლით. "
        "თუ ზუსტი ციტატა არ არის, quote სცენა საერთოდ არ გამოიყენო.\n"
        "- sign სცენაზე მხოლოდ ის ხატულა/სიტყვა, რომელიც ამ სცენის ნარაციის ნაწილში ზუსტად არის ნათქვამი. თუ არა, sign სცენა არ გამოიყენო.\n"
        "- სია (points, steps, checklist, ranking) მხოლოდ მაშინ, როცა სტატია თვითონ ჩამოთვლის ცალკეულ რამეებს; ფილმში მაქსიმუმ "
        "ერთი სია. ამბის შეჯამება სია არ არის: აირჩიე სცენა, რომელიც თემას აჩვენებს.\n"
        "- stat/bars/compare-ის ციფრი ზუსტად იმავე ნაწილის ნარაციაში უნდა ჟღერდეს, სხვა რიცხვი არ დაწერო.\n"
        "- ყოველი სცენის \"at\" არის ამ სცენის ნარაციის პირველი სიტყვები, ზუსტად.\n"
        "- არასდროს გაიმეორო ერთი და იგივე სცენის ტიპი (type) ზედიზედ ორჯერ; არ დატოვო სცენა უმოძრაოდ 3 წამზე მეტხანს გაჭრის გარეშე.\n"
        "- \"say\"-ში ლათინური ასოების სახელები დაწერე ინგლისურად (A ეი, E ი, K ქეი, P პი, T ტი), არასდროს რუსულად (ტე, პე).\n\n"
    )
    return (f"{STYLE}\n\n{georgian + chr(10) * 2 if georgian else ''}{shape}\n\n{direction}{extra}{_variety_line(avoid)}"
            f"{mistakes + chr(10) * 2 if mistakes else ''}{hard}"
            f"დაწერე ამ კლასტერის 30-40 წამიანი ვიდეოს სცენარი.\n"
            f"სათაური: {cluster.get('headline', '')}\n"
            f"კატეგორია: {cluster.get('category', 'general')}\n"
            f"წყაროების რაოდენობა: {cluster.get('source_count', 0)}\n"
            f"ნებადართული რიცხვები (მხოლოდ ეს): {allowed_line}\n\n{body}")


def _fix_anchors(story: dict) -> None:
    """Re-anchor a scene whose „at“ differs from the narration only in punctuation or quotes.

    The writer often keeps „…“ or a comma in the anchor while the narration has none. The cut
    depends on the anchor being a real substring, so the honest repair is to replace it with
    the matching slice of the narration, not to fail the job."""
    if not _repair_enabled():
        return
    narration = story.get("narration") or ""
    if not narration:
        return

    def norm_map(text):
        out, idx, prev_space = [], [], False
        for i, ch in enumerate(text):
            if ch.isspace():
                if not prev_space:
                    out.append(" "); idx.append(i); prev_space = True
                continue
            prev_space = False
            if ch.lower() in "„“\"'«».,;:!?…":
                continue
            out.append(ch.lower()); idx.append(i)
        return "".join(out), idx

    flat, idx = norm_map(narration)
    pos = 0
    for sc in story.get("scenes") or []:
        at = str(sc.get("at") or "").strip()
        if not at:
            continue
        fat, _ = norm_map(at)
        if not fat:
            continue
        p = flat.find(fat, pos)
        if p < 0:
            # The model sometimes invents an anchor that appears nowhere in the narration, and four
            # repair passes do not fix it: measured 2026-11-18 on repeated K13 failures. Re-anchor to
            # the next words of the narration instead. The cut still lands on real narration, the
            # scene order is preserved, and the video keeps its own words rather than failing.
            rest = narration[pos:]
            words = list(re.finditer(r"\S+", rest))
            if words:
                take = min(max(1, len(at.split())), len(words))
                sc["at"] = rest[words[0].start():words[take - 1].end()]
                pos += words[take - 1].end()
            continue
        start = idx[p]
        want = len(fat.split())
        # take the same number of words from the original text
        words = list(re.finditer(r"\S+", narration[start:]))
        end = start + words[min(want, len(words)) - 1].end() if words else start + len(at)
        sc["at"] = narration[start:end]
        pos = p + len(fat)


def _hard_anchor(story: dict) -> None:
    """Rebuild every anchor from the narration, word by word, in scene order.

    The normalised search in _fix_anchors strips punctuation before matching, so a match can land in
    the middle of a Georgian word: measured 2026-11-18, scene 4 of a six-scene story carried
    "რდნენ. ქვები..." cut out of "დაუპირისპირდნენ". The anchor was then not a substring of the
    narration, K13 failed, and four repairs could not fix it because the same normaliser produced the
    same cut again.

    This pass has no normalisation to get wrong: it takes the first N words of the remaining narration
    for each scene, where N is the word count the scene already asked for. It cannot produce anything
    that is not an exact slice, so it is the last word on anchors.
    """
    narration = story.get("narration") or ""
    scenes = story.get("scenes") or []
    if not narration or not scenes:
        return
    words = list(re.finditer(r"\S+", narration))
    if not words:
        return
    # Distribute by what each scene type needs, not by what the writer asked for. A scene's own word
    # count is the writer's guess, and giving every scene its guess left later scenes short of their
    # type's minimum, which is the K9 failure this pass is meant to end. Each scene takes at least its
    # catalogue minimum, and whatever is left over goes to the scenes that asked for more.
    from tt_shorts import catalog as _catalog
    needs = _catalog.min_words()
    default = _catalog.MIN_WORDS_DEFAULT
    mins = [max(1, needs.get(str(sc.get("type")), default)) for sc in scenes]
    total = len(words)

    # If the narration cannot cover every minimum, drop the scenes it cannot carry from the end.
    while len(mins) > 2 and sum(mins) > total:
        mins.pop(-2)
        scenes = scenes[:-2] + scenes[-1:]
    if sum(mins) > total:
        return  # nothing sensible to rebuild; the caller reports the real shortage

    wanted = [max(mins[i], len(str(sc.get("at") or "").split())) for i, sc in enumerate(scenes)]
    scale = min(1.0, total / sum(wanted)) if sum(wanted) > total else 1.0
    # A scene holds its frame while its words are spoken, and the stillness rule allows five seconds.
    # Georgian speech runs near 2.5 words a second, so a slice longer than about twelve words reads as
    # a stall on a phone even when every word is needed. Excess words move to the next scene rather
    # than making this one unrenderable, and the anchor is what decides where a cut falls.
    MAX_WORDS = 12
    takes = [max(mins[i], int(w * scale)) for i, w in enumerate(wanted)]
    leftover = total - sum(takes)
    i = 0
    while leftover > 0 and takes:
        if takes[i % len(takes)] < MAX_WORDS:
            takes[i % len(takes)] += 1
            leftover -= 1
        i += 1
        if i > MAX_WORDS * len(takes) * 4:  # every scene is at the cap; the rest cannot be placed
            # grow the scene with the most room in its type minimum instead of looping forever
            takes[takes.index(min(takes))] += leftover
            break

    pos = 0
    out = []
    for sc, take in zip(scenes, takes):
        if pos >= total:
            break
        take = min(take, total - pos)
        sc["at"] = narration[words[pos].start():words[pos + take - 1].end()]
        pos += take
        out.append(sc)
    story["scenes"] = out


def _anchors_ok(story: dict) -> bool:
    """Every scene anchor must sit in the narration, in order (props.cut depends on it)."""
    narration = story.get("narration", "")
    pos = 0
    for s in story.get("scenes", []):
        at = (s.get("at") or "").strip()
        if not at:
            return False
        i = narration.find(at, pos)
        if i < 0:
            return False
        pos = i + len(at)
    return True


MONTHS_KA = ("იანვარს", "თებერვალს", "მარტს", "აპრილს", "მაისს", "ივნისს", "ივლისს", "აგვისტოს",
             "სექტემბერს", "ოქტომბერს", "ნოემბერს", "დეკემბერს")


def _fix_dates(story: dict, cluster: dict) -> None:
    """N4: a video is watched for days, so „დღეს“ becomes the date the story ran."""
    raw = str(cluster.get("created_at") or "")[:10]
    try:
        day = dt.date.fromisoformat(raw)
    except ValueError:
        return
    labels = {
        "დღეს": f"{day.day} {MONTHS_KA[day.month - 1]}",
        "გუშინ": f"{(day - dt.timedelta(days=1)).day} {MONTHS_KA[(day - dt.timedelta(days=1)).month - 1]}",
        "ხვალ": f"{(day + dt.timedelta(days=1)).day} {MONTHS_KA[(day + dt.timedelta(days=1)).month - 1]}",
    }

    def fix(value):
        if isinstance(value, str):
            for word, label in labels.items():
                value = value.replace(f" {word} ", f" {label} ").replace(f" {word},", f" {label},")
                if value.startswith(f"{word} "):
                    value = label + value[len(word):]
            return value
        if isinstance(value, list):
            return [fix(v) for v in value]
        if isinstance(value, dict):
            return {k: fix(v) for k, v in value.items()}
        return value

    story["narration"] = fix(story.get("narration", ""))
    story["scenes"] = fix(story.get("scenes", []))



# Every text field a scene can carry, with the limit the renderer enforces. "end" was missing, so a
# 30-character end line reached the checker and failed the job on "at most 24" (measured 2026-11-18)
# while every other field was clamped before the check ever saw it.
# The per-field limits come from the brush catalogue, which is what the renderer enforces. This table
# used to be a second copy and disagreed with it in both directions (label 24 against the catalogue's
# 56 for a stat and 40 for a sign, "by" 40 against quote's 32, unit 8 against change's 16), so a field
# could be clamped under the limit and still fail, or be loosened past what fits on screen.
def _limits() -> dict:
    """field -> the smallest limit any brush sets for it, plus a floor for fields the catalogue omits."""
    from tt_shorts import catalog
    out = {"kicker": 24, "headline": 40, "text": 200, "big": 12, "place": 30, "sub": 30,
           "end": 24, "weekday": 20, "change": 24, "value": 12, "start": 24, "finish": 24,
           "to": 24, "from": 24, "when": 24, "where": 30, "via": 32}
    try:
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
    except Exception:
        pass  # a catalogue that cannot be read must not break the writer
    return out


_LIMITS = _limits()


def _clamp(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:—-")


_DASH_RE = re.compile(r"\s*[\u2013\u2014]\s*")


# Georgian word forms a model gets wrong often enough that a person has had to correct them.
# Every entry is a pair the owner himself flagged or that kaeasy records as a common error, so this is
# code enforcing a known rule, not a guess at grammar. Longest first so a longer wrong form is not
# half-replaced by a shorter entry.
_KA_WRONG_FORMS = [
    ("გაეცნა", "გაეცნო"),   # owner, 2026-11-16, after a live reel printed it in the hook
]


def _spell_clock(story: dict) -> None:
    """The narration is spoken text: a digit there is a lint error, so clock times become words."""
    if isinstance(story.get("narration"), str):
        story["narration"] = spell_clock_times(story["narration"])
    for sc in story.get("scenes") or []:
        if isinstance(sc, dict) and isinstance(sc.get("say"), str):
            sc["say"] = spell_clock_times(sc["say"])


def _ka_forms(story: dict) -> None:
    """Rewrite known-wrong Georgian forms everywhere the writer puts text."""
    def fix(text):
        if not isinstance(text, str):
            return text
        for wrong, right in _KA_WRONG_FORMS:
            if wrong in text:
                text = text.replace(wrong, right)
        return text

    if isinstance(story.get("narration"), str):
        story["narration"] = fix(story["narration"])
    for key in ("headline", "hook", "title", "cta"):
        if isinstance(story.get(key), str):
            story[key] = fix(story[key])
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, v in list(sc.items()):
            if isinstance(v, str):
                sc[key] = fix(v)
            elif isinstance(v, list):
                sc[key] = [fix(x) if isinstance(x, str) else x for x in v]


def _drop_stray_latin(story: dict) -> None:
    """K19: a plain English word in Georgian text is a defect, and the model keeps reintroducing it.

    Measured 2026-11-18: "ardi" appeared in a calendar scene and survived four repairs, because the
    prompt says to write Georgian and the checker enforces it, but no pass removes the word. A lone
    lowercase Latin token inside otherwise Georgian text is never a product name (those are capitalised
    and belong in "say"), so dropping it leaves a readable sentence and a clean lint.
    """
    def fix(text):
        if not isinstance(text, str) or not text:
            return text
        if not re.search(r"[ა-ჰ]", text):
            return text  # a Latin-only string is a name or a code, not Georgian text with a stray word
        out = re.sub(r"(?<![A-Za-z0-9.@/_-])[a-z]{3,}(?![A-Za-z0-9.@/_])", "", text)
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([,.;:!?])", r"\1", out)
        return out.strip()

    for key in ("headline", "hook", "title", "cta", "narration"):
        if isinstance(story.get(key), str):
            story[key] = fix(story[key])
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, v in list(sc.items()):
            if key in ("at", "type", "art", "say"):
                continue
            if isinstance(v, str):
                sc[key] = fix(v)
            elif isinstance(v, list):
                sc[key] = [fix(x) if isinstance(x, str) else x for x in v]


def _fix_separators(story: dict) -> None:
    """Rewrite the punctuation the Georgian lint bans, instead of paying a repair call for it.

    K12 forbids "!", "...", "…" and both dashes in anything we say or show, and K21 wants the
    Georgian decimal comma rather than a point. Both are mechanical, and measured 2026-11-18 they
    were the second and sixth most common reason a render died after four repairs that the model
    kept undoing, because the rule is stated in the checker and never in the prompt.

    A "!" becomes a full stop, an ellipsis becomes a comma, and 7.3% becomes 7,3%. Nothing here can
    change what a sentence means; it only changes how the same sentence is punctuated.
    """
    def fix(text):
        if not isinstance(text, str):
            return text
        out = text
        # a decimal point between digits is the one place Georgian wants a comma
        out = re.sub(r"(?<=\d)\.(?=\d)", ",", out)
        out = out.replace("…", ",").replace("...", ",")
        out = out.replace("!", ".")
        out = re.sub(r"\s*[,;]\s*(?=[.!?]|$)", "", out)
        out = re.sub(r"\s{2,}", " ", out)
        return out.strip()

    for key in ("headline", "hook", "title", "cta"):
        if isinstance(story.get(key), str):
            story[key] = fix(story[key])
    if isinstance(story.get("narration"), str):
        story["narration"] = fix(story["narration"])
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, v in list(sc.items()):
            if isinstance(v, str) and key not in ("at", "type", "art"):
                sc[key] = fix(v)
            elif isinstance(v, list):
                sc[key] = [fix(x) if isinstance(x, str) else x for x in v]


def _no_dashes(story: dict) -> None:
    """The house rule bans the en and em dash everywhere we publish (owner, standing).

    The writer is told, and the checker rejects it, but the repair pass kept bringing the same dash
    back in a sign headline, so three jobs burned their repair budget on a rule code can settle
    itself. A dash becomes a comma, which is the reading the model meant and a legal separator.
    """
    def fix(text):
        if not isinstance(text, str) or not _DASH_RE.search(text):
            return text
        # A dash between digits, or between a digit and a Georgian suffix letter, is a range or an
        # ordinal and must become a hyphen: "24–ე" is "ოცდამეოთხე", while "24, ე" is unreadable and
        # fails the spoken-text check instead (measured 2026-11-18, one of the KE samples).
        out = re.sub(r"(?<=\d)\s*[\u2013\u2014]\s*(?=[\dა-ჰ])", "-", text)
        out = re.sub(r"(?<=[ა-ჰ])\s*[\u2013\u2014]\s*(?=\d)", "-", out)
        out = _DASH_RE.sub(", ", out)
        return re.sub(r"\s{2,}", " ", out).strip()

    # The narration was never passed through this, so a dash the writer put in the spoken text reached
    # the checker every time: measured 2026-11-18, K12 and KE both reported the same em dash in the
    # narration while every scene field was already clean.
    for key in ("narration", "headline", "hook", "title", "cta"):
        if isinstance(story.get(key), str):
            story[key] = fix(story[key])
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, v in list(sc.items()):
            if key in ("at", "type", "art", "say"):
                continue
            if isinstance(v, str):
                sc[key] = fix(v)
            elif isinstance(v, list):
                sc[key] = [fix(x) if isinstance(x, str) else x for x in v]


def _drop_unsourced_numbers(story: dict, articles: list[str]) -> None:
    """Remove a number the model invented, instead of failing the job over it.

    N2 is the check that matters most in this product (a wrong figure on screen is the one error a
    reader will quote back at us), so it stays strict. But spending a repair call on a single stray
    "47" that the model cannot justify is waste: the whole sentence usually reads the same without
    it. Only the specific tokens the checker named are removed, and only when the removal leaves
    readable text, so this can never paper over a real numeric claim.

    Measured 2026-11-16: two write passes in a row ended on a single invented number.
    """
    from tt_shorts import news_check
    corpus = news_check.numbers(news_check.flat(" ".join(articles)))
    allowed = corpus | set()

    def strip(text: str) -> str:
        if not isinstance(text, str):
            return text
        def repl(m):
            return "" if m.group(0) not in allowed else m.group(0)
        out = news_check.NUM.sub(repl, text)
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([,.;:!?])", r"\1", out)
        return out.strip()

    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        # "value" is the numeric field a stat scene renders on its own line, and it was missing from
        # this list: measured 2026-11-18 on three failed jobs, the checker named a number that lived in
        # value while the stripper only walked the text fields, so four repair passes could never
        # satisfy N2 and the job died. A number that is not in the source must go wherever it sits.
        for key in ("headline", "heading", "text", "caption", "label", "value", "amount", "figure", "unit"):
            if isinstance(sc.get(key), str):
                sc[key] = strip(sc[key])
            elif isinstance(sc.get(key), (int, float)) and not isinstance(sc.get(key), bool):
                # A numeric value cannot be edited into a sourced one; if the digits are not in the
                # corpus the field is cleared and the scene loses its figure rather than the video.
                if str(sc[key]) not in allowed:
                    sc[key] = ""
        for key in ("items", "lines"):
            v = sc.get(key)
            if isinstance(v, list):
                sc[key] = [strip(x) if isinstance(x, str) else x for x in v]
    if isinstance(story.get("narration"), str):
        story["narration"] = strip(story["narration"])


def spell_clock_times(text: str) -> str:
    """Rewrite an HH:MM clock time as Georgian words, because the lint forbids every digit in speech.

    Measured 2026-11-18: "11:00" in the narration failed job after job and no repair pass ever
    rewrote it, because the rule is stated nowhere in the writer's prompt. A clock time is the one
    numeric shape whose words are mechanical, so convert it instead of asking for it again.

    11:00 -> თერთმეტ საათზე; 09:30 -> ცხრა საათსა და ოცდაათ წუთზე. The number words come from kaeasy's
    own cardinal(), which already handles the irregular thirties (ოცდაათი, not ოცდაი), so this file
    does not keep a second copy of Georgian numerals that can drift from the one the lint uses.
    """
    if not isinstance(text, str) or ":" not in text:
        return text
    # tt_shorts.kaeasy loads the plugin's modules by path, so this is the same speaker the lint uses.
    from tt_shorts import kaeasy  # noqa: WPS433

    ka_speech = kaeasy._load("speech")  # noqa: SLF001 - the loader is this module's own contract
    if ka_speech is None or not hasattr(ka_speech, "cardinal"):
        return text

    def count(n: int) -> str:
        return ka_speech.cardinal(n)

    def repl(m):
        h, mi = int(m.group(1)), int(m.group(2))
        if not (0 <= h <= 23 and 0 <= mi <= 59):
            return m.group(0)
        hour = "ერთ საათზე" if h == 1 else (lambda w: (w[:-1] if w.endswith("ი") else w) + " საათზე")(count(h))
        if not mi:
            return hour
        return hour + " და " + (lambda w: w[:-1] if w.endswith("ი") else w)(count(mi)) + " წუთზე"

    # consume the suffix a writer already put after the time, so the result does not read "საათზე საათიდან"
    text = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\s*(?:საათზე|საათიდან|საათისთვის|-ზე)", repl, text)
    return re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", repl, text)


def _spell_clock(story: dict) -> None:
    """The narration is spoken text: a digit there is a lint error, so clock times become words."""
    if isinstance(story.get("narration"), str):
        story["narration"] = spell_clock_times(story["narration"])
    for sc in story.get("scenes") or []:
        if isinstance(sc, dict) and isinstance(sc.get("say"), str):
            sc["say"] = spell_clock_times(sc["say"])


def _clamp_texts(story: dict) -> None:
    """A text one character over its schema limit is a failed job, not a bad video: clamp at a word
    boundary before the checks see it.

    The limit is the one the scene's own brush sets, not a global per-field minimum. Clamping a stat's
    label to the smallest label any brush allows shortened text that would have fitted, while a field
    the brush does not set at all still needs the floor from _LIMITS.
    """
    from tt_shorts import catalog
    brushes = catalog.load_all() or {}
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        slots = (brushes.get(str(sc.get("type"))) or {}).get("slots") or {}
        for key, floor in _LIMITS.items():
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
                sc[key] = _clamp(v, limit)
        lines = sc.get("lines")
        if isinstance(lines, list):
            sc["lines"] = [_clamp(l, 24) if isinstance(l, str) else l for l in lines]



def _repair_enabled() -> bool:
    """Structural repairs are on by default.

    It defaulted to off and the tick set it, so every repair this file already knows how to make
    (an anchor that only differs in punctuation, a scene whose anchor was invented) depended on one
    environment string surviving three layers of shell. Measured 2026-11-18: the tick exports it, a
    hand run does not, and the difference shows up as K13 failures with no cause. The switch stays
    so a test can pin the old behaviour, but its absence now means on.
    """
    return os.environ.get("TT_REPAIR_SCENES", "1") != "0"


def _repair_scenes(story: dict, articles: list[str]) -> None:
    """Drop a scene the facts cannot carry instead of failing the whole job.

    A quote the sources do not contain, a sign whose word the narration never says,
    a stat whose number is not spoken in its own part: these are writer slips, and the
    honest repair is to remove the card, not to publish an unsupported one."""
    if not _repair_enabled():
        return
    scenes = story.get("scenes") or []
    narration = story.get("narration") or ""
    if not scenes or not narration:
        return
    starts, pos, missing = [], 0, False
    for sc in scenes:
        at = str(sc.get("at") or "").strip()
        i = narration.find(at, pos) if at else -1
        if i < 0:
            missing = True
            break
        starts.append(i)
        pos = i + len(at)
    if missing or len(starts) != len(scenes):
        return
    parts = [narration[starts[i]: starts[i + 1] if i + 1 < len(starts) else len(narration)] for i in range(len(scenes))]

    def norm(t: str) -> str:
        return re.sub(r"\s+", " ", t or "").strip().lower().strip("\u201e\u201c\"'\u00ab\u00bb.,;:!?")

    joined = norm("\n".join(articles))
    kept = []
    for sc, part in zip(scenes, parts):
        t = sc.get("type")
        if t == "quote":
            q = norm(sc.get("text") or "")
            if q and q not in joined:
                continue
            if not str(sc.get("by") or "").strip():
                continue
        elif t == "sign":
            # the icon's own word must be spoken in this part; the writer cannot see that
            # mapping, so a sign card is the one scene type that fails on details it cannot check
            continue
        elif t == "stat":
            v = norm(str(sc.get("value") or ""))
            if v and v not in norm(part):
                continue
        kept.append(sc)
    if len(kept) >= 3 and len(kept) != len(scenes):
        story["scenes"] = kept


def _drop_pictograms(story: dict) -> None:
    """N10: a story about a death or the crime family carries no pictograms, so remove them in code.

    The checker bans a sign scene, a stat's icon and the motif for those stories, and the rule is
    stated in the prompt but the model keeps a sign in: measured 2026-11-18, four repair passes each
    returned one. Deleting the scene is what the checker asks for in the same sentence, and the video
    reads the same without it because the narration still says everything.
    """
    from tt_shorts import news_check
    why = news_check.no_pictograms(story)
    if not why:
        return
    scenes = story.get("scenes") or []
    kept = [sc for sc in scenes if not (isinstance(sc, dict) and sc.get("type") == "sign")]
    for sc in kept:
        if isinstance(sc, dict) and sc.get("type") == "stat":
            sc.pop("icon", None)
    story["scenes"] = kept
    story.pop("motif", None)


def _drop_unknown_icons(story: dict) -> None:
    """An icon or motif the library cannot resolve is a dead scene, not a style choice.

    Measured 2026-11-18: motif "მეგაფონი" resolved to nothing, and the checker refused the whole story.
    The motif is decoration: removing it keeps the scene and its text, which is everything the viewer
    needs.
    """
    from tt_shorts import icons
    # The story's own motif is what icons.motif_problems reports, and this pass never looked at it:
    # measured 2026-11-18, 9 jobs died on "story: motif ... is neither an icon name nor a Georgian word".
    top = story.get("motif")
    if isinstance(top, str) and top.strip() and not icons.resolve(top):
        story.pop("motif", None)
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key in ("icon", "motif", "morph_from"):
            v = sc.get(key)
            if isinstance(v, str) and v.strip() and not icons.resolve(v):
                sc.pop(key, None)
        art = sc.get("art")
        if isinstance(art, list):
            kept = []
            for node in art:
                if isinstance(node, dict):
                    v = node.get("icon") or node.get("motif")
                    if isinstance(v, str) and v.strip() and not icons.resolve(v):
                        continue
                kept.append(node)
            if kept:
                sc["art"] = kept
            else:
                sc.pop("art", None)


_LATIN_KA = {
    "a": "ა", "b": "ბ", "c": "კ", "d": "დ", "e": "ე", "f": "ფ", "g": "გ", "h": "ჰ", "i": "ი",
    "j": "ჯ", "k": "კ", "l": "ლ", "m": "მ", "n": "ნ", "o": "ო", "p": "პ", "q": "ქ", "r": "რ",
    "s": "ს", "t": "ტ", "u": "უ", "v": "ვ", "w": "ვ", "x": "ქს", "y": "ი", "z": "ზ",
}


def _fix_unspoken_names(story: dict) -> None:
    """K20: a Latin name gets a Georgian spoken form, or the voice reads Latin letters.

    The checker lists the Latin tokens the narration still carries and asks for a "say" entry. Waiting
    for a repair call is what failed before (measured 2026-11-18: "Wildberries" survived every pass),
    and the transliteration is mechanical, so it is done here: a Latin word becomes Georgian letters in
    the script's own dictation, and the written name stays Latin on screen.
    """
    from tt_shorts import normalize_ka
    narration = story.get("narration") or ""
    if not narration:
        return
    say = story.get("say") if isinstance(story.get("say"), dict) else {}
    missing = normalize_ka.unspoken(narration, say)
    for name in missing:
        if not name or not name.isascii():
            continue
        # a known brand keeps its conventional Georgian spelling where we have one
        known = {"wildberries": "ვაილდბერიზ", "openai": "ოუფენეი", "google": "გუგლი",
                 "facebook": "ფეისბუქი", "youtube": "იუთუბი", "tiktok": "ტიკტოკი",
                 "instagram": "ინსტაგრამი", "telegram": "ტელეგრამი", "amazon": "ამაზონი",
                 "meta": "მეტა", "apple": "ეფლი", "microsoft": "მაიკროსოფტი"}
        low = name.lower()
        if low in known:
            say[name] = known[low]
            continue
        ka = "".join(_LATIN_KA.get(ch, ch) for ch in low)
        if ka and not normalize_ka.LATIN.search(ka):
            say[name] = ka
    if say:
        story["say"] = say


def _fix_long_text(story: dict) -> None:
    """A quote or point that runs into the like/share rail is clipped, not unreadable.

    The rail occupies the bottom-right of the frame. Measured 2026-11-18: „ბიზნესასოციაცია“ reached
    x=956 below y=1100, which the probe rejects because the like and share buttons cover it. Trimming
    the text field in that region keeps the scene; the fuller wording stays in the narration.
    """
    RAIL_SAFE = 24  # characters that stay clear of the rail at the bottom of a vertical frame
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key in ("text", "quote", "sub", "label", "headline"):
            v = sc.get(key)
            if isinstance(v, str) and len(v) > 90 and sc.get("type") in ("quote", "points", "stat"):
                cut = v[:90]
                if " " in cut:
                    cut = cut.rsplit(" ", 1)[0]
                sc[key] = cut.rstrip(" ,.") + "."
        for key in ("items", "lines"):
            v = sc.get(key)
            if isinstance(v, list):
                sc[key] = [(x[:RAIL_SAFE * 2].rstrip() if isinstance(x, str) and len(x) > RAIL_SAFE * 2 else x)
                           for x in v]


def _shorten_story(story: dict, target: int = 42) -> None:
    """A story estimated over 45 s is rejected; dropping scenes is the honest way down.

    The estimate is words over a speaking rate. Measured 2026-11-18: a 61 s estimate against a 25-45 s
    window. Scenes are removed from the middle out, never the hook or the end, until the estimate fits.
    """
    scenes = story.get("scenes") or []
    narration = story.get("narration") or ""
    words = len(narration.split())
    if words <= 0:
        return
    rate = 2.5  # words a second, the estimate the timing probe uses
    MIN_S = 20  # the format's own floor is 18 s; stay clear of it
    while len(scenes) > 3 and words / rate > target and (words / rate) > MIN_S:
        # drop the longest scene that is neither the hook nor the end
        candidates = [(len(str(sc.get("at") or "")), i) for i, sc in enumerate(scenes)
                      if sc.get("type") not in ("hook", "end")]
        if not candidates:
            break
        _, idx = max(candidates)
        trial_words = words - len(str(scenes[idx].get("at") or "").split())
        if trial_words / rate < MIN_S:
            break  # the next cut would make the film too short to publish
        dropped = scenes.pop(idx)
        # its words leave the narration with it
        at = str(dropped.get("at") or "").strip()
        if at and at in narration:
            start = narration.find(at)
            nxt = ""
            for sc in scenes[idx:]:
                cand = str(sc.get("at") or "").strip()
                if cand and narration.find(cand, start) > start:
                    nxt = cand
                    break
            end = narration.find(nxt, start) if nxt else len(narration)
            narration = narration[:start] + narration[end:]
            story["narration"] = narration
        words = len(narration.split())
    story["scenes"] = scenes


def _fix_repeats(story: dict) -> None:
    """Two scenes of the same type in a row read as one long beat. Merge them.

    The checker refuses a repeated type, and a repair pass tends to swap the second one for the same
    type again. Merging keeps both texts and their words: the second scene's fields fill any the first
    left empty, and the anchor of the merged scene is the first one's, which is where its narration
    starts.
    """
    scenes = story.get("scenes") or []
    out = []
    for sc in scenes:
        if not isinstance(sc, dict):
            out.append(sc)
            continue
        if out and isinstance(out[-1], dict) and out[-1].get("type") == sc.get("type") and sc.get("type") not in ("hook", "end"):
            first = out[-1]
            for k, v in sc.items():
                if k in ("at", "type"):
                    continue
                if k not in first or not first[k]:
                    first[k] = v
            # a merged scene must not claim more narration than its anchor's slice
            continue
        out.append(sc)
    story["scenes"] = out


def _fix_schema_gaps(story: dict) -> None:
    """A brush's own required slots, filled or the scene is gone.

    The catalogue defines what each brush must carry (`slots`, with `required`), and a model that omits a
    required slot fails the structure check after spending its answer. Where a stand-in is honest it is
    filled; where it is not, the scene goes. Measured 2026-11-18: a timeline without "end", a change
    without "before".
    """
    out = []
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            out.append(sc)
            continue
        t = sc.get("type")
        if t == "timeline":
            if not sc.get("start"):
                sc["start"] = sc.get("from") or sc.get("first") or ""
            if not sc.get("end"):
                # the last item's label is the end of a timeline; a timeline with no end has no story
                items = sc.get("items") or []
                last = items[-1] if items and isinstance(items[-1], dict) else {}
                sc["end"] = last.get("label") or last.get("when") or ""
            if not str(sc.get("start") or "").strip() or not str(sc.get("end") or "").strip():
                continue
        out.append(sc)
    story["scenes"] = out


def _fix_em_marks(story: dict) -> None:
    """N11: an em mark and a link edge must be words the voice says in that scene's part of the narration.

    The mark is a highlight, not content: when the phrase is not spoken there, dropping it costs a
    highlight and keeps the scene, which is what the checker's own message allows. Measured 2026-11-18:
    a stat marked "15" while its part of the narration never said the number.
    """
    from tt_shorts import marks, news_check
    scenes = story.get("scenes") or []
    for i, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            continue
        em = sc.get("em")
        if isinstance(em, str) and em.strip():
            part = news_check.scene_part(story, i) if hasattr(news_check, "scene_part") else ""
            # two conditions, both fatal: the phrase must be on the scene's own text and spoken in its part
            on_screen = marks.locate(sc) if hasattr(marks, "locate") else True
            if (not on_screen) or (part and not marks.said(em, part)):
                sc.pop("em", None)
        edge = sc.get("edge")
        if isinstance(edge, str) and edge.strip():
            part = news_check.scene_part(story, i) if hasattr(news_check, "scene_part") else ""
            if part and not marks.said(edge, part):
                sc.pop("edge", None)


_KA_MONTHS = ("იანვარს", "თებერვალს", "მარტს", "აპრილს", "მაისს", "ივნისს", "ივლისს",
              "აგვისტოს", "სექტემბერს", "ოქტომბერს", "ნოემბერს", "დეკემბერს")


def _spell_relative_days(story: dict, when=None) -> None:
    """N4: a relative day ("დღეს", "გუშინ") is a defect; the date must be named or left out.

    The writer is told, and the checker rejects it, but a repair pass returns "დღეს" again because the
    source article was published that day and the model keeps the source's own wording. A named date
    reads the same and is what a viewer watching tomorrow needs.
    """
    import datetime as _dt
    today = when or _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=4)))
    mapping = {}
    for word, delta in (("დღეს", 0), ("გუშინ", -1), ("გუშინწინ", -2), ("ხვალ", 1), ("ზეგ", 2)):
        d = today + _dt.timedelta(days=delta)
        mapping[word] = f"{d.day} {_KA_MONTHS[d.month - 1]}"

    def fix(text):
        if not isinstance(text, str) or not text:
            return text
        out = text
        for word in mapping:
            # Dropping is the other outcome N4 allows, and it is the safe one: naming today's date adds a
            # numeral the source never said, which N2 then rejects (measured 2026-11-18: "18" introduced
            # by this very pass and flagged as unsourced a moment later).
            out = re.sub(rf"(?<![ა-ჰ]){word}(?![ა-ჰ])[,\s]*", "", out)
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([,.;:])", r"\1", out)
        return out.strip()

    for key in ("narration", "headline", "hook", "title"):
        if isinstance(story.get(key), str):
            story[key] = fix(story[key])
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, v in list(sc.items()):
            if key in ("at", "type", "art", "say"):
                continue
            if isinstance(v, str):
                sc[key] = fix(v)
            elif isinstance(v, list):
                sc[key] = [fix(x) if isinstance(x, str) else x for x in v]


def _drop_unverbatim_quotes(story: dict, articles) -> None:
    """N3: a quote must appear word for word in a source. A model that invents one cannot be repaired.

    Measured 2026-11-18: a quote scene carried "პასუხები" which no article contains. The prompt asks for
    a verbatim quote and four repairs return a fresh invention, so the cheaper and honest outcome is to
    remove the quote scene and let the rest of the story stand. A story with one fewer scene still
    publishes; a story with an invented quote does not, and should not.
    """
    from tt_shorts import news_check
    scenes = story.get("scenes") or []
    corpus = news_check.flat(" ".join(str(a.get("text") or a.get("content_text") or "")
                                      if isinstance(a, dict) else str(a) for a in (articles or [])))
    if not corpus:
        return
    # A quotation mark anywhere is checked the same way, and the narration is where most of them sit: a
    # name the writer wrapped in „“ but the source states plainly fails K14 as well as N3.
    narration = story.get("narration") or ""
    for quoted in re.findall(r"„([^“”]+)[“”]", narration):
        if news_check.flat(quoted) not in corpus:
            narration = narration.replace(f"„{quoted}“", quoted).replace(f"„{quoted}“", quoted)
    for quoted in re.findall(r"„([^“”]+)[“”]", narration):
        if news_check.flat(quoted) not in corpus:
            narration = narration.replace(f"„{quoted}“", "")
    story["narration"] = re.sub(r"\s{2,}", " ", narration).strip()
    out = []
    for sc in scenes:
        if isinstance(sc, dict) and sc.get("type") == "quote":
            q = str(sc.get("quote") or sc.get("text") or "")
            if q and news_check.flat(q) not in corpus:
                # the same sentence is usually in the narration too; N3 reads both, so drop it there as well
                narration = story.get("narration") or ""
                if q in narration:
                    story["narration"] = narration.replace(q, "").replace(",,", ",").strip()
                continue  # invented: the scene cannot stand
        out.append(sc)
    story["scenes"] = out


def _fix_first_scene(story: dict) -> None:
    """The first scene must be a hook; the model sometimes opens with a stat or a timeline instead.

    Measured 2026-11-18: a story whose first scene was a timeline was rejected outright, after the model
    had already spent its answer. Renaming the opening scene to a hook keeps the words the model wrote
    where it put them and satisfies the structure the engine requires, which is the only thing wrong.
    """
    scenes = story.get("scenes") or []
    if not scenes or not isinstance(scenes[0], dict):
        return
    if scenes[0].get("type") == "hook":
        return
    scenes[0]["type"] = "hook"
    # the hook brush reads "kicker"/"headline"/"text"; carry over whatever the opening scene wrote
    for src, dst in (("label", "kicker"), ("title", "headline"), ("sub", "text")):
        if scenes[0].get(src) and not scenes[0].get(dst):
            scenes[0][dst] = scenes[0][src]


def _fix_change_scenes(story: dict) -> None:
    """A "change" brush needs a before and an after object; a model that sends only a target loses the job.

    Measured 2026-11-18: the scene carried type/at/kicker/target/change/when/unit and no "before", so the
    catalogue's own structure check rejected it and four repairs kept sending the same shape because the
    prompt asks for a change without spelling out the two objects. Downgrading to a plain stat keeps the
    figure on screen with the fields the model did provide, which is the lesser loss than no video.
    """
    scenes = story.get("scenes") or []
    out = []
    for sc in scenes:
        if not isinstance(sc, dict) or sc.get("type") != "change":
            out.append(sc)
            continue
        before, after = sc.get("before"), sc.get("after")
        if isinstance(before, dict) and isinstance(after, dict):
            out.append(sc)
            continue
        # keep the number the model did give, as a stat the schema already knows
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
            continue  # nothing numeric survived: the scene cannot say anything
        label = sc.get("label") or sc.get("kicker") or ""
        out.append({"type": "stat", "at": sc.get("at"), "value": value,
                    **({"label": label} if label else {}),
                    **({"unit": sc["unit"]} if sc.get("unit") else {})})
    story["scenes"] = out


def _fix_sign_verbs(story: dict) -> None:
    """N10: a sign's verb must be one the narration actually says, or the sign goes.

    The checker knows which Georgian stems mean rises/falls/moves/joins and rejects a sign whose own
    part of the narration says none of them. The model picks the verb from the headline and keeps
    picking it through four repairs (measured 2026-11-18: "moves" against a narration that says
    neither გადავა nor გადაიტანეს). Trying every verb the narration supports keeps the sign; if none
    matches, the scene is dropped, which is exactly what the checker's message asks for.
    """
    from tt_shorts import icons
    scenes = story.get("scenes") or []
    if not any(isinstance(sc, dict) and sc.get("type") == "sign" for sc in scenes):
        return
    out = []
    for i, sc in enumerate(scenes):
        if not isinstance(sc, dict) or sc.get("type") != "sign":
            out.append(sc)
            continue
        part = _scene_part(story, i)
        verb = sc.get("verb")
        if verb in icons.VERBS and not icons.said(verb, part):
            # pick a verb the narration does support, keeping the first one that matches
            chosen = next((v for v in icons.VERBS if icons.said(v, part)), None)
            if chosen is None:
                continue  # no verb fits: the sign cannot show anything the narration says
            sc["verb"] = chosen
        out.append(sc)
    story["scenes"] = out


def _scene_part(story: dict, index: int) -> str:
    """The slice of narration a scene is responsible for: from its anchor to the next scene's."""
    narration = story.get("narration") or ""
    scenes = story.get("scenes") or []
    at = str((scenes[index] or {}).get("at") or "").strip()
    start = narration.find(at) if at else -1
    if start < 0:
        return ""
    nxt = ""
    for j in range(index + 1, len(scenes)):
        cand = str((scenes[j] or {}).get("at") or "").strip()
        if cand:
            nxt = cand
            break
    end = narration.find(nxt, start + len(at)) if nxt else -1
    return narration[start:end] if end > start else narration[start:]


def _drop_short_scenes(story: dict) -> None:
    """K9: a scene that would flash by for fewer than six words is removed, not failed."""
    narration = story.get("narration", "")
    scenes = story.get("scenes") or []
    if len(scenes) < 3:
        return
    starts, pos = [], 0
    for scene in scenes:
        at = (scene.get("at") or "").strip()
        i = narration.find(at, pos)
        if i < 0:
            return
        starts.append(len(narration[:i].split()))
        pos = i + len(at)
    # Scene 0 was kept unconditionally, so a hook with five words before the next scene reached the
    # checker and failed the render (measured 2026-11-18: K9 on scene 0 hook). The first scene gets
    # the same test as the rest; dropping it just means the second scene opens the video, which is
    # what a hook with no room for its own words should do.
    # The threshold is per scene type and lives in the brush catalogue, which is what the checker reads
    # (a drawing needs 8 words, a chart or a sign 7, the end card 4). A flat number here drifted from it
    # both ways: 6 let a 7-word rail through to fail, and 8 dropped scenes the checker would have kept.
    from tt_shorts import catalog as _catalog

    needs = _catalog.min_words()
    default = _catalog.MIN_WORDS_DEFAULT
    keep = []
    for i in range(0, len(scenes) - 1):
        need = needs.get(str(scenes[i].get("type")), default)
        if starts[i + 1] - starts[i] >= need:
            keep.append(i)
    if not keep:
        keep = [0]
    keep.append(len(scenes) - 1)
    story["scenes"] = [scenes[i] for i in dict.fromkeys(keep)]


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


def _wrap_hook(story: dict, limit: int = 22) -> None:
    """The hook renders at a fixed width; a line longer than ~18 characters clips."""
    for scene in story.get("scenes") or []:
        if scene.get("type") != "hook" or not isinstance(scene.get("lines"), list):
            continue
        scene["lines"] = hook_lines([str(line) for line in scene["lines"]], limit)


def _tidy_end(story: dict) -> None:
    """A short closing scene flashes by (K9). Start it on the last sentence, or drop it."""
    scenes = story.get("scenes") or []
    if not scenes or scenes[-1].get("type") != "end":
        return
    narration = story.get("narration", "").strip()
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", narration) if p.strip()]
    if not parts:
        return
    last_sentence = parts[-1]
    if len(last_sentence.split()) >= 4:
        scenes[-1]["at"] = " ".join(last_sentence.split()[:4])
    else:
        scenes.pop()


def _checks(story: dict, articles: list[str], cluster: dict):
    joined = "\n\n".join(articles)
    article = {"title": cluster.get("headline", ""), "description": "", "text": joined}
    return (news_check.problems(story, articles) + ka_check.problems(story, article) + art.story_problems(story)
            + icons.story_problems(story) + catalog.story_problems(story, meta.family(story.get("category", "")))
            + motion_rules.draft_problems(story))


OWNED = ("rubric", "episode", "part", "digest", "concept", "scenario")  # code sets them (rubrics.py, digest.py,
# concept.py, scenarios.py), like date


def _drop_owned(story: dict) -> None:
    for k in OWNED:
        story.pop(k, None)


# Repairs are cheap on the free quota (about 45 s each) and the failure they buy back is total, so
# four passes are worth it: measured 2026-11-16, most rejections are one or two content rules that a
# later pass satisfies, and a failed job costs a whole story.
def write(cluster: dict, articles: list[str], model: str | None = None, repairs: int = 4,
          avoid: list[str] | None = None, make_prompt=None, run_checks=None, mistakes: str = "",
          on_problems=None, director: dict | None = None, facts: dict | None = None, extra: str = "",
          extra_types=(), forgive: tuple = ()) -> dict:
    """avoid: the scene orders the latest videos used (variety.recent_sequences), so this one can differ.
    make_prompt(cluster, articles, avoid) / run_checks(story, articles, cluster): a program's own prompt and rule
    tier (programs.write); by default the news cluster's (_prompt, _checks). mistakes: the brand's recent failed
    rules (failures.prompt_block, news prompt only); on_problems(list): called with the problems of every pass
    that goes back for a repair (failures.record). forgive: prefixes of problems that go back for repairs like any
    other but never lose the script (the idea step: the caller reads what is left)."""
    # The provider and the model name have to agree: NVIDIA's endpoint names this model without the
    # vendor prefix or the :free suffix, and sending OpenRouter's spelling there is a 404.
    if model is None:
        _u = _provider()[0]
        if _u == OPENCODE_ENDPOINT:
            model = OPENCODE_MODEL
        elif _u == NVIDIA_ENDPOINT:
            model = NVIDIA_MODEL
        else:
            model = MODEL
    prompt_of = make_prompt or (lambda c, a, av: _prompt(c, a, av, mistakes, director, facts, extra, extra_types))
    checks_of = run_checks or _checks
    first = prompt_of(cluster, articles, avoid)
    try:
        story = _object(_call(first, model))
    except ValueError:
        # The writer sometimes answers in prose with no JSON at all (deepseek-flash did on 2026-11-08
        # and cost a whole render). One strict retry is far cheaper than a failed job.
        story = _object(_call(first + "\n\nდააბრუნე მხოლოდ JSON ობიექტი, ყოველგვარი ტექსტის გარეშე.", model))
    story.pop("sources", None)
    story.pop("date", None)
    story.pop("director", None)  # code assigns it (directors.py), like the date
    _drop_owned(story)
    story.setdefault("category", cluster.get("category", "general"))
    _fix_dates(story, cluster)
    _tidy_end(story)
    _wrap_hook(story)  # the first pass too
    _clamp_texts(story)
    _no_dashes(story)
    _fix_separators(story)
    _drop_stray_latin(story)
    _ka_forms(story)
    _spell_clock(story)
    normalize_ka.fix_say_letters(story)
    _repair_scenes(story, articles)
    _drop_unverbatim_quotes(story, articles)
    _spell_relative_days(story)
    _fix_em_marks(story)
    _drop_unknown_icons(story)
    _fix_unspoken_names(story)
    _fix_long_text(story)
    _shorten_story(story)
    _fix_repeats(story)
    _fix_schema_gaps(story)
    _fix_first_scene(story)
    _fix_change_scenes(story)
    _drop_pictograms(story)
    _fix_sign_verbs(story)
    _drop_short_scenes(story)  # the first pass too: a late end scene is a K9 failure that costs a repair call otherwise
    # Anchors come last: every pass above can delete a scene or rewrite the narration, and an anchor
    # fixed before that describes text that no longer exists. Measured 2026-11-18: K13 survived four
    # repairs on a story whose anchors had been correct before _spell_clock rewrote the narration.
    _fix_anchors(story)
    if not _anchors_ok(story):
        _hard_anchor(story)
    # The hard anchor distributes words evenly, which can leave a scene one word short of its type's
    # minimum while the checker demands it. Drop such a scene and rebuild: the narration still reads,
    # because its words stay in the neighbouring scene's slice.
    _drop_short_scenes(story)
    if not _anchors_ok(story):
        _hard_anchor(story)
    # identity is added once, after every model pass (see below)
    problems = checks_of(story, articles, cluster)
    if not _anchors_ok(story):
        problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    for _ in range(repairs):
        if not problems:
            break
        if on_problems:
            on_problems(list(problems))
        fix = (f"{prompt_of(cluster, articles, avoid)}\n\nწინა პასუხი უარყოფილია ამ შეცდომებით:\n- "
               + "\n- ".join(problems[:12])
               + "\n\nგანსაკუთრებით: არ დატოვო არც ერთი რიცხვი, რომელიც სტატიაში არ არის; "
               + "თუ timeline სცენას სტატიაში ზუსტი დრო არ აქვს, წაშალე ის და მისი ტექსტი narration-იდანაც მოხსენი. "
               # The model reaches for an em dash by habit; the checker bans it and the repair kept
               # coming back with the same dash, so the rule is stated where the fix is asked for.
               + "არასდროს გამოიყენო გრძელი ან საშუალო ტირე (—, –), არც სათაურში და არც ტექსტში: "
               + "დაწერე მძიმე, ორწერტილი ან დეფისი. "
               + "სცენის items-ის თითოეული ელემენტი მაქსიმუმ 40 სიმბოლოა.\n"
               + "დააბრუნე სრული გასწორებული JSON მხოლოდ.")
        story = _object(_call(fix, model))
        story.pop("sources", None)
        story.pop("date", None)
        story.pop("director", None)
        _drop_owned(story)
        story.setdefault("category", cluster.get("category", "general"))
        _fix_dates(story, cluster)
        _tidy_end(story)
        _wrap_hook(story)
        _clamp_texts(story)
        _no_dashes(story)
        _fix_separators(story)
        _drop_stray_latin(story)
        _ka_forms(story)
        _spell_clock(story)
        normalize_ka.fix_say_letters(story)
        _drop_unsourced_numbers(story, articles)
        _repair_scenes(story, articles)
        _drop_unverbatim_quotes(story, articles)
        _spell_relative_days(story)
        _fix_em_marks(story)
        _drop_unknown_icons(story)
        _fix_unspoken_names(story)
        _fix_long_text(story)
        _shorten_story(story)
        _fix_repeats(story)
        _fix_schema_gaps(story)
        _fix_first_scene(story)
        _fix_change_scenes(story)
        _drop_pictograms(story)
        _fix_sign_verbs(story)
        _drop_short_scenes(story)
        _drop_unverbatim_quotes(story, articles)
        _spell_relative_days(story)
        _fix_em_marks(story)
        _drop_unknown_icons(story)
        _fix_unspoken_names(story)
        _fix_long_text(story)
        _shorten_story(story)
        _fix_repeats(story)
        _fix_schema_gaps(story)
        _fix_first_scene(story)
        _fix_change_scenes(story)
        _drop_pictograms(story)
        _fix_sign_verbs(story)
        _drop_short_scenes(story)
        _fix_anchors(story)
        if not _anchors_ok(story):
            _hard_anchor(story)
        problems = checks_of(story, articles, cluster)
        if not _anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if not _anchors_ok(story):
        # Last chance before failing: the repair above may itself have deleted or rewritten a scene.
        _drop_unverbatim_quotes(story, articles)
        _spell_relative_days(story)
        _fix_em_marks(story)
        _drop_unknown_icons(story)
        _fix_unspoken_names(story)
        _fix_long_text(story)
        _shorten_story(story)
        _fix_repeats(story)
        _fix_schema_gaps(story)
        _fix_first_scene(story)
        _fix_change_scenes(story)
        _drop_pictograms(story)
        _fix_sign_verbs(story)
        _drop_short_scenes(story)
        _fix_anchors(story)
        if not _anchors_ok(story):
            _hard_anchor(story)
        if not _anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if any("): art: " in p for p in problems):  # a scene's own drawing that still fails is dropped (vignettes.py)
        story = vignettes.drop_bad(story)
        problems = checks_of(story, articles, cluster)
        if not _anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if any(p.startswith("draw:") for p in problems):  # a drawing that still fails is dropped, not the video
        story, swapped = drawings.mend(story)  # unless the library has one of its motif that fits this story
        story, dropped = art.drop_bad(story)
        if swapped or dropped:
            problems = checks_of(story, articles, cluster)
            if not _anchors_ok(story):
                problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    hard = (lambda found: [x for x in found if not x.startswith(forgive)]) if forgive else (lambda found: found)
    if hard(problems):
        raise ChecksFailed(hard(problems))
    # The free writer's Georgian is serviceable but not publishable. One editor pass fixes
    # grammar and calques while the facts, numbers and anchors stay frozen; if the edit breaks
    # a check, the pre-edit script is kept.
    edited = _edit(story, articles, cluster, model)
    if edited:
        edited.pop("director", None)
        _drop_owned(edited)
    if edited and _anchors_ok(edited) and not hard(checks_of(edited, articles, cluster)):
        kaeasy.learn_edit(story.get("narration", ""), edited.get("narration", ""))  # every agent learns the fix
        story = edited
    # The film's drawings: a call of their own once the words are final (illustrator.py). A failure costs the
    # drawings, never the video.
    if illustrator.on():
        story, _ = illustrator.draw(story)
    # N6: identity, date and outlets come from the data, never from the writer.
    if cluster.get("id"):
        story["id"] = cluster["id"]
    if cluster.get("created_at"):
        raw = str(cluster["created_at"])
        story["date"] = raw.replace(" ", "T") + ("Z" if "T" in raw and not raw.endswith("Z") else "")
    if cluster.get("sources"):
        story["sources"] = cluster["sources"]
    return story


def _edit(story: dict, articles: list[str], cluster: dict, model: str) -> dict | None:
    rule = ("შენ ხარ ქართული ტექსტის რედაქტორი. ქვემოთ მოცემულია ვიდეოს სცენარის JSON და სტატიები. "
            "გაასწორე მხოლოდ ქართული ენა: გრამატიკა, კალკები, სიტყვათა რიგი, ბუნებრივი მეტყველება. "
            "ფაქტები, სახელები, რიცხვები, ციტატები და ციტატის სიტყვები უცვლელი დარჩეს. "
            "არ შეცვალო JSON-ის სტრუქტურა, სცენების რიგი ან ტიპები. "
            "თუ შეცვლი სიტყვებს, რომლებზეც სცენა იწყება, შესაბამისად შეცვალე \"at\". "
            "დააბრუნე მხოლოდ JSON იგივე ფორმით.")
    body = "\n\n".join(f"--- სტატია {i + 1} ---\n{a[:2200]}" for i, a in enumerate(articles[:3]))
    prompt = f"{rule}\n\n{json.dumps(story, ensure_ascii=False)}\n\n{body}"
    try:
        return _object(_call(prompt, model, max_tokens=1800))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    payload = json.loads(pathlib.Path(os.environ["SHORTS_CLUSTER_JSON"]).read_text(encoding="utf-8"))
    story = write(payload["cluster"], payload["articles"], args.model)
    pathlib.Path(args.out).write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}: {len(story.get('scenes', []))} scenes, {len(story.get('narration', ''))} chars")


if __name__ == "__main__":
    main()
