#!/usr/bin/env python3
"""Check baked surface loops: the seam (last frame -> first frame) and text readability on the plate.

  python tools/check_surface_loops.py out/plates/loop_13_bark_rake ... [--report out/plates/report.json]

Seam: the loop is 180 frames at 30 fps, so frame 179 -> frame 0 must be a step like any other. We report
mean/p95 of |frame0 - frame179| on a 0..1 scale, the same figures as lit-surfaces goal 5 (mean <= 0.01, p95 <= 0.025),
and the ratio to a typical mid-loop frame step (informational: dawn loops on fine grain have a tiny normal step, so the ratio runs high while the absolute jump stays ~0.002-0.004).
Readability: the plate is laid between canvas and ink at 0.5 opacity (the top of the 0.35-0.50 band), and the WCAG
contrast of ink against its brightest 99th percentile must stay >= 7 (a text panel on it stays legible).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

CANVAS, INK = 0x0E, 0xF4  # tone only: the pack's own colours are applied by the engine
W, H = 270, 480


def frames(mp4: Path, picks):
    out = {}
    for i in picks:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"select=eq(n\\,{i}),scale={W}:{H}",
                              "-frames:v", "1", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                             capture_output=True, check=True).stdout
        out[i] = np.frombuffer(raw, dtype=np.uint8).reshape(H, W).astype(np.float64) / 255.0
    return out


def lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def check(d: Path) -> dict:
    mp4 = d / "plate.mp4"
    meta = json.loads((d / "plate.json").read_text(encoding="utf-8"))
    n = meta["frames"]
    f = frames(mp4, [0, 1, n // 2 - 1, n // 2, n - 1])
    seam = np.abs(f[0] - f[n - 1])
    step = 0.5 * (np.abs(f[1] - f[0]) + np.abs(f[n // 2] - f[n // 2 - 1]))  # a typical mid-loop step
    mean_d, p95_d = float(seam.mean()), float(np.percentile(seam, 95))
    ratio = mean_d / max(float(step.mean()), 1e-9)
    mid = f[n // 2]
    bg = (CANVAS + 0.5 * mid * (INK - CANVAS)) / 255.0
    bg99 = float(np.percentile(bg, 99))
    L = lambda c: float(lin(c))
    contrast = (L(INK / 255.0) + 0.05) / (L(bg99) + 0.05)
    res = {"loop": d.name, "mean_diff": round(mean_d, 4), "p95_diff": round(p95_d, 4), "step_ratio": round(ratio, 2),
           "seam_pass": bool(mean_d <= 0.01 and p95_d <= 0.025),
           "mean_luma": round(float(mid.mean()), 3), "p99_bg_luma": round(bg99, 3),
           "text_contrast": round(contrast, 1), "readable": bool(contrast >= 7.0),
           "ms_per_frame": meta.get("ms_per_frame")}
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--report")
    a = ap.parse_args()
    rows = [check(Path(d)) for d in a.dirs]
    for r in rows:
        print(json.dumps(r))
    if a.report:
        Path(a.report).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0 if all(r["seam_pass"] and r["readable"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
