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

from tt_shorts import art, drawings, icons, ka_check, kaeasy, news_check

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


SCHEMA = """
Return ONE JSON object and nothing else. Shape:
{
 "category": "politics|world|economy|society|crime|culture|sports|tech|education|region|general",
 "narration": "the spoken text, 70-95 words, sentences of 6-14 words",
 "cta": "short closing call, 4-7 words, no punctuation at the end",
 "say": {"latin-or-brand": "how to say it in Georgian"},
 "motif": "optional: the story's main icon, an icon name or the Georgian word for the thing (გაზი, მეტრო, სკოლა)",
 "scenes": [
   {"type": "hook", "at": "first words of the narration this scene starts at", "kicker": "short label", "lines": ["line 1", "line 2", "line 3"]},
   {"type": "stat", "at": "...", "kicker": "...", "headline": "...", "value": 6400, "label": "..."},
   {"type": "timeline", "at": "...", "kicker": "...", "headline": "...", "big": "22:00 -> 10:00", "start": "...", "end": "..."},
   {"type": "where", "at": "...", "kicker": "...", "place": "...", "sub": "..."},
   {"type": "who", "at": "...", "kicker": "...", "items": [{"name": "...", "role": "..."}]},
   {"type": "points", "at": "...", "kicker": "...", "items": ["...", "..."]},
   {"type": "quote", "at": "...", "kicker": "...", "text": "verbatim quote", "by": "speaker", "via": "outlet"},
   {"type": "draw", "at": "...", "kicker": "...", "headline": "...", "svg": "<g class=\"s\" style=\"--d:0.3s\">...</g>", "label": "..."},
   {"type": "pair", "at": "...", "kicker": "...", "items": [{"title": "...", "sub": "..."}, {"title": "...", "sub": "..."}], "between": "..."},
   {"type": "steps", "at": "...", "kicker": "...", "items": ["...", "...", "..."]},
   {"type": "bars", "at": "...", "kicker": "...", "unit": "...", "items": [{"label": "...", "value": 120}, {"label": "...", "value": 80}]},
   {"type": "trend", "at": "...", "kicker": "...", "unit": "...", "items": [{"label": "2023", "value": 1.2}, {"label": "2024", "value": 1.4}, {"label": "2025", "value": 1.5}]},
   {"type": "change", "at": "...", "kicker": "...", "unit": "...", "before": {"label": "...", "value": 1.2}, "after": {"label": "...", "value": 1.5}},
   {"type": "sign", "at": "...", "kicker": "...", "headline": "...", "icon": "გაზი", "verb": "stops", "label": "..."},
   {"type": "end", "at": "last words of the narration"}
 ]
}
Rules that code enforces and will send back to you:
- every number on screen and in the narration must appear in the articles;
- a quote must be verbatim from an article, inside „…“;
- no relative days (დღეს, გუშინ, ხვალ, ზეგ);
- no evaluative words, no „თქვენ“, no em dash or en dash, no „!“, „?“, „…“;
- 3 to 6 scenes; the first is hook; use the scene types that fit the story, do not invent others;
- "at" must be the exact first words of that part of the narration;
- never invent a number, time or date: if the article does not contain it, do not write it;
- do not use a "timeline" scene unless the article states exact times or dates for it;
- charts (bars, trend, change) only with values the article states, one unit, no computed differences;
  bars: 2-5 values above zero; trend: 3-8 values in time order; pair: two sides of the story; steps: 2-4 steps in order;
- "sign": one pictogram and what happens to it. icon: an icon name (flame, zap, droplet, bus, train-front, school,
  hospital, scale, tag, banknote, route, bridge, snowflake...) or the Georgian word for the thing (გაზი, დენი, წყალი,
  მეტრო, ხიდი). verb: rises|falls|stops|opens|closes|moves|splits|joins, and that scene's narration must say it
  (გაიზარდა, შემცირდა, შეწყდება, გაიხსნება, დაიხურება, გადავა, გაიყო, შეუერთდა);
- a "stat" may take an "icon": a whole count of 2-30 things is then drawn as that many icons;
- never a sign, a stat icon or a motif for crime, incidents or deaths;
- at most one "draw" scene; it is the drawing of what the story is about (see the drawing guide below);
- the last scene must start at least 4 narration words before the end, so it does not flash by.
"""


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
    """SCHEMA, with the draw scene and its style guide only when drawing is on. types: only these scene types'
    example lines (a director's, directors.scene_types); the rules stay."""
    text = SCHEMA
    if types is not None:
        keep = lambda line: not re.search(r'\{"type": "(\w+)"', line) or \
            re.search(r'\{"type": "(\w+)"', line).group(1) in types  # noqa: E731
        text = "\n".join(line for line in text.splitlines() if keep(line))
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
            director: dict | None = None, facts: dict | None = None) -> str:
    """director (directors.py, assigned by code before writing): its brief, only its scene types, the facts."""
    from tt_shorts import directors
    body = "\n\n".join(f"--- სტატია {i + 1} ---\n{a[:2600]}" for i, a in enumerate(articles[:3]))
    allowed = sorted(news_check.numbers(" ".join(articles)), key=lambda x: (len(x), x))
    allowed_line = ", ".join(allowed[:40]) if allowed else "არცერთი"
    georgian = kaeasy.prompt_block()  # free: kaeasy's ten rules + the fleet's frequent mistakes, when installed
    shape = schema(directors.scene_types(director)) if director else schema()
    direction = directors.brief_block(director, facts) if director else ""
    return (f"{STYLE}\n\n{georgian + chr(10) * 2 if georgian else ''}{shape}\n\n{direction}{_variety_line(avoid)}"
            f"{mistakes + chr(10) * 2 if mistakes else ''}"
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


def _wrap_hook(story: dict, limit: int = 22) -> None:
    """The hook renders at a fixed width; a line longer than ~18 characters clips."""
    for scene in story.get("scenes") or []:
        if scene.get("type") != "hook" or not isinstance(scene.get("lines"), list):
            continue
        out = []
        for line in scene["lines"]:
            cur = ""
            for word in str(line).split():
                cand = (cur + " " + word).strip()
                if len(cand) <= limit or not cur:
                    cur = cand
                else:
                    out.append(cur)
                    cur = word
            if cur:
                out.append(cur)
        scene["lines"] = out


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
            + icons.story_problems(story))


def write(cluster: dict, articles: list[str], model: str | None = None, repairs: int = 2,
          avoid: list[str] | None = None, make_prompt=None, run_checks=None, mistakes: str = "",
          on_problems=None, director: dict | None = None, facts: dict | None = None) -> dict:
    """avoid: the scene orders the latest videos used (variety.recent_sequences), so this one can differ.
    make_prompt(cluster, articles, avoid) / run_checks(story, articles, cluster): a program's own prompt and rule
    tier (programs.write); by default the news cluster's (_prompt, _checks). mistakes: the brand's recent failed
    rules (failures.prompt_block, news prompt only); on_problems(list): called with the problems of every pass
    that goes back for a repair (failures.record)."""
    model = model or MODEL
    prompt_of = make_prompt or (lambda c, a, av: _prompt(c, a, av, mistakes, director, facts))
    checks_of = run_checks or _checks
    story = _object(_call(prompt_of(cluster, articles, avoid), model))
    story.pop("sources", None)
    story.pop("date", None)
    story.pop("director", None)  # code assigns it (directors.py), like the date
    story.setdefault("category", cluster.get("category", "general"))
    _fix_dates(story, cluster)
    _tidy_end(story)
    _wrap_hook(story)  # the first pass too
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
        story.setdefault("category", cluster.get("category", "general"))
        _fix_dates(story, cluster)
        _tidy_end(story)
        _wrap_hook(story)
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
