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

from tt_shorts import art, catalog, drawings, icons, ka_check, kaeasy, meta, news_check

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLE = (ROOT / "tt_shorts" / "ka_style.md").read_text(encoding="utf-8")
MODEL = os.environ.get("SHORTS_WRITER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
FALLBACK = os.environ.get("SHORTS_WRITER_FALLBACK", "")
# The writer draws ("draw" scenes): a drawing per story is what makes each video its own (owner, 2026-11-02: "1000
# videos in one style is no good"; SiTech's channel draws with a free model). No person reviews it, so code does:
# art.sanitize (safe, on brand) and art.quality (big enough, builds up, one focal part); a drawing that still fails
# after the repairs is swapped for a library drawing of the same motif (drawings.py), else dropped, and the video goes
# out without it. VEASY_WRITER_DRAW=0 turns drawing off.
DRAW_ENV = "VEASY_WRITER_DRAW"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class ChecksFailed(ValueError):
    """The script still fails the checks after the repairs; .problems lists them (failures.py remembers them)."""

    def __init__(self, problems):
        super().__init__("checks failed: " + "; ".join(problems[:6]))
        self.problems = list(problems)


# The JSON shape and the rules the writer gets: generated from the brush catalog (brushes/<type>.json, catalog.py);
# schema(types) narrows it to a director's or a program's menu.
SCHEMA = catalog.schema()


def _call(prompt: str, model: str, max_tokens: int = 1800, tries: int = 3) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, "max_tokens": max_tokens, "reasoning": {"enabled": False}}
    last = ""
    for attempt in range(tries):
        req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            msg = data["choices"][0]["message"]["content"] or ""
            if msg.strip():
                return msg
            last = "empty answer"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
            if e.code == 429:
                try:
                    return _nvidia(prompt, max_tokens)
                except Exception as nv:
                    last = f"429 and nvidia fallback failed: {nv}"
                time.sleep(20 * (attempt + 1))
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
    on. types: only these scene types' lines and rules (a director's, directors.scene_types; a program's)."""
    text = catalog.schema(types)
    if drawing() and (types is None or "draw" in types):
        return f"{text}\n{art.GUIDE}"
    return "\n".join(line for line in text.splitlines() if '"draw"' not in line) + \
        '\n- never use a "draw" scene.'


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
        "- sign სცენაზე მხოლოდ ის ხატულა/სიტყვა, რომელიც ამ სცენის ნარაციის ნაწილში ზუსტად არის ნათქვამი. თუ არა, აირჩიე points.\n"
        "- stat/bars/compare-ის ციფრი ზუსტად იმავე ნაწილის ნარაციაში უნდა ჟღერდეს, სხვა რიცხვი არ დაწერო.\n"
        "- ყოველი სცენის \"at\" არის ამ სცენის ნარაციის პირველი სიტყვები, ზუსტად.\n\n"
    )
    return (f"{STYLE}\n\n{georgian + chr(10) * 2 if georgian else ''}{shape}\n\n{direction}{extra}{_variety_line(avoid)}"
            f"{mistakes + chr(10) * 2 if mistakes else ''}{hard}"
            f"დაწერე ამ კლასტერის 30-40 წამიანი ვიდეოს სცენარი.\n"
            f"სათაური: {cluster.get('headline', '')}\n"
            f"კატეგორია: {cluster.get('category', 'general')}\n"
            f"წყაროების რაოდენობა: {cluster.get('source_count', 0)}\n"
            f"ნებადართული რიცხვები (მხოლოდ ეს): {allowed_line}\n\n{body}")


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



_LIMITS = {"kicker": 24, "headline": 40, "label": 24, "big": 12, "unit": 8, "place": 30, "sub": 30, "by": 40, "text": 200, "via": 32}


def _clamp(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:—-")


def _clamp_texts(story: dict) -> None:
    """A text that is one character over its schema limit is a failed job, not a bad video:
    clamp it at a word boundary before the checks see it."""
    for sc in story.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        for key, limit in _LIMITS.items():
            v = sc.get(key)
            if isinstance(v, str) and len(v) > limit:
                sc[key] = _clamp(v, limit)
        lines = sc.get("lines")
        if isinstance(lines, list):
            sc["lines"] = [_clamp(l, 24) if isinstance(l, str) else l for l in lines]



def _repair_enabled() -> bool:
    return os.environ.get("TT_REPAIR_SCENES", "") == "1"


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
    keep = [0]
    for i in range(1, len(scenes) - 1):
        need = 4 if scenes[i].get("type") == "end" else 6
        if starts[i + 1] - starts[i] >= need:
            keep.append(i)
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
            + icons.story_problems(story) + catalog.story_problems(story, meta.family(story.get("category", ""))))


OWNED = ("rubric", "episode", "part", "digest")  # code sets them (rubrics.py, digest.py), like date and director


def _drop_owned(story: dict) -> None:
    for k in OWNED:
        story.pop(k, None)


def write(cluster: dict, articles: list[str], model: str | None = None, repairs: int = 2,
          avoid: list[str] | None = None, make_prompt=None, run_checks=None, mistakes: str = "",
          on_problems=None, director: dict | None = None, facts: dict | None = None, extra: str = "",
          extra_types=()) -> dict:
    """avoid: the scene orders the latest videos used (variety.recent_sequences), so this one can differ.
    make_prompt(cluster, articles, avoid) / run_checks(story, articles, cluster): a program's own prompt and rule
    tier (programs.write); by default the news cluster's (_prompt, _checks). mistakes: the brand's recent failed
    rules (failures.prompt_block, news prompt only); on_problems(list): called with the problems of every pass
    that goes back for a repair (failures.record)."""
    model = model or MODEL
    prompt_of = make_prompt or (lambda c, a, av: _prompt(c, a, av, mistakes, director, facts, extra, extra_types))
    checks_of = run_checks or _checks
    story = _object(_call(prompt_of(cluster, articles, avoid), model))
    story.pop("sources", None)
    story.pop("date", None)
    story.pop("director", None)  # code assigns it (directors.py), like the date
    _drop_owned(story)
    story.setdefault("category", cluster.get("category", "general"))
    _fix_dates(story, cluster)
    _tidy_end(story)
    _wrap_hook(story)  # the first pass too
    _clamp_texts(story)
    _repair_scenes(story, articles)
    _drop_short_scenes(story)  # the first pass too: a late end scene is a K9 failure that costs a repair call otherwise
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
               + "თუ timeline სცენას სტატიაში ზუსტი დრო არ აქვს, წაშალე ის და მისი ტექსტი narration-იდანაც მოხსენი.\n"
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
        _repair_scenes(story, articles)
        _drop_short_scenes(story)
        problems = checks_of(story, articles, cluster)
        if not _anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if not _anchors_ok(story):
        problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if any(p.startswith("draw:") for p in problems):  # a drawing that still fails is dropped, not the video
        story, swapped = drawings.mend(story)  # unless the library has one of its motif that fits this story
        story, dropped = art.drop_bad(story)
        if swapped or dropped:
            problems = checks_of(story, articles, cluster)
            if not _anchors_ok(story):
                problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if problems:
        raise ChecksFailed(problems)
    # The free writer's Georgian is serviceable but not publishable. One editor pass fixes
    # grammar and calques while the facts, numbers and anchors stay frozen; if the edit breaks
    # a check, the pre-edit script is kept.
    edited = _edit(story, articles, cluster, model)
    if edited:
        edited.pop("director", None)
        _drop_owned(edited)
    if edited and _anchors_ok(edited) and not checks_of(edited, articles, cluster):
        kaeasy.learn_edit(story.get("narration", ""), edited.get("narration", ""))  # every agent learns the fix
        story = edited
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
