"""The phase 0 spike's scaffold, now `engine compose scaffold` (tt_shorts/compose.py). Kept as a thin wrapper.

    python tools/compose_scaffold.py compose/24835 [--brand sitech] [--out DIR]
    = python -m tt_shorts.engine compose scaffold stories/24835.json --from compose/24835 [--brand sitech] --project DIR
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tt_shorts import compose  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="the agent's composition: index.html, compositions/*.html, beats.json")
    ap.add_argument("--story", help="the story (default stories/<the folder's name>.json)")
    ap.add_argument("--brand", help="the pack to build for (default: the story's)")
    ap.add_argument("--out", help="the project folder (default $VEASY_HOME/cache/compose/<brand>-<ref>)")
    a = ap.parse_args()
    story = a.story or ROOT / "stories" / f"{pathlib.Path(a.source).name}.json"
    r = compose.scaffold(story, a.brand, a.out, source=a.source, force=True)
    t = r.get("timing") or {}
    print(json.dumps({"project": str(r["project"]), "duration": t.get("duration"), "problems": r["problems"],
                      "beats": [(x["id"], x["t"]) for x in t.get("beats", [])]}, ensure_ascii=False))
