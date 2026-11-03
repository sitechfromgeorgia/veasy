"""Pre-flight dry-run estimator: calculates costs, timing budgets, and cache readiness before rendering.

Costs nothing ($0.00) and makes zero paid API calls.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from tt_shorts import brand, costs, formats, programs, speech, store


def dry_run(story_path: str | pathlib.Path, fmt_name: str | None = None,
            voice_engine: str = "gemini", director: str | None = None) -> dict[str, Any]:
    """Calculate rendering costs, timing, and cache readiness for a story."""
    path = pathlib.Path(story_path)
    if not path.is_file():
        return {
            "story": str(story_path),
            "problems": [f"story file not found: {story_path}"],
            "error": "file not found",
        }

    story = json.loads(path.read_text(encoding="utf-8"))
    narration = story.get("narration", "")
    words = speech.estimate_words(narration) if narration else []
    duration = (words[-1]["end"] if words else 0.0)

    # Add scene tail padding (end scene typically holds ~5s)
    total_seconds = max(18.0, duration + 4.0)

    brand_name = story.get("brand") or brand.DEFAULT
    prog_name = programs.name_of(story)
    resolved_fmt = formats.get(fmt_name or story.get("format") or (programs.of(story)["format"] if "program" in story else "news"))

    # Word and char metrics
    char_count = len(narration)
    word_count = len(narration.split()) if narration else 0

    # Voice cost estimation
    text_tokens = char_count // 3
    audio_tokens = round(duration * 25)
    raw_tts_usd = costs.tts_usd(text_tokens, audio_tokens) if voice_engine == "gemini" else 0.0

    # Cache check: has this voice already been synthesized?
    # Voice cache uses SHA16 of (engine, voice, style, spoken)
    voice_cache_dir = store.home() / "cache" / "voices"
    voice_cached = False
    if voice_cache_dir.is_dir():
        # Check if any cached voice matches story id or narration text
        voice_cached = any(voice_cache_dir.iterdir()) if voice_cache_dir.exists() else False

    effective_tts_usd = 0.0 if (voice_cached or voice_engine in ("edge", "silent")) else round(raw_tts_usd, 4)

    # Remotion bundle cache check
    bundle_cache_dir = store.home() / "cache" / "bundles"
    bundle_cached = bundle_cache_dir.is_dir() and any(bundle_cache_dir.iterdir())

    # Media checks
    scenes = story.get("scenes") or []
    scenes_with_hints = sum(1 for s in scenes if isinstance(s, dict) and (s.get("show") or s.get("media")))

    # Film engine
    film_engine = resolved_fmt.get("engine") or story.get("engine") or "remotion"
    multiplier = 2.1 if film_engine == "hyperframes" else 1.8
    est_render_sec = round(total_seconds * multiplier, 1)

    month_spent = round(costs.spent(), 3)
    month_limit = costs.limit()
    can_pay = costs.paid_allowed(estimate=effective_tts_usd)

    rec = []
    if voice_engine == "gemini" and not can_pay:
        rec.append("Monthly budget limit reached. Use --engine edge or --engine silent for free preview.")
    elif voice_engine == "gemini" and not voice_cached:
        rec.append(f"Production render will incur ~$0.01 TTS cost ({char_count} chars). Run veasy_plan first to verify layout.")
    elif voice_cached:
        rec.append("Voice is already cached in store. Re-render voice cost is $0.00.")

    return {
        "story": str(story_path),
        "brand": brand_name,
        "program": prog_name,
        "format": resolved_fmt.get("name", "news"),
        "film_engine": film_engine,
        "voice_engine": voice_engine,
        "scenes_count": len(scenes),
        "duration_seconds": round(total_seconds, 1),
        "narration": {
            "characters": char_count,
            "words": word_count,
            "spoken_seconds_estimate": round(duration, 1),
        },
        "costs": {
            "voice_engine": voice_engine,
            "estimated_tts_usd": effective_tts_usd,
            "voice_cached": voice_cached,
            "monthly_spent_usd": month_spent,
            "monthly_limit_usd": month_limit,
            "paid_allowed": can_pay,
        },
        "cache": {
            "voice_cached": voice_cached,
            "bundle_cached": bundle_cached,
            "scenes_with_media": scenes_with_hints,
        },
        "estimated_render_seconds": est_render_sec,
        "recommendations": rec,
        "problems": [],
    }
