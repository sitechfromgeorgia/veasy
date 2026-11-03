#!/usr/bin/env python3
"""Preflight for a veasy story JSON: catch the failures that only show up at render time.

    .venv/bin/python ops/preflight.py demo/film-mzia.json [--format longform]

Checks, in about a second:
  - every scene "at" is the exact first words of its narration segment, in order
  - each segment is long enough for the layout QA (>= 6 words; a chapter needs >= 8)
  - on-screen text limits that the validator enforces later
  - the story length sits inside the format's window (estimated at 2.6 words/s)
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

LIMITS = {"kicker": 24, "headline": 40, "label": 24, "big": 12, "unit": 8, "place": 30, "sub": 30, "by": 40, "text": 200, "via": 32}
MIN_WORDS = 6
MIN_CHAPTER_WORDS = 8
KA_DIR = pathlib.Path("/root/.hermes/shared-plugins/kaeasy")


def ka_lint(text: str, mode: str):
    """Georgian mechanical lint via kaeasy, when the plugin is present. Speech allows Latin brand names."""
    if not text:
        return []
    try:
        sys.path.insert(0, str(KA_DIR))
        from lint import check_text  # type: ignore
    except Exception:
        return []
    skip = {"latin_in_speech"} if mode == "speech" else set()
    return [f for f in check_text(text, mode=mode, strict=True) if f.check not in skip]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--format", default=None)
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
    narration = d.get("narration") or ""
    scenes = d.get("scenes") or []
    problems = []

    pos = 0
    for i, sc in enumerate(scenes):
        at = str(sc.get("at") or "").strip()
        if not at:
            problems.append(f"scene {i} ({sc.get('type')}): empty at")
            continue
        j = narration.find(at, pos)
        if j < 0:
            problems.append(f"scene {i} ({sc.get('type')}): at is not the next narration text: {at[:40]!r}")
            continue
        nxt = scenes[i + 1].get("at") if i + 1 < len(scenes) else None
        k = narration.find(nxt, j + len(at)) if nxt else len(narration)
        if k < 0:
            problems.append(f"scene {i + 1}: at is not after scene {i}")
            continue
        seg = narration[j:k].strip()
        words = len(seg.split())
        need = MIN_CHAPTER_WORDS if sc.get("type") == "chapter" else MIN_WORDS
        if words < need:
            problems.append(f"scene {i} ({sc.get('type')}): segment is {words} words, needs {need} (layout QA drops it near 2 s): {seg[:50]!r}")
        pos = j + len(at)
        for key, lim in LIMITS.items():
            v = sc.get(key)
            if isinstance(v, str) and len(v) > lim:
                problems.append(f"scene {i}: {key} is {len(v)} chars, limit {lim}")
        lines = sc.get("lines")
        if isinstance(lines, list):
            for ln in lines:
                if isinstance(ln, str) and len(ln) > 24:
                    problems.append(f"scene {i}: hook line {len(ln)} chars, limit 24")

    for f in ka_lint(narration, "speech"):
        problems.append(f"narration {f.check}: {f.message} ({f.snippet})")
    for i, sc in enumerate(scenes):
        for key in ("kicker", "headline", "label", "big", "unit", "place", "sub", "by", "text", "via"):
            v = sc.get(key)
            if isinstance(v, str):
                for f in ka_lint(v, "social"):
                    problems.append(f"scene {i} {key} {f.check}: {f.message} ({f.snippet})")
        for ln in sc.get("lines") or []:
            if isinstance(ln, str):
                for f in ka_lint(ln, "social"):
                    problems.append(f"scene {i} line {f.check}: {f.message} ({f.snippet})")

    words = len(narration.split())
    est = round(words / 2.6)
    if a.format:
        try:
            from tt_shorts import formats
            f = formats.get(a.format)
            if not (f["min_seconds"] <= est <= f["max_seconds"]):
                problems.append(f"length: ~{est}s is outside {a.format}'s {f['min_seconds']}-{f['max_seconds']}s window ({words} words)")
        except Exception as e:
            problems.append(f"format {a.format!r}: {e}")

    if problems:
        print(f"BLOCKED {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print(f"OK {len(scenes)} scenes, {words} words, ~{est}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
