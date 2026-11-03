"""Chapters: "01 / 03" and a segmented bar in the header, for a longer video (docs/plan-v2.md § 2: the reference's
chapter bar, top left, the whole video).

The chapters are code's, from the scene list the video shows (the writer never names them):
  - the hook opens chapter 1 (it is never a chapter alone);
  - every chapter has at least MIN_SCENES scenes (the end card counts in the last one);
  - a digest's `chapter` cards say where its stories begin: each one opens a chapter, the rule of three aside;
  - otherwise the video gets as many chapters as the scenes allow (at most MAX_CHAPTERS), split where their
    lengths come out the most even (the earliest of equals).
A video that can't make two chapters gets none.

The format key `chapters` decides: off (the default: every video as before), on, or auto (for a video of
AUTO_SECONDS or more). props["chapters"] is [{"from", "to"}] in frames; remotion/src/NewsShort.tsx Header draws it
in the header band (data-probe="header"): the current chapter's number, the count, and one segment a chapter that
fills as it plays, the accent dot at its head ("now").
"""
import itertools

from tt_shorts import speech

FPS = speech.FPS
MODES = ("auto", "on", "off")
AUTO_SECONDS = 40
MIN_SCENES = 3
MAX_CHAPTERS = 4


def _bounds(scenes, total):
    return [s["from"] for s in scenes] + [total]


def split(scenes, total, mode="off"):
    """Built scenes (with from and duration) and the video's last frame -> [{"from", "to"}] or None."""
    if mode not in MODES:
        raise ValueError(f"chapters {mode!r} is not one of {', '.join(MODES)}")
    if mode == "off" or not scenes or (mode == "auto" and total / FPS < AUTO_SECONDS):
        return None
    edge = _bounds(scenes, total)
    cards = [i for i, s in enumerate(scenes) if s.get("type") == "chapter" and i > 0]
    if cards:  # a digest: its chapter cards open its stories
        starts = [0] + cards
    else:
        n = min(MAX_CHAPTERS, len(scenes) // MIN_SCENES)
        if n < 2:
            return None
        best = None
        for cut in itertools.combinations(range(MIN_SCENES, len(scenes) - MIN_SCENES + 1), n - 1):
            starts = (0, *cut)
            sizes = [b - a for a, b in zip(starts, starts[1:] + (len(scenes),))]
            if min(sizes) < MIN_SCENES:
                continue
            lens = [edge[b] - edge[a] for a, b in zip(starts, starts[1:] + (len(scenes),))]
            spread = max(lens) - min(lens)
            if best is None or spread < best[0]:
                best = (spread, starts)
        if best is None:
            return None
        starts = list(best[1])
    if len(starts) < 2:
        return None
    ends = starts[1:] + [len(scenes)]
    return [{"from": edge[a], "to": edge[b]} for a, b in zip(starts, ends)]


def at(chapters, frame):
    """The chapter (0-based) a frame is in."""
    return max((i for i, c in enumerate(chapters or []) if c["from"] <= frame), default=0)
