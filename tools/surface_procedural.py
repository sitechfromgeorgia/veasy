"""Procedural, seamless greyscale height maps for Veasy lit surfaces (no image model, no network).

Every material is a pure function ``fn(seed, n) -> float32 (n, n) in [0, 1]`` built from periodic noise, so a tile
wraps by construction and the same seed gives the same bytes. numpy only.

Primitives (all periodic on the n x n torus):
  spectral()   fBm-like noise by shaping white noise in the Fourier domain (isotropic or stretched)
  worley()     F1 / F2 / cell id of a jittered cell grid, wrapped
  warp()       domain warping by bilinear resampling with wrap
  stripes()    integer-cycle bands (strata, flutes, ripples)
  reaction_diffusion()  Gray-Scott on a torus
  weave()      over/under thread patterns with slubs
  scratches()  random wrapped line segments
  erode()      a thermal-erosion-like smoothing of steep slopes
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

DEFAULT_N = 512


# ---------------------------------------------------------------- primitives

def _rng(seed: int, salt: int = 0) -> np.random.Generator:
    return np.random.default_rng([int(seed) & 0xFFFFFFFF, salt])


def norm01(a: np.ndarray, clip: float = 0.5) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    lo, hi = np.percentile(a, (clip, 100.0 - clip))
    if hi <= lo:
        return np.zeros(a.shape, dtype=np.float32)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def spectral(seed: int, n: int, beta: float = 2.0, sx: float = 1.0, sy: float = 1.0,
             fmin: float = 1.0, fmax: float | None = None, salt: int = 0) -> np.ndarray:
    """Periodic noise with power spectrum ~ 1/f^beta. sx/sy > 1 stretch features along x/y."""
    rng = _rng(seed, salt)
    white = rng.standard_normal((n, n))
    spec = np.fft.fft2(white)
    k = np.fft.fftfreq(n) * n
    kx, ky = np.meshgrid(k, k)
    f = np.sqrt((kx * sx) ** 2 + (ky * sy) ** 2)
    f[0, 0] = 1.0
    amp = f ** (-beta / 2.0)
    amp[f < fmin] = 0.0
    if fmax is not None:
        amp[f > fmax] = 0.0
    amp[0, 0] = 0.0
    return norm01(np.fft.ifft2(spec * amp).real)


def warp(img: np.ndarray, dx: np.ndarray, dy: np.ndarray, amount: float) -> np.ndarray:
    """Resample img at (x + amount*(dx-.5), y + amount*(dy-.5)) with wrap and bilinear filtering (amount in px)."""
    n = img.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    sx = xx + amount * (dx - 0.5)
    sy = yy + amount * (dy - 0.5)
    x0 = np.floor(sx).astype(np.int64)
    y0 = np.floor(sy).astype(np.int64)
    fx = sx - x0
    fy = sy - y0
    x0 %= n
    y0 %= n
    x1 = (x0 + 1) % n
    y1 = (y0 + 1) % n
    a = img[y0, x0] * (1 - fx) + img[y0, x1] * fx
    b = img[y1, x0] * (1 - fx) + img[y1, x1] * fx
    return (a * (1 - fy) + b * fy).astype(np.float32)


def worley(seed: int, n: int, cells: int, jitter: float = 1.0, aniso: float = 1.0, salt: int = 1):
    """Returns (F1, F2, cell_id) in pixel units; cells x cells grid wrapped. aniso>1 stretches cells along x."""
    rng = _rng(seed, salt)
    pts = rng.random((cells, cells, 2))
    pts = 0.5 + (pts - 0.5) * jitter
    cs = n / cells
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx = np.floor(xx / cs).astype(np.int64)
    cy = np.floor(yy / cs).astype(np.int64)
    f1 = np.full((n, n), 1e9, dtype=np.float32)
    f2 = np.full((n, n), 1e9, dtype=np.float32)
    ident = np.zeros((n, n), dtype=np.int64)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            gx = cx + ox
            gy = cy + oy
            px = (gx + pts[gy % cells, gx % cells, 0]) * cs
            py = (gy + pts[gy % cells, gx % cells, 1]) * cs
            ddx = (xx - px) / aniso
            ddy = yy - py
            d = np.sqrt(ddx * ddx + ddy * ddy)
            better = d < f1
            second = (~better) & (d < f2)
            f2 = np.where(better, f1, np.where(second, d, f2))
            ident = np.where(better, (gy % cells) * cells + (gx % cells), ident)
            f1 = np.where(better, d, f1)
    return f1, f2, ident


def cell_values(seed: int, cells: int, ident: np.ndarray, salt: int = 2) -> np.ndarray:
    return _rng(seed, salt).random(cells * cells).astype(np.float32)[ident]


def stripes(n: int, cycles: int, axis: int = 0, phase: np.ndarray | None = None) -> np.ndarray:
    """Integer-cycle sine bands in [0,1]; phase is an optional per-pixel offset in radians (periodic)."""
    t = np.arange(n, dtype=np.float64) * (2 * np.pi * cycles / n)
    base = np.tile(t[:, None], (1, n)) if axis == 0 else np.tile(t[None, :], (n, 1))
    if phase is not None:
        base = base + phase
    return (0.5 + 0.5 * np.sin(base)).astype(np.float32)


def scratches(seed: int, n: int, count: int, length: int, angle: float, spread: float = 0.1,
              salt: int = 3) -> np.ndarray:
    """Thin wrapped line segments accumulated into a field in [0,1] (1 = scratched)."""
    rng = _rng(seed, salt)
    out = np.zeros((n, n), dtype=np.float32)
    for _ in range(count):
        x = rng.integers(0, n)
        y = rng.integers(0, n)
        a = angle + rng.normal(0, spread)
        L = int(length * (0.4 + rng.random()))
        t = np.arange(L)
        xs = (x + t * np.cos(a)).astype(np.int64) % n
        ys = (y + t * np.sin(a)).astype(np.int64) % n
        fade = np.sin(np.pi * t / max(L - 1, 1)).astype(np.float32)
        out[ys, xs] = np.maximum(out[ys, xs], fade * (0.5 + 0.5 * rng.random()))
    return out


def blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """Periodic gaussian blur by FFT."""
    n = a.shape[0]
    k = np.fft.fftfreq(n) * n
    kx, ky = np.meshgrid(k, k)
    g = np.exp(-2 * (np.pi * sigma / n) ** 2 * (kx ** 2 + ky ** 2))
    return np.fft.ifft2(np.fft.fft2(a) * g).real.astype(np.float32)


def reaction_diffusion(seed: int, n: int, feed: float, kill: float, steps: int = 3000, size: int = 128) -> np.ndarray:
    """Gray-Scott on a torus at size x size, then resampled up by periodic FFT interpolation."""
    rng = _rng(seed, 7)
    u = np.ones((size, size))
    v = np.zeros((size, size))
    for _ in range(14):
        cx, cy = rng.integers(0, size, 2)
        r = 4
        ys = (np.arange(cy - r, cy + r) % size)[:, None]
        xs = (np.arange(cx - r, cx + r) % size)[None, :]
        u[ys, xs] = 0.5
        v[ys, xs] = 0.25
    v += 0.02 * rng.random((size, size))
    du, dv = 0.16, 0.08

    def lap(a):
        return (np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1) - 4 * a)

    for _ in range(steps):
        uvv = u * v * v
        u = u + du * lap(u) - uvv + feed * (1 - u)
        v = v + dv * lap(v) + uvv - (feed + kill) * v
    spec = np.fft.fftshift(np.fft.fft2(v))
    pad = (n - size) // 2
    big = np.zeros((n, n), dtype=complex)
    big[pad:pad + size, pad:pad + size] = spec
    up = np.fft.ifft2(np.fft.ifftshift(big)).real * (n / size) ** 2
    return norm01(up)


def weave(n: int, threads: int, over: int, thick_x: np.ndarray, thick_y: np.ndarray, gap: float = 0.12) -> np.ndarray:
    """Plain/twill weave height: thread cross-section bumps, alternating over/under. thick_* modulate thread height."""
    cell = n / threads
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    u = (xx / cell) % 1.0
    v = (yy / cell) % 1.0
    ix = np.floor(xx / cell).astype(np.int64)
    iy = np.floor(yy / cell).astype(np.int64)
    warp_on_top = ((ix + iy // 1 * over) % 2) == 0
    # cross-sections: a thread running along y has a bump profile across x, and vice versa
    prof_x = np.sin(np.pi * np.clip(u, 0, 1)) ** 0.8  # vertical thread bump across x
    prof_y = np.sin(np.pi * np.clip(v, 0, 1)) ** 0.8
    vert = prof_x * (0.55 + 0.45 * np.sin(np.pi * v)) * thick_y
    horiz = prof_y * (0.55 + 0.45 * np.sin(np.pi * u)) * thick_x
    h = np.where(warp_on_top, 0.55 + 0.45 * vert, 0.25 + 0.45 * horiz)
    h = h - gap * (1 - prof_x * prof_y)
    return norm01(h)


def erode(h: np.ndarray, iters: int = 20, talus: float = 0.02, rate: float = 0.4) -> np.ndarray:
    """Thermal erosion on the torus: move material from a cell to lower neighbours where the slope exceeds talus."""
    h = h.astype(np.float64).copy()
    for _ in range(iters):
        delta = np.zeros_like(h)
        for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
            nb = np.roll(h, sh, ax)
            d = h - nb
            m = np.where(d > talus, (d - talus) * rate * 0.25, 0.0)
            delta -= m
            delta += np.roll(m, -sh, ax)
        h += delta
    return h.astype(np.float32)


# ---------------------------------------------------------------- materials

def slate(seed, n):
    cells = 6
    f1, f2, ident = worley(seed, n, cells, 0.9, aniso=1.6)
    lvl = cell_values(seed, cells, ident)
    edge = smoothstep(0.0, 12.0, f2 - f1)
    cleave = spectral(seed, n, 2.6, sx=3.0, sy=1.0, fmin=2, fmax=60, salt=11)
    fine = spectral(seed, n, 1.2, fmin=20, salt=12)
    h = 0.55 * lvl + 0.25 * cleave + 0.25 * edge * (0.5 + lvl) + 0.05 * fine
    return norm01(erode(norm01(h), 4, 0.03))


def sandstone(seed, n):
    w1 = spectral(seed, n, 2.4, fmin=1, fmax=8, salt=21)
    w2 = spectral(seed, n, 2.4, fmin=1, fmax=8, salt=22)
    ph = spectral(seed, n, 2.0, sx=4.0, sy=1.0, fmin=1, fmax=10, salt=23)
    bands = stripes(n, 9, axis=0, phase=(ph - 0.5) * 7.0)
    bands2 = stripes(n, 23, axis=0, phase=(ph - 0.5) * 5.0 + 1.0)
    grain = spectral(seed, n, 0.4, fmin=60, salt=24)
    pits = spectral(seed, n, 1.0, fmin=10, fmax=80, salt=25)
    h = 0.35 * bands + 0.12 * bands2 + 0.28 * grain + 0.25 * (pits > 0.82) * pits
    h = warp(norm01(h), w1, w2, 14.0)
    return norm01(erode(h, 8, 0.02))


def cracked_earth(seed, n):
    cells = 9
    f1, f2, ident = worley(seed, n, cells, 1.0)
    w1 = spectral(seed, n, 2.0, fmin=2, fmax=14, salt=31)
    w2 = spectral(seed, n, 2.0, fmin=2, fmax=14, salt=32)
    f1w = warp(f1, w1, w2, 22.0)
    f2w = warp(f2, w1, w2, 22.0)
    gap = f2w - f1w
    crack = smoothstep(0.0, 7.0, gap)
    curl = np.clip(f1w / (n / cells * 0.7), 0, 1)  # plate edges curl up, centre sags
    base = cell_values(seed, cells, ident) * 0.15
    dust = spectral(seed, n, 1.4, fmin=25, salt=33)
    h = crack * (0.62 + 0.25 * curl ** 1.5 + base) + 0.1 * dust * crack
    return norm01(h)


def ice(seed, n):
    a = spectral(seed, n, 3.2, fmin=1, fmax=9, salt=41)
    b = spectral(seed, n, 3.2, fmin=1, fmax=9, salt=42)
    base = warp(spectral(seed, n, 3.0, fmin=1, fmax=7, salt=43), a, b, 40.0)
    f1, f2, _ = worley(seed, n, 4, 1.0, salt=44)
    wa = spectral(seed, n, 2.4, fmin=2, fmax=20, salt=45)
    wb = spectral(seed, n, 2.4, fmin=2, fmax=20, salt=46)
    fault = warp(f2 - f1, wa, wb, 26.0)
    cracks = 1.0 - smoothstep(0.0, 2.2, fault)
    f1b, _, _ = worley(seed, n, 22, 1.0, salt=47)
    bubbles = smoothstep(7.0, 0.0, f1b) * (spectral(seed, n, 0.3, fmin=1, salt=48) > 0.78)
    h = 0.75 * base - 0.45 * cracks + 0.25 * blur(bubbles.astype(np.float32), 1.0) * 3
    return norm01(blur(h, 0.8))


def bark(seed, n):
    w1 = spectral(seed, n, 2.4, sx=1.0, sy=1.0, fmin=1, fmax=12, salt=51)
    w2 = spectral(seed, n, 2.4, fmin=1, fmax=12, salt=52)
    ridge = spectral(seed, n, 1.6, sx=1.0, sy=9.0, fmin=2, fmax=70, salt=53)
    ridged = 1.0 - np.abs(2 * ridge - 1)
    big = spectral(seed, n, 2.0, sx=1.0, sy=8.0, fmin=2, fmax=16, salt=54)
    fis = warp(norm01(ridged ** 3), w1, w2, 24.0)
    h = 0.45 * big + 0.55 * (1 - fis)
    h = h * (0.8 + 0.2 * spectral(seed, n, 1.2, fmin=20, salt=55))
    return norm01(h)


def felt(seed, n):
    fibres = scratches(seed, n, 9000, 20, 0.0, spread=3.0, salt=61)
    h = blur(fibres, 1.3) + 0.15 * spectral(seed, n, 0.8, fmin=40, salt=62)
    h = h + 0.9 * spectral(seed, n, 2.6, fmin=2, fmax=18, salt=63)
    return norm01(blur(h, 0.8))


def linen(seed, n):
    t = 64
    sx = spectral(seed, n, 2.0, sx=14.0, sy=1.0, fmin=1, fmax=40, salt=71)
    sy = spectral(seed, n, 2.0, sx=1.0, sy=14.0, fmin=1, fmax=40, salt=72)
    thick_x = 0.8 + 0.4 * sx
    thick_y = 0.8 + 0.4 * sy
    h = weave(n, t, 1, thick_x, thick_y, gap=0.15)
    h = h + 0.12 * spectral(seed, n, 1.0, fmin=30, salt=73)
    return norm01(h)


def corrugated_card(seed, n):
    ph = spectral(seed, n, 2.6, sx=1.0, sy=3.0, fmin=1, fmax=6, salt=81)
    flutes = stripes(n, 14, axis=1, phase=(ph - 0.5) * 0.7)
    flutes = flutes ** 0.8
    fibre = scratches(seed, n, 5000, 26, 0.0, spread=0.8, salt=82)
    crush = spectral(seed, n, 2.4, fmin=1, fmax=10, salt=83)
    h = 0.7 * flutes + 0.15 * blur(fibre, 0.7) * 2 + 0.2 * crush * smoothstep(0.55, 0.9, crush)
    return norm01(h)


def brushed_steel(seed, n):
    g1 = spectral(seed, n, 0.6, sx=40.0, sy=1.0, fmin=2, salt=91)
    g2 = spectral(seed, n, 1.0, sx=14.0, sy=1.0, fmin=2, salt=92)
    ph = spectral(seed, n, 3.0, fmin=1, fmax=4, salt=93)
    sc = scratches(seed, n, 60, 220, 0.0, spread=0.01, salt=94)
    h = 0.5 * g1 + 0.35 * g2 + 0.2 * blur(sc, 0.6) * 3
    return norm01(warp(h, ph, ph, 6.0))


def rust(seed, n):
    base = spectral(seed, n, 2.6, fmin=1, fmax=16, salt=101)
    blis = np.clip((base - 0.5) * 3.0, 0, 1)
    pit = spectral(seed, n, 1.1, fmin=12, fmax=140, salt=102)
    f1, _, _ = worley(seed, n, 30, 1.0, salt=103)
    crater = smoothstep(9.0, 0.0, f1) * (spectral(seed, n, 0.4, fmin=1, salt=104) > 0.7)
    h = 0.5 * blis + 0.35 * pit * (0.4 + blis) - 0.5 * blur(crater.astype(np.float32), 1.2) * 3
    flake = spectral(seed, n, 1.8, fmin=6, fmax=60, salt=105)
    h = h + 0.2 * (flake > 0.7) * flake
    return norm01(erode(norm01(h), 3, 0.05))


def lead(seed, n):
    low = spectral(seed, n, 3.0, fmin=1, fmax=8, salt=111)
    sc = scratches(seed, n, 120, 50, 0.0, spread=3.1416, salt=112)
    dents = spectral(seed, n, 2.0, fmin=6, fmax=40, salt=113)
    h = 0.6 * low + 0.3 * dents - 0.12 * blur(sc, 0.6) * 3
    return norm01(blur(h, 0.9))


def wax(seed, n):
    a = spectral(seed, n, 3.4, fmin=1, fmax=6, salt=121)
    b = spectral(seed, n, 3.4, fmin=1, fmax=6, salt=122)
    drips = spectral(seed, n, 3.0, sx=1.0, sy=6.0, fmin=1, fmax=10, salt=123)
    base = warp(drips, a, b, 70.0)
    ridge = 1.0 - np.abs(2 * warp(drips, a, b, 90.0) - 1)
    h = 0.6 * base + 0.5 * ridge ** 4 + 0.3 * spectral(seed, n, 4.0, fmin=1, fmax=4, salt=124)
    return norm01(blur(h, 2.2))


def ceramic_glaze(seed, n):
    orange = spectral(seed, n, 2.8, fmin=3, fmax=30, salt=131)
    f1, f2, _ = worley(seed, n, 14, 1.0, salt=132)
    wa = spectral(seed, n, 2.0, fmin=3, fmax=24, salt=133)
    wb = spectral(seed, n, 2.0, fmin=3, fmax=24, salt=134)
    gap = warp(f2 - f1, wa, wb, 16.0)
    craze = 1.0 - smoothstep(0.0, 1.6, gap)
    swell = spectral(seed, n, 3.4, fmin=1, fmax=5, salt=135)
    pin = spectral(seed, n, 0.5, fmin=1, salt=136) > 0.9985
    h = 0.55 * swell + 0.2 * orange - 0.3 * craze - 0.4 * blur(pin.astype(np.float32), 1.5) * 8
    return norm01(blur(h, 0.7))


def rippled_sand(seed, n):
    ph = spectral(seed, n, 3.0, fmin=1, fmax=5, salt=141)
    ph2 = spectral(seed, n, 2.4, fmin=1, fmax=8, salt=142)
    r = stripes(n, 12, axis=0, phase=(ph - 0.5) * 12.0 + 0.8 * np.sin(np.arange(n) * 2 * np.pi / n * 3)[None, :])
    asym = r ** 1.6  # sharp crests, wide troughs
    grain = spectral(seed, n, 0.5, fmin=60, salt=143)
    r2 = stripes(n, 37, axis=0, phase=(ph2 - 0.5) * 8.0) * 0.12
    h = asym + r2 + 0.1 * grain
    return norm01(h)


def tooled_leather(seed, n):
    f1, f2, ident = worley(seed, n, 36, 0.9, salt=151)
    pebble = np.sqrt(np.clip(1.0 - (f1 / (n / 36 * 0.75)) ** 2, 0, 1))
    pebble = pebble * (0.8 + 0.2 * cell_values(seed, 36, ident))
    cr = spectral(seed, n, 1.8, fmin=2, fmax=40, salt=152)
    creases = (1.0 - np.abs(2 * cr - 1)) ** 6
    wa = spectral(seed, n, 2.4, fmin=1, fmax=8, salt=153)
    h = pebble - 0.55 * creases
    h = h + 0.25 * wa
    return norm01(h)


def cork(seed, n):
    f1, f2, ident = worley(seed, n, 40, 1.0, salt=161)
    chunk = cell_values(seed, 40, ident)
    pores = spectral(seed, n, 0.5, fmin=1, salt=162) > 0.86
    pore = blur(pores.astype(np.float32), 1.6)
    f1b, _, _ = worley(seed, n, 55, 1.0, salt=163)
    pit = smoothstep(7.0, 1.0, f1b) * (spectral(seed, n, 0.3, fmin=1, salt=164) > 0.72)
    h = 0.5 * chunk + 0.2 * smoothstep(0, 8, f2 - f1) - 0.7 * blur(pit.astype(np.float32), 1.0) * 2 - pore * 1.5
    h = h + 0.15 * spectral(seed, n, 1.4, fmin=8, salt=165)
    return norm01(h)


def basket_weave(seed, n):
    reps = 8
    cell = n // reps
    yy, xx = np.mgrid[0:n, 0:n]
    bx, by = xx // cell, yy // cell
    horizontal = ((bx + by) % 2) == 0
    u = (xx % cell) / cell
    v = (yy % cell) / cell
    slats = 4
    ph = np.where(horizontal, v, u) * slats % 1.0
    along = np.where(horizontal, u, v)
    bump = np.sin(np.pi * ph) ** 0.7 * (0.75 + 0.25 * np.sin(np.pi * along))
    lift = np.where(horizontal, 0.0, 0.18)
    jit = spectral(seed, n, 1.6, fmin=2, fmax=50, salt=171)
    h = bump * 0.6 + lift + 0.25 * jit * bump
    fibre = scratches(seed, n, 3000, 40, 0.0, spread=3.1416, salt=172)
    h = h + 0.1 * blur(fibre, 0.7) * 2
    return norm01(h)


def pumice(seed, n):
    base = spectral(seed, n, 2.4, fmin=2, fmax=24, salt=181)
    f1, _, _ = worley(seed, n, 18, 1.0, salt=182)
    f2b, _, _ = worley(seed, n, 44, 1.0, salt=183)
    big = smoothstep(16.0, 6.0, f1) * (spectral(seed, n, 0.3, fmin=1, salt=184) > 0.45)
    small = smoothstep(8.0, 2.0, f2b) * (spectral(seed, n, 0.3, fmin=1, salt=185) > 0.5)
    h = 0.6 * base + 0.3 * spectral(seed, n, 1.2, fmin=20, salt=186) - 1.1 * blur(big.astype(np.float32), 1.5) - 0.5 * blur(small.astype(np.float32), 1.0)
    return norm01(h)


def brain_coral(seed, n):
    v = reaction_diffusion(seed, n, 0.029, 0.057, steps=5000, size=128)
    rim = spectral(seed, n, 2.6, fmin=2, fmax=14, salt=191)
    h = blur(v, 1.4) + 0.18 * rim
    return norm01(h)


def knit_wool(seed, n):
    cols, rows = 16, 22
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    cw, ch = n / cols, n / rows
    gx = xx / cw
    gy = yy / ch
    col = np.floor(gx)
    cu = gx % 1.0
    cv = gy % 1.0
    off = np.where(col % 2 == 0, 0.0, 0.5)
    cv2 = (cv + off) % 1.0
    # a 'V' stitch: two leaning loops per column
    left = np.sin(np.pi * np.clip(cu * 2, 0, 1)) * np.sin(np.pi * (cv2 + 0.25 * (1 - cu)) % np.pi)
    right = np.sin(np.pi * np.clip(cu * 2 - 1, 0, 1)) * np.sin(np.pi * (cv2 + 0.25 * cu) % np.pi)
    stitch = np.maximum(left, right)
    fuzz = blur(scratches(seed, n, 7000, 14, 0.0, spread=3.0, salt=201), 0.8)
    var = spectral(seed, n, 1.8, fmin=2, fmax=30, salt=202)
    h = 0.75 * stitch ** 0.9 * (0.8 + 0.3 * var) + 0.3 * fuzz
    return norm01(h)


MATERIALS: Dict[str, dict] = {
    "slate": dict(fn=slate, name="Cleaved Slate", category="stone", depth=1.5, roughness=0.55,
                  description="Dark cleaved slate plates with stepped flake edges and fine cleavage streaks."),
    "sandstone": dict(fn=sandstone, name="Banded Sandstone", category="stone", depth=1.2, roughness=0.85,
                      description="Wind-worn sandstone with warped sedimentary strata, sandy grain and weathering pits."),
    "cracked_earth": dict(fn=cracked_earth, name="Cracked Dry Earth", category="earth", depth=1.7, roughness=0.9,
                          description="Sun-baked clay in curling polygonal plates divided by deep drying cracks."),
    "ice": dict(fn=ice, name="Clouded Ice", category="ice", depth=1.0, roughness=0.15,
                description="Smooth glassy ice with rolling melt swells, a few fracture lines and trapped bubbles."),
    "bark": dict(fn=bark, name="Furrowed Bark", category="wood", depth=1.8, roughness=0.9,
                 description="Deep vertical bark furrows with warped, ridged plates."),
    "felt": dict(fn=felt, name="Pressed Wool Felt", category="textile", depth=0.7, roughness=1.0,
                 description="Dense matted wool fibres in a soft, uneven pressed mat."),
    "linen": dict(fn=linen, name="Slubbed Linen", category="textile", depth=1.2, roughness=0.85,
                  description="Plain-weave linen with uneven slubbed threads."),
    "corrugated_card": dict(fn=corrugated_card, name="Corrugated Card", category="paper", depth=1.6, roughness=0.85,
                            description="Cardboard flutes with paper fibre and soft crush marks."),
    "brushed_steel": dict(fn=brushed_steel, name="Brushed Steel", category="metal", depth=0.6, roughness=0.35,
                          description="Fine horizontal brushing lines with a few long scratches."),
    "rust": dict(fn=rust, name="Blistered Rust", category="metal", depth=1.6, roughness=0.95,
                 description="Corroded iron with blistered scale, pits and flaking patches."),
    "lead": dict(fn=lead, name="Soft Lead Sheet", category="metal", depth=0.9, roughness=0.6,
                 description="Soft, dented lead sheet crossed by hairline scratches."),
    "wax": dict(fn=wax, name="Melted Wax", category="wax", depth=0.8, roughness=0.3,
                description="Smooth, slowly flowing melted wax with broad drips and swells."),
    "ceramic_glaze": dict(fn=ceramic_glaze, name="Crazed Ceramic Glaze", category="ceramic", depth=0.9, roughness=0.2,
                          description="Glossy glaze with an orange-peel swell, hairline crazing and a few pinholes."),
    "rippled_sand": dict(fn=rippled_sand, name="Rippled Sand", category="earth", depth=1.4, roughness=0.8,
                         description="Wind ripples in fine sand with sharp crests and soft troughs."),
    "tooled_leather": dict(fn=tooled_leather, name="Pebbled Leather", category="leather", depth=1.3, roughness=0.55,
                           description="Pebble-grain leather with deep crease lines."),
    "cork": dict(fn=cork, name="Agglomerated Cork", category="organic", depth=1.1, roughness=0.9,
                 description="Pressed cork granules with scattered pits and pores."),
    "basket_weave": dict(fn=basket_weave, name="Basket Weave", category="textile", depth=1.6, roughness=0.8,
                         description="Woven reed slats in a checkerboard basket pattern."),
    "pumice": dict(fn=pumice, name="Pitted Pumice", category="stone", depth=1.5, roughness=0.95,
                   description="Light volcanic stone riddled with large and small gas pits."),
    "brain_coral": dict(fn=brain_coral, name="Meandering Coral", category="organic", depth=1.4, roughness=0.7,
                        description="Labyrinth ridges grown by reaction-diffusion, like brain coral."),
    "knit_wool": dict(fn=knit_wool, name="Knitted Wool", category="textile", depth=1.5, roughness=0.95,
                      description="Stockinette knit rows of chunky wool stitches with fibre fuzz."),
}

GENERATOR_VERSION = 1


def generate(material_id: str, seed: int, n: int = DEFAULT_N) -> np.ndarray:
    """Seamless float32 height in [0,1] for a procedural material; same (id, seed, n) => same array."""
    if material_id not in MATERIALS:
        raise KeyError(f"unknown procedural material: {material_id}")
    h = MATERIALS[material_id]["fn"](int(seed), int(n))
    return np.clip(np.asarray(h, dtype=np.float32), 0.0, 1.0)


def default_seed(material_id: str) -> int:
    """A fixed seed per id (stable across runs)."""
    return 1000 + sorted(MATERIALS).index(material_id)


def seam_ratio(h: np.ndarray) -> float:
    """How much worse the wrap edge is than the worst interior line: the mean |step| across the wrap
    (per axis) divided by the largest mean |step| of the tile's own interior lines.
    A periodic pattern with hard cell borders passes (its borders are as sharp inside); a cut tile fails (> ~1.5)."""
    worst = 0.0
    for ax in (0, 1):
        d = np.abs(np.diff(h, axis=ax))
        inner = d.mean(axis=1 - ax).max()
        edge = np.abs(np.take(h, 0, axis=ax) - np.take(h, -1, axis=ax)).mean()
        worst = max(worst, float(edge / max(inner, 1e-9)))
    return worst
