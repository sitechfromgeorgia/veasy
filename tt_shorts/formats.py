"""Formats: a named set of choices for one kind of video (a "show"). The engine renders any story in any format;
which format a show uses is the agent's and the owner's decision, not code (owner, 2026-11-02: "build the engine
right; which version goes where we decide later with the agent").

A format chooses only among what the engine can do:
  look      auto | editorial | kinetic | cards      (auto: by the story's category, the pack's look_by_family)
  captions  page | roll | keyword                   (captions.py; keyword: a dark box, the spoken word lit, one
                                                     keyword a page in the pack's design.keyword style)
  transition auto | cut | line | panel | wipe | slide | push | dot | meter   (auto: the look's own;
                                                     props.TRANSITIONS; meter: equaliser bars rise and fall)
  beats     on | off                                (beats.py: a change inside every scene each 1.5-3 s, on the
                                                     words; off: each scene's own stagger, as before)
  chapters  auto | on | off                         (chapters.py: "01 / 03" and a segmented bar in the header;
                                                     auto: for a video of chapters.AUTO_SECONDS or more)
  outro     card | overlay | loop                   (swipe.py: the end card, a QR/link/CTA chip over the last
                                                     scene, or a seamless loop back into the hook)
  voice     family | <a preset>                     (family: by category, the pack's voice_by_family; presets are
                                                     voices.PRESETS plus the packs' own, e.g. sitech)
  music     family | <a family in brand.FAMILIES> | off
  sfx       off | on                                (sfx.py: short sound effects on the timeline's events, a
                                                     whoosh on a cut, a pop when a mark lands, ticks while a number
                                                     counts; one constant level under the voice, no ducking)
  platform  the utm_source of the QR link           (shorts, youtube, instagram, tiktok, ...)
  min_seconds / max_seconds   the length window a render must land in

Built-in formats live here; more can be added without code as JSON files in formats/<name>.json with the same
keys (a file overrides a built-in of the same name). `python -m tt_shorts.engine options` lists them all.
"""
import json
import pathlib

from tt_shorts import meta, swipe, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "formats"
LOOKS = ("auto", "editorial", "kinetic", "cards")
CAPTIONS = ("page", "roll", "keyword")
TRANSITIONS = ("auto", "cut", "line", "panel", "wipe", "slide", "push", "dot", "meter")  # props.TRANSITIONS + auto
BEATS = ("on", "off")
CHAPTERS = ("auto", "on", "off")
OUTROS = swipe.OUTROS
SFX = ("off", "on")
DEFAULTS = {"look": "auto", "captions": "page", "transition": "auto", "outro": swipe.DEFAULT_OUTRO, "voice": "family",
            "music": "family", "sfx": "off", "platform": "shorts", "min_seconds": 18, "max_seconds": 45,
            "beats": "on", "chapters": "off"}
RENDER_KEYS = ("sfx", "beats", "chapters")  # passed to props.build as they are (render_keys)
BUILTIN = {
    "news": {"label": "ამბავი: სტანდარტული", "about": "The default news Short: look and voice by category, "
             "two-line captions that never move."},
    "news-roll": {"label": "ამბავი: მოძრავი ტიტრები", "captions": "roll",
                  "about": "The same, with the three-line teleprompter captions."},
    "showcase": {"label": "შოუქეისი: გრძელი რგოლი", "captions": "roll", "look": "editorial",
                 "voice": "anchor", "music": "tech", "platform": "youtube",
                 "min_seconds": 120, "max_seconds": 360,
                 "about": "A long-form piece, up to six minutes, for YouTube and the site."},
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
    if f["transition"] not in TRANSITIONS:
        bad("transition", f["transition"], TRANSITIONS)
    if f["outro"] not in OUTROS:
        bad("outro", f["outro"], OUTROS)
    if f["beats"] not in BEATS:
        bad("beats", f["beats"], BEATS)
    if f["chapters"] not in CHAPTERS:
        bad("chapters", f["chapters"], CHAPTERS)
    tones = ("family",) + tuple(sorted(voices.known()))
    if f["voice"] not in tones:
        bad("voice", f["voice"], tones)
    musics = ("family", "off") + tuple(meta.FAMILIES)
    if f["music"] not in musics:
        bad("music", f["music"], musics)
    if f["sfx"] not in SFX:
        bad("sfx", f["sfx"], SFX)
    if not (0 < f["min_seconds"] < f["max_seconds"] <= 360):
        raise FormatError(f"format {name!r}: need 0 < min_seconds < max_seconds <= 360")
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


def render_keys(fmt):
    """The format keys props.build takes as they are: {beats, chapters}."""
    return {k: fmt.get(k, DEFAULTS[k]) for k in RENDER_KEYS}
