"""Veasy's sound effects, synthesized in code like the music (ours outright: no licence, no Content ID claims).

  python tools/compose_sfx.py [out_dir]      needs numpy + scipy; writes assets/sfx/<name>.wav (48 kHz, mono)

Six short accents (and the `meaning` set below), each a few hundredths of a second to a third of a second:

  click   a dry tap: a plain cut between scenes
  pop     a soft round pop: a chip or a mark lands
  whoosh  a short air sweep, symmetric (no build-up): a moving cut between scenes
  tick    a clock tick (the music's own clock): a number counting up
  thud    a soft low knock with its harmonics (phones play no sub): a number or a card settling
  blip    a short two-partial meter blip: a bar or a cell of a chart filling

The `meaning` set (sfx option `meaning`, tt_shorts/sfx.py), same rules:

  impact     the film's one main sound: a low knock with a short tail, on the main moment
  obj-wood   knock           obj-glass  ting            obj-metal  clank
  obj-paper  rustle          obj-water  drop            obj-soft   muffled thump
             (a story's object gets one of these, chosen by code: sfx.object_sound)

Rules, the same as the music's (the owner's ear): every sound is short and at one level (each is levelled to the
same loudness over its active part, its peak at most -3 dBFS, so no effect is louder than another), nothing rises
over seconds (a whoosh is
symmetric, not a riser), nothing lives under 120 Hz, and the output is deterministic (a fixed seed per sound: the
same files on every machine, so a render is the same twice). The mix places them under the voice at one constant
level, with no ducking (tt_shorts/sfx.py, props.mix_audio).
"""
import pathlib
import sys
import wave
import zlib

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
PEAK = 0.7  # every file's peak (-3 dBFS): sfx.py sets the level in the mix
RMS_DB = -20.0  # every file's loudness over its own active part, so no effect stands out
NAMES = ("click", "pop", "whoosh", "tick", "thud", "blip", "impact",
         "obj-wood", "obj-glass", "obj-metal", "obj-paper", "obj-water", "obj-soft")


def _t(seconds):
    return np.arange(int(seconds * SR)) / SR


def _rng(name):
    return np.random.default_rng(zlib.crc32(name.encode()))  # a fixed seed per sound


def _env(n, attack, release):
    """A fast attack, an exponential release; seconds."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(0, t - attack) / max(release, 1e-4))


def _band(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def _high(x, f=120, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def click():
    n = int(0.04 * SR)
    noise = _band(_rng("click").standard_normal(n), 1800, 6000) * _env(n, 0.0005, 0.004)
    t = _t(0.04)
    tone = np.sin(2 * np.pi * 2400 * t) * _env(n, 0.0005, 0.006) * 0.5
    return noise + tone


def pop():
    t = _t(0.09)
    f = 340 + 560 * np.exp(-t / 0.012)  # a quick pitch drop: a round pop
    phase = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(phase) + 0.25 * np.sin(2 * phase)) * _env(len(t), 0.002, 0.022)


def whoosh():
    dur = 0.34
    n = int(dur * SR)
    noise = _rng("whoosh").standard_normal(n)
    t = np.arange(n) / n
    out = np.zeros(n)
    hop = 512
    for k in range(0, n, hop):  # a band that sweeps up and back down: air moving past, then gone
        c = 500 + 2600 * np.sin(np.pi * min(1.0, (k + hop / 2) / n)) ** 1.5
        seg = noise[max(0, k - 2048):k + hop]
        out[k:k + hop] = _band(seg, c * 0.6, c * 1.5)[-len(out[k:k + hop]):]
    shape = np.sin(np.pi * t) ** 2  # symmetric: as long coming as going, never a riser
    return out * shape


def tick():
    n = int(0.03 * SR)
    t = _t(0.03)
    tone = np.sin(2 * np.pi * 1800 * t) * _env(n, 0.0003, 0.004)
    noise = _band(_rng("tick").standard_normal(n), 3000, 9000) * _env(n, 0.0002, 0.0015) * 0.6
    return tone + noise


def thud():
    t = _t(0.2)
    f = 150 + 60 * np.exp(-t / 0.02)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase)  # harmonics carry it on a phone
    knock = _band(_rng("thud").standard_normal(len(t)), 300, 1500) * _env(len(t), 0.0005, 0.006) * 0.4
    return body * _env(len(t), 0.002, 0.05) + knock


def blip():
    t = _t(0.07)
    n = len(t)
    return (np.sin(2 * np.pi * 1320 * t) + 0.35 * np.sin(2 * np.pi * 1980 * t)) * _env(n, 0.002, 0.018)


def impact():
    t = _t(0.38)
    f = 110 + 90 * np.exp(-t / 0.03)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = sum(a * np.sin(k * phase) for k, a in ((1, 1.0), (2, 0.7), (3, 0.45), (4, 0.25)))  # harmonics: a phone has no sub
    knock = _band(_rng("impact").standard_normal(len(t)), 250, 2500) * _env(len(t), 0.0005, 0.01) * 0.5
    return body * _env(len(t), 0.002, 0.11) + knock


def obj_wood():
    t = _t(0.16)
    n = len(t)
    tone = (np.sin(2 * np.pi * 430 * t) + 0.6 * np.sin(2 * np.pi * 690 * t)) * _env(n, 0.0005, 0.03)
    return tone + _band(_rng("wood").standard_normal(n), 800, 2600) * _env(n, 0.0005, 0.008) * 0.5


def obj_glass():
    t = _t(0.3)
    n = len(t)
    ring = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((2637, 1.0), (3951, 0.5), (5300, 0.25)))
    return ring * _env(n, 0.0004, 0.09)


def obj_metal():
    t = _t(0.26)
    n = len(t)
    ring = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in
               ((880, 1.0, 0.08), (1243, 0.7, 0.06), (1789, 0.5, 0.05), (2410, 0.3, 0.04)))
    return ring * _env(n, 0.0003, 0.2) + _band(_rng("metal").standard_normal(n), 2000, 7000) * _env(n, 0.0002, 0.004) * 0.4


def obj_paper():
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    bursts = sum(np.exp(-((t - c) / 0.018) ** 2) for c in (0.03, 0.085, 0.14))  # three small crumples
    return _band(_rng("paper").standard_normal(n), 2500, 9000) * bursts


def obj_water():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for start, amp in ((0.0, 1.0), (0.09, 0.45)):  # a drop, then a smaller one
        u = np.maximum(0, t - start)
        f = 500 + 900 * (1 - np.exp(-u / 0.02))  # the pitch rises as a drop's bubble closes
        out += amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.where(t >= start, np.exp(-u / 0.035), 0)
    return out


def obj_soft():
    t = _t(0.14)
    n = len(t)
    body = np.sin(2 * np.pi * 280 * t) * _env(n, 0.002, 0.035)
    return body + sosfilt(butter(2, 900, btype="low", fs=SR, output="sos"), _rng("soft").standard_normal(n)) * _env(n, 0.001, 0.02) * 0.6


def level(x):
    """Every sound to the same loudness over its active part, its peak at most PEAK; a 0.5 ms fade in (the attack
    stays) and a 3 ms fade out, so no file starts or ends with a step."""
    x = _high(np.asarray(x, dtype=float))
    fin, fout = int(0.0005 * SR), int(0.003 * SR)
    x[:fin] *= np.linspace(0, 1, fin)
    x[-fout:] *= np.linspace(1, 0, fout)
    active = np.abs(x) > 0.05 * np.max(np.abs(x))
    rms = np.sqrt(np.mean(x[active] ** 2)) if active.any() else 1.0
    x = x * (10 ** (RMS_DB / 20) / max(rms, 1e-9))
    return x / max(1.0, np.max(np.abs(x)) / PEAK)


SOUNDS = {"click": click, "pop": pop, "whoosh": whoosh, "tick": tick, "thud": thud, "blip": blip, "impact": impact,
          "obj-wood": obj_wood, "obj-glass": obj_glass, "obj-metal": obj_metal, "obj-paper": obj_paper,
          "obj-water": obj_water, "obj-soft": obj_soft}


def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main(out=None):
    out = pathlib.Path(out or pathlib.Path(__file__).resolve().parent.parent / "assets" / "sfx")
    out.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        x = level(SOUNDS[name]())
        write(out / f"{name}.wav", x)
        print(f"{name}: {len(x) / SR:.2f}s, peak {20 * np.log10(np.max(np.abs(x))):.1f} dBFS")
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
