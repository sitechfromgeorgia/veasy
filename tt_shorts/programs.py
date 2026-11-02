"""Programs: what kind of video, from what kind of source, under which rules (ROADMAP D12, B12).

A format (formats.py) says how a video looks and sounds; a program says what it is made from and what it may claim.
`news` is the default and is exactly what Veasy did before programs: a multi-source cluster, the writer's news
prompt, the news rules N1-N5. Every other program is a JSON file in programs/<name>.json plus a brief:

  label, about  what it is (label in Georgian, about in English for the agent)
  sources       the source kinds it takes (tt_shorts/sources); the first one is the default
  brief         the writer's instructions for it, a file in programs/briefs/ (null: the news-cluster prompt)
  scenes        "all", or the scene types it may use (hook and end always among them)
  rules         the rule tier: news (news_check.py) | claims | law (claims_check.py)
  format        its default format (formats/)
  publish       auto | review: review = a person watches the video before it goes out (the queue holds it)
  category      optional: every video of the program has this category (law -> "law")
  link          brand | source: the end card's link and QR open the brand's story page, or the source document
                (a law on matsne.gov.ge) when the source gives a URL
  writer        model (default: the writer model, from the brief) | digest: code builds the story from stories that
                already passed their checks (tt_shorts/digest.py), no model call

A new program is a JSON file and a brief, no code; `python -m tt_shorts.engine options` lists them and fails loudly
on a program the engine can't do. A story carries its program as "program" (set by the pipeline, like "brand").
"""
import json
import pathlib
import re
import urllib.parse

from tt_shorts import claims_check, formats, news_check

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "programs"
BRIEFS = DIR / "briefs"
DEFAULT = "news"
TIERS = claims_check.TIERS
PUBLISH = ("auto", "review")
LINKS = ("brand", "source")
KEYS = ("label", "about", "sources", "brief", "scenes", "rules", "format", "publish", "category", "link", "writer")
WRITERS = ("model", "digest")
REQUIRED = ("label", "sources", "rules", "format", "publish")
MAX_SOURCE = 7000  # characters of the source the writer reads (a news cluster: 3 x 2 600)


class ProgramError(ValueError):
    pass


def _sources():
    from tt_shorts import sources
    return sources.KNOWN


def validate(name, p):
    """Raise ProgramError when a program names something the engine can't do; returns it resolved."""
    def bad(msg):
        raise ProgramError(f"program {name!r}: {msg}")
    unknown = set(p) - set(KEYS) - {"name"}
    if unknown:
        bad(f"unknown keys {sorted(unknown)}")
    missing = [k for k in REQUIRED if k not in p]
    if missing:
        bad(f"missing {missing}")
    if not isinstance(p["sources"], list) or not p["sources"]:
        bad("sources must be a non-empty list")
    for s in p["sources"]:
        if s not in _sources():
            bad(f"source {s!r} is not one of {', '.join(_sources())}")
    if p["rules"] not in TIERS:
        bad(f"rules={p['rules']!r} is not one of {', '.join(TIERS)}")
    if p["publish"] not in PUBLISH:
        bad(f"publish={p['publish']!r} is not one of {', '.join(PUBLISH)}")
    link = p.get("link", "brand")
    if link not in LINKS:
        bad(f"link={link!r} is not one of {', '.join(LINKS)}")
    if p["format"] not in formats.load_all():
        bad(f"format {p['format']!r} is not a format (see options)")
    scenes = p.get("scenes", "all")
    if scenes != "all":
        if not isinstance(scenes, list):
            bad('scenes must be "all" or a list of scene types')
        wrong = [t for t in scenes if t not in news_check.SCENE_TYPES]
        if wrong:
            bad(f"unknown scene types {wrong}")
        if "hook" not in scenes or "end" not in scenes:
            bad("scenes must include hook and end")
    brief = p.get("brief")
    if brief is not None and not (BRIEFS / brief).is_file():
        bad(f"brief {brief!r} is not a file in programs/briefs/")
    if brief is None and name != DEFAULT and p["rules"] != "news":
        bad("only a news-tier program can use the news-cluster prompt (brief: null)")
    writer = p.get("writer", "model")
    if writer not in WRITERS:
        bad(f"writer={writer!r} is not one of {', '.join(WRITERS)}")
    cat = p.get("category")
    if cat is not None and not re.fullmatch(r"[a-z][a-z-]*", str(cat)):
        bad(f"category {cat!r} must be a lowercase key")
    return {**p, "name": name, "scenes": scenes, "link": link, "brief": brief, "category": cat,
            "about": p.get("about", ""), "writer": writer}


def load_all():
    """Every program in programs/*.json, validated. The default (news) must be there."""
    raw = {}
    if DIR.is_dir():
        for path in sorted(DIR.glob("*.json")):
            try:
                raw[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ProgramError(f"program {path.stem!r}: not JSON ({e})") from e
    if DEFAULT not in raw:
        raise ProgramError(f"the default program {DEFAULT!r} is missing (programs/{DEFAULT}.json)")
    return {name: validate(name, spec) for name, spec in raw.items()}


def get(name=None):
    every = load_all()
    name = name or DEFAULT
    if name not in every:
        raise ProgramError(f"unknown program {name!r}; known: {', '.join(every)}")
    return every[name]


def name_of(story):
    return story.get("program") or DEFAULT


def of(story):
    return get(name_of(story))


def summary(p):
    """What `engine options` shows of a program."""
    return {k: p[k] for k in ("label", "about", "sources", "rules", "scenes", "format", "publish", "category", "link",
                              "writer")}


def check_source(p, source):
    if source not in p["sources"]:
        raise ProgramError(f"program {p['name']!r} takes the sources {', '.join(p['sources'])}, not {source!r}"
                           + (" (try --program explainer)" if p["name"] == DEFAULT else ""))


def allowed(p, scene_type):
    return p["scenes"] == "all" or scene_type in p["scenes"]


def brief(p):
    return (BRIEFS / p["brief"]).read_text(encoding="utf-8").strip() if p.get("brief") else ""


def story_ref(p, cluster, ref):
    """The name a program's story is kept under: news keeps its ref, others <program>-<the source's id>."""
    if p["name"] == DEFAULT:
        return ref
    return f"{p['name']}-{cluster.get('id') or ref}"


# ---------------------------------------------------------------- what the pipeline adds after the writer


def doc_of(cluster):
    """The document facts a story keeps from its source (never from the writer): the act, the article, the URL."""
    return {k: cluster[k] for k in ("title", "article", "heading", "url", "version_date", "doc_id", "publication")
            if cluster.get(k) not in (None, "")}


def link_of(p, cluster):
    """The end card's link from the source's data, when the program says so, else None (the pack's story page)."""
    url = str(cluster.get("url") or "")
    if p["link"] != "source" or not url.startswith(("https://", "http://")):
        return None
    host = urllib.parse.urlparse(url).netloc.removeprefix("www.")
    return {"display": cluster.get("link_display") or host, "qr": url}


def stamp(story, p, cluster):
    """Program, category, document facts and link: data, set after the writer (like id, date and sources, N6)."""
    story.pop("link", None)  # a writer never sets where the QR goes
    if p["name"] == DEFAULT:
        return story
    story["program"] = p["name"]
    if p.get("category"):
        story["category"] = p["category"]
    story.setdefault("source", {}).update(doc_of(cluster))
    link = link_of(p, cluster)
    if link:
        story["link"] = link
    return story


# ---------------------------------------------------------------- checks


def story_problems(story):
    """A story that names a program: the program exists and allows every scene it uses."""
    try:
        p = of(story)
    except ProgramError as e:
        return [f"story: {e}"]
    return [f"scene {i} ({s.get('type')}): not a scene of program {p['name']!r} (it uses {', '.join(p['scenes'])})"
            for i, s in enumerate(story.get("scenes") or []) if s.get("type") and not allowed(p, s.get("type"))]


def length_problems(story, p=None):
    """The narration's estimated length (speech.estimate_words: ~0.75 s per Georgian word) inside the program's
    format window, so a long script goes back to the writer instead of failing the render's length check."""
    from tt_shorts import speech
    p = p or of(story)
    fmt = formats.get(p["format"])
    words = speech.estimate_words(story.get("narration", ""))
    try:
        secs = speech.scene_frames(story, words)[-1] / speech.FPS
    except (ValueError, RuntimeError, IndexError):
        return []  # a bad anchor is reported by the timing check
    if fmt["min_seconds"] <= secs <= fmt["max_seconds"]:
        return []
    n = len(story.get("narration", "").split())
    side = "shorten" if secs > fmt["max_seconds"] else "lengthen"
    return [f"timing: about {secs:.0f}s ({n} words), program {p['name']} wants {fmt['min_seconds']}-"
            f"{fmt['max_seconds']}s ({p['format']}): {side} the narration (~0.75 s per word)"]


def _allow_names(story):
    """Names a video may say that aren't in the source: the brand's own (its say map, wordmark, link) and the
    outlets from the data."""
    from tt_shorts import brand as packs
    try:
        b = packs.of(story)
    except (packs.BrandError, OSError, ValueError):
        return list(story.get("sources") or [])
    names = list(b.get("say") or {}) + [b["wordmark"]["text"], b["link"]["display"].split("/")[0]]
    return names + list(story.get("sources") or [])


def rule_problems(story, sources, doc=None):
    """The program's rule tier on a story: news -> news_check (with the articles), claims and law -> claims_check
    (the rules that need no source run without one, too)."""
    tier = of(story)["rules"]
    if tier == "news":
        return news_check.problems(story, sources) if sources else []
    return claims_check.problems(story, sources or [], tier, doc=doc, allow=_allow_names(story))


# ---------------------------------------------------------------- the writer for a program


def scene_schema(p, brand=None, director=None):
    """The writer's JSON shape, with only the program's scene types (and the director's) and the right categories."""
    from tt_shorts import brand as packs, catalog, directors, writer
    if director:
        mine = directors.scene_types(director, p["scenes"])
    else:
        mine = None if p["scenes"] == "all" else [t for t in catalog.types() if allowed(p, t)]
    lines = []
    for line in writer.schema(mine).splitlines():  # the catalog shows only the menu's lines and rules
        if line.lstrip().startswith('"category":'):
            if p.get("category"):
                continue  # the program sets it
            cats = "|".join(packs.load(brand)["categories"])
            line = f' "category": "{cats}",'
        if line.lstrip().startswith('"narration":'):
            line = ' "narration": "the spoken text (the brief says how many words), sentences of 6-14 words",'
        lines.append(line)
    return "\n".join(lines)


def prompt(p, cluster, articles, avoid=None, brand=None, director=None, found=None, extra=""):
    """The writer's prompt for a program that isn't news: the Georgian rulebook (K1-K22, not the news section),
    kaeasy's rules, the program's scenes and brief, the director's brief (directors.py), then the source."""
    from tt_shorts import directors, kaeasy, writer
    rules = writer.STYLE.split("\n## N.")[0].strip()
    body = "\n\n".join(articles)[:MAX_SOURCE]
    allowed_numbers = sorted(news_check.numbers(" ".join(articles)), key=lambda x: (len(x), x))
    georgian = kaeasy.prompt_block()
    facts = [f"სათაური: {cluster.get('headline', '')}",
             f"წყარო: {', '.join(cluster.get('sources') or []) or '-'}"]
    if cluster.get("article"):
        facts.append(f"მუხლი: {cluster['article']}")
    direction = directors.brief_block(director, found, p["scenes"]) if director else ""
    return (f"{rules}\n\n{georgian + chr(10) * 2 if georgian else ''}{scene_schema(p, brand, director)}\n\n"
            f"The program's brief (where it differs from the shape above, the brief wins):\n{brief(p)}\n\n"
            f"{direction}{extra}{writer._variety_line(avoid)}"
            f"დაწერე ამ წყაროს ვიდეოს სცენარი (პროგრამა: {p['label']}).\n" + "\n".join(facts) +
            f"\nნებადართული რიცხვები (მხოლოდ ეს): {', '.join(allowed_numbers[:60]) or 'არცერთი'}\n\n"
            f"--- წყარო ---\n{body}")


def writer_checks(p, story, articles, cluster, brand=None):
    """What the writer's draft must pass for this program (it goes back to the model with the problems)."""
    from tt_shorts import art, brand as packs, ka_check
    joined = "\n\n".join(articles)
    article = {"title": cluster.get("headline", ""), "description": "", "text": joined}
    draft = {**story, "program": p["name"], "brand": brand or packs.DEFAULT, "sources": cluster.get("sources") or []}
    out = rule_problems(draft, articles, doc=doc_of(cluster)) + ka_check.problems(story, article) + \
        art.story_problems(story) + [x for x in story_problems(draft) if not x.startswith("story:")] + \
        length_problems(story, p)
    cats = packs.load(brand)["categories"]
    if not p.get("category") and story.get("category") not in cats:
        out.append(f"story: category {story.get('category')!r} is not one of {', '.join(cats)}")
    return out


def write(p, data, brand=None, avoid=None, on_problems=None, director=None, facts=None, rubric=None, extra="",
          more_checks=None):
    """A source's data -> a story written under the program's brief, scenes and rules (writer.write does the rest:
    the model call, one or two repairs, the editor pass, identity from the data). on_problems: as writer.write's.
    A program whose writer is code (digest) builds the story without a model. rubric: its brief (extra) goes in the
    prompt and more_checks(story) in the repair loop (engine.write_story, rubrics.py)."""
    from tt_shorts import writer
    if p.get("writer") == "digest":
        from tt_shorts import digest, rubrics
        return digest.build(data, rubric or rubrics.get("digest"), brand)
    checks = (lambda s, a, c: writer_checks(p, s, a, c, brand) + (more_checks(s) if more_checks else []))
    return writer.write(data["cluster"], data["articles"], avoid=avoid,
                        make_prompt=lambda c, a, av: prompt(p, c, a, av, brand, director, facts, extra),
                        run_checks=checks, on_problems=on_problems)
