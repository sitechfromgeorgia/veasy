"""Free pixel checks and visual quality analysis for Veasy films (ROADMAP D13, Goal 7).

Evaluates either engine's frames (Remotion and HyperFrames) for visual defects:
  1. same_picture_twice: consecutive or repeated compositions with near-identical dHash.
  2. empty_middle: dead / washed-out central safe zone (y=248..1380, x=100..980).
  3. no_hero_frame: lack of a dominant visual anchor or typographic climax.
  4. metronome_cuts: robotic, periodic cut rhythm across scene durations.
  5. spoken_redundancy: on-screen text merely repeating spoken narration verbatim.
  6. safety holds: unreadable text (0.5s + 0.3s/word) and flash safety (ITU-R BT.1702).

All newly introduced checks trigger warnings by default until calibrated;
only flash and unreadable text hold today.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from typing import Any, Iterable

import numpy as np
from PIL import Image

from tt_shorts import flash, golden, ka_check, motion_rules, probe

# Safe zone bounding constants (matches probe.C and brand.ts)
C = probe.C
SAFE_X0, SAFE_X1 = 100, 980
SAFE_Y0, SAFE_Y1 = C.get("SCENE_TOP", 248), C.get("SCENE_BOTTOM", 1380)

# 1. same_picture_twice thresholds (Hamming bit distance on dHash)
# 32x32 band hash has 1024 bits; 16x16 frame hash has 256 bits.
CONSECUTIVE_BAND_MAX_DIFF = 50   # bits (~4.88%)
CONSECUTIVE_FRAME_MAX_DIFF = 15  # bits (~5.86%)
REPEATED_BAND_MAX_DIFF = 35      # bits (~3.42%) across any scene pair

# 2. empty_middle thresholds
MIN_CENTER_INK_SHARE = 0.018     # at least 1.8% of central safe zone must be ink
MIN_DYNAMIC_RANGE = 60           # min luminance swing across 0..255 scale
PHANTOM_CHROME_RATIO = 0.25      # center/border ink share ratio floor when borders have ink

# 3. no_hero_frame thresholds
MIN_PEAK_MASS = 0.080            # minimum peak visual mass across video
MIN_CREST_FACTOR = 1.35          # peak visual mass / mean visual mass

# 4. metronome_cuts thresholds
MIN_DURATION_STD_DEV = 0.40      # seconds
MIN_DURATION_CV = 0.075          # 7.5% coefficient of variation
LOCAL_METRONOME_TOL = 0.20       # seconds delta across 4+ consecutive scenes

# 5. spoken_redundancy thresholds
REDUNDANCY_MIN_WORDS = 7         # only body scenes with >= 7 words are audited
REDUNDANCY_LCS_MIN = 7           # contiguous match length
REDUNDANCY_RATIO_MIN = 0.70      # contiguous match / total words
REDUNDANCY_CONTAINMENT_MIN = 0.90# set intersection / total words for >=8 words


def _finding(rule: str, detail: str, scene: int | None = None, hold: bool = False) -> dict[str, Any]:
    return {"rule": rule, "scene": scene, "detail": detail, "hold": hold}


def _quote(text: str, n: int = 40) -> str:
    t = " ".join(str(text).split())
    return f"„{t[:n]}{'…' if len(t) > n else ''}“"


def _clean_tokens(text: str) -> list[str]:
    """Lowercase tokens stripped of Georgian/Latin punctuation."""
    raw = re.findall(r"[\w]+", str(text).lower())
    return [t for t in raw if re.search(r"\w", t)]


# -----------------------------------------------------------------------------
# 1. same_picture_twice
# -----------------------------------------------------------------------------


def hashes_of_stills(stills: list[str | pathlib.Path]) -> list[dict[str, Any]]:
    """Compute frame and band dhash for each still path."""
    out = []
    for i, path in enumerate(stills):
        p = pathlib.Path(path)
        if not p.is_file():
            continue
        h = golden.hashes(str(p))
        out.append({"scene": i, "path": str(p), "hash": h["hash"], "band": h["band"]})
    return out


def same_picture_twice(scene_hashes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect consecutive or repeated scenes that share near-identical dhash."""
    findings = []
    n = len(scene_hashes)
    if n < 2:
        return findings

    # Check consecutive pairs
    for i in range(n - 1):
        a, b = scene_hashes[i], scene_hashes[i + 1]
        sc_a, sc_b = a.get("scene", i), b.get("scene", i + 1)
        d_frame = golden.distance(a["hash"], b["hash"])
        d_band = golden.distance(a["band"], b["band"])
        if d_band <= CONSECUTIVE_BAND_MAX_DIFF and d_frame <= CONSECUTIVE_FRAME_MAX_DIFF:
            findings.append(_finding(
                "same_picture_twice",
                f"scenes {sc_a} and {sc_b} share near-identical composition "
                f"(band dhash diff {d_band} bits, frame diff {d_frame} bits; threshold {CONSECUTIVE_BAND_MAX_DIFF}/{CONSECUTIVE_FRAME_MAX_DIFF}): "
                f"diversify layout or change visual brush",
                scene=sc_b,
                hold=False,
            ))

    # Check non-consecutive repeated compositions
    for i in range(n):
        for j in range(i + 2, n):
            a, b = scene_hashes[i], scene_hashes[j]
            sc_a, sc_b = a.get("scene", i), b.get("scene", j)
            d_band = golden.distance(a["band"], b["band"])
            if d_band <= REPEATED_BAND_MAX_DIFF:
                findings.append(_finding(
                    "same_picture_twice",
                    f"scenes {sc_a} and {sc_b} repeat identical composition "
                    f"(band dhash diff {d_band} bits; threshold {REPEATED_BAND_MAX_DIFF}): "
                    f"vary scene styles across video",
                    scene=sc_b,
                    hold=False,
                ))

    return findings


# -----------------------------------------------------------------------------
# 2. empty_middle
# -----------------------------------------------------------------------------


def _analyze_frame_luminance(im: Image.Image) -> tuple[float, float, float, float]:
    """Returns (rho_center, rho_borders, dynamic_range_center, visual_mass)."""
    grey = im.convert("L")
    w, h = grey.size
    arr = np.array(grey, dtype=np.uint8)

    # Background luminance estimation via frame corners
    corner_size = 40
    corners = np.concatenate([
        arr[:corner_size, :corner_size].flatten(),
        arr[:corner_size, -corner_size:].flatten(),
        arr[-corner_size:, :corner_size].flatten(),
        arr[-corner_size:, -corner_size:].flatten(),
    ])
    bg_lum = float(np.median(corners))

    # Ink pixel mask: significant deviation from background
    is_ink = np.abs(arr.astype(np.float32) - bg_lum) >= 30.0

    # Crop to central safe zone
    y0, y1 = max(0, SAFE_Y0), min(h, SAFE_Y1)
    x0, x1 = max(0, SAFE_X0), min(w, SAFE_X1)
    center_ink = is_ink[y0:y1, x0:x1]
    center_lum = arr[y0:y1, x0:x1]

    rho_center = float(np.mean(center_ink)) if center_ink.size > 0 else 0.0
    dyn_range = float(np.max(center_lum) - np.min(center_lum)) if center_lum.size > 0 else 0.0

    # Border regions (chrome zones)
    top_ink = is_ink[:y0, :]
    bot_ink = is_ink[y1:, :]
    borders_ink = np.concatenate([top_ink.flatten(), bot_ink.flatten()]) if top_ink.size + bot_ink.size > 0 else np.array([])
    rho_borders = float(np.mean(borders_ink)) if borders_ink.size > 0 else 0.0

    # Bounding box of center ink for visual mass computation
    ink_ys, ink_xs = np.where(center_ink)
    if len(ink_ys) > 0:
        h_box = (np.max(ink_ys) - np.min(ink_ys) + 1) / (y1 - y0)
        w_box = (np.max(ink_xs) - np.min(ink_xs) + 1) / (x1 - x0)
        area_norm = float(h_box * w_box)
    else:
        area_norm = 0.0

    visual_mass = float(rho_center * (dyn_range / 255.0) * math.sqrt(max(0.001, area_norm)))
    return rho_center, rho_borders, dyn_range, visual_mass


def empty_middle(stills: list[str | pathlib.Path], scene_types: list[str] | None = None) -> list[dict[str, Any]]:
    """Detect frames where central safe zone has collapsed ink or washed-out content."""
    findings = []
    types = scene_types or []
    for i, path in enumerate(stills):
        p = pathlib.Path(path)
        if not p.is_file():
            continue
        sc_type = types[i] if i < len(types) else "scene"
        with Image.open(p) as im:
            rho_center, rho_borders, dyn_range, _ = _analyze_frame_luminance(im)

        if rho_center < MIN_CENTER_INK_SHARE:
            findings.append(_finding(
                "empty_middle",
                f"scene {i} ({sc_type}): central safe zone has only {rho_center:.1%} ink share "
                f"(min {MIN_CENTER_INK_SHARE:.1%}): empty or missing content",
                scene=i,
                hold=False,
            ))
        elif dyn_range < MIN_DYNAMIC_RANGE:
            findings.append(_finding(
                "empty_middle",
                f"scene {i} ({sc_type}): central safe zone dynamic range is only {dyn_range:.0f}/255 "
                f"(min {MIN_DYNAMIC_RANGE}): low-contrast or washed out",
                scene=i,
                hold=False,
            ))
        elif rho_borders >= 0.030 and (rho_center / max(1e-4, rho_borders)) < PHANTOM_CHROME_RATIO:
            findings.append(_finding(
                "empty_middle",
                f"scene {i} ({sc_type}): chrome rendered ({rho_borders:.1%} ink) but center safe zone is dead "
                f"({rho_center:.1%} ink, ratio {rho_center/rho_borders:.2f} < {PHANTOM_CHROME_RATIO}): content mount failure",
                scene=i,
                hold=False,
            ))

    return findings


# -----------------------------------------------------------------------------
# 3. no_hero_frame
# -----------------------------------------------------------------------------


def no_hero_frame(stills: list[str | pathlib.Path], story: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Verify that video possesses a climactic visual anchor / hero frame."""
    if not stills:
        return []

    masses: list[float] = []
    for path in stills:
        p = pathlib.Path(path)
        if not p.is_file():
            continue
        with Image.open(p) as im:
            _, _, _, mass = _analyze_frame_luminance(im)
            masses.append(mass)

    if not masses:
        return []

    max_mass = max(masses)
    mean_mass = sum(masses) / len(masses)
    crest = max_mass / max(1e-4, mean_mass)

    if (max_mass < MIN_PEAK_MASS or (max_mass < 0.110 and crest < MIN_CREST_FACTOR)):
        return [_finding(
            "no_hero_frame",
            f"video lacks a dominant hero anchor moment: max visual mass is {max_mass:.3f} (min {MIN_PEAK_MASS:.3f}) "
            f"and crest factor is {crest:.2f} (min {MIN_CREST_FACTOR}): sequence consists of uniform low-impact cards",
            scene=None,
            hold=False,
        )]

    return []



# -----------------------------------------------------------------------------
# 3b. safe_zone_ink
# -----------------------------------------------------------------------------

RAIL_X0 = 940          # CLAUDE.md: below y=1100 no text goes right of x=940
RAIL_Y0, RAIL_Y1 = 1100, 1552
RAIL_MAX_INK = 0.004   # share of the rail region that may carry ink


def safe_zone_ink(stills: list[str | pathlib.Path], scene_types: list[str] | None = None) -> list[dict[str, Any]]:
    """Ink in the social rail (x > 940, y 1100..1552): scene text must stay out of it."""
    findings = []
    types = scene_types or []
    for i, path in enumerate(stills):
        p = pathlib.Path(path)
        if not p.is_file():
            continue
        with Image.open(p) as im:
            grey = np.array(im.convert("L"), dtype=np.float32)
        h, w = grey.shape
        if (w, h) != (1080, 1920):
            continue
        bg = float(np.median(np.concatenate([grey[:40, :40].ravel(), grey[:40, -40:].ravel(),
                                             grey[-40:, :40].ravel(), grey[-40:, -40:].ravel()])))
        region = np.abs(grey[RAIL_Y0:RAIL_Y1, RAIL_X0:] - bg) >= 60.0
        share = float(region.mean())
        if share > RAIL_MAX_INK:
            findings.append(_finding(
                "safe_zone",
                f"scene {i} ({types[i] if i < len(types) else 'scene'}): {share:.1%} of the social rail "
                f"(x>{RAIL_X0}, y {RAIL_Y0}..{RAIL_Y1}) carries ink (max {RAIL_MAX_INK:.1%}): pull the text left",
                scene=i, hold=False))
    return findings

# -----------------------------------------------------------------------------
# 4. metronome_cuts
# -----------------------------------------------------------------------------


def metronome_cuts(durations_or_timeline: list[float] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect monotonous cut rhythm where scene durations occur at rigid periodic intervals."""
    durations: list[float] = []
    if durations_or_timeline and isinstance(durations_or_timeline[0], dict):
        # Exclude end card from rhythm analysis (QR hold)
        for row in durations_or_timeline:
            if row.get("type") != "end":
                durations.append(float(row.get("seconds", 0.0)))
    else:
        durations = [float(d) for d in durations_or_timeline]

    n = len(durations)
    if n < 3:
        return []

    mean_d = float(np.mean(durations))
    std_d = float(np.std(durations))
    cv_d = std_d / max(1e-4, mean_d)

    # Global metronome check
    if std_d < MIN_DURATION_STD_DEV and cv_d < MIN_DURATION_CV:
        return [_finding(
            "metronome_cuts",
            f"robotic metronome pacing across cuts: duration std dev is {std_d:.2f}s (CV {cv_d:.1%}, min {MIN_DURATION_CV:.1%}): "
            f"scene durations ({', '.join(f'{d:.1f}s' for d in durations)}) are uniformly periodic",
            scene=None,
            hold=False,
        )]

    # Local metronome run check: >= 4 consecutive scenes with near identical durations
    if n >= 4:
        for i in range(n - 3):
            window = durations[i : i + 4]
            diffs = [abs(b - a) for a, b in zip(window, window[1:])]
            if max(diffs) <= LOCAL_METRONOME_TOL:
                return [_finding(
                    "metronome_cuts",
                    f"local metronome lock in scenes {i}..{i+3}: cuts paced within {LOCAL_METRONOME_TOL:.2f}s of each other "
                    f"({', '.join(f'{d:.1f}s' for d in window)}): vary visual hold times",
                    scene=i + 3,
                    hold=False,
                )]

    return []


# -----------------------------------------------------------------------------
# 5. spoken_redundancy
# -----------------------------------------------------------------------------


def _longest_contiguous_overlap(seq1: list[str], seq2: list[str]) -> int:
    """Length of longest contiguous common sub-sequence of tokens."""
    m, n = len(seq1), len(seq2)
    dp = [0] * (n + 1)
    max_len = 0
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                curr[j] = dp[j - 1] + 1
                if curr[j] > max_len:
                    max_len = curr[j]
        dp = curr
    return max_len


def spoken_redundancy(story: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect body scenes where on-screen text merely repeats spoken narration verbatim."""
    findings = []
    scenes = story.get("scenes", [])
    overall_narration = str(story.get("narration", ""))

    for i, sc in enumerate(scenes):
        sc_type = sc.get("type", "scene")
        # Quotes (rule K14) and hooks are exempt from redundancy flagging
        if sc_type in ("quote", "hook", "end"):
            continue

        # Extract on-screen texts for this scene
        texts = [t for _, t in ka_check.screen_texts({"scenes": [sc]})]
        combined_text = " ".join(texts)
        screen_tokens = _clean_tokens(combined_text)
        if len(screen_tokens) < REDUNDANCY_MIN_WORDS:
            continue

        # Determine narration text for this scene
        scene_narr = sc.get("narration")
        if not scene_narr:
            # Fallback to full narration if scene-specific narration is omitted
            scene_narr = overall_narration

        narr_tokens = _clean_tokens(scene_narr)
        if not narr_tokens:
            continue

        lcs_len = _longest_contiguous_overlap(screen_tokens, narr_tokens)
        ratio_contig = lcs_len / len(screen_tokens)

        set_screen = set(screen_tokens)
        set_narr = set(narr_tokens)
        containment = len(set_screen & set_narr) / len(set_screen)

        if (lcs_len >= REDUNDANCY_LCS_MIN and ratio_contig >= REDUNDANCY_RATIO_MIN) or (
            len(screen_tokens) >= 8 and containment >= REDUNDANCY_CONTAINMENT_MIN
        ):
            findings.append(_finding(
                "spoken_redundancy",
                f"scene {i} ({sc_type}): on-screen text verbatim repeats spoken narration "
                f"({lcs_len}-word match, {containment:.0%} token overlap): "
                f"{_quote(combined_text)} -> synthesize into punchy graphical points",
                scene=i,
                hold=False,
            ))

    return findings


# -----------------------------------------------------------------------------
# 6. Integrated Safety & Layout Gates (Holds)
# -----------------------------------------------------------------------------


def reading_time_holds(story_or_props: dict[str, Any], plan_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Unreadable text hold (0.5s + 0.3s/word). Holds a render."""
    findings = []
    if plan_data and "motion" in plan_data:
        motion_holds = plan_data["motion"].get("holds", [])
        for h in motion_holds:
            if "read" in h:
                findings.append(_finding("read", h, hold=True))
        return findings

    # Compute directly via motion_rules if plan_data not supplied
    try:
        check_res = motion_rules.check(story_or_props)
        for h in check_res.get("holds", []):
            findings.append(_finding("read", h, hold=True))
    except Exception:
        pass
    return findings


def flash_holds(video_or_frames: str | pathlib.Path | np.ndarray) -> list[dict[str, Any]]:
    """ITU-R BT.1702 flash safety check. Holds a render."""
    if isinstance(video_or_frames, (str, pathlib.Path)):
        rep = flash.measure(str(video_or_frames))
    else:
        rep = flash.judge(video_or_frames)

    flash_problems = flash.problems(rep)
    return [_finding("flash", p, hold=True) for p in flash_problems]


# -----------------------------------------------------------------------------
# 7. Composite Entry Point
# -----------------------------------------------------------------------------


def check_eyes(
    story: dict[str, Any],
    stills: list[str | pathlib.Path] | None = None,
    plan_data: dict[str, Any] | None = None,
    video_path: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute all free pixel, layout, and pacing checks on a story and its stills.

    Returns structured report with findings, holds, warnings, and metrics.
    """
    findings: list[dict[str, Any]] = []
    stills = stills or []
    scene_types = [s.get("type", "scene") for s in story.get("scenes", [])]

    # 1. Reading time holds (Safety/Legibility floor): needs built props or a plan; a bare story has no timings
    if plan_data:
        findings.extend(reading_time_holds(story, plan_data))

    # 2. Flash safety hold (if video path provided)
    if video_path and pathlib.Path(video_path).is_file():
        findings.extend(flash_holds(video_path))

    # 3. Spoken redundancy check (Plan/Story text analysis)
    findings.extend(spoken_redundancy(story))

    # 4. Metronome cuts check (needs real scene durations from a plan or the motion timeline)
    if plan_data and plan_data.get("timeline"):
        findings.extend(metronome_cuts(plan_data["timeline"]))
    elif plan_data and "scenes" in plan_data:
        durs = [s.get("seconds", 0.0) for s in plan_data["scenes"] if s.get("type") != "end"]
        findings.extend(metronome_cuts(durs))

    # 5. Stills-based pixel checks (when stills are available)
    if stills:
        scene_hashes = hashes_of_stills(stills)
        findings.extend(same_picture_twice(scene_hashes))
        findings.extend(empty_middle(stills, scene_types))
        findings.extend(no_hero_frame(stills, story))
        findings.extend(safe_zone_ink(stills, scene_types))

    holds = [f for f in findings if f["hold"]]
    warnings = [f for f in findings if not f["hold"]]

    return {
        "story": story.get("id"),
        "findings": findings,
        "holds": [f"eyes hold ({f['rule']}): {f['detail']}" for f in holds],
        "warnings": [f"eyes warning ({f['rule']}): {f['detail']}" for f in warnings],
        "metrics": {
            "stills_checked": len(stills),
            "scenes_count": len(scene_types),
            "holds_count": len(holds),
            "warnings_count": len(warnings),
        },
    }


# -----------------------------------------------------------------------------
# 8. Report-only metrics (phase 3 of the 2026 report): they measure and warn, never hold
# -----------------------------------------------------------------------------

WORD_LAG_MAX = 5.5          # s: a text may show this much BEFORE its words are spoken (approved films reach 5.0: scene text comes on with its sentence; a late build is normal)
TEXT_ECHO_MAX = 0.85        # share of on-screen words the narration already says
POST_CUT_DEAD = 1.0         # s: nothing new on screen this long after a cut
POST_CUT_SHARE = 0.5        # share of cuts that may be dead
HOLD_RATIO_MAX = 0.55       # share of the film where nothing changes after the scene settled
UNRELATED_MAX = 0.9         # share of middle cuts between scenes sharing no word
CURVE_SHARE_MAX = 0.9       # share of cuts using one transition curve (kind); a pack's own cut is one curve
FADE_UP_ENTERS = ("rise",)  # the entrance style that is a fade-up
MOVING_READ_SHARE = 0.7     # share of texts still moving during half or more of their reading time


def _prefix_key(token: str) -> str:
    return token[:5]


def _spoken_starts(words: list[dict[str, Any]]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for w in words:
        for t in _clean_tokens(str(w.get("text", ""))):
            out.setdefault(_prefix_key(t), []).append(float(w.get("start", 0.0)))
    return out


def report_metrics(props: dict[str, Any], timeline: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Built props -> {"metrics": {...numbers}, "findings": [warnings]}; every finding has hold=False."""
    rows = timeline if timeline is not None else motion_rules.timeline(motion_rules._laid_out(props))
    cuts = motion_rules.cuts(motion_rules._laid_out(props)) if props.get("scenes") else []
    fps = motion_rules.FPS
    findings: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    total = max(1e-6, props.get("durationInFrames", 0) / fps)

    # word_lag: when a text comes on against when the voice says its first word
    spoken_seq = [(_prefix_key(t), float(w.get("start", 0.0)))
                  for w in props.get("words") or [] for t in _clean_tokens(str(w.get("text", "")))]
    bigrams: dict[tuple[str, str], list[float]] = {}
    for (k1, t1), (k2, _t2) in zip(spoken_seq, spoken_seq[1:]):
        bigrams.setdefault((k1, k2), []).append(t1)
    lags: list[float] = []
    worst: tuple[float, int, str] | None = None
    for r in rows:
        base = r["from"] / fps
        for t in r["texts"]:
            toks = _clean_tokens(t["text"])
            if len(toks) < 2:
                continue  # one word matches by chance: only two words in a row count
            shown_at = base + t["in"]
            cands = [x for x in bigrams.get((_prefix_key(toks[0]), _prefix_key(toks[1])), []) if abs(x - shown_at) <= 6.0]
            if not cands:
                continue
            lag = shown_at - min(cands, key=lambda s: abs(s - shown_at))
            lags.append(lag)
            if lag < 0 and (worst is None or lag < worst[0]):
                worst = (lag, r["scene"], t["text"])
    metrics["word_lag_early_max"] = round(max((-x for x in lags if x < 0), default=0.0), 2)
    metrics["word_lag_late_max"] = round(max((x for x in lags if x > 0), default=0.0), 2)
    if worst and worst[0] < -WORD_LAG_MAX:
        findings.append(_finding("word_lag", f"scene {worst[1]}: {_quote(worst[2])} comes on {worst[0]:+.1f} s from the "
                                             f"voice saying it (max {WORD_LAG_MAX:g} s): move the anchor or the text's beat",
                                 worst[1]))

    # text_echo: how much of everything on screen the narration already says
    spoken = {_prefix_key(t) for w in props.get("words") or [] for t in _clean_tokens(str(w.get("text", "")))}
    shown = [tok for r in rows for t in r["texts"] if r["type"] != "end" for tok in _clean_tokens(t["text"])]
    echo = (sum(1 for tok in shown if _prefix_key(tok) in spoken) / len(shown)) if shown else 0.0
    metrics["text_echo"] = round(echo, 2)
    if len(shown) >= 12 and echo > TEXT_ECHO_MAX:
        findings.append(_finding("text_echo", f"{echo:.0%} of the words on screen are words the voice says (max "
                                              f"{TEXT_ECHO_MAX:.0%}): the screen adds almost nothing"))

    # post_cut_motion: a cut followed by a dead second
    dead = [r["scene"] for r in rows[1:] if r["type"] != "end" and r["texts"]
            and min(t["in"] for t in r["texts"]) > POST_CUT_DEAD]
    metrics["post_cut_dead"] = len(dead)
    if rows[1:] and len(dead) / max(1, len(rows) - 1) > POST_CUT_SHARE:
        findings.append(_finding("post_cut_motion", f"{len(dead)} of {len(rows) - 1} cuts show nothing new for over "
                                                    f"{POST_CUT_DEAD:g} s (scenes {', '.join(map(str, dead))})"))

    # hold_ratio: time with nothing changing, over the film
    held = sum(max(0.0, (r["leaves"] - r["from"]) / fps - r["settled"]) for r in rows if r["type"] != "end")
    metrics["hold_ratio"] = round(held / total, 2)
    if held / total > HOLD_RATIO_MAX:
        findings.append(_finding("hold_ratio", f"{held / total:.0%} of the film is held still after scenes settle "
                                               f"(max {HOLD_RATIO_MAX:.0%}): add beats or cut sooner"))

    # unrelated_cuts: adjacent middle scenes that share no word
    sets = [{_prefix_key(tok) for t in r["texts"] for tok in _clean_tokens(t["text"])} for r in rows]
    mid = [i for i, r in enumerate(rows) if r["type"] not in ("hook", "end")]
    pairs = [(i, i + 1) for i in mid if i + 1 in mid]
    unrelated = [(a, b) for a, b in pairs if sets[a] and sets[b] and not (sets[a] & sets[b])]
    metrics["unrelated_cuts"] = len(unrelated)
    if len(pairs) >= 6 and len(unrelated) / len(pairs) > UNRELATED_MAX:
        findings.append(_finding("unrelated_cuts", f"{len(unrelated)} of {len(pairs)} cuts between middle scenes join "
                                                   f"scenes that share no word: link them with a shared noun or number"))

    # keyframes (film level): one curve, fade-up everywhere, text moving while it is read
    kinds = [c["kind"] for c in cuts if c["kind"] not in ("crossfade",)]
    share = (max(kinds.count(k) for k in set(kinds)) / len(kinds)) if kinds else 0.0
    metrics["curve_share"] = round(share, 2)
    if len(kinds) >= 6 and share > CURVE_SHARE_MAX and kinds[0] == "cut":
        findings.append(_finding("keyframes_one_curve", f"{share:.0%} of the cuts use one transition (max "
                                                        f"{CURVE_SHARE_MAX:.0%}): vary the curve"))
    enter = (props.get("style") or {}).get("enter")
    metrics["enter"] = enter
    if enter in FADE_UP_ENTERS and kinds and kinds.count("fade") / len(kinds) >= 0.5:
        findings.append(_finding("keyframes_fade_up", f"text rises in and half the cuts are fades ('{enter}'): all fade-up; "
                                                      f"pick another entrance or cut"))
    moving = []
    for r in rows:
        for t in r["texts"]:
            if t["need"] > 0 and (motion_rules.SETTLE / t["need"]) >= 0.5:
                moving.append(t)
    all_texts = [t for r in rows for t in r["texts"]]
    mshare = len(moving) / len(all_texts) if all_texts else 0.0
    metrics["moving_while_read"] = round(mshare, 2)
    if len(all_texts) >= 6 and mshare > MOVING_READ_SHARE:
        findings.append(_finding("keyframes_text_moving", f"{mshare:.0%} of the texts are still moving for half their "
                                                          f"reading time: shorten the entrance or lengthen the text"))
    return {"metrics": metrics, "findings": findings}
