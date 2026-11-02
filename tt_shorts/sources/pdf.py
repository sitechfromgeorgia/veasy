"""A PDF as a source: its text, title and date.

    python -m tt_shorts.engine write --program explainer --source pdf --ref report.pdf
    python -m tt_shorts.engine write --program law --source pdf --ref https://example.ge/act.pdf

pypdf reads the text when it is installed, else poppler's `pdftotext`. The title and the date come from the PDF's
metadata (else the first line, and the time it was read). Known weak spot: old Georgian PDFs typeset in non-Unicode
fonts (AcadNusx and the like) come out as Latin letters; check `articles` before writing from one.
"""
import datetime as dt
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

from tt_shorts.sources import SourceError, web

MIN_TEXT = 200
MAX_PAGES = 60


def _pypdf(path):
    try:
        import pypdf
    except ImportError:
        return None
    reader = pypdf.PdfReader(str(path))
    pages = [(p.extract_text() or "") for p in reader.pages[:MAX_PAGES]]
    info = reader.metadata or {}
    meta = {k.lstrip("/").lower(): str(v) for k, v in dict(info).items() if v}
    return "\n\n".join(pages), meta


def _pdftotext(path):
    if not shutil.which("pdftotext"):
        return None
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-l", str(MAX_PAGES), str(path), "-"], capture_output=True,
                       text=True, timeout=120)
    if r.returncode != 0:
        raise SourceError(f"pdf {path}: pdftotext failed: {r.stderr.strip()[:200]}")
    meta = {}
    if shutil.which("pdfinfo"):
        # -rawdates: the PDF's own "D:20261030142000+04'00'" (pdf_date reads it exactly); the default
        # "Fri Oct 30 14:20:00 2026 +04" lost the zone's hours
        info = subprocess.run(["pdfinfo", "-rawdates", str(path)], capture_output=True, text=True, timeout=60).stdout
        for line in info.splitlines():
            k, _, v = line.partition(":")
            if v.strip():
                meta[k.strip().lower()] = v.strip()
    return r.stdout.replace("\f", "\n\n"), meta


def read(path):
    """-> (text, metadata) of a PDF file, by pypdf or pdftotext."""
    got = _pypdf(path) or _pdftotext(path)
    if got is None:
        raise RuntimeError("reading a PDF requires pypdf (pip install pypdf) or pdftotext (poppler-utils)")
    return got


def clean(raw):
    """Page text -> paragraphs: hyphenated line breaks joined, whitespace collapsed, empty lines dropped."""
    raw = raw.replace("\r", "")
    raw = re.sub(r"([A-Za-zა-ჰ])-\n([a-zა-ჰ])", r"\1\2", raw)
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", raw)]
    return "\n".join(p for p in paras if p)


def pdf_date(value):
    """PDF date 'D:20261102143000+04'00'' -> UTC ISO when it has a time, else None; Mon Nov 2 ... (pdfinfo) too."""
    m = re.match(r"D?:?(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})?(Z|[+-]\d{2}'?\d{2}'?)?", str(value or ""))
    if not m:
        return web.iso_utc(value)
    y, mo, d, h, mi, s, zone = m.groups()
    tz = dt.timezone.utc
    if zone and zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        digits = re.sub(r"\D", "", zone)
        tz = dt.timezone(sign * dt.timedelta(hours=int(digits[:2]), minutes=int(digits[2:4] or 0)))
    t = dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0), tzinfo=tz)
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def payload(text, meta, name, url=""):
    from tt_shorts import store
    text = clean(text)
    if len(text) < MIN_TEXT:
        raise SourceError(f"pdf {name}: no readable text ({len(text)} characters; a scan needs OCR first)")
    title = (meta.get("title") or "").strip()
    if not title or re.search(r"untitled|\.docx?$|^microsoft", title, re.I):
        title = text.split("\n", 1)[0][:140]
    site = web.host(url) if url.startswith("http") else (meta.get("author") or pathlib.Path(name).stem)
    stated = meta.get("creationdate") or meta.get("moddate") or ""
    cluster = {"id": store.safe(pathlib.Path(name).stem)[:60] or "document", "headline": title,
               "category": "general", "created_at": pdf_date(stated) or web.now_iso(),
               "source_count": 1, "sources": [site], "url": url if url.startswith("http") else "", "title": title}
    return {"cluster": cluster, "articles": [f"{title}\n{text}"]}


def from_bytes(body, url):
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / "document.pdf"
        path.write_bytes(body)
        text, meta = read(path)
    name = re.sub(r"[?#].*", "", url).rstrip("/").rsplit("/", 1)[-1] or "document.pdf"
    return payload(text, meta, name, url)


def fetch(ref):
    ref = str(ref)
    if os.path.isfile(ref):
        text, meta = read(ref)
        return payload(text, meta, ref)
    if not re.match(r"https?://", ref):
        raise SourceError(f"pdf: {ref!r} is neither a file nor a web address")
    body, _, final = web.get(ref)
    if body[:5] != b"%PDF-":
        raise SourceError(f"pdf: {ref} is not a PDF")
    return from_bytes(body, final)
