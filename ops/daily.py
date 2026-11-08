"""The daily run for one client, through the queue: pick the day's stories, queue them, let the worker render.

tbilisi.today (owner rule 2026-11-02: start with 10 a day): 4+ outlets, the last 18 hours, category caps, sensitive
stories skipped, never the same story twice (the queue's ids make a repeat a no-op).

  python -m ops.daily --limit 10 --dry-run      # the picks only
  python -m ops.daily --limit 10                # queue them and process up to --run jobs now
  python -m ops.daily --limit 10 --run 0        # queue only; cron's `engine queue run` renders them later
  python -m ops.daily --limit 10 --rubrics      # and the day's rubrics (tt_shorts/rubrics.py, skill veasy:rubrics)

--rubrics: code reads each pick's articles (and all its members), finds the facts (rubrics.facts) and gives each
rubric to at most one story a day, the first pick it fits (rubrics.assign: continues, agree, number, changes). A
cluster that already had a video is a candidate only for "continues": it is compared with what its last video had
(rubrics.growth), and its part is in the job. A rubric job takes the rubric's format and a priority by its time
slot (the earliest slot first). Then one digest job (rubric digest, source stories) of the brand's done news videos
of --digest-day (default yesterday): the 08:00 „დილის N ამბავი“, made only when 2-3 of them passed.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tt_shorts import queue, rubrics  # noqa: E402
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


def slot_priority(rubric_id):
    """Earlier slot, higher priority (100 for 00:00 down to 76 for 23:59): a rubric job runs before the plain picks."""
    h, m = map(int, rubrics.get(rubric_id)["slot"].split(":"))
    return 100 - (h * 60 + m) // 60


def rubric_plan(picks, again, brand, fetch=None):
    """picks: the day's new clusters (rows), again: clusters that already had a video. -> ({cluster id: rubric},
    {cluster id: part}, {cluster id: facts summary}). fetch(row) -> source data (default: D1, with every member)."""
    fetch = fetch or (lambda row: {**tbilisi_today.payload(row), "members": tbilisi_today.members(row["id"])})
    cands, parts, seen_facts = [], {}, {}
    for row in list(again) + list(picks):
        data = fetch(row)
        grown = rubrics.growth(brand, data)
        f = rubrics.facts(data, brand, grown)
        sid = str(row["id"])
        if grown["had_video"]:
            parts[sid] = grown["part"]
        # a cluster that had its video already can only continue; a new one is anything but continues
        cands.append((sid, f, ("continues",) if grown["had_video"] else None))
        seen_facts[sid] = {k: f[k] for k in ("big_numbers", "prices", "rules", "dates", "places", "agreed",
                                             "members", "had_video", "new_outlets", "new_facts")}
    chosen = rubrics.assign(cands)
    return chosen, parts, seen_facts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--hours", type=int, default=30)
    ap.add_argument("--format", default="news-roll")
    ap.add_argument("--brand", default="tbilisi-today")
    ap.add_argument("--run", type=int, default=5, help="jobs to process now (0: only queue)")
    ap.add_argument("--rubrics", action="store_true", help="assign the day's rubrics and queue the morning digest")
    ap.add_argument("--digest-day", help="the day whose done videos the digest joins (default yesterday)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    # A story is spent once a video exists for it. A failed or cancelled job must not block its story
    # forever: 338 renders failed on the writer's spent OpenRouter key (2026-11-07), and every one of
    # those clusters stayed invisible to the picker even after the key was fixed.
    SEEN_STATES = {"queued", "writing", "rendering", "done", "held"}
    seen = [j["ref"] for j in queue.listing(limit=1000)
            if j["source"] == "tbilisi-today" and j.get("state") in SEEN_STATES]
    picks = tbilisi_today.candidates(a.hours, a.limit, seen=seen, scores=scores())
    out = {"picks": [{"id": c["id"], "category": c["category"], "sources": c["source_count"],
                      "headline": c["headline"][:80]} for c in picks]}
    chosen, parts = {}, {}
    if a.rubrics:
        again = [r for r in tbilisi_today.recent(a.hours) if str(r["id"]) in {str(s) for s in seen}]
        chosen, parts, found = rubric_plan(picks, again, a.brand)
        out["rubrics"] = {sid: {"rubric": r, **({"part": parts[sid]} if sid in parts else {}), "facts": found[sid]}
                          for sid, r in chosen.items()}
        day = a.digest_day or (dt.date.today() - dt.timedelta(days=1)).isoformat()
        out["digest"] = {"ref": f"done:{a.brand}:{day}", "slot": rubrics.get("digest")["slot"]}
    if not a.dry_run:
        queued = []
        for i, c in enumerate(picks):
            sid = str(c["id"])
            over = {"look": look_for(c["category"], i)}
            fmt, prio = a.format, len(picks) - i
            if sid in chosen:
                over["rubric"] = chosen[sid]
                fmt, prio = rubrics.get(chosen[sid])["format"], slot_priority(chosen[sid])
            queued.append(queue.add(a.brand, "tbilisi-today", c["id"], fmt, overrides=over, priority=prio)[0]["id"])
        for sid, r in chosen.items():  # the continues parts: clusters that are not among today's new picks
            if r == "continues":
                over = {"rubric": r, "part": parts[sid]}
                queued.append(queue.add(a.brand, "tbilisi-today", sid, rubrics.get(r)["format"], overrides=over,
                                        priority=slot_priority(r))[0]["id"])
        if a.rubrics:
            queued.append(queue.add(a.brand, "stories", out["digest"]["ref"], None, overrides={"rubric": "digest"},
                                    priority=slot_priority("digest"))[0]["id"])
        out["queued"] = queued
        out["run"] = queue.run(a.run) if a.run else None
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
