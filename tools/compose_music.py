"""tbilisi.today Shorts music: one news bed per category family, composed in code (ours outright: $0, no licence,
no Content ID claims). Written from scratch for tbilisi.today on 2026-11-01, after the owner heard the first
beds rise and fall under the voice.

  python tools/compose_music.py [out_dir]      needs numpy + scipy and ffmpeg; writes assets/music/<family>-<1..4>.m4a
                                               (VARIANTS: four loops per family, one sound)

The sound, in one idea: the brand's red dot means "now", so the bed is a clock. A soft tick on every sixteenth
runs from the first bar to the last, over warm electric-piano chords, a low pad and a quiet bass. Every family
has the same instruments (one sonic brand) in its own key, mode and tempo: minor and slower for hard news, major
and quicker for light news.

Rules the code enforces, because a bed sits under a voice for 30-45 seconds:
  - one level from start to end: no build-up, no drop, no fill. Every bar has the same parts, and a bar-by-bar
    gain pass evens out the rest (the bar-to-bar loudness spread is printed; it stays under 1 dB)
  - out of the voice's way: the 1-4 kHz band is cut, there is no melody, and the attacks are soft
  - audible on a phone: nothing important lives under 150 Hz; the bass carries harmonics
  - a seamless loop: the reverb tail wraps to the start, and the video fades it in and out
"""
import pathlib
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
MAX_SPREAD_DB = 0.8  # bar-to-bar loudness spread a loop may have; main() refuses to write one above 1 dB
LENGTH = 64.0  # seconds per loop (whole bars, rounded down); a video is 30-45 s
TAIL = 3.0
rng = np.random.default_rng(20261101)

NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
CHORDS = {"m7": (0, 3, 7, 10), "M7": (0, 4, 7, 11), "sus": (0, 5, 7, 10), "M9": (0, 4, 7, 14), "m9": (0, 3, 7, 14),
          "add9": (0, 4, 7, 14), "m": (0, 3, 7, 12), "M": (0, 4, 7, 12), "6": (0, 4, 7, 9)}

# family -> key and feel. prog: one chord per bar [(root, octave, kind)]; stabs: the beats (in a 4-beat bar) where
# the keys play; kick: beats with a soft kick ([] for none).
PIECES = {
    "politics": dict(bpm=94, prog=[("D", 3, "m9"), ("A#", 2, "M7"), ("G", 2, "m7"), ("A", 2, "sus")],
                     stabs=[0, 1.5, 2.5], kick=[0, 2]),
    "economy": dict(bpm=106, prog=[("C", 3, "M7"), ("A", 2, "m7"), ("F", 2, "M9"), ("G", 2, "6")],
                    stabs=[0, 1.5, 2.5, 3.5], kick=[0, 1, 2, 3]),
    "world": dict(bpm=98, prog=[("E", 3, "m9"), ("C", 3, "M7"), ("G", 2, "add9"), ("D", 3, "sus")],
                  stabs=[0, 1.5, 3], kick=[0, 2]),
    "crime": dict(bpm=86, prog=[("A", 2, "m9"), ("F", 2, "M7"), ("D", 3, "m7"), ("E", 2, "sus")],
                  stabs=[0, 2.5], kick=[]),
    "sports": dict(bpm=116, prog=[("D", 3, "M"), ("B", 2, "m7"), ("G", 2, "M7"), ("A", 2, "6")],
                   stabs=[0, 0.75, 1.5, 2.5, 3.5], kick=[0, 1, 2, 3]),
    "culture": dict(bpm=90, prog=[("F", 2, "M9"), ("D", 3, "m7"), ("A#", 2, "M7"), ("C", 3, "sus")],
                    stabs=[0, 2], kick=[]),
    "tech": dict(bpm=108, prog=[("A", 2, "m9"), ("F", 2, "M7"), ("C", 3, "add9"), ("G", 2, "6")],
                 stabs=[0, 0.75, 1.5, 2.5, 3], kick=[0, 2]),
    "society": dict(bpm=100, prog=[("G", 2, "add9"), ("E", 2, "m7"), ("C", 3, "M7"), ("D", 3, "sus")],
                    stabs=[0, 1.5, 2.5], kick=[0, 2]),
}


# Variations of every family's piece, so fifty videos a day don't share eight loops (owner, 2026-11-02). Same
# instruments and the same steady level (one sonic brand); each moves the key, the tempo, the rhythm of the keys
# and the clock, or starts the progression elsewhere. tt_shorts/variety.py picks the least used loop.
#   shift: semitones · bpm: added to the tempo · stabs: "same" | "sparse" | "offbeat" · rotate: bars
#   tick: 16 | 8 (clock subdivisions) · keys: octave multiplier of the electric piano · bell: its bell partial
VARIANTS = (
    dict(),
    dict(shift=2, bpm=4, stabs="offbeat", tick=8),
    dict(shift=-3, bpm=-6, stabs="sparse", keys=1, bell=0.2),
    dict(shift=5, bpm=2, rotate=2, bell=0.26),
)


def transpose(prog, semis):
    names = list(NOTES)
    out = []
    for root, octave, kind in prog:
        i = NOTES[root] + semis
        out.append((names[i % 12], octave + i // 12, kind))
    return out


def variation(p, v):
    """The family's piece p, changed by one entry of VARIANTS."""
    q = dict(p)
    q["prog"] = transpose(p["prog"], v.get("shift", 0))
    r = v.get("rotate", 0) % len(q["prog"])
    q["prog"] = q["prog"][r:] + q["prog"][:r]
    q["bpm"] = p["bpm"] + v.get("bpm", 0)
    if v.get("stabs") == "sparse":
        q["stabs"] = p["stabs"][::2] or p["stabs"]
        q["kick"] = p["kick"][::2]
    elif v.get("stabs") == "offbeat":
        q["stabs"] = sorted({(s + 0.5) % 4 for s in p["stabs"]})
    q["tick"] = v.get("tick", 16)
    q["keys"] = v.get("keys", 2)
    q["bell"] = v.get("bell", 0.12)
    return q


def hz(name, octave):
    return 440.0 * 2 ** ((NOTES[name] + 12 * (octave + 1) - 69) / 12)


def chord(root, octave, kind):
    return [hz(root, octave) * 2 ** (s / 12) for s in CHORDS[kind]]


def filt(x, cutoff, kind, order=2):
    return sosfilt(butter(order, cutoff, kind, fs=SR, output="sos"), x)


def place(track, start, sound, gain=1.0):
    i = int(round(start * SR))
    if 0 <= i < len(track):
        sound = sound[:len(track) - i]
        track[i:i + len(sound)] += sound * gain


def adsr(n, a, r):
    e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr:
        e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def epiano(f, dur, bell_gain=0.12):
    """A warm electric-piano note: sine body, a soft bell partial that fades fast, a little tremolo."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f * t) + 0.22 * np.sin(4 * np.pi * f * t) * np.exp(-t * 4)
    bell = bell_gain * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t * 9)
    trem = 1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)
    return (body + bell) * trem * np.exp(-t * 2.2) * adsr(n, 0.008, min(0.25, dur * 0.4))


def pad(freqs, dur):
    """A low, steady pad under the whole bar: detuned sines, slow in and out, so bars overlap without a seam."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for cents in (-4, 4):
            out += np.sin(2 * np.pi * f * 2 ** (cents / 1200) * t)
    return filt(out, 900, "low") * adsr(n, dur * 0.3, dur * 0.3) / (2 * len(freqs))


def bass(f, dur):
    """The 2nd-4th harmonics carry the note on a phone, whose speaker can't play the fundamental."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.6 * np.sin(4 * np.pi * f * t) + 0.3 * np.sin(6 * np.pi * f * t)
    return filt(np.tanh(1.2 * tone) / 1.2, 700, "low") * np.exp(-t * 1.5) * adsr(n, 0.015, min(0.2, dur * 0.4))


def tick(accent):
    """The clock: a very short, dark click. Accented on the beat, ghosted between."""
    n = int(0.035 * SR)
    t = np.arange(n) / SR
    click = filt(filt(rng.standard_normal(n), 5200, "high"), 9000, "low") * np.exp(-t * 160)
    tone = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 220) * 0.4  # a wooden "tock" under the noise
    return (click + tone) * (1.0 if accent else 0.45)


def kick():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    f = 58 + 95 * np.exp(-t * 34)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 13)


def reverb(stereo, seconds=2.2, wet=0.22):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    base = rng.standard_normal(n)
    out = []
    for ch in range(2):
        ir = (0.85 * base + 0.15 * rng.standard_normal(n)) * np.exp(-t * 6.5 / seconds)
        ir = filt(ir, 4500, "low")
        ir /= np.sqrt(np.sum(ir ** 2))
        out.append((1 - wet) * stereo[ch] + wet * fftconvolve(stereo[ch], ir)[:len(stereo[ch])])
    return np.array(out)


def flatten(stereo, bar, most_db=6.0):
    """Even out the level bar by bar: every bar has the same parts, so one gain per bar (cross-faded between bar
    centres) removes what the chords' different roots add, without pumping inside a bar. Measured above 150 Hz,
    where a phone plays it."""
    mono = filt(stereo.mean(axis=0), 150, "high")
    n = int(bar * SR)
    bars = max(1, len(mono) // n)
    rms = np.array([np.sqrt(np.mean(mono[i * n:(i + 1) * n] ** 2) + 1e-12) for i in range(bars)])
    gain = np.clip(np.median(rms) / rms, 10 ** (-most_db / 20), 10 ** (most_db / 20))
    centres = (np.arange(bars) + 0.5) * n
    # wrap the ends so the loop point gets the same smooth curve
    x = np.concatenate([[centres[-1] - bars * n], centres, [centres[0] + bars * n]])
    g = np.concatenate([[gain[-1]], gain, [gain[0]]])
    return stereo * np.interp(np.arange(len(mono)), x, g)


def bar_spread_db(stereo, bar):
    """Loudness spread over the loop, bar by bar (max - min, dB, above 150 Hz): what the owner heard as rising and
    falling."""
    mono = filt(stereo.mean(axis=0), 150, "high")
    n = int(bar * SR)
    levels = [20 * np.log10(np.sqrt(np.mean(mono[i:i + n] ** 2)) + 1e-12) for i in range(0, len(mono) - n + 1, n)]
    return max(levels) - min(levels)


def compose(p):
    beat = 60 / p["bpm"]
    bar = 4 * beat
    bars = int(LENGTH // bar)
    length = bars * bar
    n = int((length + TAIL) * SR)
    L, R = np.zeros(n), np.zeros(n)

    def both(t0, s, gain=1.0, pan=0.5):
        if t0 < 0:  # the first bar's pad starts before the loop: it belongs at the end, and wraps around
            t0 += length
        place(L, t0, s, gain * (1 - pan) * 2)
        place(R, t0, s, gain * pan * 2)

    for b in range(bars):  # every bar has the same parts: no intro, no build, no drop
        root, octv, kind = p["prog"][b % len(p["prog"])]
        notes = chord(root, octv, kind)
        start = b * bar
        both(start - 0.25 * bar, pad([f for f in notes[:3]], bar * 1.5), 0.55)
        for s in p["stabs"]:
            for k, f in enumerate(notes):  # the chord, spread a few ms like a hand
                both(start + s * beat + k * 0.006, epiano(f * p.get("keys", 2), beat * 1.6, p.get("bell", 0.12)),
                     0.085 * (2 / p.get("keys", 2)) ** 0.5, 0.42 + 0.05 * k)
        both(start, bass(notes[0] / 2, beat * 1.8), 0.24)
        both(start + 2 * beat, bass(notes[0] / 2, beat * 1.4), 0.2)
        for q in p["kick"]:
            both(start + q * beat, kick(), 0.2)
        sub = p.get("tick", 16)  # the clock: sixteenths (or eighths), the beat accented
        for s in range(sub):
            both(start + s * 4 * beat / sub, tick(s % (sub // 4) == 0), 0.05 * (16 / sub) ** 0.3, 0.38 if s % 2 else 0.62)

    mix = reverb(np.array([L, R]))
    loop = int(length * SR)
    mix[:, :n - loop] += mix[:, loop:]  # the tail wraps to the start: the loop has no seam
    mix = mix[:, :loop]
    mix = np.array([filt(ch, 90, "high", 4) for ch in mix])  # no sub: phones can't play it
    mix = mix - 0.55 * np.array([filt(ch, [1100, 4200], "band") for ch in mix])  # room for the voice
    mix = flatten(flatten(mix, bar), bar)  # a second pass catches what the reverb tail moved
    for _ in range(6):  # sparse or low variations need more passes: the owner hears anything over ~1 dB as pumping
        if bar_spread_db(mix, bar) <= MAX_SPREAD_DB:
            break
        mix = flatten(mix, bar)
    return mix / np.max(np.abs(mix)) * 0.89, bar


def write(path, stereo):
    pcm = (np.clip(stereo.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / "assets" / "music")
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.m4a"):
        old.unlink()
    for name, base in PIECES.items():
        for k, v in enumerate(VARIANTS, 1):
            mix, bar = compose(variation(base, v))
            spread = bar_spread_db(mix, bar)
            if spread > 1.0:  # never ship a bed that rises and falls under the voice
                print(f"{name}-{k}: skipped, bar-to-bar spread {spread:.2f} dB")
                continue
            wav, m4a = out / f"{name}-{k}.wav", out / f"{name}-{k}.m4a"
            write(wav, mix)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-af",
                            "loudnorm=I=-16:TP=-1.5:LRA=4:linear=true", "-c:a", "aac", "-b:a", "128k", str(m4a)],
                           check=True)
            wav.unlink()
            print(f"{name}-{k}: {mix.shape[1] / SR:.1f}s, bar-to-bar spread {bar_spread_db(mix, bar):.2f} dB, "
                  f"{m4a.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
