"""tbilisi.today Shorts background music, composed in code: two loops per category family, ours outright ($0, no
licence, no Content ID claims). Forked from sitech-shorts tools/compose_music.py. Run once; the loops go to
assets/music/<family>-<n>.m4a and render.py lays them under the voice (it picks one per story and handles the fades
and the ducking).

  python tools/compose_music.py [out_dir]      needs numpy + scipy (the lab's venv-cb) and ffmpeg

What the mix rules come from (knowledge/video-brainstorm/background-music.md):
  - phones barely play anything under ~150 Hz: the music lives in 200 Hz-1 kHz, the bass carries harmonics so
    it is heard on a phone, the sub is filtered out
  - the voice's consonants sit at 1-4 kHz: the bed dips there, the hats are soft and dark
  - no melody, sparse rhythm: a bed under speech, not a song
  - seamless loops (the reverb tail wraps to the start, no fades in the file): render fades per video
  - mono-safe: phones often play one speaker, so the stereo width is modest
"""
import pathlib
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
LENGTH = 75.0  # seconds per loop (whole bars, rounded down); videos are 30-60 s, longer ones loop seamlessly
TAIL = 3.0
rng = np.random.default_rng(20261028)

NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
CHORDS = {"m7": (0, 3, 7, 10), "M7": (0, 4, 7, 11), "sus": (0, 5, 7, 10), "M9": (0, 4, 7, 14), "m9": (0, 3, 7, 14),
          "add9": (0, 4, 7, 14), "m": (0, 3, 7, 12)}


def hz(name, octave):
    return 440.0 * 2 ** ((NOTES[name] + 12 * (octave + 1) - 69) / 12)


def chord(root, octave, kind):
    return [hz(root, octave) * 2 ** (s / 12) for s in CHORDS[kind]]


def env(n, a, r, sustain=1.0):
    e = np.full(n, sustain)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.linspace(0, sustain, na)
    if nr:
        e[-nr:] *= np.exp(-np.linspace(0, 5, nr))
    return e


def soft_saw(f, t, harmonics=7):
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, harmonics + 1) if f * k < SR / 2.2)


def filt(x, cutoff, kind, order=2):
    return sosfilt(butter(order, cutoff, kind, fs=SR, output="sos"), x)


def place(track, start, sound):
    i = int(start * SR)
    if i < len(track):
        sound = sound[:len(track) - i]
        track[i:i + len(sound)] += sound


def pad(freqs, dur, bright, detune=0.006):
    n = int(dur * SR)
    t = np.arange(n) / SR
    voice = np.zeros(n)
    for f in freqs:
        for d in (-detune, 0, detune):
            voice += soft_saw(f * (1 + d), t, 5) * (0.6 if d else 1)
    return filt(voice, bright, "low") * env(n, dur * 0.35, dur * 0.4) / (len(freqs) * 3)


def pluck(f, dur, bright):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return filt(soft_saw(f, t, 4) * np.exp(-t * 6), bright, "low") * env(n, 0.004, dur * 0.5)


def bell(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 3)
    return tone * np.exp(-t * 1.6) * env(n, 0.003, 0.3)


def bass(f, dur):
    """The 2nd-4th harmonics carry the note on a phone, whose speaker can't play the fundamental."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.7 * np.sin(4 * np.pi * f * t) + 0.45 * np.sin(6 * np.pi * f * t) \
        + 0.25 * np.sin(8 * np.pi * f * t)
    return filt(np.tanh(1.4 * tone) / 1.4, 900, "low") * env(n, 0.012, dur * 0.6, 0.9)


def kick(dur=0.4):
    """A soft thump with a 150-200 Hz body, so it is a beat on a phone too, not only a sub."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 60 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)


def hat(dur=0.05):
    n = int(dur * SR)
    noise = filt(filt(rng.standard_normal(n), 6500, "high"), 10000, "low")  # dark: away from the voice's "s"
    return noise * np.exp(-np.arange(n) / SR * 70) * 0.45


def reverb(stereo, seconds=2.6, wet=0.28):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    base = rng.standard_normal(n)
    out = []
    for ch in range(2):  # mostly shared impulse: wide enough, still mono-safe
        ir = (0.8 * base + 0.2 * rng.standard_normal(n)) * np.exp(-t * 6.5 / seconds)
        ir = filt(ir, 5000, "low")
        ir /= np.sqrt(np.sum(ir ** 2))
        out.append((1 - wet) * stereo[ch] + wet * fftconvolve(stereo[ch], ir)[:len(stereo[ch])])
    return np.array(out)


# tbilisi.today category family (tt_shorts.meta.FAMILIES) -> two pieces: tempo, progression
# [(root, octave, chord)], pad brightness, figure, drums. News beds stay calmer than SiTech's tech beds:
# serious families (politics, crime) pulse low and sparse, light ones (sports, culture) move more.
PIECES = {
    "politics": [
        dict(bpm=84, prog=[("D", 2, "m9"), ("A#", 2, "M7"), ("F", 2, "add9"), ("C", 3, "sus")], bright=1100,
             fig="pulse", drums="sparse"),
        dict(bpm=88, prog=[("G", 2, "m7"), ("D#", 2, "M7"), ("A#", 2, "add9"), ("F", 2, "sus")], bright=1050,
             fig="pulse", drums="sparse"),
    ],
    "economy": [
        dict(bpm=110, prog=[("C", 3, "M7"), ("G", 2, "sus"), ("A", 2, "m7"), ("F", 2, "M9")], bright=1900,
             fig="updown", drums="four"),
        dict(bpm=106, prog=[("F", 2, "add9"), ("C", 3, "add9"), ("D", 3, "m7"), ("A#", 2, "M7")], bright=1800,
             fig="updown", drums="four"),
    ],
    "world": [
        dict(bpm=92, prog=[("E", 2, "m9"), ("C", 3, "M7"), ("G", 2, "add9"), ("D", 3, "sus")], bright=1500,
             fig="up", drums="sparse"),
        dict(bpm=96, prog=[("B", 2, "m7"), ("G", 2, "M9"), ("D", 3, "add9"), ("A", 2, "sus")], bright=1450,
             fig="up", drums="sparse"),
    ],
    "crime": [
        dict(bpm=80, prog=[("A", 2, "m9"), ("F", 2, "M7"), ("D", 2, "m7"), ("E", 2, "sus")], bright=950,
             fig="pulse", drums="sparse"),
        dict(bpm=76, prog=[("C#", 2, "m7"), ("A", 2, "M7"), ("F#", 2, "m9"), ("G#", 2, "sus")], bright=900,
             fig="pulse", drums="none"),
    ],
    "sports": [
        dict(bpm=122, prog=[("D", 3, "M9"), ("B", 2, "m7"), ("G", 2, "M7"), ("A", 2, "sus")], bright=2100,
             fig="up", drums="four"),
        dict(bpm=118, prog=[("E", 2, "add9"), ("C#", 3, "m7"), ("A", 2, "M7"), ("B", 2, "sus")], bright=2000,
             fig="updown", drums="four"),
    ],
    "culture": [
        dict(bpm=78, prog=[("F", 2, "M9"), ("G", 2, "sus"), ("E", 2, "m7"), ("A", 2, "m7")], bright=1400,
             fig="bell", drums="none"),
        dict(bpm=82, prog=[("D", 3, "add9"), ("A", 2, "sus"), ("B", 2, "m7"), ("G", 2, "M9")], bright=1400,
             fig="bell", drums="none"),
    ],
    "tech": [
        dict(bpm=104, prog=[("E", 2, "m9"), ("C", 3, "M7"), ("G", 2, "add9"), ("D", 3, "sus")], bright=1700,
             fig="up", drums="four"),
        dict(bpm=100, prog=[("A", 2, "m9"), ("F", 2, "M9"), ("C", 3, "add9"), ("G", 2, "sus")], bright=1650,
             fig="up", drums="four"),
    ],
    "society": [
        dict(bpm=90, prog=[("G", 2, "add9"), ("D", 3, "sus"), ("E", 2, "m7"), ("C", 3, "M9")], bright=1500,
             fig="bell", drums="sparse"),
        dict(bpm=86, prog=[("C", 3, "M9"), ("A", 2, "m7"), ("F", 2, "add9"), ("G", 2, "sus")], bright=1450,
             fig="updown", drums="sparse"),
    ],
}


def compose(p):
    beat = 60 / p["bpm"]
    bar = 4 * beat
    bars = int(LENGTH // bar)
    length = bars * bar
    n = int((length + TAIL) * SR)
    L, R = np.zeros(n), np.zeros(n)
    both = lambda t0, s, pan=0.5: (place(L, t0, s * (1 - pan) * 2), place(R, t0, s * pan * 2))
    for b in range(bars):
        root, octv, kind = p["prog"][b % len(p["prog"])]
        notes = chord(root, octv, kind)
        start = b * bar
        intro = min(1.0, (b + 1) / 4)  # the opening builds up over four bars
        both(start, pad([f * 2 for f in notes], bar * 1.25, p["bright"]) * 0.45)
        steps = 4 if p["fig"] == "bell" else 8
        for s in range(steps):
            t0 = start + s * bar / steps
            if p["fig"] == "pulse":  # the root pulses in eighths; a high ping now and then
                both(t0, bass(notes[0] / 2, bar / steps * 0.9) * 0.28 * intro)
                if s in (3, 7) and b % 2:
                    both(t0, bell(notes[(s + b) % 4] * 4, 2.5) * 0.06, 0.3 if s == 3 else 0.7)
            elif p["fig"] == "bell":
                if (s + b) % 2 == 0:
                    both(t0, bell(notes[(s * 2 + b) % 4] * 4, 3.0) * 0.08 * intro, 0.35 if s % 2 else 0.65)
            else:
                order = [0, 1, 2, 3, 0, 1, 2, 3] if p["fig"] == "up" else [0, 1, 2, 3, 2, 1, 0, 1]
                both(t0, pluck(notes[order[s]] * 4, bar / steps * 1.6, p["bright"] * 1.8) * 0.1 * intro,
                     0.4 + 0.2 * (s % 2))
        if p["fig"] != "pulse":
            both(start, bass(notes[0] / 2, bar * 0.95) * 0.22 * intro)
        if b >= 2 and p["drums"] != "none":
            for q in range(4):
                if p["drums"] == "four" or q in (0, 2):
                    both(start + q * beat, kick() * 0.22)
                for h in ((0.5,) if p["drums"] == "sparse" else (0.5, 0.75)):
                    both(start + (q + h) * beat, hat() * (0.07 if p["drums"] == "four" else 0.05), 0.35 + 0.3 * (q % 2))
    mix = reverb(np.array([L, R]))
    loop = int(length * SR)
    mix[:, :n - loop] += mix[:, loop:]  # the tail wraps to the start: the loop has no seam
    mix = mix[:, :loop]
    mix = filt(mix, 70, "high", 4)  # no sub: phones can't play it and it eats the mix's headroom
    mix = mix - 0.5 * filt(mix, [1200, 4500], "band")  # room for the voice's consonants
    return mix / np.max(np.abs(mix)) * 0.89


def bands(stereo):
    """Share of energy per band, to check the bed is where a phone plays it and out of the voice's way."""
    mono = stereo.mean(axis=0)
    spec = np.abs(np.fft.rfft(mono)) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    total = spec.sum()
    edges = [(0, 150), (150, 1000), (1000, 4000), (4000, SR / 2)]
    return " ".join(f"{a:g}-{b:g}Hz {spec[(f >= a) & (f < b)].sum() / total:.0%}" for a, b in edges)


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
    for name, pieces in PIECES.items():
        for i, p in enumerate(pieces, 1):
            mix = compose(p)
            wav, m4a = out / f"{name}-{i}.wav", out / f"{name}-{i}.m4a"
            write(wav, mix)
            mono_drop = 10 * np.log10(np.mean(mix.mean(axis=0) ** 2) / np.mean(mix ** 2))
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                            "-c:a", "aac", "-b:a", "128k", str(m4a)], check=True)
            wav.unlink()
            print(f"{name}-{i}: {mix.shape[1] / SR:.1f}s {bands(mix)} mono {mono_drop:+.1f} dB, {m4a.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
