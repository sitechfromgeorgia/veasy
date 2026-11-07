"""`engine look`: what exists for a job or a story, and the next step. Free: it only reads.

    engine look --job j_91 | --story stories/24835.json
    -> {"kind": "job"|"story", "id", "story", "state", "sheets", "numbers", "warnings", "problems", "checks",
        "concept", "next", "tools"}

It never renders, never calls a model and never writes: a sheet, a props file or a report that is already on disk
is listed (and read for its numbers); one that is not is named in `missing`, with the command that makes it. The
tools other lanes add (review, steer, brush book) are pointed at when this build has them, and named under
`tools.absent` when it hasn't: a missing one is never an error.
"""
import importlib.util
import json
import pathlib

from tt_shorts import engine, ka_check, motion_rules, programs, queue, speech, store

# the verbs `look` points at, and the module that makes each one real in this build
SIBLINGS = {"veasy_review": "tt_shorts.review", "veasy_steer": "tt_shorts.steer", "veasy_brush_book": "tt_shorts.gallery"}
LOOK_SHEETS = ("*.jpg", "*.png")


def _have(module):
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _story_file(token):
    """A story named by a path, or by its name in stories/ (never a source ref)."""
    token = str(token).strip()
    root = pathlib.Path(__file__).resolve().parent.parent / "stories"
    for cand in (pathlib.Path(token), root / token, root / f"{token}.json"):
        try:
            if cand.suffix == ".json" and cand.is_file():
                return cand
        except (OSError, ValueError):
            pass
    return None


def _json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _render_files(result):
    """The sheets and props beside a render the job recorded -> ({name: path}, [missing names])."""
    video = (result or {}).get("file")
    found, missing = {}, []
    if not video:
        return found, missing
    v = pathlib.Path(video)
    for name, path in (("video", v), ("qa_sheet", v.with_suffix(".sheet.jpg")), ("plan_sheet", store.plan_sheet_path(v)),
                       ("props", store.props_path(v))):
        (found.__setitem__(name, str(path)) if path.exists() else missing.append(name))
    return found, missing


def _compose_sheets(story):
    """The sheets `engine compose look` saved for a composed film, when its project exists."""
    project = store.home() / "cache" / "compose" / f"{store.safe(story.get('brand') or 'tbilisi-today')}-{store.safe(story.get('id'))}"
    where = project / ".veasy" / "look"
    return sorted(str(p) for pat in LOOK_SHEETS for p in where.rglob(pat)) if where.is_dir() else []


def _numbers(story, props):
    scenes = [s for s in story.get("scenes") or [] if isinstance(s, dict)]
    words = speech.estimate_words(story.get("narration") or "")
    n = {"scenes": len(scenes), "types": [s.get("type") for s in scenes], "narration_words": len(words),
         "seconds_estimated": round(words[-1]["end"] + 0.5, 1) if words else 0}
    if props:  # the render's real numbers
        n["scene_frames"] = [s.get("frames") for s in props.get("scenes", []) if isinstance(s, dict) and "frames" in s]
        if props.get("durationInFrames"):
            n["seconds"] = round(props["durationInFrames"] / speech.FPS, 1)
    return n


def _next(kind, job, story, state, problems, has_render, tools):
    jid = job["id"] if job else None
    if story is None:
        return "queue the job for a story (veasy_queue add), or write one (veasy_write); it has no story file yet"
    if problems:
        return "fix the problems, then veasy_check again (free)"
    if state in ("done", None) and has_render:
        return "veasy_package to get the publishing kit" + (f"; {_review(tools)}" if _review(tools) else "")
    if state == "held":
        return "watch the render, then `queue approve " + str(jid) + "` or `queue reject` (a held film waits for a person)"
    if state == "failed":
        return "read the error, fix it, then `queue retry " + str(jid) + "`"
    if state in ("queued", "writing", "rendering"):
        return f"wait: the job is {state}; look again later (free)"
    return "veasy_plan for the free storyboard, then veasy_render" + (f"; {_review(tools)}" if _review(tools) else "")


def _review(tools):
    return "veasy_review for a critic's read" if "veasy_review" in tools["present"] else ""


def look(job=None, story=None):
    """-> the dict above. One of job/story. Raises ValueError for neither, or for a job/story that does not exist."""
    if not job and not story:
        raise ValueError("look needs a job id or a story: --job j_91 | --story stories/24835.json")
    row, path, kind = None, None, "story"
    if job:
        row, kind = queue.get(str(job)), "job"
        if row is None:
            raise ValueError(f"no job {job!r}: `queue list` shows the jobs")
        path = pathlib.Path(row["story"]) if row.get("story") else None
    else:
        path = _story_file(story)
        if path is None:
            raise ValueError(f"no story file for {story!r}: give a path, or a name in stories/")
    data = _json(path) if path and path.exists() else None
    result = (row or {}).get("result") or {}
    sheets, missing = _render_files(result)
    props = _json(sheets["props"]) if "props" in sheets else None
    composed = _compose_sheets(data) if data else []
    problems, warnings, checks = [], [], {}
    if data is not None:
        side = store.sources_path(path)
        sources = _json(side) if side.exists() else None
        sources = sources if isinstance(sources, list) else None
        problems = engine.check_story(data, sources)
        warnings = list(ka_check.warnings(data))
        checks = {"story": "ok" if not problems else f"{len(problems)} problem(s)", "news_rules": bool(sources),
                  "program": programs.name_of(data)}
    if props:
        try:
            warnings += motion_rules.check(props)["warnings"]
            checks["motion"] = "read from the render's props"
        except Exception as e:  # noqa: BLE001 - a stale props file is a note, not a failure of look
            warnings.append(f"look: the cached props could not be read for the motion rules ({type(e).__name__})")
    elif data is not None:
        missing.append("motion (needs a plan or a render: veasy_plan)")
    qa = result.get("qa") or {}
    if qa.get("problems"):
        problems = problems + [f"qa: {p}" for p in qa["problems"]]
    tools = {"present": ["veasy_" + k for k in ("plan", "check", "render", "still", "probe", "package")]
             + [t for t, m in SIBLINGS.items() if _have(m)],
             "absent": [t for t, m in SIBLINGS.items() if not _have(m)]}
    state = (row or {}).get("state")
    return {"kind": kind, "id": (row or {}).get("id") or (data or {}).get("id"), "story": str(path) if path else None,
            "state": state, "error": (row or {}).get("error"), "sheets": {**sheets, **({"compose": composed} if composed else {})},
            "missing": missing, "numbers": _numbers(data, props) if data else {}, "warnings": warnings,
            "problems": problems, "checks": checks, "concept": (data or {}).get("concept"),
            "next": _next(kind, row, data, state, problems, "video" in sheets, tools), "tools": tools}
