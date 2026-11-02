"""The daily run for one client, through the queue: pick the day's stories, queue them, let the worker render.

tbilisi.today (owner rule 2026-11-02: start with 10 a day): 4+ outlets, the last 18 hours, category caps, sensitive
stories skipped, never the same story twice (the queue's ids make a repeat a no-op).

  python -m ops.daily --limit 10 --dry-run      # the picks only
  python -m ops.daily --limit 10                # queue them and process up to --run jobs now
  python -m ops.daily --limit 10 --run 0        # queue only; cron's `engine queue run` renders them later
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import queue  # noqa: E402
from tt_shorts.sources import tbilisi_today  # noqa: E402

SIG = pathlib.Path("/root/sitech/scratch/story-significance/significance-map.json")  # optional ranking hint


LOOKS = {
    "hard": ("editorial", "cards"),
    "light": ("kinetic", "editorial"),
    "service": ("cards", "editorial"),
}
FAMILY = {"politics": "hard", "world": "hard", "crime": "hard", "sports": "light", "culture": "light",
          "economy": "service", "tech": "service", "society": "service", "education": "service"}


def look_for(category: str, index: int) -> str:
    """Rotate among the looks that fit the story, so consecutive videos do not look identical."""
    options = LOOKS[FAMILY.get(category, "service")]
    return options[index % len(options)]


def scores():
    try:
        return json.loads(SIG.read_text(encoding="utf-8")).get("scores", {})
    except (OSError, ValueError):
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--hours", type=int, default=30)
    ap.add_argument("--format", default="news-roll")
    ap.add_argument("--brand", default="tbilisi-today")
    ap.add_argument("--run", type=int, default=5, help="jobs to process now (0: only queue)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    seen = [j["ref"] for j in queue.listing(limit=1000) if j["source"] == "tbilisi-today"]
    picks = tbilisi_today.candidates(a.hours, a.limit, seen=seen, scores=scores())
    out = {"picks": [{"id": c["id"], "category": c["category"], "sources": c["source_count"],
                      "headline": c["headline"][:80]} for c in picks]}
    if not a.dry_run:
        out["queued"] = [queue.add(a.brand, "tbilisi-today", c["id"], a.format,
                                   overrides={"look": look_for(c["category"], i)},
                                   priority=len(picks) - i)[0]["id"]
                         for i, c in enumerate(picks)]
        out["run"] = queue.run(a.run) if a.run else None
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
