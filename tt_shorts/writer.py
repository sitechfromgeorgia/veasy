"""Cluster -> story JSON: a free model writes the script, code checks it, one repair, then it is ready to render.

The rules live in ka_style.md (K1-K22, N1-N9). This module only carries them to the model, parses the answer,
strips what the data owns (sources, date: N6) and runs the same checks the renderer trusts.

  python -m tt_shorts.writer --cluster 24725 --out stories/24725.json
"""
import argparse
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request

from tt_shorts import art, ka_check, kaeasy, news_check

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLE = (ROOT / "tt_shorts" / "ka_style.md").read_text(encoding="utf-8")
MODEL = os.environ.get("SHORTS_WRITER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
FALLBACK = os.environ.get("SHORTS_WRITER_FALLBACK", "")
# The writer may draw ("draw" scenes) only when VEASY_WRITER_DRAW=1: videos go out without a review, and a free
# model's drawings are unproven here. An agent writing a story by hand can always use draw.
DRAW_ENV = "VEASY_WRITER_DRAW"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

SCHEMA = """
Return ONE JSON object and nothing else. Shape:
{
 "category": "politics|world|economy|society|crime|culture|sports|tech|education|region|general",
 "narration": "the spoken text, 70-95 words, sentences of 6-14 words",
 "cta": "short closing call, 4-7 words, no punctuation at the end",
 "say": {"latin-or-brand": "how to say it in Georgian"},
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
    return os.environ.get(DRAW_ENV, "0") == "1"


def schema() -> str:
    """SCHEMA, with the draw scene and its style guide only when drawing is on."""
    if drawing():
        return f"{SCHEMA}\n{art.GUIDE}"
    return "\n".join(line for line in SCHEMA.splitlines() if '"draw"' not in line) + \
        '\n- never use a "draw" scene.'


def _prompt(cluster: dict, articles: list[str]) -> str:
    body = "\n\n".join(f"--- სტატია {i + 1} ---\n{a[:2600]}" for i, a in enumerate(articles[:3]))
    allowed = sorted(news_check.numbers(" ".join(articles)), key=lambda x: (len(x), x))
    allowed_line = ", ".join(allowed[:40]) if allowed else "არცერთი"
    georgian = kaeasy.prompt_block()  # free: kaeasy's ten rules + the fleet's frequent mistakes, when installed
    return (f"{STYLE}\n\n{georgian + chr(10) * 2 if georgian else ''}{schema()}\n\n"
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
    art = {"title": cluster.get("headline", ""), "description": "", "text": joined}
    return news_check.problems(story, articles) + ka_check.problems(story, art)


def write(cluster: dict, articles: list[str], model: str | None = None, repairs: int = 2) -> dict:
    model = model or MODEL
    story = _object(_call(_prompt(cluster, articles), model))
    story.pop("sources", None)
    story.pop("date", None)
    story.setdefault("category", cluster.get("category", "general"))
    _tidy_end(story)  # the first pass too: a late end scene is a K9 failure that costs a repair call otherwise
    # identity is added once, after every model pass (see below)
    problems = _checks(story, articles, cluster)
    if not _anchors_ok(story):
        problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    for _ in range(repairs):
        if not problems:
            break
        fix = (f"{_prompt(cluster, articles)}\n\nწინა პასუხი უარყოფილია ამ შეცდომებით:\n- "
               + "\n- ".join(problems[:12])
               + "\n\nგანსაკუთრებით: არ დატოვო არც ერთი რიცხვი, რომელიც სტატიაში არ არის; "
               + "თუ timeline სცენას სტატიაში ზუსტი დრო არ აქვს, წაშალე ის და მისი ტექსტი narration-იდანაც მოხსენი.\n"
               + "დააბრუნე სრული გასწორებული JSON მხოლოდ.")
        story = _object(_call(fix, model))
        story.pop("sources", None)
        story.pop("date", None)
        story.setdefault("category", cluster.get("category", "general"))
        _tidy_end(story)
        problems = _checks(story, articles, cluster)
        if not _anchors_ok(story):
            problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if not _anchors_ok(story):
        problems.append("K13: every scene \"at\" must be the exact first words of its part of the narration, in order")
    if problems:
        raise ValueError("checks failed: " + "; ".join(problems[:6]))
    # The free writer's Georgian is serviceable but not publishable. One editor pass fixes
    # grammar and calques while the facts, numbers and anchors stay frozen; if the edit breaks
    # a check, the pre-edit script is kept.
    edited = _edit(story, articles, cluster, model)
    if edited and _anchors_ok(edited) and not _checks(edited, articles, cluster):
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
