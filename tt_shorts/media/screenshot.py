"""Screenshots as proof shots: one official or own page, at the frame's size, with a box around a given phrase.

How: the chrome-headless-shell Remotion already installs (remotion/node_modules/.remotion/...), driven by a tiny
Node script over the DevTools protocol (shot.mjs, Node's own WebSocket). Playwright would be a second browser and
a heavy Python dependency for one page load; puppeteer would be a new npm package. This reuses what every Veasy
machine has for rendering anyway. SHORTS_CHROMIUM (props.chrome) wins when it is set.

What may be shot (news rule N13, `news_check.imagery`): only a page on the allow-list, never a publisher's article
page. The list is data: the pack's `media.official` (a Georgian pack: matsne.gov.ge, gov.ge and its subdomains) and
`media.own` (the pack's own site), plus a program's `screenshots`. The URL is checked before the page is opened and
again where it ended up after redirects; a page that leaves the list is refused, its file deleted.

    capture(url, allow, find=None, color="#EF4444") -> a ledger candidate with its file (kind "screenshot",
                                                       licence "screenshot", author/source: the page's host)
"""
import glob
import json
import os
import pathlib
import shutil
import subprocess
import urllib.parse

from tt_shorts import store
from tt_shorts.media import MediaError, files

NAME = "screenshot"
KINDS = ("screenshot",)
ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = pathlib.Path(__file__).with_name("shot.mjs")
WIDTH, HEIGHT = 1080, 1920


def host(url):
    return (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")


def allowed(url, allow):
    """True when url is https/http on a domain of the allow-list (the domain itself or one of its subdomains)."""
    parts = urllib.parse.urlsplit(url or "")
    h = host(url)
    if parts.scheme not in ("https", "http") or not h:
        return False
    return any(h == d or h.endswith("." + d) for d in (str(x).lower().strip(".") for x in allow or []) if d)


def chrome():
    """The browser to drive: SHORTS_CHROMIUM / Playwright's (props.chrome), else the one Remotion installed."""
    from tt_shorts import props
    found = props.chrome()
    if found:
        return found
    base = ROOT / "remotion" / "node_modules" / ".remotion" / "chrome-headless-shell"
    hits = sorted(glob.glob(str(base / "*" / "*" / "chrome-headless-shell.exe")) +
                  glob.glob(str(base / "*" / "*" / "chrome-headless-shell")))
    return hits[-1] if hits else None


def available():
    if not shutil.which("node"):
        return "node is not installed"
    if not chrome():
        return "no chrome-headless-shell (render once with Remotion, or set SHORTS_CHROMIUM)"
    return None


def search(query, kind="screenshot", n=1):
    """Screenshots aren't searched: assets.py calls capture() with the story's own link or an allow-listed URL."""
    return []


def capture(url, allow, find=None, color="#EF4444", run=subprocess.run):
    """Shoot url (on the allow-list) -> a candidate with "file". run: subprocess.run (tests pass a fake)."""
    if not allowed(url, allow):
        listed = ", ".join(allow or []) or "empty"
        raise MediaError(f"N13: {host(url) or url} is not on the screenshot allow-list ({listed})")
    why = available()
    if why:
        raise MediaError(f"screenshot: {why}")
    c = {"provider": NAME, "kind": "screenshot", "id": f"{url}|{find or ''}", "url": url, "page": url,
         "licence": "screenshot", "licence_version": "", "author": host(url), "title": "", "source": host(url),
         "width": WIDTH, "height": HEIGHT, **({"find": find} if find else {})}
    d = files.folder(c)
    out = d / files.NAMES["screenshot"]
    meta = d / "shot.json"
    if out.is_file() and meta.is_file():
        os.utime(d)
        return {**c, **json.loads(meta.read_text(encoding="utf-8")), "file": str(out)}
    cmd = ["node", str(SCRIPT), "--chrome", chrome(), "--url", url, "--out", str(out), "--width", str(WIDTH),
           "--height", str(HEIGHT), "--color", color]
    if find:
        cmd += ["--find", find]
    r = run(cmd, capture_output=True, text=True, timeout=120)
    lines = [x for x in (r.stdout or "").splitlines() if x.startswith("{")]
    res = json.loads(lines[-1]) if lines else {"ok": False, "error": (r.stderr or "")[-300:]}
    if not res.get("ok"):
        out.unlink(missing_ok=True)
        raise MediaError(f"screenshot of {url}: {res.get('error')}")
    if not allowed(res.get("url") or url, allow):  # a redirect off the list: refused, not kept
        out.unlink(missing_ok=True)
        raise MediaError(f"N13: {url} redirected to {host(res.get('url'))}, which is not on the allow-list")
    extra = {"title": (res.get("title") or "")[:160], "found": bool(res.get("found")), "box": res.get("box"),
             "landed": res.get("url") or url}
    if find and not extra["found"]:
        extra["note"] = "the phrase was not found on the page: no box drawn"
    meta.write_text(json.dumps(extra, ensure_ascii=False), encoding="utf-8")
    return {**c, **extra, "file": str(out)}


def fetch(c):
    """A ledger's screenshot whose file was collected: shoot it again (the page may have changed: assets.py
    compares the sha and says so)."""
    return pathlib.Path(capture(c["url"], [host(c["url"])], c.get("find"))["file"])
