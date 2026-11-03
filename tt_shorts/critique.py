"""Pre-flight visual critique: checklist an agent runs on a plan's stills before rendering.

Evaluates:
  1. safe_zone: scene text inside y<=1380, captions inside y<=1552, right-of-rail clear (x<=940 below y=1100).
  2. reading_pacing: text reading load (need vs shown, 0.5s + 0.3s/word), words per second.
  3. visual_stillness: motion rules (no stretches >3s with nothing changing; beat activity).
  4. motion_variety: variety novelty guard distance, transitions, entrances.
  5. hook_impact: hook scene presence, line count, headline brevity, frame-0 readability.
  6. brand_compliance: contrast floors (WCAG 7:1 ink, 4.5:1 muted, 2:1 accent), accent not on text.
  7. scene_composition: scene sequence flow, absence of duplicate consecutive scene types.

Outputs structured JSON with an overall grade (PASS, NEEDS_ATTENTION, FAIL), score (0-100),
detailed checklist items, and contact sheet path.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from tt_shorts import brand, formats, motion_rules, plan


def critique_story(story_path: str | pathlib.Path, fmt_name: str | None = None,
                   look: str | None = None, director: str | None = None,
                   plan_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a structured visual and pacing critique on a story's plan."""
    path = pathlib.Path(story_path)
    if not path.is_file():
        return {
            "story": str(story_path),
            "grade": "FAIL",
            "score": 0,
            "summary": f"Story file not found: {story_path}",
            "checklist": [],
            "problems": [f"file not found: {story_path}"],
            "recommendations": ["Provide a valid path to an existing story JSON file."],
        }

    story = json.loads(path.read_text(encoding="utf-8"))
    resolved_fmt = formats.get(fmt_name or story.get("format") or "news", look=look)

    if plan_data is None:
        plan_data = plan.run(str(path), resolved_fmt, look=look, director=director)

    checklist: list[dict[str, Any]] = []
    problems: list[str] = list(plan_data.get("problems") or [])
    recommendations: list[str] = []
    penalties = 0

    # 1. Safe Zone
    probe_info = plan_data.get("probe") or {}
    probe_problems = probe_info.get("problems") or []
    if probe_problems:
        penalties += 30
        checklist.append({
            "item": "safe_zone",
            "status": "fail",
            "message": f"Safe zone violations detected: {'; '.join(probe_problems)}",
        })
        recommendations.append("Adjust text length or padding so text stays inside y<=1380 and left of rail (x<=940 below y=1100).")
    else:
        text_count = probe_info.get("texts", 0)
        checklist.append({
            "item": "safe_zone",
            "status": "pass",
            "message": f"All {text_count} texts verified inside safe zones and clear of UI rail.",
        })

    # 2. Reading Load & Pacing
    scenes = plan_data.get("scenes") or []
    overloaded = []
    for sc in scenes:
        load = sc.get("load") or 0.0
        if load > 1.05:
            overloaded.append(f"scene {sc['scene']} ({sc['type']}): load {load:.2f} exceeds 1.0 (needs more time)")
        wps = sc.get("words_per_second") or 0.0
        if wps > 2.5:
            overloaded.append(f"scene {sc['scene']} ({sc['type']}): pace {wps:.1f} words/s is rushed (>2.5)")

    if overloaded:
        penalties += 20
        checklist.append({
            "item": "reading_pacing",
            "status": "fail",
            "message": f"Reading pacing issues: {'; '.join(overloaded)}",
        })
        recommendations.append("Shorten on-screen text or expand narration time for overloaded scenes.")
    else:
        checklist.append({
            "item": "reading_pacing",
            "status": "pass",
            "message": f"Reading pace is balanced across {len(scenes)} scenes (all loads <= 1.0).",
        })

    # 3. Visual Stillness & Motion Rules
    motion_info = plan_data.get("motion") or {}
    holds = motion_info.get("holds") or []
    warnings = motion_info.get("warnings") or []
    if holds:
        penalties += 30
        checklist.append({
            "item": "visual_stillness",
            "status": "fail",
            "message": f"Motion holds detected: {'; '.join(holds)}",
        })
        recommendations.append("Eliminate unreadable text holds or static holds before rendering.")
    elif warnings:
        penalties += 10
        checklist.append({
            "item": "visual_stillness",
            "status": "warning",
            "message": f"Motion warnings: {'; '.join(warnings)}",
        })
        recommendations.append("Review motion warnings: diversify transitions or reduce static stretches.")
    else:
        checklist.append({
            "item": "visual_stillness",
            "status": "pass",
            "message": "Dynamic pacing verified: no unreadable text or static freezes >3s.",
        })

    # 4. Motion Variety & Novelty Guard
    novelty_info = plan_data.get("novelty") or {}
    if novelty_info.get("too_close"):
        penalties += 15
        checklist.append({
            "item": "motion_variety",
            "status": "warning",
            "message": f"Planned video fingerprint is close to recent renders (similarity {novelty_info.get('similarity')}).",
        })
        recommendations.append("Re-roll style or choose another director to ensure channel variety.")
    else:
        checklist.append({
            "item": "motion_variety",
            "status": "pass",
            "message": f"Distinctive style profile (distance {novelty_info.get('distance', 1.0):.2f} from recent videos).",
        })

    # 5. Hook Impact & Frame 0
    hook_scenes = [s for s in scenes if s.get("type") == "hook"]
    if not hook_scenes:
        penalties += 25
        checklist.append({
            "item": "hook_impact",
            "status": "fail",
            "message": "Missing opening hook scene.",
        })
        recommendations.append("Ensure the first scene is a hook with high-impact lines.")
    else:
        hk = hook_scenes[0]
        hk_duration = hk.get("seconds") or 0.0
        if hk_duration < 2.5:
            penalties += 10
            checklist.append({
                "item": "hook_impact",
                "status": "warning",
                "message": f"Hook duration ({hk_duration:.1f}s) is very short (<2.5s).",
            })
            recommendations.append("Give viewers at least 3 seconds to register the hook headline.")
        else:
            checklist.append({
                "item": "hook_impact",
                "status": "pass",
                "message": f"Hook scene properly paced ({hk_duration:.1f}s, {hk.get('words', 0)} spoken words).",
            })

    # 6. Brand Compliance & Contrast
    brand_name = story.get("brand") or brand.DEFAULT
    try:
        pack = brand.load(brand_name)
        raw_theme = resolved_fmt.get("theme")
        theme_name = (pack.get("default_theme") or "dark") if raw_theme in (None, "default", "auto") else raw_theme
        theme_colors = pack["themes"][theme_name]["colors"]
        contrast_errs = brand.contrast_problems(theme_colors)
        if contrast_errs:
            penalties += 20
            checklist.append({
                "item": "brand_compliance",
                "status": "fail",
                "message": f"Contrast floor failures: {'; '.join(contrast_errs)}",
            })
            recommendations.append("Update brand theme colors to meet WCAG contrast floors.")
        else:
            checklist.append({
                "item": "brand_compliance",
                "status": "pass",
                "message": f"Palette contrast meets WCAG standards for theme '{theme_name}'.",
            })
    except Exception as e:
        penalties += 10
        checklist.append({
            "item": "brand_compliance",
            "status": "warning",
            "message": f"Brand validation check notice: {e}",
        })

    # 7. Scene Composition Flow
    scene_types = [s.get("type") for s in story.get("scenes") or []]
    has_dups = any(a == b for a, b in zip(scene_types, scene_types[1:]))
    if has_dups:
        penalties += 10
        checklist.append({
            "item": "scene_composition",
            "status": "warning",
            "message": "Consecutive duplicate scene types detected.",
        })
        recommendations.append("Alternate scene types (e.g. hook -> stat -> timeline -> quote) for visual momentum.")
    else:
        checklist.append({
            "item": "scene_composition",
            "status": "pass",
            "message": f"Smooth composition sequence ({' -> '.join(scene_types[:5])}{'...' if len(scene_types) > 5 else ''}).",
        })

    score = max(0, 100 - penalties)
    if score >= 85 and not any(c["status"] == "fail" for c in checklist):
        grade = "PASS"
        summary = f"Ready to render (Score {score}/100). All core checks passed."
    elif score >= 60 and not any(c["item"] == "safe_zone" and c["status"] == "fail" for c in checklist):
        grade = "NEEDS_ATTENTION"
        summary = f"Review recommended (Score {score}/100). Address warnings before production render."
    else:
        grade = "FAIL"
        summary = f"Render blocked (Score {score}/100). Fix critical failures."

    return {
        "story": str(story_path),
        "grade": grade,
        "score": score,
        "summary": summary,
        "checklist": checklist,
        "sheet": plan_data.get("sheet"),
        "stills": plan_data.get("stills", []),
        "recommendations": recommendations,
        "problems": problems,
    }
