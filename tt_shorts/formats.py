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
  theme     default | auto | <a theme's name>       (default: the pack's default_theme, so nothing changes; auto:
                                                     variety picks among the pack's allowed themes, least used
                                                     lately; a name: that theme of the story's pack, e.g. light,
                                                     which every pack it is used with must have; brand.json themes)
  platform  the utm_source of the QR link           (shorts, youtube, instagram, tiktok, ...)
  min_seconds / max_seconds   the length window a render must land in
  engine    remotion | hyperframes                  (optional) the film engine: a director's, else the program's,
                                                     else the format's, else the pack's, else remotion (compose.py)
  review    always | until:<n>                      (optional) composed films only: held for a person's review
                                                     always, or until the brand has n approved in a row (queue.py)

Built-in formats live here; more can be added without code as JSON files in formats/<name>.json with the same
keys (a file overrides a built-in of the same name). `python -m tt_shorts.engine options` lists them all.
"""
import json
import pathlib
import re

from tt_shorts import meta, swipe, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "formats"
LOOKS = ("auto", "editorial", "kinetic", "cards")
CAPTIONS = ("page", "roll", "keyword")
TRANSITIONS = ("auto", "cut", "line", "panel", "wipe", "slide", "push", "dot", "meter", "fade", "shutter", "split", "corner", "iris", "blind")  # props.TRANSITIONS + auto
BEATS = ("on", "off")
CHAPTERS = ("auto", "on", "off")
OUTROS = swipe.OUTROS
SFX = ("off", "on")
THEME_MODES = ("default", "auto")  # or a theme's name (brand.json themes)
ENGINES = ("remotion", "hyperframes")  # the two film engines (compose.py); remotion is the default
DEFAULT_ENGINE = "remotion"
OPTIONAL = ("engine", "review", "style")  # keys a format may set or leave to the program, director or pack
DEFAULT_REVIEW = "always"  # a composed film is held for a person unless its program or format says otherwise
DEFAULTS = {"look": "auto", "captions": "page", "transition": "auto", "outro": swipe.DEFAULT_OUTRO, "voice": "family",
            "music": "family", "sfx": "off", "platform": "shorts", "min_seconds": 18, "max_seconds": 45,
            "theme": "default", "beats": "on", "chapters": "off"}
RENDER_KEYS = ("sfx", "beats", "chapters")  # passed to props.build as they are (render_keys)
BUILTIN = {
    "news": {"label": "ამბავი: სტანდარტული", "about": "The default news Short: look and voice by category, "
             "two-line captions that never move."},
    "news-roll": {"label": "ამბავი: მოძრავი ტიტრები", "captions": "roll",
                  "about": "The same, with the three-line teleprompter captions."},
    "longform": {"label": "სიუჟეტი: ორი-ოთხი წუთი", "captions": "keyword", "look": "editorial", "chapters": "on",
              "voice": "anchor", "music": "politics", "platform": "youtube",
              "min_seconds": 90, "max_seconds": 300,
              "about": "A two-to-four-minute story with chapters, a map and numbers."},
    "story": {"label": "ისტორია: კომპოზიციური ფილმი", "captions": "keyword", "look": "editorial",
              "voice": "anchor", "music": "politics", "platform": "youtube", "engine": "hyperframes",
              "chapters": "on", "sfx": "on", "min_seconds": 90, "max_seconds": 300,
              "about": "A composed story film on HyperFrames: blocks, chapters, keyword captions, sound."},
    "film": {"label": "ფილმი: გრძელი რგოლი", "captions": "roll", "look": "editorial",
             "voice": "anchor", "music": "politics", "platform": "youtube",
             "min_seconds": 150, "max_seconds": 600,
             "about": "A documentary cut, three to ten minutes, vertical for now."},
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
    themes = themes_known()
    if f["theme"] not in THEME_MODES and f["theme"] not in themes:
        bad("theme", f["theme"], THEME_MODES + tuple(themes))
    if not (0 < f["min_seconds"] < f["max_seconds"] <= 900):
        raise FormatError(f"format {name!r}: need 0 < min_seconds < max_seconds <= 900")
    if "engine" in f:
        engine_value(f["engine"], f"format {name!r}", FormatError)
    if "review" in f:
        review_policy(f["review"], f"format {name!r}", FormatError)
    if "style" in f and f["style"] is not None:
        from tt_shorts import styles
        if f["style"] not in styles.names():
            bad("style", f["style"], styles.names())
    unknown = set(f) - set(DEFAULTS) - {"label", "about", "name"} - set(OPTIONAL)
    if unknown:
        raise FormatError(f"format {name!r}: unknown keys {sorted(unknown)}")
    return f


def themes_known():
    """Every theme name some pack defines (a format may name one; the story's pack must have it at render)."""
    from tt_shorts import brand
    out = []
    for n in brand.names():
        out += [t for t in brand.load(n)["themes"] if t not in out and re.match(r"^[a-z][a-z0-9-]*$", t)]
    return out
def engine_value(value, where="engine", error=ValueError):
    """value if it is a film engine, else raise `error`."""
    if value not in ENGINES:
        raise error(f"{where}: engine={value!r} is not one of {', '.join(ENGINES)}")
    return value


def review_policy(value, where="review", error=ValueError):
    """'always' -> ("always", None); 'until:<n>' -> ("until", n): a composed film is held for a person until the
    brand has n approved in a row (until:0: never held for this). Raises `error` on anything else."""
    m = re.fullmatch(r"until:(\d{1,4})", str(value))
    if value == "always":
        return "always", None
    if m:
        return "until", int(m.group(1))
    raise error(f"{where}: review={value!r} is \"always\" or \"until:<n>\" (n approved films in a row)")


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
