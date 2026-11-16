"""Post to a brand's Facebook Page: photos, text and Reels.

Transport only. This module owns the Graph calls, the pack-configured credential paths and the
error shape; selection rules, caps and ledgers stay with the callers.

Each brand pack provides its credential paths and daily target under brand.json `social.facebook`:
    {"page_id_file": ..., "token_file": ..., "user_token_file": ..., "reels_per_day": 3}

Every function returns a receipt dict:
    {"ok": True, "platform": "facebook", "kind": "photo"|"video"|"text"|"comment", ...ids}
    {"ok": False, "platform": "facebook", "error": {...code, message, http, fbtrace}}

A failed call never raises for an expected Graph rejection; it returns ok=False so the caller can
write an honest receipt and leave the ledger untouched. Programming and pack config errors still raise.

CLI:
    python -m tt_shorts.facebook --brand <name> verify
    python -m tt_shorts.facebook --brand <name> photo  <url-or-path> --caption "..." [--live]
    python -m tt_shorts.facebook --brand <name> video  <file.mp4>    --caption "..." [--live]
    python -m tt_shorts.facebook --brand <name> text   "..."        [--live]
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import pathlib
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from tt_shorts import brand as packs

API = "https://graph.facebook.com"
RUPLOAD = "https://rupload.facebook.com"
VERSION = "v23.0"

PLATFORM = "facebook"
# Fingerprints (not values) of tokens known to have leaked in chat/logs so every path refuses them.
LEAKED_FINGERPRINTS: set[str] = {"58228850"}
# Reels limits from the Reels Publishing API: 3..90 s, 9x16, 540x960 minimum.
REEL_MIN_SECONDS = 3.0
REEL_MAX_SECONDS = 90.0
# Reels API allows 30 API-published posts in a rolling 24 h.
REELS_DAILY_CAP = 30

# Graph codes worth another attempt: rate limits and transient platform trouble.
RETRY_CODES = {1, 2, 4, 17, 32, 341, 613}
MAX_ATTEMPTS = 3


class MissingCredentials(RuntimeError):
    """The token or page id file is absent, empty or known-compromised."""


class GraphError(RuntimeError):
    """A Graph call returned an error object."""

    def __init__(self, message: str, *, code=None, subcode=None, http=None, fbtrace=None,
                 transient: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.subcode = subcode
        self.http = http
        self.fbtrace = fbtrace
        self.transient = transient

    def as_receipt(self) -> dict:
        return {"ok": False, "platform": PLATFORM, "error": {
            "code": self.code, "subcode": self.subcode, "http": self.http,
            "message": self.message, "fbtrace": self.fbtrace}}


def _cfg(brand=None) -> tuple[dict, pathlib.Path, pathlib.Path, pathlib.Path, int]:
    pack, fb = packs.require_social(brand, "facebook")
    tok = pathlib.Path(fb["token_file"])
    pid = pathlib.Path(fb["page_id_file"])
    utok = pathlib.Path(fb.get("user_token_file") or f"{tok}.user")
    target = min(REELS_DAILY_CAP, int(fb.get("reels_per_day", 3)))
    return pack, tok, pid, utok, target


def daily_target(brand=None) -> int:
    """Daily Reel target configured on the pack, capped by the Reels API daily limit."""
    return _cfg(brand)[4]


def _read(path: pathlib.Path) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise MissingCredentials(f"{path} is missing ({e.__class__.__name__})") from e
    if not value:
        raise MissingCredentials(f"{path} is empty")
    return value


def page_token(brand=None) -> str:
    _, tok_file, _, _, _ = _cfg(brand)
    value = _read(tok_file)
    fp = token_fingerprint(value, brand=brand)
    if fp in LEAKED_FINGERPRINTS:
        raise MissingCredentials(
            f"the stored token ({fp}) was posted in chat and is compromised; "
            f"rotate it in Business Manager and save the new token to {tok_file}")
    return value


def armed(brand=None) -> bool:
    """True only when a configured brand pack has a usable, non-leaked token and page id."""
    try:
        page_token(brand=brand)
        page_id(brand=brand)
    except (MissingCredentials, packs.BrandError):
        return False
    return True


def ensure_page_token(*, brand=None, dry: bool = False) -> dict:
    """Exchange a System User or user token for the Page's own token, once."""
    _, tok_file, _, user_file, _ = _cfg(brand)
    current = _read(tok_file)
    if token_fingerprint(current, brand=brand) in LEAKED_FINGERPRINTS:
        raise MissingCredentials("stored token is known-compromised; rotate it first")
    body = _graph("GET", page_id(brand=brand), {"fields": "id,name,access_token"}, token=current,
                  idempotent=True, brand=brand)
    page_token_value = body.get("access_token")
    if not page_token_value:
        return {"ok": False, "platform": PLATFORM, "kind": "exchange",
                "error": {"message": "the token returned no Page access_token; it may not hold "
                                     "CREATE_CONTENT on this page"}}
    if dry:
        return {"ok": True, "platform": PLATFORM, "kind": "exchange", "dry": True,
                "page": body.get("name"),
                "would_write": str(tok_file),
                "fingerprint": token_fingerprint(page_token_value, brand=brand)}
    if not user_file.exists():
        user_file.write_text(current, encoding="utf-8")
        user_file.chmod(0o600)
    tok_file.write_text(page_token_value, encoding="utf-8")
    tok_file.chmod(0o600)
    return {"ok": True, "platform": PLATFORM, "kind": "exchange", "page": body.get("name"),
            "fingerprint": token_fingerprint(page_token_value, brand=brand),
            "kept_user_token_at": str(user_file)}


def page_id(brand=None) -> str:
    _, _, pid_file, _, _ = _cfg(brand)
    return _read(pid_file)


def token_fingerprint(value: str | None = None, *, brand=None) -> str:
    """A short, non-reversible handle for logs: proves which token ran without printing it."""
    value = value or page_token(brand=brand)
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def _url(path: str, params: dict | None = None) -> str:
    base = path if path.startswith("http") else f"{API}/{VERSION}/{path.lstrip('/')}"
    if params:
        base = base + ("&" if "?" in base else "?") + urllib.parse.urlencode(params)
    return base


def _decode(resp) -> dict:
    raw = resp.read()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw[:400].decode("utf-8", "replace")}


def _error_from(body: dict, http_status: int) -> GraphError | None:
    err = (body or {}).get("error")
    if not isinstance(err, dict):
        return None
    code = err.get("code")
    return GraphError(
        message=str(err.get("message") or "graph error")[:400],
        code=code,
        subcode=err.get("error_subcode"),
        http=http_status,
        fbtrace=err.get("fbtrace_id"),
        transient=(code in RETRY_CODES) or http_status == 429 or http_status >= 500,
    )


def _multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    """files: {name: (filename, bytes, content_type)}. Text fields first, file last."""
    boundary = "----veasyfb" + str(int(time.time() * 1000))
    out: list[bytes] = []
    for name, value in fields.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                   f'{value}\r\n'.encode())
    for name, (filename, payload, ctype) in files.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                   f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'.encode())
        out.append(payload)
        out.append(b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def _call(method: str, url: str, *, data: bytes | None = None, headers: dict | None = None,
          timeout: int = 120, idempotent: bool = False) -> tuple[int, dict, dict]:
    """One HTTP attempt. Retries only what cannot create a duplicate: reads, 429, 5xx on reads."""
    last: GraphError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, data=data, method=method)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, dict(resp.headers), _decode(resp)
        except urllib.error.HTTPError as e:
            body = _decode(e) if hasattr(e, "read") else {}
            err = _error_from(body, e.code) or GraphError(
                f"HTTP {e.code}", http=e.code, transient=e.code == 429 or e.code >= 500)
            retryable = err.transient and (idempotent or e.code == 429)
            if not retryable or attempt == MAX_ATTEMPTS:
                raise err
            last = err
        except urllib.error.URLError as e:
            if not idempotent or attempt == MAX_ATTEMPTS:
                raise GraphError(f"network: {str(e.reason)[:160]}", transient=True) from e
            last = GraphError(f"network: {str(e.reason)[:160]}", transient=True)
        time.sleep(2 * attempt)
    raise last or GraphError("gave up")


def _graph(method: str, path: str, fields: dict | None = None, *, token: str | None = None,
           timeout: int = 120, idempotent: bool = False, brand=None) -> dict:
    """Graph call with the brand's Page token."""
    token = token or page_token(brand=brand)
    params = dict(fields or {})
    params["access_token"] = token
    if method.upper() == "GET":
        status, _headers, body = _call("GET", _url(path, params), timeout=timeout,
                                       idempotent=True)
    else:
        body_bytes = urllib.parse.urlencode(params).encode()
        status, _headers, body = _call(
            "POST", _url(path), data=body_bytes,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout, idempotent=idempotent)
    err = _error_from(body, status)
    if err:
        raise err
    return body


# ------------------------------------------------------------------ reads
def pages(token: str | None = None, *, brand=None) -> dict:
    """Every Page the token can act for, with the tasks it holds."""
    _cfg(brand)
    try:
        body = _graph("GET", "me/accounts",
                      {"fields": "id,name,username,tasks,link", "limit": "100"}, token=token,
                      idempotent=True, brand=brand)
    except GraphError as e:
        if e.code not in (100, 200, 190):
            raise
        one = _graph("GET", page_id(brand=brand), {"fields": "id,name,username,link"},
                     token=token, idempotent=True, brand=brand)
        return {"ok": True, "platform": PLATFORM, "kind": "pages", "count": 1,
                "note": "page token: cannot enumerate pages, answers with its own",
                "pages": [{"id": one.get("id"), "name": one.get("name"),
                           "username": one.get("username"),
                           "tasks": [], "can_post": True}]}
    rows = body.get("data") or []
    return {"ok": True, "platform": PLATFORM, "kind": "pages",
            "count": len(rows),
            "pages": [{"id": r.get("id"), "name": r.get("name"),
                       "username": r.get("username"), "tasks": r.get("tasks") or [],
                       "can_post": "CREATE_CONTENT" in (r.get("tasks") or [])}
                      for r in rows]}


def verify(*, brand=None) -> dict:
    """Prove which Page the token acts as, and whether it is a Page token at all."""
    body = _graph("GET", page_id(brand=brand), {"fields": "id,name,username,link"}, idempotent=True, brand=brand)
    me = _graph("GET", "me", {"fields": "id,name"}, idempotent=True, brand=brand)
    return {"ok": True, "platform": PLATFORM, "kind": "verify",
            "id": body.get("id"), "name": body.get("name"),
            "username": body.get("username"), "link": body.get("link"),
            "as": me.get("id"), "as_name": me.get("name"),
            "token_kind": "page" if str(me.get("id")) == str(body.get("id")) else "user",
            "token": token_fingerprint(brand=brand)}


def video_status(video_id: str, *, brand=None) -> dict:
    return _graph("GET", video_id, {"fields": "status,description,permalink_url,post_id"},
                  idempotent=True, brand=brand)


def post_object_id(video_id: str, *, brand=None) -> dict:
    """The object a comment must hang from, for a published Reel."""
    pid_val = page_id(brand=brand)
    try:
        body = _graph("GET", video_id, {"fields": "post_id"}, idempotent=True, brand=brand)
    except GraphError as e:
        return {"ok": False, "error": e.as_receipt()}
    pid = body.get("post_id")
    if not pid:
        return {"ok": False, "error": {"message": "video has no post_id yet"}}
    return {"ok": True, "post_id": pid, "object_id": f"{pid_val}_{pid}"}


# ------------------------------------------------------------------ writes
def send_text(message: str, *, dry: bool = False, token: str | None = None, brand=None) -> dict:
    _cfg(brand)
    if dry:
        return {"ok": True, "platform": PLATFORM, "kind": "text", "dry": True, "chars": len(message)}
    try:
        body = _graph("POST", f"{page_id(brand=brand)}/feed", {"message": message}, token=token, brand=brand)
    except GraphError as e:
        return e.as_receipt()
    return {"ok": True, "platform": PLATFORM, "kind": "text", "id": body.get("id")}


def send_photo(image: str, caption: str, *, dry: bool = False, published: bool = True,
               token: str | None = None, brand=None) -> dict:
    """Publish a photo post. `image` is a public https URL or a local file path."""
    _cfg(brand)
    if dry:
        return {"ok": True, "platform": PLATFORM, "kind": "photo", "dry": True,
                "image": image, "chars": len(caption)}
    pid = page_id(brand=brand)
    try:
        if re.match(r"^https?://", image):
            body = _graph("POST", f"{pid}/photos",
                          {"url": image, "caption": caption,
                           "published": "true" if published else "false"}, token=token, timeout=180, brand=brand)
        else:
            path = pathlib.Path(image)
            payload = path.read_bytes()
            ctype = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            data, ct = _multipart(
                {"caption": caption, "published": "true" if published else "false",
                 "access_token": token or page_token(brand=brand)},
                {"source": (path.name, payload, ctype)})
            status, _h, resp = _call("POST", _url(f"{pid}/photos"), data=data,
                                     headers={"Content-Type": ct}, timeout=300)
            err = _error_from(resp, status)
            if err:
                raise err
            body = resp
    except GraphError as e:
        return e.as_receipt()
    return {"ok": True, "platform": PLATFORM, "kind": "photo",
            "id": body.get("id"), "post_id": body.get("post_id")}


def send_video(path: str, caption: str, *, title: str | None = None, dry: bool = False,
               publish_state: str = "PUBLISHED", token: str | None = None,
               poll_seconds: int = 90, brand=None) -> dict:
    """Publish a Reel: start an upload session, push the bytes, finish, then watch the status."""
    _cfg(brand)
    src = pathlib.Path(path)
    if not src.exists():
        return {"ok": False, "platform": PLATFORM, "kind": "video",
                "error": {"message": f"no such file: {src}"}}
    size = src.stat().st_size
    seconds = probe_seconds(src)
    if dry:
        return {"ok": True, "platform": PLATFORM, "kind": "video", "dry": True,
                "file": str(src), "bytes": size, "seconds": seconds, "chars": len(caption)}
    if seconds is not None and not (REEL_MIN_SECONDS <= seconds <= REEL_MAX_SECONDS):
        return {"ok": False, "platform": PLATFORM, "kind": "video", "file": str(src),
                "error": {"message": f"duration {seconds}s outside the Reels window "
                                     f"{REEL_MIN_SECONDS}-{REEL_MAX_SECONDS}s"}}
    pid = page_id(brand=brand)
    tok = token or page_token(brand=brand)
    try:
        start = _graph("POST", f"{pid}/video_reels", {"upload_phase": "start"}, token=tok, brand=brand)
        video_id = start.get("video_id")
        if not video_id:
            return {"ok": False, "platform": PLATFORM, "kind": "video",
                    "error": {"message": f"start returned no video_id: {json.dumps(start)[:200]}"}}
        upload_url = start.get("upload_url") or f"{RUPLOAD}/video-upload/{VERSION}/{video_id}"
        upload = _upload_bytes(upload_url, video_id, src, size, tok)
        if not upload.get("ok"):
            return {"ok": False, "platform": PLATFORM, "kind": "video", "video_id": video_id,
                    "stage": "upload", "error": upload.get("error")}
        fields = {"upload_phase": "finish", "video_id": video_id, "video_state": publish_state,
                  "description": caption}
        if title:
            fields["title"] = title
        finish = _graph("POST", f"{pid}/video_reels", fields, token=tok, timeout=180,
                        idempotent=True, brand=brand)
        receipt = {"ok": bool(finish.get("success", True)), "platform": PLATFORM,
                   "kind": "video", "video_id": video_id, "seconds": seconds, "bytes": size,
                   "post_id": finish.get("post_id") or finish.get("id"),
                   "publish_state": publish_state}
        if poll_seconds:
            receipt["status"] = _wait_ready(video_id, tok, poll_seconds, brand=brand)
        try:
            meta = video_status(video_id, brand=brand)
            raw_post = meta.get("post_id")
            if raw_post:
                receipt["post_id"] = (raw_post if "_" in str(raw_post)
                                      else f"{pid}_{raw_post}")
            if not receipt.get("permalink_url"):
                receipt["permalink_url"] = meta.get("permalink_url")
        except GraphError:
            pass
        return receipt
    except GraphError as e:
        return e.as_receipt()


def _upload_bytes(upload_url: str, video_id: str, path: pathlib.Path, size: int, token: str) -> dict:
    payload = path.read_bytes()
    headers = {"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size),
               "Content-Type": "application/octet-stream"}
    try:
        status, _h, body = _call("POST", upload_url, data=payload, headers=headers,
                                 timeout=900, idempotent=True)
    except GraphError as e:
        return {"ok": False, "error": e.as_receipt()["error"]}
    err = _error_from(body, status)
    if err:
        return {"ok": False, "error": err.as_receipt()["error"]}
    return {"ok": bool(body.get("success", True)), "body": body}


def _wait_ready(video_id: str, token: str, seconds: int, *, brand=None) -> dict:
    """Poll until the reel is published, or the budget runs out. Never raises."""
    deadline = time.time() + seconds
    last = {}
    last_error = None
    while time.time() < deadline:
        try:
            last = _graph("GET", video_id, {"fields": "status,description,permalink_url,post_id"},
                          token=token, idempotent=True, brand=brand)
            last_error = None
        except GraphError as e:
            if e.code in (190, 200, 10):
                return {"error": e.as_receipt()["error"]}
            last_error = e.as_receipt()["error"]
            time.sleep(5)
            continue
        st = (last.get("status") or {})
        video_state = st.get("video_status")
        publish = (st.get("publishing_phase") or {}).get("publish_status")
        if video_state in ("ready", "published") and publish in ("published", "completed", None):
            return {"video_status": video_state, "publish_status": publish,
                    "permalink": last.get("permalink_url")}
        if video_state in ("error", "upload_failed", "expired"):
            return {"video_status": video_state,
                    "error": (st.get("processing_phase") or {}).get("error")
                    or (st.get("publishing_phase") or {}).get("error")}
        time.sleep(5)
    st = (last.get("status") or {})
    out = {"video_status": st.get("video_status"), "timed_out": True}
    if last_error and not st:
        out["error"] = last_error
    return out


def set_thumbnail(video_id: str, image_path: str, *, dry: bool = False,
                  token: str | None = None, brand=None) -> dict:
    """Make an image the reel's cover."""
    _cfg(brand)
    path = pathlib.Path(image_path)
    if not path.exists():
        return {"ok": False, "platform": PLATFORM, "kind": "thumbnail",
                "error": {"message": f"no such file: {path}"}}
    if dry:
        return {"ok": True, "platform": PLATFORM, "kind": "thumbnail", "dry": True,
                "video_id": video_id, "image": str(path)}
    payload = path.read_bytes()
    ctype = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data, ct = _multipart({"is_preferred": "true", "access_token": token or page_token(brand=brand)},
                          {"source": (path.name, payload, ctype)})
    try:
        status, _h, body = _call("POST", _url(f"{video_id}/thumbnails"), data=data,
                                 headers={"Content-Type": ct}, timeout=180)
    except GraphError as e:
        return e.as_receipt()
    err = _error_from(body, status)
    if err:
        return err.as_receipt()
    return {"ok": bool(body.get("success", True)), "platform": PLATFORM,
            "kind": "thumbnail", "video_id": video_id, "body": body}


def comment(object_id: str, message: str, *, dry: bool = False, token: str | None = None,
            brand=None) -> dict:
    """First comment on our own post."""
    _cfg(brand)
    if dry:
        return {"ok": True, "platform": PLATFORM, "kind": "comment", "dry": True,
                "chars": len(message)}
    try:
        body = _graph("POST", f"{object_id}/comments", {"message": message}, token=token, brand=brand)
    except GraphError as e:
        return e.as_receipt()
    return {"ok": True, "platform": PLATFORM, "kind": "comment", "id": body.get("id")}


def probe_seconds(path: pathlib.Path) -> float | None:
    """Duration in seconds, or None when ffprobe is unavailable."""
    ffprobe = shutil.which("ffprobe") or "/root/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffprobe"
    if not pathlib.Path(ffprobe).exists():
        return None
    try:
        p = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(path)],
                           capture_output=True, text=True, timeout=60)
        return round(float(p.stdout.strip()), 2)
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Brand-configured Facebook transport")
    ap.add_argument("command", choices=["verify", "pages", "exchange", "photo", "video", "text"])
    ap.add_argument("target", nargs="?", help="image url/path, video file, or the text itself")
    ap.add_argument("--brand", default=None, help="brand pack name (defaults to brand.DEFAULT)")
    ap.add_argument("--caption", default="")
    ap.add_argument("--live", action="store_true", help="actually publish (default: dry)")
    a = ap.parse_args(argv)

    try:
        if a.command == "verify":
            out = verify(brand=a.brand)
        elif a.command == "pages":
            out = pages(brand=a.brand)
        elif a.command == "exchange":
            out = ensure_page_token(brand=a.brand, dry=not a.live)
        elif a.command == "photo":
            out = send_photo(a.target, a.caption or a.target, dry=not a.live, brand=a.brand)
        elif a.command == "video":
            out = send_video(a.target, a.caption, dry=not a.live, brand=a.brand)
        else:
            out = send_text(a.target or a.caption, dry=not a.live, brand=a.brand)
    except (MissingCredentials, packs.BrandError) as e:
        out = {"ok": False, "platform": PLATFORM, "error": {"message": str(e)}}
        print(json.dumps(out, ensure_ascii=False))
        return 2
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
