"""The edit room's steering wheel: change one scene's words or rhythm, estimate cost with --dry, and redraw only what moved.

Usage:
  python -m tt_shorts.engine steer demo/film-partia.json --scene 1 --set label="21 სექტემბრიდან 2 ნოემბრამდე" --dry
  python -m tt_shorts.engine steer demo/film-partia.json --scene 1 --set label="21 სექტემბრიდან 2 ნოემბრამდე"
  python -m tt_shorts.engine steer demo/film-partia.json --scene 2 --tighter
  python -m tt_shorts.engine steer demo/film-partia.json --scene 2 --breathe
  python -m tt_shorts.engine steer demo/film-partia.json --scene 2 --land
  python -m tt_shorts.engine room  demo/film-partia.json [--video out/film-partia.mp4]
"""
from __future__ import annotations

import copy
import json
import pathlib
import re
import shutil
import time

from tt_shorts import (brand as packs, catalog, costs, directors, flash, formats, motion_rules,
                       news_check, normalize_ka, probe, props, room, segments, speech, store, swipe)

FPS = speech.FPS
TIGHTER_FRAMES = -12   # -0.40s: pulls the cut earlier while preserving reading & pacing floors
BREATHE_FRAMES = 15    # +0.50s: adds breathing room after the scene settles
LAND_FRAMES = 9        # +0.30s: holds the payoff before the cut and marks the key phrase if unspoken

_INDEXED_KEY = re.compile(r"^([a-zA-Z_]\w*)(?:\[(\d+)\])?(?:\.([a-zA-Z_]\w*))?$")


def parse_scene_arg(scene_arg: int | str | None, num_scenes: int) -> int | None:
    """Resolve `--scene 3` or `--scene s3` into an integer index `0..num_scenes-1`."""
    if scene_arg is None or scene_arg == "":
        return None
    if isinstance(scene_arg, int):
        idx = scene_arg
    else:
        s = str(scene_arg).strip().lower()
        if s.startswith("s") and s[1:].isdigit():
            idx = int(s[1:])
        elif s.lstrip("-").isdigit():
            idx = int(s)
        else:
            raise ValueError(f"invalid --scene {scene_arg!r}: pass a scene number 0..{num_scenes - 1} or s0..s{num_scenes - 1}")
    if not (0 <= idx < num_scenes):
        raise ValueError(f"--scene {idx} is out of range (story has {num_scenes} scenes: 0..{num_scenes - 1})")
    return idx


def _min_scene_frames(scene: dict, is_first: bool = False) -> int:
    """Minimum frame count for `scene` so both `speech.MIN_SCENE` and `motion_rules` (`read` and `pacing`) pass."""
    stype = scene.get("type", "")
    cat_min = speech.MIN_SCENE.get(stype, speech.MIN_SCENE_DEFAULT)
    floor_s = max(cat_min, motion_rules.PACING_MIN)
    probe_scene = {**scene, "from": 0, "duration": max(90, round(floor_s * FPS))}
    for idx, (txt, _) in enumerate(motion_rules.scene_texts(probe_scene, first=is_first)):
        need_s = motion_rules.need(txt)
        enter_s = 0.0 if is_first else (motion_rules.ENTER_BASE + motion_rules.STAGGER * idx)
        exit_s = motion_rules.EXIT / FPS
        # Both staggered entrance and REVEAL_CAP must leave at least need_s on screen:
        req1 = enter_s + need_s + exit_s + 0.08
        req2 = (need_s + exit_s + 0.08) / max(0.2, 1.0 - motion_rules.REVEAL_CAP)
        floor_s = max(floor_s, req1, req2)
    return max(round(cat_min * FPS), int(round(floor_s * FPS)) + 1)


def apply_story_steer(story: dict, shown: list[dict], marks: list[int]) -> list[int]:
    """Apply top-level `story['steer']['scenes']` frame offsets to `marks` while respecting minimum scene durations."""
    steer_cfg = (story.get("steer") or {}).get("scenes") or {}
    if not steer_cfg:
        return marks
    out = list(marks)
    n = len(shown)
    for k_str, entry in sorted(steer_cfg.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 999):
        if not str(k_str).isdigit():
            continue
        i = int(k_str)
        if not (0 <= i < n):
            continue
        delta = int((entry or {}).get("frames") or 0)
        if delta == 0:
            continue
        cur_dur = out[i + 1] - out[i]
        min_i = _min_scene_frames(shown[i], is_first=(i == 0))
        if delta < 0:
            give = min(-delta, max(0, cur_dur - min_i))
            if give <= 0:
                continue
            if i < n - 1:
                out[i + 1] -= give
            else:
                out[-1] -= give
        else:
            rem = delta
            if i < n - 1:
                next_dur = out[i + 2] - out[i + 1]
                min_next = _min_scene_frames(shown[i + 1], is_first=False)
                borrow_next = min(rem, max(0, next_dur - min_next))
                if borrow_next > 0:
                    out[i + 1] += borrow_next
                    rem -= borrow_next
            if rem > 0 and i > 0 and i == n - 1:
                prev_dur = out[i] - out[i - 1]
                min_prev = _min_scene_frames(shown[i - 1], is_first=(i - 1 == 0))
                borrow_prev = min(rem, max(0, prev_dur - min_prev))
                if borrow_prev > 0:
                    out[i] -= borrow_prev
                    rem -= borrow_prev
            if rem > 0:
                for j in range(i + 1, len(out)):
                    out[j] += rem
    return out


def _coerce_value(raw_val: str, current_val=None, slot_spec: dict | None = None):
    """Coerce a CLI `--set key=value` string into the right Python type (str, int, float, list, dict)."""
    if not isinstance(raw_val, str):
        return raw_val
    text = raw_val.strip()
    if len(text) >= 2 and ((text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")):
        text = text[1:-1]
    kind = (slot_spec or {}).get("kind")
    if kind == "num" or isinstance(current_val, (int, float)) and not isinstance(current_val, bool):
        try:
            f = float(text)
            return int(f) if f.is_integer() and "." not in text else f
        except ValueError:
            pass
    if text.startswith("[") or text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return text


def parse_set_args(set_args: list[str] | dict | str | None) -> list[tuple[str, str]]:
    """Normalize `--set` inputs (a list of `'k=v'` strings, a single `'k=v'` string, or a dict) into `[(key, val)]`."""
    if not set_args:
        return []
    if isinstance(set_args, dict):
        return [(str(k), v) for k, v in set_args.items()]
    if isinstance(set_args, str):
        set_args = [set_args]
    pairs = []
    for item in set_args:
        if not isinstance(item, str) or "=" not in item:
            raise ValueError(f"invalid --set {item!r}: expected key=value (e.g. --set label=\"...\")")
        k, v = item.split("=", 1)
        k = k.strip()
        if not k:
            raise ValueError(f"invalid --set {item!r}: empty key")
        pairs.append((k, v))
    return pairs


def apply_slot_edits(story: dict, scene_idx: int | None, pairs: list[tuple[str, object]]) -> dict:
    """Apply `(key, value)` edits to a deep copy of `story`.

    Returns `{"story": updated_story, "changed_narration": bool, "edits": [descriptions]}`.
    """
    updated = copy.deepcopy(story)
    scenes = updated.get("scenes") or []
    changed_narration = False
    edits = []
    brushes = catalog.load_all()

    for raw_key, raw_val in pairs:
        if raw_key in ("narration", "cta", "category", "motif", "url") or raw_key.startswith("say."):
            if raw_key.startswith("say."):
                sub = raw_key.split(".", 1)[1]
                updated.setdefault("say", {})[sub] = _coerce_value(str(raw_val))
                changed_narration = True
                edits.append(f"say.{sub}={updated['say'][sub]!r}")
            else:
                val = _coerce_value(str(raw_val), updated.get(raw_key))
                if raw_key == "narration" and val != updated.get("narration"):
                    changed_narration = True
                updated[raw_key] = val
                edits.append(f"{raw_key}={val!r}")
            continue

        if scene_idx is None:
            raise ValueError(f"--set {raw_key}=... requires --scene <0..{len(scenes) - 1}>")

        scene = scenes[scene_idx]
        stype = scene.get("type", "")
        brush_slots = (brushes.get(stype) or {}).get("slots") or {}
        m = _INDEXED_KEY.match(raw_key)
        if not m:
            raise ValueError(f"unsupported slot syntax {raw_key!r} (use slot, list[0], or items[0].field)")
        field, idx_str, subfield = m.group(1), m.group(2), m.group(3)
        spec = brush_slots.get(field)

        if idx_str is None and subfield is None:
            val = _coerce_value(raw_val, scene.get(field), spec)
            scene[field] = val
            edits.append(f"scene {scene_idx} ({stype}).{field}={val!r}")
        elif idx_str is not None and subfield is None:
            idx = int(idx_str)
            arr = scene.get(field)
            if not isinstance(arr, list) or not (0 <= idx < len(arr)):
                raise ValueError(f"scene {scene_idx} ({stype}).{field}[{idx}] out of range")
            of_spec = (spec or {}).get("of") if isinstance(spec, dict) else None
            val = _coerce_value(raw_val, arr[idx], of_spec if isinstance(of_spec, dict) and "kind" in of_spec else None)
            arr[idx] = val
            edits.append(f"scene {scene_idx} ({stype}).{field}[{idx}]={val!r}")
        elif idx_str is not None and subfield is not None:
            idx = int(idx_str)
            arr = scene.get(field)
            if not isinstance(arr, list) or not (0 <= idx < len(arr)) or not isinstance(arr[idx], dict):
                raise ValueError(f"scene {scene_idx} ({stype}).{field}[{idx}].{subfield} out of range")
            of_spec = ((spec or {}).get("of") or {}).get(subfield) if isinstance(spec, dict) else None
            val = _coerce_value(raw_val, arr[idx].get(subfield), of_spec)
            arr[idx][subfield] = val
            edits.append(f"scene {scene_idx} ({stype}).{field}[{idx}].{subfield}={val!r}")
        else:
            obj = scene.setdefault(field, {})
            if not isinstance(obj, dict):
                raise ValueError(f"scene {scene_idx} ({stype}).{field} is not an object")
            of_spec = ((spec or {}).get("of") or {}).get(subfield) if isinstance(spec, dict) else None
            val = _coerce_value(raw_val, obj.get(subfield), of_spec)
            obj[subfield] = val
            edits.append(f"scene {scene_idx} ({stype}).{field}.{subfield}={val!r}")

    return {"story": updated, "changed_narration": changed_narration, "edits": edits}


def _auto_em_candidate(story: dict, scene_idx: int) -> str | None:
    """Find a valid voice-synced `em` phrase for `scene_idx` if the scene has none and its brush supports `em`."""
    scenes = story.get("scenes") or []
    if not (0 <= scene_idx < len(scenes)):
        return None
    s = scenes[scene_idx]
    if s.get("em"):
        return s["em"]
    b = catalog.load_all().get(s.get("type", ""))
    if not b or not (b.get("em") or {}).get("fields"):
        return None
    words = speech.estimate_words(story["narration"])
    try:
        marks = speech.scene_frames(story, words)
    except Exception:
        return None
    t0, t1 = marks[scene_idx] / FPS, marks[scene_idx + 1] / FPS
    slice_words = [w["text"] for w in words if w["end"] > t0 and w["start"] < t1]
    spoken_slice = " ".join(slice_words)
    for field in b["em"]["fields"]:
        top = field.split(".")[0]
        val = s.get(top)
        candidates = []
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            candidates.append(f"{val:g}" if isinstance(val, float) else str(val))
        elif isinstance(val, str) and val.strip():
            candidates.append(val.strip())
            toks = val.strip().split()
            if len(toks) > 2:
                candidates.append(" ".join(toks[:2]))
            if toks:
                candidates.append(toks[0])
        elif isinstance(val, list):
            for it in val:
                if isinstance(it, str) and it.strip():
                    candidates.append(it.strip())
                elif isinstance(it, dict) and "." in field:
                    sub = field.split(".", 1)[1]
                    if isinstance(it.get(sub), str) and it[sub].strip():
                        candidates.append(it[sub].strip())
        for cand in candidates:
            test_story = copy.deepcopy(story)
            test_story["scenes"][scene_idx]["em"] = cand
            if not news_check.spoken(test_story):
                return cand
    return None


def apply_rhythm_verb(story: dict, scene_idx: int | None, tighter: bool = False,
                      breathe: bool = False, land: bool = False) -> dict:
    """Apply `--tighter`, `--breathe`, or `--land` to `scene_idx` on a deep copy of `story`."""
    chosen = [name for name, flag in (("tighter", tighter), ("breathe", breathe), ("land", land)) if flag]
    if not chosen:
        return {"story": story, "verb": None, "delta_frames": 0, "edits": []}
    if len(chosen) > 1:
        raise ValueError(f"choose one rhythm verb at a time (got {', '.join('--' + c for c in chosen)})")
    scenes = story.get("scenes") or []
    if scene_idx is None:
        raise ValueError(f"--{chosen[0]} requires --scene <0..{len(scenes) - 1}>")
    verb = chosen[0]
    updated = copy.deepcopy(story)
    steer_map = updated.setdefault("steer", {}).setdefault("scenes", {})
    entry = dict(steer_map.get(str(scene_idx)) or {})
    prev_frames = int(entry.get("frames") or 0)
    delta = {"tighter": TIGHTER_FRAMES, "breathe": BREATHE_FRAMES, "land": LAND_FRAMES}[verb]
    entry["frames"] = prev_frames + delta
    entry["verb"] = verb
    steer_map[str(scene_idx)] = entry
    edits = [f"scene {scene_idx} --{verb} ({delta:+d} frames / {delta / FPS:+.2f}s)"]
    if verb == "land" and not updated["scenes"][scene_idx].get("em"):
        em = _auto_em_candidate(updated, scene_idx)
        if em:
            updated["scenes"][scene_idx]["em"] = em
            edits.append(f"scene {scene_idx} em={em!r}")
    return {"story": updated, "verb": verb, "delta_frames": delta, "edits": edits}


def _resolve_target(target_arg: str | pathlib.Path) -> dict:

    """Resolve a target argument (story `.json`, render `.mp4`, render `.json`, or `.props.json`)."""
    p = pathlib.Path(target_arg)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.suffix.lower() == ".mp4":
        meta_json = p.with_suffix(".json")
        props_json = store.props_path(p)
        meta_data = json.loads(meta_json.read_text(encoding="utf-8")) if meta_json.exists() else {}
        story_file = pathlib.Path(meta_data["story"]) if meta_data.get("story") else None
        return {
            "story_path": story_file if story_file and story_file.exists() else None,
            "video_path": p.resolve(),
            "props_path": props_json.resolve() if props_json.exists() else None,
            "meta": meta_data,
        }
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "scenes" in data and "narration" in data:
        return {"story_path": p.resolve(), "video_path": None, "props_path": None, "meta": {}}
    if isinstance(data, dict) and "story" in data and "file" in data:
        mp4 = pathlib.Path(data["file"])
        sp = pathlib.Path(data["story"])
        pp = pathlib.Path(data["props"]) if data.get("props") else store.props_path(mp4)
        return {
            "story_path": sp.resolve() if sp.exists() else None,
            "video_path": mp4.resolve() if mp4.exists() else None,
            "props_path": pp.resolve() if pp.exists() else None,
            "meta": data,
        }
    raise ValueError(f"unrecognized target {p}: pass a story .json or a rendered .mp4")


def _estimate_tts_usd(story: dict, engine: str) -> float:
    """Estimate TTS dollar cost when narration changes."""
    if engine in ("silent", "edge"):
        return 0.0
    spoken = normalize_ka.speech(story.get("narration", ""), story.get("say"))
    words = speech.estimate_words(story.get("narration", ""))
    secs = words[-1]["end"] if words else 0.0
    text_tokens = max(1, len(spoken) // 3)
    audio_tokens = round(secs * costs.AUDIO_TOKENS_PER_SECOND)
    return round(float(costs.tts_usd(text_tokens, audio_tokens) or 0.0), 6)


def _build_preview_props(story: dict, fmt: dict, engine: str = "silent",
                         locked_from: dict | None = None, director: str | None = None) -> tuple[pathlib.Path, dict]:
    """Build deterministic props for `story`, locking style/transition/music/theme to `locked_from` when steering an
    existing render so unchanged scenes keep their exact segment hashes."""
    tmp_dir = store.work_dir(f"steer-{story.get('id', 'tmp')}")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_story = tmp_dir / "story.json"
    tmp_story.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    look = (locked_from or {}).get("variant") or fmt["look"]
    transition = (locked_from or {}).get("transition") or fmt["transition"]
    outro = (locked_from or {}).get("outro") or fmt["outro"]
    theme = (locked_from or {}).get("theme") or fmt.get("theme") or "default"
    forced_style = (locked_from or {}).get("style")
    music_choice = fmt["music"]
    if locked_from and "music" in locked_from:
        music_choice = "off" if not locked_from["music"] else fmt["music"]
    work, built = props.build(
        str(tmp_story),
        variant=look,
        engine=engine,
        tone=tone,
        edge_voice=speech.EDGE_VOICES["eka"],
        platform=fmt["platform"],
        caption_design=fmt["captions"],
        music=music_choice,
        transition=transition,
        style=forced_style,
        outro=outro,
        director=director,
        theme=theme,
        **formats.render_keys(fmt),
    )
    if locked_from and locked_from.get("music"):
        built["music"] = locked_from["music"]
        (work / "props.json").write_text(json.dumps(built, ensure_ascii=False), encoding="utf-8")
    return work, built


def steer(target: str | pathlib.Path, scene: int | str | None = None,
          set_kv: list[str] | dict | str | None = None,
          tighter: bool = False, breathe: bool = False, land: bool = False,
          dry: bool = False, out_path: str | pathlib.Path | None = None,
          engine: str = "silent", format_name: str | None = None,
          look: str | None = None, director: str | None = None,
          project: str | pathlib.Path | None = None,
          renderer: str | None = None, write_story: bool = False) -> dict:
    """Steer one scene (or narration) of a film, or report the exact pre-run cost when `dry=True`."""
    t0 = time.perf_counter()
    resolved = _resolve_target(target)
    story_path = resolved["story_path"]
    if not story_path or not story_path.exists():
        raise FileNotFoundError(f"story JSON not found for {target}")
    before_story = json.loads(story_path.read_text(encoding="utf-8"))
    num_scenes = len(before_story.get("scenes") or [])
    scene_idx = parse_scene_arg(scene, num_scenes)
    pairs = parse_set_args(set_kv)
    if not pairs and not any((tighter, breathe, land)):
        raise ValueError("nothing to steer: pass --set field=value or one of --tighter, --breathe, --land")

    slot_res = apply_slot_edits(before_story, scene_idx, pairs)
    verb_res = apply_rhythm_verb(slot_res["story"], scene_idx, tighter=tighter, breathe=breathe, land=land)
    after_story = verb_res["story"]
    changed_narration = slot_res["changed_narration"]
    all_edits = slot_res["edits"] + verb_res["edits"]

    meta_info = resolved["meta"] or {}
    from tt_shorts import engine as eng_mod
    fmt = formats.get(format_name or meta_info.get("format") or eng_mod.program_format(str(story_path)),
                      look=look or meta_info.get("look"))
    film_engine = "hyperframes" if project else eng_mod.film_engine(str(story_path), fmt, director, renderer)

    locked_props = None
    if resolved["props_path"] and resolved["props_path"].exists():
        try:
            locked_props = json.loads(resolved["props_path"].read_text(encoding="utf-8"))
        except Exception:
            locked_props = None

    work_before, before_props = _build_preview_props(
        before_story, fmt, engine=engine, locked_from=locked_props, director=director
    )
    work_after, after_props = _build_preview_props(
        after_story, fmt, engine=engine, locked_from=before_props, director=director
    )

    # Only what this change introduced stops it: a film's older problems are `check`'s to report, not steer's.
    story_problems = [x for x in eng_mod.check_story(after_story) if x not in set(eng_mod.check_story(before_story))]
    motion_after = motion_rules.check(after_props)
    motion_before = set(motion_rules.check(before_props)["holds"])
    problems = list(story_problems) + [h for h in motion_after["holds"] if h not in motion_before]

    before_scenes = before_props.get("scenes") or []
    after_scenes = after_props.get("scenes") or []
    total_frames = int(after_props.get("durationInFrames") or 0)
    total_seconds = round(total_frames / FPS, 2)

    if changed_narration:
        change_kind = "narration"
        dirty_scenes = list(range(len(after_scenes)))
        clean_scenes = []
        frames_to_render = total_frames
        seconds_to_render = round(frames_to_render / FPS, 1)
        dollars = _estimate_tts_usd(after_story, engine)
        voice_status = "new"
        full_render = True
        cost_line = (
            f"new voice, every frame ({seconds_to_render:.1f} s of picture, "
            f"all {len(after_scenes)} scenes, ${dollars:.2f})"
        )
    else:
        dirty_scenes = []
        clean_scenes = []
        for i in range(len(after_scenes)):
            k_before = segments.segment_key(before_props, i, work_before) if i < len(before_scenes) else None
            k_after = segments.segment_key(after_props, i, work_after)
            if k_before != k_after:
                dirty_scenes.append(i)
            else:
                clean_scenes.append(i)
        if not dirty_scenes and scene_idx is not None and 0 <= scene_idx < len(after_scenes):
            dirty_scenes = [scene_idx]
            clean_scenes = [i for i in range(len(after_scenes)) if i != scene_idx]
        frames_to_render = sum(int(after_scenes[i]["duration"]) for i in dirty_scenes)
        seconds_to_render = round(frames_to_render / FPS, 1)
        dollars = 0.0
        voice_status = "cached"
        full_render = False
        change_kind = "timing" if verb_res["verb"] and not pairs else ("text+timing" if verb_res["verb"] else "text")
        if len(dirty_scenes) == 1:
            idx0 = dirty_scenes[0]
            s0 = after_scenes[idx0]
            f_start = int(s0["from"])
            f_end = f_start + int(s0["duration"]) - 1
            cost_line = (
                f"{seconds_to_render:.1f} s of picture "
                f"(scene {idx0} of {len(after_scenes)}, frames {f_start}-{f_end}), $0"
            )
        else:
            joined = ", ".join(f"s{i}" for i in dirty_scenes)
            cost_line = (
                f"{seconds_to_render:.1f} s of picture "
                f"({len(dirty_scenes)} of {len(after_scenes)} scenes: {joined}), $0"
            )

    saved_frames = max(0, total_frames - frames_to_render)
    saved_seconds = round(saved_frames / FPS, 1)
    saved_pct = round(100.0 * saved_frames / max(1, total_frames), 1)

    summary = {
        "story": str(story_path),
        "renderer": film_engine,
        "engine": engine,
        "scene": scene_idx,
        "kind": change_kind,
        "verb": verb_res["verb"],
        "edits": all_edits,
        "dry": bool(dry),
        "full_render": full_render,
        "voice": voice_status,
        "dollars": dollars,
        "dirty_scenes": dirty_scenes,
        "clean_scenes": clean_scenes,
        "frames_to_render": frames_to_render,
        "seconds_to_render": seconds_to_render,
        "total_frames": total_frames,
        "total_seconds": total_seconds,
        "saved_frames": saved_frames,
        "saved_seconds": saved_seconds,
        "saved_pct": saved_pct,
        "cost": cost_line,
        "motion": {
            "holds": motion_after["holds"],
            "warnings": motion_after["warnings"],
        },
        "problems": problems,
    }

    if dry or problems:
        return summary

    if True:  # a steer is saved: the next one starts from this story
        story_path.write_text(json.dumps(after_story, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    target_mp4 = (
        pathlib.Path(out_path).resolve()
        if out_path
        else (
            resolved["video_path"]
            if resolved["video_path"]
            else store.render_path(
                packs.of(after_story)["name"],
                after_story["id"],
                fmt["name"],
                after_props["variant"],
                fmt["captions"],
            ).resolve()
        )
    )

    if film_engine == "hyperframes":
        from tt_shorts import compose
        proj_dir = (
            pathlib.Path(project).resolve()
            if project
            else compose.project_dir(after_story, packs.of(after_story)["name"])
        )
        if not (proj_dir / "beats.json").exists():
            compose.scaffold(story_path, brand=packs.of(after_story)["name"], project=proj_dir, force=True)
        # If a slot in slots.json maps to the edited scene text directly, keep story.json updated in project
        (proj_dir / "story.json").write_text(json.dumps(after_story, ensure_ascii=False, indent=1), encoding="utf-8")
        hf_res = compose.render(
            story_path, fmt, brand=packs.of(after_story)["name"], project=proj_dir, engine=engine,
            out_path=target_mp4,
        )  # segmented unless SHORTS_SEGMENTS=0: the cached scenes are reused
        summary["file"] = hf_res.get("file", str(target_mp4))
        summary["problems"] = hf_res.get("problems", [])
        summary["elapsed_seconds"] = round(time.perf_counter() - t0, 3)
        target_mp4.with_suffix(".json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
        summary["room"] = room.write_room(target_mp4, story_path=story_path, engine_override="hyperframes")["room_html"]
        return summary

    # Remotion lane: ensure cached segments exist for clean scenes if steering an already-rendered video
    props.render_video(work_after, after_props, target_mp4, segmented=True)

    # Probe only the dirty scenes (or all if full_render) + flash safety check
    all_settled = probe.settled(after_props["scenes"])
    probe_frames = [all_settled[i] for i in (dirty_scenes or range(len(all_settled))) if 0 <= i < len(all_settled)] or all_settled
    if probe.enabled():
        try:
            job = {
                "props": str(pathlib.Path(work_after) / "props.json"),
                "public": str(pathlib.Path(work_after) / "public"),
                "frames": probe_frames,
                "out": None,
                "name": after_props["variant"],
            }
            per, _ = probe.run_jobs([job])
            probe_res = probe.judge(per[0], job["public"], probe_frames)
            shutil.rmtree(pathlib.Path(work_after) / "probe-serve", ignore_errors=True)
        except Exception as e:
            probe_res = {"problems": [f"probe error: {str(e)[:240]}"], "frames": probe_frames}
    else:
        probe_res = {"problems": []}
    flash_probs = flash.problems(flash.measure(target_mp4))
    post_problems = list(probe_res.get("problems") or []) + list(flash_probs or [])
    summary["probe"] = probe_res
    summary["flash_problems"] = flash_probs
    summary["problems"] = problems + post_problems

    side_props = store.props_path(target_mp4)
    side_props.write_text(json.dumps(after_props, ensure_ascii=False), encoding="utf-8")
    summary["file"] = str(target_mp4)
    summary["props"] = str(side_props)

    seg_manifest_file = segments.manifest_path(target_mp4)
    if seg_manifest_file.exists():
        seg_manifest = json.loads(seg_manifest_file.read_text(encoding="utf-8"))
        summary["hits"] = seg_manifest.get("hits", [])
        summary["misses"] = seg_manifest.get("misses", [])
        summary["splice_mode"] = seg_manifest.get("splice_mode")

    summary["elapsed_seconds"] = round(time.perf_counter() - t0, 3)
    target_mp4.with_suffix(".json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    summary["room"] = room.write_room(target_mp4, story_path=story_path, engine_override="remotion")["room_html"]
    return summary
