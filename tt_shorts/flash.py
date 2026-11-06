"""Flash: a finished video must not strobe (ITU-R BT.1702-3, the broadcast guidance on photosensitive seizures).

Videos go out without a person looking, and a look's inversions or a shutter on a dark canvas are real swings of
light. So qa_file runs the guidance's test on the file itself, whichever engine drew it:

    a change     a rise or a fall of STEP (20 cd/m2) or more in one part of the screen, its darker side under DARK
                 (160 cd/m2), at the guidance's reference peak white PEAK (200 cd/m2)
    a flash      a pair of opposing changes
    too much     more than 3 flashes (MAX_CHANGES changes) in any one second, over more than AREA (a quarter) of the
                 screen

A transition to or from saturated red counts at any luminance. The guidance names it without a formula; RED_SHARE and
RED_GAIN are WCAG 2.3.1's measure of it, the same STEP on (R - G - B) x 320.

One slow change stays one change however many frames it takes: a cell's change is counted from its last extreme, not
frame by frame. The screen is read at GRID cells, area averaged, every frame. A file that can't be read is a problem,
never a pass (the check is safety, the one hold in QA that isn't about the file's format). Pure on arrays: changes(),
worst(), judge(). measure() reads a file with ffmpeg.
"""
import subprocess

import numpy as np

from tt_shorts import speech

FPS = speech.FPS
PEAK = 200.0  # cd/m2: the guidance's reference peak white for SDR
STEP = 20.0  # cd/m2: a change is at least this
DARK = 160.0  # cd/m2: and its darker side is under this
MAX_CHANGES = 6  # in any one second: 3 flashes, a pair of changes each
AREA = 0.25  # the share of the screen those flashes may not exceed
RED_SHARE = 0.8  # WCAG 2.3.1: saturated red is R / (R + G + B) at or above this
RED_GAIN = 320.0  # and its measure is (R - G - B) x this
GRID = (27, 48)  # cells across and down: 40 px each on a 1080x1920 frame

_LINEAR = np.array([(c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                    for c in (v / 255 for v in range(256))], dtype=np.float32)  # sRGB byte -> linear light


def luminance(rgb):
    """frames x cells x 3 bytes -> frames x cells in cd/m2 on the reference display."""
    r, g, b = (_LINEAR[rgb[..., i]] for i in range(3))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) * PEAK


def redness(rgb):
    """frames x cells x 3 bytes -> frames x cells: the red measure where the cell is saturated red, else 0."""
    r, g, b = (_LINEAR[rgb[..., i]] for i in range(3))
    total = r + g + b
    share = np.divide(r, total, out=np.zeros_like(r), where=total > 0)
    return np.where(share >= RED_SHARE, np.clip(r - g - b, 0, None) * RED_GAIN, 0.0)


def changes(signal, dark=DARK):
    """frames x cells of light -> frames x cells of bool: True on the frame a cell's change is complete. A cell needs
    STEP away from its last extreme, in the other direction from its last change, with the darker side under `dark`."""
    frames, cells = signal.shape
    out = np.zeros((frames, cells), dtype=bool)
    low, high = signal[0].copy(), signal[0].copy()
    last = np.zeros(cells, dtype=np.int8)  # the last change's direction: +1 rose, -1 fell, 0 none yet
    for i in range(1, frames):
        v = signal[i]
        low, high = np.minimum(low, v), np.maximum(high, v)
        rose = (v - low >= STEP) & (low < dark) & (last <= 0)
        fell = (high - v >= STEP) & (v < dark) & (last >= 0) & ~rose
        out[i] = rose | fell
        last[rose], last[fell] = 1, -1
        high[rose], low[fell] = v[rose], v[fell]  # the next change is counted from here
    return out


def worst(found, fps=FPS):
    """frames x cells of changes -> (the largest share of the screen over MAX_CHANGES in one second, its first frame)."""
    frames = found.shape[0]
    total = np.cumsum(found, axis=0, dtype=np.int32)
    if frames <= fps:
        counts = total[-1:]
    else:
        counts = total[fps:] - total[:-fps]
    area = (counts > MAX_CHANGES).mean(axis=1)
    at = int(area.argmax())
    return round(float(area[at]), 3), at


def judge(rgb, fps=FPS):
    """frames x cells x 3 bytes -> {"checked", "area", "at" (seconds), "signal", "seconds", "limit"}: the worse of the
    luminance test and the red test."""
    if rgb.shape[0] < 2:
        return {"checked": False, "seconds": round(rgb.shape[0] / fps, 2)}
    tests = {"luminance": changes(luminance(rgb)), "red": changes(redness(rgb), dark=float("inf"))}
    results = {k: worst(v, fps) for k, v in tests.items()}
    signal = max(results, key=lambda k: results[k][0])
    area, at = results[signal]
    return {"checked": True, "area": area, "at": round(at / fps, 2), "signal": signal,
            "seconds": round(rgb.shape[0] / fps, 2), "limit": AREA}


def frames_of(path, grid=GRID, fps=FPS):
    """A video's every frame at grid cells -> frames x cells x 3 bytes, or None when ffmpeg can't read it."""
    w, h = grid
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf",
                            f"fps={fps},scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return None
    size = w * h * 3
    if r.returncode != 0 or len(r.stdout) < size:
        return None
    n = len(r.stdout) // size
    return np.frombuffer(r.stdout, dtype=np.uint8, count=n * size).reshape(n, h * w, 3)


def measure(path):
    """judge() of a video file; {"checked": False} when it can't be read."""
    rgb = frames_of(path)
    return judge(rgb) if rgb is not None else {"checked": False}


def problems(report):
    """A measure() report -> [problem strings] for qa_file: only the safety limit, and a file it could not read."""
    if not report.get("checked"):
        return ["flash: the frames could not be read, so the video was not checked for flashing"]
    if report["area"] > AREA:
        kind = "saturated red" if report["signal"] == "red" else "light"
        return [f"flash: at {report['at']:.1f}s {report['area']:.0%} of the screen flashes ({kind}) more than 3 times "
                f"in a second (ITU BT.1702: not over {AREA:.0%}); slow the cuts or the inversions there"]
    return []
