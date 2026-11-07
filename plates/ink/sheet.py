#!/usr/bin/env python
"""One sheet: every drawing in every material, mid-stroke. Rows are drawings, columns materials.

    python plates/ink/sheet.py [--out out/plates/ink/sheet.png] [--at 2.0] [--scale 0.3334]
"""
import argparse
import json
import pathlib
import subprocess
import tempfile

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
MATERIALS = ("chalk", "pencil_hatch")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default="out/plates/ink/sheet.png")
    p.add_argument("--at", type=float, default=2.0, help="seconds into a 4-second clip")
    p.add_argument("--scale", type=float, default=1 / 3)
    a = p.parse_args()
    names = sorted(json.loads((ROOT / "plates/ink/drawings.json").read_text(encoding="utf-8")))
    out = pathlib.Path(a.out)
    with tempfile.TemporaryDirectory(dir=ROOT / "out") as tmp:
        tmp = pathlib.Path(tmp)
        jobs = [{"out": str(tmp / f"{d}.{m}.png"), "spec": {"material": m, "drawing": d}, "at": a.at, "seconds": 4}
                for d in names for m in MATERIALS]
        (tmp / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
        subprocess.run(["node", "plates/ink/stills.mjs", "--jobs", str(tmp / "jobs.json"), "--scale", str(a.scale), "--quiet"],
                       cwd=ROOT, check=True)
        top, bottom = round(600 * a.scale), round(1350 * a.scale)
        width = round(1080 * a.scale)
        cell = (width, bottom - top)
        sheet = Image.new("L", (len(MATERIALS) * (cell[0] + 4), len(names) * (cell[1] + 4)), 96)
        for row, d in enumerate(names):
            for col, m in enumerate(MATERIALS):
                still = Image.open(tmp / f"{d}.{m}.png").convert("L").crop((0, top, width, bottom))
                sheet.paste(still, (col * (cell[0] + 4), row * (cell[1] + 4)))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size, len(jobs))


if __name__ == "__main__":
    main()
