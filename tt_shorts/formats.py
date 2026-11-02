"""Formats: a named set of choices for one kind of video (a "show"). The engine renders any story in any format;
which format a show uses is the agent's and the owner's decision, not code (owner, 2026-11-02: "build the engine
right; which version goes where we decide later with the agent").

A format chooses only among what the engine can do:
  look      auto | editorial | kinetic | cards      (auto: by the story's category, the pack's look_by_family)
  captions  page | roll                             (captions.py)
  voice     family | <a preset>                     (family: by category, the pack's voice_by_family; presets are
                                                     voices.PRESETS plus the packs' own, e.g. sitech)
  music     family | <a family in brand.FAMILIES> | off
  platform  the utm_source of the QR link           (shorts, youtube, instagram, tiktok, ...)
  min_seconds / max_seconds   the length window a render must land in

Built-in formats live here; more can be added without code as JSON files in formats/<name>.json with the same
keys (a file overrides a built-in of the same name). `python -m tt_shorts.engine options` lists them all.
"""
import json
import pathlib

from tt_shorts import meta, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "formats"
LOOKS = ("auto", "editorial", "kinetic", "cards")
CAPTIONS = ("page", "roll")
DEFAULTS = {"look": "auto", "captions": "page", "voice": "family", "music": "family", "platform": "shorts",
            "min_seconds": 18, "max_seconds": 45}
BUILTIN = {
    "news": {"label": "ამბავი: სტანდარტული", "about": "The default news Short: look and voice by category, "
             "two-line captions that never move."},
    "news-roll": {"label": "ამბავი: მოძრავი ტიტრები", "captions": "roll",
                  "about": "The same, with the three-line teleprompter captions."},
}


class FormatError(ValueError):
    pass


def validate(name, f):
    """Raise FormatError when a format names something the engine can't do."""
    def bad(key, value, allowed):
        raise FormatError(f"format {name!r}: {key}={value!r} is not one of {', '.join(map(str, allowed))}")
    if f["look"] not in LOOKS:
        bad("look", f["look"], LOOKS)
    if f["captions"] not in CAPTIONS:
        bad("captions", f["captions"], CAPTIONS)
    tones = ("family",) + tuple(sorted(voices.known()))
    if f["voice"] not in tones:
        bad("voice", f["voice"], tones)
    musics = ("family", "off") + tuple(meta.FAMILIES)
    if f["music"] not in musics:
        bad("music", f["music"], musics)
    if not (0 < f["min_seconds"] < f["max_seconds"] <= 90):
        raise FormatError(f"format {name!r}: need 0 < min_seconds < max_seconds <= 90")
    unknown = set(f) - set(DEFAULTS) - {"label", "about", "name"}
    if unknown:
        raise FormatError(f"format {name!r}: unknown keys {sorted(unknown)}")
    return f


def load_all():
    """Every format, built-in and from formats/*.json, resolved with the defaults and validated."""
    raw = {k: dict(v) for k, v in BUILTIN.items()}
    if DIR.is_dir():
        for path in sorted(DIR.glob("*.json")):
            raw[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return {name: validate(name, {**DEFAULTS, **spec, "name": name}) for name, spec in raw.items()}


def get(name="news", **overrides):
    """One format, with per-render overrides (None values are ignored)."""
    every = load_all()
    if name not in every:
        raise FormatError(f"unknown format {name!r}; known: {', '.join(every)}")
    f = {**every[name], **{k: v for k, v in overrides.items() if v is not None}}
    return validate(name, f)
