"""The media layer: pictures for a story's scenes, resolved into local files and a ledger, for any engine.

The writer may only suggest a picture: a scene's `show` hint (catalog.py: a short English query, "gas pipeline
repair"; or "screenshot" for the story's own official page). Code does the rest, before the voice is made:

    resolve(story)   each hint -> a search (cached), a deterministic pick (the same story picks the same file), a
                     fetch into store.media_dir, a ledger entry in the story's code-owned `assets` list and the
                     scene's code-owned `media` = {"asset": <ledger id>}
    problems(story)  the ledger's own checks (`engine check`): an allowed licence, an author where the licence
                     needs a credit, every scene's media in the ledger; news rule N13 is news_check.imagery
    for_props(...)   the files copied into a render's public/media/ and what each scene draws: the file, the pack's
                     „საილუსტრაციო" label and the credit line, both drawn small in the scene band

Remotion and HyperFrames never see a provider, a URL or a key: they draw local files. A ledger entry:

    {"id", "kind" (photo | video | screenshot | illustration | ai), "provider", "url" (the file fetched), "page"
     (where its licence is shown), "licence", "licence_version", "author", "title", "source", "query" (the hint),
     "fetched" (UTC), "sha" (sha256 of the local file), "file" (under $VEASY_HOME), "width", "height"}

Licences (LICENCES): only ones that allow commercial reuse. cc0 and pdm, then pexels and pixabay (their own free
licences), then CC BY, then CC BY-SA last: a picture under BY-SA inside a video may make the video an adaptation
under the same licence, so a pick prefers anything else. BY and BY-SA always get their credit on screen; every
stock picture does, in fact (one rule is simpler to check). `screenshot` is the licence of a proof shot of an
allow-listed official or own page (news_check N13).

No AI generation in this phase (media/ai.py is the disabled interface; N13 refuses an "ai" asset).
"""
import datetime as dt
import functools
import hashlib
import json
import os
import pathlib
import re
import shutil

from tt_shorts import store
from tt_shorts.media import MediaError

PROVIDERS = ("openverse", "commons", "pexels", "pixabay", "screenshot", "ai")
KINDS = ("photo", "video", "screenshot", "illustration", "ai", "plate")
ILLUSTRATIVE = ("photo", "video", "illustration", "ai")  # pictures that only illustrate: they carry the label
LICENCES = {"cc0": "CC0", "pdm": "Public Domain", "pexels": "Pexels", "pixabay": "Pixabay", "by": "CC BY",
            "by-sa": "CC BY-SA", "screenshot": None, "own": "Own"}
CREDITED = ("by", "by-sa")  # a credit (the author) is a condition of the licence
RANK = {"cc0": 0, "pdm": 0, "pexels": 1, "pixabay": 1, "by": 2, "by-sa": 3}
ENTRY_KEYS = ("id", "kind", "provider", "url", "licence", "author", "title", "fetched", "sha", "file")
TOP = 4  # the pick is made among the best TOP candidates of a hint, by the story's id: varied, yet fixed per story
MIN_SIDE = 640  # a picture smaller than this on its short side would be mush across a 1080 frame
# Titles a pick avoids: pictures of an event (an incident, a disaster), of text (maps, charts, logos, posters:
# text inside an image is unchecked text) and portraits (a stranger's face read as the story's subject).
AVOID = ("fire", "blaze", "explosion", "explode", "accident", "crash", "wreck", "collapse", "disaster", "flood",
         "police", "arrest", "protest", "riot", "war", "soldier", "army", "weapon", "gun", "dead", "death", "corpse",
         "body", "blood", "victim", "funeral", "injur", "wound", "map", "diagram", "chart", "graph", "infographic",
         "logo", "poster", "banner", "sign", "screenshot", "flag", "text", "portrait", "selfie", "headshot", "meme",
         "strike", "climatestrike", "demonstrat", "rally", "march")
STOP = ("the", "and", "with", "for", "from", "of", "in", "on", "at", "night", "day", "view")
SHOW_MAX = 80
CREDIT_MAX = 44  # characters: the label and the credit fit one 24 px row left of the rail, in every look
_SHOW_WORDS = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ,'&-]*")


def provider(name):
    import importlib
    if name not in PROVIDERS:
        raise MediaError(f"unknown media provider {name!r}; known: {', '.join(PROVIDERS)}")
    return importlib.import_module(f"tt_shorts.media.{name}")


def availability():
    """{provider: None (usable here) | why not}: `engine options` and `doctor` show it."""
    return {n: provider(n).available() for n in PROVIDERS}


# ---------------------------------------------------------------- the hint


def parse_show(show):
    """A scene's show hint -> (kind, what): ("photo", "gas pipeline repair"), ("video", "..."), ("screenshot", None
    = the story's own link) or ("screenshot", "<url> | <phrase>")."""
    s = (show or "").strip()
    low = s.lower()
    if low == "screenshot":
        return "screenshot", None
    for prefix, kind in (("screenshot:", "screenshot"), ("video:", "video"), ("stock:", "photo"), ("photo:", "photo")):
        if low.startswith(prefix):
            return kind, s[len(prefix):].strip()
    return "photo", s


def show_problems(scene):
    """The writer's hint: a short plain English query (1-6 words), or a screenshot of a page."""
    show = scene.get("show")
    if show is None:
        return []
    if not isinstance(show, str) or not show.strip():
        return ["show: a short English search query (gas pipeline repair) or screenshot"]
    if len(show) > SHOW_MAX:
        return [f"show: {len(show)} characters, at most {SHOW_MAX}"]
    kind, what = parse_show(show)
    if kind == "screenshot":
        url = (what or "").split("|")[0].strip()
        return [] if what is None or re.match(r"https?://", url) else ["show: screenshot:<https url> [| phrase]"]
    if not _SHOW_WORDS.fullmatch(what or "") or not 1 <= len(what.split()) <= 6:
        return [f"show: „{show}“ is not a plain English query of 1-6 words (latin letters, digits, spaces)"]
    return []


# ---------------------------------------------------------------- search and pick


def search(name, kind, query, n=20):
    """One provider's candidates for a query, cached for good in store.media_dir (deterministic re-runs; Pixabay's
    terms ask for it). A provider that is unavailable here finds nothing."""
    mod = provider(name)
    if kind not in mod.KINDS or mod.available():
        return []
    d = store.media_dir(f"search:{name}:{kind}:{query.strip().lower()}:{n}")
    cached = d / "search.json"
    if cached.is_file():
        os.utime(d)
        return json.loads(cached.read_text(encoding="utf-8"))["results"]
    results = mod.search(query, kind, n)
    cached.write_text(json.dumps({"provider": name, "kind": kind, "query": query, "n": n, "results": results,
                                  "fetched": _now()}, ensure_ascii=False), encoding="utf-8")
    return results


def relevant(c, query):
    """True when the picture's title or tags name a word of the query (a search engine's fuzzy match is not
    enough: "gas pipeline" must not bring a climate march)."""
    if not query:
        return True
    want = [w[:5] for w in re.findall(r"[a-z]+", query.lower()) if len(w) >= 3 and w not in STOP]
    have = re.findall(r"[a-z]+", f"{c.get('title') or ''} {' '.join(c.get('tags') or [])}".lower())
    return not want or any(h.startswith(w) for w in want for h in have)


def usable(c, cmap=None, query=None):
    """Why a candidate can't be used, or None. The licence is checked here again (a provider's filter is only a
    convenience)."""
    if c.get("licence") not in LICENCES or c.get("licence") == "screenshot" or c.get("kind") not in ILLUSTRATIVE:
        return f"licence {c.get('licence')!r} / kind {c.get('kind')!r} not allowed"
    if c["kind"] == "ai":
        return "AI imagery is off"
    if c["licence"] in CREDITED and not credit_text(c.get("author"), cmap):
        return "no author to credit"
    words = re.findall(r"[a-z]+", f"{c.get('title') or ''} {' '.join(c.get('tags') or [])}".lower())
    hit = next((a for a in AVOID if any(w.startswith(a) for w in words)), None)
    if hit:
        return f"its title or tags say {hit!r}"
    if not relevant(c, query):
        return "its title names nothing of the query"
    w, h = c.get("width") or 0, c.get("height") or 0
    if w and h and min(w, h) < MIN_SIDE:
        return f"too small ({w}x{h})"
    return None


def order(cands):
    """Best first: the freest licence, then a picture that fills a tall band (taller than 3:4), then as found."""
    def key(ic):
        i, c = ic
        w, h = c.get("width") or 1, c.get("height") or 1
        return RANK.get(c["licence"], 9), 0 if h / w >= 0.75 else 1, i
    return [c for _, c in sorted(enumerate(cands), key=key)]


def pick(cands, seed):
    """A deterministic choice among the TOP best: the same story and scene always get the same picture."""
    if not cands:
        return None
    best = RANK.get(cands[0].get("licence"), 9)  # only among the freest licence found (BY-SA only when nothing else)
    top = [c for c in cands if RANK.get(c.get("licence"), 9) == best][:TOP]
    return top[int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(top)]


def asset_id(c):
    return hashlib.sha256(f"{c['provider']}:{c['id']}".encode("utf-8")).hexdigest()[:16]


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def entry(c, path):
    """A fetched candidate -> its ledger entry (asset.json in its cache folder keeps the first fetch's date)."""
    from tt_shorts.media import files
    path = pathlib.Path(path)
    meta = path.parent / "asset.json"
    if meta.is_file():
        old = json.loads(meta.read_text(encoding="utf-8"))
        if old.get("sha") == files.sha256(path):
            return old
    e = {"id": asset_id(c), "kind": c["kind"], "provider": c["provider"], "provider_id": c["id"], "url": c["url"],
         "page": c.get("page", ""),
         "licence": c["licence"], "licence_version": c.get("licence_version", ""), "author": c.get("author", ""),
         "title": c.get("title", ""), "source": c.get("source", ""), "fetched": _now(), "sha": files.sha256(path),
         "file": path.resolve().relative_to(store.home().resolve()).as_posix(), "width": c.get("width") or 0,
         "height": c.get("height") or 0}
    for k in ("duration", "find", "found", "box", "landed"):
        if c.get(k) is not None:
            e[k] = c[k]
    meta.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
    return e


# ---------------------------------------------------------------- the pack's and the program's rules


def pack_media(b):
    return b.get("media") or {}


def allow_list(story, b=None):
    """The domains a screenshot may come from: the pack's official and own sites, plus the program's."""
    from tt_shorts import brand, programs
    b = b or brand.of(story)
    m = pack_media(b)
    extra = []
    if "program" in story:
        try:
            extra = programs.of(story).get("screenshots") or []
        except programs.ProgramError:
            pass
    return list(dict.fromkeys([*(m.get("official") or []), *(m.get("own") or []), *extra]))


def own_link(story, b=None):
    """The story's own page, for the hint "screenshot": its link (a law's article on matsne.gov.ge), else none."""
    url = story.get("url") or (story.get("source") or {}).get("url") or ""
    return url if re.match(r"https?://", url) else None


# ---------------------------------------------------------------- resolve


def resolve(story, b=None, providers=None, fetch=True):
    """Fill the scenes' media and the story's ledger from their show hints -> (story, report). Deterministic per story
    (cached searches, a seeded pick); a scene keeps its picture while its hint is unchanged (no network then). A
    provider error leaves that scene without a picture, never fails the story. No media at all for the crime
    family or a story about deaths (news rule N13), except screenshots. providers: the order to ask (default the
    pack's media.providers). fetch=False: only what is already in the ledger (offline)."""
    from tt_shorts import brand, catalog, news_check
    b = b or brand.of(story)
    story = json.loads(json.dumps(story))  # a copy: the caller's story is untouched
    names = [p for p in (providers or pack_media(b).get("providers") or []) if p in PROVIDERS and p != "screenshot"]
    ledger = {e["id"]: e for e in story.get("assets") or [] if isinstance(e, dict) and e.get("id")}
    report = {"scenes": {}, "errors": [], "skipped": None}
    why_not = news_check.no_imagery(story)
    cmap = font_cmap(b["_fonts"]["400"])
    used = set()
    for i, s in enumerate(story.get("scenes") or []):
        show = s.get("show")
        if not show or s.get("type") in catalog.NO_MEDIA or show_problems(s):
            s.pop("media", None)
            continue
        kind, what = parse_show(show)
        if why_not and kind != "screenshot":
            s.pop("media", None)
            report["skipped"] = f"N13: no illustrative imagery in a story about {why_not}"
            continue
        have = ledger.get((s.get("media") or {}).get("asset"))
        if have and have.get("query") == show and have["id"] not in used:
            used.add(have["id"])
            report["scenes"][i] = {"asset": have["id"], "kept": True}
            continue
        s.pop("media", None)
        if not fetch:
            continue
        try:
            e = _resolve_one(story, b, i, kind, what, names, used, cmap)
        except MediaError as err:
            report["errors"].append(f"scene {i}: {err}")
            continue
        if not e:
            report["errors"].append(f"scene {i}: nothing usable found for „{show}“")
            continue
        e = {**e, "query": show}
        ledger[e["id"]] = e
        used.add(e["id"])
        s["media"] = {"asset": e["id"]}
        report["scenes"][i] = {"asset": e["id"], "provider": e["provider"], "licence": e["licence"]}
    kept = [ledger[k] for k in dict.fromkeys(m["asset"] for m in (s.get("media") for s in story.get("scenes") or [])
                                              if m) if k in ledger]
    kept += [e for e in (story.get("assets") or []) if e.get("kind") == "plate" and e["id"] in {
        (s.get("plate") or {}).get("asset") for s in story.get("scenes") or [] if isinstance(s, dict)}]  # plates.py's
    if kept:
        story["assets"] = kept
    else:
        story.pop("assets", None)
    return story, report


def _resolve_one(story, b, i, kind, what, names, used, cmap):
    if kind == "screenshot":
        from tt_shorts.media import screenshot
        url, _, find = (what or own_link(story, b) or "").partition("|")
        if not url.strip():
            raise MediaError("the story has no page of its own to shoot")
        c = screenshot.capture(url.strip(), allow_list(story, b), find.strip() or None, b["colors"]["accent"])
        return entry(c, c["file"])
    cands, errors = [], []
    for name in names:
        try:
            cands += search(name, kind, what)
        except MediaError as err:
            errors.append(str(err))
    good = order([c for c in cands if not usable(c, cmap, what) and asset_id(c) not in used])
    seed = f"{story.get('id')}|{i}|{what.lower()}"
    while good:
        c = pick(good, seed)
        try:
            path = provider(c["provider"]).fetch(c)
            return entry(c, path)
        except MediaError as err:  # a dead link: the next one
            errors.append(str(err))
            good.remove(c)
    if errors and not cands:
        raise MediaError("; ".join(errors))
    return None


def resolve_file(path, fetch=True):
    """Resolve a story file in place (only when something changed) -> report (+ "changed")."""
    from tt_shorts import brand
    path = pathlib.Path(path)
    story = json.loads(path.read_text(encoding="utf-8"))
    new, report = resolve(story, brand.of(story), fetch=fetch)
    report["changed"] = new != story
    if report["changed"]:
        path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    report["assets"] = len(new.get("assets") or [])
    return report


def strip_code_owned(story):
    """What only code may write (a writer's media or ledger is dropped before the story is checked)."""
    story.pop("assets", None)
    for s in story.get("scenes") or []:
        if isinstance(s, dict):
            s.pop("media", None)
            s.pop("plate", None)
    return story


# ---------------------------------------------------------------- checks


def problems(story):
    """The ledger's own checks (`engine check`, every program): a licence that allows commercial reuse, its credit,
    a well-formed entry, and every scene's media in the ledger. N13's rules are news_check.imagery."""
    from tt_shorts import catalog
    out = []
    raw = story.get("assets")
    if raw is not None and not isinstance(raw, list):
        return ["assets: a list of ledger entries (code's, never the writer's)"]
    ids = set()
    for k, e in enumerate(raw or []):
        where = f"assets[{k}]"
        if not isinstance(e, dict):
            out.append(f"{where}: a ledger entry is an object")
            continue
        missing = [x for x in ENTRY_KEYS if x not in e]
        if missing:
            out.append(f"{where}: missing {', '.join(missing)}")
            continue
        if e.get("kind") == "plate":  # a baked plate (plates.py): its own checks, no provider or url to fetch again
            from tt_shorts import plates
            if e["id"] in ids:
                out.append(f"{where}: {e['id']} is in the ledger twice")
            ids.add(e["id"])
            out += [f"{where}: {x}" for x in plates.entry_problems(e)]
            continue
        if e["id"] in ids:
            out.append(f"{where}: {e['id']} is in the ledger twice")
        ids.add(e["id"])
        if e["kind"] not in KINDS:
            out.append(f"{where}: kind {e['kind']!r} is not one of {', '.join(KINDS)}")
        if e["provider"] not in PROVIDERS:
            out.append(f"{where}: provider {e['provider']!r} is not one of {', '.join(PROVIDERS)}")
        if e["licence"] not in LICENCES:
            out.append(f"{where}: licence {e['licence']!r} doesn't allow commercial reuse (allowed: "
                       f"{', '.join(LICENCES)})")
        elif (e["licence"] == "screenshot") != (e["kind"] == "screenshot"):
            out.append(f"{where}: the licence screenshot is a screenshot's, and only a screenshot's")
        if e["licence"] in CREDITED and not str(e.get("author") or "").strip():
            out.append(f"{where}: {LICENCES[e['licence']]} needs its author credited, and the ledger has none")
        if not re.fullmatch(r"[0-9a-f]{64}", str(e["sha"])):
            out.append(f"{where}: sha is the file's sha256")
        if not str(e["file"]).startswith("cache/media/") or ".." in str(e["file"]):
            out.append(f"{where}: file is under cache/media/ ($VEASY_HOME)")
        if not re.match(r"https?://", str(e["url"])):
            out.append(f"{where}: url is where the file came from (http/https)")
    for i, s in enumerate(story.get("scenes") or []):
        if not isinstance(s, dict):
            continue
        out += [f"scene {i} ({s.get('type')}): {x}" for x in show_problems(s)]
        m = s.get("media")
        if m is None:
            continue
        if not isinstance(m, dict) or set(m) != {"asset"}:
            out.append(f"scene {i} ({s.get('type')}): media is code's: {{\"asset\": <ledger id>}}")
        elif m["asset"] not in ids:
            out.append(f"scene {i} ({s.get('type')}): media {m['asset']} is not in the story's assets ledger")
        if s.get("type") in catalog.NO_MEDIA:
            out.append(f"scene {i} ({s.get('type')}): a {s.get('type')} scene carries no picture")
    return out


# ---------------------------------------------------------------- what a render draws


@functools.lru_cache(maxsize=8)
def font_cmap(path):
    """The code points the pack's font has (the credit is set in it; the probe fails a missing glyph)."""
    from fontTools.ttLib import TTFont
    return frozenset(TTFont(str(path)).getBestCmap())


def credit_text(text, cmap=None, most=28):
    """A name fit for the credit line: one line, in the font's glyphs, at most `most` characters."""
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    if cmap is not None:
        s = "".join(ch for ch in s if ord(ch) in cmap or ch == " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s if len(s) <= most else s[:most - 1].rstrip() + "…"


def credit(e, b):
    """The credit line of one asset, by the pack's template („{author} · {licence} · {source}“)."""
    cmap = font_cmap(b["_fonts"]["400"])
    if e["kind"] == "screenshot":
        return credit_text(e.get("source") or e.get("url"), cmap, 40)
    lic = LICENCES.get(e["licence"]) or e["licence"]
    if e.get("licence_version") and e["licence"] in ("by", "by-sa", "cc0"):
        lic = f"{lic} {e['licence_version']}"
    source = credit_text(e.get("source"), cmap, 20)

    def line(author, src):
        text = b["strings"]["media_credit"].format(author=author, licence=lic, source=src)
        text = re.sub(r"(\s*·\s*)+$", "", re.sub(r"(\s·\s)(\s*·\s)+", " · ", text))
        return re.sub(r"^(\s*·\s*)+", "", text).strip()
    author = credit_text(e.get("author"), cmap) or source
    text = line(author, source if author != source else "")  # no author: the collection, once
    if len(text) > CREDIT_MAX and author != source:  # the source goes first: the author is what a licence asks
        text = line(author, "")
    if len(text) > CREDIT_MAX:
        text = line(credit_text(author, None, max(8, len(author) - (len(text) - CREDIT_MAX))), "")
    return text


def local_file(e, verify=True):
    """The asset's file under $VEASY_HOME; fetched again (and checked against the ledger's sha) when gc took it."""
    from tt_shorts.media import files
    path = store.home() / e["file"]
    if not path.is_file():
        got = pathlib.Path(provider(e["provider"]).fetch(_candidate_of(e)))
        if got.resolve() != path.resolve():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(got, path)
    if verify and files.sha256(path) != e["sha"]:
        raise MediaError(f"asset {e['id']}: the file is not the one in the ledger (sha differs): resolve the story "
                         "again")
    os.utime(path.parent)
    return path


def _candidate_of(e):
    """A ledger entry -> the candidate its provider fetches again (the provider's own id is the cache folder's)."""
    return {**e, "id": e.get("provider_id") or e["id"]}


def for_props(story, b, public, fps=30):
    """Copy every asset a scene uses into public/media/ -> {asset id: what a scene draws}: {kind (image | video),
    what (the ledger's kind), src, label, credit, frames (a clip's length)}. The label is the pack's own word for an
    illustration; a screenshot gets none (it is the page itself), and its credit names the site."""
    ledger = {e["id"]: e for e in story.get("assets") or []}
    out = {}
    for s in story.get("scenes") or []:
        e = ledger.get((s.get("media") or {}).get("asset"))
        if not e or e["id"] in out:
            continue
        src = local_file(e)
        dest = pathlib.Path(public) / "media" / f"{e['id']}{src.suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
        draw = {"kind": "video" if e["kind"] == "video" else "image", "what": e["kind"], "src": f"media/{dest.name}",
                "label": b["strings"]["illustrative"] if e["kind"] in ILLUSTRATIVE else None, "credit": credit(e, b)}
        if e["kind"] == "video" and e.get("duration"):
            draw["frames"] = max(1, int(round(float(e["duration"]) * fps)))
        out[e["id"]] = draw
    return out
