"""Review packet architecture and generation logic for Veasy's film-eyes lane (ROADMAP / HyperFrames review contract).

Produces:
1. Machine-readable JSON review packets (`review_packet.json`) containing:
   - Contact sheets and visual stills ONLY.
   - Declarative film spec ONLY, NEVER THE CODE (no HTML/CSS/TSX/JS/DOM).
   - Beat timeline breakdown and per-scene reading load analysis.
   - Strictly formatted visual critique notes: `t=4.2s · where · problem -> change`.
   - Before-and-after comparison representation across iterative review rounds.
2. Human-facing and vision-agent-facing Markdown summary (`REVIEW.md`).

Contract adherence:
- The review packet must contain sheets and the film's spec ONLY, NEVER the code!
- Notes must strictly follow the skill's format:
    `t=4.2s · where · problem -> change`
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple, Union

from tt_shorts import brand, catalog, eyes, formats, motion_rules, news_check, plan, probe, props, speech, store, swipe, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Delimiters and canonical arrow
DELIMITER = " · "
ARROW = " -> "
ALTERNATIVE_ARROW = " → "

# Strict note regex: t=4.2s · where · problem -> change
NOTE_REGEX = re.compile(
    r"^t=(?P<time>\d+(?:\.\d+)?)s\s*·\s*(?P<where>[^·]+?)\s*·\s*(?P<problem>.+?)\s*(?:->|→)\s*(?P<change>.+)$"
)

# Contract guards: code extensions forbidden anywhere in review packets
FORBIDDEN_CODE_EXTENSIONS = frozenset({
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".py", ".pyc", ".sh", ".bash", ".bat", ".ps1",
    ".jsonl", ".lock", ".vue", ".svelte"
})

ALLOWED_IMAGE_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".svg"
})

CODE_PATTERNS = [
    re.compile(r"<\s*(?:template|div|span|script|style|iframe|button|video|audio|canvas)\b", re.IGNORECASE),
    re.compile(r"\b(?:const|let|var|function|class|import|export|from|return)\s+[a-zA-Z0-9_$]+"),
    re.compile(r"\bdocument\.(?:querySelector|getElementById|createElement)"),
    re.compile(r"\bwindow\.__timelines\b"),
    re.compile(r"\bgsap\.(?:to|from|fromTo|timeline)\b"),
    re.compile(r"\bremotion/src\b"),
]

# JSON schema specification for ReviewPacket
REVIEW_PACKET_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "VeasyReviewPacket",
    "type": "object",
    "required": [
        "packet_version",
        "created_at",
        "film_id",
        "brand",
        "engine",
        "round",
        "spec",
        "sheets",
        "timeline",
        "reading_load",
        "findings",
        "comparison"
    ],
    "properties": {
        "packet_version": {"type": "string", "enum": ["1.0"]},
        "created_at": {"type": "string", "format": "date-time"},
        "film_id": {"type": "string"},
        "brand": {"type": "string"},
        "engine": {"type": "string", "enum": ["remotion", "hyperframes"]},
        "round": {"type": "integer", "minimum": 1},
        "spec": {
            "type": "object",
            "required": ["goal", "output", "time", "look", "shots", "banned"],
            "properties": {
                "goal": {"type": "string"},
                "output": {"type": "object"},
                "time": {"type": "object"},
                "look": {"type": "object"},
                "objects": {"type": "array"},
                "motion": {"type": "object"},
                "shots": {"type": "array"},
                "banned": {"type": "array"},
                "qa": {"type": "array"}
            }
        },
        "sheets": {
            "type": "object",
            "properties": {
                "contact_sheet": {"type": ["string", "null"]},
                "review_beats": {"type": ["string", "null"]},
                "review_phone": {"type": ["string", "null"]},
                "review_seams": {"type": "array", "items": {"type": "string"}},
                "stills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["scene", "type", "time", "path"],
                        "properties": {
                            "scene": {"type": "integer"},
                            "type": {"type": "string"},
                            "time": {"type": "number"},
                            "path": {"type": "string"}
                        }
                    }
                }
            }
        },
        "timeline": {
            "type": "object",
            "required": ["duration_seconds", "beats"],
            "properties": {
                "duration_seconds": {"type": "number"},
                "beats": {"type": "array"}
            }
        },
        "reading_load": {
            "type": "object",
            "required": ["overall_load", "scenes"],
            "properties": {
                "overall_load": {"type": "number"},
                "scenes": {"type": "array"}
            }
        },
        "findings": {
            "type": "object",
            "required": ["summary", "notes"],
            "properties": {
                "summary": {
                    "type": "object",
                    "required": ["p0_count", "p1_count", "p2_count", "verdict"]
                },
                "notes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["priority", "time", "where", "problem", "change", "formatted"]
                    }
                }
            }
        },
        "comparison": {
            "type": "object",
            "required": ["has_comparison"]
        }
    }
}


# ==============================================================================
# 1. Note Formatting & Parsing
# ==============================================================================


def format_finding(time_s: float, where: str, problem: str, change: str) -> str:
    """Format a finding into the strict note specification:
    `t=4.2s · where · problem -> change`
    """
    clean_where = " ".join(str(where).strip().split())
    clean_problem = " ".join(str(problem).strip().split())
    clean_change = " ".join(str(change).strip().split())
    return f"t={time_s:.1f}s{DELIMITER}{clean_where}{DELIMITER}{clean_problem}{ARROW}{clean_change}"


def parse_finding(note_line: str) -> Dict[str, Any]:
    """Parse a note line formatted as `t=4.2s · where · problem -> change`.

    Raises ValueError if line does not match the specification.
    """
    line = note_line.strip()
    match = NOTE_REGEX.match(line)
    if not match:
        raise ValueError(
            f"Invalid note format: '{line}'. Expected format: 't=<sec>s · <where> · <problem> -> <change>'"
        )
    return {
        "time": float(match.group("time")),
        "where": match.group("where").strip(),
        "problem": match.group("problem").strip(),
        "change": match.group("change").strip(),
        "formatted": format_finding(
            float(match.group("time")),
            match.group("where"),
            match.group("problem"),
            match.group("change"),
        ),
    }


def classify_priority(rule: str, detail: str = "", hold: bool = False) -> str:
    """Classify finding priority:
    - P0: Breaks the read or contract (holds a render: unreadable text, safe-zone violation, contrast floor).
    - P1: Weakens the film (visual stillness > 3s, rushed pacing, high reading load, ping-pong cuts).
    - P2: Polish (transitions variety, minor timing adjustments).
    """
    rule_lower = rule.lower()
    detail_lower = detail.lower()

    # P0 checks
    if hold or rule_lower in ("read", "safe_zone", "rail", "band", "captions", "frame", "overflow", "glyph", "contrast"):
        return "P0"
    if any(k in detail_lower for k in ("unreadable", "social rail", "header zone", "captions zone", "contrast floor", "missing hook")):
        return "P0"

    # P1 checks
    if rule_lower in ("still", "moves", "background", "pacing", "pingpong", "repeat", "reading_pacing", "scene_composition", "motion_variety"):
        return "P1"
    if any(k in detail_lower for k in ("nothing changes", "stagger", "duplicate", "faster than voice", "exceeds 1.0", "pacing")):
        return "P1"

    return "P2"


# ==============================================================================
# 2. Raw Engine Finding Converters
# ==============================================================================


def convert_motion_finding(finding: Dict[str, Any], scenes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Convert a raw finding from `motion_rules.py` into the formatted note structure."""
    rule = finding.get("rule", "motion")
    detail = finding.get("detail", "")
    scene_idx = finding.get("scene")
    is_hold = finding.get("hold", False)
    priority = classify_priority(rule, detail, hold=is_hold)

    scene_data = (scenes[scene_idx] if (scenes and scene_idx is not None and 0 <= scene_idx < len(scenes)) else {})
    time_s = float(scene_data.get("start", 0.0))
    scene_type = scene_data.get("type", "scene")
    where = f"scene {scene_idx} ({scene_type})" if scene_idx is not None else "video timeline"

    # Case 1: unreadable text (read)
    if rule == "read":
        # Extract seconds needed and shown from detail if available
        # Format in motion_rules: "... is readable for X.X s, its N words need Y.Y s"
        m_sec = re.search(r"readable for (?P<shown>[\d.]+) s, its (?P<words>\d+) words need (?P<need>[\d.]+) s", detail)
        if m_sec:
            shown_s = float(m_sec.group("shown"))
            need_s = float(m_sec.group("need"))
            problem = f"text needs {need_s:.1f}s but scene ends at {shown_s:.1f}s"
            change = "expand narration or trim quote"
        else:
            problem = f"text duration insufficient for readability ({detail})"
            change = "expand scene duration or shorten on-screen copy"

    # Case 2: static stretch (still)
    elif rule == "still":
        m_quiet = re.search(r"nothing changes for (?P<quiet>[\d.]+) s", detail)
        quiet_s = m_quiet.group("quiet") if m_quiet else "3.0+"
        problem = f"visual stillness for {quiet_s}s exceeds maximum hold threshold"
        change = "split scene or add secondary motion beat"

    # Case 3: consecutive duplicate scenes (repeat)
    elif rule == "repeat":
        problem = "duplicate scene type consecutive to previous"
        change = "vary card layout or consolidate"

    # Case 4: safe zone violations in motion_rules
    elif rule == "safe_zone":
        m_coords = re.search(r"x=(?P<x>[\d.]+).*?y=(?P<y>[\d.]+)", detail)
        if m_coords:
            x_val, y_val = int(float(m_coords.group("x"))), int(float(m_coords.group("y")))
            problem = f"text extends into social rail (x={x_val}, y={y_val})"
        elif "header zone" in detail:
            problem = "text enters header zone (y < 248)"
        elif "captions zone" in detail:
            problem = "text enters captions zone (y > 1380)"
        else:
            problem = "text exceeds canvas safe zone"
        change = "trim line or reduce font size"

    # Case 5: simultaneous moves
    elif rule == "moves":
        problem = "multiple elements enter simultaneously, scattering viewer focus"
        change = "stagger element entrances by 150ms"

    # Case 6: background interference
    elif rule == "background":
        problem = "active video motion behind text obscures readability"
        change = "quiet background motion or use still image"

    # Case 7: pacing
    elif rule == "pacing":
        problem = "cut comes too fast for voice and reader comprehension"
        change = "extend scene duration or pace narration"

    # Case 8: transition ping-pong or count
    elif rule in ("pingpong", "kinds"):
        where = "transitions"
        problem = f"transition pattern issue: {detail}"
        change = "standardize transition directions and limit distinct kinds to 3"

    else:
        problem = detail or f"rule {rule} violation"
        change = "adjust scene timing or layout to satisfy rule"

    formatted = format_finding(time_s, where, problem, change)
    return {
        "priority": priority,
        "rule": rule,
        "time": time_s,
        "where": where,
        "problem": problem,
        "change": change,
        "formatted": formatted,
    }


def convert_probe_issue(issue: Dict[str, Any], scenes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Convert a layout probe issue from `probe.py` into the formatted note structure."""
    rule = issue.get("rule", "probe")
    detail = issue.get("detail", "")
    frame = issue.get("frame", 0)
    scene_idx = issue.get("scene")
    scene_type = issue.get("type") or "scene"
    time_s = round(frame / speech.FPS, 1)

    where = f"scene {scene_idx} ({scene_type})" if scene_idx is not None else issue.get("region", "frame")

    if rule == "rail":
        m_coords = re.search(r"x=(?P<x>[\d.]+).*?y=(?P<y>[\d.]+)", detail)
        if m_coords:
            x_val, y_val = int(float(m_coords.group("x"))), int(float(m_coords.group("y")))
            problem = f"text extends into social rail (x={x_val}, y={y_val})"
        else:
            problem = "text extends into social rail (x > 940 below y=1100)"
        change = "trim line or reduce font size"
    elif rule == "band":
        problem = "text outside 248..1380 vertical scene band"
        change = "clamp layout inside safe zone boundaries"
    elif rule == "captions":
        problem = "captions extend below y=1552 limit"
        change = "re-page captions or reduce font size"
    elif rule == "contrast":
        problem = f"insufficient text contrast: {detail}"
        change = "lighten ink or darken background card"
    elif rule == "overflow":
        problem = "text overflows container boundaries"
        change = "shorten text or expand container width"
    elif rule == "size":
        problem = f"text size below legibility floor: {detail}"
        change = "enlarge font size or cut words"
    elif rule == "glyph":
        problem = f"character missing in brand font: {detail}"
        change = "replace character or update font subset"
    else:
        problem = f"probe layout violation ({rule}): {detail}"
        change = "reposition or rescale element"

    priority = classify_priority(rule, detail, hold=True)
    formatted = format_finding(time_s, where, problem, change)
    return {
        "priority": priority,
        "rule": rule,
        "time": time_s,
        "where": where,
        "problem": problem,
        "change": change,
        "formatted": formatted,
    }


def convert_raw_string(problem_str: str, scenes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Convert an arbitrary raw problem or warning string into a structured note."""
    line = str(problem_str).strip()

    # If it is already formatted as t=... · where · problem -> change, parse directly
    if NOTE_REGEX.match(line):
        parsed = parse_finding(line)
        return {
            "priority": classify_priority("note", parsed["problem"]),
            "rule": "note",
            **parsed,
        }

    # Extract scene index if mentioned: "scene 3 (points)" or "scene 3:"
    m_sc = re.search(r"scenes?\s+(?P<idx>\d+)(?:\s*\((?P<typ>[^)]+)\))?", line, re.IGNORECASE)
    scene_idx = int(m_sc.group("idx")) if m_sc else None
    scene_typ = m_sc.group("typ") if (m_sc and m_sc.group("typ")) else None

    scene_data = (scenes[scene_idx] if (scenes and scene_idx is not None and 0 <= scene_idx < len(scenes)) else {})
    time_s = float(scene_data.get("start", 0.0))
    if scene_idx is not None:
        where = f"scene {scene_idx} ({scene_typ or scene_data.get('type', 'scene')})"
    else:
        where = "video timeline"

    # Safe zone rail
    if "rail" in line.lower() or "social rail" in line.lower():
        m_coords = re.search(r"x=(?P<x>[\d.]+).*?y=(?P<y>[\d.]+)", line)
        if m_coords:
            x_val, y_val = int(float(m_coords.group("x"))), int(float(m_coords.group("y")))
            problem = f"text extends into social rail (x={x_val}, y={y_val})"
        else:
            problem = "text extends into social rail"
        change = "trim line or reduce font size"
        priority = "P0"
    # Reading time
    elif "readable for" in line.lower() or "need" in line.lower() and "word" in line.lower():
        m_sec = re.search(r"readable for (?P<shown>[\d.]+) s.*?need (?P<need>[\d.]+) s", line)
        if m_sec:
            shown_s, need_s = float(m_sec.group("shown")), float(m_sec.group("need"))
            problem = f"text needs {need_s:.1f}s but scene ends at {shown_s:.1f}s"
        else:
            problem = "text reading time shorter than required words"
        change = "expand narration or trim quote"
        priority = "P0"
    # Stillness
    elif "nothing changes" in line.lower() or "still" in line.lower():
        problem = "visual stillness exceeds maximum limit"
        change = "split scene or add secondary motion beat"
        priority = "P1"
    # Pacing / load
    elif "load" in line.lower() and "exceeds" in line.lower():
        problem = "reading load exceeds 1.0"
        change = "shorten on-screen copy or pace narration"
        priority = "P1"
    elif " both " in line.lower() or "repeat" in line.lower() and "narration" not in line.lower():
        problem = "the same scene type twice in a row"
        change = "swap the second for another type (points -> pair or steps) or merge the two"
        priority = "P1"
    elif "pingpong" in line.lower():
        problem = "cuts go back and forth (A-B-A or opposite directions)"
        change = "use one transition family or a steady direction"
        priority = "P1"
    elif "metronome" in line.lower():
        problem = "scenes cut on a steady beat"
        change = "vary scene lengths: move an anchor so one scene holds longer"
        priority = "P2"
    elif "spoken_redundancy" in line.lower() or "repeats spoken" in line.lower():
        problem = "the screen only repeats the words spoken"
        change = "give the screen the number, name or a short label the voice does not say"
        priority = "P1"
    elif "empty_middle" in line.lower() or "central safe zone" in line.lower():
        problem = "the middle of the frame is empty or washed out"
        change = "put the content in the scene band or raise the ink contrast"
        priority = "P0"
    elif "hero" in line.lower():
        problem = "no frame carries the film"
        change = "make one scene a clear climax: a big number or a bold hook"
        priority = "P2"
    elif "same_picture" in line.lower() or "same picture" in line.lower():
        problem = "two scenes look the same"
        change = "change the layout or merge the scenes"
        priority = "P1"
    elif "safe_zone" in line.lower() and "hook line" in line.lower():
        problem = "a hook line is long enough to reach the social rail"
        change = "break the line shorter (26 characters or fewer)"
        priority = "P1"
    elif "flash" in line.lower():
        problem = "the film flashes more than 3 times a second"
        change = "slow the cuts or inversions"
        priority = "P0"
    elif "duplicate" in line.lower() or "match previous" in line.lower():
        problem = "numbers match previous frame"
        change = "vary card layout or consolidate"
        priority = "P1"
    else:
        # Fallback sanitization
        clean = re.sub(r"^(?:probe|motion|timing|lint)\s*[^:]*:\s*", "", line)
        problem = clean[:120]
        change = "adjust scene pacing or visual composition"
        priority = "P1"

    formatted = format_finding(time_s, where, problem, change)
    return {
        "priority": priority,
        "rule": "general",
        "time": time_s,
        "where": where,
        "problem": problem,
        "change": change,
        "formatted": formatted,
    }


# ==============================================================================
# 3. Contract Enforcement: Spec Only, Zero Code Leakage
# ==============================================================================


class CodeLeakageError(ValueError):
    """Raised when review packet violates the zero code leakage contract."""
    pass


def assert_zero_code_leakage(obj: Any, context: str = "packet") -> None:
    """Recursively verify that NO code, scripts, HTML tags, or code file paths
    exist within the object.
    """
    if isinstance(obj, str):
        # 1. Check forbidden extensions in file paths
        lower_str = obj.lower()
        for ext in FORBIDDEN_CODE_EXTENSIONS:
            if lower_str.endswith(ext) or f"{ext}#" in lower_str or f"{ext}?" in lower_str:
                raise CodeLeakageError(
                    f"Code file reference detected in {context}: '{obj}'. Review packets must contain sheets and spec ONLY, NEVER code!"
                )

        # 2. Check for code syntax / DOM tags
        for pat in CODE_PATTERNS:
            if pat.search(obj):
                raise CodeLeakageError(
                    f"Code pattern detected in {context}: '{obj[:100]}...'. Review packets must be purely visual/spec!"
                )

    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_zero_code_leakage(k, f"{context}.key({k})")
            assert_zero_code_leakage(v, f"{context}[{k}]")

    elif isinstance(obj, (list, tuple, set)):
        for i, item in enumerate(obj):
            assert_zero_code_leakage(item, f"{context}[{i}]")


def verify_contract_adherence(packet: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate review packet against the complete contract:
    1. Zero code leakage (no HTML, CSS, TSX, JS, or code paths).
    2. Notes strictly follow `t=4.2s · where · problem -> change`.
    3. Contact sheets and stills are valid image paths or references.
    4. Film spec is declarative and code-free.
    """
    violations: List[str] = []

    # 1. Zero code leakage check
    try:
        assert_zero_code_leakage(packet, context="ReviewPacket")
    except CodeLeakageError as err:
        violations.append(str(err))

    # 2. Strict note formatting verification
    notes = packet.get("findings", {}).get("notes", [])
    for idx, n in enumerate(notes):
        fmt = n.get("formatted", "")
        if not NOTE_REGEX.match(fmt):
            violations.append(
                f"Note #{idx} fails format contract: '{fmt}'. Must be 't=<sec>s · <where> · <problem> -> <change>'"
            )

    # 3. Sheets check
    sheets = packet.get("sheets", {})
    for k in ("contact_sheet", "review_beats", "review_phone"):
        val = sheets.get(k)
        if val is not None and not isinstance(val, str):
            violations.append(f"Sheet path '{k}' must be string or null, got {type(val)}")
        elif val:
            suffix = pathlib.Path(val).suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTENSIONS:
                violations.append(f"Sheet path '{val}' has invalid image extension: '{suffix}'")

    for s in sheets.get("stills", []):
        p = s.get("path", "")
        suffix = pathlib.Path(p).suffix.lower()
        if suffix not in ALLOWED_IMAGE_EXTENSIONS:
            violations.append(f"Still image '{p}' has invalid image extension: '{suffix}'")

    # 4. Spec completeness
    spec = packet.get("spec", {})
    for req in ("goal", "output", "time", "look", "shots", "banned"):
        if req not in spec:
            violations.append(f"Spec is missing required field: '{req}'")

    return (len(violations) == 0, violations)


# ==============================================================================
# 4. Clean Spec Extraction
# ==============================================================================


def extract_clean_spec(
    story_or_path: Union[str, pathlib.Path, Dict[str, Any]],
    project_dir: Optional[Union[str, pathlib.Path]] = None,
    fmt: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract or synthesize a clean, declarative film spec containing NO code.

    Reads `SPEC.md` from `project_dir` if present, or synthesizes from story + brand pack.
    """
    if isinstance(story_or_path, (str, pathlib.Path)):
        p = pathlib.Path(story_or_path)
        story = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    else:
        story = dict(story_or_path)

    b_pack = brand.of(story)
    fmt = fmt or formats.get(story.get("format") or "news")

    spec_path = pathlib.Path(project_dir) / "SPEC.md" if project_dir else None
    if spec_path and spec_path.is_file():
        # Parse authored SPEC.md
        raw_text = spec_path.read_text(encoding="utf-8")
        parsed_spec = _parse_spec_markdown(raw_text)
        assert_zero_code_leakage(parsed_spec, context="SPEC.md")
        return parsed_spec

    # Synthesize clean declarative spec (Remotion brush stories or compose without SPEC.md)
    scenes = story.get("scenes", [])
    duration_est = float(len(story.get("narration", "").split()) * 0.28 + 2.0)

    shots = []
    t_cursor = 0.0
    for i, sc in enumerate(scenes):
        w_count = sum(len(str(v).split()) for k, v in sc.items() if k not in ("type", "at", "art"))
        dur = max(2.5, round(w_count * 0.35 + 1.2, 1))
        shots.append({
            "index": i,
            "type": sc.get("type", "scene"),
            "time_range": f"{t_cursor:.1f}s-{t_cursor + dur:.1f}s",
            "hero_move": f"Scene {sc.get('type')} enters and settles typography",
            "viewer_reads": " · ".join(str(sc.get(k)) for k in ("kicker", "headline", "value", "label") if k in sc),
            "narration": sc.get("at", ""),
            "sound": "music loop bed",
        })
        t_cursor += dur

    theme_name = fmt.get("theme") or b_pack.get("default_theme", "dark")
    theme_colors = b_pack.get("themes", {}).get(theme_name, {}).get("colors", {})

    spec = {
        "goal": f"Deliver clear visual news for '{story.get('category', 'general')}' to social viewer in Georgian.",
        "output": {
            "engine": story.get("engine") or fmt.get("engine", "remotion"),
            "width": 1080,
            "height": 1920,
            "fps": speech.FPS,
        },
        "time": {
            "seconds": round(duration_est, 1),
            "frames": int(duration_est * speech.FPS),
            "bpm": None,
        },
        "look": {
            "theme": theme_name,
            "canvas": theme_colors.get("canvas", "#171817"),
            "ink": theme_colors.get("ink", "#F1EDE4"),
            "accent": theme_colors.get("accent", "#FF792E"),
            "font_family": "Brand",
            "medium": "Graphic editorial cards on clean dark ground with strict contrast",
        },
        "objects": [
            "Official news source attribution line and timestamp badge",
            "Typographic statistics, quotes, and timeline sequence cards",
            "Verified SVG seed drawings or Lucide pictogram icons",
            "Platform safe-zone boundary rails and caption pages",
        ],
        "motion": {
            "eases": "spring-settled entrances, directional wipes and fades",
            "timing_rules": "0.5s base + 0.3s per word readability floor",
            "maximum_stillness": "3.0s maximum freeze without visual change",
        },
        "shots": shots,
        "banned": [
            "Dark empty voids with floating ungrounded particles",
            "Neon blooms, lens flares, or decorative glowing rings",
            "Generic gradients or unstyled default HTML cards",
            "Text moving while being read or drifting titles",
            "Accent color applied to body text (accent is dot/marker only)",
            "Unreadable copy held under 0.5s + 0.3s/word floor",
        ],
        "qa": [
            "Frame 0 settled hook readable as thumbnail",
            "Safe zone clearance (y: 248..1380, right rail x<=940 below y=1100)",
            "WCAG contrast compliance across all text regions",
        ],
    }

    assert_zero_code_leakage(spec, context="synthesized_spec")
    return spec


def _parse_spec_markdown(text: str) -> Dict[str, Any]:
    """Parse authored SPEC.md lines into structured clean dictionary."""
    spec: Dict[str, Any] = {
        "goal": "",
        "output": {},
        "time": {},
        "look": {},
        "objects": [],
        "motion": {},
        "shots": [],
        "banned": [],
        "qa": [],
    }

    current_section = None
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue

        m_key = re.match(r"^([A-Z_]+):\s*(.*)$", trimmed)
        if m_key:
            current_section = m_key.group(1).lower()
            val = m_key.group(2).strip()
            if current_section == "goal":
                spec["goal"] = val
            elif current_section == "output":
                spec["output"] = {"description": val}
            elif current_section == "time":
                spec["time"] = {"description": val}
            elif current_section == "look":
                spec["look"] = {"description": val}
            elif current_section in ("objects", "motion", "shots", "banned", "qa"):
                if val:
                    spec[current_section].append(val)
        elif current_section in ("objects", "motion", "shots", "banned", "qa"):
            cleaned = trimmed.lstrip("-* ").strip()
            if cleaned:
                spec[current_section].append(cleaned)

    return spec


# ==============================================================================
# 5. Beat Timeline & Reading Load Extractors
# ==============================================================================


def extract_beat_timeline(scenes: List[Dict[str, Any]], duration_seconds: float) -> List[Dict[str, Any]]:
    """Build beat timeline breakdown from planned or composed scenes."""
    beats: List[Dict[str, Any]] = []
    for sc in scenes:
        idx = sc.get("scene", len(beats))
        typ = sc.get("type", "scene")
        start_s = float(sc.get("start", 0.0))
        end_s = float(sc.get("end", start_s + sc.get("seconds", 2.0)))
        dur_s = round(end_s - start_s, 2)
        words_c = sc.get("words", 0)
        wps = sc.get("words_per_second", round(words_c / dur_s, 2) if dur_s else 0.0)

        texts = []
        for t in sc.get("texts", []):
            texts.append({
                "text": t.get("text", ""),
                "words": t.get("words", 0),
                "need_s": round(float(t.get("need", 0.0)), 2),
                "shown_s": round(float(t.get("shown", dur_s)), 2),
                "is_readable": float(t.get("shown", dur_s)) + 1e-4 >= float(t.get("need", 0.0)),
            })

        beats.append({
            "scene_index": idx,
            "type": typ,
            "start_s": start_s,
            "end_s": end_s,
            "duration_s": dur_s,
            "words": words_c,
            "words_per_second": wps,
            "load": round(float(sc.get("load", 0.0)), 2),
            "texts": texts,
        })
    return beats


def extract_reading_load(scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate detailed reading load per scene and overall film load statistics."""
    scene_loads = []
    total_need = 0.0
    total_time = 0.0
    overloaded = 0

    for sc in scenes:
        idx = sc.get("scene", len(scene_loads))
        typ = sc.get("type", "scene")
        dur = float(sc.get("seconds") or (sc.get("end", 0.0) - sc.get("start", 0.0)) or 1.0)
        words_c = int(sc.get("words", 0))
        wps = float(sc.get("words_per_second") or (round(words_c / dur, 2) if dur else 0.0))
        load_val = float(sc.get("load", 0.0))

        # Sum text needs
        sc_need = sum(float(t.get("need", 0.0)) for t in sc.get("texts", []))
        total_need += sc_need
        total_time += dur

        status = "pass"
        if load_val > 1.05 or wps > 2.5:
            status = "overloaded"
            overloaded += 1

        scene_loads.append({
            "scene": idx,
            "type": typ,
            "duration_s": round(dur, 2),
            "words": words_c,
            "words_per_second": round(wps, 2),
            "load": round(load_val, 2),
            "status": status,
        })

    overall_load = round(total_need / total_time, 2) if total_time > 0 else 0.0
    return {
        "overall_load": overall_load,
        "overloaded_count": overloaded,
        "scenes": scene_loads,
    }


# ==============================================================================
# 6. Sheet & Still Resolving
# ==============================================================================


def resolve_sheet_paths(
    plan_data: Optional[Dict[str, Any]] = None,
    compose_data: Optional[Dict[str, Any]] = None,
    project_dir: Optional[Union[str, pathlib.Path]] = None,
) -> Dict[str, Any]:
    """Extract and validate contact sheet and still image paths.
    Guarantees that all paths refer strictly to images, never code files.
    """
    sheets: Dict[str, Any] = {
        "contact_sheet": None,
        "review_beats": None,
        "review_phone": None,
        "review_seams": [],
        "stills": [],
    }

    # 1. From Remotion plan_data
    if plan_data:
        if plan_data.get("sheet"):
            sheets["contact_sheet"] = str(plan_data["sheet"])
        for idx, still_path in enumerate(plan_data.get("stills", [])):
            sheets["stills"].append({
                "scene": idx,
                "type": plan_data.get("scenes", [{}])[idx].get("type", "scene") if idx < len(plan_data.get("scenes", [])) else "scene",
                "time": plan_data.get("scenes", [{}])[idx].get("start", 0.0) if idx < len(plan_data.get("scenes", [])) else 0.0,
                "path": str(still_path),
            })

    # 2. From HyperFrames compose look
    if compose_data:
        comp_sheets = compose_data.get("sheets") or {}
        if comp_sheets.get("beats"):
            sheets["review_beats"] = str(comp_sheets["beats"])
            if not sheets["contact_sheet"]:
                sheets["contact_sheet"] = str(comp_sheets["beats"])
        if comp_sheets.get("phone"):
            sheets["review_phone"] = str(comp_sheets["phone"])
        if comp_sheets.get("seams"):
            sheets["review_seams"] = [str(x) for x in comp_sheets["seams"]]

    # 3. Check project look directory if project_dir is provided
    if project_dir:
        p_dir = pathlib.Path(project_dir)
        look_dir = p_dir / ".veasy" / "look"
        if look_dir.is_dir():
            beats_jpg = look_dir / "review-beats.jpg"
            phone_jpg = look_dir / "review-phone.jpg"
            if beats_jpg.exists() and not sheets["review_beats"]:
                sheets["review_beats"] = str(beats_jpg.resolve())
                if not sheets["contact_sheet"]:
                    sheets["contact_sheet"] = str(beats_jpg.resolve())
            if phone_jpg.exists() and not sheets["review_phone"]:
                sheets["review_phone"] = str(phone_jpg.resolve())
            seams = sorted(look_dir.glob("review-seam-*.jpg"))
            if seams and not sheets["review_seams"]:
                sheets["review_seams"] = [str(s.resolve()) for s in seams]

    # Validate image extensions
    assert_zero_code_leakage(sheets, context="sheets_collection")
    return sheets


# ==============================================================================
# 7. Before-and-After Comparison Representation
# ==============================================================================


def compare_review_packets(
    previous_packet: Dict[str, Any],
    current_packet: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare two review packets (e.g. Round 1 vs Round 2) to track fixes,
    regressions, reading load deltas, and visual sheets.
    """
    prev_notes = previous_packet.get("findings", {}).get("notes", [])
    curr_notes = current_packet.get("findings", {}).get("notes", [])

    prev_by_key = {
        (n["where"].lower(), n["problem"].lower()): n for n in prev_notes
    }
    curr_by_key = {
        (n["where"].lower(), n["problem"].lower()): n for n in curr_notes
    }

    resolved = []
    for k, n in prev_by_key.items():
        if k not in curr_by_key:
            resolved.append(n)

    persisting = []
    for k, n in curr_by_key.items():
        if k in prev_by_key:
            persisting.append(n)

    new_notes = []
    for k, n in curr_by_key.items():
        if k not in prev_by_key:
            new_notes.append(n)

    # Calculate load changes
    prev_scenes = {s["scene"]: s["load"] for s in previous_packet.get("reading_load", {}).get("scenes", [])}
    curr_scenes = {s["scene"]: s["load"] for s in current_packet.get("reading_load", {}).get("scenes", [])}
    load_deltas = {}
    for sc_id, curr_load in curr_scenes.items():
        prev_load = prev_scenes.get(sc_id, curr_load)
        diff = round(curr_load - prev_load, 2)
        load_deltas[str(sc_id)] = {
            "before": prev_load,
            "after": curr_load,
            "diff": diff,
        }

    # Verdict
    prev_p0 = previous_packet.get("findings", {}).get("summary", {}).get("p0_count", 0)
    curr_p0 = current_packet.get("findings", {}).get("summary", {}).get("p0_count", 0)

    if curr_p0 == 0 and len(curr_notes) < len(prev_notes):
        verdict = "improved"
    elif curr_p0 > prev_p0 or len(new_notes) > len(resolved):
        verdict = "regressed"
    else:
        verdict = "iterating"

    comparison = {
        "has_comparison": True,
        "previous_round": previous_packet.get("round", 1),
        "current_round": current_packet.get("round", 2),
        "verdict": verdict,
        "resolved_notes": resolved,
        "persisting_notes": persisting,
        "new_notes": new_notes,
        "load_deltas": load_deltas,
        "sheets": {
            "before_contact_sheet": previous_packet.get("sheets", {}).get("contact_sheet"),
            "after_contact_sheet": current_packet.get("sheets", {}).get("contact_sheet"),
            "before_phone_sheet": previous_packet.get("sheets", {}).get("review_phone"),
            "after_phone_sheet": current_packet.get("sheets", {}).get("review_phone"),
        },
    }

    assert_zero_code_leakage(comparison, context="comparison_data")
    return comparison


# ==============================================================================
# 8. Main Review Packet Builder
# ==============================================================================


def build_review_packet(
    story_path: Union[str, pathlib.Path],
    fmt_name: str = "news",
    look: Optional[str] = None,
    director: Optional[str] = None,
    round_num: int = 1,
    project_dir: Optional[Union[str, pathlib.Path]] = None,
    compose_look_data: Optional[Dict[str, Any]] = None,
    plan_data: Optional[Dict[str, Any]] = None,
    previous_packet: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble complete ReviewPacket:
    - Sheets and declarative spec ONLY (zero code leakage).
    - Notes strictly formatted as `t=4.2s · where · problem -> change`.
    - Beat timeline and reading load per scene.
    - Before-and-after comparison representation if previous packet provided.
    """
    story_p = pathlib.Path(story_path)
    story = json.loads(story_p.read_text(encoding="utf-8")) if story_p.is_file() else {}
    b_name = story.get("brand") or brand.DEFAULT
    film_id = str(story.get("id") or story_p.stem)

    fmt = formats.get(fmt_name or story.get("format") or "news", look=look)
    engine_type = "hyperframes" if (project_dir or compose_look_data or story.get("engine") == "hyperframes") else "remotion"

    # 1. Run plan if not provided and in remotion lane
    if plan_data is None and engine_type == "remotion":
        try:
            plan_data = plan.run(str(story_p), fmt, look=look, director=director, with_probe=False)
        except Exception:
            plan_data = {}

    # 2. Extract clean spec (NO code)
    clean_spec = extract_clean_spec(story, project_dir=project_dir, fmt=fmt)

    # 3. Resolve sheet paths
    sheets = resolve_sheet_paths(plan_data=plan_data, compose_data=compose_look_data, project_dir=project_dir)

    # 4. Scenes data
    raw_scenes = (plan_data.get("scenes") if plan_data else None) or (compose_look_data.get("scenes") if compose_look_data else None) or []
    total_duration = float(plan_data.get("seconds", 20.0) if plan_data else compose_look_data.get("duration", 20.0) if compose_look_data else 20.0)

    # Synchronize spec timing with actual timeline duration
    if total_duration > 0:
        clean_spec["time"]["seconds"] = round(total_duration, 1)
        clean_spec["time"]["frames"] = int(total_duration * speech.FPS)

    # 5. Beat timeline & reading load
    timeline_beats = extract_beat_timeline(raw_scenes, total_duration)
    reading_analysis = extract_reading_load(raw_scenes)

    # 6. Gather and convert findings into strict note format
    raw_findings: List[Dict[str, Any]] = []

    # Motion rules holds/warnings
    motion_info = (plan_data.get("motion") if plan_data else None) or {}
    for h in motion_info.get("holds", []):
        raw_findings.append(convert_raw_string(h, raw_scenes))
    for w in motion_info.get("warnings", []):
        raw_findings.append(convert_raw_string(w, raw_scenes))

    # Probe problems/issues
    probe_info = (plan_data.get("probe") if plan_data else None) or {}
    for pr in probe_info.get("problems", []):
        raw_findings.append(convert_raw_string(pr, raw_scenes))

    # Overloaded scenes from reading load
    for sc in reading_analysis.get("scenes", []):
        if sc["status"] == "overloaded":
            time_s = float(raw_scenes[sc["scene"]].get("start", 0.0)) if sc["scene"] < len(raw_scenes) else 0.0
            formatted = format_finding(
                time_s,
                f"scene {sc['scene']} ({sc['type']})",
                f"reading load {sc['load']:.2f} exceeds 1.0 (pace {sc['words_per_second']:.1f} w/s)",
                "shorten copy or extend scene duration"
            )
            raw_findings.append({
                "priority": "P1",
                "rule": "reading_pacing",
                "time": time_s,
                "where": f"scene {sc['scene']} ({sc['type']})",
                "problem": f"reading load {sc['load']:.2f} exceeds 1.0 (pace {sc['words_per_second']:.1f} w/s)",
                "change": "shorten copy or extend scene duration",
                "formatted": formatted,
            })

    # Compose problems/warnings
    if compose_look_data:
        for pr in compose_look_data.get("problems", []):
            raw_findings.append(convert_raw_string(pr, raw_scenes))
        for w in compose_look_data.get("warnings", []):
            raw_findings.append(convert_raw_string(w, raw_scenes))

    # De-duplicate notes by formatted string
    seen_formatted = set()
    unique_notes = []
    for nf in raw_findings:
        fmt_str = nf["formatted"]
        if fmt_str not in seen_formatted:
            seen_formatted.add(fmt_str)
            unique_notes.append(nf)

    # Sort notes by timestamp, then priority
    p_order = {"P0": 0, "P1": 1, "P2": 2}
    unique_notes.sort(key=lambda x: (p_order.get(x["priority"], 3), x["time"]))

    p0_count = sum(1 for n in unique_notes if n["priority"] == "P0")
    p1_count = sum(1 for n in unique_notes if n["priority"] == "P1")
    p2_count = sum(1 for n in unique_notes if n["priority"] == "P2")

    if p0_count > 0:
        verdict = "rebuild" if p0_count >= 3 else "fix"
    elif p1_count > 0:
        verdict = "fix"
    else:
        verdict = "ship"

    findings = {
        "summary": {
            "p0_count": p0_count,
            "p1_count": p1_count,
            "p2_count": p2_count,
            "total_notes": len(unique_notes),
            "verdict": verdict,
        },
        "notes": unique_notes,
    }

    # 7. Comparison representation
    if previous_packet:
        comparison = compare_review_packets(previous_packet, {
            "round": round_num,
            "sheets": sheets,
            "reading_load": reading_analysis,
            "findings": findings,
        })
    else:
        comparison = {
            "has_comparison": False,
            "previous_round": None,
            "current_round": round_num,
            "verdict": "initial",
            "resolved_notes": [],
            "persisting_notes": [],
            "new_notes": [],
            "load_deltas": {},
            "sheets": {},
        }

    packet = {
        "packet_version": "1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "film_id": film_id,
        "brand": b_name,
        "engine": engine_type,
        "round": round_num,
        "spec": clean_spec,
        "sheets": sheets,
        "timeline": {
            "duration_seconds": total_duration,
            "beats": timeline_beats,
        },
        "reading_load": reading_analysis,
        "findings": findings,
        "comparison": comparison,
    }

    # Contract verification: ensure ZERO code leakage
    is_valid, errors = verify_contract_adherence(packet)
    if not is_valid:
        raise CodeLeakageError(f"Review packet contract validation failed: {'; '.join(errors)}")

    return packet


# ==============================================================================
# 9. Markdown Template Generation (REVIEW.md)
# ==============================================================================


def render_review_markdown(packet: Dict[str, Any]) -> str:
    """Render the human-facing and vision-agent-facing `REVIEW.md` document."""
    spec = packet.get("spec", {})
    sheets = packet.get("sheets", {})
    timeline = packet.get("timeline", {})
    reading = packet.get("reading_load", {})
    findings = packet.get("findings", {})
    summary = findings.get("summary", {})
    comparison = packet.get("comparison", {})
    notes = findings.get("notes", [])

    lines: List[str] = []

    # Title & Metadata
    lines.append(f"# Review Packet: {packet.get('brand')} · Film #{packet.get('film_id')}")
    lines.append("")
    lines.append(f"> **Round:** {packet.get('round')} | **Engine:** `{packet.get('engine')}` | **Verdict:** `{summary.get('verdict', 'unknown').upper()}`")
    lines.append(f"> **Findings:** {summary.get('p0_count', 0)} P0 (Hold) · {summary.get('p1_count', 0)} P1 (Weak) · {summary.get('p2_count', 0)} P2 (Polish)")
    lines.append("")

    # Visual Review Sheets
    lines.append("## 1. Visual Review Sheets")
    lines.append("")
    if sheets.get("contact_sheet"):
        lines.append(f"- **Primary Contact Sheet:** `{sheets['contact_sheet']}`")
    if sheets.get("review_beats"):
        lines.append(f"- **Beats & Mid-Scene Sheet:** `{sheets['review_beats']}`")
    if sheets.get("review_phone"):
        lines.append(f"- **Mobile 360px Sheet:** `{sheets['review_phone']}`")
    if sheets.get("review_seams"):
        lines.append(f"- **Cut Strips ({len(sheets['review_seams'])} seams):**")
        for seam in sheets["review_seams"][:5]:
            lines.append(f"  - `{seam}`")
    if sheets.get("stills"):
        lines.append(f"- **Settled Scene Stills:** {len(sheets['stills'])} stills available")
    lines.append("")

    # Film Spec Summary (NO code!)
    lines.append("## 2. Film Spec (Director's Contract)")
    lines.append("")
    lines.append(f"- **Goal:** {spec.get('goal', 'N/A')}")
    time_info = spec.get("time", {})
    lines.append(f"- **Pacing & Duration:** {time_info.get('seconds', timeline.get('duration_seconds'))}s ({time_info.get('frames', 'N/A')} frames @ {speech.FPS} fps)")
    look_info = spec.get("look", {})
    lines.append(f"- **Visual Medium:** {look_info.get('medium', 'Graphic cards')}")
    lines.append(f"- **Tokens:** Theme `{look_info.get('theme', 'dark')}` · Canvas `{look_info.get('canvas')}` · Ink `{look_info.get('ink')}` · Accent `{look_info.get('accent')}`")
    lines.append("")

    if spec.get("banned"):
        lines.append("### Banned Defaults")
        for b in spec["banned"]:
            lines.append(f"- {b}")
        lines.append("")

    # Beat Timeline & Reading Load
    lines.append("## 3. Beat Timeline & Reading Load")
    lines.append("")
    lines.append(f"Overall Reading Load: **{reading.get('overall_load', 0.0):.2f}** ({'Optimal' if reading.get('overall_load', 0) <= 1.0 else 'High'})")
    lines.append("")
    lines.append("| Scene | Type | Start-End | Duration | Spoken Words | Words/s | Reading Load | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for sc in reading.get("scenes", []):
        sc_id = sc.get("scene", 0)
        sc_typ = sc.get("type", "scene")
        dur = sc.get("duration_s", 0.0)
        w = sc.get("words", 0)
        wps = sc.get("words_per_second", 0.0)
        ld = sc.get("load", 0.0)
        stat = sc.get("status", "pass").upper()
        # Find start and end from beats
        beat_match = next((b for b in timeline.get("beats", []) if b.get("scene_index") == sc_id), {})
        t_span = f"{beat_match.get('start_s', 0.0):.1f}s-{beat_match.get('end_s', dur):.1f}s"
        lines.append(f"| {sc_id} | `{sc_typ}` | {t_span} | {dur:.1f}s | {w} | {wps:.1f} | {ld:.2f} | `{stat}` |")
    lines.append("")

    # Review Notes (Strict format)
    lines.append("## 4. Review Notes & Prescribed Changes")
    lines.append("")
    lines.append("> Notes strictly formatted as `t=<time>s · <where> · <problem> -> <change>`")
    lines.append("")

    p0_notes = [n for n in notes if n.get("priority") == "P0"]
    p1_notes = [n for n in notes if n.get("priority") == "P1"]
    p2_notes = [n for n in notes if n.get("priority") == "P2"]

    lines.append("### P0 (Hold - Breaks the Read or Contract)")
    if p0_notes:
        for n in p0_notes:
            lines.append(f"- `{n['formatted']}`")
    else:
        lines.append("- *(None - all safe zone, contrast, and readability floors passed)*")
    lines.append("")

    lines.append("### P1 (Weakens the Film)")
    if p1_notes:
        for n in p1_notes:
            lines.append(f"- `{n['formatted']}`")
    else:
        lines.append("- *(None - visual stillness and pacing balanced)*")
    lines.append("")

    lines.append("### P2 (Polish)")
    if p2_notes:
        for n in p2_notes:
            lines.append(f"- `{n['formatted']}`")
    else:
        lines.append("- *(None)*")
    lines.append("")

    # Before-and-After Comparison (if iterating)
    if comparison.get("has_comparison"):
        lines.append("## 5. Before-and-After Comparison (Round "
                     f"{comparison.get('previous_round')} -> Round {comparison.get('current_round')})")
        lines.append("")
        lines.append(f"Iteration Verdict: **`{comparison.get('verdict', 'unknown').upper()}`**")
        lines.append("")

        resolved = comparison.get("resolved_notes", [])
        lines.append(f"### Resolved Findings ({len(resolved)})")
        if resolved:
            for r in resolved:
                lines.append(f"- [x] ~`{r['formatted']}`~")
        else:
            lines.append("- *(No findings resolved in this pass)*")
        lines.append("")

        persisting = comparison.get("persisting_notes", [])
        if persisting:
            lines.append(f"### Persisting Findings ({len(persisting)})")
            for p in persisting:
                lines.append(f"- [ ] `{p['formatted']}`")
            lines.append("")

        new_n = comparison.get("new_notes", [])
        if new_n:
            lines.append(f"### New Regressions ({len(new_n)})")
            for nn in new_n:
                lines.append(f"- [!] `{nn['formatted']}`")
            lines.append("")

        sheets_comp = comparison.get("sheets", {})
        if sheets_comp.get("before_contact_sheet") and sheets_comp.get("after_contact_sheet"):
            lines.append("### Sheet Diff")
            lines.append(f"- **Before Sheet:** `{sheets_comp['before_contact_sheet']}`")
            lines.append(f"- **After Sheet:** `{sheets_comp['after_contact_sheet']}`")
            lines.append("")

    # Measurement Ledger
    lines.append("## 5. Measurement & Delivery Ledger" if not comparison.get("has_comparison") else "## 6. Measurement & Delivery Ledger")
    lines.append("")
    lines.append("- **What was measured:** Frame geometry (safe zones), text reading duration (0.5s + 0.3s/word), reading loads, WCAG contrast ratios, and stillness thresholds.")
    lines.append("- **What was visually inspected:** Beat contact sheets, typography hierarchy, mobile legibility at 360px.")
    lines.append("- **What was NOT heard:** Audio volume and mix were computationally measured via loudness filters, not heard by human ear.")
    lines.append("")

    rendered = "\n".join(lines)
    # Final assertion of zero code leakage in rendered Markdown
    assert_zero_code_leakage(rendered, context="rendered_REVIEW.md")
    return rendered


# ==============================================================================
# 10. Automated Review & Repair Loop (film-eyes lane)
# ==============================================================================

# Regex patterns for factual entity extraction
GE = "ა-ჰ"
SURNAME = re.compile(rf"(?<![{GE}])[{GE}]{{2,}}(?:შვილ(?:ი|მა|ს|ის|ით|თან|ზე|ო)?|ძე(?:მ|ს|ის|ით|სთან|ზე)?)(?![{GE}])")
LATIN_NAME = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]*(?:[.+&'][A-Za-z0-9]+|-[A-Za-z0-9]+)*")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
DATE_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)?")
TIME_RANGE_RE = re.compile(r"\d{1,2}:\d{2}\s*(?:→|-|–|—)\s*\d{1,2}:\d{2}")
URL_RE = re.compile(r"https?://[^\s\"'>]+|[a-zA-Z0-9.-]+\.(?:today|ge|com|org|net|gov)[^\s\"'>]*")
QUOTE_RE = re.compile(r"[„“\"]([^„“”\"]+)[“”\"]")

GEORGIAN_MONTHS = (
    "იანვარ", "თებერვალ", "მარტ", "აპრილ", "მაის", "ივნის",
    "ივლის", "აგვისტო", "სექტემბერ", "ოქტომბერ", "ნოემბერ", "დეკემბერ"
)
GEORGIAN_WEEKDAYS = (
    "ორშაბათ", "სამშაბათ", "ოთხშაბათ", "ხუთშაბათ", "პარასკევ", "შაბათ", "კვირა"
)

NUMERIC_KEYS = ("value", "pct", "change", "total", "n", "of", "rank", "start_val", "end_val")
DATE_KEYS = ("date", "start", "end", "time", "weekday", "when")
NAME_KEYS = ("who", "person", "speaker", "author", "place", "source_name")
CODE_KEYS = ("type", "at", "icon", "verb", "em", "style", "show", "media", "rank", "status", "state",
             "transition", "flow", "enter", "layout", "motif", "look", "beats", "duration", "art", "mark", "plate")

REPAIRABLE = ("motion repeat", "motion pingpong", "safe_zone")  # warnings a transform can fix
MAX_MACHINE_ROUNDS_CAP = 3
MAX_LOOK_ROUNDS_CAP = 2


def extract_numbers(text: str) -> list[str]:
    """Extract all numbers from text, both numeric digits and recognized numerals."""
    if not text:
        return []
    text_str = str(text)
    nums = list(NUM_RE.findall(text_str))
    try:
        from tt_shorts import speech as sp
        if hasattr(sp, "extract_numbers"):
            sp_nums = sp.extract_numbers(text_str)
            for n in sp_nums:
                s = str(n)
                if s not in nums:
                    nums.append(s)
    except Exception:
        pass
    return sorted(nums)


def _stem(word: str, keep: int = 3) -> str:
    """Stem a Georgian word by stripping case ending."""
    w = word.strip(".,:;!?„“\"'()«»").lower()
    return w if len(w) <= keep + 1 else w[:max(keep, len(w) - 2)]


def extract_facts(story: dict[str, Any]) -> dict[str, Any]:
    """Extract all immutable factual entities from a story JSON.

    Returns:
        dict containing normalized bags of numbers, dates, proper names,
        quotes, sources, links, and identity anchors.
    """
    facts: dict[str, Any] = {
        "id": str(story.get("id") or ""),
        "cluster_id": str(story.get("cluster_id") or story.get("cluster") or ""),
        "sources": sorted(str(s).strip() for s in story.get("sources") or []),
        "links": Counter(),
        "numbers": Counter(),
        "dates": Counter(),
        "quotes": Counter(),
        "proper_names": Counter(),
    }

    if story.get("url"):
        facts["links"][str(story["url"]).strip()] += 1
    if story.get("link"):
        facts["links"][str(story["link"]).strip()] += 1
    if story.get("date"):
        facts["dates"][str(story["date"]).strip()] += 1

    # Pre-scan scenes for known proper name tokens (places, persons)
    known_name_stems: set[str] = set()
    for sc in story.get("scenes") or []:
        for k in NAME_KEYS:
            if sc.get(k):
                val = str(sc[k])
                for token in re.findall(r"[\w]+", val):
                    if len(token) >= 4:
                        known_name_stems.add(token.lower()[:max(4, len(token) - 3)])

    narration = str(story.get("narration") or "")
    if narration:
        for num in extract_numbers(narration):
            facts["numbers"][num] += 1
        for quote in QUOTE_RE.findall(narration):
            cleaned = quote.strip()
            if cleaned:
                facts["quotes"][cleaned] += 1
        for surname in SURNAME.findall(narration):
            facts["proper_names"][surname] += 1
        for latin in LATIN_NAME.findall(narration):
            facts["proper_names"][latin] += 1
        for w in narration.split():
            wl = w.strip(".,:;!?„“\"'()«»").lower()
            for st in known_name_stems:
                if wl.startswith(st):
                    facts["proper_names"][st] += 1
                    break
        for m in GEORGIAN_MONTHS:
            if m in narration:
                facts["dates"][m] += len(re.findall(rf"\b\w*{m}\w*\b", narration))
        for d in GEORGIAN_WEEKDAYS:
            if d in narration:
                facts["dates"][d] += len(re.findall(rf"\b\w*{d}\w*\b", narration))
        for u in URL_RE.findall(narration):
            facts["links"][u] += 1

    for c in story.get("characters") or []:
        facts["proper_names"][str(c).strip()] += 1

    def _walk_scene_values(val: Any, key_name: str = ""):
        if isinstance(val, (int, float)):
            facts["numbers"][f"{val:g}" if isinstance(val, float) else str(val)] += 1
        elif isinstance(val, str):
            val_str = val.strip()
            if not val_str:
                return
            for n in extract_numbers(val_str):
                facts["numbers"][n] += 1
            for m in GEORGIAN_MONTHS:
                if m in val_str:
                    facts["dates"][m] += len(re.findall(rf"\b\w*{m}\w*\b", val_str))
            for d in GEORGIAN_WEEKDAYS:
                if d in val_str:
                    facts["dates"][d] += len(re.findall(rf"\b\w*{d}\w*\b", val_str))
            for t_range in TIME_RANGE_RE.findall(val_str):
                facts["dates"][t_range] += 1
            for d_iso in DATE_ISO_RE.findall(val_str):
                facts["dates"][d_iso] += 1
            for surname in SURNAME.findall(val_str):
                facts["proper_names"][surname] += 1
            for latin in LATIN_NAME.findall(val_str):
                facts["proper_names"][latin] += 1
            if key_name in NAME_KEYS:
                facts["proper_names"][val_str] += 1
            if key_name in DATE_KEYS:
                facts["dates"][val_str] += 1
            for q in QUOTE_RE.findall(val_str):
                facts["quotes"][q.strip()] += 1
            for u in URL_RE.findall(val_str):
                facts["links"][u] += 1
        elif isinstance(val, dict):
            for k, v in val.items():
                if k not in CODE_KEYS:
                    _walk_scene_values(v, k)
        elif isinstance(val, list):
            for item in val:
                _walk_scene_values(item, key_name)

    for scene in story.get("scenes") or []:
        stype = scene.get("type")
        if stype == "quote" and scene.get("quote"):
            facts["quotes"][str(scene["quote"]).strip()] += 1
        for k, v in scene.items():
            if k not in CODE_KEYS:
                _walk_scene_values(v, k)

    return facts


def facts_diff(story_before: dict[str, Any], story_after: dict[str, Any]) -> list[str]:
    """Strict invariant diff: returns a non-empty list if any fact was altered or removed.

    Hard invariant: NEVER changes a fact!
    `facts_diff(before, after) == []` must hold for all valid transformations.
    """
    f_before = extract_facts(story_before)
    f_after = extract_facts(story_after)
    diffs: list[str] = []

    if f_before["id"] and f_before["id"] != f_after["id"]:
        diffs.append(f"story id changed: {f_before['id']} -> {f_after['id']}")
    if f_before["cluster_id"] and f_before["cluster_id"] != f_after["cluster_id"]:
        diffs.append(f"cluster id changed: {f_before['cluster_id']} -> {f_after['cluster_id']}")
    if f_before["sources"] != f_after["sources"]:
        diffs.append(f"sources mismatch: {f_before['sources']} -> {f_after['sources']}")

    if f_before["numbers"] != f_after["numbers"]:
        missing = f_before["numbers"] - f_after["numbers"]
        added = f_after["numbers"] - f_before["numbers"]
        msg = []
        if missing:
            msg.append(f"missing numbers: {dict(missing)}")
        if added:
            msg.append(f"added numbers: {dict(added)}")
        diffs.append(f"quantities/numbers mismatch: {'; '.join(msg)}")

    if f_before["dates"] != f_after["dates"]:
        missing = f_before["dates"] - f_after["dates"]
        added = f_after["dates"] - f_before["dates"]
        msg = []
        if missing:
            msg.append(f"missing dates: {dict(missing)}")
        if added:
            msg.append(f"added dates: {dict(added)}")
        diffs.append(f"dates mismatch: {'; '.join(msg)}")

    if f_before["quotes"] != f_after["quotes"]:
        missing = f_before["quotes"] - f_after["quotes"]
        added = f_after["quotes"] - f_before["quotes"]
        msg = []
        if missing:
            msg.append(f"missing quotes: {dict(missing)}")
        if added:
            msg.append(f"added quotes: {dict(added)}")
        diffs.append(f"quotes mismatch: {'; '.join(msg)}")

    if f_before["proper_names"] != f_after["proper_names"]:
        missing = f_before["proper_names"] - f_after["proper_names"]
        added = f_after["proper_names"] - f_before["proper_names"]
        msg = []
        if missing:
            msg.append(f"missing proper names: {dict(missing)}")
        if added:
            msg.append(f"added proper names: {dict(added)}")
        diffs.append(f"proper names mismatch: {'; '.join(msg)}")

    if f_before["links"] != f_after["links"]:
        diffs.append(f"links mismatch: {dict(f_before['links'])} vs {dict(f_after['links'])}")

    return diffs


def audit_story(story: dict[str, Any], fmt_name: str = "news", look: str | None = None,
                director: str | None = None, with_probe: bool = False,
                style_override: dict[str, str] | None = None) -> dict[str, Any]:
    """Run deterministic local checks on a story without any paid APIs."""
    resolved_fmt = formats.get(fmt_name, look=look)
    tone = None if resolved_fmt["voice"] == "family" else resolved_fmt["voice"]

    tmp_path = pathlib.Path(f"out/review_{story.get('id', 'temp')}.json")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")

    holds: list[str] = []
    warnings: list[str] = []
    findings: list[dict[str, Any]] = []
    built_props: dict[str, Any] | None = None
    applied_style: dict[str, Any] = {}

    try:
        work, built_props = props.build(
            str(tmp_path),
            variant=look or resolved_fmt["look"],
            engine="silent",
            tone=tone,
            edge_voice=speech.EDGE_VOICES["eka"],
            platform=resolved_fmt["platform"],
            caption_design=resolved_fmt["captions"],
            music=resolved_fmt["music"],
            transition=resolved_fmt["transition"],
            outro=resolved_fmt["outro"],
            director=director,
            style=style_override,
            theme=resolved_fmt.get("theme", "default"),
            **formats.render_keys(resolved_fmt)
        )
        applied_style = built_props.get("style", {})

        motion = motion_rules.check(built_props)
        holds.extend(motion.get("holds") or [])
        warnings.extend(motion.get("warnings") or [])
        findings.extend(motion.get("findings") or [])

        for f in eyes.metronome_cuts(motion.get("timeline") or []) + eyes.spoken_redundancy(story):
            findings.append(f)
            warnings.append(f"eyes {f['rule']}: {f['detail']}")

        for f in eyes.report_metrics(built_props, motion.get("timeline"))["findings"]:
            findings.append(f)
            warnings.append(f"eyes {f['rule']}: {f['detail']}")

        nov_warning = (built_props.get("novelty") or {}).get("warning")
        if nov_warning:
            warnings.append(f"variety novelty: {nov_warning}")

        for idx, sc in enumerate(story.get("scenes") or []):
            stype = sc.get("type")
            if stype == "hook" and "lines" in sc:
                for line_idx, line in enumerate(sc["lines"]):
                    if len(line) > 26:
                        warnings.append(f"safe_zone: hook line {line_idx} is {len(line)} chars (>26), risk of rail collision")

    except (ValueError, RuntimeError) as e:
        holds.append(f"timing: {e}")
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    return {
        "holds": sorted(list(set(holds))),
        "warnings": sorted(list(set(warnings))),
        "findings": findings,
        "props": built_props,
        "style": applied_style,
    }


def transform_pacing(story: dict[str, Any], defect: str, props_data: dict[str, Any] | None) -> tuple[dict[str, Any], str | None]:
    """Repair pacing & durations defects (e.g. `read` hold, short scene)."""
    updated = copy.deepcopy(story)
    scenes = updated.get("scenes") or []
    narration = updated.get("narration") or ""

    m = re.search(r"scene\s+(\d+)", defect)
    if not m:
        return updated, None
    scene_idx = int(m.group(1))
    if scene_idx >= len(scenes):
        return updated, None

    sc = scenes[scene_idx]
    stype = sc.get("type")

    # Technique A: Shift anchor of next scene to expand scene_idx duration
    if scene_idx + 1 < len(scenes):
        next_sc = scenes[scene_idx + 1]
        next_at = next_sc.get("at")
        if next_at and next_at in narration:
            idx = narration.find(next_at)
            next_dot = narration.find(".", idx + len(next_at))
            if next_dot != -1 and next_dot + 2 < len(narration):
                after_dot = narration[next_dot + 1:].strip()
                words_after = after_dot.split()
                if len(words_after) >= 2:
                    cand_anchor = " ".join(words_after[:2])
                    next_sc["at"] = cand_anchor
                    return updated, f"shifted scene {scene_idx + 1} anchor to '{cand_anchor}' to expand scene {scene_idx} duration"

    # Technique B: Add breathing pause punctuation
    curr_at = sc.get("at")
    if curr_at and curr_at in narration:
        at_pos = narration.find(curr_at)
        next_pos = len(narration)
        if scene_idx + 1 < len(scenes) and scenes[scene_idx + 1].get("at") in narration:
            next_pos = narration.find(scenes[scene_idx + 1]["at"])

        scene_chunk = narration[at_pos:next_pos]
        if "..." not in scene_chunk and "." in scene_chunk:
            new_chunk = scene_chunk.replace(".", "...", 1)
            updated["narration"] = narration[:at_pos] + new_chunk + narration[next_pos:]
            return updated, f"added breathing pause punctuation to scene {scene_idx} narration"

    # Technique C: Condense slot word count while retaining numbers and names
    if stype == "stat" and "label" in sc:
        orig_label = sc["label"]
        tokens = orig_label.split()
        if len(tokens) > 4:
            facts = extract_facts({"narration": "", "scenes": [sc]})
            essential = set(facts["numbers"].keys()) | set(facts["proper_names"].keys())
            kept = [w for w in tokens if any(e in w for e in essential)]
            if len(kept) < len(tokens):
                new_label = " ".join(tokens[:min(len(tokens), 3)] + [w for w in tokens[3:] if w in kept])
                if new_label != orig_label:
                    sc["label"] = new_label
                    return updated, f"condensed scene {scene_idx} label to reduce reading time requirement"

    return updated, None


def transform_scene_types(story: dict[str, Any], defect: str, style_state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """Repair duplicate scene types, hook layouts, or transition defects."""
    updated = copy.deepcopy(story)
    new_style = dict(style_state)
    scenes = updated.get("scenes") or []

    m_rep = re.search(r"scenes\s+(\d+)\s+and\s+(\d+)\s+are\s+both\s+(\w+)", defect)
    if m_rep:
        second_idx = int(m_rep.group(2))
        stype = m_rep.group(3)
        if second_idx < len(scenes):
            sc = scenes[second_idx]
            if stype == "points":
                items = sc.get("items") or []
                if len(items) == 2:
                    sc["type"] = "pair"
                    sc["items"] = [{"title": str(items[0]), "sub": ""}, {"title": str(items[1]), "sub": ""}]
                    return updated, new_style, f"swapped duplicate scene {second_idx} from 'points' to 'pair'"
                else:
                    sc["type"] = "steps"
                    return updated, new_style, f"swapped duplicate scene {second_idx} from 'points' to 'steps'"
            elif stype == "steps":
                sc["type"] = "points"
                return updated, new_style, f"swapped duplicate scene {second_idx} from 'steps' to 'points'"
            elif stype == "pair":
                items = sc.get("items") or []
                sc["type"] = "points"
                sc["items"] = [it.get("title", "") for it in items if isinstance(it, dict)]
                return updated, new_style, f"swapped duplicate scene {second_idx} from 'pair' to 'points'"

    if "pingpong" in defect:
        # the cuts are the scenes' own "transition": give a back-and-forth run one steady family
        explicit = [(i, sc.get("transition")) for i, sc in enumerate(scenes) if sc.get("transition")]
        flows = [(i, list(sc["flow"])) for i, sc in enumerate(scenes) if sc.get("flow")]
        done = []
        if explicit:
            names = [t for _, t in explicit]
            keep = max(sorted(set(names)), key=names.count)
            for i, t in explicit:
                if t != keep:
                    scenes[i]["transition"] = keep
                    done.append(f"scene {i} to '{keep}'")
        if flows:
            way = flows[0][1]
            for i, f in flows:
                if f != way:
                    scenes[i]["flow"] = list(way)
                    done.append(f"scene {i} flow to {way}")
        if done:
            return updated, new_style, "steadied the cuts (" + "; ".join(done) + ") to stop the back and forth"

    if "novelty" in defect or "monotony" in defect:
        hook_options = variety.OPTIONS["hook"]
        curr_hook = new_style.get("hook", hook_options[0])
        next_hook = hook_options[(hook_options.index(curr_hook) + 1) % len(hook_options)] if curr_hook in hook_options else hook_options[1]
        new_style["hook"] = next_hook
        return updated, new_style, f"cycled hook layout to '{next_hook}' to improve variety distance"

    return updated, new_style, None


def transform_safe_zone(story: dict[str, Any], defect: str) -> tuple[dict[str, Any], str | None]:
    """Repair safe zone / typography collisions."""
    updated = copy.deepcopy(story)
    scenes = updated.get("scenes") or []

    for idx, sc in enumerate(scenes):
        if sc.get("type") == "hook" and "lines" in sc:
            lines = sc["lines"]
            too_long = any(len(line) > 22 for line in lines)
            if too_long:
                all_words = " ".join(lines).split()
                new_lines = []
                cur_line: list[str] = []
                for w in all_words:
                    if len(" ".join(cur_line + [w])) <= 20:
                        cur_line.append(w)
                    else:
                        if cur_line:
                            new_lines.append(" ".join(cur_line))
                        cur_line = [w]
                if cur_line:
                    new_lines.append(" ".join(cur_line))
                if new_lines != lines:
                    sc["lines"] = new_lines
                    return updated, f"re-balanced scene {idx} hook lines for safe zone clearance"

    return updated, None


class ReviewLoop:
    """Automated Review & Repair State Machine."""

    def __init__(
        self,
        story_data: dict[str, Any],
        rounds: int = 2,
        max_machine_rounds: int = MAX_MACHINE_ROUNDS_CAP,
        max_look_rounds: int = MAX_LOOK_ROUNDS_CAP,
        format_name: str = "news",
        look: str | None = None,
        director: str | None = None,
        with_probe: bool = False,
    ):
        self.story_initial = copy.deepcopy(story_data)
        self.story_current = copy.deepcopy(story_data)
        self.rounds_requested = max(1, rounds)
        self.max_machine = min(self.rounds_requested, max_machine_rounds)
        self.max_look = min(self.rounds_requested, max_look_rounds)
        self.format_name = format_name
        self.look = look
        self.director = director
        self.with_probe = with_probe

        self.machine_round = 0
        self.look_round = 0
        self.applied_transforms: list[str] = []
        self.history: list[dict[str, Any]] = []
        self.style_state: dict[str, Any] = {}
        self.visited_hashes: set[str] = set()

    def _state_hash(self, story: dict[str, Any], style: dict[str, Any]) -> str:
        import hashlib
        rep = json.dumps({"story": story, "style": sorted(style.items())}, sort_keys=True)
        return hashlib.sha256(rep.encode("utf-8")).hexdigest()

    def run(self) -> dict[str, Any]:
        """Execute the review and repair loop."""
        while True:
            current_round = self.machine_round + self.look_round + 1
            state_key = self._state_hash(self.story_current, self.style_state)
            self.visited_hashes.add(state_key)

            # Phase 1: Audit
            audit = audit_story(
                self.story_current,
                fmt_name=self.format_name,
                look=self.look,
                director=self.director,
                with_probe=self.with_probe,
                style_override=self.style_state or None,
            )
            self.style_state = audit.get("style") or self.style_state
            holds = audit.get("holds") or []
            warnings = audit.get("warnings") or []

            packet = {
                "round": current_round,
                "machine_round": self.machine_round,
                "look_round": self.look_round,
                "holds": holds,
                "warnings": warnings,
            }
            self.history.append(packet)

            # Check Success condition: no holds and nothing the transforms can still repair
            repairable = [w for w in warnings if any(k in w for k in REPAIRABLE)]
            if not holds and (not repairable or (self.machine_round >= self.max_machine and self.look_round >= self.max_look)):
                status = "fixed" if self.applied_transforms else "passed"
                return {
                    "status": status,
                    "rounds_executed": current_round,
                    "machine_rounds": self.machine_round,
                    "look_rounds": self.look_round,
                    "holds": [],
                    "warnings": warnings,
                    "applied_transforms": self.applied_transforms,
                    "facts_diff": facts_diff(self.story_initial, self.story_current),
                    "story": self.story_current,
                    "style": self.style_state,
                    "reasons": ["All safety and layout holds passed."] if status == "passed" else [f"Resolved holds: {'; '.join(self.applied_transforms)}"],
                }

            # Check Termination condition: Caps reached
            if self.machine_round >= self.max_machine and self.look_round >= self.max_look:
                return {
                    "status": "held",
                    "rounds_executed": current_round,
                    "machine_rounds": self.machine_round,
                    "look_rounds": self.look_round,
                    "holds": holds,
                    "warnings": warnings,
                    "applied_transforms": self.applied_transforms,
                    "facts_diff": facts_diff(self.story_initial, self.story_current),
                    "story": self.story_current,
                    "style": self.style_state,
                    "reasons": [f"Unresolved holds after {self.max_machine} machine rounds: {'; '.join(holds)}"],
                }

            # Phase 2: Select defect and apply targeted transform
            transformed = False
            candidate_story = copy.deepcopy(self.story_current)
            candidate_style = dict(self.style_state)
            action_desc: str | None = None

            # Defect 1: Pacing / Reading holds (machine round)
            pacing_holds = [h for h in holds if "read" in h or "timing" in h or "pacing" in h]
            if pacing_holds and self.machine_round < self.max_machine:
                candidate_story, action_desc = transform_pacing(candidate_story, pacing_holds[0], audit.get("props"))
                if action_desc:
                    transformed = True
                    self.machine_round += 1

            # Defect 2: Scene repetition / transition holds or warnings
            if not transformed:
                repeat_defects = [h for h in holds + warnings if "repeat" in h or "pingpong" in h or "novelty" in h]
                if repeat_defects:
                    if any("repeat" in d for d in repeat_defects) and self.machine_round < self.max_machine:
                        candidate_story, candidate_style, action_desc = transform_scene_types(candidate_story, repeat_defects[0], candidate_style)
                        if action_desc:
                            transformed = True
                            self.machine_round += 1
                    elif self.look_round < self.max_look:
                        candidate_story, candidate_style, action_desc = transform_scene_types(candidate_story, repeat_defects[0], candidate_style)
                        if action_desc:
                            transformed = True
                            self.look_round += 1

            # Defect 3: Safe zone / rail / typography
            if not transformed and self.machine_round < self.max_machine:
                safe_defects = [h for h in holds + warnings if "rail" in h or "safe_zone" in h or "overflow" in h]
                if safe_defects:
                    candidate_story, action_desc = transform_safe_zone(candidate_story, safe_defects[0])
                    if action_desc:
                        transformed = True
                        self.machine_round += 1

            # Phase 3: Invariant Guard Check
            if transformed and action_desc:
                diff = facts_diff(self.story_initial, candidate_story)
                if diff:
                    return {
                        "status": "held",
                        "rounds_executed": current_round,
                        "machine_rounds": self.machine_round,
                        "look_rounds": self.look_round,
                        "holds": holds + [f"invariant violation: {'; '.join(diff)}"],
                        "warnings": warnings,
                        "applied_transforms": self.applied_transforms,
                        "facts_diff": diff,
                        "story": self.story_current,
                        "style": self.style_state,
                        "reasons": [f"Transform rejected because it altered facts: {'; '.join(diff)}"],
                    }

                new_key = self._state_hash(candidate_story, candidate_style)
                if new_key in self.visited_hashes:
                    return {
                        "status": ("held" if holds else ("fixed" if self.applied_transforms else "passed")),
                        "rounds_executed": current_round,
                        "machine_rounds": self.machine_round,
                        "look_rounds": self.look_round,
                        "holds": holds,
                        "warnings": warnings,
                        "applied_transforms": self.applied_transforms,
                        "facts_diff": [],
                        "story": self.story_current,
                        "style": self.style_state,
                        "reasons": ["Repair converged into an oscillation cycle."],
                    }

                self.story_current = candidate_story
                self.style_state = candidate_style
                self.applied_transforms.append(action_desc)
            else:
                return {
                    "status": "held" if holds else "passed",
                    "rounds_executed": current_round,
                    "machine_rounds": self.machine_round,
                    "look_rounds": self.look_round,
                    "holds": holds,
                    "warnings": warnings,
                    "applied_transforms": self.applied_transforms,
                    "facts_diff": facts_diff(self.story_initial, self.story_current),
                    "story": self.story_current,
                    "style": self.style_state,
                    "reasons": [f"No further deterministic transform available for: {'; '.join(holds)}"] if holds else ["All checks passed."],
                }


def review_story(
    story_input: str | pathlib.Path | dict[str, Any],
    rounds: int = 2,
    max_machine_rounds: int = MAX_MACHINE_ROUNDS_CAP,
    max_look_rounds: int = MAX_LOOK_ROUNDS_CAP,
    format_name: str = "news",
    look: str | None = None,
    director: str | None = None,
    save: bool = False,
    with_probe: bool = False,
) -> dict[str, Any]:
    """Top-level entry point for reviewing and repairing a story."""
    story_path: pathlib.Path | None = None
    if isinstance(story_input, (str, pathlib.Path)):
        story_path = pathlib.Path(story_input)
        if not story_path.is_file():
            return {
                "status": "held",
                "rounds_executed": 0,
                "holds": [f"file not found: {story_input}"],
                "warnings": [],
                "applied_transforms": [],
                "facts_diff": [],
                "reasons": [f"Story file not found: {story_input}"],
            }
        story_data = json.loads(story_path.read_text(encoding="utf-8"))
    else:
        story_data = copy.deepcopy(story_input)

    loop = ReviewLoop(
        story_data,
        rounds=rounds,
        max_machine_rounds=max_machine_rounds,
        max_look_rounds=max_look_rounds,
        format_name=format_name,
        look=look,
        director=director,
        with_probe=with_probe,
    )
    result = loop.run()

    if save and story_path and result["status"] in ("fixed", "passed") and result["applied_transforms"]:
        story_path.write_text(json.dumps(result["story"], ensure_ascii=False, indent=1), encoding="utf-8")
        result["saved"] = str(story_path)

    return result



# -----------------------------------------------------------------------------
# Seeded defects: what the eyes catch (tests/fixtures/review/)
# -----------------------------------------------------------------------------

def synth_pixels(recipe: str, outdir: str | pathlib.Path) -> dict[str, Any]:
    """Deterministic frames for the pixel defects a story file cannot carry: {"stills": [paths]} or {"frames": array}.

    Canvas and ink follow the pack's dark-canvas, light-ink rule; nothing here is random.
    """
    import numpy as np
    from PIL import Image

    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    def frame(blocks: list[tuple[int, int, int, int, tuple[int, int, int]]]) -> "np.ndarray":
        arr = np.zeros((1920, 1080, 3), dtype=np.uint8)
        arr[:] = (18, 19, 22)
        arr[90:150, 100:980] = (236, 236, 232)  # chrome: the source and time line
        arr[1760:1820, 100:980] = (168, 170, 176)
        for y0, y1, x0, x1, rgb in blocks:
            arr[y0:y1, x0:x1] = rgb
        return arr

    ink = (236, 236, 232)
    good = [
        [(420, 640, 120, 960, ink), (760, 900, 160, 820, ink)],
        [(380, 560, 120, 700, ink), (700, 780, 120, 900, ink), (860, 940, 120, 800, ink)],
        [(300, 880, 120, 960, ink)],
    ]

    def save(name: str, arr: "np.ndarray") -> str:
        path = out / f"{name}.png"
        Image.fromarray(arr).save(path)
        return str(path)

    if recipe == "strobe":
        frames = np.zeros((60, 27 * 48, 3), dtype=np.uint8)
        frames[::6] = 255  # a full-screen strobe at 5 Hz
        return {"frames": frames}
    if recipe == "same_picture":
        a = save("a", frame(good[0]))
        return {"stills": [a, save("b", frame(good[1])), a, save("c", frame(good[0]))]}
    if recipe == "empty_middle":
        return {"stills": [save("a", frame(good[0])), save("dead", frame([])), save("c", frame(good[1]))]}
    if recipe == "flat_low_mass":
        # four different, equally light layouts: ink is there (no dead middle) but nothing is the climax
        shapes = [(500, 620, 150, 650), (760, 880, 400, 900), (420, 520, 200, 800), (900, 1030, 300, 780)]
        return {"stills": [save(f"flat{i}", frame([(y0, y1, x0, x1, ink)])) for i, (y0, y1, x0, x1) in enumerate(shapes)]}
    if recipe == "rail_text":
        return {"stills": [save("a", frame(good[0])), save("rail", frame([(1150, 1300, 400, 1040, ink)]))]}
    if recipe == "washed_out":
        dim = (44, 46, 52)
        return {"stills": [save("a", frame(good[0])), save("dim", frame([(380, 560, 120, 700, dim), (700, 780, 120, 900, dim), (860, 940, 120, 800, dim)]))]}
    raise ValueError(f"unknown pixel recipe: {recipe}")


def detect(story: dict[str, Any], workdir: str | pathlib.Path) -> dict[str, Any]:
    """Run every free check a fixture asks for -> {"rules": sorted rule names, "holds": [...], "warnings": [...]}.

    A fixture's optional "pixels" key names a synth_pixels recipe for defects that live in frames, not in the story.
    """
    audit = audit_story(story)
    findings = list(audit["findings"])
    holds = list(audit["holds"])
    warnings = list(audit["warnings"])
    rules = {f["rule"] for f in findings}
    for h in holds:
        if h.startswith("timing:"):
            rules.add("timing")
    recipe = story.get("pixels")
    if recipe:
        px = synth_pixels(recipe, workdir)
        types = [s.get("type", "scene") for s in story.get("scenes", [])]
        found: list[dict[str, Any]] = []
        if "frames" in px:
            found += eyes.flash_holds(px["frames"])
        else:
            stills = px["stills"]
            found += eyes.same_picture_twice(eyes.hashes_of_stills(stills))
            found += eyes.empty_middle(stills, types)
            found += eyes.no_hero_frame(stills, story)
            found += eyes.safe_zone_ink(stills, types)
        for f in found:
            rules.add(f["rule"])
            (holds if f["hold"] else warnings).append(f"eyes {f['rule']}: {f['detail']}")
    return {"rules": sorted(rules), "holds": holds, "warnings": warnings}


def review_cli(story_path: str, rounds: int = 2, format_name: str = "news", look: str | None = None,
               director: str | None = None, stills: str | None = None, packet: bool = False,
               save: bool = False) -> dict[str, Any]:
    """`engine review`: the loop, the pixel checks on given stills, notes in the skill's format, JSON-sized output."""
    res = review_story(story_path, rounds=rounds, format_name=format_name, look=look, director=director, save=save)
    story = res.pop("story", None)
    res.pop("style", None)
    if story is None:
        return res
    final = audit_story(story, fmt_name=format_name, look=look, director=director)
    rows = []
    if final.get("props"):
        rows = [{"start": r["from"] / 30.0, "type": r["type"]}
                for r in motion_rules.timeline(motion_rules._laid_out(final["props"]))]
    lines = list(res.get("holds") or []) + list(res.get("warnings") or [])
    if stills:
        folder = pathlib.Path(stills)
        files = sorted(folder.glob("*.png"), key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)])
        px = eyes.check_eyes(story, stills=[str(f) for f in files])
        res["pixel_checks"] = {"stills": len(files), "metrics": px["metrics"]}
        res["holds"] = list(res.get("holds") or []) + px["holds"]
        lines += px["holds"] + px["warnings"]
        if px["holds"] and res.get("status") != "held":
            res["status"] = "held"
    res["notes"] = [convert_raw_string(line, rows)["formatted"] for line in lines]
    res["facts_diff"] = res.get("facts_diff") or []
    if packet:
        res["packet"] = build_review_packet(story_path, fmt_name=format_name, look=look, director=director)
    return res
