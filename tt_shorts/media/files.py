"""A candidate's file, fetched once into the media cache and made fit to draw (every provider's fetch() ends here).

    store.media_dir("<provider>:<id>")/image.jpg   a photo, upright (EXIF), RGB, at most LONG_SIDE px, JPEG
    store.media_dir("<provider>:<id>")/clip.mp4    a clip, as the provider serves it (muted when drawn)
    store.media_dir("<provider>:<id>")/shot.png    a screenshot (screenshot.py writes it there itself)

The same candidate is the same folder, so a second story that picks it costs no download. The file's sha256 goes
into the story's ledger (assets.entry); a file fetched again after `engine gc` is checked against it.
"""
import hashlib
import io
import os
import pathlib

from tt_shorts import store
from tt_shorts.media import MediaError, download, request

LONG_SIDE = 1920  # a 1080x1920 frame never needs more
NAMES = {"photo": "image.jpg", "illustration": "image.jpg", "video": "clip.mp4", "screenshot": "shot.png"}


def folder(candidate):
    return store.media_dir(f"{candidate['provider']}:{candidate['id']}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def normalize_photo(body, dest):
    """Bytes of any image Pillow reads -> an upright RGB JPEG of at most LONG_SIDE px (deterministic: the same bytes
    give the same file)."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(body))
        im = ImageOps.exif_transpose(im)
    except (OSError, ValueError) as e:
        raise MediaError(f"not an image Pillow can read ({e})") from e
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (0, 0, 0))
        flat.paste(im, mask=im.split()[-1])
        im = flat
    im = im.convert("RGB")
    im.thumbnail((LONG_SIDE, LONG_SIDE), Image.Resampling.LANCZOS)
    tmp = pathlib.Path(dest).with_suffix(".part")
    im.save(tmp, "JPEG", quality=88, optimize=False, progressive=False)
    tmp.replace(dest)
    return dest


def fetch_file(candidate, headers=None):
    """Download a candidate's file (once) -> its local path. Photos are normalized; clips are kept as served."""
    kind = candidate["kind"]
    if kind not in NAMES or kind == "screenshot":
        raise MediaError(f"{candidate['provider']}: can't fetch a {kind} here")
    d = folder(candidate)
    dest = d / NAMES[kind]
    if dest.is_file() and dest.stat().st_size:
        os.utime(d)  # in use: gc keeps it another 90 days
        return dest
    if kind == "video":
        download(candidate["url"], dest, headers)
        return dest
    body, _ = request(candidate["url"], headers)
    return normalize_photo(body, dest)
