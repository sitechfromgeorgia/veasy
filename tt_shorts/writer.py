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
                       motion_rules, news_check, normalise, proofread, vignettes)
from tt_shorts.normalise import HANG, hook_lines  # noqa: F401 - the hook's typesetting lives with the hook pass

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


MONTHS_KA = ("იანვარს", "თებერვალს", "მარტს", "აპრილს", "მაისს", "ივნისს", "ივლისს", "აგვისტოს",
             "სექტემბერს", "ოქტომბერს", "ნოემბერს", "დეკემბერს")


def _fix_dates(story: dict, cluster: dict) -> None:
    """N4: a video is watched for days, so „დღეს“ becomes the date the story ran.

    Known conflict, left for the N2 work: the date it writes is digits the source may not carry, which N2 then
    rejects, while normalise._spell_relative_days drops the word instead. It runs before normalise, so the drop
    never sees the words it replaced."""
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



def _spell_clock(story: dict) -> None:
    """The narration is spoken text: a digit there is a lint error, so clock times become words."""
    if isinstance(story.get("narration"), str):
        story["narration"] = spell_clock_times(story["narration"])
    for sc in story.get("scenes") or []:
        if isinstance(sc, dict) and isinstance(sc.get("say"), str):
            sc["say"] = spell_clock_times(sc["say"])


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
                # Judged as N2 judges it, by its digit runs (news_check.numbers): "3.8" is {"3", "8"}, so the
                # whole string was never in the set and every decimal value was cleared. Masked until
                # normalise stopped dropping the stat for saying „3,8" (2026-11-18).
                if not news_check.numbers(str(sc[key])) <= allowed:
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


def _wrap_hook(story: dict, limit: int = 22) -> None:
    """The hook renders at a fixed width; a line longer than ~18 characters clips."""
    for scene in story.get("scenes") or []:
        if scene.get("type") != "hook" or not isinstance(scene.get("lines"), list):
            continue
        scene["lines"] = hook_lines([str(line) for line in scene["lines"]], limit)


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
    ctx = {"cluster": cluster, "director": director, "facts": facts}  # normalise: the director's gates bind its cuts
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
    _fix_dates(story, cluster)  # stays here until the N2 work removes it (see its docstring)
    _wrap_hook(story)  # the first pass too
    _spell_clock(story)
    # Every mechanical repair code can make, in one order, to a fixpoint (normalise.py): it writes the anchors last,
    # from the cuts it made, so no pass can leave an anchor describing text that no longer exists.
    story = normalise.normalise(story, articles, ctx).story
    # identity is added once, after every model pass (see below)
    problems = checks_of(story, articles, cluster)
    if not normalise.anchors_ok(story):
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
        _wrap_hook(story)
        _spell_clock(story)
        _drop_unsourced_numbers(story, articles)
        story = normalise.normalise(story, articles, ctx).story
        problems = checks_of(story, articles, cluster)
        if not normalise.anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if not normalise.anchors_ok(story):
        # Last chance before failing: the repair above may itself have deleted or rewritten a scene.
        story = normalise.normalise(story, articles, ctx).story
        if not normalise.anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if any("): art: " in p for p in problems):  # a scene's own drawing that still fails is dropped (vignettes.py)
        story = vignettes.drop_bad(story)
        problems = checks_of(story, articles, cluster)
        if not normalise.anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if any(p.startswith("draw:") for p in problems):  # a drawing that still fails is dropped, not the video
        story, swapped = drawings.mend(story)  # unless the library has one of its motif that fits this story
        story, dropped = art.drop_bad(story)
        if swapped or dropped:
            problems = checks_of(story, articles, cluster)
            if not normalise.anchors_ok(story):
                problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    hard = (lambda found: [x for x in found if not x.startswith(forgive)]) if forgive else (lambda found: found)
    if hard(problems):
        raise ChecksFailed(hard(problems))
    # The rules check numbers, quotes, lengths and patterns; nobody read the sentences. The owner,
    # 2026-11-18: "ტექსტები სანამ დადებ რილსებზე გადაამოწმე დიფსიკის მოდელით ... თორე ძალიან ყლეობები
    # იწერება". The writer itself reads the result with one narrow question: is every word a real
    # Georgian word the context uses. A span that is not in the text cannot block, and a clean story
    # returns nothing, so the cost is one call per story and the failure mode is a held story, never a
    # wrong published one.
    if proofread.on():
        said = proofread.blocking(story, model)
        if said:
            raise ChecksFailed([f"proofread: „{f['span']}“ {f['problem']}"
                                + (f" -> {f['fix']}" if f["fix"] else "") for f in said[:6]])
    # The free writer's Georgian is serviceable but not publishable. One editor pass fixes
    # grammar and calques while the facts, numbers and anchors stay frozen; if the edit breaks
    # a check, the pre-edit script is kept.
    edited = _edit(story, articles, cluster, model)
    if edited:
        edited.pop("director", None)
        _drop_owned(edited)
    if edited and normalise.anchors_ok(edited) and not hard(checks_of(edited, articles, cluster)):
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
