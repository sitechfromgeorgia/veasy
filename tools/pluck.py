"""Physically modelled plucked strings (extended Karplus-Strong digital waveguide).

Adapted from lemomo-ai/lemo-opuscar (MIT licence):
    Copyright (c) 2026 Lemomo AI
    Licensed under the MIT License.

Includes dedicated physical models and presets for traditional Georgian folk string instruments:
    1. Panduri (ფანდური) - 3-string Eastern/highland Georgian folk lute (bright wooden attack, mulberry resonance)
    2. Chonguri (ჩონგური) - 4-string Western Georgian silk-string lute (warm liquid decay, singing sustain)
plus classical/folk instruments: acoustic_guitar, nylon_guitar, banjo, harp, guqin, shamisen, kalimba.

Returns mono float32 @ SR (44100 Hz).
Enforces Veasy sound law: constant volume, no build-up, no ducking.
"""
import math
import pathlib
import re
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
_rng = np.random.default_rng(20261103)

# Note pitch parsing
_NOTE_MAP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(p):
    """Convert note name like 'D4', 'F#3', 'Bb2', or integer MIDI number to float MIDI pitch."""
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
    """Convert MIDI pitch to frequency in Hertz."""
    return 440.0 * 2.0 ** ((midi(p) - 69.0) / 12.0)


# ---------------------------------------------------------------- Waveguide simulation


def _simulate_loop(exc, D, g, p, ap, nap, buzz, thr):
    """Digital waveguide loop with fractional delay, one-pole lowpass loss, allpass dispersion, and bridge nonlinearity."""
    n = len(exc)
    max_d = int(np.max(D)) + 16
    M = 1
    while M < max_d:
        M *= 2
    buf = np.zeros(M, dtype=np.float32)
    out = np.zeros(n, dtype=np.float32)
    w = 0
    lp = 0.0
    st_x = np.zeros(8, dtype=np.float32)
    st_y = np.zeros(8, dtype=np.float32)

    for i in range(n):
        d = D[i]
        r = w - d
        ri = int(math.floor(r))
        fr = float(r - ri)

        # 3rd-order Lagrange fractional delay interpolation
        x0 = buf[(ri - 1) & (M - 1)]
        x1 = buf[ri & (M - 1)]
        x2 = buf[(ri + 1) & (M - 1)]
        x3 = buf[(ri + 2) & (M - 1)]

        c0 = -fr * (fr - 1.0) * (fr - 2.0) / 6.0
        c1 = (fr + 1.0) * (fr - 1.0) * (fr - 2.0) / 2.0
        c2 = -(fr + 1.0) * fr * (fr - 2.0) / 2.0
        c3 = (fr + 1.0) * fr * (fr - 1.0) / 6.0
        v = c0 * x0 + c1 * x1 + c2 * x2 + c3 * x3

        # One-pole lowpass loss filter
        lp = (1.0 - p) * v + p * lp
        s = g * lp

        # String stiffness: allpass dispersion stages
        for k in range(nap):
            y = ap * s + st_x[k] - ap * st_y[k]
            st_x[k] = s
            st_y[k] = y
            s = y

        # Bridge collision / buzz
        if buzz > 0 and s > thr:
            s = thr + (s - thr) * (1.0 - buzz) + buzz * thr * math.tanh((s - thr) / (thr + 1e-9)) * 0.3

        o = exc[i] + s
        buf[w & (M - 1)] = o
        out[i] = o
        w += 1

    return out


# Try compiling with numba if available for extra speed, otherwise use pure python simulation
try:
    from numba import njit
    _loop = njit(cache=True, fastmath=True)(_simulate_loop)
except ImportError:
    _loop = _simulate_loop


def _body_filter(x, modes, mix):
    """Simulate instrument body cavity resonances via parallel second-order bandpass filters."""
    if not modes or mix <= 0:
        return x
    y = np.zeros_like(x)
    for f, q, a in modes:
        if f >= SR / 2 * 0.95:
            continue
        bw = f / q
        lo = max(20.0, f - bw / 2.0)
        hi = min(SR / 2 * 0.98, f + bw / 2.0)
        sos = butter(1, [lo, hi], "bandpass", fs=SR, output="sos")
        y += a * sosfilt(sos, x)
    return x * (1.0 - mix) + y * mix * 2.5


# ---------------------------------------------------------------- Presets


PRESETS = {
    # 1. Georgian Panduri (ფანდური): 3-string lute, bright finger strum, mulberry wood resonance, short decay
    "panduri": dict(
        t60=2.0, damp=0.22, pos=0.12, exc="finger", nap=1, ap=-0.08, bright=0.7,
        body=[(180, 6, 1.0), (340, 7, 0.8), (720, 5, 0.5), (1450, 4, 0.3)], bmix=0.48, noise=0.04
    ),
    # 2. Georgian Chonguri (ჩონგური): 4-string lute (silk strings), warm liquid decay, singing sustain
    "chonguri": dict(
        t60=3.2, damp=0.32, pos=0.20, exc="finger", nap=1, ap=-0.04, bright=0.45,
        body=[(140, 5, 1.0), (280, 6, 0.85), (580, 5, 0.6), (1100, 4, 0.35)], bmix=0.55, noise=0.02
    ),
    # Classical / folk presets
    "acoustic_guitar": dict(
        t60=4.5, damp=0.3, pos=0.13, exc="pick", nap=2, ap=-0.15, bright=0.6,
        body=[(98, 8, 1), (204, 8, 0.9), (390, 6, 0.6), (560, 6, 0.5), (1050, 4, 0.3), (2400, 3, 0.15)],
        bmix=0.5, noise=0.03
    ),
    "nylon_guitar": dict(
        t60=3.5, damp=0.45, pos=0.15, exc="finger", nap=1, ap=-0.05, bright=0.4,
        body=[(98, 8, 1), (200, 8, 0.9), (390, 6, 0.6), (560, 6, 0.4)], bmix=0.5, noise=0.02
    ),
    "banjo": dict(
        t60=1.1, damp=0.1, pos=0.1, exc="pick", nap=3, ap=-0.2, bright=0.9,
        body=[(380, 4, 1), (850, 4, 0.8), (1700, 4, 0.7), (3100, 3, 0.5)], bmix=0.6, noise=0.04
    ),
    "harp": dict(
        t60=6.0, damp=0.4, pos=0.45, exc="finger", nap=1, ap=-0.03, bright=0.35,
        body=[(180, 5, 1), (380, 5, 0.7), (800, 4, 0.4)], bmix=0.4, noise=0.01
    ),
    "shamisen": dict(
        t60=1.4, damp=0.12, pos=0.06, exc="bachi", nap=2, ap=-0.1, bright=0.95, buzz=0.6, thr=0.18,
        body=[(260, 3, 1), (620, 3, 0.8), (1300, 3, 0.6), (2800, 3, 0.5)], bmix=0.5, noise=0.08
    ),
    "guqin": dict(
        t60=7.0, damp=0.45, pos=0.13, exc="finger", nap=1, ap=-0.05, bright=0.35,
        body=[(95, 5, 1), (210, 6, 0.8), (420, 6, 0.5), (820, 5, 0.35), (1500, 4, 0.2)], bmix=0.55, noise=0.02
    ),
    "kalimba": dict(modal=True),
}


# ---------------------------------------------------------------- Pluck synthesis


def pluck(inst, pitch, dur=2.0, vel=0.7, bend=None, vib=None, harmonic=False, trem=0.0):
    """Synthesize a plucked string note using physical modeling.

    Args:
        inst: preset name (e.g. 'panduri', 'chonguri', 'acoustic_guitar', 'nylon_guitar')
        pitch: note name (e.g. 'D4', 'G3') or MIDI pitch number
        dur: duration in seconds
        vel: velocity (0.0 to 1.0)
        bend: optional pitch bend [(time_sec, semitone_offset), ...]
        vib: optional vibrato tuple (rate_hz, depth_semitones, delay_sec)
        harmonic: synthesize flageolet natural harmonic
        trem: tremolo rate in Hz (e.g. 12 Hz for rolling strum)

    Returns:
        numpy float32 array @ SR (44100 Hz).
    """
    spec = PRESETS.get(inst, PRESETS["panduri"])
    if spec.get("modal"):
        return _modal_pluck(pitch, dur, vel)

    f0 = hz(pitch)
    if harmonic:
        f0 *= 2.0

    n_samples = int(dur * SR)
    t = np.arange(n_samples) / SR

    # Pitch trajectory (base f0 + bend + vibrato)
    f_track = np.full(n_samples, f0, dtype=np.float32)
    if bend:
        for b_time, b_semi in bend:
            mask = t >= b_time
            f_track[mask] = f0 * (2.0 ** (b_semi / 12.0))
    if vib:
        v_rate, v_depth, v_delay = vib
        v_mask = t >= v_delay
        v_lfo = np.sin(2 * np.pi * v_rate * (t - v_delay)) * (v_depth / 12.0)
        f_track[v_mask] *= 2.0 ** v_lfo[v_mask]

    # Delay length in samples: D = SR / f0
    D = SR / np.maximum(f_track, 20.0)

    # Physical parameters
    t60 = spec.get("t60", 2.5) * (200.0 / max(100.0, f0)) ** 0.5
    damp = spec.get("damp", 0.3)
    pos = spec.get("pos", 0.15)
    nap = spec.get("nap", 1)
    ap = spec.get("ap", -0.05)
    buzz = spec.get("buzz", 0.0)
    thr = spec.get("thr", 0.2)
    noise_mix = spec.get("noise", 0.03)

    # Loop gain g: 10^(-3 / (t60 * f0))
    g = float(10.0 ** (-3.0 / max(0.1, t60 * f0)))

    # Excitation impulse (triangular displacement pluck + pick noise)
    period_samples = int(SR / f0)
    exc = np.zeros(n_samples, dtype=np.float32)
    p_len = min(period_samples, n_samples)
    if p_len > 0:
        split = int(p_len * pos)
        if split > 0:
            exc[:split] = np.linspace(0, 1, split, endpoint=False)
        if p_len > split:
            exc[split:p_len] = np.linspace(1, 0, p_len - split)
        # Add slight plectrum noise
        noise = _rng.standard_normal(p_len).astype(np.float32) * noise_mix
        exc[:p_len] += noise

    # Scale excitation by velocity
    exc *= vel

    # Run waveguide simulation
    out = _loop(exc, D.astype(np.float32), g, damp, ap, nap, buzz, thr)

    # Body resonance
    body_modes = spec.get("body", [])
    bmix = spec.get("bmix", 0.4)
    out = _body_filter(out, body_modes, bmix)

    # Apply tremolo if specified (rapid rolling strum)
    if trem > 0:
        trem_lfo = 0.5 * (1.0 + np.sin(2 * np.pi * trem * t))
        out *= (0.3 + 0.7 * trem_lfo).astype(np.float32)

    # Smooth fade out at the very end to avoid pops
    fade_len = min(int(0.02 * SR), n_samples)
    if fade_len > 0:
        out[-fade_len:] *= np.linspace(1, 0, fade_len, dtype=np.float32)

    return out.astype(np.float32)


def _modal_pluck(pitch, dur, vel):
    """Modal synthesis fallback for kalimba/tines."""
    f0 = hz(pitch)
    n = int(dur * SR)
    t = np.arange(n) / SR
    partials = [(1.0, 1.0, 2.5), (2.75, 0.4, 1.5), (5.4, 0.15, 0.8), (8.9, 0.05, 0.4)]
    out = np.zeros(n, dtype=np.float32)
    for ratio, amp, decay in partials:
        freq = f0 * ratio
        if freq < SR / 2:
            out += amp * np.sin(2 * np.pi * freq * t) * np.exp(-t * decay * (f0 / 220.0))
    return (out * vel).astype(np.float32)


# ---------------------------------------------------------------- Musical helpers


def strum(inst, chord_notes, dur=3.0, speed=0.035, vel=0.7):
    """Play a rolled strum of chord notes across strings with slight timing stagger."""
    n_total = int(dur * SR)
    out = np.zeros(n_total, dtype=np.float32)
    for i, note in enumerate(chord_notes):
        offset = int(i * speed * SR)
        remaining = (n_total - offset) / SR
        if remaining > 0.1:
            # Vary velocity slightly per string
            v = vel * (0.85 + 0.15 * (i / max(1, len(chord_notes) - 1)))
            s = pluck(inst, note, dur=remaining, vel=v)
            place_len = min(len(s), n_total - offset)
            out[offset:offset + place_len] += s[:place_len]
    return out


def panduri_loop(bpm=96, bars=4, root="D4"):
    """Generate a steady Georgian Panduri folk accompaniment loop.

    Follows traditional Georgian rhythmic accompaniment (e.g. Kartli-Kakheti dance in 6/8 or 3/4).
    Tuning: G4, A4, C5 or D4, G4, A4.
    Enforces Veasy sound law: completely constant volume, seamless loop, no build-up.
    """
    root_m = midi(root)
    # Typical Panduri chords: I, IV, V, I (e.g. D -> G -> A -> D)
    chords = [
        [root_m, root_m + 5, root_m + 7],      # I (D, G, A)
        [root_m + 5, root_m + 7, root_m + 12],  # IV (G, A, D)
        [root_m + 7, root_m + 11, root_m + 14], # V (A, C#, E)
        [root_m, root_m + 5, root_m + 7],      # I
    ]

    sec_per_beat = 60.0 / bpm
    bar_dur = sec_per_beat * 4.0
    total_dur = bar_dur * bars
    n_samples = int(total_dur * SR)
    track = np.zeros(n_samples, dtype=np.float32)

    for bar_idx in range(bars):
        c_notes = chords[bar_idx % len(chords)]
        bar_start = bar_idx * bar_dur
        # Rhythmic strum pattern on beats 0, 1.5, 2.5, 3.0
        strum_beats = [0.0, 1.0, 2.0, 3.0]
        for beat in strum_beats:
            t_strum = bar_start + beat * sec_per_beat
            sample_idx = int(t_strum * SR)
            dur_rem = min(1.8, total_dur - t_strum)
            if dur_rem > 0.1:
                snd = strum("panduri", c_notes, dur=dur_rem, speed=0.025, vel=0.65)
                end_idx = min(sample_idx + len(snd), n_samples)
                track[sample_idx:end_idx] += snd[:end_idx - sample_idx]

    # Normalize to constant level (peak -3 dBFS, RMS steady)
    peak = np.max(np.abs(track)) + 1e-9
    track = track * (0.7 / peak)
    return track.astype(np.float32)
