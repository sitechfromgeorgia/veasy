"""The media layer's providers: one module per place a picture can come from (tt_shorts/assets.py drives them).

Every provider module has the same two functions and three names:

    NAME                      its key in assets.PROVIDERS and in a pack's media.providers
    KINDS                     what it can find: ("photo",), ("photo", "video"), ("screenshot",) ...
    available() -> str|None   None when it can be used here; else why not (a missing API key: skipped, not an error)
    search(query, kind, n)    -> candidates, best first, every one with a licence assets.LICENCES allows
    fetch(candidate)          -> the local file (under store.media_dir), downloaded and made fit to draw

A candidate is a plain dict, the future ledger entry (assets.entry):
    {"provider", "kind", "id", "url" (the file fetched), "page" (where a person sees its licence), "licence"
     (cc0, pdm, by, by-sa, pexels, pixabay), "licence_version", "author", "title", "source" (Flickr, Wikimedia
     Commons...), "width", "height", "duration" (a clip's seconds)}

The engines (Remotion, HyperFrames) never see a provider or a URL: assets.py resolves everything into local files
and a ledger, and each engine only draws files. No provider may be called while a video renders.

What is not here on purpose: AI image or video generation. `ai.py` is the interface it will plug into, disabled
until the owner decides (docs/plan-v2.md § 8.3 and 8.4).
"""
import json
import pathlib
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# A descriptive agent, as Wikimedia's policy asks (who calls and how to reach them); the other APIs log it too.
USER_AGENT = "Veasy/0.3 (brand-neutral video engine for agents; media layer; https://sitech.ge) python-urllib"
MAX_BYTES = 40 * 1024 * 1024  # a clip may be large; a photo is downscaled after the download
TIMEOUT = 40
GAP = 1.1  # seconds between two calls to one host: every provider's free tier asks for a polite rate

_last = {}
_lock = threading.Lock()


class MediaError(RuntimeError):
    """A provider failed for a passing reason (network, rate limit): the caller skips it or retries later."""


def _wait(host):
    with _lock:
        gap = GAP - (time.monotonic() - _last.get(host, 0.0))
        if gap > 0:
            time.sleep(gap)
        _last[host] = time.monotonic()


def request(url, headers=None, max_bytes=MAX_BYTES, tries=3):
    """GET -> (body bytes, content type). Throttled per host; a 429 or a 5xx is retried after a pause."""
    host = urllib.parse.urlsplit(url).netloc
    for i in range(tries):
        _wait(host)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise MediaError(f"{url}: larger than {max_bytes // 1024 // 1024} MB")
                return body, r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                time.sleep(4 * (i + 1))
                continue
            raise MediaError(f"{host}: HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if i < tries - 1:
                time.sleep(2 * (i + 1))
                continue
            raise MediaError(f"{host}: {e}") from e
    raise MediaError(f"{host}: no answer")


def get_json(url, headers=None):
    body, _ = request(url, headers, max_bytes=8 * 1024 * 1024)
    try:
        return json.loads(body.decode("utf-8"))
    except ValueError as e:
        raise MediaError(f"{url}: not JSON") from e


def download(url, dest, headers=None):
    """The file at url -> dest (written whole or not at all)."""
    dest = pathlib.Path(dest)
    body, ctype = request(url, headers)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(body)
    tmp.replace(dest)
    return dest, ctype
