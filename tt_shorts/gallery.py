"""`engine gallery`: the brush book, a searchable catalogue of REAL renders of everything the kit can draw.

    python -m tt_shorts.engine gallery --real              # render what is missing, then write out/gallery/index.html
    python -m tt_shorts.engine gallery --find "a number"   # the entries that fit a need, as JSON (no render)

Nothing here is drawn by hand. Every picture is a frame (or a strip of frames) that the engine rendered:
    brush x look x theme   each brush's own `example` scene, settled, in every look and theme of the default pack
    hook, motif, enter     one forced variety option each (the option, nothing else changed); an entrance is a strip
    transition             a strip of frames across the cut between two scenes
    director, style, rubric  the kit's own preview of that choice on a fixture story
    plate                  plates/<kind>/poster.png when another lane has baked one
The catalogue reads everything from data (brushes/, variety.OPTIONS, directors/, styles/, rubrics/, plates/): a brush,
a director or a plate kind that is merged later appears by itself the next time the book is rebuilt. Files are cached
by a hash of what draws them (the item's data, the pack, Remotion's source), so a rebuild renders only what changed.

Layout of out/gallery/: stills/<id>.jpg (540x960), stories/<n>.json (the stories the stills were drawn from),
manifest.json (hash, file and the exact reproduce command per file), index.html (the page: no network, one file).
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import time
import zlib

from tt_shorts import brand, catalog, directors, rubrics, styles, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "gallery"
SIZE = (540, 960)  # a still in the book (the engine's frame is 1080x1920)
FILLER = "ეს სცენა ფუნჯების წიგნისთვის მზადდება და მის ფუნჯს აჩვენებს."
SYNONYMS = {  # what a story needs -> words an agent may type; matched against an entry's slots and text
    "number": "number count amount sum price figure how many total",
    "place": "place map where region city location town",
    "list": "list items several steps process checklist sequence",
    "time": "time date when schedule deadline calendar duration countdown",
    "compare": "compare versus difference before after against two sides",
    "change": "change trend rise fall growth over time months years",
    "quote": "quote said statement words citation",
    "share": "share percent percentage part whole",
    "rank": "rank ranking top order best worst",
    "picture": "picture icon drawing sign symbol image",
    "source": "source link article reference url",
    "word": "word term meaning glossary definition explain",
    "process": "process steps stages sequence procedure how",
}
STOP = {"a", "an", "the", "of", "for", "to", "in", "and", "or", "my", "story", "with", "show", "need", "needs"}
SLOT_NEEDS = {"num": "number", "area": "place", "list": "list", "icon": "picture", "svg": "picture", "verb": "list"}


def _sha(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8") if not isinstance(p, bytes) else p)
    return h.hexdigest()[:16]


def env_hash() -> str:
    """What every picture depends on besides its own data: Remotion's source, the brand packs, the props builder."""
    h = hashlib.sha256()
    files = sorted((ROOT / "remotion" / "src").rglob("*")) + sorted((ROOT / "brands").rglob("*.json")) \
        + [ROOT / "tt_shorts" / "props.py", ROOT / "tt_shorts" / "variety.py"]
    for f in files:
        if f.is_file():
            h.update(str(f.relative_to(ROOT)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:16]


# ------------------------------------------------------------------------------------------------ the catalogue


def themes() -> list[str]:
    """The default pack's themes, in its own order (data: brand.json)."""
    return brand.theme_names(brand.load(brand.DEFAULT))


def _needs(brush: dict) -> list[str]:
    needs = {SLOT_NEEDS[s["kind"]] for s in brush["slots"].values() if s.get("kind") in SLOT_NEEDS}
    text = " ".join([brush.get("what", ""), brush.get("use_when", "")]).lower()
    for need, words in SYNONYMS.items():
        if any(w in text.split() or w in text for w in words.split()[:3]):
            needs.add(need)
    return sorted(needs)


def _words(*texts) -> str:
    out = " ".join(t if isinstance(t, str) else json.dumps(t, ensure_ascii=False) for t in texts if t)
    for need in re.findall(r"[a-z]+", out.lower()):
        if need in SYNONYMS:
            out += " " + SYNONYMS[need]
    return out


def _txt(v) -> str:
    """A spec value as one line of text: a string as it is, a list joined, a dict as its values."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        v = list(v.values())
    return "; ".join(_txt(x) for x in v) if isinstance(v, (list, tuple)) else ("" if v is None else str(v))


def items() -> list[dict]:
    """Every entry of the book: {id, kind, title, what, use_when, avoid_when, command, scene?, words, files: {key: path}}.
    `files` are paths under out/gallery/ that `render` makes; a plate's is a path in the repo that already exists."""
    out, ths = [], themes()
    for t, b in catalog.load_all().items():
        needs = _needs(b)
        out.append({
            "id": f"brush-{t}", "kind": "brush", "title": t, "what": b["what"], "use_when": b["use_when"],
            "avoid_when": b["avoid_when"], "pairs_with": b["pairs_with"], "needs": needs,
            "scene": b["example"], "slots": {k: v.get("kind") for k, v in b["slots"].items()},
            "words": _words(t, b["what"], b["use_when"], " ".join(needs), " ".join(needs[i] for i in range(len(needs)))),
            "files": {f"{look}/{th}": f"stills/brush-{t}-{look}-{th}.jpg" for look in brand.LOOKS for th in ths}})
    for key, kind in (("hook", "hook"), ("motif", "motif"), ("enter", "entrance")):
        for o in variety.OPTIONS[key]:
            out.append({"id": f"{kind}-{o}", "kind": kind, "title": o, "what": f"the {o} {kind} of a scene's headline" if key != "motif"
                        else f"the {o} background motif behind every scene", "use_when": "chosen by variety: the least used lately",
                        "avoid_when": "never forced by hand; the novelty guard picks, so videos differ",
                        "words": _words(kind, o), "files": {"": f"stills/{kind}-{o}.jpg"}})
    from tt_shorts import props
    for o in props.TRANSITIONS:
        out.append({"id": f"transition-{o}", "kind": "transition", "title": o, "what": f"the {o} cut between two scenes (a strip of frames)",
                    "use_when": "suits the look: variety.TRANSITIONS lists which cuts go with which look",
                    "avoid_when": "not at the cost of readable text: motion_rules warns when text has under 0.5 s",
                    "words": _words("transition cut between", o), "files": {"": f"stills/transition-{o}.jpg"}})
    for d, spec in directors.load_all().items():
        out.append({"id": f"director-{d}", "kind": "director", "title": d, "what": _txt(spec.get("about") or spec.get("label") or d),
                    "use_when": _txt(spec.get("brief")), "avoid_when": _txt(spec.get("never")),
                    "words": _words("director", d, spec.get("label"), spec.get("about"), spec.get("device")),
                    "files": {"": f"stills/director-{d}.jpg"}})
    for s in styles.load_all():
        out.append({"id": f"style-{s['slug']}", "kind": "style", "title": f"{s['name_en']} ({s['slug']})", "what": s["uses"],
                    "use_when": f"programs: {', '.join(s['programs'])}; engine: {s['engine']}", "avoid_when": f"never for: {', '.join(s.get('never_families', [])) or 'nothing listed'}",
                    "words": _words("style film", s["slug"], s["name_en"], s["category"], s["uses"]),
                    "files": {"": f"stills/style-{s['slug']}.jpg"}})
    for r, spec in sorted(rubrics.load_all().items()):
        out.append({"id": f"rubric-{r}", "kind": "rubric", "title": r, "what": _txt(spec.get("about") or spec.get("chip") or r),
                    "use_when": "a named show with a chip in the hook", "avoid_when": "only when its eligibility rules hold (rubrics.py)",
                    "words": _words("rubric show chip", r, spec.get("about")), "files": {"": f"stills/rubric-{r}.jpg"}})
    for poster in sorted((ROOT / "plates").glob("*/poster.png")):
        kind = poster.parent.name
        out.append({"id": f"plate-{kind}", "kind": "plate", "title": kind, "what": f"a baked grey plate: {kind}",
                    "use_when": "behind a scene, tone only (plates/README.md)", "avoid_when": "never for news, crime, incidents or deaths",
                    "words": _words("plate background baked", kind), "files": {"": str(poster.relative_to(ROOT)).replace("\\", "/")}})
    for it in out:
        it.setdefault("pairs_with", [])
        it.setdefault("needs", [])
        it["command"] = command_for(it)
    return out


def command_for(it: dict) -> str:
    """The line an agent types to see this very thing (the stills' exact reproduce commands are in manifest.json)."""
    t = it["title"].split(" (")[0]
    if it["kind"] == "brush":
        return f"python -m tt_shorts.engine still <story with a {t} scene> --look editorial"
    if it["kind"] in ("hook", "motif", "entrance"):
        return f"python -m tt_shorts.engine options   # variety picks the {it['kind']} ({t}) by itself"
    if it["kind"] == "transition":
        return f"python -m tt_shorts.engine plan <story> --transition {t}"
    if it["kind"] == "director":
        return f"python -m tt_shorts.engine plan <story> --director {t}"
    if it["kind"] == "style":
        return f"python -m tt_shorts.engine plan <story> --style {it['id'][len('style-'):]}"
    if it["kind"] == "rubric":
        return f"python -m tt_shorts.engine rubrics   # then set \"rubric\": \"{t}\" in the story"
    return "node plates/run.mjs " + t + " --spec s.json --seconds 6 --seed 1 --out out/plates/x"


def expected_files(its=None) -> list[str]:
    """Every file under out/gallery/ (or the repo, for a plate) the catalogue promises."""
    return [p for it in (its or items()) for p in it["files"].values()]


def resolve(path: str) -> pathlib.Path:
    return (ROOT / path) if path.startswith("plates/") else OUT / path


# ------------------------------------------------------------------------------------------------ the render harness


def _story(scenes: list[dict], sid: str, extra: dict | None = None) -> dict:
    """A fixture story whose scenes are given; the narration is each scene's `at` plus a filler sentence long enough."""
    parts, out = [], []
    for sc in scenes:
        b = catalog.get(sc["type"]) if hasattr(catalog, "get") else catalog.load_all()[sc["type"]]
        need = b.get("min_words", catalog.MIN_WORDS_DEFAULT)
        at = sc.get("at") or ""
        filler = FILLER
        while len((at + " " + filler).split()) < need + 1:
            filler += " " + FILLER
        parts.append(f"{at}. {filler}".strip() if at else filler)
        out.append(dict(sc, at=at or filler.split(".")[0]))
    return {"id": sid, "brand": brand.DEFAULT, "lang": "ka", "category": "tech", "date": "2026-11-02T18:00:00Z",
            "sources": ["SiTech"], "say": {}, "cta": "გამოიწერე არხი", "narration": " ".join(parts), "scenes": out, **(extra or {})}


def _write(story: dict) -> pathlib.Path:
    d = OUT / "stories"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{story['id']}.json"
    p.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def _jpg(png: pathlib.Path, dest: pathlib.Path) -> None:
    from PIL import Image
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(png) as im:
        im.convert("RGB").resize(SIZE, Image.Resampling.LANCZOS).save(dest, "JPEG", quality=84, optimize=True)


def _strip(pngs: list[pathlib.Path], dest: pathlib.Path) -> None:
    """Frames side by side at 1/3 size: a motion you can read in one picture."""
    from PIL import Image
    ims = [Image.open(p).convert("RGB").resize((SIZE[0] // 2, SIZE[1] // 2), Image.Resampling.LANCZOS) for p in pngs]
    sheet = Image.new("RGB", (ims[0].width * len(ims), ims[0].height))
    for i, im in enumerate(ims):
        sheet.paste(im, (i * ims[0].width, 0))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, "JPEG", quality=84, optimize=True)


def _manifest() -> dict:
    p = OUT / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def render(only: str | None = None, limit: int | None = None) -> dict:
    """Render every file the catalogue promises that is missing or stale -> a report. `only` keeps one kind
    (brush, hook, motif, entrance, transition, director, style, rubric)."""
    from tt_shorts import golden, probe, props, speech, store
    t0 = time.time()
    env, man = env_hash(), _manifest()
    its = [i for i in items() if i["kind"] != "plate" and (not only or i["kind"] == only)]
    work_stills = store.work_dir("gallery-stills")
    jobs, meta = [], []
    cached = 0

    def fresh(key: str, data) -> bool:
        return man.get(key, {}).get("hash") == _sha(env, data) and (OUT / key).exists()

    def add(job_name, story, look, theme, style, post, director=None):
        path = _write(story)
        work, p = props.build(str(path), look, "silent", None, speech.EDGE_VOICES["eka"], "shorts", caption_design="page",
                              music="off", transition=style["transition"], style=style, theme=theme, director=director)
        frames = probe.settled(p["scenes"])
        jobs.append({"props": str(work / "props.json"), "public": str(work / "public"), "frames": frames,
                     "out": str(work_stills), "name": job_name})
        meta.append({"name": job_name, "p": p, "frames": frames, "post": post, "story": path, "work": work})

    # brushes: one story per (look, theme) holding every missing brush's example
    order = catalog.load_all()
    brushes = sorted((i for i in its if i["kind"] == "brush"), key=lambda i: order[i["title"]]["order"])
    for look in brand.LOOKS:
        for th in themes():
            todo = [b for b in brushes if not fresh(b["files"][f"{look}/{th}"], [b["scene"], b["title"], look, th])]
            cached += len(brushes) - len(todo)
            if limit:
                todo = todo[:limit]
            if not todo:
                continue
            scenes = [b["scene"] for b in todo]
            story = _story(scenes, f"gallery-{look}-{th}")
            kinds = [b for b in todo]
            add(f"{look}-{th}", story, look, th, golden.style_for(look), ("brush", kinds, look, th))

    fixture = [catalog.load_all()["hook"]["example"], catalog.load_all()["stat"]["example"],
               catalog.load_all()["end"]["example"]]
    base = dict(golden.style_for("editorial"))
    forced = []  # (item, style overrides, which scene, strip?)
    for i in its:
        if i["kind"] in ("hook", "motif", "entrance", "transition"):
            forced.append(i)
    for i in forced[: limit or None]:
        key = {"hook": "hook", "motif": "motif", "entrance": "enter"}.get(i["kind"])
        style = dict(base)
        if key:
            style[key] = i["title"]
        else:
            style["transition"] = i["title"]
        rel = i["files"][""]
        if fresh(rel, [i["id"], style]):
            cached += 1
            continue
        story = _story(fixture, f"gallery-{i['id']}", {"motif": "გაზი"} if i["title"] == "icons" else None)
        add(f"{i['id']}", story, "editorial", "default", style, ("variety", i, None, None))

    for i in [x for x in its if x["kind"] in ("director", "style", "rubric")][: limit or None]:
        rel = i["files"][""]
        d = i["id"].split("-", 1)[1]
        if i["kind"] == "director":
            if fresh(rel, [i["id"]]):
                cached += 1
                continue
            add(i["id"], _story(fixture, f"gallery-{i['id']}"), "editorial", "default", dict(base), ("simple", i, None, None), director=d)
        elif i["kind"] == "style":
            sty = styles.get(d)
            pick = sty["picks"]
            look = (pick.get("looks") or ["editorial"])[0]
            style = {**golden.style_for(look), "motif": (pick.get("motifs") or ["grid"])[0],
                     "transition": (pick.get("transitions") or [golden.style_for(look)["transition"]])[0]}
            if fresh(rel, [i["id"], style, look]):
                cached += 1
                continue
            dr = (pick.get("directors") or [None])[0]
            add(i["id"], _story(fixture, f"gallery-{i['id']}"), look, "default", style, ("simple", i, None, None), director=dr)
        else:
            if fresh(rel, [i["id"]]):
                cached += 1
                continue
            src = ROOT / "stories" / "rubric-24835-number.json"
            story = json.loads(src.read_text(encoding="utf-8"))
            story["id"] = f"gallery-{i['id']}"
            story["rubric"] = d
            add(i["id"], story, "editorial", "default", dict(base), ("simple", i, None, None))

    per, done = probe.run_jobs(jobs) if jobs else ([], {})
    made, problems = 0, []
    for m, rows in zip(meta, per):
        files = {x["frame"]: x["file"] for x in rows if x.get("file")}
        kind, payload, look, th = m["post"]
        frames = m["frames"]
        if kind == "brush":
            for idx, b in enumerate(payload):
                f = files.get(frames[idx]) if idx < len(frames) else None
                if not f:
                    problems.append(f"no still for {b['id']} {look}/{th}")
                    continue
                rel = b["files"][f"{look}/{th}"]
                _jpg(pathlib.Path(f), OUT / rel)
                man[rel] = {"hash": _sha(env, [b["scene"], b["title"], look, th]), "item": b["id"], "look": look, "theme": th,
                            "frame": frames[idx], "story": str(m["story"].relative_to(ROOT)).replace("\\", "/"),
                            "command": f"python -m tt_shorts.engine still {str(m['story'].relative_to(ROOT)).replace(chr(92), '/')} "
                                       f"--look {look} --theme {th} --voice silent --frames {frames[idx]}"}
                made += 1
        else:
            i = payload
            rel = i["files"][""]
            pick = {"variety": None}
            sc = m["p"]["scenes"]
            if i["kind"] == "entrance":  # a strip: the stat scene from its first frame to its settled one
                s = sc[1]
                want = [s["from"] + o for o in (1, 4, 8, 13, 20)]
                pngs = _extra_frames(m, want)
                if pngs:
                    _strip(pngs, OUT / rel)
            elif i["kind"] == "transition":  # a strip across the cut from the hook to the stat scene
                cut = sc[1]["from"]
                pngs = _extra_frames(m, [cut - 10, cut - 3, cut + 2, cut + 6, cut + 12])
                if pngs:
                    _strip(pngs, OUT / rel)
            else:
                idx = 0 if i["kind"] in ("hook", "director", "style", "rubric") else 1
                f = files.get(frames[idx])
                if f:
                    _jpg(pathlib.Path(f), OUT / rel)
            if (OUT / rel).exists():
                style = {"hook": 0}
                man[rel] = {"hash": _sha(env, _hash_data(i, m)), "item": i["id"]}
                made += 1
            else:
                problems.append(f"no picture for {i['id']}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return {"made": made, "cached": cached, "jobs": len(jobs), "problems": problems,
            "took": round(time.time() - t0, 1), "bundle_built": done.get("built")}


def _hash_data(i: dict, m: dict):
    style = m["p"]["style"]
    if i["kind"] in ("hook", "motif", "entrance", "transition"):
        key = {"hook": "hook", "motif": "motif", "entrance": "enter"}.get(i["kind"])
        base = {k: v for k, v in golden_style().items()}
        if key:
            base[key] = i["title"]
        else:
            base["transition"] = i["title"]
        return [i["id"], base]
    if i["kind"] == "style":
        s = styles.get(i["id"].split("-", 1)[1])
        pick = s["picks"]
        look = (pick.get("looks") or ["editorial"])[0]
        from tt_shorts import golden
        return [i["id"], {**golden.style_for(look), "motif": (pick.get("motifs") or ["grid"])[0],
                          "transition": (pick.get("transitions") or [golden.style_for(look)["transition"]])[0]}, look]
    return [i["id"]]


def golden_style() -> dict:
    from tt_shorts import golden
    return dict(golden.style_for("editorial"))


def _extra_frames(m: dict, frames: list[int]) -> list[pathlib.Path]:
    """Render more frames of a job already built (the strips): one probe job with the same props."""
    from tt_shorts import probe
    work = m["work"]
    out = work / "strip"
    job = {"props": str(work / "props.json"), "public": str(work / "public"), "frames": [max(0, f) for f in frames],
           "out": str(out), "name": m["name"]}
    out.mkdir(exist_ok=True)
    per, _ = probe.run_jobs([job])
    got = {x["frame"]: x["file"] for x in per[0] if x.get("file")}
    return [pathlib.Path(got[max(0, f)]) for f in frames if max(0, f) in got]


# ------------------------------------------------------------------------------------------------ search and page


def find(query: str, its=None, n: int = 5) -> list[dict]:
    """The entries that fit a need ("a number", "a place"), best first. A need word ("number") counts for the
    brushes whose slots or text carry it, more for the one that carries only it (a stat is a number, a bar is
    several); the rest is word overlap with the entry's own text. Brushes come before variety options."""
    its = its or items()
    q = {w for w in re.findall(r"[a-zა-ჰ]+", query.lower()) if w not in STOP}
    named = {need for need, words in SYNONYMS.items() if need in q or q & set(words.split())}
    q |= {w for need in named for w in SYNONYMS[need].split()}
    scored = []
    for it in its:
        text = set(re.findall(r"[a-zა-ჰ]+", (it["words"] + " " + it["title"] + " " + it["what"] + " " + it["use_when"]).lower()))
        title = set(re.findall(r"[a-z]+", it["title"].lower()))
        primary = set(re.findall(r"[a-z]+", (it["what"] + " " + it["use_when"] + " " + it["title"]).lower()))
        hit = sum(len(primary & set(SYNONYMS[nd].split())) + (3 if nd in primary else 0) for nd in named)
        score = 2.0 * hit + len(q & text) * 0.5 + 4 * len(q & title) + (2 if it["kind"] == "brush" else 0)
        if q & text or q & title or hit:
            scored.append((score, it))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    out = []
    for _, it in scored[:n]:
        first = next(iter(it["files"].values()), None)
        out.append({"id": it["id"], "type": it["kind"], "need": it["use_when"], "command": it["command"],
                    "still": first, "when_not_to_use": it["avoid_when"]})
    return out


def build_page(its=None, out_dir: pathlib.Path | None = None) -> pathlib.Path:
    """out/gallery/index.html: one file, no network. Search runs in the page over each card's `data-words`."""
    out_dir = out_dir or OUT
    its = its or items()
    ths, looks = themes(), list(brand.LOOKS)
    man = _manifest()
    cards = []
    for it in its:
        files = {k: v for k, v in it["files"].items() if resolve(v).exists() or out_dir != OUT}
        if not files:
            continue
        rel = lambda p: (str(resolve(p).resolve().as_uri()) if p.startswith("plates/") else p)  # noqa: E731
        first = next(iter(files.values()))
        if it["kind"] == "brush":
            variants = "".join(
                f'<figure data-look="{lk}" data-theme="{th}"><img loading="lazy" src="{html.escape(rel(files[f"{lk}/{th}"]))}" alt="{html.escape(it["title"])} in {lk}, {th}">'
                f'<figcaption>{lk} · {th}</figcaption></figure>' for lk in looks for th in ths if f"{lk}/{th}" in files)
            pic = f'<div class="variants">{variants}</div>'
            scene = f'<details><summary>scene JSON</summary><pre>{html.escape(json.dumps(it["scene"], ensure_ascii=False, indent=1))}</pre></details>'
            repro = next((man[f]["command"] for f in files.values() if f in man and man[f].get("command")), "")
        else:
            pic = f'<figure class="one"><img loading="lazy" src="{html.escape(rel(first))}" alt="{html.escape(it["title"])}"></figure>'
            scene, repro = "", ""
        words = html.escape(f'{it["kind"]} {it["title"]} {it["words"]} {it["what"]} {it["use_when"]}'.lower())
        cards.append(
            f'<article class="card" data-kind="{it["kind"]}" data-words="{words}" id="{it["id"]}">{pic}'
            f'<div class="body"><span class="kind">{it["kind"]}</span><h3>{html.escape(it["title"])}</h3>'
            f'<p>{html.escape(it["what"])}</p><p><b>Use when</b> {html.escape(it["use_when"])}</p>'
            f'<p class="avoid"><b>Not when</b> {html.escape(it["avoid_when"])}</p>'
            f'<div class="cmd"><code>{html.escape(it["command"])}</code><button type="button" data-copy="{html.escape(it["command"])}">copy</button></div>'
            + (f'<div class="cmd"><code>{html.escape(repro)}</code><button type="button" data-copy="{html.escape(repro)}">copy</button></div>' if repro else "")
            + f'{scene}</div></article>')
    kinds = sorted({it["kind"] for it in its})
    counts = {k: sum(1 for c in cards if f'data-kind="{k}"' in c) for k in kinds}
    chips = "".join(f'<button type="button" class="chip" data-kind="{k}">{k} {counts[k]}</button>' for k in kinds if counts[k])
    page = PAGE.replace("{{CARDS}}", "\n".join(cards)).replace("{{CHIPS}}", chips).replace("{{N}}", str(len(cards)))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "index.html"
    target.write_text(page, encoding="utf-8")
    return target


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Veasy brush book</title>
<style>
:root{--bg:#0f1115;--panel:#181b21;--ink:#f1f3f5;--mute:#9aa3ad;--line:#2a2f37;--hi:#7cc4ff}
@media (prefers-color-scheme:light){:root{--bg:#f6f4ef;--panel:#fff;--ink:#16181c;--mute:#5d6672;--line:#dcd8cf;--hi:#0a6bb5}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
h1{font-size:18px;margin:0 0 8px}.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input{flex:1 1 220px;min-width:0;padding:10px 12px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);font:inherit}
.chip,.sel{border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:6px 10px;border-radius:999px;font:inherit;font-size:13px;cursor:pointer}
.chip.on,.sel.on{background:var(--hi);color:#000;border-color:var(--hi)}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:16px;max-width:1500px;margin:0 auto}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.variants{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;background:var(--line)}
figure{margin:0;position:relative}figure img{display:block;width:100%;height:auto;background:#000}
figcaption{position:absolute;left:4px;bottom:4px;font-size:10px;background:rgba(0,0,0,.65);color:#fff;padding:1px 5px;border-radius:4px}
.one img{width:100%}.body{padding:12px 14px;display:flex;flex-direction:column;gap:6px}
h3{margin:0;font-size:17px}.kind{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--hi)}
p{margin:0;font-size:13px}.avoid{color:var(--mute)}.cmd{display:flex;gap:6px;align-items:flex-start}
code{font:12px/1.4 ui-monospace,Consolas,monospace;word-break:break-all;flex:1;background:var(--bg);padding:6px 8px;border-radius:6px}
.cmd button{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:4px 8px;cursor:pointer}
pre{font-size:11px;white-space:pre-wrap;word-break:break-word;background:var(--bg);padding:8px;border-radius:6px}
#none{display:none;padding:32px 16px;text-align:center;color:var(--mute)}
.theme-light .variants figure[data-theme=dark],.theme-dark .variants figure[data-theme=light]{display:none}
@media (max-width:520px){main{grid-template-columns:1fr;padding:12px}.variants{grid-template-columns:repeat(3,1fr)}}
</style></head><body>
<header><h1>Veasy brush book <span style="color:var(--mute);font-weight:400">· {{N}} entries, every picture a real render</span></h1>
<div class="row"><input id="q" type="search" placeholder="what does the story need? a number, a place, a process, a quote" autocomplete="off" aria-label="search">
<span id="count" style="color:var(--mute);font-size:13px"></span></div>
<div class="row" style="margin-top:8px"><button type="button" class="chip on" data-kind="">all</button>{{CHIPS}}
<span style="flex:1"></span><button type="button" class="sel" data-theme="light">light theme</button><button type="button" class="sel" data-theme="dark">dark theme</button></div></header>
<main id="grid">
{{CARDS}}
</main><div id="none">No entry matches. Try a need: number, place, list, time, compare, change, quote.</div>
<script>
const SYN={number:"count amount sum price figure total",place:"map where region city location",list:"items steps process checklist sequence",time:"date when schedule deadline calendar countdown",compare:"versus difference before after",change:"trend rise fall growth",quote:"said statement citation",share:"percent percentage whole",rank:"ranking top order",picture:"icon drawing sign symbol",source:"link article reference",word:"term meaning glossary definition"};
const STOP=new Set(["a","an","the","of","for","to","in","and","or","my","story","with"]);
const cards=[...document.querySelectorAll(".card")];let kind="",theme="";
function terms(s){const t=s.toLowerCase().split(/[^a-z\\u10d0-\\u10ff0-9]+/).filter(w=>w&&!STOP.has(w));const o=new Set(t);t.forEach(w=>{for(const k in SYN){if(k===w||(w.length>3&&k.startsWith(w.slice(0,4))))SYN[k].split(" ").forEach(x=>o.add(x))}});return [...o]}
function run(){const q=document.getElementById("q").value.trim();const t=terms(q);let n=0;
cards.forEach(c=>{const w=c.dataset.words;let ok=(!kind||c.dataset.kind===kind);let s=0;
if(t.length){t.forEach(x=>{if(w.includes(x))s++});ok=ok&&s>0}c.style.display=ok?"":"none";c.style.order=ok?-s:0;if(ok)n++});
document.getElementById("count").textContent=n+" shown";document.getElementById("none").style.display=n?"none":"block"}
document.getElementById("q").addEventListener("input",run);
document.querySelectorAll(".chip").forEach(b=>b.addEventListener("click",()=>{kind=b.dataset.kind;document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("on",x===b));run()}));
document.querySelectorAll(".sel").forEach(b=>b.addEventListener("click",()=>{theme=theme===b.dataset.theme?"":b.dataset.theme;document.querySelectorAll(".sel").forEach(x=>x.classList.toggle("on",x.dataset.theme===theme));document.body.className=theme?"theme-"+theme:""}));
document.addEventListener("click",e=>{const c=e.target.closest("[data-copy]");if(c){navigator.clipboard&&navigator.clipboard.writeText(c.dataset.copy);c.textContent="copied";setTimeout(()=>c.textContent="copy",1200)}});
run();
</script></body></html>
"""


EXAMPLES = ROOT / "examples"


def examples(seed: str = "", n: int = 3, program: str | None = None) -> dict:
    """Annotated films and one bad-to-fixed pair, rotated: the same seed gives the same ones, another seed gives
    others (agents copy what they see, so a fixed list would make every film alike). `program` keeps one program's.
    -> {"films": [...], "pair": {...}} with paths relative to the repo."""
    index = json.loads((EXAMPLES / "index.json").read_text(encoding="utf-8"))
    films = [f for f in index["films"] if not program or f["program"] == program]
    start = zlib.crc32(f"films|{seed}".encode()) % max(1, len(films))
    picked = [films[(start + i) % len(films)] for i in range(min(n, len(films)))]
    pairs = index["pairs"]
    pair = pairs[zlib.crc32(f"pairs|{seed}".encode()) % len(pairs)]
    rel = lambda f: "examples/" + f  # noqa: E731
    return {"films": [{**f, "file": rel(f["file"])} for f in picked],
            "pair": {**pair, "bad": rel(pair["bad"]), "fixed": rel(pair["fixed"])}, "of": len(films)}


def run(real: bool = False, find_query: str | None = None, only: str | None = None, limit: int | None = None,
        want_examples: bool = False, seed: str = "") -> dict:
    """The `engine gallery` command: --find, --examples, or [--real] then the page."""
    if find_query:
        return {"query": find_query, "matches": find(find_query)}
    if want_examples:
        return examples(seed)
    t0 = time.time()
    report = render(only, limit) if real else None
    its = items()
    page = build_page(its)
    have = [f for f in expected_files(its) if resolve(f).exists()]
    out = {"out": str(page.relative_to(ROOT)).replace("\\", "/"), "items": len(its), "files": len(have),
           "expected": len(expected_files(its)), "took": round(time.time() - t0, 1)}
    if report:
        out["render"] = report
    return out
