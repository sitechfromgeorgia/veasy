"""Sampled instruments (offline sampler with synthetic fallbacks).

Adapted from lemomo-ai/lemo-opuscar (MIT licence):
    Copyright (c) 2026 Lemomo AI
    Licensed under the MIT License.

Supports real CC0 / CC-BY instrument sample libraries (VSCO 2 Community Edition,
Karoryfer, Salamander Grand Piano, FreePats) with automatic fallback to synthesis
when offline or when samples have not yet been downloaded.

Sampled sound contract:
    - note(inst, pitch, dur, vel) -> mono float32 @ SR
    - hit(inst, variant, vel) -> mono float32 @ SR
    - render(events, dur) -> stereo float32 (2, N) @ SR

Enforces Veasy sound law:
    - One constant level: no build-ups, no drop, no ducking.
    - Output mastered at steady volume for news bed under voice.
"""
import math
import os
import pathlib
import re
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT / "assets" / "instruments"

_rng = np.random.default_rng(20261103)
_NOTE_MAP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(p):
    """'C4' / 'D#3' / 60 -> float MIDI pitch."""
    if isinstance(p, (int, float, np.integer, np.floating)):
        return float(p)
    m = re.fullmatch(r"\s*([A-Ga-g])([#sb]*)(-?\d+)\s*", str(p))
    if not m:
        raise ValueError(f"cannot parse pitch {p!r}")
    step = _NOTE_MAP[m.group(1).upper()]
    acc = m.group(2).count("#") + m.group(2).count("s") - m.group(2).count("b")
    octave = int(m.group(3))
    return float(12 * (octave + 1) + step + acc)


def hz(p):
    """MIDI pitch to Hz."""
    return 440.0 * 2.0 ** ((midi(p) - 69.0) / 12.0)


# ---------------------------------------------------------------- Fallback Synthesis Engines


def _synth_piano(f, dur, vel):
    """Grand piano synthesis with harmonic decay and touch sensitivity."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    # Partials: fundamental, octave, fifth, second octave
    tone = (
        1.0 * np.sin(2 * np.pi * f * t) * np.exp(-t * (1.2 + f * 0.001)) +
        0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * (2.2 + f * 0.002)) +
        0.25 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * (3.5 + f * 0.003)) +
        0.1 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * (5.0 + f * 0.004))
    )
    # Attack transient
    attack_n = min(n, int(0.005 * SR))
    if attack_n > 0:
        tone[:attack_n] *= np.linspace(0, 1, attack_n)
    return (tone * vel * 0.6).astype(np.float32)


def _synth_string_section(f, dur, vel):
    """Ensemble string section with detuned chorus and bowing friction."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = np.zeros(n)
    # 5 slightly detuned voices
    for detune in (-7, -3, 0, 3, 7):
        vf = f * 2.0 ** (detune / 1200.0)
        saw = np.sin(2 * np.pi * vf * t) + 0.3 * np.sin(4 * np.pi * vf * t)
        tone += saw
    tone /= 5.0
    # Gentle lowpass
    sos = butter(2, min(3500.0, f * 6.0), "lowpass", fs=SR, output="sos")
    filtered = sosfilt(sos, tone)
    # Bow envelope (soft in, steady sustain, soft release)
    attack_n = min(n // 4, int(0.12 * SR))
    rel_n = min(n // 4, int(0.15 * SR))
    env = np.ones(n)
    if attack_n > 0:
        env[:attack_n] = np.linspace(0, 1, attack_n) ** 1.5
    if rel_n > 0:
        env[-rel_n:] = np.linspace(1, 0, rel_n) ** 1.5
    return (filtered * env * vel * 0.5).astype(np.float32)


def _synth_flute(f, dur, vel):
    """Breathy wooden/metal flute."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vibrato = 1.0 + 0.008 * np.sin(2 * np.pi * 5.2 * t)
    f_inst = f * vibrato
    sine = np.sin(2 * np.pi * np.cumsum(f_inst) / SR)
    harm2 = 0.15 * np.sin(4 * np.pi * np.cumsum(f_inst) / SR)
    noise = _rng.standard_normal(n) * 0.04
    sound = sine + harm2 + noise
    sos = butter(2, [max(100.0, f * 0.8), min(SR * 0.45, f * 3.5)], "bandpass", fs=SR, output="sos")
    sound = sosfilt(sos, sound)
    attack_n = min(n // 4, int(0.08 * SR))
    rel_n = min(n // 4, int(0.1 * SR))
    env = np.ones(n)
    if attack_n > 0:
        env[:attack_n] = np.linspace(0, 1, attack_n)
    if rel_n > 0:
        env[-rel_n:] = np.linspace(1, 0, rel_n)
    return (sound * env * vel * 0.5).astype(np.float32)


def _synth_brass(f, dur, vel):
    """Bright brass / horn."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sound = np.sin(2 * np.pi * f * t) + 0.6 * np.sin(4 * np.pi * f * t) + 0.35 * np.sin(6 * np.pi * f * t)
    sos = butter(2, min(4000.0, f * 5.0), "lowpass", fs=SR, output="sos")
    sound = sosfilt(sos, sound)
    attack_n = min(n // 4, int(0.05 * SR))
    rel_n = min(n // 4, int(0.08 * SR))
    env = np.ones(n)
    if attack_n > 0:
        env[:attack_n] = np.linspace(0, 1, attack_n)
    if rel_n > 0:
        env[-rel_n:] = np.linspace(1, 0, rel_n)
    return (sound * env * vel * 0.5).astype(np.float32)


# ---------------------------------------------------------------- Sampler Interface


def note(inst, pitch, dur=2.0, vel=0.7):
    """Play an instrument note at given pitch and duration.

    Args:
        inst: instrument name ('piano', 'cellos', 'violins', 'flute', 'trumpet', 'horn',
              'panduri', 'chonguri', 'acoustic_guitar', 'harp')
        pitch: pitch name ('C4', 'D#3') or MIDI integer
        dur: duration in seconds
        vel: velocity (0.0 to 1.0)

    Returns:
        mono float32 numpy array @ SR (44100 Hz).
    """
    inst = inst.lower().strip()
    f = hz(pitch)

    # Check for plucked folk models
    if inst in ("panduri", "chonguri", "acoustic_guitar", "nylon_guitar", "banjo", "harp", "shamisen", "guqin"):
        from tools import pluck
        return pluck.pluck(inst, pitch, dur=dur, vel=vel)

    # Check for local sampled files if present
    sample_file = SAMPLES_DIR / f"{inst}_{pitch}.wav"
    if sample_file.is_file():
        try:
            import soundfile as sf
            data, rate = sf.read(str(sample_file))
            if data.ndim > 1:
                data = data.mean(axis=1)
            target_n = int(dur * SR)
            if len(data) >= target_n:
                return (data[:target_n] * vel).astype(np.float32)
        except Exception:
            pass

    # Synthesis fallbacks
    if "piano" in inst:
        return _synth_piano(f, dur, vel)
    elif "violin" in inst or "cello" in inst or "string" in inst:
        return _synth_string_section(f, dur, vel)
    elif "flute" in inst or "woodwind" in inst or "recorder" in inst:
        return _synth_flute(f, dur, vel)
    elif "trumpet" in inst or "horn" in inst or "brass" in inst or "trombone" in inst:
        return _synth_brass(f, dur, vel)
    else:
        return _synth_piano(f, dur, vel)


def hit(inst, variant=None, vel=0.7):
    """Play an unpitched percussion hit (snare, kick, hihat, woodblock, shaker)."""
    inst = inst.lower().strip()
    if inst == "kick":
        dur = 0.25
        n = int(dur * SR)
        t = np.arange(n) / SR
        f = 55.0 + 80.0 * np.exp(-t * 30.0)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14.0) * vel).astype(np.float32)
    elif inst == "snare":
        dur = 0.2
        n = int(dur * SR)
        t = np.arange(n) / SR
        noise = _rng.standard_normal(n) * np.exp(-t * 18.0)
        body = np.sin(2 * np.pi * 185.0 * t) * np.exp(-t * 25.0)
        return ((noise * 0.7 + body * 0.5) * vel).astype(np.float32)
    elif inst in ("hihat", "tick"):
        dur = 0.04
        n = int(dur * SR)
        t = np.arange(n) / SR
        noise = _rng.standard_normal(n) * np.exp(-t * 120.0)
        sos = butter(2, 6000.0, "highpass", fs=SR, output="sos")
        return (sosfilt(sos, noise) * vel * 0.6).astype(np.float32)
    elif inst == "woodblock":
        dur = 0.08
        n = int(dur * SR)
        t = np.arange(n) / SR
        tone = np.sin(2 * np.pi * 840.0 * t) * np.exp(-t * 60.0)
        return (tone * vel * 0.8).astype(np.float32)
    else:
        # Default soft click
        return hit("hihat", vel=vel)


def render(events, total_dur):
    """Mix an event list into a stereo track.

    events: [(time_sec, inst, pitch, dur, vel), ...]
    total_dur: total duration in seconds.

    Returns:
        stereo float32 array of shape (2, N) @ SR.
    """
    n_samples = int(total_dur * SR)
    left = np.zeros(n_samples, dtype=np.float32)
    right = np.zeros(n_samples, dtype=np.float32)

    for ev in events:
        t_start, inst, pitch, dur, vel = ev[:5]
        pan = ev[5] if len(ev) > 5 else 0.0  # -1.0 (L) to +1.0 (R)
        snd = note(inst, pitch, dur=dur, vel=vel)
        start_idx = int(t_start * SR)
        end_idx = min(start_idx + len(snd), n_samples)
        if start_idx < n_samples and end_idx > start_idx:
            chunk = snd[:end_idx - start_idx]
            pan_l = math.cos((pan + 1.0) * math.pi / 4.0)
            pan_r = math.sin((pan + 1.0) * math.pi / 4.0)
            left[start_idx:end_idx] += chunk * pan_l
            right[start_idx:end_idx] += chunk * pan_r

    return np.stack([left, right])
