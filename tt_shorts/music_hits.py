"""Where the music's heavy hits are, and where a loop must start so one lands on the film's main moment.

The beds are tools/compose_music.py's, so the hits are the composer's own data, not something to detect: a loop is
whole bars at a known tempo, and every bar opens with its heaviest event (the bass note, with the kick where the
family has one on beat 0). `heavy(name)` is those bar openings, `hits(name)` adds the other soft kicks.

    offset("politics-2.m4a", 12.4) -> seconds into the loop to start from, so that bar opening lands at 12.4 s

props.mix_audio applies it with `atrim=start=` on the already-looped stream (never `-ss` on a `-stream_loop` input:
every later loop would restart at the offset, a seam). It moves the start only: the beds are levelled bar by bar,
so any start has the same level (tests/test_music_hits.py measures it with ebur128). No dependency beyond the
composer's own (numpy, scipy), and nothing is read from the m4a. A bed this module doesn't know gives offset 0.
"""
import importlib.util
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOLERANCE = 0.06  # seconds: how far a hit may land from the moment (an aac loop starts ~21 ms late; one frame is 33 ms)
_composer = []


def composer():
    if not _composer:
        spec = importlib.util.spec_from_file_location("veasy_compose_music", ROOT / "tools" / "compose_music.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _composer.append(mod)
    return _composer[0]


def piece(name):
    """`<family>-<k>[.m4a]` -> the composer's variation of that family's piece, or None."""
    m = re.fullmatch(r"([a-z]+)-(\d+)(?:\.\w+)?", pathlib.Path(name or "").name)
    c = composer()
    if not m or m.group(1) not in c.PIECES or not 1 <= int(m.group(2)) <= len(c.VARIANTS):
        return None
    return c.variation(c.PIECES[m.group(1)], c.VARIANTS[int(m.group(2)) - 1])


def grid(name):
    """(loop seconds, bar seconds, beat seconds) of a bed, as compose() builds it, or None."""
    p = piece(name)
    if not p:
        return None
    beat = 60 / p["bpm"]
    bar = 4 * beat
    return int(composer().LENGTH // bar) * bar, bar, beat


def heavy(name):
    """The loop's heaviest hits: each bar's opening (seconds from the loop's start)."""
    g = grid(name)
    if not g:
        return []
    length, bar, _ = g
    return [round(b * bar, 4) for b in range(int(round(length / bar)))]


def hits(name):
    """Every kick and bar opening of the loop, sorted."""
    p, g = piece(name), grid(name)
    if not g:
        return []
    length, bar, beat = g
    out = {round(b * bar + q * beat, 4) for b in range(int(round(length / bar))) for q in [0, *p["kick"]]}
    return sorted(out)


def offset(name, moment):
    """Seconds into the loop to start from so a heavy hit lands at film time `moment`; 0 for no moment or an unknown bed."""
    g = grid(name)
    if moment is None or not g:
        return 0.0
    return round((-moment) % g[1], 4)  # the openings repeat every bar: the first one at or after the start is enough


def landing(name, moment):
    """Film time of the heavy hit nearest `moment` when the loop starts at offset(name, moment): the check."""
    g = grid(name)
    o = offset(name, moment)
    times = [(h - o) % g[0] for h in heavy(name)]
    return min(times, key=lambda t: abs(t - moment))
