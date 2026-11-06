"""Sound effects on the timeline: which accent sounds when, and one track of them for the mix (format key `sfx`).

The cues come from the video's own timeline (the props every engine gets), never from the writer:

    a cut between scenes          whoosh (click for a plain "cut" transition), centred on the cut's motion
    a mark landing (em)           pop, when the stroke starts (speech.mark_frames: when the voice says it)
    the outro chip coming in      pop
    a stat's number counting      tick every TICK_EVERY frames while it counts (click for the flap board), then
                                  a soft thud as it settles
    a chart's bars or cells       blip as each one starts to grow (bars, compare, share)

The sounds are tools/compose_sfx.py's (synthesized, ours, deterministic). track() lays them on one stereo WAV at
their own level; props.mix_audio puts that track under the voice at one constant level (LEVEL_DB): no ducking, no
risers, nothing that rises and falls under the speech (the owner's music rule). Remotion never sees a cue: the mix
is ffmpeg's, so a HyperFrames film gets the same sound from the same props.

    cues(props) -> [{"t": seconds, "name": "whoosh"}, ...]   sorted, at least MIN_GAP apart
"""
import contextlib
import pathlib
import runpy
import sys
import wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "assets" / "sfx"
NAMES = ("click", "pop", "whoosh", "tick", "thud", "blip")
SR = 48000
FPS = 30
LEVEL_DB = -6.0  # the whole track, under the -16 LUFS voice: accents a little above the music bed, never louder
MIN_GAP = 0.06  # seconds: two accents closer than this are one
TICK_EVERY = 3  # frames between two ticks of a counting number
COUNT_DELAY, COUNT_FRAMES = 4, 32  # remotion/src/scenes/index.tsx Stat: the number counts from frame 4 for 32
WHOOSH_LEAD = 0.1  # a whoosh starts this much before the cut, so its middle lands on the moving scene
CHART_STEP = 10  # frames between two bars' starts (remotion/src/scenes: 6 + i * 10)
# Cues tailored per transition: snaps on cuts/louvers, pop on iris, whoosh on sweeps, silent on fade
CUT_SOUND = {
    "cut": "click",
    "shutter": "click",
    "blind": "click",
    "iris": "pop",
    "meter": "blip",
    "line": "whoosh",
    "panel": "whoosh",
    "wipe": "whoosh",
    "slide": "whoosh",
    "push": "whoosh",
    "split": "whoosh",
    "corner": "whoosh",
    "fade": None,
}
OPTIONS = {"off": "no sound effects (the default: renders are as before)",
           "on": "short accents on the timeline: a whoosh on a cut, a pop when a mark lands, ticks while a number "
                 "counts, blips as bars grow; one constant level under the voice, no ducking"}


def files_ready():
    return all((DIR / f"{n}.wav").is_file() for n in NAMES)


def ensure():
    """The sound files, composed once when they are missing (tools/compose_sfx.py, under a second)."""
    if not files_ready():  # its report goes to stderr: an engine command's stdout is its JSON
        with contextlib.redirect_stdout(sys.stderr):
            runpy.run_path(str(ROOT / "tools" / "compose_sfx.py"), run_name="veasy_sfx")["main"](DIR)
    return DIR


def cues(props):
    """The accents of one video, from its props' timeline -> [{t, name}] (seconds)."""
    out = []
    scenes = props.get("scenes") or []
    for i, s in enumerate(scenes):
        a = s["from"]
        if i > 0:
            tr = s.get("transition") or props.get("transition") or "line"
            snd = CUT_SOUND.get(tr, "whoosh")
            if snd:
                lead = 0.0 if snd in ("click", "pop", "blip") else WHOOSH_LEAD
                out.append({"t": max(0.0, a / FPS - lead), "name": snd})
        m = s.get("mark")
        if m and isinstance(m.get("at"), (int, float)):
            out.append({"t": (a + m["at"]) / FPS, "name": "pop"})
        t = s.get("type")
        if t == "stat" and not s.get("isotype"):
            flap = s.get("style") == "flap"
            end = min(s.get("duration", 0), COUNT_DELAY + COUNT_FRAMES)
            for f in range(COUNT_DELAY, end, TICK_EVERY):
                out.append({"t": (a + f) / FPS, "name": "click" if flap else "tick"})
            if end > COUNT_DELAY:
                out.append({"t": (a + end) / FPS, "name": "thud"})
        if t in ("bars", "compare", "chart"):
            for k in range(len(s.get("items") or [])):
                f = 6 + k * CHART_STEP
                if f < s.get("duration", 0):
                    out.append({"t": (a + f) / FPS, "name": "blip"})
        if t == "share":
            out.append({"t": (a + 8) / FPS, "name": "blip"})
    if props.get("outroFrom"):
        out.append({"t": props["outroFrom"] / FPS, "name": "pop"})
    end = props.get("durationInFrames", 0) / FPS
    kept = []
    for c in sorted(out, key=lambda c: (c["t"], NAMES.index(c["name"]))):
        if end and c["t"] >= end - 0.05:
            continue
        if kept and c["t"] - kept[-1]["t"] < MIN_GAP:
            continue
        kept.append({"t": round(c["t"], 3), "name": c["name"]})
    return kept


def _read(name):
    with wave.open(str(DIR / f"{name}.wav"), "rb") as w:
        if w.getframerate() != SR or w.getnchannels() != 1:
            raise ValueError(f"assets/sfx/{name}.wav: 48 kHz mono expected (run tools/compose_sfx.py)")
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32767


def track(cue_list, seconds, out):
    """The cues on one stereo 48 kHz WAV of `seconds` (each sound at its file's level; the mix sets the track's)."""
    ensure()
    n = int(round(seconds * SR))
    mono = np.zeros(n, dtype=np.float32)
    sounds = {}
    for c in cue_list:
        x = sounds.setdefault(c["name"], _read(c["name"]))
        a = int(round(c["t"] * SR))
        if a >= n:
            continue
        b = min(n, a + len(x))
        mono[a:b] += x[:b - a]
    pcm = (np.clip(mono, -0.99, 0.99) * 32767).round().astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    out = pathlib.Path(out)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    return out
