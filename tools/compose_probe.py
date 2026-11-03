"""The phase 0 spike's probe on a built project, now part of `engine compose check` (tt_shorts/compose.py:
run_probe). Kept as a thin wrapper.

    python tools/compose_probe.py <project> [--shots DIR]
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tt_shorts import brand, compose  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--shots", help="also save the page at each probed time (PNG)")
    a = ap.parse_args()
    project = pathlib.Path(a.project)
    timing = json.loads((project / "timing.json").read_text(encoding="utf-8"))
    r = compose.run_probe(project, timing, brand.load(timing["brand"]), a.shots)
    print(json.dumps({k: r[k] for k in ("frames", "texts", "problems", "blocked", "fonts")}, ensure_ascii=False, indent=1))
