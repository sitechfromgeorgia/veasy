"""What the document sources share: an HTTP GET with a size cap and retries, and dates as UTC ISO strings."""
import datetime as dt
import email.utils
import http.client
import re
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; Veasy/0.2; +https://github.com/sitechfromgeorgia/veasy)"
MAX_BYTES = 20 * 1024 * 1024


def get(url, timeout=30, tries=3, max_bytes=MAX_BYTES):
    """-> (body bytes, content type, final url). A cut-off transfer is retried; a network error is raised as is
    (the queue re-queues it as transient)."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ka,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ValueError(f"{url}: larger than {max_bytes // 1024 // 1024} MB")
                return body, r.headers.get("Content-Type", ""), r.geturl()
        except (http.client.IncompleteRead, ConnectionResetError):
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def decode(body, content_type=""):
    """Bytes of a page -> text, by the header's charset, else the page's <meta charset>, else UTF-8."""
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I) or \
        re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
    charset = m.group(1) if m else "utf-8"
    charset = charset.decode() if isinstance(charset, bytes) else charset
    try:
        return body.decode(charset, "replace")
    except LookupError:
        return body.decode("utf-8", "replace")


def host(url):
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_utc(value):
    """A date the document states -> 'YYYY-MM-DDTHH:MM:SSZ' when it has a time of day, else None. A bare date has
    no time to put in the header, so the caller uses the time the document was read."""
    if not value:
        return None
    value = str(value).strip()
    t = None
    try:
        t = email.utils.parsedate_to_datetime(value)  # RSS: "Mon, 02 Nov 2026 16:03:00 GMT"
    except (TypeError, ValueError, IndexError):
        pass
    if t is None:
        if not re.match(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", value):
            return None
        try:
            t = dt.datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T", 1))
        except ValueError:
            return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day(value):
    """'YYYY-MM-DD' of a stated date (with or without a time), else ''."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(value or "").strip())
    return m.group(1) if m else ""
