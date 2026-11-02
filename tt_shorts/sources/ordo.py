"""Georgian law as a source, through Ordo (github.com/sitechfromgeorgia/ordo-mcp, MIT), SiTech's legal research server.

Ordo's matsne_api.py reads matsne.gov.ge (the official Legislative Herald): an act by name or id, one article by its
number, the version in force. Veasy loads that one file from Ordo's folder (ORDO_DIR), as kaeasy.py loads kaeasy, so
a fix in Ordo reaches the videos with no copy here. Only the article's text goes to the writer: the official words.

    ref = <law>:<article>[:<part>]
      constitution:17          the Constitution of Georgia, article 17 (Ordo's CORE_LAWS: constitution, civil code,
                               criminal code, labour code, tax code, the procedure codes; Georgian names work too)
      30346:17                 the same by matsne document id
      სამოქალაქო კოდექსი:361:2   part 2 of article 361 of the Civil Code
      1507^1 / 1507¹           an article with a superscript number

The cluster carries the act's title, the article, the version (publication and its date) and the URL of the article
on matsne.gov.ge (the law program's end card links there). The header's date is when the text was read.
"""
import importlib.util
import os
import pathlib
import re
import sys

from tt_shorts.sources import SourceError, web

DEFAULT_DIR = "/root/.hermes/shared-plugins/ordo-mcp"
SITE = "matsne.gov.ge"
_mod = {}


def directory():
    return pathlib.Path(os.environ.get("ORDO_DIR", DEFAULT_DIR))


def module():
    """Ordo's matsne_api module, or None when Ordo isn't installed. Cached per folder."""
    path = directory() / "matsne_api.py"
    if str(path) in _mod:
        return _mod[str(path)]
    mod = None
    try:
        present = path.is_file()
    except OSError:
        present = False
    if present:
        try:
            spec = importlib.util.spec_from_file_location("ordo_matsne_api", path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["ordo_matsne_api"] = mod
            spec.loader.exec_module(mod)
        except Exception as e:  # noqa: BLE001 - a broken Ordo must not crash the engine
            print(f"ordo: {path} failed to load: {e}", file=sys.stderr)
            mod = None
    _mod[str(path)] = mod
    return mod


def reset():
    _mod.clear()


def available():
    return module() is not None


def version():
    """'0.1.0+1ab4463' (pyproject version + git commit), or None when Ordo is missing."""
    if not available():
        return None
    d, v = directory(), "unknown"
    try:
        m = re.search(r'^version\s*=\s*"([^"]+)"', (d / "pyproject.toml").read_text(encoding="utf-8"), re.M)
        v = m.group(1) if m else v
    except OSError:
        pass
    try:
        head = (d / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        sha = (d / ".git" / head[5:]).read_text(encoding="utf-8").strip() if head.startswith("ref: ") else head
        v += f"+{sha[:7]}"
    except OSError:
        pass
    return v


def parse_ref(ref):
    """'constitution:17' -> ('constitution', '17', None); 'civil code:361:2' -> ('civil code', '361', 2)."""
    parts = [p.strip() for p in str(ref).split(":")]
    if len(parts) < 2 or not all(parts):
        raise SourceError(f"ordo: ref {ref!r} must be <law>:<article>[:<part>], e.g. constitution:17")
    part = None
    if len(parts) >= 3 and parts[-1].isdigit() and re.match(r"\d", parts[-2]):
        part = int(parts.pop())
    law, article = ":".join(parts[:-1]), parts[-1]
    if not re.match(r"\d+(?:\s*(?:\^\s*\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹]+))?$", article):
        raise SourceError(f"ordo: {article!r} is not an article number (17, 1507^1)")
    return law, article, part


def clean(text):
    """The article's text without matsne's page furniture: the '# # #' markers and the amending acts' lines
    (returned separately). The heading 'მუხლი 17. ...' stays: it is how the viewer cites the article."""
    body, amended = [], []
    for line in text.split("\n"):
        line = re.sub(r"(?:\s*#)+\s*$", "", line).strip()
        if not line:
            continue
        if re.search(r"№\s*\d", line) and re.search(r"\d{2}\.\d{2}\.\d{4}", line) and \
                re.search(r"კანონი|დადგენილება|ბრძანება|law", line, re.I):
            amended.append(line)
        else:
            body.append(line)
    return "\n".join(body), amended


def payload(r, ref, law, part=None):
    """Ordo's get_article() result -> the source payload."""
    from tt_shorts import store
    text, amended = clean(r.get("text") or "")
    heading = (r.get("heading") or text.split("\n", 1)[0]).strip()
    if part is not None:
        if not r.get("part_text"):
            raise SourceError(f"ordo {ref}: {r.get('part_error') or f'no part {part}'}")
        text = f"{heading}\n{clean(r['part_text'])[0]}"
    title = (r.get("title") or "").strip()
    key = str(r.get("article") or "")
    name = store.safe(law) if store.safe(law) != "x" and not law.isdigit() else str(r.get("doc_id") or law)
    cluster = {"id": store.safe(f"{name}-{key}" + (f"-{part}" if part is not None else "")),
               "headline": f"{title}, {heading}" if title else heading, "category": "law",
               "created_at": web.now_iso(), "source_count": 1, "sources": [SITE],
               "url": r.get("url") or "", "title": title, "article": key, "heading": heading,
               "doc_id": r.get("doc_id"), "publication": r.get("publication"),
               "version_date": r.get("version_date") or "", "status": r.get("status") or "",
               "amended_by": amended, **({"part": part} if part is not None else {})}
    return {"cluster": cluster, "articles": [f"{title}\n{text}" if title else text]}


def fetch(ref):
    law, article, part = parse_ref(ref)
    mod = module()
    if mod is None:
        raise RuntimeError(f"the ordo source requires Ordo's matsne_api.py in {directory()} (set ORDO_DIR; "
                           f"git clone https://github.com/sitechfromgeorgia/ordo-mcp)")
    api = mod.MatsneAPI()
    kw = {"doc_id": int(law)} if law.isdigit() else {"law": law}
    r = api.get_article(article, part=part, **kw)
    err = r.get("error") if isinstance(r, dict) else "no answer"
    if err:
        if re.search(r"fetch failed|blocked|ERROR:|timed out|Temporary failure", str(err)):
            raise ConnectionError(f"matsne.gov.ge: {err}")  # the queue retries it later
        raise SourceError(f"ordo {ref}: {err}")
    if r.get("status") and r["status"] != "active":
        raise SourceError(f"ordo {ref}: the act is not in force on matsne.gov.ge (status {r['status']})")
    return payload(r, ref, law, part)
